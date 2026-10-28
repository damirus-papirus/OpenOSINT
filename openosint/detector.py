"""Input type detection. This module does not identify private people."""
import ipaddress
import re
from urllib.parse import urlparse

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
PHONE_RE = re.compile(r"^\+?[\d\s().-]{7,25}$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{2,40}$")


def _is_domain(value: str) -> bool:
    value = value.rstrip(".").lower()
    if len(value) > 253 or "." not in value:
        return False
    labels = value.split(".")
    return all(
        1 <= len(label) <= 63
        and re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label)
        for label in labels
    )


def detect(value: str) -> str:
    value = value.strip()
    if not value:
        return "unknown"
    try:
        ipaddress.ip_address(value)
        return "ip"
    except ValueError:
        pass
    if value.startswith(("https://", "http://")):
        parsed = urlparse(value)
        return "url" if parsed.hostname else "unknown"
    if EMAIL_RE.fullmatch(value):
        return "email"
    if PHONE_RE.fullmatch(value) and sum(ch.isdigit() for ch in value) >= 7:
        return "phone"
    if _is_domain(value):
        return "domain"
    if USERNAME_RE.fullmatch(value) and not any(ch.isspace() for ch in value):
        return "username"
    return "unknown"
