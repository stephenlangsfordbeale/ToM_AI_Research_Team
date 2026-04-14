# Incumbent Candidate: v6 omx_full_2 promotion

Status: promoted to incumbent candidate after a clean fresh 5-seed promotion gate.

Assignation:
- **v6**

Short labels:
- omx_full_2 promoted family
- contextual right-of-way switch (train.py-only)
- caveat: urgency proceed regression vs bottleneck proceed gain

Variant summary:
- train.py-based ToM branch (`tom_experiment=contextual_right_of_way_switch`)
- 5-seed promotion gate passed all policy checks
- clear headline gains on ToMCoordScore / collision / success / F1
- known context caveat retained explicitly for next branch planning

Promotion gate:
- seeds: 7, 11, 17, 23, 29
- episodes per seed: 800
- fresh output roots:
  - `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/omx_full_2_seed7`
  - `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/omx_full_2_seed11`
  - `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/omx_full_2_seed17`
  - `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/omx_full_2_seed23`
  - `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/omx_full_2_seed29`

Aggregate means across 5 seeds:
- baseline ToMCoordScore: 0.1109
- candidate ToMCoordScore: 0.2265
- baseline DeadlockRate: 0.10
- candidate DeadlockRate: 0.10
- baseline CollisionRate: 0.34
- candidate CollisionRate: 0.29
- baseline SuccessRate: 0.56
- candidate SuccessRate: 0.61
- baseline AmbiguityEfficiency: 0.0900
- candidate AmbiguityEfficiency: 0.1433
- baseline IntentionPredictionF1: 0.0
- candidate IntentionPredictionF1: 0.4148

Decision:
- all 5/5 seeds selected `tom`
- deadlock did not worsen on any seed
- mean ToMCoordScore improved materially
- mean collision improved
- mean success improved
- promote as incumbent candidate (**v6**)

Notable caveat:
- `high_urgency|proceed` worsened (`bad-rate 0.2821 -> 0.3774`, `success 0.7179 -> 0.6226`)
- `high_conflict_bottleneck|proceed` improved strongly (`bad-rate 0.3103 -> 0.0769`, `success 0.6897 -> 0.9231`)

Interpretation:
- The branch is promotable and strong globally, but follow-up should explicitly preserve bottleneck proceed gains while reducing urgency proceed over-shoot.

References:
- `logs/omx_full_2_5seed_summary.md`
- `logs/omx_full_2_5seed_summary.json`
- `logs/omx_full_2_promotion_note.md`
- `logs/omx_full_3_next_step_experiment_plan.md`

Seed snapshots bundled here:
- `seed7`
- `seed11` (strongest promoted seed in this gate)
- `seed23`
