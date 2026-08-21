# Pagination, Lists & Search

> Read this before you build a list endpoint, a report, a dropdown, or an embedded child
> collection.
>
> **Status in this project:** in force from day 1
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

The failure mode here is unusual: **nothing errors.**

An unbounded query does not crash. It just stops returning rows once the data grows. A report
truncated at some arbitrary count. A stock ledger capped at 50 with no way to reach row 51. A
supplier dropdown that makes supplier number 201 unselectable.

These surface twelve to twenty-four months into production, as "the system lost my data"
tickets. That is the worst possible time to find them, because by then the workaround is somebody
keeping a spreadsheet.

So the rule is not "paginate everything". It is **never truncate silently**. Every bounded
surface either tells the user it is bounded, or gives them a way to reach the rest.

---

## 2. The rules

- **Every list surface is one of three shapes** (§3a). Pick one on purpose. The wrong default is
  "no limit".
- **A cap ships with the true total and something visible saying so.** A cap without that is the
  same silent-truncation bug with a bigger number.
- **Never filter in the application after the database applied a limit.** The page fills with
  rows you are about to throw away, and the ones you wanted fall off the end.
- **Never total or rank over a capped list.** Ask the database.
- **Always search through the shared helper**, which escapes wildcard characters and combines
  columns. Never build a pattern by hand.
- **Always sort through the shared helper with an allow-list**, and keep that list in step with
  the type the endpoint declares. A raw column name from a query parameter is an injection hole.
- **Every embedded child collection is bounded by something.** If nothing bounds it, window it
  and give it its own paged endpoint.

---

## 3. The traps

### 3a. The three shapes

| Shape | Use when | The contract |
|---|---|---|
| **Paged** | anything a user browses | skip and limit in, items plus total plus skip plus limit out |
| **Capped, with the true total** | reports and boards that are scanned whole, where a pager reads badly | count over the whole set, plus a limit, and the UI says "top 50 of 900, narrow your filters" |
| **Deliberately unbounded** | financial totals and genuinely small sets | must be justified in §5 |

The third one is legitimate and rarer than people think. A *page* of an ageing total is simply a
wrong number, so that query has to see everything. Write down why.

### 3b. Filtering after the limit

**Symptom.** A list that should show unpaid bills shows only paid ones. Or shows nothing, on a
system with plenty of matching rows.

**Why.** The query fetched the oldest 200 rows and then dropped the ones that did not match. The
oldest rows are also the ones most likely to be settled, so the filter removed all of them.

**The fix.** Filter in SQL. If the endpoint does not offer the filter the caller needs, **add the
filter to the endpoint**. A filter applied after the fetch looks free and silently hides rows.

This applies on the client too. A picker that fetches a page and then drops rows in JavaScript is
the same bug on the other side of the wire.

### 3c. Aggregating over a page

**Symptom.** "Most purchased item" names something obviously wrong. A cheap high-volume item that
should win never appears.

**Why.** The code took a page sorted by *spend*, then took the maximum by *quantity* within it.
The right answer was outside the page.

**The fix.** Ask the database for the aggregate. → [`analytics.md`](analytics.md)

### 3d. The sort allow-list drifting from the declared type

**Symptom.** A sort option appears in the API docs and returns a 422 when used. Or worse, a
column that should not be sortable is.

**Why.** Two lists. One in the params type that the docs generate from, one in the data-access
layer that actually enforces. They were edited at different times.

**The fix.** Derive one from the other, or write a test that asserts they match. Either is five
minutes.

### 3e. The child collection that grows forever

**Symptom.** One record's detail response is 4MB, and getting slower.

**Why.** An embedded history or revision list with no bound. Every edit adds a row and the row
holds a full snapshot.

**The fix.** Window the embedded copy to the newest N, and add a paged endpoint for the rest. And
**take the heavy field off the list rows entirely**. A revision list does not need each
revision's full snapshot. The compare screen fetches the two it needs.

### 3f. The client filtering a fetched page

**Symptom.** A list page shows the right rows but the wrong total, or paging past page one shows
duplicates.

**Why.** The page fetched data, then filtered it in the component, then reported the filtered
count as the total.

**The fix.** Wire the list component's parameters to the query, so filtering and paging happen on
the server. → [`frontend-contract.md`](frontend-contract.md)

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Paging style | offset and limit, or cursor | | |
| Default page size, and hard maximum | | | |
| Response envelope | items plus total, or items plus a next cursor | | |
| Is the total always computed? | yes, or on request | | |
| Sort parameter | one field plus direction, or a multi-field expression | | |
| Search technique | LIKE, trigram, or full text | | |
| Cap size for reports | | | |

Row 1: offset paging is simpler, matches "page 4 of 12" and gets slower and less stable as the
offset grows. Cursor paging is stable under concurrent writes and cannot express "jump to page
7". For an internal business system, offset is usually right.

Row 4: computing the total with a window function costs one scan and gives you the number every
UI wants. Making it optional is a real optimisation only at large scale.

Row 6: escaped LIKE is right for the great majority of endpoints. Reach for anything else when
you have measured a problem, not before. Write down the decision tree once, in this doc, so the
next person does not re-litigate it per endpoint.

---

## 5. Inventory

### The caps in use

| Constant | Value | Where |
|---|---|---|
| | | |

### Windowed children with their own paged endpoint

| Parent | Child | Embedded | Paged endpoint |
|---|---|---|---|
| | | | |

### Deliberately unbounded

| Query | Why |
|---|---|
| | |

### Known gaps

---

## 6. New-list checklist

1. **Pick a shape from §3a.** If it is a report, cap it, and add the total and the visible notice
   in the same change.
2. Params: subclass the shared base, add the search field, and give the sort field a closed set
   that matches the allow-list exactly.
3. Data-access: build one where clause. Tenant scope, then filters, then search. Return the items
   and the total. Never filter afterwards in the application.
4. Pick the search technique from the decision in §4, not per endpoint.
5. **Any child collection you embed: ask what bounds it.** If nothing does, window it and add a
   paged endpoint.
6. On the client, wire the list component to the query parameters.
7. Run the route guard tests after touching a route.
8. Add the surface to §5.

---

## 7. How to re-check this doc

```bash
# All cap constants. Compare to the §5 table.
grep -rhoE "[A-Z_]+_CAP = [0-9]+" app/ --include="*.py" | sort -u
```

```bash
# Modules using the safe helpers. A list endpoint using neither is building SQL by
# hand. Read it.
grep -rln --include="*.py" "ilike_search" app/ | grep -v core/crud | wc -l
grep -rln --include="*.py" "apply_sorting" app/ | grep -v core/crud | wc -l
```

```bash
# Unbounded reads: fetching everything with no limit nearby. Noisy by nature, so
# read each hit rather than counting. Everything legitimate is listed in §5.
grep -rn --include="*.py" "scalars().all()" app/ | grep -v "test_\|limit"
```

```bash
# Client-side filtering after a fetch. Read every hit.
grep -rn "\.filter(" src/components --include="*.tsx" | grep -v "// server-side"
```

```bash
# List pages not wired to the server-side query params. Adjust the two names to
# match your own list component and its params prop.
grep -rln "useDataView" src/components/ | sort > /tmp/dv.txt
grep -rln "apiParams" src/components/ | sort > /tmp/ap.txt
comm -23 /tmp/dv.txt /tmp/ap.txt
```
