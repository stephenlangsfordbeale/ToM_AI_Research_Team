# Modal 130k Verdict

- Old auxhead-lite incumbents: Discard as current best; keep as archive baselines.
- Seed7 130k: Keep. Best single run in the branch.
- Seed11 130k: Keep. Supporting replicate with slightly rougher ambiguity handling.
- Branch as a whole: Keep as the current best candidate branch. Strong enough to supersede the old 800-episode auxhead-lite line, but not yet a fully clean behavioral endpoint.

## Branch Mean Metrics
- ToMCoordScore: 0.2307
- SuccessRate: 0.3000
- DeadlockRate: 0.2250
- CollisionRate: 0.2250
- IntentionPredictionF1: 0.6825
- StrategySwitchAccuracy: 0.9250
- AmbiguityEfficiency: 0.1063
- CoordinationEfficiency: 0.0887
- AverageDelay: 13.2250

## Seed7 130k vs Old Auxhead-Lite Seed7
- ToMCoordScore: 0.2356 vs 0.1688 (+0.0668 (better))
- SuccessRate: 0.3000 vs 0.3500 (-0.0500 (worse))
- DeadlockRate: 0.2000 vs 0.5000 (-0.3000 (better))
- CollisionRate: 0.2500 vs 0.1500 (+0.1000 (worse))
- IntentionPredictionF1: 0.6900 vs 0.4455 (+0.2445 (better))
- StrategySwitchAccuracy: 0.9500 vs 0.8500 (+0.1000 (better))
- AmbiguityEfficiency: 0.1208 vs 0.1250 (-0.0042 (worse))
- CoordinationEfficiency: 0.0925 vs 0.0900 (+0.0025 (better))
- AverageDelay: 13.2000 vs 12.1500 (+1.0500 (worse))

## Seed11 130k vs Old Auxhead-Lite Seed11
- ToMCoordScore: 0.2258 vs 0.1246 (+0.1012 (better))
- SuccessRate: 0.3000 vs 0.3000 (+0.0000 (better))
- DeadlockRate: 0.2500 vs 0.5000 (-0.2500 (better))
- CollisionRate: 0.2000 vs 0.2000 (+0.0000 (better))
- IntentionPredictionF1: 0.6751 vs 0.4558 (+0.2193 (better))
- StrategySwitchAccuracy: 0.9000 vs 0.8500 (+0.0500 (better))
- AmbiguityEfficiency: 0.0917 vs 0.0875 (+0.0042 (better))
- CoordinationEfficiency: 0.0850 vs 0.0700 (+0.0150 (better))
- AverageDelay: 13.2500 vs 11.8000 (+1.4500 (worse))

## Charts
- `metric_comparison.svg`
- `curve_overlay.svg`
- `family_outcome_grid.svg`
