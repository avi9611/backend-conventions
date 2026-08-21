# Recommendations

What I added on top of Phoenix, and the Phoenix decisions I would make differently on a new
project.

**Last verified against the code: 21 August 2026.** (Phoenix backend, at that date.)

---

## Part 1 — What I added

Phoenix has 21 concern docs. This kit has 30. Nine are new, and all nine cover something Phoenix
does in practice and never wrote down.

| New doc | Why it earns a file |
|---|---|
| [`module-anatomy-and-placement.md`](concerns/module-anatomy-and-placement.md) | Phoenix has this, split across `CLAUDE.md` §1, `MODULE_STRUCTURE.md` and `PROJECT_CONVENTIONS.md` §2 and §5. Three files, and the third contradicts the first about whether nested groups are allowed. One file. |
| [`configuration-and-secrets.md`](concerns/configuration-and-secrets.md) | The "safe in dev, dangerous in production" pattern shows up five separate times in Phoenix and is documented as an aside each time. It is one pattern and it deserves one page with a startup assertion. |
| [`seeding-and-bootstrap.md`](concerns/seeding-and-bootstrap.md) | The additive-seed trap costs an hour every time somebody meets it. Phoenix mentions it in three files as a warning and never as a rule. |
| [`testing.md`](concerns/testing.md) | Phoenix's testing practice is genuinely good and entirely undocumented. The five guard tests are the highest-value thing in this kit and they were scattered across two test files and a `CLAUDE.md` aside. |
| [`observability.md`](concerns/observability.md) | The real gap. Phoenix has a logger and no rules. Everything else in the set prevents bugs. This one is about the ones that get through, and it is the file you need at 2am. |
| [`api-contract-and-versioning.md`](concerns/api-contract-and-versioning.md) | Phoenix has a `/v1` prefix and no rule about what may change behind it. For an internal system "it is a namespace" is a fine answer, and it needs saying. |
| [`soft-delete-and-deletion.md`](concerns/soft-delete-and-deletion.md) | Phoenix deliberately does not give this a file and folds it into tenancy. The partial-unique-index trap alone justifies one. |
| [`import-and-export.md`](concerns/import-and-export.md) | Phoenix does both, in HRM, and documents neither. Formula injection is a real hole and a one-line fix. |
| [`frontend-contract.md`](concerns/frontend-contract.md) | Merges Phoenix's frontend guardrail with its unsaved-work concern, keeping only the parts where the backend's shape decides the client's behaviour. A backend developer needs those and not the rest. |

I also moved dates and timezones into the concerns folder. In Phoenix it lives next to the code as
`app/core/utils/DATETIME.md`, which is a good file in a place where a new developer will not find
it before they need it.

### The structural change to every doc

Phoenix's docs answer questions that were settled years ago and record only the answer. A new
project has to answer them, so **the question is the useful part**.

Every doc in this kit has a **§4 Decisions this project must make**: a table of the real forks in
the road, with the trade-off spelled out and a blank column for your answer. That is the main
thing that makes the folder portable.

The other structural change: §5 Inventory starts **empty**, with the headers in place. That is
correct, not incomplete. A doc that describes a mechanism you did not build is worse than no doc.

---

## Part 2 — The five things I would build on day 1

Ordered by value per hour spent. None of these is more than a day.

### 1. The five guard tests

→ [`testing.md`](concerns/testing.md) §3a

The app boots and the schema builds. No duplicate paths. Every route gated except a written
allow-list. Shared shapes pinned. Module edges declared and checked.

Phoenix wrote these after a release where **445 tests passed and the server died on boot**. They
are about 400 lines in total and they close a class of failure that review cannot see. Write them
before the second module, not after the first incident.

### 2. Seed drift detection

→ [`seeding-and-bootstrap.md`](concerns/seeding-and-bootstrap.md) §3a

The seeder does not remove anything, but it **reports** at startup what is in the database and not
in the catalogue. Ten lines. It turns an hour of "why does this role still have that permission"
into a log line.

Phoenix's answer is to document the symptom, which is the honest fallback and much worse than the
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

### 4. An OpenAPI schema snapshot in the repo

→ [`api-contract-and-versioning.md`](concerns/api-contract-and-versioning.md) §7

Generate the schema, commit it, and diff it on every change. Every contract break then shows up in
the pull request as a diff. It costs one script and it is the only thing that makes §3a of that
file enforceable rather than advisory.

### 5. Error tracking

