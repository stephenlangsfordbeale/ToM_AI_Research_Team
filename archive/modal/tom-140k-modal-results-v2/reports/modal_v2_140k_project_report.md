# Theory of Mind Contextual Right-of-Way Project Report

## Hypothesis

A policy with an explicit Theory of Mind component and stronger context-sensitive training conditions should outperform a plain recurrent baseline on the fixed Variant 2 benchmark: Contextual Right-of-Way Negotiation. The expected mechanism is not generic reward gain. It is belief-guided social adaptation. The agent should infer what sort of partner it is facing, combine that belief with urgency, norm, safety margin, and timeout pressure, and then choose a different action when the same partner belief appears under a different context.

## Method

The project used a fixed Variant 2 benchmark in which two agents approach a contested right-of-way decision under partial observability. The environment, evaluation logic, scenario families, context tags, and action semantics were held fixed during quality passes. The benchmark was designed to test socially contingent action selection rather than simple latent-style prediction.

The main development line again used an auxhead-lite architecture. This retained the lightweight Theory of Mind structure while updating the training signal inside `train.py` to push harder on safety-first behaviour, urgency override, opportunism under norm shift, and social-misread recovery. The benchmark selection metric remained `ToMCoordScore`, which combines success, coordination efficiency, intention prediction, switch accuracy, ambiguity efficiency, collision rate, deadlock rate, and delay.

This Variant 2 branch was evaluated in two main stages. First, local `800`-episode runs were executed on seeds 7 and 11 to verify that the new training conditions still beat baseline before committing to long runs. Second, both seeds were warm-started from the `800`-episode auxhead-lite checkpoints and continued to `140k` total episodes on Modal. For historical context, the older non-v2 `140k` long-run branch was also kept as a reference point.

## Ethics

This was a low-risk simulation study. No human subjects, personal data, or clinical claims were involved. The main ethical concern is still overclaiming social intelligence from narrow benchmark success. Results should therefore be framed as evidence of improved context-sensitive coordination in one controlled task, not as evidence of general human-like mindreading.

## Results

The local `800`-episode Variant 2 runs were already stronger than baseline on both seeds. Seed 7 reached `ToMCoordScore 0.2506` and seed 11 reached `0.2826`, giving a branch mean of `0.2666`.

The new `140k` Variant 2 Modal runs improved further. Seed 7 reached `ToMCoordScore 0.2959` and seed 11 reached `0.3887`. The new branch mean was `0.3423`.

Compared with the older `140k` long-run branch, the new Variant 2 branch improved its mean `ToMCoordScore` from `0.2404` to `0.3423`. Mean success rate increased from `0.250` to `0.525` and mean collision rate fell from `0.200` to `0.150`. The biggest single change was seed 11, which improved from `0.2014` on the old `140k` branch to `0.3887` on the new Variant 2 branch.

Family-level outcomes were mixed but interpretable. `late_disambiguation` remained the strongest family and improved further at the long horizon. `no_progress_switch` remained broadly stable. `false_friend` improved, especially on seed 11. `ambiguous_commit` remained mixed, particularly on seed 7. `assert_or_yield` remained the clearest failure pocket and is still the best candidate for the next targeted improvement pass.

## Analysis and Discussion

The central hypothesis is supported. The updated Theory of Mind line did not just improve a diagnostic belief variable. It also produced materially better branch-level coordination at the `140k` horizon than the earlier long-run line, especially through higher success, fewer collisions, and better intention prediction.

The most important scientific result is that the old cross-seed long-run weakness no longer looks dominant in the same way. In the earlier long-run branch, seed 11 degraded at `140k` and acted as an overtraining warning. In the new Variant 2 branch, seed 11 became the strongest checkpoint in the comparison. That is a meaningful sign that the updated training conditions improved robustness under the contextual right-of-way framing.

However, the comparison against the local `800`-episode Variant 2 runs shows a real tradeoff. The `140k` runs improved `ToMCoordScore`, intention prediction, and switch accuracy, but they did not cleanly dominate on every behavioural dimension. Relative to the local `800` branch, the `140k` runs were slower on average and showed more deadlock. This suggests that longer training refined belief quality and policy consistency, but also made the policies somewhat more deliberate and in some settings less sharp.

The best current interpretation is therefore two-part. The new Variant 2 `140k` branch is the strongest long-run result so far and clearly supersedes the older `140k` branch. At the same time, `assert_or_yield` remains unresolved and the local `800` runs still show a kind of short-horizon decisiveness that the long-run branch does not fully preserve.

## Appendix

### Technology Used

Python, PyTorch, NumPy, Modal, resumable checkpointing, CSV/JSON artifact logging, SVG-based report generation, and notebook-based inspection. The project kept the benchmark environment and evaluation code fixed while iterating only on the training surface.

### Layman’s Summary

We trained an AI agent on a small social coordination problem where it has to decide when to wait, when to go, and when to change its mind depending on both the other agent’s behaviour and the situation around them. The new long-run Version 2 results were clearly better than the older long-run branch, and this time the second seed did not collapse. That is encouraging. But the agent is still not equally good in every situation. It became better at some hard ambiguity-heavy cases, while still struggling in a family where it has to judge whether to push ahead or yield under pressure.

The best single run in this branch is `seed11 new140` with `ToMCoordScore 0.3887`.
