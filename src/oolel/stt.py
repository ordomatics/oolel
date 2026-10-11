import subprocess

from fastapi import APIRouter, Form, Request, Response, UploadFile

from .errors import ApiError

LANGUAGE = "wo"
SAMPLE_RATE = 16000
MAX_BYTES = 25 * 1024 * 1024
MAX_SECONDS = 600


def _pcm(data):
    """Any audio the caller sends, as 16 kHz mono float32."""
    done = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-f", "f32le", "-ac", "1",
                           "-ar", str(SAMPLE_RATE), "pipe:1"], input=data, capture_output=True)
    if done.returncode or not done.stdout:
        raise ApiError(400, "INVALID_AUDIO", "The file could not be read as audio.")
    return done.stdout


def router(transcribe):
    """`transcribe(pcm_f32le_16khz_bytes)` returns the text."""
    api = APIRouter()

    @api.post("/v1/audio/transcriptions")
    async def transcriptions(request: Request, file: UploadFile | None = None, language: str | None = Form(None),
                             response_format: str = Form("json"), temperature: float = Form(0.0)):
        if file is None:
            raise ApiError(400, "INVALID_REQUEST", "A file is required.")
        if language not in (None, "", LANGUAGE):
            raise ApiError(400, "UNSUPPORTED_LANGUAGE", "Speech-to-text only understands Wolof (wo).")
        if response_format not in ("json", "text"):
            raise ApiError(400, "INVALID_FORMAT", "response_format must be json or text.")
        data = await file.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ApiError(413, "FILE_TOO_LARGE", f"The file is over {MAX_BYTES // 1024 // 1024} MB.")

        pcm = _pcm(data)
        seconds = len(pcm) / (SAMPLE_RATE * 4)
        if seconds > MAX_SECONDS:
            raise ApiError(400, "AUDIO_TOO_LONG", f"The audio is over {MAX_SECONDS} seconds.")
        text = transcribe(pcm).strip()
        if response_format == "text":
            return Response(text, media_type="text/plain")
        return {"text": text, "language": LANGUAGE, "duration": round(seconds, 2)}

    return api
