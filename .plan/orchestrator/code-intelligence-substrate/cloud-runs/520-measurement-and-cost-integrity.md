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

# Measurement and cost integrity — every published figure states the population it measured

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

The epic built a measurement substrate and then audited the 36 plans that built it. Sixty-four of the
findings land on the substrate's own numbers, and they share one shape: **a figure is published as if
it were measured when part or all of it was fabricated, mislabelled, or computed over a population
other than the one its name asserts.** A reader cannot tell "no spend" from "never measured", "these
two producers agree" from "these two producers are not comparable", or "this phase recorded no
dispatch boundary" from "this phase's boundary coverage is a failure".

The mechanisms are specific and were reproduced by execution:

- **Fabricated zeros.** `manage-metrics.py`'s `cmd_record_dispatch_boundary` (`:3157`) defaults the
  `total_tokens` column to `0` when `--total-tokens` is omitted, while the four context-load columns
  in the *same row* write `unmeasured`. `analyze-logs.py` (`:1143`, `:1241-1246`) then sums that
  column into `error_total_tokens` / `retryable_total_tokens`, so a published spend figure silently
  mixes measured and fabricated contributions — and `retryable_total_tokens` does so systematically,
  because its two causes are exactly the terminations that emit no `<usage>`.
- **A precision mismatch inside one block.** `audit.py:2931` publishes `total_script_seconds` at one
  decimal while `:2887` computes the roll-up total, and `:2907-2909` each row's `share_pct`, at three.
  A one-line `(0.04s)` corpus therefore prints `total_script_seconds: 0.0` beside a row that owns
  `100.0%` of it; a two-call corpus prints shares that sum to 110 %.
- **A missing line-shape guard.** `extract_script_durations` (`analyze-logs.py:378-397`) parses every
  line handed to it, while its sibling `analyze_folded_global_logs` (`:1455-1462`) first gates on the
  entry-header grammar. Fed one real writer-produced ERROR entry, the per-plan reader manufactured a
  `pm:t:t` call of 9.99 s out of a failing script's `stdout:` continuation line — into the very
  `script_cost_rollup` its plan shipped.
- **A verdict gated on the wrong field.** `cmd_generate`'s `Dispatch-boundary total` bullet — the
  carrier of every coverage verdict, including the over-coverage `FAILURE` — is guarded by
  `if boundary_total:`, but `manage-metrics.py:1445` persists that total only `if boundary_sum:`
  while `:1439-1444` persists the row count whenever the file held rows. A phase whose boundary rows
  sum to zero (a shape the workflow documents *prescribe*) renders no bullet at all.
- **A footprint read outside its window.** `verify_failure_scope._resolve_declared_footprint:94`
  reads `PlanContext.worktree_path`, which falls back to the main checkout for a `pending` worktree,
  where both peer sites gate on `has_worktree`. In a clean foreign checkout this yields a *measured
  empty* footprint, so every verify failure lands out of scope and the classifier emits its single
  most confident verdict on no evidence.
- **An envelope stripper whose close tags mispair.** `_chat_provenance.partition_turn` (`:123-137`)
  pairs a close tag with the innermost open of its name, so a body quoting its own outermost tag
  escapes stripping and a transcript of pure harness instruction text scores as operator signal.

Around these six anchors sit the rest: labels that name fields which do not exist, two different
quantities sharing one name, era stamps that do not name the boundary that changed a check's meaning,
partitions pinned to nothing, figures computed and then discarded, and stale numbers in the epic's own
records.

## Goal

Every measurement this bucket touches either states the population it was computed over or declines to
state a number at all. An unmeasured quantity is representable and is visibly not a zero; a coverage
verdict is emitted whenever the coverage state is decidable; a duration comes only from a line that is
a log entry header; a share and its denominator are computed at the same precision; a footprint is
either resolved from the plan's own tree or reported unresolvable with a named reason; and a label
names the field and the population behind it. Where a figure cannot be produced from a fresh clone,
this plan records what a corpus-bearing run must do rather than guessing.

## Deliverables

Each deliverable groups gaps by **owning surface and shared mechanism**. Every gap this plan carries
is listed in § Gap coverage with its source-plan and gap id. The gap files
(`doc/plans/code-intelligence-substrate/{plan}/gaps.md`) are git-tracked corroboration, **not**
required reading — each defect's essential content is restated here, because a landed cloud plan's
directory is deleted at collect (`doc/plans/cloud-bridge.md` § Path 3) and those files may be gone.

> ⚠ **Every count in this plan is a lead, not a fact.** Line numbers, member counts, test counts,
> pass counts and durations were derived on a tree that has since moved, several of them while
> sibling agents ran full suites in the same checkout. **Re-derive every number at the moment you
> claim it**, and search by symbol name rather than trusting a line anchor.

---

### D1 — The dispatch-boundary ledger: what it records, what it concludes, what it publishes

One ledger, one file family: `manage-metrics.py` (writer + renderer), `analyze-logs.py` (reader),
`compile-report.py` (table), `audit.py` (independent reader), and the workflow documents that instruct
callers. The mechanism is single: **a value that was never measured must not enter a sum, a verdict
must not be gated on a field that is only persisted when non-zero, and a reconciliation must not
compare across populations.**

Land the sub-items in the order given — (a) changes what (b), (c) and (g) see, and (h) must precede
(i) or the `=` relation has no reachable row to test against.

**(a) Represent an unmeasured token count instead of writing a fabricated `0`.**
`cmd_record_dispatch_boundary` (`manage-metrics.py`, near `:3157`) writes `0` for an omitted
`--total-tokens`; `--total-tokens` is optional (`default=None`, near `:3832-3837`). Give
`total_tokens` — and, for row consistency, `tool_uses` and `duration_ms` — the same
`UNMEASURED_COLUMN_TOKEN` treatment the four context-load columns already have. Keep the legacy-row
floor in `_parse_dispatch_boundary_file` so every historical nine-column int row still parses.
⛔ `plan-marshall/workflow/execution.md` (near `:254-260`) passes `--total-tokens 0` **deliberately**
for the synthesized `clean_exit_queue_empty` pre-dispatch peek row. That is a measured zero and must
not be "fixed". Stop instructing callers to fabricate `0` at `workflow/execution.md:219` and
`workflow/planning-outline.md:468`; state at `phase-6-finalize/SKILL.md` (near `:1109`) what to pass
when 5b captured no `<usage>`; update `manage-metrics/standards/data-format.md`'s column table.
⛔ **Lock-step, and its failure mode is silent.**
`.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` parses the same file
independently: `total_tokens` sits in `_BC_LEDGER_FIELDS` but **not** in
`_BC_LEDGER_UNMEASURABLE_FIELDS`, so an `unmeasured` token would take the `totals[…] += _to_int(cell)`
branch, `_to_int` returns `0` for a non-numeric string, and `measured.add(...)` still fires — the
billing-composition reconciliation would report the row as a **measured zero** with no unrecognised
signal. Change both readers in the same commit or neither.
*Done when:* a `record-dispatch-boundary` call omitting `--total-tokens` writes a row whose third
column is not `0`; `_parse_dispatch_boundary_file` reports that row as unmeasured rather than folding
it into `error_total_tokens` / `retryable_total_tokens`; `audit.py`'s ledger reader classifies the same
cell as unmeasured rather than as a measured zero; and one named test asserts a measured `0` and an
omitted flag are distinguishable **in the file bytes and in both readers' output**.

**(b) Publish each cause-class sum with the population it was computed over.**
`analyze-logs.py` (near `:1241-1243`) computes `error_total_tokens` as an unconditional sum with no
notion of an unmeasured contributor. Carry `*_rows` and `*_rows_unmeasured` counts alongside each sum
and render them together.
*Done when:* the compile-report row for a phase whose `error` rows carry no usage shows the
unmeasured count rather than an unqualified `0`, and a test pins that rendering.

