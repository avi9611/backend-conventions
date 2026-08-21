# The Frontend Contract

> Read this before you build the client half of anything in this folder.
>
> **Status in this project:** applies as soon as there is a client
> **New in this kit.** It merges Phoenix's frontend guardrail with its unsaved-work concern, and
> keeps only the parts where the backend's shape decides the client's behaviour.
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

This is a backend kit. This file is here because some of the rules above **only work if the
client holds up its half**, and a backend developer needs to know which those are.

Three things in particular. A picker that reads the wrong endpoint reintroduces a permission bug
you fixed on the server. A list page that filters in the browser reintroduces the truncation bug.
And a query cache that is not tenant-aware looks exactly like a data leak to a user.

The rest is a short list of client conventions worth having, because the same "one owner per
rule" discipline applies there.

---

## 2. The rules

### The ones that hold up a backend rule

- **A picker reads the options endpoint, never a module's list endpoint.** If you are reaching for
  a domain list hook to fill a control, stop.
  → [`reference-data-and-pickers.md`](reference-data-and-pickers.md)
- **A list page sends its filters and paging to the server.** Never fetch a page and filter it in
  the browser. → [`pagination-and-search.md`](pagination-and-search.md)
- **A capped response renders its cap notice.** → [`analytics.md`](analytics.md)
- **On a tenant switch, remove cached queries. Do not just invalidate them.**
  → [`caching.md`](caching.md) §3e
- **After a write, do not trust nested collections in the mutation's response. Refetch.**
  → [`transactions-and-layering.md`](transactions-and-layering.md) §3a
- **Money arrives as a string and stays a string.** No float arithmetic.
  → [`money-and-quantities.md`](money-and-quantities.md)
- **Coerce every enum through a fallback.** Never cast a raw server string to an enum type.
  → [`api-contract-and-versioning.md`](api-contract-and-versioning.md) §3c
- **"Today" comes from the viewer's local calendar, not from a UTC date slice.**
  → [`dates-and-timezones.md`](dates-and-timezones.md) §3e
- **Permission checks in the UI hide affordances. They are not the security boundary.**
  → [`permissions.md`](permissions.md)

### The client's own

- **One HTTP client, stateless, no stored tokens.**
- **One conversion boundary per domain**, and it is the only place server field names appear.
- **One query-key factory per domain.** Build keys only from it, or invalidation misses.
- **Server state lives in the query cache. The UI store holds only UI state.** Never put loading
  flags or fetched lists in a store.
- **Success messages live in one place per action**, not in both the hook and the component.
- **One modal component, one list component.** A one-off dialog is how the unsaved-work guard
  gets skipped.
- **Design tokens only.** No raw colour values in components.

---

## 3. The traps

### 3a. Losing a form to the Escape key

**Symptom.** A user fills in a long form, catches Escape or clicks slightly outside the panel,
and the work is gone. No warning, no draft, nothing to recover.

**Why.** Nobody thought about it. It is invisible until it happens to somebody with twelve
minutes of typing in front of them.

**The fix, and there are two, and picking the wrong one is the mistake worth avoiding:**

| | Use when | Cost |
|---|---|---|
| **Guard the close** | the record does not exist yet, or the edit is short | one property |
| **Autosave** | the record already exists **and** the form is long enough that losing it is unacceptable | a debounce, a local buffer, a quiet mutation, a save indicator |

**Autosave is not the default and must not become one.** To autosave a *create* form you have to
create the row first, so every abandoned form leaves a half-filled record behind. And for anything
with a generated code, it **burns a document number that can never be reused**.
→ [`document-numbering.md`](document-numbering.md)

### 3b. The dirty check that fires every time

**Symptom.** The "discard your changes?" prompt appears on every close, so people learn to click
through it without reading. Which is worse than having no prompt.

**Why.** The check asks "is this form non-empty" rather than "has this form changed".

**The fix, and it is the whole rule:**

> **Compare against the state the form opened with. Never against "is it empty".**

An edit form starts full. A create form often starts pre-seeded, with one blank line, or with an
outstanding amount filled in. Phoenix wired six modals with a naive non-empty check and **all six
were wrong**, because every one of them was pre-seeded.

**Check what a form opens with before you write the expression.**

### 3c. Discarding that does not discard

**Symptom.** The user answers "discard", the panel closes, and the values are still there next
time they open it. Only a page reload clears them.

