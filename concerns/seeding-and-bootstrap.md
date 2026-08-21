# Seeding & Bootstrap

> Read this before you add starter data, a role, or a permission.
>
> **Status in this project:** in force from day 1
> **New in this kit.** Phoenix has one seeding trap that costs an hour every time somebody meets
> it, and it is documented as an aside in three files.
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

Every system needs data before a user can log in. Roles, permissions, an administrator, lookup
catalogues, a default tenant.

Seeding looks trivial and has one property that makes it dangerous: **it usually runs
automatically, and it usually only adds.** So a mistake made once sticks permanently, and on a
development setup that re-seeds on every file save, a mistake made for one keystroke sticks
permanently.

---

## 2. The rules

- **The seed is idempotent.** Safe to run any number of times.
- **The seed reads a catalogue. It does not contain one.** Permissions and roles are defined in a
  catalogue file. The seeder only applies it.
- **Be explicit about what the seed adds, what it updates, and what it never touches.** §3a.
- **Starter data that belongs to the schema goes in a migration.** Starter data that belongs to
  the application goes in the seed. Do not mix them. §3c.
- **A bootstrap administrator with a fixed password is a development tool.** It must be
  impossible to create one in production, or the Part 9 checklist has to catch it.
- **Demo data is never in the same path as required data.** §3d.

---

## 3. The traps

### 3a. The additive seed

**Symptom.** Role grants that contradict the catalogue you are reading. You remove a permission
from a role, restart, and the role still has it.

**Why.** The seeder inserts what is missing and never removes what is extra. That is the safe
default, because removing things automatically is how you delete a customer's configuration.

**Why it bites so hard in development.** If your server reloads on file save, and the reload runs
the seed, then **every save re-seeds**. A permission granted by a half-finished edit is now
permanent. You then read the catalogue, which is correct, and the database, which is not, and the
two disagree with no explanation.

**The fix, and pick one deliberately:**

- **Accept it.** Then document the symptom and the manual fix, prominently, because somebody will
  lose an hour to it. This is what Phoenix does.
- **Reconcile.** The seeder removes grants that are no longer in the catalogue. Now the catalogue
  really is the source of truth, and the risk is that it also removes a grant an administrator
  made deliberately through the UI. That is only safe if the catalogue is the *only* way grants
  are made.
- **Detect.** The seeder does not remove anything, but it **reports** the drift at startup. Ten
  lines, no risk, and it turns an hour of confusion into a log line. **This is the one I would
  build.**

### 3b. Seeding on application start

**Symptom.** Two containers start at once and both seed. Or a slow seed delays every deploy. Or a
failed seed takes the application down.

**Why.** It is very convenient, and it means a fresh environment just works.

**The fix.** Convenient in development, wrong in production. Make it a deliberate step there, like
migrations. And if it does run on start, make it safe against two processes doing it at once.

### 3c. Two seed paths that nobody distinguishes

**Symptom.** A lookup catalogue is missing on one environment and present on another, and nobody
can work out why.

**Why.** Some starter data was seeded by a migration and some by the application seeder. Both are
legitimate. Migration-seeded data arrives with the schema and is versioned with it.
Application-seeded data can be re-run and updated.

**The fix.** Write down which is which, in §5. One line each. It costs nothing and it removes a
whole class of confusion.

### 3d. Demo data mixed with required data

**Symptom.** A sample customer called "Test Client" appears in production.

**Why.** One seed script grew a section for demo data because it was convenient during a client
demonstration.

**The fix.** Separate scripts, separate commands, and demo data is never wired to anything
automatic.

**And note what demo data does to your tests.** Phoenix has two tests that fail on a freshly
seeded database and pass on the next run, because they reach for *a* record rather than pinning
the one they created, and straight after seeding they find the demo's. That is the tests being
wrong, not the seeder. But it is the kind of thing that eats a morning.

### 3e. The test fixture that picks the wrong actor

**Symptom.** A test suite that passes for months starts failing after an unrelated change, with
an error about permissions.

**Why.** A shared fixture selects "a user" with no ordering. Any churn in the users table
silently changes which one, and a non-superuser actor makes every assignment test fail.

**The fix.** Pin it. Select the superuser, exclude deleted rows, and order by creation time. Then
copy that fixture whole rather than writing a new one. → [`testing.md`](testing.md)

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| When the seed runs | on app start, a deploy step, or by hand | | |
| Additive, reconciling, or detecting | | | |
| Where permissions are defined | a code catalogue, or database rows | | |
| Where roles are defined | | | |
| Lookup catalogues | migration, or seed | | |
| Bootstrap admin | how, and how it is prevented in production | | |
| Demo data | a separate script | | |

Row 2: see §3a. Detecting is cheap and I would build it on day 1.

Row 3: a code catalogue means permissions are reviewed like code and deployed like code, and an
administrator cannot invent one. Database rows mean an administrator can, and now you need a
migration path when the code expects a permission that is not there.

---

## 5. Inventory

### What seeds what

| Data | Seeded by | When | Additive or reconciling |
|---|---|---|---|
| Permissions | | | |
| Roles and their grants | | | |
| Lookup catalogues | | | |
| The default tenant | | | |
| The bootstrap admin | | | |

### Where a permission can be registered

If there is more than one path, list every one. A permission missing from the main catalogue is
not proof it does not exist. → [`permissions.md`](permissions.md) §3c

| Path | What belongs there |
|---|---|
| | |

### Known gaps

---

## 6. New-seed-data checklist

1. **Decide whether it is schema data or application data**, and put it in the right path.
2. Make it idempotent. Run it twice in a test.
3. If it is a permission or a role, it goes in the catalogue, not in the seeder.
4. **If you are editing the catalogue on a development database that re-seeds automatically, be
   aware that a half-finished edit sticks.** Check the database afterwards.
5. Never mix it with demo data.
6. Add the row to §5.

---

## 7. How to re-check this doc

```bash
# The seed is idempotent: run it twice and diff the row counts.
python -m app.iam.seed && python -m app.iam.seed
```

```bash
# The seeder should read the catalogue, not contain one. A long literal list here
# means the catalogue moved into the seeder.
wc -l app/iam/seed.py app/iam/permission_catalog.py
```

```bash
# Grants in the database that are not in the catalogue. This is the §3a drift.
# Write it as a script and run it in CI.
```

```bash
# Demo data must not be reachable from anything automatic.
grep -rn "seed_demo\|demo_data" app/ docker/ *.yml 2>/dev/null
```
