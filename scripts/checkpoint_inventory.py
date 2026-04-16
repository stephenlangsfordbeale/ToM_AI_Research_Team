from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


REPO_ROOT = Path(__file__).resolve().parents[1]
SKIP_DIR_NAMES = {".git", "__pycache__"}
SKIP_DIR_PREFIXES = (".venv",)


def _iso_from_timestamp(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(microsecond=0).isoformat()


def _created_timestamp(path: Path) -> tuple[float, str]:
    stat_result = path.stat()
    birthtime = getattr(stat_result, "st_birthtime", None)
    if birthtime is not None:
        return float(birthtime), "birthtime"
    return float(stat_result.st_mtime), "mtime_fallback"


def _should_skip(path: Path) -> bool:
    return any(
        part in SKIP_DIR_NAMES or any(part.startswith(prefix) for prefix in SKIP_DIR_PREFIXES)
        for part in path.parts
    )


def collect_checkpoint_inventory(root: Path) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for checkpoint_path in sorted(root.rglob("*.pt")):
        if _should_skip(checkpoint_path):
            continue
        created_ts, created_source = _created_timestamp(checkpoint_path)
        modified_ts = checkpoint_path.stat().st_mtime
        records.append(
            {
                "path": str(checkpoint_path),
                "relative_path": str(checkpoint_path.relative_to(root)),
                "size_bytes": int(checkpoint_path.stat().st_size),
                "created_at_utc": _iso_from_timestamp(created_ts),
                "created_at_source": created_source,
                "modified_at_utc": _iso_from_timestamp(modified_ts),
                "file_name": checkpoint_path.name,
            }
        )
    return records


def write_sidecars(records: Iterable[Dict[str, Any]]) -> int:
    written = 0
    for record in records:
        checkpoint_path = Path(record["path"])
        sidecar_path = checkpoint_path.with_suffix(checkpoint_path.suffix + ".metadata.json")
        sidecar_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        written += 1
    return written


def summarize(records: List[Dict[str, Any]], root: Path) -> Dict[str, Any]:
    selected_model_count = sum(1 for record in records if record["file_name"] == "selected_model.pt")
    model_pt_count = sum(1 for record in records if record["file_name"] == "model.pt")
    return {
        "root": str(root),
        "checkpoint_count": len(records),
        "selected_model_count": selected_model_count,
        "model_pt_count": model_pt_count,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventory existing .pt checkpoints using filesystem metadata without rewriting them."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=REPO_ROOT,
        help="Root directory to scan for .pt checkpoints (default: repo root).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write a single aggregated JSON inventory report.",
    )
    parser.add_argument(
        "--write-sidecars",
        action="store_true",
        help="Write <checkpoint>.pt.metadata.json sidecars next to each discovered checkpoint.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve(strict=False)
    records = collect_checkpoint_inventory(root)
    summary = summarize(records, root)

    print(json.dumps(summary, indent=2, sort_keys=True))

    if args.output is not None:
        output_path = args.output.resolve(strict=False)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"summary": summary, "checkpoints": records}
        output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote_inventory={output_path}")

    if args.write_sidecars:
        written = write_sidecars(records)
        print(f"wrote_sidecars={written}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
