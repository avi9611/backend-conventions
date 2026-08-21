# Document Numbering

> Read this before you add any code a person refers to out loud. An order number, a certificate
> number, an invoice number, an asset code.
>
> **Status in this project:** decide before the first numbered record
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

Every document a human names has to have a number that is **unique, gap-free, and scoped the way
the business expects**.

Gap-free matters more than it sounds. For an audited business a missing number in a sequence is a
question somebody has to answer, not a cosmetic flaw. "Where is invoice 0042?" is a real
conversation with an auditor.

The whole mechanism is one table, one counter row per series, and one function. Do not let it
become anything more.

---

## 2. The rules

- **Numbers come from one allocator.** Never build one by hand. Never use max plus one.
- **It runs inside the caller's transaction.** If the caller rolls back, the increment rolls
  back. That is what keeps the sequence gap-free. Do not commit around it.
- **The year comes from the tenant's calendar**, never from UTC. A document raised at 02:00 local
  on 1 January would otherwise be numbered into the previous year.
  → [`dates-and-timezones.md`](dates-and-timezones.md)
- **Honour a manual override if the module allows one.** Check uniqueness first, then fall back
  to allocating.
- **Store the number on the row.** Never recompute it for display.
- **Never join on a document number.** Internal references use the primary key. A document number
  is for humans.

---

## 3. The traps

### 3a. Select-for-update locks nothing when the row does not exist

The most important paragraph in this file.

**Symptom.** The first document of each type each year fails for almost everybody. Also the first
document in a newly created tenant. Measured at one of twelve concurrent callers succeeding.

**Why.** The obvious implementation reads the counter row with a lock, and inserts it if missing.
`SELECT ... FOR UPDATE` **takes no lock on a row that is not there**. So every caller misses, every
caller inserts, one wins and the rest die on the unique constraint. It surfaces as a generic
conflict error.

**The fix.** One statement:

```sql
INSERT INTO sequences (key, last_value) VALUES (:key, 1)
ON CONFLICT (key) DO UPDATE SET last_value = sequences.last_value + 1
RETURNING last_value
```

It takes the row lock itself *and* covers the cold case. Guard it with a test that starts from an
empty table and runs many callers at once.

**Do not "simplify" it back to a lock.** Put the reason in a comment at the call site.

### 3b. A database sequence is not the same thing

**Symptom.** Numbers have gaps after failed requests.

**Why.** A native database sequence does not roll back. That is the point of it, because it means
it never blocks. It is the right tool for surrogate keys and the wrong tool for a gap-free
document number.

**The fix.** If gap-free matters, you need a counter row in a real transaction, and you accept
that concurrent allocations serialise on that row. If gap-free does not matter, say so, use the
native sequence, and write down that gaps are expected so nobody hunts them.

### 3c. Not every counter fits the same shape

**Symptom.** Somebody invents a fake tenant and a fake year so a company-wide counter can live in
the per-tenant table.

**Why.** The first counter you build has a shape, and the second one has different dimensions.

**The fix.** A second table, and a small enum of counter names so a typo starts nothing. A
mistyped free-text name would silently start a *second* counter, and the failure only shows up as
duplicate numbers on paper.

### 3d. Continuing a series that already exists on paper

**Symptom.** Go-live day. The new system starts at 1 and the paper register is at 9,236.

**The fix.** An administrator sets the opening value once, through a permissioned endpoint.
Three details that matter:

- **It moves forward only.** Refuse a lower value.
- **Refuse it in the SQL where clause**, not in the calling code, so a caller who forgets to check
  cannot re-issue numbers that already exist on paper.
- **Store the last used value**, and have the allocator return that plus one. Getting this off by
  one is very easy and very visible.

Do not backfill existing rows with invented numbers. Nulls do not collide in a unique constraint.

### 3e. A second numbering scheme, on purpose

Not every number is `TYPE-TENANT-YEAR-NNNN`. Some are composed from things that already exist:
a job number, a line number, a revision suffix. That kind consumes nothing, so a failed operation
leaves the series exactly as it found it, and there is no counter to roll back.

If you build one, state these three properties in the doc, because none of them is how the main
allocator behaves:

- Nothing is consumed.
- A number is never reused, and the allocator enforces that by reading every number already taken
  on the same stem, including cancelled and deleted ones.
- A revision inherits its original's stem rather than recomputing it. A correction issued in
  April to a March document keeps the March stem, or the chain is not legible on paper.

**And watch what it depends on.** If a composed number has no tenant segment, that is safe only
because one of its components is globally unique. If somebody later proposes scoping that
component per tenant, the number needs a tenant segment in the same change.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Is gap-free required? | **answer this first** | | |
| Format | | | |
| Scope of the counter | per tenant, global, or both | | |
| Reset | yearly, monthly, never | | |
| Which calendar decides the year | the tenant's | | |
| Manual override allowed? | per document type | | |
| Opening value for go-live | settable once, forward only | | |
| Padding width | | | |

Row 1 decides everything else. If gap-free is not required, this whole file collapses to "use a
database sequence".

Row 8: four digits runs out at 10,000. Decide what happens then, now, rather than in the year it
happens.

---

## 5. Inventory

### Document types and their formats

| Type | Prefix | Format | Scope | Resets |
|---|---|---|---|---|
| | | | | |

### Reserved but not in use

| Type | Waiting on |
|---|---|
| | |

### Where numbering is deliberately not used

| Case | Why |
|---|---|
| Internal ids | random primary keys. Document numbers are for humans, never for joins |
| | |

### Known gaps

---

## 6. New-numbered-document checklist

1. Add the type. Its value is the visible prefix, so keep it short and unambiguous.
2. In the service, never the data-access layer, inside the one transaction: take today from the
   tenant's calendar, then allocate the number with that year.
3. **Reuse one "today" for both the number's year and the record's date**, so at a year boundary
   they cannot disagree.
4. If the module allows a manual override, check uniqueness first and only allocate in the else
   branch.
5. Store the number on the row.
6. No migration needed if the counter table is generic.
7. Add the type to §5.

---

## 7. How to re-check this doc

```bash
# The document types. Compare to §5.
grep -n "class DocType" -A 30 app/*/numbering.py
```

```bash
# Call sites. Every one should be in a service, not a data-access file.
grep -rn --include="*.py" "next_number(\|next_sequence_value(" app/ | grep -v "numbering.py\|test_"
```

```bash
# A numbering call taking its year from UTC rather than the tenant calendar.
# Expect zero.
grep -rn --include="*.py" -B4 "next_number(" app/ | grep "utc_now().year\|datetime.now"
```

```bash
# The concurrency mechanism is still an upsert, not a for-update.
grep -n "on_conflict_do_update\|with_for_update" app/*/numbering.py
```
