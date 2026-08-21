# Transactions & Layering

> Read this before you write any service method that changes anything, or any call from one
> module into another.
>
> **Status in this project:** in force from day 1
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

Every module has the same layers, and the transaction belongs to exactly one of them.

When that slips, the failures are the expensive kind. A commit in the data-access layer means a
half-finished operation cannot roll back cleanly. Two commits in one service method means the
second can fail with the first already applied. An audit entry written inside the transaction
disappears when it rolls back, so your record of what happened is missing exactly the events that
went wrong.

This is the contract that keeps one business action atomic. It is the most important rule in the
whole kit.

---

## 2. The rules

- **The service owns the transaction. Exactly one commit per mutation**, in the service. The
  service stamps the tenant and the author, allocates numbers, checks the state machine, writes
  the audit entry and returns the result.
- **The data-access layer flushes and never commits.** Flush to get database-generated ids.
  Never commit, never roll back, in that layer.
- **The audit entry is written after the commit**, and never awaited.
  → [`audit-logging.md`](audit-logging.md)
- **The direction is strict**: routes to service to data-access to models. No import goes the
  other way. Routes never touch the session and never build a query.
- **A write into another module goes through that module's service, told not to commit.** A read
  from another module goes through that module's data-access layer.
- **After writing child rows, reload the parent the way a plain read would**, or you can return
  stale or empty children (§3a).
- **One place wires the service into the routes.** It hands back the module's single instance and
  never builds a second one.

---

## 3. The traps

### 3a. The stale-children trap

**Symptom.** You create a record with lines. The response comes back with an empty lines array,
or with yesterday's lines. A separate GET afterwards looks perfect. An in-process test passes.
Only the real client sees it, sometimes.

**Why.** This is specific to SQLAlchemy with `expire_on_commit=False`, but the shape exists in
any ORM with an identity map. After the commit, the session still holds the parent object as it
was loaded. Reloading the parent on that same session can hand you the cached object, with its
child collection as it was before you wrote the children.

**The fix.** Do the final read in a brand new session, exactly as an HTTP GET would. Make it one
named method on the service, and have every mutating method return through it. If it is a helper
that everyone has to remember to call, someone will forget.

### 3b. Cross-module calls that look wrong and are not

At grep distance, `repairs` importing `work_order_crud` looks like a layer skip. It is not.

- **Reads** go through the other module's data-access layer.
- **Writes** go through the other module's service, with a `commit=False` argument, so the
  collaborator flushes but the *calling* service still owns the single commit.

A proposal converting into a client is the clean example. It creates the client flush-only, then
commits the whole thing once. **Do not "fix" these into direct writes.** That splits one
transaction into two, and now half the operation can survive the other half failing.

Make the parameter explicit and default it to `True`, so the ordinary case is safe and the
shared-transaction case is visible at the call site.

### 3c. The two-commit method

**Symptom.** Occasionally a record exists with no matching child rows, or a number was allocated
for a document that does not exist.

**Why.** Somebody added a second thing to a service method and committed after each. Usually
because the second part needed the first part's id.

**The fix.** Flush to get the id. Commit once at the end. If you genuinely cannot, you have two
operations and they need two endpoints, with the second one able to run against a saved first.

### 3d. Routes that grew a query

**Symptom.** A tenant leak, or a filter that behaves differently on one endpoint.

**Why.** A route needed one extra field and building the query there was three lines instead of
thirty. Now the tenant scoping, the soft-delete filter and the sort allow-list are missing,
because they live in the layer that was skipped.

**The fix.** Ban it and test for it. A route file that mentions the session or builds a query is
a broken layer.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Who commits | the service, or a request-scoped unit of work at the edge | | |
| `expire_on_commit` | `True` (safe, extra queries) or `False` (fast, §3a trap) | | |
| Cross-module writes | a `commit=False` argument, or events, or a shared unit of work | | |
| Where the session comes from | injected per request, or a context variable | | |
| Are routes allowed to call data-access directly for trivial reads? | no, or yes with a written list | | |

On the second row: `expire_on_commit=True` avoids §3a entirely and costs you a re-read after
every commit. `False` is faster and hands you that trap. Whichever you pick, write down which and
why, because the trap only makes sense once you know the setting.

On the last row: "no" is the right answer. Every exception grows.

---

## 5. Inventory

### Where the contract is followed

Everywhere, by definition. This table records only the shape of each module's service, if they
differ.

| Module | Service shape | Notes |
|---|---|---|
| | | |

### Where the contract bends, on purpose

| Case | Detail |
|---|---|
| `commit=False` service methods | The one sanctioned way one transaction spans another module's write |
| Background jobs | A job has no request transaction, so it opens and commits its own |
| | |

### Known gaps

---

## 6. New-module checklist

1. Build the files in the anatomy order.
   → [`module-anatomy-and-placement.md`](module-anatomy-and-placement.md)
2. **One commit, in the service.** The data-access layer flushes only.
3. Stamp the tenant and the author in the service. Allocate the number there. Check the state
   machine there. Write the audit there, after the commit.
4. Need another module's data? Read through its data-access layer. Write through its service with
   `commit=False`.
5. If the method writes children and returns the parent, return through a fresh-session reload.
6. Register the router. Keep the package init light.

---

## 7. How to re-check this doc

> Paths below are examples from one tree. Adjust them to yours. What matters is the check,
> not the path. Where a count is given, it is the count **for this project**, so fill it in
> the first time you run it.

```bash
# A commit or rollback in the data-access layer. Expect zero, docstrings aside.
grep -rn --include="crud.py" "\.commit()\|\.rollback()" app/
```

```bash
# Routes touching the session or building a query. Expect zero.
grep -rn --include="routes.py" "session.execute\|session.add\|session.commit\|session.flush\|select(" app/ | grep -v import
```

```bash
# Reversed imports. Expect zero.
grep -rn --include="crud.py" --include="models.py" "import service\|\.service import" app/
```

```bash
# The sanctioned cross-module write pattern. Every hit should pass commit=False.
grep -rn --include="*.py" "commit=False" app/ | grep -v "test_"
```

```bash
# More than one commit in a single function.
#
# Read every hit. The common false positive is an if/else with one commit in each
# branch. Only one runs per call, so that is fine. A real hit is two commits on the
# same path, which means half the operation can survive the other half failing.
python3 - <<'PY'
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
        commits = [
            n for n in ast.walk(fn)
            if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
            and n.func.attr == "commit"
        ]
        if len(commits) > 1:
            print(f"{p}:{fn.lineno}  {fn.name}  ({len(commits)} commits)")
PY
```
