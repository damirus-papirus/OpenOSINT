"""RDAP lookups for public registration/network allocation records."""
from urllib.parse import quote
from .http import get_json


def _pick(data: dict, key: str):
    value = data.get(key)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return None


def lookup_rdap(query: str, kind: str) -> dict:
    endpoint = "domain" if kind == "domain" else "ip"
    url = f"https://rdap.org/{endpoint}/{quote(query, safe='')}"
    status, data, error = get_json(url, timeout=10)
    if error:
        return {"source": "RDAP", "status": "error", "http_status": status, "error": error}
    if not isinstance(data, dict):
        return {"source": "RDAP", "status": "error", "error": "Неожиданный формат ответа"}
    return {
        "source": "RDAP",
        "status": "ok",
        "object_type": data.get("objectClassName"),
        "handle": data.get("handle"),
        "name": _pick(data, "name"),
        "country": _pick(data, "country"),
        "start_address": _pick(data, "startAddress"),
        "end_address": _pick(data, "endAddress"),
        "ip_version": _pick(data, "ipVersion"),
        "port43": _pick(data, "port43"),
        "events": [
            {"event": e.get("eventAction"), "date": e.get("eventDate")}
            for e in data.get("events", []) if isinstance(e, dict)
        ],
        "entities": [
            {"handle": e.get("handle"), "roles": e.get("roles", [])}
            for e in data.get("entities", []) if isinstance(e, dict)
        ],
        "note": "Регистрационные сведения могут быть скрыты, неполны или относиться к провайдеру/регистратору."
    }
