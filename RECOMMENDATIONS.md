# Recommendations

The parts of this kit that are opinions rather than conventions.

Five things worth building on day 1. Six traps that stay open for years if you do not decide
early. Three patterns worth copying exactly. And what this kit does not cover.

**Last verified against the code: 21 August 2026.**

---

## Part 1 — The nine topics that usually go undocumented

Twenty-one of the thirty concern docs cover ground most teams eventually write down. These nine
usually do not get written, and every one of them covers something teams already do in practice.

| Doc | Why it earns a file |
|---|---|
| [`module-anatomy-and-placement.md`](concerns/module-anatomy-and-placement.md) | This normally lives split across the rules file, a structure doc and a conventions spec. Three files, and by month six they contradict each other about whether nested groups are allowed. |
| [`configuration-and-secrets.md`](concerns/configuration-and-secrets.md) | The "safe in dev, dangerous in production" pattern shows up five separate times and is documented as an aside each time. It is one pattern, and it deserves one page with a startup assertion. |
| [`seeding-and-bootstrap.md`](concerns/seeding-and-bootstrap.md) | The additive-seed trap costs an hour every time somebody meets it. It usually survives as a warning in three files and never as a rule. |
| [`testing.md`](concerns/testing.md) | Testing practice is usually good and almost never written down. The five guard tests are the highest-value thing in this kit, and they normally exist as two test files nobody points at. |
| [`observability.md`](concerns/observability.md) | The real gap. Everything else in the set prevents bugs. This one is about the ones that get through, and it is the file you need at 2am. |
| [`api-contract-and-versioning.md`](concerns/api-contract-and-versioning.md) | A `/v1` prefix with no rule about what may change behind it is decoration. For an internal system "it is a namespace" is a fine answer, and it needs saying out loud. |
| [`soft-delete-and-deletion.md`](concerns/soft-delete-and-deletion.md) | Often folded into the tenancy doc. The partial-unique-index trap alone justifies its own file. |
| [`import-and-export.md`](concerns/import-and-export.md) | Most teams build both and document neither. Formula injection is a real hole and a one-line fix. |
| [`frontend-contract.md`](concerns/frontend-contract.md) | The parts where the backend's shape decides the client's behaviour. A backend developer needs those and does not need the rest of a frontend guide. |

**Dates and timezones** is the tenth near-miss. It usually lives next to the code as a note on the
datetime helper, which is a good file in a place where a new developer will not find it before
they need it. It belongs in the concerns folder.

---

## Part 2 — The five things to build on day 1

Ordered by value per hour spent. None is more than a day.

### 1. The five guard tests

→ [`testing.md`](concerns/testing.md) §3a

The app boots and the schema builds. No duplicate paths. Every route gated except a written
allow-list. Shared response shapes pinned. Module edges declared and checked.

These get written after a release where **445 tests passed and the server died on boot**. About
400 lines in total, and they close a class of failure that review cannot see. Write them before
the second module, not after the first incident.

### 2. Seed mismatch detection

→ [`seeding-and-bootstrap.md`](concerns/seeding-and-bootstrap.md) §3a

The seeder does not remove anything, but it **reports** at startup what is in the database and
not in the catalogue. Ten lines. It turns an hour of "why does this role still have that
permission" into a log line.

The usual answer is to document the symptom, which is the honest fallback and much worse than the
detection.

### 3. A production settings assertion

→ [`configuration-and-secrets.md`](concerns/configuration-and-secrets.md) §3a

```python
if settings.ENVIRONMENT == "production":
    assert not settings.PUBLIC_ASSET_DOMAIN
    assert not settings.DOCS_ENABLED
    assert settings.CACHE_PASSWORD
```

A production build that refuses to start is a much better outcome than one that starts with a
development setting on. The pre-production checklist is the backup, not the control.

### 4. An API schema snapshot in the repo

→ [`api-contract-and-versioning.md`](concerns/api-contract-and-versioning.md) §7

Generate the schema, commit it, and diff it on every change. Every contract break then shows up in
the pull request as a diff. It costs one script, and it is the only thing that makes the
safe-versus-breaking table in that file enforceable rather than advisory.

### 5. Error tracking

→ [`observability.md`](concerns/observability.md) §4

For a small team this is the highest-value item on the whole observability list. It turns
"somebody reported something" into a grouped, counted stack trace with the request context
attached. It pays for itself in the first month.

---

## Part 3 — Six traps that stay open for years

Every one of these is cheap to settle before the first module and expensive afterwards. All six
are ones I have watched stay open in a real codebase long after everyone agreed they should be
fixed.

### 1. Settle "mine only" before writing any code

