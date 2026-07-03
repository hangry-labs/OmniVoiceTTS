"""Small dependency-free client for the OmniVoiceTTS HTTP API."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class OmniVoiceTTSClientError(RuntimeError):
    """Raised when the OmniVoiceTTS API returns an error or cannot be reached."""


@dataclass(frozen=True)
class AudioResponse:
    """Audio bytes returned by an OmniVoiceTTS synthesis endpoint."""

    content: bytes
    media_type: str
    headers: dict[str, str]

    @property
    def filename(self) -> str | None:
        disposition = self.headers.get("content-disposition", "")
        for part in disposition.split(";"):
            part = part.strip()
            if part.startswith("filename="):
                return part.split("=", 1)[1].strip('"')
        return None

    def save(self, path: str | Path) -> Path:
        output_path = Path(path)
        output_path.write_bytes(self.content)
        return output_path


class OmniVoiceTTSClient:
    """Python client for a running OmniVoiceTTS UI/API server."""

    def __init__(self, base_url: str = "http://localhost:7861", timeout: float = 300.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def ping(self) -> dict[str, Any]:
        return self._json("GET", "/tts/ping")

    def status(self) -> dict[str, Any]:
        return self._json("GET", "/tts/status")

    def defaults(self) -> dict[str, Any]:
        return self._json("GET", "/tts/defaults")

    def formats(self) -> dict[str, Any]:
        return self._json("GET", "/tts/formats")

    def languages(self) -> dict[str, Any]:
        return self._json("GET", "/tts/languages")

    def purge(self, device: str | None = None) -> dict[str, Any]:
        payload = {} if device is None else {"device": device}
        return self._json("POST", "/tts/purge", payload)

    def generate(
        self,
        text: str,
        language: str | None = None,
        voice: str | None = None,
        instruct: str | None = None,
        ref_audio: str | None = None,
        ref_text: str | None = None,
        speed: float | None = 1.0,
        duration: float | None = None,
        device: str = "auto",
        output_format: str = "wav",
        num_step: int = 32,
        guidance_scale: float = 2.0,
        pad_duration: float = 0.1,
        fade_duration: float = 0.1,
    ) -> AudioResponse:
        return self._audio(
            "/tts/generate",
            {
                "text": text,
                "language": language,
                "voice": voice,
                "instruct": instruct,
                "ref_audio": ref_audio,
                "ref_text": ref_text,
                "speed": speed,
                "duration": duration,
                "device": device,
                "output_format": output_format,
                "num_step": num_step,
                "guidance_scale": guidance_scale,
                "pad_duration": pad_duration,
                "fade_duration": fade_duration,
            },
        )

    def convert(self, **kwargs: Any) -> AudioResponse:
        return self._audio("/tts/convert", kwargs)

    def openai_speech(
        self,
        input: str,
        model: str = "omnivoice",
        voice: str = "default",
        response_format: str = "mp3",
        speed: float = 1.0,
        **kwargs: Any,
    ) -> AudioResponse:
        payload = {
            "model": model,
            "input": input,
            "voice": voice,
            "response_format": response_format,
            "speed": speed,
            **kwargs,
        }
        return self._audio("/v1/audio/speech", payload)

    def openai_models(self) -> dict[str, Any]:
        return self._json("GET", "/v1/models")

    def _json(self, method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self._request(method, path, payload)
        if not response:
            return {}
        return json.loads(response.decode("utf-8"))

    def _audio(self, path: str, payload: dict[str, Any]) -> AudioResponse:
        content, media_type, headers = self._request_with_headers("POST", path, payload)
        return AudioResponse(content=content, media_type=media_type, headers=headers)

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> bytes:
        content, _, _ = self._request_with_headers(method, path, payload)
        return content

    def _request_with_headers(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> tuple[bytes, str, dict[str, str]]:
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Accept": "*/*"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=self.timeout) as response:
                response_headers = {key.lower(): value for key, value in response.headers.items()}
                media_type = response_headers.get("content-type", "application/octet-stream").split(";", 1)[0]
                return response.read(), media_type, response_headers
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise OmniVoiceTTSClientError(f"OmniVoiceTTS API error {exc.code}: {detail}") from exc
        except URLError as exc:
            raise OmniVoiceTTSClientError(f"Could not reach OmniVoiceTTS API at {url}: {exc.reason}") from exc
        except TimeoutError as exc:
            raise OmniVoiceTTSClientError(f"Timed out waiting for OmniVoiceTTS API at {url}") from exc
