# Snapshots vs Live Reads

> Read this before you add a document, or point at master data from a record that gets issued.
>
> **Status in this project:** decide before the first issued document
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

An issued document has to keep saying what it said when it was issued. Editing the supplier
record must not rewrite last year's purchase order.

That sounds obvious and it is violated constantly, because the *natural* way to write the code is
the wrong one. Store the supplier id, join at render time. It is one line shorter and it is
wrong.

The reverse error is just as real. Freeze something that should stay current and a reprint shows
an office address you moved out of two years ago.

**Every reference from a document to master data is a decision. There is no safe default.** This
document records which way each one went, and why.

---

## 2. The rules

- **Never resolve a counterparty by id at print time.** Identity is copied onto the row when the
  document is issued.
- **Decide explicitly, per field, per document.** Frozen or live. "I did not think about it"
  ships as a bug in one direction or the other.
- **Anything read live must be part of the document's cache key**, or the change can never reach
  a reprint. That is not a separate rule, it is this rule's other half.
  → [`caching.md`](caching.md)
- **Money is always frozen with its currency.**
  → [`money-and-quantities.md`](money-and-quantities.md)
- **A rename of a lookup value cascades to the rows holding it, except where a cascade would walk
  past a freeze.** §3c.
- **Do not snapshot onto a document what the document does not state.** A payslip carries no tax
  registration number, because it is not a tax document.

---

## 3. The traps

There are four shapes. Run all four against any new document. Three of them were real bugs in
real systems and the fourth was a false alarm, which is itself worth knowing.

### 3a. Shape A — an issued document resolves a field live that should have been frozen

**Symptom.** A customer queries an old order. The copy you print does not match the copy they
hold.

**Why.** The renderer joins to the master table by id.

**The fix.** Copy the identity onto the row at issue time. A small set of columns, or a shared
mixin. Then the renderer never touches the master table.

**The one people get wrong in both directions.** Your own letterhead. Split it:

- **Frozen:** the tax registration number. It states which registration the document was issued
  under, and those change.
- **Live:** the name, address, phone and logo. A reprint should tell the reader how to reach you
  **today**.

Write that split down, because both halves look arbitrary until you see the reason.

### 3b. Shape B — editing a master record strands work in flight

**Symptom.** A part-received order can no longer be completed. The error names a field nobody
edited.

**Why.** Somebody changed a supplier's currency, or a unit of measure, and the in-flight document
now fails a consistency check against its own frozen lines.

**The fix.** Freeze the value at first use, and refuse the master edit while work is in flight,
with a message that says which records are blocking it.

### 3c. Shape C — a rename orphans every row holding the old string

**Symptom.** A filter stops matching. Rows "disappear" from a category.

**Why.** A user-extendable lookup value is stored as free text on the rows that chose it. Rename
it and every stored copy points at a name that no longer exists.

**The fix.** A rename cascades to the rows, in the same transaction, and records how many rows it
repointed in the audit entry.

**And the exception that proves the rule.** One category must *not* cascade: units of measure. A
cascade would walk straight past a freeze, because quantities carry no unit of their own, and it
would strand every in-flight order whose receiving checks the unit against a snapshot. So
renaming a unit that is **in use** is refused. An unused one renames freely.

**Deleting is a different question from renaming.** Deleting a lookup value with rows still
holding the string is usually allowed, and should record how many rows still use it, so the
orphan is an auditable fact rather than a silent one. It was *renaming* that needed the cascade.

### 3d. Shape D — a denormalised cache restates past records

**Symptom.** Nothing. This one gets investigated and turns out fine, and it is worth writing down
so nobody re-investigates it.

The item's "last purchase cost" looks like it would restate history. It does not, because every
stock movement carries its **own** cost. The cached value only seeds the default for future
movements.

**The general form:** a denormalised value is safe when every historical row carries its own
copy. It is a bug when history reads through it. Check which one you have, then record the
answer.

### 3e. The controlled-form footer

**Symptom.** A quality auditor rejects a document because its form revision number is wrong.

**Why.** Somebody wired the footer's revision and issue date to the *record's* own version and
date. Those fields describe the **blank form template**, not the document filled in on it. It is
a genuinely confusing distinction and it has shipped as a bug more than once.

**The fix.** They are properties of the template, frozen at creation of the record. If you have
controlled forms at all, write this down where somebody will find it.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Which records count as issued? | write the list | | |
| Snapshot storage | columns on the row, or a JSON blob, or a separate table | | |
| Your own letterhead | frozen, live, or split | | |
| Do lookup renames cascade? | yes, no, or yes with exceptions | | |
| Does deleting a lookup value cascade? | | | |
| Do response schemas expose the snapshot, or the live value? | | | |

Row 2: columns are queryable and cost a migration each. A JSON blob is flexible and you cannot
filter on it. For anything a report needs to group by, use columns.

Row 6 is a real trap and it usually gets left open. If the detail screen shows today's supplier
name while the PDF shows the frozen one, users will report the PDF as broken. Pick one and be
consistent.

---

## 5. Inventory

### Frozen

| What | How | On which documents |
|---|---|---|
| | | |

### Live on purpose

| What | Why | In the cache key? |
|---|---|---|
| | | |

Every row in this table must be in the cache key, or a change to it can never reach a reprint.

### Deliberately not frozen and not cascaded

| Case | Why |
|---|---|
| | |

### Known gaps

---

## 6. New-document checklist

1. **List every field the document prints.** For each one: frozen or live?
2. **Frozen** means a column set at issue time in the service. Never a join at render time.
3. **Live** means it goes in the cache key. A live read missing from the key can never reach a
   reprint.
4. **Money** freezes with its currency.
5. **Run the four shapes in §3 against your design.** Can a master edit strand work in flight?
   Does any stored string come from a lookup that could be renamed?
6. Say which side each field is on, in the module guide, and add the document to §5.

---

## 7. How to re-check this doc

> Paths below are examples from one tree. Adjust them to yours. What matters is the check,
> not the path. Where a count is given, it is the count **for this project**, so fill it in
> the first time you run it.

```bash
# The snapshot mixins and who uses them.
grep -rn --include="models.py" "SnapshotMixin" app/
```

```bash
# Re-resolving a counterparty at print time. A renderer that fetches a customer or
# supplier by id, for anything other than a listed live read, is the Shape A bug.
# Read the hits, do not count them.
grep -rn --include="*.py" "vendor_crud.get\|client_crud.get\|customer_crud.get" app/*/service/pdf.py app/*/*/service/pdf.py 2>/dev/null
```

```bash
# The no-cascade exceptions.
grep -rn --include="*.py" "NO_CASCADE" app/settings/
```

```bash
# Cross-check against the cache-key rule: every live read in §5 must appear as an
# argument to the fingerprint call.
grep -rn --include="*.py" "fingerprint(" app/ | grep -v "app/documents/"
```
