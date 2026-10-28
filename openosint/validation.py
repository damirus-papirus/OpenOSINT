"""Local-only input normalization; no owner lookup."""
import re


def validate_email(value: str) -> dict:
    value = value.strip()
    if value.count("@") != 1:
        return {"valid_syntax": False, "domain": None}
    local, domain = value.rsplit("@", 1)
    domain_ok = "." in domain and all(domain.split("."))
    local_ok = bool(local) and len(local) <= 64 and not local.startswith(".") and not local.endswith(".")
    return {
        "valid_syntax": bool(local_ok and domain_ok and len(value) <= 254),
        "domain": domain.lower() if domain_ok else None,
        "note": "Существование ящика или его владелец не проверяются."
    }


def normalize_phone(value: str) -> dict:
    digits = re.sub(r"\D", "", value)
    plus = value.strip().startswith("+")
    return {
        "input": value,
        "normalized_digits": ("+" if plus else "") + digits,
        "digit_count": len(digits),
        "note": "Без кода страны нельзя надёжно определить международный формат."
    }
