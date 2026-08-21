# Audit & Activity Logging

> Read this before you write a service mutation, or when you are wondering why an audit row is
> missing.
>
> **Status in this project:** decide in Part 1 of the checklist
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

Who changed what, when, and from where. For a regulated or audited system that is a correctness
requirement, not telemetry.

But it must never be able to break a business transaction. A logging failure that rolls back a
purchase order is a much worse outcome than a missing log line. So the design follows one shape:
**the log is dispatched after the commit, and not awaited.**

That shape has a cost, and you should decide with your eyes open. See §3a.

---

## 2. The rules

- **Never await the log call.** It is fire-and-forget by design.
- **Log after the commit, never inside the transaction.** A log written inside vanishes on
  rollback. Worse, a queued job fired inside a transaction that then rolls back runs anyway, so
  you get an audit row for something that never happened.
- **Use one wrapper**, not the logger directly. It fills in the resource type and keeps call
  sites to about four arguments.
- **Do not pass the actor's name, role, tenant or IP by hand.** They come from the request
  context. Passing them by hand is how they end up wrong.
- **The details field must be safe to serialise.** Decimals, ids and timestamps get handled.
  Arbitrary objects do not.
- **Audit tables are append-only.** No soft delete, no updates, no tenant id of their own beyond
  what is stamped.

---

## 3. The traps

### 3a. A dropped job is an unrecoverable missing row

**Symptom.** Nothing. That is the problem.

**Why.** Fire-and-forget means that if the queue is unreachable or the job fails, the business
transaction still commits and **no audit row is ever written.** There is no dead-letter and no
reconciliation.

**How much this matters depends on your answer to one question:** is the audit trail a compliance
requirement, or is it a convenience for support?

- **Convenience.** Fire-and-forget is right. Move on.
- **Compliance.** Fire-and-forget alone is not enough, and a circuit breaker does not help
  either, because a breaker sheds load and does not recover the lost row. You need a **transactional
  outbox**: write the audit row into an outbox table *inside* the same transaction, and have a
  worker move it to its destination. Then the log commits or rolls back with the business action,
  which is what you actually wanted, and delivery is a separate problem.

A system I reviewed chose fire-and-forget and now lists this gap as the most valuable thing left
to close.
**If your system is audited, build the outbox on day 1.** It is a table and thirty lines. Retro-
fitting it means backfilling a trail you cannot backfill.

### 3b. A background job has no request context

**Symptom.** Audit rows with no actor, no tenant and no IP address, appearing at odd hours.

**Why.** The context values are bound per request. A job has no request, so the fallbacks are all
empty.

**The fix.** Anything logging from a job passes the actor and tenant explicitly.

### 3c. Bulk actions that write one row per record

**Symptom.** One user action buries the audit trail under 500 rows.

**The fix.** A bulk action writes **one** summary entry, with the count and the failure count.
Deliberate, and worth stating in the doc so nobody "fixes" it.

### 3d. The IP address is the proxy's

**Symptom.** Every audit row has the same IP address.

**Why.** If the browser talks to a server that talks to your API, every request reaches you from
that server. → [`rate-limiting.md`](rate-limiting.md) §3

**The fix, and it is a real decision.** Forwarding the real address end to end means trusting a
header, and a forgeable header is arguably worse than a known-useless one. Decide, and write down
which. What you must not do is build a control that assumes the audit IP identifies a person.

### 3e. Ordering cannot be checked with a grep

You cannot grep for "the log call comes after the commit". A line-based search will not tell you.
If you need to prove it, walk the syntax tree: for every function, assert no log call appears
before its commit. §7 has the shape.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Is the trail a compliance requirement? | **answer this first** | | |
| Delivery | fire-and-forget, or a transactional outbox | | |
| What is audited | mutations only, or reads too | | |
| Storage | the same database, or a separate store | | |
| Retention | forever, or N years then archive | | |
| Does a record also keep its own status history? | yes, or the global trail only | | |
| Bulk actions | one summary row, or one per record | | |

Row 3: read auditing is expensive and almost always dwarfs the business data. If regulation
demands it for specific documents, audit those specifically rather than everything.

Row 5: decide now, because "forever" is a decision too and it shows up as a very large table in
year three.

---

## 5. Inventory

### The path

```
service mutation
  -> commit
  -> audit wrapper          (fills in the resource type)
      -> logger             (reads the request context, dispatches)
          -> queued job     (writes the row)
```

### What binds the request context

| Value | Bound by |
|---|---|
| actor name, actor role | the auth dependency |
| IP address | the auth dependency |
| tenant id | the tenant dependency |

All three must be wired, or rows land anonymous.

### Where auditing is deliberately not used

| Not audited | Why |
|---|---|
| Reads | would dwarf the business data, and nobody has asked |
| The data-access layer | it does not own the transaction, so it cannot know the write survived |
| Individual rows in a bulk action | one summary entry instead |
| | |

### Known gaps

---

## 6. New-module checklist

1. Set the module's resource name. That string shows up in the timeline, so make it the singular
   resource name.
2. In each mutating method, **after the commit**, call the audit wrapper with the actor, the
   action, the record id, and a short summary.
3. Never await it. Never call it before the commit.
4. Keep the details small and serialisable. It is a summary, not a diff of the whole row.
5. If the resource needs a human label in a timeline, add a resolver for it.

---

## 7. How to re-check this doc

> Paths below are examples from one tree. Adjust them to yours. What matters is the check,
> not the path. Where a count is given, it is the count **for this project**, so fill it in
> the first time you run it.

```bash
# Awaiting the logger. Expect zero.
grep -rn --include="*.py" "await activity.log\|await self._audit" app/
```

```bash
# Audit called from the data-access layer. It cannot know whether the write
# survived. Expect zero.
grep -rln --include="crud.py" "activity.log\|_audit(" app/
```

```bash
# The context binders. All must be wired or rows land anonymous.
grep -rn --include="*.py" "bind_actor\|bind_tenant\|bind_branch\|bind_ip" app/ | grep -v "context.py\|test_"
```

```bash
# Ordering: no log call before the commit on the same path. A grep cannot do this,
# so walk the tree. Expect zero.
#
# The `return` check is what makes it usable. Without it, an early-return branch
# that audits a read and never commits, a download for instance, is flagged on
# every run. A check that always fires is a check nobody reads.
python3 - <<'AST'
import ast, pathlib
for p in sorted(pathlib.Path("app").rglob("*.py")):
    if p.name.startswith("test_"):
        continue
    try:
        tree = ast.parse(p.read_text())
    except SyntaxError:
        continue
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        commits = sorted(
            n.lineno for n in ast.walk(fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "commit"
        )
        if not commits:
            continue
        returns = [n.lineno for n in ast.walk(fn) if isinstance(n, ast.Return)]
        for n in ast.walk(fn):
            if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr in ("log", "_audit")):
                continue
            later = [c for c in commits if c > n.lineno]
            if not later:
                continue
            # a return between the two means they sit on different paths
            if any(n.lineno < r < later[0] for r in returns):
                continue
            print(f"{p}:{n.lineno}  audit before commit in {fn.name}")
AST
```
