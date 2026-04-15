# Auxhead-Lite Incumbent Note

This snapshot stores the auxiliary-loss-only partner next-action winner from [`/Users/stephenbeale/Projects/ToM AI Research Team/train.py`](/Users/stephenbeale/Projects/ToM%20AI%20Research%20Team/train.py).

The change relative to deadlock-micro is narrow:

- add a partner next-action head to the ToM model
- train it as an auxiliary loss only
- do not feed that head back into the policy head

## Direct Comparison To Deadlock-Micro

### Seed 7

Deadlock-micro:
- `ToMCoordScore`: `0.09735433575650293`
- `SuccessRate`: `0.25`
- `CollisionRate`: `0.25`
- `DeadlockRate`: `0.5`
- `AmbiguityEfficiency`: `0.10833333333333334`
- `IntentionPredictionF1`: `0.4857452554035916`
- `AverageDelay`: `11.15`

Auxhead-lite:
- `ToMCoordScore`: `0.16876715685160154`
- `SuccessRate`: `0.35`
- `CollisionRate`: `0.15`
- `DeadlockRate`: `0.5`
- `AmbiguityEfficiency`: `0.125`
- `IntentionPredictionF1`: `0.4454796917971535`
- `AverageDelay`: `12.15`

### Seed 11

Deadlock-micro:
- `ToMCoordScore`: `0.0928497056538233`
- `SuccessRate`: `0.25`
- `CollisionRate`: `0.25`
- `DeadlockRate`: `0.5`
- `AmbiguityEfficiency`: `0.09583333333333333`
- `IntentionPredictionF1`: `0.47999789752730926`
- `AverageDelay`: `11.2`

Auxhead-lite:
- `ToMCoordScore`: `0.1245635607987759`
- `SuccessRate`: `0.3`
- `CollisionRate`: `0.2`
- `DeadlockRate`: `0.5`
- `AmbiguityEfficiency`: `0.08750000000000001`
- `IntentionPredictionF1`: `0.455811148562685`
- `AverageDelay`: `11.8`

## Interpretation

Auxhead-lite beats deadlock-micro on the primary score on both seeds while keeping deadlock flat and lowering collisions on both seeds. The tradeoff is slightly worse latent-style F1 and slightly longer delay.

The improvement appears to come mostly from better resolution in `late_disambiguation` and `no_progress_switch`, not from broad gains in every family.

## Stored Artifacts

- [`/Users/stephenbeale/Projects/ToM experiment incumbent/auxhead-lite/train.py`](/Users/stephenbeale/Projects/ToM%20experiment%20incumbent/auxhead-lite/train.py)
- [`/Users/stephenbeale/Projects/ToM experiment incumbent/auxhead-lite/seed7/selection.json`](/Users/stephenbeale/Projects/ToM%20experiment%20incumbent/auxhead-lite/seed7/selection.json)
- [`/Users/stephenbeale/Projects/ToM experiment incumbent/auxhead-lite/seed11/selection.json`](/Users/stephenbeale/Projects/ToM%20experiment%20incumbent/auxhead-lite/seed11/selection.json)
- [`/Users/stephenbeale/Projects/ToM experiment incumbent/auxhead-lite/replays/seed7_replays.json`](/Users/stephenbeale/Projects/ToM%20experiment%20incumbent/auxhead-lite/replays/seed7_replays.json)
- [`/Users/stephenbeale/Projects/ToM experiment incumbent/auxhead-lite/replays/seed11_replays.json`](/Users/stephenbeale/Projects/ToM%20experiment%20incumbent/auxhead-lite/replays/seed11_replays.json)
