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
