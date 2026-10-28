"""Text, JSON, and self-contained HTML report formatting."""
import html
import json
from datetime import datetime, timezone
from pathlib import Path


EVENT_LABELS = {
    "registration": "Дата регистрации",
    "expiration": "Дата окончания регистрации",
    "last changed": "Последнее изменение",
    "last update of RDAP database": "Обновление базы RDAP",
    "transfer": "Передача домена",
    "reinstantiation": "Восстановление",
    "deletion": "Удаление",
}


def make_report(query: str, kind: str) -> dict:
    return {
        "tool": "OpenOSINT", "version": "0.3.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "query": query, "detected_type": kind, "results": [],
        "notes": [
            "Собираются только публичные технические сведения.",
            "Результаты источников могут быть неполными; ошибка запроса не означает отсутствие данных.",
        ],
    }


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)


def _format_date(value) -> str:
    if not isinstance(value, str) or not value:
        return ""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.strftime("%d.%m.%Y %H:%M UTC") if "T" in value else parsed.strftime("%d.%m.%Y")
    except ValueError:
        return value


def _format_rdap(result: dict) -> list[str]:
    lines = []
    is_domain = result.get("object_type") == "domain"
    if is_domain:
        lines.append(f"Объект: домен {result.get('query', '')}".rstrip())
    else:
        lines.append("Объект: IP-сеть" if result.get("start_address") or result.get("end_address") else "Объект: регистрационные данные")

    if result.get("name"):
        lines.append(f"Название: {result['name']}")
    if result.get("country"):
        lines.append(f"Страна: {result['country']}")
    if result.get("start_address") or result.get("end_address"):
        start = result.get("start_address") or "не указано"
        end = result.get("end_address") or "не указано"
        lines.append(f"Диапазон адресов: {start} — {end}")
    if result.get("ip_version"):
        lines.append(f"Версия IP: {result['ip_version']}")

    events = result.get("events", [])
    shown_events = []
    for event in events:
        if not isinstance(event, dict):
            continue
        action = str(event.get("event", "")).lower()
        if action == "last update of rdap database":
            continue
        label = EVENT_LABELS.get(action, action.capitalize() if action else "")
        date = _format_date(event.get("date"))
        if label and date:
            shown_events.append((action, f"{label}: {date}"))
    priority = {"registration": 0, "last changed": 1, "expiration": 2}
    shown_events.sort(key=lambda pair: priority.get(pair[0], 10))
    lines.extend(line for _, line in shown_events)

    registrar_entities = [
        entity for entity in result.get("entities", [])
        if isinstance(entity, dict) and "registrar" in entity.get("roles", [])
    ]
    if registrar_entities:
        registrar_names = [
            entity.get("name") for entity in registrar_entities if entity.get("name")
        ]
        if registrar_names:
            lines.append("Регистратор: " + ", ".join(registrar_names))
        else:
            lines.append("Регистратор: имя не раскрыто источником")
    if result.get("note"):
        lines.append("Примечание: " + str(result["note"]))
    return lines


