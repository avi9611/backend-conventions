# Observability

> Read this before you log something, and before the first time you need to work out what
> happened in production.
>
> **Status in this project:** in force from day 1
> **New in this kit.** Phoenix has a logger and no document about it. This is the gap that hurts
> at 2am.
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

Everything else in this kit is about preventing bugs. This one is about the ones that get
through.

The question you will actually be asked is: **"a user says the invoice they created this morning
is wrong. What happened?"** Answering that needs three things, and if you did not build them in
advance you cannot retrofit them for that request.

- **A request id** that ties every log line, error and audit row for one request together.
- **Enough context on each line** to filter without guessing. Who, which tenant, which record.
- **The audit trail**, which is a separate thing with its own rules.
  → [`audit-logging.md`](audit-logging.md)

The temptation is to skip this because nothing is broken yet. The cost of skipping it is paid
entirely during incidents.

---

## 2. The rules

- **One logger factory.** No module configures logging itself.
- **Every request gets an id**, generated at the edge, put on the response, and attached to every
  log line for that request.
- **Log structured fields, not sentences with values in them.** You will want to filter by tenant
  id, and you cannot filter a sentence.
- **Never log a secret, a password, a token, or a full request body that could hold one.** §3a.
- **Never log personal data you would have to delete on request.** §3a.
- **An error log carries the stack trace. A response never does.**
  → [`error-handling.md`](error-handling.md)
- **Log at the boundary, not at every step.** §3c.
- **The health endpoint checks what it claims to check.** §3d.

---

## 3. The traps

### 3a. The log that becomes a data-protection problem

**Symptom.** Somebody asks for their data to be deleted. You delete the rows. Their name, email
and address are still in six months of log files, in a service you do not control.

**Why.** Somebody logged the whole request body during a debugging session, and it stayed.

**The fix.**

- A denylist of field names that are redacted before a line is written. Password, token, secret,
  key, authorisation. Do it centrally, not at each call site.
- Log **ids**, not values. `client_id=...` rather than the client's name and address.
- Set a retention period on logs, and know what it is.
- Never log a full request or response body outside a debug level that is off in production.

### 3b. The log line you cannot filter

**Symptom.** You have the logs and you still cannot answer the question, because finding one
user's requests means a text search that also matches unrelated lines.

**Why.** `logger.info(f"Created invoice {inv.number} for {client.name}")`.

**The fix.** Structured fields:

```python
logger.info("invoice.created", extra={
    "request_id": ctx.request_id,
    "tenant_id": str(ctx.tenant_id),
    "user_id": str(user.id),
    "invoice_id": str(inv.id),
})
```

The message becomes a stable event name you can count. The values become fields you can filter.

### 3c. Logging every step

**Symptom.** Gigabytes of logs and it is still hard to find anything.

**Why.** Every function logs its entry and exit, because that felt thorough.

**The fix.** Log at boundaries. A request in, a request out with its status and duration. A call
to an external service and its result. A job starting and finishing. Anything unexpected. That is
usually the whole list.

Inside a request, the audit trail records what changed. The log does not need to duplicate it.

### 3d. The health check that is always healthy

**Symptom.** The load balancer says everything is fine. Nothing works.

**Why.** The health endpoint returns a fixed response and never touches the database.

**The fix.** Two endpoints with different jobs:

- **Liveness.** Is the process alive? Cheap and fixed. Restarting on a failure here is correct.
- **Readiness.** Can it serve? Checks the database with a short timeout, and the cache if the
  application cannot work without it. Removing from the pool on a failure here is correct.

**Do not check every dependency in the liveness probe.** A cache outage should not make an
orchestrator restart every one of your containers.

### 3e. Metrics you listed and never wired

**Symptom.** A metrics library in your dependency list, a metrics module in your documented
project structure, and no metrics module in the repository.

**Why.** Somebody planned it from a template.

**The fix.** Either wire it or take it out of both lists. An aspirational entry in a project
structure document is the same class of lie as a stale doc.

### 3f. No slow-query visibility

**Symptom.** The application gets slower over months and nobody can say which endpoint.

**The fix.** Request timing middleware that records duration per route, and a log line above a
threshold. That is one middleware and it is the cheapest performance tooling there is.

And note the lesson from [`analytics.md`](analytics.md) §3g: **measure before optimising.** Three
of four "obvious" optimisations there turned out to solve problems that did not exist.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Log format | plain text, or JSON | | |
| Where logs go | files, stdout, or a service | | |
| Retention | | | |
| Request id | generated, or accepted from the caller | | |
| Levels, and what each means | | | |
| Metrics | none, an endpoint to scrape, or a service | | |
| Error tracking | none, or a service | | |
| Tracing | none, or distributed tracing | | |
| Health probes | liveness and readiness | | |
| Redaction list | | | |

Row 1: JSON to stdout is the default answer for anything containerised, because the platform
collects it. Plain text files are easier to read on one machine and harder to search across many.

Row 4: accepting an id from the caller lets you follow a request across services, and lets a
caller inject one. Accept it, validate the shape, and generate one when it is missing.

Row 7: error tracking is the highest value item on this list for a small team. It turns "somebody
reported something" into a grouped, counted stack trace with the request context attached.
Cheaper than the time it saves in the first month.

---

## 5. Inventory

### What is wired

| Capability | Where | Notes |
|---|---|---|
| Logger factory | | |
| Request id | | |
| Request timing | | |
| Health, liveness | | |
| Health, readiness | | |
| Metrics | | |
| Error tracking | | |

### The redaction list

| Field name pattern | |
|---|---|
| | |

### Known gaps

---

## 6. New-module checklist

1. Use the shared logger factory. Do not configure logging.
2. Log at the boundaries only. The audit trail covers what changed.
3. Structured fields, with the request id, the tenant and the record id.
4. Never log a value the redaction list would have caught. Log ids.
5. If the module calls an external service, log the call and its outcome, and think about what
   happens when that service is slow.

---

## 7. How to re-check this doc

```bash
# Modules configuring logging themselves. Expect zero.
grep -rn --include="*.py" "logging.basicConfig\|logging.getLogger(" app/ | grep -v "core/logging.py"
```

```bash
# Log lines built by string interpolation instead of structured fields. Read the hits.
grep -rn --include="*.py" 'logger\.\(info\|warning\|error\)(f"' app/
```

```bash
# Anything that could log a secret. Expect zero.
grep -rniE "logger\.[a-z]+\(.*(password|token|secret|authorization)" app/
```

```bash
# The request id is attached at the edge and reaches the logger.
grep -rn "request_id" app/core/middleware.py app/core/logging.py
```

```bash
# The health endpoints do what they claim.
grep -rn -A15 "def health\|/health" app/core/main.py
```
