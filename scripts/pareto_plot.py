"""一次性绘图脚本：从 data/opportunities.yaml 生成 Pareto 前沿可视化。

输出 4 张图到 /tmp/pareto_*.png：
  - parallel.png：parallel coordinates（6 维一图看完）
  - projection_fit_match.png：fit × match 散点（标注前沿/被支配）
  - projection_wind_risk.png：wind × trial_cost 散点
  - radar.png：雷达图（前沿方向之间互相比较）

为什么用这些图：
  - Parallel coordinates 是多目标优化里看 Pareto 前沿的标准做法——
    一条线 = 一个方向；线在所有轴上都偏高 = 不被支配。
  - 2D 投影帮助人眼理解"谁支配谁"。
  - 雷达图对 3-5 个前沿方向做直观形状对比。
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # 无 display 环境
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

# 注册 CJK 字体
for f in fm.findSystemFonts():
    name = f.lower()
    if "uming" in name or "ukai" in name or "kaitim" in name or "wenquan" in name:
        try:
            fm.fontManager.addfont(f)
        except Exception:
            pass

# 选一个能渲染中文的
_CJK_CANDIDATES = (
    "AR PL UMing CN",
    "AR PL UMing TW",
    "AR PL KaitiM GB",
    "AR PL SungtiL GB",
    "Noto Sans CJK SC",
    "WenQuanYi Zen Hei",
)
_cjk_font = next(
    (f for f in _CJK_CANDIDATES if any(f in ff.name for ff in fm.fontManager.ttflist)),
    None,
)
if _cjk_font:
    plt.rcParams["font.family"] = _cjk_font
plt.rcParams["axes.unicode_minus"] = False

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from career_compass.pareto import DIM_LABEL_ZH, pareto_from_matrix
from career_compass.schema import load_opportunities


# 品牌色板
COLOR_FRONT = "#d62728"        # 红：前沿（突出）
COLOR_DOMINATED = "#7f7f7f"    # 灰：被支配（淡化）
COLOR_HIGHLIGHT = "#1f77b4"    # 蓝：distinctive dims


def _short_label(label: str, max_len: int = 22) -> str:
    return label if len(label) <= max_len else label[: max_len - 1] + "…"


def plot_parallel(report, out_path: Path) -> None:
    """Parallel coordinates：每条线 = 一个方向；6 个维度作为竖轴。"""
    dims = report.dimensions
    labels = [DIM_LABEL_ZH[d] for d in dims]
    n_dims = len(dims)
    x = list(range(n_dims))

    fig, ax = plt.subplots(figsize=(10, 6.5))

    # 先画被支配（灰色，淡），再画前沿（红色，粗）
    for entry in report.dominated:
        ys = [entry.vector[d] for d in dims]
        ax.plot(x, ys, color=COLOR_DOMINATED, alpha=0.35, linewidth=1.0, marker="o", markersize=3)
    for entry in report.front:
        ys = [entry.vector[d] for d in dims]
        ax.plot(
            x, ys, color=COLOR_FRONT, alpha=0.85, linewidth=2.2,
            marker="o", markersize=6, label=_short_label(entry.label),
        )

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylabel("维度得分（0-1，越高越好）", fontsize=11)
    ax.set_ylim(-0.05, 1.08)
    ax.set_title(
        f"Pareto 前沿 · 红色 = {len(report.front)} 个非支配方向，灰色 = {len(report.dominated)} 个被支配",
        fontsize=12,
    )
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(
        loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize=8.5,
        title="前沿方向", title_fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def plot_projection(report, dim_x: str, dim_y: str, out_path: Path) -> None:
    """2D 散点：两维投影。前沿用红圆圈+标注，被支配用灰点。"""
    fig, ax = plt.subplots(figsize=(8.5, 6.5))

    xs_d, ys_d = [], []
    for entry in report.dominated:
        xs_d.append(entry.vector[dim_x])
        ys_d.append(entry.vector[dim_y])
    ax.scatter(xs_d, ys_d, c=COLOR_DOMINATED, s=35, alpha=0.45, label=f"被支配 ({len(report.dominated)})", zorder=2)

    xs_f, ys_f = [], []
    for entry in report.front:
        xs_f.append(entry.vector[dim_x])
        ys_f.append(entry.vector[dim_y])
    ax.scatter(
        xs_f, ys_f, c=COLOR_FRONT, s=140, alpha=0.85,
        edgecolors="black", linewidths=1.2, label=f"前沿 ({len(report.front)})", zorder=3,
    )

    # 标注前沿方向
    for entry in report.front:
        ax.annotate(
            _short_label(entry.label, 18),
            xy=(entry.vector[dim_x], entry.vector[dim_y]),
            xytext=(8, 6), textcoords="offset points",
            fontsize=8.5, color=COLOR_FRONT,
        )

    # 画"理想点"参考线
    ax.axvline(1.0, color="green", linestyle="--", alpha=0.3, linewidth=0.8)
    ax.axhline(1.0, color="green", linestyle="--", alpha=0.3, linewidth=0.8)

    ax.set_xlabel(f"{DIM_LABEL_ZH[dim_x]}（越高越好）", fontsize=11)
    ax.set_ylabel(f"{DIM_LABEL_ZH[dim_y]}（越高越好）", fontsize=11)
    ax.set_xlim(-0.05, 1.1)
    ax.set_ylim(-0.05, 1.1)
    ax.set_title(f"{DIM_LABEL_ZH[dim_x]} × {DIM_LABEL_ZH[dim_y]} 投影", fontsize=12)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="lower right", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def plot_radar(report, out_path: Path, max_legends: int = 5) -> None:
    """雷达图：最多画 max_legends 个前沿方向（多了会糊）。"""
    front = report.front[:max_legends]
    if not front:
        return
    dims = report.dimensions
    labels = [DIM_LABEL_ZH[d] for d in dims]
    n = len(dims)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles += angles[:1]  # 闭合

    fig, ax = plt.subplots(figsize=(8.5, 8.5), subplot_kw=dict(polar=True))
    colors = plt.cm.tab10(np.linspace(0, 1, len(front)))

    for idx, entry in enumerate(front):
        values = [entry.vector[d] for d in dims]
        values += values[:1]
        ax.plot(angles, values, color=colors[idx], linewidth=2.0, label=_short_label(entry.label, 20))
        ax.fill(angles, values, color=colors[idx], alpha=0.12)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=11)
    ax.set_ylim(0, 1.05)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.5", "0.75", "1.0"], fontsize=8, color="gray")
    ax.set_title(f"前沿方向形状对比（{len(front)} 个）", fontsize=12, pad=20)
    ax.grid(True, alpha=0.4)
    ax.legend(
        loc="upper right", bbox_to_anchor=(1.35, 1.05), fontsize=8.5,
        title="方向", title_fontsize=9,
    )
    fig.tight_layout()
    fig.savefig(out_path, dpi=140, bbox_inches="tight")
    plt.close(fig)


def main(opportunities_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    matrix = load_opportunities(opportunities_path)
    report = pareto_from_matrix(matrix)

    print(f"前沿 {len(report.front)} / 总 {report.size}")
    print(f"被支配 {len(report.dominated)}")

    plot_parallel(report, out_dir / "pareto_parallel.png")
    print(f"✅ {out_dir / 'pareto_parallel.png'}")

    plot_projection(report, "fit", "match", out_dir / "pareto_proj_fit_match.png")
    print(f"✅ {out_dir / 'pareto_proj_fit_match.png'}")

    plot_projection(report, "wind", "trial_cost", out_dir / "pareto_proj_wind_risk.png")
    print(f"✅ {out_dir / 'pareto_proj_wind_risk.png'}")

    plot_radar(report, out_dir / "pareto_radar.png")
    print(f"✅ {out_dir / 'pareto_radar.png'}")


if __name__ == "__main__":
    opp_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/opportunities.yaml")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("/tmp")
    main(opp_path, out)
