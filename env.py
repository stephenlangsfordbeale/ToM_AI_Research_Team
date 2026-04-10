from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Dict, List, Optional, Tuple

import numpy as np


WAIT = 0
YIELD = 1
PROBE = 2
PROCEED = 3
ASSERT = 4
ACTIONS = (WAIT, YIELD, PROBE, PROCEED, ASSERT)
ACTION_NAMES = {
    WAIT: "wait",
    YIELD: "yield",
    PROBE: "probe_gently",
    PROCEED: "proceed",
    ASSERT: "assert",
}
PARTNER_TYPES = ("cooperative", "assertive", "hesitant", "opportunistic", "deceptive_switching")


@dataclass(frozen=True)
class Scenario:
    seed: int
    partner_type: int
    family: str
    urgency: str
    norm: str
    margin: str
    evidence_step: int
    preferred_after: Tuple[int, ...]
    require_cautious_opening: bool = True


def fixed_validation_scenarios() -> List[Scenario]:
    # Fixed suite for parity across all runs.
    return [
        Scenario(13, 0, "ambiguous_commit", "low", "courteous", "moderate", 2, (PROCEED, ASSERT)),
        Scenario(29, 1, "ambiguous_commit", "low", "courteous", "narrow", 2, (YIELD, WAIT)),
        Scenario(41, 2, "ambiguous_commit", "high", "throughput_biased", "moderate", 2, (PROCEED, ASSERT)),
        Scenario(53, 3, "ambiguous_commit", "high", "throughput_biased", "narrow", 2, (YIELD, WAIT)),
        Scenario(67, 4, "false_friend", "low", "courteous", "narrow", 2, (YIELD, WAIT)),
        Scenario(79, 3, "false_friend", "high", "throughput_biased", "moderate", 2, (YIELD, WAIT)),
        Scenario(97, 0, "false_friend", "low", "courteous", "moderate", 2, (PROCEED, ASSERT)),
        Scenario(113, 1, "false_friend", "high", "throughput_biased", "narrow", 2, (YIELD, WAIT)),
        Scenario(131, 2, "no_progress_switch", "high", "throughput_biased", "moderate", 2, (ASSERT, PROCEED)),
        Scenario(149, 0, "no_progress_switch", "high", "throughput_biased", "narrow", 2, (ASSERT, PROCEED)),
        Scenario(167, 2, "no_progress_switch", "low", "courteous", "moderate", 2, (PROCEED, ASSERT)),
        Scenario(181, 3, "no_progress_switch", "high", "throughput_biased", "moderate", 2, (ASSERT, PROCEED)),
        Scenario(199, 1, "late_disambiguation", "high", "throughput_biased", "moderate", 4, (YIELD, WAIT)),
        Scenario(211, 4, "late_disambiguation", "low", "courteous", "narrow", 4, (YIELD, WAIT)),
        Scenario(227, 0, "late_disambiguation", "low", "courteous", "moderate", 4, (PROCEED, ASSERT)),
        Scenario(239, 2, "late_disambiguation", "high", "throughput_biased", "moderate", 4, (ASSERT, PROCEED)),
        Scenario(251, 1, "assert_or_yield", "high", "throughput_biased", "moderate", 2, (ASSERT, PROCEED)),
        Scenario(269, 1, "assert_or_yield", "low", "courteous", "narrow", 2, (YIELD, WAIT)),
        Scenario(281, 3, "assert_or_yield", "high", "throughput_biased", "moderate", 2, (ASSERT, PROCEED)),
        Scenario(307, 3, "assert_or_yield", "low", "courteous", "narrow", 2, (YIELD, WAIT)),
    ]


