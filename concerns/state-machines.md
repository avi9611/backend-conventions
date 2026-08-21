# State Machines

> Read this before you add a status field or an endpoint that changes one.
>
> **Status in this project:** in force from the first status field
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

A status field with free updates is a bug factory. Somebody sets a job back to open after it is
closed. Somebody approves a quote that was never submitted.

Every status gets an explicit map of which changes are allowed, checked on every change. The
value of writing the map down, rather than scattering `if status == ...` checks, is that the
legal moves live in one place per module and the illegal ones are refused the same way
everywhere.

The mechanism is about twenty lines. All the intelligence is in the maps.

---

## 2. The rules

- **Every status field has a transition map** in the module's enums file.
- **The service checks the transition before any status change**, catches the generic failure and
  re-raises the module's own named exception, which is a 409.
  → [`error-handling.md`](error-handling.md)
- **State changes go through a dedicated guarded endpoint.** Never through the generic update.
- **The generic update schema does not contain the status field**, or the assignment field.
  Neither is freely settable.
- **The guard reads state from the locked row.** → [`concurrency.md`](concurrency.md) §3b
- **One guarded endpoint per transition when the transitions carry different authority.** §3b.

---

## 3. The traps

### 3a. The map with no guarded endpoint

**Symptom.** The transition map is right, the tests of the map pass, and users still put records
into impossible states.

**Why.** Somebody left the status field on the generic update schema. The map is never consulted
on that path.

**The fix.** Take it off the schema, and test for it. A syntax-tree check is the right tool here,
because a grep cannot tell a create schema from a response schema, and the response *should*
carry the status.

### 3b. One generic state endpoint when the transitions carry different authority

**Symptom.** The permission check for approving something lives inside a switch statement on the
target status.

**Why.** A single `PATCH /{id}/state` looks tidy and is genuinely fine when every transition is
the same kind of act.

**Why it goes wrong.** When an engineer submits and a manager approves, one endpoint has to
re-derive which permission applies from the target status. That puts the check as far as possible
from the thing it protects, and it means adding a new status silently changes what an existing
permission allows.

**The fix.** One endpoint per transition, each with its own permission, when they carry different
authority. Submit, approve, reject, cancel, revise. Keep the shared map, it still guards the
moves.

### 3c. The guard that reads pre-lock state

Covered in full in [`concurrency.md`](concurrency.md) §3b. In short: the read that feeds the
guard must be the locked one, forced to refresh, or two concurrent transitions both pass.

### 3d. Assignment is not a state

**Symptom.** The transition map grows entries that are really about who holds something.

**Why.** Assignment feels like a status because it changes what people can do.

**The fix.** Keep them apart. Assignment toggles through its own endpoints, with their own
validation. The holder must be active, must be in the right tenant, and so on. That is different
validation from a transition map, and mixing them makes both harder to read.

### 3e. Terminal states that are not terminal

**Symptom.** A cancelled record gets reopened, edited, and the audit trail makes no sense.

**Why.** The map has an entry out of the terminal state, added once for a support case.

**The fix.** Terminal states have an empty allowed set. If a support case genuinely needs a way
back, that is a new named action with its own permission and its own audit entry, not an extra
arrow on the map.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Where the map lives | the module's enums file | | |
| Endpoint shape | one per transition, or one generic with a target | | |
| Status storage | a database enum type, or a string with a check constraint | | |
| Can a record have two machines? | no, or yes, on a parent and its lines | | |
| Who may force a transition | nobody, or a platform role, with an audit entry | | |

Row 3 matters more than it looks. A database enum type gives you real integrity and a painful
migration every time you add a value. A string with a check constraint is easier to change and
lets a bad value in through a direct database write. If you use enum types, read
[`migrations.md`](migrations.md) §3b before your first one.

Row 4: a parent with its own lifecycle and lines with theirs is normal and fine. Just draw both
maps, and be explicit about which parent transitions are blocked by line states.

---

## 5. Inventory

### Modules with a transition map

| Module | Entry state | Terminal states | Notes |
|---|---|---|---|
| | | | |

Draw the full diagrams somewhere. One place, not per module. A reader who wants to understand the
system's flow should not have to open nine enums files.

### Where a status field deliberately has no machine

| Case | Why |
|---|---|
| Config, lookup and permission records | they have no lifecycle. A role is not "in a state" |
| Append-only rows | never updated, so nothing transitions |
| | |

### Known gaps

---

## 6. New-status-field checklist

1. Define the enum and the transition map in the enums file. Mark the entry state in a comment.
   Give terminal states an empty allowed set.
2. Add a dedicated endpoint. Do **not** let the generic update carry the status.
3. In the service: check the transition, catch the generic failure, raise your own 409.
4. Read the state through the **locked** row, not a separate unlocked read.
5. Draw the machine into the shared diagram document and add the row to §5.

---

## 7. How to re-check this doc

> Paths below are examples from one tree. Adjust them to yours. What matters is the check,
> not the path. Where a count is given, it is the count **for this project**, so fill it in
> the first time you run it.

```bash
# Modules with a transition map.
grep -rln --include="enums.py" "_STATE_TRANSITIONS\|_TRANSITIONS" app/ | wc -l
```

```bash
# Service files that enforce transitions. Every map should have at least one
# caller. A map with none is a machine nobody checks.
grep -rln --include="*.py" "assert_transition(" app/ | grep -v "state_machine.py\|test_"
```

```bash
# A status or assignment field accepted through an update schema. Syntax tree, not
# grep, because a grep cannot tell an Update schema from a Response schema.
#
# This one does NOT expect zero. Read every hit. Three shapes are legitimate and
# will show up, so record yours here the first time you run it:
#   - a DEDICATED assignment schema whose class name happens to end in "Update"
#     (that is the rule being followed, not broken)
#   - an account status an admin sets directly, which has no state machine
#   - a child entity's own status, guarded by its own map
# Anything else is the generic update carrying a state field, which is the bug.
python3 - <<'PY'
import ast, pathlib
BANNED = {"state", "status", "assigned_to", "assigned_to_user_id"}
for p in sorted(pathlib.Path("app").rglob("schemas.py")):
    for n in ast.walk(ast.parse(p.read_text())):
        if isinstance(n, ast.ClassDef) and n.name.endswith("Update"):
            for b in n.body:
                if isinstance(b, ast.AnnAssign) and isinstance(b.target, ast.Name) \
                   and b.target.id in BANNED:
                    print(f"{p}:{b.lineno}  {n.name}.{b.target.id}")
PY
```
