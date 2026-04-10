# Lightweight Auxiliary-Loss Next-Action Comparison Review

## Status

Reviewed and saved for later reference.

Current verdict from fresh 5-seed promotion test:
- **Do not promote** this aux-loss-only variant as the incumbent.

## What was being tested

A train.py-only idea aimed at improving post-evidence commitment timing **without changing the benchmark or decision-prior logic directly**.

### Recommended lightweight aux-loss-only direction

Core idea:
- keep the existing behavior auxiliary loss against the teacher's **current** action
- lightly blend in supervision toward the teacher's **next-step** action when the current state suggests the teacher is about to switch from a soft action to a decisive action

Initial version:
- after evidence release
- non-narrow margin
- current teacher action in `WAIT / YIELD / PROBE`
- next teacher action in `PROCEED / ASSERT`
- blend:
  - `0.75 * current_teacher_CE + 0.25 * next_teacher_CE`

Tightened version that was actually promotion-tested:
- same blended aux-loss idea, but the next-action comparison only activates when the current state is:
  - post-evidence
  - contested
  - partner-soft
  - urgency- or throughput-pressured
  - non-narrow margin
  - current teacher action soft, next teacher action decisive

Why this direction was considered:
- it is **aux-loss-only**
- it avoids direct edits to the benchmark, env, eval boundary, or local runner
- it tries to encourage earlier decisive switching only in the narrow class of situations where residual soft-soft stalling seemed plausible

## Fresh promotion-gate evidence

Fresh output roots used to avoid mixing evidence:
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_auxnextcmp_promo_seed7`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_auxnextcmp_promo_seed11`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_auxnextcmp_promo_seed17`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_auxnextcmp_promo_seed23`
- `/Users/stephenbeale/Projects/ToM_AI_Research_Team/logs/v3omx_auxnextcmp_promo_seed29`

## 5-seed results table

| Seed | Decision | Baseline ToMCoordScore | Candidate ToMCoordScore | Baseline Deadlock | Candidate Deadlock | Baseline Collision | Candidate Collision | Baseline Success | Candidate Success |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 7  | keep    | 0.0994 | 0.2542 | 0.10 | 0.10 | 0.35 | 0.25 | 0.55 | 0.60 |
| 11 | keep    | 0.0613 | 0.2817 | 0.10 | 0.10 | 0.40 | 0.20 | 0.50 | 0.65 |
| 17 | keep    | 0.0994 | 0.2097 | 0.10 | 0.10 | 0.35 | 0.30 | 0.55 | 0.60 |
| 23 | discard | 0.1855 | 0.1755 | 0.10 | 0.10 | 0.25 | 0.35 | 0.65 | 0.55 |
| 29 | keep    | 0.1089 | 0.2392 | 0.10 | 0.10 | 0.35 | 0.30 | 0.55 | 0.60 |
| **Mean** | **mixed (4 keep / 1 discard)** | **0.1109** | **0.2321** | **0.10** | **0.10** | **0.34** | **0.28** | **0.56** | **0.60** |

## Aggregate read

Mean metrics favored the candidate:
- baseline `ToMCoordScore`: **0.1109**
- candidate `ToMCoordScore`: **0.2321**
- baseline `DeadlockRate`: **0.10**
- candidate `DeadlockRate`: **0.10**
- baseline `CollisionRate`: **0.34**
- candidate `CollisionRate`: **0.28**
- baseline `SuccessRate`: **0.56**
- candidate `SuccessRate`: **0.60**

But the seed-level stability was not clean enough for promotion:
- seed 23 was a selector **discard**
- on seed 23, the candidate had:
  - lower `ToMCoordScore`
  - higher `CollisionRate`
  - lower `SuccessRate`
- deadlock stayed flat, which is good, but this still breaks the desired promotion robustness

## Final recommendation

Recommendation for this aux-loss-only family:
- **Keep the notes for future review**
- **Do not promote this tested variant**
- if revisited, treat it as an exploratory branch rather than the incumbent path

## Suggested future follow-up

If this family is revisited later, likely safer directions would be:
- reduce the next-action blend weight further
- gate it even more narrowly on highly specific scenario families
- compare against the current incumbent candidate under fresh 3-seed quick gates before attempting another 5-seed promotion test
