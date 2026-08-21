# Caching

> Read this before you add a cache, change a lifetime, or debug stale data.
>
> **Status in this project:** most projects need no cache at all
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

**Start from the position that you do not need a cache.**

A cache buys you speed and charges you an invalidation contract on every write, forever. Most new
projects are nowhere near needing that trade. Phoenix has forty modules and three server-side
caches, and one of those is not really a cache.

There are usually three different things people call caching, and confusing them is the main
source of trouble:

1. **A shared server cache**, for a small number of read-heavy lists.
2. **Stored generated files**, where a document is written once and served again. The "cache key"
   is a fingerprint in the storage path.
3. **The client's query cache**, holding responses in the browser.

Most "stale data" complaints come from the third. Most silent correctness bugs come from the
second. The first is the one people reach for and usually should not.

There is a fourth thing that *looks* like caching and is not. Caching a constructed object on a
dependency factory is object reuse, not data caching. It holds a service instance, never a row.
It is safe.

---

## 2. The rules

- **Every server cache honours one kill switch.** A switch that only turns off some of the caches
  is worse than none, because it is the first thing you reach for when you suspect staleness in
  production and it has to be trustworthy.
- **A write that changes a cached list clears it *after* the commit**, never before. Clearing
  before lets a concurrent read re-cache a value that a rollback would erase.
- **Never cache anything that gates access.** Permission checks and the authenticated user stay
  on the database. Staleness there is a security bug, not a performance trade.
- **Never cache a read that immediately follows a write in the same request.** You will serve the
  pre-write value and re-cache it. The cache poisons itself.
- **Never cache a miss.** A cached negative result makes a just-created record invisible for a
  full lifetime.
- **Version the key namespace.** Put `v1` in the key so a change to the stored shape cannot
  deserialise stale data. Bump it rather than risk a bad parse.
- **Cache keys carry the tenant id** wherever the data is scoped, and the resolved user scope
  wherever the query narrows per user. §3d.
- **If a generated file reads a row live, that row is in the fingerprint.**
  → [`snapshots-vs-live.md`](snapshots-vs-live.md)

---

## 3. The traps

### 3a. The cache that makes things slower when it is down

**Symptom.** The cache server goes down and the whole application crawls. It does not fail, which
somehow makes it worse.

**Why.** Every read starts with "if not connected, connect". When the server is unreachable that
flag never flips, so **every** call re-attempts a connection against a five-second timeout. There
is no failure memory and no backoff.

Phoenix measured the worst case: a screen resolving twenty names spent **about 100 seconds**
before falling back to a database query that takes milliseconds.

**The fix.** Connect once at startup. Remember failure and back off. And take the loop apart while
you are there, because a per-id loop against a cache should almost always be one multi-key read.

### 3b. Invalidation that scans the whole keyspace

**Symptom.** Nothing, until the keyspace grows. Then everything stalls at once, including things
that have nothing to do with the cache.

**Why.** Clearing by pattern usually means listing every key on the server, which **blocks the
whole server** while it runs. If it fires on every user write, you have a scheduled outage
waiting for a data volume.

**The fix.** Scan with a cursor, or track the keys you wrote in a set so invalidation is one read.

### 3c. Documenting an API nobody uses

**Symptom.** Somebody follows the README, uses the decorator it recommends, and every filter
combination shares one cache key. They serve each other's results.

**Why.** A generic caching decorator was written, documented, and never used. Its key builder
silently skipped any argument that was an object, so a function taking a filter object got one
key for everything.

**The fix.** Delete unused API surface rather than fixing it. If your README recommends a pattern
with zero call sites, the README is a trap.

### 3d. The scope-shaped key leak

**Symptom.** One user sees another user's numbers.

**Why.** A cached list narrows per user, and the key carries the tenant but not the scope.

**The fix.** If you ever cache something that narrows per user, the key carries the tenant id,
**which** user's rows it was narrowed to, and any period parameters. A key missing the scope is a
data leak, not a cache bug.

### 3e. Client cache keys that are not tenant-scoped

**Symptom.** Switching tenant shows the previous tenant's rows for a beat. In a multi-tenant
business that reads as a leak, and users report it as one.

**Why.** The active tenant travels as a header, not as part of the query key, so both tenants
share one cache entry.

