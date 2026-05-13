# MYC Weekly Message Generator

Automatically generates the weekly WhatsApp update for Margate Yacht Club, combining:
- 📅 **Events & duties** scraped from the MYC website
- 🌊 **Tides** from PLA Margate predictions
- 🌬️ **Weather** from [Open-Meteo](https://open-meteo.com) (free, no API key)

## How it works

```
Every Wednesday 06:00 UTC
        ↓
GitHub Actions runs scraper/scrape_myc.py
        ↓
Logs into MYC website → scrapes events + duties for next 14 days
        ↓
Commits data/events.json to the repo
        ↓
GitHub Pages serves index.html → fetches data/events.json + live weather
        ↓
Heather copies the generated message → pastes into WhatsApp 🎉
```

## Setup

### 1. Create the repository
```bash
gh repo create myc-weekly-message --public
cd myc-weekly-message
# copy all these files in
git push -u origin main
```

### 2. Enable GitHub Pages
- Settings → Pages → Source: **GitHub Actions** or **Deploy from branch (main / root)**

### 3. Add secrets for MYC login
Settings → Secrets and variables → Actions → New repository secret:
- `MYC_USERNAME` — your MYC website username/email
- `MYC_PASSWORD` — your MYC website password

> ⚠️ These are for the **MYC website** (no 2FA required), NOT the Sailing Club Manager portal.

### 4. Run the workflow manually first
Actions → "Update MYC Events" → Run workflow

### 5. Check the output
Open `https://yourusername.github.io/myc-weekly-message/`

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