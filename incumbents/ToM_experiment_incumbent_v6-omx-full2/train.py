from __future__ import annotations

import argparse
import csv
from dataclasses import asdict
import json
import os
import random
from typing import Dict, List, Optional, Protocol, Tuple

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from env import (
    ACTION_NAMES,
    ASSERT,
    PARTNER_TYPES,
    PROBE,
    PROCEED,
    Scenario,
    WAIT,
    YIELD,
    ToMCoordinationEnv,
    fixed_validation_scenarios,
)
from eval import EvalMetrics, evaluate_policy


TOM_EXPERIMENTS = ("none", "belief_uncertainty_wait", "contextual_right_of_way_switch")


class BaselinePolicy(nn.Module):
    def __init__(self, obs_dim: int, hidden_dim: int, action_dim: int) -> None:
        super().__init__()
        self.hidden_dim = hidden_dim
        self.gru = nn.GRUCell(obs_dim, hidden_dim)
        self.policy_head = nn.Linear(hidden_dim, action_dim)

    def init_state(self, batch_size: int = 1, device: torch.device | None = None) -> torch.Tensor:
        device = device or torch.device("cpu")
        return torch.zeros(batch_size, self.hidden_dim, device=device)

    def step(self, obs: torch.Tensor, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, Dict[str, torch.Tensor]]:
        new_state = self.gru(obs, state)
        logits = self.policy_head(new_state)
        extra: Dict[str, torch.Tensor] = {}
        return logits, new_state, extra


