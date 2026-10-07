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

# Detectors that cannot fire, and auditors that cannot read their own inputs

**Epic:** code-intelligence-substrate
**Branch prefix:** fix

## Problem

The `plan-retrospective` aspect scripts, the archived-plan auditor, the marketplace dependency
validator and two smaller validators were each built to notice when something went wrong. An audit of
36 landed plans in this epic found that a large family of those detectors **cannot fire**, **cannot
tell an unread input from a clean one**, or **report a number computed over a population they do not
emit**. Each defect was reproduced by execution, then independently re-reproduced by an adversarial
review pass. The failures are not rare edge cases: several fire on the common path of every plan.

The five that anchor this plan:

1. **`ran_inline` is a fall-through default, not a measurement.** In
   `plan-retrospective/scripts/check-dispatch-audit.py`, `evaluate_dispatch_coverage` classifies a
   finalize step as `no_evidence` only when it has no `execution_log` row at all; *everything else that
   is not a positive integer* falls to `ran_inline`, which the module docstring and the shipped
   standard both present as **proof** the step ran inline. Three materially different inputs collapse
   there: a genuine measured zero; a dispatched step whose `<usage>` tag never arrived (the producer,
   `manage-execution-manifest.py`, states this outcome in so many words — *"a step dispatched without a
   `<usage>` tag reports zeros rather than a missing column"*); and a row with no `total_tokens` column
   at all, which the detector's own `else: value = 0` coercion converts into a "measured zero" before
   the classifier sees it. Because `dispatched` under-counts, `missing_dispatch_emission` — the
   headline finding of the deliverable that built this check — cannot fire for exactly the class of
   step whose instrumentation failed.
2. **A documented key precedence is never exercised at all.** In
   `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`, `_examined_population`'s
   docstring promises *"Precedence, strongest evidence first: 1. `plans_in_corpus` … Read first"*, but
   the implementation is a single `re.search` over an alternation, so whichever key appears **first in
   the block text** wins. Both checks that emit an alias alongside the canonical key emit the alias
   first, so the documented rule is inoperative for 100% of the blocks where it could apply — a rule
   that cannot fire, inside the deliverable built to detect that archetype.
3. **A clean run is classified as a dropped section, with run status `warning`.** In
   `plan-retrospective/scripts/compile-report.py`, the non-emit branch decides emptiness with
   `_fragment_has_payload` while the render path decides it with `_fragment_renders_empty`. The
   real clean-run fragment of `script-failure-analysis` (`total_failures: 0`, `findings: []`) has
   payload keys but renders nothing, so **every plan with no script failures** compiles a
   retrospective naming content that never existed. The same split loses content in the other
   direction: a non-dict fragment carrying real prose lands in `sections_omitted` with `dropped == []`.
4. **The Executive Summary's written branch is unreachable.** `retro_sections.py` registers
   `_executive-summary`, `compile-report.py` renders it, and `references/report-structure.md`
   specifies mandatory content for it — *"a 3-5 sentence narrative that synthesizes all aspects"* — but
   no producer writes the key and `collect-fragments.py` structurally refuses `_`-prefixed keys, so
   every retrospective this system has ever compiled ships without its headline synthesis.
5. **A summary total is computed over statuses the check does not emit.**
   `check-routing-decisions.py`'s `summary` literal counts `passed`/`failed`/`skipped`; the check
   emits `inconclusive`. A run producing two `inconclusive` mis-prune checks reports
   `summary {'passed': 0, 'failed': 0, 'skipped': 0}` — zero checks over two emitted ones, in the
   sibling of a script whose own docstring says *"Silently dropping an unrecognised verdict is exactly
   the absent-reads-as-nothing defect this aspect exists to surface, so it must not be reproduced in
   the aspect's own summary."*

The mechanism behind all of them is the same: **a detector's zero, skip, or default is emitted without
the population, availability signal, or discriminator that would make it readable**, and no guard in
the suite dies when the branch is removed.

## Goal

Every detector this plan touches publishes what it actually measured: a zero carries its population, a
skip carries the availability signal it was derived from, a classification carries the measurement it
rests on rather than a fall-through default, and a summary totals over the statuses its own code
emits. Where a defect's remedy is a genuine design choice rather than a correction, the choice is
**recorded as a proposal for the operator**, not made by the run. Every guard this plan adds or
changes is proven to bite by mutation, because a plan about detectors that cannot fire that ships
guards that cannot fire has reproduced its own subject.

## Deliverables

Six change deliverables plus **D0**, a gating derivation. Each is independently verifiable.

> ⛔ **Every count in this plan is a lead, not a fact.** Line numbers, site counts, row counts, test
> counts and corpus figures below were derived when this plan was authored, against a tree that other
> plans in this epic are changing concurrently. **Re-derive each one at the moment you use it**, and
> locate every citation by **symbol name** first (function, constant, key) with the line number as a
> hint only. Where a re-derived figure disagrees with this plan, the tree wins and the report records
> the difference.

> ⛔ **Sibling plans in this epic touch several of these same files.** Where this plan says a fix is
> owned elsewhere, do not make it here; where it says a fix must be correct in either state, read the
> tree and take the branch the tree is actually in. See § Notes → Sequencing.

> ⛔ **Every "plan directory", `status.json`, `execution.toon`, `work.log` and `logs/` named below is
> an input these scripts read, and every reproduction and test builds a **synthetic** one under the
> system temp dir. The repository's real `.plan/` tree is git-ignored and **absent from this clone** —
> do not go looking for it, and do not write into it. If a reproduction appears to need real plan
> state, that is a sign the fixture is under-built, not that the state must be found.

### D0 — Re-derive the defect set before changing anything (gating)

For each defect named in D1–D6, run the reproduction the deliverable names and record the observed
output in the run report, in a table of `deliverable | defect | reproduced? | evidence`. A defect that
**no longer reproduces** (a sibling plan landed the fix, or the surface moved) is recorded as
*already-fixed* and its deliverable item is skipped — never re-broken to match this plan, and never
reported as fixed by this run.

**HALT condition.** If the reproduction harness cannot be exercised at all — the named scripts are
absent, or the test trees do not collect — **stop and report the run blocked** with the evidence. Do
not reconstruct the defects from this plan's prose and change code on the strength of it: this plan's
whole subject is the difference between a measurement and an assumption.

*Done when:* the report carries the reproduction table with one row per D1–D6 item, each row naming
either the observed output that reproduces the defect or the evidence that it no longer exists.

### D1 — `check-dispatch-audit` publishes measurements, not defaults

Owning surface: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-dispatch-audit.py`,
its standard `…/plan-retrospective/standards/execution-context-dispatch-audit.md`, and
`…/plan-retrospective/SKILL.md`. Nine defects, one output contract.

**(a) The token discriminator.** Make `finalize_token_records` return `dict[str, int | None]`, mapping
an absent, non-integer or non-digit-string `total_tokens` to `None` instead of `0` — this replaces the
`else: value = 0` fall-through coercion — and route a `None` to `no_evidence` in
`evaluate_dispatch_coverage`. Re-document the surviving `ran_inline` bucket in the module docstring,
in the standard, and in `SKILL.md` as *"a recorded zero token attribution — an inline step, or a
dispatched step whose `<usage>` tag was not captured"*: an **upper bound** on inline execution, never
proof of it. Extend the `missing_dispatch_emission` floor note to name this as a second reason the
count under-reports. An explicit integer `0` still classifies as `ran_inline` — that bound is what
keeps the change from turning legacy rows into noise, and the `dispatched` count is unchanged, so no
currently-clean plan starts reporting `missing_dispatch_emission` because of this fix.
*(Covers 170/G13.)*

**(b) Scope `channel_completeness` to the caller it grades.** `cmd_run` already computes
`finalize_dispatch_line_count` (finalize-only) for `evaluate_dispatch_coverage`, but hands
`len(dispatch_lines)` — the **all-caller** total — to `evaluate_channel_completeness`, while both of
that block's other figures are finalize-only. Pass the finalize-scoped count instead, and publish
**both** figures in the block (`dispatch_line_count` scoped to finalize, plus a separate
`all_caller_dispatch_line_count`) so the scoping is legible rather than implicit. State the scope in
the standard's prose and in its Output TOON Schema comment. *(Covers 170/G1.)*

**(c) A `not_evaluated` grade for `channel_completeness`.** Add a fourth grade —
`confidence: not_evaluated` with a `reason` — for the case where all three inputs are zero, so a plan
with no logs at all can no longer be graded `nominal`. Update the existing test that asserts
`nominal` for the log-less fixture, extend the schema block, and add the new grade to the LLM
interpretation rule (which today tells the reader to act only on `none` / `low`). *(Covers 170/G2.)*

**(d) No bare zero in the aggregate `counts` block.** `counts.by_category.shape_violation` is emitted
as a bare `0` in both the never-evaluated and the evaluated-clean case, in the same output where the
nested block correctly reports `status: not_evaluated, evaluated_population: 0`. Emit it as a
structured value carrying its population and status (or omit it when the shape check did not
evaluate); mirror the choice in the standard. In the same change **tighten
`compile-report.py::_names_checked_set`**, the in-tree ambiguity probe: `counts` is a member of
`ZERO_ATTRIBUTION_FIELDS` in `retro_sections.py`, so today a non-empty `counts` dict *by itself*
satisfies the "this fragment names what it checked" probe — the log-less fragment passes on the
strength of the block that names nothing. *(Covers 170/G3.)*

**(e) An evaluated population for the two list-returning checks.** `evaluate_envelope_violations` and
`evaluate_generic_subagent` return bare lists and `cmd_run` publishes only their lengths, so nothing
in the output distinguishes "scanned 400 log lines, found no generic subagent" from "work.log was
absent". Return `{evaluated_population, violations, findings}` from both (population = the dispatch
lines inspected, and the work-log lines scanned, respectively) and surface both blocks alongside
`shape_violation` / `dispatch_coverage`. Extend the documented schema. `generic_subagent_violation` is
described in the shipped standard as *"the highest-priority remediation target"*, so an unreadable
zero there is the worst instance of this class. *(Covers 170/G4.)*

**(f) An explicit not-evaluated status on `dispatch_coverage`.** `load_status_metadata` swallows a
missing file, an `OSError` and a `JSONDecodeError` into `{}`, so the coverage block reports all-zeros
with no `status` and no `reason` — indistinguishable from a plan that genuinely completed zero
finalize steps and from one whose `status.json` is corrupt. Return `status: 'not_evaluated'` with a
reason naming which surface was missing, matching the shape its sibling block already uses.
*(Covers 170/G5.)*

**(g) Signed per-role pairing for `shape_violation`.** The pairing is a `Counter`-vs-`Counter`
subtraction and only a **positive** difference produces a finding, while the `[DISPATCH]` side counts
lines from every caller and the decision-log side carries no caller at all. This is live, not
theoretical: `role=verification-feedback` has both a seam-emitting producer and a hand-written one at
HEAD, so a hand-written line cancels a genuine shortfall one-for-one. Publish a per-role breakdown —
rows carrying `role`, `resolves`, `dispatch_lines` and a **signed** `delta` — keeping the *finding* on
`delta > 0` and reporting `delta < 0` as a fact, so plans with hand-written lines do not start
failing. State the caller-blindness in the standard beside the existing corroboration-limit
blockquote, naming the hand-written `[DISPATCH]` sites as the reason a role's line count can exceed
its resolve count without any dispatch being unrecorded. **Re-derive that site list** — the audit
found seven, and the tree has moved. *(Covers 170/G15.)*

**(h) De-duplicate re-fired dispatch lines, and name the population.**
`missing_dispatch_emission` is `max(0, len(dispatched) - finalize_dispatch_line_count)`, and finalize
re-resolves on every firing, so a step that re-fires contributes multiple lines but one `dispatched`
entry — masking a different step that dispatched with no line. Exact per-step pairing needs a step id
in the `[DISPATCH]` line, which is an emission change in another skill's lane and is **out of scope**
(§ Out of scope). The scoped fix: deduplicate finalize `[DISPATCH]` lines by `(role, workflow)` —
not by role alone, which would collapse distinct steps — before the comparison, and list the
`dispatched` step ids in the block beside the existing `no_evidence_steps` so the finding's population
is nameable. *(Covers 170/G8.)*

**(i) Cross-reference the corroboration limit.** The standard's `shape_violation` interpretation rule
tells the reader that findings indicate *"a resolve that never emitted its canonical `[DISPATCH]`
line"*. Both surfaces are written back to back by one call (`manage-config/scripts/_cmd_effort.py`'s
dispatch-record emitter), so a clean `shape_violation` over a populated population confirms only that
the seam's two writes agree. The substantive warning is already shipped, four sections away, in a
blockquote the interpretation rule does not point at. Extend the rule to name the shared emitter and
link that blockquote. *(Covers 170/G10.)*

*Done when:* (1) a fixture whose `execution_log` row carries **no** `total_tokens` column classifies
as `no_evidence`, and one carrying an explicit `total_tokens: 0` still classifies as `ran_inline`,
both pinned by tests; (2) a fixture with N phase-5 `[DISPATCH]` lines, zero finalize `[DISPATCH]`
lines and ≥1 token-proven dispatched finalize step reports `confidence: none`, not `nominal`; (3) the
log-less fixture reports `confidence: not_evaluated` with a reason, and no input combination that
evaluated nothing can report `nominal`; (4) no consumer can read `counts.by_category` alone and
mistake a `not_evaluated` shape check for an evaluated-clean one; (5) a run against a plan with no
`work.log` and a run against a populated clean `work.log` produce visibly different output for both
list-returning checks; (6) an absent `status.json` and a valid one carrying an empty `6-finalize` map
are distinguishable in the output; (7) a fixture carrying one resolve record for a role, no seam
`[DISPATCH]` line for it, and one hand-written `[DISPATCH]` line for the same role reports a non-zero
signal instead of `violations: 0`; (8) a fixture with 2 dispatched steps, 3 finalize `[DISPATCH]`
lines sharing one role, and one step lacking any line reports `missing_dispatch_emission >= 1`, and
the coverage block lists the dispatched step ids; (9) the interpretation rule names the shared emitter
and links the corroboration blockquote; and (10) every guard above is mutation-proven per
§ Verification.

### D2 — The retrospective report's section partition, and its two producerless registry rows

Owning surface: `…/plan-retrospective/scripts/compile-report.py`, `…/scripts/retro_sections.py`,
`…/references/report-structure.md`.

**(a) One discriminator for the drop/omit split.** Today the non-emit branch decides emptiness with
`_fragment_has_payload` while the render path uses `_fragment_renders_empty`, and the two agree only
for dicts. Replace the non-emit branch's predicate with **the same question the render path asks**:
*would this section render a usable body?* If yes, a non-emitted fragment is a **DROP**; if no, it is
an **OMISSION**. That single rule discharges four defects at once:

- a non-dict fragment carrying content (a bare non-empty string, an int, a list) on a conditional row
  is currently reported as *nothing was lost* — a silent content loss on a live production path: the
  TOON parser really does return `{'script-failure-analysis': '<prose>'}` for an aspect that wrote
  prose instead of a fragment, and `build_document` on it omits the section with `dropped == []`.
  This contradicts `report-structure.md`, which states that a fragment present, carrying payload and
  not rendering *"is a **drop**, not an omission, and must be reported as such"*. *(170's sibling
  archetype; covers 330/G1.)*
- the real clean-run `script-failure-analysis` fragment (`status: success`, `total_failures: 0`,
  `findings: []`, `lessons: []`, plus provenance keys) has payload but renders nothing, so **every
  plan with no script failures** reports `sections_dropped: ['Script Failure Analysis']` and run
  status `warning`. Stripping the provenance paths alone does not fix it — `plan_id` is the first
  payload key — which is why the render-path question, not a key blocklist, is the fix.
  *(Covers 330/G2.)*
- `check-manifest-consistency`'s and `check-routing-decisions`' real manifest-less fragments
  (`status: skipped`, `reason: '<file> not found'`, empty check lists) are both reported as dropped,
  so every plan that never had an `execution.toon` is reported as having lost content. Their skipped
  shapes **differ** — routing has no `findings` key at all — so verify against each producer's own
  output rather than assuming one follows from the other. *(Covers 330/G3, 330/G4.)*

⛔ **Do not narrow the carve-outs this touches.** A `skipped` fragment that *does* carry findings must
keep rendering (the `chat-history-analysis` carve-out depends on it), and `should_emit`'s
routing-decisions carve-out must keep emitting the findings-less *success* shape. Both are guarded
today; both must stay guarded.

The adversarial review of the source audit recorded the open question this leaves: the four defects
above were each reproduced against **one** fragment shape apiece, and the remaining conditional rows
(`permission-prompt-analysis`, `chat-history-analysis`) were never driven through their producers'
real clean-run outputs. Close that: run a **differential over every conditional row × every
deterministic producer's real output** and record the before/after partition per cell.

**(b) Record a proposal for the two producerless registry rows — do not decide.** Two rows in
`SECTION_SPEC` have no producer:

- `_executive-summary` — registered, rendered by the compiler, and specified in
  `report-structure.md` with mandatory content (*"a 3-5 sentence narrative that synthesizes all
  aspects. It must lead with overall severity … and the most important signals"*), while
  `collect-fragments.py` structurally refuses `_`-prefixed keys and no documented step injects one.
  The compiler is **not** at fault: `report-structure.md` makes the section conditional on a body
  existing and the compiler conforms exactly. The defect is producer-side, and its consequence is that
  the document's headline synthesis has never once been produced. *(Covers 330/G6.)*
- `dispatch_boundaries` — registerable (it is in the valid aspect-key set) but written by nothing at
  the top level: the only writer returns the per-phase block as a key *inside* the `log-analysis`
  fragment, so the top-level lookup never finds it and the dedicated section lands in
  `sections_omitted` on every run while its renderer stays live and correct. Nothing is lost from the
  compiled document — the same data still renders inside Log Analysis — so what is missing is the
  dedicated per-phase table, not the facts. *(Covers 330/G5.)*

Each admits two defensible resolutions (add a producer / delete the row and its documentation entry),
and each resolution is a contract change: an injection step adds an LLM-authored surface to a compiler
documented as a pure assembler, while deletion removes a specified capability. **This run makes
neither call.** It records a proposal carrying, per row: the re-derived evidence (what the compiler
does today, what greps for a producer return, what `SECTION_SPEC` minus the aspect-table keys is), the
two options with their measured consequences, a recommendation with its reasoning, and the note that
`report-structure.md`'s content requirement for `_executive-summary` must be resolved by whichever
option is taken. **Write the proposal into the run report *and* into the PR description**, because a
landed plan's directory under `doc/plans/` is deleted when the orchestrator collects it, and the PR is
what survives.

*Done when:* (1) `build_document` on a bundle whose `script-failure-analysis` key holds a bare
non-empty string returns `dropped == ['Script Failure Analysis']`, with a parametrized test covering a
string, an int and a list on a conditional row; (2) compiling the producers' **own** clean/skipped
output for `script-failure-analysis`, `manifest-decisions` and `routing-decisions` yields
`sections_dropped == []` and `status: success`, with tests built from producer output rather than
hand-written fixtures; (3) the differential over every conditional row × producer status is recorded
in the report, and the two carve-outs above are shown still to fire; (4) the divergence paragraph
`report-structure.md` currently records for the manifest-less case is deleted rather than left behind a
closed gap; and (5) the report and the PR body each carry the two-row proposal, and **no** change to
`SECTION_SPEC` or to `report-structure.md`'s `_executive-summary` entry is made by this run.

### D3 — The remaining `plan-retrospective` checks stop hiding their own inputs

Owning surface: `…/plan-retrospective/scripts/check-manifest-consistency.py`,
`…/scripts/check-routing-decisions.py`, `…/scripts/analyze-logs.py`,
`…/references/routing-decision-verification.md`, and one emitter in
`marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py`.

**(a) Rule M4 gets the availability signal instead of inferring it.** Run against an existing but
empty `--diff-file`, the script emits `diff: {base: 'file:empty.txt', …, diff_available: True}`
alongside `branch_cleanup_changes: skip — "rule M4 skipped — no diff data available (base=unknown or
empty diff)"`. The message is false about its own inputs, two lines from the field that contradicts
it. The loader already computes `evidence_available` and `cmd_run` already stores it;
`evaluate_branch_cleanup` is handed only the base label and the raw file count and re-derives
availability from `len(files) == 0` — the exact inference the module docstring forbids. Thread
`evidence_available` in and skip only when it is `False`; when evidence exists and the diff is
genuinely empty, **evaluate** the rule (a resolved empty footprint with `branch-cleanup` scheduled is
the `branch_cleanup_without_changes` finding, worded for an empty *observed* diff rather than a
filtered-away one). *(Covers 320/G2.)*

