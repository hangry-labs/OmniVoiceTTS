from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from omnivoice.docker_entrypoint import seed_baked_model_cache


class DockerEntrypointTests(unittest.TestCase):
    def test_baked_cache_merge_updates_assets_without_deleting_user_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "baked"
            destination = root / "persistent"
            (source / "snapshots" / "reviewed").mkdir(parents=True)
            (source / "snapshots" / "reviewed" / "config.json").write_text(
                "reviewed config",
                encoding="utf-8",
            )
            destination.mkdir()
            (destination / "user-model.bin").write_bytes(b"user-owned-cache")
            (destination / "snapshots" / "reviewed").mkdir(parents=True)
            (destination / "snapshots" / "reviewed" / "config.json").write_text(
                "old",
                encoding="utf-8",
            )

            copied_files, copied_bytes = seed_baked_model_cache(source, destination)

            self.assertEqual(copied_files, 1)
            self.assertEqual(copied_bytes, len("reviewed config"))
            self.assertEqual(
                (destination / "snapshots" / "reviewed" / "config.json").read_text(
                    encoding="utf-8"
                ),
                "reviewed config",
            )
            self.assertEqual((destination / "user-model.bin").read_bytes(), b"user-owned-cache")

            self.assertEqual(seed_baked_model_cache(source, destination), (0, 0))


if __name__ == "__main__":
    unittest.main()

