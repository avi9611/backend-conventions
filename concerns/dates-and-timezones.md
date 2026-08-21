# Dates & Timezones

> Read this before you add any date or timestamp column, and before you write "today" anywhere.
>
> **Status in this project:** decide in Part 1 of the checklist
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

There are **two kinds of time** in a business system, and mixing them up produces bugs that are
silent, intermittent, and only show up at month end.

| The question you are answering | What it is | Column type |
|---|---|---|
| *"When did this happen?"* | an **instant** | timestamp with timezone, stored in UTC |
| *"What day do we book this on?"* | a **business date** | a plain date |

An instant is a point on the world's timeline. A business date is a square on the paper calendar
hanging on somebody's wall. Converting between them needs to know *which* calendar, and that is
the entire reason this file exists.

---

## 2. The rules

- **A column ending in `_at` is an instant.** Stamp it in UTC. Always. Never local.
- **A column ending in `_date`, that a human reads off a document, is a business date.** Take it
  from the right calendar, never from UTC.
- **Whose calendar?** Decide once, in §4. Never the viewer's device.
- **Never write `utc_now().date()`.** It is wrong for several hours of every day, and it fails
  silently.
- **Never compare a date column against a UTC date.** Expiry, overdue and ageing checks are all
  off by a day during those hours.
- **The instant is stored in UTC and rendered in whatever zone the viewer wants.** Rendering is a
  display concern and must never influence a stored business date.
- **Convert in SQL for reports and grouping**, joined to the right zone, never hardcoded.

---

## 3. The traps

### 3a. `utc_now().date()`, and why it is wrong

Take a business four hours ahead of UTC. At 01:00 on 15 July locally, the UTC clock reads 21:00
on 14 July.

```
2026-07-15 01:00 +04:00   <- what the user sees on the wall
2026-07-14 21:00 +00:00   <- the exact same instant, in UTC
```

So `utc_now().date()` returns **14 July** while the user is plainly looking at a calendar saying
the 15th. Every document created between midnight and 04:00 local books to the previous day.

Nobody notices for months. Then it surfaces as a month-end close that is off by one order, and
you spend a day hunting it.

### 3b. Storing a time alongside the date does not fix it

This is the tempting wrong turn, so it is worth being explicit.

The instant was never the problem. Reading the instant in the *wrong calendar* was.
`2026-07-14T21:00Z` is a perfectly precise timestamp, and taking its date still gives you the
wrong day. Precision is not the issue. The calendar is.

Two more reasons a "capture the time too" column is the wrong shape:

- `created_at` already records the exact instant on every one of those tables. The audit trail is
  not missing anything.
- A business date genuinely has no time. Nobody books an order to "14 July at 15:32". Adding a
  time invents precision the business does not have and does not want.

### 3c. Which zone, when there is more than one

If your tenants sit in different countries, "the company timezone" stops being an answer. A Dubai
order books on Dubai's day. A London order books on London's day.

**The fix.** Each tenant carries an IANA zone. The request context resolves it, so any service
stamping a business date just passes `ctx.timezone`.

**A bare call with no zone falls back to a default, and that is correct only where there is
genuinely no tenant in hand.** Background jobs and schema validators. Anywhere a context is
available, passing it is not optional.

**And watch the job that loops over tenants.** It *does* have a zone in hand, per iteration.
Tenants in distant zones resolve different days in the same run. Take "yesterday" inside the
loop, from that tenant's zone, not once at the top.

### 3d. Wall-clock comparisons

**Symptom.** A punctual employee is marked late. A shift boundary lands on the wrong side.

**Why.** Comparing a stored UTC instant against a local clock time needs a conversion, and
somebody hardcoded a zone. Phoenix had one module hardcoded to the wrong country, inherited from
a port of an earlier system, and it produced real pay deductions.

**The fix.** Convert through the tenant's zone. And put the check in §7, because a hardcoded zone
is easy to grep for and impossible to spot in review.

### 3e. The client has the same trap

`new Date().toISOString().slice(0, 10)` gives you the **UTC** day. For a user ahead of UTC that
is still yesterday, early in the morning.

**The fix.** One helper for "today" on the client, reading the viewer's local calendar, and never
the raw ISO slice.

### 3f. The cached timezone in tests

The resolved zone object is usually cached for speed. A test that changes the configured zone has
to clear that cache, or the old zone sticks and the test passes for the wrong reason.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Whose calendar decides a business date | one company zone, per tenant, or per user | | |
| Where the zone is stored | a setting, or a column on the tenant | | |
| Are timestamps timezone-aware in the database? | yes | | |
| Can a user pick a display zone? | yes, or always the tenant's | | |
| Business dates on create | server-filled and user-correctable, or user-supplied | | |
| Are future business dates allowed? | no for "when did this happen", yes for "when is this due" | | |

Row 1: "one company zone" is fine until it is not, and moving off it later touches every stamp.
If a second country is even plausible, put the zone on the tenant now. The code is identical, you
just pass a value instead of reading a constant.

Row 5, and it is a real product decision rather than a shortcut. **Server-filled but correctable
gives users both halves.** They never have to type a date, and they can fix it.

**Backdating is routine, not an edge case.** The supplier invoice is dated the 10th and gets keyed
in on the 14th. It must book to the 10th, or the accounting period and the reconciliation are both
wrong. Importing history is the same story. Every imported row would otherwise stamp today.

So do not "simplify" it into a server-only, uneditable field. That deletes a fact the business
depends on. Constrain it instead: no future dates, and the date locks once the document leaves
its editable state.

---

## 5. Inventory

### Business dates

| Field | Module | Server-filled? |
|---|---|---|
| | | |

### Places that compare against "today"

| Where | What it decides |
|---|---|
| | |

### Where UTC is deliberately used

| Case | Why |
|---|---|
| Every `_at` column | it is an instant. This is correct and permanent |
| | |

### Known gaps

---

## 6. New-column checklist

1. **Ask what the column means, not what type it happens to be.** "When did this happen" or "what
   day do we book this on".
2. An instant: timezone-aware column, stamped in UTC, no default in the model beyond the shared
   mixin.
3. A business date: a plain date, not nullable, **no default in the model**. The service stamps
   it, because the service is the only layer that knows the request context.
4. The schema accepts it as **optional**, so the client never has to send it, and rejects future
   dates where that applies.
5. In the service, fill the gap and **reuse the same "today" for the document number's year**, so
   the two can never disagree at a year boundary.
6. If a data-access helper needs the year, give it a zone parameter and pass it from the service.
   The data-access layer has no request context.

---

## 7. How to re-check this doc

```bash
# The UTC-date bug. Expect zero.
grep -rn --include="*.py" "utc_now().date()\|datetime.utcnow()\|date.today()" app/ | grep -v "test_"
```

```bash
# Hardcoded timezones outside the settings file. Expect zero.
grep -rn --include="*.py" "Asia/\|Europe/\|America/" app/ | grep -v "settings.py\|test_\|\.md"
```

```bash
# A bare "today" call in a service that has a tenant context available.
# Read every hit: correct only in jobs and validators.
grep -rn --include="*.py" "business_today()" app/ | grep -v "test_\|tasks.py\|schemas.py"
```

```bash
# Client: the UTC-day slice. Expect zero.
grep -rn "toISOString().slice(0, 10)\|toISOString().split" src/
```
