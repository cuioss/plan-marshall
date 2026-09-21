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

# The audit-ledger reader still reads an undatable zero as measured

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

A sibling plan (`420-the-writer-already-destroyed-the-distinction-the-reader-learned-to-make`, merged)
taught the **plan-retrospective** reader a fourth state for the four per-dispatch context-load columns
of the dispatch-boundary ledger. Those columns were written as a literal `0` by the writer that
predated the `unmeasured` token, so a literal `0` in such a row is **byte-identical** to a genuine
measured zero and cannot be dated. That reader now reports such a `0` as **`indeterminate`** — carried
neither as a measurement nor as a deliberate abstention — unless the row carries a post-token
**fingerprint** (an `unmeasured` token, or a nonzero context-load cell) that dates it to the current
writer.

**A second, independent reader of the same on-disk ledger was left with the old three-state read.**
`_parse_dispatch_boundary_totals` in
`.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` reads the same
`work/metrics-dispatch-boundaries-{phase}.toon` rows directly (it is a *parallel* re-reader, not a
downstream consumer of the fixed reader) and sums the four columns into the billing-composition
corpus. Read by symbol: it correctly **skips** the `unmeasured` token, but any cell that parses as an
integer — **including a fingerprint-free literal `0`** — is summed and the field is marked
`measured`. So a pre-token, all-zero row still enters the corpus as *"measured, and the measurement was
zero"* — the exact information-loss over-claim plan 420 named, surviving in the one reader plan 420
scoped out under its "one component" boundary.

The corrected standard already anticipates this: `manage-metrics/standards/data-format.md`
§ Per-Dispatch Context-Load Attribution → *"Provenance of a measured zero"* states that *"a reader that
does not recover provenance … reads an undatable `0` as a measured zero."* `audit.py` is that reader.

## Goal

The audit-ledger reader tells a genuine measured zero from an undatable one the same way the
plan-retrospective reader does: a literal `0` in a fingerprint-free dispatch-boundary row no longer
enters the billing-composition totals as a measured zero, while a measured zero in a row a post-token
fingerprint dates still sums. The two parallel readers of one ledger stop disagreeing about the same
bytes.

## Deliverables

1. **D0 — consumer audit of `audit.py`'s own zero-handling (derive, do not sample).** Before changing
   the summer, derive every place in `audit.py` that concludes something from a per-dispatch
   context-load value or from the `_parse_dispatch_boundary_totals` result — the billing reconciliation
   (`_BillingCompositionRow`, the `max(row_value, dispatch_boundary_total)` reconciliation), any
   `has_billing` / population flag, any render. State for each what it concludes from a zero, so the
   gate fix is not undone one call downstream.
   *Done when:* the consumer set inside `audit.py` is enumerated and each one's zero-handling is
   stated in the run report.
2. **D1 — the provenance gate in `_parse_dispatch_boundary_totals`.** Apply the same row-level gate the
   plan-retrospective reader uses: a row is datable to the current writer iff it carries a post-token
   fingerprint — an `unmeasured` token **or** a nonzero context-load cell. A literal `0` in a datable
   row sums and marks the field measured (unchanged); a literal `0` in a **fingerprint-free** row does
   **not** sum and does **not** mark the field measured — it is undatable, so it must not be reported
   as a measured zero. The `unmeasured` token and unrecognised-cell handling are unchanged.
   *Done when:* over a ledger whose only rows are fingerprint-free all-zero rows, the four context-load
   fields are **omitted** from the returned totals (absent, exactly as an all-`unmeasured` ledger
   already yields), not present as `0`; and over a ledger with a fingerprinted row, that row's measured
   zeros still sum and are present.
   ⛔ **NEVER rewrite the archived corpus.** The ledger files are the audit record; only the reader's
   interpretation changes.
3. **D2 — docstring cross-reference corrected in lock-step.** `_parse_dispatch_boundary_totals`'s
   docstring says the cell *"reads three ways per `data-format.md` § Per-Dispatch Context-Load
   Attribution"*; that section now documents four. Update the cross-reference to name the fourth state
   and the provenance gate, so the code's own description stops contradicting the section it cites.
   *Done when:* the docstring names the undatable-zero / provenance-gate behaviour it now implements.
4. **D3 — regression tests, each verified RED pre-fix, with negative controls in BOTH directions.**
   Mirror plan 420's D4 for this reader: (a) a fingerprint-free all-zero ledger yields totals with the
   four columns **absent** (was: present as summed `0`s, field marked measured) — the fix; (b) a
   nonzero-fingerprinted row's measured zero **still** sums and is present (never marking every zero
   undatable); (c) an `unmeasured`-token-fingerprinted row's sibling measured zero still sums. Prefer
   the existing cross-reader fixture that already drives both readers off one artifact, so the two
   readers are pinned to agree.
   *Done when:* all three directions pass, each seen red first.

## Out of scope

- **The plan-retrospective reader (`analyze-logs.py`) and `manage-metrics` writer/standard.** Already
  corrected by plan 420; re-touching them is not this plan's change and would re-open a merged surface.
  A one-line note in `data-format.md` naming `audit.py` as a second provenance-recovering reader is
  permitted **only if** D0/D1 make the standard's current wording inaccurate; if the wording stays
  accurate (it describes the general "reader that does not recover provenance" case, which other
  readers may still be), leave it — do not edit the standard to make a cosmetic point.