**(c) Do not render an absent figure as `0`.**
`compile-report.render_dispatch_boundaries_body` (near `:371-378`) reads
`phase_data.get('error_total_tokens', 0)` and its siblings; the pre-070 counters `unknown_count` and
`clean_exit_queue_empty_count` in the same loop share the default and move with it. Render an explicit
non-numeric marker when the key is absent.
*Done when:* a fragment lacking `error_total_tokens` renders a cell that is not `0`, and a test
asserts the distinction between that cell and a phase whose measured value is `0`. The existing
exact-row assertion in `test_compile_report.py` (near `:876`, under the comment "This fixture carries
none of the new figures, so they default to 0") **must be updated, not deleted** — it is the
characterization of the defect.

**(d) Anchor the cause-class partition to the enum it partitions.**
`_TERMINAL_WASTE_CAUSES`, `_RETRYABLE_CAUSES` and `_RETURNED_WITH_FINDINGS_CAUSE` (`analyze-logs.py`,
near `:1025-1027`) are hand-written literals in a different bundle from `DISPATCH_TERMINATION_CAUSES`
(`manage-metrics.py`, near `:79-103`), with no test and no structural tie. Re-derive the member count
and the classified/unclassified split rather than trusting this plan's figures.
*Done when:* appending a member to `DISPATCH_TERMINATION_CAUSES` without adding it to one of the
`analyze-logs.py` cause-class tuples (including an explicit `_BENIGN_CAUSES`/`_UNCLASSIFIED_CAUSES`
tuple naming the members that belong in neither spend figure) turns a **named** test red, proven by an
executable negative control that appends a fictitious member.

**(e) Stop publishing `scripts_registered: 0` on the generator's dry-run path.**
`tools-script-executor/scripts/generate_executor.py`'s dry-run early return (near `:1271-1286`)
returns `dict(_EMPTY_SURFACE_STATS)` verbatim, so the payload states `scripts_registered: 0` beside a
non-zero `scripts_discovered`, violating the module's own residual invariant that the three surface
buckets sum to `scripts_registered`. The sibling OSError degradation path already sets
`= len(mappings)`. This site is outside the ledger's bundle and is grouped here because the mechanism
is identical: a writer defaults a count to zero on one path while its sibling sets it correctly.
*Done when:* a dry run over an N-script mapping returns `scripts_registered == N` and
`surfaces_derived + surfaces_reused + surfaces_not_derivable == N`, asserted by a test.

**(f) Refuse booleans in a token sum.**
`check-routing-decisions.sum_execution_log_tokens` (near `:495-499`) tests `isinstance(value, int)`,
and `True` is an `int` in Python, so `total_tokens: true` contributes 1 to a token sum. The sibling
reader of the same column refuses booleans explicitly (`_ledger_reconciliation.py`, near `:145-147`).
*Done when:* `sum_execution_log_tokens({'execution_log': [{'phase': '5-execute',
'total_tokens': True}]}) == 0`, asserted by a test.

**(g) Gate the boundary coverage verdict on the coverage state, not on a truthy sum.**
Compute the coverage state first and render the `Dispatch-boundary total` bullet whenever that state
is decidable **or** the total is truthy, showing a measured `0` as `0`; and persist
`dispatch_boundary_total` (as `0`) whenever `dispatch_boundary_rows_recorded` is persisted, so the two
fields never disagree about whether the file existed.
⛔ `_unclosed_boundary_floor` stays silent for a zero-sum file — there is no floor to fold — which is
why the coverage bullet is the only surface that can carry the verdict. Do not widen it.
*Done when:* a `generate` over a phase row carrying `dispatch_boundary_rows_recorded: 8`,
`subagent_samples: 3` and no non-zero `dispatch_boundary_total` renders a `FAILURE` coverage verdict
naming both producers, pinned by a regression test in
`test/plan-marshall/manage-metrics/test_dispatch_boundary_ledger_population.py`; and the minimal
realistic shape — one synthesized clean-exit row with `subagent_samples: 0` — also renders a verdict.
Correct `manage-metrics/standards/data-format.md`'s claim that the bullet "states the measure's
coverage on every render" so it is true of `cmd_generate` for **every** combination of
`dispatch_boundary_rows_recorded`, `dispatch_boundary_total` and `subagent_samples`.

**(h) Emit the agreement identity for a same-population exact agreement.**
`_reconcile_dispatched_measures` resolves an exact tie via `max(...)`, which returns the first maximal
element, and `_DISPATCHED_MEASURE_FIELDS` is ordered with `total_tokens` first — so a tie always
resolves to `total_tokens`, and the annotation gate (`if winning_field != 'total_tokens'`) then
suppresses it. Three independent producers in exact agreement render no reconciliation line at all.
Record the phase whenever two or more eligible measures were compared and state the relation among
them, including the all-equal case.
*Done when:* a `generate` over a row whose `total_tokens`, `dispatch_boundary_total` and
`subagent_total_tokens` are all equal, with `exact` boundary coverage, renders a line stating that the
measures agree, pinned by a test.

**(i) Stop comparing a dispatched measure against an inline `total_tokens`.**
`beaten` is the row's raw `total_tokens` regardless of whether that field was ruled *ineligible* as
cross-population. Either suppress the relation clause when `total_tokens` was excluded for population
reasons, or render an explicit `(not comparable — total_tokens on this row measures the inline
main-context population)`.
⛔ **Bounded by the adversarial review, and the bound changes the work.** The defect covers the `=` and
`<` relations only. The `>` relation is **sound** and must not be touched: it renders whenever a
dispatched measure beats an *eligible* `total_tokens`, which is a same-population comparison, and
`_token_population` defaults an absent stamp to `dispatched`. An earlier statement that all three
relations are cross-population was found false.
*Done when:* an `inline`-population row renders no `>` / `=` / `<` relation against `total_tokens`
(or renders an explicit not-comparable clause instead), and the two shipped regression tests for the
`=` and `<` relations run against rows whose `total_tokens` is dispatched-population.
⛔ Those two tests (`test_equal_boundary_and_total_annotated_as_agreement`,
`test_smaller_dispatched_winner_annotated_as_below_total`) both construct inline rows and **must be
rewritten, never deleted** — deleting them removes D4's regression coverage entirely.

**(j) Make the coverage figure reference the exclusion declaration.**
The `partial` (and `over`) coverage strings state a bare shortfall; the declaration block explaining
that the shortfall is expected sits in a different section. Append a short pointer to both strings.
Appending after the asserted prefix keeps `test_dispatch_boundary_ledger_population.py`'s verbatim
assertion valid — verify that before landing.
*Done when:* the PARTIAL and over coverage text names or points at the declared exclusion list, and a
test asserts the pointer.

**(k) Account for the change-type fallback in the enumerated class total.**
The `Of the 9 dispatch classes` comment (`manage-metrics.py`, near `:512-522`) and
`data-format.md` (near `:346-350`) carry a folded total that the call graph's dispatch sites cannot be
reconciled against without the run report. Either add `change-type-fallback` to
`DISPATCH_BOUNDARY_EXCLUDED_CLASSES` and restate the totals at both sites, or state explicitly at both
sites that the fallback is folded into `phase-3-outline` and why. Re-derive both totals from
`ref-workflow-architecture/standards/call-graph.md` and the constant — do not copy this plan's.
*Done when:* the enumerated class total and the exclusion list account for the fallback, and
`manage-metrics.py` and `data-format.md` state the same figures.

**(l) Remove or justify `_boundary_measure_is_partial`.**
Its docstring claims it is "preserved for callers that only need the under-coverage bit"; a
repository-wide search finds no production caller, only assertions in
`test_manage_metrics_record_dispatch_boundary.py`. Any one of three dispositions settles it: delete it
with those assertions; give it a production call site; or replace the docstring's caller claim with a
statement that it has none.
*Done when:* a repository-wide search for the symbol agrees with whichever disposition was taken, and
the run report names which one and why.

**(m) Remove the ledger matcher's recursion cliff by deleting the machinery, not rewriting it.**
`_ledger_reconciliation.pair_rows`'s `_augment` (near `:328-340`) raises `RecursionError` on roughly a
thousand same-timestamp rows per side and propagates it as a traceback rather than as a TOON error
block, which the module's own stated rule forbids. An adversarial probe over 21 056 corpora — random,
exhaustive at ≤3 rows per side, dense-tie, and unparseable-timestamp — found plain index-order
first-fit produces **the identical matching and the identical set of unpaired rows**, because the
internal sort makes each execution row's eligible indices a contiguous interval with non-decreasing
endpoints (a convex bipartite graph traversed in order, for which first-fit is already maximum).
⛔ **Do not plan a test that distinguishes the two implementations — none exists.** The original gap's
*Done when* ("reverting `_augment` makes at least one test fail") is **unsatisfiable** and was
superseded by the adversarial review; this is the better one. Add the equivalence note to
`pair_rows.__doc__` naming the internal sort as its precondition, and keep the existing ⛔ paragraph
about why nearest-first greedy was replaced.
*Done when:* `_augment` is gone, `pair_rows.__doc__` states the first-fit equivalence and its
precondition, and a test asserts that `pair_rows` over ~1 200 identical-timestamp rows on both sides
**returns** rather than raising.

---

### D2 — Duration measurement: the line-shape guard, the grammar, and the precision

Owning surface: `plan-retrospective/scripts/analyze-logs.py`, the cross-plan roll-up in
`.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`, and the writer
`manage-logging/scripts/plan_logging.py`. Mechanism: **a duration must come from a line that is a log
entry header, must be parsed by one grammar, and must be published at the precision its shares are
computed against.** Land (a) and (b) together — same file, same function, same principle.

**(a) Gate the per-plan duration reader on the log-line shape.**
`extract_script_durations` applies the duration and notation patterns to every line handed to it;
`analyze_folded_global_logs` first matches the entry-header grammar and `continue`s otherwise. Because
`log_script_execution` emits `exit_code` / `args` / `stdout` / `stderr` as indented continuation lines
on every non-zero-exit call, and the `args` line always carries a notation, captured output can add a
call that never ran. Match each line against the entry-header grammar and search only within its
`rest` group.
*Done when:* over a four-line real ERROR entry whose `stdout:` continuation carries both a notation
and a parenthesised duration, `extract_script_durations` returns exactly the header's one pair; a test
in `test/plan-marshall/plan-retrospective/test_analyze_logs.py` asserts that such a continuation line
contributes nothing to `script_cost_rollup`.

**(b) Make the per-plan duration grammar as strict as the global one.**
`_DURATION_RE` is unanchored and accepts a trailing-dot mantissa; `_GLOBAL_LOG_DUR_RE` is anchored and
strict, so the two instruments can publish different cumulative totals for the same physical line
while the reference documentation calls them "same shape, different population". Anchor and tighten
`_DURATION_RE`, or replace both uses with the one strict pattern. The `except ValueError` in
`extract_script_durations` is **unreachable** under either pattern — keep it if you like, but comment
it as unreachable rather than as a live guard.
*Done when:* `extract_script_durations` returns `[]` for `pm:x:x run (5.s)` and for
`pm:y:y run (1.5s) failed`, and returns the **last** duration (`2000.0`) for
`pm:z:z run (1.5s) retried (2.00s)`; a test asserts each of the three.
⚠ `_DURATION_RE` also feeds `script_duration_p50/p95/max_ms` and `slowest_scripts`, so tightening it
can move pre-existing per-plan figures. Run the whole `plan-retrospective` test tree and re-read the
archived-plan fixtures before landing, and record any moved figure in the run report.

**(c) Publish `total_script_seconds` at the precision its shares are computed against.**
`audit.py`'s `cross_global_log_analysis` rounds the published total to one decimal while the roll-up
total and every `share_pct` are computed at three. Change the published rounding to match.
*Done when:* `cross_global_log_analysis` over a single `(0.04s)` call publishes
`total_script_seconds: 0.04`, and for every roll-up row
`round(row['cumulative_seconds'] / result['total_script_seconds'] * 100, 1) == row['share_pct']`,
asserted by a test. Re-run the whole audit test tree; the adversarial review measured that no in-tree
test pins the old precision, but **re-derive that** rather than trusting it.

**(d) Count the duration-bearing lines the global grammar refuses.**
In `analyze_folded_global_logs`, a line whose duration the strict pattern refuses contributes to
`total_lines` and to nothing else — not `slow_call_count`, not the cost roll-up, and not
`unattributable_calls`, which is incremented only inside the `if dur_match:` branch. One exclusion
class is therefore silent, in a fragment whose whole design claim is that every exclusion is published
so a total is legible as a floor.
*Done when:* `analyze_folded_global_logs` over a log containing one well-formed call and one
refused-duration call publishes a non-zero, separately named counter for the second;
`measured + refused + unattributable` reconciles against the notation-headed line count; and
`plan-retrospective/references/log-analysis.md` documents the new key.

**(e) Establish that the readers tolerate a finer writer precision, and propose the writer change.**
`plan_logging.py` formats durations at two decimals, so any call under ~5 ms records as `0.00s` and
contributes nothing to either roll-up. ⚠ **HYPOTHESIS, and it must not be asserted as fact:** whether
the hot paths this matters for actually sit below that floor is a *timing* claim measured in a
contended tree and unmeasurable from a fresh clone. Do **not** widen the writer format in this run —
it is a `manage-logging` boundary that would mix two precision eras across every historical log and
wants its own era treatment. Land only the reader-tolerance half, and record the writer change as a
proposal for the operator with the era-mixing consequence named.
*Done when:* a test asserts that both duration patterns accept a four-decimal duration such as
`(0.0012s)` and attribute it to the right notation, and the run report carries a proposal describing
the writer widening, its era consequence, and what a corpus-bearing run would need to measure first.

---

### D3 — Footprint resolution reaches its consumers, and names a reason when it cannot

Owning surface: `phase-5-execute/scripts/verify_failure_scope.py`,
`plan-retrospective/scripts/_footprint_resolver.py`, `check-artifact-consistency.py`,
`check-manifest-consistency.py`, and `plan-retrospective/SKILL.md`. Mechanism: **a footprint is
resolved from the plan's own tree or reported unresolvable with a machine-readable reason — never
silently substituted by another tree, and never reported as an unqualified `inconclusive`.**

**(a) Gate the verify-failure footprint on `has_worktree`, and delete the docstring that sanctions the
current read.** These land in **one change** to `verify_failure_scope.py`: the docstring paragraph
stating that "an unresolvable worktree degrades to the current working directory" documents removed
behaviour as current and reads as explicit permission for the defect, while the function's own summary
line and an adjacent comment say the opposite. Replace the direct `worktree_path` read with the shared
gate — `_references_core.resolve_live_worktree(plan_id)`, or an inline `if not context.has_worktree:
return None` — mirroring both peer sites, which document this exact hazard. Keep the existing
`NO_PLAN` sentinel behaviour, which is deliberately main-checkout-bound and has its own test.
*Done when:* with the worktree query stubbed to a `pending` state, `_resolve_declared_footprint`
returns `None` **and** `compute_plan_branch_diff` is never called, with a test asserting **both** — the
"never called" half is required, because a return-value-only assertion passes even if the wrong tree
was diffed and the result discarded. No statement in the file describes a cwd or main-checkout
degradation as current behaviour.
⚠ **Known trade, and it is not a mid-run decision:** a `disabled` (non-worktree-bound) plan currently
gets a legitimate main-checkout measurement and will start reporting `footprint_resolved: false`. Both
peer sites already accept that trade — take the peer-consistent form and **record the trade in the run
report**. Do not branch on the worktree state.

**(b) Stop passing a phantom `--diff-file` to the routing-decisions aspect.**
`plan-retrospective/SKILL.md`'s aspect-13 invocation passes `--diff-file work/footprint.txt`; no step
in the repository writes that file, and `resolve_diff_file_path` now hard-errors on a missing relative
path, which `safe_main` turns into `status: error` and exit 1 — so the resolver recovery built for
exactly this case never runs. Drop the flag from the aspect-13 command and from the matching prose
elsewhere in the same document (re-locate both by searching for `footprint.txt`, not by line number).
Prefer this over adding a producer step: the shared resolver already answers the same question and the
capture is the primary tier.
*Done when:* running the documented aspect-13 command against a plan directory with no
`work/footprint.txt` returns `status: success` with `footprint_source` in
{`resolved`, `unresolved`}, and an integration test asserts that documented invocation form (no test
exercises it today).

**(c) Migrate `check-manifest-consistency` onto the shared footprint resolver.**
`load_diff_files` re-derives a git diff in the process cwd and never imports `resolve_footprint`. The
documented aspect-12 command passes neither `--diff-file` nor `--base-ref`, so the loader returns an
empty result and the withholding helper downgrades every diff-fed check *that would otherwise report a
clean `pass`* to `indeterminate` (a `fail` and a `skip` are deliberately left untouched). Fall back to
`_footprint_resolver.resolve_footprint(plan_dir, live_plan_id)`, setting `evidence_available=True` only
on a resolved footprint.
*Done when:* with `references.realized_footprint` present and no `--diff-file`/`--base-ref`,
`check-manifest-consistency run` reports its diff-fed rules as `pass`/`fail` rather than
`indeterminate`, and a test pins the still-unresolvable case yielding `indeterminate`.
⚠ Rules that have been silently `indeterminate` post-merge will start emitting real verdicts, which may
surface a backlog of manifest-drift findings. Record them; do not suppress them.

**(d) Give the two `inconclusive` returns a reason token, from one shared constant.**
`check_affected_files_recall`'s unresolvable return carries a *state* plus prose;
`check_affected_files_exact_match`'s carries neither, and the block `cmd_run` publishes for it has no
resolution field at all — so a consumer must string-match the prose to tell "never measured" from
"measured, and both sides empty". Three of the five reader sites already publish a named token
(`ARTIFACT_COVERAGE_UNMEASURABLE:`, a typed `unresolved_reason`, and `footprint_source: unresolved`
with a per-check `removal_cause`) — **that corrected count is the adversarial review's, superseding an
earlier "2 of 4"**; re-derive it before quoting it. Export one constant (e.g.
`FOOTPRINT_UNRESOLVABLE_REASON`) from `_footprint_resolver` and publish it in `details` on both
branches, surface `footprint_resolved` in the exact-match block, and give the both-empty
`inconclusive` its own distinct token.
*Done when:* both `inconclusive` returns publish a reason token drawn from one shared constant; the
exact-match block carries `footprint_resolved` and a token that differs between the unresolvable and
both-empty causes; and `plan-retrospective/references/artifact-consistency.md` documents the key
alongside the existing `details` keys.

**(e) Resolve the footprint once per `check-artifact-consistency` run.**
Both check sites call `_resolve_footprint` independently while an adjacent comment asserts the two
checks "must agree on the source of truth" — enforced by convention, not structure. Resolve once in
`cmd_run` and pass the value into the recall check, as is already done for the exact-match check.
*Done when:* `_resolve_footprint` is called exactly once per `cmd_run`, and a test asserts both checks
receive the same object. The recall check's existing tests patch the resolver and will need
retargeting.

**(f) Account for the twelfth truthiness site in the D1 population document.**
A truthiness-predicate sweep over `marketplace/**/*.py` found twelve footprint sites; eleven map to the
published population, the providers, or an unrelated `WorkspaceEdit` footprint. The twelfth —
`_manifest_validation.check_build_verdict_consistent`, whose `if not footprint: return None` guard is
fed a caller-normalized `[]` — belongs in the "Adjacent, deliberately excluded" table with its
reasoning, exactly as the two other receiver-style sites already there. Re-run the sweep rather than
trusting the count of twelve.
*Done when:* the population document accounts for every truthiness-predicate hit in a freshly re-run
sweep, each either in the population or in the excluded table with a stated reason.
⛔ **Guarded:** that document lives inside the landed `250-footprint-read-outside-its-window/`
directory, which may have been deleted at collect. If it is absent from the clone, record this item as
not-applicable with that reason and move on — do not recreate the directory.

**(g) Record a proposal for the two resolvers' divergent tier-1 failure policy.**
The shared whole-chain resolver returns the unresolved sentinel when the tier-1 git diff raises,
discarding tiers 2–4; `analyze-logs`'s scope-deviation resolver falls **through** to the capture /
merge-commit / legacy tiers and documents the deviation. For one live plan with a broken worktree diff
and a valid `references.realized_footprint`, one surface resolves and two report `inconclusive` — two
verdicts about the same plan, in one retrospective run. The direction is safe (a measurable footprint
reported unmeasurable, never the reverse), so this is a consistency and information-loss issue.
Changing `resolve_footprint`'s tier policy changes when the recall check reports `inconclusive` versus
a measured percentage — a shared-contract call this run may not make on its own.
*Done when:* the run report carries a proposal naming both policies, the argued-for one
(fall-through, because a recorded capture is a valid resolution regardless of whether a live diff could
be attempted) and its consequence for archived-mode fixtures; **and** a test lands that pins the
current divergence, so the disagreement is visible rather than latent.

---

### D4 — Every published label names the field and the population behind it

Owning surface: the `Read-cost decomposition` render bullet and lattice row in `manage-metrics.py` and
`manage-metrics/standards/data-format.md`; the CR-7 proxy framing across `plan-retrospective`; and the
chat-provenance classifiers in `_chat_provenance.py` / `_chat_gate_decisions.py` /
`extract-chat-signal.py`. Mechanism: **the label is what a reader carries away; a disclosure clause
underneath it is a correction they may not read.** Where a label asserts a population the figure does
not have, the label is the defect.

**(a) The read-cost decomposition — four gaps, one bullet, one test.**
⛔ **Execute (a) as a single change or the edits overwrite one another.** The render bullet
(`manage-metrics.py`, near `:2313-2318`) and the lattice row (`data-format.md`, near `:49`) carry four
distinct defects at once:
  - the bullet names an identifier, `resident_context_per_call`, that is a key on no record — the
    persisted field is `cache_read_per_tool_use`;
  - the lattice row states the same identity under that same phantom name, while the section's own code
    block states it correctly;
  - the bullet's value label asserts "resident context per tool-use" and then discloses, in the same
    bullet, that the numerator and denominator are different populations — so the reading and the
    correction are the wrong way round. Rename the label to something that asserts no per-call meaning
    (e.g. "read-cost factor (cache_read ÷ tool_uses)") and keep the population-span clause; apply the
    same wording wherever `data-format.md` calls it "the resident-context factor";
  - the second operand is labelled `turns` while it counts **dispatched-subagent tool uses**. The same
    document defines a turn, in the paragraph governing how `cache_read_input_tokens` is billed, as
    "one usage-bearing transcript entry"; no per-phase field carries that count at all. Label the
    operand `tool_uses` in the bullet, the identity block and the lattice row, and replace the
    "many turns vs few" rationale with what the ratio actually supports, stating explicitly that the
    identity is **arithmetic, not causal**. ⛔ Do not invent a turn count — publishing one needs a new
    producer-side field and is out of scope.
*Done when:* the rendered bullet contains no identifier that is not a key on the phase row; no rendered
or documented surface calls the ratio "resident context per call/tool-use" as a measured quantity or
calls `tool_uses` "turns"; the lattice row's identity matches the section's code block; and
§ Read-Cost Decomposition states that the identity is arithmetic rather than a turn-count
decomposition. The render-assertion test in `test_manage_metrics.py` pins the literal bullet substrings
(including `'resident context per tool-use (10,000)'` and `'turns (8)'`) and **must be updated in the
same change**.

**(b) Resolve the two different quantities both named `cache_read_per_tool_use`.**
`analyze-logs.summarize_context_position_cost` emits a per-dispatch **float** summed over the boundary
ledger rows; `manage-metrics` writes a phase-level **int** whose numerator is main-context-window and
whose denominator is dispatched-subagent. Two published figures, one name, not the same number, and
neither document mentions the other. Rename the retrospective's key to state its population (e.g.
`dispatch_boundary_cache_read_per_tool_use`, matching the `dispatch_boundary_*` prefix already used for
that population) and cross-reference both documents, stating that the two are not additively
comparable.
⚠ Sweep `marketplace/`, `.claude/` and `test/` for the key **before** renaming — the retrospective key
is read by report rendering and by archived-plan audit checks, and a partial rename makes a check read
an absent key silently.
*Done when:* a repository-wide search for `cache_read_per_tool_use` returns occurrences from exactly
one of the two producers, and each of the two documents names the other figure and says they are not
comparable.

