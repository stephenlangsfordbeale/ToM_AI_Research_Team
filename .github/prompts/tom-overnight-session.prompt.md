---
agent: ask
model: GPT-5 (copilot)
description: "Start a disciplined overnight ToM RL session with run budget, stop conditions, and conservative keep/discard rules focused on ToMCoordScore."
---
You are launching an overnight Theory-of-Mind reinforcement learning session in this workspace.

Load default settings from configs/overnight_profile.json unless the user overrides specific values.

Collect these inputs before executing:
- Run budget (default: 6 runs)
- Wall-clock budget (default: 8 hours)
- Research snapshot interval N (default: 4 runs)
- Acceptance margin epsilon (default: 0.02)
- Current baseline ToMCoordScore
- Current best accepted run ID and score
- Short-run command for training
- Short-run command for evaluation

Then execute this protocol:
1. Produce a one-paragraph plan for run 1 only.
2. Emit a `Resolved Run Config` block (profile defaults + explicit overrides) and append it to logs/overnight-run-notes.md before running jobs.
3. For each patch candidate, execute child jobs with same environment, same time budget, same evaluation scenarios, and unique run IDs.
4. Keep train/eval settings comparable across runs.
5. Log required metrics and patch metadata for each child job.
6. Apply epsilon keep/discard controller against baseline mean score.
7. After every run, append structured notes to logs/overnight-run-notes.md.
8. After every N runs, invoke subagent RESEARCHER and append one fresh snapshot to logs/research-timeline.md.
9. Stop at budget exhaustion or early if two consecutive strong regressions occur.

Resolved Run Config required fields:
- profile_name
- train_episodes
- time_budget_seconds
- seeds
- scenario_tag
- epsilon
- deadlock_delta_threshold
- research_snapshot_interval
- budget_snapshot_interval
- override_reason (only if any field differs from profile default)

Heavy-run mode policy:
- Always preserve machine-readable artifacts (child-job logs, run notes, research timeline, budget watch).
- Defer STORYTELLER narrative updates to checkpoint intervals unless severe paradox signals are detected.

Output sections:
- Session Setup
- Next Run Hypothesis
- Execution Log (append-only)
- Current Leaderboard
- Risks And Confidence
- Morning Deliverable Draft
