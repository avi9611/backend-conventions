# ADR-<n> — <the decision, as a short noun phrase>

> **Date:** <DD Month YYYY>
> **Status:** proposed / accepted / superseded by ADR-<n>
> **Current practice:** `docs/concerns/<topic>.md`

An ADR is a **dated record**. It never changes after it is accepted, except to be marked
superseded. It answers *why we decided this, then*. The concern doc answers *what is true now*.

If you find yourself editing an accepted ADR to reflect how the code works today, you want the
concern doc instead.

---

## Context

What was true when this came up. The constraint, the problem, or the thing that broke.

Include the numbers if there were any. "One of twelve concurrent callers succeeded" is worth more
than "there was a race".

## Decision

One paragraph. What we are going to do, in the active voice. "Every list query goes through the
scoping helper."

## Rules

The checkable consequences. These are what get copied into `CLAUDE.md` as one-liners and into the
concern doc in full.

- 
- 

## What we rejected, and why

The most valuable section, and the one people skip. Without it, somebody re-proposes the rejected
option in a year and nobody remembers the reason.

| Option | Why not |
|---|---|
| | |

## Consequences

What this costs. What becomes harder. What we now have to remember forever.

Be honest here. An ADR with no costs listed reads as marketing.

## Cited in

Where the code refers to this decision by number, so a reader can find the enforcement.

- `path/to/file.py`
- `CLAUDE.md` §N