**(c) State that the decomposition is structurally absent for inline-only phases.**
The contract states the mechanical persist condition and stops there. Because the denominator is the
dispatched-subagent count and an inline step produces no `<usage>` envelope, a phase that dispatched
nothing never carries the field or the bullet — so the decomposition is systematically unavailable on
exactly the phases whose `cache_read` is purely main-context, and a consumer comparing phases cannot
tell "cheap" from "unmeasurable".
*Done when:* § Read-Cost Decomposition names which phase class never carries the factor, says its
absence means "not derivable here" and never "zero read cost", and cross-references § Inline
Main-Context Attribution.
⛔ Do **not** count a test as the closure here: the persist guard reads only `tool_uses` and never the
population discriminator, so any such test passes against today's code and cannot fail against the
omission. The sentence is what closes it.

**(d) Complete the CR-7 proxy-vs-proof relabelling across the surfaces the original run missed.**
The code was softened to say `error_total_tokens` is "the strongest *proxy* … NOT a proof of it", and
the rendered column header was relabelled — but the analyst-facing rule document the retrospective
agent actually follows still instructs it to report terminal-error spend as proven waste, and four
further surfaces still carry the retired framing. Rewrite
`plan-retrospective/references/logging-gap-analysis.md`'s two bullets and their heading into the proxy
framing, consistent with the module preamble; rename the renderer's `wasted` local to `terminal_error`;
correct the "(wasted)" / "genuinely-wasted" comment lines in `test_compile_report.py` and
`test_compile_report_behavior.py`; and align the inline comment in `analyze-logs.py` that sits ~200
lines below the corrected preamble and contradicts it. Consider renaming `_TERMINAL_WASTE_CAUSES` to
`_TERMINAL_ERROR_CAUSES` in the same pass (two use sites; no test references the name).
⛔ The `the accepted causes:` enum set in the same document is pinned by a structural-equality test —
the edit must not disturb that enumeration.
*Done when:* across those five surfaces, no comment, docstring or rule sentence describes `error` rows
as genuinely wasted, non-productive, or as having "bought zero detection" without the proxy
qualification, and the rule document's wording is consistent with the module preamble.

