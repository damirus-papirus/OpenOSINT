"""Small standard-library HTTP helper with conservative timeouts."""
import json
import urllib.error
import urllib.request
import time

USER_AGENT = "OpenOSINT/0.1 (+https://github.com/damirus-papirus/OpenOSINT; public technical checks)"


def get(url: str, accept: str = "application/json", timeout: int = 8):
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": accept,
    })
    # Retry only temporary upstream failures; don't retry 404 or rate limits.
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                body = response.read(2_000_000)
                return response.status, body, dict(response.headers.items()), None
        except urllib.error.HTTPError as exc:
            if exc.code in (502, 503, 504) and attempt < 2:
                time.sleep(0.5 * (attempt + 1))
                continue
            return exc.code, exc.read(200_000), dict(exc.headers.items()), f"HTTP {exc.code}"
        except Exception as exc:
            return None, b"", {}, f"{type(exc).__name__}: {exc}"


def get_json(url: str, timeout: int = 8):
    status, body, headers, error = get(url, timeout=timeout)
    if error:
        return status, None, error
    try:
        return status, json.loads(body.decode("utf-8", errors="replace")), None
    except (ValueError, UnicodeError) as exc:
        return status, None, f"Invalid JSON: {exc}"
