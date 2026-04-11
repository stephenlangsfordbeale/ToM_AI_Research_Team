# Quick Gate Summary: postevidence-reengage

Experiment name: postevidence-reengage
Scope: train.py-only
Benchmark: Variant 1 frozen ambiguous bottleneck
Gate completed: quick_gate
Seed set: 7, 11, 17
Episodes per seed: 800
Standard or deviated: standard

Patch summary:
- tightened `late_yield` in non-narrow contexts so yielding is preferred only when the partner is actually pressing
- added `soft_reengage` to bias `PROCEED/PROBE` over `WAIT/YIELD` when evidence is out, margin is not narrow, the partner stays soft, and belief is no longer strongly assertive

Output roots:
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_postevidence_reengage_seed7`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_postevidence_reengage_seed11`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_postevidence_reengage_seed17`

## Per-seed results

| Seed | Decision | Baseline ToMCoordScore | Candidate ToMCoordScore | Baseline Deadlock | Candidate Deadlock | Baseline Collision | Candidate Collision | Baseline Success | Candidate Success |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 7 | keep | 0.0994 | 0.2870 | 0.10 | 0.10 | 0.35 | 0.20 | 0.55 | 0.65 |
| 11 | keep | 0.0613 | 0.2796 | 0.10 | 0.10 | 0.40 | 0.20 | 0.50 | 0.65 |
| 17 | keep | 0.0994 | 0.2846 | 0.10 | 0.10 | 0.35 | 0.25 | 0.55 | 0.65 |

## Aggregate means

- baseline `ToMCoordScore`: `0.0867`
- candidate `ToMCoordScore`: `0.2837`
- baseline `DeadlockRate`: `0.10`
- candidate `DeadlockRate`: `0.10`
- baseline `CollisionRate`: `0.3667`
- candidate `CollisionRate`: `0.2167`
- baseline `SuccessRate`: `0.5333`
- candidate `SuccessRate`: `0.6500`
- baseline `AmbiguityEfficiency`: `0.0708`
- candidate `AmbiguityEfficiency`: `0.1889`
- baseline `IntentionPredictionF1`: `0.0000`
- candidate `IntentionPredictionF1`: `0.4387`
- baseline `StrategySwitchAccuracy`: `0.5000`
- candidate `StrategySwitchAccuracy`: `0.5167`

## Confirmed findings

- all 3/3 quick-gate seeds selected `tom`
- mean `ToMCoordScore` improved strongly
- mean `DeadlockRate` did not worsen
- mean `CollisionRate` improved
- mean `SuccessRate` improved

## Inferred interpretation

- this patch family appears strong enough to justify spending a fresh 5-seed promotion gate
- the gain does not appear to depend on a single favorable seed within the declared 3-seed quick gate

## Decision recommendation

- quick gate: keep
- next step: run the declared 5-seed promotion gate on `7, 11, 17, 23, 29`

## Provenance note

This summary is assembled directly from the packaged per-seed `selection/selection.json`
artifacts under the three output roots above. Where branch-specific incumbent notes or
later narrative summaries differ, the live packaged quick-gate artifacts are treated as
the source of truth for this file.