class ToMPolicy(nn.Module):
    def __init__(
        self,
        obs_dim: int,
        hidden_dim: int,
        action_dim: int,
        n_partner_types: int,
        proceed_safety_penalty: float,
        conflict_dist_threshold: float,
        bottleneck_dist_threshold: float,
        tom_experiment: str,
        tom_experiment_strength: float,
        tom_belief_uncertainty_threshold: float,
        tom_context_tag_threshold: float,
    ) -> None:
        super().__init__()
        self.hidden_dim = hidden_dim
        self.n_partner_types = n_partner_types
        self.gru = nn.GRUCell(obs_dim, hidden_dim)
        self.belief_head = nn.Linear(hidden_dim, n_partner_types)
        self.partner_action_head = nn.Linear(hidden_dim, action_dim)
        self.policy_head = nn.Linear(hidden_dim + n_partner_types, action_dim)
        self.proceed_safety_penalty = proceed_safety_penalty
        self.conflict_dist_threshold = conflict_dist_threshold
        self.bottleneck_dist_threshold = bottleneck_dist_threshold
        self.tom_experiment = tom_experiment
        self.tom_experiment_strength = tom_experiment_strength
        self.tom_belief_uncertainty_threshold = tom_belief_uncertainty_threshold
        self.tom_context_tag_threshold = tom_context_tag_threshold

    def _apply_decision_prior(
        self,
        obs: torch.Tensor,
        logits: torch.Tensor,
        belief: torch.Tensor,
    ) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        logits = logits.clone()
        diagnostics: Dict[str, torch.Tensor] = {}

        conflict_close = torch.abs(obs[:, 2]) <= max(self.conflict_dist_threshold, 0.60)
        bottleneck_close = torch.abs(obs[:, 3]) <= max(self.bottleneck_dist_threshold, 0.45)
        negotiation_window = conflict_close | bottleneck_close

        urgency_high = obs[:, 5] >= self.tom_context_tag_threshold
        throughput_bias = obs[:, 6] >= self.tom_context_tag_threshold
        margin_narrow = obs[:, 7] >= self.tom_context_tag_threshold
        evidence_released = obs[:, 8] >= self.tom_context_tag_threshold
        partner_pressing = obs[:, 4] >= 0.72
        partner_soft = ~partner_pressing

        assertive_belief = belief[:, 1] + belief[:, 3] + 0.75 * belief[:, 4]
        cooperative_belief = belief[:, 0] + 0.60 * belief[:, 2]
        opportunistic_belief = belief[:, 3] + 0.85 * belief[:, 4]
        soft_partner_window = negotiation_window & evidence_released & partner_soft & (~margin_narrow)

        early_caution = (negotiation_window & (~evidence_released)).to(logits.dtype)
        late_yield = (
            negotiation_window
            & evidence_released
            & (assertive_belief > cooperative_belief + 0.14)
            & (margin_narrow | (partner_pressing & (~throughput_bias) & (assertive_belief > cooperative_belief + 0.22)))
        ).to(logits.dtype)
        late_commit = (
            negotiation_window
            & evidence_released
            & (
                (cooperative_belief + 0.06 >= assertive_belief)
                | (urgency_high & throughput_bias & (~margin_narrow))
                | ((~margin_narrow) & partner_soft & (cooperative_belief > assertive_belief + 0.04))
            )
        ).to(logits.dtype)
        false_friend_guard = (
            soft_partner_window
            & (urgency_high | throughput_bias)
            & (opportunistic_belief >= self.tom_belief_uncertainty_threshold - 0.03)
            & (cooperative_belief <= opportunistic_belief + 0.04)
        ).to(logits.dtype)
        delayed_trust_cooperative_resolution = (
            soft_partner_window
            & (~urgency_high)
            & (~throughput_bias)
            & (cooperative_belief > assertive_belief + 0.08)
            & (cooperative_belief > opportunistic_belief + 0.18)
        ).to(logits.dtype)
        delayed_trust_probe = (
            soft_partner_window
            & (~urgency_high)
            & (~throughput_bias)
            & (opportunistic_belief >= cooperative_belief - 0.02)
        ).to(logits.dtype)
        soft_reengage = (
            negotiation_window
            & evidence_released
            & partner_soft
            & (~margin_narrow)
            & (cooperative_belief + 0.05 >= assertive_belief)
            & (delayed_trust_cooperative_resolution < 0.5)
            & (delayed_trust_probe < 0.5)
        ).to(logits.dtype)

        logits[:, ASSERT] = logits[:, ASSERT] - 0.90 * early_caution
        logits[:, PROCEED] = logits[:, PROCEED] - 0.55 * early_caution
        logits[:, WAIT] = logits[:, WAIT] + 0.40 * early_caution
        logits[:, PROBE] = logits[:, PROBE] + 0.70 * early_caution

        logits[:, YIELD] = logits[:, YIELD] + 0.60 * late_yield
        logits[:, WAIT] = logits[:, WAIT] + 0.20 * late_yield
        logits[:, ASSERT] = logits[:, ASSERT] - 0.55 * late_yield
        logits[:, PROCEED] = logits[:, PROCEED] - 0.35 * late_yield

        logits[:, PROCEED] = logits[:, PROCEED] + 0.82 * late_commit
        logits[:, ASSERT] = logits[:, ASSERT] + 0.50 * late_commit * (urgency_high & throughput_bias).to(logits.dtype)
        logits[:, WAIT] = logits[:, WAIT] - 0.42 * late_commit
        logits[:, YIELD] = logits[:, YIELD] - 0.22 * late_commit

        logits[:, PROCEED] = logits[:, PROCEED] + 0.55 * soft_reengage
        logits[:, PROBE] = logits[:, PROBE] + 0.22 * soft_reengage
        logits[:, WAIT] = logits[:, WAIT] - 0.30 * soft_reengage
        logits[:, YIELD] = logits[:, YIELD] - 0.45 * soft_reengage

        logits[:, ASSERT] = logits[:, ASSERT] - 0.26 * false_friend_guard
        logits[:, PROCEED] = logits[:, PROCEED] - 0.40 * false_friend_guard
        logits[:, WAIT] = logits[:, WAIT] + 0.06 * false_friend_guard
        logits[:, PROBE] = logits[:, PROBE] + 0.34 * false_friend_guard

        logits[:, PROCEED] = logits[:, PROCEED] + 0.26 * delayed_trust_cooperative_resolution
        logits[:, PROBE] = logits[:, PROBE] - 0.16 * delayed_trust_cooperative_resolution
        logits[:, WAIT] = logits[:, WAIT] - 0.06 * delayed_trust_cooperative_resolution

        logits[:, ASSERT] = logits[:, ASSERT] - 0.12 * delayed_trust_probe
        logits[:, PROCEED] = logits[:, PROCEED] - 0.22 * delayed_trust_probe
        logits[:, WAIT] = logits[:, WAIT] + 0.04 * delayed_trust_probe
        logits[:, PROBE] = logits[:, PROBE] + 0.20 * delayed_trust_probe

        diagnostics["early_caution_mask"] = early_caution
        diagnostics["late_yield_mask"] = late_yield
        diagnostics["late_commit_mask"] = late_commit
        diagnostics["soft_reengage_mask"] = soft_reengage
        diagnostics["false_friend_guard_mask"] = false_friend_guard
        diagnostics["delayed_trust_cooperative_resolution_mask"] = delayed_trust_cooperative_resolution
        diagnostics["delayed_trust_probe_mask"] = delayed_trust_probe
        return logits, diagnostics

    def _apply_experiment_bolt_on(
        self,
        obs: torch.Tensor,
        logits: torch.Tensor,
        belief: torch.Tensor,
    ) -> Tuple[torch.Tensor, Dict[str, torch.Tensor]]:
        diagnostics: Dict[str, torch.Tensor] = {}

        if self.tom_experiment == "none":
            return logits, diagnostics

        if self.tom_experiment == "belief_uncertainty_wait":
            logits = logits.clone()
            belief_entropy = -(belief * torch.log(belief.clamp_min(1e-8))).sum(dim=-1)
            max_entropy = float(np.log(max(2, self.n_partner_types)))
            normalized_entropy = belief_entropy / max_entropy

            uncertain = normalized_entropy >= self.tom_belief_uncertainty_threshold
            conflict_near = torch.abs(obs[:, 2]) <= self.conflict_dist_threshold
            bottleneck_near = torch.abs(obs[:, 3]) <= self.bottleneck_dist_threshold
            mask = (uncertain & conflict_near & bottleneck_near).to(logits.dtype)

            logits[:, ASSERT] = logits[:, ASSERT] - self.tom_experiment_strength * mask
            logits[:, PROCEED] = logits[:, PROCEED] - 0.75 * self.tom_experiment_strength * mask
            logits[:, WAIT] = logits[:, WAIT] + 0.5 * self.tom_experiment_strength * mask
            logits[:, PROBE] = logits[:, PROBE] + 0.35 * self.tom_experiment_strength * mask

            diagnostics["belief_entropy"] = normalized_entropy
            diagnostics["experiment_mask"] = mask
            return logits, diagnostics

        if self.tom_experiment == "contextual_right_of_way_switch":
            logits = logits.clone()

            # Approximate ambiguous pressure from assertive/opportunistic/deceptive partner types.
            assertive_belief = belief[:, 1] + 0.5 * belief[:, 3] + 0.75 * belief[:, 4]
            cooperative_belief = belief[:, 0] + 0.65 * belief[:, 2]
            opportunistic_belief = belief[:, 3] + 0.85 * belief[:, 4]
            assertive_mask = assertive_belief >= self.tom_belief_uncertainty_threshold

            conflict_near = torch.abs(obs[:, 2]) <= self.conflict_dist_threshold
            bottleneck_near = torch.abs(obs[:, 3]) <= self.bottleneck_dist_threshold
            contested = conflict_near & bottleneck_near

            urgency_high = obs[:, 5] >= self.tom_context_tag_threshold
            throughput_bias = obs[:, 6] >= self.tom_context_tag_threshold
            margin_narrow = obs[:, 7] >= self.tom_context_tag_threshold
            evidence_released = obs[:, 8] >= self.tom_context_tag_threshold
            partner_pressing = obs[:, 4] >= 0.72
            partner_retreating = obs[:, 4] <= 0.28
            partner_soft = ~partner_pressing

            # Same assertive belief should trigger different strategies under different context tags.
            assert_context = (assertive_mask & contested & evidence_released & urgency_high & throughput_bias).to(
                logits.dtype
            )
            yield_context = (assertive_mask & contested & evidence_released & ((~throughput_bias) | margin_narrow)).to(
                logits.dtype
            )

            logits[:, ASSERT] = logits[:, ASSERT] + self.tom_experiment_strength * assert_context
            logits[:, PROCEED] = logits[:, PROCEED] + 0.5 * self.tom_experiment_strength * assert_context
            logits[:, WAIT] = logits[:, WAIT] - 0.5 * self.tom_experiment_strength * assert_context

            logits[:, ASSERT] = logits[:, ASSERT] - self.tom_experiment_strength * yield_context
            logits[:, PROCEED] = logits[:, PROCEED] - 0.70 * self.tom_experiment_strength * yield_context
            logits[:, YIELD] = logits[:, YIELD] + 0.48 * self.tom_experiment_strength * yield_context
            logits[:, WAIT] = logits[:, WAIT] + 0.20 * self.tom_experiment_strength * yield_context
            logits[:, PROBE] = logits[:, PROBE] + 0.24 * self.tom_experiment_strength * yield_context

            safety_first = (
                contested
                & evidence_released
                & margin_narrow
                & (partner_pressing | (cooperative_belief >= assertive_belief - 0.06))
            ).to(logits.dtype)
            urgency_override = (
                contested
                & evidence_released
                & urgency_high
                & throughput_bias
                & (~margin_narrow)
                & partner_soft
                & (cooperative_belief + 0.08 >= assertive_belief)
            ).to(logits.dtype)
            urgent_probe_proceed_bridge = (
                contested
                & evidence_released
                & urgency_high
                & throughput_bias
                & (~margin_narrow)
                & partner_soft
                & (cooperative_belief + 0.06 >= assertive_belief)
                & (opportunistic_belief <= assertive_belief + 0.10)
            ).to(logits.dtype)
            opportunism_assert = (
                contested
                & evidence_released
                & (opportunistic_belief >= self.tom_belief_uncertainty_threshold - 0.05)
                & throughput_bias
                & (~margin_narrow)
                & partner_soft
            ).to(logits.dtype)
            opportunism_yield = (
                contested
                & evidence_released
                & (opportunistic_belief >= self.tom_belief_uncertainty_threshold - 0.05)
                & (margin_narrow | (~throughput_bias) | partner_pressing)
            ).to(logits.dtype)
            recovery_yield = (
                contested
                & evidence_released
                & partner_pressing
                & (cooperative_belief > assertive_belief + 0.08)
            ).to(logits.dtype)
            recovery_assert = (
                contested
                & evidence_released
                & partner_retreating
                & (assertive_belief > cooperative_belief + 0.08)
                & urgency_high
                & throughput_bias
                & (~margin_narrow)
            ).to(logits.dtype)

            logits[:, ASSERT] = logits[:, ASSERT] - 0.65 * self.tom_experiment_strength * safety_first
            logits[:, PROCEED] = logits[:, PROCEED] - 0.95 * self.tom_experiment_strength * safety_first
            logits[:, WAIT] = logits[:, WAIT] + 0.42 * self.tom_experiment_strength * safety_first
            logits[:, PROBE] = logits[:, PROBE] + 0.92 * self.tom_experiment_strength * safety_first
            logits[:, YIELD] = logits[:, YIELD] + 0.10 * self.tom_experiment_strength * safety_first

            logits[:, ASSERT] = logits[:, ASSERT] + 0.50 * self.tom_experiment_strength * urgency_override
            logits[:, PROCEED] = logits[:, PROCEED] + 0.85 * self.tom_experiment_strength * urgency_override
            logits[:, WAIT] = logits[:, WAIT] - 0.65 * self.tom_experiment_strength * urgency_override
            logits[:, YIELD] = logits[:, YIELD] - 0.45 * self.tom_experiment_strength * urgency_override

            logits[:, ASSERT] = logits[:, ASSERT] - 0.62 * self.tom_experiment_strength * urgent_probe_proceed_bridge
            logits[:, PROCEED] = logits[:, PROCEED] + 0.42 * self.tom_experiment_strength * urgent_probe_proceed_bridge
            logits[:, WAIT] = logits[:, WAIT] - 0.28 * self.tom_experiment_strength * urgent_probe_proceed_bridge
            logits[:, YIELD] = logits[:, YIELD] - 0.12 * self.tom_experiment_strength * urgent_probe_proceed_bridge
            logits[:, PROBE] = logits[:, PROBE] + 0.58 * self.tom_experiment_strength * urgent_probe_proceed_bridge

            logits[:, ASSERT] = logits[:, ASSERT] + 0.75 * self.tom_experiment_strength * opportunism_assert
            logits[:, PROCEED] = logits[:, PROCEED] + 0.35 * self.tom_experiment_strength * opportunism_assert
            logits[:, WAIT] = logits[:, WAIT] - 0.45 * self.tom_experiment_strength * opportunism_assert

            logits[:, ASSERT] = logits[:, ASSERT] - 0.70 * self.tom_experiment_strength * opportunism_yield
            logits[:, PROCEED] = logits[:, PROCEED] - 0.55 * self.tom_experiment_strength * opportunism_yield
            logits[:, YIELD] = logits[:, YIELD] + 0.65 * self.tom_experiment_strength * opportunism_yield
            logits[:, PROBE] = logits[:, PROBE] + 0.40 * self.tom_experiment_strength * opportunism_yield

            logits[:, ASSERT] = logits[:, ASSERT] - 0.55 * self.tom_experiment_strength * recovery_yield
            logits[:, PROCEED] = logits[:, PROCEED] - 0.25 * self.tom_experiment_strength * recovery_yield
            logits[:, YIELD] = logits[:, YIELD] + 0.60 * self.tom_experiment_strength * recovery_yield
            logits[:, PROBE] = logits[:, PROBE] + 0.30 * self.tom_experiment_strength * recovery_yield

            logits[:, ASSERT] = logits[:, ASSERT] + 0.58 * self.tom_experiment_strength * recovery_assert
            logits[:, PROCEED] = logits[:, PROCEED] + 0.82 * self.tom_experiment_strength * recovery_assert
            logits[:, WAIT] = logits[:, WAIT] - 0.55 * self.tom_experiment_strength * recovery_assert
            logits[:, YIELD] = logits[:, YIELD] - 0.30 * self.tom_experiment_strength * recovery_assert

            diagnostics["assertive_belief"] = assertive_belief
            diagnostics["assert_context_mask"] = assert_context
            diagnostics["yield_context_mask"] = yield_context
            diagnostics["safety_first_mask"] = safety_first
            diagnostics["urgency_override_mask"] = urgency_override
            diagnostics["urgent_probe_proceed_bridge_mask"] = urgent_probe_proceed_bridge
            diagnostics["opportunism_assert_mask"] = opportunism_assert
            diagnostics["opportunism_yield_mask"] = opportunism_yield
            diagnostics["recovery_yield_mask"] = recovery_yield
            diagnostics["recovery_assert_mask"] = recovery_assert
            return logits, diagnostics

        raise ValueError(f"unknown tom experiment: {self.tom_experiment}")

    def init_state(self, batch_size: int = 1, device: torch.device | None = None) -> torch.Tensor:
        device = device or torch.device("cpu")
        return torch.zeros(batch_size, self.hidden_dim, device=device)

    def step(self, obs: torch.Tensor, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, Dict[str, torch.Tensor]]:
        new_state = self.gru(obs, state)
        belief_logits = self.belief_head(new_state)
        partner_action_logits = self.partner_action_head(new_state)
        belief = F.softmax(belief_logits, dim=-1)
        logits = self.policy_head(torch.cat([new_state, belief], dim=-1))

        # ToM safety bias: reduce over-aggressive proceed decisions near ambiguous bottleneck conflicts.
        conflict_near = torch.abs(obs[:, 2]) <= self.conflict_dist_threshold
        bottleneck_near = torch.abs(obs[:, 3]) <= self.bottleneck_dist_threshold
        risk_mask = (conflict_near & bottleneck_near).to(logits.dtype)
        logits = logits.clone()
        logits[:, ASSERT] = logits[:, ASSERT] - self.proceed_safety_penalty * risk_mask
        logits[:, PROCEED] = logits[:, PROCEED] - 0.5 * self.proceed_safety_penalty * risk_mask

        logits, prior_diag = self._apply_decision_prior(obs=obs, logits=logits, belief=belief)
        logits, experiment_diag = self._apply_experiment_bolt_on(obs=obs, logits=logits, belief=belief)

        extra = {"belief_logits": belief_logits, "belief": belief, "partner_action_logits": partner_action_logits}
        extra.update(prior_diag)
        extra.update(experiment_diag)
        return logits, new_state, extra


