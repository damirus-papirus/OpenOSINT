# OpenOSINT

Небольшой CLI-инструмент для **проверки публичных технических данных** и аккуратного сбора ссылок на открытые источники. Python 3.10+, без сторонних зависимостей; подходит для Termux и Windows.

## Что умеет

- распознавать домен, IP, URL, email, телефон и username;
- получать DNS-записи через публичный DNS-over-HTTPS;
- смотреть публичные RDAP-данные IP/домена;
- искать публичные имена сертификатов поддомена через crt.sh;
- проверять несколько публичных страниц профилей по username (только HTTP-статус, без сбора личных данных);
- сохранять JSON-отчёт с источниками, временем проверки и ограничениями.

**Не ищет владельцев телефонов/аккаунтов, адреса проживания, платёжные данные, родственников, закрытые базы или утёкшие данные.** Совпадение username не доказывает, что аккаунты принадлежат одному человеку. Используйте только для законной проверки своих активов или разрешённых публичных данных.

## Запуск

### Termux (Android)
```bash
pkg update
pkg install python -y
git clone https://github.com/damirus-papirus/OpenOSINT.git
cd OpenOSINT
python main.py example.com
```

### Windows
Установите Python 3.10+ с python.org, затем в PowerShell:
```powershell
git clone https://github.com/damirus-papirus/OpenOSINT.git
cd OpenOSINT
py main.py example.com
```

## Примеры
```bash
python main.py example.com
python main.py 8.8.8.8
python main.py https://example.com
python main.py user_name --profiles
python main.py someone@example.com
python main.py "+1 (202) 555-0123"
python main.py example.com --json report.json
```

Для username проверки используйте `--profiles`; она делает ограниченное число запросов и не скачивает страницы профилей. Не запускайте частые массовые проверки.

## Ограничения
- Для сетевых проверок нужен интернет.
- Сайты могут блокировать запросы или менять API; ошибка источника не означает отсутствие данных.
- Email и телефон проверяются только по формату/публичной технической информации, без определения владельца.
- Не вводите секреты, пароли, токены или чужие чувствительные данные.
