# Error Handling

> Read this before you raise anything, anywhere.
>
> **Status in this project:** in force from day 1
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

Every error a client sees should have its status code and its message defined **once**, in a
named exception, near the part of the system it belongs to.

The alternative is an inline error with a message string. Then the same failure gets a slightly
different wording each time somebody raises it, and there is no single place to see what a module
can refuse. For any system where "why did it say no?" is a real support question, that catalogue
is worth having.

---

## 2. The rules

- **Every module has an exceptions file** of named exceptions, one per refusal it can make.
- **Neither services nor routes build an inline error.** Status code and message live once. This
  includes route-level guards. Ownership refusals, upload rejections and import failures all get
  a named exception.
- **Cross-cutting errors get caught and re-raised as the module's own.** A generic invalid
  transition becomes "this proposal cannot go from draft to approved".
- **The wrong-tenant answer is 404, not 403.** → [`tenancy-and-scoping.md`](tenancy-and-scoping.md)
- **The stale-edit answer is 409. The missing-version answer is 428.**
  → [`concurrency.md`](concurrency.md)
- **Only the shared framework-level guards may raise an inline error.** Keep that list short and
  written down (§5).
- **No error response ever contains a stack trace or an internal path.**

---

## 3. The traps

### 3a. The catch-all that hides a missing guard

**Symptom.** Clean 409 responses in the logs. Everybody is happy. Nobody notices that the
application should have refused the request before it ever reached the database.

**Why.** A global handler turns any database constraint violation into a tidy 409. That is good
for the client and it hides the fact that a race got through.

**The fix.** Keep the handler. Read a constraint-violation 409 in the logs as "did we forget a
guard?" rather than "a race happened". A real concurrency bug was found this way, months after it
started firing.

### 3b. The safety net that becomes the pattern

**Symptom.** Services throw plain built-in errors and rely on the global handler mapping them to
sensible status codes.

**Why.** It works. A plain value error becomes a clean 400 and nobody has to write an exception
class.

**Why it is wrong.** You lose the catalogue. Nobody can list what a module refuses. And the
mapping is coincidence, so a refactor that changes the error type changes the HTTP status with no
review.

**The fix.** Keep the global mapping as a net that stops a stack trace leaking. Do not lean on it.

### 3c. The local helper function

**Symptom.** `def _conflict(msg)` at the top of a service file.

**Why.** Somebody wanted named errors without writing classes.

**Why it is wrong.** It is the same anti-pattern with a nicer face. The message is still written
at the call site, so it still varies, and it is still invisible from outside the file.

### 3d. Validation errors the client cannot read

**Symptom.** The form shows "Value error, ensure this value has at least 1 characters" against no
particular field.

**Why.** The framework's validation error shape is nested and per-item, and nobody flattened it.

**The fix.** Flatten validation errors into readable strings in one handler, keyed by field name,
and keep that shape stable. The client depends on it. Changing it is an API break.
→ [`api-contract-and-versioning.md`](api-contract-and-versioning.md)

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Exception base | the framework's HTTP exception, or a domain error mapped at the edge | | |
| Error body shape | one field, or a code plus message plus details | | |
| Are error codes stable identifiers the client can branch on? | yes, or messages only | | |
| Validation error shape | flattened per field, or the framework default | | |
| Which files may raise an inline error | write the list | | |
| Do errors carry a request id? | yes | | |

Row 1: subclassing the framework's HTTP exception is the least code and it puts an HTTP concept
into the service layer. A pure domain error mapped at the edge is cleaner and costs you a mapping
table. Both are defensible. Pick one and do not mix.

Row 3: if the client ever needs to react differently to two errors with the same status code, it
needs a stable code. Adding one later means touching every exception.

Row 6: yes. See [`observability.md`](observability.md). It turns "it failed" into a log lookup.

---

## 5. Inventory

### Global handlers

| Exception | Status | Notes |
|---|---|---|
| validation error | 422 | flattened to readable strings |
| integrity error | 409 | a constraint fired, usually a race |
| database unavailable | 503 | |
| any other database error | 500 | |
| catch-all | 500 | so nothing leaks a stack trace |

### Files allowed to raise an inline error

These are the cross-cutting framework guards, not domain modules. Anything else is a violation.

| File | Why exempt |
|---|---|
| the rate limiter | front-door infrastructure |
| the auth principal resolver | 401s before there is a domain |
| the token validator | |
| the permission checker | the 403 itself |

### Known gaps

---

## 6. New-module checklist

1. **Create the exceptions file first**, before the data-access layer. Name an exception for every
   refusal: not found, conflicts, invalid input the schema cannot express, ownership, state
   transitions.
2. Services and routes raise only these.
3. Catch the shared transition error and re-raise your own.
4. Wrong tenant returns your not-found exception. 404, not 403.
5. Document the refusals in the module guide, so support can look them up.

---

## 7. How to re-check this doc

> Paths below are examples from one tree. Adjust them to yours. What matters is the check,
> not the path. Where a count is given, it is the count **for this project**, so fill it in
> the first time you run it.

```bash
# Inline errors outside the exempt files. Anything else is a violation.
grep -rln --include="*.py" "raise HTTPException(" app/ | grep -v "test_\|exceptions.py"
```

```bash
# Every module should have an exceptions file.
find app -name exceptions.py | wc -l
```

```bash
# The local helper form of the same anti-pattern. Expect zero.
grep -rn --include="*.py" "def _conflict\|def _not_found\|def _bad_request" app/
```

```bash
# The global handlers are actually registered.
grep -n "register_exception_handlers\|add_exception_handler" app/core/main.py
```
