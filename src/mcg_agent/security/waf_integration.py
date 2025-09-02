from __future__ import annotations

from typing import Any, Dict, List


class WAFIntegration:
    """WAF integration layer stub.

    In production, this will proxy allow/deny decisions to an external WAF
    or gateway (e.g., Cloudflare, AWS WAF). Here we expose a minimal
    interface to validate requests and report incidents.
    """

    def __init__(self, allowed_ips: List[str] | None = None) -> None:
        self.allowed_ips = set(allowed_ips or [])

    def filter_request(self, req_meta: Dict[str, Any]) -> bool:
        """Return True if request is allowed, False if blocked."""
        ip = (req_meta.get("ip") or "").strip()
        if self.allowed_ips and ip not in self.allowed_ips:
            return False
        # Placeholder for additional rules (country, ASN, path rules, etc.)
        return True

    def report_incident(self, details: Dict[str, Any]) -> None:
        """Report a security incident (stub: print/log only)."""
        print({"waf_incident": details})


__all__ = ["WAFIntegration"]

