from typing import Any

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """與 HTTP 狀態分開描述的應用層錯誤本文（供前端與日誌一致處理）。"""

    code: str = Field(..., description="穩定錯誤碼，例如 VALIDATION_ERROR、NOT_FOUND")
    message: str = Field(..., description="給使用者／開發者閱讀的說明")
    details: Any | None = Field(default=None, description="額外結構化資訊（驗證欄位、追蹤 id 等）")


class ErrorResponse(BaseModel):
    """統一錯誤外殼：與成功回應區隔，避免混用。"""

    error: ErrorDetail


def ok_response(data: BaseModel | dict[str, Any]) -> BaseModel | dict[str, Any]:
    """成功回應維持純資料模型或 dict；錯誤一律走 ErrorResponse。"""
    return data
