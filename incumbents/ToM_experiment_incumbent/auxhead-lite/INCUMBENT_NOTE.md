# Auxhead-Lite Incumbent Note

This snapshot stores the auxiliary-loss-only partner next-action winner from [`/Users/stephenbeale/Projects/ToM AI Research Team/train.py`](/Users/stephenbeale/Projects/ToM%20AI%20Research%20Team/train.py).
It now serves as the canonical local 800-episode reference checkpoint for later 130k and 140k warm starts.

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

## Update 16.04.26

To enable multiseed 3 and 5-gate comparisons v2 aux-lite versions of seeds 17, 23 were added to the incumbent folder with the following specs. 'seed13' has a slightly worse deadlock rate to baseline but still shows improvement in other metrics.

### Seed 13

Baseline:
- `ToMCoordScore`: `0.025250000000000022`
- `SuccessRate`: `0.25`
- `CollisionRate`: `0.25`
- `DeadlockRate`: `0.5`
- `AmbiguityEfficiency`: `0.09583333333333333`
- `IntentionPredictionF1`: `0.0`
- `AverageDelay`: `11.4`

Auxhead-lite:
- `ToMCoordScore`: `0.07816039282920942`
- `SuccessRate`: `0.25`
- `CollisionRate`: `0.2`
- `DeadlockRate`: `0.55`
- `AmbiguityEfficiency`: `0.06666666666666667`
- `IntentionPredictionF1`: `0.38507423449435324`
- `AverageDelay`: `12.2`

### Seed 17

Baseline:
- `ToMCoordScore`: `0.03685000000000008`
- `SuccessRate`: `0.25`
- `CollisionRate`: `0.25`
- `DeadlockRate`: `0.5`
- `AmbiguityEfficiency`: `0.13333333333333333`
- `IntentionPredictionF1`: `0.0`
- `AverageDelay`: `11.0`

Auxhead-lite:
- `ToMCoordScore`: `0.12682726164220032`
- `SuccessRate`: `0.3`
- `CollisionRate`: `0.2`
- `DeadlockRate`: `0.5`
- `AmbiguityEfficiency`: `0.08750000000000001`
- `IntentionPredictionF1`: `0.4719804403014307`
- `AverageDelay`: `11.8`

### Seed 23

Baseline:
- `ToMCoordScore`: `-0.07005`
- `SuccessRate`: `0.15`
- `CollisionRate`: `0.35`
- `DeadlockRate`: `0.5`
- `AmbiguityEfficiency`: `0.0`
- `IntentionPredictionF1`: `0.0`
- `AverageDelay`: `10.6`

Auxhead-lite:
- `ToMCoordScore`: `0.12485602724152015`
- `SuccessRate`: `0.3`
- `CollisionRate`: `0.2`
- `DeadlockRate`: `0.5`
- `AmbiguityEfficiency`: `0.11666666666666665`
- `IntentionPredictionF1`: `0.392185908868001`
- `AverageDelay`: `11.4`


## Stored Artifacts

- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent/auxhead-lite/train.py`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent/auxhead-lite/train.py)
- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent/auxhead-lite/seed7/selection.json`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent/auxhead-lite/seed7/selection.json)
- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent/auxhead-lite/seed11/selection.json`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent/auxhead-lite/seed11/selection.json)
- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent/auxhead-lite/replays/seed7_replays.json`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent/auxhead-lite/replays/seed7_replays.json)
- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent/auxhead-lite/replays/seed11_replays.json`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent/auxhead-lite/replays/seed11_replays.json)
