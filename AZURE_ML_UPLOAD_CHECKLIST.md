# Azure ML Upload Checklist

## Package Identity
- Project folder: /Users/stephenbeale/Projects/ToM AI Research Team
- Primary training entrypoint: train.py
- Child-job orchestrator: scripts/azure_child_job_controller.py
- Azure assets: azure/pipeline.yml, azure/infra.bicep, azure/endpoint.yml

## Scientific Guardrails (must keep)
- Primary selection metric: ToMCoordScore
- Fixed parity controls: fixed scenarios and seeds
- Keep/discard uses epsilon and deadlock threshold
- Focus changes on belief-guided policy switching, ambiguity handling, and context-sensitive adaptation

## Required Python Dependencies
- numpy>=1.24
- torch>=2.2

## Local Smoke Commands
1. python train.py --variant baseline --train-episodes 800 --seed 7
2. python train.py --variant tom --tom-experiment contextual_right_of_way_switch --train-episodes 800 --seed 7
3. python scripts/azure_child_job_controller.py --episodes 800 --time-budget-seconds 600 --seeds 7,11,19,23 --scenario-tag fixed_validation_scenarios_v1 --candidate-tom-experiment contextual_right_of_way_switch

## Azure Pipeline Parameter Mapping
- train_episodes -> train.py --train-episodes
- time_budget_seconds -> controller timeout budget
- evaluation_scenarios_tag -> controller scenario tag recording
- epsilon -> keep/discard threshold
- deadlock_delta_threshold -> auto-reject safety threshold
- candidate_tom_experiment -> train.py --tom-experiment
- candidate_tom_experiment_strength -> train.py --tom-experiment-strength
- candidate_tom_belief_uncertainty_threshold -> train.py --tom-belief-uncertainty-threshold
- candidate_tom_context_tag_threshold -> train.py --tom-context-tag-threshold

## Artifact Expectations
- logs/checkpoints/child-jobs/*.pt
- logs/child-jobs/*.jsonl
- logs/child-jobs/*.json
- logs/analysis/*.json
- logs/curves/*.csv
- logs/overnight-run-notes.md
- logs/research-timeline.md
- logs/budget-watch.md

## Pre-Upload Validation
- Verify train.py runs for both baseline and tom variants
- Verify pipeline.yml command includes all candidate_tom_* knobs
- Verify controller summary prints decision and deadlock delta
- Verify no local-only folders are included in transfer (.venv, .git, __pycache__)
