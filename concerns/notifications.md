# Notifications

> Read this before you tell somebody that something happened.
>
> **Status in this project:** decide before the first approval workflow
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

When something happens in one module that another person needs to know about, the originating
service raises a notification.

The trap is assuming notifications behave like audit logging. They do not, and the difference is
the opposite of what you would guess. See §2.

The second trap is promising a channel you do not deliver.

---

## 2. The rules

- **Notifications are written inside the caller's transaction. The caller commits.** This is the
  **opposite** of the audit contract, and it is right. A notification and the thing it announces
  commit or roll back together, so there is no "order approved" message for an approval that
  rolled back.
- **Do not await the audit log. Do await the notification write.** Say this out loud when you
  onboard somebody, because the two look identical at the call site.
- **Pass the tenant and the recipient ids explicitly**, until recipient resolution is genuinely
  centralised. §3a.
- **An empty recipient list is a no-op**, so calling unconditionally is safe.
- **Reuse an event type where one fits.** Add one for a genuinely new event.
- **Only deliver channels you actually deliver.** §3b.

---

## 3. The traps

### 3a. Recipient resolution decided at every call site

**Symptom.** Changing who gets notified about approvals means editing five services.

**Why.** Each call site resolves its own recipients, because the central policy path was never
finished.

**The fix.** Decide early. Either recipients come from a policy, resolved centrally by event
type, or they are resolved at the call site and you accept that. What you must not do is have
half a policy engine and call sites that ignore it, which is where Phoenix ended up.

The natural shape is the same as permissions: **the event says what happened, the policy says who
cares.** That is worth building before you have ten call sites, not after.

### 3b. Recording a channel you do not send

**Symptom.** A user says "I never got the email". The record says an email was requested.

**Why.** The channel was recorded on the notification row and nothing dispatches it.

**The fix.** Either send it or do not offer it. If it is genuinely deferred, then the API must
refuse the channel rather than accept it and do nothing. A row that says an email was requested
and none was sent is the notification equivalent of a missing audit entry.

### 3c. Event types ahead of their emitters

**Symptom.** A long enum of event types, half of which never fire.

**Why.** Somebody enumerated the requirements document.

**Why it matters a little.** It is mostly harmless, and it does mislead a reader into thinking a
feature exists. Mark the unwired ones in §5.

### 3d. Notification volume

**Symptom.** Users turn notifications off, so they miss the ones that matter.

**Why.** Every event became a notification because each one was individually reasonable.

**The fix.** A notification needs an action or a decision behind it. "Somebody looked at your
record" is not a notification, it is a log entry. Batch what you can, and prefer a digest for
anything periodic.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Channels | in-app, email, push, SMS | | |
| Which are actually delivered today | | | |
| Recipient resolution | a policy by event type, or explicit at each call site | | |
| Transaction | inside the caller's, or fire-and-forget | | |
| Read state | per recipient row, or a separate read table | | |
| Retention | | | |
| Can a user opt out? | per event type, or not at all | | |

Row 4: inside the caller's transaction is right for anything that announces a business fact.
Fire-and-forget is right for anything advisory. If you have both, name them differently.

---

## 5. Inventory

### Dispatch sites

| Module | Where | Event |
|---|---|---|
| | | |

### Event types with no emitter yet

| Event | Waiting on |
|---|---|
| | |

### Channels recorded but not delivered

| Channel | Status |
|---|---|
| | |

### Known gaps

---

## 6. New-event checklist

1. **Reuse or add an event type.** If you add one, note in §5 whether an emitter exists yet.
2. In the originating service, **inside its transaction**, raise the notification with the
   tenant, the recipients, the event type, a title, and enough identity for the inbox to link
   straight to the record.
3. **Resolve recipients the way §4 says**, not the way the nearest call site does.
4. Request only channels that are delivered.
5. Add the dispatch site to §5.

---

## 7. How to re-check this doc

```bash
# Dispatch sites. Compare to §5.
grep -rn --include="*.py" "notification_service.notify(" app/ | grep -v "notifications/\|test_"
```

```bash
# The notify call must not commit. The caller owns the transaction.
awk '/async def notify\(/,/^\s*async def [a-z_]+\(/' app/notifications/service.py | grep -n "commit" || echo "notify has no commit"
```

```bash
# Channels requested outside the module. Any channel here that is not delivered is
# the §3b trap.
grep -rn --include="*.py" "NotificationChannel\." app/ | grep -v "enums.py\|test_"
```