class PolicyModel(Protocol):
    def init_state(self, batch_size: int = 1, device: torch.device | None = None) -> torch.Tensor:
        ...

    def step(self, obs: torch.Tensor, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, Dict[str, torch.Tensor]]:
        ...


def discount_returns(rewards: List[float], gamma: float) -> torch.Tensor:
    out: List[float] = []
    running = 0.0
    for reward in reversed(rewards):
        running = reward + gamma * running
        out.append(running)
    out.reverse()
    returns = torch.tensor(out, dtype=torch.float32)
    returns = (returns - returns.mean()) / (returns.std() + 1e-8)
    return returns


def sample_training_scenario(rng: random.Random, episode_index: int) -> Scenario:
    templates = fixed_validation_scenarios()
    template = templates[episode_index % len(templates)]
    seed = rng.randint(10_000, 999_999)
    return Scenario(
        seed=seed,
        partner_type=template.partner_type,
        family=template.family,
        urgency=template.urgency,
        norm=template.norm,
        margin=template.margin,
        evidence_step=template.evidence_step,
        preferred_after=template.preferred_after,
        require_cautious_opening=template.require_cautious_opening,
    )


def heuristic_teacher_action(
    obs: np.ndarray,
    scenario: Scenario,
    consecutive_soft_postevidence: int = 0,
) -> int:
    contested = abs(float(obs[2])) <= 0.35 and abs(float(obs[3])) <= 0.35
    urgency_high = float(obs[5]) >= 0.5
    throughput_bias = float(obs[6]) >= 0.5
    margin_narrow = float(obs[7]) >= 0.5
    evidence_released = float(obs[8]) >= 0.5
    last_partner_action = int(np.clip(np.rint(float(obs[4]) * (len(ACTION_NAMES) - 1)), 0, len(ACTION_NAMES) - 1))
    partner_pressing = last_partner_action in (PROCEED, ASSERT)
    partner_soft = last_partner_action in (WAIT, YIELD, PROBE)
    pressure_high = urgency_high or throughput_bias
    switch_pressure = evidence_released and (
        consecutive_soft_postevidence >= (2 if pressure_high else 3)
        or (pressure_high and contested and partner_soft)
    )

    assertive_like = scenario.partner_type in (1, 3, 4)
    cautious_like = scenario.partner_type in (0, 2)
    opportunistic_like = scenario.partner_type in (3, 4)

    if not evidence_released:
        if contested:
            return WAIT if (margin_narrow or not throughput_bias) else PROBE
        return PROBE

    if scenario.family == "late_disambiguation" and contested and not margin_narrow and partner_soft:
        return PROBE if not urgency_high else PROCEED

    if scenario.family in {"false_friend", "late_disambiguation"} and switch_pressure:
        if partner_soft and throughput_bias and not margin_narrow:
            return ASSERT if cautious_like else PROCEED
        if margin_narrow:
            return PROBE if partner_pressing else WAIT

    if scenario.family == "no_progress_switch":
        if switch_pressure and throughput_bias:
            return ASSERT if not margin_narrow else PROBE
        if margin_narrow:
            return PROBE if partner_pressing else WAIT
        if throughput_bias and urgency_high and partner_soft:
            return ASSERT
        return ASSERT if throughput_bias else PROCEED

    if opportunistic_like:
        if switch_pressure and throughput_bias and not margin_narrow:
            return ASSERT
        if margin_narrow:
            return PROBE if partner_pressing else WAIT
        if scenario.norm == "courteous":
            return YIELD if partner_pressing else PROBE
        if urgency_high and throughput_bias:
            return ASSERT if partner_soft else PROCEED
        return PROBE

    if assertive_like:
        if margin_narrow and contested:
            if switch_pressure and pressure_high and partner_soft:
                return PROBE
            return YIELD if partner_pressing else WAIT
        if throughput_bias and urgency_high and not margin_narrow and partner_soft:
            return ASSERT
        if switch_pressure and throughput_bias and not margin_narrow:
            return PROCEED
        return YIELD if (margin_narrow or scenario.norm == "courteous") else WAIT

    if cautious_like:
        if margin_narrow and contested:
            return PROBE
        if contested and (pressure_high or switch_pressure):
            if switch_pressure and throughput_bias and not margin_narrow and partner_soft:
                return ASSERT
            return PROCEED if not margin_narrow else PROBE
        return PROCEED

    return PROBE


