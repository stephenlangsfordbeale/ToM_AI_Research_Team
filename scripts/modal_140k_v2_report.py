from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from html import escape
from pathlib import Path
from statistics import mean


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ROOT_OLD_140 = PROJECT_ROOT / "modal" / "tom-140k-modal-results"
ROOT_NEW_140 = PROJECT_ROOT / "modal" / "tom-140k-modal-results-v2"
REPORTS_DIR = ROOT_NEW_140 / "reports"

LOCAL_V2_ROOT = {
    7: PROJECT_ROOT / "logs" / "local-run-v2-modal-seed7" / "candidate_metrics",
    11: PROJECT_ROOT / "logs" / "local-run-v2-modal-seed11" / "candidate_metrics",
}

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


def _family_outcomes_from_analysis(path: Path) -> dict[str, dict[str, int]]:
    data = _load_json(path)
    fam = defaultdict(lambda: {outcome: 0 for outcome in OUTCOMES})
    for row in data["scenario_summaries"]:
        fam[row["scenario_family"]][row["outcome"]] += 1
    return {family: dict(fam[family]) for family in FAMILIES}


def _curve_stats(path: Path) -> dict[str, float]:
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


def _new_140_bundle(seed: int) -> RunBundle:
    root = ROOT_NEW_140 / f"seed{seed}" / "target-140000"
    summary = _load_json(root / "run_summary.json")
    analysis_path = next((root / "analysis").glob("choice-analysis-*.json"))
    curve_path = next((root / "curves").glob("curve-*.csv"))
    return RunBundle(
        label=f"seed{seed}_new140",
        seed=seed,
        train_tag="new140",
        metrics=summary["eval_metrics"],
        family_outcomes=_family_outcomes_from_analysis(analysis_path),
        curve_stats=_curve_stats(curve_path),
    )


def _local_v2_bundle(seed: int) -> RunBundle:
    root = LOCAL_V2_ROOT[seed]
    metrics = _load_json(root / "metrics.json")["eval_metrics"]
    analysis_path = root / "choice_analysis.json"
    curve_path = root / "learning_curve.csv"
    return RunBundle(
        label=f"seed{seed}_local800",
        seed=seed,
        train_tag="local800",
        metrics=metrics,
        family_outcomes=_family_outcomes_from_analysis(analysis_path),
        curve_stats=_curve_stats(curve_path),
    )


def _old_140_bundle(seed: int, old_summary: dict) -> RunBundle:
    key_metrics = f"seed{seed}_140k_metrics"
    key_family = f"seed{seed}_140k_family_outcomes"
    curve_path = ROOT_OLD_140 / f"seed{seed}" / "target-140000" / "curves" / f"curve-tom-seed{seed}-ep140000.csv"
    return RunBundle(
        label=f"seed{seed}_old140",
        seed=seed,
        train_tag="old140",
        metrics=old_summary[key_metrics],
        family_outcomes=old_summary[key_family],
        curve_stats=_curve_stats(curve_path),
    )


def load_bundles() -> tuple[dict[str, RunBundle], dict]:
    old_summary = _load_json(ROOT_OLD_140 / "reports" / "modal_longrun_summary.json")
    bundles: dict[str, RunBundle] = {}
    for seed in (7, 11):
        bundles[f"seed{seed}_local800"] = _local_v2_bundle(seed)
        bundles[f"seed{seed}_old140"] = _old_140_bundle(seed, old_summary)
        bundles[f"seed{seed}_new140"] = _new_140_bundle(seed)
    return bundles, old_summary


def branch_mean(*bundles: RunBundle) -> dict[str, float]:
    return {metric: mean(bundle.metrics[metric] for bundle in bundles) for metric in METRICS}


def metric_delta_text(new: float, old: float, metric: str) -> str:
    delta = new - old
    better = delta >= 0 if metric in HIGHER_IS_BETTER else delta <= 0
    sign = "+" if delta >= 0 else ""
    return f"{sign}{delta:.4f} ({'better' if better else 'worse'})"


