from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional


def _load_profile_defaults(profile_path: str) -> Dict[str, object]:
    path = Path(profile_path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


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


def _run_and_package(
    repo_root: Path,
    *,
    artifact_prefix: str,
    variant: str,
    train_episodes: int,
    seed: int,
    max_steps: int,
    output_root: Path,
    tom_experiment: str,
    tom_experiment_strength: float,
    tom_belief_uncertainty_threshold: float,
    tom_context_tag_threshold: float,
) -> Dict[str, str]:
    model_output_dir = output_root / f"{artifact_prefix}_model"
    metrics_output_dir = output_root / f"{artifact_prefix}_metrics"
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
        variant,
        "--train-episodes",
        str(train_episodes),
        "--seed",
        str(seed),
        "--max-steps",
        str(max_steps),
        "--save-dir",
        str(internal_model_dir),
        "--curve-dir",
        str(internal_curve_dir),
        "--analysis-dir",
        str(internal_analysis_dir),
    ]

    if variant == "tom":
        cmd.extend(
            [
                "--tom-experiment",
                tom_experiment,
                "--tom-experiment-strength",
                str(tom_experiment_strength),
                "--tom-belief-uncertainty-threshold",
                str(tom_belief_uncertainty_threshold),
                "--tom-context-tag-threshold",
                str(tom_context_tag_threshold),
            ]
        )

    proc = subprocess.run(cmd, cwd=str(repo_root), text=True, capture_output=True, check=False)
    (metrics_output_dir / "stdout.log").write_text(proc.stdout or "", encoding="utf-8")
    (metrics_output_dir / "stderr.log").write_text(proc.stderr or "", encoding="utf-8")

    if proc.returncode != 0:
        raise RuntimeError(f"{variant} train.py failed with exit code {proc.returncode}")

    eval_metrics = _parse_json_line(proc.stdout, "eval_metrics=")
    checkpoint_path = _parse_path_line(proc.stdout, "saved_checkpoint=")
    curve_path = _parse_path_line(proc.stdout, "learning_curve_csv=")
    analysis_path = _parse_path_line(proc.stdout, "choice_analysis_json=")

    copied_model = _copy_if_exists(checkpoint_path, model_output_dir, "model.pt")
    copied_curve = _copy_if_exists(curve_path, metrics_output_dir, "learning_curve.csv")
    copied_analysis = _copy_if_exists(analysis_path, metrics_output_dir, "choice_analysis.json")

    payload = {
        "variant": variant,
        "seed": seed,
        "train_episodes": train_episodes,
        "max_steps": max_steps,
        "eval_metrics": eval_metrics,
        "checkpoint_source": checkpoint_path,
        "copied_model": copied_model,
        "copied_curve": copied_curve,
        "copied_analysis": copied_analysis,
        "tom_experiment": tom_experiment if variant == "tom" else "none",
        "tom_experiment_strength": tom_experiment_strength,
        "tom_belief_uncertainty_threshold": tom_belief_uncertainty_threshold,
        "tom_context_tag_threshold": tom_context_tag_threshold,
    }
    (metrics_output_dir / "metrics.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    return {
        "model_dir": str(model_output_dir),
        "metrics_dir": str(metrics_output_dir),
        "metrics_file": str(metrics_output_dir / "metrics.json"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run baseline -> candidate -> selection locally without Azure.")
    parser.add_argument("--profile", type=str, default="configs/overnight_profile.json")
    parser.add_argument("--output-root", type=str, default="logs/local-run")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--train-episodes", type=int, default=800)
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--epsilon", type=float, default=0.02)
    parser.add_argument("--deadlock-delta-threshold", type=float, default=0.15)
    parser.add_argument("--candidate-tom-experiment", type=str, default="contextual_right_of_way_switch")
    parser.add_argument("--candidate-tom-experiment-strength", type=float, default=0.25)
    parser.add_argument("--candidate-tom-belief-uncertainty-threshold", type=float, default=0.60)
    parser.add_argument("--candidate-tom-context-tag-threshold", type=float, default=0.55)
    args = parser.parse_args()

    profile = _load_profile_defaults(args.profile)
    parity = profile.get("parity_controls", {}) if isinstance(profile, dict) else {}
    controller = profile.get("controller", {}) if isinstance(profile, dict) else {}

    if args.train_episodes == 800 and "train_episodes" in parity:
        args.train_episodes = int(parity["train_episodes"])
    if args.epsilon == 0.02 and "epsilon" in controller:
        args.epsilon = float(controller["epsilon"])
    if args.deadlock_delta_threshold == 0.15 and "deadlock_delta_threshold" in controller:
        args.deadlock_delta_threshold = float(controller["deadlock_delta_threshold"])

    return args


def main() -> None:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    output_root = repo_root / args.output_root
    output_root.mkdir(parents=True, exist_ok=True)

    baseline = _run_and_package(
        repo_root,
        artifact_prefix="baseline",
        variant="baseline",
        train_episodes=args.train_episodes,
        seed=args.seed,
        max_steps=args.max_steps,
        output_root=output_root,
        tom_experiment="none",
        tom_experiment_strength=args.candidate_tom_experiment_strength,
        tom_belief_uncertainty_threshold=args.candidate_tom_belief_uncertainty_threshold,
        tom_context_tag_threshold=args.candidate_tom_context_tag_threshold,
    )
    candidate = _run_and_package(
        repo_root,
        artifact_prefix="candidate",
        variant="tom",
        train_episodes=args.train_episodes,
        seed=args.seed,
        max_steps=args.max_steps,
        output_root=output_root,
        tom_experiment=args.candidate_tom_experiment,
        tom_experiment_strength=args.candidate_tom_experiment_strength,
        tom_belief_uncertainty_threshold=args.candidate_tom_belief_uncertainty_threshold,
        tom_context_tag_threshold=args.candidate_tom_context_tag_threshold,
    )

    selected_model_dir = output_root / "selected_model"
    selection_output_dir = output_root / "selection"
    selection_output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        "scripts/select_candidate.py",
        "--baseline-metrics-dir",
        baseline["metrics_dir"],
        "--baseline-model-dir",
        baseline["model_dir"],
        "--candidate-metrics-dir",
        candidate["metrics_dir"],
        "--candidate-model-dir",
        candidate["model_dir"],
        "--epsilon",
        str(args.epsilon),
        "--deadlock-delta-threshold",
        str(args.deadlock_delta_threshold),
        "--selected-model-dir",
        str(selected_model_dir),
        "--selection-output-dir",
        str(selection_output_dir),
    ]
    proc = subprocess.run(cmd, cwd=str(repo_root), text=True, capture_output=True, check=False)
    (selection_output_dir / "stdout.log").write_text(proc.stdout or "", encoding="utf-8")
    (selection_output_dir / "stderr.log").write_text(proc.stderr or "", encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"select_candidate.py failed with exit code {proc.returncode}")

    selection_summary = json.loads(proc.stdout)
    summary = {
        "output_root": str(output_root),
        "baseline_model_dir": baseline["model_dir"],
        "baseline_metrics_dir": baseline["metrics_dir"],
        "candidate_model_dir": candidate["model_dir"],
        "candidate_metrics_dir": candidate["metrics_dir"],
        "selected_model_dir": str(selected_model_dir),
        "selection_output_dir": str(selection_output_dir),
        "selection": selection_summary,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
