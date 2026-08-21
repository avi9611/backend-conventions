# Object Storage & Attachments

> Read this before you upload, download or attach a file.
>
> **Status in this project:** decide before the first upload
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

Every file the system holds lives in object storage, reached through **one** service, and is
tracked by a row in your database.

The two must stay in step. An object nobody can reach, and a row pointing at a deleted object,
are both bugs.

That row is also the tenant-scoped, audited record of *what file belongs to what*. Which is why
deleting a file is an authorisation decision, not a filesystem operation.

---

## 2. The rules

- **Go through one storage client.** Never construct a second one anywhere.
- **Every stored file has a row** carrying what it belongs to, the tenant, the storage key, a
  checksum and the human filename. One named exception, in §3d.
- **Deleting requires the owning type *and* the owning id**, as required arguments. A tenant
  check alone is not authorisation. §3a.
- **A reprint serves the stored file** through an expiring link. Never regenerate a stored
  document on download. → [`caching.md`](caching.md)
- **The download filename is what the recipient's browser saves.** Clean and human. The cache
  token goes in the storage *key*, never in the filename.
- **Serialise concurrent generation of the same document**, or two downloads render twice.
- **A file backing a controlled document is marked protected and can never be removed.** §3c.
- **A public bucket domain is a deployment rule, not a preference.** §3b.

---

## 3. The traps

### 3a. Delete authorised by tenant alone

**Symptom.** A user with permission to edit one kind of record deletes a file belonging to
another kind.

**Why.** The delete checked only that the attachment was in the caller's tenant. In a shared
attachments table that is barely a filter.

**The fix.** Make the owning type and id **required keyword arguments**, so no caller can forget
them. Not optional with a default. Required.

### 3b. The public domain that turns every link into a permanent URL

**Symptom.** Nothing, until somebody notices that a document URL works without logging in, and
keeps working.

**Why.** A setting exists that rewrites signed links into plain links on a public domain, with no
expiry and no signature. It is genuinely useful in development, where it maps an internal
container hostname to something a browser outside the network can reach. And it is exactly the
kind of setting that gets carried into production by copying a working environment file.

**Why it is worse than it sounds.** If your storage keys are deterministic, which they are for
controlled documents, then a public domain plus a known document number is a readable URL for
anyone who has ever seen one.

**The fix.**

- **Production: leave it blank.** Expiring signed links are the access control.
- If a CDN is genuinely wanted, it fronts a **separate public bucket** holding only
  non-confidential assets. Never the bucket documents live in.
- Put it in the pre-production checklist. → [`configuration-and-secrets.md`](configuration-and-secrets.md)

### 3c. Protected files, and why the refusal is loud

A file backing a controlled document is marked protected at creation, and nothing clears the
mark.

| Path | Behaviour on a protected file |
|---|---|
| delete one | refuse with a conflict |
| replace all (the "swap this entity's file" path) | refuse, and **spare every file in the sweep**, protected or not |
| purge after commit | skip it and log a warning |

**Why the replace path refuses the whole call rather than sweeping around it.** Reaching a
protected file there means the caller believes it owns a one-file-per-entity record that actually
holds a controlled document. **That belief is the bug.** Deleting the *other* files while acting
on it makes the damage real before anybody notices.

**Why the post-commit purge skips instead of refusing.** It runs after the commit. Raising there
fails a request whose work already succeeded. The loud refusal belongs where the transaction can
still be aborted.

A consumer that legitimately keeps history filters the list itself, rather than reaching for the
replace-all path.

### 3d. Identity assets are a column, not an attachment row

Two kinds of file break the "every file has a row" rule on purpose. A user's signature image. An
organisation's letterhead and logo.

They are not documents *about* an entity. They are **part of the entity's identity**. Exactly one
per slot, replaced rather than accumulated. An attachment row would model a collection where
there is a single value, and would put "which one is current?" in a second place that can
disagree with the first.

Four rules follow, and a third such asset must copy them:

- **The key is derived from the owner**, with no date path and no random suffix, so a replacement
  overwrites in place. Safe only because the owner's id is never re-issued.
- **The old object is deleted after the commit, never before**, and only when the key actually
  changed. Deleting first means a failed write leaves the row pointing at nothing.
- **The key never leaves the server.** Responses carry a presence flag and a freshly signed link,
  generated per request and applied *after* the response is built. **Never bake a signed link
  into a cached or stored response.** It outlives its own signature inside the cache and starts
  failing part-way through the lifetime, on an image nobody can force to refresh.
- **Validate at upload, because nothing revalidates later.**

### 3e. Deterministic keys, and when they are safe

By default a storage key gets a random suffix, so the path is underivable and the database row is
the only pointer to the object.

A controlled document is the exception. Its key is deterministic, which means **losing the row is
recoverable and losing the file is detectable**. That is worth a lot for a document you must be
able to produce years later.

It is safe **only** because the document number is never reused, so the key cannot be either. Do
not copy the pattern onto a record whose identifier can be re-issued, where two documents would
collide on one key. Anything with a replace path keeps the random suffix.

### 3f. No orphan reconciliation

Nothing sweeps for objects whose row was deleted, or rows whose object is gone. A partial failure
between the object write and the row write leaves an orphan nobody notices.

Low frequency, no tooling, and worth knowing rather than discovering. If your storage bill or your
compliance story depends on it, write the sweep.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Storage | S3-compatible, or the filesystem | | |
| Upload path | through the API, or a signed direct upload from the browser | | |
| Download path | a signed link, or streamed through the API | | |
| Key structure | | | |
| Random suffix | always, or off for controlled documents | | |
| File type validation | by extension, or by reading the opening bytes | | |
| Size limits, per type | | | |
| Virus scanning | yes, or no | | |
| Public domain | blank in production | | |
| Orphan sweep | yes, or accept the drift | | |

Row 2: signed direct upload keeps large files off your API process entirely. It costs you a
second endpoint and makes validation harder, because the file arrives without passing through you.

Row 6 matters more than it looks. Extension-based checking trusts the filename. Reading the
opening bytes tells you what the file actually is. If users upload files that other users
download, do the second one. Note that it usually needs a system library, so it needs a change to
your container image too, and a package that cannot import is worse than no check.

Row 3: streaming through the API lets you log and authorise every download and puts the bytes
through your process. Signed links are cheaper and mean the download does not appear in your
access log at all. If you need download auditing, that decides it.

---

## 5. Inventory

### Storage consumers

| Consumer | Writes | Attachment row? |
|---|---|---|
| | | |

### Where the attachment-row rule is deliberately broken

| Case | Why |
|---|---|
| | |

### Known gaps

---

## 6. New-upload checklist

1. Get the client through the one shared accessor. Never build a second one.
2. Write the object, then create the row, **in the same single commit** as the rest of the
   mutation.
3. **Generating a document?** Fingerprint the live reads, put the token in the key, keep the
   filename clean, and take a lock before the cache check.
4. **Deleting a file?** Pass the owning type and the owning id. Always both.
5. Validate at upload. Nothing revalidates later.
6. Add the consumer to §5.

---

## 7. How to re-check this doc

```bash
# The storage consumers. Compare to §5.
grep -rln --include="*.py" "get_storage\|StorageService" app/ | grep -v "object_storage/\|test_"
```

```bash
# A second storage client bypassing the singleton. Expect only the storage module.
grep -rn --include="*.py" "boto3\|client(\"s3\"\|resource(\"s3\"" app/ | grep -v "object_storage/"
```

```bash
# Every delete call must pass both the owning type and the owning id.
grep -rn -A4 --include="*.py" "attachment_service.detach(" app/ | grep -v "test_\|detach_all" | grep -E "detach\(|entity_type|entity_id"
```

```bash
# The public-domain setting must be empty in the production environment file.
grep -n "S3_PUBLIC_DOMAIN" .env.example deploy/*.env* 2>/dev/null
```