def verdicts() -> dict[str, str]:
    return {
        "new_v2_branch": "Keep as the current best 140k branch. It materially outperforms the old 140k line on score and especially rescues seed11.",
        "seed7_new140": "Keep. Modest score gain over the old 140k seed7 run, with better overall success but still some ambiguity-family roughness.",
        "seed11_new140": "Keep strongly. Major improvement over the old 140k seed11 run and the best individual checkpoint in this comparison.",
        "vs_local800": "Treat the new 140k branch as a long-run refinement, not a pure dominance result. Score, belief quality, and switch accuracy improve, but some families trade away short-run sharpness for slower, more deliberate behavior.",
        "remaining_risk": "assert_or_yield is still the weakest family. The branch is better overall, but that family remains the clearest unfinished behavior gap.",
    }


def svg_tom_score_lines(bundles: dict[str, RunBundle], out_path: Path) -> None:
    width, height, margin = 920, 380, 70
    checkpoints = ["local800", "old140", "new140"]
    series = {
        "seed7": [bundles["seed7_local800"].metrics["ToMCoordScore"], bundles["seed7_old140"].metrics["ToMCoordScore"], bundles["seed7_new140"].metrics["ToMCoordScore"]],
        "seed11": [bundles["seed11_local800"].metrics["ToMCoordScore"], bundles["seed11_old140"].metrics["ToMCoordScore"], bundles["seed11_new140"].metrics["ToMCoordScore"]],
        "branch_mean": [
            mean([bundles["seed7_local800"].metrics["ToMCoordScore"], bundles["seed11_local800"].metrics["ToMCoordScore"]]),
            mean([bundles["seed7_old140"].metrics["ToMCoordScore"], bundles["seed11_old140"].metrics["ToMCoordScore"]]),
            mean([bundles["seed7_new140"].metrics["ToMCoordScore"], bundles["seed11_new140"].metrics["ToMCoordScore"]]),
        ],
    }
    colors = {"seed7": "#36cfc9", "seed11": "#ff9f40", "branch_mean": "#f7768e"}
    all_values = [value for values in series.values() for value in values]
    min_y = min(all_values) * 0.88
    max_y = max(all_values) * 1.08

    def x(idx: int) -> float:
        return margin + idx * (width - 2 * margin) / (len(checkpoints) - 1)

    def y(value: float) -> float:
        return height - margin - (value - min_y) / (max_y - min_y) * (height - 2 * margin)

    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<style>text{font-family:Menlo,Consolas,monospace;fill:#e8edf2}.small{font-size:12px}.title{font-size:18px;font-weight:700}</style>",
        "<rect width='100%' height='100%' fill='#11161c' rx='18'/>",
        f"<text x='{margin}' y='34' class='title'>ToMCoordScore: Local 800 vs Old 140k vs New V2 140k</text>",
        f"<line x1='{margin}' y1='{height-margin}' x2='{width-margin}' y2='{height-margin}' stroke='#51606f'/>",
        f"<line x1='{margin}' y1='{margin}' x2='{margin}' y2='{height-margin}' stroke='#51606f'/>",
    ]

    legend_x = width - 250
    legend_y = 52
    for idx, checkpoint in enumerate(checkpoints):
        parts.append(f"<text x='{x(idx):.1f}' y='{height - margin + 24}' text-anchor='middle' class='small'>{escape(checkpoint)}</text>")

    for row_idx, (label, values) in enumerate(series.items()):
        pts = " ".join(f"{x(idx):.1f},{y(value):.1f}" for idx, value in enumerate(values))
        color = colors[label]
        parts.append(f"<polyline fill='none' stroke='{color}' stroke-width='3' points='{pts}'/>")
        for idx, value in enumerate(values):
            parts.append(f"<circle cx='{x(idx):.1f}' cy='{y(value):.1f}' r='5' fill='{color}'/>")
            parts.append(f"<text x='{x(idx):.1f}' y='{y(value)-10:.1f}' text-anchor='middle' class='small'>{value:.3f}</text>")
        y_legend = legend_y + row_idx * 20
        parts.append(f"<line x1='{legend_x}' y1='{y_legend}' x2='{legend_x+48}' y2='{y_legend}' stroke='{color}' stroke-width='3'/>")
        parts.append(f"<text x='{legend_x+58}' y='{y_legend+4}' class='small'>{escape(label)}</text>")

    parts.append("</svg>")
    out_path.write_text("".join(parts), encoding="utf-8")


