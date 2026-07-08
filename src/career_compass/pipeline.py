"""Pipeline 编排：阶段检测、状态校验、run 预检。

阶段规则与 SKILL.md 一致：
  intake  → profile/约束/narrative 未通过 validate
  scan    → 画像齐了，signals 不足
  analyze → 有信号，尚无 opportunities.yaml
  plan    → 机会矩阵已有，strategy.md 存在（可选深入）
  done    → 机会矩阵已渲染（opportunities.md）
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .gather import scan_plan
from .schema import (
    ValidationError,
    count_signals,
    derive_education_summary,
    load_constraints,
    load_opportunities,
    load_profile,
    validate_constraints,
    validate_narrative,
    validate_profile_text_fields,
)


class Stage(str, Enum):
    intake = "intake"
    scan = "scan"
    analyze = "analyze"
    plan = "plan"
    done = "done"


STAGE_ORDER = [Stage.intake, Stage.scan, Stage.analyze, Stage.plan, Stage.done]

MIN_SIGNALS_FOR_ANALYZE = 1


@dataclass
class PipelineState:
    stage: Stage
    profile_gaps: list[str] = field(default_factory=list)
    signal_count: int = 0
    has_opportunities: bool = False
    has_opportunities_md: bool = False
    has_strategy: bool = False
    validation_errors: list[str] = field(default_factory=list)
    validation_warnings: list[str] = field(default_factory=list)


def _templates_dir(project_root: Path | None = None) -> Path:
    root = project_root or Path.cwd()
    return root / "templates"


def run_validation(data_dir: Path) -> tuple[list[str], list[str]]:
    """运行完整校验，返回 (errors, warnings)。"""
    errors: list[str] = []
    warnings: list[str] = []

    profile_path = data_dir / "profile.yaml"
    constraints_path = data_dir / "constraints.yaml"
    narrative_path = data_dir / "narrative.md"

    if not profile_path.exists():
        errors.append(f"缺少 {profile_path.name} —— 从 templates/ 拷贝并填写")
        return errors, warnings

    try:
        profile = load_profile(profile_path)
    except ValidationError as e:
        errors.append(f"profile.yaml 结构校验失败: {e}")
        return errors, warnings

    for gap in profile.gaps():
        errors.append(gap)

    vr = validate_profile_text_fields(profile)
    warnings.extend(i.message for i in vr.warnings)

    if not constraints_path.exists():
        errors.append("constraints.yaml 缺失")
    else:
        try:
            constraints = load_constraints(constraints_path)
            cr = validate_constraints(constraints)
            warnings.extend(i.message for i in cr.warnings)
        except ValidationError as e:
            errors.append(f"constraints.yaml 结构校验失败: {e}")

    if not narrative_path.exists():
        warnings.append("narrative.md 缺失 —— intake 建议填写职业故事与红线")
    else:
        nr = validate_narrative(narrative_path.read_text(encoding="utf-8"))
        errors.extend(i.message for i in nr.errors)
        warnings.extend(i.message for i in nr.warnings)

    return errors, warnings


# ---------- Schema 2.3 资格闸门校验 ----------

_ELIGIBILITY_FAIL_OK_COMPOSITES = {"D", "E", "F"}
_FACULTY_ELITE_TIERS = {"211", "985"}
_FIRST_DEGREE_BLOCKED_TIERS = {"二本", "三本"}


def validate_eligibility(matrix) -> "ValidationResult":
    """校验机会矩阵的资格闸门字段是否合规。

    返回 schema.ValidationResult：
    - ERROR：cell.eligibility==fail 但 composite ∈ {A,B,C}（封顶未执行）
    - ERROR：211/985 教职格 cell 缺 eligibility 或错误 pass，且画像第一学历为二本/三本
    - WARNING：211/985 教职格 cell 未填 institution_tier / employer_subtype
    """
    from .schema import ValidationIssue, ValidationResult

    errors: list[ValidationIssue] = []
    warnings: list[ValidationIssue] = []

    # 画像第一学历（用于 211/985 教职格 cross-check）
    first_degree_tier: str | None = None
    # matrix 本身不持有 profile；调用方负责传入更准确，这里尽力从 capability 推断
    # 真正的 cross-check 在 cmd_validate 里带 profile 再跑一次（见 cli.py）
    for cell in matrix.cross_matrix:
        elig = (cell.eligibility or "pass").strip().lower()
        comp = (cell.composite or "").strip().upper()
        # 规则 1：fail 但 composite 仍 >=C
        if elig == "fail" and comp not in _ELIGIBILITY_FAIL_OK_COMPOSITES:
            errors.append(ValidationIssue(
                level="error",
                field=f"cross_matrix.{cell.capability_id}:{cell.employer_id}",
                message=(
                    f"资格关 fail 但 composite={comp}（应 ≤D）—— "
                    f"资格闸门封顶未执行；rationale: {cell.eligibility_rationale}"
                ),
            ))
        # 规则 2：211/985 教职格元数据缺失
        sub = (cell.employer_subtype or "").strip()
        tier = (cell.institution_tier or "").strip()
        if sub == "university_faculty" and tier in _FACULTY_ELITE_TIERS:
            if not cell.eligibility_rationale and elig == "pass":
                warnings.append(ValidationIssue(
                    level="warning",
                    field=f"cross_matrix.{cell.capability_id}:{cell.employer_id}",
                    message=f"{tier} 教职格 eligibility=pass 但无 rationale，确认资格闸门已运行",
                ))

    return ValidationResult(errors=errors, warnings=warnings)


def validate_eligibility_with_profile(matrix, profile) -> "ValidationResult":
    """带 profile 的资格闸门 cross-check：
    - 211/985 教职格若 eligibility 缺失或 pass，但画像第一学历 ∈ {二本,三本} → ERROR
    """
    from .schema import ValidationIssue, ValidationResult

    base = validate_eligibility(matrix)
    edu = derive_education_summary(profile)
    first_tier = (edu.first_degree_tier or "").strip()

    extra_errors: list[ValidationIssue] = []
    if first_tier in _FIRST_DEGREE_BLOCKED_TIERS:
        for cell in matrix.cross_matrix:
            sub = (cell.employer_subtype or "").strip()
            tier = (cell.institution_tier or "").strip()
            if sub == "university_faculty" and tier in _FACULTY_ELITE_TIERS:
                elig = (cell.eligibility or "pass").strip().lower()
                if elig == "pass":
                    extra_errors.append(ValidationIssue(
                        level="error",
                        field=f"cross_matrix.{cell.capability_id}:{cell.employer_id}",
                        message=(
                            f"{tier} 教职格 eligibility=pass，但画像第一学历为「{first_tier}」—— "
                            f"211/985 教职格未运行资格闸门或错误通过"
                        ),
                    ))
    return ValidationResult(
        errors=base.errors + extra_errors,
        warnings=base.warnings,
    )


def detect_stage(data_dir: Path) -> PipelineState:
    """根据 data/ 文件推断当前阶段。"""
    errors, warnings = run_validation(data_dir)
    signals_dir = data_dir / "signals"
    signal_count = count_signals(signals_dir)
    opps_yaml = data_dir / "opportunities.yaml"
    opps_md = data_dir / "opportunities.md"
    strategy = data_dir / "strategy.md"

    has_opps = opps_yaml.exists()
    has_opps_md = opps_md.exists()
    has_strategy = strategy.exists()

    profile_gaps = []
    if (data_dir / "profile.yaml").exists():
        try:
            profile_gaps = load_profile(data_dir / "profile.yaml").gaps()
        except ValidationError:
            pass

    state = PipelineState(
        stage=Stage.intake,
        profile_gaps=profile_gaps,
        signal_count=signal_count,
        has_opportunities=has_opps,
        has_opportunities_md=has_opps_md,
        has_strategy=has_strategy,
        validation_errors=errors,
        validation_warnings=warnings,
    )

    if errors or profile_gaps:
        state.stage = Stage.intake
    elif signal_count < MIN_SIGNALS_FOR_ANALYZE:
        state.stage = Stage.scan
    elif not has_opps or not has_opps_md:
        state.stage = Stage.analyze
    elif has_strategy:
        state.stage = Stage.plan
    else:
        state.stage = Stage.done

    return state


def next_steps(state: PipelineState, data_dir: Path, project_root: Path | None = None) -> list[str]:
    """根据阶段给出下一步操作建议。"""
    root = project_root or Path.cwd()
    steps: list[str] = []

    if state.stage == Stage.intake:
        steps.append("补齐 profile.yaml / constraints.yaml / narrative.md")
        steps.append("运行: uv run career-compass validate")
        if not (_templates_dir(root) / "profile.example.yaml").exists():
            steps.append("⚠️ templates/ 缺失，请从仓库恢复模板")
        else:
            steps.append("模板: cp templates/profile.example.yaml data/profile.yaml（constraints 同理）")
        steps.append("可选: uv run career-compass scan-projects <项目路径> 自动采集证据")

    elif state.stage == Stage.scan:
        steps.append("运行: uv run career-compass scan-plan 获取检索查询")
        steps.append("联网检索后: uv run career-compass new-signal DOMAIN TOPIC FINDING SOURCE [URL]")
        steps.append(f"当前信号 {state.signal_count} 条，建议至少 {MIN_SIGNALS_FOR_ANALYZE} 条再进入 analyze")
        steps.append("参考 playbook: playbooks/2-scan.md")

    elif state.stage == Stage.analyze:
        steps.append("运行: uv run career-compass brief 聚合分析输入")
        steps.append("可选: uv run career-compass match --write-draft 生成候选机会草稿")
        steps.append("按 playbooks/3-analyze.md 审阅/修订 data/opportunities.yaml")
        steps.append("运行: uv run career-compass render-opportunities 渲染机会矩阵 ★核心交付★")

    elif state.stage == Stage.plan:
        steps.append("用户已从矩阵选定方向 —— 按 playbooks/4-plan.md 展开")
        steps.append("运行: uv run career-compass render-strategy 生成 strategy 骨架")

    elif state.stage == Stage.done:
        steps.append("★ 核心交付已完成：机会矩阵（opportunities.md）")
        steps.append("可选 — 方向深化: playbooks/4-plan.md → strategy.md（可压测 5-stress-test）")
        steps.append("可选 — 战术延伸(L3): uv run career-compass render-execution")
        steps.append("可选 — 长期修正(L4): track add / track funnel / replan [--write]")
        steps.append("可选 — 汇总视图: uv run career-compass render-pack（与矩阵信息重叠，一般不必）")

    return steps


def run_stage_check(
    stage: Stage,
    data_dir: Path,
    project_root: Path | None = None,
) -> tuple[bool, list[str]]:
    """执行某阶段的预检与提示；返回 (ok, messages)。"""
    root = project_root or Path.cwd()
    state = detect_stage(data_dir)
    messages: list[str] = []

    if stage == Stage.intake:
        tmpl = _templates_dir(root)
        for name in ("profile.example.yaml", "constraints.example.yaml"):
            p = tmpl / name
            if p.exists():
                messages.append(f"✅ 模板存在: {p}")
            else:
                messages.append(f"❌ 模板缺失: {p}")
        if state.validation_errors:
            messages.append("❌ validate 未通过，请先补齐:")
            messages.extend(f"  - {e}" for e in state.validation_errors)
            return False, messages
        messages.append("✅ intake 校验通过，可进入 scan")
        messages.append("💡 建议: uv run career-compass scan-projects <path> 采集项目证据")
        return True, messages

    if stage == Stage.scan:
        if state.validation_errors:
            messages.append("❌ 请先完成 intake（validate 未通过）:")
            messages.extend(f"  - {e}" for e in state.validation_errors)
            return False, messages
        messages.append("✅ validate 通过，生成检索计划:")
        profile = load_profile(data_dir / "profile.yaml")
        constraints = None
        cpath = data_dir / "constraints.yaml"
        if cpath.exists():
            constraints = load_constraints(cpath)
        sectors_path = data_dir / "sectors.yaml"
        for q in scan_plan(profile, sectors_path=sectors_path, constraints=constraints):
            messages.append(f"  · {q}")
        messages.append(f"当前信号: {state.signal_count} 条")
        if state.signal_count < MIN_SIGNALS_FOR_ANALYZE:
            messages.append(f"⚠️ 信号不足（需 ≥ {MIN_SIGNALS_FOR_ANALYZE}），继续 new-signal 入库")
            return False, messages
        messages.append("✅ 信号充足，可进入 analyze")
        return True, messages

    if stage == Stage.analyze:
        if state.signal_count < MIN_SIGNALS_FOR_ANALYZE:
            messages.append(f"❌ 需要至少 {MIN_SIGNALS_FOR_ANALYZE} 条信号，当前 {state.signal_count}")
            return False, messages
        messages.append(f"✅ 信号 {state.signal_count} 条")
        messages.append("💡 运行 brief 获取分析输入: uv run career-compass brief")
        messages.append("💡 可选 match 生成草稿: uv run career-compass match --write-draft")
        messages.append("💡 审阅后写/改 opportunities.yaml，再: uv run career-compass render-opportunities")
        if state.has_opportunities:
            messages.append("✅ opportunities.yaml 已存在")
            if not state.has_opportunities_md:
                messages.append("⚠️ 尚未渲染 opportunities.md")
            else:
                messages.append("✅ 机会矩阵已渲染")
            return True, messages
        messages.append("⚠️ 尚无 opportunities.yaml —— 按 playbook 3-analyze 生成")
        return False, messages

    if stage in (Stage.plan, Stage.done):
        messages.append(f"当前检测到阶段: {state.stage.value}")
        messages.extend(next_steps(state, data_dir, root))
        return state.stage == Stage.done, messages

    return True, messages
