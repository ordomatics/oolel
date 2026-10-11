import subprocess

from fastapi import APIRouter, Request, Response

from .errors import ApiError, read_body

LANGUAGE = "wo"
MAX_CHARS = 1000
LIMITS = {"exaggeration": (0.1, 0.5, 0.3), "temperature": (0.1, 0.5, 0.3), "cfg_weight": (0.0, 1.0, 0.5)}
FORMATS = {"wav": "audio/wav", "mp3": "audio/mpeg"}


def _mp3(wav_bytes):
    done = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-f", "mp3", "pipe:1"],
                          input=wav_bytes, capture_output=True, check=True)
    return done.stdout


def router(synthesize):
    """`synthesize(text, seed, exaggeration, temperature, cfg_weight)` returns WAV bytes."""
    api = APIRouter()

    @api.post("/v1/text-to-speech")
    async def text_to_speech(request: Request):
        body = await read_body(request)
        text = str(body.get("text") or "").strip()
        if not text or len(text) > MAX_CHARS:
            raise ApiError(400, "INVALID_TEXT", f"text must be 1 to {MAX_CHARS} characters.")
        if body.get("language", LANGUAGE) != LANGUAGE:
            raise ApiError(400, "UNSUPPORTED_LANGUAGE", "Text-to-speech only speaks Wolof (wo).")
        if body.get("reference_audio"):
            raise ApiError(400, "UNSUPPORTED_REFERENCE", "Text-to-speech speaks in one fixed voice.")
        fmt = body.get("output_format", "wav")
        if fmt not in FORMATS:
            raise ApiError(400, "INVALID_FORMAT", "output_format must be wav or mp3.")

        values = {}
        for key, (low, high, default) in LIMITS.items():
            try:
                value = float(body.get(key, default))
            except (TypeError, ValueError):
                raise ApiError(400, "INVALID_PARAMETER", f"{key} must be a number.")
            if not low <= value <= high:
                raise ApiError(400, "INVALID_PARAMETER", f"{key} must be between {low} and {high}.")
            values[key] = value
        try:
            seed = int(body["seed"]) if body.get("seed") not in (None, "") else None
        except (TypeError, ValueError):
            raise ApiError(400, "INVALID_PARAMETER", "seed must be an integer.")

        audio = synthesize(text, seed, **values)
        return Response(_mp3(audio) if fmt == "mp3" else audio, media_type=FORMATS[fmt])

    return api
