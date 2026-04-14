# Repo Primer

This primer maps the current repository as inspected from the local checkout on 2026-04-11.
It is written for research safety first: confirmed facts are separated from inference, and benchmark-sensitive areas are called out explicitly.

## Confirmed Repo Posture

- Canonical source root is this repository checkout, not similarly named folders elsewhere. `docs/CANONICAL_WORKFLOW.md` explicitly warns about path confusion.
- The active recommended workflow is local-first: `train.py` -> `eval.py` -> `scripts/select_candidate.py`, usually orchestrated by `scripts/local_runner.py`.
- Azure ML and Modal both exist, but the top-level `README.md` says they are no longer the primary path.
- No standalone `data/`, `dataset/`, or `datasets/` directory was found.
- No Python test suite was found.
- Run artifacts and scientific evidence are stored inside the repo, mainly under `logs/`, `modal/`, and `archive/`.

## Top-Level Directory Summary

### Active experiment code

- `train.py`
  Main training entrypoint for `baseline` and `tom` variants.
- `env.py`
  Benchmark environment, action space, partner types, and fixed validation scenarios.
- `eval.py`
  Metric definitions and fixed evaluation loop.
- `scripts/`
  Orchestration, cloud wrappers, long-run runners, and report generation.
- `configs/`
  Run-profile defaults, currently `overnight_profile.json`.
- `webapp/`
  Small inference API plus a placeholder frontend folder.

### Research evidence and reporting

- `logs/`
  Local smoke runs, local experiment runs, child-job summaries, curves, and narrative notes.
- `modal/`
  Long-run Modal results, incumbent archives, and generated visual/report assets.
- `notebooks/`
  Exploratory notebooks plus `variant2_visuals.py` for static report exports.
- `docs/`
  Process and research-policy documentation.

### Compatibility, deployment, and historical material

- `azure/`
  Azure ML components, pipeline definitions, environment spec, and model-registration job.
- `archive/`
  Legacy checkpoint tree retained for provenance, not the current recommended workflow.
- `Dockerfile.train`, `Dockerfile.infer`
  Container definitions for training and inference paths.

### Operational or non-canonical clutter

- `.github/`
  Prompt, agent, and instruction assets for AI-assisted research workflows.
- `.omx/`, `.codex/`
  Runtime/session tooling state.
- `.venv*`, `__pycache__/`
  Local environment caches.
- Top-level brief `program.md`
  Active concise project brief outside `docs/`.
- Archived legacy instruction briefs under `archive/instructions/top-level/`
  Historical instruction context kept for reference (for example former `# Mission.md` and Azure upload checklist).
- `# ToM autorsearch experiment/`
  A non-code top-level folder that does not appear to be part of the canonical local-first workflow.

## Key Python Modules And Their Roles

- `env.py`
  Defines the benchmark:
  - 5 actions: `WAIT`, `YIELD`, `PROBE`, `PROCEED`, `ASSERT`
  - 5 partner types
  - `Scenario` dataclass
  - `fixed_validation_scenarios()` with the fixed evaluation suite
  - `ToMCoordinationEnv`, including reward shaping, partner policy, observation construction, and termination logic

- `eval.py`
  Defines evaluation outputs:
  - `EvalMetrics` dataclass
  - macro-F1 for partner-type prediction
  - strategy-switch scoring
  - aggregate `ToMCoordScore`
  Evaluation always runs over `fixed_validation_scenarios()` from `env.py`.

- `train.py`
  Main scientific core:
  - `BaselinePolicy`: GRU policy-only baseline
  - `ToMPolicy`: GRU policy with belief head, partner-action head, decision priors, and optional experiment bolt-ons
  - `heuristic_teacher_action()`: interpretable action target used for behavior-shaping loss
  - `rollout_episode()`: on-policy rollout and auxiliary losses
  - `analyze_choice_context_outcomes()`: scenario-level and context-level analysis
  - `train()`: training loop, checkpoint saving, curve export, choice-analysis export, and final evaluation

- `scripts/local_runner.py`
  Primary orchestration script for local reproducible comparisons. It runs:
  1. baseline training
  2. candidate ToM training
  3. model selection
  It packages outputs into a stable artifact layout under a chosen log directory.

- `scripts/select_candidate.py`
  Applies the acceptance rule:
  - keep candidate only if `candidate ToMCoordScore >= baseline ToMCoordScore + epsilon`
  - auto-discard if deadlock worsens beyond `deadlock_delta_threshold`
  It also copies the chosen `model.pt` into `selected_model/`.

