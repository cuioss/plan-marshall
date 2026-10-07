# Landing Analysis: PLAN-PR-067 — The comment pipeline on the way in

epic: review-apparatus
workstream: WS-03
pr: plan-marshall#1616 (merged `93f5d7dbd91fea8aa59ebb158f5fa796b181e1e9`; superseded #1612, closed unmerged)

> Landing record for one shipped plan. Written after verifying every claim in the plan's own
> landing message against ground truth (dispatched `execution-context-level-5` corroboration,
> read-only) — the message is a lead, never a fact.

## Deliverable Fidelity vs Spec

Spec declares 10 deliverables (D0 gate + D1–D9). `landing-facts` reports
`deliverables_total=10, deliverables_done=10`, matching the spec's own count — but the archived
`status.json` carries **no independent deliverable counter** (no `deliverables` field anywhere in
`metadata` or `phases[]`), so `deliverables_done=10` is self-reported with no second witness in
the archive, same caveat as `PLAN-PR-066`'s landing.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| Declared Expected Surface (7 files) | shipped-as-specified | All 7 declared files appear in `#1616`'s diff; `test_github_pr.py` is the one `A` (added), the rest `M`. |
| Everything else the PR actually touched | **shipped-but-massively-undeclared** | See "Undeclared surface expansion" below — this is the dominant finding of this landing, more severe than `PLAN-PR-066`'s. |

## Metrics and Anomalies

- Tokens: **12,215,287 (12.2M)**; Duration: **26h44m** (`total_wall_seconds=96264.0`) — both match
  `record-metrics` facts exactly.
- Finalize: all 22 `6-finalize` steps report `done`.
- **Self-review closed under operator waiver after 7 rounds** (`firing_count: 7`, 6 `loop_back`
  firings + 1 waived close, `facts.acceptance=operator_waived`). Sibling churn: `simplify` fired
  10 times, `plugin-doctor` 9, `automatic-review` 5, `pre-push-quality-gate` 4, `ci-verify` 3 —
  finalize consumed 51% of total tokens (6.30M of 12.33M per the plan's own D9-adjacent lesson
  filing), the single most loop-back-heavy landing recorded in this epic so far.
- **Merged under a HEAD-bound `barrier-ask-override`** at `4ebee67ec26ececed8f70cb64910040fcccdf628`
  (matches the claimed sha exactly): required reviewer `cuioss-review-bot` was `participated_stale`
  (its last review predated a one-file indented-code fix). Operator ruling: "Merge anyway: one-file
  indented-code fix merged without cuioss-review-bot re-review." The override was granted at
  15:21:15Z, the merge landed 15:21:44Z — 29 seconds apart.
- **`create-pr`'s PR-number fact was correctly re-stamped this time** (`#1612` → `#1616`,
  `firing_count: 2`), unlike `PLAN-PR-032`'s landing which this epic recorded as a producer-gap
  defect — but the mechanism is not fixed, this run just happened to re-fire the step. See
  Follow-Ups (lesson `2026-09-24-16-001`).

## Routing and Merge Behavior

- Review: `cuioss-review-bot` marked `participated_stale`; merge authorized by operator override
  (above), not by a clean review.
- CI/merge: merged via merge queue, `cleanup_owed: false`.
- **`PR body vs actual diff` — two independent inaccuracies, corroborated structurally, not just
  narratively**: (a) the body's "Formatting chore" section claims ruff reformatted
  `test/test_shared_harness_parse_ns_defaults.py` and `_no_seam.py`; neither file is in the merge
  diff (`git log` shows both were last touched by earlier, unrelated PRs #1599/#1593 — the churn
  was absorbed upstream by a rebase and the body over-claimed it). (b)
  `manage-solution-outline/scripts/_plan_parsing.py` and `manage-solution-outline.py` are both
  modified in the diff but named **nowhere** in the PR body's Changes inventory (independently
  confirmed via CodeRabbit's own `Files selected for processing` list in finding `c108f6`) — files
  that landed silently, undisclosed in the PR's own description as well as undeclared on the spec.

### ⛔⛔ Undeclared surface expansion — the dominant finding of this landing

**24 of the 31 realized files were never on `PLAN-PR-067`'s declared Expected Surface (7 files).**
This is a much larger under-declaration than `PLAN-PR-066`'s (which had 2 undeclared files). Two
distinct populations:

**12 files collide with STILL-STAGED sibling specs** — each of these plans' Expected Surface now
overlaps files this landing already realized, and the corpus-surfaces-membership disjointness
check that would ordinarily guard emission cannot see any of it, because `PLAN-PR-067` never
declared touching them:

| File | Declaring sibling spec(s) | Consequence |
|---|---|---|
| `phase-6-finalize/scripts/pr_intent_section.py` | **PLAN-PR-073** | pre-consumed |
| `phase-6-finalize/workflow/create-pr.md` | **PLAN-PR-073**, **PLAN-PR-077** | pre-consumed on both |
| `test/plan-marshall/phase-6-finalize/test_pr_intent_section.py` | **PLAN-PR-073** | pre-consumed |
| `automatic-review/scripts/review_gate_delta.py` | **PLAN-PR-071** | pre-consumed |
| `test/.../test_counting_rule_parity.py` | **PLAN-PR-071** | pre-consumed |
| `test/.../test_review_gate_delta_exclusions.py` | **PLAN-PR-071** | pre-consumed |
| `automatic-review/standards/bot-participation-contract.md` | **PLAN-PR-069** | pre-consumed |
| `automatic-review/standards/cuioss-review-bot.md` | **PLAN-PR-069** (+ PLAN-PR-066, shipped) | pre-consumed |
| `manage-solution-outline/scripts/manage-solution-outline.py` | **PLAN-PR-074** | pre-consumed, undisclosed in PR body |
| `phase-6-finalize/standards/branch-cleanup.md` | **PLAN-PR-074** | pre-consumed |
| `finalize-step-review-retrospective/scripts/review_retrospective.py` | **PLAN-PR-076** | pre-consumed |
| `marshall-steward/references/landing-cycle.md` | PLAN-PR-066 only (already shipped) | moot |

