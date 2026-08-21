# Cross-Cutting Concerns — Index

**Last verified against the code: 21 August 2026.**

A **concern** is a topic that runs across every module. Caching, tenancy, audit logging, money.
A **module guide** tells you how one module behaves. These files tell you how one *topic* works
everywhere.

**Read the concern doc before you add the thing, not after you break it.** Each one ends with the
commands that rebuild its inventory. If a count there disagrees with the document, the document
is stale. That is the only defence these files have against rot.

---

## Read this when you are about to…

### The spine — you will touch these on almost every change

| Concern | Read it when you are about to… |
|---|---|
| [`module-anatomy-and-placement.md`](module-anatomy-and-placement.md) | create a module, a folder or a helper, or split a file that got big |
| [`transactions-and-layering.md`](transactions-and-layering.md) | write any service method that changes anything |
| [`tenancy-and-scoping.md`](tenancy-and-scoping.md) | write any query at all, in a multi-tenant system |
| [`permissions.md`](permissions.md) | add a route, or a "mine versus everyone's" distinction |
| [`error-handling.md`](error-handling.md) | raise anything, anywhere |
| [`pagination-and-search.md`](pagination-and-search.md) | build a list endpoint, a report or an embedded child collection |

### Data correctness

| Concern | Read it when you are about to… |
|---|---|
| [`concurrency.md`](concurrency.md) | handle two people editing the same record |
| [`state-machines.md`](state-machines.md) | add a status field |
| [`money-and-quantities.md`](money-and-quantities.md) | store or display a number a person will read |
| [`dates-and-timezones.md`](dates-and-timezones.md) | add any date or timestamp column |
| [`snapshots-vs-live.md`](snapshots-vs-live.md) | add a document, or point at master data from a record that gets issued |
| [`document-numbering.md`](document-numbering.md) | add a human-readable code |
| [`soft-delete-and-deletion.md`](soft-delete-and-deletion.md) | delete anything, or add a unique constraint |

### Things around the edge of the request

| Concern | Read it when you are about to… |
|---|---|
| [`caching.md`](caching.md) | add a cache, change a lifetime, or debug stale data |
| [`background-jobs.md`](background-jobs.md) | move work off the request thread |
| [`object-storage.md`](object-storage.md) | upload, download or attach a file |
| [`notifications.md`](notifications.md) | tell somebody something happened |
| [`analytics.md`](analytics.md) | add a summary panel, a report or any aggregate number |
| [`import-and-export.md`](import-and-export.md) | accept a spreadsheet, or produce one |

### Access and the front door

| Concern | Read it when you are about to… |
|---|---|
| [`security.md`](security.md) | touch auth, tokens, sessions, or anything deciding who can do what |
| [`rate-limiting.md`](rate-limiting.md) | add a route that is not behind a permission |
| [`reference-data-and-pickers.md`](reference-data-and-pickers.md) | add a dropdown, a filter, or a column showing another module's name |
| [`audit-logging.md`](audit-logging.md) | record who did what, or wonder why a row is missing |

### Running the thing

| Concern | Read it when you are about to… |
|---|---|
| [`configuration-and-secrets.md`](configuration-and-secrets.md) | add a setting, a flag or a secret |
| [`migrations.md`](migrations.md) | change the schema |
| [`seeding-and-bootstrap.md`](seeding-and-bootstrap.md) | add starter data, a role or a permission |
| [`testing.md`](testing.md) | write a test, or wonder why the suite went green and the app died |
| [`observability.md`](observability.md) | log something, or work out what happened in production |
| [`api-contract-and-versioning.md`](api-contract-and-versioning.md) | change the shape of a response |
| [`frontend-contract.md`](frontend-contract.md) | build the client half of anything above |

---

## Which of these does a new project actually need?

Not all of them. Delete the ones that do not apply. A doc describing a mechanism you did not
build is worse than no doc, because someone will follow it.

**Every project, from day one:**

`module-anatomy-and-placement` · `transactions-and-layering` · `permissions` · `error-handling` ·
`pagination-and-search` · `dates-and-timezones` · `configuration-and-secrets` · `migrations` ·
`testing` · `security` · `observability`

**Only if the thing exists:**

| Concern | Skip it when |
|---|---|
| `tenancy-and-scoping` | one tenant, and you are certain that will not change |
| `money-and-quantities` | no money and no decimal quantities anywhere |
| `document-numbering` | nothing is referred to by a code a person reads aloud |
| `snapshots-vs-live` | you never issue a document that has to stay fixed |
| `concurrency` | genuinely single-user, or every write is append-only |
| `state-machines` | no status field anywhere. Check again, there usually is one |
| `caching` | you have not added a cache yet. **This is the normal case.** Keep the doc anyway, so the rules are there when someone reaches for one |
| `background-jobs` | nothing runs outside the request yet |
| `object-storage` | no file uploads |
| `notifications` | nobody gets told anything |
| `analytics` | no summary panels or reports yet |
| `import-and-export` | no spreadsheets in or out |
| `reference-data-and-pickers` | no forms that pick another module's record |
| `rate-limiting` | you have no unauthenticated routes. You have at least login |
| `soft-delete-and-deletion` | you hard-delete everything and mean it |

---

## How these relate to your other documents

Same topic, four different jobs. Keeping them apart is what stops one topic having five
half-answers.

| Layer | Holds | Changes when |
|---|---|---|
| `CLAUDE.md` | The rule in two lines, plus a link here | Rarely. It has to stay short enough to read in full |
| `concerns/<topic>.md` | Rules, traps, decisions, inventory, gaps, checklist | Whenever the code does |
| `adr/<n>.md` | Why we decided this, on that date | Never. It is a dated record |
| `session-handoff/*.md` | What happened in one piece of work, and what was left undone | Never. Also a dated record |
| `<module>/guide.md` | How one module behaves for a user | When that module's behaviour does |

**The rule that keeps them in sync:** when a handoff establishes a lasting cross-cutting fact,
copy it into the concern doc **in the same change**. The handoff keeps the reasoning. The concern
doc holds what is true now.

---

## Writing a new one

Copy [`../templates/_CONCERN_TEMPLATE.md`](../templates/_CONCERN_TEMPLATE.md). Keep all seven
sections, in order.

The two that carry the weight are **§3 (the traps)**, which is the part nobody can work out for
themselves, and **§7 (how to re-check)**, which is what lets a reader trust a document they did
not write.

The third most valuable is **§5's second table, the deliberate exceptions**. Without it the next
person "fixes" something you left out on purpose.
