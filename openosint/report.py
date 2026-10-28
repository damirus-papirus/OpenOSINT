"""Text, JSON, and self-contained HTML report formatting."""
import html
import json
from datetime import datetime, timezone
from pathlib import Path


def make_report(query: str, kind: str) -> dict:
    return {
        "tool": "OpenOSINT", "version": "0.2.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "query": query, "detected_type": kind, "results": [],
        "notes": [
            "Собираются только публичные технические сведения.",
            "Результаты источников могут быть неполными; ошибка запроса не означает отсутствие данных.",
        ],
    }


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def render_text(report: dict, verbose: bool = False) -> str:
    lines = [
        f"{report['tool']} {report['version']}", "=" * 52,
        f"Запрос: {report['query']}", f"Тип: {report['detected_type']}",
        f"Время UTC: {report['generated_at_utc']}",
    ]
    for index, result in enumerate(report.get("results", []), 1):
        lines.extend(["", f"[{index}] {result.get('source', 'Источник')}",
                      f"Статус: {result.get('status', 'unknown')}"])
        data = result.get("data")
        if data is not None:
            lines.append("Результат: " + (str(data) if not isinstance(data, (dict, list)) else _json(data)))
        if result.get("query"):
            lines.append(f"Запрос источника: {result['query']}")
        if result.get("records"):
            records = result["records"]
            for record_type, values in records.items():
                lines.append(f"{record_type}: {len(values)} записей")
                if verbose:
                    lines.extend(f"  - {value}" for value in values)
                elif values:
                    preview = ", ".join(str(value) for value in values[:3])
                    suffix = f" … (+{len(values) - 3})" if len(values) > 3 else ""
                    lines.append(f"  {preview}{suffix}")
        if "unique_names_count" in result:
            lines.append(f"Уникальных имён сертификатов: {result['unique_names_count']}")
            names = result.get("names", [])
            shown = names if verbose else names[:15]
            if shown:
                lines.append("Имена:")
                lines.extend(f"  - {name}" for name in shown)
            if not verbose and len(names) > len(shown):
                lines.append(f"  … ещё {len(names) - len(shown)}; полный список — в JSON/HTML")
            lines.append(f"Примеров сертификатов: {len(result.get('sample_certificates', []))}")
        if "results" in result and result.get("source") == "DNS check for certificate names":
            lines.append(
                f"Проверено DNS: {result.get('checked_count', 0)}; "
                f"есть A/AAAA: {result.get('resolves_count', 0)}"
            )
            for row in result.get("results", []):
                addresses = row.get("A", []) + row.get("AAAA", [])
                suffix = ", ".join(addresses) if addresses else row.get("status", "no-answer")
                lines.append(f"  - {row.get('hostname')}: {suffix}")
        for key in ("handle", "object_type", "country", "name", "start_address",
                    "end_address", "ip_version", "port43", "events", "entities",
                    "http_status", "error", "errors", "note"):
            if key in result and result[key] not in (None, "", [], {}):
                value = result[key]
                if key in ("events", "entities", "errors") and not verbose:
                    lines.append(f"{key}: {len(value)} элементов")
                else:
                    rendered = _json(value) if isinstance(value, (dict, list)) else str(value)
                    lines.append(f"{key}: {rendered}")
        if verbose:
            skip = {"source", "status", "data", "query", "records", "unique_names_count",
                    "names", "sample_certificates", "results", "handle", "object_type",
                    "country", "name", "start_address", "end_address", "ip_version",
                    "port43", "events", "entities", "http_status", "error", "errors", "note"}
            for key, value in result.items():
                if key not in skip:
                    lines.append(f"{key}: {_json(value) if isinstance(value, (dict, list)) else value}")
    if report.get("notes"):
        lines.extend(["", "Примечания:"])
        lines.extend(f"- {note}" for note in report["notes"])
    if not verbose:
        lines.extend(["", "Подробный вывод: добавьте --verbose."])
    return "\n".join(lines)


def save_json(report: dict, path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json(report) + "\n", encoding="utf-8")


def save_html(report: dict, path) -> None:
    """Write a standalone HTML report; all source content is HTML-escaped."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sections = []
    for index, result in enumerate(report.get("results", []), 1):
        source = html.escape(str(result.get("source", "Источник")))
        status = html.escape(str(result.get("status", "unknown")))
        summary_parts = []
        if "unique_names_count" in result:
            summary_parts.append(f"Уникальных имён: {result['unique_names_count']}")
        if "records" in result:
            summary_parts.append("DNS-записи: " + ", ".join(
                f"{html.escape(str(key))} ({len(values)})"
                for key, values in result["records"].items()
            ))
        if "checked_count" in result:
            summary_parts.append(
                f"Проверено имён: {result.get('checked_count', 0)}; "
                f"разрешаются в DNS: {result.get('resolves_count', 0)}"
            )
        summary = "<p>" + html.escape(" · ".join(summary_parts)) + "</p>" if summary_parts else ""
        details = html.escape(_json(result))
        sections.append(
            f'<section><h2>{index}. {source} <span class="status">{status}</span></h2>'
            f"{summary}<details><summary>Показать подробности</summary>"
            f"<pre>{details}</pre></details></section>"
        )
    notes = "".join(f"<li>{html.escape(str(note))}</li>" for note in report.get("notes", []))
    document = f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>OpenOSINT — отчёт</title>
<style>
:root{{color-scheme:light dark}}body{{font:16px/1.5 system-ui,sans-serif;max-width:1000px;margin:0 auto;padding:20px}}
header,section{{border:1px solid #8886;border-radius:12px;padding:16px;margin:14px 0}}
h1{{margin-top:0}}.muted{{opacity:.75}}.status{{font-size:.75em;border:1px solid #8888;border-radius:8px;padding:2px 7px}}
pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}}summary{{cursor:pointer}}li{{margin:5px 0}}
</style></head><body>
<header><h1>OpenOSINT — отчёт</h1>
<p><strong>Запрос:</strong> {html.escape(str(report.get('query', '')))}</p>
<p><strong>Тип:</strong> {html.escape(str(report.get('detected_type', '')))}</p>
<p class="muted">Сформирован UTC: {html.escape(str(report.get('generated_at_utc', '')))}</p></header>
{''.join(sections)}
<section><h2>Примечания и ограничения</h2><ul>{notes}</ul></section>
</body></html>"""
    path.write_text(document, encoding="utf-8")
