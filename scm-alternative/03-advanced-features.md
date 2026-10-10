# Stage 3 — Advanced Features: Racing & Training/Ticketing

> **Goal:** Add race result management with handicap calculations, and a training/course booking system with ticketing — the two features that most directly replace SCM's specialist functionality.

> **Prerequisite:** Stage 2 (Core Modules) is complete.

---

## Scope

- [ ] Race series and results management
- [ ] Handicap calculations (PY / IRC)
- [ ] Competitor entry and start lists
- [ ] Training course management
- [ ] Course bookings / ticketing (with payment)
- [ ] Qualification / competency tracking per member
- [ ] Results publication (public-facing)

---

## Part A: Race Management

### 1. Data Model

```prisma
model Series {
  id          String    @id @default(cuid())
  name        String                       // "Summer Series 2025"
  year        Int
  handicapSystem HandicapSystem @default(PY)
  scoringSystem  ScoringSystem  @default(PURSUIT_OR_AVERAGE)
  isPublished  Boolean  @default(false)
  races       Race[]
  createdAt   DateTime  @default(now())
}

enum HandicapSystem {
  PY            // Portsmouth Yardstick (club racing)
  IRC           // IRC certificate
  NHC           // National Handicap for Cruisers
  CLASS         // One-design (no handicap)
}

enum ScoringSystem {
  LOW_POINTS      // RRS Appendix A
  BONUS_POINTS
  AVERAGE_POINTS  // discard/average
}

model Race {
  id          String    @id @default(cuid())
  series      Series    @relation(fields: [seriesId], references: [id])
  seriesId    String
  raceNumber  Int
  date        DateTime
  
  status      RaceStatus @default(SCHEDULED)
  abandonReason String?
  
  entries     RaceEntry[]
  results     RaceResult[]
}

enum RaceStatus {
  SCHEDULED
  COMPLETED
  ABANDONED
  POSTPONED
}

model RaceEntry {
  id          String    @id @default(cuid())
  race        Race      @relation(fields: [raceId], references: [id])
  raceId      String
  boat        Boat      @relation(fields: [boatId], references: [id])
  boatId      String
  helmName    String
  crewName    String?
  
  result      RaceResult?
  @@unique([raceId, boatId])
}

model RaceResult {
  id            String    @id @default(cuid())
  entry         RaceEntry @relation(fields: [entryId], references: [id])
  entryId       String    @unique
  race          Race      @relation(fields: [raceId], references: [id])
  raceId        String
  
  finishTime    DateTime?      // clock time at finish
  elapsedSeconds Int?           // seconds from gun
  correctedSeconds Int?         // after handicap
  position      Int?
  points        Float?
  
  status        ResultStatus @default(FINISHED)
}

enum ResultStatus {
  FINISHED
  DNF       // Did Not Finish
  DNS       // Did Not Start
  OCS       // On Course Side (premature start)
  DSQ       // Disqualified
  RET       // Retired
  DNC       // Did Not Compete
  AVG       // Average points (took average)
}
```

### 2. Handicap Calculation Logic

```typescript
// lib/handicap.ts

// PY calculation: corrected time = elapsed time × (1000 / PY)
function calculatePYCorrected(elapsedSeconds: number, pyNumber: number): number {
  return elapsedSeconds * (1000 / pyNumber)
}

// IRC: corrected time = elapsed time × TCC (Time Correction Coefficient)
function calculateIRCCorrected(elapsedSeconds: number, tcc: number): number {
  return elapsedSeconds * tcc
}

// Assign positions from corrected times
function assignPositions(results: RaceResult[]): RaceResult[] {
  return results
    .filter(r => r.status === 'FINISHED')
    .sort((a, b) => (a.correctedSeconds ?? Infinity) - (b.correctedSeconds ?? Infinity))
    .map((r, i) => ({ ...r, position: i + 1 }))
}
```

### 3. Scoring (RRS Appendix A — Low Point System)

- 1st = 1 point, 2nd = 2 points, etc.
- DNS/OCS = entries + 1
- DNF/RET = entries + 1
- DSQ = entries + 2
- Discard worst N races from series based on series config
- Series leaderboard calculated dynamically

### 4. Admin UI — Race Management

- `/admin/racing/series` — list series, create new series
- `/admin/racing/series/[id]` — series management:
  - Add races, add/edit entries
  - Enter finish times (stopwatch-style entry form)
  - View calculated results and series standings
  - Publish results to public page
- `/admin/racing/series/[id]/race/[raceId]` — race detail:
  - Entry list (boat, helm, crew, handicap)
  - Results entry (finish time or place)
  - Override corrected times
  - Handle abandoned/OCS boats

### 5. Race Officer Finish Recording (Mobile-Friendly)

Simple field-use screen for Race Officer:
- `/race-recording/[raceId]` — minimal UI
- List of entered boats, large "FINISH" button per boat
- Records timestamp on button press
- Syncs to server, RO can use phone/tablet on the water
- Offline-capable (PWA with service worker cache)

