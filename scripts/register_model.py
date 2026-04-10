from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Register a selected model directory in Azure ML model registry.")
    parser.add_argument("--model-path", type=str, required=True)
    parser.add_argument("--model-name", type=str, required=True)
    parser.add_argument("--subscription-id", type=str, required=True)
    parser.add_argument("--resource-group", type=str, required=True)
    parser.add_argument("--workspace-name", type=str, required=True)
    parser.add_argument("--model-version", type=str, default=None)
    parser.add_argument(
        "--dry-run",
        nargs="?",
        const="true",
        default="false",
        help="Validate inputs and print intended registration payload.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dry_run = str(args.dry_run).strip().lower() in {"1", "true", "yes", "y"}

    model_path = Path(args.model_path)
    if not model_path.exists():
        raise FileNotFoundError(f"Model path not found: {model_path}")

    if dry_run:
        print("dry_run=true")
        print(f"model_path={model_path}")
        print(f"model_name={args.model_name}")
        print(f"model_version={args.model_version}")
        print(f"subscription_id={args.subscription_id}")
        print(f"resource_group={args.resource_group}")
        print(f"workspace_name={args.workspace_name}")
        return

    from azure.ai.ml import MLClient
    from azure.ai.ml.entities import Model
    from azure.identity import DefaultAzureCredential

    credential = DefaultAzureCredential()
    client = MLClient(
        credential=credential,
        subscription_id=args.subscription_id,
        resource_group_name=args.resource_group,
        workspace_name=args.workspace_name,
    )

    model_asset = Model(
        path=str(model_path),
        name=args.model_name,
        version=args.model_version,
        type="custom_model",
        description="Selected ToM coordination model artifact.",
        tags={"source": "tom_coordination_pipeline", "selection": "epsilon_and_deadlock_guardrail"},
    )

    registered = client.models.create_or_update(model_asset)
    print(f"registered_model_name={registered.name}")
    print(f"registered_model_version={registered.version}")
    print(f"registered_model_id={registered.id}")


if __name__ == "__main__":
    main()