**(e) Close the same-name unbalanced-token hole in envelope pairing.**
`partition_turn`'s tokenizer pairs each close tag with the **innermost** open of its name, which admits
two escapes, both verified end-to-end at 30 turns reporting `operator 30 / no_signal False`:
  - **(a) quoted unmatched open** — a quoted `<tag>` in the body takes the pairing and the real outer
    open is never matched;
  - **(b) quoted close** — a quoted `</tag>` pairs with the outer open and ends the envelope early, the
    stack unwind clears, and the real trailing close becomes ordinary text, so the whole tail is
    residue.
Make the classification fail toward *synthetic* when **any** pairing interpretation leaves no prose
residue. ⛔ A greedy re-pair (each close against the outermost still-open same-name tag) closes (a) and
**not** (b) — cover (b) too, e.g. by treating a turn whose first token is an open `<T>` and whose last
token is a close `</T>` as one envelope and taking that residue if it is emptier.
⛔ **Two constraints that rule out the naive form.** Do not change the innermost-first primary pass,
which the balanced same-name nesting test pins. And any whole-span reinterpretation must still run the
operator-bearing-tag recovery, or a bare `<command-args>do it</command-args>` — first token an open,
last token its close — strips to an empty residue and the operator's typed instruction is dropped,
which a shipped test pins.
*Done when:* `is_operator_authored` is `False` for all three of the quoted-unmatched-open shape, the
quoted-close shape, and the nested-envelope-with-quoted-close shape; a 30-turn transcript of each
reports `no_signal: true` with `operator_turn_count: 0`; and the four prose-preserving tests
(unmatched-open, unmatched-close, prose-after-trailing-envelope, command-with-arguments) plus the two
same-name nesting tests still pass **unchanged**. Any new fallback must be mutation-probed in both
directions — a fallback that is too eager swallows genuine operator prose that merely opens with
markup.
⚠ **HYPOTHESIS on reachability, not on the defect.** The defect itself is OBSERVED. The finding that
neither variant occurs in the reachable transcript corpus rests on a corpus under `.plan/`, which the
clone does not have — so the run **cannot** re-measure it and must not restate it as current fact.
Report the fix as closing a content-reachable hole, latent as last measured.

**(f) Classify text-channel interrupt notices as gate decisions, not free-form corrections.**
`is_operator_authored('[Request interrupted by user]')` returns `True`, so the turn scores in
`operator_turn_count` — the counter documented as *free-form operator corrections* — while the
identical wording is listed as a gate-decision marker on the tool-result side. The two counters exist
precisely to keep those apart. Recognise the refusal/interrupt wordings on the text channel too and
count them as gate decisions, sharing **one** constant between the two modules rather than duplicating
the literals.
⛔ Widening a text-channel prefix list is the direction that can discard a genuine operator turn
quoting the wording: the anchoring and case-sensitivity guards must be **extended to the new list**,
not bypassed.
*Done when:* a user turn whose text is exactly an interrupt notice yields `operator_turn_count: 0`,
`gate_decision_count: 1`, `no_signal: false`, with the shared constant pinned to its literals in both
modules' published-constant tests.

**(g) Stop rendering harness envelopes into the Tier-1 payload.**
`render_reduced` writes a kept operator turn's raw text, envelopes intact, into `reduced_transcript` —
even though `partition_turn` has already computed the residue. Every envelope byte counts against the
read budget and is fed to the Tier-1 prompt as operator signal. Render the residue (plus recovered
operator-bearing text) for kept `user` turns; leave `assistant` context turns as they are.
⚠ **Do not claim a saving.** The only reproducible measurement is the fixture-level one (a 26-byte
operator prose turn plus the shipped reminder fixture renders ~199 bytes where the residue is ~27) —
re-derive even that. Across the last-measured reachable corpus the kept operator turns carried **zero**
bytes of envelope, and that corpus is not in the clone, so no production saving may be asserted.
*Done when:* a turn of operator prose with an attached reminder yields a `reduced_transcript`
containing the prose and not the reminder body, `operator_turn_count` is unchanged, the six chat test
modules still pass, and the run report states the fixture-level figure as the only one it measured.

---

### D5 — Detectors, era stamps, and derived figures with no durable surface

Owning surface: `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`,
`test/plan-marshall/phase-6-finalize/test_finalize_edge_ordering.py`, and
`manage-status/scripts/_cmd_planning_lane.py`. Mechanism: **a detector that cannot fire, a stamp that
does not date the change it spans, and a figure computed and then discarded are all the same failure —
a measurement whose consumer cannot tell that it is stale, partial, or absent.**

**(a) Bump four `CHECK_ERA` stamps to the boundary that changed their checks' semantics.**
`CHECK_ERA` is defined as "the boundary as of which the check's computation is known accurate" and
rides every emitted block as `fixed_since`. Plan 290 changed the semantics of four checks and bumped
none of their stamps: `merge-window-accounting` (new scan roots and an `unmeasured` state that
withholds counts), `global-log-analysis` (an `unmeasured` contract, a substrate probe, a gated summary
metric), `quality-chain` (structurally-pending rows no longer count as genuine, plus two new columns),
and `input-integrity` (a widened blind predicate covering an absent `5-execute` section). A cross-run
diff under an unchanged stamp presents pre- and post-change runs as commensurable. Set each entry to
the boundary that changed it, with the one-line rationale the neighbouring entries already carry — the
convention in force is "a plan that changes a check's semantics bumps that check's stamp", evidenced by
an entry that names its own plan's boundary inline. Re-derive the boundary identifier from that plan's
own record rather than trusting a number quoted here.
⛔ **Do not write the `PR-PENDING` sentinel.** It is resolved by `project:finalize-step-era-stamp-fill`,
a finalize step this lane never runs; an unresolved sentinel would ship.
*Done when:* each of the four entries names a boundary at or after the plan that changed it, and the
check-era model test still passes (it reads `CHECK_ERA` for its expectations, so the bump is
self-consistent; only a test pinning a literal old stamp needs updating).

