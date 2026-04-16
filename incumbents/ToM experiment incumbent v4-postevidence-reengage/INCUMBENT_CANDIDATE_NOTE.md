# Incumbent Candidate: v4 postevidence reengage

Status: promoted to incumbent candidate after 5-seed promotion gate.

Variant summary:
- train.py-only change in `ToMPolicy._apply_decision_prior`
- tightened `late_yield` in non-narrow contexts so yielding is preferred only when the partner is actually pressing
- added `soft_reengage` to bias `PROCEED/PROBE` over `WAIT/YIELD` when evidence is out, margin is not narrow, the partner stays soft, and belief is no longer strongly assertive

Promotion gate:
- seeds: 7, 11, 17, 23, 29
- episodes per seed: 800
- output roots:
  - /Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_postevidence_reengage_seed7
  - /Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_postevidence_reengage_seed11
  - /Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_postevidence_reengage_seed17
  - /Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_postevidence_reengage_seed23
  - /Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_postevidence_reengage_seed29

Aggregate means across 5 seeds:
- baseline ToMCoordScore: 0.1109
- candidate ToMCoordScore: 0.2404
- baseline DeadlockRate: 0.10
- candidate DeadlockRate: 0.10
- baseline CollisionRate: 0.34
- candidate CollisionRate: 0.27
- baseline SuccessRate: 0.56
- candidate SuccessRate: 0.61

Decision:
- all 5/5 seeds selected `tom`
- deadlock did not worsen on any seed
- promote as incumbent candidate
