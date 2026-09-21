# Landing Analysis: PLAN-CIS-051 — Detector and auditor integrity

epic: code-intelligence-substrate
workstream: WS-07
pr: #1370 — https://github.com/cuioss/plan-marshall/pull/1370

> Landing record for one shipped plan. Written by the `analyze` verb after verifying
> claims against ground truth. A pasted claim is a lead, never a fact.

## Ground truth corroborated

| Claim (from operator paste and inbox `-014.md`) | Verdict | Evidence |
|---|---|---|
| PR #1370 merged | corroborated | `ci pr view --pr-number 1370` → `state: merged`, `merge_commit_sha: 7845a4b9a383a4d58c9314bfce89970ced67c4f7` |
| main at `7845a4b9a` | corroborated | `git log origin/main` → `7845a4b9a … (#1370)` at HEAD |
| 9/9 deliverables | corroborated as shipped, but see fidelity below | landing-facts `deliverables_total=9 deliverables_done=9`; spec declares D0–D7 (eight) |
| 23,631 tests green | recorded, not independently re-run | landing-facts `final_verify=green final_verify_tests=23631` |
| Archived at `.plan/local/archived-plans/2026-08-31-detector-and-auditor-integrity` | corroborated | directory present with `metrics.md`, `execution.toon`, `work/metrics.toon` |
| `files_modified=54` | **contradicted** | the merge commit changes **63** files (`git show --stat 7845a4b9a`) — a nine-file under-count, consistent with the landing's own `references.affected_files` under-recording finding |
| Executive Summary section can never be written | **corroborated in substance, count not reproducible** | every occurrence in `plan-retrospective/` production source is a read, a comparison, or documentation; `retro_sections.py:205` states underscore-prefixed keys are unregisterable; no injection site exists. The message's "15 of 18 corpus occurrences in tests" does not reproduce at HEAD — the corpus-wide population is **24, of which 16 are under `test/`**. The mechanism is confirmed; the published ratio carries no population and is not re-derivable. |
| `metrics.toon` records `re_entered_phases: []` and 5-execute `close_count: 1` despite two loop-backs | corroborated | `work/metrics.toon` carries `close_count: 1` for all six phases; `quality-verification-report.md` records `loop_back_iteration=2` and a 6-finalize→5-execute re-entry at `2026-08-30T20:44:38Z` against `value_scope=single_close` |
| `pr-agent` (the REQUIRED bot) returned "No major issues detected" in all three rounds | **CONTRADICTED — see below** | `ci pr reviews --pr-number 1370`: 47 reviews from exactly three distinct users — `coderabbitai` (24), `cuioss-oliver` (22), `sourcery-ai` (1). **No `pr-agent` row.** `ci pr comments`: 81 comments, zero `pr-agent` occurrences |
| CodeRabbit (OPTIONAL) filed 25 findings | corroborated in magnitude | 29 inline `coderabbitai` comments on the PR; 15 of 81 threads unresolved |
| Sourcery refused structurally "in every round and never reviewed" | partially contradicted | exactly **one** `sourcery-ai` review exists (`COMMENTED`, 2026-08-30T16:38:58Z), not one per round. "Never reviewed" is consistent with a refusal body; "in every round" is not supported by the record |

### The reviewer contradiction, stated precisely

`.plan/marshal.json` sets `required_bots = "pr-agent"` and `optional_bots = "coderabbit,sourcery"`.
`pr-agent` left **no observable trace on PR #1370** — not a review, not a comment — yet the
plan's `automatic-review` step reported the required-bot quorum satisfied in three successive
rounds.

The landing narrates this as a bot that "satisfied the quorum every time while corroborating
nothing". The record supports something sharper and worse: the required reviewer did not
*respond weakly*, it did not **participate at all**, and the gate passed anyway. A quorum that
clears on a reviewer with zero observable participation is measuring its own configuration
rather than any review — the epic's own theme, sitting in the gate that admits a PR to merge.

This is the confirmed-by-absence form and it is **not** the known in-place-edit behaviour: an
in-place edit leaves the comment present with an updated timestamp, and there is no comment.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D0 — Re-derive the defect set before changing anything (gating) | shipped-as-specified | landing item 1; D1–D7 re-derived against the current tree before edits |
| D1 — `check-dispatch-audit` publishes measurements, not defaults | shipped-as-specified | `check-dispatch-audit.py` +476; `not_evaluated` added as a fourth grade; `test_check_dispatch_audit_measurement_contract.py` (+780) |
| D2 — Report section partition, and its two producerless registry rows | shipped-modified | `compile-report.py` +263, `report-structure.md`, `retro_sections.py`. The partition is now one discriminator. **The second producerless row was escalated, not decided** — see inbox `-013.md` and Follow-Ups |
| D3 — Remaining `plan-retrospective` checks stop hiding their inputs | shipped-as-specified | `analyze-logs.py` +206, `check-manifest-consistency.py` +107, `check-routing-decisions.py` +92, `test_retrospective_checks_input_availability.py` (+512) |
| D4 — Archived-plan auditor reads what it claims to read | shipped-as-specified | `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` +453 and five `checks/*.md`; `test_audit_examined_population_precedence.py` (+143) |
| D5 — Dependency validator + the detector that would have caught its drift | shipped-as-specified | `_analyze_documented_verb_set_drift.py` (new, +686), `_rule_registry.py`, `_dep_index.py` +162; found 2 genuinely unresolved rows the old validator could not see |
| D6 — Two small validators stop failing silently | shipped-as-specified | `manage-solution-outline.py` +134, `manage-execution-manifest.py` +32 |
| D7 — A delta round can be blind to its own delta | shipped-as-specified | `_self_review_detectors.py` +204, `self_review.py`; six per-class coverage counts each seeded to zero |
| *(added-unplanned)* Every guard proven to bite by mutation (42/42) | added-unplanned | landing item 9; 42 mutations across D1–D7, four killed no test and were each given a killing test proven RED-then-GREEN |

