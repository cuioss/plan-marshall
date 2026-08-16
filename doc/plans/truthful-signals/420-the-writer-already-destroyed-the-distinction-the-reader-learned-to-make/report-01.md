# Run report — 420-the-writer-already-destroyed-the-distinction-the-reader-learned-to-make (run 01)

**Date (UTC):** 2026-08-14    **Branch:** `claude/truthful-signals-writer-reader-67t3to` (harness-assigned, kept)    **PR:** _pending_    **Outcome:** in progress

## Skills loaded

- `plan-marshall:ref-code-quality` (always) — read from bundle path.
- `pm-plugin-development:plugin-script-architecture` (always) — read from bundle path.
- `plan-marshall:persona-implementer` (production code work identity) — read from bundle path.
- `pm-dev-python:python-core` (Python production code) — read from bundle path.
- `pm-dev-python:pytest-testing` (Python tests) — read from bundle path.

The `.md` standard touched (`data-format.md`) is markdown, not AsciiDoc, so `pm-documents:ref-asciidoc` was not loaded.

## Deliverables

### D0 — GATE: establish the discriminator, or prove there is none. **Verdict: there is NONE.**

Read by symbol against merged main:

- **Writer** — `manage-metrics.py` `cmd_record_dispatch_boundary` (+ `_DISPATCH_CONTEXT_LOAD_COLUMNS`,
  `UNMEASURED_COLUMN_TOKEN`). The current writer writes the four context-load cells as
  `str(int(measured))` when measured (a genuine `0` stays `0`) and the literal `unmeasured` when the
  flag is omitted. The TOON header is `plan_id:` / `phase:` / `rows[]{…9 columns…}:` — **no
  schema-version field, no writer-emitted provenance stamp.** A nine-column pre-token row and a
  nine-column post-token row carry the *same* header.
- **Reader** — `analyze-logs.py` `_parse_dispatch_boundary_file`. Confirmed the mechanism the plan
  states: a `len(parts) < 5` floor, a per-column rescue that marks a column unmeasured only when the
  column is *absent* or equals the `unmeasured` token, and otherwise an integer parse — so a
  nine-column pre-token row's four literal `0`s parse as **measured zeros**.

**Is there any out-of-band signal that dates a row to before/after the writer change?**

- **A schema stamp / a field only the new writer emits** — the only thing the current writer emits
  that the pre-token writer did not is the `unmeasured` *token*. That is a **one-directional**
  fingerprint: its presence proves post-token, but its absence proves nothing. The four columns
  themselves are not a discriminator — they were present and zero on every pre-token row (the
  separately-filed finding this plan does not re-derive).
- **A row-dating timestamp** — each row carries its own `timestamp` (column 1), but there is no
  landing instant in the record to compare it against, and the shim comments note the widening
  predates this shallow clone's history root (`dcd3c00` / `#1105`). A hard-coded landing date would
  be exactly the "landing record" dependence the plan forbids, and would be unsound across the
  rollout window.
- **The archived plan directory's date** — dates when a plan *ran*, still needs a landing instant,
  and the corpus lives under the git-ignored `.plan/` tree absent from this clone.

**Conclusion:** the affected rows are precisely the fingerprint-free rows (all context-load cells a
literal `0`, no `unmeasured` token, no nonzero), and **no in-band or out-of-band signal dates them.**
This selects **D2 over D1** — the honest answer to an information-loss problem.

**Population (published as required):**

- Archived rows are **not countable from this clone** — the corpus lives under `.plan/`, git-ignored
  and absent (the plan forbids going after it, and it is genuinely not here).
- Datable-to-provenance rows among the **affected** (fingerprint-free literal-`0`) population: **zero,
  by construction** — a literal `0` is byte-identical whether the pre-token writer defaulted it or the
  current writer measured it.
- Rows that ARE datable-to-post-token: any row bearing an `unmeasured` token or a nonzero
  context-load cell — but these are exactly the rows that already read correctly and are *not* the
  affected population.

### D1 — read provenance-dated. **N/A — refuted by D0.**

A row provably written by the *pre-token* writer is not identifiable (an all-zero row could be
pre-token or a — production-implausible — genuine all-measured-zero). D1's precondition is
unsatisfiable, so D1 does not apply.

