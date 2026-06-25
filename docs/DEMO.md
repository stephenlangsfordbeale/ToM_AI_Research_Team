# Demo Guide

This repo supports three related CLI modes for presentations and day-to-day use.

## Three modes

| Mode | Command | What it does |
|------|---------|--------------|
| **Results** | `./tom-demo` | Local 5-seed gate summary (default) |
| | `./tom-demo --modal` | Above + Modal campaigns in `logs/modal/` and warm-starts |
| | `./tom-demo --modal-only` | Modal lanes only |
| **Test** | `./tom-test` | Runs baseline vs candidate locally, applies promotion gate, prints selection |
| **Learning** | `./tom-learn` | Opens the autoresearch-macos-tomx dashboard (OMX agent loop) |

Open the interactive menu from anywhere in the repo:

```bash
tomx-notes
# or press n within 3s when entering the repo directory
```

## Suggested 5-minute demo flow

### 1. Results Mode (~1 min)

Show that the repo already has credible, gate-checked evidence:

```bash
./tom-demo
```

Highlight:
- all five seeds **keep**
- mean ToMCoordScore improvement
- deadlock held flat
- incumbent archive at `incumbents/ToM_experiment_incumbent/auxhead-clear/`

Optional Modal context for the same family:

```bash
./tom-demo --modal
```

Highlight:
- synced campaigns under `logs/modal/`
- warm-starts at `modal/tom-experiment-incumbent/auxhead-clear/` and `auxhead-lite/`
- full map in `docs/CAMPAIGN_INDEX.md`

### 2. Test Mode (~2 min)

Prove the dormant repo still works end-to-end:

```bash
./tom-test
# default: 5-episode smoke, seed 7
```

Highlight:
- `scripts/local_runner.py` orchestrates baseline → candidate → selection
- packaged artifacts under `logs/test-run-<timestamp>/`
- `selection/selection.json` is the promotion decision record

For a heavier gate during rehearsal:

```bash
./tom-test --train-episodes 800 --seed 7 --output-root logs/demo-gate
```

### 3. Learning Mode (~2 min)

Show the human-in-the-loop agent surface:

```bash
./tom-learn
```

In the browser dashboard:
1. Select profile **ToMX Local Quality**
2. Point at agent roles in `.codex/agents/`
3. Optionally trigger **Run Smoke Then Gate** or compose a prompt referencing `program.md`

Orchestration repo (OMX policies, dashboard):

- `/Users/stephenbeale/Projects/autoresearch-macos-tomx`

Benchmark repo (train/eval/select substrate):

- `/Users/stephenbeale/Projects/ToM_AI_Research_Team`

Cross-repo contract: `autoresearch-macos-tomx/policies/cross_repo_pipeline.yaml`

## Optional follow-ups

- **Modal long-run status:** `tomx-status` or menu item 8 (auto-detects running or last-used `tom-run-*` lane)
- **Serve selected model:** see `README.md` FastAPI section
- **Modal test from CLI:** not wired yet; candidate for a future menu item if time allows

## Housekeeping notes

- **Modal logs (demo):** `logs/modal/` — single Modal folder under logs
- **Modal warm-starts:** `modal/tom-experiment-incumbent/auxhead-clear/`, `auxhead-lite/`
- **Archived long-runs:** `archive/modal/` (former repo-root `modal/` bulk)
- Tracked Azure infra lives under `azure/*.yml` and `azure/infra.bicep` only.
- `azure/conservation/` is a local azcopy backup (~3.4GB) and is gitignored.
- Campaign registry: `docs/CAMPAIGN_INDEX.md`
- Regenerate the code graph after edits: `graphify update .`
