import hmac

from fastapi import Depends, FastAPI, Request

from . import tts
from .errors import ApiError, handle_api_error


def make_app(token, tts_backend=None):
    """One gateway for every Oolel capability. A capability is served only if its backend is given."""
    app = FastAPI()
    app.add_exception_handler(ApiError, handle_api_error)
    capabilities = []

    def authorized(request: Request):
        sent = request.headers.get("authorization", "")
        if not token or not hmac.compare_digest(sent, f"Bearer {token}"):
            raise ApiError(401, "UNAUTHORIZED", "Missing or wrong bearer token.")

    if tts_backend:
        app.include_router(tts.router(tts_backend), dependencies=[Depends(authorized)])
        capabilities.append("text-to-speech")

    @app.get("/health")
    def health():
        return {"ok": True, "capabilities": capabilities}

    return app
