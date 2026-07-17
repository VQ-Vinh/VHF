from __future__ import annotations

from fastapi import HTTPException


def api_error(status: int, code: str, message: str, **extra) -> HTTPException:
    retry_after = extra.pop("retry_after", None)
    detail = {"code": code, "message": message}
    if retry_after is not None:
        detail["retry_after"] = retry_after
    detail.update(extra)
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else None
    return HTTPException(status_code=status, detail=detail, headers=headers)
