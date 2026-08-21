# <Topic>

> Read this before you <the moment this concern applies>.
>
> **Status in this project:** not yet decided / in force since <date>
> **Last verified against the code:** <DD Month YYYY>

Guardrail: `CLAUDE.md` §N. Decision: ADR-N. Implementation: `path/to/thing`.

Copy this file to start a new concern doc. Keep all seven sections, in this order. The shape is
what makes them scannable and comparable. Delete this paragraph.

---

## 1. What & why

One paragraph. What the failure is, and what it costs when it happens. Not a tutorial. If a
reader needs to learn the technology itself, link out.

Say the failure mode plainly, because that is what makes someone read the rest.

## 2. The rules

The hard rules, as bullets. Each one has to be checkable. Somebody reading a diff should be able
to say "this line breaks rule 3".

Cross-reference the matching `CLAUDE.md` section, so the short guardrail and the long rule cannot
drift apart.

## 3. The traps

The failures that are not obvious from the rules. This is the section nobody can reconstruct for
themselves, so it is the most valuable part of the file.

Each trap gets three things:

- **The symptom.** How you will actually meet it. This is how a reader finds the right trap.
- **Why it happens.** The mechanism, not the moral.
- **The fix.**

If a trap cost a real day, say so and give the date. A war story is what makes a rule stick.

## 4. Decisions this project must make

The forks in the road. Fill in the last column and delete the ones that do not apply.

| Decision | Options | What we chose | Why |
|---|---|---|---|
| | | | |

An unanswered row here is a real open question, not a formatting gap. Leaving it blank is fine.
Pretending it is answered is not.

## 5. Inventory

### Where it IS used

Filled in as you build. One row per place, **verified by reading the code**, not by reading
another document. Include enough detail that a reader can tell whether their case matches.

| Where | What | Notes |
|---|---|---|
| | | |

### Where it is deliberately NOT used

The places that look like they should use this and do not, **with the reason and the
consequence**.

This is why the document is trustworthy. Without it the next person "fixes" a deliberate
omission.

| Not used | Why |
|---|---|
| | |

### Known gaps

Things that are wrong, missing or unfinished right now. Each one: what is broken, where, what it
costs, and whether a fix is planned. Delete an entry when it is fixed.

## 6. New-module checklist

A short numbered list. What a developer must do about this topic when building something new.
This is the section a future module author reads.

## 7. How to re-check this doc

The literal commands that rebuild §5, with the counts they should produce.

```bash
# what this proves
<command>
```

**If a count here disagrees with §5, §5 is stale. Fix it before relying on it.** Re-run these
whenever you touch the topic, and move the date stamp at the top.
