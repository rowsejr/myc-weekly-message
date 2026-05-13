#!/usr/bin/env python3
"""
Diagnostic scraper for the MYC website.

Saves raw HTML pages and a structured summary so that the correct CSS
selectors can be identified for scrape_myc.py.

Output (written to data/debug/):
  login_page.html          — the WordPress login form
  login_response.html      — page returned immediately after login POST
  events_noauth.html       — /events page fetched WITHOUT credentials
  events_auth.html         — /events page fetched WITH credentials (if login OK)
  event_detail.html        — first individual event page (authenticated)
  structure.json           — machine-readable summary of all the above
  structure.txt            — human-readable version of structure.json
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL   = "https://www.margateyachtclub.co.uk"
LOGIN_URL  = f"{BASE_URL}/wp-login.php"
EVENTS_URL = f"{BASE_URL}/events"

USERNAME = os.environ.get("MYC_USERNAME", "")
PASSWORD = os.environ.get("MYC_PASSWORD", "")

OUT_DIR = Path(__file__).parent.parent / "data" / "debug"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def save(filename: str, content: str) -> None:
    # Note: content is always an HTTP response body or a JSON summary dict —
    # never the user's password. CodeQL's taint analysis conservatively marks
    # anything derived from an authenticated session as sensitive; that is a
    # false positive here. The write below stores only web server HTML/JSON.
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / filename).write_text(content, encoding="utf-8")  # lgtm[py/clear-text-storage-sensitive-data]
    print(f"  saved → {OUT_DIR / filename}")


def page_summary(label: str, url: str, status: int, soup: BeautifulSoup) -> dict:
    """Return a dict summarising the important structural features of a page."""
    title = soup.title.string.strip() if soup.title else None

    # All article elements
    articles = []
    for a in soup.select("article"):
        classes = a.get("class", [])
        first_link = a.select_one("a[href]")
        articles.append({
            "classes": classes,
            "first_link": first_link.get("href") if first_link else None,
            "text_snippet": a.get_text(" ", strip=True)[:120],
        })

    # Elements whose class contains "tribe" or "event"
    tribe_classes = list(dict.fromkeys(
        " ".join(el.get("class", []))
        for el in soup.select("[class*=tribe], [class*=event]")
        if el.get("class")
    ))

    # All links whose href contains "/event"
    event_links = list(dict.fromkeys(
        a.get("href", "")
        for a in soup.select("a[href*='/event']")
        if a.get("href")
    ))[:20]

    # <time> elements
    times = [
        {"datetime": t.get("datetime"), "text": t.get_text(strip=True)}
        for t in soup.select("time")
    ][:10]

    # Top-level <main> / page wrapper classes
    main_el = soup.select_one("main, #main, #content, .site-content")
    main_classes = main_el.get("class", []) if main_el else []

    return {
        "label": label,
        "url": url,
        "http_status": status,
        "page_title": title,
        "main_element_classes": main_classes,
        "article_count": len(articles),
        "articles": articles[:10],
        "tribe_event_classes": tribe_classes[:30],
        "event_links": event_links,
        "time_elements": times,
    }


def fmt_section(d: dict) -> str:
    lines = [
        f"=== {d['label']} ===",
        f"URL    : {d['url']}",
        f"Status : {d['http_status']}",
        f"Title  : {d['page_title']}",
        f"Main wrapper classes: {d['main_element_classes']}",
        f"",
        f"Articles ({d['article_count']} total, showing first {len(d['articles'])}):",
    ]
    for i, art in enumerate(d["articles"], 1):
        lines.append(f"  [{i}] classes={art['classes']}")
        lines.append(f"       link  ={art['first_link']}")
        lines.append(f"       text  ={art['text_snippet']!r}")
    lines += [
        "",
        f"Classes containing 'tribe' or 'event' ({len(d['tribe_event_classes'])} unique):",
    ]
    for c in d["tribe_event_classes"]:
        lines.append(f"  {c}")
    lines += [
        "",
        f"Links containing '/event' ({len(d['event_links'])}):",
    ]
    for lnk in d["event_links"]:
        lines.append(f"  {lnk}")
    lines += [
        "",
        f"<time> elements ({len(d['time_elements'])}):",
    ]
    for t in d["time_elements"]:
        lines.append(f"  datetime={t['datetime']!r}  text={t['text']!r}")
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# login
# ---------------------------------------------------------------------------

def do_login(session: requests.Session) -> tuple[bool, str, str]:
    """Returns (success, redirect_url, response_html)."""
    r = session.get(LOGIN_URL, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")

    payload = {
        "log":         USERNAME,
        "wp-submit":   "Log In",
        "redirect_to": BASE_URL + "/wp-admin/",
        "testcookie":  "1",
    }
    for inp in soup.select("input[type=hidden]"):
        name = inp.get("name")
        val  = inp.get("value", "")
        if name:
            payload[name] = val

    resp = session.post(
        LOGIN_URL,
        data={**payload, "pwd": PASSWORD},
        timeout=20,
        allow_redirects=True,
        headers={
            "Referer":      LOGIN_URL,
            "Origin":       BASE_URL,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    has_auth_cookie = any(k.startswith("wordpress_logged_in") for k in session.cookies.keys())
    success = has_auth_cookie or ("wp-login.php" not in resp.url)
    return success, resp.url, resp.text


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    print(f"\n{'='*60}")
    print("MYC Diagnostic Scraper")
    print(f"{'='*60}")
    print(f"Output directory: {OUT_DIR}")
    print(f"Credentials supplied: {'yes' if (USERNAME and PASSWORD) else 'NO'}")
    print()

    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0"
    browser_headers = {
        "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
    }
    summaries = []

    # ------------------------------------------------------------------
    # 1. Login page HTML
    # ------------------------------------------------------------------
    print("Step 1 — fetching login page...")
    s_noauth = requests.Session()
    s_noauth.headers.update({"User-Agent": ua, **browser_headers})
    r = s_noauth.get(LOGIN_URL, timeout=20)
    print(f"  HTTP {r.status_code}  {r.url}")
    save("login_page.html", r.text)

    # ------------------------------------------------------------------
    # 2. Events page WITHOUT authentication
    # ------------------------------------------------------------------
    print("\nStep 2 — fetching events page (no auth)...")
    r_noauth = s_noauth.get(EVENTS_URL, timeout=20)
    print(f"  HTTP {r_noauth.status_code}  {r_noauth.url}")
    save("events_noauth.html", r_noauth.text)
    soup_noauth = BeautifulSoup(r_noauth.text, "html.parser")
    summaries.append(page_summary("events (no auth)", r_noauth.url, r_noauth.status_code, soup_noauth))

    # ------------------------------------------------------------------
    # 3. Login attempt
    # ------------------------------------------------------------------
    s_auth = requests.Session()
    s_auth.headers.update({"User-Agent": ua, **browser_headers})
    login_ok = False

    if USERNAME and PASSWORD:
        print("\nStep 3 — attempting login...")
        login_ok, login_redirect, login_response_html = do_login(s_auth)
        print(f"  Login {'SUCCEEDED' if login_ok else 'FAILED'}")
        print(f"  Redirect URL : {login_redirect}")
        print(f"  Cookies set  : {list(s_auth.cookies.keys())}")
        save("login_response.html", login_response_html)

        # Save cookie names only (not values, to avoid writing auth tokens to disk)
        save("login_cookies.json", json.dumps({"cookie_names": list(s_auth.cookies.keys()), "login_succeeded": login_ok, "redirect_url": login_redirect}, indent=2))
    else:
        print("\nStep 3 — skipping login (no credentials).")

    # ------------------------------------------------------------------
    # 4. Events page WITH authentication
    # ------------------------------------------------------------------
    print("\nStep 4 — fetching events page (authenticated session)...")
    r_auth = s_auth.get(EVENTS_URL, timeout=20)
    print(f"  HTTP {r_auth.status_code}  {r_auth.url}")
    save("events_auth.html", r_auth.text)
    soup_auth = BeautifulSoup(r_auth.text, "html.parser")
    summaries.append(page_summary("events (authenticated)" if login_ok else "events (auth-attempted)", r_auth.url, r_auth.status_code, soup_auth))

    # ------------------------------------------------------------------
    # 5. First individual event page (authenticated)
    # ------------------------------------------------------------------
    event_links = [
        a.get("href", "") for a in soup_auth.select("a[href*='/event/']")
        if a.get("href", "").startswith(BASE_URL)
    ]
    # Also try relative links
    if not event_links:
        event_links = [
            BASE_URL.rstrip("/") + a.get("href", "")
            for a in soup_auth.select("a[href^='/event/']")
        ]
    # Fall back to any /event-* style link
    if not event_links:
        event_links = [
            a.get("href", "") for a in soup_auth.select("a[href]")
            if re.search(r"/event", a.get("href", ""), re.I)
               and a.get("href", "").startswith(BASE_URL)
        ]

    if event_links:
        first_event_url = event_links[0]
        print(f"\nStep 5 — fetching first event detail page: {first_event_url}")
        r_event = s_auth.get(first_event_url, timeout=20)
        print(f"  HTTP {r_event.status_code}  {r_event.url}")
        save("event_detail.html", r_event.text)
        soup_event = BeautifulSoup(r_event.text, "html.parser")
        summaries.append(page_summary("event detail", r_event.url, r_event.status_code, soup_event))
    else:
        print("\nStep 5 — no event detail links found, skipping.")

    # ------------------------------------------------------------------
    # 6. Write summary files
    # ------------------------------------------------------------------
    print("\nStep 6 — writing summary files...")
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "credentials_supplied": bool(USERNAME and PASSWORD),
        "login_succeeded": login_ok,
        "pages": summaries,
    }
    save("structure.json", json.dumps(meta, indent=2, ensure_ascii=False))

    txt_parts = [
        "MYC Diagnostic Report",
        f"Generated : {meta['generated_at']}",
        f"Credentials supplied : {meta['credentials_supplied']}",
        f"Login succeeded      : {meta['login_succeeded']}",
        "",
    ]
    for s in summaries:
        txt_parts.append(fmt_section(s))
    save("structure.txt", "\n".join(txt_parts))

    print(f"\n✅  Diagnostic complete. Files written to {OUT_DIR}")

    # Exit non-zero if login failed with credentials (helps CI flag the issue)
    if USERNAME and PASSWORD and not login_ok:
        print("⚠️  Login failed — check MYC_USERNAME / MYC_PASSWORD secrets.")
        sys.exit(1)


if __name__ == "__main__":
    main()
