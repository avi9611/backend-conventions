# Concurrency

> Read this before you write a service method that locks, guards, or edits a record two people
> could touch at once.
>
> **Status in this project:** decide before the first multi-user edit screen
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

Two people open the same record. Both save. Without protection the second write silently
overwrites the first, and neither person is told. Nothing in the database notices, because both
wrote a legal value.

That is the whole problem class, and it has three flavours. **Cold-start races** on the first
insert of a kind. **Stale-guard races**, where a check reads data from before the lock.
**Lost-update races** on ordinary edits.

All three are subtle enough to break on an innocent refactor, which is why each one gets its own
section below.

---

## 2. The rules

- **Lock first, then check.** Every user-submitted mutation goes lock, then tenant check, then
  version check, then write. Checking an unlocked read is theatre. Two callers both pass and both
  write.
- **A locking read must force a refresh** of the object's fields. Otherwise the lock serialises
  the write while the guard reads pre-lock values. This is the trap. §3b.
- **User edits carry the version they were built from.** No version means refuse. Stale version
  means conflict. Never last-write-wins.
- **Do the whole preamble in one shared helper** so the order cannot be got wrong per module.
- **First-of-a-kind inserts use insert-on-conflict, not select-for-update.** A row lock takes
  nothing when the row does not exist yet. §3a.
- **Lock several rows in a single statement with an `IN` list**, never one at a time in
  application order. One at a time in opposite orders deadlocks.

---

## 3. The traps

### 3a. Cold start

**Symptom.** The first document of each year fails for almost everybody. Reported once a year,
in January, and impossible to reproduce in February.

**Why.** `SELECT ... FOR UPDATE` **locks nothing when the row does not exist yet.** So every
concurrent caller misses, every one inserts, one wins and the rest die on the unique constraint.
Measured on a real system: one of twelve concurrent callers succeeded.

It fires on the first record of each type each year, and on the first record in a newly created
tenant. Both of those are days when everyone is trying at once.

**The fix.** A single insert-on-conflict-do-update, returning the value. It takes the row lock
itself *and* covers the case where the row does not exist.

→ [`document-numbering.md`](document-numbering.md)

### 3b. The stale guard, and why it is the worst one here

**Symptom.** A record occasionally transitions twice. Two approvals, two generated documents, two
emails. Rare, unreproducible, and the code looks correct.

**Why.** This is an ORM identity-map problem. The sequence is:

```python
record = await service.get(session, id)          # read #1, and the variable is KEPT
locked  = await crud.get_for_update(session, id)  # read #2 — the SAME object
before  = locked.state                            # ← the value from read #1
```

The lock worked. The guard read pre-lock data. The write serialised correctly and checked the
wrong thing.

**Now the genuinely unnerving part.** A dozen other guards in the same codebase used this shape
and were **correct by accident of garbage collection**. They discarded read #1, so the object was
collected, so the locked re-read genuinely reloaded. The ordinary refactor of keeping the
reference in a variable would have silently disabled any of them. No exception. No failing test.
Just an occasional double transition.

**The fix.** Force a refresh on **every** locking read, so the property holds whether or not a
caller keeps the reference. Put it in the shared helper and put the reason in a comment, so it
cannot be simplified away.

**The rule is about the read, not about which lock you took.** The same trap turned up a second
time with a different lock: an advisory lock, then a plain eager-loading read. The read that
answers "did somebody else finish this while I was blocked?" **must force a refresh**, whatever
lock you were waiting on.

**And this one is worth reading twice:** the concurrency test passed both before and after the
lock was deleted. It was only found when somebody injected a sleep inside the locked section to
make the test actually race. **A concurrency test that has never been seen to fail is not
evidence of anything.**

### 3c. Lost updates on ordinary edits

**Symptom.** A user's change vanishes. They swear they saved it.

**The fix, and this one is cheaper than it sounds.** The edit request carries the version of the
record it was built from, in an `If-Match` header. The value is the row's own `updated_at`.

- **No new column, no migration.** Every response already carries `updated_at`, so callers echo
  back what they were given. A list row is as good a source as a detail read.
