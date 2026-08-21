# Money & Quantities

> Read this before you store or display any number a person will read.
>
> **Status in this project:** decide in Part 1 of the checklist
> **Last verified against the code:** 21 August 2026

---

## 1. What & why

Two number types run through most business systems, and each has a way to get it wrong that
ships silently.

**Money.** A float loses cents. An amount with no currency beside it is meaningless the moment
you have two currencies, and you always end up with two.

**Quantities.** Stored at three decimal places, so a plain whole number reads as `2.000` in an
error message. And the shortest formatting option in most languages flips to scientific notation
past six significant digits, so a large stock figure prints as `1.23457e+06`.

Both are fixed by using shared helpers everywhere and never formatting by hand.

There is sometimes a **third** type, and it is the interesting one. See §3a.

---

## 2. The rules

- **Money is a decimal, never a float**, and always paired with a currency.
- **Money is frozen with its currency on issued documents.**
  → [`snapshots-vs-live.md`](snapshots-vs-live.md)
- **Quantities are decimals at a fixed scale**, decided once.
- **Never interpolate a raw quantity into text a person reads.** Use the format helper in
  documents, notification bodies and error messages.
- **Never format a quantity with the shortest-representation option**, whatever your language
  calls it.
- **The wire keeps full precision.** Formatting is display only.
- **Never add across currencies.** Group by currency, or report one figure per currency.
- **One locale, chosen by you, for formatting.** Not the viewer's device (§3c).

---

## 3. The traps

### 3a. The third type, where the rule is the exact reverse

```
quantity      2.000  ->  "2"        trailing zeros are storage padding, strip them
measurement   0.000  ->  "0.000"    trailing zeros are the instrument's resolution, keep them
```

`0.000` and `0` are **different claims about the same reading.** The first says the device
resolves to a thousandth and showed nothing. The second says only that it showed nothing.

Where this matters, it matters absolutely. On a calibration certificate, a scientific result, a
lab measurement, that difference is the evidence.

Four rules follow, and each one is the opposite of the quantity rule:

| Rule | |
|---|---|
| **Column type** | Unconstrained numeric. No precision, no scale. Real data has both `0.04643277232527298` and `2.5` in the same column, and no fixed scale fits both. A fixed scale silently rescales |
| **Display** | No normalising, no grouping, no locale, never scientific. A decimals argument **pads only, never rounds**, because truncating a more precise stored value destroys evidence rather than tidying it |
| **Wire** | Crosses as a **string**, never a JSON number. Parsing JSON gives you a float, and a float round trip at six decimals is exactly the corruption this exists to prevent |
| **Negative zero** | Prints as zero, scale kept. It comes out of a subtraction in a spreadsheet. It is not a reading |

**Do not widen the quantity helper to cover it.** The two have opposite formatting rules, so one
helper would need a flag at every call site, and the failure mode of getting the flag wrong is
silent and only visible on paper. Two types, two names, no flag.

**And the client needs its own copy of the same helper**, written with string manipulation only.
No parsing to a number anywhere in it. Check it against the server version on a shared table of
cases, not by eye.

### 3b. Float on the way in, decimal in the database

**Symptom.** Totals off by a cent, occasionally, on long invoices.

**Why.** The column is a decimal, so everyone assumes it is safe. Somewhere a value passed
through a float. JSON parsing, an average, a percentage calculation.

**The fix.** Type the boundary too, not just the column. And keep money as a **string** on the
wire if your client language has no decimal type, which JavaScript does not.

### 3c. Formatting with the viewer's locale

**Symptom.** Two people look at the same invoice and see different numbers. One sees `1,234.56`
and the other `1.234,56`.

**Why.** The default number formatter in most languages follows the device.

**The fix.** Pick one locale for the whole system and enforce it. A lint rule that bans
constructing a number formatter outside one file is the cheap version, and it works.

### 3d. A bare amount column with no currency

**Symptom.** A dashboard adds two currencies together and reports a number that means nothing.

**Why.** The column was added early, when there was only one currency.

**The fix.** Pair every amount with a currency from the start. It costs one column. Retrofitting
it means a migration and a backfill decision per table, and systems carry three or four of these
open for years.

### 3e. Nothing forces the helpers

The recurring risk is a new document, notification or error message interpolating a raw value.
The helpers exist and nothing makes anyone use them. The re-check in §7 is the only guard.
Historically this shipped as `on hand 2.000` in an error message before somebody swept it.

---

## 4. Decisions this project must make

| Decision | Options | What we chose | Why |
|---|---|---|---|
| Money storage | decimal with a fixed scale, or integer minor units | | |
| Money scale | 2, or more for unit prices | | |
| Money on the wire | a string, or a number | | |
| Currency | one column beside every amount, or one per document | | |
| Quantity scale | | | |
| Rounding rule | half up, half even, or truncate | | |
| Is there a measurement type? | yes, or no | | |
| Display locale | | | |
| Percentages | their own type, or a plain decimal | | |

Row 1: integer minor units make arithmetic exact by construction and are awkward for unit prices
with four decimals. Decimals are easier to read in the database. Both work. Mixing them does not.

Row 3: a string. A JSON number is a float in most clients.

Row 6: half up matches what accountants expect. Half even reduces bias over many roundings.
Whichever you pick, use it everywhere and write it down, because two different roundings in one
system produce a total that does not match the sum of its lines.

Row 9: a rate is not money and is not a count. Conflating it with money attaches a currency to a
percentage.

---

## 5. Inventory

### The helpers

| Helper | Job |
|---|---|
| | |

### Where the helpers are deliberately not used

| Case | Why |
|---|---|
| The wire | full precision crosses. The client formats for its own display |
| Money is not trimmed like quantities | trailing zeros on money are meaningful, on quantities they are noise |
| | |

### Known gaps

---

## 6. New-field checklist

1. **Money?** The money column type in the model, the money type in the schema, and a currency
   column beside it. Never a float. Never a bare numeric.
2. **Quantity?** The quantity types.
3. **Rendering a quantity for a human**, in a document, a toast or an error message? The format
   helper. Never raw interpolation.
4. **Issuing a document with a price on it?** Freeze the currency with the amount.
5. Leave the wire at full precision.

---

## 7. How to re-check this doc

> Paths below are examples from one tree. Adjust them to yours. What matters is the check,
> not the path. Where a count is given, it is the count **for this project**, so fill it in
> the first time you run it.

```bash
# Float used for a money-shaped field. Read each hit.
grep -rn --include="models.py" --include="schemas.py" ": float\|Float(" app/ | grep -iE "amount|price|cost|total|rate|balance|paid|value"
```

```bash
# Shortest-representation formatting, the scientific-notation trap.
grep -rn --include="*.py" ':g}"' app/ | grep -v "test_"
```

```bash
# Raw quantity interpolation into text a person reads. Noisy, so read the hits.
grep -rn --include="*.py" 'f".*{.*\(qty\|quantity\|on_hand\|stock\).*}' app/ | grep -v "format_quantity\|test_"
```

```bash
# An amount column with no currency column on the same model. Read every hit.
grep -rn --include="models.py" "MoneyColumn" app/ -B2 -A2 | grep -i "currency" -c
```

```bash
# Client: constructing a number formatter outside the one numeric module.
# Better as a lint rule than a grep.
grep -rn "Intl.NumberFormat" src/ | grep -v "src/lib/numeric/"
```