- `scripts/aml_train_component.py`
  Azure wrapper around `train.py` that converts stdout-emitted artifacts into Azure component outputs.

- `scripts/azure_child_job_controller.py`
  Batch controller for multi-seed short-run comparisons. It loads defaults from `configs/overnight_profile.json`, runs child jobs, records JSONL rows, and produces a controller summary.

- `scripts/modal_v2b_runner.py`, `scripts/modal_auxhead_lite_runner.py`
  Modal long-run continuations that warm-start from incumbent checkpoints and write progress and final summaries into Modal volumes.

- `scripts/modal_130k_report.py`, `scripts/modal_longrun_report.py`, `scripts/modal_140k_v2_report.py`
  Post-run reporting scripts that aggregate metrics, curves, and family outcomes into markdown, JSON, and SVG/PDF assets.

- `scripts/register_model.py`
  Azure ML model registration helper.

- `webapp/api/main.py`
  FastAPI inference layer that rebuilds the correct model class from checkpoint metadata and exposes `/health` and `/predict`.

- `webapp/api/modal_app.py`
  Thin Modal wrapper around the FastAPI app.

- `notebooks/variant2_visuals.py`
  Visualization utility for comparing Variant 2 bundles and exporting polished figures.

- `policies/__init__.py`
  Placeholder only. No modular policy package exists yet.

## Main Execution Paths

### 1. Local-first benchmark comparison

Recommended command shape:

```bash
python scripts/local_runner.py --train-episodes 800 --seed 7 --output-root logs/local-run
```

Confirmed flow:

1. `scripts/local_runner.py` loads profile defaults from `configs/overnight_profile.json`
2. it runs `train.py` once for `baseline`
3. it runs `train.py` once for `tom`
4. it parses stdout for:
   - `saved_checkpoint=...`
   - `learning_curve_csv=...`
   - `choice_analysis_json=...`
   - `eval_metrics={...}`
5. it writes packaged artifacts into sibling `baseline_*` and `candidate_*` directories
6. it calls `scripts/select_candidate.py`
7. it writes `selected_model/model.pt` and `selection/selection.json`

### 2. Direct training/evaluation loop

Command shape:

```bash
python train.py --variant baseline|tom ...
```

Confirmed behavior:

- seeds Python, NumPy, and Torch
- trains on sampled scenarios derived from the fixed scenario templates
- evaluates with `eval.py`
- emits checkpoints, curves, and choice analysis
- supports warm-starting with `--init-checkpoint`

### 3. Azure ML pipeline path

Confirmed flow from `azure/pipeline.yml`:

1. Azure component `train.yml` wraps `scripts/aml_train_component.py`
2. baseline and candidate runs execute separately
3. `azure/components/select.yml` runs `scripts/select_candidate.py`
4. optional registration is handled by `azure/register_model.yml`

### 4. Modal long-run path

Confirmed flow:

- `tom-run` and `tom-run-detached` launch `scripts/modal_v2b_runner.py`
- Modal runners package `train.py`, `env.py`, `eval.py`, and incumbent checkpoints into the remote image
- warm starts come from `modal/tom-experiment-incumbent/...`
- status is tracked with progress JSON, run status JSON, logs, and final `run_summary.json`

### 5. Inference serving path

Command shapes:

```bash
MODEL_PATH=logs/local-run/selected_model/model.pt uvicorn webapp.api.main:app --host 0.0.0.0 --port 8000
MODEL_PATH=logs/local-run/selected_model/model.pt modal serve webapp/api/modal_app.py
```

Confirmed behavior:

- the API rebuilds either `BaselinePolicy` or `ToMPolicy` from the checkpoint payload
- `/predict` returns the greedy action plus recurrent state and selected diagnostics

## Where Configs, Prompts, Datasets, And Evaluations Live

### Configs

- `configs/overnight_profile.json`
  Research-run defaults: metric priorities, parity controls, selection thresholds, cadence, and artifact policy.
- Azure deployment/config YAML lives under `azure/`.

### Prompts and AI workflow assets

- `.github/prompts/`
  (May be empty if legacy prompts were archived under `archive/instructions/github/prompts/`.)
- `.github/agents/`
  (May be empty if legacy role prompts were archived under `archive/instructions/github/agents/`.)
- `archive/instructions/github/`
  Archived GitHub Copilot instruction/prompt/agent assets retained for referral and recovery.

### Datasets

Confirmed:

