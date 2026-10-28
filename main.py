#!/usr/bin/env python3
"""OpenOSINT command line entry point."""
import argparse
import sys
from pathlib import Path
from urllib.parse import urlparse

from openosint.detector import detect
from openosint.report import make_report, render_text, save_html, save_json
from openosint.sources.dns import lookup_dns
from openosint.sources.rdap import lookup_rdap
from openosint.sources.crtsh import lookup_certificates
from openosint.sources.subdomains import check_subdomains
from openosint.sources.public_profiles import check_profiles
from openosint.validation import validate_email, normalize_phone


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="OpenOSINT",
        description="Проверка публичных технических данных (без поиска частных персональных данных).",
    )
    parser.add_argument("query", help="Домен, URL, IP, email, телефон или username")
    parser.add_argument("--profiles", action="store_true", help="Проверить ограниченный список публичных URL профилей по username")
    parser.add_argument("--check-subdomains", action="store_true",
                        help="Проверить DNS A/AAAA максимум 15 имён из публичных сертификатов")
    parser.add_argument("--json", dest="json_path", help="Сохранить полный отчёт в JSON-файл")
    parser.add_argument("--html", dest="html_path", help="Сохранить HTML-отчёт в файл")
    parser.add_argument("--verbose", action="store_true", help="Показать подробный вывод в терминале")
    args = parser.parse_args()

    query = args.query.strip()
    kind = detect(query)
    report = make_report(query, kind)

    if kind == "domain":
        report["results"].append(lookup_dns(query))
        report["results"].append(lookup_rdap(query, "domain"))
        cert_result = lookup_certificates(query)
        report["results"].append(cert_result)
        if args.check_subdomains and cert_result.get("status") == "ok":
            report["results"].append(check_subdomains(cert_result.get("names", []), limit=15))
    elif kind == "url":
        host = urlparse(query).hostname or ""
        if host:
            report["results"].append(lookup_dns(host))
            report["results"].append(lookup_rdap(host, "domain"))
            cert_result = lookup_certificates(host)
            report["results"].append(cert_result)
            if args.check_subdomains and cert_result.get("status") == "ok":
                report["results"].append(check_subdomains(cert_result.get("names", []), limit=15))
        report["notes"].append("URL не открывался для извлечения содержимого; проверялись только публичные технические сведения о hostname.")
    elif kind == "ip":
        report["results"].append(lookup_rdap(query, "ip"))
        report["results"].append(lookup_dns(query, reverse=True))
    elif kind == "email":
        report["results"].append({
            "source": "local-validation", "status": "ok",
            "data": validate_email(query),
            "note": "Проверка синтаксиса и доменной части; владелец адреса не определяется."
        })
    elif kind == "phone":
        report["results"].append({
            "source": "local-validation", "status": "ok",
            "data": normalize_phone(query),
            "note": "Нормализация формата; владелец номера не определяется."
        })
    elif kind == "username":
        report["notes"].append("Username сам по себе не подтверждает личность. Для проверки публичных страниц добавьте --profiles.")
        if args.profiles:
            report["results"].append(check_profiles(query))
    else:
        report["notes"].append("Запрос не распознан как технический идентификатор. Автоматический поиск личных данных не выполняется.")

    print(render_text(report, verbose=args.verbose))
    if args.json_path:
        save_json(report, Path(args.json_path))
        print(f"JSON-отчёт сохранён: {args.json_path}")
    if args.html_path:
        save_html(report, Path(args.html_path))
        print(f"HTML-отчёт сохранён: {args.html_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nОстановлено пользователем.", file=sys.stderr)
        raise SystemExit(130)
