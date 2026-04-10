# Modal 140k V2 Verdict

- New v2 branch: Keep as the current best 140k branch. It materially outperforms the old 140k line on score and especially rescues seed11.
- Seed7 new140: Keep. Modest score gain over the old 140k seed7 run, with better overall success but still some ambiguity-family roughness.
- Seed11 new140: Keep strongly. Major improvement over the old 140k seed11 run and the best individual checkpoint in this comparison.
- Vs local800: Treat the new 140k branch as a long-run refinement, not a pure dominance result. Score, belief quality, and switch accuracy improve, but some families trade away short-run sharpness for slower, more deliberate behavior.
- Remaining risk: assert_or_yield is still the weakest family. The branch is better overall, but that family remains the clearest unfinished behavior gap.

## Best Individual Checkpoint
- `seed11 new140` with `ToMCoordScore=0.3887`

## Branch Mean Metrics
### local800
- ToMCoordScore: 0.2666
- SuccessRate: 0.6500
- DeadlockRate: 0.1000
- CollisionRate: 0.2500
- IntentionPredictionF1: 0.4382
- StrategySwitchAccuracy: 0.5000
- AmbiguityEfficiency: 0.1875
- CoordinationEfficiency: 0.1663
- AverageDelay: 12.2000

### old140
- ToMCoordScore: 0.2404
- SuccessRate: 0.2500
- DeadlockRate: 0.1750
- CollisionRate: 0.2000
- IntentionPredictionF1: 0.7061
- StrategySwitchAccuracy: 0.9500
- AmbiguityEfficiency: 0.1083
- CoordinationEfficiency: 0.0675
- AverageDelay: 14.5750

### new140
- ToMCoordScore: 0.3423
- SuccessRate: 0.5250
- DeadlockRate: 0.2000
- CollisionRate: 0.1500
- IntentionPredictionF1: 0.7151
- StrategySwitchAccuracy: 0.9000
- AmbiguityEfficiency: 0.1500
- CoordinationEfficiency: 0.0975
- AverageDelay: 14.4250

## Key Deltas
- Branch mean ToMCoordScore: old140 0.2404 -> new140 0.3423 (+0.1020 (better))
- Seed7 ToMCoordScore: old140 0.2793 -> new140 0.2959 (+0.0166 (better))
- Seed11 ToMCoordScore: old140 0.2014 -> new140 0.3887 (+0.1873 (better))
- Seed7 ToMCoordScore: local800 0.2506 -> new140 0.2959 (+0.0453 (better))
- Seed11 ToMCoordScore: local800 0.2826 -> new140 0.3887 (+0.1061 (better))

## Charts
- `v2_tom_score_lines.svg`
- `v2_curve_overlay.svg`
- `v2_family_success.svg`
