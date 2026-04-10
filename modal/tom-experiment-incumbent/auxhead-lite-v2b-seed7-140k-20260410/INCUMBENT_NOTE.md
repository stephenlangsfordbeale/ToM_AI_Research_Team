# Auxhead-Lite V2b Seed7 140k Snapshot

This archive preserves the validated `v2b` rerun for `seed7` at `140k`.

It is an archive snapshot, not a promotion of the global best single checkpoint.
`v2/seed11` remains the best validated single checkpoint overall, but this `v2b`
`seed7` rerun is scientifically worth keeping because it materially improves on the
previous `v2/seed7` continuation and cleanly beats the old `140k` `seed7` line.

## Source Run

- [`/Users/stephenbeale/Projects/ToM AI Research Team/modal/tom-140k-modal-results-v2b/seed7/seed7/target-140000/run_summary.json`](/Users/stephenbeale/Projects/ToM AI Research Team/modal/tom-140k-modal-results-v2b/seed7/seed7/target-140000/run_summary.json)
- [`/Users/stephenbeale/Projects/ToM AI Research Team/modal/tom-140k-modal-results-v2b/seed7/seed7/target-140000/analysis/choice-analysis-tom-seed7-ep140000.json`](/Users/stephenbeale/Projects/ToM AI Research Team/modal/tom-140k-modal-results-v2b/seed7/seed7/target-140000/analysis/choice-analysis-tom-seed7-ep140000.json)

## Why Kept

- `ToMCoordScore`: `0.2959216451784249 -> 0.36975128312803285` versus previous `v2/seed7`
- `SuccessRate`: `0.50 -> 0.55`
- `CollisionRate`: `0.20 -> 0.15`
- `DeadlockRate`: `0.25 -> 0.10`
- `AverageDelay`: `13.5 -> 15.15`
- `IntentionPredictionF1`: `0.7112260369887489 -> 0.7125091652002346`

Compared with old `140k/seed7`, this snapshot also improves:

- `ToMCoordScore`: `0.27929565785537974 -> 0.36975128312803285`
- `SuccessRate`: `0.30 -> 0.55`
- `DeadlockRate`: `0.20 -> 0.10`

## Interpretation

The main behavioral gain is reduced deadlock through more active use of
`probe_gently`, especially in normal-flow contexts, with less passive `yield`
behavior. The main unresolved weak family is still `assert_or_yield`.

This snapshot should be treated as:

- best validated `seed7` long-run checkpoint so far
- worth preserving for warm starts and reproducibility
- not enough on its own to replace the branch-level conclusion that `v2/seed11`
  is still the best validated single checkpoint

## Important Caveat

The paired `v2b/seed11` export is currently corrupted / duplicated: it contains a
byte-identical copy of the `seed7` artifacts rather than a distinct `seed11`
result. That is why this folder snapshots only `seed7`.

## Stored Artifacts

- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/auxhead-lite-v2b-seed7-140k-20260410/seed7/selected_model.pt`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/auxhead-lite-v2b-seed7-140k-20260410/seed7/selected_model.pt)
- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/auxhead-lite-v2b-seed7-140k-20260410/seed7/run_summary.json`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/auxhead-lite-v2b-seed7-140k-20260410/seed7/run_summary.json)
- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/auxhead-lite-v2b-seed7-140k-20260410/seed7/candidate_choice_analysis.json`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/auxhead-lite-v2b-seed7-140k-20260410/seed7/candidate_choice_analysis.json)
- [`/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/auxhead-lite-v2b-seed7-140k-20260410/seed7/learning_curve.csv`](/Users/stephenbeale/Projects/ToM_AI_Research_Team/modal/tom-experiment-incumbent/auxhead-lite-v2b-seed7-140k-20260410/seed7/learning_curve.csv)
