# Module Anatomy & Placement

> Read this before you create a module, a folder or a helper, and before you split a file that
> got big.
>
> **Status in this project:** in force from day 1
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

Two questions come up constantly and both get answered badly under time pressure. *Where does
this code go?* and *is this big enough to be its own module?*

Answered badly, you get a `core/` folder full of business rules, three folders called `utils`,
`helpers` and `common` that nobody can tell apart, and modules split so finely that one change
touches five of them.

The fix is not taste. It is two tests you can apply to any file in about ten seconds.

**The golden rule: what a file *is* decides where it goes. Its name never does.** Calling a tax
engine `money.py` does not make it generic. It makes it mislabelled, and mislabelled code gets
misplaced.

---

## 2. The rules

- **Every business module has the same file layout** (§3a). Same names, same order, every time.
  A developer who has read one module can read any of them.
- **The dependency direction is one way**: routes to service to data-access to models. Never the
  other way.
- **`core/` holds only portable infrastructure.** It must pass both gates in §3b.
- **No `utils`, `helpers`, `common`, `shared`, `misc` or `stuff` folder.** If you are reaching
  for one, you have not yet worked out what the thing is. Name the concept.
- **The Rule of Three.** Extract a shared abstraction only after three real duplicated uses. Two
  is a coincidence.
- **A new top-level module needs a reason** (§3c). The default answer is no.
- **Split a file when it stops being readable, not at a line count**, and split along a seam it
  already has.
- **A package's public import surface never changes when you split it.** The init file re-exports
  the same names.
- **Package init files stay light.** No heavy imports and nothing built at import time.

---

## 3. The traps

### 3a. The anatomy, and why the order matters

| File | Owns | Never does |
|---|---|---|
| `models` | the tables | import a service |
| `enums` | the status values and the allowed-transition map | |
| `schemas` | the request and response shapes | accept a server-controlled field |
| `list_params` | filters, search, and a closed set of sortable columns | |
| `exceptions` | every refusal this module can make | |
| `crud` | query building, flush-only writes | commit or roll back |
| `service` | **the transaction**, stamping, numbering, guards, audit | import from routes |
| `routes` | HTTP shape, the permission gate | touch the session or build a query |
| `dependencies` | wiring, and the declared list of outward edges | hold business logic |
| `__init__` | almost nothing | import anything heavy |

Build them in that order. Each needs the one before it. Writing `exceptions` before `crud` is the
one people skip, and skipping it is how inline error strings get scattered through a module.

### 3b. The `core/` gate

Two tests. A file may live in `core/` only if it passes **both**.

1. **Portability.** Would it drop into a completely unrelated project unchanged? If no, it is not
   core.
2. **Vocabulary.** Does it name any concept from your business? Invoice, patient, stock, tax,
   vendor, shipment? If yes, it is not core.

Allowed in core: the app factory, settings, the database session, the base model, generic list
schemas, exception handlers, middleware, logging, rate limiting, a generic data-access base, the
cache client, the storage client, the job queue setup.

**The one allowed exception** is the wiring file. The file that registers routers and the file
that imports every model for migrations may import business modules, because that is what they
are for. Wiring only, never logic.

> **The real story this gate came from.** A money and tax engine lived at `core/money/`. Because
> the name looked generic, both developers and AI assistants read it as core material, and the
> boundary kept eroding from there. A SQL wildcard escaper sat in `core/utils/text.py` as a "text
> util" for the same reason. Both got moved. The rules exist so it does not happen again.

### 3c. When a new top-level module is justified

Only one of these three:

- a **distinct bounded context**, with its own vocabulary, its own lifecycle and its own owner
- a genuinely **reusable capability** that would work in a different product
- a **shared kernel** of business primitives that two or more modules already depend on, with no
  HTTP surface and no single owner

It is **not** justified to hold shared helpers, to wrap a single file, or to prepare for
something you plan to build later. When in doubt, put it inside the most relevant existing
module. Merging later is much cheaper than un-splitting.

### 3d. Split versus keep together

Default to fewer, bigger, cohesive modules.

**Do not split** when the two things change together, share a transaction, share an invariant,
or one is meaningless without the other.

**Split only** when they have separate lifecycles, different vocabulary, a different owner and
genuinely little coupling.

### 3e. Splitting a file that got big

