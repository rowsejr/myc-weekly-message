# Stage 4 — Full Platform: Finance, Communications & Polish

> **Goal:** Complete the platform with membership renewals/invoicing, internal communications, member self-service, and general polish. At this point SCM can be cancelled.

> **Prerequisite:** Stage 3 (Racing & Training) is complete and in active use.

---

## Scope

- [ ] Membership renewal and subscription billing
- [ ] Invoicing for storage fees, course fees, event fees
- [ ] Basic financial reporting (income by category)
- [ ] Email newsletter / member communications
- [ ] Member self-service portal (full)
- [ ] Public website integration (event listings, results)
- [ ] Admin dashboard with key metrics
- [ ] Data export / backup tooling
- [ ] Performance & security hardening

---

## Part A: Membership & Finance

### 1. Membership Renewal Billing

Use **Stripe Subscriptions** or annual one-off payments:

```typescript
// Membership fee tiers (stored in DB, configurable by admin)
model MembershipFee {
  id          String    @id @default(cuid())
  memberType  MemberType @unique
  annualFee   Float
  effectiveFrom DateTime
}
```

**Renewal flow:**
1. Member receives renewal reminder email 60/30/7 days before lapse
2. Link to `/renew` page — shows current details and fee
3. Stripe Checkout handles payment
4. On success: `renewsAt` extended by 1 year, `status` = ACTIVE
5. Admin can manually record cash/cheque payments (treasurer use)

### 2. Storage Fee Invoicing

```typescript
model Invoice {
  id          String    @id @default(cuid())
  member      Member    @relation(fields: [memberId], references: [id])
  memberId    String
  
  lines       InvoiceLine[]
  
  totalAmount Float
  status      InvoiceStatus @default(DRAFT)
  issuedAt    DateTime?
  dueAt       DateTime?
  paidAt      DateTime?
  
  stripePaymentIntentId String?
  notes       String?
  createdAt   DateTime  @default(now())
}

model InvoiceLine {
  id          String    @id @default(cuid())
  invoice     Invoice   @relation(fields: [invoiceId], references: [id])
  invoiceId   String
  description String
  quantity    Float     @default(1)
  unitPrice   Float
  total       Float
}

enum InvoiceStatus {
  DRAFT
  SENT
  PAID
  OVERDUE
  CANCELLED
}
```

**Bulk invoice generation:**
- Admin runs "Generate Annual Storage Invoices" → creates draft invoices for all active storage spots
- Review and edit drafts, then bulk-send
- Members receive invoice email with payment link (Stripe)
- Treasurer dashboard shows outstanding invoices

### 3. Financial Reporting

Simple reporting (not full accounting — integrate with Xero/QuickBooks for full bookkeeping):
- Income by category (membership, storage, training, events)
- Outstanding invoices list
- Payment history export to CSV
- Annual summary report (for AGM)

Consider **Xero API** integration in a later iteration if the treasurer wants it.

---

## Part B: Communications

### 1. Member Email Newsletters

Build on the existing `myc-weekly-message` concept — but integrated:

```typescript
model Newsletter {
  id          String    @id @default(cuid())
  subject     String
  bodyHtml    String
  bodText     String
  
  status      NewsletterStatus @default(DRAFT)
  sentAt      DateTime?
  recipients  Int?      // count at time of send
  createdAt   DateTime  @default(now())
}
```

- Rich text editor in admin (Tiptap — open-source ProseMirror wrapper)
- Preview before send
- Send to: All members / Active members / Specific member types
- Unsubscribe link included (legal requirement)
- Open/click tracking (optional — Resend provides this)

**Auto-generated weekly digest (replaces `myc-weekly-message`):**
- Cron job builds and sends every Friday afternoon
- Pulls: upcoming events (next 14 days), any new notices, tides (from existing PLA data), weather
- Members opt-in/out from profile settings

### 2. In-App Notifications

- `/notifications` — member notification inbox
- Types: duty assigned, booking confirmed, renewal reminder, notice board post
- Email + in-app for important notifications
- Admin broadcast: send urgent message to all members

### 3. WhatsApp Integration (optional)

For clubs that use WhatsApp groups heavily:
- Webhook to send auto-generated weekly message to WhatsApp via **WhatsApp Business API** (Meta)
- Free tier: 1,000 conversations/month
- Alternative: use existing `myc-weekly-message` GitHub Action alongside the new platform

---

## Part C: Member Self-Service Portal

Full member self-service — reduce admin burden:

