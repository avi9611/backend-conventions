# Analytics & Stats Endpoints

> Read this before you add a summary panel, a report, or any aggregate number.
>
> **Status in this project:** decide before the first summary panel
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

Most list pages want a summary beside the table. Totals, a status breakdown, a top-ten ranking.

Every one of those numbers is an aggregate over a **whole tenant's rows**, which puts it directly
in the path of the two failures [`pagination-and-search.md`](pagination-and-search.md) exists to
prevent. Silent truncation, and aggregating over a page instead of a table.

The tempting shortcut is to fetch the list and add it up in the browser. Phoenix tried that once
and reverted it before it shipped. It pulled the entire table into the browser, page one plus
however many parallel requests it took, and summed it in JavaScript. It was wrong three ways at
once. It re-implemented a SQL predicate in TypeScript where the two could drift. It did float
arithmetic on money. And its counts were computed over a different row set than the filter its
own click-through applied.

So: **aggregates are computed in SQL, by the module that owns the table, behind one endpoint.**

---

## 2. The rules

1. **Compute in SQL, in the data-access layer.** Never fetch rows to reduce them, not in the
   application and not in the client.
2. **Tenant-scope every query**, like any other list. A stats endpoint leaks a whole tenant at a
   time.
3. **Money and quantities stay decimals.** Multiplying two decimal columns does not land on two
   places by itself. Quantize deliberately.
4. **Do not send percentages.** Return the facts and let the client derive ratios. One rounding
   decision in one place beats two that disagree by a point.
5. **Every embedded list is capped and carries its true total**, and the UI renders a cap notice.
6. **Every clickable figure maps to a real list filter that produces exactly that set.** If the
   panel says 42 and the filter behind the click returns 39, the panel is lying. Where no filter
   matches, add one. Do not approximate. §3a.
7. **One measure per quantity, across the whole system.** §3b.
8. **Read-only.** No commit, no audit, no numbering, no side effects.
9. **Typed, per-module response shapes.** No generic self-describing envelope. §3c.
10. **Gate on the module's existing read permission.** No more strictly, and never less. §3d.
11. **The client query is lazy and it invalidates.** It fires when the panel opens, not on page
    mount, and the stats key is in the invalidation list of **every** mutation in the module.
    §3e.

---

## 3. The traps

### 3a. The figure and the filter drifting apart

**Symptom.** A user clicks "42 low stock" and counts 39 rows.

**Why.** The count and the filter are two pieces of SQL, written at different times.

**The fix.** **One clause, used by both.** The bucket in the aggregate and the filter on the list
come from the same function. Then they cannot disagree.

**Two traps come with adding that filter, and both are silent:**

- **A filter name the server does not declare is ignored, not rejected.** Most frameworks drop
  unknown query parameters. So a typo gives you an *unfiltered* table with more rows than the
  figure counted, and no error anywhere.
- **A computed, query-only predicate is not a column.** If your list component derives a
  bulk-edit action from every filter it sees, a drill-only filter silently becomes a bulk action
  that fails. Exclude it explicitly.

**And the exclusions in each bucket are the point, not an oversight.** A decommissioned item, a
closed quote and a cancelled job all still carry a date that has passed. Counting them puts
permanent red on a panel that exists to show what needs doing. Each partition sums to its *live*
population, not to the module's total, and each of those invariants deserves a test.

### 3b. Two measures of the same thing

**Symptom.** Two screens report different totals for what users read as the same number.

**Why.** One sums quantity times unit cost. The other sums the stored line total. They agree
until a line carries a discount or tax.

**The fix.** Before adding an aggregate, grep for an existing one over the same table and match
it. Write the chosen measure down here. Phoenix retired a whole set of reports rather than keep
two measures in step.

**The cross-module version of the same rule.** An early-stage estimate and a priced quote are two
measures of "what this opportunity is worth". They diverge the moment anything is quoted
properly. Never add them, never compare them, and have each panel say which one it is showing.

### 3c. The generic stats envelope

**Symptom.** Labels, colours and copy end up in the server.

