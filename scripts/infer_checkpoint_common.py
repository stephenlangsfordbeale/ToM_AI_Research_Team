from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any

import numpy as np
import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from env import ACTION_NAMES, PARTNER_TYPES, ToMCoordinationEnv


def _load_module(module_path: Path, module_name: str) -> Any:
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _arg(saved_args: dict[str, Any], name: str, default: float | str | int) -> float | str | int:
    value = saved_args.get(name, default)
    return default if value is None else value


def _build_model(module: Any, variant: str, saved_args: dict[str, Any], env: ToMCoordinationEnv) -> Any:
    hidden_dim = int(_arg(saved_args, "hidden_dim", 64))
    if variant == "baseline":
        return module.BaselinePolicy(env.obs_dim, hidden_dim, env.action_dim)

    return module.ToMPolicy(
        env.obs_dim,
        hidden_dim,
        env.action_dim,
        env.n_partner_types,
        proceed_safety_penalty=float(_arg(saved_args, "tom_proceed_safety_penalty", 0.35)),
        conflict_dist_threshold=float(_arg(saved_args, "tom_conflict_dist_threshold", 0.20)),
        bottleneck_dist_threshold=float(_arg(saved_args, "tom_bottleneck_dist_threshold", 0.35)),
        tom_experiment=str(_arg(saved_args, "tom_experiment", "none")),
        tom_experiment_strength=float(_arg(saved_args, "tom_experiment_strength", 0.25)),
        tom_belief_uncertainty_threshold=float(_arg(saved_args, "tom_belief_uncertainty_threshold", 0.60)),
        tom_context_tag_threshold=float(_arg(saved_args, "tom_context_tag_threshold", 0.55)),
    )


def _to_serializable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        if value.ndim > 1 and value.shape[0] == 1:
            value = value.squeeze(0)
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return value


def _parse_json_list(raw: str, label: str) -> list[float]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{label} must be valid JSON.") from exc
    if not isinstance(value, list):
        raise SystemExit(f"{label} must be a JSON list.")
    return value


def build_parser(description: str, default_checkpoint: Path) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=default_checkpoint,
        help=f"Checkpoint path (default: {default_checkpoint})",
    )
    parser.add_argument(
        "--obs",
        required=True,
        help='Observation as JSON list, e.g. \'[0,1,1,0.5,0,0,0,0,0,0]\'',
    )
    parser.add_argument(
        "--state",
        default=None,
        help="Optional recurrent state as JSON list. Omit to start from model.init_state().",
    )
    return parser


def run_inference(
    *,
    checkpoint_path: Path,
    train_module_path: Path,
    train_module_name: str,
    obs_json: str,
    state_json: str | None,
) -> dict[str, Any]:
    checkpoint_path = checkpoint_path.expanduser().resolve(strict=False)
    if not checkpoint_path.exists():
        raise SystemExit(f"Checkpoint not found: {checkpoint_path}")
    if not train_module_path.exists():
        raise SystemExit(f"train.py not found: {train_module_path}")

    payload = torch.load(checkpoint_path, map_location="cpu")
    variant = str(payload["variant"])
    saved_args = dict(payload.get("args", {}))

    env = ToMCoordinationEnv(max_steps=int(_arg(saved_args, "max_steps", 20)))
    module = _load_module(train_module_path, train_module_name)
    model = _build_model(module, variant, saved_args, env)
    model.load_state_dict(payload["state_dict"])
    model.eval()

    obs = np.asarray(_parse_json_list(obs_json, "--obs"), dtype=np.float32)
    if obs.shape != (env.obs_dim,):
        raise SystemExit(f"--obs must have length {env.obs_dim}, got shape {obs.shape}")

    state = None
    if state_json is not None:
        state = np.asarray(_parse_json_list(state_json, "--state"), dtype=np.float32)
        if state.ndim == 1:
            state = np.expand_dims(state, axis=0)

    runner = module.build_policy_runner(model, torch.device("cpu"))
    result = {key: _to_serializable(value) for key, value in runner(obs, state).items()}

    action = result.get("action")
    if isinstance(action, int) and action in ACTION_NAMES:
        result["action_name"] = ACTION_NAMES[action]

    belief_class = result.get("belief_class")
    if isinstance(belief_class, int) and 0 <= belief_class < len(PARTNER_TYPES):
        result["belief_class_name"] = PARTNER_TYPES[belief_class]

    return {
        "checkpoint": str(checkpoint_path),
        "variant": variant,
        "obs_dim": env.obs_dim,
        "result": result,
    }