def rollout_episode(
    env: ToMCoordinationEnv,
    model: PolicyModel,
    device: torch.device,
    deterministic: bool,
    scenario: Scenario,
) -> Tuple[
    List[torch.Tensor],
    List[float],
    List[torch.Tensor],
    List[torch.Tensor],
    List[torch.Tensor],
    List[torch.Tensor],
]:
    obs = env.reset(scenario=scenario)
    state = model.init_state(device=device)
    tom_deadlock_shaping = isinstance(model, ToMPolicy)

    log_probs: List[torch.Tensor] = []
    rewards: List[float] = []
    entropies: List[torch.Tensor] = []
    belief_aux_losses: List[torch.Tensor] = []
    partner_action_aux_losses: List[torch.Tensor] = []
    behavior_aux_losses: List[torch.Tensor] = []
    prev_belief_probs: Optional[torch.Tensor] = None
    consecutive_soft_postevidence = 0
    consecutive_pressure_soft = 0

    done = False
    while not done:
        obs_pre = obs.copy()
        teacher_soft_streak = consecutive_soft_postevidence
        obs_t = torch.tensor(obs, dtype=torch.float32, device=device).unsqueeze(0)
        logits, state, extra = model.step(obs_t, state)
        dist = torch.distributions.Categorical(logits=logits)

        if deterministic:
            action_t = torch.argmax(logits, dim=-1)
        else:
            action_t = dist.sample()

        log_prob = dist.log_prob(action_t)
        entropy = dist.entropy()

        next_obs, reward, done, info = env.step(int(action_t.item()))
        action = int(action_t.item())

        if tom_deadlock_shaping:
            evidence_released = float(obs_pre[8]) >= 0.5
            urgency_high = float(obs_pre[5]) >= 0.5
            throughput_bias = float(obs_pre[6]) >= 0.5
            margin_narrow = float(obs_pre[7]) >= 0.5
            contested = abs(float(obs_pre[2])) <= 0.35 and abs(float(obs_pre[3])) <= 0.35
            partner_pressing = float(obs_pre[4]) >= 0.72
            partner_soft = not partner_pressing
            soft_action = action in (WAIT, YIELD, PROBE)
            decisive_action = action in (PROCEED, ASSERT)

            if evidence_released:
                if soft_action:
                    consecutive_soft_postevidence += 1
                    consecutive_pressure_soft = consecutive_pressure_soft + 1 if (urgency_high or throughput_bias) else 0
                    if consecutive_soft_postevidence >= 3 and (throughput_bias or not margin_narrow):
                        reward -= 0.012 if action == PROBE else 0.02
                    if (urgency_high or throughput_bias) and consecutive_pressure_soft >= 2:
                        reward -= 0.012 if action == PROBE else 0.024
                    if action == YIELD and (urgency_high or throughput_bias) and partner_soft:
                        reward -= 0.010
                else:
                    if consecutive_soft_postevidence >= 2 and not margin_narrow:
                        reward += 0.015 + (0.01 if throughput_bias else 0.0)
                    if (urgency_high or throughput_bias) and consecutive_pressure_soft >= 2:
                        reward += 0.012 + (0.006 if action == ASSERT else 0.0)
                    consecutive_soft_postevidence = 0
                    consecutive_pressure_soft = 0
            else:
                consecutive_soft_postevidence = 0
                consecutive_pressure_soft = 0

            if contested and evidence_released:
                if margin_narrow and decisive_action:
                    reward -= 0.025 if partner_pressing else 0.015
                if decisive_action and throughput_bias and urgency_high and not margin_narrow and not partner_pressing:
                    reward += 0.02
                if soft_action and urgency_high and throughput_bias and not margin_narrow and consecutive_soft_postevidence >= 2:
                    reward -= 0.015
                if action == PROBE and margin_narrow and partner_pressing:
                    reward += 0.012
                if scenario.family in {"false_friend", "late_disambiguation", "no_progress_switch"}:
                    if soft_action and partner_soft and consecutive_soft_postevidence >= 2:
                        reward -= 0.008
                    if decisive_action and (urgency_high or throughput_bias) and partner_soft:
                        reward += 0.008 if action == ASSERT else 0.004

        log_probs.append(log_prob.squeeze(0))
        entropies.append(entropy.squeeze(0))
        rewards.append(reward)

        teacher_action = heuristic_teacher_action(
            obs_pre,
            scenario,
            consecutive_soft_postevidence=teacher_soft_streak,
        )
        teacher_target = torch.tensor([teacher_action], dtype=torch.long, device=device)
        behavior_loss = F.cross_entropy(logits, teacher_target)
        if tom_deadlock_shaping:
            evidence_released = float(obs_pre[8]) >= 0.5
            urgency_high = float(obs_pre[5]) >= 0.5
            throughput_bias = float(obs_pre[6]) >= 0.5
            margin_narrow = float(obs_pre[7]) >= 0.5
            contested = abs(float(obs_pre[2])) <= 0.35 and abs(float(obs_pre[3])) <= 0.35
            partner_soft = float(obs_pre[4]) < 0.72
            next_teacher_action = heuristic_teacher_action(
                next_obs,
                scenario,
                consecutive_soft_postevidence=consecutive_soft_postevidence,
            )
            anticipates_decisive_shift = (
                evidence_released
                and contested
                and partner_soft
                and (urgency_high or throughput_bias)
                and (not margin_narrow)
                and teacher_action in (WAIT, YIELD, PROBE)
                and next_teacher_action in (PROCEED, ASSERT)
            )
            if anticipates_decisive_shift:
                next_teacher_target = torch.tensor([next_teacher_action], dtype=torch.long, device=device)
                next_action_compare_loss = F.cross_entropy(logits, next_teacher_target)
                behavior_loss = 0.75 * behavior_loss + 0.25 * next_action_compare_loss
        behavior_aux_losses.append(behavior_loss)

        if "belief_logits" in extra:
            target = torch.tensor([int(info["partner_type"])], dtype=torch.long, device=device)
            belief_loss = F.cross_entropy(extra["belief_logits"], target)
            evidence_released = float(obs_pre[8]) >= 0.5
            contested = abs(float(obs_pre[2])) <= 0.35 and abs(float(obs_pre[3])) <= 0.35
            belief_probs = F.softmax(extra["belief_logits"], dim=-1)
            belief_entropy = -(belief_probs * torch.log(belief_probs.clamp_min(1e-8))).sum(dim=-1)
            max_entropy = float(np.log(max(2, belief_probs.shape[-1])))
            normalized_belief_entropy = belief_entropy / max_entropy
            uncertain_belief = bool((normalized_belief_entropy >= 0.55).item())
            if tom_deadlock_shaping and prev_belief_probs is not None and not evidence_released and contested and uncertain_belief:
                belief_stability_compare = F.kl_div(
                    F.log_softmax(extra["belief_logits"], dim=-1),
                    prev_belief_probs.detach(),
                    reduction="batchmean",
                )
                belief_loss = 0.90 * belief_loss + 0.10 * belief_stability_compare
            belief_aux_losses.append(belief_loss)
            prev_belief_probs = belief_probs.detach()
        if "partner_action_logits" in extra:
            partner_action_target = torch.tensor([int(info["partner_action"])], dtype=torch.long, device=device)
            partner_action_aux_losses.append(F.cross_entropy(extra["partner_action_logits"], partner_action_target))

        obs = next_obs

    return log_probs, rewards, entropies, belief_aux_losses, partner_action_aux_losses, behavior_aux_losses


