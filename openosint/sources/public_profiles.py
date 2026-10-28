"""Limited public profile URL checks; does not fetch profile content."""
from urllib.parse import quote
from .http import get

SITES = {
    "GitHub": "https://github.com/{username}",
    "GitLab": "https://gitlab.com/{username}",
    "Reddit": "https://www.reddit.com/user/{username}/",
    "YouTube": "https://www.youtube.com/@{username}",
    "Twitch": "https://www.twitch.tv/{username}",
    "Pinterest": "https://www.pinterest.com/{username}/",
}


def check_profiles(username: str) -> dict:
    safe = quote(username.strip(), safe="")
    results = []
    for site, template in SITES.items():
        url = template.format(username=safe)
        status, _, headers, error = get(url, accept="text/html", timeout=5)
        if error and status is None:
            state = "unknown"
        elif status in (200, 301, 302, 307, 308):
            state = "page_responded"
        elif status == 404:
            state = "not_found"
        elif status in (401, 403, 429):
            state = "blocked_or_limited"
        else:
            state = "http_response"
        results.append({
            "site": site, "url": url, "http_status": status,
            "state": state, "error": error,
            "content_type": headers.get("Content-Type") or headers.get("content-type"),
        })
    return {
        "source": "Public profile URL checks", "status": "ok",
        "username": username, "checks": results,
        "note": "Это лишь ответы URL. Совпадение username не подтверждает, что профили принадлежат одному человеку; 403/429 и редиректы могут давать ложные выводы."
    }
