"""Conservative DNS checks for names found in public certificate records."""
from urllib.parse import quote

from .http import get_json


def check_subdomains(names: list[str], limit: int = 15) -> dict:
    """Check A/AAAA DNS answers for at most limit names; no active port scanning."""
    checked = []
    candidates = [name for name in names if isinstance(name, str)]
    for name in candidates[:limit]:
        row = {"hostname": name, "A": [], "AAAA": [], "status": "no-answer"}
        errors = []
        for record_type in ("A", "AAAA"):
            url = (
                "https://dns.google/resolve?name="
                + quote(name, safe="")
                + "&type="
                + record_type
            )
            _, payload, error = get_json(url, timeout=5)
            if error:
                errors.append(f"{record_type}: {error}")
                continue
            if isinstance(payload, dict):
                row[record_type] = [
                    answer.get("data", "")
                    for answer in payload.get("Answer", [])
                    if answer.get("type") in (1, 28) and answer.get("data")
                ]
        if row["A"] or row["AAAA"]:
            row["status"] = "resolves"
        elif errors:
            row["status"] = "error"
            row["errors"] = errors
        checked.append(row)
    return {
        "source": "DNS check for certificate names",
        "status": "ok" if checked else "empty",
        "checked_count": len(checked),
        "resolves_count": sum(1 for row in checked if row["status"] == "resolves"),
        "results": checked,
        "note": "DNS-ответ не гарантирует доступность сайта; проверялись только A/AAAA-записи, без портов и содержимого."
    }
