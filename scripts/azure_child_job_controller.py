from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class PatchSpec:
    patch_id: str
    variant: str
    extra_args: List[str]


def parse_metrics(stdout: str) -> Dict[str, float]:
    m = re.findall(r"eval_metrics=(\{.*\})", stdout)
    if not m:
        raise ValueError("eval_metrics not found in run output")
    data = json.loads(m[-1])
    return {
        "success_rate": float(data["SuccessRate"]),
        "collision_rate": float(data["CollisionRate"]),
        # Delay proxy: low efficiency implies high delay.
        "average_delay": float(1.0 - data["CoordinationEfficiency"]),
        "intention_prediction_f1": float(data["IntentionPredictionF1"]),
        "ToMCoordScore": float(data["ToMCoordScore"]),
    }


def parse_checkpoint(stdout: str) -> Optional[str]:
    m = re.findall(r"saved_checkpoint=(.*)", stdout)
    if not m:
        return None
    return m[-1].strip()


def git_diff_metadata(repo_root: Path, patch_id: str) -> Dict[str, Any]:
    try:
        result = subprocess.run(
            ["git", "--no-pager", "diff", "--", "train.py"],
            cwd=str(repo_root),
            text=True,
            capture_output=True,
            check=False,
        )
        diff_text = result.stdout or ""
    except Exception:
        diff_text = ""

    digest = hashlib.sha256((patch_id + "\n" + diff_text).encode("utf-8")).hexdigest()
    return {
        "patch_id": patch_id,
        "git_diff_sha256": digest,
        "git_diff_lines": len(diff_text.splitlines()) if diff_text else 0,
    }


def run_child_job(
    repo_root: Path,
    patch: PatchSpec,
    seed: int,
    episodes: int,
    time_budget_seconds: int,
    curve_dir: str,
    analysis_dir: str,
    save_dir: str,
) -> Dict[str, Any]:
    run_id = str(uuid.uuid4())
    cmd = [
        "python",
        "train.py",
        "--variant",
        patch.variant,
        "--train-episodes",
        str(episodes),
        "--seed",
        str(seed),
        "--curve-dir",
        curve_dir,
        "--analysis-dir",
        analysis_dir,
        "--save-dir",
        save_dir,
        *patch.extra_args,
    ]
    t0 = time.time()
    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        text=True,
        capture_output=True,
        timeout=max(10, time_budget_seconds),
        check=False,
    )
    wall = time.time() - t0

    out: Dict[str, Any] = {
        "run_id": run_id,
        "patch_id": patch.patch_id,
        "seed": seed,
        "variant": patch.variant,
        "episodes": episodes,
        "wall_seconds": round(wall, 4),
        "status": "ok" if proc.returncode == 0 else "error",
        "return_code": proc.returncode,
        "scenario_settings": "fixed_validation_scenarios_v1",
        "time_budget_seconds": time_budget_seconds,
    }

    if proc.returncode == 0:
        metrics = parse_metrics(proc.stdout)
        out.update(metrics)
        out["checkpoint"] = parse_checkpoint(proc.stdout)
    else:
        out["stderr_tail"] = (proc.stderr or "")[-1200:]

    out["patch_metadata"] = git_diff_metadata(repo_root, patch.patch_id)
    return out


def mean_score(rows: List[Dict[str, Any]], patch_id: str) -> float:
    vals = [r["ToMCoordScore"] for r in rows if r.get("patch_id") == patch_id and r.get("status") == "ok"]
    return sum(vals) / max(1, len(vals))


def mean_metric(rows: List[Dict[str, Any]], patch_id: str, metric: str) -> float:
    vals = [r[metric] for r in rows if r.get("patch_id") == patch_id and r.get("status") == "ok" and metric in r]
    return sum(vals) / max(1, len(vals))


def build_default_patches(args: argparse.Namespace) -> List[PatchSpec]:
    candidate_extra_args = [
        "--tom-experiment",
        args.candidate_tom_experiment,
        "--tom-experiment-strength",
        str(args.candidate_tom_experiment_strength),
        "--tom-belief-uncertainty-threshold",
        str(args.candidate_tom_belief_uncertainty_threshold),
        "--tom-context-tag-threshold",
        str(args.candidate_tom_context_tag_threshold),
    ]
    return [
        PatchSpec(patch_id="baseline", variant="baseline", extra_args=[]),
        PatchSpec(patch_id="candidate_tom", variant="tom", extra_args=candidate_extra_args),
    ]


