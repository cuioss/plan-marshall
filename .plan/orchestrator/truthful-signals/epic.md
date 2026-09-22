# Epic: Truthful Signals & Machinery Integrity

slug: truthful-signals

> Ledger document for one epic under `.plan/local/orchestrator/truthful-signals/`. The layout and
> authority contract live in the central standard — see
> `persona-marshall-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.
>
> **Live state only.** Shipped plans live in `landings/`; resolved defects, absorbed plans, and
> settled questions are removed rather than annotated.

## Cloud bridge

Plans from this epic may be executed in the standalone cloud lane instead of the plan-marshall
lifecycle. The mapping between this epic's plan specs and those cloud plans, and the rule for
creating, syncing, and collecting them, are in [`cloud-bridge.md`](cloud-bridge.md).

Read it before staging work for the cloud and before ingesting a landed cloud plan.

## Vision

Close the recurring defect family in which a tool, gate, or hand-off reports a confident
clean/complete signal while silently suppressing the caveat that makes it wrong — plus the adjacent
family in which machinery silently loses information it was handed. Fix each instance at the tool
layer rather than papering over symptoms. Done at the epic level means: every staged plan shipped or
explicitly retired, no open instance of the flagship archetype, and the closing rename (PLAN-TRUTH-015)
landed.

2026-09-21: `quality-aspect` (the finalize-lane instance of this same defect archetype)
merged in. Its 15 live plans joined this queue, renumbered PLAN-205..221 as workstreams
`WS-QA-01` through `WS-QA-09`. Its terminal history (3 shipped rows, renumbered
PLAN-204/210/212) and quality-aspect's own `history.md` are in the
`truthful-signals-26-09-21` archive, alongside this epic's own 196 terminal rows split
out on the same date.

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator resume-summary --slug truthful-signals
     Paste the returned block verbatim between the markers. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: === ▶ 2026-09-22 -- FULL CLEANUP RAN (A1 targeted re-ground, A3 clean, A4 found+FIXED 15x stale quality-aspect headers, A2/A5 no findings, Phase B compacted, Phase D restart-check). ⛔ PLAN-TRUTH-167 D3's base-ref HYPOTHESIS REFUTED by PR #1559 (fca06c4ca) -- claim 5 now contradicted+rescoped:no, spec is BLOCKED from next emission until re-scoped (narrower residue: merge-commit re-derivation, not upstream-base -- see spec's own FOLDED 2026-09-22 note). PLAN-TRUTH-173 claim 0 evidence updated (20->21 detectors, conclusion unchanged). A4: all 15 PLAN-2xx specs had dead quality-aspect Hand-Off Commands (quality-aspect is ARCHIVED, path never resolved) -- FIXED epic: field + hand-off path on all 15. Mid-drain: instrumentation-substrate declined 2 forwarded lessons (no matching population), restored to corpus as 2026-09-22-08-001/-002 (W-2026-09-22-a). ▶ QUEUE: 44 rows unchanged, N=1 R=0. NEXT EMIT TARGET CHANGED: PLAN-TRUTH-161 still confirmed disjoint+prep-ready (untouched by this pass); do NOT emit PLAN-TRUTH-167 until D3 re-scoped. RESTART VERDICT: NOT_READY -- worktree carries 59+ uncommitted paths across 5 epics (truthful-signals this session's own edits + orchestrator-refactor/lessons-routing pre-existing from before this session + cross-notice deliveries to instrumentation-substrate/code-intelligence-substrate/review-apparatus/test-quality/lessons-routing). Operator must decide commit scope before a fresh session can safely resume from a clean tree. Inbox genuinely empty (0 queued). A5 (distribution regroup) still declined -- 44-spec redistribution needs its own dedicated pass. ⛔⛔ PLUGIN PIN GAP STILL OPEN, OPERATOR-ONLY. ===
**Phase**: orchestrating
**Inbox (derived)**: 0 queued, 1144 archived
**Parked**:
- PLAN-TRUTH-156 (WS-01)
- PLAN-TRUTH-158 (WS-01)
- PLAN-TRUTH-159 (WS-01)
- PLAN-TRUTH-163 (WS-01)
- PLAN-TRUTH-164 (WS-01)
**Queue** (staged, in order):
1. PLAN-TRUTH-145 (WS-01)
2. PLAN-TRUTH-146 (WS-01)
3. PLAN-TRUTH-147 (WS-01)
4. PLAN-TRUTH-149 (WS-01)
5. PLAN-TRUTH-150 (WS-01)
6. PLAN-TRUTH-151 (WS-01)
7. PLAN-TRUTH-153 (WS-01)
8. PLAN-TRUTH-154 (WS-01)
9. PLAN-TRUTH-155 (WS-01)
10. PLAN-TRUTH-160 (WS-01)
11. PLAN-TRUTH-161 (WS-01)
12. PLAN-TRUTH-162 (WS-01)
13. PLAN-TRUTH-165 (WS-01)
14. PLAN-TRUTH-167 (WS-01)
15. PLAN-TRUTH-168 (WS-01)
16. PLAN-TRUTH-169 (WS-01)
17. PLAN-TRUTH-170 (WS-01)
18. PLAN-TRUTH-171 (WS-01)
19. PLAN-TRUTH-172 (WS-01)
20. PLAN-TRUTH-173 (WS-01)
21. PLAN-TRUTH-174 (WS-01)
22. PLAN-TRUTH-175 (WS-01)
23. PLAN-TRUTH-176 (WS-01)
24. PLAN-TRUTH-177 (WS-01)
25. PLAN-205 (WS-QA-01)
26. PLAN-206 (WS-QA-02)
27. PLAN-207 (WS-QA-02)
28. PLAN-208 (WS-QA-03)
29. PLAN-209 (WS-QA-03)
30. PLAN-211 (WS-QA-04)
31. PLAN-213 (WS-QA-06)
32. PLAN-214 (WS-QA-06)
33. PLAN-215 (WS-QA-06)
34. PLAN-216 (WS-QA-07)
35. PLAN-217 (WS-QA-07)
36. PLAN-218 (WS-QA-09)
37. PLAN-219 (WS-QA-08)
38. PLAN-220 (WS-QA-08)
39. PLAN-221 (WS-QA-02)
<!-- END GENERATED: resume-summary -->

### Annotations

> Hand-written, OUTSIDE the generated markers. Evacuated here by cleanup Rule 2 during the
> 2026-08-22 cloud-run ingestion: this line had been written INSIDE the `resume-summary` block,
> where the generator owns every byte and would overwrite it on the next pass.

**On the resume anchor.** `status.json.resume_anchor` is the machine authority. The generated block
above renders it VERBATIM, which is the contract; this note exists so the reason the anchor is not
*also* hand-summarised here survives a regeneration. Read the anchor from the block above or with
`orchestrator resume-summary --slug truthful-signals` — never from a second, hand-maintained copy.
PLAN-TRUTH-074 D8 owns the anchor-shape question and is the plan that introduced these markers.

> ⚠ **Known contract deviation, operator decision owed.** The persist contract says this block is
> generated and never hand-written, and that `resume-summary`'s output is pasted verbatim. It is not:
> the anchor is replaced by a pointer (pasting a ~12 KB anchor into `epic.md` would duplicate the machine
> authority), and per-row annotations were moved OUT of this block into the Ordered Queue table rather
> than hand-maintained inside it. **The block above is now restricted to status.json-derivable facts**, so
> the deviation is narrowed to the anchor pointer alone. Resolve by either teaching `resume-summary` to
> emit the pointer form, or amending the contract.

## Standing Invariants — hand-maintained, NOT derivable from `status.json`

These three outlived the generated block deliberately: nothing in `status.json` encodes them, so a
regeneration would silently drop them.

⛔ **`PLAN-TRUTH-029` is PERMANENTLY SPENT** — staged and deleted 2026-08-01, never reissue the id. It
proposed restructuring the finalize rebase/lock hot path; an orchestrator D0 measurement over the
39-plan archived corpus **refuted its premise** (the circling is triage loop-backs, not rebase
staleness) and showed its direction was **counter-indicated** (the early rebase surfaces merge conflicts
BEFORE the merge mutex is held). Measurement and residue preserved in `logs/decision.log`.

⛔ **`parallelization_scope` = 6 as of 2026-08-07 (operator directive), raised from 1. THE REASON THE
CAP EXISTED IS UNCHANGED AND STILL LOAD-BEARING.** The cap is **not** about our surface disjointness —
it is **shared capacity**. Two OTHER orchestrators (`code-intelligence-substrate`, `review-apparatus`)
emit concurrently, and the **cross-plan merge mutex is shared by every epic**. ⚠ Different constraint
classes: disjointness is *correctness*, per-epic; the cap is *capacity*, cross-epic. ⇒ **The raise was
NOT justified by disjointness evidence** — it is an operator call to accept more merge-time queueing in
exchange for throughput, recorded in `logs/decision.log`.
⭐ **What to watch now that it is 6**: merge-mutex wait times, rebase churn on plans that sat queued, and
whether a landing analysis shows two supposedly-disjoint plans collided. Those are the observations that
would justify lowering it again — and per the standing rule, an overridden advisory is **recorded, not
re-argued**, so the record is what gives the next one weight.

⛔ **Id-space split.** Staged plans use `PLAN-TRUTH-{NNN}`; old numeric ids no longer resolve in
`status.json`. Shipped / transferred / superseded rows kept their original ids by design — a persisted
`source_id` or landing pointer names them. Mapping: `plan-id-rename-map.md`.

## ⛔ Cloud-run ingestion — 2026-08-22 — READ THIS BEFORE SCHEDULING ANY GAP

`doc/plans/truthful-signals/` is **fully ingested and gone from version control** (commit
`5e9c0865d`, branch `chore/ingest-truthful-signals-cloud-runs`, **not pushed**). 47 executed plans →
`cloud-runs/{NNN}-{slug}/`, 8 un-run plans → `plans/PLAN-TRUTH-086..093`, epic docs → `cloud-runs/_epic/`.

**The full analysis is `cloud-runs/_epic/ingestion-analysis.md`.** It is the authority for everything
below and is not restated here.

**Three rulings, binding on every consumer of this ledger:**

1. **A run report is a dated record, not documentation of current state.** 32 of the 283 gaps target a
   `report-01.md` that is no longer tracked. They are **closed-as-recorded**. Five staged plans that
   cite them carry a re-scoping banner; `PLAN-TRUTH-092` is re-scoped to its contract half and loses
   its only `high` gap — correctly, because that gap is a report correction and its *class* is
   preserved structurally by that plan's D4.
2. **Every `gaps.md` is a SNAPSHOT at PR #1298 (2026-08-18).** Plans `500`/`510`/`520` landed
   afterwards. ⛔ **90 of the 283 gaps are already closed**, and **four closures are PARTIAL** —
   `190/G6` is closed for its documentation and **open for its code path**. Re-ground at HEAD before
   scheduling; a "closed" gap is a lead too.
3. **Derive a figure AFTER the review cycle closes.** The review is a diff-widening event. `500` and
   `520` both had files added after their counts were taken; `510`'s participation figure used a
   floating `origin/main` endpoint three sections after its own § Build gate corrects that defect.

**Live gap arithmetic: 218 open** (193 original + 25 filed by the derived plans), **not 283**.
216 owned; the 2 unowned are report corrections that ruling 1 disposes of.

**New Open Defects with no other home:**

- ⛔ **`500/G1` (high)** — `analyze_argument_naming` no-ops without `.plan/`, reports **clean** rather
  than *could not look*, silently disabling the whole `ARGUMENT_NAMING_*` cluster **including the rule
  plan 500 added**. Owned by `PLAN-TRUTH-094`.
- ⛔ **`510/G1` (high)** — the finalize input-table guard fires only on the literal header
  `Prompt-body field`, a convention in no normative document. Owned by `PLAN-TRUTH-095`.
- ⛔ **`510/G2` (high)** — `set --field self_review` still persists a dead key. Owned by `PLAN-TRUTH-095`.
- ⛔ **`080/G9`** — `ClaudeRuntime.project_initial_setup` overwrites `marshal.json` with no read and no
  existence check. Owned by `PLAN-TRUTH-086`.
- ⛔ **`070/G1`** — a daemon pinned below the counts extension reconciles as idle and is **drained mid-build**.
  Owned by `PLAN-TRUTH-086`.
- ⛔ **`360/D1` never shipped** — absolute version-pinned paths are still baked into the executor; what
  landed is marker-removal from a resolver that was already runtime. **Same surface as the standing
  registry/executor-pin incident family.** Owned by `PLAN-TRUTH-087`.
- ⚠ **`corpus cross-check` cannot see 34 of its own inputs** — the eight older staged specs carry
  abbreviated surface paths, so its collision count is an undercount and its parallel-safe verdict is
  not evidence. **Sequence from the ingestion analysis's collision map, not from the script.**
  A disjointness gate reporting clean over a population it never examined is this epic's archetype,
  sitting in the orchestrator's own tooling.

**✅ `250/G4` discharged for this epic** — the per-sender inbox archive migration ran: 582 messages into
49 sender directories, 0 flat remaining, re-run moves 0. ⛔ **Still owed for `code-intelligence-substrate`
(195 flat) and `review-apparatus` (136 flat)** — outside this epic's write boundary; `PLAN-TRUTH-096` D5
carries it as an operator action.

## ⭐ Split guard RAISED to 12 deliverables — operator decision 2026-08-08

The scope-bloat guard in `orchestration-model.md` presumes a split at **~6** deliverables. **For this
epic the operator has raised it to 12**, with the explicit goal of **fewer, larger, component-scoped
plans**.

- **Grouping is by COMPONENT first, task second.** Component grouping is what makes parallel execution
  safe: two plans on disjoint components are disjoint by construction, and disjointness — not count —
  is the concurrency test. A task-themed plan that spans three components is the *worst* shape, because
  it collides with everything.
- **12 is a ceiling, not a target.** A plan is merged only where the parts share a fix surface. Merging
  unrelated work to reach 12 buys nothing and makes the plan unlandable as one unit.
- ⭐ **A merge also REMOVES coordination overhead.** Two plans on one file need a serialization note, an
  ownership split, and a re-grounding obligation for whichever runs second. One plan needs none of that.
  Several of the merges below delete coordination machinery this ledger was carrying.
- ⛔ **The 12 cap does not license a bigger BLAST RADIUS.** Deliverable count and surface breadth are
  different axes; a 12-deliverable plan on one component is fine, a 6-deliverable plan across five
  components is not.

## Full-corpus review and reconciliation — 2026-08-09

> ↪ Relocated to `settled.md` § "Full-corpus review and reconciliation — 2026-08-09" — superseded by the 2026-08-22 cloud-run ingestion, whose reconciliation is broader and re-derived at HEAD.

## Ordered Queue

Mirrors `status.json` `plans[]` — reconcile status.json → here, never the reverse. Shipped rows are
not carried; `landings/` is their record.

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-TRUTH-145 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-execution-manifest/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_core.py; marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py; marketplace/bundles/plan-marshall/skills/manage-execution-manifest/standards/decision-rules.md; marketplace/bundles/plan-marshall/skills/manage-references/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-references/scripts/; marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_core.py; marketplace/bundles/plan-marshall/skills/manage-references/scripts/manage_references.py; marketplace/bundles/plan-marshall/skills/phase-1-init/**; marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/scripts/scope_creep_check.py; marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/canonical_verify.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/; test/plan-marshall/manage-execution-manifest/**; test/plan-marshall/manage-references/; test/plan-marshall/manage-references/**; test/plan-marshall/phase-5-execute/** |
| 2 | PLAN-TRUTH-146 | WS-01 | staged | marketplace/bundles/*/skills/ext-triage-*/; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/; marketplace/bundles/plan-marshall/skills/manage-change-ledger/; marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-merge-barrier; marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/landing-analysis.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md; marketplace/bundles/plan-marshall/skills/ref-toon-format/scripts/toon_parser.py; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/**; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py; marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py; marketplace/bundles/pm-requirements/skills/traceability/SKILL.md; test/plan-marshall/manage-findings/; test/plan-marshall/manage-findings/**; test/plan-marshall/plan-orchestrator/; test/plan-marshall/script-shared/**; test/plan-marshall/workflow-integration-sonar/ |
| 3 | PLAN-TRUTH-147 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_skill_domains.py; marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-status/scripts/; marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/; marketplace/bundles/plan-marshall/skills/phase-3-outline/workflow/light-lane.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/**; marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/canonical_verify.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/post_run_source_guard.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-simplify.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md; marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md; test/plan-marshall/manage-config/; test/plan-marshall/manage-status/; test/plan-marshall/phase-5-execute/; test/plan-marshall/phase-6-finalize/; test/plan-marshall/plan-marshall/ |
| 4 | PLAN-TRUTH-149 | WS-01 | staged | .claude/skills/audit-archived-plan-retrospectives/**; marketplace/bundles/plan-marshall/skills/manage-execution-manifest/**; marketplace/bundles/plan-marshall/skills/manage-findings/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/output-template.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/**; test/plan-marshall/**; test/plan-marshall/phase-6-finalize/; test/plan-marshall/plan-orchestrator/test_landing_completeness.py |
| 5 | PLAN-TRUTH-150 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/build-gradle/scripts/_gradle_cmd_parse.py; marketplace/bundles/plan-marshall/skills/build-maven/SKILL.md; marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_discover.py; marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_parse.py; marketplace/bundles/plan-marshall/skills/build-maven/standards/maven-impl.md; marketplace/bundles/plan-marshall/skills/build-npm/scripts/_npm_parse_jest.py; marketplace/bundles/plan-marshall/skills/build-npm/scripts/_npm_parse_tap.py; marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/_pyproject_cmd_parse.py; marketplace/bundles/plan-marshall/skills/manage-architecture/; marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py; marketplace/bundles/plan-marshall/skills/manage-build-server/; marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/**; marketplace/bundles/plan-marshall/skills/manage-change-ledger/**; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_qgate_mechanical.py; marketplace/bundles/plan-marshall/skills/phase-4-plan/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md; marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_jvm_patterns.py; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_parse.py; marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/**; marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/leaf-command-reference.md; marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/pr-operations.md; marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py; test/plan-marshall/; test/plan-marshall/build-maven/test_maven_cmd_parse.py; test/plan-marshall/script-shared/test_build_parse.py |
| 6 | PLAN-TRUTH-151 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-config/scripts/; marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_detect.py; marketplace/bundles/plan-marshall/skills/manage-lessons/**; marketplace/bundles/plan-marshall/skills/manage-plan-documents/**; marketplace/bundles/plan-marshall/skills/manage-solution-outline/; marketplace/bundles/plan-marshall/skills/manage-solution-outline/**; marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/_plan_parsing.py; marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_change_type_heuristic.py; marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md; marketplace/bundles/plan-marshall/skills/phase-1-init/**; marketplace/bundles/plan-marshall/skills/phase-2-refine/**; marketplace/bundles/plan-marshall/skills/phase-3-outline/; marketplace/bundles/plan-marshall/skills/phase-4-plan/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-security-audit.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/references/request-result-alignment.md; test/plan-marshall/manage-solution-outline/ |
| 7 | PLAN-TRUTH-153 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-architecture/; marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py; marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/**; marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md; marketplace/bundles/plan-marshall/skills/phase-3-outline/; marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/; marketplace/bundles/plan-marshall/skills/plan-retrospective/**; marketplace/bundles/plan-marshall/skills/ref-documentation/**; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/**; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/SKILL.md; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/rule-provenance.md; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/safe-fixes-guide.md; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/references/verification-guide.md; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_doctor_analysis.py; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_doctor_shared.py; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/standards/doctor-skills.md; test/_shared/_dispatch_roster.py; test/conftest.py; test/plan-marshall/**; test/plan-marshall/manage-locks/test_manage_locks_merge_lock_reentrant_acquire.py; test/plan-marshall/manage-tasks/** |
| 8 | PLAN-TRUTH-154 | WS-01 | staged | .claude/skills/finalize-step-sync-plugin-cache/SKILL.md; .claude/skills/sync-plugin-cache/SKILL.md; .claude/skills/sync-plugin-cache/scripts/sync.py; .plan/temp/repair-plugin-pin.py; AGENTS.md; CLAUDE.md; doc/developer/manual-sync-recovery.adoc; doc/developer/marketplace-build.adoc; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/build-server-client/**; marketplace/bundles/plan-marshall/skills/manage-build-server/**; marketplace/bundles/plan-marshall/skills/manage-run-config/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-run-config/scripts/run_config.py; marketplace/bundles/plan-marshall/skills/manage-run-config/standards/run-config-standard.md; marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/; marketplace/bundles/plan-marshall/skills/marshall-steward/references/menu-commit-trailer.md; marketplace/bundles/plan-marshall/skills/marshall-steward/references/menu-healthcheck.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/output-template.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/**; marketplace/bundles/plan-marshall/skills/plan-marshall-plugin/**; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/q-gate-validation.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/; marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci.py; marketplace/bundles/plan-marshall/skills/tools-script-executor/**; marketplace/bundles/plan-marshall/skills/workflow-integration-git/; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; test/plan-marshall/automatic-review/**; test/plan-marshall/manage-run-config/**; test/plan-marshall/tools-script-executor/**; test/plan-marshall/workflow-integration-git/** |
| 9 | PLAN-TRUTH-155 | WS-01 | staged | doc/plans/truthful-signals/170-graduate-deployment-diagram-type-from-api-sheriff/report-01.md; doc/user/configuration.adoc; doc/user/efforts.adoc; doc/user/enforcement-hook.adoc; doc/user/parallelism-and-locking.adoc; doc/user/recipes.adoc; marketplace//sync-plugin-cache; marketplace/bundles/; marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/automatic-review/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/extension-api/standards/build-systems-common.md; marketplace/bundles/plan-marshall/skills/extension-api/standards/persona-plan-marshall-agent/SKILL.md; marketplace/bundles/plan-marshall/skills/extension-api/standards/plan-marshall/workflow/await-long-running.md; marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-status/**; marketplace/bundles/plan-marshall/skills/persona-security-expert/standards/dependency-supply-chain.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/**; marketplace/bundles/plan-marshall/skills/plan-retrospective/**; marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/dispatch-logging.md; marketplace/bundles/plan-marshall/skills/tools-integration-ci/**; marketplace/bundles/plan-marshall/skills/tools-integration-ci/SKILL.md; marketplace/bundles/plan-marshall/skills/tools-permission-doctor/standards/permission-architecture.md; marketplace/bundles/pm-dev-java/skills/java-core/standards/java-17-features.md; marketplace/bundles/pm-dev-java/skills/java-core/standards/java-null-safety/SKILL.md; marketplace/bundles/pm-dev-java/skills/java-core/standards/java-null-safety/standards/null-safety-core.md; marketplace/bundles/pm-dev-java/skills/java-core/standards/java-null-safety/standards/null-safety-patterns.md; marketplace/bundles/pm-dev-java/skills/java-maintenance/standards/compliance-checklist.md; marketplace/bundles/pm-dev-java/skills/java-maintenance/standards/java-maintenance/standards/refactoring-triggers.md; marketplace/bundles/pm-documents/skills/ref-svg-diagrams/standards/diagram-type-deployment.md; marketplace/bundles/pm-documents/skills/ref-svg-diagrams/standards/ref-svg-diagrams/templates/deployment-diagram-skeleton.svg; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md; test/plan-marshall/** |
| 10 | PLAN-TRUTH-156 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/manage-status/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_mark_step.py; marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py; test/plan-marshall/manage-status/_manage_status_transition_fixtures.py; test/plan-marshall/manage-status/_mark_step_done_fixtures.py; test/plan-marshall/manage-status/test_mark_step_done_completion_head_and_keys.py; test/plan-marshall/manage-status/test_mark_step_head_anchor.py |
| 11 | PLAN-TRUTH-158 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/architecture-refresh.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/push.md; test/plan-marshall/phase-6-finalize/** |
| 12 | PLAN-TRUTH-159 | WS-01 | parked | .claude/skills/**; .claude/skills/finalize-step-deploy-target/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; test/plan-marshall/** |
| 13 | PLAN-TRUTH-160 | WS-01 | staged | doc/adr/022-Economy_rules_bind_the_persisted_artifact_never_the_reasoning_that_produced_it.adoc; marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/**; marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md; marketplace/bundles/plan-marshall/skills/phase-5-execute/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/**; test/plan-marshall/manage-metrics/** |
| 14 | PLAN-TRUTH-161 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-adr/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-adr/scripts/**; marketplace/bundles/plan-marshall/skills/manage-adr/templates/adr-template.adoc; marketplace/bundles/pm-documents/skills/ref-asciidoc/scripts/_cmd_validate.py; test/plan-marshall/manage-adr/**; test/pm-documents/ref-asciidoc/** |
| 15 | PLAN-TRUTH-162 | WS-01 | staged | .claude/skills/**; .claude/skills/finalize-step-deploy-target/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py; marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md; marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; marketplace/bundles/plan-marshall/skills/platform-runtime/standards/pretooluse-enforcement.md; test/plan-marshall/** |
| 16 | PLAN-TRUTH-163 | WS-01 | parked | test/plan-marshall/plan-orchestrator/test_orchestrator_dispatch_workflow_pin.py |
| 17 | PLAN-TRUTH-164 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/manage-status/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/**; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/_cmd_prune_ref.py; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py; test/plan-marshall/workflow-integration-git/** |
| 18 | PLAN-TRUTH-165 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py; marketplace/bundles/plan-marshall/skills/tools-permission-doctor/scripts/permission_doctor.py; marketplace/bundles/plan-marshall/skills/tools-permission-fix/**; marketplace/bundles/pm-plugin-development/skills/plugin-architecture/references/frontmatter-standards.md; marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/references/notation-spec.md; test/plan-marshall/tools-permission-doctor/**; test/plan-marshall/tools-permission-fix/** |
| 19 | PLAN-TRUTH-167 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md; marketplace/bundles/plan-marshall/skills/manage-references/scripts/_cmd_compute_footprint.py; marketplace/bundles/plan-marshall/skills/manage-references/scripts/_references_core.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/self_review.py; test/plan-marshall/phase-6-finalize/; test/pm-plugin-development/ext-self-review-plan-marshall/ |
| 20 | PLAN-TRUTH-168 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_quality_phases.py; marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_sync_defaults.py; marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py; test/plan-marshall/manage-config/ |
| 21 | PLAN-TRUTH-169 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/build-maven/; marketplace/bundles/plan-marshall/skills/build-pyproject/; marketplace/bundles/plan-marshall/skills/build-server-client/; marketplace/bundles/plan-marshall/skills/manage-build-server/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/architecture-refresh.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/push.md; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/build.py; test/conftest.py; test/plan-marshall/build-server-client/; test/plan-marshall/manage-build-server/; test/plan-marshall/phase-6-finalize/** |
| 22 | PLAN-TRUTH-170 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-status/scripts/; marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py; marketplace/bundles/plan-marshall/skills/phase-5-execute/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/; test/plan-marshall/manage-status/; test/plan-marshall/workflow-integration-git/ |
| 23 | PLAN-TRUTH-171 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-change-ledger/; marketplace/bundles/plan-marshall/skills/manage-status/**; marketplace/bundles/plan-marshall/skills/manage-status/scripts/; marketplace/bundles/plan-marshall/skills/phase-2-refine/; marketplace/bundles/plan-marshall/skills/phase-4-plan/; marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/_cmd_prune_ref.py; marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py; test/plan-marshall/manage-change-ledger/; test/plan-marshall/manage-status/; test/plan-marshall/workflow-integration-git/ |
| 24 | PLAN-TRUTH-172 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py; marketplace/bundles/plan-marshall/skills/phase-3-outline/workflow/light-lane.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py; marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md; test/plan-marshall/manage-tasks/scripts/; test/plan-marshall/plan-marshall/ |
| 25 | PLAN-TRUTH-173 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_patterns.py; test/pm-plugin-development/ext-self-review-plan-marshall/ |
| 26 | PLAN-TRUTH-174 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/; marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/extract-chat-signal.py; marketplace/bundles/plan-marshall/skills/ref-toon-format/scripts/toon_parser.py; test/plan-marshall/plan-retrospective/** |
| 27 | PLAN-TRUTH-175 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-change-ledger/**; marketplace/bundles/plan-marshall/skills/manage-metrics/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/**; marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/dispatch-logging.md; test/plan-marshall/manage-change-ledger/**; test/plan-marshall/manage-metrics/**; test/plan-marshall/phase-6-finalize/** |
| 28 | PLAN-TRUTH-176 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md; marketplace/bundles/plan-marshall/skills/tools-script-executor/**; marketplace/bundles/pm-plugin-development/skills/recipe-fix-argparse-rejection/**; test/plan-marshall/tools-script-executor/** |
| 29 | PLAN-TRUTH-177 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/phase-1-init/**; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; test/plan-marshall/phase-1-init/** |
| 30 | PLAN-205 | WS-QA-01 | staged | marketplace/bundles/plan-marshall/skills/build-pyproject/; marketplace/bundles/plan-marshall/skills/manage-build-server/; marketplace/bundles/plan-marshall/skills/manage-change-ledger/; marketplace/bundles/plan-marshall/skills/manage-locks/; marketplace/bundles/plan-marshall/skills/manage-metrics/; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/ |
| 31 | PLAN-206 | WS-QA-02 | staged | marketplace/bundles/plan-marshall/skills/manage-metrics/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/ |
| 32 | PLAN-207 | WS-QA-02 | staged | marketplace/bundles/plan-marshall/skills/phase-5-execute/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/ |
| 33 | PLAN-208 | WS-QA-03 | staged | marketplace/bundles/plan-marshall/skills/automatic-review/ |
| 34 | PLAN-209 | WS-QA-03 | staged | marketplace/bundles/plan-marshall/skills/automatic-review/; marketplace/bundles/plan-marshall/skills/manage-providers/ |
| 35 | PLAN-211 | WS-QA-04 | staged | marketplace/bundles/plan-marshall/skills/manage-lessons/; marketplace/bundles/plan-marshall/skills/workflow-integration-git/ |
| 36 | PLAN-213 | WS-QA-06 | staged | marketplace/bundles/plan-marshall/skills/manage-tasks/; marketplace/bundles/plan-marshall/skills/phase-4-plan/; marketplace/bundles/plan-marshall/skills/phase-5-execute/ |
| 37 | PLAN-214 | WS-QA-06 | staged | marketplace/bundles/plan-marshall/skills/phase-2-refine/; marketplace/bundles/plan-marshall/skills/plan-marshall/; marketplace/bundles/plan-marshall/skills/workflow-integration-github/ |
| 38 | PLAN-215 | WS-QA-06 | staged | marketplace/bundles/plan-marshall/skills/manage-architecture/; marketplace/bundles/plan-marshall/skills/manage-lessons/; marketplace/bundles/plan-marshall/skills/tools-script-executor/ |
| 39 | PLAN-216 | WS-QA-07 | staged | marketplace/bundles/plan-marshall/skills/manage-findings/; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/ |
| 40 | PLAN-217 | WS-QA-07 | staged | marketplace/bundles/plan-marshall/skills/manage-logging/; marketplace/bundles/plan-marshall/skills/plan-retrospective/ |
| 41 | PLAN-218 | WS-QA-09 | staged | marketplace/bundles/plan-marshall/skills/manage-config/ |
| 42 | PLAN-219 | WS-QA-08 | staged | marketplace/bundles/plan-marshall/skills/phase-6-finalize/ |
| 43 | PLAN-220 | WS-QA-08 | staged | marketplace/bundles/plan-marshall/skills/phase-6-finalize/; marketplace/bundles/plan-marshall/skills/tools-integration-ci/ |
| 44 | PLAN-221 | WS-QA-02 | staged | marketplace/bundles/plan-marshall/skills/marshall-steward/; marketplace/bundles/plan-marshall/skills/platform-runtime/; marketplace/bundles/plan-marshall/skills/tools-script-executor/; marketplace/bundles/pm-plugin-development/skills/finalize-step-deploy-target/ |
<!-- END GENERATED: ordered-queue -->

### Queue annotations

> Hand-written, OUTSIDE the generated markers, and preserved verbatim by every `compact` pass.
> The `ordered-queue` marker pair was inserted during the 2026-08-22 cloud-run ingestion under
> cleanup Rule 1 (one-time migration): this ledger predates the markers, which PLAN-TRUTH-074
> introduced, so the block had been reported `markers_absent` — a BLIND SPOT, never an abstention.
> The table above wrapped an empty header with no data rows; nothing was moved and nothing deleted.

> ↪ Relocated to `settled.md` § "Ordered Queue annotations — five reconciliations 2026-07-30 → 2026-08-08, and the API-Sheriff receipt" — five completed reconciliation passes and one
> cross-repo receipt, every one superseded by a later pass and finally by the 2026-08-22 ingestion.
> Moved VERBATIM, nothing condensed: the queue's live state is `status.json`, rendered in the
> generated block above.

**⛔ COLLISION MAP AMENDMENT — 2026-08-23, from the PR #1330 ingestion. Read WITH R5's machine-derived
map, not instead of it.**

- ⛔ **NEW collision `-088 ↔ -089`.** `PLAN-TRUTH-089 DB` (the `record-step` `unmeasured` fold, D-1330-g)
  must update **both** readers in one change, and the second — `plan-retrospective/scripts/
  check-routing-decisions.py` — is in **`-088`'s** Expected Surface. The writer
  (`manage-execution-manifest`) is `-089`'s. **The split is inherent to the defect, not an authoring
  choice: a half-landed change fails SILENTLY**, because a non-numeric cell coerced by a `_to_int`-style
  helper returns `0` and re-enters the sum looking measured. ⇒ **Serialize `-088` and `-089`; never pair
  them in one `next` block.** `-088` also gained `manage-change-ledger/scripts/_ledger_core.py` and
  `-089` gained `plan-marshall/workflow/planning.md` + `phase-5-execute/standards/workflow.md`.
- ⚠ **`-095 ↔ -097` now share `phase-6-finalize/standards/push.md`** — `-095 D6` (D-1330-b) reads it as a
  cross-check for the order-10/order-11 contradiction while `-097` owns it. **Read-only in `-095`**, so
  this is a sequencing note rather than a hard collision: if they run together, `-095` must not edit it.
- ✅ **Unchanged by this ingestion: `-093` stays genuinely disjoint** (D-1330-h folded into surfaces it
  already owned — `disposition-to-hint-routing.md`, `finalize-step-preference-emitter.md`), and `-087`'s
  additions (`_build_shared.py`, `test_review_retrospective.py`) collide with nothing currently staged.
- ⛔ **`-094` and `-096` remain the two genuinely disjoint singles** from R5. This amendment adds no
  constraint on either.

**PLAN-TRUTH-166 — 2026-09-15.** `corpus cross-check` reports ONE staged overlap: `-145` declares
`phase-6-finalize/standards/architecture-refresh.md`. ⇒ **Never pair `-166` with `-145` in one `next`
block.** Every other overlap row it reports is against a shipped/superseded spec. `-159` is adjacent
(same archetype as `-166 D4`, `.claude/skills/` surface) but path-disjoint.

**2026-09-17 — `-152` TRANSFERRED OUT to the new `post-run-quality` epic** (operator-directed), where it
is `PLAN-PRQ-01`. Its row here is `parked`, not `transferred`, because `queue --transition` cannot write
that status — first-party evidence for `-143` D9. ⛔ **`-146` STAYS here**: PLAN-PRQ-01's D10 consumes its
unified-vocabulary work, so the dependency runs outward, not inward. ⚠ `-144` now shares
`manage-lessons/**` with `post-run-quality` PLAN-PRQ-05 — **cross-epic, so no gate can see it**; check
that epic's queue before launching `-144`.

**2026-09-17 — `-166` SHIPPED (#1501), so every collision below is RETIRED.** `-145`, `-158` and `-167`
are unblocked; `-167` still must not pair with `-147` (`pre-submission-self-review.md`) or `-145`
(`manage-references/scripts/`), and `-158` still shares `architecture-refresh.md` with `-145`. ⛔ Read the
next block as history, not as live constraint.

**2026-09-15 (c) drain — parser-derived collisions against RUNNING `-166`** (symmetric `corpus cross-check`
read): ⛔ **`-158`** (`architecture-refresh.md`, by its own fold) and **`-145`** (same file) and **`-167`**
(`test/plan-marshall/phase-6-finalize/` contains `test_architecture_refresh.py`) are unpickable until 166
lands. ⚠ The earlier emit block `146/158/160` is **RETRACTED** — 158 now collides with 166, and 146/160
collide with the queue-order selection `143`/`144`. `-167 ↔ -147` share `pre-submission-self-review.md` and
`-167 ↔ -145` share `manage-references/scripts/` — never pair.

## ⛔ Inbound routing rule — every incoming item is classified BEFORE it is dispositioned

**Since 2026-08-24 this epic has THREE siblings: `code-intelligence-substrate`, `review-apparatus`
and `lessons-routing`.** Every incoming item — each `inbox/` message at drain time, each landing
residue, each operator-pasted finding — MUST be classified against all **four** owners before any
disposition is applied. An item that is silently kept here because it arrived here is a routing
failure, not a decision.

⚠ **The count changed on 2026-08-24 and the older prose below still says "three owners" in places** —
four is correct. Re-read this table, not a remembered version of it.

⛔ **STANDING OPERATOR INSTRUCTION 2026-07-30 — we are a DISPATCHER for the PR-review theme, not an
owner.** `review-apparatus` owns the automated-PR-review apparatus end to end. **Every finding AND
every landing concerning PR-related work is forwarded there — we stage no plan for it.** Five staged
rows (PLAN-60, 100, 116, 117, 119) were released on this instruction; see the Decisions entry.

⚠ **The dispatcher role has one non-obvious obligation:** forwarding a *landing* is not the same as
forwarding a *finding*. A landing is only useful to the receiver if it carries the **post-merge
outcome**, and today's landing message is emitted **pre-merge with no outcome** — that is the defect
PLAN-100 describes, and it has just been transferred to `review-apparatus`. ⇒ **Until PLAN-100's
successor lands there, every PR-related landing we forward must have its outcome attached by hand.**
Recorded so the gap is not discovered by a receiver acting on an outcome-less landing.

### The discriminator

| Belongs HERE (`truthful-signals`) | Belongs to `code-intelligence-substrate` | Belongs to `review-apparatus` | Belongs to `lessons-routing` |
|---|---|---|---|
| A signal about **behaviour or a contract** that reads as confident while hiding a caveat: merge/landing truthfulness, config surfaces, the daemon, docs contracts, test isolation, **build-gate ↔ CI parity**. ⚠ **`lessons` was REMOVED from this cell on 2026-08-24** — see the fourth column | A signal about **how the system KNOWS things** — navigation, index, graph, content search — **or about MEASUREMENT** of the codebase or of our own runs: footprint derivation, cost/token accounting, evidence emission, detector population and derivation | **Anything PR-review**: reviewer configuration and event subscriptions, the trigger/await machinery, the participation taxonomy and its classifier, the pre-merge review barrier, merge-queue behaviour, the org-side / `pr-agent-settings` config repos, **and the post-merge review revisits** | **Anything about where a FINDING GOES and whether it survives**: the lessons corpus and its store resolution, the audience/ownership classification of a finding, the upstream issue route out of a consumer repo, lesson provenance (component, version), multi-developer durability, and the consumer-repo corpus. ⭐ **The test is DESTINATION, not subject**: a defect *in* `manage-lessons`' behaviour that reads confident while hiding a caveat is still OURS; a question about *who should receive a finding and whether it reaches them* is theirs |

⭐ **Boundary refinements settled 2026-07-30, both by operator decision through `review-apparatus`:**
**(a)** all five post-merge revisits (#1055, #1057, #1058, #1059, #1061) moved THERE — splitting one out
of a batch of five was worse than either whole, so **the standing post-merge-revisit rule no longer
applies to us for PR-related PRs**; **(b)** the *build-gate* half of a review/gate plan stays HERE — the
former PLAN-60 split, with its build half returning as `PLAN-TRUTH-019`. ⇒ **"Review coverage" and
"gate coverage" are different subjects even inside one plan.**

⭐⭐ **Boundary settled 2026-08-24 on the creation of `lessons-routing`, with the corpus searched
before the epic was created.** `lessons` was removed from our column above. The search was done and its
result is recorded so nobody repeats it: of **17 staged** rows here, **none** carries a lessons subject
in its slug, and the five historical lessons-subject plans (`PLAN-90`, `PLAN-103`, `PLAN-109`,
`PLAN-TRUTH-044`, `PLAN-TRUTH-047`) are all **shipped** — historical, not movable. ⇒ **Nothing was
transferred, because there was nothing live to transfer.**

⚠ **One near-miss, deliberately KEPT here.** `PLAN-TRUTH-091` carries a folded deliverable about
`lessons-housekeeping` recording a verdict that a concurrent actor invalidated within nine minutes.
⛔ **It stays** — its subject is **verdict currency over a mutable global store**, and the spec says so
itself (*"Generalizes beyond lessons: any finalize step whose verdict derives from a global store…"*).
Lessons is the instance, not the subject; the remedy is the `verdict_inputs` currency shape shared with
`-097` DB. **Do not re-route it on a keyword match.**

⭐ **`PLAN-103` (SHIPPED #1050) is the reason the new epic's LR-02 exists and must be read before it
runs.** It scoped the store-ownership guard to *prefixed* components — fixing the prefix-LESS case. The
residue is that for a PREFIXED component the ownership predicate is still plan-marshall-shaped, so in a
consumer repo a client's own `api-sheriff:maven-build` is classified foreign exactly as
`plan-marshall:build-maven` is. **That residue is `lessons-routing`'s, not ours.**

⚠ **`review-bot contracts` was removed from our column on 2026-07-30** — it now reads to
`review-apparatus`. It is left named here explicitly because it was ours for the epic's whole life and
a reader of older entries will otherwise keep routing it to us.

**Rule of thumb:** if fixing it changes *what the system reports about itself*, it is likely ours.
If fixing it changes *what the system can find out, or how it counts*, it is likely the sibling's.

⚠ **Ambiguity defaults HERE, and the ambiguity is recorded.** Do not ping-pong an item between
epics. When the classification is genuinely unclear, keep it in this epic, apply its disposition,
and note the open question — a wrongly-kept item is recoverable; an item bounced twice loses its
provenance.

### Transport — forward, never copy

When an item belongs to the sibling, **forward it to that epic's inbox** rather than dispositioning
it here. Stage the payload with `Write` first (no message body passes through a shell argument):

```bash
python3 .plan/execute-script.py plan-marshall:marshall-orchestrator:orchestrator inbox write \
  --slug code-intelligence-substrate --sender-type orchestrator --sender-id truthful-signals \
  --kind {landing|finding|candidate-lesson} --payload-file {path}
```

Then complete the drain here: **archive the source message** (forwarding IS its consuming
disposition) and log it as `forwarded` with the target epic named, per the standard's two-sided
record obligation. The forwarded payload MUST carry its original provenance — the source PR, the
observing plan, and any orchestrator verification already performed — because the sibling's drain
treats an incoming message as a **lead, not a fact**, exactly as this one does.

⛔ **Forward, never copy.** One owner per item. A signal recorded in both epics produces two
independent plans against one defect — the duplicate-work failure the surface-disjointness rule
exists to prevent.

## ⛔ Cross-epic plan-ID allocation — RETIRED for new work as of 2026-07-30

> ↪ Relocated to `settled.md` § "⛔ Cross-epic plan-ID allocation — RETIRED for new work as of 2026-07-30" — the allocation scheme is RETIRED for new work; the band-invariant record is history, not policy.

## Decisions

Binding decisions that still govern. Settled ones are removed.

- **Merge only within a serialization class.** Plans that already share files can never run in
  parallel, so merging them costs zero throughput and saves a plan lifecycle. Surface-disjoint plans
  **are** parallel slots — merging those destroys capacity. Apply this to every future merge question.
- **PLAN-TRUTH-003 and PLAN-TRUTH-002 both need a population-derived plugin-doctor detector; PLAN-77 and PLAN-99
  both instrument `platform-runtime`. Share the substrate by SEQUENCING, do not merge** — each pair
  is a parallel slot.
- **`standard`, not `default`, is the renamed lane tier value** — `default:` is the built-in step-id
  namespace prefix and would collide.
- **PLAN-TRUTH-015 is drain-gated to last** — it renames directories most other plans modify.
- **The `pr-agent-settings` charter is out of scope for every plan.** The operator owns it. Until it
  lands, the Intent section in PR bodies can *reduce* review recall.
- **PLAN-70 D4-style evidence gates:** a registry doc may only be authored from OBSERVED bot output,
  never from assumption — the defect class this epic exists to remove.
- ⛔ **FIVE PLANS RELEASED TO `review-apparatus` 2026-07-30, and this epic is now a dispatcher for the
  PR-review theme.** Operator instruction. Released (all STAGED, none running): **PLAN-116** (review
  detectors check the wrong observable, incl. Shape F), **PLAN-119** (barrier deadlocks on a refusing
  bot; carries D3 accepted-coverage-gap, still owed to the operator), **PLAN-117** (merge-queue enqueue
  does not take), **PLAN-100** (landing message carries no outcome), **PLAN-60** (in-house gate ↔
  CI/PR-bot parity). Rows transitioned to `transferred`; handover sent as `truthful-signals-001` to
  that epic's inbox. **No id travels** — each is re-issued there as `PLAN-PR-NNN`.
  - **The operator's instruction was literally "all open plans (not running)" = all 24 staged rows; it
    was scoped to these five on an explicit orchestrator escalation.** Rationale recorded because the
    narrower reading was ours, not the operator's: 17 of the 24 have no PR-review subject at all (the
    PLAN-TRUTH-017 live data-loss path, PLAN-TRUTH-018 timezone rendering, the superseded PLAN-105), and
    `review-apparatus` runs `parallelization_scope=1`, so a 24-plan transfer would have become one
    serial queue under a charter that does not cover most of it.
  - ⛔ **PLAN-TRUTH-001 (then PLAN-113) deliberately NOT released**, though it is finalize-adjacent: `code-intelligence-substrate`
    has already written the **sequencing into PLAN-CIS-011 (ex-PLAN-121) as a hard constraint**.
    Moving it to a third epic would silently invalidate a cross-epic agreement recorded in
    another ledger. **A transfer is not a local decision when a third party has already sequenced
    against the row.** PLAN-TRUTH-006 (then PLAN-52) also stays (git-mutation contract, not review).
    ✅ Both retentions were **accepted without argument** by `review-apparatus` in `-004`.
  - **PLAN-115 stays** — launched, and `review-apparatus-001` explicitly asked that it not move. That
    epic sequences the `tools-integration-ci` plan-less-PR seam BEHIND its landing; we owe them the
    landing report.
- **A deferral conditioned on another epic's PR MUST name the PR.** Adopted from
  `code-intelligence-substrate` and extended to `review-apparatus`. A cross-epic constraint recorded on
  one side only has **no reader on the other side to retire it** — PLAN-TRUTH-003's `manage-metrics` deferral
  sat live after its condition (#1059) had already merged. Naming the PR turns retirement into a check
  rather than a memory. This matters MORE under the dispatcher arrangement, not less.

## Inbox drain — 2026-08-09 (evening), 37 messages, every one dispositioned

> ↪ Relocated to `settled.md` § "Inbox drain — 2026-08-09 (evening), 37 messages, every one dispositioned" — a completed drain is closed by definition; every message was dispositioned and archived.

## Inbox drain — 2026-08-09, 34 messages, every one dispositioned

> ↪ Relocated to `settled.md` § "Inbox drain — 2026-08-09, 34 messages, every one dispositioned" — a completed drain is closed by definition; every message was dispositioned and archived.

## Inbox drain — 2026-08-08, 57 messages, every one dispositioned

> ↪ Relocated to `settled.md` § "Inbox drain — 2026-08-08, 57 messages, every one dispositioned" — a completed drain is closed by definition; every message was dispositioned and archived.

## Condensation — 2026-08-08, 49 staged → 36, grouped by component

> ↪ Relocated to `settled.md` § "Condensation — 2026-08-08, 49 staged → 36, grouped by component" — a completed one-off condensation; its result is the queue, which status.json now carries.

## Premise verification sweep — 2026-08-08, ALL 49 staged plans

> ↪ Relocated to `settled.md` § "Premise verification sweep — 2026-08-08, ALL 49 staged plans" — superseded — every premise was re-grounded again at the 2026-08-22 ingestion against HEAD.

## Distribution decisions — 2026-08-08 full reconciliation

> ↪ Relocated to `settled.md` § "Distribution decisions — 2026-08-08 full reconciliation" — a completed distribution pass; the surviving collision map is re-derived in the ingestion analysis.

## Inbox drain — 2026-09-04 (b), `findings-from-cui-http.md`, 45 findings dispositioned

> ↪ Relocated to `settled.md` § "Inbox drain — 2026-09-04 (b), `findings-from-cui-http.md`, 45 findings dispositioned" — a completed drain is closed by definition; every message was dispositioned and archived.

## Inbox drain — 2026-09-04, 32 messages, every one dispositioned

> ↪ Relocated to `settled.md` § "Inbox drain — 2026-09-04, 32 messages, every one dispositioned" — a completed drain is closed by definition; every message was dispositioned and archived.

## Inbox drain — 2026-09-03, 36 messages, every one dispositioned

> ↪ Relocated to `settled.md` § "Inbox drain — 2026-09-03, 36 messages, every one dispositioned" — a completed drain is closed by definition; every message was dispositioned and archived.

## Inbox drain — 2026-09-02, 2 messages, both dispositioned

> ↪ Relocated to `settled.md` § "Inbox drain — 2026-09-02, 2 messages, both dispositioned" — a completed drain is closed by definition; every message was dispositioned and archived.

## Inbox drain — 2026-09-05, 16 messages, every one dispositioned (PLAN-TRUTH-126 full ship)

> ↪ Relocated to `settled.md` § "Inbox drain — 2026-09-05, 16 messages, every one dispositioned (PLAN-TRUTH-126 full ship)" — a completed drain is closed by definition; every message was dispositioned and archived.

## Inbox drain — 2026-09-05 (b), 11 messages, every one dispositioned (PLAN-TRUTH-093 full ship)

> ↪ Relocated to `settled.md` § "Inbox drain — 2026-09-05 (b), 11 messages, every one dispositioned (PLAN-TRUTH-093 full ship)" — a completed drain is closed by definition; every message was dispositioned and archived.

## Inbox drain — 2026-09-05 (c), 9 messages, every one dispositioned (PLAN-TRUTH-089 full ship)

> ↪ Relocated to `settled.md` § "Inbox drain — 2026-09-05 (c), 9 messages, every one dispositioned (PLAN-TRUTH-089 full ship)" — a completed drain is closed by definition; every message was dispositioned and archived.

## Inbox drain — 2026-09-06, 1 message, 11 items dispositioned (`review-apparatus-033`)

**1 scanned / 1 archived / 0 invalid / 0 archive_failed.** One message carrying **nine relayed
candidate-lessons plus two extra observations** — bundled by the sender *"to avoid nine queue rows
arriving from one drain, not because they share a subject."*

| Item | Disposition |
|---|---|
| 1 — 32 re-firings = 71% of an 8.63M-token 3-file plan | folded → `-107` |
| 6 — execute yielded `voluntary_checkpoint` on 4 of 5 dispatches | folded → `-107`, surface +1 |
| 2 — argparse rejections, 5 more notations | **recurrence** → `-129`, not staged again |
| 4 — split `include_unrealised` by declared intent | folded → `-130` |
| 5 — record `changed_files` on task records | **second independent report** → `-138` |
| 7 — a correcting clause re-seeds the defect: DELETE instead | folded → `-117`, **not** re-promoted |
| 8 — prose under `Files to survey:` parses into path fragments | folded → `-134`, surface reaches OUR gate |
| 9 — two set-guarding checks over an empty population | folded → `-104` |
| obs — `manage-logging read --phase` does not filter | folded → `-104`, surface +1 |
| obs — `bd825d` recurrence, **third occurrence** | folded → `-129`, **root cause named** |
| 3 — session-injected commit trailer displaces the resolver | **Open Defect**, operator decision owed |

### ⭐⭐⭐ Item 1 is the first COMPLETE cost measurement this epic holds

`any_phase_missing_end_time: false` — so **8.63M tokens / 28h44m wall, `6-finalize` 6.20M (72%)** are
**real figures, not floors.** Every prior measurement here is a floor (`-089` never closed the phase;
`-093` was `n=5/6`). ⇒ **The 71-77% finalize share is now established across four independent runs, one
of them fully attributed.**

### ⭐⭐ Item 6 REFUTES a hypothesis this epic was carrying

Every stopping instance recorded so far is mid-`finalize`, and the leading hypothesis was that stops
cluster there. **This one is mid-`execute` at 4 of 5 dispatches.** ⇒ `-107` D0(b)'s surviving arm now
has a second phase with a real denominator, and **outline must not scope the remedy to finalize.**

### ⛔ Item 2's FLOOR qualification had to survive the fold, and nearly did not

The sending dispatcher observed **8 distinct failing notations** and **2 lie outside the log window that
step paged** — so its 6-row table is a **lower bound**. A fold that carried the table and dropped that
sentence would have handed D0 a population that reads complete and is not.

### ⭐⭐ Item 8 pairs with our own opposite defect

Prose parsing into path fragments **adds phantom paths** to a declared footprint; our own in-flight
plans declaring `affected_files: 0` **write none at all**. ⛔ **Both end at the disjointness gate, and a
fix for one does not touch the other** — `-134` D0 must state which direction it addresses.

## Inbox drain — 2026-09-07, 12 messages, every one dispositioned (PLAN-TRUTH-128 full ship)

**12 scanned / 12 archived / 0 invalid / 0 archive_failed.** 11 from the landing plan, 1 from
`review-apparatus`. **8 folded · 2 forwarded · 1 reconciled · 1 split across two owners.**

➡ **`truthful-signals-050.md` → `review-apparatus`** (the quorum passes at zero yield) and
**`truthful-signals-057.md` → `code-intelligence-substrate`** (`blocked_user_review` spend in no
published class — the THIRD distinct hole in that decomposition, and a separate defect from the
41-of-41 unmeasured columns: **an unbucketed ROW versus an unfilled COLUMN**).

### ⛔⛔⛔ The headline: the self-review matched 0 of 75 candidates in classes IT DECLARES

`pre-submission-self-review` fired 8×, closed `75 candidates examined, no check matched`, and CodeRabbit
then filed **9 actionable items — four in classes the gate already declares, two of them genuine
fail-open contract defects.** ⛔ **Not a vacuous run**: the right population was examined, the right
classes applied, and the verdict was still unearned.

⭐⭐⭐ **The sender's sentence inverts a discipline this epic promotes:** *"it publishes the population
size — the discipline this epic asks for — and then draws the wrong reassurance from it."* ⇒
**Publishing the population is NECESSARY AND NOT SUFFICIENT. A stated denominator makes an unearned
verdict MORE persuasive, not less.**

### ⭐⭐⭐ Two messages in one drain, and one is a candidate CAUSE of the other

`arm-the-refusal-...-001` reports that `pre-submission-self-review.md:133-143` invokes the surfacer with
**no `--base-branch`**. **Verified first-party**: `self_review.py surface` defaults it to **local
`main`**, so a plan rebased onto `origin/main` over-scopes — that run measured **136 files against a
real diff of 21, ~6×.**

⚠ **Recorded as a HYPOTHESIS with a named test, because the two senders reason OPPOSITELY** — `-001`
concluded the failure is *"in the matching, not in candidate enumeration."* **Both can be true.** ⇒
**Re-run the surfacer on #1425's branch with `--base-branch origin/main` and compare the candidate mix
against the recorded 75.**

### ⭐⭐ `sync-affected-files` is STRUCTURALLY INCAPABLE of closing the gap it is reached for

Declared 19, realized 21; the verb **added zero** on re-run because it re-derives from the **solution
outline**, and the outline is what is short. ⇒ **A clean-looking `added_count: 0` that reads as
confirmation.** ⛔ Paired with `-008` (a deliverable closed at 62.5% declared coverage) as the
**opposite direction** — realization exceeding declaration, and declaration exceeding realization.
**`-136` D0 must own both or ship a one-way check over a two-way defect.**

### ⭐⭐ D0(c) was recorded UNANSWERABLE, not clean — protect that

The spec asked whether the exempt path ever permitted a real push. **It cannot be answered from HEAD:
`push` only ever wrote `"pushed {branch}"`, so the discriminator this plan ADDS never existed to sweep
for.** ⇒ **Latent by assumption, not by measurement.** ⛔ **Do not let a later reader convert
"unanswerable" into "clean."**

## Inbox drain — 2026-09-07 (b), 24 messages, every one dispositioned (PLAN-TRUTH-099 full ship)

**24 scanned / 24 archived / 0 invalid / 0 archive_failed.** Three senders. **9 folded · 8 forwarded ·
1 reconciled.** ➡ `truthful-signals-051.md` → `review-apparatus` (7 items), `truthful-signals-058.md`
→ `code-intelligence-substrate` (1).

### ⭐⭐⭐ The verb retires a workaround this orchestrator used FOUR TIMES in this session

`queue --add-row` is live. Until it landed, every staged spec went in through a whole-array
`update-field --field plans` rewrite — 145+ rows through one shell argument, no rollback — and `-138`,
`-139`, `-140` each went that way behind hand-written key-order / duplicate-id / count assertions.
⇒ **Those assertions WERE the workaround. They are retired; every future append uses the verb.**

### ⛔⛔ THE FOOTPRINT GATES WHAT A PLAN CAN LEARN — third consequence, and the one with a price

`review-apparatus-034` item 1: **`lessons-consult` RAN, SUCCEEDED, and searched exactly ONE component**,
derived from a **9-file declaration against a realized 158-file footprint.** The lesson whose proposed
action was *verbatim* what the operator later redirected that plan to do came from the **immediately
preceding PR** and was invisible — its component fell outside the shrunken set. **A six-hour detour.**
⇒ Folded to `-136` as its third consequence. ⛔ *"A successful `lessons-consult` return is
indistinguishable from a complete one."*

### ⛔ THE LANDING FACTS REGRESSED — fifth data point, first reversal

| `-126` | `-093` | `-089` | `-128` | **`-099`** |
|---|---|---|---|---|
| none | outside the map | **complete** | **complete** | **none again** |

⇒ **Compliance is INTERMITTENT, not improving — two complete landings did not establish a trend.**
⚠ The facts are all present **in prose**, so the producer had them and emitted none machine-readably.
`-106`'s subject: a producer that cannot fail its own contract.

### ⭐⭐⭐ A positive control for the self-review gate, two landings after its worst showing

`pre-submission-self-review` caught that the `--add-row` id regex anchored with `$`, **which in Python
matches before a trailing newline** — so `PLAN-07\n` passed and the exact-string duplicate check never
collided. **The `duplicate_plan_id` guard the plan exists to add was evadable by ONE TRAILING BYTE.**
⇒ Two landings ago the same step matched 0 of 75. **The gate is INCONSISTENTLY EFFECTIVE, not uniformly
blind — a harder problem than being broken.**

## Inbox drain — 2026-09-07 (c), 11 messages, every one dispositioned (PLAN-TRUTH-125 full ship)

**11 scanned / 11 archived / 0 invalid.** 4 folded (`-104` `-105` `-116` `-129`), 1 forwarded, 1
reconciled, **1 DISCARDED WITH A POSITIVE ACCOUNT**, 2 recorded as Open Defects.
`landing-check: complete: true` — recovered from `-099`'s regression.

### ⭐⭐ A defect reported against this plan was closed BY this plan, in the same commit

`arm-the-refusal-...-002`: **no plan could pass a local whole-tree `verify` on macOS** — the always-on
skip gate refused the `/proc`-dependent nodeid, absent from `_SKIP_EXCEPTIONS`; CI is Linux so it was
invisible there. ⛔ **Verified first-party and already CLOSED**: the table now carries 12 entries
including that nodeid, and `git log -S` names the adding commit as **`39ec2a0ad` — PR #1427, this
landing.** ⇒ **Discarded with a positive account. The report and the remedy crossed in flight.**

### ⭐⭐⭐ The shipped test is the exemplar this corpus keeps asking for

TOON now has one canonical implementation, **and a test that proves its population TWO independent ways
— by function name AND by behaviour — cross-checked.** ⇒ **`derive completeness, never assert it`
implemented as a CONTROL rather than restated as prose.** Cite `39ec2a0ad` rather than re-inventing it.

### ⛔ A contaminated denominator that MANUFACTURES a failure

`check-artifact-consistency` reported a failing **57% recall**; **six of its ten "missing files" are
`lessons-consult` prose bullets.** Real recall ≈ **71%**. ⛔ Both numbers are plausible, so only
enumerating the ten reveals four are not files at all ⇒ **a recall figure must publish its
denominator's MEMBERSHIP, not its size.**

## Inbox drain — 2026-09-08, 8 messages, every one dispositioned (no landing)

**8 scanned / 8 archived / 0 invalid.** One sender, all `candidate-lesson`, relayed from Token-Sheriff
PLAN-11 (PR #718 / `4e1e88db`). **5 folded (`-104` `-105`×2 `-121` `-129`), 3 forwarded** as
`truthful-signals-053.md`.

### ⭐⭐⭐ `-023` NAMES THE MECHANISM BEHIND THIS EPIC'S OWN STRANDED `uv.lock`

> *"`pre-push-quality-gate` declares `mutates_source: false`. The dispatcher reads that declared fact
> FIRST and, on `false`, SKIPS ITS COMMIT INSTRUMENTATION ENTIRELY — no staging, no commit, no owner
> for any diff the step produced."*

⛔⛔ **We recorded `uv.lock` as *"nothing owns committing it"* on 2026-09-05 without knowing why. Now we
do.** The declaration is read as a fact, and on `false` **the owning code path is never created** — so
the dirty tree survives to `push`, where it either blocks or rides along unattributed.

⇒ **n = 2, two projects, one harness defect.** ⛔ **And the real defect is not the wrong declaration:
a declared fact about a PROJECT-RESOLVED command is unknowable at declaration time**, so re-declaring
the step is not the remedy. ⚠ The sender's split survives the fold — the project half is their PLAN-12,
and **fixing only that leaves the harness still believing the command is non-mutating.**

> ⛔ **CORRECTED 2026-09-11** — the harness half SHIPPED the same day this was written: **#1454
> (`f24b19a51`) re-declared `pre-push-quality-gate` as `mutates_source: true`** and item 5f now commits the
> gate's own edits. "Re-declaring the step is not the remedy" was wrong — declaring `true` is safe for a
> non-mutating project too, since 5f commits only what is dirty. See the 2026-09-11 drain below and the
> 2026-09-11 fold at the end of `PLAN-TRUTH-105`.

### ⛔⛔ `-022` — A TOTAL WRITE LOSS THAT RECORDS `done`

`phase-6-finalize`'s dispatch loop consumes `escalate_ask` for **`automatic-review` only**, so
`adr-propose`'s escalations are **unreachable**: the leaf returns proposals, the dispatcher never reads
the field, no prompt reaches the operator, **and the step records `outcome: done`.**

**Two ADR-worthy decisions were lost**; the operator learned of them only from the plan's closing
narrative. ⛔ **The only trace is a `display_detail` that STATES the loss in plain words and still
renders as success** — *"no ADRs proposed (2 candidates need operator confirmation)"*.

⇒ **`escalate_ask` is a channel with ONE registered consumer and an OPEN SET of producers.**
**Enumerate the producers, not the consumer.**

### ⛔✅ `-024` — the stale `worktree_path` reaches FIVE independent sightings — NOW STAGED as `PLAN-TRUTH-164`

Two first-party here (`-126`, `-093` archived records), one with the root cause
(`worktree-remove` is not the symmetric counterpart of `worktree-create`), and now a third epic.
⚠ Fully diagnosed, unowned for four sightings, and the count measured the DELAY, not the defect.

**Fifth sighting, 2026-09-15, PLAN-TRUTH-148's own finalize run**: `metadata.use_worktree`/`worktree_path`
still pointed at a worktree `branch-cleanup` had already deleted; three dispatched post-merge steps
correctly REFUSED rather than operate against the wrong tree (the fail-closed behaviour is correct — the
defect is the metadata going stale, not the refusal). Operator worked around it in-session
(`use_worktree=false` after `branch-cleanup`). Five sightings over an extended period with a fully-named
root cause and no fix is past the delay-measuring stage — **staged as `PLAN-TRUTH-164`.**

## Inbox drain — 2026-09-11, 40 messages, every one dispositioned (cross-repo lessons, no landing)

**40 scanned / 40 archived / 0 invalid.** Two senders, all `candidate-lesson`, both consumer-repo
orchestrators relocating plan-marshall lessons out of their own stores (integrate-then-remove):
**API-Sheriff** `deployment-configurability` (9, each with a verification table at `356973d80`) and
**Token-Sheriff** `lessons-handling-26-09-04-01` (31, `-025`…`-055`). Every material claim spot-checked
first-party at HEAD `356973d80` (= `origin/main`) before any write.

**24 folded · 3 staged (2 new specs) · 2 promoted (1 lesson) · 11 discarded (10 forwarded, 1 refuted).**

| Message | Disposition | Destination / reason |
|---|---|---|
| `api-sheriff-…-001` | folded | `PLAN-TRUTH-122` — NEW root cause: `'[deprecation]'` compiled as a regex character class; `failIfNoSpecifiedTests` absent tree-wide; surface +3 |
| `api-sheriff-…-002` | discarded | forwarded to `review-apparatus` as `truthful-signals-054.md` (Item 1) |
| `api-sheriff-…-003` | discarded | forwarded `review-apparatus` `-054` (Item 7); two-axis rule is already lesson `2026-09-03-16-001` |
| `api-sheriff-…-004` | folded | `PLAN-TRUTH-117` (dispatch-time delta rule, surface +1); footprint half forwarded to `code-intelligence-substrate` as `truthful-signals-059.md` |
| `api-sheriff-…-005` | folded | `PLAN-TRUTH-132` — `step_execution_tier` is a second frozen param; `VALID_RECORD_OUTCOMES` has no lost-return value; surface +2 |
| `api-sheriff-…-006` | folded | `PLAN-TRUTH-105` — ledger stamps the POST-churn sha (template:579); **fold (b)'s direction CORRECTED in place**; surface +1 |
| `api-sheriff-…-007` | folded | `PLAN-TRUTH-118` D4 — enqueue corroborated by branch rule only (`github_ops.py`:982); surface +1 |
| `api-sheriff-…-008` | staged | **`PLAN-TRUTH-141`** (new) — light lane never writes `pr_title` its `2-refine` capture requires; no transition checks the phase array |
| `api-sheriff-…-009` | promoted | lesson **`2026-09-11-15-001`** (`persona-module-tester`, falsifiability — merged with `-044`) |
| `-025` | folded | `PLAN-TRUTH-105` — correction chain for `-023`; adds no surface |
| `-026` | folded | `PLAN-TRUTH-122` D1 — widening by argument subtraction drops `-am` (3rd plan) |
| `-027` | folded | `PLAN-TRUTH-105` — `tests_run: 0` + `measured`, third relay, onto `-018`; adds no surface |
| `-028` | folded | A → `PLAN-TRUTH-119` (q-gate skipped on `recipe_key` while outline branches on `plan_source`; surface +1); B → `PLAN-TRUTH-091` (consumer configured the phantom `drop_review_on_scope_gate`; precedence diagnosis REFUTED — nothing reads it; adds no surface) |
| `-029` | discarded | forwarded `review-apparatus` `-054` (Item 6) |
| `-030` | discarded | forwarded `review-apparatus` `-054` (Item 6) |
| `-031` | discarded | forwarded `review-apparatus` `-054` (Item 5) |
| `-032` | discarded | forwarded to `lessons-routing` as `truthful-signals-001.md` (Item 1) |
| `-033` | folded | `PLAN-TRUTH-122` D1 — the phase-4 task deriver is a third `test-compile -pl -am` emission site; surface +1 |
| `-034` | folded | `PLAN-TRUTH-119` D3 — TDD prose ordering contradicts `depends_on` (second instance); adds no surface (D3's `phase-4-plan/**` already declared) |
| `-035` | staged | **`PLAN-TRUTH-142`** (new) — `integration-tests` named 4× in `canonical_verify.md` but absent from `canonicals:` |
| `-036` | folded | `PLAN-TRUTH-135` — `consult` resolves the plan dir main-anchored only; a LIVE member for a spec whose original mechanisms were refuted; surface +1 |
| `-037` | folded | `PLAN-TRUTH-105` — clean-tree assertions cannot tell a mutating gate from interference; surface +1 |
| `-038` | discarded | forwarded `code-intelligence-substrate` `-059` (Item 2) — `diff-modules` reports a missing snapshot `derived.json` as `changed` |
| `-039` | discarded | REFUTED at HEAD — `review_completeness` D3 prose uses the live flags; `--settled-bots` removed by #1041 (FYI in `review-apparatus` `-054`) |
| `-040` | folded | `PLAN-TRUTH-129` — "hard-coded literal" REFUTED (0 hits); the notation is authored at allocation → validate at task creation; surface +1 |
| `-041` | folded | `PLAN-TRUTH-122` D3 — trailing Failsafe block, recurrence of `-002` |
| `-042` | folded | `PLAN-TRUTH-105` — `-023` instance closed at HEAD by #1454; Token-Sheriff now declares `build.maven.profiles.mutating` |
| `-043` | folded | `PLAN-TRUTH-117` — criterion total contradicts its own addends; adds no surface |
| `-044` | promoted | lesson **`2026-09-11-15-001`** (merged with `api-sheriff-…-009`) |
| `-045` | folded | `PLAN-TRUTH-129` — A is a recurrence of the declared `auth_failed` funnel; B arity; C invented flag; surface +1 |
| `-046` | folded | `PLAN-TRUTH-122` D1 — degraded pre-push arms (4th plan); no `resolve-test-scope` verb |
| `-047` | discarded | forwarded `review-apparatus` `-054` (Item 2) |
| `-048` | folded | `PLAN-TRUTH-107` — recurrence of `-016`, split at HEAD: pre-push's absence is a RECORDED refusal, self-review/simplify have none; surface +2 |
| `-049` | discarded | forwarded `review-apparatus` `-054` (Item 3) |
| `-050` | discarded | forwarded `review-apparatus` `-054` (Item 4) |
| `-051` | folded | `PLAN-TRUTH-105` — a producer named for the `plan=NO_PLAN` hypothesis; adds no surface (`manage-architecture/` declared) |
| `-052` | staged | **`PLAN-TRUTH-142`** (new) — a phase-5 leaf reports done over an unstaged Step 10a commit |
| `-053` | folded | `PLAN-TRUTH-117` — fixing the cited sites is not closing the class; surface shared with `api-sheriff-…-004` |
| `-054` | folded | `PLAN-TRUTH-119` D1 — both request classifiers read a heading-truncated section; surface +3 |
| `-055` | folded | `PLAN-TRUTH-105` — `analyses_examined` lists `test` when `tests_run: 0` (`_build_shared.py`:870-873); adds no surface |

### ⛔⛔ The `-023` harness half is CLOSED — and this ledger was still saying it is live

**#1454 (`f24b19a51`, 2026-09-08) re-declared `pre-push-quality-gate` as `mutates_source: true`.** The
2026-09-08 drain above and `PLAN-TRUTH-105`'s fold both ruled that remedy out as impossible; it shipped
the same day, and the resume anchor carried "the MECHANISM half is still live, owned by `-105`" for three
days after. Both corrected in place with a pointer. **What did NOT ship is the ledger half**
(`api-sheriff-…-006`): the `kind=build` row carries the POST-churn sha, so a mandated revert of gate churn
leaves a passing verify permanently `stale` — and the `-006` fold in `PLAN-TRUTH-105` had stated that
direction backwards.

### ⭐⭐ Three sender claims were refuted before they could become spec text

`-028` B's precedence diagnosis (the param is read by nothing), `-040`'s "hard-coded second copy" (the
notation occurs nowhere), and `-039` whole (the prose is correct at HEAD). ⇒ **A relayed lesson that
arrives with its own verification table is still a lead** — API-Sheriff's tables held up on every row
checked; Token-Sheriff's un-tabled relays produced all three refutations. That asymmetry is the argument
for the tabled format.

### ⭐ Recurrence counts, for the record — each measures the DELAY, not the defect

The reactor/test-jar shape (`PLAN-TRUTH-122` D1): 4 Token-Sheriff plans + 1 API-Sheriff. `tests_run`
under-report (`-122` D3 / `-105` D0): 3 relays. The `pr_title` light-lane gap: 3 independent sightings
and 2 active local lessons before a spec existed. The `wrong_store` override: re-occurred after the first
relocation.

## ⭐⭐ NEW SIBLING EPIC `next-level` — boundary rule, standing 2026-09-14

Scaffolded and decomposed 2026-09-14 (slug `next-level`, `parallelization_scope: 1`, 4 workstreams, 7
staged plans). Its subject: the asymmetry between how this repository quality-gates its Python and how it
treats its own instruction substrate (157 components / ~175k lines of markdown under
`marketplace/bundles/**`, assertion and no test). **The boundary, stated once so it need not be
re-derived per item:**

- **`truthful-signals` owns** a signal that reads as confident while hiding a caveat — a count that means
  something other than it appears to, a gate that credits an event that never happened, a ledger that
  reports a state it cannot see. The defect is in the **reporting**.
- **`next-level` owns** the substrate that steers the agent, and whether anything measures it — a rule
  nobody has tested, a corpus nobody has evaluated on the runtime it ships to, a resident cost nobody has
  priced, a standard nobody has practised. The defect is in the **absence of an instrument**.
- **The test for the boundary case** (both a missing measurement AND a claim presenting as settled
  without it): does fixing it require BUILDING AN INSTRUMENT? If yes, `next-level`. If the fix is making
  an existing report tell the truth, `truthful-signals`.

**Two retirements already performed (operator-directed, 2026-09-14, before this session):**
`truthful-signals-009` (a corpus-calibration finding, `next-level`'s WS-02 in full) superseded whole by
`next-level-001.md` — resolvable via `inbox validate`, body preserved byte-for-byte, nothing lost.
`truthful-signals-010` split 2/3: findings 4 (PBT standard liveness — vacuous-authority in the testing
standards) and 5 (a working multi-model eval harness, design-input-only prior art) absorbed by
`next-level`; findings 1, 2, 3 stayed here and were dispositioned in this session's drain (see below).

## Inbox drain — 2026-09-17, 14 messages, every one dispositioned (PLAN-TRUTH-166 full ship)

**14 scanned / 14 archived / 0 invalid / 0 archive-failed — genuine EMPTY zero afterward.** One landing
(`complete: true`, no missing keys) plus 13 candidate-lessons: 2 relayed from Token-Sheriff, 11 first-party
from the landing plan. **11 folded, 1 forwarded, 1 promoted, 0 discarded.** Landing analysis:
`landings/PLAN-TRUTH-166.md`.

⭐⭐ **PLAN-TRUTH-166 exercised its own fix during its own finalize** — `discover --force --apply plan`
classified the descriptor delta as `clean` and committed nothing. The strongest control this epic has seen
for a defect class: the plan's own PR carries none of the churn it exists to stop.

| Message | Disposition | Destination / reason |
|---|---|---|
| `…-012.md` (landing) | reconciled | **`PLAN-TRUTH-166` shipped**, PR #1501, merged `e8c3cad5b`. Corroborated first-party against `origin/main` and `ci pr view`. Unblocks `-145`, `-158`, `-167`. |
| `lessons-handling-…-065.md` | folded | **`PLAN-TRUTH-143`** — ⛔ the disjointness gate counts TERMINAL and CLOSED-EPIC specs, so a maturing epic eventually cannot emit. **This orchestrator overrode the same rule on 2026-09-15 (c)** by comparing only in-flight rows. Surface +1. |
| `lessons-handling-…-066.md` | folded | **`PLAN-TRUTH-167`** — confirm-and-close answered: `realized_footprint` is captured at `branch-cleanup`, AFTER review-fix rounds ⇒ superseded on its own key, but its `--base-ref` inherits the staleness D3 fixes. |
| `…-001.md` | folded | **`PLAN-TRUTH-145` D4/D5** — third sighting, first-party: `plan_creation_sha` has no writer; `could_not_look` on all 16 tasks. ⭐ A could-not-look that fires on EVERY invocation is an INERT guard. |
| `…-002.md`, `-004.md`, `-005.md` | folded | **`PLAN-TRUTH-152`** — three retrospective producers publishing a confident figure over an unread population (post-merge empty diff read as "nothing changed"; a MUST its own sibling contract states, violated by the producer; `build_time: 0` where the consumer rule says `unavailable`). |
| `…-003.md` | folded | **`PLAN-TRUTH-167` D3** — promoted HYPOTHESIS → OBSERVED with source lines; the shipped consequence (simplify editing three upstream files) is recorded. Surface +1. |
| `…-006.md` | folded | **`PLAN-TRUTH-147`** — self-seeding MEASURED (55% overall, **79% after round 1**) and the terminating move named: deletion-or-pointer by default from round 2, share published as the stop signal. |
| `…-007.md` | folded | **`PLAN-TRUTH-160`** — the Billing column is empty because no call site passes the flags the recorder already accepts (0 of 13 rows). Surface +2. |
| `…-008.md` | folded | **`PLAN-TRUTH-154`** — an escalation built on the documented DEFAULT (3) while the resolved ceiling was 14; the operator authorized a change nothing needed. |
| `…-009.md` | forwarded | **`review-apparatus`** as `truthful-signals-059.md` — the EXTERNAL review loop re-found its own remediation's residue in 2 of 3 rounds, at an hour per round. |
| `…-010.md` | folded | **`PLAN-TRUTH-153`** — a documented error token no component emits; what is owed is the detector class, with a matched control. Surface +1. |
| `…-011.md` | promoted | Lesson **`2026-09-17-06-001`** — a tolerant read is void when a stricter read of the same artifact runs first on the same path. Instance already fixed in-run; only the rule survives. |

⛔ **Two items outlive the plan.** `finalize-step-simplify` edited three files outside the declared
footprint (all reverted) — the same attribution-scope defect one layer up, now owned by `PLAN-TRUTH-167`
D3 with first-party evidence. The marshalld daemon reconcile was deferred (daemon busy), leaving a
`reconcile-owed` marker on this machine — machine-local operator action, no plan work owed.

⚠ **Unattended-review budget: 1 of 10 waits spent** on this landing's CodeRabbit quota refusal (~96 min).

## Inbox drain — 2026-09-15 (c), 20 messages, every one dispositioned (no landing)

**20 scanned / 20 archived / 0 invalid / 0 archive-failed — genuine EMPTY zero afterward** (`live_count 0`,
no closed senders, `invalid_count 0`). Three passes: 1 operator-selected message (then emitted as
PLAN-TRUTH-166, now RUNNING), 14 queued, and 5 that arrived mid-drain at 18:35Z. Every claim re-grounded
at `7a028157e` unless marked a single-run lead. **2 new specs staged (167, 168), 10 specs folded into,
1 discard, 0 promotions** — every candidate-lesson named a plan-marshall defect or a gap already documented,
none a standing rule the corpus lacks.

⭐ **Two consuming repos (API-Sheriff, Token-Sheriff) independently hit the same four shapes on
`0.1.1670` the same day** — architecture-refresh churn (→166), its self-commit staling push (→158), the
self-review deadlock on a non-plan-marshall diff (→167), and phase-6 cleanup verbs that fail after
`worktree-remove` (→164). Cross-repo recurrence on one version is the strongest priority signal this
drain carries.

| Message | Disposition | Destination / reason |
|---|---|---|
| `api-sheriff-deployment-configurability-010.md` | folded | **`PLAN-TRUTH-149`** — the `orchestrated` verdict has no persisted carrier: emit-landing skips on an EMPTY `epic` input resolved only inside lessons-capture's gate; compose drops the step on *detector unavailable*. D1 makes the loss visible, not reachable. |
| `api-sheriff-deployment-configurability-011.md` | staged | **`PLAN-TRUTH-167`** (new) — no surfacer reads Java; building one recorded out of scope. |
| `api-sheriff-deployment-configurability-012.md` | folded | **`PLAN-TRUTH-145`** — D4/D5 sighting only; `plan_creation_sha` still has no writer. |
| `api-sheriff-deployment-configurability-013.md` | folded | **`PLAN-TRUTH-150`** — no CI verb reads a run by commit; post-merge `main` verification unreachable. Surface +1. |
| `api-sheriff-pro-forma-integration-test-fixes-001.md` | staged | **`PLAN-TRUTH-167`** (new) — selection by resolvability, round-invariant refusal loops to the ceiling, surfacer base = stale local `main`. |
| `lessons-handling-26-09-04-01-056.md` | folded | **`PLAN-TRUTH-147` D9** — light lane never sets `pr_title`; deterministic false-RED. |
| `lessons-handling-26-09-04-01-057.md` | staged | **`PLAN-TRUTH-167`** (new) — second consumer instance of the zero-detector self-review loop. |
| `lessons-handling-26-09-04-01-058.md` | folded | **`PLAN-TRUTH-158`** — a fourth cause: `architecture-refresh` self-commits outside `push.md`'s `mutates_source` membership. Surface +1 ⇒ 158 now sequences behind RUNNING 166. Obs 1 (16 of 20 PR files churn) is recurrence evidence for 166, recorded here, never edited into a running spec. |
| `lessons-handling-26-09-04-01-059.md` | folded | **`PLAN-TRUTH-150` D5** — sixth `tests_run: 0`; miscount vs zero-tests discriminator trap. |
| `lessons-handling-26-09-04-01-060.md` | folded | **`PLAN-TRUTH-150`** — Maven failure-trailer advice filed as blocking `deprecation_warning`. |
| `lessons-handling-26-09-04-01-061.md` | folded | **`PLAN-TRUTH-161` D2** — `manage-adr` template fails `ref-asciidoc`'s header rule. Surface +3. |
| `lessons-handling-26-09-04-01-062.md` | folded | **`PLAN-TRUTH-145`** — `verify:coverage` composed for a test-resource-only change; fan-out lead for 146. |
| `lessons-handling-26-09-04-01-063.md` | folded | **`PLAN-TRUTH-162`** — phase-4-plan rejections, identical retry ignoring the hint. Surface +1. |
| `lessons-handling-26-09-04-01-064.md` | staged | **`PLAN-TRUTH-168`** (new) — `sync-defaults` reverts a deliberate `remove-step` while reporting `added`. |
| `api-sheriff-deployment-configurability-014.md` | folded | **`PLAN-TRUTH-151`** — phase-3-outline transitioned past its own q-gate; three criteria written ahead of evidence (single-run leads). |
| `api-sheriff-deployment-configurability-015.md` | folded | **`PLAN-TRUTH-150` D7** — `files_exist` blind to `depends_on`. Surface +1. |
| `api-sheriff-deployment-configurability-016.md` | folded ×3 | `-009` → **158** recurrence; `-011` harness-blocked `sleep` in `branch-cleanup.md` → **159** (population widened, surface +1); `-012` `prune-local-and-remote-ref` not idempotent → **164 D2**, closing the 2026-09-07 UNOWNED Open Defect (surface +1). |
| `api-sheriff-deployment-configurability-017.md` | discarded | Already documented in `await-long-running.md` — the consumer backgrounded a daemon wait the standard forbids. |
| `api-sheriff-deployment-configurability-018.md` | folded | **`PLAN-TRUTH-151`** — a spec-mandated build flag is a claim class the Verify-First Contract does not name. Adopted by this orchestrator now. |
| `api-sheriff-configuration-security-hardening-001.md` | staged | **`PLAN-TRUTH-166`** (new) — `architecture-refresh` Tier 0 commits tool-migration descriptor churn into an unrelated plan's PR under that plan's name, past `descriptor-regression-check`, which examines only `name`/`description`/`description_reasoning` and publishes no examined-field population. Re-grounded at `7a028157e`: the churn IS tool-caused — the `generation` back-fill and dotted→path `key_packages` re-keying are INTENDED `discover` migrations (`_cmd_manage.py` § `api_discover`). ⛔ **One sender premise REFUTED:** `tree_sha: null` is not confident-but-empty — `unknown_generation()` is the deliberate honest-`unknown` header. Staged, not folded: no staged or live spec in any epic owns this step. Emitted immediately on operator direction. |

## Inbox drain — 2026-09-15 (b), 1 message, dispositioned (no landing)

**1 scanned / 1 archived / 0 invalid** — genuine EMPTY zero afterward. Self-filed orchestrator finding,
surfaced while `cleanup` was mid-run and correctly left undrained by that pass (draining is `analyze`'s
job, not `cleanup`'s).

| Message | Disposition | Destination / reason |
|---|---|---|
| `truthful-signals-011.md` | staged | **`PLAN-TRUTH-165`** (new) — `detect-suspicious` reports `suspicious_count: 0` on an allow list with a mid-command wildcard that silently over-grants, because `SUSPICIOUS_PATTERNS` covers only dangerous-target regexes, never malformed grammar; `claude_runtime.py`'s deny-rule renderer independently flags the same hazard class the allow-rule inspector misses entirely. Triggering rule already fixed in place. |

## Inbox drain — 2026-09-15, 99 messages, every one dispositioned (PLAN-TRUTH-148 + PLAN-TRUTH-157 double full ship)

**99 scanned / 99 archived / 0 invalid** — genuine EMPTY zero afterward. Two simultaneous plan landings
(`plan-truth-148`: 63 candidate-lesson + 1 landing; `plan-truth-157`: 31 candidate-lesson + 1 landing) plus
3 stragglers (`adhoc-token-economy-analysis`: 2 findings; `review-apparatus-041`: 1 cross-epic transfer
bundling 18 items from `next-level`'s own boundary sweep).

PR #1488 verified first-party via `ci pr view` (found via `ci pr list --head feature/plan-truth-148`,
since the landing message's own `pr=` claim was not trusted on its own): `state=merged`,
`merge_commit_sha=db0ae63464f1…`. PR #1494 verified first-party: `state=merged`,
`merge_commit_sha=ab86d7cbfeb7f9…` (sha reused from this session's own earlier corroboration at that
landing's paste). Both `landing-check`: `complete: true`. `landings/PLAN-TRUTH-148.md` and
`landings/PLAN-TRUTH-157.md` written — full deliverable fidelity, metrics/anomalies, and per-message
disposition detail live there; this entry summarizes.

**6 promoted (3 lessons) · 15 folded · 2 staged as evidence into one shared spec (verb-paraphrase) · 2
staged as new independent specs (adhoc findings) · 1 staged as a deferred-defect follow-up · 1 forwarded to
`review-apparatus` · 1 distributed fold (the `review-apparatus-041` transfer, across 8 targets) · 64
discarded (self-resolved self-review/process-note artifacts, recurrences of already-tracked archetypes) ·
2 landing messages reconciled.**

| Cluster | Messages | Disposition |
|---|---|---|
| Self-review loop-cost / no convergence signal (both plans, same day) | `148`-001, `157`-002 | Fold → `PLAN-TRUTH-147` |
| Post-merge empty-diff false FAIL (3rd sighting) / plan-retrospective measurement bugs | `148`-002, `157`-001,003 | Fold → `PLAN-TRUTH-152` |
| Build-time oracle blind to 96 real builds / 15s-timeout misclassified as `argparse_rejection` | `148`-003,062 | Fold → `PLAN-TRUTH-150`, Expected Surface += `manage-change-ledger/**` |
| Outline declared-intent vocabulary gap / outline-refine self-review cluster (4 sub-findings) | `148`-004, `157`-008–012 | Fold → `PLAN-TRUTH-151` |
| Per-step token record gap / finalize dispatcher prompt-body bug / terminal-step token gap | `148`-005,006, `157`-004,007 | Fold → `PLAN-TRUTH-149` |
| Verb-paraphrase / invented-flag population (23 failures across both plans) | `148`-007,055–061,063, `157`-006,028–031 | **Staged → PLAN-TRUTH-162** as evidence, upgrades Watch **W-1483-b** (population threshold now met) |
| Self-review misreads coarse roster label as blocking every sub-step | `148`-008 (dup 013) | **Promoted** — lesson `2026-09-15-06-001` |
| Self-review guard/control-authoring pitfalls (6 distinct vacuity/scoping shapes + negation-scope) | `157`-013,016,017,021,022,024,026 | **Promoted** — lesson `2026-09-15-06-002` |
| Hardcoded roster/surface list drifts from its own live source (found from both directions) | `148`-048, `157`-027 | **Promoted** — lesson `2026-09-15-06-003` |
| `architecture search --category` vs `--module` doc-usability nit | `157`-005 | Discarded — minor, no defect |
| `automatic-review` closed `done` with a refused-structural reviewer un-triaged | `148`-054 | Forwarded → `review-apparatus` (`truthful-signals-058.md`) |
| Self-resolved self-review artifacts, all `resolution: fixed`/`rejected`/process-note | `148`-009-012,014-047,049-053, `157`-014,015,018,019,020,023,025 | Discarded — recurrences of already-tracked archetypes (`2026-09-05-16-001` pointer-not-restatement; WS-10 doc-contract-divergence; derive-completeness-never-assert-it; `plan-orchestrator` process lessons), self-resolved within each plan's own run, nothing owed |
| `review-apparatus-041` (18-item transfer, `next-level`'s boundary sweep) | 1 message | Distributed fold: `PLAN-TRUTH-145` (§B-001,§B-004), `PLAN-TRUTH-150` (§B-020), `PLAN-TRUTH-151` (§C-019), `PLAN-TRUTH-152` (§C-002), `PLAN-TRUTH-153` (§C-016,§C-018), `PLAN-TRUTH-154` (§A-014,§C-015) |
| Billing (cost) column undercounts output 5×, ten non-comparable figures in one column | `adhoc-token-economy-analysis-001` | **Staged → PLAN-TRUTH-160** (new) — read in full and corroborated on its merits, not discarded for an unfamiliar sender |
| ADR number allocation reads the local tree, two branches collide invisibly | `adhoc-token-economy-analysis-002` | **Staged → PLAN-TRUTH-161** (new) — likewise corroborated on its merits |
| Two deferred dispatch/write-grant-detector defects (`00d610`, `9a819a`) at `157`'s own loop-back ceiling | (named in `157`'s own landing, not a separate inbox message) | **Staged → PLAN-TRUTH-163** (new) |
| `148`-064, `157`-032 | landing messages | Reconciled — see Reconciliation Actions in each `landings/` file |

Residue named in the landings but not filed as separate messages: PLAN-TRUTH-147 gains fresh evidence its
D6/convergence-signal fix needs observation under a real loop-back-heavy run, not yet exercised (both
landings' own self-review anomalies recurred despite that fix having shipped earlier in this epic).

## Inbox drain — 2026-09-14, 5 messages, every one dispositioned (no landing)

**5 scanned / 5 archived / 0 invalid** — genuine EMPTY zero afterward. Sources: `next-level` (1,
existence notice), `review-apparatus` (2, cross-epic transfer), `truthful-signals` itself (2, an
operator-directed analysis this epic's own orchestrator filed and later split against the boundary
above).

| Message | Disposition | Destination / reason |
|---|---|---|
| `next-level-001.md` | absorbed | Records the boundary rule and the two prior retirements (see section above) |
| `truthful-signals-009.md` | retired by successor | `lifecycle=superseded`, already absorbed whole by `next-level-001.md` |
| `truthful-signals-010.md` (rev 3) | folded ×3 | finding 1 (doc-consistency enforced only at finalize) → `PLAN-TRUTH-147`; finding 2 (approval inferred from absence of objection, un-enumerated population) → `PLAN-TRUTH-154`, surface extended; finding 3 (operator decisions during execute have no write-back channel) → `PLAN-TRUTH-151`, surface extended |
| `review-apparatus-039.md` | staged | **`PLAN-TRUTH-159`** (new) — `project:finalize-step-deploy-target` documents `./pw generate-claude`, denied by hook rule R4, documented recovery is a dead end |
| `review-apparatus-040.md` | folded | `PLAN-TRUTH-150` — a gate build row's `worktree_sha=None` is harmless by convention, not invariant; dropped by `plan-pr-046` and carried nowhere until this transfer |

**Sweep result, per `next-level-001.md`'s own request: zero further candidates.** Every one of the 15
staged specs (143–147, 149–156, 158, 159) had its full Objective re-read against the boundary rule above.
Every one is reporting/detection-correctness shaped — a confident signal hiding a caveat, a record
diverging from reality, a producer claiming success over something it never checked — matching this
epic's own theme. None proposes adversarial rule-testing, cross-model behavioural evaluation,
resident-context-cost measurement, or PBT-standard-liveness derivation (`next-level`'s WS-01…WS-04). No
`inbox write` performed beyond the two retirements already done by the prior session. This sweep need not
be re-run on the unchanged 15; only a newly-staged or newly-folded spec needs checking against the
boundary going forward.

## Inbox drain — 2026-09-13 (b), 5 messages, every one dispositioned (PLAN-TRUTH-127 full ship)

**5 scanned / 5 archived / 0 invalid** — genuine EMPTY zero afterward. Four `candidate-lesson` from
`plan-truth-127`, one `landing`. A fifth message (`review-apparatus-038.md`, a cross-epic transfer from
`review-apparatus` bundling 5 items from `plan-pr-046`'s own landing) arrived independently mid-drain and
was drained in the same pass.

PR #1483 verified first-party via `ci pr view` (`state=merged`, `merge_commit_sha=c38342609a1af…`, matches
both the paste and the landing message). Landing `landing-check`: `complete: true`.
`landings/PLAN-TRUTH-127.md` written.

**3 promoted · 1 staged (new spec) · 3 folded (from the review-apparatus transfer) · 1 absorbed as a
Watch · 1 forwarded to review-apparatus.**

| Message | Disposition | Destination / reason |
|---|---|---|
| `plan-truth-127-001` | promoted | lesson **`2026-09-13-20-002`** (`marshall-steward`) — `drift --marketplace` publishes a count with no stated population; self-caught, finding `4adc50` withdrawn as `rejected` |
| `plan-truth-127-002` | promoted | lesson **`2026-09-13-20-003`** (`ext-self-review-plan-marshall`) — a plan whose subject IS a defect archetype shipped that exact defect twice inside its own fix (`af0a4d`, `9e4ff2`), neither caught by the deterministic surfacer; proposes a self-application pass |
| `plan-truth-127-003` | promoted | lesson **`2026-09-13-20-004`** (`plan-retrospective`) — three could-not-look discriminators hidden outside the payload (build_time docstring; review-body field mismatch; `UNTOUCHED_PHASE_STATUSES` prose). Instance 2 (review-body) ALSO forwarded to `review-apparatus` per the plan's own routing note |
| `plan-truth-127-004` | staged | **`PLAN-TRUTH-158`** (new) — push.md's freshness-reconciliation refusal names a specific cause (un-built source drift) from an ambiguous absence that the same contract can also produce two other ways |
| `review-apparatus-038` item 1–2 | folded | `PLAN-TRUTH-152` — post-merge empty-diff graded FAIL over an unobservable state; `permission-prompt-analysis` empty-list design question |
| `review-apparatus-038` item 3 | folded | `PLAN-TRUTH-147` — `pre-submission-self-review` fired 7×/6 loop-backs with no computed convergence signal |
| `review-apparatus-038` item 4 | folded | `PLAN-TRUTH-145` — finalize never calls the `reconcile-scope` detector it already has; 3rd consecutive `review-apparatus` landing exceeding its declaration |
| `review-apparatus-038` item 5 | absorbed | Watch **W-1483-b** — verb-paraphrase argparse rejections, needs a population before action |

Residue named in the landing but not filed as separate messages: `353313` (re-entry marker reports zero
on a run with four re-entries — Open Defect, recurrence against shipped PLAN-TRUTH-101); `ac1774`
(`manage-lessons consult` unrunnable post-move — Open Defect); plugin-doctor scoped-gate coverage gap
(Watch **W-1483-a**); the status.json↔metrics cross-ledger reconciliation (deferred, cross-referenced to
PLAN-TRUTH-146's sequencing, not re-staged).

## Inbox drain — 2026-09-13, 7 messages, every one dispositioned (PLAN-TRUTH-139 full ship)

**7 scanned / 7 archived / 0 invalid** — genuine EMPTY zero afterward (0 live, `closed_senders` empty,
`invalid_count: 0`). One sender, `plan-truth-139`: 6 `candidate-lesson` + 1 `landing`.

PR #1479 verified first-party via `ci pr view` (`state=merged`, `merge_commit_sha=d931d8baa9477…`, matches
both the paste and the landing message's `pr=#1479`/`merge_state=merged`). Landing `landing-check`:
`complete: true` — all 9 required keys present with real values. `landings/PLAN-TRUTH-139.md` written.

**2 promoted · 1 staged (new spec) · 1 folded · 2 discarded (forwarded to `review-apparatus`).**

| Message | Disposition | Destination / reason |
|---|---|---|
| `plan-truth-139-001` | promoted | lesson **`2026-09-13-14-001`** (`recipe-security-audit`) — the audit's own report-boundary sweep enumerated its population instead of deriving it; found 4 of 5 unsanitised boundaries, CodeRabbit found the 5th (`266f33`) |
| `plan-truth-139-002` | promoted | lesson **`2026-09-13-14-002`** (`plan-marshall:plan-marshall`, anti-pattern) — a triage FIX task that flips a claim's truth conditions must assert both directions (matched pre/post control); two of this run's own fixes introduced the inverse of the defect they closed (`574fd5`, `9c441d`), both caught only by the reviewer |
| `plan-truth-139-003` | staged | **`PLAN-TRUTH-156`** (new) — `mark-step-done` accepts `head_at_completion` from the caller instead of deriving it; this run self-caught a FABRICATED sha (padded short-hash) before it shipped, logged at WARNING (`858d9c`) |
| `plan-truth-139-004` | folded | `PLAN-TRUTH-150` — temp residue poisons the adaptive learned build duration, which silently re-tiers canonicals to `execution_tier: orchestrator` when the learned `bash_timeout_seconds` crosses the leaf ceiling; surface unchanged (already covered) |
| `plan-truth-139-005` | discarded | forwarded to `review-apparatus` as `truthful-signals-056.md` (Item 1) — `review_body_summary_patterns` classifies a whole body meta by its opening line, hiding a Major (`f7de42`) that arrived as an outside-diff comment |
| `plan-truth-139-006` | discarded | forwarded to `review-apparatus` `-056` (Item 2) — the gate/review delta instrument is structurally excluded on every PR this repo's finalize ordering touches; re-fire `pre-push-quality-gate` after the `mutates_source` steps that follow it |
| `plan-truth-139-007` | reconciled | full ship — see Reconciliation Actions in `landings/PLAN-TRUTH-139.md` |

Residue named in the landing but not filed as separate messages: `367874` (Sonar `count_status: confirmed`
with zero new-code issues, but NO Sonar analysis has ever run for this PR — an empty-surface zero,
structurally indistinguishable from a clean scan; recorded as a Watch below, recurs on every plan until
Sonar is wired into PR CI); `409263` (`triage.md` prescribes `deliverable: 0` for a FIX task, which the
validator rejects — a RECURRENCE of already-filed lesson `2026-09-06-09-002`, not a new item); `805bc7`
(in-process build env inheritance, declined by the plan itself as out-of-footprint — no action).

## Inbox drain — 2026-09-21, 20 messages, every one dispositioned (ledger relocation to `.plan/orchestrator/`)

**9 staged (4 new specs) · 11 promoted (global lessons corpus).**

| Message | Disposition | Destination / reason |
|---|---|---|
| `truth-143-...-001` | staged | **`PLAN-TRUTH-174`** D1 — `extract-chat-signal` truncates `reduced_transcript` in a lossy TOON re-parse |
| `truth-143-...-004` | staged | **`PLAN-TRUTH-174`** D2 — `outline-vs-shipped` reports `comparison: measured` over an absent assessment store |
| `truth-143-...-002` | staged | **`PLAN-TRUTH-175`** D1 — `boundary_monotonicity` reports zero violations over a crossed 1h36m phase boundary |
| `truth-143-...-003` | staged | **`PLAN-TRUTH-175`** D2 — 41 of 77 finalize dispatch-boundary rows record structural zero tokens, not unmeasured |
| `truth-143-...-007` | staged | **`PLAN-TRUTH-175`** D3 — `context_position_cost` measured 0 of 98 dispatch rows on a 14.4M-token plan |
| `truth-143-...-005` | staged | **`PLAN-TRUTH-175`** D4 — 8 of 15 token-proven dispatched finalize steps emit no `[DISPATCH]` line |
| `truth-143-...-006` | staged | **`PLAN-TRUTH-175`** D5 — build-time oracle holds no row for a plan with 139 logged build calls |
| `truth-143-...-008` | staged | **`PLAN-TRUTH-176`** (new) — pre-flight invocation validator; 41 script-call failures, 16 argparse rejections on one plan |
| `post-run-quality-001` | staged | **`PLAN-TRUTH-177`** (new) — forwarded from `post-run-quality`: `phase-1-init` writes no `source_id` for description-sourced plans, orchestration detection fails open |
| `truth-143-...-009` | promoted | lesson **`2026-09-21-10-002`** — hand-maintained doc enumeration of a code-declared set |
| `truth-143-...-010` | promoted | lesson **`2026-09-21-10-003`** — a round-loop fix can self-seed the next instance of its own defect class |
| `truth-143-...-011` | promoted | lesson **`2026-09-21-10-004`** — coverage figures re-derived in transit produce structurally impossible zeros |
| `truth-143-...-012` | promoted | lesson **`2026-09-21-10-005`** — self-review findings go stale against a moving HEAD |
| `truth-143-...-013` | promoted | lesson **`2026-09-21-10-006`** — a population-derived guard walking one document under-covers a roster split across two |
| `truth-143-...-014` | promoted | lesson **`2026-09-21-10-007`** — a deliverable named the dispatch wrapper, not the defining module |
| `truth-143-...-015` | promoted | lesson **`2026-09-21-10-008`** — positive pattern: do not back-fill an empty assessment population to make a validator pass |
| `truth-143-...-016` | promoted | lesson **`2026-09-21-10-009`** — a publisher and its registration row are one edit |
| `truth-143-...-017` | promoted | lesson **`2026-09-21-10-010`** — an idempotent-success path must observe a complete marker (bug already fixed in PR #1539 TASK-020, lesson records the rule) |
| `truth-143-...-018` | promoted | lesson **`2026-09-21-10-011`** — a guard's stated scope must be derivable from its mechanism (frozenset within-set vacuity, already fixed in same PR) |
| `truth-143-...-019` | promoted | lesson **`2026-09-21-10-012`** — publishing an indeterminacy count is not enforcing it (`candidates_indeterminate`, already fixed in same PR, TASK-025) |

Also this pass: relocated `epic.md`/`status.json` drift from the day-old tracked snapshot at #1558 into
the tracked `.plan/orchestrator/` location (the only two files that had drifted). Discovered a platform
gotcha worth its own future finding: `orchestrator queue --add-row` / `inbox archive` / `manage-logging
decision` / `resume-summary` resolve their read AND write target to the MAIN checkout regardless of actual
cwd, even when invoked from a worktree with its own copied executor — only `git` itself and the `Write`
tool correctly targeted this worktree. Worked around by mirroring main's post-write state into the
worktree and reverting main to clean after each affected call.

## Inbox drain — 2026-09-22, 1 message, 18 items dispositioned (no landing)

**1 scanned / 1 archived / 0 invalid / 0 archive_failed.** One message, `lessons-handling-26-09-22-01-001.md`,
bundling 18 candidate-lessons. ⛔ **7 of the 18 were this epic's own 2026-09-21 promotions round-tripped
back to it** with their corpus copies then deleted by the sender's integrate-then-remove step — see Open
Defects, forwarded to `lessons-routing`. All 7 restored to the corpus as `2026-09-22-07-001..007`.

| Item | Disposition |
|---|---|
| `2026-09-21-10-003` (self-seeding fix) | discard, boomerang → restored `2026-09-22-07-002`; already folded into `PLAN-TRUTH-147` (2026-09-17) + `PLAN-TRUTH-173` D0 |
| `2026-09-21-10-005` (self-review staleness) | discard, boomerang → restored `2026-09-22-07-003`; already folded into `PLAN-TRUTH-173` D2/D3 + `PLAN-TRUTH-167` D2 |
| `2026-09-19-21-006` (monkeypatch vacuity) | discard here → forwarded to `test-quality` (`truthful-signals-001.md`), ambiguous owner vs local `PLAN-TRUTH-153` |
| `2026-09-21-10-009` (publisher/registration edit) | discard, boomerang → restored `2026-09-22-07-006`; weakest-covered, no confirmed staged owner (nearest: `PLAN-TRUTH-173` D1/D3) |
| `2026-09-21-10-011` (frozenset within-set vacuity) | discard, boomerang → restored `2026-09-22-07-007`; fully covered by `PLAN-TRUTH-153` D9, already fixed same PR (#1539) |
| `2026-09-21-10-006` (roster split across two docs) | discard, boomerang → restored `2026-09-22-07-004`; covered by `PLAN-TRUTH-153` D9/D0 |
| `2026-09-21-10-007` (deliverable named wrapper not module) | discard, boomerang → restored `2026-09-22-07-005`; no confirmed owner (LOW-CONFIDENCE: `PLAN-TRUTH-151` D0 / `code-intelligence-substrate`) |
| `2026-09-21-13-003` (manage-lessons set-body header) | folded → **`PLAN-211` D3** — named mechanism REFUTED at HEAD (`set_body` fails closed, cannot destroy header), subject live: the 4 headerless lessons below ARE fresh population for D3's claim |
| `2026-09-19-21-005` (verification-command mismatch) | recurrence, verbatim already inside `PLAN-TRUTH-151`'s § FOLDED 2026-09-15 (c) — no edit, no restage |
| `2026-09-20-08-011` (suspicion heuristic vs orchestrated specs) | folded → **`PLAN-214` D1** — definitively NOT `PLAN-TRUTH-151` (opposite prescription, already-accepted corpus learning there); cross-ref `orchestrator-refactor`'s Watch for the derived population, do not re-derive |
| `2026-09-20-07-001` (deploy-target doc/hook mismatch) | folded → **`PLAN-TRUTH-162` D3** — recurrence, routing hazard avoided (NOT `PLAN-TRUTH-159`, which is RETIRED/merged into 162) |
| `2026-09-20-07-002` (sync-plugin-cache stale notation) | folded → **`PLAN-TRUTH-162` D3/D4** — corroborated first-party at `7d82d5d90` (live notation run reproduced the rejection); D4 design note: `.claude/**` is outside the architecture inventory |
| `2026-09-21-10-002` (doc enumeration drift) | discard, boomerang → restored `2026-09-22-07-001`; covered by `PLAN-TRUTH-153` D8/D9 + `PLAN-TRUTH-173` |
| `2026-09-20-08-007` (footprint capture pre-rebase) | folded → **`PLAN-TRUTH-167` D3** — ⚠ RE-GROUND before launch: PR #1559 (`fca06c4ca`, `orchestrator-refactor`) may already ship the upstream-base half; surviving residue is narrower (merge-commit re-derivation specifically) |
| `2026-09-21-08-001` (PR-diff-size gate) | discard here → forwarded to `review-apparatus` (`truthful-signals-061.md`, primary, per standing dispatcher rule) + `code-intelligence-substrate` (`truthful-signals-061.md`, secondary, publish half) |
| `2026-09-21-08-002` (sweep population re-derivation) | discard — code residue already routed to `code-intelligence-substrate` by the lesson's own text; rule half too thin (LOW-CONFIDENCE) to warrant a spec edit |
| `2026-09-21-08-003` (done vs pending findings ledger) | folded → **`PLAN-TRUTH-146` D8/D9** — ⚠ possible duplicate of `review-apparatus` cross-notice `truthful-signals-058.md` (2026-09-15 drain), check before launch |
| `2026-09-21-08-004` (PR pointer names dead PR) | folded → **`PLAN-TRUTH-170` D0/D1** (surface +1: `create-pr.md`) — consumer half split to **`PLAN-TRUTH-174` D2**, sequence 170 → 174 |

All 18 drafted by dispatched `execution-context-level-5` (role `orchestrator.analyze`), corroborated and
applied by the orchestrator. Zero queue rows staged/retired this pass — every disposition landed as a fold
into an existing staged spec, a discard, or a cross-epic forward; no `queue --add-row` was warranted.

## Open Defects

### 2026-09-22 — `7d82d5d90`: lessons-handling round-tripped this epic's own one-day-old promotions back to it, then deleted the corpus copies

**FORWARDED to `lessons-routing`** (cross-notice `truthful-signals-002.md`, that epic's inbox). Draining
message `lessons-handling-26-09-22-01-001.md` (18 bundled candidate-lessons), 7 of the 18
(`2026-09-21-10-002`, `-003`, `-005`, `-006`, `-007`, `-009`, `-011`) turned out to be THIS epic's own
promotions from the 2026-09-21 drain — a lessons-handling triage pass found them one day old and still
`active` in the global corpus, matched them to this epic's theme, and re-routed them back here as if new.
The sender's closing claim ("none `already-covered`") was false for all 7. Per the mode's
integrate-then-remove ordering, the corpus copies were then deleted once the message was confirmed queued
— silently inverting a deliberate promotion into a deletion. `manage-lessons list` returned `total: 0` at
discovery. **Restored all 7 verbatim** from the still-archived source (`inbox/archive/
truth-143-orchestrator-inbox-delivery-path/*.md`, which the delete-then-reroute never touched) as fresh
lessons `2026-09-22-07-001` through `-007`. No fix staged on this side — the routing/dedup gap belongs to
`lessons-routing`, forwarded per the standing dispatcher convention.

### 2026-09-22 — `7d82d5d90`: `corpus cross-check`'s live-plan scan never excludes the `NO_PLAN` sentinel, so `candidate_comparison_determinate` is structurally false on every `next` run in this checkout

**UNOWNED.** Root-caused ground-truth (not from the flagging paste alone — verified directly): `_live_plan_records()`
(`plan-orchestrator/scripts/orchestrator.py:3339`) enumerates every active plan via `_iter_active_plan_dirs()`
(`manage-status/scripts/_cmd_sibling_collision.py:129`), which includes ANY directory under `.plan/local/plans/`
carrying a `status.json` file — with no exclusion for `.plan/local/plans/NO_PLAN`, the "plan-less operations
sentinel" directory (`metadata.sentinel: true` in its own `status.json`). Confirmed: `NO_PLAN/status.json` exists,
is a regular file, not a symlink — it passes every admission check `_iter_active_plan_dirs` applies. Grepped both
files for `sentinel`/`NO_PLAN` — no filter exists; the one `sentinel` hit in `_iter_active_plan_dirs`'s own
docstring ("directories carrying a `status.json` sentinel are included") is an unrelated use of the word (status.json
as a presence marker), not a NO_PLAN exclusion, which reads as handling on a skim but isn't.

Because `NO_PLAN` carries no `references.json`, `_read_affected_files` returns an empty set, so
`_live_plan_records` flags it `comparable: False` — it lands in `corpus cross-check`'s `live_indeterminate_plans[]`
on every single invocation, in every epic, permanently (the sentinel directory is a fixture, not a transient state).
That makes `candidates_indeterminate >= 1` for `candidate_kind: live_plan` unconditionally, which per
ADR-019's fail-closed rule sets `candidate_comparison_determinate: false` — the `next` verb's third disjointness
conjunct ([orchestrate.md § Step 4](../../plan-orchestrator/workflow/orchestrate.md)) can therefore never pass
on its own reading in this checkout; every emit that has ever cleared it did so on an operator override (as the
2026-09-22 paste describes) or went unnoticed. Fix belongs in `_iter_active_plan_dirs` (or `_live_plan_records`):
skip a plan dir whose `status.json` carries `metadata.sentinel: true`, or hard-code the `NO_PLAN` name exclusion.
No spec currently owns this.

### 2026-09-21 — `74153664d`: cleanup A1 re-grounding found 5 staged specs blocking on refuted pointer claims

**UNOWNED.** Dispatched corroboration re-grounded all 30 live specs' verify-first claims against HEAD
(78 claims across 22 specs; 8 specs had none unsettled). Verdict tally: 27 corroborated, 45 unverifiable
(never blocks), 6 contradicted. The 6 contradicted claims are all "pointer" claims — a spec's own
Claim Labels asserting that another spec's referenced findings all hold — and in each case the pointed-to
spec's OWN persisted verdicts now include at least one `contradicted` entry, so the blanket assertion is
false. Stamped `rescoped: no` (honest, not yet re-scoped), which correctly BLOCKS these 5 specs from
`next` emission until someone reads the pointed-to spec's contradiction and updates the citing spec's
claim in place: **PLAN-TRUTH-145** (2 blocking claims, pointing at -136 and -138), **PLAN-TRUTH-146**
(pointing at -124, which itself has FOUR contradicted verdicts), **PLAN-TRUTH-150** (pointing at -105),
**PLAN-TRUTH-153** (pointing at -112). (PLAN-TRUTH-152's contradicted claim is moot — that spec was
found duplicate of `post-run-quality` PLAN-PRQ-01 in the same pass and transitioned to `transferred`.)
No spec currently owns doing this re-scope work; it is cheap per-spec (read the one pointed-to
contradiction, narrow or correct the claim) but touches 4 specs authored well before this HEAD.

### 2026-09-21 — path drift and unreachable evidence found in the same A1 pass

**UNOWNED, informational.** Two residue findings from the same re-grounding dispatch, neither blocking:
(1) every pointer/lesson citation across the corpus still reads the pre-relocation path
`.plan/local/orchestrator/truthful-signals/...` — the live tree is `.plan/orchestrator/truthful-signals/...`
(confirmed: files exist at the new path under every cited name). Cosmetic in evidence text only, but
worth a mechanical sweep next time any of these specs are touched. (2) **PLAN-TRUTH-175**'s entire
evidentiary basis (5 of 5 claims) rests on PLAN-TRUTH-143's own retrospective artifacts
(`work/metrics.toon`, dispatch-boundary TOON, etc.) — that plan's directory no longer exists on disk
(archived, and no `.plan/local/archive/` tree exists in this checkout either), so those figures can
never be independently re-derived; only `landings/PLAN-TRUTH-143.md`'s own restatement survives. A
launched plan implementing -175 should treat those figures as unverifiable leads, not re-derivable facts.

### 2026-09-20 — `1c56734`: a dispatched terminal finalize step can run without the runtime inputs its own contract declares, one step before an irreversible action

**UNOWNED.** Surfaced at `PLAN-TRUTH-143`'s own landing (PR #1539). The dispatch running `emit-landing`
did not carry the `orchestrated`/`epic` runtime inputs the step body declares as dispatcher-resolved.
Taking the step's own guard literally (fail-closed on missing inputs) would have emitted **no landing at
all**, immediately before `archive-plan` destroys the plan directory — a silent, unrecoverable loss of the
epic hand-off. The plan worked around it by re-deriving its epic from `request.md`'s `source_id` via
`orchestrator inbox detect` rather than trusting the declared dispatcher-resolved inputs. The guard's
fail-closed posture and the irreversibility of the very next step point in opposite directions; this is a
genuine gap in the finalize step contract, not an operator error, and the workaround is plan-specific
rather than a general fix. No spec currently owns this. See `landings/PLAN-TRUTH-143.md` § Follow-Ups.

### 2026-09-13 — `353313`: the re-entry marker reports zero re-entries on a run that re-entered four times

**UNOWNED, recurrence against SHIPPED PLAN-TRUTH-101.** Surfaced at PLAN-TRUTH-127's landing (PR #1483).
`manage-metrics generate` reported `re_entered_phases: []` on a run that re-entered `3-outline` three times
and `5-execute` once, every one through `set-phase`, which writes the `loop_back_reentry` marker. Same
family as `documented-invocations-...-003` (already shipped as PLAN-TRUTH-101, which addressed the
phase-5 path specifically) — this recurrence shows the gap is not phase-specific, and a joint fix across
every phase is likely cheaper than another single-phase patch. No spec currently owns this.

### 2026-09-13 — `ac1774`: `manage-lessons consult` is structurally unrunnable once a plan directory moves into its worktree

**UNOWNED.** Surfaced at PLAN-TRUTH-127's landing (PR #1483). `manage-lessons consult` reads main's slot
and returns `outline_not_found` once a plan directory has moved into its worktree — an agent treating
that as "nothing surfaced" would publish a clean Lessons Consulted section over a consult that never
looked. No spec currently owns this.

### ⛔⛔ 2026-09-07 — DISPATCH WAS BLOCKED MID-FINALIZE AND THE TOPOLOGY CHANGED SILENTLY

**UNOWNED.** On `PLAN-TRUTH-125`'s finalize, **agent dispatch and `SendMessage` were blocked by the
session's permission classifier**, so `branch-cleanup`, the retrospective **and everything after ran
INLINE rather than under their dispatch envelopes.**

⛔⛔ **The steps completed, and their `[OK]` rows are INDISTINGUISHABLE from enveloped runs.** Every
per-dispatch measurement for those steps is **absent rather than zero**, and the tail's cost figures are
not comparable with earlier landings'. ⇒ **A topology change that alters what is measurable was
invisible in the step record.**

⚠ **The operator flagged it as possibly unintentional**, which is the other half: if the block was a
misconfiguration, nothing in the run would have said so. ⭐ **The run disclosed it; the machinery did
not.**

### ⛔ 2026-09-07 — `prune-local-and-remote-ref` IS NOT IDEMPOTENT AGAINST ITS OWN SIBLING

✅ **OWNED since 2026-09-15 (c) by `PLAN-TRUTH-164` D2** — second independent sighting from API-Sheriff PR
#305 (`api-sheriff-deployment-configurability-016.md` § `-012`). Original entry follows.

**UNOWNED.** `worktree-remove` deletes the local branch; `prune-local-and-remote-ref` then **hard-errors
on the missing branch, ABORTS, and never reaches the remote-tracking ref** — precisely the stale ref it
exists to remove. Verified against the remote (`git ls-remote` empty while `show-ref` still resolved)
and removed by hand.

⇒ **Two independent problems, either benign alone**: (1) a cleanup verb whose precondition its own
sibling routinely destroys treats *already gone* as an error rather than a no-op; (2) it **fails fast
across INDEPENDENT operations**, so one failure suppresses an unrelated remaining one.


### ⛔⛔⛔ 2026-09-06 — A SESSION-INJECTED COMMIT TRAILER DISPLACES THE CONFIGURED RESOLVER, AND IT IS LIVE IN THIS ORCHESTRATOR'S OWN SESSION

**UNOWNED. Relayed as `review-apparatus-033` item 3 (`-005`), and CONFIRMED FIRST-PARTY AGAINST THIS
SESSION rather than taken as a report.**

The repository's authority is unambiguous. `CLAUDE.md` states the resolver is authoritative and that
the trailer **names the SYSTEM that produced the commit, never the assistant or vendor behind it**, with
*"no assistant name, no context window, no marketing claims."* The resolver agrees:

```text
run_config commit-trailer get
  -> Co-Authored-By: plan-marshall <noreply@cuioss.de>   (name_source: default, email_source: default)
```

⛔⛔ **And this session's own instructions carry a later block that overrides it**, instructing every
commit to end with an assistant-and-vendor trailer naming a model and its context window — **precisely
the three things `CLAUDE.md` forbids by name.**

⭐⭐⭐ **THIS IS NOT A HISTORICAL REPORT. It is live in the environment that just ran this cleanup**, and
the orchestrator authored no commit only because the prime directive forbids it. **Any assistant session
that DOES commit here inherits the displacement silently** — the trailer is written from the injected
value, the resolver is never called, and nothing compares the two.

⛔ **The failure mode is the epic's archetype at the attribution layer:** a configured, resolvable,
authoritative value exists; a second source overrides it; **and no mechanism reads both.** A commit
carrying the wrong trailer is well-formed, passes every gate, and is indistinguishable at review from a
correct one.

⚠ **Deliberately NOT staged as a spec this pass.** The remedy is contested in a way the ledger cannot
settle: it is either a `format-commit`-side check (compare the about-to-be-written trailer against
`commit-trailer get` and refuse a mismatch) or a session-configuration fix outside the repository
entirely. ⇒ **Operator decision owed.** ⭐ The cheap half is available today regardless: **a commit-time
assertion that the trailer equals the resolver's value costs one call and closes the silent path.**



#### ⛔⛔⛔ SHARPENED 2026-09-07 — THE ESCALATION IS THE DEFECT, AND IT HAS NOW FIRED **FIVE** TIMES

A second machine hit it again and the operator asked the right question: *"Any idea why I was asked at
all? It is the fifth time, although even the question itself states that it is defined."*

**It is not over-caution. The agent has no ranking rule, and the document supplies the wrong one.**

⛔ **CLAUDE.md § Commit Trailer states the rule ABSOLUTELY and is SILENT ON CONFLICT.** *"Every commit
… ends with exactly this trailer, and nothing else by way of attribution."* Verified: **there is no
precedence clause anywhere in that section**, and the only `supersede` language in the whole file
belongs to the unrelated `doc/plans/` lane carve-out.

⛔⛔ **AND THE SECTION'S OWN OVERRIDABILITY CLAUSE MAKES THE SESSION BLOCK LOOK LEGITIMATE.** It says
*"The value above is the **default**, not a hardcode. A project overrides either half through
`plan-marshall:manage-run-config`."* ⇒ **The doc announces that the trailer IS overridable and then does
not close the set.** A later instruction supplying a different trailer reads as *the sanctioned override
arriving through a different channel.* ⭐⭐ **The agent is not misreading a clear rule; it is reading a
rule that describes an override mechanism without saying it is the ONLY one.**

⛔ **Why FIVE times: the adjudication has no home.** The operator's answer resolves the session it was
asked in and nothing else. **No mechanism records that this conflict was adjudicated**, and the
conflicting instruction is re-injected **every session**. ⇒ **The recurrence rate equals the injection
rate, and will not decay.**

⛔⛔ **The repo cannot stop this by configuration alone**: one of the two parties is OUTSIDE the
repository and re-asserts itself each session. **`run_config commit-trailer set` cannot help — the
conflict is not about the VALUE, it is about which source wins.**

⭐⭐⭐ **TWO FIXES, DIFFERENT HALVES, AND ONLY ONE STOPS THE ASKING:**

| Fix | What it closes | Cost |
|---|---|---|
| **Close the override set in CLAUDE.md** — one sentence: the `run_config` resolver is the ONLY override; a trailer supplied by any other channel is not authoritative | ⭐ **Stops the ASKING** — the agent gains the ranking rule it lacks | one sentence |
| **Assert at commit time** that the about-to-be-written trailer equals `commit-trailer get`, and refuse a mismatch | **Stops the DAMAGE**, and makes the question moot because the wrong value cannot be written | one call in the commit path |

⛔ **Neither substitutes for the other.** The doc sentence prevents a correct agent from asking; the
assertion prevents an incorrect one from writing. ⚠ **Both are repository-source edits, so the
orchestrator has applied NEITHER** — they need a plan or an operator edit.

⭐ **Every reported instance so far CHOSE CORRECTLY** (the project trailer), so no commit is known to
carry the wrong value. **The cost to date is entirely operator attention — five interruptions — which is
exactly the cost profile that makes it easy to keep deferring.**

### ⛔⛔⛔ 2026-09-05 (d) — OUR OWN IN-FLIGHT PLANS DECLARE NO FOOTPRINT AT `4-plan`, AND A SIBLING AT THE SAME PHASE DECLARES 52

**UNOWNED. New, and it is the ROOT of the disjointness coverage hole recorded at the last two emits.**

Derived first-party by reading every `references.json` under `.plan/local/plans/`, not inferred:

| Plan | Epic | Phase | `affected_files` |
|---|---|---|:-:|
| `one-format-several-implementations-that-disagree` (`-125`) | **ours** | `4-plan` | **0** |
| `the-ledger-has-no-safe-single-row-append` (`-099`) | **ours** | `4-plan` | **0** |
| `test-suite-anti-vacuity` (`CIS-053`) | foreign | **`4-plan`** | **52** |
| `required-reviewer-returns-empty-list` (`PR-042`) | foreign | `6-finalize` | 3 |

⛔⛔ **The comparison is what settles it.** A sibling at the SAME phase carries 52, so an empty footprint
at `4-plan` is **neither a phase artifact nor scaffolding lag** — `3-outline` is where the declared
footprint is derived from the solution outline's deliverables, and both of ours came out of it empty.

⇒ **This is the `affected_files` under-recording defect, observed on our own plans**, and it has a
direct, measured consequence: `corpus cross-check`'s `live_plan` arm compared **1 of 5** live plans at
the last emit, **because the two it could not see were ours.** ⛔ **The gate is blind to exactly the
plans a new emit most needs to avoid**, and every "no live overlap" reading taken while a plan sits at
`affected_files: 0` is SILENCE, not a checked negative.

⭐ **The workaround in use is stated, not silent**: candidates are compared against the running plans'
declared **specs** via `corpus_spec` rows. **That is spec-vs-spec, not spec-vs-realized**, and it
inherits every under-declaration the spec carries — it is a proxy, and it is recorded as one each time
it is used.

⚠ **Do NOT fold this into `PLAN-TRUTH-136`** (*the declared footprint cannot learn a path the outline did
not predict*) without checking: that spec's subject is a footprint that **fails to GROW**; this is a
footprint that was **never written at all**. Same file, different failure, and only the second makes the
disjointness gate vacuous.


### ⚠ 2026-09-05 (c) — `branch-cleanup` FACTS: REFRAMED FROM A CAPABILITY GAP TO A COMPLIANCE GAP

**Supersedes the framing of the two entries above; the defect is NOT closed.** `PLAN-TRUTH-089`'s
archived `phase_steps` entry carries `['outcome', 'display_detail', 'facts']` with a **populated map** —
`{merge_mechanism: merge_queue, merge_state: merged, work_performed: true}` — and its landing was the
first in this series to return `landing-check: complete: true`, zero missing keys.

⛔⛔ **But the prescription was already in force when the other two ran.** `branch-cleanup.md` was last
modified at `cc5ea40a1` (**#1392, 2026-09-03**) and carries **24** references to `merge_mechanism`; both
`-126` and `-093` finalized on **2026-09-05**, after it.

⇒ **Three runs, one prescription, one emitter.** That is R75's archetype: *a mandatory emission with no
post-condition check is a promise, not a contract.* ⛔ **A fix that adds more prose to `branch-cleanup.md`
fixes nothing — the prose is already there and was already ignored twice.**

⚠ **One alternative cause, stated rather than dismissed:** seating is per-envelope, so `-126` and `-093`
may have run against skill bodies predating #1392. **NOT corroborated** — the seated version of a
finalize envelope is recorded nowhere reachable. ⭐ **The remedy is identical either way: a
post-condition check on the emission.**

### ⛔⛔⛔ 2026-09-05 (c) — THE `23/23` SERIES IS FOUR, AND THE UNDER-REPORT HAS GROWN 15×

| Plan | firings | steps | headline | under-report |
|---|:-:|:-:|:-:|:-:|
| `-075` | 29 | 22 | `23/23` | 7 |
| `-126` | 67 | 23 | `23/23` | 44 |
| `-093` | 75 | 23 | `23/23` | 52 |
| **`-089`** | **124** | **22** | `23/23` | **102** |

Eleven steps re-fired on `-089`: `plugin-doctor` **19×**, `pre-submission-self-review` **19×**,
`pre-push-quality-gate` **18×**, `lessons-housekeeping` **17×**, `automatic-review` **10×**.

⛔ **124 firings to complete 22 steps is a 5.6× multiplier**, and it is the whole of the cost story:
`6-finalize` took **11.27M tokens / 2245 tool uses** against implementation's **507K / 194**. ⇒ **Any
consumer that reads a step roster as a work count is wrong by up to 5.6× on the phase that dominates
spend.**

⭐ `-089`'s report disclosed its own re-fire profile accurately, as `-093`'s did. **The headline above it
still has not moved across four landings.**


### ⛔ 2026-09-05 (b) — A REPORT'S CLOSING MESSAGE COUNT CONTRADICTS ITS OWN STEP LINE, AND THE ENUMERATION

**UNOWNED. New.** `PLAN-TRUTH-093`'s report closes: *"Four inbox messages reached epic
`truthful-signals`: three candidate-lessons from the retrospective (`-007`/`-008`/`-009`) and the
landing (`-010`)."*

**`inbox list` enumerated TEN from that sender (`-001`…`-010`)** — and the report's own step line says
so: `lessons-capture … 6 inbox message(s) to epic truthful-signals`. **6 + 3 + 1 = 10.**

⛔ **Not a transport failure — every message arrived and every one drained.** It is a
**count-vs-enumeration divergence inside a single report**, where an earlier line in the same document
carries the missing six. ⭐ **A drain that had trusted the closing count would have left six messages
unread with no signal that it had** — the failure mode is silent, and the correct behaviour (enumerate,
never accept a narrated count) is what caught it. ⇒ This epic's archetype turned on the report itself.

### ⛔⛔ 2026-09-05 (b) — SECOND INSTANCE, ONE DAY APART: `branch-cleanup` WRITES A FACT **OUTSIDE** THE FACTS MAP

**Sharpens the 2026-09-05 entry above rather than repeating it.** `PLAN-TRUTH-093`'s archived
`phase_steps` entry carries `['outcome', 'display_detail', 'head_at_completion']` — **still no `facts`
map, yet a fact-shaped value (`head_at_completion`) written outside one.**

⇒ **The step is not fact-blind; it is writing a fact where no typed consumer reads.** That reframes the
fix: not *"start recording facts"* but *"record through `--fact`, and move the value already being
captured into that channel."* ⭐ The operator's own prescription (*"record `merge_state` via `--fact`"*)
is right, and `head_at_completion` should ride with it.

⚠ **The dead `worktree_path` also reproduced** — `use_worktree: True` with a non-existent path in the
archived record, exactly as in `-126`. ⇒ **`866bcd`'s persisted-state half is reproducible, not
incidental.**

### ⛔⛔ 2026-09-05 (b) — THE `23/23` SERIES IS NOW THREE, AND IT IS TRENDING UP

`PLAN-TRUTH-093`: **75 firings across 23 recorded steps, headlined `23/23`; TEN steps re-fired**
(`pre-submission-self-review` **12× with 7 CONSECUTIVE `failed`**; plugin-doctor and simplify **7×**;
five more at **6×**).

| Plan | firings | steps | headline | re-fires disclosed |
|---|:-:|:-:|:-:|---|
| `-075` | 29 | 22 | `23/23` | 1 |
| `-126` | 67 | 23 | `23/23` | budget only |
| `-093` | **75** | 23 | `23/23` | ⭐ **the re-fire profile, accurately** |

⭐ **The DISCLOSURE improved between `-126` and `-093`** — this report stated the 12× and the seven
consecutive failures, and the record confirms it exactly. ⛔ **What has not moved is the `23/23`
headline still sitting above it**, and the firing count is trending up.

### ⚠ 2026-09-05 (b) — `uv.lock`: CUSTODY IS NOW ESTABLISHED, AND THE DEFECT IS AGE

`PLAN-TRUTH-093` reports the dirty file *"was already modified in the main checkout before finalize
touched it; no plan step wrote it."* ⭐⭐ **Corroborated by construction** — this epic recorded the same
file dirty from `-126`'s run *before* `-093`'s finalize began. ⇒ **Two runs agree on custody: `-126`
produced it, `-093` inherited and correctly disclaimed it.**

⛔ **Still uncommitted, still the repair main needs** (`#1417` moved `pyproject.toml` to ruff `>=0.16.5`
without relocking). **The open question is no longer authorship — it is that nothing owns committing it.**



#### ⭐⭐⭐ MECHANISM FOUND 2026-09-08 — IT IS NOT NEGLECT, IT IS A DECLARED FACT THE DISPATCHER TRUSTS

*"nothing owns committing it"* is now explained. Relayed from Token-Sheriff PLAN-11 and folded to
`PLAN-TRUTH-105`: **`pre-push-quality-gate` declares `mutates_source: false`; the dispatcher reads that
declaration FIRST and, on `false`, skips commit instrumentation entirely.** ⇒ **No staging, no commit,
no owner for any diff the step produced — by construction, not by oversight.**

⛔⛔ **The remedy is NOT to re-declare the step.** The gate command is **project-resolved**: ours relocks
`uv.lock`, theirs writes a dependency into a POM. **A declared fact about a project-resolved command is
unknowable at declaration time**, which is the actual defect.

⇒ **This entry is no longer "an aged repair nobody committed" — it is a live instance of a harness
defect with a second corroborating project.** ⚠ The file is still dirty and still the repair main needs.

### ⛔⛔ 2026-09-05 — `branch-cleanup` RECORDS NO TYPED FACTS AT ALL, AND THE PRODUCER IT NEEDS ALREADY EXISTS

**UNOWNED.** From the `PLAN-TRUTH-126` landing. The run reported *"`branch-cleanup` records no
`merge_state` fact"*. **The archived record says more:** its `phase_steps` entry carries **only
`outcome` and `display_detail` — `facts: {}`.** ⇒ `merge_state` is not a missing key in a populated
map; **the map is empty.** A fix that adds one key to a step that emits no facts is fixing the symptom.

⭐ **The producer exists and is one call away**: `ci pr view` returns `state: merged` **and** a
`merge_commit_sha`. ⛔⛔ **But mind the field-name collision, which is a live trap:** `ci pr view` ALSO
returns a field literally named `merge_state`, which is GitHub's *mergeability* status and reads
`unknown` for **every** merged PR. **Wiring `merge_state` ← `merge_state` would ship a permanent
`unknown` that looks correct.** The landing payload's `merge_state` must be fed from **`state`**.

⚠ Consequence today: `PLAN-TRUTH-126`'s landing carried `merge_state=unknown` and `landing-check`
returned `complete: false` on **that one key alone** — otherwise the most complete landing this epic
has drained.

### ⛔⛔ 2026-09-05 — THE `23/23` HEADLINE HID 44 RE-FIRINGS — SECOND INDEPENDENT INSTANCE

**UNOWNED.** Derived from `PLAN-TRUTH-126`'s archived `phase_steps`: **67 firings across 23 recorded
steps, headlined `23/23`; nine steps re-fired.** `pre-submission-self-review` fired **15 times with 12
of 14 prior outcomes `failed`**; `pre-push-quality-gate`, `plugin-doctor`, `ci-verify` and
`automatic-review` fired **6** each.

⭐ **The run was HONEST where it spoke** — it disclosed the self-review budget exhaustion verbatim
(*"out of budget: 12 rounds, 26 findings fixed, last round NOT clean"*), and the record corroborates it
harder than the headline reads. ⛔ **The defect is the DISCLOSURE SURFACE, not the runner:** `23/23` is
a step ROSTER presented where a work count is read.

⇒ **Second independent instance** — `PLAN-TRUTH-075` recorded 29 firings across 22 steps headlined
`23/23` with one re-fire disclosed. **The roster/firing conflation has now survived a landing that was
specifically about guards reporting what they did not measure.**

### ⚠ 2026-09-05 — `uv.lock` IS DIRTY ON MAIN, AND THE FRAMING IS INVERTED: IT IS A REPAIR, NOT DRIFT

**UNOWNED.** Finding `3d8e95`. The run reported a stray `ruff 0.16.4→0.16.6` relock made by a step
declaring `mutates_source: false`, past the merge gate with no push path left.

⭐⭐ **Corroborated, and the corroboration inverts the framing.** `#1417` (`b90185b4c`, dependabot)
changed **`pyproject.toml` ONLY — 1 file, 1 line** — moving the ruff requirement to `>=0.16.5`
**without relocking**. ⇒ **Main landed inconsistent**: the constraint demands `>=0.16.5` while
`uv.lock` pinned `0.16.4`. The uncommitted relock (20 insertions / 20 deletions, ruff only) is **the
repair main needs, stranded in a dirty working tree.**

⛔ **So the remedy is COMMIT, not revert** — and the two real defects are unchanged by that: a step
declaring `mutates_source: false` mutated source, and it did so past the merge gate with no push path
left. ⚠ **A dependabot requirement bump that does not relock is a third, separate gap** and is not
this epic's — record it, do not adopt it.


### ⛔⛔ 2026-09-03 — A PHASE BOUNDARY WAS CROSSED WITH THE PHASE'S DECLARED VERIFICATION NEVER HAVING RUN

**UNOWNED.** From the `PLAN-TRUTH-101` landing (PR #1386, `landings/PLAN-TRUTH-101.md`), reported by
the run against its own artifacts.

The `5-execute → 6-finalize` boundary was crossed while the manifest declared **3**
`verification_steps` and the execution log held **zero** `record-step` rows for `5-execute`.

⭐⭐ **The gap closed only because a later loop-back re-fired `pre-push-quality-gate` against the newer
HEAD — that is, by luck.** Absent the loop-back the plan ships unverified **and nothing reports it**.
The boundary check cannot distinguish *"the declared verification ran and passed"* from *"no
verification row exists at all"*, which is this epic's own which-kind-of-zero rule applied to the one
gate that decides whether execute is finished.

⚠ Sibling observation from the same run, kept separate because it has a different cause:
**`metrics.toon` still reports `re_entered_phases: []`** after a completed
`6-finalize → 5-execute → 6-finalize` loop-back carrying `loop_back_iteration: 1`. A re-entry that
happened and one that did not are byte-identical in that field. ⛔ Do not fold the two — one is a
missing gate, the other a missing record.

### ⚠ 2026-09-03 — A FINDINGS COUNT PUBLISHED BESIDE AN ENUMERATION THAT DOES NOT SUPPORT IT

**Low severity, recorded because of WHERE it landed.** The `PLAN-TRUTH-101` report states *"Nine
findings were filed and deliberately not fixed"* and then names **eight** ids. The landing message's
own residue section enumerates the same eight, so the machine record and the id list agree and only the
word *nine* disagrees.

The likely ninth referent is `c128cb`, named inside `f3d2df`'s text — but it is described as **acted
upon**, not deferred, so it does not belong to a count of findings *deliberately not fixed*.

⛔ **Recorded as a divergence, not resolved by inference:** either the count is off by one or a ninth
deferred finding exists that the payload omits, and this epic's rule forbids choosing between those
from a restated total. ⭐ **It is the epic's archetype in miniature, inside a report whose subject is
exactly that class of defect.** Candidate owners: `PLAN-TRUTH-117` (restated counts and underived
completeness claims) or `PLAN-TRUTH-110` (a plan decides what the epic learns and nothing audits it).

### ⛔ 2026-09-03 — OWED, OPERATOR-ONLY: THE PLUGIN-REGISTRY PIN GAP RE-OPENED AT `0.1.1588`

Re-opened by `PLAN-TRUTH-101`'s own cache sync — **every `/sync-plugin-cache` re-opens it**, so this is
the expected state after a landing, not a new fault. 18 entries, 10 dirs.

```bash
python3 .plan/temp/repair-plugin-pin.py --target 0.1.1588
```

⛔ **A FULL RESTART is required afterwards to re-seat skill bodies.** ⚠ Per R158, two corrections to the
remembered procedure: **there is no `--apply` flag** — writing is the DEFAULT and `--dry-run` is the
opt-out — and after the repair **delete `*/0.1.1588/.orphaned_at`**, because the foreign GC marks the
freshly-synced version within minutes of the sync and those markers are its, not the repair's.


### ⛔ 2026-09-03 — A NON-MESSAGE-SHAPED FILE IN `inbox/` IS INVISIBLE TO THE DRAIN — ⚠ HALF DISCHARGED 2026-09-04

> ⚠ **STATUS UPDATE 2026-09-04.** The two separable defects this entry named have diverged:
> **(b) is DISCHARGED** — `findings-from-cui-http.md` was dispositioned across all 45 findings and
> archived intact (see the 2026-09-04 (b) drain record above). **(a) REMAINS OPEN and unowned**:
> `inbox list` still discloses no `foreign_files[]`, so a non-message-shaped file in `inbox/` is still
> invisible to the drain and `count: N` is still true and misleading in the same breath. ⭐ **The
> archive verb, by contrast, accepted the off-shape name and placed it flat without complaint** — so
> the enumerator and the archiver disagree about what counts as a message, which is a second, smaller
> instance of the same gap.


**UNOWNED, and the highest-value item this drain surfaced.** `inbox/findings-from-cui-http.md` (51 KB)
is **not enumerated by `inbox list`** — its filename does not match the `{sender}-{NNN}.md` shape the
enumerator requires — so it sat through this drain and every previous one untouched. `count: 36` was
correct and `inbox/` held 37 files.

⛔⛔ **It is not a stray.** Its own header states it aggregates **52 lesson records** filed in the
`cui-http` store between 2026-08-26 and 2026-09-01 (mostly the `quality-report-remediation` epic, 19
plans, PRs #153–#186), deduplicated into **8 themes / 27 findings** — and that **"the source lessons
were removed after this file was written and verified; this document is now the sole record."**

⭐⭐ **It independently corroborates four of today's dispositions**, which is strong evidence its
remaining themes are worth the same treatment: Theme 1 (invocation-time argparse rejections, *"both
existing guards fire at the wrong time"*, 2 recurrences) ↔ the newly staged `PLAN-TRUTH-129`; Theme 2
(review-bot participation, *"never re-trigger a quota-blocked bot"*, **4 recurrences — its worst
offender**) ↔ the cluster transferred to `review-apparatus`; Theme 5.2 (*"the scope-creep guard has
never measured anything"*) ↔ the `-104` fold; Theme 6.1 (*"a step that writes tracked files while
declaring no `mutates_source`"*, 2 recurrences) ↔ the `-121` fold, which arrived here today from a
completely different repository.

**Its other themes are untouched:** 3 (what the diff left alone), 4 (tests and gates that prove
nothing), 5 (which kind of zero is this), 6.2–6.3 (contract bypass), 7–8 (not yet read).

⛔ **NOT dispositioned by this drain, deliberately.** 27 findings is a second drain's worth of work and
absorbing it silently inside this one would be scope creep. **It is the next action.** ⚠ **Do not move
or rename the file before it is drained** — it is the only copy.

⚠ **Two separable defects here, do not conflate them:** (a) the enumerator cannot see a
non-message-shaped file *and reports nothing about it*, so `count: 36` is true and misleading in the
same breath — a `foreign_files[]` disclosure would fix that; (b) this particular document needs a
disposition pass.

### ⛔ 2026-09-03 — `manage-logging decision` EXITS 0 AND EMITS NOTHING AT ALL

**UNOWNED.** Observed first-party while executing this drain, on 36 consecutive calls.
`manage-logging decision --store orchestrator` **writes the record correctly and prints no output** —
no TOON, no `status:` line, nothing. A caller checking the marketplace's documented `status: success`
contract therefore reads **every successful write as a failure**.

⭐ **It is not a theoretical risk — it fired here.** This drain's own disposition driver checked
`'status: success' in stdout` and consequently reported **36 of 36 messages as `archive_failed`** while
all 36 decision-log lines had in fact landed. ⛔ **Only the persist-then-archive ordering prevented
damage**: nothing had been archived yet, so the queue was intact and the run was recoverable by
re-driving the archive half alone. Under the reverse ordering the drain would have archived 36 messages
and then reported them all as failures.

⚠ **The recovery itself cost a real hazard:** re-running the driver unchanged would have **double-logged
all 36 dispositions**, because the successful writes are indistinguishable from failed ones at the
caller. Candidate owners, in preference order: `PLAN-TRUTH-106` (the terminal emission and the operator
report do not check themselves) or `PLAN-TRUTH-121` (producer/report integrity). ⛔ **Route it at the
next cleanup rather than assuming either** — a silent producer and a producer whose write is unreadable
are different defects, and this is the first.


### ⛔⛔ 2026-09-03 — `scope_creep_check` READS A KEY THAT IS NOT IN THE SCHEMA AND HAS NO PRODUCER

**UNOWNED.** Ingested as a data-point from a consumer project; **corroborated first-party at HEAD
`19453cb1b` over a LARGER, INDEPENDENT corpus**, and the diagnosis below is sharper than the report's.

`phase-5-execute/scripts/scope_creep_check.py` diffs the plan's live footprint against
`references.json`'s **`plan_creation_sha`**. Without it the guard returns
`status: could_not_look` / `reason: no_baseline_sha` and **omits `residual_count` entirely**.

⭐⭐ **The guard is EXEMPLARY and must not be "simplified" by whoever fixes this.** It refuses to publish
a zero it did not measure, and its SKILL states why: *a 0 published by a run that never compared anything
is indistinguishable from "compared, found none", and a reason field alone does not fix that because it
is advisory and trivially dropped.* ⇒ **This is the discipline this epic keeps asking for, working
correctly. The defect is entirely upstream of it.**

#### ⛔ The sharper finding: it is a SCHEMA gap, not merely a missing writer

`manage-references/scripts/_references_core.py:25` defines `ReferencesData` — `branch`, `base_branch`,
`issue_url`, `build_system`, `domains`, `affected_files`, `external_docs`, `realized_footprint`,
`merge_commit_sha`. **`plan_creation_sha` is not among them.** ⇒ The consumer reads a key **the schema
of the file it reads does not declare**, and `grep -rl` across the whole marketplace returns **two files,
both consumers** (`scope_creep_check.py` and `phase-5-execute/SKILL.md`). **No producer exists anywhere.**

#### The population — two independent corpora, same shape

| Corpus | Plans with `references.json` | Carrying `plan_creation_sha` |
|---|:-:|:-:|
| this checkout (local) | **31** | **1** |
| the reporting project | 12 | 1 |

The single local hit is `2026-08-25-participation-credit-anchored-to-merge-candidate`
(`1169fb5bfade…`, **a real commit**). ⇒ **43 plans across two unrelated repositories, two hits.**
Independent replication of "seeded once, then never again".

#### ⚠ A correction to the report's inference — the co-occurring keys are NOT a mystery

The report notes the hit also carries `realized_footprint` and `merge_commit_sha`, and reads that as
evidence of *"a different code path"* writing all three. **Both of those keys are IN the schema and have
documented producers**: `realized_footprint` is written by `manage-references capture-footprint` (called
by `default:branch-cleanup` before it removes the worktree), and `merge_commit_sha` by `branch-cleanup`
**on the synchronous merge path only** — *"absent on the async merge-queue path"*. ⇒ **Their
co-occurrence is fully explained by a sync-merge landing and is NOT evidence of a third writer.**
⛔ Do not chase a shared producer for all three; the unexplained write is `plan_creation_sha` **alone**.

⚠ **Still unexplained, and honestly so:** what wrote `plan_creation_sha` on those two plans. `references.json`
is plain JSON and `ReferencesData` is a `total=False` TypedDict — typing, not enforcement — so any writer
with file access could have. **Not determinable from the corpus alone.**

#### What it costs

⇒ **Scope-creep detection has never run on any plan in either corpus but one.** The reporting project
names two plans the guard exists to catch — one realizing 28 files against 11 declared, another exceeding
its declaration by four paths — **both found by hand**. ⚠ Those instances are theirs and were not
corroborated here; the *silence of the guard* is what this entry establishes.

⭐ **The fix is a PRODUCER plus a schema entry, not a consumer change.** Something must stamp HEAD into
`references.json` at plan creation (`phase-1-init` or `manage-references`), and `ReferencesData` must
declare the field so the next reader is not reading an undeclared key.

#### ⭐⭐ RECURRENCE 2026-09-04 — a THIRD independent corpus, and it is still UNOWNED

A **second reporting machine** independently re-derived this defect and filed it as
`2026-09-04-12-003`, stating it in the same two parts this entry does: *"structurally dead for every
plan — it reads `references.json.plan_creation_sha` and no producer for that field exists anywhere in
the bundle,"* and *"its graceful `could_not_look` makes an absent measurement look like a clean one."*
⇒ **Independent replication n=3** (this checkout, the first reporting project, this machine) — folded
here per the dedup discipline rather than opened as a second defect.

⭐ **Re-corroborated first-party at `c3a1aacbc`** via `architecture search --content --pattern
"plan_creation_sha"` over a **clean sweep** (`files_scanned: 5340`, `unreadable[0]`,
`truncated: false`): **5 files, 2 consumers and 3 tests** — `phase-5-execute/SKILL.md`,
`phase-5-execute/scripts/scope_creep_check.py`, and the three `test/plan-marshall/phase-5-execute/`
suites. **`manage-references` appears nowhere. The producer still does not exist.**

⚠ **Coverage caveat, stated rather than assumed:** `search --content` is inventory-scoped, so
`.plan/` (git-ignored) is NOT swept. The zero above is a trustworthy *"no producer in any inventoried
bundle file"* — it is **not** a statement about plan-local `references.json` instances.

⛔ **STILL UNOWNED after three independent findings.** The nearest staged specs
(`PLAN-TRUTH-104`, `PLAN-TRUTH-111`) touch the surface but neither takes the producer-plus-schema fix
as its subject. **Three corpora is past the point where this should be waiting on an accident to
adopt it** — stage it, or fold it explicitly into `-111` with the surface updated in the same act.

#### ✅ OWNED 2026-09-05 — `PLAN-TRUTH-138` STAGED, on a FOURTH report that finally named a MISS

**TokenSheriff, 2026-09-05:** *"Scope-creep was never measured — on any of the 10 tasks. The guard
returned `could_not_look` every time because `references.json` has no `plan_creation_sha`."*
⇒ **n=4 independent corpora.** ⭐⭐ **But the fourth carried the thing the first three lacked:**
*"it's the guard that would have flagged this plan's one genuine out-of-footprint edit."*

⛔⛔ **THAT IS THE SENTENCE THAT MOVED IT FROM RECORDED TO STAGED, AND THE DISTINCTION IS THIS EPIC'S
OWN.** Reports 1-3 established the guard's **SILENCE** — a strong claim about the instrument and a weak
one about cost, since a silent guard over a population with no creep costs nothing. Report 4
establishes a **MISS**: a real out-of-footprint edit that reached a merge because the only thing
looking for it was starved. ⚠ **The miss itself is foreign-corpus and is NOT corroborated here** — the
spec labels it `HYPOTHESIS` and does not claim a catch rate. What changed is the *expected* cost, and
that is enough to buy an owner.

⚠ **Deliberately NOT folded into `-111`.** `-111` is a dated grab-bag whose D0 re-grounds a 2026-08-24
snapshot and whose own spec tells outline to split it if members diverge; a missing producer plus a
schema entry diverges. ⚠ Also kept apart from `-104`: **same archetype, opposite end of the pipe** —
`-104`'s consumer discards a published population, this consumer publishes its population correctly and
is starved of input. Naming the archetype in both shipped docs is right; sharing code is not.

⇒ **Ledger 185 → 186 rows**, appended by the assertion-guarded programmatic path (`queue --add-row`
still does not exist — `-099` is the fix); `corpus enumerate` clean **both** directions
(186/186, `rows_without_spec: 0`, `specs_without_row: 0`, `unreadable: 0`).

### ⛔⛔⛔ 2026-09-03 — `restart-check`'s `running_plans` SIGNAL REPORTS READY WHILE PLANS ARE IN FLIGHT

Found by executing `cleanup` for a restart, which is precisely the situation the signal exists for.
**Corroborated first-party at HEAD `19453cb1b`.**

`orchestrator.py:2476` selects in-flight rows with `str(row.get('status','')) == RUNNING_STATUS`, and
`_orchestrator_inbox.py:79` defines `RUNNING_STATUS = 'running'`. ⛔ **This epic's live plans carry
status `launched`, not `running`** — `PLAN-TRUTH-089` and `PLAN-TRUTH-101` were both `launched` and both
demonstrably executing (`manage-status list`: 5-execute and 6-finalize, each in its own worktree) —
**and the signal returned `ready` with the evidence string *"no plan row is running"*.**

⭐⭐ **The docstring states the intent the behaviour does not deliver:** *"In-flight plans. A restart
mid-run loses the run's context, so it blocks."* ⇒ **The one signal whose stated job is to block a
mid-run restart reported ready during exactly such a run.**

⛔ **Why this is worse than an ordinary miss:** the evidence string is not vague, it is *positively
wrong*. A reader is told a fact was checked and found false. And the failure is **silent by
construction** — a queue that never writes `running` makes this predicate unable to fire at all, so no
amount of running plans will ever turn it red.

⚠ **What is NOT yet established, and D0 of any owning plan must settle it:** whether the defect is the
PREDICATE (it should test `launched` too, or a derived liveness set) or the VOCABULARY (rows that are
live should carry `running`, and `launched` should mean emitted-not-started). ⛔ **Do not assume the
first.** `launched` and `running` may be a deliberate emit-vs-start distinction — this epic records
`emit ≠ running` as a standing rule — in which case the fix is that the transition to `running` is
never made, which is a different defect in a different place. **The two remedies are incompatible and
the evidence does not yet choose between them.**

⭐ **Independent corroboration is available and cheap**: `manage-status list` names the live plan set
without reference to the queue's status vocabulary at all. A signal that cross-checked the two could not
have produced this answer. ⇒ Whatever the chosen remedy, **the derivation should not rest on a single
vocabulary the queue is free to spell differently.**

⚠ **Consequence for this session, recorded rather than assumed:** the `not_ready` verdict returned today
is correct, but it is correct **for the wrong reason** — it failed on the inbox signal alone, and would
have said `ready` once the inbox drained, while two plans were still executing.

### ⛔⛔ 2026-09-03 — `branch-cleanup` DESTROYS STATE LATER STEPS NEED — one cause, two consequences

Surfaced by PLAN-TRUTH-102's landing (#1384) and **cross-referenced onto `PLAN-TRUTH-127`, which already
owns the other half.**

- **Consequence A (owned, `-127` arm 2)** — `transition --completed` is unreachable post-finalize,
  because `_clean_tree_refusal` shells `git -C {worktree}` and the worktree is gone.
- **Consequence B (NEW, unowned)** — **`build_time` reports all-zero over 77 executed builds**, because
  `branch-cleanup` destroys the worktree-resident ledger oracle *before* the reporting steps read it.
  ⛔ **A destroyed-oracle zero is BYTE-IDENTICAL to a build-free run** — this epic's archetype, in a
  metric.

⭐⭐⭐ **Do not treat these as two root causes.** One step removes a resource two later steps depend on,
and each surfaced separately because each was noticed by a different consumer. ⚠ **A fix that only
teaches `build_time` to say "oracle destroyed" leaves A standing, and a fix that only re-orders for A
leaves B standing.** The ordering question — what may run after `branch-cleanup`, and what must read its
inputs before it — is the shared remedy.

⚠ The reporting plan routed B as its own candidate `-009` into the inbox; the drain will reconcile it
against this entry rather than opening a third record.

### ⚠ 2026-09-03 — A `marshalld` TIMEOUT ABANDONS THE WAIT, NOT THE BUILD (unowned)

From the same landing. **A `timeout` verdict is a statement about the WAITER, not the BUILD, and the two
are reported as one.** Three pytest suites ran concurrently before a process-table scan reaped them —
the documented "re-run once" recovery stacked a fresh suite onto one still running.

⛔⛔ **One `timeout` verdict was outright FALSE: the abandoned build had PASSED, 62 seconds after the
budget elapsed.** ⇒ The verdict named a failure that did not occur, and the run acted on it.

⭐ **Correct handling recorded:** the contaminated latency figures had already reached a lesson
(`2026-09-02-20-001`), and the plan **corrected it in place** rather than leaving a wrong premise in the
corpus. ⚠ Related to the standing rule *never trust a routed build's outer status; an implausible
duration is a failure signal* — but this is its **inverse**: a plausible-looking timeout over a build
that succeeded. Both directions now have an instance.

### ⚠ 2026-09-03 — NO `ext-self-review-{domain}` IMPLEMENTOR EXISTS FOR ANY DOMAIN BUT PLAN-MARSHALL'S OWN

**UNOWNED, and deliberately NOT folded into `PLAN-TRUTH-126`.** This is the second half of the
instance-4 finding folded there, and it is a **capability gap, not a truthfulness defect** — writing a
domain surfacer is building a feature in `pm-dev-java`, and folding it into a truthfulness plan would
change what that plan is. ⭐ The two halves are **independent by construction**: `-126` D4's coverage
reporting is correct and valuable **even if no Java implementor is ever written**, because *"0% of the
changed surface was analysable"* is a true and useful answer.

**Corroborated first-party at HEAD `30cd8aaf8`:** `ext-point-self-review-surfacing` has **exactly one
implementor across every bundle** — `pm-plugin-development:ext-self-review-plan-marshall`. The only
other two hits on the ext-point name are its own contract (`extension-api`) and its consumer
(`phase-6-finalize`). ⇒ **Every domain except plan-marshall's own has no surfacer**, so this is not
Java-specific; Java is simply the domain that noticed.

⚠ **Sequencing, if it is ever taken up:** it belongs AFTER `-126` D4, not before. Coverage reporting
makes the gap *visible* and therefore measurable; writing implementors without it means nobody can tell
which domains are still uncovered, or whether a new implementor actually widened coverage. ⛔ Writing the
implementor first would close the loudest instance while leaving the silent-green mechanism intact for
every remaining domain.

⛔ **Not claimed:** whether a Java surfacer is worth building at all. That is a value judgement about
`pm-dev-java`'s roadmap, not a defect verdict, and this entry records the gap rather than proposing the
work.


#### ⛔⛔ RECURRENCE 2026-09-06 — A JAVA REPO CONFIRMS IT FIRST-PARTY, AND THE DERIVED RATIO IS 1 OF 7

A separate Java project reported the structural self-review **never ran** on a real plan: no
`ext-self-review-{domain}` surfacer exists for Java, so **CodeRabbit was the only structural review that
change got.**

⭐⭐ **Derived here rather than accepted, and the derivation is worse than the report.** Two
`architecture find` sweeps over the same bundle tree:

| Extension point | Implementors | Domains covered |
|---|:-:|---|
| `ext-triage-{domain}` | **7** | js · java · oci · python · docs · plugin · reqs |
| `ext-self-review-{domain}` | **1** | plan-marshall only |

⇒ ⛔ **The domain set is KNOWN and ENUMERABLE — its sibling extension point covers all seven. Structural
self-review reaches ONE of them.** This is not "Java is missing"; it is **an extension point implemented
for 14% of the population its own sibling proves exists.** ⛔ **Any consumer project that is not
plan-marshall itself gets NO structural self-review at all**, and the finalize step still renders in the
`[OK]` column.

⭐⭐⭐ **BUT THE DISCLOSURE WORKED, AND THAT IS A SHIPPED DELIVERABLE OBSERVED IN THE WILD.** The
reporter saw it: *"it's recorded as done with the **not-run verdict**."* That is **`PLAN-TRUTH-126` D5**
(*record an un-run or un-observed dimension in the finalize step's own verdict*, shipped in #1397) —
**working, in a foreign repository, on a domain it was not written for.** ⇒ **The step no longer claims
a review it did not perform.** ⛔ The gap is now honestly reported and still unfixed, which is exactly
the state this epic wants defects to be in — **visible, not silent.**

⚠ **This raises the priority without changing the diagnosis.** A 1-of-7 extension point is a
population-shaped gap, not a per-domain request; **a fix that adds only Java leaves five domains and
re-earns this defect.**

### ✅ 2026-09-03 — `fresh` MEANS TWO DIFFERENT THINGS IN THE PRE-COMMIT FRESHNESS GATE — NOW OWNED BY `PLAN-TRUTH-128`

> ↪ Relocated to `settled.md` § "✅ 2026-09-03 — `fresh` MEANS TWO DIFFERENT THINGS IN THE PRE-COMMIT FRESHNESS GATE — NOW OWNED BY `PLAN-TRUTH-128`" — ownership transferred to PLAN-TRUTH-128, which is now RUNNING.

### ✅ 2026-09-03 — A LOOPED-BACK PHASE IS RECORDED `in_progress` FOREVER — NOW OWNED BY `PLAN-TRUTH-127`

> ↪ Relocated to `settled.md` § "✅ 2026-09-03 — A LOOPED-BACK PHASE IS RECORDED `in_progress` FOREVER — NOW OWNED BY `PLAN-TRUTH-127`" — ownership transferred to PLAN-TRUTH-127, which is staged and re-grounded.

### ⛔⛔ 2026-08-27 — TWO DEFECTS SHIPPED INTO MAIN by PLAN-TRUTH-098 (#1359, `841f9093`)

Neither is fixed by #1359; both were proven **by execution** in that run and both are folded to
`PLAN-TRUTH-101`. Recorded here because they are live in merged main, not merely staged work.

**D-098-a — two documented capture commands name `work/footprint.txt`, which no step creates.**
`plan-retrospective` `references/routing-decision-verification.md` (aspect 13) and the
**newly-shipped** `references/outline-vs-shipped.md` (aspect 15) both instruct capture into that path.
⛔ **Run verbatim, both aspects exit 1.** They produced fragments in that run only because the agent
**deviated from the documented command**. ⭐⭐ **The new file copied its broken sibling's reference — a
defect propagated by IMITATION into the very deliverable meant to close the gap**, which is the
sharpest instance of doc-contract drift this epic has recorded.

**D-098-b — "Phase Dispatch Boundaries" is a permanently dead report section.** `compile-report.py`
reads a **top-level** `dispatch_boundaries` key; `analyze-logs.py` **nests** it inside its log-analysis
fragment; **no aspect registers it.** ⛔ The omission classifies **benign** (`sections_omitted`), so the
loud half never fires — **a drop reported as an omission**. ⚠ **Test fixtures hand-construct the key**,
so the suite is **green over a shape production never emits.**

**⭐ D-098-c — the answering tier was NOT the tier the plan shipped, and the plan said so.** The
retrospective resolved a post-merge footprint via **tier 2 (`realized_capture`)**, not D1's new tier 4
(`pr_landing`): `branch-cleanup` wrote the capture before removing the worktree, so the fall-through
never reached it. ⇒ **D1's tier is shipped and controlled-tested but UNEXERCISED IN THE WILD.** Not a
defect in the plan — a defect in how a landing would otherwise read. Do not treat #1359 as validating
tier 4.

**⚠ D-098-d — `record-metrics` records no typed facts.** Totals ride `display_detail` prose;
`phase_steps` carries no `facts` sub-dict, so `total_tokens` / `total_wall_seconds` are unreadable from
where the landing spec points. The landing read them from the metrics store instead and **named the gap
rather than degrading the values to `unknown`** — the right handling. Also: **billing-weighted total
has no schema key at all** (185.4M uncarried).

**⚠ D-098-e — `steps` can never be complete for the last two composed slots.** `emit-landing` cannot
observe its own terminal outcome and `archive-plan` (order 1100) has not run when the landing is
written, so both read `unknown` **by construction**. ⛔ Structural, not a producer defect — writing
`done` there would fabricate an unobserved state. Worth a schema note so a reader does not chase it.

### ⛔⛔⛔ 2026-08-26 — A LIVE DATA-DESTRUCTION PATH IN MERGED MAIN. Read this second (after the merge-path false-green).

Ingested from an operator paste of a **foreign-machine** plan-marshall report, after that machine lost
a plan directory to `worktree-remove`. ⭐ **The paste named one mechanism; first-party corroboration at
`31bed3e76` found three, and the two it did not name are the ones that explain why nobody caught it.**
Staged as **`PLAN-TRUTH-114`**. ⛔ **This is a RECURRENCE** — `leaf-validator-yield` closed as a no-op
after a hand-invoked `worktree-remove` lost the plan dir, and that was recorded as operator error
against a guard believed to be script-enforced. **It was not operator error.**

**D-114-a — the move-back guard resolves through the very tree it protects, so it fails OPEN.**
`cmd_worktree_remove` (`git-workflow.py`:1545) gates on `_plan_dir_on_current_checkout(plan_id)`, which
walks up from **cwd** (`_find_plan_root_from_cwd`, `marketplace_paths.py`:374) and probes
`{root}/.plan/local/plans/{id}/status.json`. With cwd inside the worktree the walk-up terminates at the
worktree, the probe finds the **worktree-resident** `status.json` — the sole authoritative copy the
guard exists to protect — and returns `True`. The refusal never fires. ⛔ **Not a typo: the predicate's
own docstring documents that resolution as INTENDED**, because it was written for
`cmd_locate_plan_checkout`, whose contract genuinely is *"is it on the current checkout"*. ⚠ A second
cwd-derived value at the same call site (`main_root`, :1524) becomes the worktree too, so the `git -C`
target is the tree being removed.

**D-114-b — the cwd-keyed audit JUSTIFIED this predicate by naming ONE caller, and the second caller
inverts its reasoning.** `cwd-keyed-store-resolution-audit.md`:55 dispositions
`_plan_dir_on_current_checkout` as **JUSTIFY (positive-presence probe)** on the stated ground that it
feeds `cmd_locate_plan_checkout` and that *"a `False` … is disambiguated by the caller's second
(structural worktree) probe … it never stands alone as authoritative absence."* ⛔ **`cmd_worktree_remove`
is a second caller the audit never enumerated**, where the predicate DOES stand alone and the
conclusion drawn from it IS a destructive authorization. ⭐⭐ **And the polarity is inverted**: the audit
reasoned about a `False` standing alone as authoritative *absence*; the live defect is a `True` standing
alone as authoritative *presence*. ⇒ This is the **"a reviewer's list of call sites is a SAMPLE, not an
enumeration"** archetype, and it is the epic's population-derived-detector rule violated inside an audit
whose whole subject was resolution blindness.

**D-114-c — every existing test pins the resolver to `main` by fiat, so the suite structurally cannot
observe the defect.** `TestWorktreeRemoveMoveBackPrecondition._patch` (`test_git_workflow.py`:1494) sets
`monkeypatch.setattr(git_workflow, '_find_plan_root_from_cwd', lambda: main)` — in the refusal case AND
the `--force` case — and `TestWorktreeRemove` (`test_git_workflow_worktree.py`:432) does the same. ⭐ The
precondition fixture builds the **exact** real-world geometry (main + registered worktree holding the
sole plan state) and then overrides the one value that would make it fail. ⇒ **vacuous-guard /
test-pins-the-assumption**, and a one-line change to that lambda flips it red — which makes it a clean
confirm/refute artifact rather than a rewrite.

**D-114-d — three documents advertise a protection the code does not provide.**
`branch-cleanup.md`:1497 states *"The `worktree-remove` verb operates on the main checkout internally and
does not rely on the caller's cwd"* — **false at both cwd-derived points**. `worktree-handling.md`
§ Cleanup Ordering item 0 and `branch-cleanup.md`:92 both advertise the refusal as script-enforced and
**not overridable by `--force`**, which is precisely why a caller trusts the ordering instead of
double-checking. `cwd-policy.md` states the phase-5+ invariant as *"never changed away from the pinned
worktree"* (:23) while also stating the move-back runs *"with cwd = main"* (:19) — and **neither fixes
the cwd at the `worktree-remove` call site, which sits between them.** ⇒ doc-contract-divergence, and
the reason the guard's blind spot was invisible from the docs alone.

**D-114-e — `manage-findings` reports a false not-found over a store it declines to scan (FOLDED to
`PLAN-TRUTH-109` as D5).** `resolve_finding` asserts parent existence through `get_finding`, which
enumerates `_list_finding_files` — whose docstring states the exclusion outright: *"excluding qgate-\*,
assessments"*. A Q-Gate finding therefore returns `Finding not found: {hash_id}` from `resolve`, while
the **same module's** `query_findings` merges that store and advertises it (`qgate_included: True`,
separate `plan_count` / `qgate_count`). ⛔ **`-109`'s D0 sweep as written would have MISSED this**: it
looks for *"a store path that may not exist"*, and here the store exists and is read by a sibling verb.
The sweep predicate was widened accordingly.

**⛔ D-114-g — A THIRD FAILURE MODE OF THE SAME VERB, found 2026-08-26 while doing the cleanup, and
NOT foldable into `-114` because that plan had already gone `running`.** `worktree-remove` against the
stranded `metrics-ledger-readers-and-timestamp-provenance` returned
`plan_resolution_failed` — *"manage-status get-worktree-path returned non-success: error='file_not_found'"*.
⇒ **The verb cannot clean up after an ARCHIVED plan at all**: the removal path is gated on a plan
record that finalize itself archives, so the worktree the lifecycle created becomes unreachable through
the lifecycle's own removal verb. ⭐ **This refuses EARLIER than the move-back guard** — at
`_resolve_worktree_path_for_plan`, before `:1545` is reached — so it is distinct from D-114-a
(fail-open) and from D5's timeout (fail-slow). **Three polarities, one verb:** fails open, fails slow,
and is unreachable. ⚠ **It is also why W-088-b's worktree survived two days**: the hand path was not
merely preferred, it was the only path that existed.

✅ **DELIVERED 2026-08-26 by operator paste, at phase `1-init`.** It could not reach `-114` through the
ledger — the running-row exclusion forbids re-scoping a spec mid-execution, and `inbox write
--target-plan` is refused by the running-plan guard (F8: a mid-run inbox message has no reader; the
channel that would carry it is `PLAN-TRUTH-100`, still **staged**). ⇒ The operator pasted it directly
into the running session. ⭐ **The delivery landed at `1-init`, on main, before the worktree existed —
so this was NOT a mid-execution re-scope at all**, it was an addition to a brief still being formed.
⚠ **The orchestrator's own timing was the near-miss, not the mechanism**: the row was transitioned to
`running` on operator confirmation minutes BEFORE the finding was made, which is what closed the ledger
path. **A confirmed start and an observed start are not the same instant**, and the gap between them is
where a finding becomes undeliverable. Adjacent to `-100`; do not re-derive.

**⛔ D-114-h — A FIFTH `worktree-remove` FINDING, from the 2026-08-27 inbox drain, and it ALSO cannot
reach `-114`.** Inbox message `lessons-handling-26-08-26-01-012.md` (lesson `2026-08-24-16-001`),
absorbed here as an observation because `-114` is `running`. ⭐ **`worktree-remove` reports a single
boolean `clean` for two dirty states whose dispositions are OPPOSITE:**

| Dirty state | Correct disposition |
|---|---|
| dirty with **uncommitted work** | refuse and preserve — there is work to save |
| dirty only with **deletions of tracked, index-clean files** | recoverable; preserving the tree saves nothing |

⛔ **The step's own hint is self-defeating on this path** — *"Pass `--force` only after verifying the
worktree is clean"* asks for exactly the verification that has already failed. ⇒ Distinguish the two in
the payload and **report WHAT makes the tree dirty** (the porcelain lines), so the operator decision
does not need a separate manual probe. **Matched pair required**, because the dispositions are opposite.

⭐⭐ **It independently corroborates `-114` D5's timeout half, which I had filed only as a HYPOTHESIS:**
*"The 60s internal git bound produced a **timeout** on the first call and the real refusal only on the
second. A transient timeout and a substantive refusal reach the caller as the same
`error: worktree_remove_failed`."* That is a second, independent observer of the same conflation.

⛔ **Read the scope limit before acting.** The lesson's own words: *"The cause is unknown. This lesson
records an observation, not a diagnosis."* Four tracked files (`LICENSE.md`, `build.py`, `pw`,
`pw.bat`) vanished from one worktree **after a clean push**; the worktree was later force-removed, so
**the only instance is gone**. ⭐ A hypothesis was raised **and refuted by its own test** — the obvious
candidate was the first `worktree-remove` call, which timed out at the 60s bound and is the only
file-deleting operation in the window; **refuted, because the `.plan/temp/` scratch written earlier is
fully intact**. ⇒ **DO NOT stage a plan to find the cause.** The routable part is the payload change,
which does not depend on the cause being found.

⚠ **Same delivery constraint as D-114-g** — running-row exclusion plus the running-plan inbox guard ⇒
**operator paste if it should be in `-114`'s scope**, otherwise its own spec once `-114` lands.

**⚠ D-114-f — UNVERIFIED LEAD, recorded as a Watch, not a finding.** The same report names a
*"sonar-roundtrip false negative"* as a third, lower-severity defect. The paste carries **no mechanism,
no file, and no symbol**, so nothing was corroborated and nothing is staged. See § Watches.

### ⛔⛔ 2026-08-26 — From the PLAN-TRUTH-086 drain (PR #1351, `b4e8a2364`, 10 messages)

**D-086-a — A LANDING SHIPPED WITH NO `kind: landing` MESSAGE.** The plan filed 10 messages, **all
`candidate-lesson`**. `emit-landing` produced no landing envelope, so there is no `landing-facts`
block, `inbox landing-check` had nothing to run against, and the PR number, merge state, deliverable
counts and step outcomes were recovered from the **operator paste and git** rather than from a
machine-readable fact. ⛔ **The drain's vocabulary has no term for this**: `landings_incomplete`
counts landings that carried a partial block, and this landing is **absent**, not incomplete —
the two are different and only one is currently representable. ⚠ Both prior drains (`-094` #1343,
`-087` #1340) emitted `complete: true`. ⇒ Adjacent to `-110` (a plan decides what the epic learns and
nothing audits that decision) — this is that defect's strongest instance: the plan decided to emit
no landing at all and nothing noticed.

**D-086-b — a queue row went `staged` → `shipped` in one step, with no record it was ever in flight.**
The orchestrator emitted the command under `auto_emit: false`; the operator launched without
confirming back, so no `launched` transition was ever recorded. ⚠ **This is CORRECT under the
emit≠running invariant** — the orchestrator must not record a start it did not observe. The defect is
the consequence, not the rule: the ledger has no representation for *"launched, unobserved"*, so a
plan that ran for a full day is indistinguishable from one that never started. ⇒ Not a rule change;
a missing state.

**D-086-c — the retrospective graded the run against a plugin-cache reference contract 314 versions
stale** (inbox `-008`). ⚠ UNOWNED. Same family as `D-088-b` and the stale-executor findings from the
`-087` drain: derived state outliving the tree it describes.

⚠ **Not re-filed here (routed):** `-002` merge-queue corroboration → lesson `2026-08-26-15-001`
(**confirmed first-party twice this session, independently — see below**); `-001`+`-010`
stopping-short → lesson `2026-08-26-15-002`; `-003` → `-097`; `-004`+`-006` → `-098`; `-007` →
`-101` (seventh member); `-005`/`-009` already tracked as R5 / R7.

⭐⭐ **`-002` is the one to read: two observers, two runs, same false signal.** `ci pr merge-queue`
returns `enqueued: true` with `enqueue_corroboration: "merge_queue rule active on branch"` — a claim
about the **branch rule**, never about **this PR's membership**. This orchestrator hit it landing
#1347 and #1350 and recorded it *before* draining the plan's identical finding. The upstream doc
already concedes the scope (*"a pre-enqueue probe … run BEFORE the `gh` call"*) — so a documented
**pre**-condition is being consumed as a **post**-condition confirmation.

### ⛔⛔ 2026-08-25 — From the unanalyzed-landing sweep of #1345 and #1346

Neither PR is ours and neither is re-staged. Both were ingested as **OBSERVATION** — no queue
transition, no `landings/` record. What they change for THIS epic is recorded here.

**D-SWEEP-a — TWO PARSERS READ ONE `## Expected Surface` AND RETURN CONTRADICTORY ANSWERS, AND THE
LOSING ONE GOVERNS CONCURRENCY.** Measured first-party at `a2be2691c` on `PLAN-TRUTH-098`:

| Reader | Verdict | Consumed by |
|---|---|---|
| `orchestrator.py` queue renderer | `(no expected surface)` | ⛔ **the disjointness gate** |
| `epic-surface-partition classify` (#1345) | `declarative`, **6 resolved paths** | the partition report |

⛔ This is strictly sharper than the "no machine-readable form" framing `-113` was staged on: it is
not that the declaration cannot be parsed — **it IS parsed, correctly, by a reader that is not wired
to the gate.** It also mechanically explains the `-098` cross-check blind spot recorded during that
staging. ⇒ Folded to `-113` § RE-SCOPE; the remedy shrinks to *re-point the gate and delete the
second parser*, and `-113` D1's "3 surfaceless staged specs" figure is corrected in place.

**D-SWEEP-b — #1345 added a THIRD plan-id detector and it does not recognise `PLAN-{CODE}-{NNN}`.**
`classify`'s `plan_id` returns the whole filename for every code-slug spec (`PLAN-TRUTH-113-….md`
instead of `PLAN-TRUTH-113`), while the older numeric form resolves correctly. ⇒ `attribution` and
multiply-claimed detection **cannot group by plan for this epic at all**, since `truthful-signals` is
entirely code-slug named. ⭐ `orchestrator inbox detect` already declares itself *"the single
detection seam — consumers never add a second detector"* and accepts all three forms. ⚠ Cross-bundle
(`pm-plugin-development` vs `plan-marshall`) — confirm ownership before editing. ⇒ `-113`.

**D-SWEEP-c — ADR-019 is this epic's thesis promoted repo-wide, and the orchestrator is in its
declared scope.** *"An audit separates what it could not evaluate from what it evaluated and found
wanting"* (Status **Proposed**); `affects:` names `plan-orchestrator` and
`tools-epic-surface-partition`. ⛔ **`(no expected surface)` rendering as a silent pass at the
disjointness gate is therefore a LIVE ADR-019 violation inside our own machinery**, not an adjacent
concern. ⇒ `-113` D2 cites ADR-019 as authority rather than re-deriving the rule. ⚠ The ADR is
`Proposed`, not `Accepted` — cite it as governing intent and note the status.

⭐ **Also corrected by the sweep:** the staged corpus is in BETTER shape than `-113` assumed — all
**23** staged specs classify `declarative` (0 prose); the 43 `prose` specs are all terminal rows.
Five staged specs carry unresolved entries: `-086` (**7** of 39), `-090`, `-091`, `-092`, `-097`.

### ⛔⛔ 2026-08-25 — From the PLAN-TRUTH-087 drain (PR #1340, `b5ee8fac7`, 13 messages)

**D-087-a — A PER-RUN CEILING RAISE BECAME THE PROJECT DEFAULT, SILENTLY. ⚠ OPERATOR DECISION OWED.**
The loop-back ceiling was raised `3 → 8` mid-run to unblock this plan. `.plan/marshal.json` **is a
tracked file** — an exception to the `.plan/` gitignore — and `b5ee8fac7` is its most recent
modifier, carrying exactly one hunk: `-"max_iterations": 3, +"max_iterations": 8,` under
`phase-6-finalize`. ⚠ **The raise was load-bearing** (6 iterations spent; at 3 or 5 the run halts
with findings unreviewed) — that is not in dispute. ⛔ **What is: it rode into main inside the plan's
own footprint and is now standing policy for every future finalize, with no decision-log entry and
no step record.** The only trace is the config line. ⇒ Keep 8, or revert and make per-run raises
explicit and scoped.

**D-087-b — a step emitted a truthful `done` whose precondition had silently expired, INTO THE
LANDING PAYLOAD.** `finalize-step-sync-baseline` recorded `done` against an earlier base; a
mid-finalize rebase then replayed 24 commits with 3 carrying conflicts across 7 files, hand-resolved;
the step was skipped as not head-dependent and never re-ran. **The landing's machine-readable `steps`
fact therefore reads `finalize-step-sync-baseline:done` for a baseline that no longer exists**, and
no record anywhere states a rebase happened. ⇒ Folded to `-097` with `-004`/`-011`.

**D-087-c — the declared surface has no machine-readable form, so two honest measurements disagree
by 27 points.** The landing claims recall `100% (44/44)`; a path-exact measurement at the drain gives
`30/41 = 73.2%` with 26 substantive undeclared files. Neither is wrong-by-carelessness: the
`## Expected Surface` section mixes abbreviated paths, bare filenames and glob fragments. ⇒ Folded to
`-113` D0 as first-party evidence.

**D-087-d — a landing Residue claim was CONTRADICTED at ground truth.** It states 14 files of a new
skill (`tools-epic-surface-partition`) shipped in this PR outside every declared surface. **#1340
contains zero such files**; the skill landed in **#1345** (`00b92fca3`). The Residue described the
worktree at retrospective time, not the merged PR. ⚠ **Generalise the process point, not the
instance: a retrospective that reads the WORKTREE and a landing that describes the MERGE are two
different populations, and the payload does not say which one a Residue bullet came from.**

**D-087-e — ✅ DISCHARGED 2026-08-25 via PR #1347 (`a2be2691c`).** Issued on operator direction, each
`--insight` extracted VERBATIM from its archived message rather than retyped. Corroborated at main
rather than taken from the merge report: `enriched.json` on `main` carries **6** insights (was 2).
⭐ **The obligation was larger than it looked: `.plan/project-architecture/**/enriched.json` is a
TRACKED file**, so the owed calls were never merely local bookkeeping — an unissued hint is a **lost
repository change**, which is why an archived plan silently dropping four of them matters. Original
entry retained below as the record of what was owed.

**D-087-e (as filed) — 4 owed `architecture enrich insight` calls are UNISSUED, and nothing tracks them.**
`-005`…`-008` carry exact commands to run after merge (the discover-after-merge rule). The
`plan-marshall` module record carries **zero** insights, so none was applied, and **the plan that
owed them is archived** — the obligation has no owner. ✅ The retrospective's flagged overlap is
RESOLVED: not duplicates. The archive holds two prior hints; the only near-match is *"improvement
findings are a standing consideration"* for module `orchestrator`, while `-005` is the same insight
for module `plan-marshall`. Per-module insights, both legitimate. ⇒ Handed to the operator — the
orchestrator does not mutate the architecture store.

**D-087-f — the daemon reconcile is owed, not done.** `owed: true`, `defer_count: 1`; `marshalld`
was busy at cache-sync time and deferred rather than draining a live build. Still on the
pre-`0.1.1547` pin. ⚠ UNOWNED.

**D-087-g — three of five operator turns were bare nudges** (`retry`, `contniue`, `contniue`). The
run stalled and needed hand-restarting three times, and **no metric or step record captures a
stall.** A run that needed three manual restarts reads identically to one that did not. ⚠ UNOWNED.

⚠ **Not re-filed here (already owned):** the self-review self-seeding pair → refinement on lesson
`2026-08-09-13-001` + new lesson `2026-08-25-15-001`; stale-executor findings → lesson
`2026-08-25-15-002`; the three review-participation findings → `review-apparatus`
(`truthful-signals-037.md`); head-dependence pair → `-097`.

### ⛔ 2026-08-25 — From the PLAN-TRUTH-094 drain (PR #1343, `1169fb5bf`, 8 messages)

**Five plugin-doctor rule-surface defects with NO owner.** The other seven findings from inbox `-001`
folded into `-101` / `-104` / `-111` / `-108`; these five are one subsystem and one theme — *plugin-doctor
documents or ships rule machinery that emits nothing* — and are held here pending the `7a3b32` operator
decision, which governs whether four of them are defects at all.

**D-094-a — seven documented rule ids have no emitter; two detectors run and their output is
discarded.** *(`7a3b32` — ⛔ NEEDS AN OPERATOR DECISION, escalated 2026-08-25)* Of 18 ids
`plugin-doctor/SKILL.md` cites, **7 exist nowhere in 426 scripts**. `check_explicit_script_violations`
and `check_command_self_containment` execute and return under keys `_doctor_analysis.py` never reads,
so no `Finding` is ever constructed. ⚠ **Two reviewers disagreed on the classification**, and the
disagreement is the whole difficulty: are the `doctor-skills.md` sections documenting these legitimate
**LLM-phase checks**, or **documentation of rules that emit nothing**? That is a design call about
whether plugin-doctor's LLM phase is a first-class rule surface — not a bug report. ⛔ **Until it is
settled, D-094-b…e must not be scoped**, because the same answer decides whether they are dead code or
an unwired second tier.

**D-094-b — `validate_command_mappings` is dead code.** *(`74b801`)* Leaves **3 of 10** documented
`extension.py` contract requirements checked by nothing: required-profile presence,
`discover_modules()` compliance, and `ExtensionBase` inheritance.

**D-094-c — plugin-doctor ships a tested `extension.py` validator nothing can reach.** *(`d2785d`)*
`validate_extension` / `scan_extensions` cover 7 of 10 contract bullets and **are unit-tested**, but
have no caller, sit behind the unregistered `_validate.py`, and the gate's extension entry is the
*different* `validate_extension_contracts`, whose population excludes these manifests by
directory-name prefix. ⇒ **11 manifests validated by nobody, and a green row printed.** ⭐ The unit
tests are what make this dangerous: they are the evidence a reader would cite for coverage that does
not exist.

**D-094-d — a stated contract nothing enforces, asserted to be enforced.** *(`b9a23d`)*
`_doctor_shared.py`'s docstring says every entry must have a `fix-catalog.md` row; `rule-provenance.md`
says **a regression test enforces it**; **no test does**, and the tree violates the contract while
green. ⚠ The false part is the *claim of enforcement*, which is worse than the missing test — it tells
a reader not to look.

**D-094-e — prescribed tooling that does not exist.** *(`8668f3`)* `verification-guide.md` prescribes
`verify-fix.sh` and `analyze-tool-coverage.sh`; plugin-doctor ships **no `.sh` files at all**.
`safe-fixes-guide.md` sample code names `FIX_PRIORITY`, which exists nowhere.

⚠ **Not re-filed here (already owned):** `e2b602` → `-101` (sixth member + a recurrence of its fifth);
`ec6c97` → `-104`; `8d655d` / `ed23b9` / `0c4569` → `-111` D6–D8; the `-004` self-review half → `-108`.
`5bdbb9` and `a02741` are **review-apparatus's** and are already live in that epic's inbox — this drain
added nothing there.

### ⛔ 2026-08-24 — From the PLAN-TRUTH-088 drain (PR #1342, `91bbe7470`, 16 messages)

**D-088-a — the sanctioned inbox lifecycle verb was bypassed for the SECOND consecutive landing.**
`-096` corrected message `-009` without `inbox amend` (D-096-c); `-088` declared message `-015`
superseded **in its Residue prose** while the envelope still read `lifecycle: live`,
`superseded_by: ""`. I recorded it properly with `inbox supersede`, and the drain then routed it as
`retired_by_successor` without running its `kind: landing` branch — which is the whole point, since
running that branch would have driven a second full-ship reconciliation for one PR. ⛔ **Two
landings, two different verbs, same failure**: the verb exists, shipped, and the emitting site does
not reach for it. This is no longer an incident. ⚠ **UNOWNED.**

**D-088-b — `0.1.1240` is UNMARKED in the plugin cache, and it caused three distinct failures in one
day.** Surveyed first-party this session: cache holds `{1240, 1526, 1527, 1538, 1539, 1541, 1542}`,
unmarked = **`{1240, 1538, 1542}`**. Because `1240` is unmarked it is live to the loader, and that
one fact explains: (1) `lessons-capture` emitting the duplicate landing `-015` from a body that
structurally cannot carry a `landing-facts` block; (2) the served `manage-metrics` SKILL.md
documenting a **6**-value `--termination-cause` enum where the live argparse accepts **12**
(inbox `-001`); and (3) this session's own harness surfacing the **pre-#1162**
`marshall-orchestrator` / `persona-marshall-orchestrator` skill names. ⭐ **The retired
`unmarked == [pin]` framing would report this clean — three unmarked dirs, one of them the pin.**
Only `executor == installPath` catches the gap, and the loader following an unmarked STALE dir is the
separate hazard.

**D-088-c — nine findings shipped unfixed, and one is an independent confirmation of `D-CI`.** All
nine were recorded and are out of footprint. Three matter here: the routed build reporting
`tests_run: 0` on every green run (R6/R57 — `-087` DA, still RUNNING); **the circular CI skip that
verified nothing for most of this PR's life** — an independent second sighting of the R95 `D-CI`
family, on a different PR and a different plan; and `scope_creep_check` rendering an unmeasured
comparison as a clean zero (folded to `-104` as arrival path 3). ⛔ **R95 is no longer a single
observation.**

### ⛔ 2026-08-24 — R50 / R60 revisited now that PLAN-TRUTH-096 has landed. PARTIAL CLOSE.

Both defects were explicitly deferred with *"revisit when `-096` lands."* It has. Verified against
the shipped `landing-payload-spec.md` at HEAD `77db1a0d3` — **one half closed, both defects remain
open**, and neither may be marked resolved.

✅ **CLOSED — the false-completeness half.** `-096` D1 shipped the split by CONDITION, not by key:
`n/a` is the **answered-degraded** class ("a PR that was never created, a real end state"), `unknown`
is the **could-not-read** class ("asserts only that nothing was observed"), and *"`emit-landing.md`
routes EVERY failed read here, at every key."* A failed read can no longer be laundered into
`complete: true`. This landing's own message is the proof: `pr=unknown` → `complete: false`.

⛔ **STILL OPEN — `D-1337-e`.** A landing that is **complete-as-possible** (ad-hoc / cross-repo /
foreign-machine, no plan lifecycle) has no `plan_id`, `deliverables_*`, `total_tokens` or `steps` **to
read**. It must write `n/a` at those five, and for those five `n/a` **reads as missing** ⇒ it still
reports `complete: false` **identically to a plan landing whose facts were LOST**. The `n/a`/`unknown`
split fixed the `pr` / `merge_state` axis, where `n/a` is a legal answer; it did not give the five
must-exist keys a **structurally-inapplicable** representation. Two different zeros, still collapsed.

⛔ **STILL OPEN — `D-075-g`**, in its whole-block-absent form. A landing carrying **no
`landing-facts` block at all** still surfaces as all-eight-missing, indistinguishable from a producer
that emitted a block and lost every value. The split discriminates *values*; it does not
discriminate *a block that was never written*.

⇒ Both belong to **`PLAN-TRUTH-106`**, which is now unblocked on `-096` (R70 cleared) and waits only
on `-104`. ⛔ **Do not record either as closed by `#1338`** — the half that closed is the half
`-096` scoped, and saying otherwise is the exact over-claim this epic tracks.


### ⛔ 2026-08-24 — From the PLAN-TRUTH-096 drain (PR #1338, `77db1a0d3`, 13 messages)

**D-096-a — three DEFECT-BEARING findings were archived `pending`, and this is the instance W-VIS-a
could not confirm.** `bug.jsonl` in the archived plan carries exactly three rows, all `resolution:
pending`: **`e9ef2c` (severity `error`)**, `5ed45d`, `5721cb`. ⭐ **Read against W-VIS-a**: my
retracted `-095` claim was wrong because all 29 of those were `assessments` with no `resolution`
field. These three DO carry the field and DO carry `pending` — so the pattern is real, it simply was
not real *there*. ⚠ The distinction that saved me from a second false measurement is the same one:
**tally by TYPE before reporting a pending count.** All three now have owners
(`-106`, `-093`, `-086`); they survive the archive only through this drain.

**D-096-b — the landing drained INCOMPLETE at `pr`, and the emitter was right to let it.**
`landing-check` on `-012` returns `complete: false`, `missing_keys: [pr]` — **7 of 8 required keys
supplied**, against `-075`'s all-eight-missing one day earlier. Cause is finding `e9ef2c`:
`create-pr`'s record carries **no `facts` sub-dict at all**, only `display_detail: "#1338"`, while
`create-pr.md` mandates `--fact pr_number=` on both branches (doc byte-identical across cache
`0.1.1538`/`1539`/`1541` ⇒ a live producer gap, not version skew). ⛔ **Do not "fix" this by making
the landing report complete** — `n/a` at `pr` would drain as *"no PR exists"* for a PR that merged,
and re-parsing `#1338` from `display_detail` is forbidden. `unknown` is the honest token. Owned by
`-106`. ⭐ **Nothing surfaces the loss at the step**: `create-pr`'s `display_detail` is intact, so only
the drain sees it.

**D-096-c — a message was corrected in place WITHOUT the `inbox amend` verb, and its envelope cannot
tell.** The runner reports correcting `-009` before it drained, and the body confirms it (*"The
original version of this message carried that hypothesis"*). But the envelope carries **no `amended`
field and `revision: 0`** — indistinguishable from a virgin message. ⛔ This is exactly what
`PLAN-TRUTH-038` (#1198) built `inbox amend` to prevent: *"a bare in-place edit that left the
envelope unchanged would only replace an authorized bypass with an unauthorized one."* The verb
exists, shipped, and was not used. ⚠ **UNOWNED** — the gap is that nothing makes the sanctioned path
the reachable one at the emitting site.

**D-096-d — our own prep-ready gate is vacuous over 19 of 124 specs.** Verified first-party at head
`77db1a0d3` after `code-intelligence-substrate`'s message 026: **19 specs carrying a `Claim Labels`
heading parse to ZERO claims** — 13 table-form, 6 prose-only. `orchestrate.md` Step 4 defines
prep-ready as *"iff no row carries `admits: false`"*, and **zero rows means no row carries it**, so the
admission gate returns READY for a spec it could not read. Affected STAGED plans: **`-086`, `-089`,
`-090`, `-091`, `-092`** (table-form) and **`-097`** (prose-only). ⛔ **`-086` is the plan R3 names as
the sole candidate unblocked when a slot frees** — so this is not a latent defect, it is on the next
emit path. ⭐ `#1338` closed only the case-sensitivity gate (and closed it for BOTH addressed
headings, one line wider than CIS reported); the bullet-form gate in `_parse_claims` remains. Remedy
owned by **`PLAN-CIS-051`** — we stage nothing, but until it lands, **treat a prep-ready PASS on any
of those 19 as INDETERMINATE, not as READY.**

### ⛔⛔⛔ 2026-08-24 — A LIVE FALSE-GREEN IN THE MERGE PATH. Read this first.

Surfaced by the type-separated live-plan findings sweep, **filed by running plans, invisible through
the sanctioned read path**, and NOT reported through any channel that reaches an operator.

**D-CI-a — the CI-complete precondition resolved GREEN off a run whose heavy verify was SKIPPED, on a
tree whose tests were RED.** *(filed by `metrics-ledger-readers-and-timestamp-provenance`,
`qgate-6-finalize`, severity **error**)*

> At head `031e5293e` the `ci-complete` precondition returned `wait_succeeded` / `ci_final_status:
> success` and `ci_verify` recorded outcome **green with 0 findings**. **A local `module-tests` run on
> that exact tree was RED — 17977 passed / 2 failed.** The CI observable was `overall_status: success`
> across 5 checks, but **`verify / verify` was SKIPPED while `verify / conclusion` reported SUCCESS.**

⭐ The filer separates what it proved from what it inferred: *"VERIFIED: the local failure, the skipped
job, and the green precondition. INFERRED (not proven): the mechanism."* **Preserve that split.**

**D-CI-b — CIRCULAR SKIP: no `pull_request` run exists, so every push run skips verify and nothing
tests the PR.** *(same sweep, severity **error**, evidence explicitly marked verified-not-inferred)*

> Against PR #1342: `ci checks pull-request-runs` returns `run_count: 3`,
> **`pull_request_run_count: 0`**, `has_pull_request_run: false`, **`not_triggered: true`**. All three
> runs are **push**-event runs, and in every one **`verify / verify` is SKIPPED while
> `verify / conclusion` reports SUCCESS.** `python-verify.yml`'s own concurrency comment states the push
> run skips the heavy verify **precisely BECAUSE the commit is covered by an open PR**, delegating real
> verification to the `pull_request` run. **That run does not exist.**

⛔⛔ **The delegation is circular and the required check reports SUCCESS at both ends of it.**
`verify / conclusion` is the required gate; it is green over a skipped job, on a PR nothing verified.

**D-CI-c — PR #1343 received no `pull_request` event at all; the entire PR-triggered fan-out is
missing.** *(filed by `plugin-doctor-detector-coverage-residue`, severity **error**)* — the same
condition observed on a second PR, which makes it a pattern rather than one misfire.

⚠ **OWNERSHIP.** `PLAN-TRUTH-087` (`build-gates-test-suite-confidence-and-ci-workflow-lint`) is the
named owner of CI-workflow lint and build-gate confidence, and is **RUNNING** — so these cannot be
folded into its spec. ⭐ **The detection machinery already exists and worked**:
`workflow-integration-github`'s `pull_request_runs` verb reports exactly the `not_triggered` observable
that proved D-CI-b. **What is missing is that nothing CONSUMES it before the merge gate.**

⛔ **Do not treat this as a CI-configuration curiosity.** A required check reporting SUCCESS over a
skipped verify, on a tree with failing tests, is the exact class this epic exists to close — and unlike
most entries here it is **live in the merge path right now**.

### From the 2026-08-24 PR #1340 run (operator transcript, mid-run)

**D-1340-a — `ci pr view` returns no PR body, so no caller can append to one.** ⛔⛔ **VERIFIED
FIRST-PARTY, and the runner's FRAMING IS STALE — record both halves.**

**The capability gap is REAL.** `ci pr view --pr-number 1340` returns 12 fields
(`status`, `operation`, `pr_number`, `pr_url`, `state`, `title`, `head_branch`, `base_branch`,
`is_draft`, `mergeable`, `merge_state`, `review_decision`) and **no `body`**, with no flag to request
one — while `pr edit` **replaces** the body from a scratch file. ⇒ **Read-modify-append on a PR body is
unreachable through the abstraction, and a caller attempting it silently overwrites what it meant to
append to.**

⛔ **But the runner attributed it to a LIVE documented instruction, and that instruction is already
RETIRED.** `architecture-refresh.md:276` reads: *"This branch **previously** prescribed `ci pr view` →
`ci pr prepare-body --for edit` → `ci pr edit`… **No PR exists when this step runs**"*, and states the
remedy is a **re-homing** of the deferred-enrichment note to a surface after `default:create-pr`. ⇒ The
doc withdrew the sequence for a *different* reason (no PR exists yet) and does not currently prescribe
it. **The runner's "a documented remedy with no reachable invocation" is not true of this doc today.**

⭐⭐ **The sharper finding, which neither the runner nor the doc states:** the doc's owed re-homing
**targets a surface after `create-pr`, where a PR does exist — and that surface hits this exact
capability wall.** ⇒ **The gap does not merely explain the retirement; it blocks the fix the retirement
promises.** ⚠ UNOWNED. Not `-101` (nothing is currently mis-documented); it is a CI-abstraction
capability gap with a named blocked consumer.

**D-1340-b — the `create-pr` renderer truncated `## Intent` mid-sentence at a 1500-character budget,
dropping the explicit non-goals paragraph.** The run reports the cut landed at `**Explicit`, so *"the
explicit non-goals paragraph never made it into the PR body"* — ⛔ *"precisely the paragraph that stops
a reviewer filing a scoped-out concern as a gap, **and the bots were about to read it**."* ⚠ **We did
not locate a `1500` literal in `create-pr.md`**, so the budget's home is unconfirmed; the truncation
itself is the run's first-party observation of its own output. ⭐ The runner's mitigation is worth
keeping as the pattern: rather than rewrite the body blind and lose the step's grounding, it posted the
missing content as an **additive top-level comment** — zero risk to the body. ⚠ UNOWNED; **check
against `review-apparatus` before staging**, since a truncated Intent is a review-input defect.

### From the 2026-08-24 inbox drain of PLAN-TRUTH-095 (PR #1339, `b95d78437`) — 13 messages

**FULL SHIP.** 9 of 13 messages folded into existing owners; the four below are UNOWNED.

**D-095-a — ➡ RE-HOMED to `code-intelligence-substrate`, NOT ours. Do not re-derive it here.**
Forwarded 2026-08-24 as `truthful-signals-049.md`, as a corroboration of **`PLAN-CIS-043` arm A**
(*"the self-review surface over-reports its own coverage"* — `_detect_count_prose` reads only
`SKILL.md` while its sibling reads `standards/*.md` too, so *"full surface" means the full FILE
surface, not the full DETECTOR surface*). ⭐ **Same family, different blind spot**, found by
cross-checking `PLAN-TRUTH-108` against their corpus rather than by reading ours. The substance, kept
here only as a pointer:
⛔⛔ **This qualifies this orchestrator's own analysis of one turn earlier**, which called the
`3→2→0→2→1→1` self-review pattern *"the design working"*. That holds for the delta-vs-full mechanism —
but `-095` names a case it does **not** cover. One over-claim appeared at **four sites** and was
corrected in the order *the tooling could see them* — docstrings, then assertion messages, then a
comment — because **the surfacer emits only `context: docstring` prose, so two copies were structurally
invisible.** ⇒ *"When a delta's whole content is uncovered prose, the candidate set is byte-identical
to the previous round's, and a clean verdict certifies nothing."* ⚠ **A clean delta round is not merely
a filter over a narrower file set; it can be a verbatim repeat of a round already run.** ⛔ **And the
full-surface confirmation pass is a WEAKER backstop than assumed** — CIS-043 arm A establishes it is a
full *file* surface, not a full *detector* surface. **Both defects must close for the step's closing
verdict to mean what it says.** ⚠ **OWNED BY CIS. Removed from our ledger.**

**D-095-b — `direct-gh-glab-usage` publishes a verdict over a population that is empty by
construction.** *(inbox `-001`)* It reports `counts.total: 0` with **no field naming what it scanned**.
Its Surface B is `git diff {base}...HEAD` with `base = args.base or 'main'` — so for a plan whose PR has
landed, `HEAD == main` (verified: both `b95d78437`) and **the diff compares a commit to itself.** Three
further paths in `_git_diff_added_lines` return `[]` silently (`FileNotFoundError`,
`TimeoutExpired`, `returncode != 0`). ⭐ **The matched control makes it concrete**: at the stale recorded
`main_sha` the aspect emitted **35 error-severity findings**; at the true merge base, **0**; at the
default, **0** — *the right answer, reached by not looking.* ⇒ Emit the resolved `base`, the diff file
count, and a three-way `status` (`evaluated` / `indeterminate` / `not_applicable`); return
`indeterminate` when the git call fails or `base == HEAD`. ⭐ **The precedent is in the same skill**:
`check-artifact-consistency` already reports `inconclusive` with `footprint_resolved: false` and
*"recall is unmeasurable, not 0%"*. ⚠ UNOWNED.

**D-095-c — a stale seated cache is an active generator of confident FALSE findings.** *(inbox `-007`)*
Every skill body in that retrospective envelope loaded from **`0.1.1240`**, per its own skill-load
banners. Reading the seated `manage-metrics/SKILL.md` (a 6-value `--termination-cause` enum) against the
plan's real rows, **10 of 11 carried causes absent from the documented enum** — textbook
doc-contract-divergence, plausible severity, plausible fix. Repo source documents **12**, argparse
confirms 12, and a contract test guards three enumeration sites. **It was refuted only because the repo
source was checked before the finding was written.** ⇒ Folded into `-106` D0 as direct evidence for its
cause (a); the **generalisable** half — *never file a doc-contract finding from a seated body without
re-checking repo source* — is recorded here and is UNOWNED.

**D-095-d — `CLAUDE.md`'s "Structured queries first" hard rule misdescribes the content sweep's
coverage.** *(inbox `-009`)* The rule's parenthetical says dotfile trees outside the allowlist
(`.claude/**`, `.github/**`) *"are **not** searched"*, which reads as a settled question. **The actual
allowlist is two FILENAMES, not directories.** ⇒ An agent trusting the documented coverage draws a
wrong boundary in either direction. ⚠ UNOWNED, and it is a **repo-root `CLAUDE.md`** change, not a
bundle one.

**D-095-e — `prune-local-and-remote-ref` guards the remote ref's absence but not the local branch's.**
*(inbox `-011`)* `_cmd_prune_ref.cmd_prune_ref` deletes two things and guards only the second, so it
**always errors on the documented cleanup order**. ⚠ UNOWNED.

### From the 2026-08-24 inbox drain of PLAN-TRUTH-075 (PR #1336, `77c9dc70a`) — 10 messages

**FULL SHIP** — a tracked plan of this epic, so unlike the #1330/#1332/#1337 observations it carries a
queue transition and a landing record (`landings/PLAN-TRUTH-075.md`). All 10 messages dispositioned;
most residue folded into existing owners. Only the two below are recorded as defects here.

**D-075-f — a finding superseded a claim in `solution_outline.md` and the outline was never
corrected.** *(from `-007` / `-009`)* PLAN-TRUTH-075's outline "Closed on re-verification" table, and
**both** the phase-2-refine and phase-3-outline agent summaries, state that PR #1299 *predates* the
plan's staging. **That is false** — staged 2026-08-09, #1299 landed 2026-08-18, executed 2026-08-23.
Finding `74f30d` carries the corrected chronology with `git show -s --date=short` evidence and
supersedes them, **but the outline's prose was never corrected**, so the plan's primary design artifact
still contradicts its own finding and archives that way.

⛔ **The two diagnoses have OPPOSITE remedies**, which is why this is a defect and not a tidiness
complaint: *"staging ingested a stale claim"* argues for better sourcing at staging time and is
**wrong**; *"the spec was accurate when written and its target was fixed by unrelated work during 14
days in the queue"* is **queue latency** and argues for re-verification at execution start. A reader of
the outline gets the wrong one. ⭐ The chronology was got backwards **twice by inspection** and right
only once `git` was consulted. ⚠ **UNOWNED.** The general shape — *a finding that supersedes an artifact
claim must correct the artifact, not only record the correction elsewhere* — is broader than one plan.

**D-075-g — a landing message carried NO `landing-facts` block at all.** `-010` is a real tracked
plan's landing, and `inbox landing-check` returns `complete: false` with **all eight** required keys
missing, `schema` included — the pre-fix prose-only shape. Every figure in the landing record was
therefore read out of prose or re-derived first-party rather than drained.

⭐⭐ **This SHARPENS `D-1337-e` and proves the two cases are distinct.** `D-1337-e` was a landing that
*could not* carry the facts (ad-hoc lane, no producers existed). **This is a plan that had a full
lifecycle and simply did not emit them.** ⛔ `check_landing_completeness` reports the two **identically**
— *"could not" and "did not" collapsed into one `complete: false`* — which is the same two-zeros
archetype, now with a matched pair of live instances one day apart. ⚠ **UNOWNED**, same as `D-1337-e`:
`PLAN-TRUTH-096` (orchestrator-inbox-and-landing-residue) is the natural home and is **RUNNING**.
Revisit both together when `-096` lands.

### From the 2026-08-23 ingestion of PR #1337 (`2cd1a19c8`, foreign machine, ad-hoc `NO_PLAN` lane)

Classified **OBSERVATION, not full-ship** — the run is untracked here, so **no queue transition and no
`landings/` record**, consistent with the R4/R16 precedent. Do not "fix" that by stamping a row.
**Every claim below was corroborated FIRST-PARTY at HEAD `2cd1a19c8`**; where the corroboration
sharpened or contradicted the report, that is marked and attributed.

⭐ **Coverage statement, per the R37 standing rule.** The population enumerated was the report's
**SECTIONS**, not its lesson list: §1 trigger, §2 root cause, §3 what shipped, §4 adversarial review,
§5 `finalize-step-simplify`, §6 PR review round, §7 verification, §8 process note, §9 residuals (5
items), §10 lessons (4 items). **All ten sections were dispositioned.** §§1–3, §7 corroborated with no
residue; §6 forwarded whole; §§4–5, §8–10 produced the items below.

**D-1337-a — the suspicious-permission audit polices the grammar that grants nothing and is silent on
the one that grants everything.** *(report § 9.2 — it ranks this highest-value of its three residuals;
the corroboration agrees and goes further.)* `_claude_runtime_impl.py:1009-1013` carries five
`suspicious_patterns`. Two of them — `Write(/tmp/` (medium) and `Write(/**)` (**high**) — are now
**false positives by this codebase's own shipped premise**, since #1337 established that `Write(...)`
allow rules are never consulted. ⭐ **SHARPENING: the coverage is not merely incomplete, it is exactly
INVERTED.** The audit's only **high**-severity filesystem-wide-*write* detector fires on the rule that
grants nothing, while **`Edit(/**)`, which genuinely grants filesystem-wide write, matches no pattern at
all** — nor does `Edit(/tmp/`. A settings file carrying `Edit(/**)` passes this audit clean. ⚠ The three
genuine patterns (`Bash(sudo:`, `Bash(*)`, `Read(/**)`) are correct and are not in scope. ⇒ **owned by
`PLAN-TRUTH-103` D1 (STAGED).**

**D-1337-b — `apply-fixes --scope project` can never reach the file whose entries actually take
effect.** *(report § 9.1)* `claude_runtime.py` carries two settings-path resolvers with **mirror-image**
preferences: `_claude_project_settings_path` (write, `:2389`) prefers `.claude/settings.json` when it
`is_file()`; `_claude_project_settings_read_path` (read, `:2406`) prefers `.claude/settings.local.json`,
and its own docstring calls that *"the file whose entries actually take effect for that operator"*. On a
project where both exist, a pruning `apply-fixes` writes the shared file and **never reaches the local
one**. ⭐ **SHARPENING — the MECHANISM is live in THIS repository while the SYMPTOM is absent, and the
two must not be conflated.** First-party: both files exist here, `settings.local.json` carries live
grants, and the write resolver therefore targets `settings.json`. The retired rule simply happens not to
be in our local file, so nothing shows. ⛔ **An absent symptom is not an absent defect** — this epic's
own archetype. Do not let a clean local check close it. ⇒ **owned by `PLAN-TRUTH-103` D2 (STAGED).**

**D-1337-c — a `clear` verdict over an EMPTY population is reported as a checked negative.** *(report
§ 5 — the report observed the vacuity in its own run and that observation is why this is visible; the
GENERALIZATION below is ours.)* ⛔ **The report's framing is TOO NARROW — do not carry it forward.** It
attributes the vacuity to its lane (*"`NO_PLAN` has no findings ledger"*), which reads as a
standalone-lane artifact ordinary plans never hit. **It is not.** `review_commitments.reconcile` computes
`conflicts` as a cross-product over `commitments × deletions` and returns `VERDICT_CLEAR` whenever that
is empty — so **any** plan with an empty `pr-comment` findings set gets `clear` by construction, which is
the ordinary case for a PR no bot filed against. ⭐ **The script is NOT the defect:**
`review_commitments.py:361` publishes `commitments_considered` and `deletions_considered` beside the
verdict, exactly as this epic's population rule demands — **the producer complies and the CONSUMER
discards it.** `finalize-step-simplify.md:203-209` branches on `verdict` alone and its `clear` row reads
*"No deletion touched a committed line"*, asserting a **checked** negative where the fact is an
**unchecked** one. ⭐⭐ **Sharpest: the guard already exists and covers one arrival path of two** — the
same table's third row says *"An UNKNOWN verdict, never a clear pass"* for `status: error`, so the
anti-vacuity concept is present, correct, and half-installed. ⇒ **owned by `PLAN-TRUTH-104` (STAGED).**

**D-1337-d — `deny` and `ask` lists are never pruned.** *(report § 9.3; low.)* Pruning rebuilds `allow`
only. Corroborated that this is reachable **only** from a hand-edited file: `_protect_path_deny_rules`
(`claude_runtime.py:2730`) emits `Read(...)` and `Bash(...)` exclusively — no plan-marshall path emits a
`Write(...)` deny rule. ⇒ **owned by `PLAN-TRUTH-103` D3 (STAGED).**

**D-1337-e — `check_landing_completeness` cannot represent a landing that is complete-as-possible.**
⭐ **NEW — found by this ingestion, present in NEITHER the report NOR the epic before now, and observed
rather than reasoned: it fired on our own forward.** A `kind: landing` message about a run that had no
plan lifecycle (ad-hoc `NO_PLAN`, cross-repo, or foreign-machine) has no `plan_id`,
`deliverables_total`, `deliverables_done`, `total_tokens` or `steps` **to read** — those producers never
existed. The spec sanctions `n/a` but counts it as MISSING for exactly those five, so such a landing
reports `complete: false` **identically to a plan landing whose facts were lost**. ⛔ **Two different
zeros collapsed into one** — the archetype this epic exists to hunt, living inside its own inbox
machinery. Verified first-party: `truthful-signals-031.md` returns `complete: false` with precisely
those five in `missing_keys`, and the message had to explain in PROSE that the incompleteness is
structural, because the payload has no way to say it. ⚠ **UNOWNED.** `PLAN-TRUTH-096`
(orchestrator-inbox-and-landing-residue) is the natural home but is **RUNNING**, so it can neither be
folded into nor addressed by `inbox write --target-plan` (the running-plan guard refuses). Revisit when
`-096` lands: if it does not close this, it needs its own spec.

### ⛔⛔ DO NOT "FIX" `_is_uniform_array` — a load-bearing behaviour that LOOKS like a bug (2026-08-23, from PR #1332 § 2.6; MISSED on first ingestion, recorded on the operator's second-miss challenge)

**This is a landmine warning, not a defect to schedule.** It is recorded because the behaviour reads as an
obvious bug, a plan already came within one commit of "fixing" it, and the blast radius is invisible from
the call site that motivates the change.

**The behaviour.** `ref-toon-format/scripts/toon_parser.py:502` `_is_uniform_array` treats an array as
uniform when all items are dicts, and — its own docstring — *"Uses union of all keys found, allowing
optional fields (missing keys serialize as empty)."* So a RAGGED array (rows with different key sets)
serializes as a tabular block with blanks, not as escaped JSON.

**Why a plan tried to change it.** `list-providers` rendered `url: ""` for a CI provider after the
declaration dropped `default_url` — the union-and-blank rule re-introduced the key at serialization time.
That is *"a provider configured with a blank URL"*, the exact state four separate sites promise never
appears. The in-house self-review's prescribed remedy was to **delete the four promises**; escalating
instead preserved them.

⭐⭐ **What saved it, and the method is the lesson.** The fix agent implemented a serializer-level repair,
measured it, and got a **fully green suite — 21,726 tests — and REFUSED THAT GREEN AS EVIDENCE**, because
it had already watched `list-providers` degrade to escaped-JSON under the same change while tests stayed
green. It instrumented `_is_uniform_array` and re-ran the suite as a **coverage probe**, finding **22
ragged renderings across ~12 key-shapes and 2 call sites** — the change ledger, the Q-Gate findings store,
doctor results, the skill registry, architecture records. All would have become escaped-JSON strings and
**stopped round-tripping**, since `_parse_simple_array` reads only scalar items.
⇒ **A green suite over an unmeasured population is not evidence.** This epic's theme, caught in the act by
a run that then went and measured the population.

✅ **CORROBORATED FIRST-PARTY, and the raggedness is WORSE than the report stated.** Sampling this
repository's own `.plan/work/change-ledger.jsonl` (468 rows) 2026-08-23:

| kind | keys | |
|---|---|---|
| `build` | 12 | exclusive: `args`, `command`, `duration_seconds`, `exit_code`, `log_file`, `outcome`, `status` |
| `job` | 7 | exclusive: `fingerprint`, `job_id` |
| **shared** | **5 of 14** | |

⇒ One live file, two kinds, **sharing barely a third of their keys**. It round-trips today only because of
the union-and-blank rule.

**The correct fix, already applied where it belonged.** `run_list_providers` now emits a per-provider
**mapping** keyed by `canonical_credentials_key`, so an absent key is genuinely absent — the call site
changed, the serializer did not. ⚠ That mapping introduced its own defect (**D-1332-d**, the canonical-key
collision), which is tracked separately and does not argue for reopening this.

⛔ **If a future plan proposes changing `_is_uniform_array`'s union-and-blank rule, it MUST first
instrument the serializer and publish the ragged-rendering population it would break.** A test suite
cannot see this: the 22 renderings pass green either way until something tries to parse them back.


### From the 2026-08-23 ingestion of the `fix-provider-abstraction-mismatch` run report (PR #1332 + #1335, foreign machine)

> ↪ Relocated to `settled.md` § "From the 2026-08-23 ingestion of the `fix-provider-abstraction-mismatch` run report (PR #1332 + #1335, foreign machine)" — PR #1332 + #1335 ingested and fully dispositioned

### From the 2026-08-23 ingestion of the `fix-settings-file-scope-inconsistency` landing (PR #1330, foreign machine)

> ↪ Relocated to `settled.md` § "From the 2026-08-23 ingestion of the `fix-settings-file-scope-inconsistency` landing (PR #1330, foreign machine)" — PR #1330 ingested and fully dispositioned; the residue that is ours has owners

### From the 2026-08-22 `cleanup` pass

- ✅ **D-074-f — RESOLVED 2026-08-22 by operator ruling: git history IS the durable copy.**
  ⭐ **The orchestrator's alarm was PARTLY WRONG and is corrected here rather than quietly dropped.**
  The claim *"`-092` cannot be executed from a fresh clone"* is **REFUTED**: a clone carries full
  history by default, so every deleted artifact is retrievable with

  ```bash
  git show 00ec21c28^:doc/plans/truthful-signals/{NNN}-{slug}/report-01.md
  ```

  — **verified first-party** against `060-invented-plan-scoping-flags-…/report-01.md`, which returns
  its full body. The corpus never left durable storage; it left the **working tree**. Those are
  different claims and only the second is true.

  **Operator ruling:** no action owed — *"if we need the originals we can go back in the git history."*
  ⇒ **`-092` is UNBLOCKED and emittable.** The residual is small and was applied: its Expected Surface
  names working-tree paths that no longer resolve, so the retrieval command above is recorded on the
  spec (A3 — correct the Expected Surface). ⛔ Do NOT re-open this as a durability defect; the record
  below is retained as the audit trail of what was checked, not as an open item.

  **What was verified at HEAD (retained, all still true — only the CONCLUSION drawn from them was
  wrong):**
  - `doc/plans/truthful-signals/` is **absent from git** — `doc/plans/` holds
    `code-intelligence-substrate`, `review-apparatus`, `test-quality`, `multiplattform`, and no
    `truthful-signals`.
  - PR **#1328** (`00ec21c28`) is **194 files changed, 737 insertions, 46,545 deletions**. It DELETED
    the whole corpus (`gaps.md` / `plan.md` / `report-01.md` / `verification.md` × 47 runs) and ADDED
    only two files: `doc/concepts/analyzis-cloud-plan/README.adoc` and `truthfull-signals.adoc`.
  - The corpus now lives at `.plan/local/orchestrator/truthful-signals/cloud-runs/{NNN}-{slug}/`, and
    `git check-ignore -v` resolves that path to **`.gitignore:45: .plan/*`**.

  ⇒ The WORKING-TREE copy is machine-local; the **committed history is not**. `00ec21c28` is a normal
  deletion commit, so every artifact remains reachable at `00ec21c28^` in any clone. The analysis
  (`.adoc`, 737 lines) is additionally live in the working tree.

  ⭐ **The lesson that survives, restated correctly.** *"Deleted from the working tree"* and *"lost"*
  are different claims, and the orchestrator collapsed them. Anchor R1's *"FULLY INGESTED AND GONE"* is
  accurate; the defect was in the READING, not the record. ⚠ The genuine residue is narrower and worth
  keeping: **a spec whose Expected Surface names a deleted path gives no reader a way to know the
  content is one `git show` away.** That is what was fixed.

  ✅ **APPLIED:** `-092` (10 paths) and `-088` (1 path) carry a retrieval note naming the
  `git show 00ec21c28^:{path}` form, so the surface is actionable rather than merely dead-looking.
  Both specs are emittable; neither is local-only on this account.

### From the 2026-08-22 drain of PLAN-TRUTH-074 (9 messages, every one dispositioned)

> ↪ Relocated to `settled.md` § "From the 2026-08-22 drain of PLAN-TRUTH-074 (9 messages, every one dispositioned)" — PLAN-TRUTH-074 shipped as #1134 and all 9 messages were dispositioned

### From the 2026-08-01 drain — concrete defects, folded to an owner or recorded here

> ↪ Relocated to `settled.md` § "From the 2026-08-01 drain — concrete defects, folded to an owner or recorded here" — every defect here was folded to an owner or resolved; the owners carry the live state

### ✅ Resolved / retracted — compacted 2026-08-08, retained as the record

> ↪ Relocated to `settled.md` § "✅ Resolved / retracted — compacted 2026-08-08, retained as the record" — the retraction record itself, retained and reachable rather than dropped

## Watches

### W-2026-09-22-a — `instrumentation-substrate` declined 2 forwarded lessons, both restored to corpus

Inbox message `instrumentation-substrate-001.md`: that epic (formerly `next-level`) checked forwarded
candidate-lessons `2026-09-03-16-004` (security remedy validated against local state only) and
`2026-09-05-08-001` (narrowed catch drops finally-less cleanup) against its 9 staged specs — none covers
domain-skill content rules, only CLAUDE.md-bounded procedural rules. Recommended restoring both as
standing corpus rules. Restored verbatim as `2026-09-22-08-001` / `-002`. No further action owed on
either side — this is the round-trip's clean-decline counterpart, not a defect (unlike the 2026-09-22
`lessons-routing` round-trip Open Defect, which silently re-routed and deleted rather than declining and
recommending restoration).

⚠ Their decline message itself cited the retired `.plan/local/orchestrator/truthful-signals/lessons/
forwarded-to-other-epics/` path (files are actually at the current `.plan/orchestrator/...` path) —
another instance of the pervasive path-drift already recorded under "2026-09-21 — path drift and
unreachable evidence" above.

### W-1560-a — a `ci pr merge-queue` wait-loop hung once, recovered by manual re-enqueue

Surfaced at PLAN-TRUTH-144's landing (PR #1560). The merge got stuck once on a hung wait-loop inside
`ci pr merge-queue`; the operator recovered by re-enqueuing the PR directly and polling manually rather
than relying on the original wait. First-party sighting, n=1. Not staged — watch for recurrence; this
epic already tracks merge-queue robustness generally (e.g. PLAN-TRUTH-063, PLAN-PR-009).

### W-1560-b — 4 unreadable lessons and an `allowed-tools: Grep` declared-but-denied gap need operator judgment

Surfaced at PLAN-TRUTH-144's landing (PR #1560), flagged explicitly by the plan's own retrospective as
needing operator judgment rather than blocking: (1) 4 unreadable lessons in the global corpus traced to
an earlier plan's write pattern; (2) a skill or tool declaring `allowed-tools: Grep` while the runtime
denies it at call time. No concrete remedy proposed in the landing narrative — left here pending an
operator call on scope.

### W-1539-a — Task 19 (D4, mailbox checkpoint plan-id derivation) recorded infeasible on PLAN-TRUTH-143's landing

Surfaced at PLAN-TRUTH-143's landing (PR #1539). `deliverables_done=10/10` reports the run fully
complete, but the task roster was 28 tasks: 27 `done` and 1 `infeasible` — task 19, "Derive the mailbox
checkpoint plan id from `classification.plan_spec`" (0/2 sub-steps), under D4 (the check-points
deliverable). D4's other tasks (8, 9, 21) completed. Deliverable-level completeness hides
task-level abandonment. Unclear without further reading whether this leaves a real gap in the delivered
checkpoint-address surface or was genuinely out of scope — confirm at the next `corpus
enumerate`/`cleanup` pass. See `landings/PLAN-TRUTH-143.md`.

### W-1483-a — plugin-doctor ran SCOPED, so a cross-skill rule class was never gated

Surfaced at PLAN-TRUTH-127's landing (PR #1483). `plugin-doctor` ran scoped to the four changed
directories, so its cross-skill rule class was not evaluated — a counterpart skill outside those four
directories could read green locally and red at whole-tree CI. No spec currently owns broadening this.

### ✅ RETIRED 2026-09-15 — W-1483-b upgraded to PLAN-TRUTH-162, population threshold met

Forwarded via `review-apparatus` (`inbox/review-apparatus-038.md` item 5, from `plan-pr-046`'s landing PR
#1477). `plan-marshall:persona-plan-marshall-agent` keeps inventing a plausible verb instead of reading
the declared one; the existing recurrence checklist has not moved the rate. Sender's own confidence was
medium and self-flagged: the claim that the checklist is ineffective needed the rejection population
behind it before anyone acted. Absorbed as a Watch rather than staged, pending that population.

**Population arrived 2026-09-15 from three independent sources in one day**: PLAN-TRUTH-148's own landing
(17 failures, 10 unique, 8 components), PLAN-TRUTH-157's own landing (6 more, 5 documented signatures),
and the `review-apparatus-041` transfer from PLAN-PR-065 (10 more + a distinct executor-registration
defect) — 23+ failures well past the blocking threshold this Watch named. **Staged as `PLAN-TRUTH-162`**
(D0 derive full population per signature; D1 uniform canonical-invocation hint across `manage-*`; D2
correct inducing skill descriptions).

### W-1479-a — Sonar's `confirmed` zero is an empty-surface zero, not a clean scan (recurring)

Surfaced at PLAN-TRUTH-139's landing (PR #1479, `367874`). `sonar-roundtrip` reported `count_status:
confirmed` with zero new-code issues, but **no Sonar analysis has ever run for this PR** — gate 404, newest
CE task months old, provider not activated. `confirmed` attests only that the CE queue was settled and
empty; it is structurally indistinguishable from a genuinely clean scan and reads confidently green either
way. **Recurs on every plan in this repo until Sonar is wired into PR CI** — do not re-file it per landing;
retire this Watch only when that wiring lands (candidate owner: a successor to `PLAN-TRUTH-150`, or a new
spec, once triaged).

### From the 2026-09-05 (d) consumer-project data-point on `marshall-steward` health

- ⭐⭐⭐ **W-0905d-a — THE REPORTER'S FRAMING WAS TOO NARROW AND THE CORRECTION IS THE FINDING.** They
  diagnosed the plugin-wildcard check as a **consumer-project** problem: the documented path
  (`marketplace/.claude-plugin/marketplace.json`) does not exist in a consumer repo. ⛔ **It exists here,
  and the check is equally blind.** `generate_required_wildcards` reads `marketplace.get('bundles', {})`
  — a dict, **as its own docstring states** (*"from scan-marketplace-inventory JSON output"*) — while
  **both** descriptors, the installed one and this repository's own, carry a `plugins` **array** of 10.
  ⇒ **Universal defect. The missing file in a consumer repo is a second, lesser symptom.**
- ⭐⭐⭐ **W-0905d-b — REPRODUCED HERE IN ONE COMMAND, using the documented invocation and the documented
  path** (`menu-healthcheck.md:48-50`): `added[0]`, `already_present: 0`, `total: 0`,
  **`bundles_analyzed: 0`**, `status: success`.
- ⛔⛔ **W-0905d-c — THE MATCHED PAIR IS WHAT MAKES IT UNARGUABLE.** The reporting consumer has **zero**
  `Skill(...)` wildcards in either settings file; this repository has **17** globally, including
  `Skill(plan-marshall:*)`. **The check emits the IDENTICAL `added: []` / `status: success` over OPPOSITE
  ground truths.** It cannot tell *"every wildcard is present"* from *"none is, and I did not look."*
- ⭐⭐ **W-0905d-d — THE DISCRIMINATOR IS ALREADY PUBLISHED AND NOBODY BRANCHES ON IT.**
  `bundles_analyzed: 0` rides the payload. ⇒ **The shipped shape of this epic's archetype: the SCRIPT
  complies, the CONSUMER discards** — the same pairing recorded at `D-1337-c`. ⛔ **A fix that only adds
  a population field changes nothing here.** Two things are owed: point the caller at the artifact whose
  shape the function declares (or teach the function the descriptor), **and make `bundles_analyzed: 0`
  unreachable with `status: success`.**
- ⚠ **W-0905d-e — AUTO-MODE MASKS THE COST, AND TURNING IT OFF IS WHEN THE BILL ARRIVES.** With
  permissions auto-approved a missing `Skill(...)` wildcard is invisible. **A consumer who runs the
  health check, reads `success`, and then disables auto-mode gets a prompt storm the check certified
  against.**
- ⇒ **Folded to `PLAN-TRUTH-103`** with its Expected Surface widened by 3 entries, and a recorded scope
  note: **D0's population becomes *false premises the permission machinery holds*, not *`Write`-modelling
  sites*.** This member is an input-SHAPE premise, and a sweep scoped to the narrower phrase would not
  have found it.


### From the 2026-09-05 TokenSheriff data-point (2 items, both dispositioned)

- ⭐⭐⭐ **W-0905-a — W-0904-c's HYPOTHESIS IS NOW OBSERVED, AND THE POPULATION IS 2, NOT 1.**
  Yesterday this orchestrator wrote *"at least one consumer repo is in exactly that state — NOT
  corroborated here."* TokenSheriff reported itself. ⛔ **Rather than take the instance, the population
  was DERIVED**: 30 repos walked under `~/git/`, **9 carry a `.plan/marshal.json`, 0 unreadable, and
  TWO carry the retired `pr-agent` token** — TokenSheriff **and `nifi-extensions`, which the report did
  not name.** Clean: `API-Sheriff`, `cui-http`, `cui-jsf-test-basic`, `cui-llm-rules`,
  `cui-open-rewrite`, `cuioss-parent-pom`, `plan-marshall`.
- ⛔⛔ **W-0905-b — THE TWO ARE NOT THE SAME SEVERITY, AND A SWEEP THAT TREATS THEM ALIKE IS WRONG
  BOTH WAYS.** `TokenSheriff/.plan/marshal.json:107` carries `pr-agent` in **`required_bots`** ⇒
  **MERGE-BLOCKED**; `nifi-extensions/.plan/marshal.json:106` carries it in **`optional_bots`** ⇒
  **NOT blocked**, merely dead config that renders `unregistered_kind`. Mechanism verified first-party:
  `review_completeness.py:1130-1131` collects every `_UNPROVEN_STATES` member into `unproven_bots`,
  `:1139` narrows to `required_unproven`, and `:1147`/`:1149` compute `participation_complete` from the
  **required** set alone. ⇒ **The operator's *"every plan fails its review quorum on a spelling"* is
  exactly right for TokenSheriff and does NOT transfer to `nifi-extensions`.**
- ⭐ **W-0905-c — `PLAN-PR-044` SHIPPED A DETECTOR AND THE DETECTOR IS WORKING.** TokenSheriff is not
  evidence against the fix; **it is the fix firing.** What has no owner is the **migration** half — a
  correct fail-closed barrier now blocks a repo whose only fault is that nobody edited its config.
  ⇒ Corroboration forwarded as **`truthful-signals-047.md`**.
- ⛔ **W-0905-d — THE REMEDY IS OPERATOR-OR-PLAN WORK, NOT OURS, AND IT WAS NOT APPLIED.** Both files
  are **foreign repository source**; editing them is outside the orchestrate-never-implement boundary,
  so the finding is reported and NOT applied. ⚠ **HYPOTHESIS, uncorroborated:** these 9 are the whole
  fleet. The walk covered `~/git/*` on ONE machine at depth 1 — a consumer checked out elsewhere,
  nested deeper, or on another machine is **outside this population, and its absence is silence, not a
  clean reading.**

### From the 2026-09-04 foreign-machine data-point (3 items, all dispositioned)

- ➡ **W-0904-a — `truthful-signals-046.md` FILED to `review-apparatus` (transfer, not an offer).**
  Two of the three items were theirs by the PR/review routing test and are now **in their inbox**,
  not merely named at: the `cuioss-review-bot` gap (`2026-09-04-12-001`) and the Sourcery
  refusal-misclassification (`2026-09-04-12-002`). ⛔ **A ledger cannot see a duplicate in another
  ledger**, which is the whole reason this went through `inbox write` rather than into our own queue.
- ⭐⭐ **W-0904-b — `PLAN-PR-044`'s D0 IS ANSWERED, and the answer arrived AFTER its landing.** Their
  D0 asked for the proximate cause before fixing anything and named the alternative it had not settled
  (*"this repository's registry DOES map `cuioss-review-bot` → `pr-agent`, so the operator's stated
  pair should NOT mismatch here"*). **The operator's data-point settles it: a rename shipped OUT OF
  ORDER, not a bad map.** Corroborated first-party — `cc5ea40a1` / **#1392** renamed
  `automatic-review/standards/pr-agent.md` → `cuioss-review-bot.md` and updated this checkout's
  `.plan/marshal.json` in the same commit (34 files, +1616/−308). ⚠ **A landed plan can still receive
  the answer to its own gate question** — this is the second time a post-landing data-point has settled
  something a shipped spec left open, and it is an argument for the post-merge revisit, not against it.
- ⛔⛔ **W-0904-c — THE FIX MADE A STALE TOKEN DETECTABLE; IT MIGRATED NOBODY, AND THE BLOCK IS
  FAIL-CLOSED.** Corroborated first-party at `review_completeness.py:310-313` / `:323-335`:
  `unregistered_kind` is a member of `_UNPROVEN_STATES`, and its own comment says so verbatim —
  *"Blocking exactly as `absent` is … so the barrier still fails closed."* ⇒ **a consumer repository
  whose `marshal.json` still carries `bot_kind: pr-agent` is now MERGE-BLOCKED, not warned.**
  ⭐ Renaming a `bot_kind` invalidates every consumer config fleet-wide and **no propagation mechanism
  exists** — the operator's own framing: *"the migration ordering has no enforcing mechanism."*
  ⚠ **HYPOTHESIS, NOT corroborated here (foreign-repo evidence):** at least one consumer is in that
  state today. Confirm/refute against each consumer's `required_bots` / `optional_bots` and its live
  barrier output. ⭐ **The generalized half is already OURS and staged as `PLAN-TRUTH-132`** — do not
  re-stage the frozen-param mechanism; the reviewer-config propagation side is `review-apparatus`'s.
- ⭐ **W-0904-d — `PLAN-TRUTH-132` claim 4 STAMPED `corroborated` at `c3a1aacbc`.** Its fifth claim was
  the one this orchestrator had explicitly recorded as **not corroborated** (*"the sender's evidence is
  foreign-repo … if no such rename exists here, the instance is dropped"*). **The rename does exist
  here**, so the instance stands. ⇒ **A `HYPOTHESIS` written honestly as unverifiable got settled by a
  later, unrelated paste** — the verify-first labelling is what made that settlement a one-call
  `corpus set-verdict` instead of a re-investigation.

### From the 2026-08-26 foreign-machine report ingestion

- ⚠ **W-114-a — "sonar-roundtrip false negative", claimed but UNCORROBORATED.** The foreign-machine
  report listed this as one of three defects, alongside two that were fully corroborated first-party
  (D-114-a and D-114-e). This one carries **no mechanism, no file, and no symbol** — only the label.
  ⛔ **It is recorded as an unverified LEAD, per the analyze contract's "a pasted claim is a lead, never
  a fact" rule, and NOTHING was staged on it.** ⭐ **Do not upgrade this to a finding on the strength of
  the other two being right** — that is the confident-signal-hides-a-caveat shape this epic is named
  for, applied to a source's credibility instead of to a signal. **Next action:** ask the operator for
  the report's own detail on it, or reproduce a Sonar fetch→triage→post roundtrip and observe the
  claimed false negative. Until then it is neither open nor closed — it is unread.

### From the 2026-08-25 PLAN-TRUTH-094 drain (PR #1343)

- ⚠ **W-094-a — the shipped `population_size` / `blind_spots` figures differ from the spec's by ~18×,
  and nothing in either artifact says whether they measure the same population.** `-094`'s spec D3
  states the clean gate publishes population `152` and `blind_spots` `69`; the landing measures
  **`2792` and `304`** on the real corpus at the merged HEAD. ⭐ **This is very likely the verify-first
  contract WORKING** — the spec labelled every claim `HYPOTHESIS` and required D0 to re-derive before
  fixing, so a moved number is the expected outcome. ⛔ **But "likely" is the whole problem**: a
  ~18× move is equally consistent with a re-derivation and with a silently different denominator
  (rules vs invocation sites), and **neither the spec nor the landing states which**. Do NOT close this
  by assuming the benign reading. Settles against `_analyze_argument_naming.py` at `1169fb5bf`: read
  what the counter iterates over, and compare it to what the `152` figure iterated over.

- ⚠ **W-094-b — a plan filed the SAME subject into two epics' inboxes as two different kinds.**
  `-094` wrote `5bdbb9` and `a02741` to `review-apparatus` as `kind: finding`, AND wrote the same two
  subjects to `truthful-signals` as `kind: candidate-lesson` (`-004`, `-007`). Both drains would
  disposition them independently, and neither can see the other's. ⭐ This drain caught it only because
  it read the sibling's inbox before forwarding — which is not a step any contract requires. ⇒ Watch
  whether this recurs; if it does, the emitting site needs a cross-epic dedup, not the drains.

### From the 2026-08-25 `cleanup` pass

- ✅ **W-CU-d — THE PIN GAP IS CLOSED. `executor == installPath` PASSES, verified independently.**
  Operator ran the repair 2026-08-25 11:09 CEST (backup `installed_plugins.json.bak-20260825T110945`,
  14 entries `0.1.1538 → 0.1.1544`, 0 markers to clear). ⭐ **Verified by double-sampling rather than
  by the script's own `post-verify: ALL ALIGNED`** — a repair asserting its own success is the witness
  class this epic distrusts. Both samples agree: registry `version` AND `installPath` = `0.1.1544`,
  executor pin = `0.1.1544`. This supersedes W-096-a and W-088-a, which tracked the gap at 1541 and
  1542. ⚠ **The per-landing leak is NOT fixed** — `sync-plugin-cache` still mints a version without
  re-pinning, so the gap re-opens on the next landing. What closed is this instance.

- ⛔ **W-CU-e — `0.1.1240` SURVIVES THE REPAIR AND IS STILL LOADABLE.** Unmarked set after the fix is
  `{1240, 1538, 1543, 1544}`. The repair aligns the registry and clears markers on dirs the registry
  will reference; **it does not retire anything.** So the directory that leaked the pre-#1162
  `marshall-orchestrator` skill names into this session, served the 6-value enum against a live 12
  (inbox `-001`), and produced `-088`'s block-less duplicate landing `-015` is **still unmarked and
  still reachable.** ⭐ Re-pinning made it not-the-pin; it did not make it not-loadable. ⇒ The residual
  hazard is unchanged and needs its own remedy — D-088-b stands.

- ⭐⭐ **W-CU-a — MY OWN A3 AMBIGUITY SCAN COMMITTED THE DEFECT CLASS IT WAS AUDITING FOR. Third
  instance in two days.** The scan flagged `-108` and `-111` as *missing an Objective*. Both have one:
  `-111`'s sits under `## Provenance`, `-108`'s under `## What is genuinely missing`. My detector keyed
  on the heading vocabulary `Objective|Goal|Problem` and reported every other spelling as ABSENT —
  which is **exactly** `D-096-d`'s claim parser (one bullet shape recognised, tables and prose read as
  zero claims) and exactly inbox `-003`'s declared-files scraper (one prose shape recognised, tables
  and lists contribute nothing). ⛔ **Three components, three authors, one failure mode, and the third
  was written by the orchestrator auditing for the first two.** ⇒ Both specs are `declined`, not
  flagged: the finding was the detector's, not theirs. ⭐ The general rule this epic should adopt:
  **a structural detector must report the shapes it did not recognise, not silently score them absent** —
  a scan that cannot enumerate its own misses is indistinguishable from a clean one.

- ✅ **W-CU-b — RAISED AND THEN REFUTED WITHIN THE SAME PASS. `compact` IS idempotent; my first
  reading was wrong.** I observed `regenerated_count` **2 → 1 → 0 → 0** on what I believed was an
  unchanged ledger and recorded it as off-contract. ⛔ **It was not: the input HAD changed.** The
  reproduction I proposed — *"a compact immediately after a `resume_anchor` write"* — I then ran, and
  it reproduced exactly: anchor write → `regenerated_count: 1` (the START-HERE block correctly picking
  up the new anchor) → `0` → `0`. **The `1` is the block doing its job, not drifting.** Idempotence
  means *no change given no input change*, and I had written the anchor between the calls I was
  comparing. ⭐ **Kept in the ledger deliberately, as the record of a false defect I raised and killed
  in one pass** — the cost of the wrong version escaping is a future reader hunting a phantom
  non-determinism in the one component this epic relies on to keep `epic.md` truthful.

- ⛔ **W-CU-c — DRAIN OWED, and `cleanup` structurally cannot consume it.** `PLAN-TRUTH-094` landed as
  **#1343** *during* this pass and emitted **8 messages** (1 finding, 6 candidate-lessons, 1 landing)
  between 07:26 and 07:45Z. Phase C refuses to drain by permanent documented default, and its refusal
  is about consumed messages — these are FRESH. ⇒ This needs `analyze`, a different verb. ⭐ Note
  `-008` carries **`revision: 1`** — the landing was corrected through `inbox amend`. **After
  `D-096-c` and `D-088-a` recorded two consecutive landings bypassing the lifecycle verbs, this one
  reached for the sanctioned path.** Record the improvement, not only the failures.

### From the 2026-08-24 PLAN-TRUTH-088 drain

- ⛔ **W-088-a — the pin gap WIDENED again, exactly as predicted, and the repair is still unrun.**
  Double-sampled: registry pins **`0.1.1538`** on every entry; executor now **`0.1.1542`** (was 1541
  at the `-096` drain). `sync-plugin-cache` ran again in this landing and minted another version
  without re-pinning ⇒ **one version per landing, confirmed across two consecutive landings.** The
  operator repair remains outstanding; `TARGET` must be re-pointed to `0.1.1542` before it is run.

- ✅ **W-088-b — CLEARED 2026-08-26. The retained worktree is gone; the underlying defect now has an
  owner.** Removed after first-party safety checks: PR **#1342 `state: merged`** via the CI
  abstraction, squash commit **`91bbe7470`** on main, plan dir archived at
  `.plan/local/archived-plans/2026-08-24-metrics-ledger-…`. ⛔ **The 19 branch commits "not in main"
  are pre-squash history, NOT lost work** — `--is-ancestor` returning false is the expected shape of a
  squash merge and must not be read as an unmerged branch. Hand path per this entry's own prescription
  (`rm -rf`, `git worktree prune`, `git branch -D`). ⭐ **Doing it produced D-114-g**: the verb REFUSES
  on an archived plan, so the hand path was the only path. The 60 s budget and the scratch growth are
  now **`-114` D5/D6**; the unreachability is **D-114-g**. Original entry follows.
- ⚠ **W-088-b (original) — the worktree was RETAINED and `branch-cleanup` was right to stop.**
  `git worktree remove` timed out twice on its fixed 60 s budget: `.plan/temp/pytest-basetemp` is
  large enough that listing it alone is 11.3 MB, much of it nested git repos from fixtures. Deleting
  the scratch was declined and `git clean -ffdx` is improvisation the step forbids. ⭐ **A step that
  refuses to improvise past its own budget is the behaviour we want** — record it as correct, not as
  a failure. Verified present at `dd55c6f8e` holding
  `feature/metrics-ledger-readers-and-timestamp-provenance`. Operator cleanup: remove that path by
  hand, `git worktree prune`, then delete the branch. ⚠ **The 60 s budget is FIXED and the scratch
  grows with the test suite — this will recur and get worse.**

- ⭐⭐ **W-088-c — the self-review loop's cost is DEFENSIBLE ON YIELD, and this qualifies R22.**
  ~1.4M tokens across 7 rounds, **9 real defects, ZERO false positives**. R22's claim is about the
  *re-fire amplification*, not about self-review's yield; both hold. ⛔ **`-097` DB must not cite this
  landing as licence to collapse the settle band** — the measurement says the opposite about this
  step specifically.

- ⚠ **W-088-d — `registry_parity` has NO LIVE OWNER.** `cleanup restart-check` names
  `PLAN-TRUTH-059` as the owner of that signal and excludes it from the verdict floor. **`-059`
  SHIPPED as #1213.** So the one signal that would observe D-088-b is permanently `not_available`
  and attributed to a closed plan. Recorded rather than staged; it needs an owner.


### From the 2026-08-24 PLAN-TRUTH-096 drain

- ⚠ **W-096-a — the registry pin gate FAILS, and this landing is why.** Double-sampled first-party,
  both samples agreeing: registry `installPath`/`version` = **`0.1.1538`** (every entry), executor pin
  = **`0.1.1541`** (160 references). ⭐ **This landing's own `sync-plugin-cache` minted `1541` and
  re-pinned nothing** — the per-landing steady-state leak, not a corruption. The landing message says
  so itself. Repair is **operator-only**; the script's `TARGET` is already re-pointed to `0.1.1541`.
  ⛔ Graded against the work still ahead rather than the version delta: the scripts resolve
  numerically-newest (`1541`, which CONTAINS this landing's fixes), so the drain's own
  `landing-check` and `corpus verdicts` ran on post-fix code. No halt was warranted.

- ⛔ **W-096-b — "gh is not authenticated here" is CONTRADICTED first-party. Do not run `gh auth
  login` on this evidence.** The runner reported `ci pr view` failing for auth. In this session, from
  the main checkout, **both `ci pr view --pr-number 1338` and `ci pr comments --pr-number 1338`
  succeed against the live API**. Same machine, same user, same credential store ⇒ the failure was
  scoped to the runner's context (most likely a cwd whose worktree `branch-cleanup` had already
  removed), not a logged-out `gh`. ⭐ **The report diagnosed a cause its evidence did not support** —
  the epic's own archetype, in the hand-off itself.

- ⚠ **W-096-c — `metrics-ledger-readers-and-timestamp-provenance` (`-088`) went BACKWARDS.** It read
  `6-finalize` at the start of this session and reads **`5-execute`** now, with its worktree at a
  **detached HEAD**. That is a loop-back re-entry, which is legitimate — but it is the exact
  population `-097` DB/DE is scoped to, and per `PLAN-TRUTH-055` a re-entered phase's per-phase
  metrics are not representable. Watch, do not intervene: the plan is running and owns its own lane.

- ⚠ **W-096-d — `-097` absorbed three more items while already over the split guard.** `-006`, `-007`
  and `-008` folded in as EVIDENCE for existing deliverables (F2 ×2, DB ×1) and added no new
  deliverable, deliberately. ⭐ W-075-c stands and is now worse in weight if not in count: **before
  `-097` is emitted, split it.** Its prose-only `Claim Labels` section also puts it in D-096-d's
  19-spec set, so its prep-ready verdict is not currently trustworthy either.

### ⛔⛔ From the 2026-08-24 findings-visibility investigation — a RETRACTION by this orchestrator

- ⛔⛔ **W-VIS-a — I REPORTED A FALSE MEASUREMENT AND STAGED A PLAN ON IT. The operator caught it.**
  I claimed `PLAN-TRUTH-095` *"archived with 29 findings pending — filed, never resolved, archived
  anyway"* and staged an archive gate in `PLAN-TRUTH-110`. **All 29 were `assessments`**, whose schema
  carries **no `resolution` field** — a `phase-3-outline` scope judgement, not a defect. My sweep
  defaulted the missing field to `pending`. ⇒ **`-095` archived with ZERO unresolved defects; the
  invariant works.** The same error inflated the live count **26 → 7**. ✅ `-110` rewritten, its gate
  deleted, R90 corrected in place, R93 records it.
  ⭐⭐ **The generalisable rule, and it is one this epic already enforces on others:** *a count over a
  population whose record types were never inspected is not a measurement.* I had the type breakdown
  one command away and reported the total. ⛔ **Before any finding count: break it down by type and
  state, per type, whether an absent `resolution` means unresolved or means the field does not apply.**
  ⚠ Recorded here rather than only in the spec, because the failure was the ORCHESTRATOR's method, not
  the plan's.

- ⚠ **W-VIS-b — the orchestrator's live-plan findings sweep is a WORKAROUND with an expiry.** It reads
  `.plan/local/worktrees/*/…/artifacts/findings/*.jsonl` directly, bypassing the script funnel, because
  `manage-findings list` returns `total_count: 0` against an absent plan directory. ⛔ **`PLAN-TRUTH-109`
  is what retires it — do not let it harden into the way findings are read.** ⚠ And per W-VIS-a, **the
  sweep MUST separate types before reporting any count**; its first run did not, and that is what
  produced the retraction.

### From the 2026-08-24 inbox drain of PLAN-TRUTH-095

- ⚠ **W-095-a — the build oracle's FOUR clean health zeros against 112 builds. Recurrence of W-075-b,
  n=2 and much larger.** *(inbox `-003`)* `analyze-logs` emits `build_time: {total_build_seconds: 0.0,
  build_count: 0, suspect_count: 0, pass: 0, error: 0, timeout: 0, killed: 0}` — **four of those are
  health signals and all four read clean** — while the **same fragment from the same script on the same
  plan** reports `pyproject_build, 112, 28174490.0, …, 88.649` — **112 invocations, 7h49m, 88.6% of all
  script time**, slowest call 1,405,600 ms, and 47 build-result logs on disk, several over 5 MB. ⛔ *"A
  reader who takes `timeout: 0, killed: 0` as evidence of build health is reading a population the
  ledger never observed."* ⭐ **Sharper than `-075`'s instance** (52 builds), which reported only
  `build_count`/`total_build_seconds`; this one shows **four independent health signals all reading
  clean from an unobserved population**. ⇒ Folded to **`-088` DA (RUNNING)** — carry to its landing
  revisit; the reporting half (`analyze-logs` holds both numbers and should say they disagree) is still
  not in DA's scope.

- ⭐ **W-095-b — external review contributed NOTHING measurable, and the plan said so plainly.**
  `automatic-review`: **0 comments — 1 empty, 1 refused, 1 refused-structural**; `review-retrospective`:
  *"3 reviewers compared, 0 actionable comments"*. ⇒ On a 9-deliverable, 179,695-character PR, **every
  in-house defect came from `pre-submission-self-review` (8 firings, 20 findings, 115 candidates) and
  none from a bot.** ⚠ Forwarded to `review-apparatus` as `truthful-signals-034.md` **before** this
  drain, carrying the diff-size arithmetic as a lead; **this landing corroborates those figures
  first-party.** Re-check when that epic drains it.

### From the 2026-08-24 VERIFICATION of PLAN-TRUTH-075's operator report against ground truth

The operator pasted the plan's final report after the drain. Checking it against the archived
`status.json` and the live machine produced three things **no inbox message contained**, and one
correction to this orchestrator's own work.

- ⛔⛔ **W-075-d — `sync-plugin-cache` reported `[OK]` while WIDENING the executor/registry split.**
  The report's step line reads *"sync-plugin-cache — 11 bundles; executor regenerated"*, and it is
  truthful about what it did. **Double-sampled first-party afterwards:** registry `installPath` and
  `version` = **`0.1.1526`**; executor `MARSHALL_VERSION` = **`0.1.1538`**; the freshly-created
  `0.1.1538` cache dir **already carries `.orphaned_at`**. ⇒ The gap this session opened with was 1526
  vs 1527; **it is now 1526 vs 1538**, and `executor != installPath` still fails. ⭐ **The step whose
  entire job is cache/executor coherence completed successfully and left them incoherent, and nothing
  in the finalize band checks the invariant afterwards.** ⚠ `0.1.1240` now carries **BOTH** `.in_use`
  and `.orphaned_at` — a contradictory pair, and 1240 is the version the memory record's incident 17
  says a manifest regression pointed at. ⚠ `dist-manifest.json` is **ABSENT** from
  `~/.claude/plugins/`, so the fifth-consumer assertion that record calls for cannot be evaluated here.
  ⛔ Repair remains operator-only. ⭐ This supersedes R52's figures, which are now stale.

- ⭐⭐ **W-075-e — SIX steps re-fired, not four, and only ONE re-fire is disclosed in the whole
  report.** Archived `status.json` `phase_steps["6-finalize"]`: `pre-push-quality-gate` 3 firings;
  `pre-submission-self-review`, `finalize-step-simplify`, `create-pr`, `ci-verify`, `automatic-review`
  2 each. **29 firings across 22 recorded steps, presented as "23/23 done".** Only
  `pre-push-quality-gate` says *"re-fired at f41d4cdaf"*; the other five re-fires are invisible.
  ⛔ **`pre-submission-self-review`'s `prior_firings[0].outcome` is `failed`**, and the report renders
  that step `[OK] … clean on full surface`. **A step that failed and then passed reads as clean.** ⇒
  Folded into `-097` as **F6**, with F4 corrected. ⚠ The report's 23 vs the store's 22 is `archive-plan`,
  which archives the file it would write itself into — benign in cause, but it means the headline
  **cannot be reconciled against the state store at all**.

- ⚠ **W-075-f — `finalize-step-simplify` reported `reconcile clear` and the report gives no way to tell
  whether that `clear` was CHECKED or VACUOUS.** Its `display_detail` reads *"0 edits, 3 candidates
  declined with reasons, **reconcile clear**"*, with no population beside it. This plan **did** have
  `pr-comment` findings (`automatic-review — 3 comments: 1 fixed, 1 accepted, 1 noted`), so the verdict
  here was probably genuine — **but "probably" is the finding.** ⇒ Live confirmation that `D-1337-c`
  bites at the REPORT surface too, not only in the branch table: `-104` must make the checked and
  vacuous cases distinguishable **in what the step renders**, not merely in what the seam returns.

### From the 2026-08-24 inbox drain of PLAN-TRUTH-075 (PR #1336)

- ⭐⭐ **W-075-a — A RULE OF THUMB WAS THE SOLE LINE OF DEFENCE AGAINST A FALSE GREEN, AND IT HELD.**
  `build_server wait --plan-id` re-attach returned `job_status: success`, `exit_code: 0`,
  `duration_seconds: 79` for a **different build** (the named `log_file` held `./pw verify
  pm-plugin-development` from an earlier run, not the coverage build being awaited). The return carries
  no `command`, no `job_id`, and no submitted-vs-resolved discriminator, so **a stale re-attach is
  indistinguishable from the caller's own job completing green.** ⭐ **It was caught ONLY because 79s
  was implausible for a build already observed running past 600s** — i.e. by the standing rule *never
  trust a routed build's outer status; an implausible duration is a failure signal.* ⇒ The rule earns
  its place and should be restated wherever routed builds are awaited. ⛔ **But a heuristic is not a
  control**: the machine discriminator is owned by **`PLAN-TRUTH-105` D1 (STAGED)**, and until it ships
  this failure remains detectable only by a reader who happens to find the duration odd.

- ⚠ **W-075-b — `-005`'s hypothesis is ALREADY REFUTED; do not let it re-enter as a new lead.** The
  message reports `build_time: {total_build_seconds: 0.0, build_count: 0}` against its own
  `script_cost_rollup` showing **52 `pyproject_build` invocations, 9,173,400 ms, 57% of all script
  time**, and hypothesises a worktree-anchored ledger that never merges back. ⭐ **The plan was right to
  mark it NOT ESTABLISHED** — and R5 already refuted exactly that hypothesis first-party: the walk-up
  (`_find_plan_root_from_cwd`) anchors a `.plan/local/worktrees/{id}` worktree on the **MAIN checkout**,
  and the main ledger holds 468 rows / 433 `kind=build`. **The ledger is not destroyed and the write IS
  reached**; what fails is what the row CARRIES (424/433 `plan_id` null or `NO_PLAN`). ⇒ Folded into
  **`-088` DA (RUNNING)**, whose re-scoped remedy already targets the real cause. ⭐ **The genuinely new
  half is the REPORTING defect and it stands on its own**: `build_count: 0` beside a non-empty
  `pyproject_build` rollup **in the same fragment** is an internally contradictory report, and
  `analyze-logs` has **both numbers in hand**. It should say so rather than emitting a bare unavailable.
  ⚠ Carry that to `-088`'s landing revisit — it is not in DA's current scope.

- ⚠ **W-075-c — the split guard is now DEMONSTRABLY breached on `-097`, and the drain made it worse.**
  `-097` carried 14 deliverables (guard: 12) and two finding sections before this drain; it now carries
  **five** finding sections (F2 amended, F3/F4/F5 added, DD amended). Every addition is EVIDENCE rather
  than a new deliverable, which is why the count did not rise — **but that is exactly how an oversized
  plan hides its growth.** ⛔ A split-guard notice was written into the spec itself instructing outline
  to **presume a split is required** rather than absorb. ⚠ Watch whether outline honours it; if `-097`
  reaches execution unsplit, that is a guard that reported and was ignored.

### From the 2026-08-23 ingestion of PR #1337 (foreign machine)

- ⚠ **W-1337-a — "the CI abstraction CAUGHT it" is not first-party supported; the abstraction RELAYS,
  it does not GUARD.** The report's § 8 process note says `ci pr safe-merge` **refused** with
  `merge_queue rule active on branch` and that *"the abstraction caught it and named both remedies"* —
  and the underlying behaviour is real and valuable: an immediate merge would have closed the PR
  UNMERGED, and routing through `ci pr merge-queue` succeeded. ⛔ **But the claim about the MECHANISM
  does not corroborate.** First-party: the string `merge_queue rule active on branch` appears **nowhere**
  in `tools-integration-ci/scripts/`, and no remedy-naming logic was found there — `ci_base.py` declares
  the `safe-merge` verb (`:1030-1034`) and nothing more. ⇒ The refusal is almost certainly **GitHub's own
  API error surfaced verbatim**, which means our layer faithfully relays a provider refusal rather than
  guarding against the condition. ⚠ **Why the distinction is load-bearing:** a provider that returned a
  soft success instead of an error would NOT be caught — which is exactly the `#1081` failure this epic
  already tracks (`ci pr merge` returned `merged: true` and deleted the branch WITHOUT merging). Do not
  let "the abstraction caught it" harden into a belief that a guard exists. ⭐ The corroborated part
  stands and strengthens the per-verb honesty mapping: `merge-queue` reports honestly, `safe-merge`
  refuses honestly, `merge` lied once. ⚠ Routing note: the discriminator lists *merge-queue behaviour*
  under `review-apparatus` and *merge/landing truthfulness* here; this is kept HERE per the
  ambiguity-defaults-here rule, and the ambiguity is recorded rather than resolved.

- ⚠ **W-1337-b — their residual § 9.4 (`marshal_status: stale`) is THEIR machine and does NOT transfer,
  but the comparison is worth keeping.** They report `.plan/marshal.json` at `0.1.1527` against
  installed `0.1.1537`. Ours is a **different** landscape: registry `installPath` = `0.1.1526` (the
  version this session's skill bodies were seated from), executor pinned `0.1.1527`, and the `0.1.1527`
  cache dir carries `.orphaned_at` — the live pin split of R42, re-confirmed double-sampled this session
  and unchanged by the restart. ⇒ **Their remedy (`/marshall-steward upgrade`) is not ours**; ours is
  operator-only repair. Recorded so a reader does not import their version numbers as this machine's.

- ⚠ **W-1337-c — their residual § 9.5 (repo-wide plugin-doctor backlog) is a RECURRENCE, not a new
  item.** They report hundreds of `bash_chain_shapes_in_skills` and `resolver-matrix-coverage` findings
  on a whole-tree run, with **0** component issues in the skills #1337 touched. ⇒ Folds onto
  `PLAN-TRUTH-094` (plugin-doctor-detector-coverage-residue), currently **RUNNING**. ⛔ No new spec, and
  no `inbox write --target-plan` — the running-plan guard refuses delivery to a live plan, which is
  correct pre-`-100` behaviour. Recorded here so the recurrence is not lost while `-094` is in flight.

### From the 2026-08-23 ingestion of PR #1330 (foreign machine)

- ⚠ **W-1330-a — TWO QUESTIONS THAT RUN DID NOT SETTLE, flagged rather than answered. Do not record
  either as established.**
  **(1)** Whether Claude Code **executes** two byte-identical hook entries across settings layers or
  collapses them. The sources consulted disagree. The harm is bounded either way — the render hook is
  idempotent, so the cost is duplicated invocations of a script the codebase itself calls *"among the
  largest recurring script costs"* (`claude_runtime.py:966-969`), not a correctness break. ⭐ **D-1330-c's
  remedy is deliberately chosen to be the one that does not depend on this answer.**
  **(2)** Whether `lessons-capture` carrying `lane: off` in `step_params` while remaining in
  `phase_6.steps` is correct. It most likely is (`class: core` steps are immune to a weakening `off`),
  **but the immunity predicate was NOT verified.** ⚠ This bears on **D-074-a**, whose cause is recorded
  as half-settled precisely because live `marshal.json` has `lane: off` — settle the immunity predicate
  and D-074-a's ambiguity may resolve with it.

- ⚠ **W-1330-b — A CONFIDENTLY-WRONG ROOT CAUSE WAS GIVEN TO THE OPERATOR AND REJECTED. Our own theme,
  observed in the wild.** The first diagnosis of the blocked `test-compile` gate blamed a local Python
  3.14 interpreter and asserted *"nothing in the repo is broken"*. The operator rejected it and demanded
  the divergence be analysed properly; three isolation runs against unmodified `main` then established
  the real cause (MYPYPATH-dependent module resolution — see D-1330-i). ⭐ **Keep this as the archetype
  instance it is: the wrong answer was not tentative, it was confident, and only an operator refusing it
  produced the right one.** The repository had ALREADY solved the real problem at a sibling call site —
  so the correct answer was reachable by reading the codebase, not by reasoning about interpreters.

- ⚠ **W-1330-c — A `cd … && …` COMPOUND UN-PINNED THE SHELL FROM THE PLAN WORKTREE MID-RUN**, sending
  three subsequent script calls against the main checkout; one decision-log write went nowhere and was
  re-issued after re-pinning. No state was corrupted. ⭐ Recorded because the failure is silent — a
  script that resolves its store by cwd walk-up (`_find_plan_root_from_cwd`) writes to a DIFFERENT store
  rather than erroring. Same resolver family as the D-1330 ledger analysis in PLAN-TRUTH-088 DA.

- ⭐⭐ **W-1330-d — NINE OF THE TEN LESSONS ARE ONE DEFECT CLASS, AND IT IS THIS EPIC'S THEME, INDEPENDENTLY
  DERIVED ON ANOTHER MACHINE.** The source report's own § 8 states it: *a measurement or signal that
  reports a confident value over a population it did not actually cover.* L1 `tests_run: 0` for 17,888
  tests · L4 a 214-file footprint for a 20-file plan · L5 164,084 tokens billed to a phase that did no
  work · L6 three "Completed" lines for one success and two failures · L7 zero artifacts for three
  file-producing tasks · L8 `0.0` build seconds for 23 minutes of builds · L9 a measured-looking `0` for
  ten never-instrumented steps · L10 recurrence 18 for one re-observed judgement.
  ⭐ **Its diagnosis is sharper than "the pattern is unknown" and worth adopting verbatim:** the
  repository already has the correct pattern in at least three places — the `unmeasured` sentinel, the
  `partial`/`exact` coverage discriminator, and the withheld verdict (`majority_discarded`,
  `structural_share: null`). **The recurring failure is that each new measurement surface is built
  without checking what its sibling does when it cannot measure.**
  ⇒ **This is a corroboration of the epic's premise from an independent run, not a new epic.** The
  report proposes "a follow-up epic"; we already are it, and the measurement half is
  `code-intelligence-substrate`'s by our own discriminator. **No epic is spawned on this observation.**


- ⚠ **W-074-a — FINALIZE COST CONCENTRATION, AND NOTHING IN THE RUN COULD SEE IT HAPPENING
  (2026-08-22, PLAN-TRUTH-074).** That plan spent **61.7%** of its tokens in finalize against
  **16.8%** in the phase that did the work, landing at **3.6× its `single_module + feature` error
  anchor** (all four fallback ratios also tripped). Script wall time: builds **62.4%** + CI 16.8% +
  CI-polling 13.1% = **92.3%**, from **144 build invocations for a 16-file change**.
  ⭐ **This was not waste in the failure sense** — 20 finalize dispatches, all `step_complete`, zero
  error, zero retryable. It was the cost of the work as configured, and both operator gates declared
  their cost before being answered toward the more expensive branch.
  ⛔ **The watchable defect is the missing feedback loop, not the spend.**
  `status.metadata.execution_profile_cost_preview` was never recorded, so
  `check-routing-decisions` returns `comparison: not_attempted` — the aspect implements the
  predicted-vs-actual comparison and has **never had an input**. The anchor table, the phase totals
  and the accumulators all exist mid-run; a plan crossing its error anchor by 3× is knowable before
  it crosses it by 3.6×. ⇒ Watch until PLAN-TRUTH-088 F2 records the preview. **The 144-build count
  is the largest single lever and is worth investigating on its own.**

- ⚠ **PLAN-TRUTH-049's D-1 verdict is SOUND but its BOUND is wider than the run recorded
  (2026-08-09).** D-1 concluded outcome (i) — our ISO markers age out — from a matched control
  (5.39 d epoch-ms vs 5.21 d ISO, both present, both unexpired ⇒ no differential). The run named ONE
  truncation of its observable window: our own sweep's pruning. **A second was found at the landing
  analysis: the foreign producer RESETS markers** — `0.1.1327`'s marker was deleted at
  `09:39:03.901` while `0.1.1331` was marked 66 ms later. A reset restarts an age. ⇒ **the window is
  narrower than 5.39 days by an unknown amount**, so "no differential within the observable window" is
  weaker evidence than it reads. ⛔ **This does NOT overturn the verdict** — no differential was
  observed and the epoch-ms remedy stays refuted — and it must not be re-litigated as one. It is
  recorded because a bound quietly narrower than stated is this epic's exact subject. **Settling it
  requires watching one dir across two foreign-GC cycles, not waiting longer.**
- ⛔ **THE FINALIZE APPARATUS COST TWICE THE PLAN IT FINALIZED (PLAN-TRUTH-049, 2026-08-09).**
  **68% of 6.4M raw / 104.9M billing-weighted tokens was `6-finalize`**, driven by **four review rounds
  and three loop-backs** — for a **five-file documentation-and-invariant change**. ⚠ **Not filed as a
  defect**: four rounds found five real defects across three independent mechanisms, including a
  vacuous guard reintroduced *by its own fix*, so the spend bought something. It is recorded as a cost
  datum for the token-reduction priority, and as the counter-example to any "finalize is overhead"
  framing. ⭐ Note the shape: **a doc-only plan's finalize is not cheaper than a code plan's**, because
  the review rounds key on the PR, not on the diff's nature.
- ⭐⭐ **PLAN-TRUTH-055's SUBJECT REPRODUCED INDEPENDENTLY WHILE IT IS RUNNING (2026-08-09, #1123).**
  `metrics.md` totals **5.6M tokens** while the **dispatch ledger sums differently**, and the
  retrospective flagged **`5-execute` carrying three inconsistent totals** — plus **three defects in
  the retrospective's own machinery**. This is not new work: it is a second, independent instance of
  the re-entered-phase accounting defect **-055 is in flight against right now**, so it raises that
  plan's population rather than opening a queue item. ⛔ **Do NOT stage it separately** — the duplicate
  would be invisible to -055's own ledger, which is the shape that retired PLAN-PR-018.
- ⚠ **UNVERIFIED LEAD, and the stated justification did NOT hold — `uv.lock` churn (2026-08-09).**
  #1123 reverted a regenerated `uv.lock` on every build, justified as *"main's lock appears stale
  against the landed ruff bump"*. **Checked first-party: it is not.** The ruff bump `d5dcf900c` (#1097)
  touched `pyproject.toml` only; `uv.lock` was last written by `4fde77e6f` (#1113), **after** it; and
  the lock's ruff entry carries specifier `>=0.16.1` resolving **`0.16.2`** — consistent on both.
  ⇒ **the reverting was the right call, the reason given was wrong.** What remains is a different and
  unverified claim — that the lock re-resolves on every build — which would be ordinary drift against
  newer releases, not staleness against #1097. ⭐ Worth separating because *"stale against a landed
  bump"* implies a missed update someone must apply; *"re-resolves on every build"* implies a build
  reproducibility question. **No PR is owed for the reason given.**
- ⚠ **OPERATOR FORK, OPEN — the dirty `.plan/project-architecture/*` descriptors on main.** #1123 left
  two descriptor files dirty with learned hints written mid-run, and **they now have no push path**
  because the PR landed. The operator asked whether to land them via a follow-up or discard. ⛔ **This
  is PLAN-TRUTH-064's exact subject** (the guard that cannot see `.plan/` files dirty on main) — and
  **-064 is currently BLOCKED** by the cross-epic `executor-rejects-invalid-invocations-before-spawn`,
  so the owning plan cannot answer it. ⭐ Note the compounding: the file is an **active producer** that
  grows on most runs (4 hint lines, then 6, then this pair), so "decide later" is not cost-free.
- ⚠ **UNOWNED, INHERITED FROM PLAN-TRUTH-011 (2026-08-09).** The "logging-escape probes written into
  the permanent work log" observation (PR #1034) was carried into 011 as an explicitly-non-deliverable
  hypothesis for outline-time re-verification. **Nothing in the landed diff addresses it, and the plan
  that carried it has shipped** ⇒ it now has no owner. Re-home or discard at the next drain.
- ⛔ **TWO OF OUR RECORDED CLAIMS WERE REFUTED BY `review-apparatus`, 2026-08-01. Both corrections stand.**
  - **`#1066`: CodeRabbit DID review — our claim is REFUTED.** Our anchor carried *"#1066's FIRST question
    is whether CodeRabbit actually reviewed … it has NOT been run."* **They ran it.**
    `ci pr comments --pr-number 1066` returned **8 CodeRabbit comments including a Major** (compose-result
    shape contract), 3 inline at 11:58:43Z, PR merged 12:06:46Z — **8 minutes later**, with **all 8
    unresolved**. ⇒ Not one-bot-deep; the awaitable window is not implicated. ⚠ **A merge with 8
    unresolved comments incl. a Major is itself a post-merge triage obligation** (PLAN-102's subject).
  - **`truthful-signals-009` (our finding on #1071): mechanism RIGHT, target bot WRONG.**
    `standards/coderabbit.md` stops our scenario twice — `participation_requires_update: false` (so
    #1071's movement arm never applies to CodeRabbit) and `refusal_patterns: ["Review limit reached"]`,
    which our evidence body matches **verbatim**. CodeRabbit was **correctly** classified refused.
    ⭐ **But the mechanism is real and lands on PR-Agent**, where `participation_requires_update: true`
    AND `refusal_patterns` is **EMPTY** — a PR-Agent refusal edited in place would be credited as
    participation, on the bot that is **required**. ⚠ Marked **HYPOTHESIS, not observed** by them (no
    PR-Agent refusal has ever been seen — which is *why* the list is empty). **Owned by
    `review-apparatus`; nothing owed by us.** ⭐ The sharp part: **#1071 did not create the empty list,
    it changed that list's risk profile** — the emptiness was deliberate and fail-closed, and safe until
    *movement* became a credit signal. Nobody re-examined the old reasoning against the new arm.
  - ⭐ **THEIR META-LESSON, adopted as ours**: *"a claim repeated across two messages is still ONE source,
    and we treated the repetition as corroboration."* They had counted `#1066` as a second measured
    instance because it appeared in two of our messages. **Repetition is not corroboration** — count
    sources, not mentions.
  - ✅ They **ACCEPT** our #1073 participation picture, and note our `1 reviewer, 0 actionable` reading is
    itself corrupted by **PLAN-PR-016 (running)**: the aggregator maps `accepted` → `false_positive`.

- ⭐ **FINALIZE HOT-PATH INTEL, measured 2026-08-01 over the 39-plan archived corpus. Reuse these
  numbers; do not re-derive them from scratch.** (Residue of the deleted PLAN-TRUTH-029.)
  - **CI-run overhead is real: 58 runs for 36 plans (61 % over one-per-plan). 16 of 36 (44 %) re-ran.**
    Distribution 20×1, 11×2, 4×3, 1×4.
  - ⛔ **The cause is triage loop-backs, NOT rebase staleness.** All 16 multi-run plans recorded a
    `Loop-back iteration`; a search for the discriminating case — >1 CI run with ZERO loop-backs —
    returned **none**. Example: #1068 logged *"unified triage created 3 fix tasks … loop_back_target=
    5-execute"*.
  - ⭐ **THE ACTIONABLE QUESTION**: loop-backs are **necessary but not sufficient** — several plans
    recorded `loopback=1` with only ONE CI run, so some loop-backs are absorbed without a re-run.
    **What distinguishes an absorbed loop-back from a re-running one is the real lever on the hot path.**
  - ⛔ **Do not "move the rebase later".** 2 of 39 `sync-baseline` records resolved merge conflicts
    (`2 conflicts resolved`, `3 conflicts merged`). The early rebase surfaces conflicts BEFORE the merge
    mutex is held; moving it later would resolve them **while holding the cross-plan lock**, blocking
    every other plan. The current placement is a conflict pre-filter, not a liability.
  - **OBSERVED**: 39 of 39 `finalize-step-sync-baseline` records read `action=rebased` — never a noop.
    `origin` had advanced before finalize started in every recorded plan. ⚠ Two read
    `action=rebased, 0 upstream commits` — a rebase reporting no upstream work; **mislabelled noop or a
    real defect, unresolved.**
  - ⚠ **MEASUREMENT GAP**: `branch-cleanup`'s `display_detail` is free text; only ~10 of ~35 records
    mention rebasing at all. **The late rebase's action is not recoverable from the ledger**, so the
    doc's claim that it "degrades to `action: noop` in the common case" is **UNVERIFIED — not refuted**
    (the 39/39 figure measures the EARLY rebase, a different step). ⇒ Fold the structured-`display_detail`
    fix onto **PLAN-TRUTH-006**, which already owns this surface.
  - ⭐ **The merge goes through a PLATFORM MERGE QUEUE** (nearly every `branch-cleanup` record says
    *"merged via queue"*), which performs final validation — that is why the force-push→CI-invalidation
    path does not fire. **Check this before proposing any merge-path change.**

- ⚠ **Our build wrappers normalise their OWN output paths and not the caller's.** From the API-Sheriff
  PLAN-35 report (their Link 1, **VERIFIED by their reproduction, not by us**): in one command line the
  `build-maven` wrapper supplied its `-l` build-log flag as an **absolute** path while the caller's
  `-Dmdep.outputFile` rode through **relative** — and `maven-dependency-plugin` resolves `outputFile`
  against the **module** basedir under `-pl`, not the invocation directory. The file landed in a
  directory nobody expected, where a root-anchored `.gitignore` pattern (`.plan/*`) did not cover it,
  which is what turned a stray temp file into a dirty working tree and then into the `rm -rf`.
  ⭐ **The infrastructure already applies the right discipline to its own flag and does not extend it
  to the caller's.** ⇒ Watch, not staged: the fix for *their* instance is an API-Sheriff `CLAUDE.md`
  note (Rec 1, theirs), but the generalisable question — should a build wrapper normalise
  caller-supplied output-path arguments to absolute — is ours and is unanswered. **Do not stage until
  the population is derived**; one instance in one wrapper is not a pattern yet.
  ⛔ **Do NOT "fix" this by broadening `.gitignore` to `**/.plan/`.** The report is explicit and
  correct: the root-anchoring is what made the bug *visible*. Hiding nested `.plan/` directories would
  suppress a working signal and let the next stray accumulate silently.

- ✅ **PLAN-TRUTH-003's (ex-PLAN-96) `manage-metrics` deferral is LIFTED — the condition expired unnoticed.** The spec
  deferred `manage-metrics/scripts/manage-metrics.py` explicitly while
  `code-intelligence-substrate`'s **#1059 was open**. Reported via `code-intelligence-substrate-005`
  and **orchestrator-verified against `git log`: #1059 merged as `dfe7fde0b`.** PLAN-TRUTH-003 may take the
  deferred site. ✅ **The unrelated HOLD is ALSO cleared as of 2026-07-31** — the `manage-status` and
  `manage-execution-manifest` collisions were with PLAN-57 and PLAN-202, both now SHIPPED (#1068, #1066).
  ⭐ The interesting part is not the lift but that **nothing would ever
  have told us**: the release was an event in another epic's ledger. This is what the new
  name-the-PR convention exists to prevent.
- ✅ **POST-MERGE REVISITS — ALL FIVE TRANSFERRED to `review-apparatus` 2026-07-30** (#1055, #1057,
  #1058, #1059, #1061). Operator decision, via `review-apparatus-004`: splitting one out of a batch of
  five was worse than either whole, and post-merge review coverage is that epic's subject. **They are
  recorded there as watches; the standing post-merge-revisit rule no longer binds us for PR-related
  PRs.** ⚠ This REVERSES the position recorded here hours earlier ("the revisits stay OURS") — the
  earlier reasoning was that the rule is about our landings, and the operator overrode it. The detail
  below is retained because it is the evidence they inherited, not because we still owe the work.
  - **#1059** (added 2026-07-30 from `truthful-signals-008`) merged with **no bot review of its final
    HEAD `cf634762`**: pr-agent reviewed `acbdcecf3` **75 minutes earlier**, CodeRabbit was genuinely
    rate-limited (body carries `rate limit`), Sourcery hard-refused. ⇒ **Partial participation read as
    participation while the merged diff went unreviewed.**
  - **#1057**: CodeRabbit's refusal said *"next review available in 2 minutes"* — that gap is
    **RECOVERABLE** via an explicit re-review trigger, so this one is worth doing first.
  - ⛔ **The line above is SUPERSEDED** — see the transfer note at the head of this entry.
- ⭐ **Across two epics and five PRs in ONE day, the review channel failed in five DISTINCT ways and
  every failure was survivable by operator authority.** Raised jointly by
  `code-intelligence-substrate-005`: ours were #1061 (check completed with **no comment at all**) and
  #1058 (reviewed HEAD 1, refused HEAD 2); theirs were #1056 (CodeRabbit never reviewed) and #1059
  (**all three** bots non-participating). ⇒ **That population must be DERIVED before any detector is
  built against it** — it is now `review-apparatus`'s to own, and it is the strongest argument yet
  that the participation signal must report **HOW it concluded, not just WHAT**. Forwarded in
  `truthful-signals-001`.
- ⚠ **"Orchestrator" names TWO entities, and PLAN-TRUTH-015 would sharpen the collision rather than
  resolve it.** `execution_tier: orchestrator` (`persona-plan-marshall-agent/SKILL.md:76`) is owned
  by the **plan-lifecycle orchestrator** — the `/plan-marshall` main context that *drives the
  worktree* and dispatches leaves. It is NOT the **epic orchestrator** (`marshall-orchestrator`),
  which drives no worktree and is forbidden implementation builds by the prime directive. A plan
  saying *"the orchestrator-tier build I owe"* is correct: its own main context must run it rather
  than dispatch it to a leaf.
  ⇒ **PLAN-TRUTH-015 renames the EPIC orchestrator to `plan-orchestrator`** — which is very nearly the name
  of the plan-lifecycle orchestrator that owns this tier. **Operator asked which entity was meant on
  2026-07-29, which is live evidence the two are already confusable under the CURRENT names.**
  PLAN-TRUTH-015 should either pick a name that does not collide with the tier vocabulary, or explicitly
  rename the tier in the same change. Re-check at its scoping — it is drain-gated to last, so
  there is time.
- ⚠ **"pr-agent has no availability problem" is now TOO STRONG — self-corrected by the plan that
  relied on it.** Within minutes of pr-agent being made the **sole required bot on reliability
  grounds**, its `review / review` job **FAILED** on #1052's HEAD `5eb51463e`, leaving that commit
  with **zero review coverage** (CodeRabbit rate-limited, Sourcery weekly-quota'd).
  ⭐ **The failure mode still argues FOR the decision**: a job failure caught **fail-closed** — the
  gate reported `FAILURE`, not a false green — which is the machinery working, and is categorically
  better than a silent quota refusal reported as `SUCCESS`. **But availability and honesty are
  different properties, and only the second was ever demonstrated.**
  ⇒ ⚠ **This bears on #1048** (*"review every pushed HEAD so the primary bot's evidence is
  reliable"*), which **merged as `fe130064f`** — its premise is pr-agent reliability, and pr-agent
  failed on the very next PR. Re-check that #1048's fix addresses job-failure recovery and not only
  stale-HEAD coverage.
- ⛔ **A DEDUP INSTRUCTION WAS REFUTED — the defect is a PATTERN, not a site.** PLAN-103 reported that
  *"#1049 already fixed the planning-lane scoring defect I filed as candidate lesson -005 — the epic
  should dedupe rather than queue it."* **Verified at HEAD and REFUTED:** `#1049`'s diff touches
  `_cmd_planning_lane.py`, `manage-status.py`, two SKILL docs and two test modules — **it does NOT
  touch `_cmd_change_type_heuristic.py`**, which at HEAD still does
  `for candidate in ('clarified_request', 'original_input')`, i.e. reads **one section, not the
  request body**.
  ⇒ #1049 fixed the *planning-lane scorer*; the **change-type heuristic is a SEPARATE CONSUMER with
  the same section-scoping pattern and was not fixed.** Dropping `-005` would have lost a live defect
  in a second consumer.
  ⭐ **The real lesson is bigger than the dedup**: the narrow-body read was **never one bug — it is a
  pattern replicated across consumers.** ⇒ **PLAN-57's D1 must DERIVE the consumer population**, not
  fix the site it names. ⚠ And a "this is already fixed, drop it" instruction is the highest-risk
  class of lead: acting on it discards work silently and leaves nothing behind to trip over.
- ⛔ **THE DOC LAYER AND THE SCRIPT LAYER RAN AT DIFFERENT VERSIONS IN A LIVE SESSION, WITH NO SIGNAL.**
  Drained from `code-intelligence-substrate-007` 2026-07-30 and **corroborated by symbol at HEAD.** The
  sibling warned that cache `0.1.1240` carries the pre-#1057 pointer regex while the executor embeds
  `0.1.1269`. Verified: `_SOURCE_ID_RE` in the `1240` copy of `_orchestrator_inbox.py` is `PLAN-\d+`
  only, while the `1269` copy is the three-way alternation with `[A-Z0-9]{2,8}` — **one symbol, two
  copies, disagreeing about what an orchestrated pointer is.** 30 version dirs are live in the cache.
  ⭐ **The generalisation is bigger than their warning.** The executor is NOT broken — it embeds exactly
  ONE version (129 paths at `1269`, and the lone `0.1.1069` hit is a docstring example, not a path), so
  neither the mapping check nor `_detect_multi_version_pollution` would fire. The divergence is that
  **this session's skill router served prose from `1240` while every script call resolved `1269`.** That
  pair is inspected by nothing. ⇒ **FOLDED into PLAN-TRUTH-008 as a fourth divergence axis** (its D3
  currently closes the verdict vocabulary at three, which is the plan's own archetype turned on itself).
  ⚠ **Our exposure: NIL, and the check that establishes it matters more than the verdict** — 68 rows ↔
  68 spec files, name-level and **bidirectional**, 0 orphans, 0 mismatches, empty diff. The weaker
  grammar check was nearly accepted in its place (see the next entry).
  ⚠ Also recorded: the code slug is `re.compile`d with **no `IGNORECASE`** — uppercase-only. A lowercase
  slug returns `unrecognised_id` and the plan then writes **no inbox message at finalize**, silent at
  both ends. Do not lowercase a plan id.
- ✅ **A SIBLING ACCEPTED OUR VERIFICATION CRITIQUE, AND BOTH EPICS INDEPENDENTLY DERIVED THE SAME RULE.**
  Drained from `code-intelligence-substrate-008` 2026-07-30. They accepted that their "all 17 pointers
  return `detection: orchestrated`" was **one grammar assertion repeated seventeen times** — `inbox
  detect` never opens the file — and re-ran the bidirectional enumeration (21/21, 0 orphans, 0
  mismatches). They adopted it as their standing rule 5.
  ⭐ **Recurrence, not a new item:** their *"a cross-epic clearance is a snapshot, not a state — re-derive
  from both queues at emit time"* is the SAME rule this ledger already carries as *"re-derive every
  cross-epic blocker against the sibling live queue at drain time."* **Two epics arrived at it
  independently, which is stronger evidence than either statement alone.** Folded onto the existing rule
  per the dedup discipline rather than filed twice.
  ⚠ **Their side-changes are SIBLING-ASSERTED, not verified by us** — `PLAN-TRUTH-001` re-pointed across
  7 occurrences in their `PLAN-CIS-011` and 5 in their `epic.md`; a stale *"cross-epic surface CLEARED"*
  paragraph corrected; our PLAN-105 correction closed a stale dependency line in their `PLAN-CIS-001`.
  **Their tree is outside our direct-file-access carve-out, so we cannot confirm any of it** — recorded
  as their claim. The substantive constraint is unchanged: **PLAN-TRUTH-001 must land before their
  PLAN-CIS-011**. ✅ Its former block behind RUNNING PLAN-202 is CLEARED — PLAN-202 SHIPPED (#1066).
  ⚠ Their `PLAN-49` decision ("keep it, do not renumber") is **MOOT on our side** — `PLAN-49` no longer
  exists in `plans[]`; it was reissued as **PLAN-TRUTH-015** on 2026-07-30. Do not resurrect `PLAN-49`
  from their note.

## ⭐ Standing rules absorbed from the 2026-08-01 drain (8 candidate-lessons)

Four are **recurrences** of rules already here — folded, with the recurrence recorded, per the dedup
discipline. Four are **new** and sharpen an existing rule or add one.

**Folded (recurrence recorded, no new entry):**

- *When a documented count and its enumeration disagree, DERIVE the population — never reconcile the
  numeral to the list.* ⇒ Folds onto **a request that states a count states a sample**. ⭐ This one is
  self-demonstrating: PLAN-TRUTH-001's own derived roster was **9 where its prose said 8**, and
  reconciling downward would have shipped the defect it was written to remove.
- *A fix for the hand-maintained-membership archetype reintroduced the archetype (7th sighting).*
  ⇒ Folds onto **archetype knowledge does not transfer by exposure**; the count stands at **7**.
- *A reviewer's occurrence count is a SAMPLE, not an enumeration — and you cannot tell which you got.*
  ⇒ Folds onto the same count/sample rule; the *cannot-tell-which* half is the sharp part.
- *A path-part skip-list is a vacuous-guard generator.* ⇒ Folds onto **any path-part skip-list is guilty
  until shown to scan**, now sharpened: **every sweep needs a CONTROL ASSERTION** — a case that proves
  the sweep can fail. A skip-list without one is a guard nobody has shown to fire.

**New:**

- ⭐ **A SELF-REVIEW PASS THAT FINDS A DEFECT HAS NOT FINISHED.** Iterate to a genuinely clean pass.
  PLAN-TRUTH-001 found a real defect on **all three** passes; **two were created by its own earlier
  fixes**, and `finalize-step-simplify` caught a seventh in the third-pass fix. Stopping at "the pass
  found something and I fixed it" ships the fix's own defect.
- ⭐ **A DETECTOR THAT RE-DERIVES A SUBSET OF ITS PRODUCER'S RULES WILL DRIFT — CONSUME THE PRODUCER'S
  OUTPUT INSTEAD.** Re-implementing "which things count" beside the thing that decides it guarantees the
  two disagree eventually, silently, and in the direction nobody tests.
- ⭐ **BEFORE GRADING A COUNT IN PROSE, DECIDE WHETHER IT COUNTS THE SYSTEM OR THE FILE'S OWN COVERAGE.**
  The same numeral means different things at the two scopes, and a grader that picks the wrong one
  reports a confident wrong verdict. ⚠ We hit exactly this today reading `13` (one step's contribution)
  against `19` (the plan's total) and nearly filed it as a defect.
- ⭐ **A REBASE WIDENS A RENAME'S POPULATION — RE-DERIVE THE SWEEP AFTER CONFLICT RESOLUTION, NEVER
  ASSUME IT CARRIES.** Upstream commits pulled in by the rebase can contain new occurrences the
  pre-rebase sweep never saw.

## ⭐ Standing rules absorbed from the 2026-08-23 ingestion of PR #1337 (§ 10, four lessons)

Two are **recurrences** of archetypes already tracked here — folded with the recurrence recorded, per
the dedup discipline. Two are **new**.

**Folded (recurrence recorded, no new entry):**

- *L1 — a retirement is not complete until every surface that renders the thing also prunes it.* Two
  consumers of one renderer existed; teaching only one produced a change correct in isolation and
  half-applied in practice. ⇒ Folds onto **doc-contract-divergence / producer-consumer drift**. ⭐ The
  generalizable check is worth keeping verbatim: *after removing something from a shared producer, grep
  for EVERY consumer of that producer, not just the one the task started from.*
- *L2 — the absent test IS the drift mechanism.* `normalize`'s default set had no pin, which is
  precisely why it could silently diverge from the renderer's intent. ⇒ Folds onto **test-pins-the-defect
  / vacuous-guard**, as its constructive inverse: *when adding a second consumer of shared state, pin
  BOTH sides or expect them to part.*

**New:**

- ⭐⭐ **PRUNING A USER'S CONFIG NEEDS A STATED ENTRY CRITERION, AND "it's obsolete" IS NOT ONE.** The
  defensible criterion is *"it grants nothing by construction."* Shipped in `_RETIRED_DEFAULT_RULES`
  (`claude_runtime.py:2596-2610`) and verified first-party at `2cd1a19c8`, verbatim: *"Retirement deletes
  a rule from an operator's settings without asking, which is only defensible because this rule grants
  nothing by construction. A rule that still guards a real tool call does not belong here however
  obsolete it looks."* ⭐ **This criterion was added BECAUSE the adversarial review pointed out the
  mechanism had no guard against its own generalization** — a mechanism whose next entry could silently
  revoke a live grant through the same code path. ⇒ **Any future destructive-by-default sweep over
  operator state owes a written entry criterion before its first member.**
- ⭐ **INSERTING A CLASS MID-FILE SILENTLY REPARENTS EVERYTHING BELOW IT.** A purely mechanical error no
  test catches: the suite stays green while the class docstring becomes false about half its members. On
  #1337 a new test class inserted mid-file reparented two live-default tests under a docstring that was
  false about them, and it was caught by review rather than by any gate. ⇒ **Run a targeted parentage
  check after ANY test-file restructuring.** ⚠ This is the same shape as the `_is_uniform_array` lesson
  already recorded under Open Defects — *a green suite is not evidence about a property the suite does
  not assert* — arriving through a different door.

## ⭐⭐ Standing rule absorbed 2026-09-03 — a data-point from `nifi-extensions`, NOT ingested as work

⛔ **Recorded as a RULE only.** No defect, no spec, no queue row, and nothing corroborated first-party —
the run is a consumer project and was supplied as a data-point (operator direction). It earns a place
here because it names a failure mode this epic did not have a word for.

- ⭐⭐⭐ **NOTICING SOMETHING AND THEN REASONING IT AWAY WITHOUT A CHECK IS WORSE THAN NOT NOTICING IT.**
  The reporting run's pre-submission self-review **did** spot the defect (an empty-error-object case) and
  waved it through as *"consistent with the documented semantics"* — without testing it, and without
  checking it against the issue text, **which said the opposite**. ⇒ The lesson is NOT that the review
  missed it.

  **Why this is sharper than an ordinary miss, and why it belongs to this epic:** a miss leaves NO
  TRACE, so the question stays open and the next reader may still ask it. **A dismissal leaves a
  RECORD SAYING "CHECKED"** — it closes the question for everyone downstream on the strength of
  reasoning that was never tested. That is this epic's theme exactly (*a confident signal hides a
  caveat*), located in the one place we had assumed was the remedy: **the review itself manufactures the
  false confidence.**

  ⇒ **The operational rule: a self-review that reasons an observation away owes the same evidence as one
  that reports a finding.** "Consistent with the documented semantics" is a HYPOTHESIS about the
  documentation, not a verdict about the code — and here the documentation and the issue text disagreed,
  so the reasoning was checkable and cheap to check. ⛔ **A dismissal without a check is not a cleared
  finding; it is an unrecorded one.**

  ⚠ **Bearing on staged work, as a seam and not a transfer:** `PLAN-TRUTH-108` (*the self-review decides
  its own close and its distinguishing property is invisible*) is the natural owner should this ever be
  actioned. **It is deliberately NOT folded there** — the operator supplied this to learn from, not to
  schedule, and an unrequested fold would manufacture scope. Recorded here so the rule survives the
  session; a future reader deciding to act on it starts at `-108`.

- ⭐ **A test that passed on arrival is not evidence the fix works, and a report must say which is
  which.** The same run isolated its red phase deliberately — **7 assertions failed for the right reason
  before a two-line fix, while 3 coverage tests passed on arrival** — and said so rather than implying a
  full red-green cycle across all ten. ⇒ **Report the red-green split, never the aggregate.** An
  all-green suite that includes tests which never went red proves less than its size suggests, and
  stating the partition is what keeps the number honest.

## ⭐ Standing rules absorbed from the 2026-08-24 PLAN-TRUTH-075 drain

- ⭐⭐ **RE-GROUND A STAGED SPEC AGAINST HEAD AT EXECUTION START — QUEUE LATENCY AGES SPECS, AND THE
  REMEDY IS NOT BETTER STAGING.** PLAN-TRUTH-075 staged four deliverables; **three closed on
  re-verification with no code change** (D0 by code read, D1 already satisfied at both sites, D2 already
  shipped by #1299). The spec was staged 2026-08-09 and executed 2026-08-23; #1299 landed 2026-08-18 —
  **during the 14 days it waited.** ⛔ **Nothing about the staging process could have caught this**, so
  the remedy is re-verification at *execution* time, not better sourcing at *staging* time. ⭐ **The
  mechanism that produced this outcome already exists and should be strengthened, not replaced**:
  phase-2-refine's source-premise verification is what did it, and it paid for itself several times over
  on this plan alone — the cost of *not* doing it would have been three unnecessary edits to a file two
  other plans also claim. ⚠ **This is the orchestrator's `corpus set-verdict` field seen from the plan
  side**, and it is the strongest evidence yet that the prep-ready admission test is worth its
  machinery. One addition worth making: when re-verification closes a deliverable because its target
  already shipped, **record the landing commit AND its date and compare against the staging date** — the
  predates/postdates distinction is cheap to compute and was got wrong twice here by inspection.

- ⭐⭐ **A GUARD BUILT TO PREVENT A DEFECT IS A PRIME SITE FOR THAT DEFECT — SECOND CONFIRMATION, NOW
  TREAT IT AS EXPECTED.** PLAN-TRUTH-075's n−1-of-n guard **reproduced n−1-of-n four times inside
  itself**, across five rounds, each one level deeper: glob pinned at 2 of 4 sites → population check
  was mere non-emptiness → skip row bound POSITIONALLY while the docstring claimed semantic → **the
  REPORT surface still bound positionally, same defect other surface** → the cardinality floor cannot
  detect a marker SWAP. PLAN-TRUTH-055 did the same inside its own fix. ⇒ **Two independent
  confirmations: this is expected behaviour, not a surprise, and a fix for a vacuous guard must be
  reviewed as adversarially as the guard.** ⭐ **The most instructive round is the one whose FIRST FIX
  WAS WRONG**: block-wide uniqueness failed on a *correct* document, because the block legitimately
  quotes a second phrase in its stale-base paragraph — and **the tests caught it**. The landed fix scopes
  the binding to the verdict sentence's paragraph. Guard grew 4 → 10 tests, every fix with a matched
  negative control, two of them red against a first-match binding.

- ⭐ **THREE OF FIVE REPRODUCED DEFECTS WERE ANTI-CORRELATED WITH THE INTERESTING CASE.** `tests_run: 0`
  on GREEN runs only (the RED path reports correctly) · a coverage budget that truncates ONLY passing
  runs (the failing path short-circuits inside it) · a gate-delta unmeasurable only when a gate
  re-fires. ⇒ **When auditing a signal, test the HEALTHY path first.** A signal that degrades only when
  the system is working is invisible to exactly the runs that would expose it, and this drain found
  three in one plan.

## ⭐ Orchestrator practice — rules adopted from hand-offs and from this orchestrator's own failures

Each is addressed to **this orchestrator**, not to a plan, so they are recorded as practice rather
than staged as work.

- ⛔⛔ **A HAND-WRITTEN COLLISION MAP IS WRONG AGAIN — R39 RECURRED, IN THE SAME SESSION THAT WROTE R39
  DOWN. (2026-08-23, this orchestrator's own failure.)** Staging `PLAN-TRUTH-103` and `PLAN-TRUTH-104` I
  hand-derived each spec's Dependencies section, **including a sentence in each telling the reader not to
  trust a hand-written map**, and then ran `corpus cross-check` (152 specs / 7 sibling epics / 7 live
  plans). Results: `-103` — I named 2 collisions and **missed 2** (`PLAN-TRUTH-086`, and the cross-epic
  `PLAN-CIS-052`); `-104` — I named 1 and **missed 2** (`review-apparatus/PLAN-PR-030`,
  `code-intelligence-substrate/PLAN-CIS-052`). **Both misses on both specs were the CROSS-EPIC ones** —
  the class a single ledger structurally cannot see, which is precisely why the machine arm exists. ⇒
  **Never author a Dependencies section from reading; generate it, then write prose around the generated
  set.** ⭐ The subject check still had to be done by hand and it earned its keep: `PLAN-PR-030` shares
  `review_commitments.py` with `-104`, and only reading it established that its item is the **exception
  tuple** (G17, drop a dead `KeyError`) rather than the branch table — an ordering constraint, not a
  duplicate. **The machine finds the overlap; only a reader can tell a collision from a duplicate.**

- ⛔⛔ **DRAIN A PASTED REPORT BY SECTION, NEVER BY ITS LESSON LIST. (Adopted 2026-08-23 from FOUR
  misses in one ingestion — this orchestrator's own failure, not a hand-off.)**
  Ingesting the PR #1332 run report, I dispositioned all 13 numbered lessons and **skipped the analysis
  sections**. Four dispositionable findings were missed, and **each surfaced only because the operator
  asked** — twice:
  - **§ 10** (automatic-review round-tripping: cycle 1 worth it, cycle 2 not, the amplification not review
    cost at all, 1 of 10 findings self-inflicted) → belonged to `review-apparatus`, forwarded late.
  - **§ 9.9 rec 3** (right-size the finalize gate band) → its premise was REFUTABLE at HEAD; the mechanism
    already exists.
  - **§ 2.6** (the `_is_uniform_array` landmine) → a **do-not-fix warning**, the class of item that
    evaporates most easily because it schedules no work.
  - **§ 9.6** (the exploration split, a second data point on a sibling's n=1 headline figure) → belonged to
    `code-intelligence-substrate`, forwarded late.
  ⇒ **Adopt, both halves:** (1) the drain's population is the report's **SECTIONS**, enumerated before
  dispositioning — a numbered lesson list is a *subset* of a report's findings and is never its census;
  (2) **state which sections were covered** in the drain record, so the drain's own coverage is
  inspectable rather than asserted. A report's narrative sections routinely carry the findings its author
  did not think to number — including every *do-not-do-this* warning, which by construction appears in no
  lesson list.
  ⭐ **This is the epic's own archetype committed by its orchestrator: a completeness claim over a
  population that was never enumerated.** It is recorded HERE, in narrative, and deliberately not left in
  the `resume_anchor` where it was first written — the anchor is rewritten every session, so a standing
  rule kept only there is a rule with an expiry date. **That mistake was made once with this very rule**
  before it was moved.

- ⚠ **Report a corpus-reconciliation state by its own name; never in words that collide with a lifecycle
  status. (Adopted 2026-08-23, operator-flagged.)** I described `-098`/`-099` as **"unqueued"** — meaning
  *a spec file with no `plans[]` row* (`specs_without_row_count`) — and the operator reasonably read it as
  **"paused"**. Those are different kinds of thing: reconciliation state versus a value in the closed
  lifecycle vocabulary (`staged` / `launched` / `running` / `shipped` / `parked` / `superseded` /
  `transferred`). ⇒ Name the reconciliation state explicitly and say what it implies — *"has a spec file
  but no queue row, so it is invisible to every check that keys on the queue"* — rather than coining an
  adjective that reads as a status.

- ⛔ **Emit-time re-grounding verifies CITATIONS, not PREMISES — and a citation check cannot catch a
  stale premise.** Observed three consecutive times in that epic: an emit-time "Premise HEAD Stamp"
  correctly caught stale citations, while refine/outline then falsified **four** premises it had
  passed. The clearest case: *"every line number was accurate; what was stale was the REASON for the
  deliverable, because the immediately-preceding plan in the same workstream had already done the
  work."*
  ⇒ **Adopt:** for a staged plan with a **hard dependency on an immediately-preceding plan in the
  same workstream**, add an emit-time step beyond the citation check — **per deliverable, ask whether
  the dependency's landed diff already satisfies it**, and mark it `VERIFY-STILL-NEEDED` rather than
  `OBSERVED`. ⇒ **And:** when a spec records a deferred question about mechanism (*"confirm at outline
  whether X"*), that premise is **UNVERIFIED**, not merely unconfirmed — **it must not be stated as
  OBSERVED alongside verified citations.**
  ✅ What worked and is kept: a verify-first clause of the form *"re-ground this spec against
  {PLAN}'s LANDED DIFF; do not document what its spec promised, document what it shipped"* — it
  caught all four.
- ⚠ **`auto_emit` makes `launched` ambiguous and over-reports concurrency.** Under `auto_emit: true`
  the stamp is recorded at **emit** time, so a plan the operator never started still counts toward
  `R`. ✅ **This epic runs `auto_emit: false`, so the stamp tracks reality here** — recorded because
  the *counting* lesson applies regardless.
  ⭐ **The cheap check, which this orchestrator independently hit on 2026-07-29**: a started plan has
  a `.plan/local/plans/{plan_id}/` directory; an emitted-but-unstarted one does not. ⚠ **Timing
  caveat: the directory lags a real start by tens of seconds, so a single negative check immediately
  after a reported start is NOT evidence of failure.**
  ⇒ **Handling rule adopted:** when a slot is held by an emitted-but-unstarted plan, **re-emit THAT
  plan** — filling the slot with a different one strands the first.

- ⛔ **GOVERNANCE GAP — PR #1048 landed on main matching NO plan in either epic queue.** Work is
  reaching `main` outside the epic ledger, so no landing was analysed, no post-merge revisit ran, and
  no residue was drained for it. **Establish provenance and decide whether ad-hoc PRs get a
  lightweight ledger row** — otherwise the queue silently stops being a complete record of what
  shipped. ⚠ **#1051 and #1052 are in the same category and still open.**
- **Standing rule:** a green finalize is not proof the bots saw the diff. Only
  `ci pr comments --pr-number N` is evidence of participation; a check state is not.
  ⭐ **CONVERSE NOW STATED EXPLICITLY, on direct counter-example: a green bot check is NOT evidence of
  participation and MUST NOT be read as one.** Observed **twice within one hour on two PRs**
  (`lane-router-…-018`): on #1052 at 11:09:59Z the aggregated check list read `CodeRabbit SUCCESS
  pass` while CodeRabbit's own comment, **same minute**, said *"Review limit reached … so we couldn't
  start this review."* The identical pair occurred on #1049 at 09:23:24Z — and the review that
  eventually ran ~70 minutes later found **2 actionable issues, 1 Major**. ⇒ **The green check was
  not merely uninformative; it was green over a diff that genuinely contained defects.**
  ⛔ **Silence would be safer than this**: an absent check reads as *unknown* and is treated
  cautiously; a `SUCCESS` check reads as *reviewed, clean* and is treated as evidence. The refusal is
  machine-readable with a named reason and retry window — but only on the `pr comments` surface,
  which gates do not consult, while the check surface they DO consult has already collapsed it to
  `pass`. ⚠ The `review_completeness` guard **did** classify the refusal correctly from the comment
  surface on #1049 — **the detector works; the defect is the parallel contradicting signal.**
  ⇒ Open PR **#1051** (*"gate the merge on required-bot participation, not comment count"*) appears
  to address exactly this — **establish its provenance and confirm before staging anything new.**
  ⭐ **RECURRENCE 2026-07-28 (#1041) — the live confirming instance.** CodeRabbit produced a
  `completed` **check-run** while posting only a rate-limit refusal: zero review body, zero inline
  comments. Reading the check state would have reported a required bot as "done". ⇒ Sharpens the
  rule with the mechanism: a check conclusion reports that the bot's **integration** finished, which
  **a refusal also satisfies**. And **a comment authored *by* a bot is not a review *by* that bot.**
  Participation is established from each bot's declared publish shape — CodeRabbit: posted review
  body or inline comments; PR-Agent: the Guide `issue_comment` via presence **plus `updated_at`
  movement**, never inline-comment count, never check state; Sourcery: posted review body. Quorum
  over `required_bots` proves participation only, **never review quality**. PLAN-92's shipped D6 is
  the machinery form of this rule.
- ⛔ **Standing rule — every landed plan gets a post-merge PR revisit before its `analyze` closes.**
  The merge outruns the review: CodeRabbit posted **58 s** after merge on #1026 and **2 m 42 s** after
  merge on #1036, so a finalize that observed a clean PR is observing a review that had not happened
  yet. Findings that arrive in that window land **untriaged in main** and are invisible to the plan
  that caused them — #1036's five live findings are exactly this, and PLAN-102 exists because of it.
  The revisit is therefore **mandatory per landing, not opportunistic**:
  1. Fetch the merged PR's comments at analyze time — `ci pr comments --pr-number {N}` — never the
     check state, never the plan's own report, never the inbox landing message (all three are leads).
  2. Read **every** comment against the merge timestamp. A comment newer than the merge is a
     post-merge finding the plan never saw.
  3. **Scan for the same pattern elsewhere, do not stop at the one PR.** A late review that fired on
     one PR fires on its neighbours: check the sibling PRs landed in the same window for comments
     arriving after their own merges. A single-PR check reads a recurrence as an isolated incident.
  4. Record what is found as an Open Defect / inbox `finding`, with the recurrence count stated
     **separately** from the number of PRs examined — a volume is not a coverage number.
  A landing whose revisit was skipped is **not reconciled**, however green the finalize looked.
- ⛔⛔ **PLAN-92's landing message ASSERTS A MERGE THAT HAS NOT HAPPENED — reconciliation is OWED.**
  Message `one-coherent-automated-review-contract-002.md` (21:04:27Z) states PR #1041 "merged … HEAD
  `b9692bebe`". **Verified against ground truth: `origin/main` head is `8b143643b` (#1040), and
  #1041 is still OPEN.** PLAN-92 therefore stays `launched` — no landing report, no `shipped`
  transition, no `pr` stamp. ⭐ **This is the THIRD confirmation of the standing rule that a landing
  message is written PRE-MERGE and has asserted a landing that had not happened** — PLAN-100 owns
  the fix. **Reconcile PLAN-92 from PR state when #1041 actually merges, not from this message.**
- ⛔ **#1041 will merge with PARTIAL REQUIRED-BOT COVERAGE, by explicit operator decision.**
  `required_bots = coderabbit,pr-agent`; only **pr-agent** reviewed. CodeRabbit — a **required** bot —
  never reviewed (rate-limit refusal, still refusing ~30 min past its own stated 51-minute ETA), and
  Sourcery hard-refused on the 150 000-character diff limit. ✅ **The contract did NOT launder the
  gap** — it recorded "pr-agent reviewed 1 finding fixed, coderabbit rate-limited, sourcery over size
  limit" and "1/3 bots reviewed". ⚠ **But the shipped surface has been reviewed by ONE of TWO
  required bots, and the one defect found in it (`1a69d5`) was found by that single reviewer.**
- ⭐ **DECISION OWED (operator) — does a large-diff plan owe an explicit accepted-coverage-gap
  record?** Sourcery is now **structurally unreachable for large plans**: its refusal is keyed on
  diff SIZE, not time, so no wait-and-retry recovery can ever reach it, and there is **no signal at
  planning time** — it surfaces only at finalize, after the diff exists. Classified `optional` here
  so the gate did not block. Two candidate postures: (a) a size ceiling becomes a planning
  constraint whenever a size-limited bot is `required`, or (b) an explicit accepted-coverage-gap
  record, mirroring the partial-required-coverage decision made on #1041. Practice half filed as
  lesson `2026-07-28-23-002`.
- ⭐⭐ **FOURTH CONSECUTIVE PR (#1040) — the refusal was again unrecognized, and BOTH rate-limit
  shapes appeared on ONE PR.** Sourcery was refused at 18:52:26Z with the **weekly diff-character
  quota** phrasing (second confirmation of that shape); CodeRabbit was refused at 18:52:31Z with the
  **rolling-window** phrasing (*"Review limit reached… next review available in 6 minutes"*) and then
  reviewed successfully at 19:33Z. The finalize nonetheless reported **"review-retrospective: 2
  reviewers compared"**. ⇒ This is direct second confirmation of **PLAN-92 paste items (2) and (6)**,
  and the unrecognized-refusal streak is now **#1024, #1032, #1034, #1040**.
- ⭐ **PLAN-105 SHARPENED (orchestrator-verified 2026-07-29) — the root is an ASYMMETRY, not an
  empty intersection, and it shifts D1's likely verdict toward option (a).** Operator observed
  leaves repeatedly reporting *"hit the R2 block on bare grep and fell back to git grep"* and asked
  whether `architecture` lookup is unused or broken. **Verified: neither.**
  `architecture find --pattern "recipe-match"` returns **0**; `--pattern "*recipe_match*"` returns
  **4, all PATH matches**. `manage-architecture/SKILL.md` classifies `find` as a files-inventory
  reader — *"categorised paths, reverse lookup, **glob search**"*. **It is a path glob, never a
  content search, and it works as designed.** The "structured queries first" rule is likewise scoped
  to **navigation** (file discovery, module identification, path resolution) and never claimed to
  cover content matching.
  ⇒ **The real defect:** `CLAUDE.md`'s no-shell-file-ops rule prescribes **the Grep tool** as the
  remedy for content search — correct and satisfiable **in main context**. Dispatched leaves have
  that tool **revoked at runtime**, while the **prohibition on bare `grep` is still enforced**.
  **The permission was withdrawn but the prohibition retained**, so the rule's own remedy is
  unavailable exactly where the rule still binds. `git grep` survives only via the incidental git
  carve-out.
  ⇒ ⛔ **THIS RECOMMENDATION IS REFUTED — recorded, not quietly dropped.** The ledger previously said
  the asymmetry *"argues for D2 option (a) — grant `Grep` to `execution-context` leaves."*
  **First-party evidence gathered by PLAN-105 before it stood down disproves it** (arch-constraint
  `2026-07-29-08-001`): `Grep`/`Glob` were revoked from **six separate dispatched leaves in one run**
  while the agent frontmatter declared them and `permissions.deny` was `[]`. **Neither project
  surface withholds the tool** — the revocation is at harness runtime, above both, so **no edit in
  this repository can widen it back.** Granting `Grep` is therefore **not an available repair**, and
  the recommendation was unimplementable.
  ⇒ **The surviving answer is `code-intelligence-substrate` PLAN-03 `content-search-seam`**: deliver
  content search as a **script seam** through `execute-script.py` — reaching leaves with no harness
  change and no permission change — and **eliminate `git grep` as a practice** rather than document
  it. PLAN-105 was **CLOSED-SUPERSEDED** (PR #1046 closed, never merged); see
  [`landings/PLAN-105.md`](landings/PLAN-105.md).
  ⭐ **Kept verbatim as a worked instance of the epic's own standing rule — our analysis is not
  exempt.** A confident orchestrator recommendation was wrong on a checkable fact, and the plan it
  was aimed at disproved it.
- ⭐⭐ **THE PUREST INSTANCE THE EPIC HAS PRODUCED — phase-4 froze `enabled_bots`, the very key
  PLAN-92 retired, leaving ZERO bot gating on PLAN-92's own PR.** A plan whose subject was
  single-sourcing the bot contract shipped past a gate that had been silently emptied by its own
  change. Recorded from the #1041 retrospective; the general frozen-vs-live reconciliation is
  PLAN-64's D3.
- ✅ **#1041 re-checked 2026-07-29 (~8 h post-merge): STILL CLEAN, no late review ever arrived.**
  CodeRabbit never returned despite the stated 51-minute ETA. ⇒ **The "wait for the window and the
  bot will review" theory is REFUTED for this PR** — a required bot's refusal can be terminal for the
  whole PR, not merely delayed. Reinforces lesson `2026-07-28-23-001` (an ETA is a lower bound, never
  a wait budget) and the operator decision owed on accepted-coverage-gap records.
- ⚠ **The CI check named CodeRabbit reported SUCCESS at #1041's merge time while no review had
  happened** — the second observed instance (after #1042's `completed` check-run) of a green
  bot-named check over a refusal. This is the machinery form of the standing rule below.
- ✅ **RETIRED 2026-07-29 — the two #1049 post-merge findings are REMEDIATED.** PR **#1052** merged as
  `ef80c1c8d` at 12:50:15Z carrying both fixes (title strip anchored to line 1; the S3 unset-signal
  prose corrected). ⚠ **#1052 itself landed UNQUEUED** — a fifth ad-hoc PR — but its own post-merge
  revisit is **clean** (latest comment 11:44:35Z, merged 12:50:15Z), so the late-arrival recurrence
  **stays at n=4**. The entry below is kept for the record; the findings it describes are no longer
  live in main.
- ⛔⛔ **THE RULE FIRED AGAIN — #1049, recurrence n=3 → n=4.** Merged 10:27:40Z; CodeRabbit posted
  **2 actionable inline findings at 10:32:38–10:32:42Z**, ~5 minutes post-merge. **Both are LIVE and
  untriaged in main, and both sit in `_cmd_planning_lane.py` — the file PLAN-101 just changed.**
  - 🟠 **MAJOR — the shipped doc claims a mechanism the code does not implement.** The bullets say a
    missing `change_type` deep-biases "per the DQ1 signal set", but `evaluate_signals_pure` computes
    `s3_deep = change_type in _DEEP_CHANGE_TYPES and not narrow_and_concrete`, and `None` is not in
    `_DEEP_CHANGE_TYPES`. ⭐ **The fix for the epic's theme reproduced the epic's theme.**
    ⛔ **Interacts with the IN-FLIGHT PLAN-112**: stale `change_type` (PLAN-112's subject) and unset
    `change_type` (this finding) **both fail toward the NARROWER posture** — the direction that drops
    sonar-roundtrip, automatic-review and the security audit. **PLAN-112 D2 must treat `None`
    explicitly and D1 must read this finding.**
  - 🟡 Minor — the title filter drops **every** `# Request…` heading though the docstring says the
    host title is "the ONLY line removed". Doc-contract divergence in the seam the plan rewrote.
- ⛔⛔ **THE RULE FIRED — #1042, recurrence n=2 → n=3.** The mandatory post-merge revisit caught a
  live finding on its first real application. Timeline: operator posts `@coderabbitai review`
  04:47:51Z → CodeRabbit **acknowledges** 04:47:59Z (an ack, NOT a review) → **PR merged 04:50:10Z**
  → CodeRabbit posts the **actual review** *"Actionable comments posted: 1"* at **05:01:17Z**, ~11
  minutes POST-MERGE. **The plan merged on an acknowledgement.** ⚠ It reported this honestly
  (`head_sha_verified: false`, and it declined to read the ack as a review) — **the gap is
  structural, not a reporting failure.**
  **LIVE UNTRIAGED FINDING IN MAIN**: `_self_review_detectors.py:1454`, 🟠 Minor / Functional
  Correctness — `_DEF_OR_CLASS_HEADER` accepts indented functions but `_DEF_NAME` matches only
  `def`, so **a nested closure is treated as an unnamed header and closes the outer block**,
  splitting the outer function's body and its scan-loop shape. ⭐ **It sits in the block-parsing
  helper of the unreachable-guard detector PLAN-81 just shipped** — a defect in the detector built
  to catch defects. ⇒ **PLAN-102 owns the sweep**; this is its second confirmed population member
  alongside the five #1036 findings.
- ✅ **Post-merge revisit performed for the #1040 landing — CLEAN, and the sibling scan is a genuine
  negative.** #1040 merged 20:17:29Z, latest comment 20:16:20Z. Siblings #1039 / #1038 / #1037 all
  clean too. **The late-arrival recurrence stays at n=2 (#1026, #1036) and did NOT grow.** ⚠ The
  #1038 margin was **88 seconds** — the window is narrow, not absent.
- ⭐ **CONFIRMED 2026-07-28 (#1034) — Sourcery has at least TWO refusal phrasings and #1021 covers
  only one.** PLAN-80 / #1021 built its recognizer on *"your pull request is larger than the review
  limit of"*. The #1034 refusal is a **different mode** — a weekly diff-character quota:
  *"you have reached your weekly rate limit of 500000 diff characters"*. `automatic-review` folded
  that **detected** refusal into `completeness: complete: true` via `no_check_name`.
  **This is evidence, not a hypothesis, that the credit PLAN-92 gives #1021 is overstated — PLAN-92
  D1 owes the re-verify.** Third consecutive PR (#1024, #1032, #1034) with an unrecognized refusal.
  ⚠ PLAN-92 is IN FLIGHT, so this needs an operator paste to reach it.
- **Our own triage replies are returned as stored comments** — the same shape as PLAN-92 defect 6
  (author filter not filtering), which under `pre_merge_comment_barrier` `fail_into_loopback` is an
  infinite loop.
- **`git worktree remove` timed out mid-removal again (#1034, third sighting)**, leaving 4 tracked
  files deleted, then refusing with *"contains modified or untracked files"*. Recovered with
  `git checkout --` and **no `--force`**. That answers the open question about which recovery the
  standard should mandate: the non-force path works.
- **An empty corpus may read as a clean one.** `.plan/local/archived-plans/` is empty; the corpus
  lives at `.plan/temp/dormated-plans/`. Treat any zero-finding corpus run as UNVERIFIED until the
  path is confirmed.
- **The lane-router under-route is live, n=4.** The path counter cannot tell a TARGET from a
  CITATION and requires a directory separator — but that changes the scope *label*, not the *route*;
  `surgical` and `single_module` are both narrow. There is **no operator-facing lane surface at all**:
  un-prompted plans are contract-correct, and a prompted one is an undocumented improvisation.
  ⚠ Do not "fix" this by documenting that prompt as a step.
- **Unlabelled mechanism claims in deliverable PROSE escape the Verify-First Contract.** Re-check at
  each spec authoring.
- **Semantically-incoherent auto-merge across two plans sharing one config surface** — textually
  clean, silently deletes a knob. No gate covers it; mitigation is procedural.

### Archetype counters — re-check at every landing

- **Flagship: confident-signal-hides-a-caveat — n=8** (+1 on 2026-08-02: `sync-defaults` returning
  `success, added_count: 1` over a write a later same-stage save reverted → PLAN-TRUTH-043). Open
  instances: the false-fresh `kind=build` row (PLAN-TRUTH-010 producer / PLAN-82 consumer) **and** the
  unguarded config write.
- **Vacuous guard — n=7** (+1 on 2026-08-02: ArchUnit's `no…` form inverting condition-event polarity so
  a hand-written `violated()` condition reports nothing → PLAN-TRUTH-042; **a mode distinct from the
  round-6 `allowEmptyShould(true)` one, on the same skill**). Plus the inert thinking-directive family
  at **n=5** → PLAN-TRUTH-002.
- **Defending-documentation / vacuous authority — n=6** (+1 on 2026-08-02: `order_config_keys`'s
  docstring asserting it is the single ordering authority routed through by both write paths, when five
  write sites exist and ≥3 bypass it → PLAN-TRUTH-043). ⭐ **In the file that implements the guarantee.**
- **Producerless contract row — n=3** (`dispatch_boundaries`; declared-but-never-emitted
  `display_detail`; a step declaring a required prompt-body field the generic dispatcher cannot carry).
  → PLAN-TRUTH-012, PLAN-TRUTH-040.
- ⭐ **Accidental-redundancy-caught-it — NEW 2026-08-02, n=1.** The config revert was found only because
  **two freshness oracles disagreed** (`marshal_status: stale` vs `executor_action: fresh`). **Had they
  agreed — the normal case — it ships.** ⛔ Whenever a defect was caught by two reports disagreeing,
  ask what the designed check was; if there wasn't one, that absence is the finding.
- **Volume-read-as-coverage — n=3 surfaces.** → PLAN-81, PLAN-78.
- **Correct-verdict-wrong-evidence — n=4.** A right conclusion resting on a mechanism that does not
  hold.
- **A report is a LEAD — and a confident provenance header ("verified, first-party") is itself an
  unverified claim.** Caught twice at inbox drains; one supplied inventory had a quoted docstring
  that does not exist in the file.
- **A reviewer's list of call sites is a SAMPLE, not an enumeration.** Every set-guarding detector
  must be population-derived — copy `test/_shared/_dispatch_roster.py`.
- **Test-pins-the-defect.** A test written from observed behaviour rather than the contract.
- **Diff-scoped-sweep-misses-the-tree.** Re-check on any rename plan (PLAN-TRUTH-015, PLAN-57's rename half).
- **Verify-before-implement (BINDING).** Every serialized inference is labelled OBSERVED or
  HYPOTHESIS with a named confirm/refute artifact, marked verify-at-outline.
- **UNOWNED-INFRA (harness, not our code)** — dispatch instability, tool-grant nondeterminism,
  harness timeout-floor bound ordering. Detect and document; do not fix.
