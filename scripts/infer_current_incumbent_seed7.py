#!/usr/bin/env python3
from __future__ import annotations

import json

from infer_checkpoint_common import REPO_ROOT, build_parser, run_inference


DEFAULT_CHECKPOINT = (
    REPO_ROOT
    / "incumbents"
    / "ToM_experiment_incumbent"
    / "deadlock-micro"
    / "seed7"
    / "selected_model.pt"
)
INCUMBENT_TRAIN_PY = REPO_ROOT / "incumbents" / "ToM_experiment_incumbent" / "deadlock-micro" / "train.py"


def main() -> int:
    parser = build_parser(
        "Minimal standalone inference runner for the archived deadlock-micro seed7 checkpoint.",
        DEFAULT_CHECKPOINT,
    )
    args = parser.parse_args()
    output = run_inference(
        checkpoint_path=args.checkpoint,
        train_module_path=INCUMBENT_TRAIN_PY,
        train_module_name="incumbent_seed7_train",
        obs_json=args.obs,
        state_json=args.state,
    )
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
