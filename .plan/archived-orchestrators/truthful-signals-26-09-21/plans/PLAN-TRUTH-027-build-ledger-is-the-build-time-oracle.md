# PLAN-TRUTH-027: make the build ledger the build-time oracle — reporting and retrospective audit

epic: truthful-signals
workstream: WS-01

## Objective

Consume what `PLAN-TRUTH-026` makes available: report **total build time** in the plan's final report,
and teach `audit-archived-plan-retrospectives` to audit the build ledger — **build time vs overall
wall-clock** and the **passing/failing build ratio**.

⚠ **This is a RE-BASING, not a greenfield addition.** A build-duration audit already exists; it
reconstructs durations by regex-parsing a log that is both incomplete and tool-specific. The value here
is replacing a lossy derivation with the structured ledger, not adding a second one.

## Provenance

Operator request, 2026-07-31, as a follow-on to `PLAN-TRUTH-026`. Split out of that plan rather than
folded into it: 026 stood at six deliverables (already at the split threshold), and this half is
**surface-disjoint** from it — 026 mutates producers (`script-shared/build`, the executor template,
the wrappers, `manage-change-ledger`), this one mutates consumers (`plan-retrospective` and the
project-local audit skill). Split recorded as an epic decision.

⚠ **Routing note, recorded rather than acted on.** By this epic's inbound routing rule, *measurement of
our own runs* is `code-intelligence-substrate`'s subject and this would ordinarily be forwarded. **The
operator assigned it here explicitly, as part of this work chain.** Kept, with the tension noted so a
later reader does not "correct" the routing. ⇒ **Notify `code-intelligence-substrate` when this lands**
— the audit corpus is what they read.

## Deliverables

1. **D0 — GATE (mutates nothing): establish what already exists, and the wall-clock denominator.**
   Read the existing `sequence-and-build-minimality` check and enumerate exactly which build facts it
   derives, from which source, over which population. Then establish the wall-clock denominator the
   ratio needs. ⛔ **Do not add a check that duplicates a facet already computed** — fold instead.
   ⚠ D0 also settles whether `work/metrics.toon` is present often enough to be a reliable denominator;
   the existing metrics check has an absent-file branch, so a ratio built on it inherits that hole.
2. **D1 — re-base build-duration classification onto the ledger.** The existing check derives duration
   by parsing `(N.NNs)` out of `logs/script-execution.log` for `build-pyproject:pyproject_build run`
   calls. Post-026 the ledger carries `duration_seconds` structurally, for **every** build system.
   ⛔ **Two blindnesses must be named and closed, not silently inherited**: (a) the current derivation
   sees only `build-pyproject`, so Maven / Gradle / npm builds are invisible; (b) per 026's finding,
   builds run in phases 1-4 never reach the plan-scoped log at all, so they are invisible regardless of
   tool. ⇒ **The current build totals are undercounts of unknown size** — say so, and quantify the
   delta once the ledger is authoritative.
3. **D2 — the two new ledger-derived facets.** (a) **Build time vs overall wall-clock** — the share of
   a plan's elapsed time spent inside builds. (b) **Passing vs failing build ratio**, derived from the
   ledger `status` field across its four values (`success` / `error` / `timeout` / `killed`).
   ⛔ **`killed` is not `error`** — a whole-tree kill is an infrastructure event, and collapsing it into
   "failed" would report a harness problem as a code problem. ⭐ Add the invariant the existing metrics
   check's *impossible values* family already models: **build time cannot exceed plan wall-clock** —
   a violation is a recording defect, and it is the check that would have caught a duration plumbed
   through wrongly by 026.
4. **D3 — report total build time in the final report.** Surface the aggregate on the plan's own
   reporting surface, not only in the cross-plan audit. ⚠ D0 names the exact surface; **do not assume
   it is the retrospective report** — the operator's phrasing ("final report") may name a different
   artifact, and this is the deliverable most likely to be aimed at the wrong file.
5. **D4 — tests, each verified to FAIL pre-fix, plus doc reconciliation.** (a) A ledger with a known
   mix of the four statuses produces the expected pass/fail ratio, with `killed` counted separately.
   (b) A build-time-exceeds-wall-clock fixture is flagged. (c) A non-pyproject build appears in the
   totals — **the test that proves blindness (a) is closed**. (d) The D0 population derivation is
   asserted non-empty. Reconcile the affected check documents and `SKILL.md`'s check count, which is
   stated as a number in the skill description.

## Claim Labels

- **OBSERVED**: `audit-archived-plan-retrospectives` has 23 check documents under `checks/`
  (enumerated this pass), and **none of them references the change ledger** — `change-ledger`,
  `change_ledger`, and `kind=build` all return zero hits across the skill.
- **OBSERVED — the overlap that reframes this request**: `checks/sequence-and-build-minimality.md`
  ALREADY performs "build-duration classification" against `THRESHOLDS` duration bands, sourcing
  `logs/script-execution.log` `notation subcommand (N.NNs)` lines, and its documented classification
  population is `build-pyproject:pyproject_build run` calls. ⇒ **The request is not "add build-time
  auditing"; it is "stop deriving it from a lossy log".**