→ [`permissions.md`](concerns/permissions.md) §3a

The common shape is a row-scope rule that narrows lists and not single-record reads. So a record
reassigned to somebody else drops off the previous owner's list, and their saved link still opens
**and edits** it. The documentation and the UI then promise something the API does not keep.

The fix is not hard. What makes it stick is that nobody answered the underlying question:
**is "mine only" a confidentiality boundary, or a UI default?** Answer it in Part 1 of the
checklist and the implementation follows.

And there is one trick worth copying exactly. In a module with a narrower rule, **override the
inherited tenant-only helper so it raises**. Then a future method physically cannot reach for the
house helper by accident, which is how these holes reopen.

### 2. Build the audit outbox on day 1, if the trail is a compliance requirement

→ [`audit-logging.md`](concerns/audit-logging.md) §3a

The standard design dispatches audit entries to a queue, fire-and-forget, after the commit. If the
queue is unreachable, the business transaction commits and **no audit row is ever written**. No
dead letter, no reconciliation.

For a system where the trail is a convenience, fire-and-forget is right. For an audited one, an
outbox is a table and about thirty lines, and it makes the log commit or roll back with the thing
it describes. You cannot retrofit a trail you did not write.

### 3. Put the tenant in the client's cache keys immediately

→ [`caching.md`](concerns/caching.md) §3e

Query keys that are not tenant-scoped mean both tenants share one cache entry. The visible symptom
gets fixed by clearing cached queries on switch, plus a page reload. That works, and correctness
then depends on somebody remembering to do it.

Threading the tenant into every key factory is mechanical, and it is about thirty files once the
application exists. At the start it is zero.

### 4. Name the shared kernel for its concept, not `common`

→ [`module-anatomy-and-placement.md`](concerns/module-anatomy-and-placement.md) §2

Almost every project ends up with a module named `common` or `shared`, and almost every project's
own placement rules list those as smell words. The contents are usually correctly classified and
well named per file. Only the folder is wrong, and moving it later needs a compatibility shim and
a caller migration.

Naming it per concept on day 1 costs nothing.

### 5. Mark every foreign-key cycle "alter afterwards", from the first one

→ [`migrations.md`](concerns/migrations.md) §3d

A cycle that carries the flag regenerates cleanly. One that does not means a from-scratch
regeneration of the schema needs manual reordering, permanently.

The flag is one keyword. Use it on every cycle you create, including the first.

### 6. Give exports their own permission

→ [`import-and-export.md`](concerns/import-and-export.md) §3f

Export usually gets treated as the same act as reading the list. Sometimes there is even an export
permission declared that gates nothing.

It is one permission, and it is the difference between "who may look at this" and "who may take a
copy of this on their laptop".

---

## Part 4 — Three patterns worth copying exactly

Named because they are unusual, and because the obvious alternatives are worse.

**The options endpoint contract.**
→ [`reference-data-and-pickers.md`](concerns/reference-data-and-pickers.md)

A separate, deliberately tiny, ungated endpoint per referenceable resource. Its safety comes from
the narrowness of the shape rather than from a gate, and a test pins the field set so widening it
has to be deliberate. It closed 14 real defects across 6 of 10 roles in the system it came from.
Most teams either gate the picker and live with empty required fields, or open the register up
entirely.

**Optimistic locking on the row's own updated timestamp.**
→ [`concurrency.md`](concerns/concurrency.md) §3c

No new column, no migration, no schema change, because every response already carries the value.
Callers echo back what they were given, and a list row is as good a source as a detail read. And
refusing a request that carries no version, rather than allowing it, is the detail that makes it
hold.

**"Never truncate silently" as the rule, rather than "paginate everything".**
→ [`pagination-and-search.md`](concerns/pagination-and-search.md)

It is the version of the rule that survives contact with reports, dashboards and financial totals,
where a pager reads badly or is simply the wrong answer. A cap plus the true total plus a visible
notice beats either extreme.

---

## Part 5 — What this kit does not cover

Say what you have not built, so nobody assumes.

- **Deployment, containers and infrastructure.** Referenced in the checklist, not specified.
- **Anything multi-service.** Every rule here assumes one deployable application with one
  database. Most of them survive the move to services. The transaction rules do not.
- **Front-end architecture beyond the contract.**
  → [`frontend-contract.md`](concerns/frontend-contract.md) covers only where the backend's shape
  decides the client's behaviour.
- **Real-time.** Websockets, server-sent events, live updates. Nothing here about them.
- **Search infrastructure.** The search rules assume a database. A dedicated search engine brings
  its own concern doc.
- **Data protection and retention as a policy.** Flagged in three docs as a decision. Not
  specified, because it is legal before it is technical.
