from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "checkpoint_inventory.py"
SPEC = importlib.util.spec_from_file_location("checkpoint_inventory", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
checkpoint_inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checkpoint_inventory)


class CheckpointInventoryTests(unittest.TestCase):
    def test_collect_checkpoint_inventory_records_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            checkpoint_path = root / "seed7" / "selected_model.pt"
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            checkpoint_path.write_bytes(b"checkpoint")

            records = checkpoint_inventory.collect_checkpoint_inventory(root)

            self.assertEqual(len(records), 1)
            record = records[0]
            self.assertEqual(record["file_name"], "selected_model.pt")
            self.assertEqual(record["relative_path"], "seed7/selected_model.pt")
            self.assertIn("created_at_utc", record)
            self.assertIn("modified_at_utc", record)
            self.assertGreater(record["size_bytes"], 0)

    def test_write_sidecars_creates_metadata_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            checkpoint_path = root / "candidate" / "model.pt"
            checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
            checkpoint_path.write_bytes(b"checkpoint")

            records = checkpoint_inventory.collect_checkpoint_inventory(root)
            written = checkpoint_inventory.write_sidecars(records)

            self.assertEqual(written, 1)
            sidecar_path = checkpoint_path.with_suffix(".pt.metadata.json")
            self.assertTrue(sidecar_path.exists())
            payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["path"], str(checkpoint_path))


if __name__ == "__main__":
    unittest.main()