- **OBSERVED**: `checks/metrics.md` documents `work/metrics.toon` as contributing `duration_seconds`
  (wall-clock), `agent_duration_seconds` (worked), and `idle_duration_ms`, and already carries an
  *impossible values* rule comparing worked against wall-clock — the precedent D2's invariant follows.
  It also documents an **absent-`metrics.toon` branch**, which is the hole D0 must size.
- **HYPOTHESIS**: `work/metrics.toon`'s `duration_seconds` is the right wall-clock denominator for D2a.
  **Confirm/refute at D0.** Confirm/refute artifact: the metrics producer that writes `duration_seconds`
  and whether it is per-phase-summable to a plan total.
- **HYPOTHESIS**: the "final report" surface in D3 is the retrospective report rather than a distinct
  finalize-phase artifact. **Confirm/refute at D0 — an operator's naming of one artifact may
  under-scope or mis-aim the work** (this epic's standing rule).
- **HYPOTHESIS**: the shipping-predicate exclusion `sequence-and-build-minimality` applies (plans that
  delivered nothing are excluded before the check sees them) should apply identically to the new
  facets. **Confirm/refute at D0** — inheriting it silently would be as wrong as dropping it silently.
- **Verify-first clause**: this plan is meaningless until `PLAN-TRUTH-026` has landed the
  `duration_seconds` ledger field. If 026's D3 re-scoped away from plumbing duration (its own
  verify-first clause allows that), **this plan re-scopes with it** — D1 and D2a both assume a
  structured duration exists in the ledger.

## Expected Surface

- **OBSERVED**: `.claude/skills/audit-archived-plan-retrospectives/checks/sequence-and-build-minimality.md`
  — the existing build-duration derivation to re-base
- **OBSERVED**: `.claude/skills/audit-archived-plan-retrospectives/checks/metrics.md` — the wall-clock
  source and the impossible-values precedent
- **OBSERVED**: `.claude/skills/audit-archived-plan-retrospectives/SKILL.md` — the stated check count
- **HYPOTHESIS**: `.claude/skills/audit-archived-plan-retrospectives/scripts/**` — the implementing
  analyzers named in the check doc (`cross_sequence_build_minimality` and siblings), by symbol
  (verify-at-outline)
- **HYPOTHESIS**: `plan-marshall/skills/plan-retrospective/**` for D3 (verify-at-outline — D0 names it)
- **HYPOTHESIS**: tests under the project-local skill's test home

## Dependencies and Sequencing

- ⛔ **Depends on PLAN-TRUTH-026** — hard. This plan consumes the `duration_seconds` field and the
  mandatory `plan_id` 026 adds. **Do not launch before 026 lands.**
- ✅ **Surface-disjoint from PLAN-TRUTH-026** (consumers vs producers), so the two never collide; the
  dependency is on 026's *landed output*, not on its files.
- ⚠ **Adjacent to `code-intelligence-substrate`'s measurement work** — the retrospective corpus is
  theirs to read. Notify on landing (see § Provenance routing note).
- ⚠ **PLAN-TRUTH-018** (`configurable-display-timezone-for-rendered-timestamps`) touches rendering
  surfaces; if D3 renders a duration with a timestamp, check for overlap at outline.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-027-build-ledger-is-the-build-time-oracle.md"
```

## ⭐ FOLDED 2026-08-02 — a build whose published duration is 0 against 411 seconds of real work

**Reported by `code-intelligence-substrate` (msg `-012` § 5), explicitly NOT delegated** — they offered
it and we are taking it, because it is this plan's subject (the build ledger as the build-time oracle).

On PR #1079 a `module-tests` run was **killed at 411s by the build wrapper's internal ceiling while the
architecture-resolved envelope promised 441s**, and the outer routed status reported
**`duration_seconds = 0`** against 411 seconds of real work. The suite needed 330s and passed under an
explicit override.

⛔ **Two distinct defects, and this plan owns the second:**

1. **The wrapper's internal ceiling and the resolved envelope disagree** (411 vs 441). ⇒ **The published
   number and the enforced number are different, and only one is published.**
2. ⭐ **`duration_seconds = 0` for a 411-second run makes the ledger's own duration field actively
   false**, not merely absent — and this plan's D-series treats `duration_seconds` as the oracle for
   build-time-vs-wallclock reporting. **A zero is indistinguishable from a cache hit or a no-op**, which
   is the same conflation this epic recorded when a 2–5s type-check green turned out to be a stale cache
   (folded onto `PLAN-TRUTH-019`).

⇒ **D0 must treat `duration_seconds = 0` as a suspect value requiring corroboration, never as data.**
⚠ Corpus consequence: any build-time total computed over archived plans **under-counts by every killed
run**, in an unknown amount. Promoted by CIS to their corpus as lesson `2026-08-02-15-006`.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
