# Permissions & Access Control

> Read this before you add a route, or a "mine versus everyone's" distinction.
>
> **Status in this project:** decide in Part 1 of the checklist
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

Every route is gated by a permission string. Roles hold permissions. Users hold roles. One
catalogue is the source of truth, and permissions are seeded from it rather than hand-assigned
per role.

Two separate axes decide who sees what. **The permission** answers "may you touch this resource
at all?" **The scope** answers "all of them, or only yours?" The second axis is where all the
sharp edges are, and most teams do not realise they have made a decision there until it bites.

---

## 2. The rules

- **Gate every route with a permission check.** One shared dependency, one format, everywhere.
- **New permissions go in the catalogue**, and are granted to the full-access roles
  automatically. Do not hand-list them per role, or the list rots.
- **Never hardcode a role name in business logic.** Check the permission. A role's contents must
  be able to change without a code change.
- **Never cache a permission check or the authenticated user.** A stale grant is a hole. A stale
  revoke means a removed permission keeps working. → [`caching.md`](caching.md)
- **A route that is not behind a permission is part of the unauthenticated front door.** It needs
  a throttle. → [`rate-limiting.md`](rate-limiting.md)
- **A dropdown is not a register read.** Do not gate a picker feed on the owning module's read
  permission. → [`reference-data-and-pickers.md`](reference-data-and-pickers.md)
- **If a permission is added or renamed, every place that names it changes in the same commit.**
  Including the client.

---

## 3. The traps

### 3a. The "mine only" rule that only applies to lists

**Symptom.** A record is reassigned to somebody else. It drops off the previous owner's list.
Their saved link still opens it, and still lets them edit it.

**Why.** The list narrows in the query. The single-record path goes through a shared helper that
checks only the tenant. Nobody wrote the narrowing there because nobody wrote that helper.

**The cost.** In practice this is not enumeration, because ids are random. The real case is
reassignment, and it happens constantly. Bulk endpoints have the same hole.

**The fix.** Decide the question first: **is "mine only" a confidentiality boundary or a UI
default?**

- Boundary. Then enforce it on the detail read, the write and the bulk paths, using the *same
  predicate* the list uses, written once.
- Default. Then grant those roles the read-all permission and delete the "own only" wording from
  the catalogue.

What you must not do is what Phoenix did, which is document and display a promise the API does
not keep. Whichever way you go, the danger sign is the same: **the list predicate and the detail
predicate written in two places.**

### 3b. The client-side permission name is a lookup table, not a string swap

**Symptom.** A button is invisible for everybody except administrators, and nobody can explain
why. No error anywhere.

**Why.** The client spells permissions differently from the server, and maps between them by
hand. One client key can require several server permissions, and often not the obvious ones. A
reports panel might need read-all rather than a reports permission, because the panel counts the
whole tenant.

**Nothing fails when that table drifts.** An entry pointing at a permission that no longer exists
just returns false, which silently hides the affordance from everyone.

**The fix.** Either use the same string on both sides, or make a test assert that every name in
the client's table exists in the server's catalogue. The second is ten lines. Do it on day 1.

### 3c. A permission missing from the catalogue is not proof it does not exist

**Symptom.** You conclude a permission is dead and delete it. Login breaks.

**Why.** More than one thing can register permissions. An auth provider, a plugin, an
optional module. They get merged at seed time.

**The fix.** Have exactly one registration path if you can. If you cannot, list the other paths
in §5 of this document, and grep them before calling a permission dead.

### 3d. Approval roles that quietly grow

**Symptom.** The person who approves customer pricing can also sign off technical work, because
both approvals landed on the same role.

**Why.** A role that already means "the approver" is the obvious place to hang the next approval.
Each individual step is reasonable.

**The fix.** Before reaching for the existing approver role, ask what the approval **attests to**.
Money is one kind of claim. A technical or safety judgement is another. If they differ, it needs
its own role. One person can hold both, and that is then a recorded decision rather than a side
effect.

**Adding a role is free. Taking a permission back needs a data migration**, because the seed only
adds.

### 3e. The additive seed

**Symptom.** Role grants that contradict the catalogue you are reading.

**Why.** The seeder only inserts what is missing. A permission granted by a half-finished edit
sticks permanently, and on a dev setup that re-seeds on every file save, it sticks after one
keystroke. → [`seeding-and-bootstrap.md`](seeding-and-bootstrap.md)

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Format | `resource:action`, or `resource.action`, or a flat name | | |
| Segments | exactly two, or a third scope segment | | |
| Row scope | a separate `read_all` action, or a scope segment, or none | | |
| Is "mine only" a boundary or a default? | **answer this before writing any code** | | |
| Who bypasses everything | nobody, a superuser flag, a platform role | | |
| Where roles are defined | a code catalogue, or database rows an admin edits | | |
| Can an admin create custom roles? | no, or yes | | |
| Client permission names | the same strings, or a mapping table with a test | | |

Row 2: a two-segment name with `read_all` as its own action is simpler than a three-segment name
with a scope. Three segments look tidier and give you a parsing rule to remember in every check.

Row 4 is the one that costs the most if you leave it. See §3a.

Row 7: if yes, then §3a's trap gets sharper. A custom role is exactly where a picker or a panel
turns out to need a permission nobody expected.
→ [`reference-data-and-pickers.md`](reference-data-and-pickers.md)

---

## 5. Inventory

### The permission catalogue

Keep the catalogue itself as the source of truth. This table records only the things a reader
cannot get from it.

| Fact | Value |
|---|---|
| Total permissions | |
| Full-access roles | |
| Other registration paths | |
| Permissions that gate no route (declared and unused) | |

### Routes that are deliberately not gated

Each entry needs a reason. Adding one is a security decision.

| Route | Why it is safe |
|---|---|
| | |

### Known gaps

---

## 6. New-route checklist

1. **Pick or add the permission.** Reuse an existing one if it fits.
2. Gate the route. Use the form that gives you the user object only if you need it.
3. **If the resource has an owner and a "mine only" role**, narrow the list, and narrow the
   single-record read, the write and the bulk paths with the same predicate.
4. Never name a role in the handler. Never cache the check.
5. If the route is not gated, throttle it and add it to the allow-list with a reason.
6. If you added or renamed a permission, update the client's mapping in the same commit.

---

## 7. How to re-check this doc

```bash
# Every route is gated. This walks the resolved dependency graph rather than the
# source, because a gate can be written three different ways and grepping for one
# reports the other two as unguarded. Run it as a test, not by hand.
python -m pytest app/apis -q
```

```bash
# Hardcoded role names in business logic. Expect zero outside the access-control
# module itself.
grep -rn --include="*.py" '"admin"\|"superuser"\|"manager"' app/ | grep -v "iam/\|auth/\|test_\|catalog"
```

```bash
# Nothing that gates access may be cached. Expect zero hits.
grep -rn --include="*.py" "cache" app/iam/permission/ app/iam/auth/current_user.py
```

```bash
# Every permission the client names must exist on the server.
# Run as a test. Roughly:
#   assert set(client_mapping_values) <= set(server_catalogue_names)
```

```bash
# Permissions that gate no route: declared and unused.
# Diff the catalogue against the gates the OpenAPI walk found.
```
