from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from html import escape
from pathlib import Path
from statistics import mean


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INCUMBENT_ROOT = PROJECT_ROOT / "modal" / "tom-experiment-incumbent"
ROOT_130 = PROJECT_ROOT / "modal" / "tom-130k-modal-results"
ROOT_140 = PROJECT_ROOT / "modal" / "tom-140k-modal-results"
REPORTS_DIR = ROOT_140 / "reports"

METRICS = [
    "ToMCoordScore",
    "SuccessRate",
    "DeadlockRate",
    "CollisionRate",
    "IntentionPredictionF1",
    "StrategySwitchAccuracy",
    "AmbiguityEfficiency",
    "CoordinationEfficiency",
    "AverageDelay",
]

HIGHER_IS_BETTER = {
    "ToMCoordScore",
    "SuccessRate",
    "IntentionPredictionF1",
    "StrategySwitchAccuracy",
    "AmbiguityEfficiency",
    "CoordinationEfficiency",
}

FAMILIES = [
    "ambiguous_commit",
    "false_friend",
    "late_disambiguation",
    "no_progress_switch",
    "assert_or_yield",
]
OUTCOMES = ["success", "collision", "deadlock", "timeout"]


@dataclass
class RunBundle:
    label: str
    seed: int
    train_tag: str
    metrics: dict[str, float]
    family_outcomes: dict[str, dict[str, int]]
    curve_stats: dict[str, float]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def family_outcomes(path: Path) -> dict[str, dict[str, int]]:
    data = _load_json(path)
    fam = defaultdict(lambda: {outcome: 0 for outcome in OUTCOMES})
    for scenario in data["scenario_summaries"]:
        fam[scenario["scenario_family"]][scenario["outcome"]] += 1
    return {family: dict(fam[family]) for family in FAMILIES}


def curve_stats(path: Path) -> dict[str, float]:
    rows = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(path.open(encoding="utf-8"))]
    reward_ma = [row["reward_ma_10"] for row in rows]
    reward = [row["reward_sum"] for row in rows]
    entropy = [row["entropy"] for row in rows]
    best_idx = max(range(len(rows)), key=lambda idx: reward_ma[idx])
    return {
        "curve_file": path.name,
        "episodes": float(len(rows)),
        "best_reward_ma10": reward_ma[best_idx],
        "best_reward_ma10_episode": rows[best_idx]["episode"],
        "last_reward_ma10": reward_ma[-1],
        "last100_reward_ma10_mean": mean(reward_ma[-100:]),
        "last1000_reward_ma10_mean": mean(reward_ma[-1000:]),
        "last100_reward_mean": mean(reward[-100:]),
        "last1000_reward_mean": mean(reward[-1000:]),
        "entropy_last100_mean": mean(entropy[-100:]),
    }


def load_bundles() -> dict[str, RunBundle]:
    bundles: dict[str, RunBundle] = {}

    old7 = _load_json(INCUMBENT_ROOT / "auxhead-lite" / "seed7" / "candidate_metrics.json")
    old11 = _load_json(INCUMBENT_ROOT / "auxhead-lite" / "seed11" / "candidate_metrics.json")
    bundles["old_auxhead_seed7"] = RunBundle(
        label="old_auxhead_seed7",
        seed=7,
        train_tag="800",
        metrics=old7["eval_metrics"],
        family_outcomes=family_outcomes(INCUMBENT_ROOT / "auxhead-lite" / "seed7" / "candidate_choice_analysis.json"),
        curve_stats={},
    )
    bundles["old_auxhead_seed11"] = RunBundle(
        label="old_auxhead_seed11",
        seed=11,
        train_tag="800",
        metrics=old11["eval_metrics"],
        family_outcomes=family_outcomes(INCUMBENT_ROOT / "auxhead-lite" / "seed11" / "candidate_choice_analysis.json"),
        curve_stats={},
    )

    for target, root in [("130k", ROOT_130), ("140k", ROOT_140)]:
        for seed in (7, 11):
            seed_root = root / f"seed{seed}" / f"target-{target[:-1]}000"
            summary = _load_json(seed_root / "run_summary.json")
            bundles[f"seed{seed}_{target}"] = RunBundle(
                label=f"seed{seed}_{target}",
                seed=seed,
                train_tag=target,
                metrics=summary["eval_metrics"],
                family_outcomes=family_outcomes(next((seed_root / "analysis").glob("choice-analysis-*.json"))),
                curve_stats=curve_stats(next((seed_root / "curves").glob("curve-*.csv"))),
            )

    return bundles


