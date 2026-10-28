"""Certificate Transparency lookup via crt.sh."""
import re
from urllib.parse import quote

from .http import get_json


_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def _valid_dns_name(value: str) -> bool:
    value = value.lower().rstrip(".")
    if not value or len(value) > 253 or "/" in value or "@" in value or " " in value:
        return False
    labels = value.split(".")
    return len(labels) >= 2 and all(_LABEL.fullmatch(label) for label in labels)


def lookup_certificates(domain: str) -> dict:
    domain = domain.lower().strip().rstrip(".")
    url = "https://crt.sh/?q=" + quote("%." + domain, safe="") + "&output=json"
    status, data, error = get_json(url, timeout=12)
    if error:
        return {"source": "crt.sh Certificate Transparency", "status": "error", "http_status": status, "error": error}
    if not isinstance(data, list):
        return {"source": "crt.sh Certificate Transparency", "status": "error", "error": "Неожиданный формат ответа"}

    names = set()
    entries = []
    for item in data:
        if not isinstance(item, dict):
            continue
        raw_names = []
        common_name = item.get("common_name")
        if common_name:
            raw_names.extend(str(common_name).splitlines())
        raw_names.extend(str(item.get("name_value", "")).splitlines())
        for raw_name in raw_names:
            name = raw_name.strip().lower().rstrip(".")
            if name.startswith("*."):
                name = name[2:]
            # Keep only valid DNS names within the requested domain.
            if _valid_dns_name(name) and (name == domain or name.endswith("." + domain)):
                names.add(name)
        if len(entries) < 30:
            entries.append({
                "id": item.get("id"),
                "issuer_name": item.get("issuer_name"),
                "not_before": item.get("not_before"),
                "not_after": item.get("not_after"),
            })
    return {
        "source": "crt.sh Certificate Transparency",
        "status": "ok",
        "unique_names_count": len(names),
        "names": sorted(names)[:300],
        "sample_certificates": entries,
        "note": "Исторические сертификаты могут включать старые или неактивные поддомены. Показаны только корректные DNS-имена внутри запрошенного домена."
    }
