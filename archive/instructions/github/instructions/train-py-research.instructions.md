---
applyTo: "train.py"
description: "Use for ToM RL edits in train.py: one focused change per run, preserve evaluation integrity, and prioritize stable ToMCoordScore gains."
---
When editing train.py for ToM experiments:

Hard rules:
- One focused hypothesis and one focused change per run.
- Do not alter evaluation seeds or validation scenarios from train.py.
- Do not redefine ToMCoordScore or remove penalties.
- Prefer conservative, interpretable changes over complex rewrites.

Experiment quality checklist:
- Hypothesis is explicit and falsifiable.
- Change is localized and attributable.
- Run length and eval settings are comparable to baseline.
- Decision references ToMCoordScore first, then secondary metrics.
- Rejected ideas are documented briefly to avoid repetition.

Acceptance guidance:
- Keep only meaningful score gains or clearly better stability/robustness with no material tradeoff.
- Discard noisy wins and unstable regressions.