- **Rewriting the archived corpus.** It is the audit record; the fix is interpretive. (Same boundary
  as plan 420, for the same reason.)
- **The two further residues plan 420 named** — a denominator that states *when* it was sampled but not
  *what* it counted, and a partiality verdict blind to a *stale-closed* phase. Each deserves its own
  plan; folding them in here would widen a one-reader fix into an unrelated sweep.

## Expected surface

- `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` — `_parse_dispatch_boundary_totals`
  (the summer), and the `_BC_LEDGER_*` constants it reads (`_BC_LEDGER_COLUMNS`,
  `_BC_LEDGER_UNMEASURED_TOKEN`, `_BC_LEDGER_UNMEASURABLE_FIELDS`, `_BC_LEDGER_FIELDS`). **Located by
  symbol.** ⚠ This tree is **not** in the architecture crawl inventory (the standard says so), so a
  content search will not find it — open it by path.
- The audit test suite under `test/plan-marshall/audit-archived-plan-retrospectives/**`, and the
  cross-reader representability fixture that drives both readers off one artifact
  (`test/plan-marshall/manage-metrics/test_record_model_representability.py` carries
  `test_unmeasured_fixture_reads_three_ways_in_the_audit_ledger_reader` and a legacy-fixture
  cross-check — **re-derive the exact names at the moment of the change; they may have moved**).
- ⛔ **NOT** `analyze-logs.py`, the `manage-metrics` writer, or the archived corpus.

## Claim labels

Every count and line reference below is a **lead** — re-derive it by symbol at the moment of the
change; the clone the run sees is not guaranteed to match the tree this plan was authored from.

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `audit.py` `_parse_dispatch_boundary_totals` sums a fingerprint-free literal `0` and marks the field `measured` (skipping only the `unmeasured` token) | OBSERVED | that function in `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`, read by symbol — the integer-parse branch marks the field measured with no zero-provenance gate |
| It is a **parallel** re-reader of the on-disk ledger, not a downstream consumer of the plan-retrospective reader | OBSERVED | the function reads the `.toon` file directly; it does not import `analyze-logs` output |
| The standards section already documents the fourth state and names the "reader that does not recover provenance" case | OBSERVED | `manage-metrics/standards/data-format.md` § Per-Dispatch Context-Load Attribution → "Provenance of a measured zero" (git-tracked) |
| A cross-reader fixture drives BOTH readers off one artifact and can pin them to agree | HYPOTHESIS | `test/plan-marshall/manage-metrics/test_record_model_representability.py` — confirm the fixture and the two reader-specific tests still exist and still share one artifact before relying on it |
| No consumer inside `audit.py` concludes something from a context-load zero that D1 would leave stale | HYPOTHESIS | D0's sweep — an **asserted absence**, the higher-risk half: verify it by reading `audit.py`'s billing reconciliation, not by assuming it |

## Verification

- **D0's absence is the risk half.** The gate fix (D1) is worthless if a call inside `audit.py`
  downstream of `_parse_dispatch_boundary_totals` reads a now-absent field as `0` on arrival — the same
  composition failure plan 420 named for the other reader. Derive the consumer set by reading, not by
  sampling, and state each one's zero-handling.
- **Both D3 directions are the deliverable that makes this safe.** One direction stops the fix from
  marking every zero undatable (a fingerprinted measured zero must still sum); the other proves the
  affected fingerprint-free zero now drops out of the totals. Each seen red first.
- **Pin the two readers together.** Prefer the cross-reader fixture so a future change that moves only
  one reader fails a test, keeping the two parallel readers of one ledger in agreement — the property
  this plan restores.
- Python and test changes are expected, so the build gate takes its full path.

## Notes

- **Provenance.** This plan is the recorded residue of the merged plan
  `420-the-writer-already-destroyed-the-distinction-the-reader-learned-to-make` (its run report's
  Residue section, git-tracked under that plan's directory, and its D3 consumer audit, are the source
  record — read them for the fingerprint rule and the exact defect). The residue was scoped out of 420
  under its "one component" boundary because `audit.py` is a separate bundle; this plan is that
  component.
- **The fingerprint rule is transplanted, not re-invented.** "Datable iff the row carries an
  `unmeasured` token or a nonzero context-load cell" is exactly the gate plan 420 landed in
  `analyze-logs.py` `_parse_dispatch_boundary_file`; keep the two definitions identical so the readers
  cannot drift. A measured `0` in a fingerprinted row stays measured (matches the standard's row-3
  example `…,9100,0,0,0` — three genuine measured zeros).
- ⚠ **Sequencing.** No blocker — plan 420 has landed, so the standard and the sibling reader are
  already in their corrected state. If any further plan on the dispatch-boundary surface is mid-flight,
  re-ground before starting.
- ⛔ **Do not go looking under `.plan/`** for the orchestrator spec, the archived corpus, or any
  landing record — that tree is git-ignored and absent from a cloud clone. Everything this plan needs
  is named above and reachable from the checkout.
