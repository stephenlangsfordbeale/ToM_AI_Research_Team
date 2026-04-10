from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional


def _parse_json_line(stdout: str, prefix: str) -> Dict[str, float]:
    matches = re.findall(rf"{re.escape(prefix)}(\{{.*\}})", stdout)
    if not matches:
        raise ValueError(f"{prefix} payload not found in train.py output")
    parsed = json.loads(matches[-1])
    return {str(k): float(v) for k, v in parsed.items()}


def _parse_path_line(stdout: str, prefix: str) -> Optional[str]:
    matches = re.findall(rf"{re.escape(prefix)}(.*)", stdout)
    if not matches:
        return None
    return matches[-1].strip()


def _copy_if_exists(src_path: Optional[str], dst_dir: Path, dst_name: str) -> Optional[str]:
    if not src_path:
        return None
    src = Path(src_path)
    if not src.exists():
        return None
    dst = dst_dir / dst_name
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return str(dst)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wrapper around train.py for Azure ML component outputs.")
    parser.add_argument("--variant", choices=["baseline", "tom"], required=True)
    parser.add_argument("--train-episodes", type=int, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--tom-experiment", type=str, default="none")
    parser.add_argument("--tom-experiment-strength", type=float, default=0.25)
    parser.add_argument("--tom-belief-uncertainty-threshold", type=float, default=0.60)
    parser.add_argument("--tom-context-tag-threshold", type=float, default=0.55)
    parser.add_argument("--model-output", type=str, required=True)
    parser.add_argument("--metrics-output", type=str, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    model_output_dir = Path(args.model_output)
    metrics_output_dir = Path(args.metrics_output)
    model_output_dir.mkdir(parents=True, exist_ok=True)
    metrics_output_dir.mkdir(parents=True, exist_ok=True)

    internal_model_dir = metrics_output_dir / "_checkpoints"
    internal_curve_dir = metrics_output_dir / "_curves"
    internal_analysis_dir = metrics_output_dir / "_analysis"
    internal_model_dir.mkdir(parents=True, exist_ok=True)
    internal_curve_dir.mkdir(parents=True, exist_ok=True)
    internal_analysis_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        "train.py",
        "--variant",
        args.variant,
        "--train-episodes",
        str(args.train_episodes),
        "--seed",
        str(args.seed),
        "--max-steps",
        str(args.max_steps),
        "--save-dir",
        str(internal_model_dir),
        "--curve-dir",
        str(internal_curve_dir),
        "--analysis-dir",
        str(internal_analysis_dir),
    ]

    if args.variant == "tom":
        cmd.extend(
            [
                "--tom-experiment",
                args.tom_experiment,
                "--tom-experiment-strength",
                str(args.tom_experiment_strength),
                "--tom-belief-uncertainty-threshold",
                str(args.tom_belief_uncertainty_threshold),
                "--tom-context-tag-threshold",
                str(args.tom_context_tag_threshold),
            ]
        )

    proc = subprocess.run(cmd, cwd=str(repo_root), text=True, capture_output=True, check=False)
    (metrics_output_dir / "stdout.log").write_text(proc.stdout or "", encoding="utf-8")
    (metrics_output_dir / "stderr.log").write_text(proc.stderr or "", encoding="utf-8")

    if proc.returncode != 0:
        raise RuntimeError(f"train.py failed with exit code {proc.returncode}")

    eval_metrics = _parse_json_line(proc.stdout, "eval_metrics=")
    checkpoint_path = _parse_path_line(proc.stdout, "saved_checkpoint=")
    curve_path = _parse_path_line(proc.stdout, "learning_curve_csv=")
    analysis_path = _parse_path_line(proc.stdout, "choice_analysis_json=")

    copied_model = _copy_if_exists(checkpoint_path, model_output_dir, "model.pt")
    copied_curve = _copy_if_exists(curve_path, metrics_output_dir, "learning_curve.csv")
    copied_analysis = _copy_if_exists(analysis_path, metrics_output_dir, "choice_analysis.json")

    payload = {
        "variant": args.variant,
        "seed": args.seed,
        "train_episodes": args.train_episodes,
        "max_steps": args.max_steps,
        "eval_metrics": eval_metrics,
        "checkpoint_source": checkpoint_path,
        "copied_model": copied_model,
        "copied_curve": copied_curve,
        "copied_analysis": copied_analysis,
        "tom_experiment": args.tom_experiment if args.variant == "tom" else "none",
        "tom_experiment_strength": args.tom_experiment_strength,
        "tom_belief_uncertainty_threshold": args.tom_belief_uncertainty_threshold,
        "tom_context_tag_threshold": args.tom_context_tag_threshold,
    }

    (metrics_output_dir / "metrics.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()