### 6. Public Results Pages

- `/results` — list of series
- `/results/[seriesId]` — series leaderboard + individual race results
- Printable view for trophy presentations
- Historical archive back to first entered season

---

## Part B: Training & Ticketing

### 1. Data Model

```prisma
model TrainingCourse {
  id            String    @id @default(cuid())
  title         String                        // "RYA Day Skipper", "Powerboat Level 2"
  description   String?
  courseType    CourseType
  capacity      Int
  
  sessions      CourseSession[]
  bookings      CourseBooking[]
  prerequisites Qualification[]  // required before booking
  awards        Qualification[]  @relation("CourseAwards")
  
  price         Float     @default(0)
  memberPrice   Float?    // discounted for members
  createdAt     DateTime  @default(now())
}

enum CourseType {
  RYA_KEELBOAT
  RYA_DINGHY
  RYA_POWERBOAT
  SAFETY
  RACE_TRAINING
  SOCIAL
  JUNIOR
  OTHER
}

model CourseSession {
  id          String    @id @default(cuid())
  course      TrainingCourse @relation(fields: [courseId], references: [id])
  courseId    String
  startDate   DateTime
  endDate     DateTime
  location    String?
  instructorId String?
  instructor  Member?   @relation(fields: [instructorId], references: [id])
}

model CourseBooking {
  id          String    @id @default(cuid())
  course      TrainingCourse @relation(fields: [courseId], references: [id])
  courseId    String
  member      Member    @relation(fields: [memberId], references: [id])
  memberId    String
  
  status      BookingStatus @default(PENDING)
  paymentStatus PaymentStatus @default(UNPAID)
  stripePaymentIntentId String?
  
  notes       String?
  bookedAt    DateTime  @default(now())
  
  @@unique([courseId, memberId])
}

enum BookingStatus {
  PENDING
  CONFIRMED
  WAITLIST
  CANCELLED
  ATTENDED
  NO_SHOW
}

model Qualification {
  id          String    @id @default(cuid())
  name        String    @unique    // "RYA Day Skipper", "Powerboat L2"
  issuer      String?              // "RYA"
  
  memberQuals MemberQualification[]
}

model MemberQualification {
  id              String    @id @default(cuid())
  member          Member    @relation(fields: [memberId], references: [id])
  memberId        String
  qualification   Qualification @relation(fields: [qualId], references: [id])
  qualId          String
  achievedAt      DateTime
  expiresAt       DateTime?
  certificateRef  String?
  
  @@unique([memberId, qualId])
}
```

### 2. Payment Integration (Stripe)

```typescript
// app/api/bookings/[id]/checkout/route.ts
import Stripe from 'stripe'

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!)

// Create checkout session → redirect member to Stripe hosted page
// On success: webhook updates BookingStatus to CONFIRMED, PaymentStatus to PAID
```

- Use **Stripe Checkout** (hosted page) — no PCI compliance burden
- Webhook handler at `/api/webhooks/stripe`
- Refund flow: admin can issue refund from booking detail page (calls Stripe API)

### 3. Ticketing UI

#### Member screens
- `/training` — browse available courses with dates, price, spaces remaining
- `/training/[courseId]` — course detail, book button
- `/bookings` — member's current and past bookings
- `/bookings/[id]` — booking detail, cancel button (within policy)

#### Admin screens
- `/admin/training` — list all courses with booking counts
- `/admin/training/new` — create course with sessions
- `/admin/training/[id]` — course detail:
  - Booking list (member, status, payment)
  - Waiting list management
  - Mark attendance
  - Issue qualification on completion
- `/admin/qualifications` — searchable member qualification register

### 4. Qualification / Competency Tracking

- Members have a "logbook" of earned qualifications
- Shown on member profile (private to member + admin)
- Useful for: who can be Race Officer, Safety Boat Helm, Instructor
- Filter duty assignments by qualification: "Only show members with Powerboat L2 as Safety Boat"

---

## Acceptance Criteria for Stage 3 Complete

- [ ] Current season race programme entered with all results
- [ ] Series leaderboard calculated correctly (verified against current SCM/manual data)
- [ ] Public results page live
- [ ] At least one training course bookable with Stripe payment
- [ ] Qualification records imported for existing qualified members
- [ ] Race Officer finish recording tested on mobile on the water
- [ ] Booking confirmation emails working

---

## Suggested Additional Libraries for Stage 3

| Purpose | Library | Why |
|---|---|---|
| Payments | Stripe + stripe-js | Industry standard, PCI compliant |
| PWA / offline | next-pwa | Race recording offline support |
| Charts/visualisation | Recharts | Series standings charts |
| QR codes | qrcode | Ticket/booking QR codes for attendance |
| PDF certificates | @react-pdf/renderer | Print qualification certificates |
| Data tables | TanStack Table (already) | Race result tables |

---

## Next Stage

Once Stage 3 is live → [Stage 4: Finance & Communications](./04-full-platform.md)
