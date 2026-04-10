# Repo-local Codex agents

These agent definitions are scoped to this repository so they can be edited in-repo and discovered with the workspace.

Files:
- `tom-train-tuner.toml` — train.py-only tuning agent for the frozen Variant 1 benchmark
- `tom-results-judge.toml` — result aggregation and keep/discard or promotion decisions
- `tom-incumbent-curator.toml` — snapshot promoted candidates into dedicated incumbent folders

These complement the global agents in `~/.codex/agents` and are intended to make ToM-specific workflows immediately available and updateable from this repo.
