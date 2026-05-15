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
LOGIN_URL = f"{BASE_URL}/login"
DO_LOGIN_URL = f"{BASE_URL}/do_login"
EVENTS_URL = f"{BASE_URL}/events"
ROSTER_URL = f"{BASE_URL}/roster"

USERNAME = os.environ.get("MYC_USERNAME", "")
PASSWORD = os.environ.get("MYC_PASSWORD", "")

# TLS verification: set MYC_VERIFY_TLS=0 to disable verification temporarily
# for debugging behind corporate proxies. Prefer configuring REQUESTS_CA_BUNDLE
# / SSL_CERT_FILE with your corporate root CA bundle.
VERIFY_TLS = os.environ.get("MYC_VERIFY_TLS", "1").strip().lower() not in {"0", "false", "no"}

OUTPUT_PATH = Path(__file__).parent.parent / "data" / "events.json"


def login(session: requests.Session) -> bool:
    """Log into the MYC site (Boxstuff /do_login form)."""
    if not (USERNAME and PASSWORD):
        return False

    r = session.get(LOGIN_URL, timeout=20, verify=VERIFY_TLS)
    soup = BeautifulSoup(r.text, "html.parser")

    token_el = soup.select_one("form[action='/do_login'] input[name='authenticity_token']") or soup.select_one(
        "input[name='authenticity_token']"
    )
    token = token_el.get("value", "") if token_el else ""

    redirect = "/portal"
    payload = {
        "utf8": "✓",
        "authenticity_token": token,
        "email": USERNAME,
        "password": PASSWORD,
        "redirect": redirect,
        "redirect_bad": redirect,
        "commit": "Login",
    }

    resp = session.post(
        DO_LOGIN_URL,
        data=payload,
        timeout=20,
        allow_redirects=True,
        verify=VERIFY_TLS,
        headers={
            "Referer": LOGIN_URL,
            "Origin": BASE_URL,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    # Logged-in indicator: logout link appears in the HTML
    if "/do_logout" in (resp.text or ""):
        return True

    # Fallback: try fetching /portal and see if logout is present
    probe = session.get(BASE_URL + "/portal", timeout=20, verify=VERIFY_TLS)
    return "/do_logout" in (probe.text or "")


def fetch_events_list(session: requests.Session) -> list[dict]:
    """Fetch the /events page and extract event links for the next 14 days."""
    today = datetime.now(timezone.utc).date()
    cutoff = today + timedelta(days=14)

    r = session.get(EVENTS_URL, timeout=20, verify=VERIFY_TLS)
    print(f"  Events page: {r.url} (HTTP {r.status_code})")
    soup = BeautifulSoup(r.text, "html.parser")
    if soup.title:
        print(f"  Page title: {soup.title.string.strip()}")
    events: list[dict] = []

    # ------------------------------------------------------------------
    # Strategy A (current MYC site): boxstuff-style calendar
    # Each event appears in a <div class='ui-cell ui-space ...'> with a
    # mini-calendar (month/day) and a title link to /event/...
    # Example:
    #   <div class='ui-cell ui-space' ...>
    #     <div class='ui-month'>May</div>
    #     <div class='ui-day'>17</div>
    #     <a href="/event/commodore-cup-8">Commodore Cup...</a>
    #     <span style='color:#888;'>Sunday 17 May, 10:30-13:30</span>
    # ------------------------------------------------------------------
    ui_cells = soup.select("div.ui-cell")
    if ui_cells:
        print(f"  Selector 'div.ui-cell' matched {len(ui_cells)} element(s)")
        for cell in ui_cells:
            link_el = cell.select_one("a[href^='/event/'], a[href*='/event/']")
            if not link_el:
                continue

            title = link_el.get_text(strip=True)
            href = (link_el.get("href") or "").strip()
            url = href if href.startswith("http") else (BASE_URL.rstrip("/") + href)

            # Prefer parsing date from the human-readable line (more reliable)
            raw_when = ""
            when_el = cell.select_one("span[style*='color:#888']")
            if when_el:
                raw_when = when_el.get_text(" ", strip=True)

            event_date = parse_date(raw_when)
            if event_date is None:
                # Fallback: month/day blocks in the mini calendar
                m_el = cell.select_one(".ui-cal-md .ui-month")
                d_el = cell.select_one(".ui-cal-md .ui-day")
                if m_el and d_el:
                    try:
                        month_name = m_el.get_text(strip=True)
                        day_num = int(d_el.get_text(strip=True))
                        # Use current year from 'today'; calendar page is current/upcoming.
                        event_date = datetime.strptime(f"{day_num} {month_name} {today.year}", "%d %b %Y").date()
                    except Exception:
                        event_date = None

            if event_date is None:
                continue
            if event_date < today or event_date > cutoff:
                continue

            events.append({"title": title, "date": str(event_date), "url": url, "duties": {}})

        # If we found anything with this strategy, return early.
        if events:
            return events

    # ------------------------------------------------------------------
    # Strategy B (older site): The Events Calendar plugin (tribe_*)
    # ------------------------------------------------------------------
    selector_sets = [
        "article.type-tribe_events",
        ".tribe-events-calendar-list__event",
        ".tribe-event",
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
            sample = list(dict.fromkeys(" ".join(e.get("class", [])) for e in tribe_els))[:8]
            print(f"  Elements with 'tribe'/'event' classes: {sample}")
        return events

    for article in articles:
        link_el = article.select_one("a.url, h2 a, h3 a, .tribe-event-url, a[href*='/event/']")
        if not link_el:
            link_el = article.select_one("a[href]")
        title_el = article.select_one(".tribe-events-list-event-title, .tribe-events-calendar-list__event-title, h2, h3")
        date_el = article.select_one(".tribe-event-date-start, .tribe-events-abbr, time[datetime]")
        if not date_el:
            date_el = article.select_one("time, .tribe-events-schedule")

        if not link_el:
            continue

        href = link_el.get("href", "").strip()
        url = href if href.startswith("http") else (BASE_URL.rstrip("/") + href)
        title = (title_el.get_text(strip=True) if title_el else link_el.get_text(strip=True))

        raw_date = (date_el.get("datetime") if date_el else None) or (date_el.get_text(strip=True) if date_el else "")
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
    if not raw:
        return None

    # Common patterns on the MYC events page include:
    #   "Sunday 17 May, 10:30-13:30"
    #   "Friday 15 May, 19:30-16:00"
    m = re.search(r"\b(\d{1,2})\s+([A-Za-z]{3,9})\b", raw)
    if m:
        try:
            day = int(m.group(1))
            mon = m.group(2)
            # Assume current year in UTC for the rolling 14-day window.
            year = datetime.now(timezone.utc).year
            return datetime.strptime(f"{day} {mon} {year}", "%d %B %Y").date()
        except Exception:
            # Try abbreviated month
            try:
                year = datetime.now(timezone.utc).year
                return datetime.strptime(f"{day} {mon} {year}", "%d %b %Y").date()
            except Exception:
                pass

    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d %B %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(raw.strip()[: len(fmt) + 2], fmt).date()
        except Exception:
            pass

    m = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except Exception:
            pass
    return None


def scrape_event_duties(session: requests.Session, event: dict) -> dict:
    """Deprecated.

    Duty assignments are not consistently rendered on individual /event/* pages.
    Use `scrape_roster_duties()` and match back onto events by (title, date).
    """
    _ = (session, event)
    return {}


def _normalize_title(s: str) -> str:
    s = (s or "").strip().lower()
    # roster shows things like: "Event Title : Sub-title"
    # events list usually only shows "Event Title". Use lhs for matching.
    s = s.split(":", 1)[0].strip()
    s = re.sub(r"\s+", " ", s)
    return s


def scrape_roster_duties(session: requests.Session) -> dict[tuple[str, str], dict]:
    """Scrape duty assignments from the authenticated /roster table.

    Returns a mapping keyed by (date_iso, normalized_event_title) with a value:
      {
        "event_title": "...",        # as displayed in roster
        "date": "YYYY-MM-DD",
        "assignments": {
           "Power Boat Helm (PB2)": [{"name": "...", "role": "PB2 Qualified", "status": "confirmed"/"pending"/"needed"/"unassigned"/"unknown", "member_url": "..."}],
            ...
        }
      }
    """
    r = session.get(ROSTER_URL, timeout=20, verify=VERIFY_TLS)
    if r.status_code != 200:
        print(f"  Roster page: {r.url} (HTTP {r.status_code})")
        return {}

    if "/do_logout" not in (r.text or ""):
        # Not authenticated
        return {}

    soup = BeautifulSoup(r.text, "html.parser")
    page = soup.select_one("#ui-object-page-content") or soup
    table = page.select_one("table.pretty")
    if not table:
        return {}

    duties_by_event: dict[tuple[str, str], dict] = {}

    current_date_iso: str | None = None
    current_event_title_raw: str | None = None

    for row in table.select("tbody tr"):
        tds = row.select("td")
        if len(tds) < 4:
            continue

        # Column 1: date + event title (only present on group-begin)
        col0 = tds[0]
        date_text = (col0.select_one("span") or col0).get_text(" ", strip=True)
        title_el = col0.select_one("strong")
        title_text = title_el.get_text(" ", strip=True) if title_el else ""

        if row.get("class") and "group-begin" in row.get("class"):
            # date_text like: "Sun 17 May"; assume current year.
            # Use parse_date helper and serialize to ISO.
            dt = parse_date(date_text)
            current_date_iso = str(dt) if dt else None
            current_event_title_raw = title_text or None

        if not current_date_iso or not current_event_title_raw:
            # Can't attribute row
            continue

        # Column 2: duty name + (optional) role/qualifier in a small <p>
        duty_cell = tds[1]
        duty_name = duty_cell.get_text("\n", strip=True).split("\n", 1)[0].strip()
        role_el = duty_cell.select_one("p")
        role = role_el.get_text(" ", strip=True) if role_el else ""

        # Cleanup common noise / whitespace
        duty_name = re.sub(r"\s+", " ", duty_name).strip()
        role = re.sub(r"\s+", " ", role).strip()
        if role == "":
            role = None

        contact_cell = tds[3]
        member_a = contact_cell.select_one("a[href^='/member/']")
        name = member_a.get_text(" ", strip=True) if member_a else ""
        member_url = ""
        if member_a and member_a.get("href"):
            href = member_a.get("href").strip()
            member_url = href if href.startswith("http") else (BASE_URL.rstrip("/") + href)

        status = "unknown"
        if contact_cell.select_one("img[alt*='Tick'], img[src*='tick']"):
            status = "confirmed"
        elif "pending" in contact_cell.get_text(" ", strip=True).lower():
            status = "pending"
        elif contact_cell.select_one("form.volunteer"):
            status = "needed"
        elif contact_cell.get_text(" ", strip=True) == "-":
            status = "unassigned"

        key = (current_date_iso, _normalize_title(current_event_title_raw))
        bucket = duties_by_event.setdefault(
            key,
            {
                "event_title": current_event_title_raw,
                "date": current_date_iso,
                "assignments": {},
            },
        )

        bucket["assignments"].setdefault(duty_name, []).append(
            {
                "name": name or None,
                "role": role,
                "status": status,
                "member_url": member_url or None,
            }
        )

    return duties_by_event


def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-GB,en;q=0.9",
    })

    print("Logging in to MYC website...")
    logged_in = False
    if USERNAME and PASSWORD:
        logged_in = login(session)
        print(f"  Login {'succeeded' if logged_in else 'FAILED (continuing without duties)'}")
    else:
        print("  No credentials set — running without login (events only)")

    print("Fetching events list...")
    events = fetch_events_list(session)
    print(f"  Found {len(events)} events in next 14 days")

    roster_by_event: dict[tuple[str, str], dict] = {}
    if logged_in:
        print("Fetching duty roster...")
        roster_by_event = scrape_roster_duties(session)
        print(f"  Parsed roster entries: {len(roster_by_event)}")

    duties_by_url: dict[str, dict] = {}

    for ev in events:
        # Attach roster duties to each event
        key = (ev.get("date", ""), _normalize_title(ev.get("title", "")))
        roster_item = roster_by_event.get(key)
        if roster_item:
            ev["duties"] = roster_item.get("assignments", {})
        else:
            ev["duties"] = {}

        duties_by_url[ev["url"]] = {
            "title": ev["title"],
            "date": ev["date"],
            "url": ev["url"],
            "duties": ev.get("duties", {}),
        }

    # Write events output (used by GitHub Pages)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "events": events,
    }
    OUTPUT_PATH.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\n✅ Written {len(events)} events to {OUTPUT_PATH}")

    # Write duties snapshot separately (so you can evolve format without breaking the page)
    duties_path = Path(__file__).parent.parent / "data" / "duties.json"
    duties_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "logged_in": logged_in,
        "source": "roster",
        "duties": duties_by_url,
    }
    duties_path.write_text(json.dumps(duties_payload, indent=2, ensure_ascii=False))
    print(f"✅ Written duties snapshot to {duties_path}")


if __name__ == "__main__":
    main()