def build_policy_runner(model: PolicyModel, device: torch.device):
    def _runner(obs: np.ndarray, state_np: Optional[np.ndarray]) -> Dict[str, np.ndarray]:
        obs_t = torch.tensor(obs, dtype=torch.float32, device=device).unsqueeze(0)
        if state_np is None:
            state_t = model.init_state(device=device)
        else:
            state_t = torch.tensor(state_np, dtype=torch.float32, device=device)

        with torch.no_grad():
            logits, new_state, extra = model.step(obs_t, state_t)
            action = int(torch.argmax(logits, dim=-1).item())
            out: Dict[str, np.ndarray] = {"action": np.array(action, dtype=np.int64), "state": new_state.cpu().numpy()}
            if "belief" in extra:
                out["belief_class"] = np.array(int(torch.argmax(extra["belief"], dim=-1).item()), dtype=np.int64)
                out["belief_confidence"] = np.array(float(torch.max(extra["belief"], dim=-1).values.item()), dtype=np.float32)
            for key in (
                "experiment_mask",
                "assert_context_mask",
                "yield_context_mask",
                "safety_first_mask",
                "urgency_override_mask",
                "urgent_probe_proceed_bridge_mask",
                "opportunism_assert_mask",
                "opportunism_yield_mask",
                "recovery_yield_mask",
                "recovery_assert_mask",
                "early_caution_mask",
                "false_friend_guard_mask",
                "delayed_trust_cooperative_resolution_mask",
                "delayed_trust_probe_mask",
                "soft_reengage_mask",
                "late_yield_mask",
                "late_commit_mask",
            ):
                if key in extra:
                    out[key] = np.array(float(extra[key].squeeze(0).item()), dtype=np.float32)
            return out

    return _runner


