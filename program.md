# Program

## Objective
Optimize ToMCoordScore in a compact two-agent partially observable coordination task.

## Editable Surface
- Allowed edits: train.py only.
- Fixed files: env.py and eval.py.

## Primary Metric
ToMCoordScore is the only selection metric for keeping a change.

ToMCoordScore combines:
- SuccessRate (weight 0.5)
- CoordinationEfficiency (weight 0.3)
- IntentionPredictionF1 (weight 0.2)

Apply hard penalties for collision and deadlock.

## Evaluation Integrity Rules
- Keep validation scenarios fixed.
- Keep evaluation seeds fixed.
- Do not redefine metric weights or remove penalties.
- Compare only with matching evaluation settings.

## Research Loop
1. State one testable hypothesis.
2. Make one focused change in train.py.
3. Run short train and fixed-seed evaluation.
4. Compare against baseline and current best.
5. Keep only credible improvements.

## Keep/Discard Rule
Keep a change only if:
- ToMCoordScore improves meaningfully, or
- score is flat while collisions/deadlocks/stability clearly improve.

Discard if:
- score regresses,
- gain is likely noise,
- collisions/deadlocks materially worsen,
- training becomes unstable.

## Artifact Layout (agents)

- Campaign registry: `docs/CAMPAIGN_INDEX.md`
- Local gate summary (Results Mode default): `logs/omx_full_2_5seed_summary.md`
- Synced Modal logs: `logs/modal/` only (not repo-root `modal/` bulk)
- Modal warm-starts: `modal/tom-experiment-incumbent/auxhead-clear/`, `auxhead-lite/`
- Archived Modal long-runs: `archive/modal/`
- Benchmark incumbents: `incumbents/ToM_experiment_incumbent/`
  - `auxhead-clear/` — canonical local gate snapshot
  - `../ToM_experiment_incumbent_v6-omx-full2/` — v6 omx_full_2 promoted train snapshot
  - `../ToM_experiment_incumbent_v6-baseline-f1zero/` — baseline F1zero continuation lane

New runs: use separated dimensions — platform / family / gate / campaign / seed — not legacy flat `logs/` names.
