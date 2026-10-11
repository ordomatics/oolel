import io
import math
import struct
import wave

from fastapi.testclient import TestClient

from oolel.app import make_app

AUTH = {"Authorization": "Bearer secret"}
heard = []


def fake(pcm):
    heard.append(len(pcm))
    return " jërëjëf "


client = TestClient(make_app("secret", stt_backend=fake))


def tone(seconds=1.0, rate=8000):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(8000 * math.sin(i / 10))) for i in range(int(rate * seconds))))
    return buffer.getvalue()


def post(files=None, data=None, headers=AUTH):
    return client.post("/v1/audio/transcriptions", files=files if files is not None else {"file": ("a.wav", tone(), "audio/wav")},
                       data=data or {}, headers=headers)


def test_audio_is_resampled_and_the_text_comes_back_trimmed():
    heard.clear()
    response = post(data={"language": "wo", "response_format": "json", "temperature": "0.0"})
    assert response.json() == {"text": "jërëjëf", "language": "wo", "duration": 1.0}
    assert heard == [16000 * 4]


def test_plain_text_format():
    response = post(data={"response_format": "text"})
    assert response.text == "jërëjëf" and response.headers["content-type"].startswith("text/plain")


def test_no_token_is_refused_without_transcribing():
    heard.clear()
    assert post(headers={}).status_code == 401
    assert not heard


def test_only_wolof_is_understood():
    response = post(data={"language": "fr"})
    assert response.status_code == 400 and response.json()["error"]["code"] == "UNSUPPORTED_LANGUAGE"


def test_bad_input_is_a_400():
    assert post(files={"file": ("a.wav", b"not audio", "audio/wav")}).json()["error"]["code"] == "INVALID_AUDIO"
    assert post(data={"response_format": "srt"}).json()["error"]["code"] == "INVALID_FORMAT"
    assert post(files={}).status_code == 400
