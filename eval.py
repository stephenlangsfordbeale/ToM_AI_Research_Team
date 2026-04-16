from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import numpy as np

from env import (
    PARTNER_TYPES,
    PROBE,
    WAIT,
    Scenario,
    ToMCoordinationEnv,
    YIELD,
    fixed_validation_scenarios,
)


@dataclass
class EvalMetrics:
    SuccessRate: float
    CoordinationEfficiency: float
    IntentionPredictionF1: float
    StrategySwitchAccuracy: float
    AmbiguityEfficiency: float
    AverageDelay: float
    CollisionRate: float
    DeadlockRate: float
    ToMCoordScore: float


def _macro_f1(y_true: List[int], y_pred: List[int], n_classes: int) -> float:
    f1s: List[float] = []
    for cls in range(n_classes):
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == cls and p == cls)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != cls and p == cls)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == cls and p != cls)
        if tp == 0 and (fp > 0 or fn > 0):
            f1s.append(0.0)
            continue
        precision = tp / max(1, tp + fp)
        recall = tp / max(1, tp + fn)
        if precision + recall == 0:
            f1s.append(0.0)
        else:
            f1s.append(2.0 * precision * recall / (precision + recall))
    return float(np.mean(f1s)) if f1s else 0.0


def _strategy_switch_score(actions: List[int], scenario: Scenario) -> float:
    if not actions:
        return 0.0
    cautious = {WAIT, YIELD, PROBE}
    early_actions = actions[: scenario.evidence_step]
    late_actions = actions[scenario.evidence_step :]
    early_ok = True
    if scenario.require_cautious_opening:
        early_ok = any(action in cautious for action in early_actions)
    late_ok = any(action in scenario.preferred_after for action in late_actions)
    return 1.0 if early_ok and late_ok else 0.0


def evaluate_policy(
    policy_fn: Callable[[np.ndarray, Optional[np.ndarray]], Dict[str, np.ndarray]],
    env: Optional[ToMCoordinationEnv] = None,
) -> EvalMetrics:
    env = env or ToMCoordinationEnv()
    scenarios = fixed_validation_scenarios()
    ambiguous_families = {"ambiguous_commit", "false_friend", "late_disambiguation"}

    successes: List[float] = []
    collisions: List[float] = []
    deadlocks: List[float] = []
    efficiencies: List[float] = []
    delays: List[float] = []
    switch_scores: List[float] = []
    ambiguity_efficiencies: List[float] = []
    true_types: List[int] = []
    pred_types: List[int] = []

    for scenario in scenarios:
        obs = env.reset(scenario=scenario)
        state = None
        done = False
        action_history: List[int] = []

        last_info: Dict[str, float] = {
            "success": 0.0,
            "collision": 0.0,
            "deadlock": 0.0,
            "coord_eff": 0.0,
            "step": 0.0,
        }
        while not done:
            out = policy_fn(obs, state)
            action = int(out["action"])
            state = out.get("state")
            pred = out.get("belief_class")
            action_history.append(action)

            obs, _, done, info = env.step(action)
            last_info = info

            if pred is not None:
                true_types.append(int(info["partner_type"]))
                pred_types.append(int(pred))

        successes.append(float(last_info["success"]))
        collisions.append(float(last_info["collision"]))
        deadlocks.append(float(last_info["deadlock"]))
        efficiencies.append(float(last_info["coord_eff"]))
        delays.append(float(last_info["step"]))

        switch_score = _strategy_switch_score(action_history, scenario)
        switch_scores.append(switch_score)
        if scenario.family in ambiguous_families:
            ambiguity_efficiencies.append(float(last_info["success"]) * (1.0 - float(last_info["step"]) / env.max_steps))

    success_rate = float(np.mean(successes))
    coord_eff = float(np.mean(efficiencies))
    collision_rate = float(np.mean(collisions))
    deadlock_rate = float(np.mean(deadlocks))
    average_delay = float(np.mean(delays)) if delays else float(env.max_steps)
    strategy_switch_accuracy = float(np.mean(switch_scores)) if switch_scores else 0.0
    ambiguity_efficiency = float(np.mean(ambiguity_efficiencies)) if ambiguity_efficiencies else 0.0

    if pred_types:
        intention_f1 = _macro_f1(true_types, pred_types, n_classes=len(PARTNER_TYPES))
    else:
        intention_f1 = 0.0

    delay_rate = average_delay / max(1, env.max_steps)
    base = (
        0.30 * success_rate
        + 0.18 * coord_eff
        + 0.14 * intention_f1
        + 0.20 * strategy_switch_accuracy
        + 0.18 * ambiguity_efficiency
    )
    penalties = 0.42 * collision_rate + 0.24 * deadlock_rate + 0.04 * delay_rate
    tom_coord_score = base - penalties

    return EvalMetrics(
        SuccessRate=success_rate,
        CoordinationEfficiency=coord_eff,
        IntentionPredictionF1=float(intention_f1),
        StrategySwitchAccuracy=strategy_switch_accuracy,
        AmbiguityEfficiency=ambiguity_efficiency,
        AverageDelay=average_delay,
        CollisionRate=collision_rate,
        DeadlockRate=deadlock_rate,
        ToMCoordScore=float(tom_coord_score),
    )