### D2 — say so IN THE OUTPUT, per row: the fourth state `indeterminate`.

`_parse_dispatch_boundary_file` now applies a **row-level provenance gate**. A row is *datable to the
current writer* iff it carries a post-token fingerprint — an `unmeasured` token OR a nonzero
context-load cell. Then per column:

- `unmeasured` token → **unmeasured** (unchanged).
- unparseable → **unrecognised** (unchanged).
- nonzero integer → **measured** (unchanged).
- literal `0` → **measured** if the row is datable, else **`indeterminate`** — key omitted, column
  named in the new `row['indeterminate_columns']`.

`indeterminate_columns` is always emitted (present, possibly empty), alongside `unmeasured_columns`
and `unrecognised_columns`. The fourth state is distinct from `unmeasured` (D2's ⛔: not collapsed
into it) and from `unrecognised`. Implemented in commit _(see Build/commits)_.

### D3 — consumer audit (derived, not sampled).

Consumers of the four context-load columns / `_parse_dispatch_boundary_file` output:

| Consumer | Reads what | What it concludes from a zero | Disposition |
|---|---|---|---|
| `plan-retrospective/compile-report.py` `render_dispatch_boundaries_body` | the `dispatch_boundaries` fragment | **Nothing numeric from a context-load zero** — it counts `rows`, and reports the cause-count / `error_total_tokens` / `retryable_total_tokens` fields (all `total_tokens`-based), then JSON-dumps the fragment. The new `indeterminate_columns` flows into that dump automatically. | **Safe, no change.** The parser fix is not undone here. |
| `plan-retrospective/retro_sections.py` | section registry only | nothing | **Safe, no change.** |
| `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` `_parse_dispatch_boundary_totals` | the on-disk ledger **directly** (a *parallel* reader, not downstream of the reader fixed here) | **Correctly** skips the `unmeasured` token (does not treat it as `0`). But it **sums a fingerprint-free literal `0` and marks the field `measured`** — the same information-loss over-claim, in a different component. | **Out of this plan's stated surface** ("one component"; `analyze-logs.py` + `data-format.md` + tests). Recorded as **adjacent work** (Residue). It is not a *downstream* consumer of the fixed reader — it independently re-reads the ledger — so it does not undo the plan-retrospective fix. |

**Key D3 result:** *no consumer treats the `unmeasured` token as `0`* (the specific composition
failure D3 names), and *no downstream consumer of the fixed reader concludes anything from a
context-load zero* — so the parser fix is not undone within the plan-retrospective component.

### D4 — regression tests, red-first, both directions.

In `test/plan-marshall/plan-retrospective/test_analyze_logs.py`,
`TestDispatchBoundaryContextLoadColumns`:

- **Direction 1 — the fix:** `test_all_zero_no_fingerprint_row_reads_indeterminate` — the affected
  `…,0,0,0,0` row now reads all four as `indeterminate` (was the old
  `test_measured_zero_context_load_stays_zero`, which *encoded the defect* and is replaced).
- **Direction 1 negative control (measured zero stays measured):**
  `test_nonzero_fingerprint_keeps_measured_zeros_measured` (`…,9100,0,0,0`) and
  `test_unmeasured_token_fingerprint_keeps_measured_zeros_measured` (`…,unmeasured,0,0,0`) — a
  genuine post-token measured zero still reads as measured. Guards against marking *every* zero
  indeterminate.
- **Direction 2 — the opposite collapse (empty collection not absent):**
  `test_indeterminate_columns_present_empty_on_legacy_row` — a row with no indeterminate columns
  still emits `indeterminate_columns == []` (present, never collapsed to absent). This is the same
  conflation the sibling `_count_affected_files` idiom keeps on guard for
  (`A PRESENT-but-empty list is a MEASURED 0, not an absence`).
- **Edge case:** `test_indeterminate_zero_coexists_with_unrecognised_cell` — an unrecognised cell is
  not a fingerprint, so undatable `0`s stay indeterminate beside it.

Each new assertion is RED pre-fix (the pre-fix reader read the `0`s as measured and emitted no
`indeterminate_columns` key) — verification recorded under Findings/Build.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (`analyze-logs.py`,
`test_analyze_logs.py`), so the full `./pw verify` path was taken.

