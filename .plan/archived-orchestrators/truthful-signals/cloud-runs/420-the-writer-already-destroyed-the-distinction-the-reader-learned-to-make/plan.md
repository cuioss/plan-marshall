> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# The writer already destroyed the distinction the reader just learned to make

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

A recently-landed change taught the metrics reader a three-state vocabulary — **measured / unmeasured /
unrecognised**. **The rescue does not reach the rows that need it most: a nine-column pre-change row
still reads as a MEASURED ZERO.**

The mechanism, read by symbol against merged main:

- The column-count check is a **floor** (`< 5`), correctly widened from a strict equality so a widened
  row is no longer dropped. **This part is right.**
- The per-column rescue marks a column **unmeasured** only when the column is **absent** (its index
  exceeds the row's length) or its cell equals the explicit unmeasured token.
- Otherwise the cell is parsed as an integer.

⇒ **A nine-column pre-change row has all four appended cells PRESENT, containing a literal `0`.** Parsing
succeeds ⇒ the column is recorded as a **measured zero**. **The rescue cannot fire, because nothing is
missing.**

### ⭐⭐ The blast radius is not an estimate — it follows from an already-filed finding

A separate finding states that **the four per-dispatch context-load columns were declared, wired, and
zero on every row** before the change.

⇒ **The pre-change corpus consists ENTIRELY of the rows this defect mis-reads.** Every archived plan's
context-load figures currently read as *"measured, and the measurement was zero"* when the truth is
*"never measured."*

### ⛔ THE SHAPE, and why widening the floor cannot fix it

> **A three-state vocabulary cannot recover a distinction the two-state writer already destroyed.**

The reader was taught to say *unmeasured*; the writer had already committed `0` to disk. **The bytes on
disk are IDENTICAL for "measured zero" and "wrote zero because it had nothing."** No reader-side change
can separate them — **this is an information-loss problem, not a parsing problem.**

⭐ **And it is the epic's own theme turned on the epic's own fix**: the run that made the record *capable*
of honesty left the existing record *confidently wrong* — **and the fix's own tests pass because they
exercise the new writer.**

## Goal

A reader of the metrics corpus can tell "measured zero" from "never measured" — or, where it provably
cannot, **says so per row** instead of asserting either.

## Deliverables

1. **D0 — GATE: establish the discriminator, or prove there is none.** Mutates nothing. Is there **any**
   out-of-band signal that dates a row to before or after the writer change — a schema stamp, an archived
   plan directory's date, a field only the new writer emits?
   *Done when:* the answer is recorded, **with the population published**: how many archived rows, how
   many datable, how many not.
   ⛔ **Everything below depends on the answer, and "there is none" is a LEGITIMATE and IMPORTANT
   outcome.**
2. **D1 — If a discriminator EXISTS: read provenance-dated.** A row provably written by the pre-change
   writer reads its four appended columns as **unmeasured**, regardless of cell content.
   *Done when:* pre-change rows no longer read as measured zeros.
   ⛔ **NEVER rewrite the archived corpus.** The corpus is the audit record; **the interpretation is what
   changes.**
3. **D2 — If NO discriminator exists: say so IN THE OUTPUT, per row.** The verdict becomes
   **`indeterminate`** — a **fourth** state, distinct from *unmeasured* (the writer said so) and
   *unrecognised* (the reader could not parse it).
   *Done when:* the fourth state exists and is emitted for the affected rows.
   ⛔ **Do NOT collapse it into `unmeasured`.** ⭐ **That would be the same over-claim in the opposite
   direction — asserting the writer made a statement it never made.**
   ⭐ This is the *`indeterminate`-as-its-own-outcome* rule a sibling plan carries for a different oracle,
   **arriving independently in a second component.**
4. **D3 — A consumer audit.** Which readers consume these four columns, and **what does each conclude
   from a zero?**
   *Done when:* the consumer set is derived and each one's handling is stated.
   ⛔ **A fix at the parser is worthless if a downstream consumer treats `unmeasured` as `0` on arrival**
   — which is the exact composition failure this plan is about.
5. **D4 — Regression tests, each verified RED pre-fix, with matched negative controls in BOTH
   directions.**
   - A genuine **post-change measured zero** must **still** read as measured. ⛔ **A fix that marks every
     zero `indeterminate` has replaced a false positive with a false negative.**
   - ⛔⛔ **And the opposite collapse must be covered too.** The same landing shipped a measurement using
     an idiom that **collapses an empty collection to absent** — *the same conflation, in the same run,
     in the opposite direction.* **One end reads a written zero as measured; the other writes an empty
     list as absent.** ⇒ **Cover both, or the fix trades one collapse for the other.**
   *Done when:* both directions pass, each seen red first.

Five deliverables, one component.

## Out of scope

- ⛔ **Rewriting the archived corpus.** See D1. It is the audit record.
- **A denominator that states WHEN it was sampled but not WHAT it counted.** A related residual on the
  same surface: the landing added mandatory **sampling points** and stopped short of mandatory
  **subjects**. ⭐ **A denominator with a timestamp and no population is still an unlabelled number — and
  the sampling point tells a reader the figure is fresh, which is exactly the confidence that makes the
  missing subject harder to notice.** **Record it; it deserves its own plan.**
- **A partiality verdict that cannot see a *stale-closed* phase, only a *never-closed* one.** A third
  state on the same axis — `open`, `closed`, and **`closed but its values predate the last write`**.
  **Record it as adjacent work**, not as a deliverable here.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py` — the column
  floor, the rescue condition, and the integer parse. **Located by symbol.**
- `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md` — the
  positional-compatibility paragraph, which **states the intended behaviour the code does not deliver for
  widened rows** and must be corrected **in lock-step**.
- The metrics writer — the provenance stamp, **if D0 finds one**.
- `test/plan-marshall/plan-retrospective/**`.
- ⛔ **NOT the archived corpus** — read, never rewritten.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The column check is a floor; the rescue fires only on an absent column or the explicit token; otherwise the cell is parsed | HYPOTHESIS | that script, **by symbol** — ⭐ **fully checkable from this clone, and it is the whole mechanism** |
| A present literal zero therefore parses as measured | HYPOTHESIS | follows from the above — **verify by running the parser over a synthetic nine-column row** |
| The four columns were zero on **every** pre-change row | HYPOTHESIS | ⛔ **a separately-filed finding, NOT re-derived here.** ⭐ **This is what makes the blast radius total rather than partial** — if it is wrong, the impact is smaller and the plan re-scopes |
| The defect was confirmed empirically against merged main | HYPOTHESIS | ⚠ **reported by the run that filed it; the MECHANISM was confirmed by source read, the empirical check was NOT re-run.** Both routes agree, which is why it is stated — not because either alone settles it |
| A provenance discriminator exists | HYPOTHESIS | ⛔ **GENUINELY OPEN — D0 may refute it.** The plan is designed to be useful either way |
| This script is the only reader of these columns | HYPOTHESIS | ⛔ **D3's sweep. An unverified ABSENCE of other consumers is the higher-risk half** |
| The data-format standard states behaviour the code does not deliver | HYPOTHESIS | that paragraph — ⭐ **and it must be corrected in lock-step, or the doc keeps promising what the fix cannot give** |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D4's two-directional controls are the deliverable that makes this safe.** One direction stops the
  fix from marking every zero indeterminate; the other stops it from re-introducing the
  empty-collapses-to-absent conflation that shipped in the same landing.
- ⛔ **D0's "there is none" outcome must be reported as a RESULT, not as a failure.** It selects D2 over
  D1, and D2 is the honest answer to an information-loss problem.
- **D3's consumer set must be derived, not sampled.** ⭐ A parser fix undone by one downstream consumer's
  zero-handling is the composition failure this plan exists to name.
- **The standards paragraph must be corrected in the same change.** Leaving it stating the undelivered
  behaviour is doc-contract divergence introduced by the fix.
- Python and test changes are expected, so the build gate takes its full path.

## Notes

- ⚠ **Sequencing: do not pair with any plan touching the retrospective surface.** A sibling plan holds
  the finding this plan's blast-radius claim rests on and is **not a blocker** — this plan re-derives the
  consequence rather than depending on the fix — **but if it lands first, re-ground: it may change what
  the columns contain going forward.**
- ⚠ Another sibling on the metrics surface may be mid-flight. **Check before starting.**
- ⛔ **Do not go looking for the orchestrator spec, the archived corpus, the inbox messages, or any
  landing record.** They live under `.plan/`, which is git-ignored and absent from this clone. **The
  mechanism is fully checkable from source and is described above in enough detail to verify it there.**
