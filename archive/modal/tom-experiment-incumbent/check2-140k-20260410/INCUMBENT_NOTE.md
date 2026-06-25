# Check2 140k Snapshot

This archive preserves the completed `check2` previous-V2 duplicate run at
`140k` for both `seed7` and `seed11`.

It is a snapshot of the finished branch evidence. It does not change the
top-level incumbent pointer automatically.

## Source Run

- volume: `tom-previous-v2-duplicate-check2`
- output family: `auxhead-lite`
- targets:
  - `seed7/target-140000`
  - `seed11/target-140000`

## Headline Result

This is the strongest validated two-seed branch so far.

- branch mean `ToMCoordScore`: `0.3423141581196191 -> 0.4424851581196191`
- branch mean `SuccessRate`: `0.525 -> 0.625`
- branch mean `CollisionRate`: `0.15 -> 0.075`
- branch mean `DeadlockRate`: `0.20 -> 0.10`
- branch mean `StrategySwitchAccuracy`: `0.90 -> 0.925`
- branch mean `AmbiguityEfficiency`: `0.15 -> 0.18958333333333333`
- branch mean `CoordinationEfficiency`: `0.0975 -> 0.1275`

## Seed 7

Compared with the earlier `v2` `140k` seed7 result:

- `ToMCoordScore`: `0.2959216451784249 -> 0.4653711581281331`
- `SuccessRate`: `0.50 -> 0.65`
- `CollisionRate`: `0.20 -> 0.05`
- `DeadlockRate`: `0.25 -> 0.10`
- `StrategySwitchAccuracy`: `0.90 -> 0.95`

Family-level read:

- `ambiguous_commit` improved from `1 success / 2 collisions / 1 deadlock` to `3 success / 1 timeout`
- `false_friend` improved from `2 success / 1 collision / 1 deadlock` to `3 success / 1 timeout`
- `late_disambiguation` stayed perfect at `4/4`
- `assert_or_yield` is still unresolved at `0 successes`

Interpretation:

- strongest single checkpoint so far
- major improvement comes from much cleaner success / collision / deadlock tradeoffs
- not primarily a huge jump in context-optimality, since context-sensitive regret only changed slightly

## Seed 11

Compared with the earlier `v2` `140k` seed11 result:

- `ToMCoordScore`: `0.38870678285503113 -> 0.4195991581111051`
- `SuccessRate`: `0.55 -> 0.60`
- `CollisionRate`: `0.10 -> 0.10`
- `DeadlockRate`: `0.15 -> 0.10`
- `AverageDelay`: `15.35 -> 15.2`

Family-level read:

- `late_disambiguation` improved from `3 success / 1 deadlock` to `4 success`
- `ambiguous_commit`, `false_friend`, and `no_progress_switch` were roughly stable
- `assert_or_yield` is still unresolved at `0 successes`

Interpretation:

- smaller improvement than seed7, but still a real step up
- looks more like a refinement / cleanup of an already-strong run than a behavioral rewrite

## Scientific Interpretation

Keep strongly.

Current read:

- best validated two-seed branch so far: `check2`
- best validated single checkpoint so far: `seed7 check2`
- biggest remaining weak family: `assert_or_yield`

Behaviorally, the branch looks better because it negotiates and re-engages more effectively under ambiguity, producing far fewer catastrophic outcomes, rather than because it fully solved the hardest context-sensitive family.

## Stored Artifacts

- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/check2-140k-20260410/seed7/selected_model.pt`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/check2-140k-20260410/seed7/selected_model.pt)
- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/check2-140k-20260410/seed7/run_summary.json`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/check2-140k-20260410/seed7/run_summary.json)
- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/check2-140k-20260410/seed7/candidate_choice_analysis.json`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/check2-140k-20260410/seed7/candidate_choice_analysis.json)
- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/check2-140k-20260410/seed7/learning_curve.csv`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/check2-140k-20260410/seed7/learning_curve.csv)
- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/check2-140k-20260410/seed11/selected_model.pt`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/check2-140k-20260410/seed11/selected_model.pt)
- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/check2-140k-20260410/seed11/run_summary.json`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/check2-140k-20260410/seed11/run_summary.json)
- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/check2-140k-20260410/seed11/candidate_choice_analysis.json`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/check2-140k-20260410/seed11/candidate_choice_analysis.json)
- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/check2-140k-20260410/seed11/learning_curve.csv`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/check2-140k-20260410/seed11/learning_curve.csv)
