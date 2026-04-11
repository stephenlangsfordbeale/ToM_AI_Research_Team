# Promotion Gate Summary: delayedtrust-split

Experiment name: delayedtrust-split
Scope: train.py-only
Benchmark: Variant 1 frozen ambiguous bottleneck
Gate completed: promotion_gate
Seed set: 7, 11, 17, 23, 29
Episodes per seed: 800
Standard or deviated: standard

Patch summary:
- kept the narrow high-pressure `false_friend_guard`
- added a low-pressure delayed-trust split for post-evidence, partner-soft, non-narrow cases
- `delayed_trust_cooperative_resolution` allows `PROCEED` when cooperative belief clearly clears opportunistic belief
- `delayed_trust_probe` favors `PROBE` when opportunistic-soft remains competitive

Output roots:
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_delayedtrust_promo_seed7`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_delayedtrust_promo_seed11`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_delayedtrust_promo_seed17`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_delayedtrust_promo_seed23`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_delayedtrust_promo_seed29`

## Per-seed results

| Seed | Decision | Baseline ToMCoordScore | Candidate ToMCoordScore | Baseline Deadlock | Candidate Deadlock | Baseline Collision | Candidate Collision | Baseline Success | Candidate Success |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 7 | keep | 0.0994 | 0.1783 | 0.10 | 0.10 | 0.35 | 0.35 | 0.55 | 0.55 |
| 11 | keep | 0.0613 | 0.1858 | 0.10 | 0.10 | 0.40 | 0.35 | 0.50 | 0.55 |
| 17 | keep | 0.0994 | 0.2335 | 0.10 | 0.10 | 0.35 | 0.30 | 0.55 | 0.60 |
| 23 | keep | 0.1855 | 0.2285 | 0.10 | 0.10 | 0.25 | 0.30 | 0.65 | 0.60 |
| 29 | keep | 0.1089 | 0.2012 | 0.10 | 0.10 | 0.35 | 0.30 | 0.55 | 0.60 |

## Aggregate means

- baseline `ToMCoordScore`: `0.1109`
- candidate `ToMCoordScore`: `0.2054`
- baseline `DeadlockRate`: `0.10`
- candidate `DeadlockRate`: `0.10`
- baseline `CollisionRate`: `0.3400`
- candidate `CollisionRate`: `0.3200`
- baseline `SuccessRate`: `0.5600`
- candidate `SuccessRate`: `0.5800`
- baseline `AmbiguityEfficiency`: `0.0900`
- candidate `AmbiguityEfficiency`: `0.1267`
- baseline `IntentionPredictionF1`: `0.0000`
- candidate `IntentionPredictionF1`: `0.4141`
- baseline `StrategySwitchAccuracy`: `0.5000`
- candidate `StrategySwitchAccuracy`: `0.5400`

## Confirmed findings

- all 5/5 promotion-gate seeds selected `tom`
- mean `ToMCoordScore` improved
- mean `DeadlockRate` did not worsen
- mean `CollisionRate` improved slightly
- mean `SuccessRate` improved slightly

## Inferred interpretation

- this branch trades some easy-seed peakiness for a more stable cross-seed profile
- the hard-seed veto has been reduced enough that the full declared promotion gate stays acceptable across all five seeds

## Decision recommendation

- promotion gate: promote_candidate
- rationale: full 5-seed gate completed with all seeds kept, deadlock flat, and aggregate coordination metrics improved

## Provenance note

This summary is assembled directly from the packaged per-seed `selection/selection.json`
artifacts under the five output roots above. Branch-specific incumbent notes and result
tables remain useful supporting evidence, but the packaged promotion artifacts are treated
as the source of truth for this file.
