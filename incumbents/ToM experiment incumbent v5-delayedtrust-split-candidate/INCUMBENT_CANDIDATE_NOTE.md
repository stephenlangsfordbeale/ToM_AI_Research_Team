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
