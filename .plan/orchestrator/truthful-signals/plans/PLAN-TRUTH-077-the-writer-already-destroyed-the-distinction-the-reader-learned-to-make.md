# PLAN-TRUTH-077: the writer already destroyed the distinction the reader just learned to make

epic: truthful-signals
workstream: WS-01

> Staged 2026-08-09 from inbox message `-014` (`kind: error`) filed by the `PLAN-TRUTH-055` run, and
> **confirmed first-party by this orchestrator against merged main** before staging.
> ⛔ **This is a live defect in `main`, not a residual.**

## Objective

`PLAN-TRUTH-055` (#1129, `2586ef00c`) taught the metrics reader a three-state vocabulary —
**measured / unmeasured / unrecognised**. The rescue does not reach the rows that need it most: a
nine-column **pre-change** row still reads as a **measured zero**.

## OBSERVED — re-derived first-party against merged main, by symbol

`plan-retrospective/scripts/analyze-logs.py`:

- `:597` — `if len(parts) < 5: continue`. A **floor**, correctly widened from the old strict `!= 5` so a
  widened row is no longer dropped. **This part is right.**
- `:616-621` — the per-column rescue marks a column **unmeasured** only when
  `index >= len(parts)` (the column is **absent**) or the cell equals the explicit unmeasured token.
- `:627-628` — otherwise `int(cell)`.

⇒ **A nine-column pre-change row has all four appended cells PRESENT and containing a literal `0`.**
`int('0')` succeeds ⇒ the column is recorded as a **measured zero**. **The rescue cannot fire, because
nothing is missing.**

### ⭐⭐ The blast radius is not an estimate — it follows from an already-filed finding

Inbox message `provider-logging-path-containment-003` (L3), folded into `PLAN-TRUTH-045` at the
2026-08-09 drain, states: *"the four per-dispatch context-load columns are **declared, wired, and zero
on every row**."*

⇒ **The pre-change corpus consists ENTIRELY of the rows this defect mis-reads.** Every archived plan's
context-load figures currently read as *"measured, and the measurement was zero"* when the truth is
*"never measured."*

### ⛔ THE SHAPE, AND IT IS WHY WIDENING THE FLOOR CANNOT FIX IT

> **A three-state vocabulary cannot recover a distinction the two-state writer already destroyed.**

The reader was taught to say *unmeasured*; the writer had already committed `0` to disk. **The bytes on
disk are identical for "measured zero" and "wrote zero because it had nothing."** No reader-side change
can separate them — this is an information-loss problem, not a parsing problem.

⭐ **And it is the epic's own theme turned on the epic's own fix**: the run that made the record
*capable* of honesty left the existing record *confidently wrong*, and the fix's own tests pass because
they exercise the new writer.

## Deliverables

1. **D0 — GATE: establish the discriminator, or prove there is none.** Is there ANY out-of-band signal
   that dates a row to before/after the writer change — a `metrics.md` schema stamp, the archived plan
   directory's date, a `close_count`/`value_scope` field only the new writer emits? ⛔ **Everything below
   depends on the answer, and "there is none" is a legitimate and important outcome.**
   ⚠ **Publish the population**: how many archived rows, how many datable, how many not.
2. **D1 — if a discriminator EXISTS: read provenance-dated.** A row provably written by the pre-change
   writer reads its four appended columns as **unmeasured**, regardless of cell content. ⛔ **Never
   rewrite the archived corpus** — the corpus is the audit record; the interpretation is what changes.
3. **D2 — if NO discriminator exists: say so IN THE OUTPUT, per row.** The verdict becomes
   **`indeterminate`** — a fourth state, distinct from `unmeasured` (the writer said so) and from
   `unrecognised` (the reader could not parse it). ⛔ **Do NOT collapse it into `unmeasured`**: that
   would be the same over-claim in the opposite direction, asserting the writer made a statement it
   never made. ⭐ This is the `indeterminate`-as-its-own-outcome rule `PLAN-TRUTH-059` already carries
   for the pin oracle, arriving independently in a second component.
4. **D3 — a consumer audit.** Which readers consume these four columns, and what does each currently
   conclude from a zero? ⛔ **A fix at the parser is worthless if a downstream consumer treats
   `unmeasured` as `0` on arrival** — the exact composition failure this plan is about.
5. **D4 — regression tests, each verified RED pre-fix, with a matched negative control**: a genuine
   post-change measured zero **must still** read as measured. ⛔ A fix that marks every zero
   `indeterminate` has replaced a false positive with a false negative.

**Five deliverables, one component.**

## Claim Labels

- **OBSERVED (this orchestrator, first-party against merged main, by symbol)**: the `:597` floor; the
  `index >= len(parts)` rescue condition at `:616-621`; the `int(cell)` path at `:627-628`; and the
  consequence that a present literal `0` parses as measured.
- **OBSERVED (already filed, `provider-…-003` / L3, folded into `-045`)**: the four columns were
  declared, wired and **zero on every row** pre-change — which is what makes the blast radius total
  rather than partial.
- **REPORTED (the `-055` run, first-party to it, NOT re-derived here)**: that the defect was *"confirmed
  empirically against merged main"* by that run. ⭐ This orchestrator confirmed the **mechanism** by
  reading the source; it did **not** re-run the empirical check. Both routes agree.
- **HYPOTHESIS**: that a provenance discriminator exists. ⛔ **Genuinely open — D0 may refute it**, and
  the plan is designed to be useful either way. Confirm/refute against the `metrics.md` writer in
  `manage-metrics` and the archived corpus under `.plan/local/archived-plans/` — **verify-at-outline.**
- **HYPOTHESIS**: that `analyze-logs.py` is the only reader of these columns. Confirm/refute by a
  consumer sweep — that IS D3, and an unverified *absence* of other consumers is the higher-risk half.

## Expected Surface

- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py`
  — `:597`, `:616-621`, `:627-633`
- **OBSERVED**: `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md:814`
  — the positional-compatibility paragraph, which **states the intended behaviour that the code does not
  deliver for nine-column rows** and must be corrected in lock-step
- **HYPOTHESIS**: the `manage-metrics` writer (the provenance stamp, if D0 finds one)
- **HYPOTHESIS**: `test/plan-marshall/plan-retrospective/` — the regression home
- ⛔ **NOT** `.plan/local/archived-plans/**` — the corpus is read, never rewritten.

## Dependencies and Sequencing

- ⛔ **`PLAN-TRUTH-045` holds the L3 finding this plan's blast-radius claim rests on**, and `-045` is
  `staged`. **Not a blocker** — this plan re-derives L3's consequence rather than depending on its fix —
  but if `-045` lands first, re-ground: it may change what the columns contain going forward.
- ⚠ **Adjacent to `PLAN-TRUTH-035`** (the token total is a partition labelled a whole), which is
  implemented-but-unfinalized on the same `manage-metrics` surface. **Check its state before emitting.**
- ⛔ **Do not pair with any plan touching `plan-retrospective`** — `-045` is the obvious collision.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-077-the-writer-already-destroyed-the-distinction-the-reader-learned-to-make.md"
```

## Write-Boundary

Touches only its own repository source and tests. ⛔ **Writes nothing under
`.plan/local/archived-plans/`** — see D1. Creates and edits NO file under `.plan/local/orchestrator/`
other than its own `inbox/{sender}-{seq}` message.


---

## ⭐ FOLDED AT STAGING FROM THE SAME DRAIN — three more residuals of #1129, all on this surface

- **`metrics-014` (finding)** — the message that produced this plan. Recorded here so the spec's origin
  is traceable to its filer.
- **`metrics-005`** — *`len(x) or None`: the plan whose thesis is "absent is not zero" shipped a
  measurement that collapses empty to absent.* ⛔⛔ **The same conflation, in the same run, in the
  opposite direction from the escaped defect.** One end reads a written `0` as measured; the other
  writes an empty list as absent. ⇒ **D4's negative controls must cover BOTH directions**, or the fix
  trades one collapse for the other.
- **`metrics-015`** — *a denominator that states WHEN it was sampled and not WHAT it counted
  (`files_mod…`).* ⇒ #1129's D3 added mandatory **sampling points** and stopped short of mandatory
  **subjects**. ⭐ A denominator with a timestamp and no population is still an unlabelled number — the
  sampling point tells a reader the figure is fresh, which is exactly the confidence that makes the
  missing subject harder to notice.
- **`hook-001`** — *the partiality verdict cannot see a **stale-closed** phase, only a **never-closed**
  one.* ⇒ A third state on the same axis this plan is about: `open`, `closed`, and **`closed but its
  values predate the last write`**. Folded here because #1129 shipped and this is its live successor on
  the record-honesty surface.
