from __future__ import annotations

import re
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RepositoryContractTests(unittest.TestCase):
    def test_snapshot_and_package_versions_match(self) -> None:
        snapshot = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        match = re.fullmatch(r"(\d+\.\d+(?:\.\d+)?)-snapshot", snapshot)
        self.assertIsNotNone(match)
        release = match.group(1)
        package_base = release if release.count(".") == 2 else f"{release}.0"
        with (ROOT / "pyproject.toml").open("rb") as handle:
            package_version = tomllib.load(handle)["project"]["version"]
        self.assertEqual(package_version, f"{package_base}.dev0")

    def test_dockerfile_uses_unified_persistent_layout(self) -> None:
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("HF_HOME=/app/persistent/models/huggingface", dockerfile)
        self.assertIn("OMNIVOICE_SETTINGS_PATH=/app/persistent/app/settings.json", dockerfile)
        self.assertIn(
            "OMNIVOICE_OPENAI_VOICE_PROFILE_DIR=/app/persistent/voices/openai",
            dockerfile,
        )
        self.assertIn("HEALTHCHECK", dockerfile)
        self.assertIn("http://127.0.0.1:7861/tts/ping", dockerfile)

    def test_one_container_workflow_builds_both_variants_and_registries(self) -> None:
        workflows = ROOT / ".github" / "workflows"
        self.assertFalse((workflows / "docker-build-tiny.yml").exists())
        self.assertFalse((workflows / "docker-build.yml").exists())
        workflow = (workflows / "docker-images.yml").read_text(encoding="utf-8")
        for expected in (
            "target: baked",
            "target: tiny",
            "hangrylabs/omnivoicetts",
            "ghcr.io/hangry-labs/omnivoicetts",
            "latest_tiny",
        ):
            self.assertIn(expected, workflow)

    def test_taskfile_uses_one_product_volume(self) -> None:
        taskfile = (ROOT / "Taskfile.yml").read_text(encoding="utf-8")
        self.assertIn("DATA_VOLUME: omnivoicetts_data", taskfile)
        self.assertIn("-v {{.DATA_VOLUME}}:{{.DATA_ROOT}}", taskfile)
        self.assertNotIn("OPENAI_PROFILE_VOLUME:", taskfile)
        self.assertNotIn("HF_CACHE_VOLUME:", taskfile)


if __name__ == "__main__":
    unittest.main()
