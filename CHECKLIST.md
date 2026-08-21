# The Checklist

Every convention in this kit, as things to tick off.

**Last verified against the code: 21 August 2026.**

Nine parts. Part 1 is done once. Parts 2 to 7 are done every time you build the thing they name.
Part 8 is the review gate. Part 9 is before you go live.

Each item links to the concern doc that explains it. **Read the doc before you add the thing, not
after you break it.**

- [Part 1 — Decisions to make before any code](#part-1--decisions-to-make-before-any-code)
- [Part 2 — The skeleton](#part-2--the-skeleton)
- [Part 3 — Every module](#part-3--every-module)
- [Part 4 — Every route](#part-4--every-route)
- [Part 5 — Every mutation](#part-5--every-mutation)
- [Part 6 — Every list](#part-6--every-list)
- [Part 7 — Every document, file and number](#part-7--every-document-file-and-number)
- [Part 8 — Before you merge](#part-8--before-you-merge)
- [Part 9 — Before you go live](#part-9--before-you-go-live)
- [The anti-pattern list](#the-anti-pattern-list)

---

## Part 1 — Decisions to make before any code

Twenty questions. Answer them in writing, in an ADR each, before the first module. All of them
are cheap now. Most get very expensive once there is data.

### Identity and shape of a row

- [ ] **Primary keys.** UUID or bigint? UUID costs index size and readability. Bigint leaks how
      many rows you have and makes ids guessable. Pick one and never mix.
- [ ] **Timestamps.** Every table gets `created_at` and `updated_at`, stored in UTC, with a
      timezone-aware column type. → [`dates-and-timezones.md`](concerns/dates-and-timezones.md)
- [ ] **Authorship.** Does every business row record who created and last changed it? If yes,
      that is a mixin, not a per-table decision.
- [ ] **Soft delete.** Which tables get it, and which do not. Decide the rule now, because
      soft delete plus a unique constraint is a trap.
      → [`soft-delete-and-deletion.md`](concerns/soft-delete-and-deletion.md)
- [ ] **Mixins over a god base class.** Compose per table. Do not force tenancy or soft delete
      onto config, permission or append-only tables.

### Tenancy

- [ ] **Is this system multi-tenant?** By what? Branch, company, workspace, customer?
      → [`tenancy-and-scoping.md`](concerns/tenancy-and-scoping.md)
- [ ] **If yes: which tables are scoped and which are deliberately shared?** "Scope everything"
      is wrong. Write the list.
- [ ] **Can a user cross tenants?** If yes, the same query behaves differently for different
      people, which is the hardest part of the whole feature.
- [ ] **Does the database enforce it, or does every query?** Row-level security in Postgres, or
      application-side scoping. If application-side, one missed query is a silent leak.

### Money, numbers and time

- [ ] **Money type.** Decimal with a fixed scale. Never float. Always stored with its currency.
      → [`money-and-quantities.md`](concerns/money-and-quantities.md)
- [ ] **Quantity type and its scale.** Decide the decimal places once.
- [ ] **Is there a third numeric type?** A measurement, a coordinate, a scientific reading.
      Trailing zeros mean something on those and nothing on a quantity.
- [ ] **Whose calendar decides what day a record books on?** The server's, the tenant's, or the
      viewer's? Never the viewer's.
      → [`dates-and-timezones.md`](concerns/dates-and-timezones.md)

### Access

- [ ] **Permission model.** Permission strings held by roles, held by users. Never check a role
      name in business logic. → [`permissions.md`](concerns/permissions.md)
- [ ] **Is there a row-level "mine versus everyone's" distinction?** If yes, decide now whether
      it is a confidentiality boundary or a UI default. Left unsettled, this gap stays open for
      years.
- [ ] **Who bypasses everything?** A superuser flag, a platform role, or nobody.
- [ ] **Where does the token live?** An httpOnly cookie set by a server you control beats
      anything the browser's JavaScript can read. → [`security.md`](concerns/security.md)
- [ ] **Is there self-service registration?** If not, say so out loud, because someone will add
      it back.

### Records and documents

- [ ] **Which records get a human-readable number?** What is the format, and does it reset each
      year? → [`document-numbering.md`](concerns/document-numbering.md)
- [ ] **Which records, once issued, must never change what they say?** That is the snapshot
      list, and it is a per-field decision, not a per-table one.
      → [`snapshots-vs-live.md`](concerns/snapshots-vs-live.md)
- [ ] **What is audited, and is the audit allowed to fail?** If the audit trail is a compliance
      requirement, fire-and-forget is not good enough on its own.
      → [`audit-logging.md`](concerns/audit-logging.md)

### Infrastructure

- [ ] **Cache: do you need one at all?** Most new projects do not. Adding one costs you an
      invalidation contract on every write, forever. → [`caching.md`](concerns/caching.md)
- [ ] **Background jobs: what genuinely cannot happen in the request?** Start with the answer
      "nothing" and make each case argue for itself.
      → [`background-jobs.md`](concerns/background-jobs.md)
- [ ] **File storage.** One service, one client, presigned URLs, and an attachment row for every
      object. → [`object-storage.md`](concerns/object-storage.md)

---

## Part 2 — The skeleton

Build this once, before the first business module.

### Layout

- [ ] `app/core/` holds portable infrastructure and **nothing that names a business concept**.
      Two tests: would it drop into an unrelated project unchanged, and does it use a word from
      your domain? → [`module-anatomy-and-placement.md`](concerns/module-anatomy-and-placement.md)
- [ ] One package per business module. Every module has the same file layout.
- [ ] No `utils/`, `helpers/`, `common/`, `shared/` or `misc/` folder. If you are reaching for
      one, you have not yet found what the thing actually is.
- [ ] The only allowed `core` to business import is the wiring file that registers routers and
      models. Wiring only, never logic.

### The pieces

- [ ] **Settings** loaded from environment variables into a typed object. Required secrets have
      no default, so a missing one fails at boot rather than at 3am.
      → [`configuration-and-secrets.md`](concerns/configuration-and-secrets.md)
- [ ] **Database session factory.** One place. Decide `expire_on_commit` now and write down
      which way and why. → [`transactions-and-layering.md`](concerns/transactions-and-layering.md)
- [ ] **Base model plus mixins.**
- [ ] **Generic list helpers**: pagination, sorting with an allow-list, and an escaped search
      helper. Written once, used by every module.
      → [`pagination-and-search.md`](concerns/pagination-and-search.md)
- [ ] **Global exception handlers** that turn framework errors into clean JSON, including a
      catch-all so nothing ever leaks a stack trace.
      → [`error-handling.md`](concerns/error-handling.md)
- [ ] **Middleware**: CORS, compression, trusted hosts, request timing, security headers.
- [ ] **Logging** with a single logger factory. Structured, with request ids.
      → [`observability.md`](concerns/observability.md)
- [ ] **Health endpoint** that checks the database and returns quickly.
- [ ] **API docs** are behind auth or switched off in production.
- [ ] **Migration tooling** wired, with a single file that imports every model so autogenerate
      can see them. → [`migrations.md`](concerns/migrations.md)
- [ ] **Seed script** that is idempotent and safe to re-run.
      → [`seeding-and-bootstrap.md`](concerns/seeding-and-bootstrap.md)

### Guard tests — write these on day 1, not day 300

These are the cheapest quality tooling you will ever write. Each one is under 100 lines and each
catches a class of bug that review misses.

- [ ] **The app boots.** A test that imports the app and builds the full OpenAPI schema. Without
      it, a route file with a bad import passes the whole suite and kills the server on start.
      This is real: 445 tests passed and the server died with a `NameError`.
      → [`testing.md`](concerns/testing.md)
- [ ] **No duplicate route paths.** Two routes on the same method and path means one is dead.
- [ ] **Every route is permission-gated**, except an explicit allow-list where each entry
      carries a written reason. Adding to that list is a security decision.
      → [`permissions.md`](concerns/permissions.md)
- [ ] **Module dependency edges are declared.** Each module writes down which other modules it
      reaches into. A test recomputes it from the source and fails when they disagree, in either
      direction. → [`module-anatomy-and-placement.md`](concerns/module-anatomy-and-placement.md)
- [ ] **No write schema accepts a server-controlled field.** Walk the syntax tree, not a grep. A
      grep cannot tell a create schema from a response schema.
      → [`tenancy-and-scoping.md`](concerns/tenancy-and-scoping.md)
- [ ] **Cross-tenant isolation.** One test per module that proves a read from the wrong tenant
      returns nothing. A leak is invisible without one.

---

## Part 3 — Every module

Build the vertical slice in this order. The order matters, because each file needs the one
before it. → [`module-anatomy-and-placement.md`](concerns/module-anatomy-and-placement.md)

- [ ] 1. **models** — the tables. Compose the mixins. Money columns get a currency beside them.
- [ ] 2. **enums** — the status values and the map of which change is allowed.
      → [`state-machines.md`](concerns/state-machines.md)
- [ ] 3. **schemas** — create, update, response, detail, list. Create accepts only what a client
      may set. Update is all optional. Neither accepts tenant id, author, generated codes,
      status or assignment.
- [ ] 4. **list params** — the filters, the search field, and a sort field restricted to a
      closed set of column names.
- [ ] 5. **exceptions** — a named exception for every refusal the module can make. Write these
      *before* the CRUD layer. → [`error-handling.md`](concerns/error-handling.md)
- [ ] 6. **crud** — query building and writes. Flushes, never commits.
- [ ] 7. **service** — the business logic. Owns the one transaction.
- [ ] 8. **routes** — thin. Permission gate, request shape, call the service.
- [ ] 9. **dependencies** — the wiring, plus the declared list of modules this one reaches into.
- [ ] 10. **package init** — light. No heavy imports, or you get circular import failures at
       boot.
- [ ] 11. **tests** — against a real database.
- [ ] 12. **Register**: permissions in the catalog, router in the aggregator, models in the
       migration import file. Miss any one and the failure is silent and confusing.
- [ ] 13. **Migration**, reversible. Apply it up, then down, then up again.
- [ ] 14. **Module guide** — a plain-language document of what this module does, its rules and
       its edge cases. → [`templates/MODULE-GUIDE.md`](templates/MODULE-GUIDE.md)

### While you build it, ask each concern its question

- [ ] Is any entity here tenant-scoped? → [`tenancy-and-scoping.md`](concerns/tenancy-and-scoping.md) §6
- [ ] Does anything here get a human-readable number? → [`document-numbering.md`](concerns/document-numbering.md) §6
- [ ] Does anything here get issued and then have to stay fixed? → [`snapshots-vs-live.md`](concerns/snapshots-vs-live.md) §6
- [ ] Does another module's form need to pick one of these by id? → [`reference-data-and-pickers.md`](concerns/reference-data-and-pickers.md) §6
- [ ] Does anything here need a status? → [`state-machines.md`](concerns/state-machines.md) §6
- [ ] Does anything here fire a notification? → [`notifications.md`](concerns/notifications.md) §6
- [ ] Does anything here store a file? → [`object-storage.md`](concerns/object-storage.md) §6
- [ ] Does anything here need a summary panel or a report? → [`analytics.md`](concerns/analytics.md) §6
- [ ] Does anything here need to run outside the request? → [`background-jobs.md`](concerns/background-jobs.md) §6
- [ ] Does anything here need a cache? Almost certainly not. → [`caching.md`](concerns/caching.md) §6
- [ ] Does anything here take in or hand out a spreadsheet? → [`import-and-export.md`](concerns/import-and-export.md) §6
- [ ] Does a screen depend on how this module shapes its responses? → [`frontend-contract.md`](concerns/frontend-contract.md) §6

---

## Part 4 — Every route

- [ ] It is behind a permission check, or it is on the written allow-list with a reason.
      → [`permissions.md`](concerns/permissions.md)
- [ ] If it is not behind a permission check, it is throttled, and the throttle is keyed on
      **who is asking**, never on their IP address. Behind a proxy every request shares one
      address, so a per-IP limit is a limit on the whole company.
      → [`rate-limiting.md`](concerns/rate-limiting.md)
- [ ] Literal paths are declared **before** parameterised ones, or the parameter route swallows
      them. `/instruments/due` after `/instruments/{id}` is unreachable.
- [ ] It takes the tenant context, and reads and writes are scoped by it.
- [ ] It raises named exceptions only. No inline status codes with a message string.
- [ ] The wrong-tenant answer is **404, not 403**. A 403 confirms the record exists.
- [ ] It has a summary, and every field has a description. That is what somebody reads at 2am.
- [ ] If it changes the shape of an existing response, check what is safe to change first, and
      plan the sequence. → [`api-contract-and-versioning.md`](concerns/api-contract-and-versioning.md)
- [ ] After adding it, run the route guard tests. No other test imports the router aggregator.

---

## Part 5 — Every mutation

- [ ] **Exactly one commit**, in the service layer. The CRUD layer flushes and never commits.
      → [`transactions-and-layering.md`](concerns/transactions-and-layering.md)
- [ ] Tenant id and author are stamped **in the service**, from the request context. Never from
      the request body.
- [ ] If a status changes, it goes through the transition guard, on a dedicated endpoint. Not
      through the generic update.
- [ ] If a user submitted this edit, it carries the version it was built from. No version means
      refuse. Stale version means conflict. Never last-write-wins.
      → [`concurrency.md`](concerns/concurrency.md)
- [ ] **Lock first, then check.** A guard that reads before it locks is theatre. And the read
      after the lock must be forced to refresh, or you check the values you already had.
- [ ] If it writes child rows and then returns the parent, reload the parent the way a plain
      read would. Otherwise you can serialise stale or empty children.
- [ ] The audit entry is written **after** the commit, never inside it.
      → [`audit-logging.md`](concerns/audit-logging.md)
- [ ] If it changes something that is cached, the cache is cleared **after** the commit.
      → [`caching.md`](concerns/caching.md)
- [ ] If it needs another module to write something, it calls that module's service and tells it
      not to commit, so the whole thing stays one transaction.

---

## Part 6 — Every list

- [ ] Pick one of three shapes on purpose: paged, capped with the true total shown, or
      deliberately unbounded with a written reason.
      → [`pagination-and-search.md`](concerns/pagination-and-search.md)
- [ ] **Never truncate silently.** A cap ships with the real total and something on screen that
      says so. A cap without that is the same bug with a bigger number.
- [ ] Search goes through the shared helper that escapes wildcard characters. Never build a
      pattern by hand.
- [ ] Sorting goes through the shared helper with an allow-list. A raw column name from a query
      parameter is an injection hole.
- [ ] **Never filter in the application after the database applied a limit.** The page fills
      with rows you are about to throw away and the ones you wanted fall off the end.
- [ ] **Never total up a capped list.** Ask the database.
- [ ] Every child collection you embed in a response is bounded by something. If nothing bounds
      it, window it and give it its own paged endpoint.
- [ ] Aggregates are computed in SQL by the module that owns the table.
      → [`analytics.md`](concerns/analytics.md)
- [ ] Every clickable number on a summary panel maps to a filter that returns exactly that set.
      If no filter matches, add one. Do not approximate.

---

## Part 7 — Every document, file and number

### A human-readable number

- [ ] It comes from one shared allocator, inside the caller's transaction, so a rollback leaves
      no gap. → [`document-numbering.md`](concerns/document-numbering.md)
- [ ] The allocator uses an insert-on-conflict, not a select-for-update. A row lock takes
      nothing when the row does not exist yet, which is exactly what happens on the first
      document of each year.
- [ ] The year comes from the tenant's calendar, not from UTC.

### A generated document

- [ ] Every field it prints is decided: frozen at issue, or read live. There is no safe default.
      → [`snapshots-vs-live.md`](concerns/snapshots-vs-live.md)
- [ ] Anything read live is part of the cache key, or a change to it can never reach a reprint.
- [ ] The file is generated once and stored. A reprint serves the stored file. Regenerating on
      every download destroys the file that any shared link points at.
- [ ] Concurrent downloads of the same document are serialised, or two of them render twice.
- [ ] The download filename is the clean human name. The cache key lives in the storage path.

### An uploaded file

- [ ] It goes through one storage service. Never a second client.
      → [`object-storage.md`](concerns/object-storage.md)
- [ ] It has a row recording what it belongs to, so deleting it is an authorisation decision and
      not a filesystem operation.
- [ ] Deleting requires both the owning type and the owning id. A tenant check alone is not
      authorisation.
- [ ] Links are presigned and expire. A public bucket domain is a deployment rule, not a
      preference.

---

## Part 8 — Before you merge

- [ ] Tests pass. Quote the real numbers, like `839 passed, 1 failed`. Never write "tests pass".
      Name any failure that predates you and say how you proved it.
- [ ] The route guard tests pass.
- [ ] Nothing new landed in `core/` that names a business concept.
- [ ] No new `utils`, `helpers`, `shared` or `common` bucket.
- [ ] No new abstraction with fewer than three real uses.
- [ ] If behaviour changed, the module guide changed in the same commit.
- [ ] If a cross-cutting rule changed, its concern doc changed in the same commit, and the date
      stamp moved.
- [ ] If the change spans backend and frontend, both halves shipped together. A new required
      header or field breaks every caller that has not been updated.
      → [`api-contract-and-versioning.md`](concerns/api-contract-and-versioning.md) ·
      [`frontend-contract.md`](concerns/frontend-contract.md)
- [ ] The API schema snapshot was regenerated, and the diff is what you meant.
- [ ] If it was a real decision, a reversal, a migration, an auth change or an audit, write a
      handoff. → [`templates/SESSION-HANDOFF.md`](templates/SESSION-HANDOFF.md)
- [ ] Nothing was committed without being asked for.

---

## Part 9 — Before you go live

- [ ] Every secret comes from the environment. Nothing is in the repo.
      → [`configuration-and-secrets.md`](concerns/configuration-and-secrets.md)
- [ ] The default admin account created by any bootstrap script is gone or has a new password.
- [ ] API documentation is off, or behind authentication.
- [ ] Security response headers are set, and you know which layer sets them. Do not assume the
      proxy covers a page it never sees. → [`security.md`](concerns/security.md)
- [ ] Transport is HTTPS only, with strict transport security on in production and off in dev.
- [ ] The cache and the queue both require a password.
- [ ] Public asset domains are off for any bucket holding customer data.
- [ ] Data leaving the system is permissioned and audited. Export is not the same act as read.
      → [`import-and-export.md`](concerns/import-and-export.md)
- [ ] Log output has no passwords, tokens or personal data in it.
      → [`observability.md`](concerns/observability.md)
- [ ] Backups run, and you have restored one at least once. An untested backup is a hope.
- [ ] Migrations run as a deliberate step, not automatically on container start.
- [ ] There is an alert for the queue being down, since a dropped job is silent.
- [ ] Rate limits are on and fail open, so a cache outage does not lock everybody out.

---

## The anti-pattern list

Put this list in `CLAUDE.md` too. Each line is one rule broken. This is the version you scan a
diff against.

1. A commit or rollback in the data-access layer, or more than one commit in a mutation.
2. Trusting a tenant id or an author id from the request body.
3. A list query with no tenant scoping, or a wrong-tenant read that returns 403 instead of 404.
4. Float for money, or an amount stored with no currency beside it.
5. Filtering search results in the application, or building a LIKE pattern without escaping.
6. Sorting by a raw query parameter with no allow-list.
7. Accepting a status or an assignment through the generic update schema.
8. Returning a parent after writing its children, on the same session.
9. An unguarded route, or a role name hardcoded in business logic.
10. Feeding a dropdown from a permission-gated list endpoint, or gating an options endpoint.
11. A new database enum with no drop in the downgrade, or a model missing from the migration
    import file.
12. Heavy imports in a package init file, or relying on implicit lazy loading.
13. Awaiting the audit call, or writing audit inside the transaction.
14. Building an inline HTTP error in a service or a route instead of a named exception.
15. Interpolating a raw decimal quantity into text a person will read.
16. Re-reading a counterparty by id at print time on an already-issued document.
17. Regenerating a stored document on every download, or a cache key that misses a live read.
18. Changing a cached list without clearing the cache after the commit.
19. Taking today's date from UTC instead of the tenant's calendar.
20. Patching a module-level object by assignment in a test. It leaks into every later test.
