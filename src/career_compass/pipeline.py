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
    load_constraints,
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
        steps.append("运行: uv run career-compass render-opportunities 渲染机会矩阵")
        steps.append("可选: uv run career-compass render-pack 渲染求职定位包")

    elif state.stage == Stage.plan:
        steps.append("用户已从矩阵选定方向 —— 按 playbooks/4-plan.md 展开")
        steps.append("运行: uv run career-compass render-strategy 生成 strategy 骨架")

    elif state.stage == Stage.done:
        steps.append("★ 主交付物已完成（机会矩阵）")
        steps.append("渲染执行材料: uv run career-compass render-pack && render-execution")
        steps.append("开始投递后: uv run career-compass track add ... / track funnel")
        steps.append("反馈修订: uv run career-compass replan [--write]")
        steps.append("若想深入某方向: 选一个方向 → playbooks/4-plan.md")
        steps.append("可选压测: playbooks/5-stress-test.md")

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