**(b) Record a proposal on the `CHECK_ERA` contract's scope — do not edit the contract.**
The contract sentence phrases the stamp in *roadmap-era* terms, which on a literal reading would excuse
a non-roadmap plan from bumping anything — while the file's live practice refutes that reading. That is
a governing-contract question, and this run may not self-approve a change to a contract that governs
it.
*Done when:* the run report carries a proposal stating both readings, the evidence for the practice in
force, and the concrete contract-text edit it recommends — with no such edit applied.

**(c) Teach the exploration-share check to read the sub-source fields.**
The check builds its counter set from the five coarse buckets only; the three sub-source byte fields —
index-answerable, doc-residency and unattributed — are persisted per phase and carry a **contractual
partition invariant** (they sum exactly to the exploration result bytes), yet no occurrence of their
names exists anywhere under the audit skill. The epic's whole value case turns on the
index-answerable share, and it is currently readable only one plan's report at a time.
*Done when:* the check reads all three sub-source fields with the same absent-is-not-zero discipline
the coarse counters use, asserts the partition invariant per phase, reports the split alongside the
existing shares, and a synthetic-fixture test asserts that an **absent** sub-source field excludes the
plan while a **measured `0`** is retained. The check's sub-document names the new inputs.
⚠ Keep the two exclusion populations separate: a plan measured for the coarse buckets but archived
before the sub-sources existed must not silently drop out of the existing corpus.

**(d) Report the exploration split per phase, not pooled per plan.**
The parser's own docstring says it sums each counter "across the plan's phase sections", and the row
dataclass carries only a phase count — so one corpus-wide numerator is divided by one corpus-wide
denominator. The source plan's ⛔ guard says in terms: do not pool phases into one headline; report the
per-phase range. A working model for the parse exists in the same file — the billing-composition phase
parser reads the identical `[phase]`-sectioned shape and returns a per-phase mapping presence-only;
the exploration parser differs from it only by collapsing that outer key.
*Done when:* the check's TOON block carries one row per canonical phase with its own contributing-plan
count, and a test asserts that a two-plan corpus whose phases differ produces distinct per-phase shares
rather than one pooled figure.
⚠ The derived cut-points are computed with a degenerate-corpus spread guard; a per-phase population is
smaller and degenerates sooner, so re-apply that guard per phase or the thresholds fire on everything.

**(e) Apply the schema read and the re-entry guard the check inherits but never runs.**
Sound implementations of a three-state schema/partiality read and of a re-entry (`close_count > 1`)
label both exist in the same file and are non-vacuously tested — and **neither is reached from the
exploration-share region**. So a plan whose markers are old-schema, and a phase row closed more than
once (whose counters are therefore sums across closes), both enter the shares unlabelled.
*Done when:* the exploration-share block carries, per plan, the record's schema state and the set of
re-entered phases; a fixture carrying the retired schema keys is reported as old-schema with its shares
labelled as floors rather than admitted clean; and a fixture with a twice-closed phase is
excluded-or-labelled while a once-closed phase is not.
⚠ Labelling old-schema records as floors shrinks the clean corpus and interacts with (d)'s per-phase
degeneracy — report the floored count alongside the clean one rather than dropping it.

**(f) Make the finalize edge canary watch `destroys`, then discharge the failure by re-measuring.**
`test_finalize_edge_ordering.py` asserts, in prose and as a test, that the **consumer** side of an
artifact-level data edge has no frontmatter marker at all. That is false: the extension-point standard
now defines both `reads` and `destroys` as optional consumer-side fields, the order-bands standard
states the ordering obligation they carry, and two finalize steps already declare `destroys`. The
canary's probe set lists only the read-side spellings, so the guard written to force a re-measurement
stayed green when exactly the event it names occurred. Add `destroys` to the probe set — which makes
the canary fail immediately, as intended — then discharge that failure by rewriting the module's
coverage claim and its test, and by either extending the edge derivation to emit `reads`→producer and
`reads`-after-`destroys` edges or stating explicitly that those edges are out of the derivation's
current scope and why.
⛔ **Stop condition, so no mid-run decision is needed:** deriving the new edge class may surface real
ordering violations the gate-relative derivation never checked. If the gate cannot go green without
reordering a shipped finalize step, **do not reorder it** — land the coverage restatement and the
canary widening, record each violation as a finding in the run report, and say the derivation extension
is deferred with the violations named.
*Done when:* adding a `reads:` **or** a `destroys:` declaration to any finalize step document either
produces a derived edge the gate assertion checks or turns a named test red, and no statement in the
module claims the consumer-side vocabulary is empty while the extension-point standard defines it.

**(g) Give the derived edge cardinality a self-refreshing publication surface.**
The only publication of the finalize edge count and its coverage percentage is prose in a dated run
report, which has already drifted. Re-derive the current figures with the module's own derivation
function — **do not carry any number from this plan or from that report** — and publish them where a
reader meets them without running a test file by hand (a report-style entry point on the module, or a
generated line in the extension-point standard refreshed by a test that fails when document and
derivation disagree).
*Done when:* a reader can obtain the current edge count and coverage percentage from the tree without
running a test file by hand, and adding a marker-carrying step updates that surface or fails a test.

**(h) Persist `scope_provenance` alongside `scope_estimate`.**
The planning-lane command computes `scope_provenance`, uses it in a log line, and discards it; only
`scope_estimate` reaches `references.json`. The deep-lane refine step later overwrites
`scope_estimate`, so on a deep-lane plan the router's own input is destroyed by its output while a
light-lane plan keeps it — the evidence survives exactly when nobody needs it, and nothing can audit
whether the lane was right.
*Done when:* after the scope-estimate heuristic persists, `references.json` carries both fields, and a
test asserts the pre-route provenance survives a simulated deep-lane overwrite of `scope_estimate`
(the overwrite records its own provenance under a distinct key).

---

### D6 — The epic's own records: correct what is false, propose what needs a corpus

Owning surface: files under `doc/plans/code-intelligence-substrate/` only. Two mechanisms, one
surface: a record that states a false measurement, and a deliverable that is blocked on a corpus a
clone cannot have.

**(a) GATING STOP-CONDITION — derive corpus reachability first, and halt this deliverable's numeric
half on the answer.** Before anything else in D6, establish whether an archived-plan corpus is
reachable from this clone: list the tracked contents of `.plan/` and probe for
`.plan/local/archived-plans/` and `.plan/local/plans/`. `.plan/` is git-ignored apart from a small
configuration and project-architecture set, so the expected answer is **absent**.
  - If **absent** (expected): the five corpus-blocked items in (c) are discharged as **recorded
    proposals**, never as attempted measurements. Do not improvise a hand-rolled aggregation over
    whatever the clone happens to hold — that is the discipline failure the source plans exist to
    prevent.
  - If **present**: still do not attempt the measurements in this run. Record that the premise changed
    and propose the corpus-bearing work as a separate plan, so this run's scope stays what it was
    authored to be.
*Done when:* the run report states, first-party, which of the two the clone was, with the command used
and its output.

**(b) Correct four false measurement claims in the epic's records.**
Each is a record edit, no code. ⛔ **Guarded:** a landed plan's directory is deleted at collect, so any
of these files may be absent. For each, if the file is absent, record it as not-applicable with that
reason — do not recreate the directory, and do not rewrite a dated record in place where the source
gap asks for the correction to be made in a successor report instead.
  - `020-corpus-residency-admission-control/report-01.md` claims a per-phase byte total *is* "exactly"
    that plan's per-document consumption measure. It is one integer per phase, with no path retained,
    no matching tool-call sub-split, and it measures **residency**, not consumption. Replace the
    equivalence with the accurate relation and name the three shortfalls.
  - `080-exploration-split-…/report-01.md` states in three places that the audit checks read that
    plan's D1 counters; they read a different field family entirely (the coarse buckets, not the three
    sub-source byte fields). State the correction in the resumed plan's report rather than rewriting
    the dated record, naming the three sub-source fields as D1's actual inputs and their writer.
  - The same report's residue says the instrument "already exists — nothing needs building". Restate it
    as **two** prerequisites: the corpus (which needs a corpus-bearing machine) and the per-phase
    sub-source aggregator (D5(c)/(d)/(e) here — **git-derivable, buildable in a cloud clone**), naming
    the aggregator as work rather than as existing.
  - `310-main-sha-records-the-pinned-cwd/report-01.md` asserts a single consumer of the `main_*`
    handshake columns; two further in-file consumers read them (one compares the dirty-file sets, one
    iterates the invariants and explicitly skips the dirty-files column, deferring it to the first).
    Enumerate every consumer and state which were examined.