**Realized surface exceeded the declared surface at four paths.** `## Expected Surface`
declared neither `plan-marshall/skills/script-shared/scripts/argparse_surface.py` (+63),
`manage-execution-manifest/scripts/_manifest_core.py` (+35),
`manage-execution-manifest/scripts/_decision_line_shapes.py` (+23), nor
`plan-retrospective/references/logging-gap-analysis.md` (+64). The spec named
`manage-execution-manifest.py` "emitter only". This is the declared-vs-realized footprint
drift the epic tracks, recorded here as evidence for the next disjointness pairing.

## Metrics and Anomalies

- Tokens: 9,415,265 dispatched; 244,268,269 billing-weighted (~26×). 6-finalize alone is
  113,180,615 billing-weighted — 46% of the run.
- Duration: 43h50m reported wall, 10h59m worked (n=5/6), 32h51m idle.
- Loop-backs: 2 of a ceiling of 5. Tasks: 26. Findings: 138, all resolved.

**Two figures in the report are not what they look like, and both are corroborated:**

1. **The 6-finalize cell absorbs both loop-back execute passes.** `work/metrics.toon` carries
   `close_count: 1` and `value_scope=single_close` for 5-execute while status metadata records
   `loop_back_iteration=2` and a 6-finalize→5-execute re-entry. `re_entered_phases` is empty.
   The accumulate-on-re-entry contract exists and **never fires on a real loop-back** — so
   3,804,957 is not finalize cost.
   ⛔ This is the retired-per-phase-figure archetype recurring in a sharper form: previously
   the figures were *unrepresentable*; here the representation exists and the producer never
   writes it.
2. **4.46M tokens are named by no record-step row**, so the execution-log total covers ~37%
   of the spend it summarises (inbox `-008.md`: neither ledger sees the whole plan; the union
   exceeds either by 12 rows).

Both are recorded as Open Defects and folded into the queue below rather than carried as prose.

## Routing and Merge Behavior

- Review: three participants — `coderabbitai` (24 reviews / 29 inline comments, 15 of 81
  threads unresolved at merge), `cuioss-oliver` (22), `sourcery-ai` (1). The configured
  REQUIRED bot `pr-agent` did not participate. See § the reviewer contradiction.
- CI/merge: merged via merge queue (`step.branch-cleanup.merge_mechanism=merge_queue`),
  merged at 2026-08-31T07:47:15Z, final verify green over 23,631 tests.
- **Merge-mutex override, and it cost what it was meant to prevent.** The mutex was overridden
  on operator instruction after ~50 minutes blocked by a sibling plan. The first enqueue was
  then EJECTED when four upstream PRs landed during the queue wait
  (`step.finalize-step-sync-baseline.action=rebased`, `upstream_commit_count=4`), forcing a
  rebase, a re-derived constant, a full re-verify, a force-push and a re-review. No step
  records this; it is operator narrative preserved here.
- **A rebase conflict that could not be merged, only measured.** `EXPECTED_MARKER_ANCHORS` was
  24 upstream and 26 on the branch; the truth on the merged tree was 25. Picking either literal
  would have shipped a false measurement into a test whose purpose is to publish a real one.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-CIS-051 --status shipped`
- [x] row `pr` stamped `1370`
- [x] row `landing` stamped `landings/PLAN-CIS-051.md`
- [x] row `plan_marshall_plan_id` stamped `detector-and-auditor-integrity`
- [x] epic.md queue reconciled from status.json; both generated blocks regenerated
- [x] inbox drained — 19 enumerated, dispositions recorded per message
- [x] resume_anchor updated (prepended, never overwritten)

## Follow-Ups

Each is recorded with where it went; none is left as prose only.

- **Required-bot quorum clears on a non-participating reviewer** (`pr-agent` absent from #1370
  while `required_bots="pr-agent"`) → routed to the **`review-apparatus`** epic under the
  standing three-way rule: the PR/review test runs first and wins outright. Recorded here as
  the corroborating measurement; the fix is not ours.
- **Phase re-entry accounting never fires on a real loop-back** (inbox `-004.md`) → folded into
  `PLAN-CIS-050-measurement-and-cost-integrity`.
- **Neither token ledger sees the whole plan; union exceeds either by 12 rows / 4.46M**
  (inbox `-008.md`) → folded into `PLAN-CIS-050`.
- **Context-load channel recorded 0 measured rows across 33 dispatches** (inbox `-009.md`) →
  folded into `PLAN-CIS-050`; corroborates lessons-handling `-001.md`'s seven-mechanism cluster.
- **Executive Summary section structurally unwritable** (inbox `-003.md`) → folded into
  `PLAN-CIS-054-documentation-surface-truthfulness`… *(see queue annotations for the final
  fold target recorded at drain time)*.
- **`pre-commit-verify-freshness` is canonical-blind** (inbox `-001.md`, qgate `3e7381`,
  severity `error` — it can admit an unverified tree to finalize) → staged as new work.
- **`phase-3-outline:480` promises a phase-4-plan guard that does not exist** (inbox `-002.md`)
  → folded into `PLAN-CIS-054`.
- **`architecture search --content` `count` is a double-counted ROW count**
  (truthful-signals `-053.md`) → the seam is ours (`PLAN-CIS-001`, shipped), so this is a
  successor, not a re-open.