def metric_delta_text(new: float, old: float, metric: str) -> str:
    delta = new - old
    better = delta >= 0 if metric in HIGHER_IS_BETTER else delta <= 0
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.4f} ({'better' if better else 'worse'})"


def branch_mean(seed7: RunBundle, seed11: RunBundle) -> dict[str, float]:
    return {metric: mean([seed7.metrics[metric], seed11.metrics[metric]]) for metric in METRICS}


def verdicts() -> dict[str, str]:
    return {
        "old_auxhead_lite_incumbents": "Discard as current best; keep as archive baselines.",
        "seed7_130k": "Keep. Strong and robust.",
        "seed11_130k": "Keep. Supporting replicate and safer cross-seed stopping point.",
        "seed7_140k": "Keep. Current best single run.",
        "seed11_140k": "Discard as branch default; useful negative datapoint showing overtraining risk.",
        "branch_overall": "Keep the long-run branch, but prefer 130k as the safer cross-seed recommendation and seed7 140k as the best individual checkpoint.",
    }


def svg_metric_lines(bundles: dict[str, RunBundle], out_path: Path) -> None:
    labels = ["old7", "130k-7", "140k-7", "old11", "130k-11", "140k-11"]
    keys = ["old_auxhead_seed7", "seed7_130k", "seed7_140k", "old_auxhead_seed11", "seed11_130k", "seed11_140k"]
    values = [bundles[key].metrics["ToMCoordScore"] for key in keys]
    width, height, margin = 900, 360, 70
    min_y, max_y = min(values) * 0.9, max(values) * 1.1

    def x(idx: int) -> float:
        return margin + idx * (width - 2 * margin) / (len(values) - 1)

    def y(val: float) -> float:
        return height - margin - (val - min_y) / (max_y - min_y) * (height - 2 * margin)

    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(values))
    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<style>text{font-family:Menlo,Consolas,monospace;fill:#e8edf2}.small{font-size:12px}.title{font-size:18px;font-weight:700}</style>",
        "<rect width='100%' height='100%' fill='#11161c' rx='18'/>",
        f"<text x='{margin}' y='34' class='title'>ToMCoordScore Across Targets</text>",
        f"<line x1='{margin}' y1='{height-margin}' x2='{width-margin}' y2='{height-margin}' stroke='#51606f'/>",
        f"<line x1='{margin}' y1='{margin}' x2='{margin}' y2='{height-margin}' stroke='#51606f'/>",
        f"<polyline fill='none' stroke='#36cfc9' stroke-width='3' points='{pts}'/>",
    ]
    for i, (label, value) in enumerate(zip(labels, values)):
        parts.append(f"<circle cx='{x(i):.1f}' cy='{y(value):.1f}' r='5' fill='#ff9f40'/>")
        parts.append(f"<text x='{x(i):.1f}' y='{height-margin+22}' text-anchor='middle' class='small'>{label}</text>")
        parts.append(f"<text x='{x(i):.1f}' y='{y(value)-10:.1f}' text-anchor='middle' class='small'>{value:.3f}</text>")
    parts.append("</svg>")
    out_path.write_text("".join(parts), encoding="utf-8")


