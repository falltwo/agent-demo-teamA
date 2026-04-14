from pydantic import BaseModel, Field


class StubInfoResponse(BaseModel):
    """最小範例端點：確認路由與設定載入。"""

    message: str = Field(default="stub")
    api_version: str