Around 600 lines a layer file stops being readable. Turn it into a package. The contract does not
change when you do. A `crud/` package is still flush-only. A `routes/` package is still thin.

| Package | Siblings are | The init file re-exports |
|---|---|---|
| `service/` | one orchestrator, plus collaborator files of free functions taking the service as the first argument | the class **and** its instance |
| `crud/` | one file **per entity**, each owning its own search and sort column lists | every class **and** every instance |
| `routes/` | one file **per entity**, each declaring its own router with the original prefix | every router |

A `service/` needs an orchestrator because a service is one class that grew. `crud/` and `routes/`
do not. Those only get big when they hold several *independent* entities, so the split is a plain
move along class boundaries.

**A helper shared by several siblings gets its own sibling, named for the concept.** Not a
`helpers.py` bucket. And not `core/` just because it looks generic. The owning module keeps it
until a second module actually needs it.

### 3f. The circular import trap

Two modules that need each other will deadlock at import time if both import at the top of the
file.

The fix is to import the other module **inside the function that uses it**. That defers the
import to call time. It looks untidy and it is load-bearing. Put a comment on it saying so, or
somebody will move it to the top "for tidiness" and break the boot.

The same trap is why package init files stay light. An init that imports the service, which
imports another module's service, which imports back, fails on a half-initialised module with an
error message that names none of the files involved.

### 3g. Declared edges, so the coupling stays visible

Because those imports are scattered through a module, nothing shows you the module's real
dependencies. So each module's `dependencies` file declares them in one place:

```python
OUTWARD_EDGES: tuple[str, ...] = ("branch", "clients", "iam", "work_orders")
```

A test recomputes that list from the source and fails when the two disagree, **in either
direction**. Reach into a new module and the test tells you to declare it. Drop the last import
and it tells you to remove it.

Count only imports of another module's *behaviour*, meaning its service or data-access layer.
Importing its models, schemas or enums is sharing a type, not depending on behaviour.

This is 80 lines of test and it is the single best structural tool in the kit. Write it early.

### 3h. Domain groups

When several modules form one business domain, nest them: `app/crm/leads`, `app/crm/proposals`.

Each sub-module keeps the **full** anatomy and is self-contained. A group is a code grouping, not
a merge. The group's own init file stays empty apart from a docstring.

**Nesting is a pure code move. Table names, URL paths and permission strings do not gain the
group prefix.** If they do, you have made a breaking change out of a tidy-up.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Layout | flat modules, or domain groups | | |
| Layer file names | `crud`/`service`/`routes`, or `repository`/`domain`/`api` | | |
| Where the shared business kernel lives | one module, or per-concept modules | | |
| Split threshold | a line count, or purely readability | | |
| Are edges declared and tested? | yes, or trust review | | |

On the third row: a single module named `common` is the easy answer and it is also the smell word
from §2. Naming it per concept costs nothing at the start and is annoying to fix later.

---

## 5. Inventory

### The modules and what layer each is

| Module | Layer (core / capability / kernel / domain) | Notes |
|---|---|---|
| | | |

### Where it is deliberately NOT followed

| Exception | Why |
|---|---|
| | |

### Known gaps

---

## 6. New-module checklist

1. **Check it deserves to be a module** against §3c. Usually it does not, and it belongs inside
   an existing one.
2. Build the files in the §3a order.
3. Keep the init file light.
4. Declare the outward edges, even if the tuple is empty.
5. Register the router, the permissions and the models. Missing any one of those fails silently
   in a different way each time.
6. Do not add an abstraction for a second module you have not written yet.

---

## 7. How to re-check this doc

```bash
# Nothing in core may name a business concept. Replace the word list with your own
# domain vocabulary. Expect hits only in the wiring files.
grep -rniE "invoice|vendor|patient|stock|tax|shipment|tenant_name" app/core/ --include="*.py"
```

```bash
# Bucket folders. Expect zero.
find app -type d \( -name utils -o -name helpers -o -name common -o -name shared -o -name misc \)
```

```bash
# Layer files past the split threshold.
find app -name "crud.py" -o -name "service.py" -o -name "routes.py" | xargs wc -l | sort -rn | head -20
```

```bash
# Reversed-direction imports. A data-access or model file importing a service. Expect zero.
grep -rn --include="crud.py" --include="models.py" "import service\|\.service import" app/
```

```bash
# The edge declaration test.
python -m pytest app/test_module_edges.py -q
```