- There is no separate dataset directory.
- The benchmark dataset is code-defined in `env.py::fixed_validation_scenarios()`.
- Training scenarios are sampled from those fixed templates via `sample_training_scenario()` in `train.py`.

Inferred:

- This project treats the environment definition itself as the dataset specification for the compact benchmark.
- Result artifacts in `logs/` and `modal/` act as experiment datasets for analysis and reporting.

### Evaluations

- `eval.py`
  Canonical metric definitions and evaluation loop.
- `train.py::analyze_choice_context_outcomes()`
  Richer analysis used to generate `choice_analysis.json`.
- Artifact locations:
  - `metrics.json`
  - `choice_analysis.json`
  - `selection.json`
  - report markdown/JSON/SVG/PDF under `modal/` and `docs/`

## Safe-Change Zones

These are relatively safe places to improve clarity without silently changing benchmark semantics:

- `docs/`
  Documentation and process notes.
- `.github/prompts/`, `.github/agents/`, `.github/instructions/`
  AI workflow assets, as long as they do not misstate the scientific workflow.
- `scripts/modal_*_report.py`
  Reporting and summarization, not training semantics.
- `notebooks/variant2_visuals.py`
  Visualization only.
- `webapp/frontend/`
  Placeholder area with no active frontend implementation.

## Sensitive Zones

Changes here can invalidate comparability, reproducibility, or promotion decisions:

- `env.py`
  Benchmark definition, reward logic, observation surface, and fixed validation scenarios.
- `eval.py`
  Metric semantics, especially `ToMCoordScore`.
- `train.py`
  Model behavior, auxiliary losses, checkpoint schema, and scientific analysis outputs.
- `scripts/select_candidate.py`
  Acceptance logic for promotion/selection.
- `scripts/local_runner.py` and `scripts/aml_train_component.py`
  Artifact contract and orchestration semantics.
- `modal/tom-experiment-incumbent/`
  Provenance snapshots and warm-start lineage.
- `logs/`, `modal/`, `archive/`
  Scientific evidence; edits should be deliberate and auditable.

## Fragile Or Unclear Parts

- Multiple `train.py` copies exist under `modal/tom-experiment-incumbent/`.
  At least two differ from the current root `train.py`, while one snapshot matches it exactly. This is a real source-of-truth risk.

- The benchmark “dataset” is embedded in code.
  Any edit to `fixed_validation_scenarios()` or environment semantics is effectively a benchmark revision.

- There is no automated test suite.
  The repo relies on smoke runs, metrics artifacts, and report inspection instead of unit/integration tests.

- Committed artifacts and active source live together.
  This helps provenance, but it increases the chance of accidental edits to evidence directories.

- `modal/tom-experiment-incumbent/CURRENT_INCUMBENT.txt` points to a path outside the canonical repo root.
  That matches the broader path-confusion warning in `docs/CANONICAL_WORKFLOW.md` and should be treated carefully.

- `webapp/frontend/` and `policies/` are placeholders.
  They suggest intended future structure, but not active implementation.

- Azure is present but described as non-primary.
  Future maintainers need a clearer support statement so they know whether Azure paths are production-ready, compatibility-only, or historical.

## Validation Steps For Future Code Edits

Use the lightest validation that still protects experiment validity.

### If you change docs or prompts only

1. Re-read the edited markdown for factual accuracy against the repo.
2. Check that referenced paths actually exist.

### If you change `train.py`, `env.py`, `eval.py`, or selection/orchestration logic

1. Run a smoke comparison:

```bash
python scripts/local_runner.py --train-episodes 5 --seed 7 --output-root logs/local-smoke-validation
```

2. Confirm the artifact contract exists:
   - `baseline_model/model.pt`
   - `baseline_metrics/metrics.json`
   - `candidate_model/model.pt`
   - `candidate_metrics/metrics.json`
   - `selected_model/model.pt`
   - `selection/selection.json`

3. Inspect `metrics.json` and `selection.json` to verify:
   - evaluation still runs
   - expected metric keys are present
   - selection logic still produces a decision

4. If you touched `env.py` or `eval.py`, explicitly document that comparability may have changed.

### If you change inference code

1. Produce a fresh selected model with the smoke run above.
2. Start the API or import the runtime loader.
3. Validate `/health` and one `/predict` request.

### If you change Modal or Azure paths

1. First prove the local-first path still works.
2. Then validate the specific wrapper or YAML against the current artifact contract.
3. Do not claim scientific success from progress files alone; use final summaries and analysis artifacts.