→ [`observability.md`](concerns/observability.md) §4

For a small team this is the highest-value item on the whole observability list. It turns
"somebody reported something" into a grouped, counted stack trace with the request context
attached. It pays for itself in the first month.

---

## Part 3 — Six Phoenix decisions I would revisit

Not criticism. Every one of these was a reasonable call at the time, and each is written up in the
relevant concern doc. These are the ones where a new project has a cheaper option because it has
not started yet.

### 1. Settle "mine only" before writing any code

→ [`permissions.md`](concerns/permissions.md) §3a

Phoenix's own-scope rule narrows lists and not single-record reads. So a record reassigned to
somebody else drops off the previous owner's list and their saved link still opens **and edits**
it. Four modules are still on the old shape, years later, and the documentation and the UI promise
something the API does not keep.

The fix is not hard. What made it stick is that nobody answered the underlying question:
**is "mine only" a confidentiality boundary, or a UI default?** Answer it in Part 1 of the
checklist and the implementation follows.

The Phoenix module that *did* fix it did something worth copying exactly: it **overrides the
inherited tenant-only helper so it raises**, so a future method physically cannot reach for the
house helper by accident.

### 2. Build the audit outbox on day 1, if the trail is a compliance requirement

→ [`audit-logging.md`](concerns/audit-logging.md) §3a

Phoenix dispatches audit entries to a queue, fire-and-forget, after the commit. If the queue is
unreachable, the business transaction commits and **no audit row is ever written**. No dead
letter, no reconciliation. Phoenix lists this as the single most valuable gap left open.

For a system where the trail is a convenience, fire-and-forget is right. For an audited one, an
outbox is a table and about thirty lines, and it makes the log commit or roll back with the thing
it describes. You cannot retrofit a trail you did not write.

### 3. Put the tenant in the client's cache keys immediately

→ [`caching.md`](concerns/caching.md) §3e

Phoenix's query keys are not tenant-scoped, so both tenants share one cache entry. The visible
symptom was fixed by removing cached queries on switch, plus a full page reload. That works, and
correctness now depends on remembering to do it.

Threading the tenant into every key factory is mechanical and it is about thirty files once the
application exists. At the start it is zero.

### 4. Name the shared kernel for its concept, not `common`

→ [`module-anatomy-and-placement.md`](concerns/module-anatomy-and-placement.md) §2

Phoenix's own placement rules list `common` as a smell word and block new ones. Phoenix has
`app/common`. The contents are correctly classified and well named per file. Only the folder is
wrong, and moving it now needs a compatibility shim and a caller migration.

Naming it per concept on day 1 costs nothing.

### 5. Mark every foreign-key cycle "alter afterwards", from the first one

→ [`migrations.md`](concerns/migrations.md) §3d

Phoenix has three cycles. The newest carries the flag and regenerates cleanly. The two older ones
do not, so a from-scratch regeneration of that schema needs manual reordering, permanently.

The flag is one keyword. Use it on every cycle you create.

### 6. Give exports their own permission

→ [`import-and-export.md`](concerns/import-and-export.md) §3f

Phoenix has an export permission declared and gating nothing. Export is treated as the same act as
reading the list.

It is one permission and it is the difference between "who may look at this" and "who may take a
copy of this on their laptop".

---

## Part 4 — Three Phoenix decisions I would copy exactly

Worth naming, because they are unusual and they are right.

**The options endpoint contract.**
→ [`reference-data-and-pickers.md`](concerns/reference-data-and-pickers.md)

A separate, deliberately tiny, ungated endpoint per referenceable resource. Its safety comes from
the narrowness of the shape rather than from a gate, and a test pins the field set so widening it
has to be deliberate. It closed 14 real defects across 6 of 10 roles. Most teams either gate the
picker and live with empty required fields, or open the register up entirely.

**Optimistic locking on the row's own updated timestamp.**
→ [`concurrency.md`](concerns/concurrency.md) §3c

No new column, no migration, no schema change, because every response already carries the value.
Callers echo back what they were given, and a list row is as good a source as a detail read. And
refusing a request with no version, rather than allowing it, is the detail that makes it hold.

**"Never truncate silently" as the rule, rather than "paginate everything".**
→ [`pagination-and-search.md`](concerns/pagination-and-search.md)

It is the version of the rule that survives contact with reports, dashboards and financial totals,
where a pager reads badly or is simply wrong. A cap plus the true total plus a visible notice is a
better answer than either extreme.

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
