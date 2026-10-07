# PLAN-TRUTH-127: The archived record says a phase is still running, and the closer can only close one

epic: truthful-signals
workstream: WS-01
priority: HIGH — operator-designated 2026-09-03; it corrupts the PERMANENT record, and 4 of 30 archived plans already carry it

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-TRUTH-127-the-archived-record-says-a-phase-is-still-running-and-the-closer-can-only-close-one.md`
> and is queued in the epic `status.json` `plans[]` field. The orchestrator EMITS the command below;
> it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief, so
> every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Reported from a foreign machine as a data-point (a run whose `status.json` recorded `5-execute` as
`in_progress` on a merged plan while its metrics ledger recorded the phase correctly). ⭐⭐ **The
orchestrator then derived the mechanism AND the population first-party in this checkout at HEAD
`30cd8aaf8` — so this plan does NOT rest on the foreign report.** The report supplied the question; the
evidence below is local.

## Objective

**A plan that looped back can archive with a phase still marked `in_progress`, and the record is
permanent.** ⛔ It is not a display glitch: `status.json` is documented as the machine authority for the
plan lifecycle, so the archived corpus contains plans whose authoritative record asserts a phase is
running on work that merged weeks ago.

### The measured population — derived, not asserted

Over **all 30 archived plans** in this checkout (every one carries a `status.json` with a `phases`
block; 180 phase rows total, values `done` 176 / `in_progress` 4):

| Cohort | Plans | Carrying an `in_progress` phase |
|---|:-:|:-:|
| **`loop_back_reentry` present** | 5 | **4 (80%)** |
| **`loop_back_reentry` absent** | 25 | **0 (0%)** |

⇒ **The correlation is near-total and the mechanism below explains it exactly.** All four carry
`current_phase: 6-finalize` rather than `complete`, and in all four the OPEN phase is `6-finalize` while
`5-execute` reads `done`.

⭐⭐ **The fifth loop-back plan is the matched negative control and it must be preserved as such**:
`2026-08-09-hook-timeout-unit-confusion` looped back and closed cleanly (all six phases `done`). ⇒ The
defect is **not** "a loop-back always breaks it" — it is conditional, and D0 must state the condition
rather than the correlation.

### The mechanism — two defects that COMPOSE

**(1) `set-phase` opens a phase and never closes one.** `_status_query.py:77` `cmd_set_phase` sets
`current_phase`, stamps the target `PHASE_STATUS_IN_PROGRESS`, and records `loop_back_reentry`. Marking
a phase `done` is exclusively `cmd_transition --completed`'s job (`_cmd_lifecycle.py:441`). ⇒ A loop-back
re-opens `5-execute`; if the resumed dispatch yields `blocked` rather than completing, **nothing ever
closes it** and the plan carries TWO open phases into finalize.

**(2) ⛔⛔ `cmd_archive` closes exactly ONE phase — the FIRST non-done one.** `_cmd_lifecycle.py:534-540`:

```python
active_idx = next((i for i, p in enumerate(phases) if p.get('status') != PHASE_STATUS_DONE), None)
if active_idx is not None:
    phases[active_idx]['status'] = PHASE_STATUS_DONE
if all(p.get('status') == PHASE_STATUS_DONE for p in phases):
    status['current_phase'] = 'complete'
