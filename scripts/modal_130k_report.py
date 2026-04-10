from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from html import escape
from pathlib import Path
from statistics import mean


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULTS_ROOT = PROJECT_ROOT / "modal" / "tom-130k-modal-results"
INCUMBENT_ROOT = PROJECT_ROOT / "modal" / "tom-experiment-incumbent"
REPORTS_DIR = RESULTS_ROOT / "reports"

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
    metrics: dict[str, float]
    family_outcomes: dict[str, dict[str, int]]
    curve_stats: dict[str, float]


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_choice_family_outcomes(path: Path) -> dict[str, dict[str, int]]:
    analysis = _load_json(path)
    fam: dict[str, dict[str, int]] = defaultdict(lambda: {outcome: 0 for outcome in OUTCOMES})
    for scenario in analysis["scenario_summaries"]:
        fam[scenario["scenario_family"]][scenario["outcome"]] += 1
    return {family: dict(fam[family]) for family in FAMILIES}


def load_curve_stats(path: Path) -> dict[str, float]:
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    parsed = [{k: float(v) for k, v in row.items()} for row in rows]
    reward_ma = [row["reward_ma_10"] for row in parsed]
    reward = [row["reward_sum"] for row in parsed]
    entropy = [row["entropy"] for row in parsed]
    best_idx = max(range(len(parsed)), key=lambda idx: reward_ma[idx])
    return {
        "episodes": float(len(parsed)),
        "best_reward_ma10": reward_ma[best_idx],
        "best_reward_ma10_episode": parsed[best_idx]["episode"],
        "last_reward_ma10": reward_ma[-1],
        "last100_reward_ma10_mean": mean(reward_ma[-100:]),
        "last1000_reward_ma10_mean": mean(reward_ma[-1000:]),
        "last100_reward_mean": mean(reward[-100:]),
        "last1000_reward_mean": mean(reward[-1000:]),
        "entropy_first100_mean": mean(entropy[:100]),
        "entropy_last100_mean": mean(entropy[-100:]),
    }


def load_bundles() -> dict[str, RunBundle]:
    bundles: dict[str, RunBundle] = {}

    incumbent_seed7 = _load_json(INCUMBENT_ROOT / "auxhead-lite" / "seed7" / "candidate_metrics.json")
    incumbent_seed11 = _load_json(INCUMBENT_ROOT / "auxhead-lite" / "seed11" / "candidate_metrics.json")
    incumbent_choice7 = load_choice_family_outcomes(INCUMBENT_ROOT / "auxhead-lite" / "seed7" / "candidate_choice_analysis.json")
    incumbent_choice11 = load_choice_family_outcomes(INCUMBENT_ROOT / "seed11" / "candidate_choice_analysis.json")

    bundles["old_auxhead_seed7"] = RunBundle(
        label="old_auxhead_seed7",
        seed=7,
        metrics=incumbent_seed7["eval_metrics"],
        family_outcomes=incumbent_choice7,
        curve_stats={},
    )
    bundles["old_auxhead_seed11"] = RunBundle(
        label="old_auxhead_seed11",
        seed=11,
        metrics=incumbent_seed11["eval_metrics"],
        family_outcomes=incumbent_choice11,
        curve_stats={},
    )

    for seed in (7, 11):
        root = RESULTS_ROOT / f"seed{seed}" / "target-130000"
        summary = _load_json(root / "run_summary.json")
        bundles[f"seed{seed}_130k"] = RunBundle(
            label=f"seed{seed}_130k",
            seed=seed,
            metrics=summary["eval_metrics"],
            family_outcomes=load_choice_family_outcomes(next((root / "analysis").glob("choice-analysis-*.json"))),
            curve_stats=load_curve_stats(next((root / "curves").glob("curve-*.csv"))),
        )

    return bundles


def metric_delta_text(new: float, old: float, metric: str) -> str:
    delta = new - old
    if metric in HIGHER_IS_BETTER:
        better = delta >= 0
    else:
        better = delta <= 0
    sign = "+" if delta >= 0 else ""
    mark = "better" if better else "worse"
    return f"{sign}{delta:.4f} ({mark})"


def branch_mean_metrics(seed7: RunBundle, seed11: RunBundle) -> dict[str, float]:
    return {metric: mean([seed7.metrics[metric], seed11.metrics[metric]]) for metric in METRICS}


def verdicts() -> dict[str, str]:
    return {
        "old_auxhead_lite_incumbents": "Discard as current best; keep as archive baselines.",
        "seed7_130k": "Keep. Best single run in the branch.",
        "seed11_130k": "Keep. Supporting replicate with slightly rougher ambiguity handling.",
        "branch_130k": "Keep as the current best candidate branch. Strong enough to supersede the old 800-episode auxhead-lite line, but not yet a fully clean behavioral endpoint.",
    }