class ToMCoordinationEnv:
    """Ambiguous bottleneck negotiation benchmark under partial observability."""

    def __init__(self, lane_len: int = 9, max_steps: int = 20, obs_noise: float = 0.02) -> None:
        self.lane_len = lane_len
        self.max_steps = max_steps
        self.obs_noise = obs_noise
        self.bottleneck = (lane_len - 1) / 2.0
        self.rng = random.Random(0)
        self.np_rng = np.random.default_rng(0)

        self.step_id = 0
        self.agent_pos = 0.0
        self.partner_pos = float(lane_len - 1)
        self.partner_type = 0
        self.current_scenario: Optional[Scenario] = None
        self.last_partner_action = WAIT
        self.last_agent_action = WAIT
        self.no_progress_steps = 0

    @property
    def obs_dim(self) -> int:
        return 10

    @property
    def action_dim(self) -> int:
        return len(ACTIONS)

    @property
    def n_partner_types(self) -> int:
        return len(PARTNER_TYPES)

    def reset(
        self,
        scenario: Optional[Scenario] = None,
        scenario_seed: Optional[int] = None,
        partner_type: Optional[int] = None,
    ) -> np.ndarray:
        if scenario is None:
            scenario = Scenario(
                seed=scenario_seed if scenario_seed is not None else 13,
                partner_type=partner_type if partner_type is not None else 0,
                family="ambiguous_commit",
                urgency="low",
                norm="courteous",
                margin="moderate",
                evidence_step=2,
                preferred_after=(PROCEED, ASSERT),
            )
        if scenario_seed is None:
            scenario_seed = scenario.seed

        self.rng.seed(scenario_seed)
        self.np_rng = np.random.default_rng(scenario_seed)
        self.step_id = 0
        self.agent_pos = 0.0
        self.partner_pos = float(self.lane_len - 1)
        self.partner_type = scenario.partner_type if partner_type is None else partner_type
        self.current_scenario = scenario
        self.last_partner_action = WAIT
        self.last_agent_action = WAIT
        self.no_progress_steps = 0
        return self._obs()

    def _scenario(self) -> Scenario:
        if self.current_scenario is None:
            raise RuntimeError("Environment reset must be called before stepping.")
        return self.current_scenario

    def _contested(self) -> bool:
        return abs(self.agent_pos - self.bottleneck) <= 1.35 and abs(self.partner_pos - self.bottleneck) <= 1.35

    def _partner_forward_delta(self, action: int) -> float:
        if action == WAIT:
            return 0.0
        if action == YIELD:
            return 0.6
        if action == PROBE:
            return -0.5
        if action == PROCEED:
            return -1.0
        return -1.25

    def _agent_forward_delta(self, action: int) -> float:
        if action == WAIT:
            return 0.0
        if action == YIELD:
            return -0.6
        if action == PROBE:
            return 0.5
        if action == PROCEED:
            return 1.0
        return 1.25

    def _partner_policy(self, agent_action: int) -> int:
        scenario = self._scenario()
        contested = self._contested()
        evidence_released = self.step_id >= scenario.evidence_step
        agent_pressing = agent_action in (PROCEED, ASSERT)
        agent_soft = agent_action in (WAIT, YIELD, PROBE)

        if not evidence_released:
            if contested:
                if scenario.family in {"false_friend", "late_disambiguation"}:
                    return PROBE if self.step_id % 2 == 0 else WAIT
                if scenario.family == "no_progress_switch":
                    return WAIT if self.step_id % 2 == 0 else PROBE
                return PROBE
            return PROCEED if self.partner_pos > self.bottleneck + 1.5 else PROBE

        if scenario.family == "assert_or_yield" and self.partner_type in {1, 3}:
            if scenario.norm == "throughput_biased" and scenario.urgency == "high" and agent_pressing:
                return YIELD
            if scenario.norm == "courteous" and scenario.margin == "narrow":
                return ASSERT if contested else PROCEED

        if scenario.family == "no_progress_switch" and self.partner_type in {0, 2, 3}:
            if contested and agent_pressing:
                return YIELD
            if contested:
                return WAIT

        if self.partner_type == 0:  # cooperative
            if contested:
                return YIELD if agent_pressing or scenario.norm == "courteous" else PROBE
            return PROCEED

        if self.partner_type == 1:  # assertive
            if contested:
                return ASSERT if agent_soft else PROCEED
            return PROCEED

        if self.partner_type == 2:  # hesitant
            if contested:
                return YIELD if agent_action == ASSERT else WAIT
            return PROBE

        if self.partner_type == 3:  # opportunistic
            if contested:
                if agent_action in (WAIT, YIELD):
                    return ASSERT
                return YIELD if scenario.norm == "courteous" else PROCEED
            return PROBE if self.partner_pos > self.bottleneck + 1.0 else PROCEED

        # deceptive_switching
        if contested:
            return ASSERT if scenario.family in {"false_friend", "late_disambiguation"} else PROCEED
        return PROCEED

    def _obs(self) -> np.ndarray:
        scenario = self._scenario()
        obs = np.array(
            [
                self.agent_pos / max(1.0, self.lane_len - 1),
                self.partner_pos / max(1.0, self.lane_len - 1),
                (self.partner_pos - self.agent_pos) / max(1.0, self.lane_len - 1),
                (self.bottleneck - self.agent_pos) / max(1.0, self.lane_len - 1),
                float(self.last_partner_action) / max(1.0, len(ACTIONS) - 1),
                1.0 if scenario.urgency == "high" else 0.0,
                1.0 if scenario.norm == "throughput_biased" else 0.0,
                1.0 if scenario.margin == "narrow" else 0.0,
                1.0 if self.step_id >= scenario.evidence_step else 0.0,
                abs(self.partner_pos - self.bottleneck) / max(1.0, self.lane_len - 1),
            ],
            dtype=np.float32,
        )
        if self.obs_noise > 0:
            obs += self.np_rng.normal(loc=0.0, scale=self.obs_noise, size=obs.shape).astype(np.float32)
        return obs

    def step(self, agent_action: int) -> Tuple[np.ndarray, float, bool, Dict[str, float]]:
        scenario = self._scenario()
        contested_before = self._contested()
        partner_action = self._partner_policy(int(agent_action))

        old_a, old_b = self.agent_pos, self.partner_pos
        next_a = float(np.clip(old_a + self._agent_forward_delta(int(agent_action)), 0.0, self.lane_len - 1))
        next_b = float(np.clip(old_b + self._partner_forward_delta(int(partner_action)), 0.0, self.lane_len - 1))

        margin_buffer = 0.45 if scenario.margin == "narrow" else 0.30
        contested_next = abs(next_a - self.bottleneck) <= 1.0 and abs(next_b - self.bottleneck) <= 1.0
        overlap = next_a + margin_buffer >= next_b
        collision = contested_next and overlap

        if collision:
            done = True
            reward = -1.2
            success = 0.0
            deadlock = 0.0
            efficiency = 0.0
        else:
            self.agent_pos = next_a
            self.partner_pos = next_b
            moved = (abs(self.agent_pos - old_a) > 1e-6) or (abs(self.partner_pos - old_b) > 1e-6)
            self.no_progress_steps = 0 if moved else self.no_progress_steps + 1
            self.step_id += 1

            success = 1.0 if (self.agent_pos >= self.lane_len - 1 and self.partner_pos <= 0.0) else 0.0
            deadlock = 1.0 if self.no_progress_steps >= 4 else 0.0
            timeout = self.step_id >= self.max_steps
            done = bool(success or deadlock or timeout)

            reward = -0.01
            if scenario.urgency == "high":
                reward -= 0.005
            if contested_before and agent_action == WAIT:
                reward -= 0.02
            if contested_before and scenario.norm == "courteous" and agent_action == ASSERT:
                reward -= 0.04
            if contested_before and scenario.norm == "throughput_biased" and agent_action in (WAIT, YIELD):
                reward -= 0.02
            if self.step_id <= scenario.evidence_step and scenario.require_cautious_opening and agent_action in (PROCEED, ASSERT):
                reward -= 0.02
            if self.step_id > scenario.evidence_step and contested_before:
                if agent_action in scenario.preferred_after:
                    reward += 0.04
                else:
                    reward -= 0.015

            if success:
                reward += 1.0
            if deadlock:
                reward -= 0.6

            efficiency = 1.0 - (self.step_id / self.max_steps) if success else 0.0

        self.last_partner_action = int(partner_action)
        self.last_agent_action = int(agent_action)

        info: Dict[str, float] = {
            "success": success,
            "collision": 1.0 if collision else 0.0,
            "deadlock": deadlock,
            "coord_eff": efficiency,
            "partner_type": float(self.partner_type),
            "partner_action": float(partner_action),
            "step": float(self.step_id),
            "urgency_high": 1.0 if scenario.urgency == "high" else 0.0,
            "throughput_bias": 1.0 if scenario.norm == "throughput_biased" else 0.0,
            "margin_narrow": 1.0 if scenario.margin == "narrow" else 0.0,
            "evidence_released": 1.0 if self.step_id >= scenario.evidence_step else 0.0,
        }
        return self._obs(), float(reward), done, info