**Why.** A `{metrics: [{key, label, value, unit}]}` envelope removes the per-module mapping code,
which is the most boring code in the panel.

**Why it is wrong.** It moves presentation decisions into the layer that keeps none of your other
presentation decisions. Revisit it after four modules have shipped and the repetition is real,
not imagined.

**The one exception worth making** is a field saying *whose* numbers these are. See §3d. Without
it a panel cannot tell a genuinely empty tenant from a narrowed view.

### 3d. Gating a panel, and the three shapes

**Do not copy the neighbouring module's gate. Read this module's list query first.** There are
three shapes and picking the wrong one either lies or hides the panel.

**(a) The list applies no owner narrowing.** Gate on the plain read permission. Requiring
"read all" would hide the panel from people who can already read every row it counts, which rule
10 forbids in the other direction.

**(b) The list narrows, and the aggregate can narrow with it.** Gate on the plain read
permission and pass the caller's id down. **This is the preferred answer.**

**(c) The list narrows and the aggregate cannot follow.** Gate on "read all" and hide the panel.
This is a fallback, not a design. The people whose daily work the module *is* get no analytics at
all.

**If you take (b), five rules come with it:**

1. **Copy the narrowing predicate from that module's list query. Do not re-derive it.** If they
   ever differ, every figure disagrees with the table it drills into.
2. **Put the narrowing in one place**, a single scope helper every aggregate runs through.
   Narrowing individual queries invites one to be missed, and a missed one leaks tenant-wide
   counts.
3. **Skip owner rankings when narrowed.** "Leads per salesperson" over one person's rows is a
   single row with their own name on it.
4. **Return which scope this is**, so the UI can say whose numbers these are.
5. **Test the equality absolutely.** The narrowed total must equal the narrowed list's total for
   the same user. Delta assertions are not enough, because the failure mode is a *wrong
   denominator* and a delta hides it.

### 3e. The stats key that nothing invalidates

**Symptom.** A user creates a record and the panel still shows the old count for a minute.

**Why.** A key factory where the list key and the stats key are siblings. Invalidating the list
key does not touch stats.

**The fix at small scale:** add the stats key to every mutation's invalidation list.

**The fix past about a dozen mutation sites: make it impossible to forget rather than a rule to
follow.** Replace the raw invalidate call with one helper that busts the entity key and the stats
key together. Then copying the neighbouring mutation gets it right by default. The failure mode
of the plain rule is one forgotten call site showing a stale figure with nothing to report.

### 3f. Multi-section panels, when one gate does not fit

If a panel spans several registers behind **separate** read permissions, neither single-gate
answer works. Gated on all of them, you hide it from somebody who can read one. Gated on any one,
you serve the most sensitive section to somebody who can read the least sensitive.

**So the gate is per section.** The route opens on "any of these", then resolves each section
separately, and a section the caller may not read is **absent from the response**, not empty.

Four things follow:

1. **Absent and all-zero mean different things**, and the UI renders them differently. No tab,
   versus a tab saying there is nothing. Never collapse them into one.
2. **The scope field is per section, not per response.** A caller can hold "read all" on one
   register and "read own" on another.
3. **This is not the generic envelope §3c forbids.** Every field is typed and named. Only whether
   a section is present varies.
4. **A section the caller cannot read costs no queries**, rather than being computed and thrown
   away.

### 3g. What these actually cost — measure before optimising

Phoenix measured this on a copy of production inflated to five years of volume. Roughly 300,000
documents and 288,000 line items. The results cancelled three of four planned optimisations.

| Endpoint shape | Today | Five years of volume |
|---|---:|---:|
| A simple snapshot | 2ms | 2ms |
| A moderate panel | 3ms | 50ms |
| The heaviest panel, 11 queries over the two largest tables | 4ms | **207 to 360ms** |

**Four conclusions:**

1. **The indexes were already right.** A status aggregate ran as an index-only scan and still
   cost 6ms, because it has to walk 49,000 index entries to count them. **You cannot index your
   way out of counting every row in a tenant.**