def svg_metric_bars(bundles: dict[str, RunBundle], path: Path) -> None:
    labels = ["old aux7", "old aux11", "seed7 130k", "seed11 130k"]
    keys = ["old_auxhead_seed7", "old_auxhead_seed11", "seed7_130k", "seed11_130k"]
    metric = "ToMCoordScore"
    values = [bundles[key].metrics[metric] for key in keys]
    width = 760
    height = 360
    margin = 60
    chart_h = 220
    chart_w = width - 2 * margin
    max_value = max(values) * 1.15
    bar_gap = 28
    bar_w = (chart_w - bar_gap * (len(values) - 1)) / len(values)
    colors = ["#8884d8", "#82ca9d", "#ff9f40", "#36cfc9"]
    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<style>text{font-family:Menlo,Consolas,monospace;fill:#e8edf2} .small{font-size:12px} .title{font-size:18px;font-weight:700}</style>",
        "<rect width='100%' height='100%' fill='#11161c' rx='18'/>",
        f"<text x='{margin}' y='34' class='title'>ToMCoordScore Comparison</text>",
    ]
    for idx, (label, value, color) in enumerate(zip(labels, values, colors)):
        x = margin + idx * (bar_w + bar_gap)
        bar_h = chart_h * (value / max_value)
        y = 290 - bar_h
        parts.append(f"<rect x='{x:.1f}' y='{y:.1f}' width='{bar_w:.1f}' height='{bar_h:.1f}' fill='{color}' rx='10'/>")
        parts.append(f"<text x='{x + bar_w / 2:.1f}' y='310' text-anchor='middle' class='small'>{escape(label)}</text>")
        parts.append(f"<text x='{x + bar_w / 2:.1f}' y='{y - 8:.1f}' text-anchor='middle' class='small'>{value:.3f}</text>")
    parts.append("</svg>")
    path.write_text("".join(parts), encoding="utf-8")


