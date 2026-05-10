"""Request-id propagation + structured-log binding."""

import time
import uuid

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Generate or propagate `X-Request-Id`, bind to structlog contextvars,
    log request start/end with timing."""

    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=rid,
            method=request.method,
            path=request.url.path,
        )
        log = structlog.get_logger("http")
        started = time.time()
        log.info("request_started")
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            log.error("request_failed", err=str(exc))
            raise
        duration_ms = int((time.time() - started) * 1000)
        response.headers["x-request-id"] = rid
        log.info("request_completed", status=response.status_code, duration_ms=duration_ms)
        return response
