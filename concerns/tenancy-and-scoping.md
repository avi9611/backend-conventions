# Tenancy & Scoping

> Read this before you write any query, route or service method that touches business data.
>
> **Status in this project:** decide in Part 1 of the checklist
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

One database serving several tenants. A tenant can be a branch, a company, a workspace or a
customer account. The name changes, the problem does not.

**A user of tenant A must never see tenant B's rows.** Usually nothing in the database enforces
this. Every query enforces it itself. That is why the rules here are absolute rather than
advisory. One missing scope call is a silent cross-tenant leak, and no test catches it unless you
wrote that test on purpose.

Two things make this harder than it first looks:

- **Some data is shared across tenants on purpose** and some is not. "Scope everything" is wrong
  and will break real workflows.
- **Some users can cross tenants.** So the same query behaves differently depending on who runs
  it, which is where almost all the sharp edges live.

---

## 2. The rules

- **Every list query goes through the one scoping helper.** Not a hand-written where clause.
  One helper, so there is one place to fix.
- **A single-record read from the wrong tenant returns 404, not 403.** A 403 confirms the record
  exists, which is itself a leak.
- **Writes stamp the tenant id in the service**, from the request context. Never from the request
  body. The create and update schemas should not even accept the field.
- **If a service narrows what a single record can reach, its list queries must narrow to match**,
  or the list and the detail page disagree about what exists.
- **Cache keys carry the tenant id** wherever the data is scoped.
- **Do not force a tenant id onto config, permission or append-only tables** (§3d).
- **Every module gets a cross-tenant test.** A leak is invisible without one.

---

## 3. The traps

### 3a. The unscoped-when-unpinned trap

**Symptom.** An administrator sees everything, which is correct. Then a normal user reports
seeing another tenant's rows, once, and nobody can reproduce it.

**Why.** The scoping helper returns the query unfiltered when the caller can cross tenants and
has not picked one. That is right for shared master data and wrong for everything else. And the
first request after a fresh login often carries no tenant header yet, because the client has not
loaded it, so an administrator's first page load is always the unpinned case.

**The fix.** Be explicit about which entities may aggregate across tenants and which may never.
For the ones that may never, write a local scope that always uses the active tenant. Then write
the test.

### 3b. The list says no, the detail says yes

**Symptom.** A record is absent from the list, but opening its URL works. Reported as "the search
is broken".

**Why.** The list query is scoped and the single-record guard is not, or they use different
rules. Very easy to end up with when the single-record path goes through a shared base class and
the list does not.

**The fix.** The list predicate and the single-record predicate come from the **same function**,
written once. If a module needs a narrower rule, it overrides both together, and a test asserts
they agree.

### 3c. The one that hurts most: a shared base helper that only checks the tenant

**Symptom.** You add a "mine only" rule to a module's list. Everything looks right. Six months
later somebody notices a user can still open and edit a record that dropped off their list.

**Why.** The single-record path went through the inherited base helper, which applies the tenant
check and nothing else. Nobody noticed, because it was the *inherited* behaviour and not a line
of code anybody wrote.

**The fix, and it is worth copying exactly.** In a module with a narrower rule, **override the
inherited helper so it raises**. Then the module physically cannot reach for the house helper by
accident. Force every path through the module's own narrowing. I have seen this done for one
module and skipped for four others, and those four were still an open hole years later.

### 3d. Not everything gets a tenant id

Forcing it on the wrong tables causes its own problems.

| Not scoped | Why |
|---|---|
| Config, permission and lookup tables | Company-wide by definition. A tenant id there would fragment your catalogue per tenant |
| Append-only children of a scoped parent | Audit rows, history rows, journal lines. They are reached only through the parent, so the parent's scope already confines them. They also get no soft delete |
| Deliberately shared master data | Customers and suppliers are often shared. Physical equipment usually is not. Decide per table and write it down |

A useful test for the second row: can this row ever be reached except through its parent? If no,
it does not need its own tenant id, and adding one gives you two sources of truth that can
disagree.

### 3e. The nullable tenant id

**Symptom.** A base class that assumes a tenant id is always present cannot be used, so one
module writes its scoping by hand. That hand-written copy is then the one with the bug.

**Why.** Some config genuinely means "applies to everyone unless overridden". A tax rate is the
classic case. Null means company-wide, and the query becomes `tenant = X OR tenant IS NULL`.

