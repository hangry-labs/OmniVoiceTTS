from __future__ import annotations

import unittest

import httpx

from omnivoice.remote_audio import RemoteAudioError, RemoteAudioFetcher


class RemoteAudioFetcherTests(unittest.IsolatedAsyncioTestCase):
    async def test_download_is_bounded(self) -> None:
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"12345", request=request)
        )
        fetcher = RemoteAudioFetcher(
            max_bytes=4,
            allowed_hosts=["audio.example"],
            transport=transport,
            resolver=lambda host, port: ["8.8.8.8"],
        )
        with self.assertRaisesRegex(RemoteAudioError, "limit"):
            await fetcher.fetch("https://audio.example/reference.wav")

    async def test_redirect_destination_is_revalidated(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                302,
                headers={"location": "http://169.254.169.254/metadata.wav"},
                request=request,
            )

        fetcher = RemoteAudioFetcher(
            max_bytes=1024,
            allowed_hosts=["*"],
            transport=httpx.MockTransport(handler),
            resolver=lambda host, port: [host if host[0].isdigit() else "8.8.8.8"],
        )
        with self.assertRaisesRegex(RemoteAudioError, "link-local"):
            await fetcher.fetch("https://audio.example/reference.wav")


if __name__ == "__main__":
    unittest.main()
