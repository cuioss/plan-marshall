# PLAN-TRUTH-169: A timeout verdict describes the wait, not the work — and the time budgets it is measured against are undeclared

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md` as PM-MCP input.
> **Do NOT emit; un-park only by explicit operator decision.** The spec body below stays intact as the evidence chain.

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Provenance

Staged 2026-09-18 from the corpus-wide lessons sweep (131 scanned, 124 classified to this epic). Five
lessons across four plans, none previously owned by any spec; all preserved verbatim at
`.plan/local/orchestrator/truthful-signals/lessons/{id}.md`. Corroborated in a consuming repo the same
week by `api-sheriff-deployment-configurability-020`.

## Objective

**A build that succeeded is reported as a failure because the thing that died was the observer, and the
budgets those verdicts are measured against are picked rather than derived.** Three mechanisms, one
consequence — a red signal nobody can act on:

1. A `marshalld` timeout verdict abandons the wait and **never reaps the build**, so the documented
   re-run compounds the very load that caused it — and at least one `timeout` covered a build that had
   already passed.
2. Per-test time budgets are undeclared and machine-dependent: the same test is red under
   `module-tests` and green under `verify`/CI, because the budget was never derived from measured
   latency.
3. An adaptive build budget ignores what the preceding sync absorbed, so a cold rebuild after a
   dependency bump reads as a code-caused regression.

⭐ The epic's theme in its sharpest form: each verdict is *confident, wrong, and about a different subject
than the one it names*.

## Deliverables

Five deliverables. D0 is a gate.

**D0 — GATE: derive the verdict population and the budget population.** Enumerate every place a
time-based outcome becomes a build verdict (daemon wait, pytest-timeout, adaptive build budget, the
finalize wait barrier), and for each: what it measures, what it claims, and where its threshold comes
from. ⛔ Publish both populations with their sizes — five lessons found by four plans is a sample, not a
census.

**D1 — A timeout is a NO-VERDICT, not a red build.** `job_status=timeout` arriving before any test output
means the wait ended, not that the work failed. Report it as its own outcome that no consumer may read as
failure, and **reap or re-attach rather than resubmit**: re-attachment is by job id against the daemon.
⚠ `PLAN-TRUTH-078` shipped "a timeout is not a red test and a kill is not a timeout" — D0 states what
that left standing before D1 adds anything.

**D2 — The wait's death never silently discards the work.** When the observer dies, the daemon-side build
continues; the documented recovery is re-attach-by-id, and a resubmit must be refusable while a live job
for that id exists.

**D3 — Every time budget is derived and declared.** A threshold states the measurement it came from
(p50/p95 of observed runs) and the scope it applies to, so the same test cannot be red in one runner and
green in another without that difference being visible. Includes the adaptive build budget's blindness to
an absorbed dependency sync.

**D4 — Controls, both directions.** A genuinely failing build still reports red; a timeout over a passing
build reports no-verdict and is not counted as a failure in any roll-up; and a budget whose derivation is
absent fails loudly rather than defaulting to a number.

**D5 — ABSORBED from PLAN-TRUTH-158: report the observation, not the inferred cause, when a freshness
reconciliation record is absent.** `push.md`'s negative branch reads *"No reconciliation record names the
current HEAD: the `stale` is genuine un-built source drift"* — but that same contract produces that same
absence in **four** distinct ways: (1) no finalize-internal commit happened (the intended meaning), (2)
`SKILL.md` Step 3 item 5f(d) deliberately fail-closed because no `status: success` build entry existed,
(3) the record was owed and simply not emitted, and (4) — folded 2026-09-17 — the committing step sits
OUTSIDE the reconciliation membership entirely, because `default:architecture-refresh` (order 10) commits
its own descriptor changes while declaring no `mutates_source`, and `push.md` line 73 defines membership as
`mutates_source: true` AND `order >=` `pre-push-quality-gate`'s. Report
`reconciliation_record_absent` and name the causes that absence admits; ⛔ do NOT change the fail-closed
halt, which is correct on all four.

**D6 — ABSORBED from PLAN-TRUTH-158: corroborate cause 1 where it is cheap, and surface cause 2
distinctly.** Where the dispatcher's own `phase_steps` records (per-step `head_at_completion`) can
independently establish whether live HEAD is a finalize-internal commit, use that rather than trusting the
record's presence. Cause 2 (*the last build did not succeed*) is a materially different operator action
from causes 1/3 (*you edited source after the build*) — today both arrive as the same sentence.

**D7 — ABSORBED 2026-09-18 from `review-apparatus-043.md` § Set 2: the pyprojectx build-gate's coverage
boundary reports a limit it did not apply.** Bullets G5, G8, G9 and G12 of that epic's retired
`PLAN-PR-062` D4 (body at `PLAN-PR-030` § D4) edit `_gate_coverage.py` and `build.py` —
`_render_structural_limits`, `structural_limits`, `CoverageBoundary.complete`, `render_coverage_summary`,
`_ANALYSIS_LIMITS`, `_skip_empty_mypy_scope`, and the `structural_limit` field. ⭐ Routed here because a
coverage boundary that renders a limit it did not enforce is a **build-gate verdict that misdescribes its
own scope** — this spec's subject — and not PR-review machinery. ⚠ Read the bullets from the retired spec
at `.plan/local/orchestrator/review-apparatus/plans/`; they are NOT restated here, and the pointer chain is
successor → `Carried from` → retired theme spec → source.

⭐ **Why these merged rather than staying two plans.** Both specs are about a **time-or-state signal that
names the wrong subject**: a timeout that describes the wait, and an absent record that names one of four
causes as if it were the only one. They share `phase-6-finalize`'s push gate and the build-verdict
classification path, so splitting them costs two finalize cycles over one file family. ⚠ This is a
**confident merge**, not a weak one: the two D-sets are disjoint and neither collapses into the other.

## Claim Labels

Each is OBSERVED by the plan that filed the cited lesson; every lesson is preserved in this epic. ⛔ Re-ground
each against the named surface at HEAD before scoping (verify-at-outline for all).

- OBSERVED (lesson `2026-09-02-21-002`, KEEP of its cluster): a marshalld timeout verdict abandons the wait
  but never reaps the build, so every documented re-run compounds the load that caused it; the verdict
  described the wait while the build had passed. Members `2026-09-02-21-001` and `2026-09-03-09-001` were
  retired as redundant of it.
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Lesson 2026-09-02-21-002 preserved at lessons/; the marshalld timeout technical assertion was not re-grounded against build-server-client / manage-build-server at this HEAD, as the spec's own verify-at-outline-for-all instruction requires.
- OBSERVED (lesson `2026-09-05-21-001`, KEEP): the plugin-doctor real-tree test exceeds a 300 s
  pytest-timeout under a bare `module-tests` while passing under `verify` — the budget, not the code,
  decides the colour. Member `2026-09-02-20-001` (a 30 s budget against a 24–57 s verb) retired as redundant.
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Lesson 2026-09-05-21-001 present in the epic's lessons store; the 300s pytest-timeout-vs-verify divergence was not re-measured against test/conftest.py or the pytest config at this HEAD.
- OBSERVED (lesson `2026-09-04-08-016`): before treating a build timeout as budget-vs-code, check whether
  the preceding sync absorbed a dependency-graph change — a cold rebuild is not a regression.
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Lesson 2026-09-04-08-016 present; the dependency-sync/cold-rebuild premise was not re-grounded against the adaptive budget inputs.
- OBSERVED (inbox `api-sheriff-deployment-configurability-020`, first-party in a consuming repo): job
  `dbbc60f9` timed out at 300 s against a native IT whose p50 is 1250–1800 s, and a killed waiter for job
  `2ead9378…` was recovered by re-attaching to the same job id — the build had succeeded in 1255 s.
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Cites first-party observations inside inbox message api-sheriff-deployment-configurability-020 (job ids dbbc60f9 / 2ead9378); that message is consumed/archived and the daemon state is not re-observable read-only.
- ⚠ HYPOTHESIS: these four sites are the whole population — ⛔ asserted by nobody; D0 owns the derivation
  (verify-at-outline).
  - verdict: unverifiable | checked_at: 74153664d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Self-declared population claim (these four sites are the whole population), explicitly assigned to D0 by the spec itself.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-server-client/` — the wait/re-attach client contract (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-build-server/` — the daemon's timeout and reap behaviour (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/` — outcome classification (D1, D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/build-maven/` and `.../build-pyproject/` — the adaptive budget and its inputs (D3) (verify-at-outline)
- HYPOTHESIS: `test/conftest.py` and the pytest-timeout configuration — the per-test budget surface (D3) (verify-at-outline)
- OBSERVED: `test/plan-marshall/build-server-client/` and `test/plan-marshall/manage-build-server/` — D4's controls
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/push.md` — the freshness-reconciliation refusal text and its attribution logic (D5, D6; absorbed from PLAN-TRUTH-158)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/architecture-refresh.md` — the self-committing step outside the membership (D5; absorbed from PLAN-TRUTH-158)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — Step 3 item 5f(d)'s record-emission obligation and the `phase_steps` `head_at_completion` carrier (D5, D6) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/**` — coverage for the four-cause discrimination (D5, D6) (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py` — the coverage boundary and its structural limits (D7; absorbed from `review-apparatus-043` § Set 2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/build.py` — `render_coverage_summary` and the `structural_limit` field (D7) (verify-at-outline)

## Dependencies and Sequencing

## Folded Signals

- Folded 2026-09-22 from `truth-161-adr-number-allocation-001.md` (PLAN-TRUTH-161 landing): CI-wait timeout findings recurred during finalize and were taken into account as external-infrastructure noise with a verify re-run as remedy. First-party corroboration for D1's triage treatment (a timeout is a no-verdict, never a plan defect) and D4's roll-up discipline. Adds no file surface.
- Recurrence 2026-09-24 from `truth-147-lane-reports-green-003.md`: CI-timeout verdicts on verify runs are a standing consideration — `deadline_exceeded` from the precondition wait is re-polled to completion, interim findings taken into account as moot (3x). Owed `architecture enrich insight --module plan-marshall` stays plan-side. Adds no file surface.
- Recurrence 2026-09-24 from `truth-147-lane-reports-green-004.md`: same standing consideration for review-bot waits — `deadline_exceeded` CodeRabbit wait re-polled to completion, interim findings moot (2x). Adds no file surface.
- Folded 2026-09-25 from `lessons-routing-002.md` (relayed ex-API-Sheriff PLAN-29): `ci_wait`'s adaptive timeout budget doesn't fit known-slow CI jobs — 5 `ci_timeout` findings all resolved `accepted` ("retry, not a failure") across 3 loop-backs, pure wasted iteration on a deterministic disposition. D3's subject verbatim (budgets derived from measured latency): seed the adaptive budget with the project's known-slow ceilings, or re-poll once automatically before filing. Adds no file surface.
- Recurrence 2026-09-25 from `truth-179-opencode-target-detection-landed-006.md`: transient CI verify timeouts at superseded HEADs as standing consideration — taken into account, re-poll on current HEAD (2x). Adds no file surface.

## Dependencies and Sequencing

- Depends on: none.
- ⚠ Shares build-outcome classification with `PLAN-TRUTH-150` (build and CI verdicts that mislead on the
  healthy path). Different members, same file family — **sequence, never pair**.
- ⛔ `PLAN-TRUTH-078` already shipped in this area; D0 must read what it left standing rather than
  re-deriving from these lessons alone.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-169-a-timeout-verdict-describes-the-wait-not-the-work-and-time-budgets-are-undeclared.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