⛔⛔ **`PLAN-PR-071` is now 50% pre-consumed (3 of its 6 declared files) and `PLAN-PR-073` is 43%
pre-consumed (3 of its 7)** — the two highest-exposure specs in the corpus by this measure. Neither
should be emitted without a full re-grounding against `93f5d7dbd` first — their declared Expected
Surface and their claims about what those files contain are both now suspect.

⛔ **`PLAN-PR-068`'s known 3-file declared overlap with `PLAN-PR-067` has now fully LANDED.**
`github_pr.py`, `workflow-integration-github/SKILL.md`, `test_github_pr.py` — the exact three files
`PLAN-PR-067`'s own Claim Labels already flagged as a sequencing risk (`verdict: contradicted`,
`checked_at: 7d82d5d90`, "DISJOINTNESS IS FALSE") — are now realized in `#1616`. This converts a
sequencing risk into a fact: `PLAN-PR-068` must be re-grounded, not merely sequenced, before it
next runs.

**12 further files are declared by NO spec in the epic at all** — an orphaned undeclared surface,
mostly a new `tools-integration-ci` CI-verb surface and merge-queue/refusal test coverage:
`doc/user/parallelism-and-locking.adoc`; `manage-solution-outline/scripts/_plan_parsing.py`;
`tools-integration-ci/SKILL.md`, `standards/api-contract.md`, `standards/gitlab-impl.md`,
`standards/pr-operations.md`; and six test files (`test_participation_site_population_records.py` —
adjacent to but not identical to `PLAN-PR-070`'s declared `test_participation_site_population_guards.py`
— `test_merge_shaped_offrouting_refusal_offrouting.py`, `test_github_merge_queue.py`,
`test_github_ops_pr_merge_queue.py`, `test_github_pr_refusals.py`, `test_pre_merge_barrier_core.py`).
Not retro-corrected on the now-shipped spec (this epic's standing precedent — a shipped spec's
surface has no consumer); recorded as an Open Defect for a future spec to formally claim.

⚠ **A spec-internal contradiction, harmless now the spec is terminal but worth recording**: the
spec's own 2026-09-18 D3 amendment asserted `pr_intent_section.py` was "already on this spec's
Expected Surface" — it never was; the file is declared by `PLAN-PR-073` instead. The claim was
simply wrong about the spec's own declaration and nobody caught it before staging.

## Reconciliation Actions

- [x] row `status` → `shipped`
- [x] row `pr` stamped → `plan-marshall#1616`
- [x] row `landing` stamped → `landings/PLAN-PR-067.md`
- [x] row `plan_marshall_plan_id` stamped → `the-comment-pipeline-on-the-way-in`
- [x] epic.md narrative reconciled (Queue annotation + Open Defect)
- [x] Open Defect opened: the 24-file undeclared-surface expansion, split into the 12-file
      sibling-collision population and the 12-file orphan population
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated via `orchestrator regenerate-view`
- [x] inbox messages `the-comment-pipeline-on-the-way-in-001` through `-006` drained and archived
      (1 landing reconciled here, 4 candidate-lessons folded as recurrences, 1 promoted as a new
      lesson)

## Follow-Ups

- **`PLAN-PR-071` and `PLAN-PR-073` must be re-grounded against `93f5d7dbd` before either is next
  emitted** — recorded prominently in the Queue annotations, not just here, since `next`'s ordinary
  membership check cannot see this on its own.
- **`PLAN-PR-068` needs full re-grounding, not merely sequencing**, before it next runs — its
  3-file declared overlap with this landing is now realized fact, not risk.
- **`PLAN-PR-069`, `PLAN-PR-074`, `PLAN-PR-076`, `PLAN-PR-077`** each have 1–2 files now pre-consumed
  by this landing — lower exposure than 071/073, recorded but not blocking emission on their own;
  re-check at their own outline/re-grounding time.
- **12 orphan files declared by no spec** — a genuine corpus gap (new `tools-integration-ci` verb
  surface + merge-queue/refusal test coverage that arrived with no owning deliverable). Not staged
  as a new spec here (out of scope for a landing reconciliation); recorded as an Open Defect for a
  future cleanup pass to judge whether it needs its own spec or folds into an existing one (likely
  `PLAN-PR-068`'s merge-queue/refusal surface, given the file names).
- Lesson `2026-09-24-16-001` (create-pr record re-stamp) — promoted; the mechanism that
  re-stamped the PR number correctly *this* run is not guaranteed, only observed once.
- Lessons `2026-09-23-05-001`, `2026-09-24-09-001`, `2026-09-24-09-005`, `2026-09-24-09-008` — each
  gained a further recurrence note from this plan's finalize (4th, 4th, 2nd-direction, and 2nd
  occurrence respectively); no new lesson filed for these.