**The fix, and there are two levels.**

- **Proper:** put the tenant id in every query key factory.
- **Working:** on switch, **remove** the cached queries rather than invalidating them.
  Invalidating refetches *mounted* queries and leaves unmounted data in place, which is exactly
  the rows the next screen renders.

And be honest about the third thing: the query cache was never the only place tenant data
settled. Component state, stores, URL state and anything computed once on mount all survive a
cache clear. A full page reload is the only thing that clears all of it at once. Confirm first,
because a switch throws away unsaved work.

### 3f. Two hashes that answer different questions

If your documents have revisions, you may need **two** fingerprints and they are not
interchangeable.

- **The storage token** decides whether to re-render. Over-invalidating is right here. A needless
  re-render costs one file.
- **A content hash over only what prints** decides whether a re-render counts as a **new issue**.
  Over-invalidating is wrong here. It puts a higher issue number on a customer's document because
  somebody fixed a typo in an internal note.

Keep them separate and name them differently.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Do we have a server cache at all? | **start with no** | | |
| The kill switch | one flag every cache honours | | |
| What is cacheable | write the list, and keep it short | | |
| Key format | | | |
| Lifetime tiers | pick three or four, not a number per call site | | |
| Jitter on the lifetime | yes, so keys do not all expire together | | |
| Client cache lifetimes | one small set of tiers | | |
| Are rate-limit counters part of the cache? | they are **state**, so exempt from the kill switch | | |

Row 8 is not a detail. If the throttle counters honour the cache kill switch, then flipping that
switch to debug staleness silently disables your login throttle.

---

## 5. Inventory

### Server cache consumers

| Where | What | Key shape | Lifetime | Cleared by |
|---|---|---|---|---|
| | | | | |

### Stored generated files

| Consumer | Document | Fingerprint covers | Token lives in |
|---|---|---|---|
| | | | |

### Client lifetime tiers

| Tier | Used by | Why |
|---|---|---|
| | | |

### Where caching is deliberately not used

| Not cached | Why |
|---|---|
| Permission checks | the result gates access. A stale grant is a hole |
| The authenticated user | same reason. A deactivated user must stop working immediately |
| A read following a write in the same request | it serves the pre-write value and re-caches it |
| Searched lists | the search term is too variable. The cache fills with single-use keys |
| Misses | a cached miss makes a new record invisible for a full lifetime |
| | |

### Known gaps

---

## 6. New-module checklist

Most new modules need **no cache at all**. Add one only when a list is read on nearly every screen
and is safe to serve slightly stale. Then:

1. **Decide it is cacheable.** Not if it gates access. Not if it is read straight after a write.
   Not if it is per-user-search.
2. **Copy the shape from an existing one.** Read-through, plain data rather than ORM objects, a
   versioned namespace, jitter on the lifetime.
3. **Honour the kill switch**, explicitly.
4. **Put the tenant id in the key**, and the user scope if the query narrows per user.
5. **Clear it after the commit**, in the service, in the same method that owns the transaction.
   Never inside the transaction, never in the data-access layer.
6. Do not cache misses.
7. If the module generates a document, list every row it reads live in the fingerprint.
8. On the client, pick a lifetime tier rather than inventing a number.
9. Add a row to §5 in the same change.

---

## 7. How to re-check this doc

```bash
# Cache consumers. Compare to §5.
grep -rln --include="*.py" "from app.core.cache import" app/ | grep -v "app/core/cache/"
```

```bash
# Everyone who honours the kill switch. Every consumer must appear.
grep -rln --include="*.py" "CACHE_ENABLED" app/ | grep -v "core/settings.py"
```

```bash
# Nothing that gates access may appear here. Expect zero.
grep -rn --include="*.py" "cache" app/iam/permission/ app/iam/auth/current_user.py
```

```bash
# Client lifetime tiers. Compare the counts to §5.
grep -rho --include="*.ts" --include="*.tsx" "staleTime: [^,]*" src/ | sort | uniq -c | sort -rn
```

```bash
# Client tenant-switch handling. Removing queries and reloading must both appear.
# A bare invalidate in the switcher is the §3e bug.
grep -n "removeQueries\|invalidateQueries\|location.reload" src/components/*/tenant-switcher.tsx
```
