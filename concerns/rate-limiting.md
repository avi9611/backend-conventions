# Rate Limiting

> Read this before you add a route that is not behind a permission.
>
> **Status in this project:** needed as soon as you have a login endpoint
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

The authenticated application is protected by permissions. The **unauthenticated front door** is
protected by rate limiting instead, because there is no user to check yet. Login,
forgot-password, token refresh.

Getting this wrong means either password guessing goes unthrottled, or a legitimate office gets
locked out all at once.

**One deployment fact changes the whole design.** If the browser talks to a server that talks to
your API, then every request reaches you from that one address.

---

## 2. The rules

- **Throttle every route that is not behind a permission check.** An unguarded, unthrottled route
  is an open door.
- **Key the throttle on an identity, never on an IP address.** An email, an account, a token
  subject. §3a.
- **Rate-limit counters are state, not cache.** They are the one thing exempt from the cache kill
  switch. → [`caching.md`](caching.md)
- **The throttle fails open.** If the counter store is down, requests pass rather than locking
  everybody out.
- **Never read the first entry of a forwarded-for header.** A proxy appends, so the first hop is
  caller-set and forgeable.
- **Use a fixed window, and set the expiry on the first failure.** Refreshing it each time
  somebody tries makes the window slide forward forever, so a patient attacker is never released
  and never blocked.

---

## 3. The traps

### 3a. The per-IP limit that is really a global limit

**Symptom.** One office cannot log in. Everybody there sees "too many attempts", including people
who typed their password correctly the first time.

**Why.** Behind a single proxy, "per IP" means "per company".

**The fix.** Key on the identity being attempted. A per-email failure counter is IP-independent,
so the proxy cannot weaken it, and one person's typos cannot lock out their colleagues.

Systems behind a proxy end up removing their per-IP login and refresh limits for exactly this
reason.

### 3b. The one place a per-IP limit is still right

Forgot-password. It is global on purpose, it is a rare flow, and it exists to stop somebody
flooding an inbox. It is not there to identify a caller.

Be explicit about which of your limits are identity-keyed and which are global, and why. Two
different jobs.

### 3c. The kill switch that disables your throttle

**Symptom.** Somebody flips the cache flag off to debug staleness in production, and the login
throttle silently stops working.

**Why.** The counters live in the cache, so they honoured the cache flag.

**The fix.** Rate-limit counters are **state**. They get their own flag, and they never honour
the cache one.

### 3d. Fail open or fail closed

If the counter store is unreachable, do requests pass or fail?

**Fail open** means an outage in your cache is not an outage in your login. And it means the
throttle is off during that outage.

**Fail closed** means nobody can log in when the cache blinks.

For a business system, fail open. For something holding money, think harder. Either way, write
down which, and alert on the store being down, because the failure is otherwise invisible.

### 3e. Not resetting on success

**Symptom.** A user with a bad memory locks themselves out mid-morning even though they got in at
nine.

**Why.** The failure counter was never reset on a successful sign-in.

**The fix.** One line. Easy to forget.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| What is throttled | write the list | | |
| Login throttle key | identity, or IP, or both | | |
| Failure threshold and window | | | |
| Behaviour at the limit | refuse, delay, or lock the account | | |
| Counter store | the cache, or the database | | |
| Fail open or closed | | | |
| Is there a global request limit? | at the proxy, or none | | |

Row 4: locking the account turns a throttle into a denial-of-service tool against a named user,
because anybody who knows their email can lock them out. A refusal with a window is usually
better.

Row 7: an application-level throttle is not a defence against volume. If you need one, it belongs
at the proxy or the CDN, before your process is involved.

---

## 5. Inventory

### The controls

| Control | Keyed on | Where | What it is for |
|---|---|---|---|
| | | | |

### Where throttling is deliberately not applied

| Not throttled | Why |
|---|---|
| Authenticated routes | protected by permissions, not rate limits |
| | |

### Known gaps

---

## 6. New-unauthenticated-route checklist

1. **Ask first whether it should be authenticated.** Most things should not be on the front door.
2. If it genuinely must be public, add a throttle **keyed on an identity**, never on the client
   address.
3. Gate it on the rate-limit flag, not the cache flag, and make it fail open.
4. Give it a named exception, not an inline error. The rate limiter is one of the few files
   allowed inline ones. Your route is not.
   → [`error-handling.md`](error-handling.md)
5. Add it to the ungated allow-list with a reason.
   → [`permissions.md`](permissions.md)

---

## 7. How to re-check this doc

> Paths below are examples from one tree. Adjust them to yours. What matters is the check,
> not the path. Where a count is given, it is the count **for this project**, so fill it in
> the first time you run it.

```bash
# The rate limiter's public surface.
grep -n "^def \|^async def \|^class " app/core/rate_limit.py
```

```bash
# Who calls the throttle. Compare to §5.
grep -rln --include="*.py" "check_identity_throttle\|RateLimit(" app/ | grep -v "rate_limit.py\|test_"
```

```bash
# A new per-IP limiter. Outside the rate limiter, the client-address helper should
# appear only where an address is captured for AUDIT, never for throttling.
grep -rn --include="*.py" "client_ip(" app/ | grep -v "rate_limit.py"
```

```bash
# The counters must not honour the cache flag.
grep -n "RATE_LIMIT_ENABLED\|CACHE_ENABLED" app/core/rate_limit.py
```
