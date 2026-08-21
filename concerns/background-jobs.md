# Background Jobs

> Read this before you move work off the request thread, or when debugging a job that did not run.
>
> **Status in this project:** start with nothing in the background
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

Some work must not block the HTTP response. Writing an audit row, cleaning up old data, sending
an email.

The important thing to know about most systems is how little genuinely belongs here. One system I
reviewed ran **two** background tasks in production, across forty modules. Knowing that is worth
more than the framework's documentation, because it is easy to assume a rich pipeline exists when
it does not.

**Background is not free.** A job has no request context, owns its own transaction, fails
silently, and is a second place your code can be running from. Make each case argue for itself.

---

## 2. The rules

- **Dispatch and forget. Never await a job.**
- **A job has no request context.** No tenant, no actor, no IP address. Pass everything it needs
  explicitly. → [`audit-logging.md`](audit-logging.md) §3b
- **A job owns its own session and its own transaction.** The request transaction is long gone.
- **Dispatch *after* the request's commit**, never inside the transaction. A job fired inside a
  transaction that then rolls back still runs, for work that never happened.
- **A dropped job is silent.** If the result matters, that is a design decision, not something to
  discover later. §3a.
- **Anything periodic is registered in one schedule**, and the schedule is in version control.

---

## 3. The traps

### 3a. Nobody knows the job failed

**Symptom.** Nothing. Again, that is the problem.

**Why.** Fire-and-forget means a broker outage or a task failure leaves the business transaction
committed and the follow-up work simply not done. No dead letter, no reconciliation, no alert.

**The fix depends on what the job does.**

- **Genuinely optional work.** Fine. Move on.
- **Work somebody is waiting for**, like an email. It needs retries and a dead-letter queue, and
  somebody has to look at the dead letters.
- **Work that is part of the record**, like an audit entry. It needs a transactional outbox, so
  the row commits with the business action and delivery is a separate concern.
  → [`audit-logging.md`](audit-logging.md) §3a

Write down which category each job is in. That single column in §5 is the whole value of this
file.

### 3b. The unmaintained rollup table

**Symptom.** A summary panel shows figures for some months and not others, beside a list full of
data.

**Why.** A pre-aggregated summary table exists. It was written as a side effect of something else
running, or by a job that was never actually scheduled. One codebase had both at once: a summary
table written only as a side effect of running payroll, and a second written by nothing at all,
because the task existed but appeared in no schedule and had no route.

**The general rule this is an instance of: before building a figure on a pre-aggregated table,
check what writes it and when.** A summary table with no live writer is worse than no summary
table, because it looks authoritative.

**And even a maintained one is always some window out of date.** If the panel sits beside a list
of the raw rows, read the raw rows. → [`analytics.md`](analytics.md)

### 3c. The job that loops over tenants and gets the day wrong

Covered in [`dates-and-timezones.md`](dates-and-timezones.md) §3c. Take "yesterday" inside the
loop, from that tenant's zone. Tenants in distant zones resolve different days in the same run.

### 3d. Complete infrastructure that nothing uses

**Symptom.** A 300-line circuit breaker, re-exported twice, with zero call sites.

**Why.** It was written for a need that was real and then the need moved. In the case I saw, it
was written synchronous, for jobs calling external services, and the place it was actually wanted
was an async cache read it could not wrap.

**The fix.** Either connect it or delete it. Dead infrastructure is worse than none, because the
next person assumes the problem is solved.

### 3e. Two connection pools, one process

Some database drivers are not safe across a process fork. A worker that forks needs to build its
own engine per process rather than inheriting the web app's. This is easy to get wrong with async
Postgres drivers, and the failure is confusing rather than obvious.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Do we need a queue at all? | **start with no** | | |
| Queue | a real broker, or the framework's in-process tasks, or database rows | | |
| Retries | per job, with a written policy | | |
| Dead letters | where they go and who looks | | |
| Is there an outbox for anything? | | | |
| Periodic schedule | in code, or in the scheduler's own config | | |
| How do we know a job failed? | | | |

Row 2: framework-level in-process background tasks are enough for genuinely fire-and-forget work
and die with the process. A real broker survives a restart and costs you a service to run. Rows
in a table you poll is the boring answer and it works surprisingly far.

Row 7 is the one people skip. Answer it before the first job, not after the first silent failure.

---

## 5. Inventory

### What actually runs

| Task | Trigger | Job | If it fails |
|---|---|---|---|
| | | | |

Keep this list complete. Its value is that a reader can trust "that is the whole list".

### Where work is deliberately not backgrounded

| Not backgrounded | Why |
|---|---|
| Document generation | the user waits once and reprints are instant |
| | |

### Known gaps

---

## 6. New-job checklist

1. **Ask whether it should be a job at all.** Most work belongs in the request. Background it only
   if the user genuinely should not wait, or it is periodic.
2. Put it in the owning module.
3. **Pass everything explicitly.** Actor, tenant, ids. There is no request context inside a job.
4. Dispatch from the service, **after** its commit. Never await.
5. **Decide how you will know it failed**, and write that in §5.
6. For a periodic task, add it to the one schedule, and check it is actually registered.
7. Add it to §5. The "that is the whole list" claim depends on it staying current.

---

## 7. How to re-check this doc

> Paths below are examples from one tree. Adjust them to yours. What matters is the check,
> not the path. Where a count is given, it is the count **for this project**, so fill it in
> the first time you run it.

```bash
# Every dispatch in the codebase. Compare to §5.
grep -rn --include="*.py" "\.delay(\|\.apply_async\|add_task(" app/ | grep -v "test_"
```

```bash
# The periodic schedule. Every scheduled task should exist, and every periodic
# task should be scheduled. Check both directions.
grep -n "beat_schedule\|crontab\|schedule" app/core/background/celery_app.py
```

```bash
# Tasks defined but never scheduled and never dispatched. These are the §3b trap.
# Compare the task decorator list against the two greps above.
grep -rn --include="*.py" "@db_task\|@simple_task\|@shared_task" app/
```
