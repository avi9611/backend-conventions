# API Contract & Versioning

> Read this before you change the shape of a response, or the meaning of a field.
>
> **Status in this project:** in force from the first client
> **New in this kit.** Phoenix has a version prefix and no rules about what may change behind it.
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

The moment a second piece of software reads your API, the shape of your responses is a contract.

For an internal system where you ship the client and the server together, that contract is cheap
to change and the risk is different. It is not "we broke a customer's integration". It is **the
two halves silently disagreeing**, which is worse because nothing errors.

The failures are quiet. A field renamed on the server and mapped by the old name on the client
becomes undefined, which renders as an empty cell. A new required filter that the client does not
send is ignored, so the table shows more rows than the summary counted. An enum value added on
the server crashes a switch statement that has no default.

---

## 2. The rules

- **Adding an optional field is safe. Everything else is a change to plan.** §3a.
- **Never change what a field means while keeping its name.** Add a new one.
- **A client that must send a new field ships in the same change as the server that requires
  it.** → [`concurrency.md`](concurrency.md) §3e
- **Never send a field the client should not see, and rely on the client not showing it.**
- **Unknown query parameters are dropped, not rejected.** So a typo in a filter name is silent.
  §3b.
- **Unknown enum values must not crash the client.** §3c.
- **The validation error shape is part of the contract.** Changing it breaks every form.
  → [`error-handling.md`](error-handling.md)
- **The version prefix exists. Decide what it actually means.** §4.

---

## 3. The traps

### 3a. What is safe and what is not

| Change | Safe? | Note |
|---|---|---|
| Add an optional response field | yes | |
| Add an optional request field | yes | |
| Add an optional query filter | yes | |
| Remove a response field | **no** | the client may read it |
| Rename a field | **no** | this is a remove plus an add |
| Change a field's type | **no** | including number to string |
| Narrow a field from nullable to required | **no** for requests, yes for responses |
| Widen a field from required to optional | yes for requests, **no** for responses |
| Add an enum value | **depends** | see §3c |
| Remove an enum value | **no** | old records may still hold it |
| Change a status code | **no** | |
| Change the error body shape | **no** | |
| Change the default sort or page size | **depends** | it changes what a client sees with no code change |

The safe sequence for a rename is the same as the one for a database column. Add the new one,
populate both, switch the client, then remove the old one. Four deploys, and each one is safe on
its own.

### 3b. The filter name that is silently ignored

**Symptom.** A table shows more rows than the number the summary panel reported. No error
anywhere.

**Why.** Most frameworks **drop unknown query parameters** rather than rejecting them. So a
mistyped filter name gives you an unfiltered result.

**The fix.** Check the filter name against the endpoint's declared params. Or, better, configure
your params model to **reject** unknown fields, and find out at development time. That is a real
trade: rejecting means an old client sending a removed filter now gets a 422 instead of being
ignored. For an internal system where both halves ship together, rejecting is better.

→ [`analytics.md`](analytics.md) §3a

### 3c. The new enum value that crashes the client

**Symptom.** A screen goes blank after a server deploy.

**Why.** The client maps a status string to a label with an exhaustive lookup and no fallback.

**The fix, on the client.** Coerce every incoming enum through a helper that takes the allowed
set and a fallback. Never cast a raw string straight to an enum type. Then a new value renders as
itself rather than breaking the page.

Do that from the first enum, because retrofitting it means touching every transformer.

### 3d. The field that leaks because the client hides it

**Symptom.** A cost price appears in the network tab for a user who is not supposed to see it.

**Why.** One response shape serves two audiences, and the client hides the field for one of them.

**The fix.** Different shapes for different audiences. The minimal dropdown shape is the extreme
version of this rule.
→ [`reference-data-and-pickers.md`](reference-data-and-pickers.md)

### 3e. The naming boundary

If your server speaks `snake_case` and your client speaks `camelCase`, then converting in exactly
one place is the rule that makes everything else work.

**One transformer file per domain, and it is the only place server field names appear.**
Components never see the server's shape. Then a rename on the server is a change to one file
rather than a search across the whole client.

**Request payloads are the exception.** They go straight out, so they keep the server's naming.
Build them in one function so that stays contained.

### 3f. Documentation as the contract

If your framework generates API documentation from your types, that is your contract document and
it is free. Two things make it worth reading:

- **Give every endpoint a summary and every field a description.** They cost a line each and they
  are what somebody reads at 2am.
- **Generating the schema is also your best boot test.** → [`testing.md`](testing.md) §3a

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Versioning | a path prefix, a header, or none | | |
| What the version means | "we will never break within v1", or just a namespace | | |
| Do we support two versions at once? | | | |
| Unknown query params | ignore, or reject | | |
| Field naming on the wire | snake_case, or camelCase | | |
| Where conversion happens | one transformer per domain | | |
| Deprecation | a header, a sunset date, or a message in the changelog | | |
| Is there a published changelog? | | | |

Row 2 is the one that matters and the one nobody answers. A `/v1` prefix with no rule about what
may change inside it is decoration. **For an internal system, "it is a namespace and we ship both
halves together" is a perfectly good answer.** Write it down, so nobody assumes the prefix
promises stability it does not.

Row 3: if the answer is ever yes, the cost is that every change has to work on both versions
until the old one is retired. Avoid it as long as you can.

---

## 5. Inventory

### Version and prefix

| Fact | Value |
|---|---|
| Prefix | |
| What it promises | |
| Versions live | |

### Shared response shapes

The ones that many endpoints use, and that are therefore expensive to change.

| Shape | Used by | Pinned by a test? |
|---|---|---|
| | | |

### Breaking changes made

| Date | What | How it was rolled out |
|---|---|---|
| | | |

### Known gaps

---

## 6. New-endpoint checklist

1. Give it a summary. Give every field a description.
2. Use the shared list envelope and the shared error shape rather than inventing new ones.
3. Decide whether unknown params are ignored or rejected, once, in the shared base.
4. On the client, add the transformer, and coerce every enum through the fallback helper.
5. If it changes an existing shape, check §3a first, and plan the sequence.
6. If it requires something new from the client, ship both halves together.

---

## 7. How to re-check this doc

```bash
# Endpoints with no summary. These are the ones nobody can read at 2am.
python -c "
from app.core.main import app
s = app.openapi()
missing = [(p, m) for p, ops in s['paths'].items() for m, op in ops.items()
           if not op.get('summary')]
print(len(missing)); [print(*x) for x in missing[:30]]"
```

```bash
# Snapshot the schema and diff it on every change. This is the single most useful
# thing in this file. Commit the snapshot.
python -c "
import json
from app.core.main import app
print(json.dumps(app.openapi(), indent=2, sort_keys=True))" > openapi.snapshot.json
git diff --stat openapi.snapshot.json
```

```bash
# Client: raw enum casts with no fallback. Read every hit.
grep -rn "as [A-Z][A-Za-z]*Status\|as [A-Z][A-Za-z]*Type" src/lib/*/transformers.ts
```

```bash
# Client: server field names outside the transformer files. Expect zero.
grep -rn "\bcreated_at\b\|\bis_deleted\b\|\btenant_id\b" src/components/
```