```

With one open phase (the normal path) this is correct. **With two, `next()` picks the EARLIER one —
`5-execute` — closes it, and leaves `6-finalize` open.** The `all(done)` guard then fails, so
`current_phase` never becomes `complete`.

⭐⭐⭐ **That is exactly the observed shape: `5-execute` reads `done` and `6-finalize` reads
`in_progress`.** The single closure was spent on the re-opened phase, and the record ends up asserting
that the phase which actually finished is still running — **the archiver marked the wrong phase done and
reported success.**

⚠ **Note the shape difference from the foreign report, and do not smooth it over.** The report described
`5-execute` left open; the local population has `6-finalize` left open with `5-execute` closed. **Same
mechanism family, different terminal phase** — consistent with (2) having run in the local cases and not
in the reported one. D0 states which, rather than assuming they are one shape.

### ⭐⭐⭐ FOLDED 2026-09-03 — the same `branch-cleanup` cause has a SECOND consequence

PLAN-TRUTH-102's landing (#1384) surfaced it: **`build_time` reports all-zero over 77 executed builds**,
because `branch-cleanup` destroys the worktree-resident ledger oracle *before* the reporting steps read
it — and **a destroyed-oracle zero is byte-identical to a build-free run.**

⇒ **One step removes a resource two later steps depend on.** Arm (3) below is the repair path closing;
this is a measurement being destroyed. Each was noticed by a different consumer, which is why they were
filed separately.

⛔ **This widens D0 and D1's framing, and the plan must not fix only its own half.** A change that
teaches `build_time` to report "oracle destroyed" leaves the transition unreachable; a change that only
re-orders for the transition leaves `build_time` lying. **The shared question is the ordering contract:
what may run after `branch-cleanup`, and what must read its inputs before it.** ⚠ D0 states whether this
plan fixes both, fixes the contract, or fixes one and NAMES the other as deferred — ⛔ never silently
fixes one.

### (3) The repair path is structurally closed, and the refusal names the wrong cause

`_cmd_lifecycle.py:55` `_clean_tree_refusal` shells `git -C {worktree_path} status --porcelain` and
**fails closed when the command itself fails** — *"an unreadable tree cannot be proven clean"*, which is
correct reasoning. But after `branch-cleanup` removes the worktree the command can never succeed, so
`transition --completed` is unreachable for any worktree plan once finalize has run.

⛔ **And a REMOVED worktree and a DIRTY worktree both surface as `error: worktree_dirty_at_boundary`.**
A tree that is *gone* is reported as one that is *dirty* — a confident code naming a cause it did not
establish, this epic's archetype. ⭐ The operator on the reporting machine hit exactly this and
**correctly declined to clear the metadata to bypass the guard.** The guard is not the defect; its
diagnosis is.

## Deliverables

Six deliverables. D0 is a gate.

---

**D0 — GATE: state the CONDITION, not the correlation, and settle the repair question.**

- *(a) Why did the control close?* `2026-08-09-hook-timeout-unit-confusion` looped back and closed all
  six phases. Establish what differed — most likely its resumed `5-execute` completed normally, so
  `cmd_archive`'s single closure landed on `6-finalize`. ⛔ **Publish the condition as a predicate, not
  as "4 of 5 loop-backs failed."** A correlation over n=5 is not a mechanism, and this plan already has
  the mechanism from source.
- *(b) Widen the population beyond archived plans.* The 30 archived are one cohort; live and dormated
  plan directories are others. Publish each cohort's count separately — ⛔ **a single blended figure
  would hide which lifecycle stage produces the defect.**
- *(c) Repairing the four existing records — ⛔ **SETTLED BY THE OPERATOR, 2026-09-03: NO.** Do not
  re-open it.* They are historical artifacts of a since-fixed defect, and rewriting an archived
  `status.json` to say something the run did not record is the falsification this epic exists to
  prevent. **Fix forward; leave the record honest.** ⇒ D0(c) is not a question this plan answers, it is
  a constraint it inherits, and D5 test 4 carries its only consequence.

---

**D1 — `cmd_archive` must close EVERY open phase, or refuse and name them.** The single-closure loop is
the proximate cause of the wrong-phase-done record. Two admissible fixes, D0 picks one:

1. Close every non-`done` phase, not just the first; or
2. Refuse to archive with more than one open phase, naming them.

⛔ **What is NOT admissible is the current behaviour: close one, leave the rest, report success.** ⭐ Fix
(2) is the more truthful shape if a second open phase means an obligation was genuinely skipped — but it
turns a silent record defect into a blocking archive failure, so D0 states which it wants and why.

⚠ **Whichever: `current_phase` must reach `complete` on the success path.** Today the `all(done)` guard
silently leaves it at `6-finalize`, which is a second observable of the same bug and must not survive.

---

**D2 — a re-opened phase that ends without completing must not stay open silently.** When a resumed
dispatch yields `blocked` (or any terminal-without-completion outcome), the re-opened phase's state must
become legible — closed if the work is done, or explicitly recorded as abandoned. ⛔ **`in_progress`
forever is not a state any run intended**; it is the absence of a transition, and the absence is what
must be caught.

⭐ `set-phase` already writes `loop_back_reentry`, so **the ledger knows a loop-back happened** — the
signal exists and nothing consumes it for this. ⚠ Prefer consuming that existing marker over adding a
second one.

---

**D3 — a missing worktree is not a dirty one.** Split `worktree_dirty_at_boundary` so a removed or
unreadable worktree returns a distinct code naming that cause. ⛔ **Do NOT weaken the fail-closed
posture** — an unreadable tree still cannot be proven clean and still refuses; the change is to the
DIAGNOSIS, not the verdict. ⭐ This is the smallest deliverable here and is self-contained; if the plan
is split it can ride alone.

⚠ Then settle whether a post-finalize `transition --completed` should be reachable at all. It may be
correct that it is not — the worktree is gone because the work is done — in which case the answer is
that **D1/D2 must make the repair unnecessary**, and D3 exists so the refusal explains itself rather
than misdirecting the next operator.

---

**D4 — reconcile the two ledgers, because today nothing does.** The metrics ledger recorded the phase
correctly (`close_count: 2`, `end_time` present, no missing boundaries) while `status.json` did not.
⇒ **Two ledgers disagree about whether a phase completed and no reader compares them.** Add the
cross-check, and report a disagreement as a finding rather than letting the more authoritative-looking
file win by default.

⭐⭐ **Seam, not a transfer:** `PLAN-TRUTH-124` D6's `statistics` is the natural place for a cross-ledger
read to live, and `-124` D1 owns the verdict vocabulary a disagreement is reported in. **D4 must not coin
a second vocabulary.** If `-124` has landed, emit into it; if not, record the requirement and defer the
naming.

---

**D5 — the tests, and the control is what makes them real.** ⛔ Population-derived per this epic's
standing rule; publish the population size.

1. **Two open phases archive correctly** — a fixture with `5-execute` and `6-finalize` both open asserts
   D1's chosen behaviour (all closed, or a refusal naming both). ⛔ **The matched negative control is a
   single-open-phase fixture that still archives normally** — without it the test passes on an archiver
   that refuses everything.
2. **`current_phase` reaches `complete`** on the success path, asserted over the two-open fixture.
3. **A removed worktree yields the D3 code, a dirty one yields `worktree_dirty_at_boundary`** — two
   fixtures, two distinct codes. ⛔ One fixture cannot show a distinction.
4. **No archived plan carries an open phase** — derive the corpus from the tree and assert it, publishing
   the count. ⛔⛔ **The four historical records ARE left unrepaired (operator decision, D0c), so this
   assertion MUST exclude them by an EXPLICIT, ENUMERATED allow-list — never by weakening the
   predicate.** A known-bad record excluded by name is a recorded exception; one excluded by a loosened
   rule is an invisible one, and the loosened rule would also stop catching the NEXT occurrence. ⚠ The
   allow-list is therefore itself a finding surface: a fifth entry appearing in it after this plan lands
   means the fix did not hold.

## Claim Labels

Derived first-party at HEAD `30cd8aaf8` on 2026-09-03 unless marked otherwise; re-ground at the plan's
own HEAD before relying on any one of them.

- **OBSERVED** — 30 archived plans, all carrying a `phases` block; 180 phase rows with values `done` 176
  / `in_progress` 4. Four plans carry an open phase, all `6-finalize`, all with
  `current_phase: 6-finalize` (not `complete`), all with `5-execute` reading `done`.
  - verdict: contradicted | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: yes | evidence: Population stale: 39 archived plans / 234 phase rows / 228 done / 6 in_progress at HEAD, not 30/180/176/4. Re-scoped: the spec now states the derivation instead of the frozen count.
- **OBSERVED** — `loop_back_reentry` present in 5 plans, 4 of which carry an open phase; absent in 25, 0
  of which do. ⚠ **This is a CORRELATION over n=5**, published as such. The mechanism below is what makes
  it a finding; the correlation alone would not.
  - verdict: contradicted | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: yes | evidence: REFUTED: no_lb=33 now carries one open-phase case (2026-09-05-apply-the-cloud-plan-lane-contract-amendments, no loop_back_reentry), so the 0 pct correlation no longer holds. Re-scoped: D0 must derive the open-phase population independently of loop_back_reentry.
- **OBSERVED** — `_status_query.py:77` `cmd_set_phase` stamps only `PHASE_STATUS_IN_PROGRESS` and writes
  `loop_back_reentry`; it never marks a phase `done`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _status_query.py cmd_set_phase L77-138 sets PHASE_STATUS_IN_PROGRESS and writes loop_back_reentry on backward moves; never sets done
- **OBSERVED** — `_cmd_lifecycle.py:534-540` `cmd_archive` closes the FIRST non-`done` phase via `next()`
  and gates `current_phase = 'complete'` on `all(done)`. ⇒ with two open phases it closes the earlier and
  leaves the later, which is exactly the observed shape.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _cmd_lifecycle.py L534-540: active_idx=next() picks first non-done phase; current_phase=complete gated on all(done)
- **OBSERVED** — `_cmd_lifecycle.py:441` `cmd_transition` is the only site setting `PHASE_STATUS_DONE`
  besides the archive closer.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Only two PHASE_STATUS_DONE assignment sites in _cmd_lifecycle.py: L441 cmd_transition and L539 cmd_archive
- **OBSERVED** — `_cmd_lifecycle.py:55` `_clean_tree_refusal` fails closed when `git status` fails and
  returns `worktree_dirty_at_boundary` for both a dirty tree and an unreadable/absent one.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _cmd_lifecycle.py:55-115 _clean_tree_refusal returns worktree_dirty_at_boundary both when git status fails and when stdout is non-empty
- **OBSERVED** — the phase-status vocabulary is exactly `done` / `in_progress`
  (`tools-file-ops/constants.py:81-82`).
  - verdict: contradicted | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: yes | evidence: constants.py:80-84 VALID_PHASE_STATUSES is (pending, in_progress, done) -- three values; the spec read lines 81-82 and missed PENDING at line 80. Re-scoped in place.
- **OBSERVED (control)** — `2026-08-09-hook-timeout-unit-confusion` carries `loop_back_reentry` and all
  six phases `done`. ⇒ closing after a loop-back is achievable; the defect is conditional.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: 2026-08-09-hook-timeout-unit-confusion status.json still carries loop_back_reentry plus all six phases done and current_phase complete
- **REPORTED, NOT CORROBORATED** — the foreign run's specifics: `5-execute` left open, the metrics ledger
  reading `close_count: 2` with `end_time` present, and the post-merge repair refusal. ⛔ Foreign machine,
  not read here. ⚠ **Its terminal phase differs from every local case**, which D0(a) must explain rather
  than average away.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Self-labelled REPORTED NOT CORROBORATED by the spec; foreign-machine specifics unreachable from this checkout
- **HYPOTHESIS** — that the four local cases all arose from a resumed `5-execute` that never completed,
  leaving two open phases at archive time. Confirm/refute against each plan's `execution.toon` and
  metrics (verify-at-outline) — the artifacts are on disk for all four.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: One loop-back case checked (2026-08-08-provider-logging-path-containment matches the shape) but not exhaustively swept
- **Verify-first clause** — before D1 changes the archiver, confirm no consumer depends on
  `cmd_archive` closing exactly one phase (e.g. a caller that archives mid-lifecycle deliberately). A
  dependent consumer turns D1 from a fix into a contract change and is a re-scope.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Verify-first clause naming no consumer check; a full caller-graph sweep of cmd_archive callers was not run this pass

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` — the
  archive closer (D1), the transition site (D2), and `_clean_tree_refusal` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_status_query.py` —
  `cmd_set_phase` and the `loop_back_reentry` marker (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/standards/status-lifecycle.md` — the
  phase-lifecycle contract these changes alter (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md` — the canonical invocations
  for the changed verbs and any new refusal code (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — the loop-back caller
  that invokes `set-phase` (D2)
- OBSERVED: `test/plan-marshall/manage-status/` — the D5 archiver, transition and refusal-code tests
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-metrics/` — touched only if D4's
  cross-check reads the metrics ledger from that side rather than from `statistics`
  (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-metrics/` — same condition (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- ⚠ **D4 is seamed to `PLAN-TRUTH-124`** — its D1 owns the verdict vocabulary and its D6 `statistics` is
  the natural host for a cross-ledger read. ⛔ **Do not coin a second vocabulary here.** If `-124` has not
  landed, D4 records the requirement and defers.
- ⚠ **`PLAN-TRUTH-123` is a downstream consumer**: a plan record that misstates its own phase completion
  is an input its scorer would read. Seam note only; no ownership moves.
- ⛔ **Surface overlap with the `manage-status` cluster is likely** — several staged specs touch
  `manage-status` (`-099`, `-100`, `-115` among them) and `-089` is LIVE on `manage-status/SKILL.md`.
  **Re-derive from `corpus cross-check` at emit time; do not trust this note.**
- Adjacent to: `PLAN-TRUTH-121` (*producers report success over a write nothing can read*) is a
  neighbouring class but NOT this one — there the write reported false success; here every individual
  write succeeded and a second call never happened. ⛔ Do not merge the two.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-127-the-archived-record-says-a-phase-is-still-running-and-the-closer-can-only-close-one.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO
file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⭐ FOLDED 2026-09-03 — inbox drain (1 message(s))

- **`dual-homed-hook-install-renders-identically-010.md`** — *only 8 of 31 metrics ledger rows pair across the two stores, and the `6-finalize` phase row understates its own dispatch spend.* (Supersedes `-004.md`, retired by this drain.)

  First-party `manage-metrics reconcile-ledgers` over PLAN-TRUTH-102: `findings_count: 23`, `union_rows: 31`, `execution_log_rows: 25`, `boundary_rows: 14`. Per-phase pairing — `4-plan` 0/1/**0** (structurally excluded); `5-execute` 5/3/**1** over 7; `6-finalize` 20/10/**7** over 23. ⇒ **74% of rows exist in exactly one store.**

  **Two distinct defect shapes ride that gap, and the reconciler already names them apart:**
  - `row_absent_from_execution_log` — *“a dispatch terminated and recorded its usage, but no `record-step` row names it in the window — this spend is invisible to any `execution_log` sum”*. Four rows: `6-finalize` carries 221,480 + 187,333 + 82,919 = **491,732 tokens**, `5-execute` a further **310,257**. ⇒ **802K tokens of measured, attributed spend that no phase total includes.**
  - `boundary_never_closed` — `6-finalize`: *“10 dispatch-boundary rows recorded but the phase row carries no `end_time`”*, carrying **1,579,116 tokens**. ⭐⭐ **The rows are present; nothing closed the phase, so its own summary of them was never computed.** This is the limb that meets this spec’s subject directly — a closer that does not close.

  ⛔ **Both failures move the number in the SAME direction — down.** A phase whose boundary was never closed and whose dispatch rows never paired reports *a confident, well-formed, small figure*, and nothing in `metrics.md` marks the row as partial. **You have to run a separate reconciliation verb to discover the headline was assembled from a quarter of the rows.** Every token-roadmap figure derived from per-phase rows inherits it.

  **Three asks, kept separate:** (1) `metrics.md` publishes its own pairing state — `6-finalize: X tokens (7 of 23 rows paired)` rather than a bare `X`; ⭐ *“a total whose denominator is unstated is not publishable — the project already enforces this for `corpus` counts and `inbox list` zeros”*. (2) **Fix `boundary_never_closed` at the WRITER, not the reader** — establish whether the close is missing, racing, or skipped on a particular termination path. (3) Decide whether `row_absent_from_boundary_ledger` is a defect at all: the reconciler’s own text says it may be *“a declared exclusion class”* **but does not say WHICH**, so all 17 such rows read as ambiguous and **swamp the 4 unambiguous ones**. Publish the exclusion classes as data.

  ⚠ **The sender’s own staleness warning, honoured here:** *“do not treat the figures above as stable — they were re-derived during finalize and moved between the retrospective’s read (30-row union) and this one (31-row union) as later steps recorded. Re-derive before acting.”* The superseded `-004.md` carries the 30-row reading; the divergence between the two is itself evidence for ask (2).

  ⚠ **Root cause named by the sender:** `record-step` and `record-dispatch-boundary` are written by **independent call sites with no shared transaction and no shared key** — a boundary row carries no `step_id`, so the two can only be joined on phase plus a **300-second time window**. Nothing enforces that a dispatch which recorded one recorded the other. **The single largest dispatch of the run** (`pre-submission-self-review`’s 5th firing, 953,588 tokens, 1,773,582 ms) **has a `record-step` row and no boundary row.**

## ⭐ FOLDED 2026-09-04 — inbox drain (2 message(s))

- **`documented-invocations-...-003`** — *a finalize loop-back into phase-5 leaves no re-entry record on the phase row.* The plan demonstrably looped back (`automatic-review` filed 7 pr-comment findings, triage opened fix tasks, phase-5 produced commits `a4cdb8784` and `49769bd2f`, `loop_back_iteration: 1`) — and **every re-entry signal reports a plan that never looped back**: `re_entered_phases: []`; the `5-execute` row’s `close_count` is `1` **while `close_count > 1` is the documented AUTHORITATIVE re-entry marker**; the row’s `end_time` is `2026-09-02T19:03:55Z` while two of its own dispatch-boundary rows are stamped **`2026-09-03T10:54:29Z` and `11:10:21Z`**; `returned_with_findings` is 0 across all 21 rows; and **no step’s `prior_firings` carries a `loop_back` outcome.**

  ⛔ **Root cause: the loop-back re-enters phase-5 without calling `end-phase` / `phase-boundary` on the way back out**, so the row is never re-closed and `close_count` never increments. ⭐⭐ **The accounting consequence is real and was caught only by a DIFFERENT mechanism**: the row’s own `total_tokens` (1,038,561) is short of its dispatch-boundary total (1,323,927), and **the reconciliation preferred the larger measure, silently repairing a 285,366-token gap the re-entry signal denied existed.**

  **Two independent repairs, both cheap:** stamp the phase boundary on loop-back re-entry; and add a `phase_reentry_undeclared` finding to `reconcile-ledgers` — **any dispatch-boundary row timestamped later than its phase row’s `end_time` while `close_count == 1`.** ⭐ *“It already reads both ledgers and already emits `boundary_never_closed`; this is one comparison more.”*

- **`documented-invocations-...-005`** — *phase-5 dispatches record usage at termination but no `record-step` row names them.* `reconcile-ledgers` for `5-execute`: `execution_log_rows: 0`, `boundary_rows: 6`, **all six classified `row_absent_from_execution_log`**, carrying **1,323,927 tokens**.

  ⭐⭐ **This is NOT the benign structural case, and the same call proves it**: `4-plan` is correctly reported `structurally_excluded` because the execution log’s writer does not accept that phase — **which shows the discriminator working, and shows that `5-execute`, which the writer DOES accept, is a genuine gap.**

  ⛔ **The consequence is a LIVE wrong number**: `check-routing-decisions` reports `cost_preview.execution_log_tokens: 2710183` under `execution_log_population: "5-execute,6-finalize"`. **The population string claims both phases; the figure covers `6-finalize` alone and understates the plan by 1,323,927 tokens — about 23% of its total spend.** ⭐ **The ask offers an honest either/or:** emit `record-step` rows for phase-5, **or** — if phase-5 is deliberately outside the population — **declare it in the writer’s accepted set the way `4-plan` is declared**, so no consumer builds a population string promising coverage the ledger does not have.

  ⚠ **SURFACE DELIBERATELY NOT ADDED.** Both folds point at `phase-5-execute/**`, which is claimed by the **LAUNCHED `PLAN-TRUTH-089`**. Adding it here would manufacture a collision against a live plan. **Re-scope after `-089` lands.**

## ⛔ RE-SCOPED 2026-09-05 — cleanup re-grounding at `66320e70d` (3 claims contradicted)

⛔ **The claim bullets above are LEFT VERBATIM on purpose.** Their ordinals are the address the
persisted verdicts key on, and rewriting them would silently re-point every stamp. This section is the
re-scope; read it as superseding the bullets it names.

| Claim | Was | Is at HEAD |
|:-:|---|---|
| 0 | 30 archived plans / 180 phase rows / 176 done / 4 in_progress | **39 / 234 / 228 / 6** |
| 1 | the open-phase defect correlates 100% with `loop_back_reentry` (0% without) | **REFUTED** — `has_lb`=6 (5 open) but `no_lb`=33 now carries **one** open-phase case (`2026-09-05-apply-the-cloud-plan-lane-contract-amendments`, no `loop_back_reentry`) |
| 6 | `VALID_PHASE_STATUSES` holds two values | **three** — `constants.py:80-84` is `(pending, in_progress, done)`; the spec read lines 81-82 and missed `PENDING` at line 80 |

⭐⭐ **Claim 1's refutation STRENGTHENS the plan rather than weakening it.** The spec's mechanism was
that a loop-back leaves a phase open; a case with **no** loop-back marker and an open phase means the
mechanism has a **second entry path the spec does not model**. ⇒ **D0 must derive the open-phase
population independently of `loop_back_reentry`, not partition by it.**

⛔⛔ **Claims 0 and 1 are the SAME authoring defect this epic just promoted a rule against: a frozen
count restated where a derivation belonged.** ⇒ **Re-scope rule for this spec: state the derivation, not
the number.** Claim 0's premise becomes *"derive the archived-plan and phase-row populations at outline
via a walk of `.plan/local/archived-plans/*/status.json`"* — a count that was correct when written and
drifts by construction is a restatement, and the terminating move is a pointer at its source.
