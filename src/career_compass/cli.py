"""Career-Compass CLI 入口。

命令:
  career-compass validate              校验画像/约束，列出完整性缺口
  career-compass status                检测当前 pipeline 阶段与下一步
  career-compass run [--stage STAGE]   编排 pipeline 阶段预检
  career-compass brief                 输出供分析用的统一 brief
  career-compass scan-plan             基于画像生成检索查询
  career-compass new-signal DOMAIN TOPIC FINDING SOURCE [URL] [--confidence LEVEL]
  career-compass scan-projects <path>...  扫描指定项目目录，自动提取证据
  career-compass render-opportunities  把 opportunities.yaml 渲染成机会矩阵(核心交付物)
  career-compass render-strategy       渲染 strategy.md 骨架（选定方向后用）
  career-compass match [--write-draft]  运行匹配引擎，输出摘要或写 opportunities.draft.yaml
  career-compass render-pack [--stdout] 渲染求职定位包 v1 → data/job_pack.md
  career-compass render-execution [--stdout] 渲染求职执行包 → data/execution_pack.md
  career-compass track add|list|update|funnel  投递追踪
  career-compass replan [--write]      反馈闭环 → 修订建议 / opportunities.revised.yaml
  career-compass jd-analyze <file>     JD 技能聚类 vs 画像缺口
  career-compass job add|list|show|analyze|remove  感兴趣岗位库（收藏 JD）

数据目录默认 ./data，可用环境变量 CC_DATA 覆盖。
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

from .gather import add_signal, scan_plan
from .jd_analyze import analyze_jd_file
from .jobs import (
    add_saved_job,
    analyze_saved_job,
    get_saved_job,
    list_saved_jobs,
    remove_saved_job,
)
from .match import generate_candidate_opportunities
from .pipeline import Stage, detect_stage, next_steps, run_stage_check
from .replan import replan_and_optional_write
from .render import brief, render_execution_pack, render_job_pack, render_opportunities, render_strategy
from .scanner import scan_project
from .schema import (
    ApplicationStatus,
    ApplicationTier,
    OpportunityMatrix,
    ProjectsFile,
    ValidationError,
    Constraints,
    load_constraints,
    load_industry_graph,
    load_opportunities,
    load_profile,
    load_projects,
    load_role_taxonomy,
    load_sectors,
    load_signals,
    save_opportunities,
    save_projects,
)
from .track import add_application, funnel_stats, list_applications, update_application

DATA = Path(os.getenv("CC_DATA", "data"))
PROFILE = DATA / "profile.yaml"
CONSTRAINTS = DATA / "constraints.yaml"
NARRATIVE = DATA / "narrative.md"
SIGNALS = DATA / "signals"
SECTORS = DATA / "sectors.yaml"
PROJECTS = DATA / "projects.yaml"
OPPORTUNITIES_YAML = DATA / "opportunities.yaml"
OPPORTUNITIES_DRAFT = DATA / "opportunities.draft.yaml"
OPPORTUNITIES_MD = DATA / "opportunities.md"
JOB_PACK = DATA / "job_pack.md"
EXECUTION_PACK = DATA / "execution_pack.md"
APPLICATIONS = DATA / "applications.yaml"
SAVED_JOBS = DATA / "saved_jobs.yaml"
OPPORTUNITIES_REVISED = DATA / "opportunities.revised.yaml"
INDUSTRY_GRAPH = DATA / "industry_graph.yaml"
ROLE_TAXONOMY = DATA / "role_taxonomy.yaml"
STRATEGY = DATA / "strategy.md"
PROJECT_ROOT = Path.cwd()


def _print_validation(errors: list[str], warnings: list[str]) -> None:
    if errors:
        print("❌ 错误（必须修复）:")
        for e in errors:
            print(f"  - {e}")
    if warnings:
        print("⚠️  警告（建议补齐）:")
        for w in warnings:
            print(f"  - {w}")


def cmd_validate(_args: argparse.Namespace) -> int:
    from .pipeline import run_validation

    errors, warnings = run_validation(DATA)

    if errors:
        _print_validation(errors, warnings)
        return 1

    if warnings:
        _print_validation(errors, warnings)
        print("\n✅ 画像结构完整，但有警告 —— 建议回到 playbook 1-intake 补齐")
        return 2

    print("✅ 画像与约束完整，可进入 playbook 2-scan / 3-analyze")
    return 0


def cmd_status(_args: argparse.Namespace) -> int:
    state = detect_stage(DATA)
    print(f"当前阶段: {state.stage.value}")
    print(f"  信号: {state.signal_count} 条")
    print(f"  机会矩阵: {'✅' if state.has_opportunities else '—'} yaml · "
          f"{'✅' if state.has_opportunities_md else '—'} md")
    if state.has_strategy:
        print("  strategy.md: ✅")

    if state.validation_errors:
        print("\n阻塞项:")
        for e in state.validation_errors[:5]:
            print(f"  - {e}")
        if len(state.validation_errors) > 5:
            print(f"  … 共 {len(state.validation_errors)} 项")

    if state.validation_warnings:
        print("\n建议项:")
        for w in state.validation_warnings[:3]:
            print(f"  - {w}")

    print("\n下一步:")
    for step in next_steps(state, DATA, PROJECT_ROOT):
        print(f"  → {step}")

    return 0 if state.stage in (Stage.analyze, Stage.scan, Stage.done, Stage.plan) else 1


def cmd_run(args: argparse.Namespace) -> int:
    stage_name = args.stage
    if stage_name:
        try:
            stage = Stage(stage_name)
        except ValueError:
            valid = ", ".join(s.value for s in Stage)
            print(f"❌ 未知阶段 {stage_name!r}，可选: {valid}")
            return 1
    else:
        stage = detect_stage(DATA).stage

    print(f"▶ run --stage {stage.value}\n")
    ok, messages = run_stage_check(stage, DATA, PROJECT_ROOT)
    for line in messages:
        print(line)

    if not ok:
        print(f"\n⏸ 阶段 {stage.value} 预检未通过，请按提示补齐后重试")
        return 1

    print(f"\n✅ 阶段 {stage.value} 预检通过")
    if stage != Stage.done:
        nxt = list(Stage)
        idx = nxt.index(stage)
        if idx + 1 < len(nxt):
            print(f"💡 下一阶段: uv run career-compass run --stage {nxt[idx + 1].value}")
    return 0


def cmd_brief(_args: argparse.Namespace) -> int:
    print(brief(
        PROFILE, CONSTRAINTS, NARRATIVE, SIGNALS, SECTORS, PROJECTS,
        industry_graph_path=INDUSTRY_GRAPH,
        role_taxonomy_path=ROLE_TAXONOMY,
    ))
    return 0


def cmd_scan_plan(_args: argparse.Namespace) -> int:
    profile = load_profile(PROFILE)
    constraints = load_constraints(CONSTRAINTS) if CONSTRAINTS.exists() else None
    for q in scan_plan(profile, sectors_path=SECTORS, constraints=constraints):
        print(q)
    return 0


def cmd_new_signal(args: argparse.Namespace) -> int:
    path = add_signal(
        SIGNALS,
        args.domain,
        args.topic,
        args.finding,
        args.source,
        retrieved_on=date.today(),
        source_url=args.url,
        confidence=args.confidence,
    )
    print(f"✅ 已写入 {path}")
    return 0


def cmd_scan_projects(args: argparse.Namespace) -> int:
    """扫描用户点名的项目目录，提取证据写入 data/projects.yaml（按 path upsert）。"""
    existing = load_projects(PROJECTS) if PROJECTS.exists() else ProjectsFile(scanned_on=date.today())
    by_path = {p.path: p for p in existing.projects}
    for raw in args.paths:
        try:
            pe = scan_project(Path(raw))
            by_path[pe.path] = pe
            sig = ", ".join(pe.inferred_signals) or "(无明显信号)"
            print(f"✅ {pe.name}: {sig} · {pe.scale.files} files · {pe.scale.commits or 0} commits")
        except Exception as e:
            print(f"❌ {raw}: {e}")
    pf = ProjectsFile(scanned_on=date.today(), projects=list(by_path.values()))
    save_projects(PROJECTS, pf)
    print(f"\n写入 {PROJECTS}（共 {len(pf.projects)} 个项目）")
    return 0


def cmd_render_opportunities(_args: argparse.Namespace) -> int:
    if not OPPORTUNITIES_YAML.exists():
        print(f"❌ 找不到 {OPPORTUNITIES_YAML}。先跑 playbook 3-analyze 生成机会矩阵数据。")
        return 1
    out = render_opportunities(OPPORTUNITIES_YAML)
    OPPORTUNITIES_MD.write_text(out, encoding="utf-8")
    print(f"✅ 渲染机会矩阵到 {OPPORTUNITIES_MD}")
    return 0


def cmd_render_strategy(_args: argparse.Namespace) -> int:
    out = render_strategy({"date": date.today().isoformat()})
    STRATEGY.write_text(out, encoding="utf-8")
    print(f"✅ 渲染 strategy 骨架到 {STRATEGY}（选定方向后，交给 playbook 4-plan 填充）")
    return 0


def cmd_match(args: argparse.Namespace) -> int:
    """运行匹配引擎，打印摘要或写入 draft。"""
    if not PROFILE.exists():
        print(f"❌ 缺少 {PROFILE}")
        return 1
    if not INDUSTRY_GRAPH.exists() or not ROLE_TAXONOMY.exists():
        print("❌ 缺少 industry_graph.yaml 或 role_taxonomy.yaml")
        return 1

    profile = load_profile(PROFILE)
    constraints = load_constraints(CONSTRAINTS) if CONSTRAINTS.exists() else Constraints()
    graph = load_industry_graph(INDUSTRY_GRAPH)
    roles = load_role_taxonomy(ROLE_TAXONOMY)
    signals = load_signals(SIGNALS)
    projects = load_projects(PROJECTS) if PROJECTS.exists() else None

    opps = generate_candidate_opportunities(
        profile, constraints, graph, roles, signals, projects,
    )

    print(f"匹配引擎产出 {len(opps)} 个候选方向:\n")
    for i, o in enumerate(opps, 1):
        ms = o.role_families[0].match_score if o.role_families else None
        ms_s = f"{ms:.0%}" if ms is not None else "—"
        comp = f"{o.competition_index:.2f}" if o.competition_index is not None else "—"
        print(f"  {i}. {o.direction} [{o.composite}] 行业={o.industry} 匹配={ms_s} 竞争={comp}")
        if o.skill_gaps:
            gaps = ", ".join(g.skill for g in o.skill_gaps[:3])
            print(f"     缺口: {gaps}")

    if args.write_draft:
        matrix = OpportunityMatrix(generated_on=date.today(), directions=opps)
        save_opportunities(OPPORTUNITIES_DRAFT, matrix)
        print(f"\n✅ 草稿已写入 {OPPORTUNITIES_DRAFT}（审阅后可 mv 为 opportunities.yaml）")
    else:
        print("\n💡 加 --write-draft 写入 data/opportunities.draft.yaml")

    return 0


def cmd_render_pack(args: argparse.Namespace) -> int:
    if not OPPORTUNITIES_YAML.exists():
        print(f"❌ 找不到 {OPPORTUNITIES_YAML}")
        return 1
    if not PROFILE.exists():
        print(f"❌ 找不到 {PROFILE}")
        return 1

    out = render_job_pack(
        OPPORTUNITIES_YAML,
        PROFILE,
        role_taxonomy_path=ROLE_TAXONOMY if ROLE_TAXONOMY.exists() else None,
    )
    if args.stdout:
        print(out)
    else:
        JOB_PACK.write_text(out, encoding="utf-8")
        print(f"✅ 求职定位包已渲染到 {JOB_PACK}")
    return 0


def cmd_render_execution(args: argparse.Namespace) -> int:
    if not OPPORTUNITIES_YAML.exists():
        print(f"❌ 找不到 {OPPORTUNITIES_YAML}")
        return 1
    if not PROFILE.exists():
        print(f"❌ 找不到 {PROFILE}")
        return 1

    out = render_execution_pack(
        OPPORTUNITIES_YAML,
        PROFILE,
        NARRATIVE,
        CONSTRAINTS,
        role_taxonomy_path=ROLE_TAXONOMY if ROLE_TAXONOMY.exists() else None,
    )
    if args.stdout:
        print(out)
    else:
        EXECUTION_PACK.write_text(out, encoding="utf-8")
        print(f"✅ 求职执行包已渲染到 {EXECUTION_PACK}")
    return 0


def cmd_track(args: argparse.Namespace) -> int:
    sub = args.track_cmd

    if sub == "add":
        tier = ApplicationTier(args.tier)
        app = add_application(
            APPLICATIONS,
            args.company,
            args.role,
            tier=tier,
            direction=args.direction or "",
            channel=args.channel or "",
            status=ApplicationStatus.applied,
            notes=args.notes or "",
        )
        print(f"✅ 已记录投递 id={app.id} · {app.company} / {app.role} [{tier.value}]")
        return 0

    if sub == "list":
        apps = list_applications(APPLICATIONS)
        if not apps:
            print("(尚无投递记录 —— track add 开始记录)")
            return 0
        for a in apps:
            print(f"{a.id}\t{a.status.value}\t[{a.tier.value}]\t{a.company}\t{a.role}\t{a.applied_on}")
        return 0

    if sub == "update":
        try:
            status = ApplicationStatus(args.status)
        except ValueError:
            print(f"❌ 无效 status: {args.status}")
            return 1
        app = update_application(
            APPLICATIONS,
            args.id,
            status=status,
            feedback=args.feedback,
            notes=args.notes,
        )
        if not app:
            print(f"❌ 找不到 id={args.id}")
            return 1
        print(f"✅ 已更新 {app.id} → {app.status.value}")
        return 0

    if sub == "funnel":
        stats = funnel_stats(APPLICATIONS)
        print(f"投递总数: {stats['total']}")
        if stats["total"] == 0:
            print("(尚无数据)")
            return 0
        print(f"响应率: {stats['response_rate']:.0%} · 面试率: {stats['interview_rate']:.0%} · Offer率: {stats['offer_rate']:.0%}")
        print(f"ghosted: {stats['ghosted_count']} · rejected: {stats['rejected_count']}")
        print("按状态:", stats["by_status"])
        print("按梯队:", stats["by_tier"])
        if stats["feedback_keywords"]:
            print("\n反馈摘录:")
            for fb in stats["feedback_keywords"][:5]:
                print(f"  - {fb[:100]}")
        return 0

    print("❌ 未知 track 子命令")
    return 1


def cmd_replan(args: argparse.Namespace) -> int:
    report = replan_and_optional_write(
        APPLICATIONS,
        OPPORTUNITIES_YAML,
        OPPORTUNITIES_REVISED,
        write=args.write,
    )
    f = report.funnel
    print(f"=== Replan 报告 ({report.generated_on}) ===\n")
    print(f"漏斗: 共 {f['total']} 投 · 面试率 {f['interview_rate']:.0%} · ghosted {f['ghosted_count']}")

    if not report.suggestions:
        print("\n✅ 暂无修订建议（或尚无投递数据）")
        return 0

    print("\n建议:")
    for s in report.suggestions:
        print(f"  [{s.kind}] {s.target}: {s.reason}")
        if s.action:
            print(f"    → {s.action}")

    if args.write and report.revised_matrix:
        print(f"\n✅ 修订矩阵已写入 {OPPORTUNITIES_REVISED}")
        print("💡 审阅后可: mv data/opportunities.revised.yaml data/opportunities.yaml && render-opportunities")
    elif report.revised_matrix:
        print("\n💡 加 --write 写入 opportunities.revised.yaml")

    return 0


def cmd_jd_analyze(args: argparse.Namespace) -> int:
    if not PROFILE.exists():
        print(f"❌ 缺少 {PROFILE}")
        return 1
    path = Path(args.file)
    if not path.exists():
        print(f"❌ 找不到 {path}")
        return 1

    profile = load_profile(PROFILE)
    projects = load_projects(PROJECTS) if PROJECTS.exists() else None
    result = analyze_jd_file(path, profile, projects)

    print(f"JD 分析: {result.source}")
    print(f"技能覆盖率: {result.coverage_rate:.0%}\n")
    print("Top 技能词频:")
    for skill, cnt in list(result.skill_frequency.items())[:10]:
        print(f"  {skill}: {cnt}")

    if result.skill_gaps:
        print("\n相对画像的缺口:")
        for g in result.skill_gaps[:12]:
            print(f"  - [{g.priority}] {g.skill} ({g.notes})")
    else:
        print("\n✅ 与 Top JD 技能高度对齐")

    return 0


def _print_job_fit(report) -> None:
    print(f"\n=== {report.company} · {report.role} ===")
    print(f"id: {report.job_id}")
    print(f"摘要: {report.summary}")
    if report.linked_direction:
        print(f"关联机会矩阵方向: {report.linked_direction}")
    if report.matched_skills:
        print(f"已覆盖技能: {', '.join(report.matched_skills[:10])}")
    if report.skill_gaps:
        print("相对缺口:")
        for g in report.skill_gaps:
            print(f"  - {g}")
    if report.barriers:
        print("硬门槛 / 风险:")
        for b in report.barriers:
            print(f"  ⚠️  {b}")
    if report.notes:
        print(f"备注: {report.notes}")


def cmd_job(args: argparse.Namespace) -> int:
    sub = args.job_cmd

    if sub == "add":
        path = Path(args.file) if args.file else None
        if not path or not path.exists():
            print("❌ 请用 --file 指定 JD 文本文件")
            return 1
        desc = path.read_text(encoding="utf-8")
        job = add_saved_job(
            SAVED_JOBS,
            args.company,
            args.role,
            desc,
            location=args.location or "",
            source=args.source or "招聘软件",
            linked_direction=args.direction or "",
            notes=args.notes or "",
        )
        print(f"✅ 已保存岗位 id={job.id} · {job.company} / {job.role}")
        if PROFILE.exists():
            profile = load_profile(PROFILE)
            projects = load_projects(PROJECTS) if PROJECTS.exists() else None
            constraints = load_constraints(CONSTRAINTS) if CONSTRAINTS.exists() else None
            _print_job_fit(analyze_saved_job(job, profile, projects, constraints))
        return 0

    if sub == "list":
        jobs = list_saved_jobs(SAVED_JOBS)
        if not jobs:
            print("(尚无收藏岗位 —— job add --file jd.txt 开始收藏)")
            return 0
        for j in jobs:
            loc = f" @ {j.location}" if j.location else ""
            print(f"{j.id}\t[{j.status.value}]\t{j.company}\t{j.role}{loc}\t{j.saved_on}")
        return 0

    if sub == "show":
        job = get_saved_job(SAVED_JOBS, args.id)
        if not job:
            print(f"❌ 找不到 id={args.id}")
            return 1
        print(f"# {job.company} · {job.role}\n")
        print(f"状态: {job.status.value} · 来源: {job.source} · 保存于: {job.saved_on}")
        if job.location:
            print(f"地点: {job.location}")
        if job.linked_direction:
            print(f"关联方向: {job.linked_direction}")
        if job.notes:
            print(f"备注: {job.notes}")
        print("\n--- JD ---\n")
        print(job.description[:8000])
        return 0

    if sub == "analyze":
        if not PROFILE.exists():
            print(f"❌ 缺少 {PROFILE}")
            return 1
        profile = load_profile(PROFILE)
        projects = load_projects(PROJECTS) if PROJECTS.exists() else None
        constraints = load_constraints(CONSTRAINTS) if CONSTRAINTS.exists() else None
        jobs = list_saved_jobs(SAVED_JOBS)
        if args.id:
            jobs = [j for j in jobs if j.id == args.id]
            if not jobs:
                print(f"❌ 找不到 id={args.id}")
                return 1
        if not jobs:
            print("(尚无收藏岗位)")
            return 0
        for j in jobs:
            _print_job_fit(analyze_saved_job(j, profile, projects, constraints))
        return 0

    if sub == "remove":
        if remove_saved_job(SAVED_JOBS, args.id):
            print(f"✅ 已删除 {args.id}")
            return 0
        print(f"❌ 找不到 id={args.id}")
        return 1

    print("❌ 未知 job 子命令")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(prog="career-compass", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("validate", help="校验画像/约束完整性").set_defaults(func=cmd_validate)
    sub.add_parser("status", help="检测 pipeline 阶段与下一步").set_defaults(func=cmd_status)
    r = sub.add_parser("run", help="编排 pipeline 阶段预检")
    r.add_argument(
        "--stage",
        choices=[s.value for s in Stage],
        default=None,
        help="指定阶段（默认自动检测当前阶段）",
    )
    r.set_defaults(func=cmd_run)
    sub.add_parser("brief", help="输出统一 brief").set_defaults(func=cmd_brief)
    sub.add_parser("scan-plan", help="基于画像生成检索查询").set_defaults(func=cmd_scan_plan)

    s = sub.add_parser("new-signal", help="追加一条外部信号")
    s.add_argument("domain", help="trends / market / landscape")
    s.add_argument("topic")
    s.add_argument("finding")
    s.add_argument("source", help="可追溯的来源名")
    s.add_argument("url", nargs="?", default=None)
    s.add_argument("--confidence", default="medium", choices=["low", "medium", "high"])
    s.set_defaults(func=cmd_new_signal)

    sp = sub.add_parser("scan-projects", help="扫描指定项目目录，自动提取证据")
    sp.add_argument("paths", nargs="+", help="要扫描的项目目录（可多个）")
    sp.set_defaults(func=cmd_scan_projects)

    sub.add_parser("render-opportunities", help="渲染机会矩阵(核心交付物)").set_defaults(func=cmd_render_opportunities)
    sub.add_parser("render-strategy", help="渲染 strategy.md 骨架").set_defaults(func=cmd_render_strategy)

    m = sub.add_parser("match", help="运行匹配引擎生成候选机会")
    m.add_argument(
        "--write-draft",
        action="store_true",
        help="写入 data/opportunities.draft.yaml",
    )
    m.set_defaults(func=cmd_match)

    rp = sub.add_parser("render-pack", help="渲染求职定位包 v1")
    rp.add_argument("--stdout", action="store_true", help="输出到 stdout 而非 job_pack.md")
    rp.set_defaults(func=cmd_render_pack)

    re = sub.add_parser("render-execution", help="渲染求职执行包 (Phase 3)")
    re.add_argument("--stdout", action="store_true", help="输出到 stdout")
    re.set_defaults(func=cmd_render_execution)

    tr = sub.add_parser("track", help="投递追踪 (Phase 3)")
    tr_sub = tr.add_subparsers(dest="track_cmd", required=True)

    ta = tr_sub.add_parser("add", help="记录一次投递")
    ta.add_argument("company")
    ta.add_argument("role")
    ta.add_argument("--tier", default="B", choices=["A", "B", "C"])
    ta.add_argument("--direction", default="", help="对应机会矩阵 direction")
    ta.add_argument("--channel", default="", help="内推/官网/猎头")
    ta.add_argument("--notes", default="")
    ta.set_defaults(func=cmd_track)

    tr_sub.add_parser("list", help="列出投递").set_defaults(func=cmd_track)

    tu = tr_sub.add_parser("update", help="更新投递状态")
    tu.add_argument("id")
    tu.add_argument("status", choices=[s.value for s in ApplicationStatus])
    tu.add_argument("--feedback", default=None)
    tu.add_argument("--notes", default=None)
    tu.set_defaults(func=cmd_track)

    tr_sub.add_parser("funnel", help="投递漏斗统计").set_defaults(func=cmd_track)

    rp2 = sub.add_parser("replan", help="基于投递反馈修订机会矩阵")
    rp2.add_argument("--write", action="store_true", help="写入 opportunities.revised.yaml")
    rp2.set_defaults(func=cmd_replan)

    jd = sub.add_parser("jd-analyze", help="分析 JD 文件 vs 画像技能缺口")
    jd.add_argument("file", help="JD 文本文件路径")
    jd.set_defaults(func=cmd_jd_analyze)

    jb = sub.add_parser("job", help="感兴趣岗位库（收藏 JD）")
    jb_sub = jb.add_subparsers(dest="job_cmd", required=True)

    ja = jb_sub.add_parser("add", help="保存感兴趣岗位")
    ja.add_argument("company")
    ja.add_argument("role")
    ja.add_argument("--file", required=True, help="JD 全文文本文件")
    ja.add_argument("--location", default="")
    ja.add_argument("--source", default="招聘软件")
    ja.add_argument("--direction", default="", help="关联机会矩阵 direction")
    ja.add_argument("--notes", default="")
    ja.set_defaults(func=cmd_job)

    jb_sub.add_parser("list", help="列出收藏岗位").set_defaults(func=cmd_job)

    js = jb_sub.add_parser("show", help="查看岗位详情")
    js.add_argument("id")
    js.set_defaults(func=cmd_job)

    jan = jb_sub.add_parser("analyze", help="分析收藏岗位 vs 画像")
    jan.add_argument("id", nargs="?", default=None, help="省略则分析全部")
    jan.set_defaults(func=cmd_job)

    jr = jb_sub.add_parser("remove", help="删除收藏岗位")
    jr.add_argument("id")
    jr.set_defaults(func=cmd_job)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