def load_profile_defaults(profile_path: Optional[str]) -> Dict[str, Any]:
    if not profile_path:
        return {}
    path = Path(profile_path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Azure-style child job controller for short-run patch comparisons.")
    parser.add_argument("--profile", type=str, default="configs/overnight_profile.json")
    parser.add_argument("--episodes", type=int, default=120)
    parser.add_argument("--time-budget-seconds", type=int, default=600)
    parser.add_argument("--epsilon", type=float, default=0.02)
    parser.add_argument("--deadlock-delta-threshold", type=float, default=0.15)
    parser.add_argument("--scenario-tag", type=str, default="fixed_validation_scenarios_v1")
    parser.add_argument("--seeds", type=str, default="7,11,19,23")
    parser.add_argument("--curve-dir", type=str, default="logs/curves")
    parser.add_argument("--analysis-dir", type=str, default="logs/analysis")
    parser.add_argument("--save-dir", type=str, default="logs/checkpoints/child-jobs")
    parser.add_argument("--output-dir", type=str, default="logs/child-jobs")
    parser.add_argument("--candidate-tom-experiment", type=str, default="none")
    parser.add_argument("--candidate-tom-experiment-strength", type=float, default=0.25)
    parser.add_argument("--candidate-tom-belief-uncertainty-threshold", type=float, default=0.60)
    parser.add_argument("--candidate-tom-context-tag-threshold", type=float, default=0.55)
    parser.add_argument("--write-summary-only", action="store_true")
    args = parser.parse_args()

    profile = load_profile_defaults(args.profile)
    parity = profile.get("parity_controls", {}) if profile else {}
    controller = profile.get("controller", {}) if profile else {}

    if args.episodes == 120 and parity.get("train_episodes"):
        args.episodes = int(parity["train_episodes"])
    if args.time_budget_seconds == 600 and parity.get("time_budget_seconds"):
        args.time_budget_seconds = int(parity["time_budget_seconds"])
    if args.scenario_tag == "fixed_validation_scenarios_v1" and parity.get("scenario_tag"):
        args.scenario_tag = str(parity["scenario_tag"])
    if args.seeds == "7,11,19,23" and parity.get("seeds"):
        args.seeds = ",".join(str(s) for s in parity["seeds"])
    if args.epsilon == 0.02 and controller.get("epsilon") is not None:
        args.epsilon = float(controller["epsilon"])
    if args.deadlock_delta_threshold == 0.15 and controller.get("deadlock_delta_threshold") is not None:
        args.deadlock_delta_threshold = float(controller["deadlock_delta_threshold"])

    repo_root = Path.cwd()
    output_dir = repo_root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    jsonl_path = output_dir / f"child-job-runs-{stamp}.jsonl"
    summary_path = output_dir / f"controller-summary-{stamp}.json"

    patches = build_default_patches(args)
    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]

    rows: List[Dict[str, Any]] = []
    if not args.write_summary_only:
        for patch in patches:
            for seed in seeds:
                row = run_child_job(
                    repo_root=repo_root,
                    patch=patch,
                    seed=seed,
                    episodes=args.episodes,
                    time_budget_seconds=args.time_budget_seconds,
                    curve_dir=args.curve_dir,
                    analysis_dir=args.analysis_dir,
                    save_dir=args.save_dir,
                )
                row["scenario_settings"] = args.scenario_tag
                rows.append(row)

        with jsonl_path.open("w", encoding="utf-8") as f:
            for row in rows:
                f.write(json.dumps(row, sort_keys=True) + "\n")

    baseline_score = mean_score(rows, "baseline") if rows else 0.0
    candidate_score = mean_score(rows, "candidate_tom") if rows else 0.0
    baseline_deadlock = mean_metric(rows, "baseline", "deadlock_rate") if rows else 0.0
    candidate_deadlock = mean_metric(rows, "candidate_tom", "deadlock_rate") if rows else 0.0
    deadlock_delta = candidate_deadlock - baseline_deadlock
    decision = "keep" if candidate_score >= baseline_score + args.epsilon else "discard"

    auto_reject_reason: Optional[str] = None
    if deadlock_delta > args.deadlock_delta_threshold:
        decision = "discard"
        auto_reject_reason = (
            f"deadlock_delta {deadlock_delta:.6f} exceeds threshold {args.deadlock_delta_threshold:.6f}"
        )

    best_checkpoint: Optional[str] = None
    if decision == "keep":
        cands = [r for r in rows if r.get("patch_id") == "candidate_tom" and r.get("status") == "ok"]
        if cands:
            best_checkpoint = sorted(cands, key=lambda x: x.get("ToMCoordScore", -1e9), reverse=True)[0].get("checkpoint")

    summary = {
        "timestamp": stamp,
        "protocol": {
            "same_environment": True,
            "same_time_budget": True,
            "same_evaluation_scenarios": True,
            "scenario_tag": args.scenario_tag,
        },
        "epsilon": args.epsilon,
        "deadlock_delta_threshold": args.deadlock_delta_threshold,
        "baseline_mean_ToMCoordScore": baseline_score,
        "candidate_mean_ToMCoordScore": candidate_score,
        "baseline_mean_deadlock_rate": baseline_deadlock,
        "candidate_mean_deadlock_rate": candidate_deadlock,
        "deadlock_delta": deadlock_delta,
        "decision": decision,
        "auto_reject_reason": auto_reject_reason,
        "next_generation_seed_checkpoint": best_checkpoint,
        "runs_logged": len(rows),
        "run_log_path": str(jsonl_path),
        "profile_path": args.profile,
    }

    with summary_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    print("controller_summary=" + json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
