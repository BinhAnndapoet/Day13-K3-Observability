from __future__ import annotations

import re
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars

from .logging_config import get_logger

CORRELATION_ID_PATTERN = re.compile(r"^req-[0-9a-f]{8}$")

log = get_logger()


def new_correlation_id() -> str:
    return f"req-{uuid.uuid4().hex[:8]}"


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # 1. Xóa context cũ để tránh leak giữa các request
        clear_contextvars()

        # 2. Lấy từ header nếu đúng format req-<8 ký tự hex>, sai thì sinh mới.
        #    Không tin giá trị client gửi lên: chuỗi lạ sẽ làm hỏng log và truy vết.
        incoming = request.headers.get("x-request-id", "").strip()
        correlation_id = (
            incoming if CORRELATION_ID_PATTERN.fullmatch(incoming) else new_correlation_id()
        )

        # 3. Bind vào structlog context — mọi log sau đó tự động có trường này
        bind_contextvars(correlation_id=correlation_id)
        request.state.correlation_id = correlation_id
        
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        # 4. Trả correlation ID và thời gian xử lý trong response header
        response.headers["x-request-id"] = correlation_id
        response.headers["x-response-time-ms"] = f"{duration_ms:.1f}"

        # 5. Ghi wall-clock that su cua request.
        #    response_sent.latency_ms chi do phan ben trong agent.run nen KHONG bao
        #    gom thoi gian request nam cho trong hang doi. Khi event loop bi chan,
        #    hai so nay lech han nhau va chi so nay moi phan anh dung trai nghiem
        #    nguoi dung. Dat service="http" de tach khoi cac log tang ung dung.
        log.info(
            "request_completed",
            service="http",
            duration_ms=round(duration_ms, 1),
            status_code=response.status_code,
            payload={"path": request.url.path, "method": request.method},
        )

        return response
