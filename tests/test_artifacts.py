from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from omnivoice.artifacts import (
    ArtifactExpiredError,
    ArtifactNotFoundError,
    ArtifactStore,
)


def create_artifact(store: ArtifactStore, *, now: float = 1000):
    return store.create(
        b"audio",
        extension="mp3",
        ttl_seconds=300,
        format="mp3",
        mime_type="audio/mpeg",
        duration_seconds=1.25,
        sample_rate=24_000,
        seed=42,
        voice_mode="random",
        voice="auto",
        language="auto",
        now=now,
    )


class ArtifactStoreTests(unittest.TestCase):
    def test_artifact_metadata_never_contains_input_text_or_audio(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ArtifactStore(directory)
            artifact = create_artifact(store)
            resolved, path = store.resolve(artifact.token, now=1200)
            metadata = json.loads(
                (Path(directory) / f"{artifact.token}.json").read_text(encoding="utf-8")
            )
            audio = path.read_bytes()

        self.assertEqual(audio, b"audio")
        self.assertEqual(resolved.size_bytes, 5)
        self.assertNotIn("text", metadata)
        self.assertNotIn("audio", metadata)

    def test_expired_artifact_is_removed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ArtifactStore(directory)
            artifact = create_artifact(store)
            with self.assertRaisesRegex(ArtifactExpiredError, "expired"):
                store.resolve(artifact.token, now=1300)
            self.assertFalse(any(Path(directory).iterdir()))

    def test_invalid_token_cannot_escape_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = ArtifactStore(directory)
            with self.assertRaisesRegex(ArtifactNotFoundError, "not found"):
                store.resolve("../settings", now=1000)


if __name__ == "__main__":
    unittest.main()
