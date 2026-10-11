from fastapi.testclient import TestClient

from oolel.app import make_app

TOKEN = "secret"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
calls = []


def fake(text, seed, **values):
    calls.append((text, seed, values))
    return b"RIFFfake"


client = TestClient(make_app(TOKEN, tts_backend=fake))


def post(body=None, headers=AUTH):
    return client.post("/v1/text-to-speech", json=body if body is not None else {"text": "Jërëjëf"}, headers=headers)


def test_audio_comes_back_with_the_defaults():
    calls.clear()
    response = post()
    assert response.status_code == 200 and response.content == b"RIFFfake"
    assert response.headers["content-type"] == "audio/wav"
    assert calls == [("Jërëjëf", None, {"exaggeration": 0.3, "temperature": 0.3, "cfg_weight": 0.5})]


def test_the_form_encoding_the_odoo_module_uses_is_read_too():
    calls.clear()
    response = client.post("/v1/text-to-speech", data={"text": "Jërëjëf", "language": "wo", "seed": "7", "exaggeration": "0.2"}, headers=AUTH)
    assert response.status_code == 200
    assert calls[0][1] == 7 and calls[0][2]["exaggeration"] == 0.2


def test_no_or_wrong_token_is_refused_without_synthesizing():
    calls.clear()
    assert post(headers={}).status_code == 401
    assert post(headers={"Authorization": "Bearer nope"}).status_code == 401
    assert not calls


def test_only_wolof_is_spoken():
    for language in ("en", "fr"):
        response = post({"text": "Hello", "language": language})
        assert response.status_code == 400
        assert response.json()["error"]["code"] == "UNSUPPORTED_LANGUAGE"


def test_a_reference_voice_is_refused():
    assert post({"text": "Jërëjëf", "reference_audio": "AAAA"}).json()["error"]["code"] == "UNSUPPORTED_REFERENCE"


def test_bad_input_is_a_400():
    for body in ({"text": ""}, {"text": "x" * 1001}, {"text": "a", "output_format": "ogg"},
                 {"text": "a", "temperature": 9}, {"text": "a", "exaggeration": "loud"}, {"text": "a", "seed": "x"}):
        assert post(body).status_code == 400, body