2. **No server cache.** Every endpoint was under 4ms at real volume. Caching a 4ms query buys
   nothing and costs you a scope-key trap. → [`caching.md`](caching.md) §3d
3. **No throttle.** At 4ms a reload loop costs nothing worth defending against.
4. **Do add a short private cache header.** It is the whole answer to the browser-reload hole,
   because the request is never sent. `private` is not optional, since these responses are per
   user and per scope.

**And the expensive shape is the time series, not the count.**

| Query over 300,000 rows | Time |
|---|---:|
| group by status | 21ms |
| group by month over five years | 103ms |
| the same with a purpose-built index | 71ms |

A month-grouped rollup is the single most expensive thing in any panel. **Two rules, both free if
built in from the start:** one time-series query per panel, not one per chart. And default the
period to a window, never to all time.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Where aggregates live | the owning module, or a reporting module | | |
| Response shape | typed per module, or a generic envelope | | |
| Period filter | none, or a fixed set of windows | | |
| Charts | CSS bars, or a charting library | | |
| Server cache on stats | no, until measured | | |
| Cache header | short and private | | |
| Own-scope panels | narrow the aggregate, or hide the panel | | |

Row 3: adding a period to the shared contract before a panel needs one is speculative. When it
arrives, resolve it against the tenant's calendar.
→ [`dates-and-timezones.md`](dates-and-timezones.md)

Row 4: CSS bars are enough for distributions across buckets, which is what most panels show. A
bar per bucket cannot answer "how does this month compare to last", so the first period filter is
also the first real chart. When that happens, add a chart **primitive to the shared kit**, on the
same terms as everything else there. It is not a licence for one module to hand-roll a chart.

---

## 5. Inventory

### The endpoints

| Module | Endpoint | What it reports | Gate |
|---|---|---|---|
| | | | |

### Shared partition clauses

One definition each, used by both the count and the list filter.

| Clause | List filter name | Buckets | Deliberately excluded |
|---|---|---|---|
| | | | |

### Where an aggregate is deliberately not offered

| Not reported | Why |
|---|---|
| | |

Good entries here are the ones that stop somebody adding a wrong number. "This module reports no
revenue, because it cannot see the invoices, and deriving one from job volume would be a second
quietly wrong answer."

### Known gaps

---

## 6. New-panel checklist

1. Write the aggregate queries in the module's data-access layer, each tenant-scoped, each
   returning the rows and the true total where capped. **Reuse the module's existing filter
   clauses** so the numbers and the filters are the same SQL.
2. Add a cap constant and a typed response shape. Decimals throughout. Quantize money. No
   percentages.
3. Add a read-only analytics collaborator that shapes rows into the response.
4. Add the endpoint, gated per §3d, declared **before** any id route.
5. For every figure you intend to be clickable, confirm a list filter exists that returns exactly
   that set. Add one if not.
6. Client: add the stats key to **every** mutation's invalidation list, or use a helper that
   cannot be forgotten.
7. Client: map the response onto the shared kit. No new layout components. If the kit cannot
   express it, extend the kit.
8. Tests: totals against a hand-summed fixture, buckets partition exactly, cross-tenant
   isolation, and the cap path.
9. Update the module guide with any rule the panel exposes.

---

## 7. How to re-check this doc

```bash
# Every aggregate endpoint. Compare to §5.
grep -rnE '^\s+"(/stats|/reports/[a-z-]+)"' app --include="*.py"
```

```bash
# The read-only analytics collaborators.
find app -name "analytics.py" -o -name "*_analytics.py" | grep -v "test_"
```

```bash
# The partition clauses. Each should have exactly one definition.
grep -rn "def _.*_clause" app --include="*.py"
```

```bash
# Client: nobody may define an analytics primitive outside the shared kit.
# Importing one is fine. A local copy is the smell.
grep -rn "^function \(CapNotice\|StatTile\|KpiStrip\|SegmentedBar\)" src/ | grep -v "shared/analytics"
```

```bash
# Client: every module with a stats query must bust that key on writes.
grep -rn "stats()" src/lib/
```
