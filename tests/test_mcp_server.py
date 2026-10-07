from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from fastapi import FastAPI
from fastapi.testclient import TestClient
from mcp.server.mcpserver.exceptions import ToolError

from omnivoice import app as runtime
from omnivoice.artifacts import ArtifactStore
from omnivoice.mcp_server import attach_mcp, create_mcp_server
from omnivoice.service.schemas import TTSRequest
from omnivoice.settings import RuntimeSettingsStore


class FakeRuntime:
    APP_VERSION = "test"

    def __init__(self, settings_path: Path) -> None:
        self.RUNTIME_SETTINGS = RuntimeSettingsStore(settings_path)


def simple_arguments(**overrides):
    values = {
        "text": "Hello from MCP.",
        "language": "auto",
        "voice_id": "auto",
        "ttl_seconds": 300,
    }
    values.update(overrides)
    return values


class MCPServerTests(unittest.IsolatedAsyncioTestCase):
    async def test_advanced_clone_creation_persists_description_and_type(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_directory = root / "input"
            input_directory.mkdir()
            (input_directory / "sample.wav").write_bytes(b"RIFF-test-audio")
            profile = {
                "id": "narrator",
                "description": "Warm narrator for product demonstrations.",
                "profile_type": "cloned",
                "language": "English",
                "seed": 123,
                "randomize_seed": False,
                "has_transcript": True,
            }
            with (
                patch("omnivoice.app.UI_UPLOAD_DIR", root / "uploads"),
                patch("omnivoice.app.load_openai_voice_profiles", return_value={}),
                patch(
                    "omnivoice.app.reference_audio_analysis",
                    return_value={"duration_seconds": 6.0, "warnings": []},
                ),
                patch(
                    "omnivoice.app.save_openai_voice_profile",
                    return_value="narrator",
                ) as save_profile,
                patch("omnivoice.app.voice_profile_payloads", return_value=[profile]),
                patch("omnivoice.app.clear_voice_clone_prompt_cache"),
            ):
                server = create_mcp_server(
                    artifact_store=ArtifactStore(root / "output"),
                    base_url="http://testserver",
                    advanced=True,
                    input_directory=input_directory,
                )
                result = await server.call_tool(
                    "create_cloned_voice_profile",
                    {
                        "name": "Narrator",
                        "description": profile["description"],
                        "audio_location": "sample.wav",
                        "reference_text": "This is the exact transcript.",
                        "language": "English",
                        "seed": 123,
                        "replace": False,
                    },
                )

        self.assertFalse(result.is_error)
        self.assertEqual(result.structured_content["voice"], profile)
        saved = save_profile.call_args.args
        self.assertEqual(saved[0], "narrator")
        self.assertEqual(saved[2:6], ("This is the exact transcript.", "English", 123, False))
        self.assertEqual(saved[6:], (profile["description"], "cloned"))

    async def test_simple_complete_synthesis_honors_allocator_cleanup_setting(self) -> None:
        waveform = np.zeros(24_000)
        with (
            patch.object(
                runtime,
                "synthesize_payload",
                return_value=("mp3", 24_000, waveform, 42),
            ),
            patch.object(runtime, "warn_if_cpu_memory_tight"),
            patch.object(runtime, "EMPTY_CUDA_CACHE_AFTER_REQUEST", True),
            patch.object(runtime, "clear_cuda_allocator_cache") as clear_cache,
        ):
            result = runtime.synthesize_complete_payload(TTSRequest(text="Hello."))

        self.assertEqual(result[:2], ("mp3", 24_000))
        self.assertIs(result[2], waveform)
        self.assertEqual(result[3:], (42, []))
        clear_cache.assert_called_once_with(runtime.RESET_CUDA_PEAK_AFTER_CACHE_CLEAR)

    async def test_compact_and_advanced_catalogs_are_deliberately_separate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ArtifactStore(Path(directory) / "output")
            compact = create_mcp_server(
                artifact_store=store,
                base_url="http://testserver",
                advanced=False,
                input_directory=Path(directory) / "input",
            )
            advanced = create_mcp_server(
                artifact_store=store,
                base_url="http://testserver",
                advanced=True,
                input_directory=Path(directory) / "input",
            )
            compact_tools = {tool.name: tool for tool in await compact.list_tools()}
            advanced_tools = {tool.name: tool for tool in await advanced.list_tools()}

        core = {
            "get_health",
            "find_languages",
            "get_cloned_voices_catalog",
            "inspect_speech",
            "talk_simple",
        }
        self.assertEqual(set(compact_tools), core)
        self.assertEqual(
            set(advanced_tools),
            core
            | {
                "talk_advanced",
                "create_cloned_voice_profile",
                "create_designed_voice_profile",
                "delete_voice_profile",
            },
        )
        simple_schema = compact_tools["talk_simple"].input_schema
        self.assertEqual(set(simple_schema["properties"]), set(simple_arguments()))
        self.assertEqual(simple_schema["required"], ["text"])
        self.assertEqual(simple_schema["properties"]["language"]["default"], "auto")
        self.assertEqual(simple_schema["properties"]["voice_id"]["default"], "auto")
        self.assertEqual(simple_schema["properties"]["ttl_seconds"]["default"], 3600)
        self.assertIn("verbatim", simple_schema["properties"]["text"]["description"])
        self.assertNotIn("audio", simple_schema["properties"])
        self.assertIn("Preferred speech tool", compact_tools["talk_simple"].description)

    async def test_missing_clone_reference_error_explains_both_recovery_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            server = create_mcp_server(
                artifact_store=ArtifactStore(root / "output"),
                base_url="http://testserver",
                advanced=True,
                input_directory=root / "input",
            )
            with self.assertRaises(ToolError) as error:
                await server.call_tool(
                    "create_cloned_voice_profile",
                    {
                        "name": "missing-reference",
                        "description": "Diagnostic voice.",
                        "audio_location": "missing.wav",
                        "reference_text": "Missing reference.",
                        "language": "English",
                        "seed": 42,
                        "replace": False,
                    },
                )

        message = str(error.exception)
        self.assertIn("MCP input directory", message)
        self.assertIn("HTTP(S) URL", message)

    async def test_catalog_returns_only_saved_voice_ids_and_descriptions(self) -> None:
        profiles = [
            {
                "id": "roxy",
                "description": "Warm technical narrator.",
                "profile_type": "cloned",
                "language": "english",
                "seed": 123,
                "randomize_seed": False,
                "has_transcript": True,
            }
        ]
        with tempfile.TemporaryDirectory() as directory, patch(
            "omnivoice.app.voice_profile_payloads", return_value=profiles
        ):
            server = create_mcp_server(
                artifact_store=ArtifactStore(Path(directory) / "output"),
                base_url="http://testserver",
                advanced=False,
                input_directory=Path(directory) / "input",
            )
            result = await server.call_tool("get_cloned_voices_catalog", {})

        self.assertFalse(result.is_error)
        self.assertEqual(result.structured_content["count"], 1)
        self.assertEqual(result.structured_content["voices"][0]["id"], "roxy")
        self.assertEqual(
            result.structured_content["voices"][0]["description"],
            "Warm technical narrator.",
        )
        self.assertNotIn("ref_audio", result.structured_content["voices"][0])

    async def test_simple_generation_returns_link_metadata_not_audio(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ArtifactStore(Path(directory) / "output")
            with (
                patch(
                    "omnivoice.app.synthesize_complete_payload",
                    return_value=("mp3", 24_000, np.zeros(24_000), 77, []),
                ),
                patch("omnivoice.mcp_server.encode_audio_bytes", return_value=b"mp3-data"),
            ):
                server = create_mcp_server(
                    artifact_store=store,
                    base_url="http://testserver",
                    advanced=False,
                    input_directory=Path(directory) / "input",
                )
                result = await server.call_tool("talk_simple", simple_arguments())

            payload = result.structured_content
            token = payload["download_url"].rsplit("/", 1)[1]
            artifact, path = store.resolve(token)
            generated_audio = path.read_bytes()

        self.assertFalse(result.is_error)
        self.assertEqual(generated_audio, b"mp3-data")
        self.assertEqual(payload["seed"], 77)
        self.assertEqual(artifact.mime_type, "audio/mpeg")
        self.assertNotIn("text", payload)
        self.assertNotIn("data", payload)
        self.assertTrue(all(block.type == "text" for block in result.content))


class MCPTransportTests(unittest.TestCase):
    def test_compact_and_advanced_gates_follow_independent_persisted_settings(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = FakeRuntime(root / "settings.json")
            store = ArtifactStore(root / "output")
            app = FastAPI()
            with patch.dict(
                "os.environ",
                {
                    "OMNIVOICE_MCP_ALLOWED_HOSTS": "testserver",
                    "OMNIVOICE_MCP_BASE_URL": "http://testserver",
                },
            ):
                attach_mcp(api_app=app, runtime=fake, artifact_store=store)
                request = {
                    "headers": {
                        "Accept": "application/json, text/event-stream",
                        "MCP-Protocol-Version": "2025-06-18",
                    },
                    "json": {
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "initialize",
                        "params": {
                            "protocolVersion": "2025-06-18",
                            "capabilities": {},
                            "clientInfo": {"name": "test-client", "version": "1.0"},
                        },
                    },
                }
                with TestClient(app) as client:
                    compact_disabled = client.post("/mcp/", **request)
                    advanced_disabled = client.post("/mcp/advanced/", **request)
                    fake.RUNTIME_SETTINGS.set_mcp_access(
                        enabled=True, advanced_enabled=False
                    )
                    compact_enabled = client.post("/mcp/", **request)
                    advanced_still_disabled = client.post("/mcp/advanced/", **request)
                    fake.RUNTIME_SETTINGS.set_mcp_access(
                        enabled=True, advanced_enabled=True
                    )
                    advanced_enabled = client.post("/mcp/advanced/", **request)

        self.assertEqual(compact_disabled.status_code, 403)
        self.assertEqual(advanced_disabled.status_code, 403)
        self.assertEqual(compact_enabled.status_code, 200)
        self.assertEqual(advanced_still_disabled.status_code, 403)
        self.assertEqual(advanced_enabled.status_code, 200)
        self.assertEqual(
            compact_enabled.json()["result"]["serverInfo"]["name"],
            "omnivoicetts-compact",
        )
        self.assertEqual(
            advanced_enabled.json()["result"]["serverInfo"]["name"],
            "omnivoicetts-advanced",
        )


if __name__ == "__main__":
    unittest.main()
