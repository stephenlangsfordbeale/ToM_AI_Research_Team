# Incumbent Candidate: v6 baseline-F1zero warm starts (seed7,11,23)

Purpose:
- package baseline checkpoints (F1=0 at 800) for a controlled continuation lane
- test whether 800 -> 130k continuation from baseline initialization avoids the 140k degeneration pattern observed from the v6 ToM warm-start lane

Seeds packaged:
- seed7 from `logs/omx_full_2_seed7/baseline_model/model.pt`
- seed11 from `logs/omx_full_2_seed11/baseline_model/model.pt`
- seed23 from `logs/omx_full_2_seed23/baseline_model/model.pt`

Notes:
- these checkpoints were produced at train_episodes=800 under the canonical local benchmark
- this folder intentionally reuses `selected_model.pt` naming so existing modal continuation runners can package them uniformly
- when continued with `variant=tom`, expect `init_checkpoint_missing_keys` for ToM-only heads (normal for baseline -> tom warm start)