def svg_new_curve_overlay(bundles: dict[str, RunBundle], out_path: Path) -> None:
    width, height, margin = 940, 420, 70
    series = [
        ("seed7 new140", ROOT_NEW_140 / "seed7" / "target-140000" / "curves" / "curve-tom-seed7-ep140000.csv", "#36cfc9"),
        ("seed11 new140", ROOT_NEW_140 / "seed11" / "target-140000" / "curves" / "curve-tom-seed11-ep140000.csv", "#ff9f40"),
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

    def map_x(value: float) -> float:
        return margin + (value - min_x) / (max_x - min_x) * (width - 2 * margin)

    def map_y(value: float) -> float:
        return height - margin - (value - min_y) / (max_y - min_y) * (height - 2 * margin)

    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<style>text{font-family:Menlo,Consolas,monospace;fill:#e8edf2}.small{font-size:12px}.title{font-size:18px;font-weight:700}</style>",
        "<rect width='100%' height='100%' fill='#11161c' rx='18'/>",
        f"<text x='{margin}' y='34' class='title'>New V2 140k Reward MA10 Overlay</text>",
        f"<line x1='{margin}' y1='{height-margin}' x2='{width-margin}' y2='{height-margin}' stroke='#51606f'/>",
        f"<line x1='{margin}' y1='{margin}' x2='{margin}' y2='{height-margin}' stroke='#51606f'/>",
    ]
    legend_x = width - 230
    legend_y = 46
    for idx, (label, rows, color) in enumerate(loaded):
        pts = " ".join(f"{map_x(row['episode']):.1f},{map_y(row['reward_ma_10']):.1f}" for row in rows)
        parts.append(f"<polyline fill='none' stroke='{color}' stroke-width='2.5' points='{pts}'/>")
        y_legend = legend_y + idx * 20
        parts.append(f"<line x1='{legend_x}' y1='{y_legend}' x2='{legend_x+52}' y2='{y_legend}' stroke='{color}' stroke-width='3'/>")
        parts.append(f"<text x='{legend_x+62}' y='{y_legend+4}' class='small'>{escape(label)}</text>")
    parts.append("</svg>")
    out_path.write_text("".join(parts), encoding="utf-8")


def svg_family_success(bundles: dict[str, RunBundle], out_path: Path) -> None:
    width, height = 1180, 470
    margin_left, top = 210, 80
    cell_w, cell_h = 120, 44
    headers = [
        "s7 local800",
        "s7 new140",
        "s11 local800",
        "s11 new140",
    ]
    keys = ["seed7_local800", "seed7_new140", "seed11_local800", "seed11_new140"]

    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>",
        "<style>text{font-family:Menlo,Consolas,monospace;fill:#e8edf2}.small{font-size:12px}.title{font-size:18px;font-weight:700}</style>",
        "<rect width='100%' height='100%' fill='#11161c' rx='18'/>",
        f"<text x='{margin_left}' y='34' class='title'>Family Success Counts: Local 800 vs New V2 140k</text>",
    ]
    for idx, header in enumerate(headers):
        x = margin_left + idx * cell_w + cell_w / 2
        parts.append(f"<text x='{x:.1f}' y='{top-16}' text-anchor='middle' class='small'>{escape(header)}</text>")

    for row_idx, family in enumerate(FAMILIES):
        y = top + row_idx * cell_h
        parts.append(f"<text x='{margin_left-14}' y='{y+26}' text-anchor='end' class='small'>{escape(family)}</text>")
        for col_idx, key in enumerate(keys):
            value = bundles[key].family_outcomes[family]["success"]
            x = margin_left + col_idx * cell_w
            fill = "#2fbf71"
            opacity = 0.18 + 0.18 * value
            parts.append(f"<rect x='{x}' y='{y}' width='{cell_w-8}' height='{cell_h-8}' fill='{fill}' fill-opacity='{opacity:.2f}' rx='8'/>")
            parts.append(f"<text x='{x+(cell_w-8)/2:.1f}' y='{y+25}' text-anchor='middle' class='small'>{value}</text>")
    parts.append("</svg>")
    out_path.write_text("".join(parts), encoding="utf-8")


