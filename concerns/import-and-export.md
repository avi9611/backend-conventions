# Import & Export

> Read this before you accept a spreadsheet, or produce one.
>
> **Status in this project:** only needed when the first spreadsheet appears
> **New in this kit.** Phoenix does both and documents neither.
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

Every business system eventually grows a spreadsheet import and a spreadsheet export, because
that is how the business already works.

Both are riskier than they look. An import is an unauthenticated-shaped surface with
authentication on it: arbitrary content, from a file, that becomes rows in your database. An
export is a way for one permission to become a copy of your whole dataset on somebody's laptop.

Neither is hard. Both are easy to do badly, and the failures are unusually annoying because they
involve a file somebody else made.

---

## 2. The rules

- **An import is validated in full before anything is written**, and reports every problem at
  once. §3a.
- **An import runs in one transaction, or it is explicitly resumable.** Never half-applied with
  no record of where it stopped.
- **A template is downloadable, and it is generated from the same definition the parser uses.**
  §3b.
- **An export is a permissioned action and it is audited.** It is not "a list endpoint with a
  different content type".
- **An export uses the same query as the list it exports**, including the tenant scope and the
  row-level scope.
- **Dates and numbers in an export are formatted for reading, and the raw value is available.**
  §3c.
- **Never trust a filename or an extension.** → [`object-storage.md`](object-storage.md)
- **A large export goes to a file the user fetches, not down the request.** §3d.

---

## 3. The traps

### 3a. The import that reports one error at a time

**Symptom.** A user fixes row 4, uploads again, and is told about row 9. Twenty times.

**Why.** The parser raises on the first problem.

**The fix.** Two passes. Validate everything, collect every problem with its row number and
column name, and return the whole list. Only write if the list is empty.

**And be specific.** "Row 12, column 'Department': 'Enginering' is not a known department. Did you
mean 'Engineering'?" costs ten minutes to write and saves the support conversation entirely.

### 3b. The template that drifts from the parser

**Symptom.** A user downloads the template, fills it in, and the import rejects the column names.

**Why.** The template is a checked-in file and the parser was updated.

**The fix.** Generate the template from the same column definition the parser reads. One list of
columns, two consumers. Then they cannot drift.

### 3c. The timezone in the export

**Symptom.** An exported report disagrees with the screen by one day, near midnight, for some
rows.

**Why.** The export formatted the stored UTC instant directly, and the screen renders in the
tenant's zone. → [`dates-and-timezones.md`](dates-and-timezones.md)

**The fix.** Convert to the right calendar in the export, exactly as the screen does. And for a
report grouped by month, convert in SQL, joined to the tenant's zone.

**The number version of the same trap.** A spreadsheet will happily reformat a value you wrote as
text, and will turn a long number into scientific notation, and will strip leading zeros from a
code. If a column is an identifier, write it as text and say so in the column definition.

### 3d. The export that times out

**Symptom.** A user exports "everything" and the request dies at 30 seconds.

**Why.** The whole thing was built in memory and returned in the response.

**The fix, in order of effort:**

- **Cap it**, with the true total and a visible notice, like any other list.
  → [`pagination-and-search.md`](pagination-and-search.md)
- **Stream it**, so memory stays flat and the first bytes arrive quickly.
- **Generate it in the background**, store it, and notify the user with a link.
  → [`background-jobs.md`](background-jobs.md)

Start with the cap. Most "export everything" requests are actually "export this filtered view",
and the cap makes that visible.

### 3e. Formula injection

**Symptom.** A user opens your CSV export and their spreadsheet runs a command.

**Why.** A cell whose value starts with `=`, `+`, `-` or `@` is treated as a formula by most
spreadsheet applications. If any of your data is user-supplied text, somebody can put one there.

**The fix.** Prefix such values with a quote character on export, or write a real spreadsheet file
rather than CSV, where cell types are explicit. This is a genuine, commonly-missed hole, and it is
one line.

### 3f. The export that is a data exfiltration path

**Symptom.** Somebody leaves with a copy of your customer list.

**Why.** They had permission to view the customer list, which is reasonable, and export was
treated as the same act.

**The fix.** Treat export as its own permission, audit every one with the row count and the
filters used, and consider notifying somebody for large exports. That is a policy decision, not a
technical one, so make it deliberately.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Import formats | CSV, xlsx, both | | |
| Import transaction | all-or-nothing, or per-row with a report | | |
| Import size limit | | | |
| Template source | generated, or a checked-in file | | |
| Export permission | separate from read, or the same | | |
| Are exports audited? | | | |
| Export delivery | inline, streamed, or generated in the background | | |
| Export cap | | | |
| Date and number formatting in exports | | | |

Row 2: all-or-nothing is much easier to reason about and to explain to a user. Per-row is what
they ask for when the file is large. If you do per-row, you owe them a report file saying exactly
which rows landed.

Row 5: separate. It is one extra permission and it is the difference between "who can look at
this" and "who can take a copy of this".

---

## 5. Inventory

### Imports

| What | Format | Transaction | Template |
|---|---|---|---|
| | | | |

### Exports

| What | Format | Permission | Audited | Capped at |
|---|---|---|---|---|
| | | | | |

### Known gaps

---

## 6. New-import checklist

1. Define the columns **once**. The parser and the template generator both read that definition.
2. Validate everything, collect every problem with a row and column reference, then write.
3. One transaction, or a written resume story.
4. Set a size limit and enforce it before parsing.
5. Audit the import with the row counts.
6. Test with a file that has a wrong column order, a missing column, an extra column, blank rows,
   and a value of the wrong type.

## 6b. New-export checklist

1. It gets its own permission.
2. It uses the **same query** as the list it exports, tenant scope and row scope included.
3. Cap it, with the true total and a notice.
4. Convert dates to the right calendar. Write identifiers as text.
5. Escape anything that could be read as a formula.
6. Audit it, with the filters and the row count.
7. Add it to §5.

---

## 7. How to re-check this doc

```bash
# Every import and export endpoint. Compare to §5.
grep -rn --include="routes.py" "import\|export\|upload\|download" app/ | grep "@router"
```

```bash
# Export endpoints must be permission-gated and audited.
grep -rn -A10 "export" app/*/routes.py app/*/*/routes.py 2>/dev/null | grep -E "require_permission|_audit"
```

```bash
# Formula injection guard on CSV writers. Expect a guard everywhere a value is
# written from user-supplied text.
grep -rn --include="*.py" "csv.writer\|writerow" app/
```

```bash
# Exports formatting a UTC instant directly rather than converting.
grep -rn --include="*.py" "strftime" app/ | grep -iE "export|report"
```
