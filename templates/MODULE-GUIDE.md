# <Module> — how it behaves

> Plain-language guide to what this module does. Written for anybody who needs to know how it
> behaves, including people who do not read code.
>
> **Last verified against the code:** <DD Month YYYY>

---

## Invariants

The rules this module will never break. **Start here.** If you are changing the module, these are
the things a change must not violate.

- 
- 
- 

## What it is for

Two or three sentences. What business need this covers. Not a list of endpoints.

## What it deliberately does not do

Just as important. The things somebody will assume it does, with the reason it does not.

| Not done | Why |
|---|---|
| | |

## The records it owns

| Record | What it represents | Lifecycle |
|---|---|---|
| | | |

## The lifecycle

For each record with a status, the states and what moves between them. Draw it as a list of
arrows, not a diagram nobody can update.

```
DRAFT ──submit──▶ PENDING ──approve──▶ APPROVED
                     │
                     └──reject──▶ REJECTED
```

Terminal states: 

## What a user can do, and what happens

One row per action. This is the section support reads.

| The user does | The system does | Who may |
|---|---|---|
| | | |

## Edge cases and refusals

Every refusal this module can make, in the words a user sees, with the reason behind it.

| It says | Because | What to do instead |
|---|---|---|
| | | |

## Fields that are frozen, and fields that stay live

If this module issues a document, this table is required.
See `docs/concerns/snapshots-vs-live.md`.

| Field | Frozen at issue, or live | Why |
|---|---|---|
| | | |

## Permissions

| Permission | Lets you |
|---|---|
| | |

Row-level scope: <does "mine only" apply here, and what counts as mine?>

## How it connects to other modules

| Module | Direction | What flows |
|---|---|---|
| | | |

## Known gaps

What is unfinished or wrong today, and whether a fix is planned.
