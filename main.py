#!/usr/bin/env python3
"""OpenOSINT command line entry point."""
import argparse
import sys
import threading
import time
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


class Progress:
    """Компактный однострочный прогресс-бар для терминала."""

    def __init__(self, total: int, enabled: bool = True, width: int = 16):
        self.total = max(1, total)
        self.done = 0
        self.enabled = enabled
        self.width = width
        self.current = ""
        self.started = time.monotonic()
        self._stop = threading.Event()
        self._thread = None
        self._tty = enabled and sys.stdout.isatty()

    def _draw(self, suffix: str = "") -> None:
        if not self.enabled:
            return
        percent = int(min(1.0, self.done / self.total) * 100)
        filled = int(self.width * percent / 100)
        bar = "█" * filled + "░" * (self.width - filled)
        # Только возврат каретки: обновляем ту же строку без ANSI-очистки
        # и без дополнительных подписей, которые могут переноситься в Termux.
        line = f"OpenOSINT [{bar}] {percent}%"
        sys.stdout.write("\r" + line)
        sys.stdout.flush()

    def _animate(self) -> None:
        frames = ("|", "/", "-", "\\")
        index = 0
        while not self._stop.wait(0.15):
            if self._tty:
                self._draw(frames[index % len(frames)])
                index += 1

    def run(self, label: str, function, *args, **kwargs):
        self.current = label
        self._stop.clear()
        if self.enabled:
            self._draw("работает")
            if self._tty:
                self._thread = threading.Thread(target=self._animate, daemon=True)
                self._thread.start()
        try:
            return function(*args, **kwargs)
        finally:
            self._stop.set()
            if self._thread is not None:
                self._thread.join(timeout=0.3)
                self._thread = None
            self.done += 1
            if self.enabled:
                self._draw("готово")
            self.current = ""

    def add_step(self) -> None:
        self.total += 1

    def finish(self) -> None:
        if self.enabled:
            self._draw("готово")
            sys.stdout.write("\n")
            sys.stdout.flush()


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
    parser.add_argument("--no-progress", action="store_true", help="Отключить индикатор прогресса")
    args = parser.parse_args()

    query = args.query.strip()
    kind = detect(query)
    report = make_report(query, kind)
    progress = Progress(
        total=3 if kind in ("domain", "url") else (
            2 if kind == "ip" else 1 if kind == "username" and args.profiles else 1
        ),
        enabled=not args.no_progress,
    )

    if kind in ("domain", "url"):
        host = query if kind == "domain" else (urlparse(query).hostname or "")
        if host:
            report["results"].append(progress.run("Проверка DNS", lookup_dns, host))
            report["results"].append(progress.run("Регистрационные сведения RDAP", lookup_rdap, host, "domain"))
            cert_result = progress.run("Поиск имён в Certificate Transparency", lookup_certificates, host)
            report["results"].append(cert_result)
            if args.check_subdomains and cert_result.get("status") == "ok":
                progress.add_step()
                report["results"].append(progress.run(
                    "Проверка DNS найденных имён", check_subdomains, cert_result.get("names", []), limit=15
                ))
        if kind == "url":
            report["notes"].append("URL не открывался для извлечения содержимого; проверялись только публичные технические сведения о hostname.")
    elif kind == "ip":
        report["results"].append(progress.run("Регистрационные сведения RDAP", lookup_rdap, query, "ip"))
        report["results"].append(progress.run("Обратный DNS", lookup_dns, query, reverse=True))
    elif kind == "email":
        report["results"].append(progress.run("Локальная проверка формата email", lambda: {
            "source": "local-validation", "status": "ok",
            "data": validate_email(query),
            "note": "Проверка синтаксиса и доменной части; владелец адреса не определяется."
        }))
    elif kind == "phone":
        report["results"].append(progress.run("Локальная нормализация телефона", lambda: {
            "source": "local-validation", "status": "ok",
            "data": normalize_phone(query),
            "note": "Нормализация формата; владелец номера не определяется."
        }))
    elif kind == "username":
        report["notes"].append("Username сам по себе не подтверждает личность. Для проверки публичных страниц добавьте --profiles.")
        if args.profiles:
            report["results"].append(progress.run("Проверка публичных страниц профиля", check_profiles, query))
    else:
        report["notes"].append("Запрос не распознан как технический идентификатор. Автоматический поиск личных данных не выполняется.")

    progress.finish()
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
