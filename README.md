# oolel

Wolof speech and language services on the open [Oolel models](https://huggingface.co/soynade-research)
(AGPL-3.0), served from [Modal](https://modal.com). One gateway, one bearer token. It answers the
routes `llm_soynade` calls, so that provider only needs its `api_base` and API key pointed here.

| Capability | Route | Model | Status |
|---|---|---|---|
| Text-to-speech | `POST /v1/text-to-speech` | Oolel-Voices | live |
| Speech-to-text | `POST /v1/audio/transcriptions` | Wolof-HuBERT-CTC | live |
| Translation | `POST /v1/translations` | Oolel | planned |

`GET /health` is open and lists the capabilities being served. Everything else needs
`Authorization: Bearer <token>`. Errors are `{"error": {"code", "message"}}`, the shape the provider reads.

## Text-to-speech

`text`, optional `output_format` (wav|mp3), `seed`, `exaggeration`, `temperature`, `cfg_weight`; JSON or form.
Returns the audio. Wolof only (`language` other than `wo` is a 400) and one fixed voice cloned from
`voice.wav`; any `reference_audio` is a 400. English and French from these weights are unusable: keep the
Soynade API for them. CPU only: about 20 s for a short line, one line at a time per container, two
containers at most, idle containers stop after 5 minutes (the next call then waits about a minute).

## Speech-to-text

Multipart `file` (any audio ffmpeg reads, up to 25 MB and 10 minutes), optional `language` (only `wo`),
`response_format` (json|text). `temperature` is accepted and ignored: the recognizer is deterministic.
Returns `{"text", "language", "duration"}`. Wolof only. The model card reports a word error rate of about
36%, so treat the text as a draft. Long audio is read in 30 s windows. CPU only.

## Adding a capability

1. A router in `src/oolel/<name>.py` that takes a backend callable, as `tts.py` does.
2. Register it in `app.py` (`make_app` serves a capability only when it is given a backend).
3. A Modal class in `modal_app.py` with its own image and resources (a GPU for the larger models),
   and pass it to `make_app`.

## Deploy and test

    modal secret create oolel OOLEL_TOKEN=<token>   # the token you put in the provider's API key
    PYTHONPATH=src modal deploy modal_app.py

    pip install -e ".[test]" && pytest