def analyze_choice_context_outcomes(
    model: PolicyModel,
    device: torch.device,
    max_steps: int,
    conflict_dist_threshold: float,
    bottleneck_dist_threshold: float,
    urgency_threshold: float,
) -> Dict[str, object]:
    env = ToMCoordinationEnv(max_steps=max_steps)
    scenarios = fixed_validation_scenarios()
    policy = build_policy_runner(model, device)

    step_counts: Dict[str, int] = {}
    step_outcomes: Dict[str, Dict[str, int]] = {}
    terminal_outcomes: Dict[str, Dict[str, int]] = {}
    partner_style: Dict[str, Dict[str, int]] = {}
    experiment_mask_counts: Dict[str, int] = {}
    scenario_summaries: List[Dict[str, object]] = []

    def _inc_count(d: Dict[str, int], key: str) -> None:
        d[key] = d.get(key, 0) + 1

    cautious_actions = {WAIT, YIELD, PROBE}
    decisive_actions = {PROCEED, ASSERT}
    context_regrets: List[float] = []

    def _context_sensitive_regret(actions: List[int], scenario: Scenario) -> float:
        if not actions:
            return 1.0

        preferred_cautious = all(action in cautious_actions for action in scenario.preferred_after)
        preferred_decisive = all(action in decisive_actions for action in scenario.preferred_after)
        regrets: List[float] = []
        for idx, action in enumerate(actions):
            if idx < scenario.evidence_step:
                regrets.append(0.35 if scenario.require_cautious_opening and action in decisive_actions else 0.0)
                continue

            if action in scenario.preferred_after:
                regrets.append(0.0)
                continue

            if preferred_decisive and action in cautious_actions:
                pressure_penalty = 0.55 if (scenario.urgency == "high" or scenario.norm == "throughput_biased") else 0.35
                regrets.append(pressure_penalty if scenario.margin != "narrow" else pressure_penalty - 0.10)
                continue

            if preferred_cautious and action in decisive_actions:
                safety_penalty = 0.80 if (scenario.margin == "narrow" or scenario.norm == "courteous") else 0.65
                regrets.append(safety_penalty)
                continue

            regrets.append(0.45)

        return float(sum(regrets) / max(1, len(regrets)))

    for scenario in scenarios:
        obs = env.reset(scenario=scenario)
        state: Optional[np.ndarray] = None
        done = False
        chosen_keys: List[str] = []
        final_info: Optional[Dict[str, float]] = None
        action_history: List[int] = []
        belief_history: List[Optional[int]] = []
        belief_confidences: List[float] = []

        while not done:
            obs_pre = obs.copy()
            out = policy(obs_pre, state)
            action = int(out["action"])
            state = out.get("state")
            action_history.append(action)
            belief_history.append(int(out["belief_class"])) if "belief_class" in out else belief_history.append(None)
            belief_confidences.append(float(out.get("belief_confidence", 0.0)))

            for mask_key in (
                "experiment_mask",
                "assert_context_mask",
                "yield_context_mask",
                "safety_first_mask",
                "urgency_override_mask",
                "urgent_probe_proceed_bridge_mask",
                "opportunism_assert_mask",
                "opportunism_yield_mask",
                "recovery_yield_mask",
                "recovery_assert_mask",
                "early_caution_mask",
                "false_friend_guard_mask",
                "delayed_trust_cooperative_resolution_mask",
                "delayed_trust_probe_mask",
                "soft_reengage_mask",
                "late_yield_mask",
                "late_commit_mask",
            ):
                if float(out.get(mask_key, 0.0)) > 0.5:
                    experiment_mask_counts[mask_key] = experiment_mask_counts.get(mask_key, 0) + 1

            conflict_near = abs(float(obs_pre[2])) <= conflict_dist_threshold
            bottleneck_near = abs(float(obs_pre[3])) <= bottleneck_dist_threshold
            urgent = float(obs_pre[5]) >= urgency_threshold
            evidence_released = float(obs_pre[8]) >= urgency_threshold

            if conflict_near and bottleneck_near:
                context = "high_conflict_bottleneck"
            elif not evidence_released:
                context = "ambiguous_early"
            elif urgent:
                context = "high_urgency"
            else:
                context = "normal_flow"

            style = ACTION_NAMES.get(action, f"action_{action}")

            key = f"{context}|{style}"
            _inc_count(step_counts, key)
            chosen_keys.append(key)

            obs, _, done, info = env.step(action)
            final_info = info

            if key not in step_outcomes:
                step_outcomes[key] = {"collision_steps": 0, "deadlock_steps": 0, "success_steps": 0}
            if info["collision"] > 0:
                step_outcomes[key]["collision_steps"] += 1
            if info["deadlock"] > 0:
                step_outcomes[key]["deadlock_steps"] += 1
            if info["success"] > 0:
                step_outcomes[key]["success_steps"] += 1

            partner_key = f"partner_type_{int(info['partner_type'])}"
            if partner_key not in partner_style:
                partner_style[partner_key] = {label: 0 for label in ACTION_NAMES.values()}
                partner_style[partner_key]["total"] = 0
            partner_style[partner_key][style] += 1
            partner_style[partner_key]["total"] += 1

        if final_info is None:
            continue

        if final_info["collision"] > 0:
            terminal = "collision"
        elif final_info["deadlock"] > 0:
            terminal = "deadlock"
        elif final_info["success"] > 0:
            terminal = "success"
        else:
            terminal = "timeout"

        for key in chosen_keys:
            if key not in terminal_outcomes:
                terminal_outcomes[key] = {"collision": 0, "deadlock": 0, "success": 0, "timeout": 0}
            terminal_outcomes[key][terminal] += 1

        belief_shift_moment = None
        if belief_history and belief_history[0] is not None:
            initial_belief = belief_history[0]
            for idx, belief_class in enumerate(belief_history[1:], start=1):
                if belief_class is not None and belief_class != initial_belief:
                    belief_shift_moment = idx
                    break

        action_switch_moment = None
        saw_cautious = False
        for idx, action in enumerate(action_history):
            if action in cautious_actions:
                saw_cautious = True
            if saw_cautious and action in decisive_actions and idx >= scenario.evidence_step:
                action_switch_moment = idx
                break

        context_sensitive_regret = _context_sensitive_regret(action_history, scenario)
        context_regrets.append(context_sensitive_regret)

        timeout_pressure = "high" if len(action_history) >= max(1, int(0.6 * max_steps)) else "low"
        context_tag_set = {
            "urgency": scenario.urgency,
            "norm": scenario.norm,
            "margin": scenario.margin,
            "timeout_pressure": timeout_pressure,
        }
        context_tag = "|".join(f"{key}={value}" for key, value in context_tag_set.items())
        if terminal == "success":
            human_interpretation = "The learner read the bottleneck well enough to resolve the negotiation cleanly."
        elif terminal == "deadlock":
            human_interpretation = "The learner saw the ambiguity but failed to convert it into a useful strategy switch."
        elif terminal == "collision":
            human_interpretation = "The learner committed too aggressively under ambiguity and forced a costly clash."
        else:
            human_interpretation = "The learner never found a convincing commitment point before timeout."

        scenario_summaries.append(
            {
                "scenario_family": scenario.family,
                "partner_style": PARTNER_TYPES[scenario.partner_type],
                "context_tag": context_tag,
                "context_tag_set": context_tag_set,
                "belief_shift_moment": belief_shift_moment,
                "belief_turning_point": belief_shift_moment,
                "action_switch_moment": action_switch_moment,
                "action_switch_point": action_switch_moment,
                "switch_delay_after_evidence": None
                if action_switch_moment is None
                else max(0, action_switch_moment - scenario.evidence_step),
                "context_sensitive_action_regret": context_sensitive_regret,
                "outcome": terminal,
                "human_interpretation": human_interpretation,
                "one_line_interpretation": human_interpretation,
                "belief_confidence_peak": max(belief_confidences) if belief_confidences else 0.0,
            }
        )

    total_steps = max(1, sum(step_counts.values()))
    context_choice_rates = {k: v / total_steps for k, v in step_counts.items()}
    experiment_mask_rates = {k: v / total_steps for k, v in experiment_mask_counts.items()}

    context_outcome_rates: Dict[str, Dict[str, float]] = {}
    for key, outcomes in terminal_outcomes.items():
        denom = max(1, sum(outcomes.values()))
        context_outcome_rates[key] = {name: count / denom for name, count in outcomes.items()}

    partner_style_rates: Dict[str, Dict[str, float]] = {}
    for partner_key, counts in partner_style.items():
        denom = max(1, counts["total"])
        partner_style_rates[partner_key] = {
            f"{label}_rate": counts[label] / denom for label in ACTION_NAMES.values()
        }

    risk_self = step_counts.get("high_conflict_bottleneck|assert", 0) + step_counts.get(
        "high_conflict_bottleneck|proceed", 0
    )
    risk_coop = (
        step_counts.get("high_conflict_bottleneck|yield", 0)
        + step_counts.get("high_conflict_bottleneck|wait", 0)
        + step_counts.get("high_conflict_bottleneck|probe_gently", 0)
    )
    risk_total = max(1, risk_self + risk_coop)

    return {
        "scenarios_evaluated": len(scenarios),
        "choice_context_counts": step_counts,
        "choice_context_rates": context_choice_rates,
        "context_terminal_outcome_rates": context_outcome_rates,
        "partner_style_rates": partner_style_rates,
        "experiment_mask_firing_counts": experiment_mask_counts,
        "experiment_mask_firing_rates": experiment_mask_rates,
        "motivation_profile": {
            "high_conflict_assertive_rate": risk_self / risk_total,
            "high_conflict_cautious_rate": risk_coop / risk_total,
        },
        "mean_context_sensitive_action_regret": float(sum(context_regrets) / max(1, len(context_regrets))),
        "scenario_summaries": scenario_summaries,
    }


