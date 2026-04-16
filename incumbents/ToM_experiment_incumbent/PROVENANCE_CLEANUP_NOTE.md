# Incumbent Layout Note

Canonical root: [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent)

This root was renamed on 2026-04-15 from `ToM experiment incumbent` to `ToM_experiment_incumbent` to remove spaces from the canonical path and make the archived branches easier to distinguish in tooling and UI surfaces.

## Branches

- `deadlock-micro/`: archived older Variant 1 incumbent snapshot that previously lived at the root of the folder.
- `auxhead-lite/`: archived 800-episode ToM reference checkpoint family used as the local warm-start reference for later 130k and 140k runs.

## Naming Rules

- Reserve the word `baseline` for actual baseline-policy checkpoints only.
- Use `800-episode reference` when referring to `auxhead-lite/seed7/selected_model.pt` or its sibling seed snapshots.
- Treat this root as an archive of incumbent branches, not as a single current incumbent snapshot.

## Legacy Pointer

- `CURRENT_INCUMBENT.txt` is retained as a legacy pointer file because it already exists in the archive, but it should not be treated as the provenance source of truth for the folders in this root.
