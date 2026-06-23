"""
Office / WFH detection — IP-based classification.

Compares a client IP against the OFFICE_IP_RANGES list from settings.
Returns: "office" | "remote" | "unknown"
"""
import ipaddress
from typing import Optional

from app.core.config import settings


def _get_office_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    """Parse OFFICE_IP_RANGES from settings into network objects. Cached per call."""
    raw = settings.OFFICE_IP_RANGES.strip()
    if not raw:
        return []
    networks = []
    for cidr in raw.split(","):
        cidr = cidr.strip()
        if cidr:
            try:
                networks.append(ipaddress.ip_network(cidr, strict=False))
            except ValueError:
                pass   # silently skip malformed ranges
    return networks


def classify_work_location(client_ip: Optional[str]) -> tuple[str, str]:
    """
    Returns (work_location, location_source):
      - ("office", "auto")  — IP is within configured office ranges
      - ("remote", "auto")  — IP is known but not in office ranges
      - ("unknown", "auto") — no OFFICE_IP_RANGES configured or IP missing
    """
    networks = _get_office_networks()

    if not networks or not client_ip:
        return ("unknown", "auto")

    try:
        addr = ipaddress.ip_address(client_ip.split(",")[0].strip())
    except ValueError:
        return ("unknown", "auto")

    for net in networks:
        try:
            if addr in net:
                return ("office", "auto")
        except TypeError:
            pass   # IPv4/IPv6 mismatch — skip

    return ("remote", "auto")


def get_client_ip(request) -> Optional[str]:
    """
    Extract client IP from a FastAPI Request object.
    Respects X-Forwarded-For if behind a proxy (first non-private IP wins).
    Falls back to request.client.host.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For: client, proxy1, proxy2
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None