`./pw verify plan-marshall` → **SUCCESS** (exit 0): mypy(production) [279 files], ruff, SPDX headers,
mypy(test) [589 files], module-tests [plan-marshall] — **16475 passed, 1 skipped**. A first attempt
surfaced a real mypy error in the reader (`int | None` from a deferred-decision tuple assigned into
the row dict); restructured to a first-pass/deferred-zero-only design and re-verified clean.

(Two earlier `uv`/`./pw` invocations failed on an environmental fetch — a proxy stream error
downloading a transitive `mypy` dep — not a build failure; the retry succeeded.)

## Findings

- **Red-first verification (D4):** all five new-behaviour assertions FAILED against the stashed
  pre-fix reader for the right reasons — the pre-fix reader read the `0`s as measured
  (`input_tokens in row`) and emitted no `indeterminate_columns` key. After restoring the fix, the
  full reader + representability suites pass (120 passed locally; 16475 in the module verify).
- **Self-review (mypy):** the initial two-pass tuple design assigned `int | None` into the row dict —
  caught by the build gate, fixed by deferring only the literal-zero decision. Recorded as a run
  finding, fixed.
- **Verification sub-agent (Step 6, independent, read-only):** all five deliverables confirmed
  implemented-as-specified, with an empirical five-case trace run through the actual parser
  (`…,9100,0,0,0` → four measured; `…,unmeasured,0,0,0` → three measured zeros + input unmeasured;
  `…,0,0,0,0` → four indeterminate; `…,0,not-an-int,0,0` → three indeterminate + one unrecognised;
  legacy → four unmeasured). D3's absence-of-undoing-consumer claim (the plan's flagged high-risk
  half) held. The sub-agent's beyond-diff sweep surfaced stale lock-step "three-way" claims:
  - **F1 (fixed):** `manage-metrics/SKILL.md` `record-dispatch-boundary` block called the reader
    contract "three-way" — a named lock-step restating surface. Corrected to "four-way (measured /
    unmeasured / unrecognised / indeterminate)".
  - **F2 (fixed):** `data-format.md` subsection header still read "three-way cell read" directly above
    the table this change rewrote to four rows. Corrected to "the cell read".
  - **F3 (fixed):** the `UNMEASURED_COLUMN_TOKEN` comment in `manage-metrics.py` (a lock-step
    restating surface) asserted a flat "THREE-way distinction". Rewritten to note the reader's fourth
    state for an undatable zero.
  - **F4 (deferred → residue):** `audit.py`'s `_parse_dispatch_boundary_totals` docstring cites the
    standard's section as "reads three ways". `audit.py` genuinely reads three ways and is a separate,
    out-of-surface component; the corrected standard already acknowledges "a reader that does not
    recover provenance reads an undatable `0` as a measured zero", so the standard is accurate. The
    docstring cross-reference will move when the audit.py follow-on (Residue) lands. Not fixed here to
    hold the plan's "one component" boundary.

## Reviewer participation

_pending._

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** _pending (run start/end)._
- **Population:** this single Claude Code cloud session's usage; NOT comparable to a plan-marshall
  `metrics.toon` total.

## Contract check (Step 9)

_pending._

## What have we learned (Step 9)

_pending._

## Residue

- **`audit.py` `_parse_dispatch_boundary_totals` (D3):** applies the three-state cell read but reads a
  fingerprint-free literal `0` as a measured zero (marks the field `measured`), the same information-loss
  over-claim as the pre-fix plan-retrospective reader, in a separate component
  (`.claude/skills/audit-archived-plan-retrospectives/`) outside this plan's stated surface. Natural
  follow-on: extend the same row-level provenance gate to that parallel reader, and update its docstring
  cross-reference (currently "reads three ways per data-format.md § Per-Dispatch Context-Load
  Attribution") to four ways at the same time (verification F4).
- **Adjacent (named in the plan's Out-of-scope):** a denominator that states WHEN it was sampled but
  not WHAT it counted; a partiality verdict that cannot see a *stale-closed* phase. Recorded, not
  addressed here.
