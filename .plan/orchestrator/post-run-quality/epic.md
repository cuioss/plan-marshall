# Epic: Post-Run Quality Analysis

slug: post-run-quality

> Ledger document for one epic under `.plan/orchestrator/post-run-quality/`. The layout and
> authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

**Everything this project does to judge a run AFTER it has finished — and whether any of it is
trustworthy.** Fourteen distinct aspects exist today across four surfaces: the 16-aspect
`plan-retrospective`, the 24-check archived-plan corpus auditor, the metrics/findings measurement
substrate, and the lessons corpus that is supposed to close the loop. They were built one at a time, and
the evidence says the seams between them leak: a producer publishes a confident figure over a population
it never read; an auditor's own census cannot census itself; a process lesson reaches the governing
contract **1 time in 5**; and an obligation a finished plan left behind has no owner once that plan is
archived.

Too large for one plan because the aspects share no owner and no vocabulary: each is a separate producer,
several were built by different plans in different epics, and the fixes span `plan-retrospective`,
`.claude/skills/audit-archived-plan-retrospectives`, `manage-metrics`, `manage-findings` and
`manage-lessons`. **Done at the epic level** means: every post-run producer states the population it read,
every post-run verdict is derivable rather than self-reported, the loop from finding → lesson → governing
contract is measured rather than assumed, and an obligation that outlives its plan has a tracker.

