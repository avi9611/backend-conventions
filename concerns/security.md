# Security — the hub

> Read this before you touch auth, sessions, tokens, uploads, or anything deciding who can do
> what.
>
> **Status in this project:** in force from day 1
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

**This file is the map, not the territory.** Security is spread across mechanisms that each have
their own home. This page lists every control, says where it lives, and points at the detailed
file. Start here, then follow the link for the one you are touching.

Security is not one module. It is a set of controls at every layer. The front door (auth,
throttles). The request (permissions, tenant isolation). The data (snapshots, audit). The
transport (cookies, headers). The deployment (CORS, trusted hosts, secrets).

Keeping them findable is what stops a change to one quietly weakening another.

---

## 2. The rules, each owned elsewhere

- **Never cache a permission check or the authenticated user.** Staleness there is a security
  bug. → [`permissions.md`](permissions.md), [`caching.md`](caching.md)
- **Throttle the unauthenticated front door, keyed on identity and not on IP.**
  → [`rate-limiting.md`](rate-limiting.md)
- **The wrong-tenant answer is 404, not 403.** A 403 confirms the record exists.
  → [`tenancy-and-scoping.md`](tenancy-and-scoping.md)
- **Tokens live in httpOnly cookies, never where JavaScript can read them.** §3a.
- **Passwords are hashed with a slow, salted algorithm, and validated by exactly one rule.**
  Never hand-write a length limit on a password field somewhere else.
- **Setting a password ends every session on that account.** A password change that leaves old
  sessions alive is not a password change.
- **Never forward a caller-set hop header.** § 3c.
- **Every mutation is audited, after the commit.** → [`audit-logging.md`](audit-logging.md)
- **No error response ever contains a stack trace.**
  → [`error-handling.md`](error-handling.md)

---

## 3. The traps

### 3a. Where the token lives

**The pattern worth copying.** The browser talks to a server you control. That server holds the
token in an httpOnly cookie and calls the API on the user's behalf. The token never enters
JavaScript, so an injected script cannot read it.

**What it costs.** Every request goes through an extra hop, which brings §3b and §3c with it.

**The alternative** is a token in browser storage, where any injected script can take it. That is
a real trade and plenty of systems make it. What you should not do is make it by accident.

### 3b. Every request arrives from one address

If you use the pattern above, **every request reaches your API from that server**, not from the
user's browser.

Two consequences, both load-bearing:

- **A per-IP limit is a company-wide limit.** One office hitting the login page throttles
  everybody. → [`rate-limiting.md`](rate-limiting.md)
- **The audit IP is the proxy's, not the user's.** Do not build a control that assumes it
  identifies a person.

### 3c. The forwarded header you must not forward

**Symptom.** A caller sets a header claiming to be a different IP address, and your throttle and
your audit trail believe them.

**Why.** A proxy that copies incoming headers wholesale forwards the caller's own
`X-Forwarded-For` and `X-Real-IP` along with everything else. Those are exactly the headers your
IP resolver trusts.

**The fix.** Strip them at the proxy, and read the *last* hop rather than the first. A proxy
appends, so the first entry is the caller-set part.

### 3d. Security headers set in a layer that never sees the page

**Symptom.** A scanner reports missing headers on the dashboard, and everybody points at the
config that does set them.

**Why.** The reverse-proxy config sets headers for the API host, and the browser-facing
application is served by something else entirely. The header block never reaches it.

**The fix.** Know which layer serves which surface, and set headers there. Write it down here.
Do not delete a header block assuming a proxy covers it.

**And note that a JSON API and a browser application want different policies.** An API can be as
strict as it likes. An application that loads any script needs a real policy. Documentation pages
that load assets from elsewhere need an exemption, and that exemption must be **cut out of the
catch-all rule, not appended after it**, or it does nothing.

### 3e. The development convenience carried into production

Three of these, and all three are one copied environment file away:

| Setting | In development | In production |
|---|---|---|
| A public storage domain | maps an internal hostname so links work | turns every file link into a permanent public URL |
| A bootstrap admin with a fixed password | convenient | a known account with a known password |
| API documentation open | how you work | a map of your whole API |

**The fix.** They go in the pre-production checklist, and each one gets a startup assertion where
you can write one. A production build that refuses to start with a development setting on is a
much better outcome than one that starts.

### 3f. The password length nobody expects

Most bcrypt implementations hash only the **first 72 bytes** of a password and silently ignore
the rest. So a password policy that allows longer is not enforcing what it claims.

Cap the length in the policy, in the one place the policy lives, and note why.

### 3g. Registration you did not mean to have

