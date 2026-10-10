# Stage 1 — MVP: Auth + Members + Basic Events

> **Goal:** Get a working, deployed application that can replace SCM's most basic function — knowing who your members are and what events are coming up. This is the foundation everything else builds on.

---

## Scope

- [ ] Project scaffolding and repository setup
- [ ] Authentication (member login + admin role)
- [ ] Member directory (CRUD)
- [ ] Basic membership status (active/lapsed/pending)
- [ ] Simple event calendar (create/edit/view)
- [ ] Public-facing events page (replaces the scraped MYC WordPress events)
- [ ] Deployment pipeline (CI/CD to staging)

**Out of scope for MVP:** Payments, boat records, race results, ticketing.

---

## 1. Project Setup

### Repository structure
```
myc-club-platform/
├── apps/
│   ├── web/          ← Next.js frontend
│   └── api/          ← FastAPI backend (or use Next.js API routes)
├── packages/
│   └── db/           ← Prisma schema / migrations
├── docker-compose.yml
└── README.md
```

### Tooling choices
- **Monorepo:** Turborepo (simple, Next.js native)
- **Package manager:** pnpm
- **DB schema:** Prisma ORM (TypeScript types, migrations, seeding)
- **Linting/formatting:** ESLint + Prettier

### Bootstrap commands
```bash
npx create-turbo@latest myc-club-platform
cd myc-club-platform
pnpm add -D prisma
npx prisma init
```

---

## 2. Database Schema (MVP)

```prisma
model Member {
  id            String    @id @default(cuid())
  email         String    @unique
  firstName     String
  lastName      String
  phone         String?
  address       String?
  memberNumber  String?   @unique
  memberType    MemberType @default(FULL)
  status        MemberStatus @default(ACTIVE)
  joinedAt      DateTime  @default(now())
  renewsAt      DateTime?
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
  
  // Auth
  accounts      Account[]
  sessions      Session[]
  
  // Relations (for later stages)
  boats         Boat[]
  eventSignups  EventSignup[]
}

enum MemberType {
  FULL
  JUNIOR
  FAMILY
  SOCIAL
  HONORARY
  STUDENT
}

enum MemberStatus {
  ACTIVE
  LAPSED
  PENDING
  SUSPENDED
}

model Event {
  id          String    @id @default(cuid())
  title       String
  description String?
  startDate   DateTime
  endDate     DateTime?
  location    String?
  eventType   EventType @default(SOCIAL)
  isPublic    Boolean   @default(true)
  createdAt   DateTime  @default(now())
  
  duties      EventDuty[]
  signups     EventSignup[]
}

enum EventType {
  RACE
  TRAINING
  SOCIAL
  DUTY
  MEETING
  OTHER
}
```

---

## 3. Authentication

Use **NextAuth.js v5** (Auth.js) with:
- **Magic link email** (passwordless — best for older members, no passwords to forget)
- **Admin role** stored on the Member record
- Session-based auth (JWT stored in httpOnly cookie)

```typescript
// pages/api/auth/[...nextauth].ts
providers: [
  EmailProvider({
    server: process.env.EMAIL_SERVER,
    from: 'noreply@margateyachtclub.co.uk'
  })
]
```

**Role model:**
- `MEMBER` — can view own profile, see events, sign up
- `COMMITTEE` — can manage events, view all members
- `ADMIN` — full access, can manage members and roles

---

## 4. Member Management UI

### Admin screens
- `/admin/members` — searchable/filterable table of all members
  - Filter by: status, member type, renewal due
  - Export to CSV (for backups / treasurer use)
- `/admin/members/new` — add a member manually
- `/admin/members/[id]` — edit member, set status, send magic link invite

### Member self-service screens
- `/profile` — view/edit own contact details
- `/profile/membership` — view membership status and renewal date

### Import from SCM
- Admin upload of CSV export from SCM
- Migration script maps SCM field names → Prisma schema
- Handles duplicates by email match

---

## 5. Events Calendar (Basic)

### Admin screens
- `/admin/events` — list upcoming events with quick edit
- `/admin/events/new` — create event with title, dates, type, description
- `/admin/events/[id]/duties` — assign duty roles (Race Officer, Safety Boat etc.)

### Member/public screens
- `/events` — paginated list of upcoming events (replaces scraped WordPress events)
- `/events/[id]` — event detail page with duties shown

### Duty roles (hardcoded for MVP, configurable in Stage 2)
- Race Officer
- Safety Boat Helm
- Safety Boat Crew
- Instructor
- Starter

---

## 6. Deployment

### Development
```bash
docker-compose up   # PostgreSQL + pgAdmin locally
pnpm dev            # Next.js dev server
```

### Production (free/cheap tier)
| Service | Provider | Cost |
|---|---|---|
| Frontend | Vercel | Free |
| Database | Supabase | Free (500MB) |
| Email | Resend.com | Free (3,000/mo) |
| **Total** | | **£0/month** |

Scale up when needed:
- Supabase Pro: $25/mo (8GB, daily backups)
- OR self-host on Hetzner CX21: ~£5/mo

---

## 7. Acceptance Criteria for Stage 1 Complete

- [ ] A member can receive a magic link and log in
- [ ] An admin can create, edit and deactivate a member
- [ ] CSV import from SCM works for test data
- [ ] An admin can create an event with duties
- [ ] The public events page lists upcoming events
- [ ] The app is deployed and accessible at a real URL
- [ ] Basic mobile-responsive layout works on phone
- [ ] At least one admin account exists for MYC committee

---

## Suggested Libraries for Stage 1

| Purpose | Library | Why |
|---|---|---|
| Full-stack framework | Next.js 14 (App Router) | Routing, SSR, API routes in one |
| Auth | Auth.js (NextAuth v5) | Magic links, roles, sessions |
| ORM | Prisma | Type-safe DB access, migrations |
| UI components | shadcn/ui | Copy-paste Tailwind components, accessible |
| Tables | TanStack Table | Sortable/filterable member tables |
| Forms | React Hook Form + Zod | Validation, type-safe schemas |
| Date handling | date-fns | Lightweight, tree-shakeable |
| Email | Resend SDK | Simple API, generous free tier |

---

## Next Stage

Once Stage 1 is live and tested with real MYC data → proceed to [Stage 2: Core Modules](./02-core-modules.md)
