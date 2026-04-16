# Variant 1 Incumbent Note

This folder stores the archived deadlock-micro incumbent for Variant 1 after the deadlock-specific micro-iteration in [`/Users/stephenbeale/Projects/ToM AI Research Team/train.py`](/Users/stephenbeale/Projects/ToM%20AI%20Research%20Team/train.py).

There is no git repository in [`/Users/stephenbeale/Projects/ToM AI Research Team`](/Users/stephenbeale/Projects/ToM%20AI%20Research%20Team), so this snapshot serves as the incumbent tag.

## Hypothesis

Apply a very small ToM-only train-time pressure against repeated post-evidence soft actions to reduce avoidable hesitation without changing the incumbent architecture.

## Seed 7

Source run:
[`/Users/stephenbeale/Projects/ToM AI Research Team/logs/local-run-v1-deadlockmicro/selection/selection.json`](/Users/stephenbeale/Projects/ToM%20AI%20Research%20Team/logs/local-run-v1-deadlockmicro/selection/selection.json)

- baseline `ToMCoordScore`: `-0.0598`
- candidate `ToMCoordScore`: `0.09735433575650293`
- deadlock: `0.5 -> 0.5`
- collision: `0.35 -> 0.25`
- `StrategySwitchAccuracy`: `0.85 -> 0.85`
- `AmbiguityEfficiency`: `0.041666666666666664 -> 0.10833333333333334`
- `IntentionPredictionF1`: `0.0 -> 0.4857452554035916`
- decision: `keep`

## Seed 11

Source run:
[`/Users/stephenbeale/Projects/ToM AI Research Team/logs/local-run-v1-deadlockmicro-s11/selection/selection.json`](/Users/stephenbeale/Projects/ToM%20AI%20Research%20Team/logs/local-run-v1-deadlockmicro-s11/selection/selection.json)

- baseline `ToMCoordScore`: `-0.0714`
- candidate `ToMCoordScore`: `0.0928497056538233`
- deadlock: `0.5 -> 0.5`
- collision: `0.35 -> 0.25`
- `StrategySwitchAccuracy`: `0.85 -> 0.85`
- `AmbiguityEfficiency`: `0.00416666666666667 -> 0.09583333333333333`
- `IntentionPredictionF1`: `0.0 -> 0.47999789752730926`
- decision: `keep`

## Stored Artifacts

- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent/deadlock-micro/train.py`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent/deadlock-micro/train.py)
- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent/deadlock-micro/seed7/selection.json`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent/deadlock-micro/seed7/selection.json)
- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent/deadlock-micro/seed11/selection.json`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent/deadlock-micro/seed11/selection.json)
- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent/deadlock-micro/seed7/candidate_choice_analysis.json`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent/deadlock-micro/seed7/candidate_choice_analysis.json)
- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent/deadlock-micro/seed11/candidate_choice_analysis.json`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/incumbents/ToM_experiment_incumbent/deadlock-micro/seed11/candidate_choice_analysis.json)

## Promotion Decision

Promote this deadlock-micro `train.py` as the incumbent before any further auxiliary-head comparison. It is now retained as an archived branch under `deadlock-micro/` to keep the later `auxhead-lite/` 800-episode reference visually distinct.
