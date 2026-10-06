from __future__ import annotations

import re
import tomllib
import unittest
from html import unescape
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
        self.assertIn("HF_HOME=/app/baked-models/huggingface", dockerfile)
        self.assertIn('CMD ["python", "-u", "omnivoice/docker_entrypoint.py"]', dockerfile)

    def test_docker_images_include_a_verifiable_compliance_bundle(self) -> None:
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        for expected in (
            "NOTICE THIRD_PARTY_NOTICES.md",
            "third_party/README.md /app/third_party/README.md",
            "install_compliance_bundle.py",
            "verify_compliance_bundle.py",
            "OMNIVOICE_MODEL_REVISION=c5fdb5ccb189668d56333f77ba2629f4cd7535f4",
            "OMNIVOICE_ASR_MODEL_REVISION=41f01f3fe87f28c78e2fbf8b568835947dd65ed9",
            "LicenseRef-OmniVoice-CC-BY-NC",
            "LicenseRef-Boson-Higgs-Audio-2-Community",
        ):
            self.assertIn(expected, dockerfile)

        notices = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        root_notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
        required_attribution = (
            "Built with Meta Llama 3",
            "Built with Higgs Materials licensed from Boson AI USA, Inc., Copyright Boson",
            "Meta Llama 3 is licensed under the Meta Llama 3 Community License",
            "Boson Higgs Audio 2 is licensed under the Boson Community License",
        )
        for expected in required_attribution:
            self.assertIn(expected, notices)
            self.assertIn(expected, root_notice)
        self.assertIn("CC-BY-NC", notices)
        self.assertIn("100,000 annual active users", notices)

        taskfile = (ROOT / "Taskfile.yml").read_text(encoding="utf-8")
        self.assertIn("compliance-test:", taskfile)
        self.assertTrue((ROOT / "scripts" / "install_compliance_bundle.py").is_file())
        self.assertTrue((ROOT / "scripts" / "verify_compliance_bundle.py").is_file())

    def test_public_docs_do_not_misrepresent_model_license(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        dockerhub = (ROOT / "docs" / "dockerhub.md").read_text(encoding="utf-8")
        for document in (readme, dockerhub):
            self.assertIn("CC-BY-NC", document)
            self.assertIn("not licensed for commercial use", document)
            self.assertIn("Third-Party Notices", document)
            self.assertIn(
                "Built with Meta Llama 3",
                document,
                msg="public documentation must carry Meta's required product attribution",
            )
            self.assertIn(
                "Built with Higgs Materials licensed from Boson AI USA, Inc.",
                document,
            )

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
        self.assertNotIn("defusedxml==0.7.1", project["dependencies"])
        self.assertIn("ssml-h-tools==0.1.0", project["dependencies"])
        self.assertEqual(project["optional-dependencies"]["torchaudio"], ["torchaudio==2.8.0"])
        self.assertNotIn("omnivoice-demo", project["scripts"])
        self.assertFalse((ROOT / "omnivoice" / "cli" / "demo.py").exists())
        self.assertIn("python-multipart==0.0.28", project["dependencies"])
        self.assertIn("VERSION", config["tool"]["hatch"]["build"]["targets"]["sdist"]["include"])
        self.assertIn("assets", config["tool"]["hatch"]["build"]["targets"]["sdist"]["include"])
        ssml_adapter = (ROOT / "omnivoice" / "service" / "ssml.py").read_text(encoding="utf-8")
        self.assertIn("from ssml_h import (", ssml_adapter)

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

    def test_ssml_h_showcase_has_reproducible_audio_examples(self) -> None:
        page = (ROOT / "examples" / "ssml-h.html").read_text(encoding="utf-8")
        self.assertIn("SSML-H Conversation Examples", page)
        self.assertIn("The shopping negotiation", page)
        self.assertNotIn("Loading source...", page)
        self.assertNotIn("data-ssml-source", page)
        self.assertIn('&lt;h:voice-definition name="Isabel"', page)
        mother_daughter = (ROOT / "examples" / "assets" / "ssml-h" / "mother-daughter.ssml").read_text(encoding="utf-8")
        for fragment in (
            'name="Isabel" age="child" pitch="high" accent="british" scope="request" seed="1476293754"',
            'name="Mother" gender="female" age="middle-aged" pitch="high" accent="british" scope="request" seed="998282591"',
            "Mommy mommy I want this",
            "Put it down please !",
            "> But, I [sigh] !</prosody>",
            "> I [sigh] ! </prosody>",
            "But I, I really really want it. I spotted it first !",
            "No, put it down right now.",
            " This is the end of this discussion !!!",
        ):
            self.assertIn(fragment, mother_daughter)
        self.assertEqual(
            re.findall(r'<break time="(\d+ms)"\s*/>', mother_daughter),
            ["500ms", "600ms", "400ms", "400ms"],
        )
        self.assertIn("https://hangrylabs.app/ns/ssml-h/1.0", page)
        self.assertIn("request seed 24680", page)
        self.assertIn('"randomize_seed":false', page)
        for slug in ("mother-daughter", "model-meeting", "moon-navigation"):
            self.assertIn(f"assets/ssml-h/{slug}.mp3", page)
            self.assertGreater((ROOT / "examples" / "assets" / "ssml-h" / f"{slug}.mp3").stat().st_size, 1_000)
            source_path = ROOT / "examples" / "assets" / "ssml-h" / f"{slug}.ssml"
            self.assertTrue(source_path.is_file())
            embedded = re.search(
                rf'<code id="{re.escape(slug)}-source">(.*?)</code>',
                page,
                flags=re.DOTALL,
            )
            self.assertIsNotNone(embedded)
            self.assertEqual(
                unescape(embedded.group(1)).strip(),
                source_path.read_text(encoding="utf-8").strip(),
            )
        self.assertTrue((ROOT / "scripts" / "generate-ssml-h-examples.py").is_file())
        highlighter = (ROOT / "examples" / "ssml-h.js").read_text(encoding="utf-8")
        self.assertIn("function highlightSsml(source)", highlighter)
        self.assertIn('class="syntax-cue"', highlighter)
        taskfile = (ROOT / "Taskfile.yml").read_text(encoding="utf-8")
        self.assertIn("generate-ssml-h-examples:", taskfile)


if __name__ == "__main__":
    unittest.main()