def render_text(report: dict, verbose: bool = False) -> str:
    lines = [
        f"{report['tool']} {report['version']}", "=" * 52,
        f"Запрос: {report['query']}", f"Тип: {report['detected_type']}",
        f"Время проверки (UTC): {_format_date(report['generated_at_utc'])}",
    ]
    for index, result in enumerate(report.get("results", []), 1):
        source = result.get("source", "Источник")
        lines.extend(["", f"[{index}] {source}"])
        status = result.get("status", "unknown")
        status_label = {"ok": "успешно", "partial": "частично", "error": "ошибка", "empty": "нет результатов"}.get(status, status)
        lines.append(f"Статус: {status_label}")

        if source == "RDAP" and status == "ok":
            lines.extend(_format_rdap(result))
            if verbose and result.get("handle"):
                lines.append(f"Технический ID объекта: {result['handle']}")
            continue

        if status in ("error", "empty"):
            if result.get("note"):
                lines.append("Пояснение: " + str(result["note"]))
            if result.get("http_status"):
                lines.append(f"HTTP-код: {result['http_status']}")
            if result.get("error") and (verbose or not result.get("note")):
                lines.append(f"Техническая причина: {result['error']}")
            continue

        if result.get("data") is not None:
            data = result["data"]
            if isinstance(data, dict) and "valid_syntax" in data:
                lines.append("Синтаксис: корректен" if data.get("valid_syntax") else "Синтаксис: есть ошибки")
                for key, value in data.items():
                    if key != "valid_syntax" and value not in (None, "", [], {}):
                        lines.append(f"{key.replace('_', ' ').capitalize()}: {value}")
            else:
                lines.append("Результат: " + (str(data) if not isinstance(data, (dict, list)) else _json(data)))

        if result.get("query"):
            lines.append(f"DNS-запрос: {result['query']}")
        if result.get("records"):
            for record_type, values in result["records"].items():
                lines.append(f"{record_type}: {len(values)} записей")
                if values:
                    shown = values if verbose else values[:3]
                    lines.extend(f"  - {value}" for value in shown)
                    if not verbose and len(values) > len(shown):
                        lines.append(f"  … ещё {len(values) - len(shown)}")
                elif verbose:
                    lines.append("  Записей нет")

        if "unique_names_count" in result:
            lines.append(f"Уникальных DNS-имён в сертификатах: {result['unique_names_count']}")
            names = result.get("names", [])
            shown = names if verbose else names[:10]
            if shown:
                lines.append("Имена:")
                lines.extend(f"  - {name}" for name in shown)
            if not verbose and len(names) > len(shown):
                lines.append(f"  … ещё {len(names) - len(shown)}; полный список сохранён в JSON/HTML")
            if verbose:
                certs = result.get("sample_certificates", [])
                if certs:
                    lines.append(f"Примеры сертификатов: {len(certs)}")
                    for cert in certs[:10]:
                        lines.append(f"  - ID {cert.get('id')}: {_format_date(cert.get('not_before'))} — {_format_date(cert.get('not_after'))}")

        if source == "DNS check for certificate names":
            lines.append(
                f"Проверено имён: {result.get('checked_count', 0)}; "
                f"имеют A/AAAA-записи: {result.get('resolves_count', 0)}"
            )
            for row in result.get("results", []):
                addresses = row.get("A", []) + row.get("AAAA", [])
                suffix = ", ".join(addresses) if addresses else {
                    "error": "ошибка запроса", "no-answer": "DNS-записи не найдены"
                }.get(row.get("status"), row.get("status", "нет данных"))
                lines.append(f"  - {row.get('hostname')}: {suffix}")

        if result.get("note") and source != "RDAP":
            lines.append("Примечание: " + str(result["note"]))
        if result.get("errors"):
            errors = result["errors"]
            if verbose:
                lines.extend(f"Ошибка: {error}" for error in errors)
            else:
                lines.append(f"Ошибок отдельных запросов: {len(errors)}")
        if verbose:
            skip = {"source", "status", "data", "query", "records", "unique_names_count",
                    "names", "sample_certificates", "results", "note", "errors"}
            for key, value in result.items():
                if key not in skip and value not in (None, "", [], {}):
                    lines.append(f"{key.replace('_', ' ').capitalize()}: {_json(value) if isinstance(value, (dict, list)) else value}")

    if report.get("notes"):
        lines.extend(["", "Примечания:"])
        lines.extend(f"- {note}" for note in report["notes"])
    if not verbose:
        lines.extend(["", "Подробности: --verbose; полный JSON: --json report.json"])
    return "\n".join(lines)


def save_json(report: dict, path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json(report) + "\n", encoding="utf-8")


def _humanize_rdap_html(result: dict) -> str:
    return "\n".join(_format_rdap(result))


def save_html(report: dict, path) -> None:
    """Write a standalone HTML report with readable summaries and escaped raw details."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    sections = []
    for index, result in enumerate(report.get("results", []), 1):
        source = html.escape(str(result.get("source", "Источник")))
        status = html.escape(str(result.get("status", "unknown")))
        if source == "RDAP" and result.get("status") == "ok":
            summary = "<ul>" + "".join(
                f"<li>{html.escape(line)}</li>" for line in _format_rdap(result)
            ) + "</ul>"
        else:
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
            if result.get("note") and result.get("status") in ("error", "empty"):
                summary_parts.insert(0, str(result["note"]))
            if result.get("http_status") and result.get("status") in ("error", "empty"):
                summary_parts.append(f"HTTP-код: {result['http_status']}")
            summary = "<p>" + html.escape(" · ".join(summary_parts)) + "</p>" if summary_parts else ""
        details = html.escape(_json(result))
        sections.append(
            f'<section><h2>{index}. {source} <span class="status">{status}</span></h2>'
            f"{summary}<details><summary>Технические данные JSON</summary>"
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
