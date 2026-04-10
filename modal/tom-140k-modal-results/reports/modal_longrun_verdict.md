# Modal Long-Run Verdict

- Old auxhead-lite incumbents: Discard as current best; keep as archive baselines.
- Seed7 130k: Keep. Strong and robust.
- Seed11 130k: Keep. Supporting replicate and safer cross-seed stopping point.
- Seed7 140k: Keep. Current best single run.
- Seed11 140k: Discard as branch default; useful negative datapoint showing overtraining risk.
- Branch overall: Keep the long-run branch, but prefer 130k as the safer cross-seed recommendation and seed7 140k as the best individual checkpoint.

## Branch Mean Metrics
### 130k
- ToMCoordScore: 0.2307
- SuccessRate: 0.3000
- DeadlockRate: 0.2250
- CollisionRate: 0.2250
- IntentionPredictionF1: 0.6825
- StrategySwitchAccuracy: 0.9250
- AmbiguityEfficiency: 0.1063
- CoordinationEfficiency: 0.0887
- AverageDelay: 13.2250

### 140k
- ToMCoordScore: 0.2404
- SuccessRate: 0.2500
- DeadlockRate: 0.1750
- CollisionRate: 0.2000
- IntentionPredictionF1: 0.7061
- StrategySwitchAccuracy: 0.9500
- AmbiguityEfficiency: 0.1083
- CoordinationEfficiency: 0.0675
- AverageDelay: 14.5750

## Key Deltas
- Seed7 ToMCoordScore: 130k 0.2356 -> 140k 0.2793 (+0.0437 (better))
- Seed11 ToMCoordScore: 130k 0.2258 -> 140k 0.2014 (-0.0244 (worse))

## Charts
- `longrun_metric_lines.svg`
- `longrun_curve_overlay.svg`
- `longrun_family_success.svg`
