from __future__ import annotations

import json
import os
import selectors
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

try:
    import modal
except ImportError as exc:  # pragma: no cover - optional dependency path
    raise RuntimeError("Install Modal first: pip install modal") from exc


def _resolve_project_root() -> Path:
    candidates: list[Path] = []
    env_root = os.environ.get("TOM_PROJECT_ROOT")
    if env_root:
        candidates.append(Path(env_root).expanduser())

    candidates.append(Path.cwd())

    try:
        candidates.append(Path(__file__).resolve().parents[1])
    except Exception:  # pragma: no cover - defensive path handling
        pass

    for candidate in candidates:
        candidate = candidate.resolve()
        if (candidate / "train.py").exists() and (candidate / "modal").exists():
            return candidate

    # Fall back to the script-relative parent when no candidate looks like the repo root.
    return Path(__file__).resolve().parents[1]


PROJECT_ROOT = _resolve_project_root()
INCUMBENT_FAMILY = os.environ.get("TOM_INCUMBENT_FAMILY", "v5-delayedtrust-split-candidate")
APP_NAME = os.environ.get("TOM_V5_MODAL_APP_NAME", "tom-v5-delayedtrust-runner-20260414")
DEFAULT_VOLUME_NAME = os.environ.get(
    "TOM_V5_MODAL_VOLUME_NAME",
    "tom-v5-delayedtrust-runs-20260414",
)
REMOTE_OUTPUT_FAMILY = os.environ.get("TOM_V5_REMOTE_OUTPUT_FAMILY", INCUMBENT_FAMILY)
LOCAL_INCUMBENT_ROOT = PROJECT_ROOT / "modal" / "tom-experiment-incumbent" / INCUMBENT_FAMILY
REMOTE_PROJECT_ROOT = Path("/root/project")
REMOTE_INCUMBENT_ROOT = Path("/root/incumbent") / INCUMBENT_FAMILY
REMOTE_OUTPUT_ROOT = Path("/root/outputs")

DEFAULT_TARGET_TOTAL_EPISODES = 140000
DEFAULT_SAVE_EVERY = 2000
DEFAULT_COMMIT_INTERVAL_SECONDS = 60
DEFAULT_SEEDS = (7, 11, 23)

WAIT_FOR_RESULTS = os.environ.get("TOM_V5_WAIT_FOR_RESULTS", "1").lower() not in {"0", "false", "no"}


def _parse_prefixed_line(stdout: str, prefix: str) -> str | None:
    for line in stdout.splitlines():
        if line.startswith(prefix):
            return line.split("=", 1)[1].strip()
    return None


