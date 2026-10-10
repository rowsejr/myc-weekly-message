# Tech Stack & Library Research

> Deep-dive into technology choices for the MYC Club Platform. Each decision is justified against the alternatives with links for further investigation.

---

## Core Framework Decision

### Option A: Next.js (App Router) — **RECOMMENDED**
- Full-stack React framework — handles both frontend and API routes
- Server-side rendering for fast public pages (events, results)
- App Router provides server components (excellent for data-heavy tables)
- Huge ecosystem, extensive documentation, Vercel deployment is trivial
- **TypeScript first** — reduces bugs in complex domain logic (handicaps, scoring)

### Option B: Python FastAPI backend + React frontend
- Pro: consistent with existing `scrape_myc.py` Python codebase
- Con: two separate deployments, CORS complexity, more infrastructure to manage
- Better choice if the platform needs to be a pure API (for mobile app first)

### Option C: Django (Python full-stack)
- Pro: excellent admin panel out of the box, Django ORM is mature
- Con: Python templating is dated, less JS ecosystem, needs separate React for interactivity

**Decision: Next.js 14 (App Router) + TypeScript.** FastAPI can be added later if a mobile app requires a pure REST API.

---

## Database

### PostgreSQL — **RECOMMENDED**
- Relational DB: perfect for membership/race/finance data with complex relationships
- JSON columns available for flexible metadata
- Excellent tooling: pgAdmin, TablePlus, Prisma Studio

### Prisma ORM — **RECOMMENDED**
```bash
pnpm add prisma @prisma/client
npx prisma init --datasource-provider postgresql
```
- Type-safe queries generated from schema
- Auto-complete in VS Code
- Migration system tracks schema changes
- Prisma Studio = visual DB browser (excellent for committee demos)

### Supabase — **RECOMMENDED for early stage**
- Managed PostgreSQL with generous free tier (500MB, unlimited API calls)
- Built-in Auth (alternative to NextAuth if preferred)
- Real-time subscriptions (useful for live race recording)
- Row-level security for data isolation
- URL: https://supabase.com — Free → Pro ($25/mo) as needed

---

## Authentication

### Auth.js (NextAuth v5) — **RECOMMENDED**
```bash
pnpm add next-auth@beta
```
- Magic link email (passwordless — ideal for members not used to passwords)
- Social providers (Google login) easy to add
- Credentials provider available if passwords are required
- Built-in CSRF protection, secure httpOnly cookies
- Works seamlessly with Next.js App Router
- Docs: https://authjs.dev

### Alternative: Supabase Auth
- If using Supabase for DB, can use Supabase Auth instead of NextAuth
- Magic links, OTP, social auth all included
- Simpler setup but more vendor lock-in

---

## UI Components

### shadcn/ui — **RECOMMENDED**
```bash
npx shadcn-ui@latest init
npx shadcn-ui@latest add button card table form dialog
```
- NOT a component library — it's a code generator
- Components are copied into your project (full control)
- Built on Radix UI (accessible, unstyled primitives) + Tailwind CSS
- Consistent, professional design out of the box
- Docs: https://ui.shadcn.com

### Tailwind CSS — **RECOMMENDED** (installed with shadcn/ui)
- Utility-first CSS — fast to build with, no CSS naming bikeshedding
- Excellent responsive design utilities

### TanStack Table v8 — **RECOMMENDED**
```bash
pnpm add @tanstack/react-table
```
- Headless table logic (no UI lock-in) + shadcn/ui table for styling
- Sorting, filtering, pagination, column visibility all built-in
- Perfect for member directory, race results, invoice tables

---

## Calendar

### FullCalendar — **RECOMMENDED**
```bash
pnpm add @fullcalendar/react @fullcalendar/daygrid @fullcalendar/timegrid \
         @fullcalendar/list @fullcalendar/interaction
```
- Most complete open-source calendar library
- React component, TypeScript types included
- Drag-and-drop event rescheduling
- Month/week/day/list views
- iCal export support
- Docs: https://fullcalendar.io

### Alternative: react-big-calendar
- Simpler, lighter weight
- Less features than FullCalendar

---

## Forms & Validation

### React Hook Form — **RECOMMENDED**
```bash
pnpm add react-hook-form zod @hookform/resolvers
```
- Best performance (uncontrolled inputs, minimal re-renders)
- Integrates perfectly with Zod for type-safe validation
- Works natively with shadcn/ui form components

### Zod — **RECOMMENDED**
- TypeScript-first schema validation
- Shared schemas between frontend and backend API
- Validates and transforms API request bodies, form inputs

---

## Payments

### Stripe — **RECOMMENDED**
```bash
pnpm add stripe @stripe/stripe-js
```
- Industry standard, PCI compliant
- Stripe Checkout hosted page (no PCI burden on club)
- Webhook support for async payment confirmation
- Subscription billing for membership renewals
- UK pricing: 1.4% + 20p per transaction (EU cards), 2.9% + 30p (international)
- Stripe Dashboard = easy financial oversight for treasurer
- Free to set up, no monthly fee
- Docs: https://stripe.com/docs

---

## Email

### Resend — **RECOMMENDED**
```bash
pnpm add resend
```
- Developer-friendly email API
- Free tier: 3,000 emails/month (plenty for a yacht club)
- React Email for templates: `pnpm add @react-email/components react-email`
- Excellent deliverability
- Docs: https://resend.com

### React Email — templates
```bash
pnpm add @react-email/components react-email
```
- Write email templates as React components
- Preview in browser during development
- Renders to HTML + plain text automatically

---

## Background Jobs & Scheduling

