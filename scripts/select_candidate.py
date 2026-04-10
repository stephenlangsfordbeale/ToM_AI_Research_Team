from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Dict


def _load_metrics(metrics_dir: Path) -> Dict[str, object]:
    path = metrics_dir / "metrics.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing metrics file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _metric(payload: Dict[str, object], metric_name: str) -> float:
    eval_metrics = payload.get("eval_metrics", {})
    if not isinstance(eval_metrics, dict):
        return 0.0
    value = eval_metrics.get(metric_name, 0.0)
    return float(value)


def _copy_model(model_dir: Path, selected_model_dir: Path) -> None:
    selected_model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "model.pt"
    if not model_path.exists():
        raise FileNotFoundError(f"Expected model file not found: {model_path}")
    shutil.copy2(model_path, selected_model_dir / "model.pt")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select candidate model using epsilon and deadlock guardrail.")
    parser.add_argument("--baseline-metrics-dir", type=str, required=True)
    parser.add_argument("--baseline-model-dir", type=str, required=True)
    parser.add_argument("--candidate-metrics-dir", type=str, required=True)
    parser.add_argument("--candidate-model-dir", type=str, required=True)
    parser.add_argument("--epsilon", type=float, default=0.02)
    parser.add_argument("--deadlock-delta-threshold", type=float, default=0.15)
    parser.add_argument("--selected-model-dir", type=str, required=True)
    parser.add_argument("--selection-output-dir", type=str, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    baseline_metrics = _load_metrics(Path(args.baseline_metrics_dir))
    candidate_metrics = _load_metrics(Path(args.candidate_metrics_dir))

    baseline_tom_coord = _metric(baseline_metrics, "ToMCoordScore")
    candidate_tom_coord = _metric(candidate_metrics, "ToMCoordScore")
    baseline_deadlock = _metric(baseline_metrics, "DeadlockRate")
    candidate_deadlock = _metric(candidate_metrics, "DeadlockRate")

    decision = "keep" if candidate_tom_coord >= baseline_tom_coord + args.epsilon else "discard"
    deadlock_delta = candidate_deadlock - baseline_deadlock
    auto_reject_reason = None
    if deadlock_delta > args.deadlock_delta_threshold:
        decision = "discard"
        auto_reject_reason = (
            f"deadlock_delta {deadlock_delta:.6f} exceeds threshold {args.deadlock_delta_threshold:.6f}"
        )

    selected_variant = "tom" if decision == "keep" else "baseline"
    selected_model_source = Path(args.candidate_model_dir) if selected_variant == "tom" else Path(args.baseline_model_dir)
    selected_model_dest = Path(args.selected_model_dir)
    selection_output_dir = Path(args.selection_output_dir)
    selection_output_dir.mkdir(parents=True, exist_ok=True)

    _copy_model(selected_model_source, selected_model_dest)

    summary = {
        "decision": decision,
        "selected_variant": selected_variant,
        "epsilon": args.epsilon,
        "deadlock_delta_threshold": args.deadlock_delta_threshold,
        "baseline_metrics": baseline_metrics.get("eval_metrics", {}),
        "candidate_metrics": candidate_metrics.get("eval_metrics", {}),
        "baseline_ToMCoordScore": baseline_tom_coord,
        "candidate_ToMCoordScore": candidate_tom_coord,
        "baseline_deadlock_rate": baseline_deadlock,
        "candidate_deadlock_rate": candidate_deadlock,
        "deadlock_delta": deadlock_delta,
        "auto_reject_reason": auto_reject_reason,
    }

    (selection_output_dir / "selection.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
