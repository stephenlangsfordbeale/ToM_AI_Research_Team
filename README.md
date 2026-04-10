# ToM Experiment Handoff (Local-First)

Canonical repo root:

- `/Users/stephenbeale/Projects/ToM_AI_Research_Team`

Start with:

- [`docs/CANONICAL_WORKFLOW.md`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/docs/CANONICAL_WORKFLOW.md)

This repository contains a compact Theory-of-Mind reinforcement learning workflow with a working local path for train -> eval -> select, a small FastAPI inference layer, and an optional Modal wrapper after the local path works.

## Real Entrypoints
- `train.py`
  - Actual training entrypoint for both `baseline` and `tom`.
  - Also runs fixed evaluation through `eval.py`.
  - Emits:
    - `saved_checkpoint=...`
    - `learning_curve_csv=...`
    - `choice_analysis_json=...`
    - `eval_metrics={...}`
- `scripts/select_candidate.py`
  - Actual selection entrypoint.
  - Reads `metrics.json` from baseline and candidate metric directories.
  - Copies the chosen `model.pt` into the selected model directory.
- `scripts/local_runner.py`
  - New local-first orchestration entrypoint.
  - Runs baseline training, candidate training, packages the current artifact contract, and then calls `scripts/select_candidate.py`.
- `webapp/api/main.py`
  - FastAPI inference entrypoint for a selected checkpoint artifact.
- `webapp/api/modal_app.py`
  - Optional Modal ASGI wrapper around the FastAPI app.

## Artifact Contract
The active local selection path now uses the same packaged artifact shape already exercised in `logs/smoke/`:

- `<output-root>/baseline_model/model.pt`
- `<output-root>/baseline_metrics/metrics.json`
- `<output-root>/baseline_metrics/learning_curve.csv`
- `<output-root>/baseline_metrics/choice_analysis.json`
- `<output-root>/candidate_model/model.pt`
- `<output-root>/candidate_metrics/metrics.json`
- `<output-root>/candidate_metrics/learning_curve.csv`
- `<output-root>/candidate_metrics/choice_analysis.json`
- `<output-root>/selected_model/model.pt`
- `<output-root>/selection/selection.json`

Each `metrics.json` includes:
- `variant`
- `seed`
- `train_episodes`
- `max_steps`
- `eval_metrics`
- `checkpoint_source`
- `copied_model`
- `copied_curve`
- `copied_analysis`
- ToM experiment settings

## Exact Commands
Create the environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the local train/eval/select path:

```bash
python scripts/local_runner.py --train-episodes 800 --seed 7 --output-root logs/local-run
```

Run a short smoke version:

```bash
python scripts/local_runner.py --train-episodes 5 --seed 7 --output-root logs/local-smoke
```

Serve the selected model with FastAPI:

```bash
MODEL_PATH=logs/local-run/selected_model/model.pt uvicorn webapp.api.main:app --host 0.0.0.0 --port 8000
```

Smoke-check the API:

```bash
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/predict \
  -H 'content-type: application/json' \
  -d '{"obs":[0,1,1,0.5,0,0,0,0,0,0]}'
```

Optional Modal path after the local path works:

```bash
pip install modal
MODEL_PATH=logs/local-run/selected_model/model.pt modal serve webapp/api/modal_app.py
```

## Notes
- `eval.py` remains the fixed evaluation boundary.
- `scripts/azure_child_job_controller.py` and `azure/` are no longer the primary path.
- `Dockerfile.train` no longer installs Azure-specific packages.
- `Dockerfile.infer` now runs the FastAPI app directly.
# ToM_AI_Research_Team
