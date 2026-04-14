# Incumbent Candidate: v5 delayedtrust split

Status: promoted to incumbent candidate after a fresh 5-seed promotion gate.

Short labels:
- false_friend branch confusion
- delayed trust split

Variant summary:
- train.py-only change in post-evidence belief-to-policy routing
- keeps a narrow high-pressure `false_friend_guard`
- adds a low-pressure delayed-trust split:
  - `delayed_trust_cooperative_resolution`
  - `delayed_trust_probe`
- objective: preserve strong behavior on friendly seeds while converting the hard `false_friend`-like seed from discard to keep

Promotion gate:
- seeds: 7, 11, 17, 23, 29
- episodes per seed: 800
- fresh output roots:
  - /Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_delayedtrust_promo_seed7
  - /Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_delayedtrust_promo_seed11
  - /Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_delayedtrust_promo_seed17
  - /Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_delayedtrust_promo_seed23
  - /Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_delayedtrust_promo_seed29

Aggregate means across 5 seeds:
- baseline ToMCoordScore: 0.1109
- candidate ToMCoordScore: 0.2054
- baseline DeadlockRate: 0.10
- candidate DeadlockRate: 0.10
- baseline CollisionRate: 0.34
- candidate CollisionRate: 0.32
- baseline SuccessRate: 0.56
- candidate SuccessRate: 0.58
- baseline AmbiguityEfficiency: 0.0900
- candidate AmbiguityEfficiency: 0.1267
- baseline IntentionPredictionF1: 0.0
- candidate IntentionPredictionF1: 0.4141

Decision:
- all 5/5 seeds selected `tom`
- deadlock did not worsen on any seed
- mean ToMCoordScore improved
- mean collision improved slightly
- mean success improved slightly
- promote as incumbent candidate

## Additional long-run salvage evidence

After the canonical 5-seed `800` promotion gate above, two later `140000` long-run duplicate results were recovered from app-log exports for this same branch family.

Recovered single-seed long-run evidence:

- seed 7 salvage:
  - [pair folder](</Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v2-duplicate-v5dt-<seed7>>)
  - `ToMCoordScore`: `0.49421979601396815`
  - `CollisionRate`: `0.0`
  - `DeadlockRate`: `0.1`
  - `SuccessRate`: `0.7`
- seed 11 salvage:
  - [pair folder](</Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v2-duplicate-v5dt-20260411-031103 : App Logs>)
  - `ToMCoordScore`: `0.41869302653054163`
  - `CollisionRate`: `0.1`
  - `DeadlockRate`: `0.1`
  - `SuccessRate`: `0.6`

Combined salvage references:

- [long-run salvage pair note](/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v5dt_longrun_salvage_pair_20260411.md)
- [long-run salvage pair stats](/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v5dt_longrun_salvage_pair_stats_20260411.md)
- [seedwise means versus local800 baseline](/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v5dt_longrun_vs_local800_seedwise_means_20260411.md)

## How to interpret the long-run salvage

- These salvaged `140000` runs are strong additional evidence that the branch family remains competitive deep into training.
- The strongest recovered single-seed result is `seed7`, which reached `ToMCoordScore 0.4942` with `CollisionRate 0.0`.
- Relative to the local `800` baseline line, long-run `140000` results look materially stronger on headline score and collision reduction, especially on `seed7`.
- However, the salvaged long-run pair is still single-seed evidence and does not replace the canonical reusable 1/3/5 multiseed gate workflow.
- Treat the `800` promotion gate above as the canonical promotion evidence, and treat the salvaged `140000` runs as strong supporting branch-history and provenance evidence.

## Packaged seed snapshots for multiseed continuation

This incumbent folder now includes packaged `selected_model.pt` warm starts for:
- `seed7`
- `seed11`
- `seed23`

These are all from the same `800`-episode promoted family spec and are ready for 800 -> 140000 continuation studies.
