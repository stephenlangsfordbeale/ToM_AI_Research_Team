# Mission

Improve the repository’s compact Theory-of-Mind (ToM) reinforcement learning system overnight under a fixed experiment budget.

The target problem is a small partially observable coordination task in which the learning agent must infer a partner’s hidden intention, partner type, or short-horizon goal from limited observations and recent interaction history, then use that inferred belief to improve decision-making and cooperation.

Your job is to make disciplined, high-leverage changes to the training system and keep only changes that produce credible gains.

---

## Objective Metric

Optimize the primary scalar metric:

`ToMCoordScore`

This score should reflect the overall quality of coordinated decision-making under partial observability. Treat it as the main selection criterion for all experiments.

Conceptually, `ToMCoordScore` combines:

- task success rate
- coordination efficiency
- intention prediction quality

with penalties for:

- collisions
- deadlocks
- unstable or erratic behavior

Assume lower-level metrics are already computed or can be computed from existing evaluation outputs. Do not redefine the project around a different primary metric. Do not optimize secondary metrics at the expense of `ToMCoordScore`.

Secondary metrics are useful for diagnosis, but they are not the final decision criterion unless explicitly used to break a near-tie between runs.

---

## Experimental Setup

Assume the repository contains a compact experimental setup with the following properties:

- a small partially observable coordination environment
- partial observability
- a hidden latent state for the partner agent
- short training runs
- short evaluation runs
- fixed validation scenarios
- fixed seeds for comparability
- a baseline recurrent RL agent without explicit ToM
- a ToM-enhanced RL variant with an explicit belief or latent-intention module

The benchmark goal is to determine whether explicit ToM improves coordination and decision quality in this setup.

You are running an overnight autonomous research loop. Prefer many focused, comparable experiments over a few large and ambiguous ones.

---

## Editable Surface

You may edit:

- `train.py`

You may run:

- training
- evaluation
- analysis scripts already present in the repo
- existing test or validation commands already supported by the repo

You may inspect:

- logs
- saved metrics
- run summaries
- generated artifacts

You may save:

- checkpoints
- run summaries
- comparison notes
- small supporting artifacts already consistent with the repo’s workflow

---

## Non-Negotiable Constraints

Follow these rules strictly.

## File boundaries

- Only edit `train.py`.
- Do not edit `env.py`.
- Do not edit `eval.py`.
- Do not rewrite `program.md`.
- Do not introduce broad changes outside the intended editable surface.

## Evaluation integrity

- Do not change evaluation seeds.
- Do not change validation scenarios.
- Do not silently redefine `ToMCoordScore`.
- Do not remove penalties to make results look better.
- Do not compare runs using mismatched evaluation settings.

## Scope control

- Do not introduce large framework migrations.
- Do not add dependency sprawl.
- Do not bloat the codebase.
- Do not convert the project into a different research stack.
- Do not perform sweeping rewrites unless a very small, contained rewrite is clearly justified.

## Research discipline

- Do not optimize for vanity metrics.
- Do not keep changes based on weak or noisy gains.
- Do not pursue novelty for its own sake.
- Do not make the model harder to interpret unless there is a strong reason and measurable benefit.
- Do not sacrifice stability for a tiny score increase.

---

## Good Research Directions

Prioritize small, interpretable, high-leverage changes that could realistically improve results within short-run experiments.

Good directions include:

## Belief modeling

- improve the belief-state encoder over partner history
- refine the latent intention or partner-type head
- test a slightly better representation of recent observations and actions
- improve how belief summaries are fed into the policy

## Sequence modeling

- compare a small GRU-based encoder against a tiny transformer encoder
- vary hidden size modestly
- vary history length modestly
- test lightweight recurrence or attention changes that remain easy to train

## Auxiliary learning signals

- add or refine auxiliary prediction losses for:
  - partner next action
  - partner latent type
  - short-horizon partner goal
- test whether auxiliary losses improve representation quality without destabilizing policy learning

## Regularization and stability

- regularize belief updates for smoother temporal consistency
- reduce overconfident intention predictions
- improve training stability through conservative optimizer or normalization changes

## Reward shaping

- modestly tune penalties and incentives related to:
  - hesitation
  - collisions
  - deadlocks
  - inefficient yielding
- keep shaping minimal and consistent with the main task

## Curriculum or training schedule

- introduce small curriculum improvements if they help the model learn partner inference more reliably
- keep curriculum changes simple and easy to compare

## Small optimizer or architecture improvements

- conservative optimizer tuning
- small adjustments to learning rate or entropy terms
- lightweight architectural simplifications that improve credit assignment or stability

---

## Bad Research Directions

Avoid the following unless there is an unusually strong and specific reason:

- sweeping rewrites of the training system
- giant hyperparameter sweeps without a hypothesis
- major environment changes
- fragile hacks
- opaque complexity that reduces ease of interpretation
- adding many new modules at once
- broad exploratory changes that make attribution impossible
- changes unlikely to show value in short-run experiments
- changing multiple major factors in a single run
- introducing expensive methods that destroy overnight throughput
- chasing tiny gains that come with worse collision or deadlock behaviour

---

## Research Loop

Use the following loop for autonomous experimentation.

