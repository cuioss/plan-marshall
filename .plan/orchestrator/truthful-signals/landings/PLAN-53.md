# Landing Analysis: PLAN-53 — Orchestrator queue row-field setter

epic: truthful-signals
workstream: WS-01
pr: #1010 (https://github.com/cuioss/plan-marshall/pull/1010) — squash-merged via the merge queue as `d44fdccb8`

> Landing record for one shipped plan. Written by the `analyze` verb after verifying each
> claim against ground truth — the merged commit, the shipped source at HEAD, and the CI
> abstraction's PR state. The finalize narrative was treated as a lead, not a fact.

## Deliverable Fidelity vs Spec

The spec staged **five** deliverables (D1 gate, D2 setter, D3 gap signal, D4 guidance sweep,
D5 tests); the landing reports **three**. The renumbering is a presentation difference, not a
scope reduction: D1 shipped as the ADR-grade verdict table in the PR body (the spec required
"ADR-grade rationale in the PR body" — satisfied literally), and D5's tests shipped inside
D1–D3 rather than as a separate line. **All five spec deliverables are accounted for.**

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — design gate, ADR-grade rationale in PR body | shipped-as-specified | 6-row verdict table in the `d44fdccb8` commit message: setter shape, whitelist, unknown-id, unknown-field, concurrency, D3 trigger |
| D2 — per-row setter through the manage-status-mediated path | **shipped-modified (premise corrected)** | `orchestrator.py:60` `PLAN_ROW_FIELDS`, `:139` `_mutate_plan_row`, `:169` `rmw_json(...)`, `:244-248` `invalid_field`, `:513` argparse. See "Premise correction" below |
| D3 — unstamped terminal row made observable | shipped-as-specified | `orchestrator.py:66` `TERMINAL_PLAN_STATUSES = ('shipped','landed')`, `:307`/`:323` gap marker in `_format_plan_line`. Correctly-stamped rows render byte-identically |
| D4 — retire the direct-edit instruction from guidance | **shipped-rescoped (no literal target existed)** | Verified independently: a scan of the whole `.plan/local/orchestrator/**` + `archived-orchestrators/**` tree finds NO ledger that currently *prescribes* a direct `status.json` edit. `truthful-signals/epic.md:309` only *describes* the past defect. D4 became "fill the vacuum that invites it" — `SKILL.md` canonical block, `analyze.md` Step 4, `landing-analysis.md` per-field checklist |
| D5 — tests | shipped-as-specified | `test_orchestrator.py` +263 lines: `TestQueueSetRow` (named-row set, sibling byte-identity, unknown-id and unknown-field fail-closed, mutual-exclusivity), `TestResumeSummary` gap-marker cases |

**Premise correction (D2) — a spec claim was CONTRADICTED at implementation time.** The spec
asserted D2 would write "through the same `manage-status`-mediated path the transition already
uses". Ground truth: `--transition` called `file_ops.write_json` **directly**. The plan honoured
the spec's *intent* ("no new direct-write path") by routing BOTH branches through one
`_locks_core.rmw_json`-guarded helper — so it **removed** a pre-existing lost-update surface
rather than merely declining to add one. Confirmed at HEAD: `_write_status` no longer exists in
`orchestrator.py`; every write goes through `rmw_json` (`:37` import, `:169` call site).
This is a net-positive overshoot of the staged scope, and it retires the exact whole-array
lost-update risk the spec's "twice in one session" observation documented.

**Verify-first scorecard.** The spec's own OBSERVED/HYPOTHESIS labels held up well: the
HYPOTHESIS about interleaved emptiness (per-session diligence variance, not a withdrawn writer)
was already settled at staging time and needed no rework. The one claim that failed was an
*unlabelled* incidental assertion inside D2's prose — "the same manage-status-mediated path the
transition already uses" — which carried no label at all. That is the labelling gap, not a
labelling error: the Verify-First Contract's three claim classes do not currently fence a
mechanism claim embedded in a deliverable's body text. Recorded as a watch.

## Metrics and Anomalies

- Tokens: ~2M
- Duration: 1h22m worked
- Finalize: 21/21 steps complete; `lessons-housekeeping` 0 removed / 0 promoted / 136 retained;
  `lessons-capture` folded into 2 existing lessons; `plugin-doctor` clean (3 skills gated);
  `pre-submission-self-review` found and fixed 1 contract-drift finding
- Anomalies: **first CI resolution was RED** — `review / review` reported CANCELLED. Diagnosed as
  the known PR-Agent `concurrency` + `cancel-in-progress` self-cancellation, not a code failure;
  a workflow rerun turned it green. 12 checks green at merge.

## Routing and Merge Behavior

- Review: `automatic-review` 0 comments. PR-Agent's finding count was **zero this run**, so the
  third-reviewer publish path remains unverified on this repo beyond the earlier API-Sheriff case.
  `review-retrospective` had nothing to compare — the 3-reviewer retrospective is still owed.
- CI/merge: green after rerun (12 checks), squash-merged via the merge queue, branch cleaned up,
  worktree removed, main clean. No rebase conflicts.
- **Surface collisions: none.** PLAN-53 ran concurrently with PLAN-69, PLAN-66 and PLAN-51 and
  touched only the `marshall-orchestrator` tree plus its test module, exactly as its spec's
  disjointness section predicted. The four-way disjointness call is **validated by outcome**.
  Notably, PLAN-53's HYPOTHESIS about pulling `manage-status/_status_core.py` into scope did NOT
  materialise — the seam chosen was `_locks_core.rmw_json` instead — so the flagged
  PLAN-53/PLAN-57 collision risk never came due.

## Reconciliation Actions

- [x] status.json `plans[]` entry updated — status `launched` → `shipped`, `pr=1010`,
      `landing=landings/PLAN-53.md` (stamped with the `--set-row` verb this plan shipped)
- [x] epic.md queue row reconciled from status.json
- [x] Watch added — unlabelled mechanism claims inside deliverable body text escape the
      Verify-First Contract's three claim classes
- [x] Watch added — PR-Agent `cancel-in-progress` self-cancellation produced a red CI resolution
      requiring a manual rerun (second observation of this defect)
- [x] Watch updated — third-reviewer publish path still unverified on this repo (0 findings)
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

- **The setter is now the sanctioned stamping path** — `analyze.md` Step 4 and the
  landing-analysis template both name it. This landing dogfooded it: PLAN-53's own `pr` and
  `landing` cells were stamped with `queue --set-row`, which is the strongest available
  end-to-end confirmation that the shipped verb works.
- **PR-Agent self-cancellation is now n=2** (this landing + the API-Sheriff #103 observation).
  It is an infrastructure defect in `.github/workflows/pr-agent.yml`, not epic surface, but it
  sits squarely inside PLAN-70's territory (which already owns the review-registry sweep and has
  a ZERO-content-hit finding on that same workflow file). Recorded as a watch and flagged to
  PLAN-70 rather than staged separately.
- **marshal.json provisioning stamp is stale** (0.1.1192 vs 0.1.1218) — operator-facing
  `/marshall-steward` reconciliation, outside the orchestrator's carve-out. Surfaced to the
  operator. This is ALSO a live instance adjacent to PLAN-69's territory: a version stamp that
  disagrees with what is actually installed.
- No new plan staged. Nothing in this landing needs work that an existing staged spec does not
  already own.
