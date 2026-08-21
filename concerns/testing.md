# Testing

> Read this before you write a test, and when you are wondering how the suite went green while
> the application died on boot.
>
> **Status in this project:** in force from day 1
> **Worth its own file.** Testing practice is usually good and almost never written down.
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

Tests are the gate. If there is no separate lint or type gate, they are the *only* gate, and you
should say so out loud in `CLAUDE.md` so nobody assumes otherwise.

The trap specific to this kind of application is not "we have too few tests". It is that the
tests all reach into the code the same way, so a whole class of failure is structurally invisible
to them.

---

## 2. The rules

- **Tests run against a real database.** Mocking the data layer tests your mocks.
- **A test that has never been seen to fail proves nothing.** Especially a concurrency test. §3b.
- **Never patch a module-level object by assignment.** It leaks into every later test in the
  process. Use the framework's patching helper, which restores afterwards. §3c.
- **Write the guard tests, not just the behaviour tests.** §3a.
- **Quote real numbers when you report a run.** "839 passed, 1 failed". Never "tests pass".
- **Name any failure that predates you, and say how you proved it did.** Otherwise the next
  person re-investigates it.
- **A test fixture that picks "a" record picks the wrong one eventually.** Pin it. §3d.

---

## 3. The traps

### 3a. The structural blind spot, and the five guard tests that close it

**Symptom.** `445 tests passed` and the server dies on boot with a name error.

**Why.** Every test imports services, data-access classes or models **directly**. None of them
import the router aggregator. So a route module that fails at import time is invisible to the
whole suite while the application refuses to start.

This is not hypothetical. It has happened, when a route gained a query parameter helper in a file
that never imported it.

**The fix is five small tests.** None is over 100 lines. Together they are the highest-value
testing you will write.

**1. The app boots and the schema builds.**

Import alone only proves the module executed. **Generating the full API schema is what walks
every signature and every response model**, so it catches a route whose annotations do not
resolve. Assert the path count is above a floor, and spot-check a few endpoints the suite
otherwise never touches.

**2. No duplicate route paths.** Two routes on the same method and path means one is dead code.

Note one detail: some frameworks stopped flattening included routers into the parent's route
list, so the obvious way of reading the route table returns almost nothing and the test cannot
fail. Walk the tree properly and assert a realistic count, so a silently empty check is loud.

**3. Every route is permission-gated, except an explicit allow-list.**

**Walk the resolved dependency graph, not the source.** A gate can be written three different
ways. Grepping for one of them reports the other two as unguarded, which trains people to ignore
the test.

Each allow-list entry carries a written reason. The bar for adding one: it is either
unauthenticated by necessity, or it is scoped to the caller's own row so no permission could
narrow it further.

**4. Shared response shapes have not been widened.**

If you have a shape that is deliberately minimal, like a dropdown option, pin its field set:

```python
assert set(ReferenceOption.model_fields) == {"id", "label", "sublabel", "is_active"}
```

The pressure to add a field is constant and always locally reasonable. Each one is a one-line
change in a file nobody re-reads. The test does not ask whether the field is useful, it asks
whether you meant it. → [`reference-data-and-pickers.md`](reference-data-and-pickers.md)

**5. Declared module edges match the code.**

→ [`module-anatomy-and-placement.md`](module-anatomy-and-placement.md) §3g

### 3b. The concurrency test that cannot fail

**Symptom.** A concurrency test passes. It also passes with the lock deleted.

**Why.** The test fires two operations and neither of them ever actually overlaps, because they
are far too fast.

**The fix.** Inject a delay inside the locked section, so the race is real. **Then delete the lock
and confirm the test fails.** Only then put the lock back.

A real double-approval bug was found this way, in a path where the test had been passing for
months. → [`concurrency.md`](concurrency.md)

### 3c. The patch that leaks

**Symptom.** A test fails only when the whole suite runs, and passes alone. Or a test fails that
nobody touched.

**Why.** Somebody replaced a method on a module-level object by assignment. Nothing restores it,
so every later test in that process sees the fake.

**The fix.** Use the framework's patching fixture, which restores automatically. Ban the
assignment form and grep for it.

### 3d. The fixture that picks the wrong actor

**Symptom.** A suite that passed for months starts failing after an unrelated change, with an
error about permissions or assignment.

