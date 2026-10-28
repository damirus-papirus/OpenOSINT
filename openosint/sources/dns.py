"""DNS-over-HTTPS lookups using Google's public resolver."""
import json
from urllib.parse import quote
from .http import get

TYPES = ("A", "AAAA", "MX", "NS", "TXT", "CNAME")


def lookup_dns(name: str, reverse: bool = False) -> dict:
    target = name
    if reverse:
        try:
            import ipaddress
            target = ipaddress.ip_address(name).reverse_pointer
            record_types = ("PTR",)
        except ValueError:
            return {"source": "Google Public DNS DoH", "status": "error", "error": "Некорректный IP"}
    else:
        record_types = TYPES

    records = {}
    errors = []
    for record_type in record_types:
        url = "https://dns.google/resolve?name=" + quote(target, safe="") + "&type=" + record_type
        status, body, _, error = get(url, timeout=6)
        if error:
            errors.append(f"{record_type}: {error}")
            continue
        try:
            payload = json.loads(body.decode("utf-8", errors="replace"))
            answers = payload.get("Answer", [])
            records[record_type] = [item.get("data", "") for item in answers if item.get("data")]
        except (ValueError, AttributeError) as exc:
            errors.append(f"{record_type}: ответ не удалось разобрать ({exc})")
    return {
        "source": "Google Public DNS over HTTPS",
        "status": "partial" if errors else "ok",
        "query": target,
        "records": records,
        "errors": errors,
        "note": "Публичные DNS-записи; пустой результат не доказывает отсутствие ресурса."
    }
