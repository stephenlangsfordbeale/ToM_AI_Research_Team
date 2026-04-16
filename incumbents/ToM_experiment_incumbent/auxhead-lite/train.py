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

        assertive_belief = belief[:, 1] + belief[:, 3] + 0.75 * belief[:, 4]
        cooperative_belief = belief[:, 0] + 0.60 * belief[:, 2]

        early_caution = (negotiation_window & (~evidence_released)).to(logits.dtype)
        late_yield = (
            negotiation_window
            & evidence_released
            & (assertive_belief > cooperative_belief + 0.10)
            & (margin_narrow | ((~throughput_bias) & (assertive_belief > cooperative_belief + 0.18)))
        ).to(logits.dtype)
        late_commit = (
            negotiation_window
            & evidence_released
            & (
                (cooperative_belief + 0.03 >= assertive_belief)
                | (urgency_high & throughput_bias & (~margin_narrow))
                | ((~margin_narrow) & (torch.abs(cooperative_belief - assertive_belief) <= 0.10))
            )
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

        diagnostics["early_caution_mask"] = early_caution
        diagnostics["late_yield_mask"] = late_yield
        diagnostics["late_commit_mask"] = late_commit
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
            assertive_mask = assertive_belief >= self.tom_belief_uncertainty_threshold

            conflict_near = torch.abs(obs[:, 2]) <= self.conflict_dist_threshold
            bottleneck_near = torch.abs(obs[:, 3]) <= self.bottleneck_dist_threshold
            contested = conflict_near & bottleneck_near

            urgency_high = obs[:, 5] >= self.tom_context_tag_threshold
            throughput_bias = obs[:, 6] >= self.tom_context_tag_threshold
            margin_narrow = obs[:, 7] >= self.tom_context_tag_threshold
            evidence_released = obs[:, 8] >= self.tom_context_tag_threshold

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
            logits[:, PROCEED] = logits[:, PROCEED] - 0.75 * self.tom_experiment_strength * yield_context
            logits[:, YIELD] = logits[:, YIELD] + 0.6 * self.tom_experiment_strength * yield_context
            logits[:, WAIT] = logits[:, WAIT] + 0.25 * self.tom_experiment_strength * yield_context

            diagnostics["assertive_belief"] = assertive_belief
            diagnostics["assert_context_mask"] = assert_context
            diagnostics["yield_context_mask"] = yield_context
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


def heuristic_teacher_action(obs: np.ndarray, scenario: Scenario) -> int:
    contested = abs(float(obs[2])) <= 0.35 and abs(float(obs[3])) <= 0.35
    urgency_high = float(obs[5]) >= 0.5
    throughput_bias = float(obs[6]) >= 0.5
    margin_narrow = float(obs[7]) >= 0.5
    evidence_released = float(obs[8]) >= 0.5

    assertive_like = scenario.partner_type in (1, 3, 4)
    cautious_like = scenario.partner_type in (0, 2)

    if not evidence_released:
        if contested:
            return WAIT if (margin_narrow or not throughput_bias) else PROBE
        return PROBE

    if assertive_like:
        if throughput_bias and urgency_high and not margin_narrow:
            return ASSERT
        return YIELD if (margin_narrow or scenario.norm == "courteous") else WAIT

    if cautious_like:
        if contested and (urgency_high or throughput_bias):
            return PROCEED if not margin_narrow else PROBE
        return PROCEED

    if scenario.family == "no_progress_switch":
        return ASSERT if throughput_bias else PROCEED

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
    consecutive_soft_postevidence = 0

    done = False
    while not done:
        obs_pre = obs.copy()
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
            throughput_bias = float(obs_pre[6]) >= 0.5
            margin_narrow = float(obs_pre[7]) >= 0.5
            soft_action = action in (WAIT, YIELD, PROBE)

            if evidence_released:
                if soft_action:
                    consecutive_soft_postevidence += 1
                    if consecutive_soft_postevidence >= 3 and (throughput_bias or not margin_narrow):
                        reward -= 0.012 if action == PROBE else 0.02
                else:
                    if consecutive_soft_postevidence >= 2 and not margin_narrow:
                        reward += 0.015 + (0.01 if throughput_bias else 0.0)
                    consecutive_soft_postevidence = 0
            else:
                consecutive_soft_postevidence = 0

        log_probs.append(log_prob.squeeze(0))
        entropies.append(entropy.squeeze(0))
        rewards.append(reward)

        teacher_action = heuristic_teacher_action(obs_pre, scenario)
        teacher_target = torch.tensor([teacher_action], dtype=torch.long, device=device)
        behavior_aux_losses.append(F.cross_entropy(logits, teacher_target))

        if "belief_logits" in extra:
            target = torch.tensor([int(info["partner_type"])], dtype=torch.long, device=device)
            belief_aux_losses.append(F.cross_entropy(extra["belief_logits"], target))
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

            out: Dict[str, np.ndarray] = {
                "action": np.array(action, dtype=np.int64),
                "state": new_state.cpu().numpy(),
            }

            action_probs = F.softmax(logits, dim=-1)
            topk = torch.topk(action_probs, k=min(2, action_probs.shape[-1]), dim=-1).values.squeeze(0)
            if topk.numel() >= 2:
                action_confidence_margin = float((topk[0] - topk[1]).item())
            else:
                action_confidence_margin = 1.0
            out["action_confidence_margin"] = np.array(action_confidence_margin, dtype=np.float32)

            if "belief" in extra:
                belief = extra["belief"]
                out["belief_class"] = np.array(int(torch.argmax(belief, dim=-1).item()), dtype=np.int64)
                out["belief_confidence"] = np.array(float(torch.max(belief, dim=-1).values.item()), dtype=np.float32)

                belief_entropy = -(belief * torch.log(belief.clamp_min(1e-8))).sum(dim=-1)
                max_entropy = float(np.log(max(2, belief.shape[-1])))
                normalized_belief_entropy = float((belief_entropy / max_entropy).item())
                out["belief_entropy"] = np.array(normalized_belief_entropy, dtype=np.float32)

                out["belief_probs"] = belief.squeeze(0).cpu().numpy().astype(np.float32)

            for key in (
                "experiment_mask",
                "assert_context_mask",
                "yield_context_mask",
                "early_caution_mask",
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

    for scenario in scenarios:
        obs = env.reset(scenario=scenario)
        state: Optional[np.ndarray] = None
        done = False
        chosen_keys: List[str] = []
        final_info: Optional[Dict[str, float]] = None
        action_history: List[int] = []
        action_label_history: List[str] = []
        belief_history: List[Optional[int]] = []
        belief_confidences: List[float] = []
        belief_entropies: List[float] = []
        belief_probs_trace: List[List[float]] = []
        action_confidence_margins: List[float] = []
        context_trace: List[str] = []
        evidence_released_trace: List[int] = []


        while not done:
            obs_pre = obs.copy()
            out = policy(obs_pre, state)
            action = int(out["action"])
            state = out.get("state")
            action_history.append(action)
            action_label_history.append(ACTION_NAMES.get(action, f"action_{action}"))
            belief_history.append(int(out["belief_class"])) if "belief_class" in out else belief_history.append(None)
            belief_confidences.append(float(out.get("belief_confidence", 0.0)))
            belief_entropies.append(float(out.get("belief_entropy", 0.0)))

            belief_probs = out.get("belief_probs")
            if belief_probs is None:
                belief_probs_trace.append([])
            else:
                belief_probs_trace.append([float(x) for x in belief_probs.tolist()])

            action_confidence_margins.append(float(out.get("action_confidence_margin", 0.0)))

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
            
            context_trace.append(context)
            evidence_released_trace.append(int(evidence_released))


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

        context_tag = f"urgency={scenario.urgency}|norm={scenario.norm}|margin={scenario.margin}"
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
                "belief_shift_moment": belief_shift_moment,
                "action_switch_moment": action_switch_moment,
                "outcome": terminal,
                "human_interpretation": human_interpretation,
                "belief_confidence_peak": max(belief_confidences) if belief_confidences else 0.0,
                "belief_confidence_trace": belief_confidences,
                "belief_entropy_trace": belief_entropies,
                "belief_probs_trace": belief_probs_trace,
                "belief_class_trace": belief_history,
                "action_trace": action_history,
                "action_label_trace": action_label_history,
                "action_confidence_margin_trace": action_confidence_margins,
                "context_trace": context_trace,
                "evidence_released_trace": evidence_released_trace,

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
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    curve_rows: List[Dict[str, float]] = []

    def _moving_avg(values: List[float], window: int) -> float:
        w = max(1, min(window, len(values)))
        return float(sum(values[-w:]) / w)

    reward_history: List[float] = []
    scenario_rng = random.Random(args.seed + 10_003)

    for episode in range(1, args.train_episodes + 1):
        scenario = sample_training_scenario(scenario_rng, episode - 1)
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
                "episode": float(episode),
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
                f"episode={episode} loss={loss.item():.4f} policy_loss={policy_loss.item():.4f} "
                f"reward_sum={reward_sum:.3f}"
            )

    metrics = evaluate_policy(build_policy_runner(model, device), env=ToMCoordinationEnv(max_steps=args.max_steps))
    choice_analysis = analyze_choice_context_outcomes(
        model=model,
        device=device,
        max_steps=args.max_steps,
        conflict_dist_threshold=args.analysis_conflict_dist_threshold,
        bottleneck_dist_threshold=args.analysis_bottleneck_dist_threshold,
        urgency_threshold=args.analysis_urgency_threshold,
    )

    if args.save_dir:
        os.makedirs(args.save_dir, exist_ok=True)
        ckpt_path = os.path.join(args.save_dir, f"{args.variant}_seed{args.seed}.pt")
        torch.save({"variant": args.variant, "state_dict": model.state_dict(), "args": vars(args)}, ckpt_path)
        print(f"saved_checkpoint={ckpt_path}")

    if args.curve_dir:
        os.makedirs(args.curve_dir, exist_ok=True)
        curve_path = os.path.join(args.curve_dir, f"curve-{args.variant}-seed{args.seed}-ep{args.train_episodes}.csv")
        with open(curve_path, "w", newline="", encoding="utf-8") as f:
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
        print(f"learning_curve_csv={curve_path}")

    if args.analysis_dir:
        os.makedirs(args.analysis_dir, exist_ok=True)
        analysis_path = os.path.join(
            args.analysis_dir,
            f"choice-analysis-{args.variant}-seed{args.seed}-ep{args.train_episodes}.json",
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
    parser.add_argument("--save-dir", type=str, default="checkpoints")
    parser.add_argument("--curve-dir", type=str, default="logs/curves")
    parser.add_argument("--analysis-dir", type=str, default="logs/analysis")
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