**(c) Record a proposal for each of the five corpus-blocked measurement deliverables.**
Each proposal names the deliverable, the instrument that exists, the population it needs, and what
"discharged" would look like — so an operator can queue it without re-deriving any of that. No proposal
makes a design call on the operator's behalf, and the run makes none of these measurements itself.
  - **Re-scope the corpus-residency D1, or specify the instrument it needs.** The deliverable asks four
    questions (which documents are read, how often, how many times within one envelope, how much of
    each read document a step consumes); the only instrument in the tree answers the residency half.
    ⚠ The raw material exists one layer down — the exploration walk extracts a per-call target path and
    then discards it into a bucket — so the per-document half is a *retained field* away, not a missing
    capability. The proposal must state the two options (persist the path the walk already extracts, a
    plan-sized change across the runtime and the data-format contract; **or** narrow the deliverable to
    the residency half and move the per-document question to its own deliverable) and recommend one
    **without applying either**, because it is a scope decision with no operator present.
  - **Run the dispatch-waste finding-yield sweep and the class shares.** The population is identifiable
    and the figure is publishable; nobody has read it against a real corpus. The proposal must record
    that D1(a) here must land first, or the retryable half measures as zero and the terminal half
    silently omits unmeasured rows, and that a share computed against an unsettled denominator would
    reproduce the sample-is-not-a-population error.
  - **Perform the exploration-split deliverables from a corpus-bearing session**, after D5(c)/(d)/(e)
    land — reporting the per-phase split with per-phase contributing-plan counts, the addressable share
    as a lower bound until the byte remainder is classified, and every figure with its population,
    phase and sampling point.
  - **Discharge the aggregate-cost roll-up's numeric half.** Run the cross-plan log analysis, read the
    cost roll-up and the sub-precision counter, decide the reduction target from the ranking, and write
    the delivery assertion against whichever path it names.
  - **Stage a successor plan for the envelope-length deliverables.** Unlike the other four, this one is
    **executable here**: author a new plan file at
    `doc/plans/code-intelligence-substrate/{NNN}-{slug}.md` that (i) names the three carried-forward
    deliverables with their ⛔ guards, (ii) states the corpus precondition in its own preamble, and
    (iii) names `090-envelope-length-and-the-isolation-currency` as the plan whose deliverables it
    carries. Re-derive `{NNN}` as the next free sparse-in-tens prefix from a fresh listing of the epic
    directory — **several sibling plans are being authored into the 5xx range concurrently, so do not
    reuse a number from this plan**. ⛔ Do **not** add per-plan status to the epic README: the
    directory shape is the status signal. ⛔ **Stop condition:** if `090-…/plan.md` is absent from the
    clone (deleted at collect), record this item as blocked with that reason rather than inventing
    deliverables from their titles.
*Done when:* the run report carries five clearly separated proposals, each naming its instrument, its
missing population and its discharge condition; and, for the fifth, a new plan file exists such that a
search of the epic directory for `090-envelope-length-and-the-isolation-currency` returns a file other
than 090's own — or a recorded block explaining why not.

**(d) Re-derive six stale figures in the precision-validation run report.**
Six numeric claims in `230-validate-precision/report-01.md` were found wrong or self-contradictory: a
new-test count and a collected-total, an inventory-suite pass count, **two different whole-suite
totals for one `./pw verify` run**, three mutually inconsistent commit counts, an all-guards-off
fixture count belonging to a superseded fixture, and two baseline tables naming no measurement
revision.
⚠ **Every corrected figure is a HYPOTHESIS until this run re-derives it**, and the pass counts
especially: the audit's figures were taken in a shared tree while sibling agents ran full suites, and
the tree has moved since. Re-derive each from the artifact it describes — the test file at the merge
commit, a fresh run of the named directory, the PR's own commit list, the shipped fixture — and where a
figure cannot be re-derived (the whole-suite totals refer to a tree that no longer exists), say so and
state the two populations rather than picking one.
*Done when:* each of the six claims either states a re-derived figure with the artifact it came from,
or states explicitly that it is not re-derivable and names the two populations it conflated; and both
baseline tables name their measurement revision.

## Out of scope

Each exclusion states its reason, because there is no operator to ask mid-run.

- **Every gap not listed in § Gap coverage.** Sibling plans `500`, `510`, `530`, `540`, `550`, `560`
  and `570` in this epic own the rest of the audit's findings, and several touch the same files (see
  Notes). Fixing an adjacent gap here creates a conflict a concurrent run cannot see.
- **The `>` relation in the reconciliation clause (D1(i)).** The adversarial review established it is
  a **sound** same-population comparison; an earlier claim that all three relations were
  cross-population was refuted. "Fixing" it would break a correct branch.
- **The deliberate `--total-tokens 0` on the synthesized clean-exit queue-peek row (D1(a)).** That is a
  measured zero on a row with no agent return to parse — it reaches neither published sum, and
  rewriting it as `unmeasured` would make a true statement false.
- **Widening the log writer's duration format (D2(e)).** It is a `manage-logging` boundary change that
  mixes two precision eras across every historical log line and wants its own era treatment; and the
  claim that it matters rests on a timing measurement no clone can reproduce. Recorded as a proposal.
- **Editing the `CHECK_ERA` contract text (D5(b)).** It governs every check's stamp; a cloud run may
  not self-approve a change to a contract that governs it. Recorded as a proposal.
- **Building the per-document exploration instrument (D6(c), first proposal).** Persisting the target
  path the exploration walk already extracts is a plan-sized change across the runtime and the
  data-format partition contract, and choosing it over narrowing the deliverable is a scope decision.
  Recorded as a proposal.
- **Any measurement that needs `.plan/local/archived-plans/` or `.plan/local/plans/`.** Those trees are
  git-ignored and therefore absent from the clone by construction. This plan names them **only** to
  tell the run not to go looking for them.
- **Reordering any shipped finalize step (D5(f)).** If the widened edge derivation surfaces an ordering
  violation, that is a finding to record, not a reordering to perform — a finalize step's order is a
  contract other steps depend on.
- **The `' ERROR '` space-delimited filter in `analyze-logs.py`'s work-log reader.** A partial sweep
  during the audit confirmed it is real (the writer emits the bracketed form, so the error-line list —
  and therefore the top-error-tags figure — is empty for every real log), but it was deliberately not
  filed as a gap of any plan in this bucket. It belongs to whichever plan owns the work-log reader.
  Recorded here so the run knows it is **real and unfiled** rather than unexamined, and leaves it
  alone.
- **The `PR-PENDING` era-stamp sentinel mechanism.** It is resolved by a finalize step that runs only in
  the local plan-marshall lifecycle, which this lane does not execute; writing the sentinel here would
  ship an unresolved placeholder.
- **Renaming published field names beyond the two the plan names explicitly** (`cache_read_per_tool_use`
  on the retrospective side, and the `wasted` **local**). Every other field name is read by consumers
  outside this plan's expected surface, and a partial rename makes a check read an absent key silently.
- **Running `/sync-plugin-cache` or recording a cache sync as owed.** `CLAUDE.md` § Standalone Plan Lane
  states the sync is inert in this lane: it reads a git-ignored build tree and writes a machine-local
  cache, neither of which a fresh clone has. The merged bundle source is authoritative.

## Expected surface

Re-derive every path by symbol search before editing; line anchors in this plan are leads.

- `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py` — the ledger
  writer, the coverage verdict, the reconciliation, the exclusion declaration, the read-cost bullet.
- `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/_ledger_reconciliation.py` — the
  recursion cliff and the first-fit equivalence note.
- `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md` — the column
  table, the coverage-render claim, the exclusion totals, the read-cost decomposition and its lattice
  row.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py` — the ledger
  parser, the cause-class partition and its sums, the two duration grammars, the folded-global reader,
  the CR-7 comments.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py` — the
  dispatch-boundaries table and its `.get(…, 0)` defaults.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-artifact-consistency.py`,
  `check-manifest-consistency.py`, `check-routing-decisions.py`, `_footprint_resolver.py` — footprint
  resolution, reason tokens, the boolean coercion.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/_chat_provenance.py`,
  `_chat_gate_decisions.py`, `extract-chat-signal.py` — envelope pairing, notice classification, the
  reduced payload.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/logging-gap-analysis.md`,
  `log-analysis.md`, `artifact-consistency.md`, `chat-history-analysis.md` — the analyst-facing rules.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md` — the aspect-12/13 invocations.
- `marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/verify_failure_scope.py` — the
  footprint gate and its docstring.
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md`,
  `.../skills/plan-marshall/workflow/execution.md`, `.../workflow/planning-outline.md` — the
  instructions that currently tell callers to fabricate a `0`.
- `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py` — the
  dry-run stats.
- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_planning_lane.py` —
  `scope_provenance` persistence.
- `marketplace/bundles/plan-marshall/skills/manage-logging/scripts/plan_logging.py` — **read only**,
  to establish the writer's precision for the proposal.
- `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` and its `checks/` documents —
  the lock-step ledger reader, the published total precision, the four era stamps, the exploration-share
  region.
- `test/plan-marshall/manage-metrics/`, `test/plan-marshall/plan-retrospective/`,
  `test/plan-marshall/phase-6-finalize/test_finalize_edge_ordering.py`,
  `test/plan-marshall/audit-archived-plan-retrospectives/`,
  `test/pm-plugin-development/tools-marketplace-inventory/` (read only, for re-derivation).
- `doc/plans/code-intelligence-substrate/**` — the record corrections and the new successor plan file.

## Claim labels