def train(args: argparse.Namespace) -> EvalMetrics:
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    device = torch.device("cuda" if torch.cuda.is_available() and not args.cpu else "cpu")
    env = ToMCoordinationEnv(max_steps=args.max_steps)

    if args.variant == "baseline":
        model: PolicyModel = BaselinePolicy(env.obs_dim, args.hidden_dim, env.action_dim)
    else:
        model = ToMPolicy(
            env.obs_dim,
            args.hidden_dim,
            env.action_dim,
            env.n_partner_types,
            proceed_safety_penalty=args.tom_proceed_safety_penalty,
            conflict_dist_threshold=args.tom_conflict_dist_threshold,
            bottleneck_dist_threshold=args.tom_bottleneck_dist_threshold,
            tom_experiment=args.tom_experiment,
            tom_experiment_strength=args.tom_experiment_strength,
            tom_belief_uncertainty_threshold=args.tom_belief_uncertainty_threshold,
            tom_context_tag_threshold=args.tom_context_tag_threshold,
        )

    model.to(device)
    if args.init_checkpoint:
        checkpoint = torch.load(args.init_checkpoint, map_location=device)
        checkpoint_variant = checkpoint.get("variant")
        if checkpoint_variant and checkpoint_variant != args.variant:
            raise ValueError(
                f"checkpoint variant {checkpoint_variant!r} does not match requested variant {args.variant!r}"
            )

        incompatible = model.load_state_dict(checkpoint["state_dict"], strict=args.init_strict)
        checkpoint_args = checkpoint.get("args", {})
        checkpoint_seed = checkpoint_args.get("seed")
        checkpoint_train_episodes = checkpoint_args.get("train_episodes")

        print(f"init_checkpoint={args.init_checkpoint}")
        print(f"init_checkpoint_variant={checkpoint_variant or 'unknown'}")
        print(f"init_checkpoint_seed={checkpoint_seed}")
        print(f"init_checkpoint_train_episodes={checkpoint_train_episodes}")
        print("init_checkpoint_missing_keys=" + json.dumps(sorted(incompatible.missing_keys)))
        print("init_checkpoint_unexpected_keys=" + json.dumps(sorted(incompatible.unexpected_keys)))

    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    curve_rows: List[Dict[str, float]] = []

    def _moving_avg(values: List[float], window: int) -> float:
        w = max(1, min(window, len(values)))
        return float(sum(values[-w:]) / w)

    reward_history: List[float] = []
    if args.resume_curve_from and os.path.exists(args.resume_curve_from):
        with open(args.resume_curve_from, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                curve_rows.append(
                    {
                        "episode": float(row["episode"]),
                        "reward_sum": float(row["reward_sum"]),
                        "reward_ma_10": float(row["reward_ma_10"]),
                        "policy_loss": float(row["policy_loss"]),
                        "entropy": float(row["entropy"]),
                        "aux_loss": float(row["aux_loss"]),
                        "behavior_aux_loss": float(row["behavior_aux_loss"]),
                        "total_loss": float(row["total_loss"]),
                    }
                )
                reward_history.append(float(row["reward_sum"]))

    scenario_rng = random.Random(args.seed + 10_003)
    for _ in range(max(0, args.episode_offset)):
        scenario_rng.randint(10_000, 999_999)

    def _artifact_episode_tag() -> int:
        return args.artifact_episode_tag if args.artifact_episode_tag > 0 else args.episode_offset + args.train_episodes

    def _checkpoint_payload(completed_chunk_episodes: int) -> Dict[str, object]:
        completed_total_episodes = args.episode_offset + completed_chunk_episodes
        reported_train_episodes = args.reported_train_episodes or completed_total_episodes
        checkpoint_args = vars(args).copy()
        checkpoint_args["train_episodes"] = int(reported_train_episodes)
        checkpoint_args["completed_chunk_episodes"] = int(completed_chunk_episodes)
        checkpoint_args["completed_total_episodes"] = int(completed_total_episodes)
        return {
            "variant": args.variant,
            "state_dict": model.state_dict(),
            "args": checkpoint_args,
            "progress": {
                "completed_chunk_episodes": int(completed_chunk_episodes),
                "completed_total_episodes": int(completed_total_episodes),
                "base_train_episodes": int(args.base_train_episodes),
                "reported_train_episodes": int(reported_train_episodes),
            },
        }

    def _write_curve(path: str) -> None:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "episode",
                    "reward_sum",
                    "reward_ma_10",
                    "policy_loss",
                    "entropy",
                    "aux_loss",
                    "behavior_aux_loss",
                    "total_loss",
                ],
            )
            writer.writeheader()
            writer.writerows(curve_rows)

    def _write_progress(completed_chunk_episodes: int, latest_checkpoint: str | None, latest_curve: str | None) -> None:
        if not args.progress_json:
            return
        completed_total_episodes = args.episode_offset + completed_chunk_episodes
        payload = {
            "seed": args.seed,
            "variant": args.variant,
            "base_train_episodes": int(args.base_train_episodes),
            "completed_chunk_episodes": int(completed_chunk_episodes),
            "completed_total_episodes": int(completed_total_episodes),
            "completed_additional_episodes": int(max(0, completed_total_episodes - args.base_train_episodes)),
            "remaining_total_episodes": int(max(0, _artifact_episode_tag() - completed_total_episodes)),
            "reported_train_episodes": int(args.reported_train_episodes or completed_total_episodes),
            "latest_checkpoint": latest_checkpoint,
            "latest_curve": latest_curve,
            "artifact_episode_tag": int(_artifact_episode_tag()),
            "is_final": completed_chunk_episodes >= args.train_episodes,
        }
        os.makedirs(os.path.dirname(args.progress_json), exist_ok=True)
        with open(args.progress_json, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)

    def _save_progress_artifacts(completed_chunk_episodes: int, final: bool = False) -> None:
        latest_checkpoint = None
        latest_curve = None

        if args.save_dir:
            os.makedirs(args.save_dir, exist_ok=True)
            latest_checkpoint = os.path.join(args.save_dir, f"latest-{args.variant}_seed{args.seed}.pt")
            torch.save(_checkpoint_payload(completed_chunk_episodes), latest_checkpoint)
            print(f"latest_checkpoint={latest_checkpoint}")
            if final:
                final_checkpoint = os.path.join(args.save_dir, f"{args.variant}_seed{args.seed}.pt")
                torch.save(_checkpoint_payload(completed_chunk_episodes), final_checkpoint)
                print(f"saved_checkpoint={final_checkpoint}")

        if args.curve_dir:
            os.makedirs(args.curve_dir, exist_ok=True)
            latest_curve = os.path.join(args.curve_dir, f"latest-curve-{args.variant}-seed{args.seed}.csv")
            _write_curve(latest_curve)
            print(f"latest_curve_csv={latest_curve}")
            if final:
                final_curve = os.path.join(
                    args.curve_dir,
                    f"curve-{args.variant}-seed{args.seed}-ep{_artifact_episode_tag()}.csv",
                )
                _write_curve(final_curve)
                print(f"learning_curve_csv={final_curve}")

        _write_progress(completed_chunk_episodes, latest_checkpoint, latest_curve)

    for episode in range(1, args.train_episodes + 1):
        global_episode = args.episode_offset + episode
        scenario = sample_training_scenario(scenario_rng, global_episode - 1)
        log_probs, rewards, entropies, belief_aux_losses, partner_action_aux_losses, behavior_aux_losses = rollout_episode(
            env,
            model,
            device,
            deterministic=False,
            scenario=scenario,
        )
        returns = discount_returns(rewards, args.gamma).to(device)

        policy_loss = -(torch.stack(log_probs) * returns).mean()
        entropy_bonus = torch.stack(entropies).mean()
        loss = policy_loss - args.entropy_coef * entropy_bonus

        if belief_aux_losses:
            loss = loss + args.aux_loss_weight * torch.stack(belief_aux_losses).mean()
        if partner_action_aux_losses and args.variant == "tom":
            loss = loss + 0.08 * torch.stack(partner_action_aux_losses).mean()
        if behavior_aux_losses:
            behavior_weight = 0.35 if args.variant == "baseline" else 0.25
            loss = loss + behavior_weight * torch.stack(behavior_aux_losses).mean()

        optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

        reward_sum = float(sum(rewards))
        reward_history.append(reward_sum)
        belief_aux_loss_value = float(torch.stack(belief_aux_losses).mean().item()) if belief_aux_losses else 0.0
        behavior_aux_loss_value = float(torch.stack(behavior_aux_losses).mean().item()) if behavior_aux_losses else 0.0
        curve_rows.append(
            {
                "episode": float(global_episode),
                "reward_sum": reward_sum,
                "reward_ma_10": _moving_avg(reward_history, 10),
                "policy_loss": float(policy_loss.item()),
                "entropy": float(entropy_bonus.item()),
                "aux_loss": belief_aux_loss_value,
                "behavior_aux_loss": behavior_aux_loss_value,
                "total_loss": float(loss.item()),
            }
        )

        if episode % max(1, args.log_every) == 0:
            print(
                f"episode={global_episode} loss={loss.item():.4f} policy_loss={policy_loss.item():.4f} "
                f"reward_sum={reward_sum:.3f}"
            )

        if args.save_every and episode % args.save_every == 0:
            _save_progress_artifacts(episode, final=False)

    metrics = evaluate_policy(build_policy_runner(model, device), env=ToMCoordinationEnv(max_steps=args.max_steps))
    choice_analysis = analyze_choice_context_outcomes(
        model=model,
        device=device,
        max_steps=args.max_steps,
        conflict_dist_threshold=args.analysis_conflict_dist_threshold,
        bottleneck_dist_threshold=args.analysis_bottleneck_dist_threshold,
        urgency_threshold=args.analysis_urgency_threshold,
    )

    _save_progress_artifacts(args.train_episodes, final=True)

    if args.analysis_dir:
        os.makedirs(args.analysis_dir, exist_ok=True)
        analysis_path = os.path.join(
            args.analysis_dir,
            f"choice-analysis-{args.variant}-seed{args.seed}-ep{_artifact_episode_tag()}.json",
        )
        with open(analysis_path, "w", encoding="utf-8") as f:
            json.dump(choice_analysis, f, indent=2, sort_keys=True)
        print(f"choice_analysis_json={analysis_path}")

    print("eval_metrics=" + json.dumps(asdict(metrics), sort_keys=True))
    print("choice_context_analysis=" + json.dumps(choice_analysis, sort_keys=True))
    mask_counts_obj = choice_analysis.get("experiment_mask_firing_counts", {})
    mask_rates_obj = choice_analysis.get("experiment_mask_firing_rates", {})
    mask_counts: Dict[str, float] = mask_counts_obj if isinstance(mask_counts_obj, dict) else {}
    mask_rates: Dict[str, float] = mask_rates_obj if isinstance(mask_rates_obj, dict) else {}
    if mask_counts:
        mask_summary = " ".join(
            f"{name}:n={int(mask_counts.get(name, 0))},r={float(mask_rates.get(name, 0.0)):.3f}"
            for name in sorted(mask_counts.keys())
        )
        print("experiment_mask_summary=" + mask_summary)
    else:
        print("experiment_mask_summary=none")
    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train compact ToM coordination baseline/variant.")
    parser.add_argument("--variant", choices=["baseline", "tom"], default="baseline")
    parser.add_argument(
        "--tom-experiment",
        choices=list(TOM_EXPERIMENTS),
        default="none",
        help="Optional bolt-on experiment for ToM variant; default keeps legacy behavior.",
    )
    parser.add_argument(
        "--tom-experiment-strength",
        type=float,
        default=0.25,
        help="Scaling for the selected bolt-on experiment.",
    )
    parser.add_argument(
        "--tom-belief-uncertainty-threshold",
        type=float,
        default=0.60,
        help="Normalized belief entropy threshold for uncertainty-triggered experiments.",
    )
    parser.add_argument(
        "--tom-context-tag-threshold",
        type=float,
        default=0.55,
        help="Threshold to binarize context tag features for context-sensitive bolt-ons.",
    )
    parser.add_argument("--train-episodes", type=int, default=800)
    parser.add_argument("--max-steps", type=int, default=20)
    parser.add_argument("--hidden-dim", type=int, default=64)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--gamma", type=float, default=0.98)
    parser.add_argument("--entropy-coef", type=float, default=0.01)
    parser.add_argument("--aux-loss-weight", type=float, default=0.25)
    parser.add_argument("--tom-proceed-safety-penalty", type=float, default=0.12)
    parser.add_argument("--tom-conflict-dist-threshold", type=float, default=0.55)
    parser.add_argument("--tom-bottleneck-dist-threshold", type=float, default=0.45)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--cpu", action="store_true")
    parser.add_argument(
        "--base-train-episodes",
        type=int,
        default=0,
        help="Episodes already represented by the warm-start checkpoint lineage before this invocation.",
    )
    parser.add_argument(
        "--episode-offset",
        type=int,
        default=0,
        help="Global training episode offset used for resumed training and curve numbering.",
    )
    parser.add_argument(
        "--reported-train-episodes",
        type=int,
        default=0,
        help="Optional total episode count to record in checkpoint metadata instead of the local train chunk size.",
    )
    parser.add_argument(
        "--artifact-episode-tag",
        type=int,
        default=0,
        help="Optional episode tag used in final curve and analysis filenames.",
    )
    parser.add_argument(
        "--init-checkpoint",
        type=str,
        default="",
        help="Optional checkpoint path to warm-start model weights before training.",
    )
    parser.add_argument(
        "--init-strict",
        action="store_true",
        help="Require an exact state-dict key match when warm-starting from a checkpoint.",
    )
    parser.add_argument("--save-dir", type=str, default="logs/checkpoints")
    parser.add_argument("--curve-dir", type=str, default="logs/curves")
    parser.add_argument("--analysis-dir", type=str, default="logs/analysis")
    parser.add_argument(
        "--resume-curve-from",
        type=str,
        default="",
        help="Optional existing curve CSV path to load before appending resumed training rows.",
    )
    parser.add_argument(
        "--progress-json",
        type=str,
        default="",
        help="Optional progress JSON path updated during periodic and final saves.",
    )
    parser.add_argument(
        "--save-every",
        type=int,
        default=0,
        help="If positive, periodically persist latest checkpoint, curve, and progress every N episodes.",
    )
    parser.add_argument("--analysis-conflict-dist-threshold", type=float, default=0.20)
    parser.add_argument("--analysis-bottleneck-dist-threshold", type=float, default=0.35)
    parser.add_argument("--analysis-urgency-threshold", type=float, default=0.5)
    parser.add_argument("--log-every", type=int, default=50)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    train(args)


if __name__ == "__main__":
    main()