**(b) The routing summary totals over the statuses it emits.** Replace the three hard-coded
comprehensions in `check-routing-decisions.py`'s `summary` literal with a total counter over the check
list — a status-bucket map with an unknown-status fallback, or the sibling script's `summarize_checks`
shape, whose docstring already states why this must not be reproduced. *(Covers 320/G3.)*

**(c) `diff_available` stops defaulting optimistically.** `filter_bookkeeping` seeds
`reduction['diff_available'] = True` and relies on its single caller to overwrite it; the value is
read to decide whether to withhold verdicts, so a caller that forgot would assert evidence that never
existed. Default it to `False` — the fail-closed direction — keeping the caller's assignment in
lock-step. ⚠ If seeding `False` reddens tests because a fixture relies on the optimistic seed, do
**not** weaken the tests: take the other form the gap names instead — drop the key from
`filter_bookkeeping`'s output and make `apply_input_reduction` take `diff_available` as an explicit
parameter, so it cannot be forgotten. Both satisfy the same *Done when*; the choice is settled by
running the suite, not by judgement. *(Covers 320/G9.)*

**(d) `frozen_manifest_stale` removals become readable.** The `reconcile` verb emits its dropped-step
record without a `[STATUS]` tag and with the step id wrapped in backticks; the routing check's shared
pattern requires the tag, and no per-mechanism pattern covers this shape, so `resolve_removal_causes`
returns no cause and a prunable step removed by reconcile is reported as a `mis_prune` whenever the
realized footprint touched production code — the false verdict the check exists to end, on a live
path. Route the emission through the shared `format_dropped_record` formatter (dropping the backticks,
since the reader's capture expects a bare or prefixed step id); this closes the sibling
`frozen_manifest_backfill` shape drift too. **Retain a legacy pattern for archived logs**, exactly as
the existing legacy-aggregate precedent in the same reader does — archived logs carry the old shape and
must keep resolving. Retire the counter-example paragraph in
`references/routing-decision-verification.md` in the same change. *(Covers 290/G5.)*

**(e) Total per-task ARTIFACT emission failure becomes reportable.** In `analyze-logs.py`, the
partiality guard fires only for `0 < N < M` and the comment defers the `N == 0` case to a plan-level
floor. That floor counts `[ARTIFACT]` lines from **every** caller, and `phase-1-init` emits
`[ARTIFACT]` unconditionally on every plan, so the floor is **provably dead**: a plan with 3 completed
tasks, 0 per-task `[ARTIFACT]` lines and 2 phase-1 lines produces zero findings. Widen the partiality
guard to `N < M` and give the `N == 0` case its own message distinguishing *"this plan uses no
per-task emission"* from *"emission was bypassed"* — the discriminator is whether the plan's footprint
is non-empty, which the surrounding code already resolves. Correct the comment. Scope the new finding
on the footprint so archived plans predating per-task emission do not start reporting it.
*(Covers 170/G7.)*

*Done when:* (1) with an existing empty `--diff-file` and `branch-cleanup` scheduled,
`branch_cleanup_changes` is no longer a skip carrying "no diff data available", and with neither
`--diff-file` nor `--base-ref` it still skips — both pinned; (2) a run producing two `inconclusive`
mis-prune checks reports `inconclusive: 2`, with a test asserting
`sum(summary.values()) == len(mis_prune_checks)` over a list containing every status the script emits
**plus one unknown**; (3) no code path can reach the verdict-withholding logic with `diff_available`
unset-but-true, pinned by a test that constructs a reduction block without the caller's assignment;
(4) a test staging a decision log containing the reconcile stale line asserts the removal cause
resolves, and a second test asserts an archived-shape line still resolves; (5) a fixture with M ≥ 1
completed tasks, zero per-task `[ARTIFACT]` lines, a non-empty footprint and at least one non-task
`[ARTIFACT]` line produces a finding, while a plan that legitimately has no completed tasks does not;
and (6) every guard above is mutation-proven per § Verification.

### D4 — The archived-plan auditor reads what it claims to read

Owning surface: `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` and its `checks/`
documents. This tree is **project-local**, not a marketplace bundle; it is git-tracked and present in a
fresh clone.

**(a) `_examined_population` honours its documented precedence.** Replace the single alternation
`re.search` with an iteration over the population-key tuple in order, searching a per-key pattern and
returning the first key that matches. Keep the key set as it is. *(Covers 290/G1.)*

**(b) `check_input_integrity`'s docstring matches its predicate.** The docstring says the bucket is
`blind` *"exactly when the 5-execute phase recorded zero tokens"*; the shipped predicate is
`(execute_absent or execute_recorded_zero) and not execute_marker_explained` — wrong in both
directions. Rewrite the sentence to name both routes into `blind` and the marker carve-out, matching
the check document, which already states it correctly. *(Covers 290/G2.)*

**(c) The second cwd-walk-up root resolver.** `_resolve_repo_root` walks up from `Path.cwd()` to the
nearest ancestor holding `.plan/local` and falls back to the working directory itself; the returned
root then derives the lessons corpus and the archived-plan tree. `lessons-learned` is a sanctioned
**main-anchored** path with a shared resolver that other callers already use, so resolving it by a cwd
walk-up means that, run from a pinned worktree, the auditor reads the worktree's corpus and reports a
partial read as a corpus fact. Route the main-anchored reads through the shared resolver; keep the
walk-up only for genuinely cwd-scoped paths and make the fallback explicit about what it means. If the
archived-plan tree is intended to be cwd-scoped, say so in the docstring so the divergence is a
decision rather than an accident. *(Covers 310/G3.)*

**(d) The retired footprint key.** `inputs.modified_files_count` reads `references.modified_files`, a
key the current writer no longer emits and that the references data model no longer carries. The
consequence is **not** uniform blindness, and the audit's first reading of it was corrected on
adversarial review — re-derive per call site: three consumers read
`modified_files_count or affected_files_count` and so silently **substitute the declared footprint for
the realized one** (harder to notice than a zero); one reports a hard `0`; and the shipped-plan
predicate carries an independent PR-record criterion, so the shipping partition is not meaningfully at
risk. Resolve the footprint through the same tier order the shared resolver uses —
`realized_footprint` → `merge_commit_sha` → `modified_files` — inside `audit.py`, and update the check
documents to name the resolved source rather than the raw key. *(Covers 050/G4.)*

**(e) The reconcilability claim in the global-log-analysis check document.** Two lines promise each
row's share is a share *"of the published `total_script_seconds`"*, and the same claim appears in two
in-code comment blocks. The shares are computed against a 3-decimal total while the published figure
is rounded to 1 decimal, so they do not reconcile below ~1 s. **The precision fix itself is owned by a
sibling plan** (§ Out of scope). Read the shipped rounding at the moment of the run: if the published
total already carries the precision the shares use, the claim is true — record that and change
nothing; if it does not, amend both document lines and both comment blocks to state the precision
difference explicitly. The branch is settled by reading the code, not by a decision.
*(Covers 270/G2.)*

**(f) Settle or refute the unlocated warning claim.** A claim carried by an earlier plan asserted that
some `WARNING`-level emission fires **at every boundary regardless of condition**, training readers to
ignore the channel it shares with real warnings. Two independent searches have failed to locate it,
and both composer warning families that were checked (`_lane_keep_decision` and the ceremony
pre-filter) are conditional, so neither fires at 100%. ⚠ The plan that carried the claim lives under
`doc/plans/` and its directory **may already have been collected and deleted** — do not depend on it;
everything the claim asserted is restated here. Run a bounded sweep of `WARNING`-level emissions
across `manage-execution-manifest`, `manage-metrics` and `plan-retrospective` for one whose guard is
unconditional at a boundary, and **record either the site or an explicit refutation** in the run
report. Refutation is an expected and acceptable outcome; the adversarial review that re-checked this
raised the prior that the claim is simply wrong. If a site *is* found, do not silently remove or
narrow the warning — record it, and gate any change on a test showing the warning still fires on the
condition it names. *(Covers 290/G6.)*

*Done when:* (1) a test stages one block carrying two different population values in **both** orders
and asserts the canonical key's value is returned in both, and that test is **confirmed to fail**
against the pre-fix single-alternation implementation; (2) a grep for the retired docstring sentence
returns nothing and the docstring names both routes into `blind`; (3) the auditor derives its
lessons-corpus path from the shared main-anchored resolver, with a test asserting that from a cwd
inside a linked worktree the resolved corpus is main's; (4) a fixture plan whose `realized_footprint`
is **disjoint** from its `affected_files` is graded against the realized set at each of the four
consuming sites — the disjointness is what stops the existing fallback from satisfying the test; (5)
the check document either needs no edit (recorded, with the shipped rounding quoted) or states the
precision difference at every site that claims recomputability; and (6) the report carries the warning
sweep's verdict — a named `path:line`, or a refutation naming the population swept.

### D5 — The dependency validator, and the detector that would have caught its drift

Owning surface: `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/`
(`resolve-dependencies.py`, `_dep_detection.py`, `_dep_index.py`, `SKILL.md`) and
`marketplace/bundles/pm-plugin-development/skills/plugin-doctor/`.

**(a) Partition the unresolved rows by reason.** A large share of `validate`'s unresolved rows name a
first segment that is not an indexed bundle at all (build-tool notations, timestamp format strings,
CVE literals), which is why `validate` is documented as a report rather than a gate. Add a per-row
reason field distinguishing `unknown-bundle` from `missing-component` — rather than suppressing by
bundle membership — and update the SKILL's § "Precision of `validate`". **Re-derive the row counts**;
the corpus figures move with concurrent edits and the audit measured them on a shared tree.
*(Covers 230/G15.)*

**(b) Dispose of the nested-module rows through that mechanism.** The largest single finding group
names a module that lives one directory below the component glob, which recurses no further than
`scripts/*.py`, so **no rename alone can make the mapping resolve**. Widening component discovery into
`scripts/{subdir}/` would add components to a namespace that `deps`, `rdeps`, `tree` and the
architecture projection all key on — a contract change this run does **not** make. Instead, discharge
the gap's own *Done when* through (a): re-classify those rows with a stated reason naming the
nested-module mechanism, and **record the namespace-widening option as a proposal** in the run report
and the PR body, with the measured row count and the consumers it would affect. *(Covers 230/G16.)*

**(c) Make the three unconditional drops provisional.** The comment-line skip, the URL-line skip and
the `http`/digit segment filters discard matches outright instead of recording an exclusion, so a
broken notation written on a markdown heading or beside a URL is invisible to the gate and the graph
under-reports real edges. Route all three through the same `Exclusion` mechanism the other predicates
use, adding a member per shape, so the index decides on existence. Measured when the gap was filed:
neutralising the comment-line skip alone gained 11 edges, 9 of which resolve, with 2 surfacing as new
unresolved rows — both non-references (an illustrative `foo:bar` inside a code comment, and a Trivy
ignore literal). **Those figures are leads** — the corpus moves — and the two non-reference rows are
the ones to expect and disclose, not to suppress. *(Covers 230/G19.)*

**(d) Check that a retargeted verb is registered.** The retarget asks only whether a shape *may* bear
a verb and whether an entry script exists; it never asks whether the segment is one the entry script
registers, so a notation naming a verb that does not exist resolves clean. This is the one place the
change *adds* resolutions, so it is the one place it can manufacture a false clean verdict. Validate
the segment against the entry script's argparse surface using the helper `plugin-doctor` already uses,
and leave the row unresolved when the verb is not registered. Expect some live retargets to turn back
into findings; disclose the delta rather than tuning it away. *(Covers 230/G20.)*

**(e) A `plugin-doctor` rule for verb-set drift.** No rule in the quality gate compares a script's
argparse **subcommand set** against the verbs its skill documents — the two nearest rules compare a
documented flag enum against `choices=` and a stated integer count against a derived population.
⛔ **Re-verify that absence before building** (it is an asserted absence, the highest-risk claim
shape): re-run the whole-tree quality gate, list the registered rules, and confirm none does this. Then
add an analyzer that, for each skill carrying a canonical-invocations block, AST-parses the owning
script's `add_parser` calls to derive the live verb set and compares it against the verb names the
skill's `SKILL.md` and `standards/` contract document, emitting a `verb_missing_from_docs` and a
`phantom_documented_verb` finding class. Follow the house discipline the sibling rules state: derive
the population (never hard-code a script list), publish the population size on every finding, and fail
**closed** — SKIP, not pass — on an unparseable script or a nested/group subparser it cannot resolve.
Add its provenance row. *(Covers 135/G14.)*

⚠ **Registration hazard, resolved by observation rather than by judgement.** The rule sweeps every
bundle, so its first run will surface drift outside this plan's surface, and the drift instances that
motivated it are owned by a **sibling plan** (§ Out of scope). Do not fix that drift here and do not
weaken the rule to hide it. Instead: implement the analyzer with its tests, run the whole-tree gate,
and record the finding set in the report. Then read the runner to determine whether it supports a
registered-but-non-failing rule. If it does, register the rule that way and record a one-line proposal
to promote it to build-failing once the drift is triaged. If it does not, land the analyzer and its
tests **without** the gate registration, and record the same proposal with the measured finding set
attached. Either way the tree is never left red, and the decision is taken by reading the runner.

**(f) Two half-open dispositions, recorded where they survive.** An earlier run recorded two review
findings as *Fixed* when only their resolvable halves were: a **broken** reference written
parenthetically, and a **broken** reference carrying a `.py` suffix, both still escape the gate
silently — the exclusion predicates rescue the *valid* forms only, and tests codify that as intended.
The primary target is that run's report under `doc/plans/`, which **may already have been collected
and deleted**: if the file exists, restate both dispositions as *partly fixed* and distinguish the
valid and broken cases; if it does not, record that in the run report and stop there for that half.
Independently — and regardless of the report's existence — confirm by reading that the skill's
**shipped** disclosed-limitations paragraph names both escape shapes, and add the sentence if it does
not. That surface is durable, which the report is not. *(Covers 230/G11, 230/G12.)*

*Done when:* (1) `validate` output carries a per-row reason and the in-namespace subset can be
consumed without a client-side bundle check; (2) the nested-module rows carry a stated reason, and the
namespace-widening proposal is in the report and the PR body with **no** discovery change made; (3)
disabling each of the three unconditional skips changes no unresolved row, and the previously-hidden
resolvable notations appear as edges; (4) a synthetic unregistered verb on a skill with an entry
script stays unresolved while a registered one still resolves, and the live unregistered-verb instance
is reported again; (5) the new rule emits both finding classes against a **synthetic** fixture skill
carrying one drift of each kind, emits nothing against a synthetic clean skill, SKIPs (never passes)
on a fixture whose script cannot be parsed, and the report records what it reports for the live
tree — the synthetic fixtures are what make this *Done when* independent of whether the sibling plan
has landed; and (6) the shipped disclosed-limitations paragraph names both escape shapes.

### D6 — Two small validators stop failing silently

**(a) A missing bucket comment is reported, not only a wrong one.** The outline standard states that
the resolved bucket MUST be recorded as a comment on the profiles line and that *"a missing or wrong
bucket comment is a Q-Gate finding"*; `manage-solution-outline.py`'s `_check_declared_bucket`
implements only the *wrong* half — `if not declared or not write_set: return []` — and no other
consumer of the declared bucket exists, so the cheapest way to evade the new check is to delete the
comment. Emit a **warning** (not an error — an error would break existing outlines) when a deliverable
with a non-empty write-set carries no declared bucket, and a warning when the declared value is
outside the documented six-value vocabulary. Check the phase-3 gate's warning handling before landing.
*(Covers 280/G10.)*

**(b) The bucket check's fail-open becomes observable.** `_write_set_is_all_documentation` returns
`None` on `ImportError` and the caller writes `if not …(): return []`; `None` is falsy, so an
unavailable import makes the whole bucket check vanish with no signal at all — indistinguishable from
"checked and clean". Append a warning naming the unavailable predicate. The fail-open is currently
unreachable in practice (the executor puts every skill's `scripts/` on the path), which is why this is
low severity and not a live outage — but it is precisely the shape this plan exists to remove.
*(Covers 280/G11.)*

**(c) The operator-quotable scope statement is grammatical.** `self_review.py`'s
`_format_scope_statement` computes a noun once and reuses it for a plural demonstrative later in the
same sentence, so the one-file delta case — the commonest shape of a loop-back round — renders
*"covers only these file"*. The field exists to be quoted verbatim into findings and PR bodies, so
text a reader feels compelled to fix by hand defeats its purpose. ⛔ **Keep the sentence prefix
byte-identical** (three existing tests assert on prefixes of this string); change only the tail.
*(Covers 100/G5.)*

*Done when:* (1) validating a deliverable with a non-empty write-set and no bucket comment yields a
warning naming the missing audit trail, with a paired negative asserting a present bucket yields none,
and an out-of-vocabulary value yields a warning; (2) a test that patches the import to fail asserts a
warning is produced and no bucket error is raised; (3) `_format_scope_statement` returns a grammatical
sentence for a 1-file delta, with a test asserting the **complete** string for 0, 1 and 2 files; and
(4) the three existing prefix assertions still pass unchanged.

## Out of scope

Each exclusion states its reason, because there is no operator to ask mid-run.

- **Publishing `total_script_seconds` at the precision its shares are computed against.** Owned by the
  measurement-and-cost sibling plan in this epic, in the same `audit.py`. Excluded because two runs
  editing one file collide, and because D4(e) is authored to be correct whether or not that fix has
  landed — it reads the shipped rounding and branches on it.
- **The four `CHECK_ERA` stamp bumps in `audit.py`.** Same file, same sibling plan, and the underlying
  question (is the stamp roadmap-scoped or plan-scoped?) is a convention call this run cannot make.
- **Fixing the `manage-architecture` verb-drift instances that motivated D5(e).** Owned by the
  documentation-surface sibling plan. Excluded because D5(e)'s value is the *detector*, and because a
  *Done when* that depends on those instances still being open would make this plan's result a
  function of another plan's landing order — which is why D5(e) is verified against synthetic fixtures
  instead.
- **Adding the reverse `registry → table` aspect-table assertion.** Owned by the test-suite sibling
  plan, and it must land only **after** the two producerless registry rows are resolved: adding it now
  would require encoding those rows as exemptions, pinning in place the exact defect D2(b) proposes to
  remove.
- **Pre-fix pinning of the sparse-ratio confidence branch.** Owned by the test-suite sibling plan; that
  gap exists to pin the branch *before* D1(b) changes its behaviour. This plan does not duplicate it,
  but D1's *Done when* requires tests covering **all four** confidence grades after the change, so the
  branch is not left unguarded whichever order the two plans land in.
- **Putting a step id into the `[DISPATCH]` line.** That is the only way to pair
  `missing_dispatch_emission` exactly per step, and it is an emission-format change in another skill's
  lane with its own consumers. D1(h) ships the scoped `(role, workflow)` de-duplication instead, and
  the residual under-count stays documented in the floor note.
- **Widening component discovery into `scripts/{subdir}/`.** A namespace change that `deps`, `rdeps`,
  `tree` and the architecture projection all key on. D5(b) records it as a proposal; making the call
  headless would change a published contract on a guess.
- **Adding a producer for `_executive-summary`, or deleting the row.** Both are contract changes with
  defensible arguments on either side; D2(b) records the proposal. A run that picked one would be
  self-approving a change to a documented structure with no operator in the loop.
- **The report-defect gaps of other buckets, and any `doc/plans/` file outside this plan's own
  directory.** The lane contract forbids status or bookkeeping writes under `doc/plans/` outside the
  running plan's directory; the two report restatements this plan does carry (D5(f)) are authored to
  degrade to a recorded note if their target has been collected.

## Expected surface

Paths are as of authoring; locate by symbol name and re-derive.

- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-dispatch-audit.py` — D1,
  all nine items.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/standards/execution-context-dispatch-audit.md`
  — D1's schema, grades, scope statement and interpretation rules.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md` — D1's `ran_inline`
  re-documentation.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py` — D1(d)'s
  probe tightening and D2(a)'s partition predicate.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/retro_sections.py` — read by
  D1(d) and D2; **not modified** by D2(b), which only proposes.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/report-structure.md` — D2(a)'s
  divergence-paragraph deletion.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-manifest-consistency.py`,
  `…/check-routing-decisions.py`, `…/analyze-logs.py` — D3.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/routing-decision-verification.md`
  — D3(d).
- `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py`
  — D3(d)'s emitter only.
- `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` and its `checks/*.md` — D4.
- `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/{resolve-dependencies.py,_dep_detection.py,_dep_index.py}`
  and its `SKILL.md` — D5(a)–(d), (f).
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/` — D5(e): a new analyzer, its
  registration, and its provenance row.
- `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/self_review.py`
  — D6(c).
- `marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py`
  — D6(a), (b).
- `test/plan-marshall/plan-retrospective/`, `test/plan-marshall/audit-archived-plan-retrospectives/`,
  `test/pm-plugin-development/`, and the manage-solution-outline test module — new and changed tests
  for every item above.

## Claim labels

`OBSERVED` means the audit **and** its adversarial re-review both reproduced the defect by execution
or by reading the cited text verbatim. `HYPOTHESIS` means it rests on reading plus inference, or on a
single unreplicated measurement; each carries a named artifact reachable from a fresh clone that will
settle it. Every artifact below is a git-tracked file or a test the run writes — none is a `.plan/`
path, which a cloud clone cannot see.

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `ran_inline` absorbs an absent `total_tokens` column and a dispatched-but-unmeasured step | OBSERVED | `check-dispatch-audit.py::finalize_token_records` + `evaluate_dispatch_coverage`; two fixtures (column absent / `total_tokens: 0`) |
| `channel_completeness` is fed an all-caller line count while its other two figures are finalize-only | OBSERVED | `check-dispatch-audit.py::cmd_run` — the two call sites, one scoped and one not |
| A log-less plan directory grades `confidence: nominal` | OBSERVED | run the shipped script against a plan dir holding only an empty `logs/` |
| `counts.by_category.shape_violation` is a bare `0` in both the not-evaluated and clean cases | OBSERVED | same log-less run; the existing test asserting the bare `0` |
| The two list-returning checks publish no evaluated population | OBSERVED | `evaluate_envelope_violations`, `evaluate_generic_subagent`, and the `counts` block in `cmd_run` |
| `dispatch_coverage` emits all-zeros with no status when `status.json` is absent or corrupt | OBSERVED | `load_status_metadata`'s exception swallowing + the coverage block's return |
| A hand-written `[DISPATCH]` line cancels a genuine `shape_violation` shortfall | HYPOTHESIS | a fixture with one resolve record for a role, no seam line, one hand-written line — D1(g)'s test; the two live producers for that role are the corroboration |
| Re-fired dispatch lines inflate the numerator and mask a missing emission | HYPOTHESIS | a fixture with 2 dispatched steps, 3 same-role finalize lines, one step with no line — D1(h)'s test |
| The `shape_violation` interpretation rule does not point at the corroboration-limit blockquote | OBSERVED | the standard's two sections, read |
| The `N == 0` per-task ARTIFACT floor is provably dead | OBSERVED | re-derived against a pristine `analyze-logs.py`: 3 completed tasks, 0 per-task lines, 2 phase-1 lines → zero findings |
| A non-dict fragment with content on a conditional row is reported as *nothing lost* | OBSERVED | `parse_toon` on an aspect line carrying prose, then `build_document` |
| The real clean-run `script-failure-analysis` fragment is reported as a dropped section | OBSERVED | the producer's own clean-run output through `build_document` |
| Manifest-less `manifest-decisions` and `routing-decisions` skips are reported as dropped | OBSERVED | both producers' own skipped fragments through `build_document` |
| `_executive-summary` has no producer and its written branch is unreachable | OBSERVED | tree-wide grep for the key; `collect-fragments.py`'s `_`-prefix refusal; `sections_omitted` on every bundle |
| `dispatch_boundaries` is registerable but written only nested inside another fragment | OBSERVED | `SECTION_SPEC` keys minus aspect-table keys; the single writer in `analyze-logs.py` |
| The remaining conditional rows behave the same way | HYPOTHESIS | D2(a)'s differential over every conditional row × producer status |
| M4 skips with "no diff data available" while publishing `diff_available: True` | OBSERVED | run with an existing empty `--diff-file`; reproduced twice, independently |
| The routing summary reports zero over two emitted `inconclusive` checks | OBSERVED | run `cmd_run` on a plan with a manifest, a footprint and no decision log |
| `filter_bookkeeping` seeds `diff_available: True` and relies on one caller to correct it | OBSERVED | the seed literal and its single caller assignment |
| The `frozen_manifest_stale` line is unreadable to `resolve_removal_causes` | HYPOTHESIS | D3(d)'s test staging that exact line and asserting the cause resolves |
| `_examined_population` returns whichever population key appears first in the block | OBSERVED | demonstrated first-party against the shipped module in both key orders |
| `check_input_integrity`'s docstring contradicts its predicate | OBSERVED | the docstring and the predicate, read |
| `_resolve_repo_root` resolves a main-anchored path by a cwd walk-up | OBSERVED | the resolver and its five consuming sites |
| `references.modified_files` has no writer; three consumers substitute the declared footprint | OBSERVED | the references data model, the shim declaration, and the four call sites re-read per site |
| The global-log check doc claims a reconciliation that does not hold below ~1 s | OBSERVED | the two doc lines and the two comment blocks against the two rounding sites |
| A `WARNING` that fires at every boundary regardless of condition exists | HYPOTHESIS | D4(f)'s bounded sweep — refutation is an expected outcome; two prior searches failed |
| A large share of unresolved `validate` rows name a non-indexed bundle | OBSERVED | the row partition, re-derived row-by-row on adversarial review |
| The nested module cannot resolve under a non-recursive component glob | OBSERVED | the module's on-disk path against `scripts/*.py` |
| The three unconditional drops hide resolvable edges | OBSERVED | neutralise the comment-line skip and diff the edge count; two of the newly-surfaced rows are non-references |
| A retargeted verb is not checked against the entry script's registered verbs | OBSERVED | a live notation naming a verb the entry script does not register |
| **No quality-gate rule compares an argparse subcommand set against documented verbs** (asserted absence) | HYPOTHESIS | re-run the whole-tree gate, enumerate the registered rules, and confirm — **D5(e) must not build until this is re-verified** |
| Two review dispositions were recorded as fixed when only their resolvable halves were | OBSERVED | probes for a broken parenthesised reference and a broken `.py`-suffixed reference; the tests that codify the behaviour |
| A missing bucket comment is unimplemented, though the standard calls it a Q-Gate finding | OBSERVED | the standard's clause; the check's early return; the declared-bucket consumer sweep |
| The bucket check's `ImportError` arm resolves to silence | OBSERVED | the tri-state return against the falsy-check call site |
| `_format_scope_statement` renders "these file" for a 1-file delta | OBSERVED | call it with `('delta', 1, ref)` |

## Verification

**This plan's subject is detectors that cannot fire. Its own guards are therefore mutation-proven, and
that is a requirement, not an aspiration.** A deliverable whose guard survives mutation is **not
done**.

1. **Red-first, per behavioural change.** Every test this plan adds for a defect must be **confirmed
   to fail against the pre-fix code** before the fix lands, and the failure output recorded in the run
   report. A test written after the fix and never seen red is evidence of nothing.
2. **Mutation-proof, per guard.** For every branch, predicate, default and status this plan adds or
   changes, apply a mutation that removes its effect (a condition forced to `False`, a default
   restored to the old value, a threshold changed, a status literal replaced) and record which tests
   go red. The report carries a table: `guard | file+symbol | mutation applied | tests killed`. **A
   mutation that kills nothing is a finding against this run** — add the test that kills it, then
   re-run the mutation, before calling the item done.
3. **Mutation method.** Snapshot the file **outside the repository** (the system temp dir) before each
   mutation, restore by copying the snapshot back, and confirm the restore by checksum and by
   `git status --porcelain` being clean for that file. **Never** use `git checkout`, `git restore` or
   `git stash` to undo a mutation — a concurrent edit elsewhere in the tree makes those destructive.
   Mutate the **file on disk**, not a patched in-memory module: an in-process patch can miss a shape
   only the file exercises.
4. **Cold reads, for the text whose value is what a later reader does with it.** Dispatch the pre-PR
   verification sub-agent to read these **cold** — without this plan — and to report *which reading it
   took*, verbatim, in the report:
   - the `check-dispatch-audit` output on a log-less plan: *"for each zero in this output, did the
     check evaluate anything, or could it not tell?"* If it cannot tell, D1 is not met — this is the
     acceptance test the original deliverable set for itself and failed.
   - the revised `ran_inline` documentation: *"does a `ran_inline` classification prove the step ran
     inline?"* The correct reading is **no — it is an upper bound.**
   - the revised `shape_violation` interpretation rule: *"does a clean `shape_violation` over a
     populated population show that dispatch discipline was verified?"* The correct reading is
     **no — it shows only that the emitter's two writes agree.**
   - the D2(b) and D5(b) proposals: *"does this text decide anything, or does it put a choice to a
     reader?"* The correct reading is **it puts a choice to a reader.** A proposal that reads as a
     decision has failed its purpose, however complete it looks.
5. **Differential over the partition (D2).** Record the before/after `sections_written` /
   `sections_omitted` / `sections_dropped` / `status` for every conditional row × every deterministic
   producer's real output. This closes the open question the source audit's own review left: the four
   partition defects were each reproduced against one fragment shape apiece.
6. **Suites.** Run the affected test trees individually (`test/plan-marshall/plan-retrospective/`,
   `test/plan-marshall/audit-archived-plan-retrospectives/`, `test/pm-plugin-development/`, the
   manage-solution-outline module) and then the full build gate the lane contract requires. Record
   collected/passed counts **re-derived at the moment of the claim** — not carried from an earlier
   round, which is a defect this epic keeps finding.
7. **No proposal is implemented.** Confirm by reading the diff that `SECTION_SPEC` gained and lost no
   row, that `report-structure.md`'s `_executive-summary` content requirement is unchanged, and that
   component discovery still globs one level. Each proposal appears in the report **and** in the PR
   body.
8. **Re-derive every count** this plan states before repeating it anywhere.

## Notes

**Where the evidence lives.** Every defect above was filed against a landed plan in this epic, with
its evidence in that plan's `gaps.md` and its supporting analysis in the `verification.md` beside it —
for example `doc/plans/code-intelligence-substrate/170-finalize-dispatch-evidence-is-missing/gaps.md#G13`.
Those files are git-tracked and corroborate this plan, **but do not depend on them**: a landed cloud
plan's directory is deleted when the orchestrator collects it, so a run may find them gone. Everything
needed to execute is restated here. If a gap file *is* present, read it — it carries the per-entry
risk notes; if it is absent, that is expected and not a blocker.

**The adversarial review wins where it disagrees with a gap entry.** Each gap was re-reviewed by an
independent pass that re-ran the measurements, and several entries were corrected by it. This plan
carries the corrected readings, and says so where the correction changes what a run should do:
the compiler is **not** at fault for the missing Executive Summary (the producer side is);
`_examined_population`'s precedence is **inoperative today**, not merely at latent risk; the retired
footprint key causes **substitution of the declared set for the realized one** at three sites rather
than uniform blindness; and the shipped standard **does** already disclose the corroboration limit, so
that gap is a navigation defect rather than a missing warning.

**Timing figures are not evidence.** No deliverable here rests on a duration or throughput number.
Any such figure encountered in a gap file was measured in a shared audit tree with sibling agents
running full suites and must be re-measured before being relied on.

**Sequencing.** This plan is in the same epic as several sibling plans that touch the same files.

- ⛔ **`.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`** is edited by D4 **and**
  by the measurement-and-cost sibling (precision fix, four era stamps) and the test-suite sibling (a
  census guard test). **Do not run this plan concurrently with either against the same branch.** If
  one has already landed, rebase and re-derive before D4 — in particular D4(e), which reads the
  shipped rounding and branches on it.
- **`check-dispatch-audit.py`**: the test-suite sibling adds a pre-fix pin for the sparse-ratio
  confidence branch that D1(b) changes. This plan is correct in either order, because D1's *Done when*
  requires all four confidence grades to be covered after the change; if that sibling has landed,
  **extend** its tests rather than duplicating them.
- **`retro_sections.py` / the aspect table**: the test-suite sibling's reverse correspondence
  assertion must land **after** the two producerless rows are resolved. This plan only *proposes* that
  resolution, so it neither unblocks nor blocks that sibling — record that plainly in the report so the
  ordering is not misread as discharged.
- **`manage-architecture`'s documented verb set** is corrected by the documentation-surface sibling.
  D5(e) is deliberately verified against synthetic fixtures so it does not care which order the two
  land in; its live-tree finding set is *recorded*, never asserted.

**Two proposals, no decisions.** D2(b) and D5(b) exist because a headless run must not self-approve a
contract change. Each is authored to produce a written proposal with re-derived evidence, two options,
their measured consequences and a recommendation — and to change nothing. A run that implements either
has exceeded this plan.

## Gap coverage

Every gap in this plan's scope, and the deliverable that discharges it. Citations are
`{source-plan}/gaps.md#{id}` under `doc/plans/code-intelligence-substrate/` — corroboration, not
required reading (§ Notes).

| Deliverable | Gaps discharged |
|---|---|
| D0 (gating) | none — it derives the state D1–D6 act on |
| D1 | `170-finalize-dispatch-evidence-is-missing/gaps.md#G13` (high), `#G1` (high), `#G2` (high), `#G3` (high), `#G4` (medium), `#G15` (medium), `#G8` (medium), `#G5` (low), `#G10` (low) |
| D2 | `330-retrospective-report-sections-structurally-dead/gaps.md#G1` (high), `#G2` (high), `#G3` (medium), `#G4` (medium); proposal-only: `#G6` (high), `#G5` (medium) |
| D3 | `320-manifest-cross-check-discards-production-tree/gaps.md#G2` (high), `#G3` (high), `#G9` (low); `170-finalize-dispatch-evidence-is-missing/gaps.md#G7` (high); `290-auditor-detector-integrity/gaps.md#G5` (medium) |
| D4 | `290-auditor-detector-integrity/gaps.md#G1` (high), `#G2` (medium), `#G6` (medium); `310-main-sha-records-the-pinned-cwd/gaps.md#G3` (medium); `050-post-run-band-contract-and-ordering-residue/gaps.md#G4` (medium); `270-aggregate-cost-invisible-to-per-call-ceiling/gaps.md#G2` (medium) |
| D5 | `230-validate-precision/gaps.md#G15` (medium), `#G16` (medium), `#G19` (medium), `#G20` (medium), `#G11` (low), `#G12` (low); `135-remove-lsp-query-facade/gaps.md#G14` (medium) |
| D6 | `280-outline-plan-scope-derivation-integrity/gaps.md#G10` (medium), `#G11` (low); `100-self-review-surfacing-integrity/gaps.md#G5` (low) |

**36 gaps: 11 high, 18 medium, 7 low.** All eleven high-severity gaps are carried by a deliverable;
one of them — the producerless `_executive-summary` row — is discharged as a **recorded proposal**
rather than a code change, for the reason stated in D2(b) and § Out of scope. None is dropped.