### Member dashboard (`/dashboard`)
- Upcoming events they've signed up for
- Their duty assignments (with confirm button)
- Membership status + renewal date + "Renew Now" CTA
- Their boat(s) and storage spot
- Recent notifications
- Quick links: book training, view results, committee notice board

### Profile management
- Edit contact details (syncs back to member record)
- Change email (requires re-verification)
- Upload profile photo
- Privacy settings (show/hide in member directory)
- Notification preferences (email frequency, types)

### Member directory
- `/members` — searchable list (members only)
- Show: name, boat, role in club
- Privacy-respecting: contact details only shown with consent

---

## Part D: Admin Dashboard & Reporting

### Key metrics widget
- Total active members (vs same time last year)
- Boats on site
- Upcoming events (next 7 days)
- Outstanding invoices (£ total)
- Unfilled duty slots
- Open course bookings

### Admin quick actions
- Bulk send renewal reminders
- Generate storage invoices
- Download member CSV
- Download race results PDF

---

## Part E: Public Website Integration

Option A — **Embedded widgets (recommended for clubs with existing websites):**
- Provide embeddable JavaScript snippets for:
  - Events calendar (`<script src="https://your-platform.com/embed/calendar.js">`)
  - Race results
  - Course listings
- MYC keeps their WordPress site, just embeds live data from the platform

Option B — **Replace the website entirely:**
- Next.js site IS the public website
- Marketing pages + member portal in one
- Custom domain: `club.margateyachtclub.co.uk` or similar

---

## Part F: Security & Compliance

### GDPR compliance
- Privacy policy page (generated from template)
- Member data export on request (right to access)
- Member data deletion on request (right to erasure — soft delete with anonymisation)
- Data retention policy (configurable)
- Cookie consent banner

### Security hardening
- Rate limiting on auth endpoints (Upstash Redis rate limiter)
- CSRF protection (built into NextAuth)
- Input sanitisation everywhere (Zod schemas already handle this)
- Dependency audit in CI pipeline (npm audit / Snyk)
- Environment variable scanning (prevent secret leaks)
- HTTPS enforced (Vercel does this automatically)
- Regular backups: pg_dump cron → encrypted S3 bucket

### Audit log
```typescript
model AuditLog {
  id          String    @id @default(cuid())
  actor       Member?   @relation(fields: [actorId], references: [id])
  actorId     String?
  action      String    // "member.updated", "invoice.created" etc.
  targetType  String?   // "Member", "Boat" etc.
  targetId    String?
  metadata    Json?
  createdAt   DateTime  @default(now())
}
```

---

## Part G: Migration Checklist (SCM → New Platform)

- [ ] Export all member records from SCM (CSV)
- [ ] Export all boat records from SCM (CSV)
- [ ] Export race results history (manual if no export available)
- [ ] Run migration scripts (Stage 1 import tooling)
- [ ] Verify member count matches
- [ ] Verify boat/storage allocation matches
- [ ] Run parallel for 1 season (both systems)
- [ ] Committee sign-off on all modules
- [ ] Cancel SCM subscription (save £3,000/yr 🎉)

---

## Acceptance Criteria for Stage 4 Complete

- [ ] Membership renewal via Stripe working and tested
- [ ] Storage invoices generated and sent successfully
- [ ] Weekly digest email replacing `myc-weekly-message` GitHub Action
- [ ] Member self-service portal in active use (>50% of members logged in)
- [ ] Admin dashboard in daily use by committee
- [ ] GDPR compliance reviewed
- [ ] 3 months without needing SCM
- [ ] SCM subscription cancelled

---

## Suggested Additional Libraries for Stage 4

| Purpose | Library | Why |
|---|---|---|
| Rich text editor | Tiptap | Newsletter/notice editor, extensible |
| Stripe subscriptions | Stripe (already) | Recurring membership billing |
| Rate limiting | @upstash/ratelimit | Redis-based, serverless-compatible |
| Background jobs | Inngest | Cron jobs, renewal reminders, digests |
| Analytics (self-hosted) | Plausible or Umami | Privacy-respecting, GDPR safe |
| Charts | Recharts (already) | Financial dashboard charts |
| PDF invoices | @react-pdf/renderer (already) | Invoice generation |
| Search | Fuse.js | Client-side fuzzy search for member directory |

---

## Post-Launch Considerations

1. **RYA integration** — RYA clubs can submit results online; consider API integration for race results submission
2. **Handicap updates** — RYA updates PY numbers annually; build an admin tool to bulk-update
3. **Mobile app** — Progressive Web App (PWA) first, native app only if demand warrants
4. **Multi-club** — if other clubs want to use the platform, extract into SaaS (the £3k/yr problem affects hundreds of clubs)
