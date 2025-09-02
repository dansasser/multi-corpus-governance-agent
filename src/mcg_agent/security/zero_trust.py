from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ZeroTrustSettings(BaseModel):
    """Configuration for Zero Trust controls (transport-level assumed external).

    Note: TLS 1.3 termination, DB-at-rest encryption, and Redis TLS
    are configured at deployment/runtime. This settings model captures
    application-level toggles and allowlists used by middlewares.
    """

    allowed_origins: List[str] = Field(default_factory=list)
    allowed_methods: List[str] = Field(default_factory=lambda: ["GET", "POST"])
    allowed_headers: List[str] = Field(default_factory=lambda: ["authorization", "content-type"])  # noqa: E501
    enforce_auth: bool = True
    rate_limit_per_minute: int = 60


class ZeroTrust:
    """Core helpers for enforcing app-level Zero Trust behaviors."""

    def __init__(self, settings: ZeroTrustSettings | None = None) -> None:
        self.settings = settings or ZeroTrustSettings()

    def apply_security_headers(self, response_headers: Dict[str, str]) -> Dict[str, str]:
        """Apply security headers. Framework-agnostic (dict in, dict out)."""
        headers = dict(response_headers)
        headers.setdefault("X-Content-Type-Options", "nosniff")
        headers.setdefault("X-Frame-Options", "DENY")
        headers.setdefault("Referrer-Policy", "no-referrer")
        headers.setdefault("Permissions-Policy", "microphone=(), camera=()")
        headers.setdefault("Cache-Control", "no-store")
        return headers

    def validate_request_meta(self, req: Dict[str, Any]) -> bool:
        """Lightweight request validation for origin/method/headers.

        Expects a dict with keys: origin, method, headers(list[str]).
        """
        origin = (req.get("origin") or "").lower()
        method = (req.get("method") or "").upper()
        headers = [h.lower() for h in (req.get("headers") or [])]

        if self.settings.allowed_origins and origin not in [o.lower() for o in self.settings.allowed_origins]:  # noqa: E501
            return False
        if method and method not in self.settings.allowed_methods:
            return False
        # Require at least the allowed headers subset to be present when enforce_auth
        if self.settings.enforce_auth:
            needed = set([h.lower() for h in self.settings.allowed_headers])
            if not needed.issubset(set(headers)):
                return False
        return True


__all__ = ["ZeroTrustSettings", "ZeroTrust"]

