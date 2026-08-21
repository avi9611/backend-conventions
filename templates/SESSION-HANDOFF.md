# <Topic> — <DD Month YYYY>

> A handoff is a **dated record**. It is never edited afterwards. It holds what code and git
> cannot: why this approach, what was rejected, and what was deliberately left undone.
>
> **If this establishes a lasting cross-cutting fact, copy it into `docs/concerns/<topic>.md` in
> the same change.** The handoff keeps the reasoning. The concern doc holds what is true now.

**Repos touched:** <one file covers both halves of a full-stack change, not two>

---

## What prompted this

The bug, the request, or the question. If it was a bug, describe the symptom the way it was
actually reported, because that is how the next person will meet it again.

## What I changed

In normal words, not just file paths.

- 
- 

Files, for reference:

- `path/to/file.py`

## Why this approach

The reasoning that is not visible in the diff.

## What I rejected

The alternatives, and why not. **Do not skip this.** It is the reason the file exists.

| Option | Why not |
|---|---|
| | |

## What I deliberately did not do

Scope I left out on purpose, so nobody reads it as an oversight. Say whether it is planned.

## Test results

Quote the real numbers.

```
<N> passed, <N> failed
```

Pre-existing failures, and how I proved they predate this work:

- 

## What to watch

Anything that could go wrong from this, or anything the next person should check.

## Follow-ups

Concrete, actionable, with enough context to pick up cold.

- [ ] 
