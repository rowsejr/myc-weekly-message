# Stage 2 — Core Modules: Boats, Calendar & Duties

> **Goal:** Add the boat/storage register and a proper structured calendar with duty management — the two SCM modules used most daily by MYC committee.

> **Prerequisite:** Stage 1 (MVP) is complete and live.

---

## Scope

- [ ] Boat register (owner, class, sail number, storage allocation)
- [ ] Storage / cradle / swinging mooring management
- [ ] Full interactive calendar (week/month views)
- [ ] Duty roster with member assignment and notifications
- [ ] Committee announcements / notice board
- [ ] Member self-service: sign up for duties, view own boat record

---

## 1. Boat Register

### Data model additions

```prisma
model Boat {
  id            String    @id @default(cuid())
  name          String
  sailNumber    String?
  boatClass     String
  designerClass String?   // e.g. "Laser", "RS200", "Wayfarer"
  hullColour    String?
  lengthMetres  Float?
  weightKg      Float?
  pyNumber      Int?      // Portsmouth Yardstick handicap
  ircRating     Float?    // IRC certificate value
  
  // Ownership
  ownerId       String
  owner         Member    @relation(fields: [ownerId], references: [id])
  
  // Storage
  storageSpot   StorageSpot? @relation(fields: [storageSpotId], references: [id])
  storageSpotId String?
  
  status        BoatStatus @default(ACTIVE)
  notes         String?
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt
  
  raceEntries   RaceEntry[]
}

enum BoatStatus {
  ACTIVE
  LAID_UP
  SOLD
  REMOVED
}

model StorageSpot {
  id          String    @id @default(cuid())
  identifier  String    @unique  // e.g. "A12", "Swinging-3", "Dinghy-Park-Row-2"
  spotType    StorageType
  location    String?           // e.g. "Dinghy Park North", "Swinging Moorings"
  isAvailable Boolean   @default(true)
  notes       String?
  boat        Boat?
  
  // Billing (for Stage 4)
  annualFee   Float?
}

enum StorageType {
  DINGHY_PARK
  SWINGING_MOORING
  PONTOON_BERTH
  HARD_STANDING
  CRADLE
}
```

### Admin UI screens
- `/admin/boats` — full boat register, filter by class/status/owner
- `/admin/boats/new` — add boat, link to member owner
- `/admin/boats/[id]` — edit boat, assign storage spot
- `/admin/storage` — grid/map view of storage spots, show occupancy
- `/admin/storage/[id]` — spot detail, history, fee notes

### Member screens
- `/boats` — member's own boat(s), storage spot shown
- `/boats/[id]` — boat detail (read-only for member, edit request button)

### Boat class library
- Seed database with common club classes and their PY numbers from RYA table
- Allow custom/unrated classes

---

## 2. Full Interactive Calendar

Replace the simple events list with a proper calendar:

### Features
- Month, week, and list views
- Event types colour-coded (Race = blue, Training = green, Social = orange, Duty = red)
- Click event → event detail sidebar/modal
- Admin can drag-and-drop to reschedule events
- iCal export (`/calendar.ics`) so members can subscribe in Google Calendar / Apple Calendar
- Public calendar view (no login needed)

### Library recommendation
- **FullCalendar** (open-source, excellent React integration)
  - `@fullcalendar/react` + `@fullcalendar/daygrid` + `@fullcalendar/timegrid`
  - Free for self-hosted use
  - iCal export via `@fullcalendar/icalendar`

```bash
pnpm add @fullcalendar/react @fullcalendar/daygrid @fullcalendar/timegrid \
         @fullcalendar/interaction @fullcalendar/icalendar
```

### iCal endpoint
```typescript
// app/api/calendar.ics/route.ts
// Returns RFC 5545-compliant iCal feed
// Susbcribable URL for Google/Apple/Outlook
```

---

## 3. Duty Roster

This is one of SCM's most-used features. Replace with a proper duty management system.

### Data model additions

```prisma
model DutyRole {
  id          String    @id @default(cuid())
  name        String    @unique  // "Race Officer", "Safety Boat Helm" etc.
  description String?
  isRequired  Boolean   @default(true)
  sortOrder   Int       @default(0)
  duties      EventDuty[]
}

model EventDuty {
  id          String    @id @default(cuid())
  event       Event     @relation(fields: [eventId], references: [id])
  eventId     String
  role        DutyRole  @relation(fields: [roleId], references: [id])
  roleId      String
  
  assignedTo  Member?   @relation(fields: [memberId], references: [id])
  memberId    String?
  
  confirmedAt DateTime?
  notes       String?
  
  @@unique([eventId, roleId])
}
```

### Admin UI
- `/admin/duties` — roster table view (events as rows, roles as columns)
  - Click a cell to assign/reassign a member
  - Bulk-assign duties for an entire season
  - Print-friendly duty list
- Duty swap requests: member requests a swap, admin approves

### Member notifications
- Email sent to member when assigned a duty
- Reminder email 48 hours before the event
- Member can mark duty as "confirmed"

### Duty sign-up (volunteer model)
- `/duties/available` — list of unfilled duty slots
- Members can volunteer for unassigned duties
- Admin gets notified and confirms

---

## 4. Committee Notice Board

Simple internal communications:
- `/noticeboard` — list of posts (pinned, recent)
- Admin can post notices, attach PDFs
- Members see on login dashboard
- No login required to view (or restrict to members — configurable)

---

## 5. Acceptance Criteria for Stage 2 Complete

- [ ] All club boats imported from SCM CSV export
- [ ] Storage spots entered and boats allocated
- [ ] Full calendar showing race programme for current season
- [ ] Duty roster populated for at least 4 weeks ahead
- [ ] Members receive email when assigned a duty
- [ ] iCal feed works in Google Calendar
- [ ] Mobile calendar usable on phone

---

## Suggested Additional Libraries for Stage 2

| Purpose | Library | Why |
|---|---|---|
| Calendar | FullCalendar | Best open-source calendar, React native |
| File uploads | uploadthing | Easy S3-compatible uploads (boat photos, docs) |
| iCal generation | ical-generator | Node.js iCal RFC5545 generation |
| PDF generation | @react-pdf/renderer | For duty rosters, member letters |
| Notifications | Resend (already in Stage 1) | Duty assignment emails |
| Map/diagram | Leaflet.js | Storage yard map (SVG overlay on aerial photo) |

---

## Next Stage

Once Stage 2 is live → [Stage 3: Racing & Training](./03-advanced-features.md)