- **428 when the header is absent.** Opting out is refused, or the bug quietly comes back for any
  form that forgets it.
- **409 when it is stale.**

**Do not use the ORM's built-in version column.** That fires on *every* flush, including the
system's own writes. A background rollup touching a record while a user edits it would fail the
user's save for a reason they cannot act on. This check belongs only where a person submitted a
form.

### 3d. Multi-row locking and deadlock

**Symptom.** Occasional deadlock errors under load, on a path that allocates payments across
bills.

**Why.** Rows locked one at a time, in the order of an application list. Two callers with the
lists in opposite orders deadlock.

**The fix.** One statement with an `IN` list. The database locks in scan order regardless of your
list order. **Keep it one statement.** This looks like a deadlock risk and is the opposite.

### 3e. Rolling out the version check breaks callers in transit

**Symptom.** The moment a route requires the header, every client that has not shipped yet gets a
428.

**The fix.** Do these as vertical slices, one module at a time, server and client together. Not
"add the header everywhere, then update the client".

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Lost-update protection | `If-Match` on `updated_at`, a version column, or none | | |
| Missing version header | refuse with 428, or allow | | |
| Which routes get it | user-submitted edits and deletes only | | |
| Bulk endpoints | exempt, or per-row versions | | |
| Locking style | row locks, or advisory locks, or both | | |
| Idempotency keys on creates | yes, or no | | |

Row 2: allowing it means any form that forgets the header silently loses its protection. Refusing
means a noisy rollout and a guarantee. Refuse.

Row 4: exempt is usually right. A bulk action takes an explicit id list and reports per-row
failures already, and there is no single sensible version for a batch.

Row 6: an idempotency key stops a double-submitted create from making two records. Most internal
systems skip it and rely on unique constraints instead, which works when there is a natural key
and does not when there is not. If your clients retry automatically, add it.

---

## 5. Inventory

### Routes carrying the version precondition

| Module | Routes |
|---|---|
| | |

### Where it is deliberately not applied

| Case | Why |
|---|---|
| Bulk endpoints | explicit id list, per-row failures, no single version for a batch |
| System writes | rollups and counters lock first and do not go through a person's form |
| Duplicate creates on a natural key | a unique constraint gives you the 409 with no application lock |
| | |

### Known gaps

---

## 6. New-mutation checklist

1. **User-submitted edit or delete of a shared record?** Use the shared lock-then-check helper
   and take the version header on the route.
2. **A guard that reads state and then acts on it?** The read feeding the guard must be the
   locked one, forced to refresh. Do not add a second unlocked read and guard on that.
3. **First-of-a-kind insert on a natural key?** Insert-on-conflict, not read-then-insert.
4. **Locking several rows?** One statement.
5. Ship server and client together for any new version requirement.
6. If you write a concurrency test, **make it fail once** with the lock removed. Otherwise it
   proves nothing.

---

## 7. How to re-check this doc

> Paths below are examples from one tree. Adjust them to yours. What matters is the check,
> not the path. Where a count is given, it is the count **for this project**, so fill it in
> the first time you run it.

```bash
# Every locking read must force a refresh. A locking read without it is a latent
# stale-guard bug. The two counts should match.
grep -rn --include="*.py" "get_for_update\|with_for_update" app/ | grep -v "test_\|README" | wc -l
grep -rn --include="*.py" "populate_existing" app/ | grep -v "test_" | wc -l
```

```bash
# Routes carrying the version precondition. A shared-record update route without
# one is a lost-update risk.
grep -rn --include="routes.py" "IfMatchDep" app/ | grep -v import | wc -l
grep -rln --include="routes.py" "IfMatchDep" app/
```

```bash
# Every user mutation should reach the shared lock-then-check helper rather than
# hand-rolling lock plus check.
grep -rn --include="*.py" "_get_locked(" app/ | grep -v "scoped_service.py\|test_" | wc -l
```

```bash
# Cold-start inserts use insert-on-conflict, not for-update.
grep -rn "on_conflict_do_update\|with_for_update" app/*/numbering.py app/*/*/numbering.py 2>/dev/null
```
