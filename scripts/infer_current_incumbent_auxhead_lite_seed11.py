#!/usr/bin/env python3
from __future__ import annotations

import json

from infer_checkpoint_common import REPO_ROOT, build_parser, run_inference


DEFAULT_CHECKPOINT = (
    REPO_ROOT
    / "incumbents"
    / "ToM_experiment_incumbent"
    / "auxhead-lite"
    / "seed11"
    / "selected_model.pt"
)
AUXHEAD_LITE_TRAIN_PY = REPO_ROOT / "incumbents" / "ToM_experiment_incumbent" / "auxhead-lite" / "train.py"


def main() -> int:
    parser = build_parser(
        "Minimal standalone inference runner for the 800-episode auxhead-lite seed11 reference checkpoint.",
        DEFAULT_CHECKPOINT,
    )
    args = parser.parse_args()
    output = run_inference(
        checkpoint_path=args.checkpoint,
        train_module_path=AUXHEAD_LITE_TRAIN_PY,
        train_module_name="incumbent_auxhead_lite_seed11_train",
        obs_json=args.obs,
        state_json=args.state,
    )
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
