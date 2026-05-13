#!/usr/bin/env python3
"""
Scraper for Margate Yacht Club website.
Logs in, finds upcoming events for the next 14 days, and extracts duty assignments.
Writes output to data/events.json.
"""
import os
import re
import json
import requests
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup
from pathlib import Path

BASE_URL  = "https://www.margateyachtclub.co.uk"
LOGIN_URL = f"{BASE_URL}/wp-login.php"
EVENTS_URL = f"{BASE_URL}/events"

USERNAME = os.environ.get("MYC_USERNAME", "")
PASSWORD = os.environ.get("MYC_PASSWORD", "")

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "events.json"


def login(session: requests.Session) -> bool:
    """Log into the MYC WordPress site."""
    # Fetch login page first (to get any nonce/hidden fields)
    r = session.get(LOGIN_URL, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")

    payload = {
        "log":         USERNAME,
        "pwd":         PASSWORD,
        "wp-submit":   "Log In",
        "redirect_to": BASE_URL + "/wp-admin/",
        "testcookie":  "1",
    }
    # Include any hidden fields (nonce, etc.)
    for inp in soup.select("input[type=hidden]"):
        name = inp.get("name")
        val  = inp.get("value", "")
        if name:
            payload[name] = val

    resp = session.post(LOGIN_URL, data=payload, timeout=20, allow_redirects=True)
    # Definitive indicator: WordPress sets a wordpress_logged_in_* cookie on success
    if any(k.startswith("wordpress_logged_in") for k in session.cookies.keys()):
        return True
    # Fallback: if we were redirected away from the login page, assume success
    success = "wp-login.php" not in resp.url
    if not success:
        print(f"    (login response URL: {resp.url}, status: {resp.status_code})")
    return success


def fetch_events_list(session: requests.Session) -> list[dict]:
    """Fetch the /events page and extract event links for the next 14 days."""
    today = datetime.now(timezone.utc).date()
    cutoff = today + timedelta(days=14)

    r = session.get(EVENTS_URL, timeout=20)
    print(f"  Events page: {r.url} (HTTP {r.status_code})")
    soup = BeautifulSoup(r.text, "html.parser")
    if soup.title:
        print(f"  Page title: {soup.title.string.strip()}")
    events = []

    # The MYC site uses The Events Calendar plugin — standard class names.
    # Try multiple selector strategies from most-specific to most-general.
    selector_sets = [
        # The Events Calendar v5+
        "article.type-tribe_events",
        # The Events Calendar list view items
        ".tribe-events-calendar-list__event",
        ".tribe-event",
        # Older Events Calendar or custom themes
        "article[class*=tribe]",
        "article[class*=event]",
        ".tribe-event-url",
    ]
    articles = []
    for sel in selector_sets:
        articles = soup.select(sel)
        if articles:
            print(f"  Selector '{sel}' matched {len(articles)} element(s)")
            break

    if not articles:
        # Diagnostic: report what article classes exist and tribe-like elements
        all_articles = soup.select("article")
        if all_articles:
            sample_classes = [" ".join(a.get("class", [])) for a in all_articles[:5]]
            print(f"  No event articles matched — article classes found: {sample_classes}")
        tribe_els = soup.select("[class*=tribe], [class*=event]")
        if tribe_els:
            sample = list({" ".join(e.get("class", [])) for e in tribe_els})[:8]
            print(f"  Elements with 'tribe'/'event' classes: {sample}")
        return events

    for article in articles:
        # Try to find the event link and title
        link_el = article.select_one("a.url, h2 a, h3 a, .tribe-event-url, a[href*='/event/']")
        if not link_el:
            link_el = article.select_one("a[href]")
        title_el = article.select_one(".tribe-events-list-event-title, .tribe-events-calendar-list__event-title, h2, h3")
        date_el  = article.select_one(".tribe-event-date-start, .tribe-events-abbr, time[datetime]")
        if not date_el:
            date_el = article.select_one("time, .tribe-events-schedule")

        if not link_el:
            continue

        url   = link_el.get("href", "").strip()
        title = (title_el.get_text(strip=True) if title_el else link_el.get_text(strip=True))

        # Parse date
        raw_date = date_el.get("datetime") or date_el.get_text(strip=True) if date_el else ""
        event_date = parse_date(raw_date)
        if event_date is None:
            continue
        if event_date < today or event_date > cutoff:
            continue

        events.append({"title": title, "date": str(event_date), "url": url, "duties": {}})

    return events


def parse_date(raw: str):
    """Try several formats, return a date object or None."""
    from datetime import date
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d %B %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(raw.strip()[:len(fmt)+2], fmt).date()
        except Exception:
            pass
    # Try to find yyyy-mm-dd anywhere in the string
    m = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except Exception:
            pass
    return None


def scrape_event_duties(session: requests.Session, event: dict) -> dict:
    """Visit the individual event page and extract duty/role assignments."""
    url = event["url"]
    if not url:
        return {}

    r = session.get(url, timeout=20)
    soup = BeautifulSoup(r.text, "html.parser")

    duties = {}

    # Strategy: look for common patterns in MYC event pages.
    # The event content is usually in .tribe-events-single or .entry-content
    content = soup.select_one(".tribe-events-single-section, .tribe-events-single, .entry-content, article")
    if not content:
        content = soup

    text = content.get_text("\n", strip=True)

    # Extract roles using common patterns from the sample messages
    patterns = {
        "race_officer":      r"Race Officers?:\s*(.+)",
        "safety_boat_helm":  r"Safety Boat [Hh]elm[:\s]+(.+)",
        "safety_boat_crew":  r"Safety Boat [Cc]rew[:\s]+(.+)",
        "safety_boat":       r"Safety Boat[:\s]+(.+)",
        "instructor":        r"Instructor[:\s]+(.+)",
        "briefing":          r"(?:Race |Safety )?[Bb]riefing(?:\s+at)?[:\s]+(.+)",
        "race_start":        r"Race [Ss]tart[:\s]+(.+)",
        "meet":              r"Meet.*?(?:from|at|:)\s*(.+)",
        "on_water":          r"On water[:\s]+(.+)",
    }

    for key, pattern in patterns.items():
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            duties[key] = m.group(1).strip().split("\n")[0].strip()

    # Also try table-based layouts (some WordPress themes use tables for duties)
    for row in content.select("tr"):
        cells = [td.get_text(strip=True) for td in row.select("td, th")]
        if len(cells) >= 2:
            label = cells[0].lower()
            value = cells[1]
            if "race officer" in label:
                duties["race_officer"] = value
            elif "safety" in label and "helm" in label:
                duties["safety_boat_helm"] = value
            elif "safety" in label and "crew" in label:
                duties["safety_boat_crew"] = value
            elif "safety" in label:
                duties["safety_boat"] = value

    # Parse event times from the page
    time_el = soup.select_one(".tribe-events-schedule, .tribe-event-date-start")
    if time_el:
        duties["_event_time_raw"] = time_el.get_text(strip=True)

    return duties


def main():
    session = requests.Session()
    session.headers["User-Agent"] = (
        "Mozilla/5.0 (compatible; MYCBot/1.0; +https://github.com/rowsejr)"
    )

    print("Logging in to MYC website...")
    if USERNAME and PASSWORD:
        ok = login(session)
        print(f"  Login {'succeeded' if ok else 'FAILED (continuing anyway)'}")
    else:
        print("  No credentials set — running without login (public events only)")

    print("Fetching events list...")
    events = fetch_events_list(session)
    print(f"  Found {len(events)} events in next 14 days")

    for ev in events:
        print(f"  Scraping duties for: {ev['title']} ({ev['date']})")
        ev["duties"] = scrape_event_duties(session, ev)

    # Write output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "events": events,
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\n✅ Written {len(events)} events to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