**Why.** Panels usually stay mounted while closed, because unmounting mid-animation makes them
snap shut. So closing flips a flag and does **not** erase the state inside.

**The fix.** Every guarded form needs a second half. Either it resets on open, which also covers
the paths the guard does not (a footer cancel button, or reopening after a successful save), or it
re-seeds from the server on an explicit discard.

**An autosaving panel needs the second one for a sharper reason:** its pending write is a timer
that closing does not cancel. Without it, "discard" keeps the values *and* lets the queued save
write them, which is the exact opposite of what the button says.

### 3d. Coverage of the guard cannot be enforced cheaply

The dirty property is optional and defaults to off, because defaulting it on would make every
read-only detail panel prompt.

**So a modal added tomorrow silently gets the old lose-everything behaviour.** There is no lint
rule for "this component contains an input and should therefore pass the property".

The audit is a one-off script: find every file containing the modal component plus form state, and
diff it against those passing the property. Phoenix ran it and found **30 unguarded modals**,
*after* a pass that believed itself complete.

**Deliberately unguarded:** read-only panels, single-action confirmations, and pickers. One click
is cheap to redo, and a prompt on a trivial dialog is how the prompt stops being read on the forms
that matter.

### 3e. The store that holds server state

**Symptom.** A list shows stale data after a write, and invalidating the query does not help.

**Why.** The data was copied into a UI store on mount.

**The fix.** The query cache is the only home for server data. If a store is over about fifty
lines, it is probably holding server state.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Field naming on the wire | matches the server, or converted | | |
| Where conversion happens | one file per domain | | |
| Server state | a query library, or hand-rolled | | |
| Default staleness | | | |
| Are query keys tenant-scoped? | | | |
| Mutation feedback | a blocking overlay, or inline | | |
| Unsaved-work guard | every form, or long forms only | | |
| Autosave | which screens, and none by default | | |

Row 5: yes is the correct answer and it means threading the tenant into every key factory. The
cheaper answer is removing cached queries on switch. Do the cheap one now and the correct one in
the next data-layer pass.

Row 7: every form that holds typed input. It is one property.

---

## 5. Inventory

### Where a backend rule depends on the client

| Backend rule | The client's half | Where |
|---|---|---|
| Pickers are ungated and narrow | pickers read the options endpoint | |
| Lists never truncate silently | list pages send params to the server | |
| Caps carry a true total | the cap notice renders | |
| Tenant isolation | cached queries are cleared on switch | |

### Guarded and unguarded forms

| Form | Guarded | Autosaves |
|---|---|---|
| | | |

### Known gaps

---

## 6. New-screen checklist

1. Data layer first: types, one conversion file, the API functions, the hooks with a key factory.
2. **Pickers use the shared picker.** Do not write a new one.
3. **List pages send their params to the server.**
4. Every form that holds typed input passes the dirty property, compared against **the state it
   opened with**.
5. Every guarded form also resets on open, or re-seeds on discard.
6. Add the stats key to every mutation's invalidation list, if the module has a panel.
7. Gate privileged affordances on a permission check, and remember it is not the boundary.
8. Design tokens only.

---

## 7. How to re-check this doc

```bash
# Pickers reading a gated module list. Expect zero in the shared components.
grep -rn "useVendors\|useClients\|useItems\|useUsers\b" src/components/shared/
```

```bash
# List pages not wired to server-side params.
grep -rln "useDataView" src/components/ | sort > /tmp/dv.txt
grep -rln "apiParams" src/components/ | sort > /tmp/ap.txt
comm -23 /tmp/dv.txt /tmp/ap.txt
```

```bash
# Unguarded modals: files with a modal and form state that do not pass isDirty.
grep -rl "<Modal" src/components | xargs grep -l "useState\|useForm" | sort > /tmp/forms.txt
grep -rl "isDirty" src/components | sort > /tmp/guarded.txt
comm -23 /tmp/forms.txt /tmp/guarded.txt
```

```bash
# Server field names outside the conversion files. Expect zero.
grep -rn "\bcreated_at\b\|\bis_deleted\b" src/components/
```

```bash
# Raw colour values in components. Expect zero.
grep -rnE "#[0-9a-fA-F]{6}|bg-\[#" src/components/
```

```bash
# Server data in a UI store. A store over ~50 lines is the smell.
wc -l src/lib/*/store.ts 2>/dev/null | sort -rn | head
```