def write_report(bundles: dict[str, RunBundle], old_summary: dict, md_path: Path, json_path: Path) -> None:
    branch_local800 = branch_mean(bundles["seed7_local800"], bundles["seed11_local800"])
    branch_old140 = branch_mean(bundles["seed7_old140"], bundles["seed11_old140"])
    branch_new140 = branch_mean(bundles["seed7_new140"], bundles["seed11_new140"])
    verdict_map = verdicts()

    payload = {
        "verdicts": verdict_map,
        "branch_mean_local800": branch_local800,
        "branch_mean_old140": branch_old140,
        "branch_mean_new140": branch_new140,
        "seed7_local800_metrics": bundles["seed7_local800"].metrics,
        "seed7_old140_metrics": bundles["seed7_old140"].metrics,
        "seed7_new140_metrics": bundles["seed7_new140"].metrics,
        "seed11_local800_metrics": bundles["seed11_local800"].metrics,
        "seed11_old140_metrics": bundles["seed11_old140"].metrics,
        "seed11_new140_metrics": bundles["seed11_new140"].metrics,
        "seed7_local800_family_outcomes": bundles["seed7_local800"].family_outcomes,
        "seed7_new140_family_outcomes": bundles["seed7_new140"].family_outcomes,
        "seed11_local800_family_outcomes": bundles["seed11_local800"].family_outcomes,
        "seed11_new140_family_outcomes": bundles["seed11_new140"].family_outcomes,
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    best_row = max(
        [
            ("seed7 local800", bundles["seed7_local800"].metrics["ToMCoordScore"]),
            ("seed7 new140", bundles["seed7_new140"].metrics["ToMCoordScore"]),
            ("seed11 local800", bundles["seed11_local800"].metrics["ToMCoordScore"]),
            ("seed11 new140", bundles["seed11_new140"].metrics["ToMCoordScore"]),
        ],
        key=lambda item: item[1],
    )

    lines = [
        "# Modal 140k V2 Verdict",
        "",
        f"- New v2 branch: {verdict_map['new_v2_branch']}",
        f"- Seed7 new140: {verdict_map['seed7_new140']}",
        f"- Seed11 new140: {verdict_map['seed11_new140']}",
        f"- Vs local800: {verdict_map['vs_local800']}",
        f"- Remaining risk: {verdict_map['remaining_risk']}",
        "",
        "## Best Individual Checkpoint",
        f"- `{best_row[0]}` with `ToMCoordScore={best_row[1]:.4f}`",
        "",
        "## Branch Mean Metrics",
        "### local800",
    ]
    lines.extend(f"- {metric}: {branch_local800[metric]:.4f}" for metric in METRICS)
    lines.extend(["", "### old140"])
    lines.extend(f"- {metric}: {branch_old140[metric]:.4f}" for metric in METRICS)
    lines.extend(["", "### new140"])
    lines.extend(f"- {metric}: {branch_new140[metric]:.4f}" for metric in METRICS)
    lines.extend(
        [
            "",
            "## Key Deltas",
            f"- Branch mean ToMCoordScore: old140 {branch_old140['ToMCoordScore']:.4f} -> new140 {branch_new140['ToMCoordScore']:.4f} ({metric_delta_text(branch_new140['ToMCoordScore'], branch_old140['ToMCoordScore'], 'ToMCoordScore')})",
            f"- Seed7 ToMCoordScore: old140 {bundles['seed7_old140'].metrics['ToMCoordScore']:.4f} -> new140 {bundles['seed7_new140'].metrics['ToMCoordScore']:.4f} ({metric_delta_text(bundles['seed7_new140'].metrics['ToMCoordScore'], bundles['seed7_old140'].metrics['ToMCoordScore'], 'ToMCoordScore')})",
            f"- Seed11 ToMCoordScore: old140 {bundles['seed11_old140'].metrics['ToMCoordScore']:.4f} -> new140 {bundles['seed11_new140'].metrics['ToMCoordScore']:.4f} ({metric_delta_text(bundles['seed11_new140'].metrics['ToMCoordScore'], bundles['seed11_old140'].metrics['ToMCoordScore'], 'ToMCoordScore')})",
            f"- Seed7 ToMCoordScore: local800 {bundles['seed7_local800'].metrics['ToMCoordScore']:.4f} -> new140 {bundles['seed7_new140'].metrics['ToMCoordScore']:.4f} ({metric_delta_text(bundles['seed7_new140'].metrics['ToMCoordScore'], bundles['seed7_local800'].metrics['ToMCoordScore'], 'ToMCoordScore')})",
            f"- Seed11 ToMCoordScore: local800 {bundles['seed11_local800'].metrics['ToMCoordScore']:.4f} -> new140 {bundles['seed11_new140'].metrics['ToMCoordScore']:.4f} ({metric_delta_text(bundles['seed11_new140'].metrics['ToMCoordScore'], bundles['seed11_local800'].metrics['ToMCoordScore'], 'ToMCoordScore')})",
            "",
            "## Charts",
            "- `v2_tom_score_lines.svg`",
            "- `v2_curve_overlay.svg`",
            "- `v2_family_success.svg`",
        ]
    )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_student_report(bundles: dict[str, RunBundle], report_path: Path) -> None:
    branch_local800 = branch_mean(bundles["seed7_local800"], bundles["seed11_local800"])
    branch_old140 = branch_mean(bundles["seed7_old140"], bundles["seed11_old140"])
    branch_new140 = branch_mean(bundles["seed7_new140"], bundles["seed11_new140"])
    best_seed = max((7, 11), key=lambda seed: bundles[f"seed{seed}_new140"].metrics["ToMCoordScore"])
    best_score = bundles[f"seed{best_seed}_new140"].metrics["ToMCoordScore"]

    lines = [
        "# Theory of Mind Contextual Right-of-Way Project Report",
        "",
        "## Hypothesis",
        "",
        "A policy with an explicit Theory of Mind component and stronger context-sensitive training conditions should outperform a plain recurrent baseline on the fixed Variant 2 benchmark: Contextual Right-of-Way Negotiation. The expected mechanism is not generic reward gain. It is belief-guided social adaptation. The agent should infer what sort of partner it is facing, combine that belief with urgency, norm, safety margin, and timeout pressure, and then choose a different action when the same partner belief appears under a different context.",
        "",
        "## Method",
        "",
        "The project used a fixed Variant 2 benchmark in which two agents approach a contested right-of-way decision under partial observability. The environment, evaluation logic, scenario families, context tags, and action semantics were held fixed during quality passes. The benchmark was designed to test socially contingent action selection rather than simple latent-style prediction.",
        "",
        "The main development line again used an auxhead-lite architecture. This retained the lightweight Theory of Mind structure while updating the training signal inside `train.py` to push harder on safety-first behaviour, urgency override, opportunism under norm shift, and social-misread recovery. The benchmark selection metric remained `ToMCoordScore`, which combines success, coordination efficiency, intention prediction, switch accuracy, ambiguity efficiency, collision rate, deadlock rate, and delay.",
        "",
        "This Variant 2 branch was evaluated in two main stages. First, local `800`-episode runs were executed on seeds 7 and 11 to verify that the new training conditions still beat baseline before committing to long runs. Second, both seeds were warm-started from the `800`-episode auxhead-lite checkpoints and continued to `140k` total episodes on Modal. For historical context, the older non-v2 `140k` long-run branch was also kept as a reference point.",
        "",
        "## Ethics",
        "",
        "This was a low-risk simulation study. No human subjects, personal data, or clinical claims were involved. The main ethical concern is still overclaiming social intelligence from narrow benchmark success. Results should therefore be framed as evidence of improved context-sensitive coordination in one controlled task, not as evidence of general human-like mindreading.",
        "",
        "## Results",
        "",
        f"The local `800`-episode Variant 2 runs were already stronger than baseline on both seeds. Seed 7 reached `ToMCoordScore {bundles['seed7_local800'].metrics['ToMCoordScore']:.4f}` and seed 11 reached `{bundles['seed11_local800'].metrics['ToMCoordScore']:.4f}`, giving a branch mean of `{branch_local800['ToMCoordScore']:.4f}`.",
        "",
        f"The new `140k` Variant 2 Modal runs improved further. Seed 7 reached `ToMCoordScore {bundles['seed7_new140'].metrics['ToMCoordScore']:.4f}` and seed 11 reached `{bundles['seed11_new140'].metrics['ToMCoordScore']:.4f}`. The new branch mean was `{branch_new140['ToMCoordScore']:.4f}`.",
        "",
        f"Compared with the older `140k` long-run branch, the new Variant 2 branch improved its mean `ToMCoordScore` from `{branch_old140['ToMCoordScore']:.4f}` to `{branch_new140['ToMCoordScore']:.4f}`. Mean success rate increased from `{branch_old140['SuccessRate']:.3f}` to `{branch_new140['SuccessRate']:.3f}` and mean collision rate fell from `{branch_old140['CollisionRate']:.3f}` to `{branch_new140['CollisionRate']:.3f}`. The biggest single change was seed 11, which improved from `{bundles['seed11_old140'].metrics['ToMCoordScore']:.4f}` on the old `140k` branch to `{bundles['seed11_new140'].metrics['ToMCoordScore']:.4f}` on the new Variant 2 branch.",
        "",
        "Family-level outcomes were mixed but interpretable. `late_disambiguation` remained the strongest family and improved further at the long horizon. `no_progress_switch` remained broadly stable. `false_friend` improved, especially on seed 11. `ambiguous_commit` remained mixed, particularly on seed 7. `assert_or_yield` remained the clearest failure pocket and is still the best candidate for the next targeted improvement pass.",
        "",
        "## Analysis and Discussion",
        "",
        "The central hypothesis is supported. The updated Theory of Mind line did not just improve a diagnostic belief variable. It also produced materially better branch-level coordination at the `140k` horizon than the earlier long-run line, especially through higher success, fewer collisions, and better intention prediction.",
        "",
        "The most important scientific result is that the old cross-seed long-run weakness no longer looks dominant in the same way. In the earlier long-run branch, seed 11 degraded at `140k` and acted as an overtraining warning. In the new Variant 2 branch, seed 11 became the strongest checkpoint in the comparison. That is a meaningful sign that the updated training conditions improved robustness under the contextual right-of-way framing.",
        "",
        "However, the comparison against the local `800`-episode Variant 2 runs shows a real tradeoff. The `140k` runs improved `ToMCoordScore`, intention prediction, and switch accuracy, but they did not cleanly dominate on every behavioural dimension. Relative to the local `800` branch, the `140k` runs were slower on average and showed more deadlock. This suggests that longer training refined belief quality and policy consistency, but also made the policies somewhat more deliberate and in some settings less sharp.",
        "",
        "The best current interpretation is therefore two-part. The new Variant 2 `140k` branch is the strongest long-run result so far and clearly supersedes the older `140k` branch. At the same time, `assert_or_yield` remains unresolved and the local `800` runs still show a kind of short-horizon decisiveness that the long-run branch does not fully preserve.",
        "",
        "## Appendix",
        "",
        "### Technology Used",
        "",
        "Python, PyTorch, NumPy, Modal, resumable checkpointing, CSV/JSON artifact logging, SVG-based report generation, and notebook-based inspection. The project kept the benchmark environment and evaluation code fixed while iterating only on the training surface.",
        "",
        "### Layman’s Summary",
        "",
        "We trained an AI agent on a small social coordination problem where it has to decide when to wait, when to go, and when to change its mind depending on both the other agent’s behaviour and the situation around them. The new long-run Version 2 results were clearly better than the older long-run branch, and this time the second seed did not collapse. That is encouraging. But the agent is still not equally good in every situation. It became better at some hard ambiguity-heavy cases, while still struggling in a family where it has to judge whether to push ahead or yield under pressure.",
        "",
        f"The best single run in this branch is `seed{best_seed} new140` with `ToMCoordScore {best_score:.4f}`.",
    ]
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    bundles, old_summary = load_bundles()
    write_report(
        bundles,
        old_summary,
        REPORTS_DIR / "modal_v2_140k_verdict.md",
        REPORTS_DIR / "modal_v2_140k_summary.json",
    )
    write_student_report(
        bundles,
        REPORTS_DIR / "modal_v2_140k_project_report.md",
    )
    svg_tom_score_lines(bundles, REPORTS_DIR / "v2_tom_score_lines.svg")
    svg_new_curve_overlay(bundles, REPORTS_DIR / "v2_curve_overlay.svg")
    svg_family_success(bundles, REPORTS_DIR / "v2_family_success.svg")
    print(f"wrote_reports={REPORTS_DIR}")


if __name__ == "__main__":
    main()