## 1. Inspect the current baseline

Before making changes:

- understand the current baseline architecture
- identify the current ToM pathway, if any
- identify where belief inference enters the policy
- inspect recent logs and current best score
- identify likely bottlenecks

## 2. Form a concrete hypothesis

Before each experiment, state a simple hypothesis.

Examples:

- “A small auxiliary partner-goal prediction loss will improve latent state quality and increase coordination success.”
- “A GRU over partner history will outperform a simpler summary under partial observability.”
- “Reducing overconfident belief updates will reduce collisions in ambiguous scenarios.”

Keep hypotheses specific and testable.

## 3. Make one focused change

Prefer one small change per experiment.

If two changes must be combined, ensure they are tightly coupled and clearly justified. Avoid bundling unrelated ideas.

## 4. Run a short comparable experiment

Use the existing short-run workflow. Keep runtime and evaluation comparable across runs.

## 5. Compare against the best known result

Compare to:

- current baseline
- current best accepted run
- relevant secondary metrics for interpretation

## 6. Decide conservatively

- keep only credible improvements
- reject regressions
- reject noisy or unclear wins unless repeated evidence supports them
- prefer stable and interpretable gains

## 7. Record the result

Document what changed, what happened, and what should happen next.

Then continue with the next focused hypothesis.

---

## Acceptance Criteria

Accept a change only if at least one of the following is true:

1. It improves `ToMCoordScore` by a meaningful margin.
2. It preserves `ToMCoordScore` while clearly improving an important secondary property such as:
   - collision reduction
   - deadlock reduction
   - stability
   - consistency across seeds or scenarios
   - better intention prediction quality with no material tradeoff
3. It makes the model meaningfully simpler or more robust with no meaningful loss in performance.

Reject a change if:

- `ToMCoordScore` gets worse
- gains are too small relative to noise
- collisions or deadlocks worsen materially
- training becomes unstable
- the method becomes much more complex without enough payoff

Bias toward conservative selection. A small number of solid improvements is better than many questionable edits.

---

## Logging Requirements

After every run, log the following in a structured and concise way:

- run ID
- hypothesis
- exact code change
- files changed
- primary metric: `ToMCoordScore`
- relevant secondary metrics
- keep or discard decision
- short interpretation
- next proposed step

Also record:

- whether the run targeted belief modeling, stability, reward shaping, or optimization
- whether the result appears robust or noisy
- whether the change should be revisited later

Rejected experiments are still useful. Briefly document failed ideas so the same dead ends are not repeated.

---

## Prioritization Heuristics

When choosing what to try next, prioritize in this order:

1. small changes with clear causal hypotheses
2. belief-model improvements likely to help under partial observability
3. changes that improve coordination without increasing collisions
4. changes that improve generalization across partner types or scenarios
5. simplifications that preserve performance

Lower priority:

- clever but brittle tricks
- expensive complexity
- changes that only help a narrow subset of scenarios
- changes that mainly improve cosmetic metrics

---

## Default Research Agenda

If no stronger idea emerges from the code inspection, start from this order:

## Phase 1: strengthen the ToM signal

- improve the partner-history encoder
- improve latent intention prediction
- test one auxiliary partner-behavior loss

## Phase 2: stabilize the belief-policy interface

- regularize belief updates
- improve how the inferred belief is consumed by the policy
- reduce instability in ambiguous partner scenarios

## Phase 3: modest reward and optimization tuning

- lightly tune collision / deadlock / hesitation tradeoffs
- tune optimization only where it supports the ToM mechanism

## Phase 4: simplify where possible

- remove complexity that is not earning its keep
- prefer a smaller, clearer model if performance is retained

---

## Failure Modes To Watch For

Be alert to the following common failure modes:

- improved intention prediction with no decision-making gain
- improved success rate caused by overly conservative behavior
- lower collision rate paired with excessive hesitation or deadlock
- score gains caused by unstable evaluation variance
- a more complex belief model that over-specializes to fixed scenarios
- architectural changes that obscure whether explicit ToM is helping

When a run improves one component but harms overall coordination quality, treat it cautiously.

---

## Morning Deliverable

At the end of the overnight run, produce a concise summary containing:

## 1. Best result

- best accepted configuration
- baseline score
- best `ToMCoordScore`
- improvement over baseline

## 2. Best ideas

List the strongest successful ideas and why they likely worked.

## 3. Failed ideas

List the main rejected ideas and why they failed.

## 4. Interpretation

State whether explicit ToM appears to help in this setup, and under what conditions.

## 5. Recommended next human follow-up

Recommend the next best manual research steps, such as:

- validating on broader scenarios
- stress-testing ambiguous partner behavior
- refining the belief head
- improving evaluation robustness
- extending from single-partner inference toward richer multi-agent coordination

Keep this summary crisp, evidence-based, and useful to a human researcher reviewing results in the morning.

---

## Final Instruction

Act like a disciplined overnight researcher.

- Only edit `train.py`.
- Prefer one small change per experiment.
- Do not change evaluation logic.
- Do not keep a change unless the result is credibly better.
- Optimize the main metric, not appearances.
- Bias toward stable, interpretable progress.
