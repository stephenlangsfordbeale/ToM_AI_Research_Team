# Promotion Gate Summary: postevidence-reengage

Experiment name: postevidence-reengage
Scope: train.py-only
Benchmark: Variant 1 frozen ambiguous bottleneck
Gate completed: promotion_gate
Seed set: 7, 11, 17, 23, 29
Episodes per seed: 800
Standard or deviated: standard

Patch summary:
- tightened `late_yield` in non-narrow contexts so yielding is preferred only when the partner is actually pressing
- added `soft_reengage` to bias `PROCEED/PROBE` over `WAIT/YIELD` when evidence is out, margin is not narrow, the partner stays soft, and belief is no longer strongly assertive

Output roots:
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_postevidence_reengage_seed7`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_postevidence_reengage_seed11`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_postevidence_reengage_seed17`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_postevidence_reengage_seed23`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_postevidence_reengage_seed29`

## Per-seed results

| Seed | Decision | Baseline ToMCoordScore | Candidate ToMCoordScore | Baseline Deadlock | Candidate Deadlock | Baseline Collision | Candidate Collision | Baseline Success | Candidate Success |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 7 | keep | 0.0994 | 0.2870 | 0.10 | 0.10 | 0.35 | 0.20 | 0.55 | 0.65 |
| 11 | keep | 0.0613 | 0.2796 | 0.10 | 0.10 | 0.40 | 0.20 | 0.50 | 0.65 |
| 17 | keep | 0.0994 | 0.2846 | 0.10 | 0.10 | 0.35 | 0.25 | 0.55 | 0.65 |
| 23 | keep | 0.1855 | 0.2117 | 0.10 | 0.10 | 0.25 | 0.30 | 0.65 | 0.60 |
| 29 | keep | 0.1089 | 0.2392 | 0.10 | 0.10 | 0.35 | 0.30 | 0.55 | 0.60 |

## Aggregate means

- baseline `ToMCoordScore`: `0.1109`
- candidate `ToMCoordScore`: `0.2604`
- baseline `DeadlockRate`: `0.10`
- candidate `DeadlockRate`: `0.10`
- baseline `CollisionRate`: `0.3400`
- candidate `CollisionRate`: `0.2500`
- baseline `SuccessRate`: `0.5600`
- candidate `SuccessRate`: `0.6300`
- baseline `AmbiguityEfficiency`: `0.0900`
- candidate `AmbiguityEfficiency`: `0.1700`
- baseline `IntentionPredictionF1`: `0.0000`
- candidate `IntentionPredictionF1`: `0.4385`
- baseline `StrategySwitchAccuracy`: `0.5000`
- candidate `StrategySwitchAccuracy`: `0.5200`

## Confirmed findings

- all 5/5 promotion-gate seeds selected `tom`
- mean `ToMCoordScore` improved strongly
- mean `DeadlockRate` did not worsen
- mean `CollisionRate` improved
- mean `SuccessRate` improved

## Inferred interpretation

- this branch clears the reusable promotion gate on the live packaged artifacts
- the cross-seed profile is stronger than baseline even though seed 23 remains less clean than the friendlier seeds

## Decision recommendation

- promotion gate: promote_candidate
- rationale: full 5-seed gate completed with all seeds kept, deadlock flat, and aggregate coordination metrics improved

## Provenance note

This summary is assembled directly from the packaged per-seed `selection/selection.json`
artifacts under the five output roots above. Where older branch-specific notes or tables
differ numerically, the live packaged promotion artifacts are treated as the source of truth
for this file.