def svg_seed_curves(bundles: dict[str, RunBundle], out_path: Path) -> None:
    width, height, margin = 960, 420, 70
    series = [
        ("seed7 130k", ROOT_130 / "seed7" / "target-130000" / "curves" / "curve-tom-seed7-ep129200.csv", "#ff9f40"),
        ("seed7 140k", ROOT_140 / "seed7" / "target-140000" / "curves" / "curve-tom-seed7-ep140000.csv", "#36cfc9"),
        ("seed11 130k", ROOT_130 / "seed11" / "target-130000" / "curves" / "curve-tom-seed11-ep129200.csv", "#f7768e"),
        ("seed11 140k", ROOT_140 / "seed11" / "target-140000" / "curves" / "curve-tom-seed11-ep140000.csv", "#9d4edd"),
    ]

    loaded = []
    for label, path, color in series:
        rows = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(path.open(encoding="utf-8"))]
        step = max(1, len(rows) // 550)
        sampled = rows[::step]
        loaded.append((label, sampled, color))

    all_x = [row["episode"] for _, rows, _ in loaded for row in rows]
    all_y = [row["reward_ma_10"] for _, rows, _ in loaded for row in rows]
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)

    def map_x(v: float) -> float:
        return margin + (v - min_x) / (max_x - min_x) * (width - 2 * margin)

    def map_y(v: float) -> float:
        return height - margin - (v - min_y) / (max_y - min_y) * (height - 2 * margin)

    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<style>text{font-family:Menlo,Consolas,monospace;fill:#e8edf2}.small{font-size:12px}.title{font-size:18px;font-weight:700}</style>",
        "<rect width='100%' height='100%' fill='#11161c' rx='18'/>",
        f"<text x='{margin}' y='34' class='title'>Reward MA10 Overlay: 130k vs 140k</text>",
        f"<line x1='{margin}' y1='{height-margin}' x2='{width-margin}' y2='{height-margin}' stroke='#51606f'/>",
        f"<line x1='{margin}' y1='{margin}' x2='{margin}' y2='{height-margin}' stroke='#51606f'/>",
    ]
    legend_y = 46
    legend_x = width - 290
    for idx, (label, rows, color) in enumerate(loaded):
        pts = " ".join(f"{map_x(r['episode']):.1f},{map_y(r['reward_ma_10']):.1f}" for r in rows)
        parts.append(f"<polyline fill='none' stroke='{color}' stroke-width='2.4' points='{pts}'/>")
        y = legend_y + idx * 20
        parts.append(f"<line x1='{legend_x}' y1='{y}' x2='{legend_x+55}' y2='{y}' stroke='{color}' stroke-width='3'/>")
        parts.append(f"<text x='{legend_x+64}' y='{y+4}' class='small'>{escape(label)}</text>")
    parts.append("</svg>")
    out_path.write_text("".join(parts), encoding="utf-8")


def svg_family_bars(bundles: dict[str, RunBundle], out_path: Path) -> None:
    width, height = 1100, 460
    margin_left, top = 170, 80
    cell_w, cell_h = 110, 44
    headers = ["s7 130k success", "s7 140k success", "s11 130k success", "s11 140k success"]
    keys = ["seed7_130k", "seed7_140k", "seed11_130k", "seed11_140k"]
    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<style>text{font-family:Menlo,Consolas,monospace;fill:#e8edf2}.small{font-size:12px}.title{font-size:18px;font-weight:700}</style>",
        "<rect width='100%' height='100%' fill='#11161c' rx='18'/>",
        f"<text x='{margin_left}' y='34' class='title'>Family Success Counts</text>",
    ]
    for idx, header in enumerate(headers):
        x = margin_left + idx * cell_w + cell_w / 2
        parts.append(f"<text x='{x:.1f}' y='{top-16}' text-anchor='middle' class='small'>{escape(header)}</text>")
    for row_idx, family in enumerate(FAMILIES):
        y = top + row_idx * cell_h
        parts.append(f"<text x='{margin_left-14}' y='{y+26}' text-anchor='end' class='small'>{escape(family)}</text>")
        for col_idx, key in enumerate(keys):
            success = bundles[key].family_outcomes[family]["success"]
            x = margin_left + col_idx * cell_w
            fill = "#2fbf71"
            opacity = 0.18 + 0.20 * success
            parts.append(f"<rect x='{x}' y='{y}' width='{cell_w-8}' height='{cell_h-8}' fill='{fill}' fill-opacity='{opacity:.2f}' rx='8'/>")
            parts.append(f"<text x='{x+(cell_w-8)/2:.1f}' y='{y+25}' text-anchor='middle' class='small'>{success}</text>")
    parts.append("</svg>")
    out_path.write_text("".join(parts), encoding="utf-8")


