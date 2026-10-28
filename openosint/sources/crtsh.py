"""Certificate Transparency lookup via crt.sh."""
from urllib.parse import quote
from .http import get_json


def lookup_certificates(domain: str) -> dict:
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
        common_name = item.get("common_name")
        if common_name:
            names.update(line.strip().lower() for line in common_name.splitlines() if line.strip())
        for name in str(item.get("name_value", "")).splitlines():
            name = name.strip().lower().lstrip("*.")
            if name:
                names.add(name)
        if len(entries) < 100:
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
        "note": "Исторические сертификаты могут включать старые или неактивные поддомены."
    }
