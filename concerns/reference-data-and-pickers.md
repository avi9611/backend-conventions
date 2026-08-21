# Reference Data & Pickers

> Read this before you add a dropdown, a filter, or a column that shows another module's name.
>
> **Status in this project:** decide before the second module that has a form
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

**Filling in a field is not the same act as browsing the register behind it.**

You gate every route on a permission, and for a while a dropdown gets fed by the owning module's
real list endpoint. That conflates two different questions.

"May this person browse the supplier list?" and "May this person put a supplier on the purchase
request they are allowed to raise?" are not the same question. Answer both with the same
permission and you produce a form with a permanently empty required field, and no error message
explaining why.

This is not hypothetical. In Phoenix a technician who held "create purchase request" opened the
form and got a 403 on every keystroke in the supplier field. An audit across seven roles found
the same shape in **14 places across 6 of the 10 non-admin roles**.

**The fix is a second, deliberately tiny endpoint per referenceable resource.** It carries no
permission and returns an id, a label and one disambiguator. Its safety comes from the narrowness
of the shape, not from a gate. The real list endpoints are untouched and stay gated.

---

## 2. The rules

- **A picker reads the options endpoint. Never the module's list endpoint.** If you are reaching
  for the module's list hook to fill a control, stop.
- **The response is the shared options shape and nothing else.** A test enforces it.
- **The option is id, label, one sublabel, and an active flag. Do not add a fifth field.** Every
  field here is published to every authenticated user across every referenceable resource at
  once. Widening it is a security decision and the test makes you make it deliberately.
- **Never put money, contact details, tax numbers, addresses, stock levels, costs or notes on an
  option.** If the control needs one of those, it needs the gated endpoint, requested only when
  the user holds the permission.
- **Options endpoints are tenant-scoped and capped.** One shared cap, not a per-module number,
  and return a flag saying whether the cap hid anything.
- **Options endpoints never apply the "mine only" rule.** Own-scope answers "whose register am I
  browsing", which is the wrong question for a field that has to name the record already in front
  of you.
- **Narrowing the params is fine. Widening the response is not.** A status filter restricts what
  may be offered and reveals nothing.
- **Every ungated options route goes on the allow-list with a written reason.**
- **A gated options route is a bug, not a compromise.** It brings back the original problem for
  whoever lacks the gate.

---

## 3. The traps

### 3a. Pinning the value you already hold

**Symptom.** An edit form renders with the supplier field blank, even though the record has one.
Or the user types a search and the value they already picked vanishes from the control.

**Why.** The control shows a search result. The stored value is not in it, either because the
search excludes it or because that supplier has since been archived.

**The fix, on the server, not in the component.** The options endpoint takes a list of ids to pin
into the result, returned regardless of the search text and regardless of the active filter, and
sorted first. Then the client is a plain search box.

Doing it in the component means eight components each carrying the same shim, and eight chances
to get it wrong. Phoenix had exactly that, then deleted all eight.

**Pinned ids must not bypass the tenant filter, and must not bypass any narrowing predicate.**
A pinned id cannot be a way to smuggle a row into a picker that is meant to exclude it.

### 3b. The silent params bug

**Symptom.** Nothing throws. Nothing logs. The pinning feature just does nothing, and the edit
form quietly renders blank, forever.

**Why.** This one is FastAPI-specific and worth knowing. A params model declared with `Depends()`
makes list fields read as a **request body**. On a GET that means they are never populated. The
endpoint still answers 200.

**The fix.** Declare it as a query model, `Annotated[XOptionsParams, Query()]`. And write a test,
because the failure mode is invisible.

### 3c. Search columns must be narrower than the register's

**Symptom.** Somebody works out a customer's phone number by typing guesses into a dropdown and
watching which ones return a row.

**Why.** The options endpoint reused the register's search column list. The response omits the
phone number, but a search that **confirms** a value is a disclosure even when the response does
not contain it.

**The fix.** Match on the public identifier only. Name and code, not email, phone or contact
person.

### 3d. Hiding the control instead of fixing the feed

**Symptom.** A whole form section is invisible for a role that should be able to use it.

**Why.** Somebody worked around the 403 by hiding the control behind the owning module's read
permission. Now the gate hides a capability the role actually has.

**The fix.** Fix the feed, then delete the workaround. Phoenix found one of these still in place
after the picker was fixed.

### 3e. The parallel mechanism in the corner of the codebase

**Symptom.** One module has its own "active items" endpoints that do the same job, gated on that
module's read permission, returning the full response object.

**Why.** That module was built by someone else, or earlier, and solved the problem locally.

**Why it did not break yet.** Often only one seeded role holds any of that module's permissions,
and it holds all of them, so the gate never bites. **The exposure is the next custom role
somebody builds** in an access-control screen. A payroll clerk with only salary permissions gets
an empty required dropdown and no error.

**The fix.** Replace them, delete the old routes, and delete any cache that existed only to serve
them.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Options endpoints exist at all | yes, or gate pickers and accept the empty-field bug | | |
| Ungated, or gated on "logged in and in this tenant" | | | |
| The option shape | id + label + sublabel + active, or something else | | |
| Cap | one shared number, or per module | | |
| Where the label is decided | the owning module's service | | |
| How the allow-list is enforced | a test, or review | | |

Row 2: ungated does not mean anonymous. Every one of these still needs a logged-in user and a
tenant. What it drops is the *resource* permission.

Row 5 matters. The label is a business decision. "Vendor name, then code" is not something a
generic helper can choose. Keep the helper mechanical and let the module supply the label.

---

## 5. Inventory

### The options routes

| Route | Label · sublabel | Narrowing params | What it offers |
|---|---|---|---|
| | | | |

### Where an options route is deliberately not used

| Case | Why |
|---|---|
| | |

Typical entries here: a control that needs a value to *compute* with, such as a tax rate, rather
than a label. Or a query that answers "who may approve this", which needs a permission join that
does not fit the option shape. Or the module's own register page, which **is** the register and
stays gated.

### Known gaps

---

## 6. New-module checklist

1. **Does anything reference this module by id in another module's form, filter or column?** If
   no, stop. You do not need an options route.
2. Add the query to the data-access layer using the shared helper, passing your own tenant-scoped
   statement as the base. Pick the **narrowest** search columns that still let somebody find the
   row.
3. Map rows to options in the service. The label belongs here, not in the shared helper.
4. Add the route. Literal path before any id route. Query model, not a body model. No permission.
   Plain tenant context, never the own-scoped variant.
5. Add it to the allow-list with a one-line reason.
6. On the client, use the one shared picker component. Do not write a new one.
7. Run the route contract tests.

---

## 7. How to re-check this doc

```bash
# Every options route in the app. A new one means §5 is stale.
python -c "
from app.core.main import app
print(sorted(p for p in app.openapi()['paths'] if p.endswith('/options')))"
```

```bash
# The whole contract: shape, field set, tenant scope, cap, allow-list.
python -m pytest app/apis -q
```

```bash
# Client pickers still reading a gated module list. Expect zero in the shared
# picker components.
grep -rn "useVendors\|useClients\|useItems\|useUsers\b" src/components/shared/
```

```bash
# Cross-module list reads outside the shared pickers. Each hit must be either the
# module's own register page, or a gated read guarded by a permission check.
grep -rn "useVendors\|useClients\|useItems\|useUsers\b" src/components --include="*.tsx" | grep -v "components/shared/"
```
