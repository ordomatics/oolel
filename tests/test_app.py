from fastapi.testclient import TestClient

from oolel.app import make_app


def test_health_needs_no_token_and_lists_what_is_served():
    assert TestClient(make_app("t", tts_backend=lambda *a, **k: b"")).get("/health").json() == {
        "ok": True, "capabilities": ["text-to-speech"]}


def test_a_capability_without_a_backend_is_not_served():
    client = TestClient(make_app("t"))
    assert client.get("/health").json()["capabilities"] == []
    assert client.post("/v1/text-to-speech", json={"text": "a"}, headers={"Authorization": "Bearer t"}).status_code == 404


def test_a_slow_backend_does_not_block_the_event_loop():
    import asyncio
    import time

    import httpx

    def slow(*a, **k):
        time.sleep(1)
        return b"RIFF"

    async def run():
        transport = httpx.ASGITransport(app=make_app("t", tts_backend=slow))
        async with httpx.AsyncClient(transport=transport, base_url="http://x") as client:
            synth = asyncio.create_task(client.post("/v1/text-to-speech", json={"text": "a"},
                                                    headers={"Authorization": "Bearer t"}))
            start = time.monotonic()
            await asyncio.sleep(0.2)
            await client.get("/health")
            waited = time.monotonic() - start
            await synth
            return waited

    assert asyncio.run(run()) < 0.5