`OBSERVED` means the audit **and** its adversarial review both reproduced the claim by execution.
`HYPOTHESIS` means it rests on reading alone, on a single unreplicated measurement, or on a timing or
corpus figure. Every artifact named below is reachable from a fresh clone.

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The boundary writer defaults an omitted `--total-tokens` to `0` while the context-load columns write `unmeasured`, and both cause-class sums fold that `0` in as measured | OBSERVED | `manage-metrics.py` `cmd_record_dispatch_boundary`; `analyze-logs.py` `_parse_dispatch_boundary_file`; re-run the writer three times against a scratch ledger and read the bytes |
| The audit skill's ledger reader would report an `unmeasured` token as a **measured zero**, silently | OBSERVED | `audit.py` `_BC_LEDGER_FIELDS` vs `_BC_LEDGER_UNMEASURABLE_FIELDS` and `_to_int` — read all three symbols |
| The coverage bullet is gated on a total persisted only when non-zero, so a zero-summing phase renders no verdict | OBSERVED | `manage-metrics.py` `cmd_generate` boundary bullet + the two persistence branches; render a phase row with rows-recorded set and no total |
| The `=` and `<` reconciliation relations render only against an **inline** `total_tokens`; `>` is sound | OBSERVED (bounded by adversarial review) | `_reconcile_dispatched_measures`, `_reconciliation_relation_clause`, `_token_population`; the counter-probe is an unstamped row |
| A row can acquire the `inline` stamp while already carrying dispatched measures, making the defect reachable on real data rather than only in fixtures | **HYPOTHESIS** — established by reading the `enrich` branch, never by running it over a transcript | `manage-metrics.py` `enrich`: the `subagent_*` write and the later `total_tokens_population` stamp. If unreachable in practice the defect is fixture-only; the render fix is correct either way |
| The generator's dry-run path publishes `scripts_registered: 0` beside a non-zero discovered count | OBSERVED | run `generate_executor.py generate --dry-run --marketplace --marketplace-root .` and read the payload |
| `extract_script_durations` parses continuation lines and manufactured a 9.99 s call from a failing script's stdout | OBSERVED | feed one writer-produced ERROR entry to `extract_script_durations` and to `analyze_folded_global_logs` and compare |
| `total_script_seconds` is published at one decimal while its shares are computed at three | OBSERVED | `audit.py` `cross_global_log_analysis` — run it over a synthetic one-line and two-line corpus |
| No in-tree test pins the old `total_script_seconds` precision (measured as a full green audit tree under the candidate fix) | **HYPOTHESIS** — a single suite-count measurement in a contended tree | apply the change and run `test/plan-marshall/audit-archived-plan-retrospectives/`; re-derive the count |
| The three synthetic line bodies the per-plan grammar accepts are emitted by **no current writer** (an asserted absence) | **HYPOTHESIS** | `plan_logging.py`'s message format and `format_log_entry`'s continuation-line emission — read both and search for any other writer of the same shape |
| Calls under the writer's floor record as `0.00s`; whether the hot paths sit below that floor | **HYPOTHESIS** — a timing claim, unmeasurable without a corpus | `plan_logging.py`'s format string is readable; the floor's *impact* is not. Do not assert it |
| The verify-failure footprint reads a worktree path that falls back to the main checkout, and in a clean foreign checkout yields a measured-empty footprint and an `exclusively_out_of_scope: true` verdict | OBSERVED (reproduced from two working directories, and independently on review) | `verify_failure_scope._resolve_declared_footprint`; `PlanContext._resolve_worktree_face`; stub the worktree query to `pending` and spy on the diff call |
| The 343-path cardinality in that reproduction | **HYPOTHESIS / volatile** — it is whatever this checkout's own diff held when measured | re-derive; the stable fact is that a foreign tree is diffed at all |
| The documented aspect-13 command hard-errors because no step writes `work/footprint.txt` | OBSERVED (by execution, twice) | run the documented command against a plan directory lacking that file; then again with the flag omitted |
| Three of the five footprint reader sites already publish a named unresolved token | OBSERVED (corrected from an earlier "2 of 4") | the three sites' emitted keys; re-derive the count before quoting it |
| The envelope tokenizer admits both the quoted-open and the quoted-close escape | OBSERVED (both variants, end-to-end at 30 turns) | `_chat_provenance.partition_turn`; call `is_operator_authored` on the three named shapes |
| Neither escape occurs in the reachable transcript corpus (latent, not active) | **HYPOTHESIS in this lane** — the corpus lives under `.plan/` and is absent from the clone | not re-derivable here. Report the fix as closing a content-reachable hole; do not restate the corpus figure as current |
| The Tier-1 payload saving from rendering residue instead of raw text | **HYPOTHESIS** — the fixture-level figure is reproducible; the corpus-level figure (zero envelope bytes across the kept operator turns) is not | the shipped reminder fixture and `render_reduced`; measure the fixture case and claim nothing beyond it |
| Four checks' semantics changed at a boundary their `CHECK_ERA` stamps do not name | OBSERVED | `audit.py`'s `CHECK_ERA` mapping and the four checks' current implementations |
| The exploration-share region reads none of the three sub-source byte fields, and applies neither the schema read nor the re-entry guard that exist in the same file | OBSERVED (asserted absence, verified by search with a control) | search the audit skill tree for the three field names and for the two guard symbols; the control is the same search under `marketplace/` and `test/` |
| The finalize edge canary is blind to `destroys`, and two steps declare it today | OBSERVED | the canary's marker set; the two step documents; re-run the module's own record discovery with `destroys` added |
| The published finalize edge cardinality (13 in the record vs 14 of 25 re-derived) | **HYPOTHESIS / lead** | re-derive with the module's own derivation function; do not carry either number |
| `_augment` raises `RecursionError` near a thousand same-timestamp rows, and plain first-fit is exactly equivalent on every input the module can produce | OBSERVED (reproduced twice; equivalence probed over 21 056 corpora) | `_ledger_reconciliation.pair_rows`; construct the N≈1 200 case. ⛔ The original gap's *Done when* for this was **unsatisfiable** and is superseded |
| `_boundary_measure_is_partial` has no production caller (an asserted absence) | OBSERVED | repository-wide symbol search; the only hits are test assertions |
| The six numeric claims in the precision-validation record are wrong or self-contradictory | OBSERVED for the **contradictions** (two whole-suite totals, three commit counts); **HYPOTHESIS** for every corrected value | re-derive each from its own artifact at run time; the suite counts were measured in a contended tree |
| No archived-plan corpus is reachable from a fresh clone | OBSERVED, and re-verified as D6(a)'s gating step | `git ls-files .plan` plus a directory probe — this is the plan's one halting premise |

## Verification

Beyond each deliverable's *Done when*:

1. **Build gate.** The lane's conditional Python gate applies: this plan changes Python, so `./pw
   verify` runs and must be green before the PR. Record the command, the commit it ran at, and the
   result. Read the result rather than the exit code where a wrapper is involved.
2. **Red before green, per deliverable.** Every test this plan adds must be shown **failing against the
   defect** and passing after — by reconstructing the pre-fix behaviour (a byte snapshot of the file,
   restored by copy; never `git checkout`/`restore`/`stash`) or by an executable negative control. A
   test added without that demonstration is recorded as unproven, not as coverage. This matters most
   for D1(d) and D5(f), whose whole subject is a guard that could not fire.
3. **Tests that must be rewritten, not deleted.** Name each in the run report with what it now pins:
   the two reconciliation regression tests (D1(i)), the exact-row dispatch-boundaries assertion
   (D1(c)), the read-cost bullet assertion (D4(a)), and the finalize canary's coverage assertions
   (D5(f)). Deleting any of them removes the only regression coverage its deliverable has.
4. **Cold reads — dispatch an independent reader who has not seen this plan, and record which reading
   they took.** These five deliverables are text whose value is the behaviour it produces in a later
   reader; "implemented as specified" cannot verify them:
   - after D4(d): give the reader the rewritten logging-gap rule document and ask what
     `error_total_tokens` asserts. The correct reading is **a proxy for genuinely-wasted spend, not a
     proof of it**. Any reading of "proven waste" means the wording failed.
   - after D4(a): give the reader the rendered read-cost bullet and the lattice row and ask what the
     second operand counts. The correct reading is **dispatched-subagent tool uses**, and that the
     identity is arithmetic rather than a turn-count decomposition.
   - after D4(c): give the reader § Read-Cost Decomposition and ask what it means when a phase carries
     no read-cost factor. The correct reading is **not derivable for this phase class**; a reading of
     "zero read cost" means the sentence failed. This deliverable is closed by that sentence and by
     nothing else — no test can fail against the omission it names.
   - after D1(g): give the reader the corrected `data-format.md` passage and ask what an **absent**
     `Dispatch-boundary total` bullet means. The correct reading is that the boundary file held no
     rows — and that a rows-present, zero-summing phase now renders a verdict rather than nothing.
   - after D5(b): give the reader the `CHECK_ERA` proposal and ask whether a non-roadmap plan that
     changes a check's semantics must bump its stamp. The proposal has failed if the reader cannot
     answer, or answers from the contract sentence rather than from the practice the proposal
     evidences.
5. **Lock-step check by reading, not by executing.** After D1(a), read the audit skill's ledger reader
   and confirm by inspection that the new unmeasured token is classified as unmeasured on **both**
   sides. Its failure mode is a silent measured zero, so a green suite is not evidence here.
6. **Re-derivation ledger.** The run report lists every number this plan quoted, the value the run
   re-derived, and the artifact it came from. Where a figure was not re-derivable (any corpus or
   timing figure), the report says so explicitly rather than repeating this plan's value.
7. **Collateral scan.** Diff the branch against the expected surface and name every file changed that
   the surface list does not predict, with the reason. D2(b) and D4(b) in particular can move
   previously published per-plan figures and keys; any such movement is disclosed, not absorbed.
8. **Proposals are proposals.** Confirm that no contract text was edited for the four proposal items
   (D2(e), D3(g), D5(b), D6(c) first item) — a diff of those files must show no change beyond what a
   named deliverable authorised.

## Notes

**Where the adversarial review overrode the original gap, and it changed the work.** Each gap in this
bucket was re-reviewed after the audit, and where the two disagree the review wins. The cases that
change what this run should do are carried into the deliverables above and repeated here so they are
not lost:

- The reconciliation-clause defect covers `=` and `<` only; `>` is a sound same-population comparison
  (D1(i)). An earlier statement that all three were cross-population was refuted by counter-probe.
- The ledger matcher's original *Done when* — "reverting `_augment` makes a test fail" — is
  **unsatisfiable**: no test distinguishes the two implementations, and the proposed randomised
  property test passes against both. D1(m) carries the replacement, and the fix is a **deletion**, not
  a rewrite.
- The footprint reader-site count is **3 of 5**, not 2 of 4 (D3(d)).
- Two severities were raised on review and this plan treats them accordingly: the published-precision
  defect and the generator's dry-run count are both **high**; the exclusion-reference and reason-token
  gaps are both **medium**.
- The ledger-token risk was corrected: the audit skill would report an unmeasured token as a **measured
  zero**, not as an unrecognised value — a silent failure, worse than the one originally claimed.

**Timing and corpus figures are unreliable by construction.** Several source measurements were taken in
a shared tree while sibling agents ran full suites, and several rest on a transcript or archived-plan
corpus that no clone has. Every such claim is labelled `HYPOTHESIS` above with a named artifact. A run
that restates one of them as established fact has reproduced the defect this epic exists to close.

**Sequencing against sibling plans.** Plans `500`–`570` were authored concurrently from the same audit.
Measured file overlap with this plan:

- `530` (detector and auditor integrity) — `audit.py`, `compile-report.py`, `analyze-logs.py`,
  `check-routing-decisions.py`.
- `550` (test-suite anti-vacuity) — `manage-metrics.py`, `verify_failure_scope.py`,
  `generate_executor.py`, `audit.py`, `_chat_provenance.py`.
- `540` and `560` — `manage-metrics.py`.

None of those plans is a prerequisite of this one and this one is not a prerequisite of them, but they
touch the same files, so **do not run this plan concurrently with `530` or `550`**. If either has an
open PR against these files when this run starts, rebase onto it and re-derive every line anchor;
if a conflict cannot be resolved without changing a sibling's behaviour, stop and report rather than
resolving it unilaterally.

**Internal sequencing.** D1(a) before D1(b), D1(c) and any figure that sums the token column. D1(h)
before D1(i). D2(a) and D2(b) together — same file, same function. D3(a)'s two halves in one change.
D4(a)'s four edits in one change. D5(c)/(d)/(e) before any attempt at the exploration-split
measurements, and D6(a) before anything numeric in D6.

**Machine-local paths named only so the run does not look for them.** `.plan/local/archived-plans/`,
`.plan/local/plans/`, and the transcript corpus behind the chat-provenance reachability figures are
git-ignored. They are **not** in the clone and are **not** to be searched for beyond D6(a)'s single
gating probe. Every confirm/refute artifact in § Claim labels is git-reachable.

**Plugin cache sync is not owed.** This plan edits `marketplace/bundles/`, but `CLAUDE.md` § Standalone
Plan Lane states that `/sync-plugin-cache` is inert in this lane and that a lane plan neither performs
a sync nor records one as owed.

## Gap coverage

Sixty-four gaps: 9 high, 30 medium, 25 low. Each is cited as `{source-plan}/gaps.md#{id}` — git-tracked
corroboration, not required reading; the defect is restated in the deliverable that discharges it.