def svg_curve_overlay(path_seed7: Path, path_seed11: Path, out_path: Path) -> None:
    def load_points(path: Path) -> tuple[list[float], list[float]]:
        rows = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(path.open(encoding="utf-8"))]
        step = max(1, len(rows) // 600)
        sampled = rows[::step]
        return [row["episode"] for row in sampled], [row["reward_ma_10"] for row in sampled]

    x7, y7 = load_points(path_seed7)
    x11, y11 = load_points(path_seed11)
    width = 900
    height = 420
    margin = 60
    all_x = x7 + x11
    all_y = y7 + y11
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    if min_y == max_y:
        min_y -= 1
        max_y += 1

    def map_x(v: float) -> float:
        return margin + (v - min_x) / (max_x - min_x) * (width - 2 * margin)

    def map_y(v: float) -> float:
        return height - margin - (v - min_y) / (max_y - min_y) * (height - 2 * margin)

    def polyline(xs: list[float], ys: list[float]) -> str:
        return " ".join(f"{map_x(x):.1f},{map_y(y):.1f}" for x, y in zip(xs, ys))

    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<style>text{font-family:Menlo,Consolas,monospace;fill:#e8edf2} .small{font-size:12px} .title{font-size:18px;font-weight:700}</style>",
        "<rect width='100%' height='100%' fill='#11161c' rx='18'/>",
        f"<text x='{margin}' y='34' class='title'>Reward MA10 Overlay</text>",
        f"<line x1='{margin}' y1='{height-margin}' x2='{width-margin}' y2='{height-margin}' stroke='#51606f' stroke-width='1'/>",
        f"<line x1='{margin}' y1='{margin}' x2='{margin}' y2='{height-margin}' stroke='#51606f' stroke-width='1'/>",
        f"<polyline fill='none' stroke='#ff9f40' stroke-width='2.5' points='{polyline(x7, y7)}'/>",
        f"<polyline fill='none' stroke='#36cfc9' stroke-width='2.5' points='{polyline(x11, y11)}'/>",
        f"<text x='{width-220}' y='40' class='small'>seed7 130k</text>",
        f"<line x1='{width-310}' y1='36' x2='{width-230}' y2='36' stroke='#ff9f40' stroke-width='3'/>",
        f"<text x='{width-220}' y='62' class='small'>seed11 130k</text>",
        f"<line x1='{width-310}' y1='58' x2='{width-230}' y2='58' stroke='#36cfc9' stroke-width='3'/>",
        "</svg>",
    ]
    out_path.write_text("".join(parts), encoding="utf-8")


def svg_family_heatmap(seed7: RunBundle, seed11: RunBundle, out_path: Path) -> None:
    width = 980
    height = 420
    margin_left = 180
    top = 70
    cell_w = 90
    cell_h = 42
    color_map = {"success": "#2fbf71", "collision": "#ff6b6b", "deadlock": "#9b5de5", "timeout": "#f4a261"}
    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<style>text{font-family:Menlo,Consolas,monospace;fill:#e8edf2} .small{font-size:12px} .title{font-size:18px;font-weight:700}</style>",
        "<rect width='100%' height='100%' fill='#11161c' rx='18'/>",
        f"<text x='{margin_left}' y='34' class='title'>Family Outcome Grid</text>",
    ]
    headers = [f"s7 {o}" for o in OUTCOMES] + [f"s11 {o}" for o in OUTCOMES]
    for idx, header in enumerate(headers):
        x = margin_left + idx * cell_w + cell_w / 2
        parts.append(f"<text x='{x:.1f}' y='{top-14}' text-anchor='middle' class='small'>{escape(header)}</text>")
    for row_idx, family in enumerate(FAMILIES):
        y = top + row_idx * cell_h
        parts.append(f"<text x='{margin_left-14}' y='{y + 26}' text-anchor='end' class='small'>{escape(family)}</text>")
        values = [seed7.family_outcomes[family][o] for o in OUTCOMES] + [seed11.family_outcomes[family][o] for o in OUTCOMES]
        labels = OUTCOMES + OUTCOMES
        for col_idx, (value, label) in enumerate(zip(values, labels)):
            x = margin_left + col_idx * cell_w
            fill = color_map[label]
            opacity = 0.20 + 0.18 * value
            parts.append(
                f"<rect x='{x}' y='{y}' width='{cell_w-6}' height='{cell_h-6}' fill='{fill}' fill-opacity='{opacity:.2f}' rx='8'/>"
            )
            parts.append(
                f"<text x='{x + (cell_w-6)/2:.1f}' y='{y + 25}' text-anchor='middle' class='small'>{value}</text>"
            )
    parts.append("</svg>")
    out_path.write_text("".join(parts), encoding="utf-8")


def write_summary(bundles: dict[str, RunBundle], out_md: Path, out_json: Path) -> None:
    seed7_old = bundles["old_auxhead_seed7"]
    seed11_old = bundles["old_auxhead_seed11"]
    seed7_new = bundles["seed7_130k"]
    seed11_new = bundles["seed11_130k"]
    branch_mean = branch_mean_metrics(seed7_new, seed11_new)
    verdict_map = verdicts()

    payload = {
        "verdicts": verdict_map,
        "branch_mean_metrics": branch_mean,
        "seed7_vs_old_auxhead": {
            metric: {
                "new": seed7_new.metrics[metric],
                "old": seed7_old.metrics[metric],
                "delta": seed7_new.metrics[metric] - seed7_old.metrics[metric],
            }
            for metric in METRICS
        },
        "seed11_vs_old_auxhead": {
            metric: {
                "new": seed11_new.metrics[metric],
                "old": seed11_old.metrics[metric],
                "delta": seed11_new.metrics[metric] - seed11_old.metrics[metric],
            }
            for metric in METRICS
        },
        "seed7_curve_stats": seed7_new.curve_stats,
        "seed11_curve_stats": seed11_new.curve_stats,
        "seed7_family_outcomes": seed7_new.family_outcomes,
        "seed11_family_outcomes": seed11_new.family_outcomes,
    }
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# Modal 130k Verdict",
        "",
        f"- Old auxhead-lite incumbents: {verdict_map['old_auxhead_lite_incumbents']}",
        f"- Seed7 130k: {verdict_map['seed7_130k']}",
        f"- Seed11 130k: {verdict_map['seed11_130k']}",
        f"- Branch as a whole: {verdict_map['branch_130k']}",
        "",
        "## Branch Mean Metrics",
    ]
    for metric in METRICS:
        lines.append(f"- {metric}: {branch_mean[metric]:.4f}")
    lines.extend(
        [
            "",
            "## Seed7 130k vs Old Auxhead-Lite Seed7",
        ]
    )
    for metric in METRICS:
        lines.append(
            f"- {metric}: {seed7_new.metrics[metric]:.4f} vs {seed7_old.metrics[metric]:.4f} "
            f"({metric_delta_text(seed7_new.metrics[metric], seed7_old.metrics[metric], metric)})"
        )
    lines.extend(
        [
            "",
            "## Seed11 130k vs Old Auxhead-Lite Seed11",
        ]
    )
    for metric in METRICS:
        lines.append(
            f"- {metric}: {seed11_new.metrics[metric]:.4f} vs {seed11_old.metrics[metric]:.4f} "
            f"({metric_delta_text(seed11_new.metrics[metric], seed11_old.metrics[metric], metric)})"
        )
    lines.extend(
        [
            "",
            "## Charts",
            "- `metric_comparison.svg`",
            "- `curve_overlay.svg`",
            "- `family_outcome_grid.svg`",
        ]
    )
    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    bundles = load_bundles()
    write_summary(
        bundles,
        REPORTS_DIR / "modal_130k_verdict.md",
        REPORTS_DIR / "modal_130k_summary.json",
    )
    svg_metric_bars(bundles, REPORTS_DIR / "metric_comparison.svg")
    svg_curve_overlay(
        RESULTS_ROOT / "seed7" / "target-130000" / "curves" / "curve-tom-seed7-ep129200.csv",
        RESULTS_ROOT / "seed11" / "target-130000" / "curves" / "curve-tom-seed11-ep129200.csv",
        REPORTS_DIR / "curve_overlay.svg",
    )
    svg_family_heatmap(bundles["seed7_130k"], bundles["seed11_130k"], REPORTS_DIR / "family_outcome_grid.svg")
    print(f"wrote_reports={REPORTS_DIR}")


if __name__ == "__main__":
    main()