**Why.** A shared fixture selects "a user" with no ordering. Any churn in the users table changes
which one, silently. A non-superuser actor then fails every test that assigns something.

**The fix.** Pin it. Superuser only, not deleted, ordered by creation time. And when you write a
new one, **copy an existing fixture whole**. The three conditions are the point of it, not
decoration.

One codebase had 18 copies of this fixture, and every one of them was wrong until somebody
finally noticed.

### 3e. Order-dependent tests

**Symptom.** Two tests fail on a freshly seeded database and pass on the next run.

**Why.** They reach for *a* record of some kind rather than pinning the one they created. Straight
after seeding they find the seed's record.

**The fix.** Create what you need and pin it. And know the symptom, because "passes on the second
run" is otherwise baffling.

### 3f. Tests that cannot see a whole layer

Beyond §3a, notice what your suite structurally cannot reach. If nothing goes over HTTP, then
nothing tests your serialisation, your status codes, your headers or your permission
dependencies as they actually run.

That may be a fine trade, and it is a decision. Write it down, and write the guard tests that
cover the gap it leaves.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Test level | services and data-access directly, or over HTTP | | |
| Database | a real one, or an in-memory substitute | | |
| Isolation | transaction rollback per test, or a truncate, or a fresh database | | |
| Fixtures | shared factories, or per-module | | |
| Is there a lint gate? | | | |
| Is there a type gate? | | | |
| Coverage target | a number, or none | | |
| Where guard tests live | | | |

Row 1: direct calls are fast and miss everything in §3f. Over HTTP is slower and tests the thing
users actually hit. A pragmatic answer is direct calls for business logic plus the five guard
tests for the layer above.

Row 2: an in-memory substitute is not your database. Different SQL, different constraint
behaviour, different types. If your application uses anything beyond the most basic SQL, use the
real one in a container.

Row 3: transaction rollback per test is fast and clean, and it makes it hard to test anything
that commits. Since the service layer owns commits, that matters here. Truncating between tests
is slower and honest.

Rows 5 and 6: if the answer is no, say so in `CLAUDE.md` explicitly. "There is no lint gate here,
tests are the gate" is useful information. Silence is not.

---

## 5. Inventory

### The guard tests

| Test | What it catches |
|---|---|
| | |

### Known-failing tests

Keep this current, with the reason and how you proved it predates the current work. Otherwise
every new person investigates it again.

| Test | Since | Why it fails | Whose fix |
|---|---|---|---|
| | | | |

### The current baseline

| Date | Result |
|---|---|
| | |

### Known gaps

---

## 6. New-module checklist

1. Tests against a real database, in the module's own test file.
2. **A cross-tenant isolation test.** One per module. A leak is invisible without it.
   → [`tenancy-and-scoping.md`](tenancy-and-scoping.md)
3. A test per named exception the module can raise, so the refusals are actually reachable.
4. If the module has a state machine, test that an illegal transition is refused.
5. If the module has a capped list, test the cap path. Patch the cap down rather than seeding 500
   rows.
6. If the module has aggregates, test totals against a hand-summed fixture, and test that the
   buckets partition exactly.
7. **Run the route guard tests after any route edit.**
8. Copy an existing fixture whole rather than writing a new one.

---

## 7. How to re-check this doc

> Paths below are examples from one tree. Adjust them to yours. What matters is the check,
> not the path. Where a count is given, it is the count **for this project**, so fill it in
> the first time you run it.

```bash
# The whole suite. Record the real numbers in §5.
python -m pytest -q
```

```bash
# The guard tests, which are the ones that fail for structural reasons.
python -m pytest app/apis app/test_module_edges.py -q
```

```bash
# Patching by assignment. Expect zero.
grep -rn --include="test_*.py" "^\s*[a-z_]*\.[a-z_]*\.[a-z_]* = " app/ | grep -v "monkeypatch\|self\."
```

```bash
# Fixtures that pick a record with no ordering. Read every hit.
grep -rn --include="test_*.py" -A3 "select(User)" app/ | grep -v "order_by"
```

```bash
# Which test files exist per module. A module with no test file is the gap.
for d in app/*/ app/*/*/; do
  [ -d "$d" ] || continue
  ls "$d"test_*.py >/dev/null 2>&1 || echo "no tests: $d"
done
```
