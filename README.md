# Backend Conventions Kit

A portable set of rules, traps and checklists for building a new backend.

It is the Phoenix `docs/concerns/` folder with the Phoenix taken out. Every rule here was paid
for once already, by a bug that shipped. The point of copying the folder into a new project is
that you do not pay for them again.

**Last verified against the code: 21 August 2026.** (Phoenix backend, at that date.)

---

## What is in here

| File | What it is for |
|---|---|
| [`CHECKLIST.md`](CHECKLIST.md) | **Start here.** The whole convention set as things to tick off. Day 0 decisions, then per module, per route, per mutation, per list, per PR, and before you go live. |
| [`concerns/`](concerns/README.md) | One file per topic that runs across every module. Read one *before* you add the thing it covers. |
| [`RECOMMENDATIONS.md`](RECOMMENDATIONS.md) | What I added on top of Phoenix, and the six Phoenix decisions I would make differently next time. |
| [`templates/`](templates/) | Copy-me files. The always-loaded guardrail file, a concern doc, an ADR, a module guide, a session handoff. |
| [`tools/check_docs.py`](tools/check_docs.py) | Fails the commit when a doc link is dead or a doc has gone stale. |

---

## How to use it on day 1 of a new project

1. Copy this whole folder into the new repo as `docs/`.
2. Work through **Part 1 of [`CHECKLIST.md`](CHECKLIST.md)** and write down your answers. That is
   about twenty decisions. Most of them are cheap now and very expensive in month six.
3. Copy [`templates/CLAUDE.md.template`](templates/CLAUDE.md.template) to the repo root as
   `CLAUDE.md` and fill in the blanks. This is the file an AI assistant loads at the start of
   every session, so it has to stay short.
4. Delete the concern docs for things your project genuinely does not have. If you have one
   branch and will only ever have one, delete `tenancy-and-scoping.md`. Do not keep a doc that
   describes a mechanism you did not build. A doc that lies is worse than no doc.
5. As you build, fill in each concern doc's **§5 Inventory**. That table is what makes the doc
   worth reading a year later.
6. Wire `tools/check_docs.py` into a pre-commit hook.

---

## The three rules that keep this folder honest

These matter more than any single convention below. Without them the folder rots in about four
months and then actively misleads people.

### 1. One owner per rule

A cross-cutting rule is written out in full in **exactly one place**: its concern doc.

Everywhere else it appears as a one-line summary with a link. The ADR owns *why we decided this*.
The concern doc owns *what is true now*. `CLAUDE.md` owns *the one line you read before every
change*.

This split exists because the same rule once lived in eight files and the copies disagreed. When
a rule changes you should have one file to edit, not eight to hunt.

### 2. Every doc carries a date stamp

Put this line near the top of every file:

```
Last verified against the code: 21 August 2026
```

If you check a claim while working, move the date. If you find a doc wrong, fix it in the same
change as the code. An undated doc is unusable, because nobody can tell "true in July" from
"true today".

`tools/check_docs.py` makes a missing stamp an error and a stamp older than 30 days a warning.

### 3. Every doc ends with the commands that rebuild it

The last section of every concern doc is a set of shell commands that regenerate its inventory,
with the count each should produce. If a count disagrees with the table, **the table is stale**.

This is the only real defence a document has. Review will not catch drift. A grep will.

---

## The shape of a concern doc

Seven sections, always in this order. The shape is what makes them comparable.

| § | Section | What goes in it |
|---|---|---|
| 1 | What & why | The failure this prevents, in one paragraph. Not a tutorial. |
| 2 | The rules | Checkable bullets. A reviewer should be able to say "this line breaks rule 3". |
| 3 | The traps | The non-obvious failures. Each one names its symptom, because the symptom is how you will meet it. |
| 4 | Decisions to make | A table of forks in the road with a blank "what we chose" column. **This is the section that makes the doc portable.** |
| 5 | Inventory | Where it is used in this project, and where it is deliberately not used, with the reason. |
| 6 | New-module checklist | What a future module author must do about this topic. |
| 7 | How to re-check | The literal commands, with expected counts. |

§4 is the one Phoenix does not have. Phoenix answered those questions years ago and wrote down
only the answer. A new project has to answer them, so the questions are the useful part.

§5 starting empty is normal and correct. Fill it as you build.

---

## Keep the guardrail file short

`CLAUDE.md` in the repo root is loaded into an assistant's context at the **start of every
session**, before anyone knows which part of it matters. Every line you add is context spent on
all the work it is not about.

Treat 350 lines as a ceiling, not a target. The split:

- The **rule** goes in `CLAUDE.md`, in one or two lines. It has to be the version that prevents
  the bug on its own.
- The **inventory, the reasoning, the war story, the open gaps** go in the concern doc. Always.
- Put the pointer in the section *heading*, like
  `## 15. Caching → docs/concerns/caching.md`, so it costs no extra line.

The test: **can someone write correct code for the common case from `CLAUDE.md` alone?** If yes,
everything else belongs in the concern doc.

Writing a concern doc should make its `CLAUDE.md` section *shorter*, not longer.

---

## Where these rules came from

Phoenix is a multi-branch calibration lab CRM. FastAPI, async SQLAlchemy 2.0, Postgres, Redis,
Celery, S3. About 40 modules, 330 routes, 840 tests.

The stack shows through in places. Where a rule is really about SQLAlchemy or FastAPI I have said
so, and said what the general version of the rule is. Most of them are not about the stack at all.
"Do not aggregate over a page you already capped" is true in Django, Rails and Go.
