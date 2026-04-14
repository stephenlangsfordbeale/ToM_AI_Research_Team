---
agent: ask
model: GPT-5 (copilot)
description: "Append a standardized ToM run note block to logs/overnight-run-notes.md from provided run outputs."
---
You are given a completed run's outputs.

Task:
1. Extract the required schema fields.
2. Keep values factual; use `unknown` if absent.
3. Append one markdown block to logs/overnight-run-notes.md.

Required schema:
- run_id
- hypothesis
- exact_code_change
- files_changed
- ToMCoordScore
- relevant_secondary_metrics
- target_category (belief_modeling | stability | reward_shaping | optimization)
- robustness_assessment (robust | noisy | unclear)
- decision (keep | discard)
- short_interpretation
- next_step

Block format:
## <run_id>
- hypothesis: ...
- exact_code_change: ...
- files_changed: ...
- ToMCoordScore: ...
- relevant_secondary_metrics: ...
- target_category: ...
- robustness_assessment: ...
- decision: ...
- short_interpretation: ...
- next_step: ...

---