⭐ **The epic's own instrument is the honest zero.** Every deliverable here is judged by one question:
after it lands, can a reader tell *"checked and clean"* from *"never looked"*? That is ADR-019 applied to
the machinery that grades us.

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary --slug post-run-quality
     Paste the returned `summary` block verbatim between the markers (the same
     invocation also emits `ordered_queue` for the Ordered Queue section below).
     Anything a reader wants to add BY HAND goes in the annotation zone below,
     outside the markers — never inside them. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: === ▶ **2026-09-21 -- LEDGER RELOCATED (tracked path), PLAN-PRQ-02 SHIPPED, RECONCILED.** Store moved .plan/local/orchestrator/{slug}/ -> tracked .plan/orchestrator/{slug}/ by orchestrator-refactor PLAN-01 (#1557/#1558); this session ported all pass-2 corrections (PRQ-01/03/05/07/10/11) into the tracked tree and dropped the 'local' segment from every spec's Hand-Off Command. PLAN-PRQ-02 (PR #1550) shipped: landing written (landings/PLAN-PRQ-02.md), queue fields stamped, 9 inbox messages dispositioned and archived -- 2 folded into new spec PLAN-PRQ-12 (TOON block-scalar corruption one hop upstream of PRQ-02 D3, plus a tier-gate delivery-integrity gate), 2 folded into PRQ-09 D3 (widened to 3 render-gap shapes), 2 folded as corroborating citations into PRQ-08 D0, 1 confirming citation into PRQ-09 D4, 1 new unowned Open Defect (plan-efficiency-ratios script + scope-creep reconciliation, deliberately lower-priority per its own filing), 1 lesson promoted (2026-09-21-10-001, argparse-rejection recurrence anti-pattern). QUEUE 12 total: PRQ-02 + PRQ-06 shipped / 10 staged (PRQ-01,-03,-04,-05,-07,-08,-09,-10,-11,-12) / 0 running. Inbox empty (33 archived total, 0 queued). At parallelization_scope 1 with R=0, a slot is now OPEN -- PRQ-03 is the queue-order candidate (no blocking dependency; PRQ-01 remains hard-blocked on truthful-signals PLAN-TRUTH-146, PRQ-05 hard-blocked on truthful-signals PLAN-TRUTH-144 running). This reconciliation itself is landing via PR from worktree branch chore/post-run-quality-ledger-relocation with bot review skipped (ledger-only, not reviewable content). ⛔ The old .plan/local/orchestrator/post-run-quality/ tree is ORPHANED -- never read or write it again. ▶ ON RESUME: (a) confirm this reconciliation PR merged and main pulled; (b) run next to emit PRQ-03's hand-off command, checking truthful-signals' queue first per the two hard blocks above. ===
**Phase**: orchestrating
**Inbox (derived)**: 0 queued, 33 archived
**Queue** (staged, in order):
1. PLAN-PRQ-03 (WS-02)
2. PLAN-PRQ-04 (WS-04)
3. PLAN-PRQ-01 (WS-01)
4. PLAN-PRQ-05 (WS-03)
5. PLAN-PRQ-07 (WS-05)
6. PLAN-PRQ-08 (WS-01)
7. PLAN-PRQ-09 (WS-01)
8. PLAN-PRQ-10 (WS-01)
9. PLAN-PRQ-11 (WS-01)
10. PLAN-PRQ-12 (WS-01)
- PLAN-PRQ-02 (WS-01) — plan=retrospective-aspects-publish-verdict — PR 1550 — landing=landings/PLAN-PRQ-02.md — status: shipped
- PLAN-PRQ-06 (WS-04) — plan=prq-06-a-lane-override-that-cannot-take-effect-is — PR 1541 — landing=landings/PLAN-PRQ-06.md — status: shipped
<!-- END GENERATED: resume-summary -->

### Annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated markers.
     A regeneration replaces only what sits BETWEEN the markers, so everything written
     here survives it. -->

- PLAN-PRQ-01 — carries the substance of `truthful-signals` PLAN-TRUTH-152 (itself the merge of
  PLAN-TRUTH-123 + PLAN-TRUTH-130). Its 11 deliverables were re-grounded at transfer; see the transfer
  record under `## Decisions`.
- PLAN-PRQ-05 — carries the substance of `next-level` PLAN-09.
- PLAN-PRQ-07 — operator-directed addendum (not epic-derived like PRQ-01..06). Spans TWO repos: this one
  (relocating `audit-archived-plan-retrospectives`, staging `analyze-marshall-quality`) and a NEW
  `plan-marshall-telemetry` repo the executing plan creates with operator confirmation. See `## Decisions`
  for the split-placement call (folded into this epic as WS-05, not a separate epic).

## Ordered Queue

<!-- GENERATED BLOCK — never hand-write or hand-edit the table between the markers.
     Regenerated from status.json and the staged specs: emitted as `ordered_queue` by
     orchestrator.py resume-summary --slug post-run-quality (paste it verbatim after a queue change),
     and rewritten in place by the compact stage (orchestrator.py compact --slug post-run-quality) at
     cleanup. Only the LIVE queue is rendered here. -->

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-PRQ-03 | WS-02 | staged | .claude/skills/audit-archived-plan-retrospectives/SKILL.md; .claude/skills/audit-archived-plan-retrospectives/checks/; .claude/skills/audit-archived-plan-retrospectives/scripts/audit.py; .claude/skills/recipe-plan-review/SKILL.md; test/plan-marshall/audit-archived-plan-retrospectives/ |
| 2 | PLAN-PRQ-04 | WS-04 | staged | marketplace/bundles/plan-marshall/skills/manage-status/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/**; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md; test/plan-marshall/phase-6-finalize/** |
| 3 | PLAN-PRQ-01 | WS-01 | staged | .claude/skills/audit-archived-plan-retrospectives/SKILL.md; .claude/skills/audit-archived-plan-retrospectives/checks/; .claude/skills/audit-archived-plan-retrospectives/scripts/audit.py; doc/analyzis-cloud-plan/; marketplace/bundles/plan-marshall/skills/manage-findings/**; marketplace/bundles/plan-marshall/skills/manage-references/**; marketplace/bundles/plan-marshall/skills/phase-3-outline/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py; marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/**; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/retro_sections.py; marketplace/bundles/plan-marshall/skills/script-shared/scripts/; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py; marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; test/plan-marshall/audit-archived-plan-retrospectives/; test/plan-marshall/manage-findings/**; test/plan-marshall/plan-retrospective/; test/plan-marshall/plan-retrospective/** |
| 4 | PLAN-PRQ-05 | WS-03 | staged | .claude/skills/finalize-step-lessons-housekeeping/; marketplace/bundles/plan-marshall/skills/manage-lessons/; test/plan-marshall/manage-lessons/ |
| 5 | PLAN-PRQ-07 | WS-05 | staged | .claude/skills/audit-archived-plan-retrospectives/; marketplace/bundles/plan-marshall/skills/finalize-step-analyze-marshall-quality/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/; test/plan-marshall/audit-archived-plan-retrospectives/ |
| 6 | PLAN-PRQ-08 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py; marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/; marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md; marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/references/; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/retro_sections.py; test/plan-marshall/manage-metrics/; test/plan-marshall/plan-retrospective/ |
| 7 | PLAN-PRQ-09 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-tasks/**; marketplace/bundles/plan-marshall/skills/plan-retrospective/references/; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/retro_sections.py; test/plan-marshall/plan-retrospective/ |
| 8 | PLAN-PRQ-10 | WS-01 | staged | doc/user/configuration.adoc; marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md; marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md; marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_patterns.py; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/self_review.py; test/plan-marshall/phase-6-finalize/; test/pm-plugin-development/ext-self-review-plan-marshall/ |
| 9 | PLAN-PRQ-11 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/plan-retrospective/references/; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/; test/plan-marshall/plan-retrospective/ |
| 10 | PLAN-PRQ-12 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/plan-retrospective/references/chat-history-analysis.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/extract-chat-signal.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_chat_signal_reducer.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_claude_runtime_impl.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/antigravity_runtime.py; marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/opencode_runtime.py; marketplace/bundles/plan-marshall/skills/ref-toon-format/scripts/toon_parser.py; test/plan-marshall/plan-retrospective/test_extract_chat_signal.py; test/plan-marshall/platform-runtime/ |
<!-- END GENERATED: ordered-queue -->

### Queue annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated table markers. -->

- **Scope is 1 — strictly sequential** (operator decision at init). Most of this corpus shares
  `plan-retrospective/**`, so the disjointness gate would serialize the majority regardless; the knob
  makes that explicit rather than discovered per round.
- PLAN-PRQ-01 ↔ PLAN-PRQ-02 — both touch `plan-retrospective/scripts/`; never pair.
- PLAN-PRQ-03 is the only spec whose surface is entirely project-local (`.claude/skills/`), so it is the
  natural partner if the scope knob is ever raised.
- PLAN-PRQ-07 ↔ PLAN-PRQ-01, PLAN-PRQ-03 — both touch `.claude/skills/audit-archived-plan-retrospectives/**`,
  the exact skill PRQ-07 relocates out of this repo. PRQ-07 is a hard DEPENDENCY on both landing first, not
  a mere disjointness overlap — never emit PRQ-07 while either is staged/launched/running.
- PLAN-PRQ-07 ↔ PLAN-PRQ-04, PLAN-PRQ-06 — conditional overlap on `phase-6-finalize/**`, pending whether
  PRQ-07's finalize step lands marketplace-bundled (HYPOTHESIS, verify-at-outline in its spec).

## Decisions

- 2026-09-17 — **Epic created, and it OWNS the subject end to end.** Operator decision at init, chosen
  over two alternatives: (a) staging only unowned aspects and leaving the subject split across three
  ledgers, and (b) a narrower retrospective-plus-audit cut. Rationale: a single ledger cannot see a
  duplicate held in another ledger, and this subject was already split three ways — the split is what let
  the same defect class (a producer publishing a confident figure over an unread population) be
  re-discovered independently in `truthful-signals`, `next-level` and `code-intelligence-substrate`.
- 2026-09-17 — **`parallelization_scope: 1`** (operator). Surface concentration, as recorded in the queue
  annotations above.
- 2026-09-17 — **Two transfers IN, and they are transfers rather than offers.** `truthful-signals`
  PLAN-TRUTH-152 → `PLAN-PRQ-01`; `next-level` PLAN-09 → `PLAN-PRQ-05`. Each source spec is retired in
  its own ledger with a pointer here, and its substance is carried in the receiving spec — not merely
  named. ⛔ **A mechanical limitation is recorded with them**: `orchestrator.py queue --transition` accepts
  only `staged|launched|running|parked|shipped|landed`, so the historical `transferred` status the ledgers
  already contain **cannot be written by the sanctioned verb**. The source rows are therefore `parked`
  with the transfer recorded in narrative. This is exactly `truthful-signals` PLAN-TRUTH-143 D9 ("the
  queue's single-row writer cannot write three statuses the ledger already holds") — first-party evidence
  for it, recorded here rather than re-staged.
- 2026-09-17 — **Reviewer-quality measurement stays with `review-apparatus`.** `finalize-step-review-retrospective`
  grades PR reviewers, and the standing three-way routing rule gives anything PR-review to that epic —
  the PR test wins outright. This epic owns the *plan-side* post-run surfaces and consumes the reviewer
  signal; it does not own it. ⚠ One seam sits exactly on that boundary and is named in PLAN-PRQ-04 rather
  than silently claimed: `review_completeness`'s `bot_states` classification has no persisted handoff an
  `order: 990` step can read, so the zero-findings grade fails closed to `indeterminate`.

- 2026-09-17 — **`lessons-capture` must be off when configured off; the mechanism is reclassification off
  the floor class.** Operator ruling, in two parts: the outcome (*"lessons capture should be off if
  configured off"*), then the mechanism, chosen from three with their blast radii stated. Rejected: a
  per-element immunity opt-out (would have changed the `ext-point-lane-element` contract every lane element
  inherits) and reclassify-plus-pinned-tier (would have preserved today's minimal-profile behaviour at the
  cost of a class declaration that no longer means what it says). ⚠ **Accepted side effect**: a non-immune
  class defaults to tier `standard`, so `lessons-capture` will also stop running under an
  `execution_profile: minimal` plan with no override at all — a change every consumer inherits on upgrade.
  PLAN-PRQ-06 D3 carries the ruling and D4 pins the side effect with a control. ⛔ The immunity rule itself
  is CORRECT and stays — it is the element's classification that was wrong.

- 2026-09-19 — **Inbox drain: 23 `PLAN-PRQ-06` messages, 13 distinct signals, all dispositioned and
  archived.** Discard (3, already tracked/owned elsewhere): orchestration-detection (this epic's own new
  Open Defect, forwarded to `truthful-signals` as `post-run-quality-001.md`); `record-dispatch-boundary`
  (`PLAN-PRQ-08`'s existing claim); agent-initiated-re-dispatch (`code-intelligence-substrate`
  `PLAN-CIS-052` D7-D10 + shipped `PLAN-CIS-035`). Fold (5): 2 into `PLAN-PRQ-02` (D3's second corrupted
  aspect; D1's second defect + new claim, the `forwarded_to_manifest` dead-letter), 3 into `PLAN-PRQ-09`
  (D4's third denominator-pollution class; two NEW claims — script-failure misclassification,
  wait-time-rollup honesty — split out to `PLAN-PRQ-11` per the scope-bloat guard rather than pushing
  PRQ-09 to 8 deliverables). Stage (1 signal → 2 specs): **`PLAN-PRQ-10`** (finalize re-fire convergence +
  self-review coverage honesty — the self-review standard's own `:222` deferral of a per-detector reach
  map is directly challenged, with the registry named that undercuts its feasibility premise) and
  **`PLAN-PRQ-11`** (spend/diagnostic-tier population miscounts, split from PRQ-09). Promote (4): new
  corpus lessons `2026-09-19-21-003`..`-006` — co-reference-population fix scoping, only/all/none
  claim-scope discipline, verify-the-gate-before-writing-the-deliverable, mock-insulates-a-boundary.
  Lesson `2026-09-19-12-001` (duplicate of the PRQ-10 payload) superseded, redirecting to PRQ-10.
  Two further residuals (executor path-scoping, executor diagnostics, phase-5-yield-reason) forwarded to
  `code-intelligence-substrate` as `post-run-quality-001.md`. ⚠ **Correction**: the live lessons corpus was
  found to be ~4-6 entries during this drain, not the 172 an earlier resume_anchor claimed — confirmed
  legitimate (860+ surviving tombstones), drained by other activity between 2026-09-18 and 2026-09-19, not
  a wipe; this epic did not cause and does not own that drain.
- 2026-09-19 — **PLAN-PRQ-06 SHIPPED** — PR #1541 (`a1dd4901f`), merged via merge queue, 10 self-review
  rounds, one real CodeRabbit fix-task loop-back (3 findings), 9.56M tokens / 34h wall / 6h10m worked.
  `landings/PLAN-PRQ-06.md` is the full reconciliation record. `emit-landing` never fired (see the new
  Open Defect below) — reconciled from the operator's paste, verified against the merge commit, PR state
  and the archived plan directory before recording anything.
- 2026-09-18 — **PLAN-PRQ-06 launched** (operator confirmation, "plan 006 started"); `staged → launched`.
- 2026-09-18 — **Inbox drain: `truthful-signals-001.md`.** Forwarded 2 lessons at the end of that epic's
  own corpus sweep. Folded lesson `2026-09-15-08-003` (oversized plan, no pre-execution anchor check) into
  `PLAN-PRQ-08` D4 — same clock as the post-merge check D4 already covered, one phase earlier — with the
  Expected Surface updated in the same act (`phase-4-plan/SKILL.md`, verified via `corpus surfaces`).
  Discarded lesson `2026-09-18-06-001` (the restored "verify a handed claim" standing rule) from further
  corpus-work consideration: `PLAN-PRQ-09` D5 already owns writing the governing clause it asks to be
  preserved as, so landing D5 resolves the tension the forwarding message raised without a second action.
- 2026-09-18 — **Cleanup A1/A4 (corpus set-verdict + duplication cross-check), `checked_at: 1605831c5`.**
  Dispatched `execution-context-level-5` to re-ground all 9 staged specs' Claim Labels against HEAD: 37
  rows, 21 corroborated / 6 contradicted / 10 unverifiable; all 36 addressable verdicts persisted (0
  blocking). Applied 5 `rescoped: yes` corrections in place (PRQ-01, PRQ-02 ×2, PRQ-03, PRQ-04, PRQ-09) —
  see each spec's Claim Labels for the verdict lines and the inline corrections. Also added PRQ-08's
  missing never-retry-`remove`-on-`not_found` guard (safety, PRQ-09 already carried it). **A4 duplication
  cross-check**: 0 within-epic duplicates (this epic's own 9 specs are mutually disjoint in subject); 4
  `source_origin_matches` are the two already-recorded, already-reconciled transfers (PRQ-01←truthful-signals,
  PRQ-05←next-level); 852 `file_overlap_matches`, the overwhelming majority against `code-intelligence-substrate`
  plans that are already `shipped` (moot — historical surface, not a live collision) or against broad
  recursive test-mirror globs (`test/plan-marshall/plan-retrospective/**` etc., structural over-declaration
  noise per the gate's own documented residual-error classes) — no new supersede action warranted. One
  live, modest overlap worth a Watch: `code-intelligence-substrate` `PLAN-CIS-050` (staged, 14
  deliverables) shares several `plan-retrospective` scripts with PRQ-01; different epic's business, noted
  rather than resolved here.
- 2026-09-17 — **WS-05 / PLAN-PRQ-07 added: cross-repo telemetry, folded into this epic rather than split
  into a new one.** Operator-directed addendum: a new `plan-marshall-telemetry` repo, its `transfer` and
  `analyze` project-level skills, a new `analyze-marshall-quality` finalize step here, and relocating
  `.claude/skills/audit-archived-plan-retrospectives` into the telemetry repo. Two placement questions were
  put to the operator and both were answered: (1) new epic vs. new workstream here — **workstream**, on the
  thematic overlap (this epic already owns "everything this project does to judge a run after it has
  finished"); (2) one plan vs. two (repo+transfer, then analyze+finalize+migration) — **one plan**, kept
  under the ~6-deliverable split guard at 5 deliverables. ⛔ PRQ-07 carries a hard sequencing dependency on
  PRQ-01 and PRQ-03 (both edit the skill PRQ-07 relocates) recorded in its own spec and in the queue
  annotations above — this is NOT a mere disjointness overlap the `next` gate would otherwise catch on its
  own, since PRQ-01/03 sit in WS-01/WS-02 and the gate reasons per-surface, not per-dependency-chain.

- 2026-09-17 — **Lessons-corpus sweep: 16 candidate lessons analyzed against this epic's scope.** 8 moved
  into `archive/lessons/{id}.md` and incorporated into Open Defects (below); 2 removed outright as
  duplicates of already-staged PLAN-PRQ-02 deliverables (D2, D3); 6 left untouched — their subject is
  `review-apparatus` (reviewer-quality metrics, review-pipeline carry-forward discipline) or fleet-wide
  orchestrator mechanics (spec staleness, inbox-detect argparse), not this epic's. All 10 removed lessons
  carry a `completely_covered` tombstone in `.plan/local/lessons-learned/.tombstones/` pointing back at
  either the archive copy or the covering PRQ-02 deliverable. Two corpus entries (`2026-09-08-22-006/-007`)
  surfaced a `list`/`get` inconsistency and were deliberately left untouched — see Watches.

- 2026-09-21 — **Cleanup pass 2 (restart preparation), `checked_at: e8a71650`.** Dispatched A1
  corroboration across the 10 non-`PLAN-PRQ-02` specs (that one excluded — actively launched/running).
  22 claims corroborated (19/3 corroborated/contradicted), 0 blocking. Five specs corrected in place:
  `PLAN-PRQ-01` (restored the source's hard `PLAN-TRUTH-146` dependency and a dropped Expected Surface
  glob, both softened/lost at the 2026-09-17 transfer), `PLAN-PRQ-05` (corpus size has moved ~5× since
  staging — flagged as must-re-derive, not trust; `PLAN-TRUTH-144` moved `staged → RUNNING`, hardened
  from a theoretical collision to a live block), `PLAN-PRQ-07` (wrong citation for the archived-plans
  layout), `PLAN-PRQ-10` (registry population corrected from 5 to 6 content classes; D1 narrowed to two
  of its three proposed shapes, the third refused by the finalize-step facts contract; D0(b)'s Expected
  Surface pointed at the wrong file for `CANDIDATE_LISTS`; three more cross-epic collisions declared —
  `truthful-signals` `PLAN-TRUTH-173`/`-167` and `review-apparatus` `PLAN-PR-074`, all staged, all
  touching the same self-review files no single gate can see across three ledgers), `PLAN-PRQ-11` (D1's
  premise materially refuted — the partition it proposed to add already exists in the classifier; narrowed
  to publishing it plus one further subtype split). A4: 0 new within-epic duplicates; one missing overlap
  note added to `PLAN-PRQ-11`. This is the SECOND time a corroboration pass has found and corrected a
  transfer-softened dependency and a dropped Expected Surface entry (`PLAN-PRQ-01`) — worth naming as a
  pattern: a spec TRANSFER is not merely a copy, and each one needs its own re-grounding pass rather than
  being trusted as verbatim.

- 2026-09-21 — **Ledger store relocated to a tracked address; PLAN-PRQ-02 landed and reconciled.**
  `orchestrator-refactor` PLAN-01 (PR #1557/#1558, landed on `main` ahead of this reconciliation) moved
  the orchestrator store from the git-ignored `.plan/local/orchestrator/{slug}/` to the git-tracked
  `.plan/orchestrator/{slug}/` — this epic's canonical tree is now version-controlled. The migration
  landed from a snapshot taken BEFORE cleanup pass 2 completed, so this epic's tracked copy briefly
  diverged from the pass-2-complete content that remained only in the old, now-orphaned local path;
  reconciled here by porting every pass-2 correction (specs `PLAN-PRQ-01/03/05/07/10/11`, this Decisions
  entry) into the tracked tree and updating every spec's `Hand-Off Command` path to drop the `local`
  segment. `PLAN-PRQ-02` (retrospective-aspects-publish-verdict, PR #1550) shipped in the same window;
  its landing (`landings/PLAN-PRQ-02.md`) and inbox drain are reconciled in this same pass — see the
  landing record for the 9-message disposition. This reconciliation itself runs inside a worktree on
  branch `chore/post-run-quality-ledger-relocation`, landed via its own PR with bot review skipped (a
  ledger-only relocation, not reviewable content) — the pattern PLAN-01 itself established for its own
  landing. The old `.plan/local/orchestrator/post-run-quality/` tree is now ORPHANED — do not read or
  write it going forward.

## Open Defects

- **The census does not census itself.** `audit-archived-plan-retrospectives` SKILL.md:231-236 states it
  outright — the suspect-zero census is excluded from its own population, "the detector-inside-its-own-
  population failure mode, standing unresolved in the instrument built to surface it." — source: inventory
  sweep 2026-09-17. ⇒ Owned by PLAN-PRQ-03.
- **Deterministic computation sited in retrospective reference prose instead of a script.** Filed 2026-09-21
  (inbox `retrospective-aspects-publish-verdict-007.md`, actions #1/#2 — action #3 already folded into
  `PLAN-PRQ-09` D4). Two members: (1) `references/plan-efficiency.md` Sections 1-2 compute four ratios
  against a 35-row static anchor table entirely in prose, with three separate arithmetic-hazard warnings
  (ms-vs-seconds, string-typed plan-level keys silently defeating `max(denominator, 1)`, numerator must be
  worked not wall time) that exist only because the computation lives in a doc instead of code; (2)
  `request-result-alignment`'s scope-creep set-difference re-derives by hand what `manage-references`
  already ships as a three-way (declaration/structured-derivation/realized-footprint) reconciliation — on
  this run the hand computation and the existing reconciliation returned different-but-both-correct figures
  (8 vs 10 creep paths) for a legitimate reason (differing read-intent declarations), which is exactly the
  second-producer risk `plan-efficiency.md` itself warns against for denominators. ⇒ **Unowned** — the
  filing message itself frames this as lower priority than its action #3; no spec staged.
- ✅ **RESOLVED-AS-REFUTED 2026-09-17, and re-staged on its true mechanism as `PLAN-PRQ-06`** (operator
  reported the same observation independently; analyzed the same day). The entry as filed read: *"either
  the lane resolution does not drop a non-ceremony step at `off`, or the landing's step list is not
  derived from the composed manifest."* ⛔ **BOTH readings are refuted**, and the refuting evidence is
  retained here per the standing convention:
  - `_manifest_lanes.py:171-172` + `:37` — an `off` on a `core` / `derived-state` element is **immune by
    contract**, documented in `ext-point-lane-element.md:50-51, 70, 90`. `lessons-capture` declares
    `lane.class: core`, the same class as `push` / `create-pr` / `branch-cleanup`.
  - The archived plan's `execution.toon` composed the step (lines 33, 84, 118) and recorded it `executed`
    (line 158); its `logs/decision.log` entry `4a5900` carries the neutralization warning verbatim. **The
    landing told the truth.**
  ⇒ The real defect is that the neutralization is invisible to the operator — both config writers validate
  the lane value space and never read the element's class, and the one honest record is a compose-time log
  line inside a plan directory that is then archived. Owned by **PLAN-PRQ-06**.
  ✅ **SHIPPED 2026-09-19, PR #1541 (`a1dd4901f`).** All 7 deliverables (D0-D4, D3a, D2a) landed —
  write-side refusal, read-side surfacing, `lessons-capture` reclassified `core → prunable` (the
  2026-09-17 operator ruling), and the manifest now carries the effective lane with the requested value
  preserved separately. See `landings/PLAN-PRQ-06.md` for the full reconciliation.
- ⛔ **NEW 2026-09-19 — orchestration detection fails open for a plan with no `source_id`.** Confirmed
  first-party on `PLAN-PRQ-06`'s own landing: its `request.md` carries no `source_id` section, so whatever
  detector `emit-landing` consults for the orchestration verdict answered a confident "not orchestrated"
  rather than "indeterminate" — `emit-landing` never fired, and this epic never received its landing
  notification. 23 messages (10 retrospective-lesson observations + 13 lessons-capture findings) had to be
  filed to this epic's inbox manually as a workaround. Same shape as corpus lesson `2026-09-09-06-001`
  ("orchestrator inbox detect cannot be called for a plan with no source_id, which is every
  description-sourced plan"), which the 2026-09-17/18 lessons sweep correctly excluded as fleet-wide
  orchestrator-mechanics — this entry is NOT a reversal of that call, it is a second, costlier instance of
  the same excluded defect, recorded here because it directly hit this epic's own pipeline. ⇒ **Unowned by
  this epic** — the fix belongs wherever orchestrator-platform mechanics live (`truthful-signals`, on
  precedent), not staged here.
- **An obligation that outlives its plan has no owner.** `truthful-signals` epic.md records four owed
  `architecture enrich insight` calls whose owning plan was archived before they were issued, against a
  git-TRACKED file — "the obligation has no owner" — and a deferred `marshalld` reconcile marked
  `owed: true` that nothing re-checks. — source: `truthful-signals` epic.md D-087-e / D-087-f. ⇒ Owned by
  PLAN-PRQ-04.
- **`recipe-plan-review` persists nothing.** An LLM-only request-vs-landed re-check whose result exists
  only in the session that ran it, so no corpus question can ever be asked of it. — source: inventory
  sweep. ⇒ Owned by PLAN-PRQ-03 D0's population.
- **No mechanical achieved-thoroughness measurement exists** (`plan-retrospective/SKILL.md:215`) — the
  achieved side of coverage is a floor-graded self-report. — source: inventory sweep. ⇒ Unowned; candidate
  for a later PRQ spec, deliberately not folded into PLAN-PRQ-01 to keep its 11 carried deliverables from
  growing.

### Moved in from the global lessons corpus (2026-09-17)

> ⛔ **RECONCILED 2026-09-17 after a concurrent-session collision.** Two orchestrator sessions swept the
> corpus against this epic at the same time. The entries below were written by one of them; the other
> staged `PLAN-PRQ-08` / `PLAN-PRQ-09` and consolidated the archive. **Each entry now names its owning
> spec** — per this document's own contract, a defect folded into a plan spec is owned there and is no
> longer an unowned Open Defect:
>
> - handed-claim restated as fact (`2026-08-27-16-003`) ⇒ **PLAN-PRQ-09 D5**
> - producerless `SECTION_SPEC` row (`2026-08-31-09-001`) ⇒ **PLAN-PRQ-09 D3**
> - `affected_files_recall` denominator (`2026-09-03-23-004`) ⇒ **PLAN-PRQ-09 D4**
> - plan-level recall hides a 67% deliverable (`2026-09-05-07-006`) ⇒ **PLAN-PRQ-09 D4**
> - footprint resolver has no landed-commit tier (`2026-09-04-08-004`) ⇒ **PLAN-PRQ-02 D1**
> - lesson-creation Gate 2 blind population (`2026-09-03-23-006`) ⇒ **PLAN-PRQ-05**
> - manifest order inverted (`2026-09-04-08-001`) and the deep-lane assessment gap ⇒ ⚠ **still unowned**;
>   both are the other session's classification and neither is folded into a spec yet.
>
> The full disposition table, including which session retired which lesson and under which verdict, is
> `lessons/README.md`.

Eight lessons analyzed against this epic's scope, moved into `archive/lessons/{id}.md` (this epic's own
tree), incorporated below, and tombstoned in the global corpus as `completely_covered` pointing back here.
Two further lessons (`2026-09-04-08-003`, `2026-09-13-20-004`) were duplicates of already-staged
deliverables and were tombstoned directly without an archive copy — see the tombstones at
`.plan/local/lessons-learned/.tombstones/` for their covering clauses. Six other candidates that matched on
keyword but not on subject (reviewer-quality metrics, qgate reopen, orchestrator-mechanics bugs) were left
untouched in the corpus — their territory is `review-apparatus` or fleet-wide orchestrator mechanics, not
this epic's.

- **A defect claim handed to a retrospective is restated as fact without verification.** A dispatch-context
  claim asserted the lessons corpus was filing body-less stubs; a one-call census refuted it (6 of 6
  lessons carried full bodies). Standing rule: treat a supplied defect claim as a hypothesis with a named
  verification, never as a finding — derive a set property, don't restate it. — source:
  `archive/lessons/2026-08-27-16-003.md` (also `lessons/2026-08-27-16-003.md` in the peer session's
  consolidated archive). ⇒ Owned two ways, not in conflict: **PLAN-PRQ-09 D5** carries the defect half
  (verify before filing), and the standing rule itself was **RESTORED to the live lessons corpus as
  `2026-09-18-06-001`** by the peer session with operator approval — it is agent-facing guidance, not a
  work item, so it belongs where sessions recall it rather than only in a staged spec. My original
  `completely_covered` retirement of `2026-08-27-16-003` is superseded by that restoration; see
  `lessons/README.md` for the full record, including the peer's flag that my ten `completely_covered`
  tombstones (this one and nine siblings below) assert the rule now lives in a codified clause when in
  fact it lives in a staged, not-yet-implemented spec — a fair correction I cannot retract (no tombstone
  edit path exists) but record here so it is not read as settled coverage.
- **A producerless `SECTION_SPEC` row is an operator proposal, not an in-plan decision.** When a
  `plan-retrospective` row's renderer is live but its producer does not exist, record both options
  (register vs. delete) with a recommendation and escalate — deciding it in-plan silently settles an
  architecture question (whether the compiler stays a pure assembler) as a side effect. Observed twice
  (`_executive-summary`, `dispatch_boundaries`); both escaped four self-review rounds and 42/42 mutation
  kills because the row reads as benign in every report. — source: `archive/lessons/2026-08-31-09-001.md`.
  ⇒ Governance constraint on PLAN-PRQ-02 D0: if D0's 16-aspect sweep finds a producerless row, escalate it,
  don't fix it in-plan.
- **`affected_files_recall`'s denominator excludes read-intent only, not delete-intent or foreign-checkout
  declarations.** A plan that correctly deleted a file or wrote to another repository is scored down for
  it — `recall_pct: 89.5` on a plan whose per-deliverable coverage was 96-100%. The by-construction argument
  `request-result-alignment.md` already states for the read case applies verbatim to the other two classes
  but was never generalised. — source: `archive/lessons/2026-09-03-23-004.md`. ⇒ Feeds PLAN-PRQ-02 D0 as a
  fourth population-denominator instance (alongside D1-D3).
- **Plan-level `affected_files_recall` hides a deliverable that shipped two thirds of its declared sites.**
  The check unions every deliverable's declared surface, so one deliverable at 67% (the one whose title
  asserted completeness) is invisible inside a plan-level 86%. Real cost: a same-day follow-up commit was
  needed post-merge. — source: `archive/lessons/2026-09-05-07-006.md`. ⇒ Feeds PLAN-PRQ-02 D0 as a fifth
  instance (granularity, not exclusion-class).
- **The composed manifest ran `plan-retrospective` (order 995) before `lessons-capture` (order 991), so the
  once-per-run orchestration verdict was never resolved before its first consumer.** Verified three ways
  (declared frontmatter order, the composed manifest's actual step order, the execution log). Root cause
  located at compose time but NOT established — two leads named, neither tested. — source:
  `archive/lessons/2026-09-04-08-001.md`. ⇒ **Unowned** — new defect, not covered by any staged PRQ. A
  candidate for a future PRQ spec or a PLAN-PRQ-04 D0 population member (it is an obligation-adjacent
  ordering defect, but the mechanism is orchestration compose, not archival).
- **The footprint resolver has no landed-commit tier, so a post-merge or archived-plan retrospective cannot
  resolve a footprint once the worktree is gone.** `branch-cleanup` destroys the resolver's only evidence
  source before `plan-retrospective` runs; every `RESOLVING_TIERS` member is worktree-bound. Proposed fix:
  add a tier that diffs the merge commit against its first parent. — source:
  `archive/lessons/2026-09-04-08-004.md`. ⇒ Cross-referenced from PLAN-PRQ-02 D1 (same resolver file,
  `_cmd_compute_footprint.py`) **and** PLAN-PRQ-07 (the telemetry `analyze` engine needs this exact tier to
  measure archived plans whose worktree has been gone for months — this lesson is the first-party evidence
  that the gap is real and already load-bearing on live plans, not merely a future concern for PRQ-07).
- **The deep planning lane records no per-file assessments, so `outline-vs-shipped` measures against an
  empty denominator.** A 12-deliverable, 100 KB deep-lane outline left `assessments_store_present: false`;
  the aspect degraded honestly (published its zero denominators) rather than faking a pass, which is why
  this is a measurement gap rather than a false green. — source: `archive/lessons/2026-09-15-08-007.md`.
  ⚠ **POSSIBLE DUPLICATE of PLAN-PRQ-01 D8 ("Close the outline write-back gap")** — verify-at-outline
  whether D8 already subsumes the write-back-never-happens case before treating this as separate work.
- **Gate 2 of lesson creation cannot read a worktree-resident plan's scope from the main checkout, so it
  silently under-covers.** `manage-plan-documents request read` (unlike `manage-findings`'s five read
  verbs) has no `--any-checkout` fallback, so Gate 2's covering-plan check ran against 2 of 5 active plans
  on first observation and 2 of 6 on a ten-day-later recurrence — unfixed and reproducing identically. The
  recurrence adds a sharper finding: the failing call's `suggestions[]` recommend creating a duplicate
  request document that already exists in the other checkout. — source:
  `archive/lessons/2026-09-03-23-006.md`. ⇒ New candidate deliverable for PLAN-PRQ-05 (lessons corpus
  provenance and quality) — Gate 2 is exactly the epic's own "verdict over an unread population" archetype,
  applied to the lessons corpus's own filing gate.

## Watches

- **CI-wait behaviour needs an operator call, not a fold.** From the 2026-09-19 inbox drain:
  `ci_complete_precondition`'s early-negative return path (return immediately when the precondition
  cannot possibly resolve — no run started, SHA mismatch) and its ~600s poll budgets (95%+ of the harness
  ceiling) are `phase-6-finalize`/CI-behaviour changes, not post-run measurement — outside this epic's
  territory, and the standing PR/CI routing rule does not cleanly decide an owner. Neither staged nor
  forwarded; recorded here pending an operator decision on where it belongs.
- **Post-run verification is an operator option, not a precondition.** `doc/analyzis-cloud-plan/README.adoc:606`
  calls making it a precondition "the highest-value change in the set and it is not close." No plan here
  claims it yet — it is an execution-lifecycle change, not a post-run-producer change. — re-check when
  PLAN-PRQ-01 and PLAN-PRQ-02 have landed and the producers are trustworthy enough to gate on.
- **Landed claims decay and nothing re-checks them** (`README.adoc:615`, recommendation #5, explicitly
  "the one recommendation that is not about the cloud lane"). — re-check at the next corpus audit.
- **1 of 5 recorded process lessons reached the governing contract** (`test-quality.adoc:738-755`). That
  ratio is the epic's headline outcome metric for the learning half. — re-check after PLAN-PRQ-05 lands.
- **`manage-lessons list` and `get` disagree on two corpus entries.** During the 2026-09-17 lessons sweep,
  `2026-09-08-22-006` and `2026-09-08-22-007` both listed as `active` with **empty `component`/`category`**
  under `list` (and `list --status all`), but `get --lesson-id` returned `not_found` for both. ⛔ **Neither
  was touched** — `manage-lessons remove` has a recorded failure mode of destroying a lesson while
  returning `not_found`, so a retry on `not_found` risks a second destructive loss; this epic's own
  PLAN-PRQ-05 Claim Labels already carry that exact warning verbatim. Left in the corpus, unremoved,
  unarchived. — re-check as first-party evidence for PLAN-PRQ-05 D1/D2 (a corpus entry `list` can see but
  nothing else can safely read or act on is precisely a precision/provenance defect); do not attempt
  `remove` on either id outside a plan that has read `manage-lessons remove`'s failure-mode documentation
  first.
- **`plan-retrospective` reads an unclosed accumulator** (SKILL.md:133-167, "R2"), worked around by a
  `manage-metrics generate` reconcile at Step 2.5 because `record-metrics` (998) cannot move earlier. —
  re-check whether PLAN-PRQ-02's population derivation makes the workaround removable.
