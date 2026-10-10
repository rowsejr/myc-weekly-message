# SCM Alternative — Project Overview

> **Goal:** Replace Sailing Club Manager (clubmin.net, ~£3,000/yr) with a self-hosted, open-source sailing club management platform tailored to Margate Yacht Club (MYC).

---

## What Sailing Club Manager Currently Provides

Based on analysis of the MYC usage and known SCM feature set:

| Module | SCM Capability | Notes |
|---|---|---|
| Membership | Member records, renewals, payments | Core paid feature |
| Boat Register | Boat details, storage allocation, fees | Includes crane/lift booking |
| Events/Calendar | Event creation, duty assignment | 2FA-protected portal |
| Race Results | Series, results entry, handicaps (PY/IRC) | RYA handicap tables |
| Training | Course bookings, qualifications tracking | Basic ticketing |
| Communications | Member emails/newsletters | Rudimentary |
| Finance | Invoicing, subscriptions, basic accounting | Limited reporting |

SCM is described internally as a **"relatively rudimentary database"** — it stores records but offers little intelligence, poor UX, and expensive annual licensing.

---

## Replacement Architecture — Five Modules

```
┌─────────────────────────────────────────────────────────┐
│                    MYC Club Platform                    │
├──────────┬──────────┬──────────┬──────────┬────────────┤
│ Members  │  Boats   │ Calendar │ Training │  Racing    │
│ Manager  │ & Storage│ & Events │& Tickets │ & Results  │
└──────────┴──────────┴──────────┴──────────┴────────────┘
         ↑ Shared auth, notifications, payments ↑
```

---

## Staged Delivery Plan

| Stage | Name | Delivers | Estimated Effort |
|---|---|---|---|
| [Stage 1](./01-mvp.md) | MVP | Auth + Members + Basic Events | 2–4 weeks |
| [Stage 2](./02-core-modules.md) | Core Modules | Boats + Calendar + Duties | 4–6 weeks |
| [Stage 3](./03-advanced-features.md) | Advanced Features | Racing + Training/Tickets | 6–8 weeks |
| [Stage 4](./04-full-platform.md) | Full Platform | Finance + Communications + Polish | 4–6 weeks |

**Total estimated build:** 16–24 weeks part-time (2–3 days/week), or 8–12 weeks full-time.

---

## Cost Comparison

| | SCM | Self-Hosted Alternative |
|---|---|---|
| Annual licence | £3,000 | £0 |
| Hosting (VPS/cloud) | Included | ~£120–£240/yr (e.g. Hetzner CX21) |
| Payment processing | ~2.5% | Stripe ~1.4% + 20p |
| Maintenance | Vendor | Club volunteer / committee |
| Data ownership | Vendor | **Club owns all data** |
| Customisation | None | Unlimited |

**Break-even in Year 1.** Net saving from Year 2: ~£2,760+/yr.

---

## Technology Decision

See [Tech Stack & Libraries](./05-tech-stack.md) for full research.

**Recommended stack:**
- **Backend:** Python / FastAPI (familiar from this repo's scraper)
- **Database:** PostgreSQL (via Supabase free tier for early stage, or self-hosted)
- **Frontend:** Next.js (React) + Tailwind CSS
- **Auth:** NextAuth.js or Supabase Auth (magic link + optional 2FA)
- **Payments:** Stripe
- **Email:** Resend.com (free tier generous)
- **Hosting:** Vercel (frontend) + Railway or Fly.io (backend/DB)

---

## Files in This Planning Directory

| File | Contents |
|---|---|
| `00-overview.md` | This file — full project overview |
| `01-mvp.md` | Stage 1: MVP build plan |
| `02-core-modules.md` | Stage 2: Boats, Calendar, Duties |
| `03-advanced-features.md` | Stage 3: Racing, Training, Ticketing |
| `04-full-platform.md` | Stage 4: Finance, Comms, polish |
| `05-tech-stack.md` | Library research & technology decisions |

---

## Starting a New Project

When you are ready to build:
1. Create a new GitHub repo: `myc-club-platform` (or similar)
2. Copy the tech stack decisions from `05-tech-stack.md`
3. Begin with `01-mvp.md` — complete Stage 1 before touching later stages
4. Keep SCM running in parallel until Stage 3 is complete and tested

> ⚠️ **Note on SCM data:** SCM requires 2FA so automated migration is not possible. Plan a one-time manual export (CSV/Excel) from SCM's admin panel for member and boat records, then import via a migration script in Stage 1.
