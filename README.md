# MYC Weekly Message Generator

Automatically generates the weekly WhatsApp update for Margate Yacht Club, combining:
- 📅 **Events & duties** scraped from the MYC website
- 🌊 **Tides** from PLA Margate predictions
- 🌬️ **Weather** from [Open-Meteo](https://open-meteo.com) (free, no API key)

## How it works

```
Every day at 12:00 UK local time (Europe/London)
        ↓
GitHub Actions runs scraper/scrape_myc.py
        ↓
Logs into MYC website → scrapes events + duties for next 14 days
        ↓
Validates and commits data/events.json to the repo
        ↓
GitHub Pages (deploy from main/root) serves index.html → fetches data/events.json + live weather
        ↓
Copy the generated message → paste into WhatsApp 🎉
```

## Setup

### 1. Create the repository
```bash
gh repo create myc-weekly-message --public
cd myc-weekly-message
# copy all these files in
git push -u origin main
```

### 2. Enable GitHub Pages (root deploy)
- Settings → Pages → Source: **Deploy from branch**
- Branch: **main**
- Folder: **/ (root)**

### 3. Add secrets for MYC login
Settings → Secrets and variables → Actions → New repository secret:
- `MYC_USERNAME` — your MYC website username/email
- `MYC_PASSWORD` — your MYC website password

> ⚠️ These are for the **MYC website** (no 2FA required), NOT the Sailing Club Manager portal.

### 4. Run the workflow manually first (test/fresh data push)
Actions → "Update MYC Events" → **Run workflow**
- Leave `force_refresh` checked (default) to force a fresh scrape immediately.

### 5. Check the output
Open `https://yourusername.github.io/myc-weekly-message/`

## First-time setup checklist

- [ ] GitHub Pages enabled with **main / root**
- [ ] `MYC_USERNAME` and `MYC_PASSWORD` secrets added
- [ ] Manual workflow run completed successfully
- [ ] `data/events.json` updated by workflow
- [ ] Site URL loads and shows generated message content

## Daily operations & troubleshooting

### Trigger model
- Scheduled runs happen every day at 12:00 UK local time (Europe/London) with timezone-safe gating.
- Manual runs are available anytime using **Run workflow** and `force_refresh=true`.

### Post-run checks
- Actions run status is ✅ successful.
- `data/events.json` commit appears when data changes.
- Site reflects fresh timestamp/content.

### If a run fails
1. Open Actions → latest **Update MYC Events** run.
2. Check logs for:
   - login/credentials issues (`MYC_USERNAME`, `MYC_PASSWORD`)
   - MYC site structure changes affecting selectors
   - temporary network/API failures
3. Fix issue, then rerun manually with `force_refresh=true`.
4. Previous `data/events.json` remains as fallback so the UI still loads.

## Updating tide data

When the 2026 tide data runs out, copy the updated `RAW_TIDES` array from
[can-i-sail](https://rowsejr.github.io/can-i-sail/) into `index.html`.

## Known limitations

- **Sailing Club Manager** (clubmin.net) requires 2FA, so duty roster from there
  cannot be automated. The scraper uses the public MYC event pages instead.
- If the MYC website structure changes, `scraper/scrape_myc.py` may need updating.
- Weather forecasts are only available ~10 days ahead.

## Local development

```bash
cd scraper
pip install -r requirements.txt
export MYC_USERNAME="your@email.com"
export MYC_PASSWORD="yourpassword"
python scrape_myc.py
# Then open index.html in a browser (use Live Server or similar to avoid CORS)
```
