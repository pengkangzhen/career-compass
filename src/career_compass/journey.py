"""用户旅程 ↔ 引擎阶段 ↔ 架构层映射。

系统层：L0 构建画像 → L1 探索世界 → L2 做出决策 → L3 开始行动 → L4 持续追踪
用户层：认识自己 → 探索世界 → 做出决策 → 开始行动 → 持续追踪
引擎：  intake → scan → analyze → execute → track/replan
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .pipeline import MIN_SIGNALS_FOR_ANALYZE, Stage, detect_stage
from .schema import count_signals


class JourneyStep(str, Enum):
    know_self = "know_self"
    explore = "explore"
    decide = "decide"
    act = "act"
    track = "track"


JOURNEY_STEPS: tuple[dict[str, str], ...] = (
    {
        "id": JourneyStep.know_self.value,
        "title": "认识自己",
        "subtitle": "背景、技能、约束与价值观",
        "engine": "intake",
    },
    {
        "id": JourneyStep.explore.value,
        "title": "探索世界",
        "subtitle": "行业趋势、岗位与市场信号",
        "engine": "scan",
    },
    {
        "id": JourneyStep.decide.value,
        "title": "做出决策",
        "subtitle": "比较机会矩阵，选定方向",
        "engine": "analyze",
    },
    {
        "id": JourneyStep.act.value,
        "title": "开始行动",
        "subtitle": "（可选）简历与投递策略",
        "engine": "execute",
        "optional": True,
    },
    {
        "id": JourneyStep.track.value,
        "title": "持续追踪",
        "subtitle": "（可选）投递反馈与矩阵迭代",
        "engine": "track / replan",
        "optional": True,
    },
)

# 引擎 Stage → 主旅程步骤（plan 归入「做出决策」深化；done = 核心交付完成）
STAGE_TO_JOURNEY: dict[Stage, JourneyStep] = {
    Stage.intake: JourneyStep.know_self,
    Stage.scan: JourneyStep.explore,
    Stage.analyze: JourneyStep.decide,
    Stage.plan: JourneyStep.decide,
    Stage.done: JourneyStep.track,
}

CORE_COMPLETE_HINT = (
    "机会矩阵已就绪。可选：render-execution 准备投递材料；"
    "track / replan 记录进展并迭代方向"
)

NEXT_HINTS: dict[JourneyStep, str] = {
    JourneyStep.know_self: "在「对话」里聊聊你的背景、经历和硬约束",
    JourneyStep.explore: "查看「行业趋势」，或用 Agent 采集带来源的市场信号",
    JourneyStep.decide: "打开「机会矩阵」，比较几个方向后自行选择",
    JourneyStep.act: "（可选）运行 render-execution 生成行动手册，准备投递材料",
    JourneyStep.track: "若开始投递，用 track 记录进展；无回音时用 replan 修订矩阵",
}


@dataclass
class JourneyProgress:
    know_self_done: bool = False
    explore_done: bool = False
    decide_done: bool = False
    act_done: bool = False
    track_started: bool = False
    signal_count: int = 0
    has_applications: bool = False

    @property
    def core_done(self) -> bool:
        """L2 机会矩阵已渲染 = 北斗星核心交付完成。"""
        return self.decide_done


def assess_journey_progress(data_dir: Path) -> JourneyProgress:
    """根据 data/ 文件判断各旅程步骤完成情况。"""
    state = detect_stage(data_dir)
    signal_count = count_signals(data_dir / "signals")
    applications_path = data_dir / "applications.yaml"
    execution_pack = data_dir / "execution_pack.md"
    saved_jobs = data_dir / "saved_jobs.yaml"

    know_self_done = not state.validation_errors
    explore_done = (
        signal_count >= MIN_SIGNALS_FOR_ANALYZE
        or saved_jobs.is_file()
    )
    decide_done = state.has_opportunities_md
    act_done = execution_pack.is_file()
    has_applications = False
    if applications_path.is_file():
        try:
            from .schema import load_applications

            has_applications = bool(load_applications(applications_path).applications)
        except Exception:
            has_applications = applications_path.stat().st_size > 20

    return JourneyProgress(
        know_self_done=know_self_done,
        explore_done=explore_done,
        decide_done=decide_done,
        act_done=act_done,
        track_started=has_applications,
        signal_count=signal_count,
        has_applications=has_applications,
    )


def current_journey_step(progress: JourneyProgress) -> JourneyStep:
    if not progress.know_self_done:
        return JourneyStep.know_self
    if not progress.explore_done:
        return JourneyStep.explore
    if not progress.decide_done:
        return JourneyStep.decide
    # 核心交付完成；L3/L4 为可选延伸，默认停留在「持续追踪」
    return JourneyStep.track


@dataclass
class JourneyStatus:
    current: JourneyStep
    current_title: str
    steps: list[dict[str, object]] = field(default_factory=list)
    next_hint: str = ""
    engine_stage: str = ""
    progress: JourneyProgress = field(default_factory=JourneyProgress)

    def to_dict(self) -> dict:
        return {
            "current": self.current.value,
            "current_title": self.current_title,
            "steps": self.steps,
            "next_hint": self.next_hint,
            "engine_stage": self.engine_stage,
            "know_self_complete": self.progress.know_self_done,
            "core_complete": self.progress.core_done,
        }


def build_journey_status(data_dir: Path) -> JourneyStatus:
    pipeline = detect_stage(data_dir)
    progress = assess_journey_progress(data_dir)
    current = current_journey_step(progress)

    done_map = {
        JourneyStep.know_self: progress.know_self_done,
        JourneyStep.explore: progress.explore_done,
        JourneyStep.decide: progress.decide_done,
        JourneyStep.act: progress.act_done,
        JourneyStep.track: progress.track_started,
    }

    steps: list[dict[str, object]] = []
    for meta in JOURNEY_STEPS:
        step_id = JourneyStep(meta["id"])
        is_optional = meta.get("optional", False)
        steps.append(
            {
                "id": meta["id"],
                "title": meta["title"],
                "subtitle": meta["subtitle"],
                "engine": meta["engine"],
                "optional": is_optional,
                "done": done_map.get(step_id, False),
                "current": (not progress.core_done) and step_id == current,
            }
        )

    if progress.core_done:
        display_title = "已完成"
        display_hint = CORE_COMPLETE_HINT
    else:
        display_title = next(s["title"] for s in JOURNEY_STEPS if s["id"] == current.value)
        display_hint = NEXT_HINTS[current]

    return JourneyStatus(
        current=current,
        current_title=display_title,
        steps=steps,
        next_hint=display_hint,
        engine_stage=pipeline.stage.value,
        progress=progress,
    )
