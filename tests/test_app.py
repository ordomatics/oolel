from fastapi.testclient import TestClient

from oolel.app import make_app


def test_health_needs_no_token_and_lists_what_is_served():
    assert TestClient(make_app("t", tts_backend=lambda *a, **k: b"")).get("/health").json() == {
        "ok": True, "capabilities": ["text-to-speech"]}


def test_a_capability_without_a_backend_is_not_served():
    client = TestClient(make_app("t"))
    assert client.get("/health").json()["capabilities"] == []
    assert client.post("/v1/text-to-speech", json={"text": "a"}, headers={"Authorization": "Bearer t"}).status_code == 404