def _read_json_if_exists(path: Path) -> dict[str, object] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _run_streaming_subprocess(
    cmd: list[str],
    cwd: Path,
    stdout_log_path: Path,
    stderr_log_path: Path,
    commit_interval_seconds: int,
    tick_callback: Callable[[], None] | None = None,
) -> tuple[int, str, str]:
    proc = subprocess.Popen(
        cmd,
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    selector = selectors.DefaultSelector()
    assert proc.stdout is not None
    assert proc.stderr is not None
    selector.register(proc.stdout, selectors.EVENT_READ, data="stdout")
    selector.register(proc.stderr, selectors.EVENT_READ, data="stderr")

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    last_commit = time.monotonic()

    with stdout_log_path.open("a", encoding="utf-8") as stdout_log, stderr_log_path.open(
        "a", encoding="utf-8"
    ) as stderr_log:
        while selector.get_map():
            events = selector.select(timeout=1.0)
            for key, _ in events:
                stream_name = key.data
                line = key.fileobj.readline()
                if line == "":
                    selector.unregister(key.fileobj)
                    continue

                if stream_name == "stdout":
                    stdout_lines.append(line)
                    stdout_log.write(line)
                    stdout_log.flush()
                    print(line, end="")
                else:
                    stderr_lines.append(line)
                    stderr_log.write(line)
                    stderr_log.flush()
                    print(line, end="", file=sys.stderr)

            if tick_callback is not None:
                try:
                    tick_callback()
                except Exception as exc:  # pragma: no cover - diagnostic only
                    print(f"status_sync_warning={exc}", file=sys.stderr)

            if time.monotonic() - last_commit >= commit_interval_seconds:
                outputs.commit()
                last_commit = time.monotonic()

        returncode = proc.wait()

    outputs.commit()
    return returncode, "".join(stdout_lines), "".join(stderr_lines)


def _discover_packaged_seeds() -> tuple[int, ...]:
    for incumbent_root in (LOCAL_INCUMBENT_ROOT, REMOTE_INCUMBENT_ROOT):
        seeds: list[int] = []
        for checkpoint_path in sorted(incumbent_root.glob("seed*/selected_model.pt")):
            seed_dir = checkpoint_path.parent.name
            try:
                seeds.append(int(seed_dir.removeprefix("seed")))
            except ValueError:
                continue

        if seeds:
            return tuple(sorted(set(seeds)))

    raise RuntimeError(
        "No packaged checkpoints found under "
        f"{LOCAL_INCUMBENT_ROOT} or {REMOTE_INCUMBENT_ROOT}. "
        "If running from a non-repo cwd, set TOM_PROJECT_ROOT to the repo root."
    )


AVAILABLE_SEEDS = _discover_packaged_seeds()


def _as_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return int(float(stripped))
        except ValueError:
            return None
    return None


def _extract_progress_status_fields(
    progress_payload: dict[str, object],
    base_train_episodes: int,
    target_total_episodes: int,
) -> dict[str, object]:
    completed_total = _as_int(progress_payload.get("completed_total_episodes"))
    completed_chunk = _as_int(progress_payload.get("completed_chunk_episodes"))
    completed_additional = _as_int(progress_payload.get("completed_additional_episodes"))
    remaining_total = _as_int(progress_payload.get("remaining_total_episodes"))

    if completed_total is None and completed_additional is not None:
        completed_total = base_train_episodes + completed_additional
    if completed_total is None and completed_chunk is not None:
        completed_total = base_train_episodes + completed_chunk

    if completed_additional is None and completed_total is not None:
        completed_additional = max(0, completed_total - base_train_episodes)

    if remaining_total is None and completed_total is not None:
        remaining_total = max(0, target_total_episodes - completed_total)

    fields: dict[str, object] = {}
    if completed_total is not None:
        fields["completed_total_episodes"] = int(completed_total)
    if completed_additional is not None:
        fields["completed_additional_episodes"] = int(completed_additional)
    if completed_chunk is not None:
        fields["completed_chunk_episodes"] = int(completed_chunk)
    if remaining_total is not None:
        fields["remaining_episodes"] = int(remaining_total)

    for source_key, target_key in (
        ("latest_checkpoint", "progress_latest_checkpoint"),
        ("latest_curve", "progress_latest_curve"),
        ("artifact_episode_tag", "progress_artifact_episode_tag"),
        ("reported_train_episodes", "progress_reported_train_episodes"),
        ("is_final", "progress_is_final"),
    ):
        if source_key in progress_payload:
            fields[target_key] = progress_payload[source_key]

    return fields

image = (
    modal.Image.debian_slim()
    .pip_install_from_requirements(str(PROJECT_ROOT / "requirements.txt"))
    .add_local_file(PROJECT_ROOT / "train.py", remote_path=str(REMOTE_PROJECT_ROOT / "train.py"))
    .add_local_file(PROJECT_ROOT / "env.py", remote_path=str(REMOTE_PROJECT_ROOT / "env.py"))
    .add_local_file(PROJECT_ROOT / "eval.py", remote_path=str(REMOTE_PROJECT_ROOT / "eval.py"))
)

for seed in AVAILABLE_SEEDS:
    image = image.add_local_file(
        LOCAL_INCUMBENT_ROOT / f"seed{seed}" / "selected_model.pt",
        remote_path=str(REMOTE_INCUMBENT_ROOT / f"seed{seed}" / "selected_model.pt"),
    )

app = modal.App(APP_NAME)
outputs = modal.Volume.from_name(DEFAULT_VOLUME_NAME, create_if_missing=True)


@app.function(image=image, cpu=4.0, timeout=12 * 60 * 60, volumes={str(REMOTE_OUTPUT_ROOT): outputs})
def run_v5_seed(
    seed: int,
    target_total_episodes: int = DEFAULT_TARGET_TOTAL_EPISODES,
    save_every: int = DEFAULT_SAVE_EVERY,
    commit_interval_seconds: int = DEFAULT_COMMIT_INTERVAL_SECONDS,
) -> dict[str, object]:
    if seed not in AVAILABLE_SEEDS:
        raise ValueError(f"Only packaged seeds {AVAILABLE_SEEDS} are available for incumbent family {INCUMBENT_FAMILY}.")

    checkpoint_path = REMOTE_INCUMBENT_ROOT / f"seed{seed}" / "selected_model.pt"

    import torch

    checkpoint = torch.load(checkpoint_path, map_location="cpu")
    checkpoint_args = checkpoint.get("args", {})
    start_episodes = int(checkpoint_args.get("train_episodes", 0))
    if target_total_episodes <= start_episodes:
        raise ValueError(
            f"target_total_episodes={target_total_episodes} must exceed checkpoint train_episodes={start_episodes}"
        )

    output_dir = REMOTE_OUTPUT_ROOT / REMOTE_OUTPUT_FAMILY / f"seed{seed}" / f"target-{target_total_episodes}"
    checkpoint_dir = output_dir / "checkpoints"
    curve_dir = output_dir / "curves"
    analysis_dir = output_dir / "analysis"
    progress_json = output_dir / "progress.json"
    run_status_json = output_dir / "run_status.json"
    stdout_log_path = output_dir / "stdout.log"
    stderr_log_path = output_dir / "stderr.log"
    latest_checkpoint_path = checkpoint_dir / f"latest-tom_seed{seed}.pt"
    latest_curve_path = curve_dir / f"latest-curve-tom-seed{seed}.csv"
    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    curve_dir.mkdir(parents=True, exist_ok=True)
    analysis_dir.mkdir(parents=True, exist_ok=True)

    existing_summary = _read_json_if_exists(output_dir / "run_summary.json")
    if existing_summary and existing_summary.get("returncode") == 0:
        existing_summary["resume_mode"] = "already_complete"
        return existing_summary

    existing_progress = _read_json_if_exists(progress_json) or {}
    completed_total_episodes = int(existing_progress.get("completed_total_episodes", start_episodes))
    completed_additional_episodes = max(0, completed_total_episodes - start_episodes)
    resume_checkpoint = latest_checkpoint_path if latest_checkpoint_path.exists() else checkpoint_path
    remaining_episodes = target_total_episodes - completed_total_episodes
    if remaining_episodes <= 0:
        payload = {
            "seed": seed,
            "incumbent_family": INCUMBENT_FAMILY,
            "output_family": REMOTE_OUTPUT_FAMILY,
            "initial_checkpoint": str(checkpoint_path),
            "initial_checkpoint_train_episodes": start_episodes,
            "completed_total_episodes": completed_total_episodes,
            "completed_additional_episodes": completed_additional_episodes,
            "target_total_episodes": target_total_episodes,
            "output_dir": str(output_dir),
            "resume_checkpoint": str(resume_checkpoint),
            "resume_mode": "completed_without_summary",
            "returncode": 0,
        }
        _write_json(output_dir / "run_summary.json", payload)
        outputs.commit()
        return payload

    status_payload = {
        "seed": seed,
        "state": "running",
        "incumbent_family": INCUMBENT_FAMILY,
        "output_family": REMOTE_OUTPUT_FAMILY,
        "target_total_episodes": target_total_episodes,
        "initial_checkpoint": str(checkpoint_path),
        "resume_checkpoint": str(resume_checkpoint),
        "base_train_episodes": start_episodes,
        "completed_total_episodes": completed_total_episodes,
        "completed_additional_episodes": completed_additional_episodes,
        "remaining_episodes": remaining_episodes,
        "save_every": save_every,
        "commit_interval_seconds": commit_interval_seconds,
    }
    _write_json(run_status_json, status_payload)
    outputs.commit()

    last_progress_signature: str | None = None

    def _sync_run_status_from_progress(force_commit: bool = False) -> None:
        nonlocal last_progress_signature
        progress_payload = _read_json_if_exists(progress_json)
        if not isinstance(progress_payload, dict):
            return

        progress_fields = _extract_progress_status_fields(
            progress_payload=progress_payload,
            base_train_episodes=start_episodes,
            target_total_episodes=target_total_episodes,
        )
        if not progress_fields:
            return

        signature = json.dumps(progress_fields, sort_keys=True, default=str)
        if signature == last_progress_signature:
            return

        status_payload.update(progress_fields)
        status_payload["state"] = "running"
        status_payload["last_progress_sync_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        _write_json(run_status_json, status_payload)
        last_progress_signature = signature
        if force_commit:
            outputs.commit()

    cmd = [
        sys.executable,
        "-u",
        "train.py",
        "--variant",
        "tom",
        "--seed",
        str(seed),
        "--train-episodes",
        str(remaining_episodes),
        "--base-train-episodes",
        str(start_episodes),
        "--episode-offset",
        str(completed_total_episodes),
        "--reported-train-episodes",
        str(target_total_episodes),
        "--artifact-episode-tag",
        str(target_total_episodes),
        "--init-checkpoint",
        str(resume_checkpoint),
        "--hidden-dim",
        str(checkpoint_args.get("hidden_dim", 64)),
        "--lr",
        str(checkpoint_args.get("lr", 3e-4)),
        "--gamma",
        str(checkpoint_args.get("gamma", 0.98)),
        "--entropy-coef",
        str(checkpoint_args.get("entropy_coef", 0.01)),
        "--aux-loss-weight",
        str(checkpoint_args.get("aux_loss_weight", 0.25)),
        "--max-steps",
        str(checkpoint_args.get("max_steps", 20)),
        "--tom-experiment",
        str(checkpoint_args.get("tom_experiment", "contextual_right_of_way_switch")),
        "--tom-experiment-strength",
        str(checkpoint_args.get("tom_experiment_strength", 0.25)),
        "--tom-belief-uncertainty-threshold",
        str(checkpoint_args.get("tom_belief_uncertainty_threshold", 0.60)),
        "--tom-context-tag-threshold",
        str(checkpoint_args.get("tom_context_tag_threshold", 0.55)),
        "--tom-proceed-safety-penalty",
        str(checkpoint_args.get("tom_proceed_safety_penalty", 0.12)),
        "--tom-conflict-dist-threshold",
        str(checkpoint_args.get("tom_conflict_dist_threshold", 0.55)),
        "--tom-bottleneck-dist-threshold",
        str(checkpoint_args.get("tom_bottleneck_dist_threshold", 0.45)),
        "--analysis-conflict-dist-threshold",
        str(checkpoint_args.get("analysis_conflict_dist_threshold", 0.2)),
        "--analysis-bottleneck-dist-threshold",
        str(checkpoint_args.get("analysis_bottleneck_dist_threshold", 0.35)),
        "--analysis-urgency-threshold",
        str(checkpoint_args.get("analysis_urgency_threshold", 0.5)),
        "--save-dir",
        str(checkpoint_dir),
        "--curve-dir",
        str(curve_dir),
        "--analysis-dir",
        str(analysis_dir),
        "--resume-curve-from",
        str(latest_curve_path if latest_curve_path.exists() else ""),
        "--progress-json",
        str(progress_json),
        "--save-every",
        str(save_every),
    ]

    returncode, stdout_text, _ = _run_streaming_subprocess(
        cmd=cmd,
        cwd=REMOTE_PROJECT_ROOT,
        stdout_log_path=stdout_log_path,
        stderr_log_path=stderr_log_path,
        commit_interval_seconds=commit_interval_seconds,
        tick_callback=lambda: _sync_run_status_from_progress(force_commit=True),
    )

    # Final sync in case the last progress write happened right before process exit.
    _sync_run_status_from_progress(force_commit=True)

    saved_checkpoint = _parse_prefixed_line(stdout_text, "saved_checkpoint")
    learning_curve_csv = _parse_prefixed_line(stdout_text, "learning_curve_csv")
    choice_analysis_json = _parse_prefixed_line(stdout_text, "choice_analysis_json")
    eval_metrics_raw = _parse_prefixed_line(stdout_text, "eval_metrics")
    eval_metrics = json.loads(eval_metrics_raw) if eval_metrics_raw else None

    summary = {
        "seed": seed,
        "incumbent_family": INCUMBENT_FAMILY,
        "output_family": REMOTE_OUTPUT_FAMILY,
        "initial_checkpoint": str(checkpoint_path),
        "initial_checkpoint_train_episodes": start_episodes,
        "additional_train_episodes": target_total_episodes - start_episodes,
        "target_total_episodes": target_total_episodes,
        "output_dir": str(output_dir),
        "resume_checkpoint": str(resume_checkpoint),
        "resume_mode": "resumed" if resume_checkpoint != checkpoint_path else "fresh_from_incumbent",
        "saved_checkpoint": saved_checkpoint,
        "learning_curve_csv": learning_curve_csv,
        "choice_analysis_json": choice_analysis_json,
        "eval_metrics": eval_metrics,
        "returncode": returncode,
    }

    status_payload["state"] = "completed" if returncode == 0 else "failed"
    if returncode == 0:
        status_payload["completed_total_episodes"] = int(target_total_episodes)
        status_payload["completed_additional_episodes"] = int(max(0, target_total_episodes - start_episodes))
        status_payload["remaining_episodes"] = 0
    status_payload["last_status_update_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    _write_json(run_status_json, status_payload)
    _write_json(output_dir / "run_summary.json", summary)
    outputs.commit()

    if returncode != 0:
        raise RuntimeError(f"train.py failed for seed {seed} with exit code {returncode}")

    return summary


def _parse_seed_csv(seed_csv: str) -> tuple[int, ...]:
    values = [part.strip() for part in seed_csv.split(",") if part.strip()]
    seeds = tuple(int(v) for v in values)
    for seed in seeds:
        if seed not in AVAILABLE_SEEDS:
            raise ValueError(f"Seed {seed} not available in packaged incumbent family {INCUMBENT_FAMILY}: {AVAILABLE_SEEDS}")
    return seeds


@app.local_entrypoint()
def main(
    target_total_episodes: int = DEFAULT_TARGET_TOTAL_EPISODES,
    seeds_csv: str = "7,11,23",
    save_every: int = DEFAULT_SAVE_EVERY,
    commit_interval_seconds: int = DEFAULT_COMMIT_INTERVAL_SECONDS,
) -> None:
    seeds = _parse_seed_csv(seeds_csv)
    print(f"project_root={PROJECT_ROOT}")
    print(f"incumbent_family={INCUMBENT_FAMILY}")
    print(f"local_incumbent_root={LOCAL_INCUMBENT_ROOT}")
    print(f"available_seeds={AVAILABLE_SEEDS}")
    calls: list[tuple[int, object]] = []

    for seed in seeds:
        function_call = run_v5_seed.spawn(
            seed,
            target_total_episodes=target_total_episodes,
            save_every=save_every,
            commit_interval_seconds=commit_interval_seconds,
        )
        calls.append((seed, function_call))
        print(json.dumps({"seed": seed, "submitted": True}, indent=2, sort_keys=True))

    print(f"app_name={APP_NAME}")
    print(f"volume_name={DEFAULT_VOLUME_NAME}")

    if not WAIT_FOR_RESULTS:
        return

    results = modal.FunctionCall.gather(*[function_call for _, function_call in calls])
    for result in results:
        print(json.dumps(result, indent=2, sort_keys=True))
