"""Report formatting and JSON export."""
import json
from datetime import datetime, timezone


def make_report(query: str, kind: str) -> dict:
    return {
        "tool": "OpenOSINT", "version": "0.1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "query": query, "detected_type": kind, "results": [],
        "notes": [
            "Собираются только публичные технические сведения.",
            "Результаты источников могут быть неполными; ошибка запроса не означает отсутствие данных.",
        ],
    }


def render_text(report: dict) -> str:
    lines = [
        f"{report['tool']} {report['version']}", "=" * 52,
        f"Запрос: {report['query']}", f"Тип: {report['detected_type']}",
        f"Время UTC: {report['generated_at_utc']}",
    ]
    for index, result in enumerate(report.get("results", []), 1):
        lines.extend(["", f"[{index}] {result.get('source', 'Источник')}",
                      f"Статус: {result.get('status', 'unknown')}"])
        for key, value in result.items():
            if key in ("source", "status"):
                continue
            import json
            pretty = json.dumps(value, ensure_ascii=False, indent=2) if isinstance(value, (dict, list)) else str(value)
            lines.append(f"{key}: {pretty}")
    if report.get("notes"):
        lines.extend(["", "Примечания:"])
        lines.extend(f"- {note}" for note in report["notes"])
    return "\n".join(lines)


def save_json(report: dict, path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
