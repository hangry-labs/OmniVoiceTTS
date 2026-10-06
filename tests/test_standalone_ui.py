from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from omnivoice.standalone_ui.gpu import read_gpu_stats
from omnivoice.standalone_ui.server import _read_version_file, attach_ui


class StandaloneUiTests(unittest.TestCase):
    @staticmethod
    def backend_app() -> FastAPI:
        backend = FastAPI()

        @backend.get("/tts/ping")
        async def ping() -> dict[str, str]:
            return {"msg": "pong"}

        return backend

    def test_product_shell_and_local_assets_are_available(self) -> None:
        gpu_payload = {
            "gpus": [],
            "history": {},
            "sample_interval_seconds": 1,
            "idle_timeout_seconds": 60,
        }
        with patch(
            "omnivoice.standalone_ui.server.GPU_MONITOR.request_snapshot",
            return_value=gpu_payload,
        ):
            with TestClient(attach_ui(api_app=self.backend_app())) as client:
                responses = {
                    path: client.get(path)
                    for path in (
                        "/",
                        "/static/app.js",
                        "/static/audio-editor.js",
                        "/static/audio-utils.js",
                        "/static/i18n.js",
                        "/static/styles.css",
                        "/static/vendor/lucide/lucide.css",
                        "/static/vendor/lucide/lucide.woff2",
                        "/static/vendor/wavesurfer/wavesurfer.esm.js",
                        "/static/vendor/wavesurfer/plugins/regions.esm.js",
                        "/assets/omnivoice_logo_horizontal.webp",
                        "/assets/omnivoice_favicon.webp",
                        "/assets/hangrylabs_logo.webp",
                        "/system/gpu",
                        "/tts/ping",
                    )
                }

        self.assertTrue(all(response.status_code == 200 for response in responses.values()))
        index = responses["/"]
        self.assertIn('src="/assets/omnivoice_logo_horizontal.webp"', index.text)
        self.assertIn('href="/assets/omnivoice_favicon.webp"', index.text)
        self.assertIn('href="https://hangrylabs.app/"', index.text)
        self.assertLess(index.text.index('class="labs-signature"'), index.text.index('class="collapsed-mascot"'))
        self.assertIn('data-tab="generate"', index.text)
        self.assertIn('data-tab="stream"', index.text)
        self.assertIn('data-tab="voices"', index.text)
        self.assertIn('data-tab="api"', index.text)
        self.assertIn('data-tab="system"', index.text)
        self.assertIn('id="profile-audio-preview"', index.text)
        self.assertIn('id="delete-profile-dialog"', index.text)
        self.assertIn('id="advanced-generation"', index.text)
        self.assertIn('id="normalize-text"', index.text)
        self.assertIn('id="normalization-preview"', index.text)
        self.assertIn('data-input-type="ssml"', index.text)
        self.assertIn('data-input-type="ssml-h"', index.text)
        self.assertLess(index.text.index('id="advanced-generation"'), index.text.index('<section class="content-panel">'))
        self.assertIn('class="voice-form-grid"', index.text)
        self.assertIn('<div class="system-controls">', index.text)
        system_grid = index.text[index.text.index('<div class="system-grid">'):]
        self.assertLess(system_grid.index('<div class="system-controls">'), system_grid.index('id="gpu-output"'))
        self.assertLess(system_grid.index('id="clear-cache"'), system_grid.index('id="save-defaults"'))
        self.assertLess(system_grid.index('id="save-defaults"'), system_grid.index('id="readiness-output"'))
        self.assertNotIn("{{UI_VERSION}}", index.text)
        self.assertIn(f"UI v{_read_version_file()}", index.text)
        self.assertEqual(responses["/system/gpu"].headers["cache-control"], "no-store")
        self.assertEqual(responses["/assets/omnivoice_favicon.webp"].headers["content-type"], "image/webp")
        self.assertEqual(responses["/static/vendor/lucide/lucide.woff2"].headers["content-type"], "font/woff2")
        self.assertEqual(responses["/tts/ping"].json(), {"msg": "pong"})

    def test_localized_routes_use_existing_catalog_and_direction(self) -> None:
        with TestClient(attach_ui(api_app=self.backend_app())) as client:
            polish = client.get("/pl")
            arabic = client.get("/ar")

        self.assertEqual(polish.status_code, 200)
        self.assertIn('<html lang="pl" dir="ltr">', polish.text)
        self.assertIn('"locale":"pl"', polish.text)
        self.assertIn('"tabs.generate":"Generuj"', polish.text)
        self.assertEqual(arabic.status_code, 200)
        self.assertIn('<html lang="ar" dir="rtl">', arabic.text)

    def test_development_mode_disables_asset_caching(self) -> None:
        with patch.dict("os.environ", {"OMNIVOICE_UI_DEV": "1"}):
            with TestClient(attach_ui(api_app=self.backend_app())) as client:
                responses = [client.get(path) for path in ("/", "/pl", "/static/styles.css", "/assets/omnivoice_favicon.webp")]

        self.assertTrue(all(response.headers["cache-control"] == "no-store" for response in responses))

    def test_browser_code_owns_stream_cleanup_and_demand_driven_gpu_polling(self) -> None:
        with TestClient(attach_ui(api_app=self.backend_app())) as client:
            script = client.get("/static/app.js").text
            stylesheet = client.get("/static/styles.css").text

        self.assertIn("class IncrementalAudioPlayback", script)
        self.assertIn("new AudioEditor($('#generate-output')", script)
        self.assertIn("new AudioEditor($('#stream-output')", script)
        self.assertIn("new AudioEditor($('#profile-audio-preview')", script)
        self.assertIn("state.streamAbort?.abort()", script)
        self.assertIn("function startGpuMonitor()", script)
        self.assertIn("function stopGpuMonitor()", script)
        self.assertIn("document.addEventListener('visibilitychange'", script)
        self.assertIn("GPU_HISTORY_RETENTION_MS = 10 * 60 * 1000", script)
        self.assertIn("function nativeLanguageLabel(id, fallback)", script)
        self.assertIn("input_type: state.inputType", script)
        self.assertIn("/tts/ssml/capabilities", script)
        self.assertIn("/tts/text/normalize", script)
        self.assertIn("normalize_text: controls.normalize_text && state.inputType === 'text'", script)
        self.assertIn(
            '<voice name="Elisabeth"><prosody rate="slow">Yes, all preparations are complete.</prosody></voice>',
            script,
        )
        self.assertNotIn('<voice name="Elisabeth">Yes. <prosody', script)
        self.assertIn("languages.languages", script)
        self.assertIn(".generate-action-row, .generate-action-row .primary-button { width: 100%; }", stylesheet)
        self.assertIn("grid-template-columns: minmax(700px, 1.45fr) minmax(340px, 0.75fr)", stylesheet)
        self.assertIn("grid-template-columns: minmax(300px, 0.8fr) minmax(420px, 1.2fr)", stylesheet)
        self.assertIn("@media (max-width: 560px)", stylesheet)

    @patch("omnivoice.standalone_ui.gpu.subprocess.run")
    def test_gpu_monitor_parses_optional_nvidia_metrics(self, run) -> None:
        run.return_value.returncode = 0
        run.return_value.stdout = (
            "0, NVIDIA RTX Test, 37, N/A, 4096, 16384, 52, [N/A], 61.5, 300, "
            "2400, 3000, 13000, 14000, P2, 5, 16\n"
        )

        stats = read_gpu_stats()

        self.assertEqual(stats[0]["utilization"], 37)
        self.assertIsNone(stats[0]["memory_utilization"])
        self.assertIsNone(stats[0]["fan_speed"])
        self.assertEqual(stats[0]["memory_total"], 16384)
        self.assertEqual(stats[0]["power"], 61.5)


if __name__ == "__main__":
    unittest.main()
