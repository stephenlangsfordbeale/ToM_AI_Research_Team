from __future__ import annotations

import os
from functools import lru_cache
from typing import List, Optional

import numpy as np
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from env import ToMCoordinationEnv
from train import BaselinePolicy, PolicyModel, ToMPolicy


DEFAULT_MODEL_PATH = "logs/local-run/selected_model/model.pt"


class PredictRequest(BaseModel):
    obs: List[float]
    state: Optional[List[float]] = None


class PredictResponse(BaseModel):
    action: int
    state: List[float]
    belief_class: Optional[int] = None
    experiment_mask: Optional[float] = None
    assert_context_mask: Optional[float] = None
    yield_context_mask: Optional[float] = None


def _arg(args: dict, name: str, default: float | str) -> float | str:
    value = args.get(name, default)
    return default if value is None else value


def _build_model(variant: str, saved_args: dict, env: ToMCoordinationEnv) -> PolicyModel:
    hidden_dim = int(_arg(saved_args, "hidden_dim", 64))

    if variant == "baseline":
        return BaselinePolicy(env.obs_dim, hidden_dim, env.action_dim)

    return ToMPolicy(
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


@lru_cache(maxsize=1)
def load_runtime() -> tuple[PolicyModel, torch.device, str, str]:
    model_path = os.environ.get("MODEL_PATH", DEFAULT_MODEL_PATH)
    if not os.path.exists(model_path):
        raise FileNotFoundError(
            f"Model artifact not found at {model_path}. Run scripts/local_runner.py first or set MODEL_PATH."
        )

    payload = torch.load(model_path, map_location="cpu")
    variant = str(payload["variant"])
    saved_args = dict(payload.get("args", {}))
    env = ToMCoordinationEnv(max_steps=int(_arg(saved_args, "max_steps", 20)))
    model = _build_model(variant, saved_args, env)
    model.load_state_dict(payload["state_dict"])
    model.eval()
    device = torch.device("cpu")
    return model, device, variant, model_path


app = FastAPI(title="ToM Coordination Inference API")


@app.get("/health")
def health() -> dict:
    try:
        _, _, variant, model_path = load_runtime()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return {"status": "ok", "variant": variant, "model_path": model_path}


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest) -> PredictResponse:
    try:
        model, device, _, _ = load_runtime()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    expected_obs_dim = ToMCoordinationEnv().obs_dim
    if len(request.obs) != expected_obs_dim:
        raise HTTPException(status_code=422, detail=f"Expected obs with length {expected_obs_dim}.")

    obs_t = torch.tensor(request.obs, dtype=torch.float32, device=device).unsqueeze(0)
    if request.state is None:
        state_t = model.init_state(device=device)
    else:
        state_t = torch.tensor(np.asarray(request.state, dtype=np.float32), dtype=torch.float32, device=device).unsqueeze(0)

    with torch.no_grad():
        logits, new_state, extra = model.step(obs_t, state_t)

    response = {
        "action": int(torch.argmax(logits, dim=-1).item()),
        "state": new_state.squeeze(0).cpu().tolist(),
    }
    if "belief" in extra:
        response["belief_class"] = int(torch.argmax(extra["belief"], dim=-1).item())
    for key in ("experiment_mask", "assert_context_mask", "yield_context_mask"):
        if key in extra:
            response[key] = float(extra[key].squeeze(0).item())

    return PredictResponse(**response)