If accounts are created by an administrator, then say so, remove any self-registration route, and
put a check in §7. Otherwise somebody adds one back, reasonably, because the framework template
had one.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Token storage | httpOnly cookie via a server hop, or browser storage | | |
| Access token lifetime | | | |
| Refresh token lifetime, and rotation | | | |
| Password hashing | bcrypt, argon2 | | |
| Password policy | one rule, in one file | | |
| Self-registration | yes, or admins create accounts | | |
| Self-service password change | yes, or admin reset only | | |
| Multi-factor | now, later, never | | |
| Session revocation | on password change, on role change, on demand | | |
| API docs in production | off, or behind auth | | |
| CORS origins | an explicit list | | |
| Who sets security headers | | | |

Row 3: rotation means each refresh issues a new refresh token and invalidates the old one. It
turns a stolen refresh token into a detectable event, because the real user's next refresh fails.

Row 9: on role change is the one people forget. If you revoke somebody's permissions and their
existing token still works for two hours, you did not revoke them. This interacts directly with
"never cache the permission check".

---

## 5. Inventory — where each control lives

### Authentication
| Control | Where |
|---|---|
| Password hashing | |
| Password policy | |
| Bootstrap admin | |
| Self-registration | |

### Tokens and sessions
| Control | Where |
|---|---|
| Access token lifetime | |
| Refresh, logout, logout-all | |
| Revoke-all on password change | |

### Authorisation
| Control | Where |
|---|---|
| Route gates | → [`permissions.md`](permissions.md) |
| Row-level scope | → [`permissions.md`](permissions.md) |
| Tenant isolation | → [`tenancy-and-scoping.md`](tenancy-and-scoping.md) |

### Transport
| Control | Where |
|---|---|
| Cookie flags | |
| Hop-header stripping | |
| Security headers, browser pages | |
| Security headers, API | |

### Data
| Control | Where |
|---|---|
| Parameterised queries and escaped search | → [`pagination-and-search.md`](pagination-and-search.md) |
| Optimistic locking | → [`concurrency.md`](concurrency.md) |
| Upload validation | → [`object-storage.md`](object-storage.md) |
| Audit trail | → [`audit-logging.md`](audit-logging.md) |

### Where controls are deliberately relaxed

| Relaxed | Why |
|---|---|
| Per-IP login throttle removed | behind one proxy it caps the whole company. The per-identity throttle does the real work |
| Client-side permission checks | a convenience, not a boundary. The API enforces |
| A platform-operator bypass | intentional. Never granted to a business role |
| | |

### Known gaps

Keep the security backlog here, consolidated, with a pointer to the file that owns each one.
Also keep a **closed** list, so a stale audit read does not reopen something already fixed.

---

## 6. Doing something security-touching — where to go

| You are about to… | Read |
|---|---|
| add a route, or a row-scope distinction | [`permissions.md`](permissions.md) |
| add an unauthenticated endpoint | [`rate-limiting.md`](rate-limiting.md) |
| touch login, tokens or cookies | this file §3a, plus your auth module |
| accept a file upload | [`object-storage.md`](object-storage.md) |
| let two people edit one record | [`concurrency.md`](concurrency.md) |
| change what an issued document shows | [`snapshots-vs-live.md`](snapshots-vs-live.md) |
| add a setting or a secret | [`configuration-and-secrets.md`](configuration-and-secrets.md) |
| deploy | Part 9 of [`../CHECKLIST.md`](../CHECKLIST.md) |

---

## 7. How to re-check this doc

> Paths below are examples from one tree. Adjust them to yours. What matters is the check,
> not the path. Where a count is given, it is the count **for this project**, so fill it in
> the first time you run it.

```bash
# Password hashing and the single policy. Expect the policy type on every password
# field and zero hand-written length limits elsewhere.
grep -rn "CryptContext\|schemes=" app/iam/auth/tokens.py
grep -rn "PasswordStr" app/iam/
grep -rn "password.*min_length=" app/iam/ || echo "no hand-written password length"
```

```bash
# Setting a password ends the account's sessions. Expect a hit in both the
# self-service and the admin-reset paths.
grep -rn "revoke_all" app/iam/
```

```bash
# Client: tokens in httpOnly cookies, never in browser storage.
grep -rn "httpOnly" src/app/api/auth/
grep -rniE "localStorage\.(set|get)Item\([^)]*(token|jwt|auth)" src/ || echo "no token in browser storage"
```

```bash
# The proxy must not forward caller-set hop headers.
grep -n "x-forwarded\|x-real-ip" src/proxy.ts
```

```bash
# Self-registration must not exist, if that is the decision.
grep -rn "\"/register\"\|'/register'" app/ || echo "no self-registration"
```

```bash
# Security headers on browser pages. Know which file is the only source.
grep -n "Content-Security-Policy\|X-Frame-Options" next.config.ts
```
