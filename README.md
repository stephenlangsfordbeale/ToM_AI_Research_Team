# ToM Experiment Handoff (Local-First)

Canonical repo root:

- `/Users/stephenbeale/Projects/ToM_AI_Research_Team`

Start with:

- [`docs/DEMO.md`](docs/DEMO.md) — three-mode demo flow (Results / Test / Learning)
- [`docs/CANONICAL_WORKFLOW.md`](docs/CANONICAL_WORKFLOW.md) — scientific workflow and artifact policy
- [`docs/CAMPAIGN_INDEX.md`](docs/CAMPAIGN_INDEX.md) — campaign registry (local, `logs/modal/`, warm-starts, archive)

This repository contains a compact Theory-of-Mind reinforcement learning workflow with a working local path for train → eval → select, a small FastAPI inference layer, and optional Modal/Azure paths after the local path works.

## Demo CLI (three modes)

| Mode | Command | Purpose |
|------|---------|---------|
| Results | `./tom-demo` | Show 5-seed promotion summary (no training) |
| Test | `./tom-test` | Local runner + promotion gate smoke or gate run |
| Learning | `./tom-learn` | OMX agent dashboard (`autoresearch-macos-tomx`) |

Interactive menu: `tomx-notes` (or press **n** when entering the repo in a terminal).

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
  - Local-first orchestration entrypoint.
  - Runs baseline training, candidate training, packages the artifact contract, and calls `scripts/select_candidate.py`.
- `webapp/api/main.py`
  - FastAPI inference entrypoint for a selected checkpoint artifact.
- `webapp/api/modal_app.py`
  - Optional Modal ASGI wrapper around the FastAPI app.

## Artifact Contract

The active local selection path uses the packaged artifact shape exercised in `logs/smoke/` and `logs/omx_full_2_seed*/`:

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

Each `metrics.json` includes variant, seed, train episodes, eval metrics, and ToM experiment settings.

Checkpoint payloads saved by `train.py` embed `checkpoint_metadata` (timestamp, git commit, seed, variant, episode progress).

## Exact Commands

Create the environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Quick demo smoke (Test Mode):

```bash
./tom-test
```

Full local train/eval/select:

```bash
python scripts/local_runner.py --train-episodes 800 --seed 7 --output-root logs/local-run
```

Show latest 5-seed promotion evidence (Results Mode):

```bash
./tom-demo
```

Serve the selected model with FastAPI:

```bash
MODEL_PATH=logs/local-run/selected_model/model.pt uvicorn webapp.api.main:app --host 0.0.0.0 --port 8000
```

Optional Modal path after the local path works:

```bash
pip install modal
MODEL_PATH=logs/local-run/selected_model/model.pt modal serve webapp/api/modal_app.py
```

## Notes

- `eval.py` remains the fixed evaluation boundary.
- `azure/conservation/` is a local backup only (gitignored); tracked Azure infra is under `azure/*.yml`.
- `scripts/azure_child_job_controller.py` and `azure/` pipeline YAML are compatibility paths, not the primary demo lane.
- Learning Mode orchestration lives in `autoresearch-macos-tomx` (`./tom-learn` launches its dashboard).