| Deliverable | Gap | Sev | Defect in one line |
|---|---|---|---|
| D1(a) | `070-dispatch-spend-on-dispatches-that-produced-nothing/gaps.md#G1` | high | Writer defaults an omitted `--total-tokens` to `0`; both cause-class sums fold it in as measured |
| D1(b) | `070-…/gaps.md#G2` | medium | `error_total_tokens` published without the population it was summed over |
| D1(c) | `070-…/gaps.md#G6` | medium | Renderer defaults an absent dispatch-boundary key to `0` |
| D1(d) | `070-…/gaps.md#G13` | medium | Cause-class partition is hand-written literals with no tie to the enum |
| D1(e) | `040-generator-fails-open-and-its-fixtures-cannot-see-it/gaps.md#G9` | high | Dry-run path publishes `scripts_registered: 0` against a non-zero discovered count |
| D1(f) | `340-token-ledgers-disagree-and-the-smallest-is-named-actual/gaps.md#G6` | low | `sum_execution_log_tokens` counts `True` as 1 where the sibling reader refuses booleans |
| D1(g) | `060-dispatch-boundary-ledger-is-not-a-commensurable-population/gaps.md#G1` | high | Coverage verdict gated on a total persisted only when non-zero |
| D1(h) | `060-…/gaps.md#G2` | medium | Exact three-way agreement emits no reconciliation line at all |
| D1(i) | `060-…/gaps.md#G3` | high | `=` and `<` relations compare a dispatched measure against an inline `total_tokens` |
| D1(j) | `060-…/gaps.md#G9` | medium | Coverage text states a bare shortfall with no pointer to the exclusion declaration |
| D1(k) | `060-…/gaps.md#G6` | low | Enumerated class total does not record the change-type-fallback fold |
| D1(l) | `060-…/gaps.md#G8` | low | `_boundary_measure_is_partial` claims a caller population it does not have |
| D1(m) | `340-…/gaps.md#G2`, `#G3` | low, low | `_augment` is provably redundant and carries a recursion cliff that escapes as a traceback |
| D2(a) | `270-aggregate-cost-invisible-to-per-call-ceiling/gaps.md#G14` | high | Per-plan duration reader has no line-shape guard; a stdout line manufactures a call |
| D2(b) | `270-…/gaps.md#G4` | medium | Per-plan duration grammar is unanchored where the global one is strict |
| D2(c) | `270-…/gaps.md#G1` | high | `total_script_seconds` published at a coarser precision than its shares |
| D2(d) | `270-…/gaps.md#G5` | medium | A duration the global grammar refuses is excluded silently |
| D2(e) | `270-…/gaps.md#G13` | low | Writer's two-decimal duration format caps the instrument (proposal only) |
| D3(a) | `250-footprint-read-outside-its-window/gaps.md#G1`, `#G2` | high, medium | Footprint read from a path that falls back to the main checkout, sanctioned by a stale docstring |
| D3(b) | `050-post-run-band-contract-and-ordering-residue/gaps.md#G1` | high | Documented aspect invocation passes a `--diff-file` no step produces, and now hard-errors |
| D3(c) | `050-…/gaps.md#G2` | medium | Manifest cross-check never migrated to the shared footprint resolver |
| D3(d) | `250-…/gaps.md#G4` | medium | Two `inconclusive` returns carry no machine-readable reason token |
| D3(e) | `050-…/gaps.md#G9` | low | Footprint resolved twice per run, with the agreement enforced by convention |
| D3(f) | `250-…/gaps.md#G5` | low | A twelfth truthiness site is absent from the D1 population document |
| D3(g) | `250-…/gaps.md#G7` | low | The two resolvers' tier-1 failure policies diverge (proposal + a pinning test) |
| D4(a) | `030-attribution-populations-and-the-cost-decomposition/gaps.md#G4`, `#G5`, `#G6`, `#G10` | low, low, medium, medium | One bullet and one lattice row name a phantom field, assert a per-call meaning they deny, and call `tool_uses` "turns" |
| D4(b) | `030-…/gaps.md#G3` | medium | Two different quantities published under the name `cache_read_per_tool_use` |
| D4(c) | `030-…/gaps.md#G7` | low | Decomposition structurally absent for inline-only phases, with the consequence unstated |
| D4(d) | `070-…/gaps.md#G4`, `#G8`, `#G9` | medium, low, low | The CR-7 proxy-vs-proof correction never reached the rule document or four comment surfaces |
| D4(e) | `260-chat-signal-provenance-filter-under-inclusive/gaps.md#G1` | high | Same-name unbalanced token lets a synthetic turn read as operator prose |
| D4(f) | `260-…/gaps.md#G7` | low | Text-channel interrupt notices score as free-form corrections, not gate decisions |
| D4(g) | `260-…/gaps.md#G6` | low | Harness envelopes rendered into the Tier-1 payload the residue already excludes |
| D5(a) | `290-auditor-detector-integrity/gaps.md#G8`, `#G9`, `#G10`, `#G11` | medium ×4 | Four `CHECK_ERA` stamps do not name the boundary that changed their checks' semantics |
| D5(b) | (the contract-scope question raised by `290-…/gaps.md#G8`) | — | Recorded as a proposal; no gap id of its own |
| D5(c) | `080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case/gaps.md#G3` | medium | Auditor reads none of the three exploration sub-source byte fields |
| D5(d) | `080-…/gaps.md#G4` | medium | Exploration split pooled per plan where the source plan forbids pooling |
| D5(e) | `080-…/gaps.md#G7` | medium | Exploration-share applies neither the schema read nor the re-entry guard it inherits |
| D5(f) | `050-…/gaps.md#G10` | medium | Coverage canary watches `reads` and is blind to the `destroys` half actually declared |
| D5(g) | `050-…/gaps.md#G8` | low | Derived edge cardinality published only as drifted report prose |
| D5(h) | `350-outline-derived-set-closure-integrity/gaps.md#G12` | medium | `scope_provenance` computed, logged and discarded |
| D6(b) | `020-corpus-residency-admission-control/gaps.md#G1` | medium | Report claims a per-phase byte total *is* the per-document consumption measure |
| D6(b) | `080-…/gaps.md#G1` | low | Report claims the audit checks read D1's counters; they read a different field family |
| D6(b) | `080-…/gaps.md#G2` | medium | Residue handoff says "nothing needs building" where a git-derivable aggregator is missing |
| D6(b) | `310-main-sha-records-the-pinned-cwd/gaps.md#G8` | low | Report asserts a single consumer of the `main_*` columns; there are three |
| D6(c) | `020-…/gaps.md#G2` | medium | D1 is unanswerable from the persisted record — re-scope or build the instrument (proposal) |
| D6(c) | `070-…/gaps.md#G12` | medium | Finding-yield sweep and class shares never run against a corpus (proposal) |
| D6(c) | `080-…/gaps.md#G5` | medium | D1–D4 never performed from a corpus-bearing session (proposal) |
| D6(c) | `270-…/gaps.md#G12` | medium | D1's numeric half, D3 and D4(b) never discharged against a corpus (proposal) |
| D6(c) | `090-envelope-length-and-the-isolation-currency/gaps.md#G6` | medium | D1/D3/D4 have no successor plan — author one (executable here) |
| D6(d) | `230-validate-precision/gaps.md#G6`, `#G7`, `#G8`, `#G9`, `#G13`, `#G14` | low ×6 | Six stale or self-contradictory numeric claims in the run report |

**Coverage check.** High: `040/G9`, `050/G1`, `060/G1`, `060/G3`, `070/G1`, `250/G1`, `260/G1`,
`270/G1`, `270/G14` — nine, all named in a deliverable, none out of scope. Medium: thirty. Low:
twenty-five. Total sixty-four. Re-derive these tallies from the table rather than trusting the
sentence.