def write_report(bundles: dict[str, RunBundle], md_path: Path, json_path: Path) -> None:
    branch_130 = branch_mean(bundles["seed7_130k"], bundles["seed11_130k"])
    branch_140 = branch_mean(bundles["seed7_140k"], bundles["seed11_140k"])
    verdict_map = verdicts()
    payload = {
        "verdicts": verdict_map,
        "branch_mean_130k": branch_130,
        "branch_mean_140k": branch_140,
        "seed7_130k_metrics": bundles["seed7_130k"].metrics,
        "seed7_140k_metrics": bundles["seed7_140k"].metrics,
        "seed11_130k_metrics": bundles["seed11_130k"].metrics,
        "seed11_140k_metrics": bundles["seed11_140k"].metrics,
        "seed7_130k_family_outcomes": bundles["seed7_130k"].family_outcomes,
        "seed7_140k_family_outcomes": bundles["seed7_140k"].family_outcomes,
        "seed11_130k_family_outcomes": bundles["seed11_130k"].family_outcomes,
        "seed11_140k_family_outcomes": bundles["seed11_140k"].family_outcomes,
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# Modal Long-Run Verdict",
        "",
        f"- Old auxhead-lite incumbents: {verdict_map['old_auxhead_lite_incumbents']}",
        f"- Seed7 130k: {verdict_map['seed7_130k']}",
        f"- Seed11 130k: {verdict_map['seed11_130k']}",
        f"- Seed7 140k: {verdict_map['seed7_140k']}",
        f"- Seed11 140k: {verdict_map['seed11_140k']}",
        f"- Branch overall: {verdict_map['branch_overall']}",
        "",
        "## Branch Mean Metrics",
        "### 130k",
    ]
    lines.extend(f"- {metric}: {branch_130[metric]:.4f}" for metric in METRICS)
    lines.extend(["", "### 140k"])
    lines.extend(f"- {metric}: {branch_140[metric]:.4f}" for metric in METRICS)
    lines.extend(
        [
            "",
            "## Key Deltas",
            f"- Seed7 ToMCoordScore: 130k {bundles['seed7_130k'].metrics['ToMCoordScore']:.4f} -> 140k {bundles['seed7_140k'].metrics['ToMCoordScore']:.4f} "
            f"({metric_delta_text(bundles['seed7_140k'].metrics['ToMCoordScore'], bundles['seed7_130k'].metrics['ToMCoordScore'], 'ToMCoordScore')})",
            f"- Seed11 ToMCoordScore: 130k {bundles['seed11_130k'].metrics['ToMCoordScore']:.4f} -> 140k {bundles['seed11_140k'].metrics['ToMCoordScore']:.4f} "
            f"({metric_delta_text(bundles['seed11_140k'].metrics['ToMCoordScore'], bundles['seed11_130k'].metrics['ToMCoordScore'], 'ToMCoordScore')})",
            "",
            "## Charts",
            "- `longrun_metric_lines.svg`",
            "- `longrun_curve_overlay.svg`",
            "- `longrun_family_success.svg`",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    bundles = load_bundles()
    write_report(
        bundles,
        REPORTS_DIR / "modal_longrun_verdict.md",
        REPORTS_DIR / "modal_longrun_summary.json",
    )
    svg_metric_lines(bundles, REPORTS_DIR / "longrun_metric_lines.svg")
    svg_seed_curves(bundles, REPORTS_DIR / "longrun_curve_overlay.svg")
    svg_family_bars(bundles, REPORTS_DIR / "longrun_family_success.svg")
    print(f"wrote_reports={REPORTS_DIR}")


if __name__ == "__main__":
    main()
