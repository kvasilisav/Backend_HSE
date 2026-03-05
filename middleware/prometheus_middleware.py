import re
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from metrics import REQUEST_COUNT, REQUEST_DURATION


def _normalize_path(path: str) -> str:
    if re.match(r"^/moderation_result/\d+$", path):
        return "/moderation_result/{task_id}"
    return path


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path == "/metrics":
            return await call_next(request)
        method = request.method
        endpoint = _normalize_path(request.url.path)
        start = time.perf_counter()
        response = await call_next(request)
        duration = time.perf_counter() - start
        REQUEST_COUNT.labels(
            method=method,
            endpoint=endpoint,
            status=response.status_code,
        ).inc()
        REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        return response