### Inngest — **RECOMMENDED**
```bash
pnpm add inngest
```
- Serverless background jobs — runs in Vercel/Next.js
- Cron scheduling (for renewal reminders, weekly digest)
- Retry logic, error handling built-in
- Free tier: 50,000 runs/month
- Replaces the GitHub Actions cron from `myc-weekly-message`
- Docs: https://www.inngest.com

### Alternative: Vercel Cron Jobs
- Built into Vercel — simpler for basic cron
- Less retry logic than Inngest

---

## Race Results & Scoring

No existing library does RRS scoring well in JavaScript — build this in-house:

### Key algorithms to implement
1. **PY handicap correction:** `corrected = elapsed × (1000 / PY)`
2. **IRC handicap correction:** `corrected = elapsed × TCC`
3. **Position assignment:** sort by corrected time
4. **RRS Appendix A Low Points scoring:** position = points, DNS/OCS = entries+1, DNF/RET = entries+1, DSQ = entries+2
5. **Series scoring with discards:** drop worst N races, sum remainder

### PY Number Data Source
- RYA publishes annual PY tables at https://www.rya.org.uk/racing/technical/handicapping
- Seed the DB with the latest table (CSV available from RYA)
- Admin tool to update PY numbers each year

---

## Storage Yard Visualisation

### Option A: SVG diagram
- Commission/create an SVG map of the yard
- Colour-code spots by status (occupied/available)
- Click spot → modal with boat/owner details
- No library needed — pure SVG + React event handlers

### Option B: Leaflet.js with aerial photo overlay
```bash
pnpm add leaflet react-leaflet
pnpm add -D @types/leaflet
```
- Georeferenced aerial photo as map background
- GeoJSON polygons for each storage spot
- Interactive: click spot, hover tooltip
- Better for clubs with complex multi-area storage

---

## File Uploads

### uploadthing — **RECOMMENDED**
```bash
pnpm add uploadthing @uploadthing/react
```
- Handles S3-compatible file uploads from Next.js
- TypeScript end-to-end
- Free tier: 2GB storage, 10GB bandwidth/month
- Use for: boat photos, race notices, event attachments
- Docs: https://uploadthing.com

---

## PDF Generation

### @react-pdf/renderer — **RECOMMENDED**
```bash
pnpm add @react-pdf/renderer
```
- Generate PDFs from React components
- Use for: invoices, duty rosters, race results, qualification certificates
- Renders server-side in Next.js API routes

---

## Search

### Fuse.js — **RECOMMENDED** (client-side fuzzy search)
```bash
pnpm add fuse.js
```
- Lightweight, no server needed for member directory search
- Fuzzy matching: "smth" matches "Smith"

### Postgres Full-Text Search (server-side)
- For larger datasets, use Postgres FTS via Prisma raw queries
- No additional library needed

---

## Analytics

### Umami (self-hosted) or Plausible — **RECOMMENDED**
- GDPR compliant, privacy-preserving
- No cookie consent banner needed
- Umami: free self-hosted (one more service to run)
- Plausible: $9/mo hosted (simpler)

**Avoid Google Analytics** — requires cookie consent, data goes to Google.

---

## Development Tooling

| Tool | Purpose | Command |
|---|---|---|
| Turborepo | Monorepo task runner | `npx create-turbo@latest` |
| pnpm | Fast package manager | `npm install -g pnpm` |
| Prisma Studio | Visual DB browser | `npx prisma studio` |
| Prettier | Code formatting | `pnpm add -D prettier` |
| ESLint | Linting | Built into Next.js |
| Husky + lint-staged | Pre-commit hooks | `pnpm add -D husky lint-staged` |
| Docker Compose | Local PostgreSQL | See template below |

### docker-compose.yml (local dev)
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: myc_club
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  pgadmin:
    image: dpage/pgadmin4
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@myc.local
      PGADMIN_DEFAULT_PASSWORD: admin
    ports:
      - "5050:80"

volumes:
  postgres_data:
```

---

## Hosting & Infrastructure (Full Stack)

| Layer | Service | Cost/mo | Notes |
|---|---|---|---|
| Frontend | Vercel | Free | Auto-deploy from GitHub |
| Database | Supabase | Free → $25 | 500MB free, then $25 |
| Background jobs | Inngest | Free | 50k runs/month free |
| File storage | uploadthing | Free | 2GB free |
| Email | Resend | Free | 3k emails/month free |
| Payments | Stripe | 0 + % | 1.4% + 20p per transaction |
| **Total (small club)** | | **~£0–£25/mo** | Scales with usage |

**Self-hosted alternative (full control, lower long-term cost):**
- Hetzner CX21 VPS: €4.51/mo (~£4)
- Docker Compose: PostgreSQL + Next.js + Caddy (reverse proxy)
- Backblaze B2: object storage at $0.006/GB
- Estimated total: ~£10–15/mo

---

## Summary: Full Library List

```bash
# Core
pnpm add next@latest react react-dom typescript
pnpm add prisma @prisma/client

# Auth
pnpm add next-auth@beta

# UI
pnpm add tailwindcss @shadcn/ui
pnpm add @tanstack/react-table
pnpm add react-hook-form zod @hookform/resolvers

# Calendar
pnpm add @fullcalendar/react @fullcalendar/daygrid @fullcalendar/timegrid \
         @fullcalendar/list @fullcalendar/interaction

# Payments & email
pnpm add stripe @stripe/stripe-js
pnpm add resend @react-email/components react-email

# Background jobs
pnpm add inngest

# Files & PDF
pnpm add uploadthing @uploadthing/react
pnpm add @react-pdf/renderer

# Rich text (newsletters)
pnpm add @tiptap/react @tiptap/pm @tiptap/starter-kit

# Utilities
pnpm add date-fns fuse.js ical-generator

# Dev
pnpm add -D @types/node @types/react prettier husky lint-staged
```
