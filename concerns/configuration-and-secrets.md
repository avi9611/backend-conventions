# Configuration, Flags & Secrets

> Read this before you add a setting, a feature flag or a secret.
>
> **Status in this project:** in force from day 1
> **New in this kit.** Phoenix has these rules scattered across four files. They are worth one.
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

Configuration is where development conveniences leak into production, and where a missing value
turns into an incident at 3am instead of a failure at boot.

Three separate things get lumped together and they have different rules:

- **Settings.** Values that differ per environment. Database host, log level, page size.
- **Secrets.** Values that must never be readable. Keys, passwords, tokens.
- **Feature flags.** Switches that change behaviour, usually temporarily.

The dangerous ones are the settings that are *safe* in development and *dangerous* in production.
Those are the ones that travel, because somebody copies a working environment file.

---

## 2. The rules

- **One typed settings object, loaded from the environment.** No reading environment variables
  anywhere else in the code.
- **Required secrets have no default.** A missing one fails at boot, loudly, not at first use.
- **Nothing secret is ever in the repository.** Not in an example file, not in a test fixture,
  not in a comment.
- **Every setting is in the example environment file, with a comment**, and the example file
  holds no real value.
- **A dangerous default is a failed boot in production.** §3a.
- **Every kill switch is honoured by everything it claims to cover.** A switch you cannot trust
  is worse than no switch.
- **Never log a secret**, including in a startup dump of the configuration.
  → [`observability.md`](observability.md)
- **Feature flags have an owner and a removal date.** §3d.

---

## 3. The traps

### 3a. The development convenience that travels

The recurring pattern, and the reason this file exists. A setting is correct in development and
dangerous in production, and it moves when somebody copies a working environment file.

Real examples, all from Phoenix:

| Setting | In development | In production |
|---|---|---|
| A public storage domain | rewrites an internal hostname so a browser can follow links | turns every file link into a permanent, unsigned, guessable URL |
| API docs enabled | how you work | a map of your whole API |
| A bootstrap admin with a fixed password | convenient | a known account, known password |
| Auto-reload with automatic seeding | convenient | re-runs your seed on every restart |
| An open cache with no password | fine on a laptop | an open cache |

**The fix, and it is better than a checklist.** Write a startup assertion:

```python
if settings.ENVIRONMENT == "production":
    assert not settings.PUBLIC_ASSET_DOMAIN, "public asset domain must be blank in production"
    assert not settings.DOCS_ENABLED, "API docs must be off in production"
    assert settings.CACHE_PASSWORD, "cache password required"
```

**A production build that refuses to start is a much better outcome than one that starts.** The
checklist in Part 9 is the backup, not the primary control.

### 3b. The setting nobody can find

**Symptom.** A value is hardcoded in three places, with slightly different values.

**Why.** Somebody needed a timeout, put a number in the file, and the next person copied it.

**The fix.** Every tunable is a named setting with a default, grouped under a section comment, and
documented in the example file. If it is not worth naming, it is not worth being different in two
places.

### 3c. Computed settings that hide a dependency

A settings object with a property that builds a database URL from five other fields is convenient
and it hides which fields are actually required.

Keep computed values as properties, and cache the settings instance so it is built once. But make
sure the *inputs* are declared as required fields, so a missing one fails at boot rather than
producing a malformed URL that fails at first connection.

### 3d. Feature flags that become permanent

**Symptom.** A flag from two years ago, defaulted off, with a code path nobody has run.

**Why.** Flags are added under time pressure and removed never.

**The fix.** Every flag gets a row in §5 with an owner and an expected removal. A flag with no
removal date is not a flag, it is a configuration option, and it should be named and documented
as one.

**And there is a kind of flag that is not temporary and should be recognised as such.** A "the
next phase is not built yet" hook, where a function is a no-op that logs until the real
implementation arrives. That is a good pattern, because it means call sites already exist and
switching it on touches no caller. Say that in the doc, and hold the promise: **flipping the flag
must not require touching any call site.**

### 3e. Dependencies declared but not used, and used but not declared

Not configuration exactly, and it lives with the same class of problem. Both directions happen:

- **Declared and never imported.** One unused data library can add over 100MB to your image and
  build time on every rebuild.
- **Imported and never declared.** Your code imports a package it gets as somebody else's
  dependency. Nothing objects, until that dependency relaxes its version floor and your import
  fails at runtime.

**The fix.** A periodic check, in §7. And know whether your build actually installs from your
lock file, because "the lock file exists" and "the image uses it" are different claims.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Settings source | environment variables, or a secret manager | | |
| Environments | which ones exist, and what differs | | |
| Secret rotation | how, and how often | | |
| Are settings validated at boot? | yes, with production assertions | | |
| Feature flag mechanism | settings, or a database table, or a service | | |
| Who may change production settings | | | |
| Does the build install from the lock file? | | | |

Row 1: environment variables are the simple answer and they appear in process listings, crash
dumps and container inspection output. A secret manager costs setup and gives you rotation and an
audit trail. For anything holding customer data, the second is worth it.

Row 5: settings mean a deploy to flip a flag. A database table means an admin can flip it, and
now you need to think about caching it and about who is allowed to.

---

## 5. Inventory

### Settings that are dangerous in production

| Setting | Safe value in production | Asserted at boot? |
|---|---|---|
| | | |

### Kill switches

| Switch | What it covers | What it deliberately does not |
|---|---|---|
| | | |

### Feature flags

| Flag | Default | Owner | Remove by |
|---|---|---|---|
| | | | |

### Secrets, and where they come from

| Secret | Source | Rotation |
|---|---|---|
| | | |

### Known gaps

---

## 6. New-setting checklist

1. Add it to the settings object, in the right section, with a type and a description.
2. **Required secret? No default.**
3. Add it to the example environment file, with a comment, and no real value.
4. **Is it dangerous in production?** Add the boot assertion, and add the row to §5.
5. **Is it a flag?** Add the owner and the removal date.
6. Never read it anywhere except through the settings object.

---

## 7. How to re-check this doc

```bash
# Environment variables read outside the settings module. Expect zero.
grep -rn --include="*.py" "os.environ\|os.getenv" app/ | grep -v "core/settings.py\|test_"
```

```bash
# Every setting appears in the example file.
grep -oE "^\s+[A-Z_]+:" app/core/settings.py | tr -d ' :' | sort -u > /tmp/declared.txt
grep -oE "^[A-Z_]+" .env.example | sort -u > /tmp/documented.txt
comm -23 /tmp/declared.txt /tmp/documented.txt
```

```bash
# The example file holds no real secret.
grep -inE "password=.{8,}|secret=.{8,}|key=[A-Za-z0-9]{16,}" .env.example
```

```bash
# The production assertions exist.
grep -n "ENVIRONMENT ==\|is_production" app/core/settings.py app/core/main.py
```

```bash
# Declared but never imported, and imported but never declared.
python3 -c "
import ast, pathlib, sys
roots = set()
for p in pathlib.Path('app').rglob('*.py'):
    try: tree = ast.parse(p.read_text())
    except Exception: continue
    for n in ast.walk(tree):
        if isinstance(n, ast.Import): roots |= {a.name.split('.')[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom) and n.level == 0 and n.module:
            roots.add(n.module.split('.')[0])
print(sorted(r for r in roots if r not in sys.stdlib_module_names and r != 'app'))"
```
