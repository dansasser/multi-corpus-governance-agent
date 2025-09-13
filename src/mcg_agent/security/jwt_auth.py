from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from mcg_agent.config import get_settings


security_scheme = HTTPBearer(auto_error=False)


def create_access_token(
    subject: str,
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None,
) -> str:
    settings = get_settings()
    to_encode: Dict[str, Any] = {
        "sub": subject,
        "iat": datetime.now(timezone.utc),
    }
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.security.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = datetime.now(timezone.utc) + expires_delta
    if extra_claims:
        to_encode.update(extra_claims)
    return jwt.encode(to_encode, settings.security.JWT_SECRET_KEY, algorithm=settings.security.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.security.JWT_SECRET_KEY,
            algorithms=[settings.security.JWT_ALGORITHM],
            options={"verify_aud": False},
        )
        return payload
    except jwt.ExpiredSignatureError as e:  # type: ignore[attr-defined]
        raise HTTPException(status_code=401, detail="token_expired") from e
    except jwt.InvalidTokenError as e:  # type: ignore[attr-defined]
        raise HTTPException(status_code=401, detail="invalid_token") from e


async def get_current_user(creds: HTTPAuthorizationCredentials = Security(security_scheme)) -> Dict[str, Any]:
    if creds is None or not creds.scheme.lower().startswith("bearer"):
        raise HTTPException(status_code=401, detail="missing_token")
    token = creds.credentials
    payload = decode_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="invalid_subject")
    return {"user_id": user_id, **{k: v for k, v in payload.items() if k not in {"sub"}}}


__all__ = ["create_access_token", "decode_token", "get_current_user"]

