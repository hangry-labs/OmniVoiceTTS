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

    def test_lightweight_ci_remains_dependency_free(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("python -m compileall -q omnivoice scripts tests", workflow)
        self.assertIn("tomllib.load", workflow)
        self.assertIn("docker build --check .", workflow)
        self.assertNotIn("pip install", workflow)
        self.assertNotIn("unittest discover", workflow)

    def test_taskfile_uses_one_product_volume(self) -> None:
        taskfile = (ROOT / "Taskfile.yml").read_text(encoding="utf-8")
        self.assertIn("DATA_VOLUME: omnivoicetts_data", taskfile)
        self.assertIn("-v {{.DATA_VOLUME}}:{{.DATA_ROOT}}", taskfile)
        self.assertNotIn("OPENAI_PROFILE_VOLUME:", taskfile)
        self.assertNotIn("HF_CACHE_VOLUME:", taskfile)

    def test_runtime_package_excludes_retired_gradio_demo(self) -> None:
        with (ROOT / "pyproject.toml").open("rb") as handle:
            config = tomllib.load(handle)
        project = config["project"]
        self.assertNotIn("gradio==6.14.0", project["dependencies"])
        self.assertNotIn("torchaudio==2.8.0", project["dependencies"])
        self.assertEqual(project["optional-dependencies"]["torchaudio"], ["torchaudio==2.8.0"])
        self.assertNotIn("omnivoice-demo", project["scripts"])
        self.assertFalse((ROOT / "omnivoice" / "cli" / "demo.py").exists())
        self.assertIn("python-multipart==0.0.28", project["dependencies"])
        self.assertIn("VERSION", config["tool"]["hatch"]["build"]["targets"]["sdist"]["include"])
        self.assertIn("assets", config["tool"]["hatch"]["build"]["targets"]["sdist"]["include"])

    def test_builtin_voice_is_an_explicit_runtime_asset(self) -> None:
        runtime_voice = ROOT / "omnivoice" / "runtime_assets" / "voices" / "openai_default_voice.mp3"
        self.assertTrue(runtime_voice.is_file())
        app_source = (ROOT / "omnivoice" / "app.py").read_text(encoding="utf-8")
        self.assertIn('PACKAGE_DIR / "runtime_assets" / "voices"', app_source)

    def test_examples_page_uses_current_local_brand_assets(self) -> None:
        page = (ROOT / "examples" / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="styles.css"', page)
        self.assertIn('../assets/omnivoice_logo.webp', page)
        self.assertIn('../assets/hangrylabs_mascot.webp', page)
        self.assertNotIn("tailwindcss.com", page)
        self.assertNotIn("../hangrylabs/", page)
        self.assertTrue((ROOT / "examples" / "styles.css").is_file())


if __name__ == "__main__":
    unittest.main()
