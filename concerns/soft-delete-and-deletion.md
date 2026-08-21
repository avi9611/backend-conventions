# Soft Delete & Deletion

> Read this before you delete anything, and before you add a unique constraint.
>
> **Status in this project:** decide in Part 1 of the checklist
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

Deleting a business record usually means marking it deleted, not removing the row. That keeps
history readable and keeps foreign keys valid.

It also creates four problems that only appear later. A unique constraint that now blocks a name
you can no longer see. Queries that forget the filter. A "deleted" record that other records
still point at. And a general-purpose delete endpoint that turns out to be the wrong tool for a
record with dependents.

This file is short because the rules are short. It is here because every one of these has cost
somebody a day.

---

## 2. The rules

- **Soft delete is for business data.** Config, permissions and append-only rows get hard delete
  or no delete at all.
- **Every query on a soft-deletable table filters out deleted rows.** No exceptions, so make it
  part of the shared query builder rather than something each query remembers.
- **A unique constraint on a soft-deletable table is a partial index** that applies only to live
  rows. §3a.
- **Deleting is refused when something depends on the row.** Refuse with a message that names
  what is blocking it. §3c.
- **Hard delete exists only where there is a written reason.**
- **Restoring is a real operation, or it is not offered.** A "deleted" flag that nothing can
  clear is a hard delete with extra steps.

---

## 3. The traps

### 3a. The unique constraint that outlives the row

**Symptom.** "A customer with that code already exists." There is no such customer on screen.

**Why.** The deleted row still holds the code, and the unique constraint does not know about the
deleted flag.

**The fix.** A partial unique index:

```sql
CREATE UNIQUE INDEX ix_clients_code_live
  ON clients (tenant_id, code) WHERE is_deleted = false;
```

Do this from the first table, not after the first support ticket. Retrofitting it means finding
every duplicate that accumulated in the meantime.

**The alternative** is to blank or suffix the unique field on delete, which loses information and
makes the audit trail confusing. The partial index is better.

### 3b. The query that forgot the filter

**Symptom.** A deleted record appears in one screen and not another. Or a count is higher than
the list.

**Why.** One query, usually a new aggregate or a report, did not add the filter.

**The fix.** Put the filter in the shared query builder, so a query has to *opt out* rather than
opt in. And check aggregates specifically, because they are written later, by somebody else, and
usually not by copying an existing list query. → [`analytics.md`](analytics.md)

### 3c. Deleting a record other records point at

**Symptom.** A screen shows "unknown supplier" on an old order.

**Why.** The supplier was deleted. The order still holds the id and the join now finds nothing.

**The fix.** Two halves and you need both.

- **Refuse the delete** when live records depend on it, and say what they are. "Cannot delete
  this supplier, 3 open orders reference it."
- **Freeze the identity on the dependent record** so an old order does not need the join at all.
  → [`snapshots-vs-live.md`](snapshots-vs-live.md)

The second half is what makes the first half's rule bearable. Without it you can never delete
anything, ever.

### 3d. Hard delete, and when it is right

Not everything should be soft deleted.

| Case | Delete style | Why |
|---|---|---|
| Business records | soft | history has to stay readable |
| Append-only children of a business record | cascade with the parent | reached only through the parent |
| Session tokens, one-time codes, cache-like rows | hard | keeping them is a liability, not an asset |
| Config and lookup values | usually refuse, or deactivate | see §3e |
| Personal data on request | hard, or anonymise | a legal requirement beats a convention |

The last row deserves a real decision. If somebody has a right to erasure, a soft delete does not
satisfy it. Decide up front which tables hold personal data and what erasure means for each one.

### 3e. Deactivate is not the same as delete

A config value that is in use should be **deactivated**, not deleted. It stops being offered in
new records and keeps working on existing ones.

That is a different flag with a different meaning, and conflating them means either you cannot
retire an option, or retiring one breaks history. Two flags, two words, no ambiguity.

### 3f. Bulk delete

A bulk delete acts on an explicit id list. It reports per-row failures rather than failing whole,
because one blocked record should not stop the other forty-nine. And it writes **one** audit
entry with the counts, not fifty. → [`audit-logging.md`](audit-logging.md)

Bulk paths are also where the "mine only" rule is most often forgotten.
→ [`permissions.md`](permissions.md) §3a

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Which tables are soft deletable | write the list, or "all business data" | | |
| Filter placement | in the shared query builder, or per query | | |
| Unique constraints | partial indexes on live rows | | |
| Can a deleted record be restored? | yes, by whom, or no | | |
| Blocked deletes | refuse and name the blocker, or cascade | | |
| Personal data erasure | write the policy | | |
| Purge policy | never, or hard delete after N years | | |

Row 4: if the answer is no, say so and call the flag what it is. An unrestorable soft delete is
still useful, because it keeps foreign keys valid, but do not build a restore UI you cannot
support.

Row 7: soft-deleted rows accumulate forever by default. That is a decision, not an accident.

---

## 5. Inventory

### Soft-deletable tables

| Table | Partial unique index? | Restorable? |
|---|---|---|
| | | |

### Hard delete, on purpose

| Table | Why |
|---|---|
| | |

### Referential guards

| Deleting this | Is refused when |
|---|---|
| | |

### Known gaps

---

## 6. New-table checklist

1. Decide soft, hard or no delete, using §3d.
2. If soft: use the shared mixin, and make sure the shared query builder filters it.
3. **Every unique constraint becomes a partial index on live rows.**
4. Decide what depends on this record and add the referential guard.
5. If other records store this one's name, freeze it there.
6. Add a delete test that proves the guard fires, and a list test that proves deleted rows do not
   appear.

---

## 7. How to re-check this doc

> Paths below are examples from one tree. Adjust them to yours. What matters is the check,
> not the path. Where a count is given, it is the count **for this project**, so fill it in
> the first time you run it.

```bash
# Unique constraints on soft-deletable tables that are not partial. Read every hit.
grep -rn --include="models.py" "unique=True\|UniqueConstraint" app/
```

```bash
# Queries on soft-deletable models with no deleted filter. Noisy. Read the hits,
# and pay particular attention to anything in an analytics or reports file.
grep -rn --include="*.py" "select(" app/*/crud.py app/*/*/crud.py 2>/dev/null | grep -v "is_deleted"
```

```bash
# Hard deletes. Every one should be listed in §5.
grep -rn --include="*.py" "session.delete(\|delete(" app/ | grep -v "test_\|soft\|is_deleted"
```
