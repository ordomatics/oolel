from fastapi.responses import JSONResponse


class ApiError(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message


def handle_api_error(_request, exc):
    return JSONResponse({"error": {"code": exc.code, "message": exc.message}}, status_code=exc.status)


async def read_body(request):
    """JSON or form, whichever the caller sent."""
    if "json" in request.headers.get("content-type", ""):
        body = await request.json()
    else:
        body = dict(await request.form())
    if not isinstance(body, dict):
        raise ApiError(400, "INVALID_REQUEST", "Expected an object.")
    return body
