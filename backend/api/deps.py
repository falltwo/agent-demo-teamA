import hmac
from typing import Annotated

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.config import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]

_bearer = HTTPBearer(auto_error=False)


def verify_admin_token(
    settings: SettingsDep,
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> None:
    """若 ADMIN_API_TOKEN 已設定，驗證 Bearer token；未設定則跳過（向後相容）。

    使用 hmac.compare_digest 做定時比對，避免 timing-attack 推敲 token 字元。
    """
    token = settings.admin_api_token
    if not token:
        return  # 未設定 ADMIN_API_TOKEN，開放存取
    if credentials is None:
        raise HTTPException(status_code=401, detail="Invalid or missing admin token")
    if not hmac.compare_digest(credentials.credentials or "", token):
        raise HTTPException(status_code=401, detail="Invalid or missing admin token")


AdminAuthDep = Annotated[None, Depends(verify_admin_token)]