**The fix.** It is a real requirement, so plan for it. Either make the base class handle a
nullable tenant, or accept that this module writes its own guard and cover it with its own test.
What you must not do is let it quietly opt out of scoping altogether, which is exactly what
happens, and it costs a real authorisation bug.

### 3f. File attachments share one namespace

**Symptom.** A user with permission to edit instruments deletes an attachment belonging to a
purchase order.

**Why.** The delete checked only that the attachment was in the caller's tenant. In a shared
attachments table that is not authorisation, it is barely a filter.

**The fix.** Deleting an attachment requires the owning entity type **and** the owning entity id,
as required arguments, so no caller can forget them.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| What is a tenant | branch, company, workspace, customer | | |
| Enforcement | database row-level security, or every query | | |
| Can a user belong to several tenants? | no, or yes with an active-tenant switcher | | |
| Can anyone see across tenants? | nobody, or a permission | | |
| How does the active tenant travel? | header, subdomain, path, token claim | | |
| Which tables are shared? | write the list | | |
| An unpinned cross-tenant user sees | everything, or their default tenant | | |
| Wrong-tenant single read returns | 404 | | |

Row 2 is the big one. Database row-level security makes leaks structurally impossible and costs
you complexity in connection handling and migrations. Application scoping is simple and one
missed query is a leak. If your data is sensitive and your team is growing, the database option
is worth the cost.

Row 5: a header is easiest to get wrong, because a client that forgets it gets the default
silently. A subdomain or a token claim cannot be forgotten. If you use a header, the first
request after login is the case to think about.

---

## 5. Inventory

### Scoped entities

| Model | Scoped? | Soft delete? | Notes |
|---|---|---|---|
| | | | |

### Where scoping is deliberately not applied

| Not scoped | Why |
|---|---|
| | |

### Known gaps

---

## 6. New-module checklist

1. **Decide whether the entity is scoped at all.** Business data, yes. Config, permissions,
   append-only children, no.
2. **Decide whether it may ever be shared across tenants.** If it can never be, override the
   single-record reach rule **and** narrow the list queries to match.
3. Every list query starts with the scoping helper.
4. The service subclasses the scoped base and sets its resource name and not-found exception.
5. Writes stamp the tenant id. The create and update schemas do not accept it.
6. Routes take the tenant context.
7. Any cache key for this data includes the tenant id.
8. **Write the cross-tenant test.** One per module, no exceptions.
9. Add the module to §5.

---

## 7. How to re-check this doc

> Paths below are examples from one tree. Adjust them to yours. What matters is the check,
> not the path. Where a count is given, it is the count **for this project**, so fill it in
> the first time you run it.

```bash
# Files that scope their list queries. A scoped module missing from this list is
# either a leak or a deliberate local scope. Know which.
grep -rln --include="*.py" "scope_to_tenant\|scope_to_branch" app/ | grep -v "test_\|context.py"
```

```bash
# Real subclasses of the scoped base. Match on the class line, not the bare name:
# a comment or a re-export mentioning it is not a subclass.
grep -rn --include="*.py" "class .*(.*ScopedService.*)" app/
```

```bash
# A write schema that accepts a tenant or author field. Use the syntax tree, not a
# grep: a grep cannot tell a Create schema from a Response schema, and a Response
# carrying the tenant id is correct.
#
# This does not always expect zero. Assigning a user TO a tenant is admin input, not
# a tenancy stamp, so the admin user schemas legitimately appear. So does a config
# row whose tenant is nullable (see 3e). List yours here, and treat anything else as
# a leak.
python3 - <<'PY'
import ast, pathlib
FORBIDDEN = ("tenant", "branch", "created_by", "company_id", "owner_id")
for p in sorted(pathlib.Path("app").rglob("schemas.py")):
    for n in ast.walk(ast.parse(p.read_text())):
        if isinstance(n, ast.ClassDef) and n.name.endswith(("Create", "Update")):
            for b in n.body:
                if isinstance(b, ast.AnnAssign) and isinstance(b.target, ast.Name) \
                   and any(f in b.target.id for f in FORBIDDEN):
                    print(f"{p}:{b.lineno}  {n.name}.{b.target.id}")
PY
```

```bash
# Modules that override the single-record reach rule. Each one must also narrow
# its list queries. Read every hit.
grep -rn --include="*.py" "_is_reachable\|_is_visible" app/ | grep -v "scoped_service.py"
```

```bash
# Every module should have a cross-tenant isolation test.
grep -rln "test_.*isolation\|test_.*cross_branch\|test_.*cross_tenant" app/ | sort
```
