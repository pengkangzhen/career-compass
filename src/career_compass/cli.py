"""Career-Compass CLI 入口。

命令:
  career-compass validate              校验画像/约束，列出完整性缺口
  career-compass brief                 输出供分析用的统一 brief（含目标行业池）
  career-compass scan-plan             基于画像生成检索查询
  career-compass new-signal DOMAIN TOPIC FINDING SOURCE [URL] [--confidence LEVEL]
  career-compass render-opportunities  把 opportunities.yaml 渲染成机会矩阵(核心交付物)
  career-compass render-strategy       渲染 strategy.md 骨架（选定方向后用）

数据目录默认 ./data，可用环境变量 CC_DATA 覆盖。
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

from .gather import add_signal, scan_plan
from .render import brief, render_opportunities, render_strategy
from .schema import ValidationError, load_constraints, load_profile

DATA = Path(os.getenv("CC_DATA", "data"))
PROFILE = DATA / "profile.yaml"
CONSTRAINTS = DATA / "constraints.yaml"
NARRATIVE = DATA / "narrative.md"
SIGNALS = DATA / "signals"
SECTORS = DATA / "sectors.yaml"
OPPORTUNITIES_YAML = DATA / "opportunities.yaml"
OPPORTUNITIES_MD = DATA / "opportunities.md"
STRATEGY = DATA / "strategy.md"


def cmd_validate(_args: argparse.Namespace) -> int:
    try:
        profile = load_profile(PROFILE)
    except FileNotFoundError:
        print(f"❌ 找不到 {PROFILE}。先执行: cp templates/profile.example.yaml {PROFILE}")
        return 1
    except ValidationError as e:
        print(f"❌ profile.yaml 校验失败:\n{e}")
        return 1

    gaps = profile.gaps()
    try:
        load_constraints(CONSTRAINTS)
    except FileNotFoundError:
        gaps.append("constraints.yaml 缺失")
    except ValidationError as e:
        print(f"❌ constraints.yaml 校验失败:\n{e}")
        return 1

    if gaps:
        print("⚠️  画像完整性缺口（回到 playbook 1-intake 补齐）:")
        for g in gaps:
            print(f"  - {g}")
        return 2

    print("✅ 画像与约束完整，可进入 playbook 3-analyze")
    return 0


def cmd_brief(_args: argparse.Namespace) -> int:
    print(brief(PROFILE, CONSTRAINTS, NARRATIVE, SIGNALS, SECTORS))
    return 0


def cmd_scan_plan(_args: argparse.Namespace) -> int:
    profile = load_profile(PROFILE)
    for q in scan_plan(profile):
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
    print(f"✅ 已追加到 {path}")
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


def main() -> int:
    parser = argparse.ArgumentParser(prog="career-compass", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("validate", help="校验画像/约束完整性").set_defaults(func=cmd_validate)
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

    sub.add_parser("render-opportunities", help="渲染机会矩阵(核心交付物)").set_defaults(func=cmd_render_opportunities)
    sub.add_parser("render-strategy", help="渲染 strategy.md 骨架").set_defaults(func=cmd_render_strategy)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
