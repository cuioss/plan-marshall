# Epic: Automated PR review apparatus reliability

slug: review-apparatus

> Ledger document for one epic under `.plan/local/orchestrator/review-apparatus/`. The layout and
> authority contract live in the central standard — see
> `persona-marshall-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Cloud bridge

Plans from this epic may be executed in the standalone cloud lane instead of the plan-marshall
lifecycle. The mapping between this epic's plan specs and those cloud plans, and the rule for
creating, syncing, and collecting them, are in [`cloud-bridge.md`](cloud-bridge.md).

Read it before staging work for the cloud and before ingesting a landed cloud plan.

## Vision

The cuioss org runs three automated PR reviewers — CodeRabbit, Sourcery, and PR-Agent
(`cuioss-review-bot`, Gemini on Vertex) — with PR-Agent designated the PRIMARY reviewer on
reliability grounds. This epic owns whether that apparatus actually produces a trustworthy review
signal, end to end: the org-side reviewer configuration and event subscriptions, the trigger and
await machinery in plan-marshall, the participation taxonomy and its classifier, and the pre-merge
barrier that consumes the verdict.

It is too large for one plan because it spans three repositories under different release cadences
(`plan-marshall`, `cuioss/pr-agent-settings`, `cuioss-organization`) and because its defects recur:
the same "a confident signal that hides a caveat" shape has now surfaced in the classifier, in two
detectors, and in the barrier, each time found by hand from an operator paste rather than by any
standing check.

**Done** looks like: a merge candidate's review state is reported truthfully without a human
disproving it; a required bot that reviewed an earlier HEAD is re-triggered rather than mislabelled;
a bot that refuses does not deadlock the barrier; and the org-side configuration that causes staleness
is fixed at the source rather than only described more honestly downstream.

## START HERE

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: === 2026-09-18 CLEANUP + RESTART PREP DONE. HEAD has MOVED to 7242b33ef (was 7a028157e) — every stamped verdict is checked_at 7a028157e and is now STALE: reported, never promoted. restart_verdict READY (5/5 scored, sampled 2026-09-18T08:51:08Z, inbox 0 queued / 341 archived). R = 0 of N = 2. ===
NEXT ACTION ON RESTART: (a) PLAN-PR-066 remains the ONE emitted plan awaiting operator-confirmed launch (13 deliverables incl. D11 rename + D12 settings-repo docs rewrite); (b) run `next` for the SECOND slot — it is usable for the first time: overlap rows fell 5545 -> 2 and only 066/069 (cuioss-review-bot.md) and 067/068 (github_pr read vs write) collide; PLAN-PR-075 is disjoint from everything; (c) ⛔ do NOT emit a parked PLAN-PR-056..064 — they are pointer chains now, not work.
⭐ THE SLOT MATH (re-derived 2026-09-18 after the component re-cut): N = 2, R = 0. 10 staged component plans + PLAN-PR-066. Every deliverable body still lives in a RETIRED source spec — a successor points at the parked theme spec, which points at the original. ⛔ Never retype a body; follow the chain. ORCHESTRATOR HOUSEKEEPING now owns 7 ex-deliverables that reach no repository diff (epic.md Open Defects) — do them in a cleanup pass, not a plan.
⛔⛔ THE PLUGIN PIN IS SPLIT AGAIN (2026-09-18, double-sampled): executor MARSHALL_VERSION 0.1.1677 vs registry installPath 0.1.1670 on 18/18 entries; sole unmarked dir is 0.1.1670 on 10/10 bundles. GATE executor == installPath FAILS. ⛔ REPAIR IS OPERATOR-ONLY — the classifier refused even a dry run (Self-Modification). Scripts are staged OUTSIDE the session scratchpad at ~/.claude/plugin-pin-repair/: run `! python3 ~/.claude/plugin-pin-repair/repair_1_markers.py --apply` (markers FIRST), then `! python3 ~/.claude/plugin-pin-repair/repair_2_registry.py --apply`, then a FULL RESTART — /reload-plugins does NOT re-seat skill bodies. ⚠ Re-read both versions before running: the executor regenerates on any /plan-marshall preflight, so TARGET in both scripts may need updating.
⛔⛔ HIGHEST-RISK OPEN ITEM, unchanged: THE SHIPPED MARKER GATE IS UNEXERCISED AND FAILS CLOSED. `recent_review_start` is ABSENT from CodeRabbit live summary comments, and `_is_participation_evidence` gates content with a BARE substring test over the whole body (any occurrence anywhere satisfies it — quoted PR text included). A verdict comment that does not match resolves a clean review `absent`, which BLOCKS A MERGE. CodeRabbit raised it twice (b131a3, c847ec), both taken_into_account, never disputed. ⛔ The decline was CORRECT — do not anchor against an unsampled layout. SAMPLE FIRST: PLAN-PR-058 D0 owns it and must publish the sampled population with its size.
⭐⭐ THE PACK SYSTEM, VERIFIED FIRST-PARTY 2026-09-14 — do not re-derive: generation is DETERMINISTIC AND NEEDS NO LLM (harvests `## Enforcement` bullets per domain, MAX_DOMAIN_RULES=12, MAX_CATEGORY_BULLETS=10), fires automatically on every push to main touching marketplace/bundles/** or marketplace/targets/**, and REPLACES packs/ wholesale. 8 artifacts, 12534 bytes total on pr-agent-settings main. ⛔ SMALL PACKS ARE A MEASUREMENT OF THE SOURCE SKILLS, NOT A GENERATOR DEFECT — operator confirmed correct and OUT OF SCOPE. ⛔⛔ THE CONSUMER SIDE DOES NOT EXIST: cuioss-organization reusable-pr-agent-review.yml v0.27.0 references NEITHER project.yml NOR packs/ (grep count 0), so this repo pr-agent block is INERT CONFIGURATION. That is exactly what PLAN-PR-066 builds.
⭐ PLAN-PR-066 OPERATOR RULINGS, settled at staging 2026-09-14 — do not re-litigate: an `enabled` flag in .github/project.yml with ABSENT = DISABLED (shaped like the existing sonar.enabled key); ⛔ disabled means THE CHARTER IT HAS TODAY, never NO CHARTER — the flag governs pack ASSEMBLY only; the spine stays unselectable. Rollout is opt-in per repo over a DERIVED population, never a sweep.
⛔ THE QUEUE CANNOT EXPRESS `retired` — VALID_STATUS_VOCABULARY is {staged, launched, running, parked, shipped, landed}; 20 superseded specs are recorded `parked`, which is SAFE (next walks staged only) but NOT TRUE. Real status lives in each spec header, the epic.md redistribution table, and decision.log. Filed to truthful-signals as review-apparatus-036.md.
⛔ FOUR CONSECUTIVE LANDINGS DIVERGED DECLARED-vs-REALIZED, and #1491 diverged in BOTH directions (19 declared / 13 realized, not nested; 4 declared-but-never-touched). ⭐ Over-declaration is the worse half for the gate: it sequences siblings behind files nothing ever claims. `reconcile-scope` detects the drift and NOTHING IN FINALIZE CALLS IT — unowned.
⛔ #1491 MERGED ON A RECORDED REVIEW BYPASS (operator decision, empty rosters + skip-bot-review). `0 comments found` means NOBODY LOOKED — never read it as evidence of quality. That conflation is what PLAN-PR-061 exists to end.
PHASE A 2026-09-15: `corpus enumerate` 68/68 BOTH directions, 0 rows_without_spec, 0 specs_without_row, 0 unreadable. Tally 34 shipped / 20 parked / 10 staged / 4 retired = 68. A1 BY DERIVATION: 218 paths moved since 77cb2e251 and ZERO were deleted or renamed, so no staged spec can have been invalidated by a retired path — the discriminator is the RETIRED-path set, not the moved count. A2 nothing retired (no positive account). A3 nothing to apply: blocking_count 0 over 389 claims, 68/68 claim sections parsed, 0 unreadable; the 3 prose specs are named and deliberate. A4 no duplication action. A5 redistribution DECLINED — applied in full 2026-09-12, and PLAN-PR-066 absorbed PLAN-PR-039 on 2026-09-14.
PHASE B: the 2026-09-13 dated block was relocated VERBATIM to settled.md; nothing dropped, still-live items carried forward here. compact regenerated the derivable blocks; invariants re-checked after a pointer correction (see below); unreachable_count 0.
⛔ A POINTER DEFECT I INTRODUCED AND THE INVARIANT CAUGHT: the first version of this anchor named the relocation heading in an ABBREVIATED form with an ellipsis, which matches no heading in settled.md, and `relocated_pointer_reachable` came back VIOLATED over 10 pointers. ⭐ Cite a relocation heading EXACTLY and in full — an abbreviated pointer is an unreachable one.
PHASE C `archive_drain: refused` — the PERMANENT documented default. No EPIC-WIDE quiescence signal exists; closed_senders is per-sender only and the sender population is open. ⛔ Never derive quiescence from a timer or a merge landing.
⚠ INBOX IS AN ACTIVE CHANNEL: 26 messages drained across the last three sessions from five distinct senders (plan-pr-046, pr-065, truthful-signals, plan-truth-139, next-level). An empty queue is the EMPTY zero, never `finished` — no sender has filed a stream-end.
✅ TIER WATCH CLOSED 2026-09-15 (operator): premise refuted — already hybrid (CodeRabbit + Sourcery Tier 1, pr-agent Tier 2, finalize self-review). CodeRabbit stays REQUIRED until pr-agent reaches similar quality, measured by review-practice.md § 1; corpus pass findings/2026-09-15-pr-agent-vs-coderabbit-vs-sourcery.md says NOT met (152/156 guides canned, paired recall 4/123). Next corpus pass lower bound: 2026-09-15T09:50:16Z.
⛔ NEW 2026-09-18 (drain): inbox emptied — post-run-quality-001 forwarded four reviewer-quality lessons, ALL FOUR already absorbed in the same-day lessons pass (drain record on PLAN-PR-072, no new deliverable; the bot_states persisted-carrier seam it names IS 072 D2 consumed by 071 D1); truthful-signals-059 staged as PLAN-PR-076 D4 (the EXTERNAL loop re-found its own remediation residue in 2 of 3 rounds on #1501) with its two cheap rules written into review-practice.md § 10. Still open from 2026-09-15: review-practice.md § 1 gating table is STALE (says CodeRabbit optional); the architecture search --content .github blind spot is unfiled; PLAN-PR-066 D12 carries the settings-repo docs REWRITE that PLAN-PR-065 falsely recorded as done.
⛔ STILL OWED: TokenSheriff permanently merge-blocked (required_bots names the retired pr-agent kind); two ADR proposals await confirmation (79a483); the deploy-target/R4 divergence is DECIDED (skill adopts the executor invocation, filed as review-apparatus-039.md) and needs the ./pw population DERIVED rather than the single site fixed.

> ↪ This pass relocated one anchor block to `settled.md` § "Relocated resume-anchor blocks (2026-09-15 cleanup, operator-confirmed)"
>   — 35 blocks are now relocated in total; the 2026-09-13 and 2026-09-04 passes each have their own section in that file, listed in its header.
>   ⛔ Read them before re-deriving anything about 2026-09-04/08/13 — they carry the refutations.

⛔ STANDING RULES AND DO-NOT-RE-DERIVE NOTES — kept INLINE verbatim below, deliberately NOT relocated:
=== ⛔⛔ OPERATOR-CONFIRMED 2026-08-25: N = 1 STANDS. DO NOT DO PAIRING ANALYSIS. ===
Intra-epic parallel-run review is RETIRED. No overlap matrices, no disjointness comparisons between two staged specs of this epic, do NOT re-derive the must-not-run-concurrently bullets. At N = 1 the disjointness test is satisfied BY CONSTRUCTION whenever R = 0. A FULL SLOT IS STEADY STATE, NEVER A SHORTFALL TO FIX.
⚠ SUPERSEDED IN PART 2026-09-08: the knob is now N = 2 (metadata parallelization_scope), so pairing IS derived again — but only from the parser (corpus surfaces + corpus cross-check), never by hand-built overlap matrices. The three classes below still bind.
⭐ THREE CLASSES SURVIVE - full reading key in epic.md section Sequencing constraints:
  A. ORDERING BINDS: PR-024 before PR-025 - PR-024 before PR-031 - PR-030 before PR-031 - PR-038 before PR-039/066 - PR-064 (ex-028) after PR-033 (landed).
  B. OWNERSHIP BINDS: 030 G7 claimed by BOTH PR-025 D3 and PR-027 D5. A spec-correctness defect. SETTLE IT before either is emitted.
  C. CROSS-EPIC IS THE ONLY LIVE COLLISION QUESTION: N = 2 is EPIC-LOCAL. Three orchestrators still put concurrent plans in the repo. manage-status list + source_id before every emit REMAINS MANDATORY.
⛔ THE TRAP: C is easy to lose while retiring D, because both are worded as collisions. Discriminator = WHOSE LEDGER the other plan lives in.
✅ ADJACENCY WATCH RETIRED as UNRESOLVABLE under this configuration, not answered (n=2, no negative control). Reopen before the first pairing if the knob is ever raised.

=== ⭐⭐ PLAN-PR-038 + PLAN-PR-039 ARCHITECTURE - SETTLED WITH THE OPERATOR, do NOT re-litigate ===
- Packs are GENERATED, never hand-written, derived from the skill tree (discover_domains keys on *-security / arch-gate-* / ext-triage-*). Seven derive today plus the spine; all eight land in pr-agent-settings packs/.
- They become PUBLISHED ARTIFACTS in cuioss/pr-agent-settings - NOT fetched from plan-marshall at review time, which would make 21 repos depend on a product repo and invert the dependency direction.
- Selection + per-project additions declared in .github/project.yml: packs: plus additional_rules:, which is APPEND-ONLY. ⛔ security is NOT a selectable pack - it is a 10-topic spine folded into every pack and a project must never deselect it. That is WHY additional_rules cannot replace.
- Read from the DEFAULT BRANCH ONLY - reading the PR head would let an author change the rules reviewing their own PR. Precedent: repo_context_from_default_branch = true.
- Any read/fetch/compose failure FAILS THE REVIEW LOUDLY. No silent fallback to a bare charter.
- The composed charter is ECHOED INTO THE RUN LOG - the audit surface for the free-text channel.
- ⛔ maven is DEFERRED as a RECORDED PRECONDITION by explicit operator decision (maven is to be modularized anyway). Ship the seven derivable domains, add NO authored-pack mechanism.
⛔ SEQUENCING: PLAN-PR-038 → consumer fan-out → PLAN-PR-066 (ex-039). 066 landing first fails every review in 21 repos. ⭐ ITS PRECONDITION IS NOW DISCHARGED: packs/ exists on pr-agent-settings main since #64 / PLAN-PR-065.
⚠ TWO LOAD-BEARING HYPOTHESES marked verify-at-outline, still UNEXECUTED: that the dotted-env form generalises from VERTEXAI.* / github_action_config.* to PR_REVIEWER.EXTRA_INSTRUCTIONS (if refuted, PLAN-PR-066 D3 re-scopes and D1/D2 are worthless without it - SETTLE IT EARLY), and that an injected env value OUTRANKS a repo-local .pr_agent.toml.

=== STANDING (carried) ===
READ cloud-wave-audit.md BEFORE TOUCHING ANY STAGED PLAN - coverage matrix, overlap map, the now-TEN pre-emit amendments (6 applied at this emit, so NINE remain), the 14 standing rules.
⛔ PLAN-PR-029 D2 must absorb 070 G1 third requirement - as written its Done-when CERTIFIES a permanently-unresolved thread. Carried by PLAN-PR-059.
⛔ Once PR-032 lands (it HAS, #1416), DROP PLAN-PR-031 D5 items 1-3 and PLAN-PR-026 D6 lane item — now carried by PLAN-PR-060 D9 and PLAN-PR-061 respectively. CHECK THEM OFF AT EMIT, not at outline.
EVERY PRE-041 VERDICT IS STALE (f6d058b4b/77c9dc70a). Reported, never promoted - not a refutation.
POST-MERGE REVISITS OWED: 1077, 1078, 1080, 1087, 1118, 1130 plus foreign 14, 237, 202, 643. 1334 and 1344 done. ⚠ 1338 has 7 unresolved threads on the merged PR. The 13 wave PRs got post-run verifications - do NOT re-queue.
PLAN-PR-002 PARKED: cuioss-organization#235 OPEN - corroborate against the FOREIGN PR.
⛔ wrong_case tautology still live in main: marshall-steward/scripts/determine_mode.py:580-582.
⛔ A pre-existing macOS test defect is OPERATOR-ASSIGNED to a separate plan: test_qgate_closure.py::test_a_declared_glob_escaping_the_repo_is_unmeasured_not_empty asserts == Path(/etc) against a path resolving to /private/etc. Also a pollution-guard teardown flake in test_comments_stage.py under xdist.
⚠ The build wrapper reported status: timeout on a run that COMPLETED (17877 passed in 467s). Read the LOG layer, never the outer status.
ENVIRONMENT: epic tree GITIGNORED, LOCAL-ONLY - restart safe, machine loss is not. Nothing unpushed.
**Phase**: orchestrating
**Inbox (derived)**: 0 queued, 342 archived
**Parked**:
- PLAN-PR-002 (WS-02) — plan=org-empty-review-guard-too-broad — PR cuioss-organization#235 — landing=landings/PLAN-PR-002.md
- PLAN-PR-043 (WS-01)
- PLAN-PR-045 (WS-01)
- PLAN-PR-029 (WS-03)
- PLAN-PR-030 (WS-03)
- PLAN-PR-026 (WS-03)
- PLAN-PR-035 (WS-03)
- PLAN-PR-031 (WS-03)
- PLAN-PR-037 (WS-03)
- PLAN-PR-039 (WS-02)
- PLAN-PR-040 (WS-03)
- PLAN-PR-047 (WS-03)
- PLAN-PR-048 (WS-01)
- PLAN-PR-049 (WS-03)
- PLAN-PR-050 (WS-03)
- PLAN-PR-051 (WS-03)
- PLAN-PR-052 (WS-01)
- PLAN-PR-053 (WS-01)
- PLAN-PR-054 (WS-04)
- PLAN-PR-055 (WS-04)
- PLAN-PR-056 (WS-01)
- PLAN-PR-057 (WS-01)
- PLAN-PR-058 (WS-01)
- PLAN-PR-059 (WS-03)
- PLAN-PR-060 (WS-03)
- PLAN-PR-061 (WS-03)
- PLAN-PR-062 (WS-03)
- PLAN-PR-063 (WS-03)
- PLAN-PR-064 (WS-04)
**Queue** (staged, in order):
1. PLAN-PR-066 (WS-02)
2. PLAN-PR-067 (WS-03)
3. PLAN-PR-068 (WS-03)
4. PLAN-PR-069 (WS-01)
5. PLAN-PR-070 (WS-01)
6. PLAN-PR-071 (WS-03)
7. PLAN-PR-072 (WS-03)
8. PLAN-PR-073 (WS-04)
9. PLAN-PR-074 (WS-04)
10. PLAN-PR-075 (WS-04)
11. PLAN-PR-076 (WS-03)
<!-- END GENERATED: resume-summary -->

## Ordered Queue

⛔ **Mirrored from `status.json` `plans[]` — the ARRAY order IS the queue order.** Id numbering carries
no ordering authority. When this table and `status.json` disagree, **`status.json` wins** and this table
is reconciled from it, never the reverse.

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-PR-002 | WS-02 | parked | .github/workflows/reusable-pr-agent-review.yml |
| 2 | PLAN-PR-043 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md; marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md; marketplace/bundles/plan-marshall/skills/manage-locks/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py; test/plan-marshall/automatic-review/; test/plan-marshall/manage-locks/; test/plan-marshall/workflow-integration-github/ |
| 3 | PLAN-PR-045 | WS-01 | parked | .github/workflows/; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md; marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; test/plan-marshall/automatic-review/; test/plan-marshall/workflow-integration-github/test_github_pr.py |
| 4 | PLAN-PR-029 | WS-03 | parked | ../cloud-runs/100-coderabbit-ai-agent-block-strip-vs-extract/report-01.md; marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md; marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md; marketplace/bundles/plan-marshall/skills/untrusted-ingestion/standards/threat-model.md; marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/standards/comment-patterns.json; marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/standards/comment-patterns.json; marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py; marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/standards/sonar-rules.json; marketplace/bundles/plan-marshall/skills/workflow-pr-doctor/standards/automated-review-lifecycle.md; test/plan-marshall/manage-findings/test_findings_store_resolve.py; test/plan-marshall/workflow-integration-github/test_github_pr.py; test/plan-marshall/workflow-integration-gitlab/test_gitlab_pr.py; test/plan-marshall/workflow-integration-sonar/test_fetch_findings.py |
| 5 | PLAN-PR-030 | WS-03 | parked | ../cloud-runs/090-feed-pr-findings-back-into-local-review/report-01.md; .claude/skills/finalize-step-plugin-doctor/SKILL.md; .claude/skills/finalize-step-review-retrospective/SKILL.md; build.py; marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_gate_delta.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/sonar-roundtrip.md; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py; marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_patterns.py; test/plan-marshall/automatic-review/test_bot_participation_contract.py; test/plan-marshall/automatic-review/test_counting_rule_parity.py; test/plan-marshall/automatic-review/test_review_gate_delta.py; test/plan-marshall/build-pyproject/test_gate_coverage.py; test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review.py |
| 6 | PLAN-PR-026 | WS-03 | parked | .claude/skills/finalize-step-review-retrospective/SKILL.md; .claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py; marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; test/plan-marshall/automatic-review/; test/plan-marshall/finalize-step-review-retrospective/ |
| 7 | PLAN-PR-035 | WS-03 | parked | marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py; marketplace/bundles/plan-marshall/skills/workflow-pr-doctor/standards/automated-review-lifecycle.md; test/plan-marshall/workflow-integration-github/test_github_pr.py |
| 8 | PLAN-PR-031 | WS-03 | parked | marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; test/plan-marshall/automatic-review/test_structural_refusal.py; test/plan-marshall/workflow-integration-github/test_github_pr.py |
| 9 | PLAN-PR-037 | WS-03 | parked | .claude/skills/finalize-step-review-retrospective/SKILL.md; .claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md; test/plan-marshall/finalize-step-review-retrospective/test_review_retrospective.py; test/plan-marshall/manage-findings/test_findings_store_resolve.py |
| 10 | PLAN-PR-039 | WS-02 | parked | (prose) |
| 11 | PLAN-PR-040 | WS-03 | parked | marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; test/plan-marshall/workflow-integration-github/test_github_pr.py |
| 12 | PLAN-PR-047 | WS-03 | parked | .claude/skills/finalize-step-review-retrospective/SKILL.md; .claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_gate_delta.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; test/plan-marshall/automatic-review/; test/plan-marshall/finalize-step-review-retrospective/ |
| 13 | PLAN-PR-048 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; test/plan-marshall/automatic-review/; test/plan-marshall/phase-6-finalize/ |
| 14 | PLAN-PR-049 | WS-03 | parked | marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_patterns.py; test/plan-marshall/manage-findings/; test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review.py |
| 15 | PLAN-PR-050 | WS-03 | parked | marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; marketplace/bundles/plan-marshall/skills/manage-logging/standards/log-format.md; marketplace/bundles/plan-marshall/skills/manage-metrics/; marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py; marketplace/bundles/plan-marshall/skills/manage-status/standards/status-lifecycle.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/post-run-review.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/; test/plan-marshall/manage-findings/; test/plan-marshall/manage-logging/; test/plan-marshall/manage-status/ |
| 16 | PLAN-PR-051 | WS-03 | parked | marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; test/plan-marshall/automatic-review/test_review_completeness.py; test/plan-marshall/phase-6-finalize/ |
| 17 | PLAN-PR-052 | WS-01 | parked | .claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py; marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py; test/plan-marshall/automatic-review/; test/plan-marshall/workflow-integration-github/ |
| 18 | PLAN-PR-053 | WS-01 | parked | .claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-merge-barrier.md; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py; test/plan-marshall/automatic-review/; test/plan-marshall/manage-findings/; test/plan-marshall/workflow-integration-github/ |
| 19 | PLAN-PR-054 | WS-04 | parked | marketplace/bundles/plan-marshall/skills/manage-metrics/; marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md; marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py; marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/leaf-command-reference.md; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py; test/plan-marshall/manage-solution-outline/test_survey_scope_declaration.py; test/plan-marshall/phase-6-finalize/test_foreign_pr_gate.py |
| 20 | PLAN-PR-055 | WS-04 | parked | .claude/skills/finalize-step-review-retrospective/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-metrics/; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pr_intent_section.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md; test/plan-marshall/phase-6-finalize/test_dispatch_roster_closure.py; test/plan-marshall/phase-6-finalize/test_pr_intent_section.py; test/plan-marshall/plan-orchestrator/; test/plan-marshall/plan-orchestrator/test_landing_completeness.py |
| 21 | PLAN-PR-056 | WS-01 | parked | .github/workflows/; marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md; marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md; marketplace/bundles/plan-marshall/skills/manage-locks/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py; test/plan-marshall/automatic-review/; test/plan-marshall/manage-locks/; test/plan-marshall/workflow-integration-github/ |
| 22 | PLAN-PR-057 | WS-01 | parked | .claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py; marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py; test/plan-marshall/automatic-review/; test/plan-marshall/phase-6-finalize/; test/plan-marshall/workflow-integration-github/ |
| 23 | PLAN-PR-058 | WS-01 | parked | .claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py; marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-merge-barrier.md; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py; test/plan-marshall/automatic-review/; test/plan-marshall/manage-findings/; test/plan-marshall/phase-6-finalize/; test/plan-marshall/workflow-integration-github/ |
| 24 | PLAN-PR-059 | WS-03 | parked | marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md; marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md; marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md; marketplace/bundles/plan-marshall/skills/untrusted-ingestion/standards/threat-model.md; marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/standards/comment-patterns.json; marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/standards/comment-patterns.json; marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py; marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/standards/sonar-rules.json; marketplace/bundles/plan-marshall/skills/workflow-pr-doctor/standards/automated-review-lifecycle.md; test/plan-marshall/manage-findings/test_findings_store_resolve.py; test/plan-marshall/workflow-integration-github/test_github_ops_pr_comments.py; test/plan-marshall/workflow-integration-github/test_github_pr.py; test/plan-marshall/workflow-integration-gitlab/test_gitlab_pr.py; test/plan-marshall/workflow-integration-sonar/test_fetch_findings.py |
| 25 | PLAN-PR-060 | WS-03 | parked | .claude/skills/cloud-plan-lane/SKILL.md; .plan/; marketplace/bundles/; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py; marketplace/bundles/plan-marshall/skills/workflow-pr-doctor/standards/automated-review-lifecycle.md; test/plan-marshall/automatic-review/test_structural_refusal.py; test/plan-marshall/workflow-integration-github/test_github_pr.py |
| 26 | PLAN-PR-061 | WS-03 | parked | .claude/skills/finalize-step-review-retrospective/SKILL.md; .claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py; marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_gate_delta.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; test/plan-marshall/automatic-review/; test/plan-marshall/finalize-step-review-retrospective/ |
| 27 | PLAN-PR-062 | WS-03 | parked | .claude/skills/finalize-step-plugin-doctor/SKILL.md; .claude/skills/finalize-step-review-retrospective/SKILL.md; build.py; marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_gate_delta.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-self-review-surfacing.md; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/ci-verify.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/sonar-roundtrip.md; marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_gate_coverage.py; marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_detectors.py; marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/scripts/_self_review_patterns.py; test/plan-marshall/automatic-review/test_bot_participation_contract.py; test/plan-marshall/automatic-review/test_counting_rule_parity.py; test/plan-marshall/automatic-review/test_review_gate_delta.py; test/plan-marshall/build-pyproject/test_gate_coverage.py; test/plan-marshall/manage-findings/; test/pm-plugin-development/ext-self-review-plan-marshall/test_self_review.py |
| 28 | PLAN-PR-063 | WS-03 | parked | .claude/skills/finalize-step-review-retrospective/SKILL.md; .claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md; marketplace/bundles/plan-marshall/skills/manage-logging/standards/log-format.md; marketplace/bundles/plan-marshall/skills/manage-metrics/; marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py; marketplace/bundles/plan-marshall/skills/manage-status/standards/status-lifecycle.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/post-run-review.md; marketplace/bundles/plan-marshall/skills/plan-retrospective/; test/plan-marshall/finalize-step-review-retrospective/test_review_retrospective.py; test/plan-marshall/manage-findings/; test/plan-marshall/manage-findings/test_findings_store_resolve.py; test/plan-marshall/manage-logging/; test/plan-marshall/manage-status/ |
| 29 | PLAN-PR-064 | WS-04 | parked | .claude/skills/finalize-step-review-retrospective/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-metrics/; marketplace/bundles/plan-marshall/skills/manage-solution-outline/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pr_intent_section.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md; marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py; marketplace/bundles/plan-marshall/skills/tools-integration-ci/standards/leaf-command-reference.md; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py; test/plan-marshall/manage-solution-outline/test_survey_scope_declaration.py; test/plan-marshall/phase-6-finalize/test_dispatch_roster_closure.py; test/plan-marshall/phase-6-finalize/test_foreign_pr_gate.py; test/plan-marshall/phase-6-finalize/test_pr_intent_section.py; test/plan-marshall/plan-orchestrator/ |
| 30 | PLAN-PR-066 | WS-02 | staged | .claude/skills/cloud-plan-lane/SKILL.md; .github/project.yml; .github/workflows/pr-agent-packs-publish.yml; .github/workflows/pr-agent.yml; doc/developer/marketplace-build.adoc; marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md; marketplace/bundles/plan-marshall/skills/marshall-steward/references/landing-cycle.md; marketplace/targets/README.md; marketplace/targets/__init__.py; marketplace/targets/component_targets.py; marketplace/targets/generate.py; marketplace/targets/pr_agent/; test/default/test_workflow_lint.py; test/marketplace/targets/pr_agent/; test/marketplace/targets/test_component_targets.py; test/marketplace/targets/test_generate_cli.py; test/pm-plugin-development/plugin-doctor/test_analyze_target_scope.py |
| 31 | PLAN-PR-067 | WS-03 | staged | marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_ops.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/standards/comment-patterns.json; test/plan-marshall/workflow-integration-github/test_github_ops_pr_comments.py; test/plan-marshall/workflow-integration-github/test_github_pr.py |
| 32 | PLAN-PR-068 | WS-03 | staged | marketplace/bundles/plan-marshall/skills/workflow-integration-github/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-gitlab/scripts/gitlab_pr.py; marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/SKILL.md; marketplace/bundles/plan-marshall/skills/workflow-integration-sonar/scripts/sonar.py; test/plan-marshall/workflow-integration-github/test_github_pr.py |
| 33 | PLAN-PR-069 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py; marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md; marketplace/bundles/plan-marshall/skills/automatic-review/standards/sourcery.md; marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md; marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py; test/plan-marshall/automatic-review/test_bot_registry_markers.py; test/plan-marshall/automatic-review/test_bot_registry_patterns.py; test/plan-marshall/automatic-review/test_structural_refusal_cap.py; test/plan-marshall/automatic-review/test_structural_refusal_diff.py; test/plan-marshall/manage-locks/ |
| 34 | PLAN-PR-070 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md; marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py; marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_re_review.py; test/plan-marshall/automatic-review/test_participation_site_population_guards.py; test/plan-marshall/automatic-review/test_review_completeness_cli.py; test/plan-marshall/automatic-review/test_review_completeness_evidence.py; test/plan-marshall/automatic-review/test_review_completeness_state.py; test/plan-marshall/automatic-review/test_review_completeness_verdicts.py; test/plan-marshall/automatic-review/test_unknown_bot_kind_escalation.py |
| 35 | PLAN-PR-071 | WS-03 | staged | marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_gate_delta.py; test/plan-marshall/automatic-review/test_counting_rule_parity.py; test/plan-marshall/automatic-review/test_review_gate_delta_cli.py; test/plan-marshall/automatic-review/test_review_gate_delta_escapes.py; test/plan-marshall/automatic-review/test_review_gate_delta_exclusions.py; test/plan-marshall/automatic-review/test_review_gate_delta_shares.py |
| 36 | PLAN-PR-072 | WS-03 | staged | marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py; marketplace/bundles/plan-marshall/skills/manage-findings/standards/jsonl-format.md; test/plan-marshall/manage-findings/ |
| 37 | PLAN-PR-073 | WS-04 | staged | marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/pr_intent_section.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/create-pr.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md; test/plan-marshall/phase-6-finalize/test_pr_intent_section.py; test/plan-marshall/plan-orchestrator/ |
| 38 | PLAN-PR-074 | WS-04 | staged | marketplace/bundles/plan-marshall/skills/manage-solution-outline/scripts/manage-solution-outline.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/ci_verify.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/foreign_pr_gate.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/review_commitments.py; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/archive-plan.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/post-run-review.md; marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-merge-barrier.md; test/plan-marshall/phase-6-finalize/test_foreign_pr_gate_cli.py; test/plan-marshall/phase-6-finalize/test_foreign_pr_gate_gate.py; test/plan-marshall/phase-6-finalize/test_review_commitments_commitments.py; test/plan-marshall/phase-6-finalize/test_review_commitments_reporting.py |
| 39 | PLAN-PR-075 | WS-04 | staged | marketplace/bundles/plan-marshall/skills/manage-logging/standards/log-format.md; marketplace/bundles/plan-marshall/skills/manage-metrics/; marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py; marketplace/bundles/plan-marshall/skills/manage-status/standards/status-lifecycle.md; test/plan-marshall/manage-status/ |
| 40 | PLAN-PR-076 | WS-03 | staged | .claude/skills/finalize-step-review-retrospective/SKILL.md; .claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py; test/plan-marshall/finalize-step-review-retrospective/ |
<!-- END GENERATED: ordered-queue -->

### Queue annotations

**2026-09-05 — PLAN-PR-032 landed (#1416); two staged proposals are now DISCHARGED.** PR-032's own
Dependencies section stated the consequence in advance: *"Once this plan lands, drop PLAN-PR-031 D5
items 1-3 and PLAN-PR-026 D6's lane item — they become discharged, and leaving them staged re-opens
the proposal-only loop this plan exists to close."*

- **PLAN-PR-031 D5 items 1–3** — discharged. Their subject was a *proposal* against
  `.claude/skills/cloud-plan-lane/SKILL.md` that PR-031 was forbidden to apply. PR-032 applied it.
- **PLAN-PR-026 D6's lane item** — discharged, same reason.

⛔ **Neither spec file is edited to remove them here.** Both are staged, not running, so the drop is a
scoping decision their own outline phase must apply — recorded at the queue rather than silently
deleted from a spec, so the audit record of *why* they were dropped survives. A launch of either
plan reads this annotation first.

**2026-09-05 — PLAN-PR-049 and PLAN-PR-050 staged** from the PLAN-PR-032 drain (6 candidate-lesson
messages, 3 into each). Both are `declarative` at 8 and 9 resolved path entries respectively, so both
admit a disjointness check. ⛔ **PLAN-PR-049 overlaps PLAN-PR-030** on `pre-submission-self-review.md`,
`pre-push-quality-gate.md`, `_self_review_patterns.py` and `ext-self-review-plan-marshall/SKILL.md` —
**sequence, never pair.** PR-049 and PR-050 are disjoint from each other and may pair.

**2026-09-05 — PLAN-PR-043 D6 gained Limb C** (the rate-window knob is scoped to `required_bots`, so
it cannot await the bot that actually reviews). Expected Surface unchanged — every path Limb C names
was already declared for D5/D6, verified from `corpus surfaces` (14 entries before and after), not
assumed from the edit.

**2026-09-05 — PLAN-PR-048 gained D3a** as a sub-deliverable of D3, deliberately NOT a sixth
top-level deliverable: the spec stays at 5 and the scope-bloat guard is not tripped. D3a carries a
LEAD, not a finding — a foreign Sourcery refusal-misclassification filing that must be **fetched
before it is folded**, with the existing two-shape dedup warning attached.

**2026-09-18 — inbox `truthful-signals-060.md` FOLDED into `PLAN-PR-043` D6 as Limb D** (the body
lives there; `PLAN-PR-069` D3/D4 carry it forward via the `Carried from` pointer chain — see
`PLAN-PR-069`'s own note that every deliverable body lives at its original source spec). Forwarded
from `truthful-signals`, relayed from API-Sheriff's PLAN-26 drain (PR `cuioss/API-Sheriff#314`,
squash `a475cff`); an uncorroborated lead, recorded as such. Of the message's three named mechanics
and one config consequence: (1) the hourly included-review budget and (2) the pause-then-trigger
requirement are corroborating restatements of D6 Limb A and D7's already-recorded rules
("never trigger inside a closed window … wait for FULL expiry → then trigger"); (3) "a *Review
finished* comment is not a verdict" restates the `matched` vs `head_sha_verified` discrimination
`branch-cleanup-rereview.md` already ships, and the currency-blind disposition `PLAN-PR-070` D5/D6
owns; the config consequence — `re_review_await_timeout_seconds` (default 600s, in
`branch-cleanup-rereview.md`) is a second, independently-scoped instance of Limb A's
flat-timeout-inside-the-hourly-window defect — is the one genuinely new fact, and it is recorded as
a corroborating population fact on Limb A's existing "Done when" rather than as a new deliverable.
⛔ **Expected Surface unchanged, on both `PLAN-PR-043` and `PLAN-PR-069`**: `branch-cleanup-rereview.md`
and `github_re_review.py` are declared by `PLAN-PR-070`, not either of these — the fold adds no file
surface here, by design (see the fold text itself for the discharge argument).


Per-row narrative the generator cannot derive. Outside the markers on purpose — a compaction pass
preserves this zone verbatim.

- ⭐⭐⭐ **PLAN-PR-042 IS THE EPIC'S HIGHEST-PRIORITY SPEC — operator-set 2026-08-30. Emit it FIRST
  once a slot frees.** *The required reviewer returns an empty list on a correct, full review.*
  It sits at the head of the staged queue for that reason, ahead of PLAN-PR-025B.
  ⛔ **It is an INVESTIGATION, not a fix** — the cause is unknown and the plan's deliverable is
  evidence plus a decision. Its D0/D1 are a controlled A/B; do not pre-commit to a remedy.
  ⛔ **FIVE hypotheses are ALREADY REFUTED first-party and must NOT be re-investigated**: the model
  ladder (3.7-flash was used, no fallback), diff clipping (full diff, 203k of 256k tokens), charter
  absence (fully applied and maximally permissive), trigger failure (it ran and published), and
  diff-size correlation (hit rate 0%/0%/11%/6%/0% across ascending size buckets — the two hits are
  *not* the smallest PRs). The plan begins after all five.
  ⛔ **This is never "drop pr-agent"** — one of its two findings is a security defect CodeRabbit did
  not file (cui-http #162). D2 arm (c) coordinates with PLAN-PR-025B D7, which promotes CodeRabbit.
  ⚠ D3 depends on the PLAN-PR-037 fold; D0–D2 do not.
- ⭐ **PLAN-PR-037 absorbed a second defect 2026-08-30 (new D4)**: `_is_actionable` buckets
  `issue_comment` → meta unconditionally while `review_body` gets a registry-driven per-reviewer
  test, so **pr-agent's `actionable_count` is structurally 0**. ⛔ Consequence beyond wrong counts:
  **every pre-2026-08-30 `actionable_count: 0` for pr-agent is uninformative** — zero by
  construction, not by measurement. Do not cite one as evidence. ⚠ PR-037 still collides with a live
  plan on `_findings_core.py`, so this was a FOLD, not an emit.
- ⛔⛔ **PLAN-PR-025 IS RETIRED AND SUPERSEDED (2026-08-29) — the mandatory split is DONE.** Do not
  re-split it and do not emit it. Its row rides the live queue only because `retired` is not terminal.
  **Amend the successors, never it.**
  - **PLAN-PR-025A** (D0–D6, *the record*) — **EMITTED 2026-08-29**, awaiting operator-confirmed launch.
    It inherited 025's first-staged queue position.
  - **PLAN-PR-025B** (D7–D9, *the recovery*) — **BLOCKED until 025A LANDS.** The dependency is
    load-bearing, not bookkeeping: 025B's recovery branches on the refusal `cause` **before**
    `rate_limit_class`, and 025A's **D1** is what emits that `cause` on both producers. They also share
    `bot_registry.py`, `automatic-review/SKILL.md` and `coderabbit.md`. ⛔ Never concurrent.
- **PLAN-PR-025A keeps all seven of D0–D6 as ONE plan — a recorded decision, not an oversight.** The
  (a) D0+D1+D2 / (b) D3+D4 / (c) D5+D6 subdivision survives as an *internal ordering obligation*,
  because D1–D5 all consume D0's three derived populations: three plans would either re-derive the same
  populations three times — the exact hand-maintained-population defect the plan exists to close — or
  couple two sub-plans to a third's run report. D0 is a **gate**, so the six work deliverables sit *at*
  the guard, not over it.
- **PLAN-PR-027 is the recommended first emit, as its half (a) (D1+D2+D5) only.** D1 is the epic's
  stated blocker, it is D0-independent, cheap, and it unblocks every dispatched leaf that composes a
  `ci` invocation. ⛔ Correct its D0 HALT scope first — as written a D0 failure destroys D1.
  ⚠ **SUPERSEDED — PR-027 SHIPPED as #1356.** Kept for the reasoning only; it is no longer a candidate.
- **PLAN-PR-028 is BLOCKED at the prep-ready gate on purpose** (`corpus verdicts` → `blocking_count: 1`).
  Verdict `contradicted`, `rescoped: no`. It must be re-authored, not emitted. Its *premise* survives
  plan 080's refutation — re-verified at HEAD; do not re-refute it.
  ⚠ **SUPERSEDED 2026-08-25** — PR-028 was re-authored, the verdict rescoped, and the corpus now reports
  `blocking_count: 0`. It is no longer blocked at the gate; it IS still blocked by a live-plan collision
  (`manage-solution-outline.py`, `_orchestrator_inbox.py`) and by its own mandatory 540a/540b split.
- **PLAN-PR-032 is free to run now** — nothing else in the epic may touch `cloud-plan-lane/SKILL.md`.
- **PLAN-PR-033 is operator-gated by construction**: its D0 is an `AskUserQuestion`, not an edit.
- PLAN-PR-018 and PLAN-PR-004 are retired; PLAN-PR-002 is parked on an open foreign PR
  (`cuioss-organization#235`). All three ride the live queue because they are not terminal.

### Sequencing constraints (the only ones that bind)

⭐ Derived from the 2026-08-23 re-grounding, against `e8324d241`. The pre-wave constraints this section
carried named only plans that have since shipped; they are in [`settled.md`](settled.md) via the
relocated narrative and no longer bind.

#### ⛔⛔ READING KEY — OPERATOR-CONFIRMED 2026-08-25: `N = 1` STANDS, so DO NOT DO PAIRING ANALYSIS

**The operator has confirmed `parallelization_scope` stays at `1`. Intra-epic pairing review is
RETIRED — do not compute overlap matrices, do not run disjointness comparisons between two staged
specs of this epic, and do not re-derive the "must not run concurrently" bullets below.** At `N = 1`
the `next` verb's disjointness admission test is satisfied by construction whenever `R = 0`: there is
no second plan to collide with. Time spent on it is time spent on a question the configuration has
already answered.

⭐ **But three of the four classes below are NOT concurrency claims and survive untouched.** Read each
bullet for its class before discarding it:

| Class | Status at `N = 1` | What it covers |
|---|---|---|
| **A — ORDERING** | ⛔ **BINDS** | "X before Y" — a real dependency in the work, not a pairing question. PR-024 → PR-025 · PR-024 → PR-031 · PR-030 → PR-031 · PR-038 → PR-039 · PR-033 behind PR-028 D4/D5 |
| **B — OWNERSHIP** | ⛔ **BINDS** | `030 G7` claimed by BOTH PR-025 D3 and PR-027 D5. Two specs asserting ownership of one gap is a SPEC-CORRECTNESS defect: run sequentially, the second plan either redoes the work or finds its brief false. Settle it. Nothing to do with concurrency |
| **C — CROSS-EPIC** | ⛔⛔ **BINDS, AND IS THE ONLY LIVE PAIRING QUESTION** | `N = 1` is EPIC-LOCAL. Three orchestrators at `N = 1` still put **three concurrent plans** in the repo, so a sibling epic's launched plan CAN collide with ours. The standing check — `manage-status list` plus each live plan's `source_id` before emitting — is UNAFFECTED and still mandatory |
| **D — INTRA-EPIC PAIRING** | ✅ **RETIRED** | Every "must not run concurrently with" and every "may run concurrently" bullet below. Kept as the record of why the ordering in class A was chosen; not a live question |

⛔ **The one trap:** class C is easy to lose when retiring class D, because both are worded as
collisions. The discriminator is whose ledger the other plan lives in — ours (retired) or a sibling's
(still live). A sibling's plan is invisible to this epic's queue, which is exactly why that check
cannot be dropped along with the intra-epic ones.

- ⛔ **PLAN-PR-024 then PLAN-PR-025, NEVER concurrent.** Three adjacent bullets of ONE list in
  `bot-participation-contract.md` § "Evidence for a bot that edits one comment in place" belong to the
  two plans, inside a single git hunk. PLAN-PR-024 also restructures the participation loop that
  PLAN-PR-025 adds one field to — a small change onto a restructured loop is far cheaper than the
  reverse.
- ⛔ **`github_pr.py` + `test_github_pr.py` are claimed by THREE plans** — PLAN-PR-024, -025, -029
  (and PLAN-PR-034, -035 once staged). Code plus its pinning tests: a harder collision than any
  documentation contention. Serialise all of them.
- ⛔ **The § Consumers contention is THREE-WAY, not two-way.** PLAN-PR-024 and PLAN-PR-025 each ADD a
  row to `bot-participation-contract.md` § Consumers; PLAN-PR-030 REWRITES the `review_gate_delta
  assess` row inside the same table body. Two insertions plus one in-place edit conflict on one hunk.
- ⛔ **A THIRD shared contract surface has no split governing it**:
  `workflow-integration-github/SKILL.md` § `github_pr fetch_findings`, written by PLAN-PR-024 (D3, D4)
  and PLAN-PR-025 (D2, D6). The exported split table covers `bot-participation-contract.md` only.
- ⛔ **PLAN-PR-026 must not run with PLAN-PR-027** (both write inside `automatic-review/SKILL.md`
  § Canonical invocations → `review_completeness — deficit`, and both edit the `branch-cleanup.md`
  barrier block within twenty lines) **nor with PLAN-PR-030**
  (`finalize-step-review-retrospective/SKILL.md`, which NO split governs).
- ⛔ **PLAN-PR-027 must not run with PLAN-PR-028** — `phase-6-finalize/SKILL.md`, `ci_base.py`,
  `_github_pr.py`.
- **PLAN-PR-030 before PLAN-PR-031** — both edit `cloud-runs/090-…/report-01.md`, and PLAN-PR-030's
  contract fixes should land before PLAN-PR-031 appends to the same document.
- **PLAN-PR-024 before PLAN-PR-031** — PLAN-PR-031 D4 cold-READS two sections PLAN-PR-024 rewrites;
  running after is what makes the cold read grade the landed text.
- ✅ **SETTLED 2026-08-25 — `030 G7` belongs to PLAN-PR-027 D5. The collision is WITHDRAWN.**
  Derived from the two `Discharges` lines rather than from prose: **PLAN-PR-025 D3 names `030` G5,
  `030` G8 and `120` G5 and has never named G7**; PLAN-PR-027 D5 names `020-G13, 020-G12, 030-G7,
  030-G10, 060-G4`. Exactly one deliverable in the corpus formally claims the gap, so there was never
  a double claim to arbitrate — the recorded collision was a **surface adjacency** (both edit the
  `review_completeness — check` / `— deficit` blocks in `automatic-review/SKILL.md` § Canonical
  invocations) reported as an ownership question. ⭐ **This is class B in the reading key above, and
  the settlement is why it no longer blocks:** ownership is now unambiguous, so neither spec is held.
  ⚠ **The adjacency survives as a PRESERVATION obligation recorded on PLAN-PR-025 D3** — whichever
  lands second must re-read those two blocks and carry the other's edit forward, because both plans
  legitimately touch the same lines and a silent drop would re-open a closed gap invisibly. Both spec
  files now carry the settlement; nothing was re-scoped and no work moved.
- ⛔⛔ **CROSS-EPIC, and a single ledger cannot see it.** `corpus cross-check` (7 sibling epics, 277
  candidates scanned) found five sibling specs whose surface includes
  `.claude/skills/cloud-plan-lane/SKILL.md`. Two bind PLAN-PR-032:
  **`truthful-signals/PLAN-TRUTH-075` is LAUNCHED** (emitted, not started) on the lane's build gate —
  a live collision; and `code-intelligence-substrate/PLAN-CIS-055` edits §§ Step 7 and Step 8 for
  *different* passages — not a duplicate, but never pair them. ✅ `PLAN-TRUTH-061` (shipped #1112, the
  plan that introduced the disclosure PLAN-PR-032 repairs), `PLAN-TRUTH-063` (shipped) and
  `PLAN-TRUTH-092` (staged) were checked by grep and are non-duplicates.
- ✅ **May run concurrently:** PLAN-PR-032 with anything in THIS epic (sole editor of its file — the
  binding constraint is cross-epic, above); PLAN-PR-028 with PLAN-PR-029 (disjoint files, disjoint
  symbols); PLAN-PR-031 with PLAN-PR-026/-027/-028/-029.
- ⛔⛔ **`parallelization_scope` is 1, and the limit is MACHINE-WIDE, not epic-local.** Three
  orchestrators run concurrently (`review-apparatus`, `truthful-signals`,
  `code-intelligence-substrate`), so one plan per epic is already three concurrent plans in the repo.
  ⇒ **At `N = 1` no pairing decision arises at all**, and every constraint above binds as pure
  ORDERING. They become live pairing questions only if the knob is raised.
- ✅ **ADJACENCY WATCH — RETIRED 2026-08-25 as UNRESOLVABLE UNDER THIS CONFIGURATION, not as answered.**
  Two consecutive pairings (PR-014 + PR-016, then PR-015 + PR-016) were file-level disjoint but both
  inside `automatic-review/`, and neither reported a collision. The operator has confirmed `N = 1`
  stands, so **no further pairing will ever test it** — the watch cannot resolve by observation and
  keeping it open costs a re-read every session for a question nothing will answer.
  ⛔ **It is retired, NOT closed clean.** The record stands that two pairings produced no observed
  collision and that this is n=2 with no negative control — it was never evidence that file-level
  disjointness inside one directory is safe. Should `parallelization_scope` ever be raised, **reopen
  this before the first pairing**, because the question is then live again and still unanswered.

  ⛔⛔ **REOPENED 2026-09-02 — the condition above has been met.** The operator raised
  `parallelization_scope` from `1` to `2` to pair **PLAN-PR-044 ∥ PLAN-PR-038**, so the question is
  live again and the reopening is the retirement clause discharging itself, not a reversal of it.

  ⭐ **This pairing is a materially better test than the two that produced n=2, and the reason is
  worth stating so the next reader does not treat all three as one series.** PR-014 + PR-016 and
  PR-015 + PR-016 were file-level disjoint but both sat inside `automatic-review/` — same directory,
  same mental model, adjacent semantics. PR-044 ∥ PR-038 are disjoint at the *module* level:
  `automatic-review` + `manage-config` + `marshall-steward` against `marketplace/targets/` +
  `.github/` + `.pr_agent.toml`. Nothing is shared, not even a parent directory.

  ⛔ **Which is exactly why a clean result here proves LESS about the original question, not more.**
  The retired watch asked whether *file-level disjointness inside one directory* is safe. This
  pairing does not probe that at all — it is a different, easier case. ⚠ **Do not record a clean
  PR-044 ∥ PR-038 run as n=3 on the adjacency question.** It is n=1 on a new, weaker question
  (cross-module disjointness), and the original still has no negative control.

  **What to record when the pair resolves:** whether either plan hit a rebase conflict or a re-verify
  signal against the other; and whether the DECLARED surfaces held — per the epic's own measured
  residual, about two thirds of files a landing touches were never declared, so an absent collision
  is only as good as the declarations. ⛔ Read the realized footprints, not the specs, before calling
  it clean.

  ⚠ **A confound to record NOW rather than discover later: the cross-epic axis was BLIND at the
  moment of this pairing.** All three live plans from sibling ledgers declare no `affected_files`
  (today's Open Defect), so the check that would catch a *cross-epic* collision could not run. A
  clean result is therefore consistent with "no collision" AND with "a collision the instrument
  could not see". Do not resolve the watch on it.

## Standing Constraints

The rules that bind future work. ⛔ **This section is not a diary** — the chronological narrative lives
in [`decisions-archive.md`](decisions-archive.md), and the full audit trail in `logs/decision.log`.

### Earned by the cloud wave — 2026-08-23

Fourteen rules, each paid for by a measured failure across the thirteen landings. Evidence in
[`cloud-wave-audit.md`](cloud-wave-audit.md) § 3.

1. **A test that drives the library is not a test of the pipeline.** Two plans shipped green with
   explicit discrimination tests, and both surfaces still collapse in production, because each test
   hands the pure function an input the workflow cannot supply. Every *Done when* on a rendering
   surface must exercise the **step's path**.
2. **Before crediting a discrimination fix, sweep for the PRODUCER of its discriminating input.**
   `_grade_comparison` has four grades and no writer of `--reviewed-reviewers` exists anywhere; it is a
   three-valued function in production and four-valued only in its unit tests.
3. **A capability with no caller is not a deliverable.** A § Consumers row says what a command *reads*,
   not who runs it. This epic read one as proof of a caller once already.
4. **"The mechanism exists" is not "the measurement exists".** Two HALT-gated clauses were discharged
   by a proposition adjacent to the one they stated.
5. **A refuted premise is not a clean surface.** After a refutation, re-walk the declared surface; do
   not infer its health from the refutation.
6. **A refutation's trigger and its closure are separately assessable.** A verify-first gate licenses
   closing the PLAN, never closing every DEFECT it named.
7. **A "population-complete" derivation that filters through a hand-listed vocabulary is complete only
   over the vocabulary.** Derive membership *and* vocabulary, or state the hand-list as a hand-list.
8. **An argued mutation is not a measured one.** Two structural falsifiability arguments were measured
   and both were wrong.
9. **A published null result is dated evidence, not a durable fact.** One of this epic's has already
   gone stale in merged main.
10. **A run report can contradict the diff it shipped with.** Read `git show {squash} --name-status`
    before believing any footprint claim.
11. **A late review-fix invalidates the prose that same landing wrote.** Any late fix obligates
    re-deriving every deliverable section that describes the design.
12. **A proposal-only deliverable decays.** A recorded proposal against a live file needs a re-anchor
    step or an owner who can apply it, or it becomes a regression.
13. ⭐⭐ **A run governed by a contract cannot amend that contract — so a gap in it needs an owner
    outside its lane.** Three gaps sat open for twelve days on this alone. **Ingesting a plan from
    `doc/plans/` into this ledger dissolves the prohibition**, because a `/plan-marshall` run is not a
    lane run. Check for this whenever a staged spec says "recorded as a proposal".
14. **Never trust a count written beside a table.** One report took four consecutive fixes of that
    defect and still landed with two miscounted bundles.

⛔ **And one about this ledger's own tooling:** the eight ingested specs cite gap ids in **four
incompatible notations** (`070-G1`, `` `010` G4 ``, `090/G2`, `090 G1`). A single-form coverage grep
manufactures false orphans — this orchestrator published one and retracted it. Match all four forms.

### Identity and mechanics

- **Plan ids are `PLAN-PR-NNN`**, created and transferred alike; spec files
  `plans/PLAN-PR-NNN-{slug}.md`. ⚠ **The `PR` token must be UPPERCASE** — the `inbox detect` grammar is
  `PLAN-{SLUG}-{DIGITS}` with a 2–8 uppercase-alphanumeric slug; a lowercase variant classifies
  `unrecognised_id` and **silently detaches the plan from this epic**. Digits zero-padded to three.
- `parallelization_scope = 1` (strictly sequential) — the surfaces here mutually overlap.
- **Cross-epic moves go through the inbox, never a direct edit.** An orchestrator's write carve-out is
  its own tree only.
- ⛔ **Provenance ids are NEVER rewritten.** Sibling ids moved (`PLAN-113`→`PLAN-TRUTH-001`,
  `PLAN-52`→`PLAN-TRUTH-006`, the returned PLAN-60 build half→`PLAN-TRUTH-019`; `PLAN-115` unchanged,
  being launched). **Only forward-looking pointers carry the new id** — provenance prose, `logs/`, and
  `inbox/archive/` keep the transfer-time ids, because rewriting them would falsify the audit trail.

### Ownership boundaries

- ⭐ **This epic OWNS the automated-PR-review apparatus; `truthful-signals` is a DISPATCHER for the
  theme.** Standing operator instruction: all findings AND landings of PR-related work land here.
- ⛔ **Not ours, do not take**: `PLAN-TRUTH-001` (a sibling recorded its sequencing as a hard
  constraint), `PLAN-TRUTH-006` (a git-mutation defect, not a review defect), `PLAN-TRUTH-019` (the
  returned PLAN-60 build-gate half — **must not be re-absorbed**).
- **A forwarded finding's CODE defects belong to the reporting plan's epic**; only the apparatus half is
  taken here.

### Verification discipline — each rule was earned by breaking it

- ⛔ **Re-derive `inbox list` at the drain top.** A count carried in prose is never authority; a drain
  found a 4th message an anchor denied.
- ⛔ **Re-derive PR state at analysis time.** Two operator reports of "open"/"enqueued" were already
  merged, one by 32 minutes.
- ⛔ **GREP BEFORE ASSERTING AN ABSENCE.** This orchestrator recorded "nothing waits for a reopening
  window" as fact; one `grep` refuted it (`review_rate_window_await` was shipped all along). An asserted
  absence is the higher-risk half of the verify-first contract.
- ⛔ **Verify a flag or command surface against the executor (`--help`), never against a doc — cached or
  not.** Skills load from cache `0.1.1240` while the executor embeds `0.1.1271`, with 32 versions
  coexisting: **what is READ is 31 versions behind what is RUN.**
- ⭐ **A handover summary is a lead; the released SPEC is the artifact.** Accepting PLAN-116 at its
  stated scope would have staged two defects twice — found only by reading the source spec.
- ⭐ **A reported instance is a SAMPLE, never a population.** Two instances of one shape ⇒ derive the
  population, do not stage a second plan.

### ⭐ "pr-agent edits ONE comment in place" breaks a THIRD site — derive on the right question

Confirmed 2026-07-30 on `#1068`. One config fact (`persistent_comment = true`) breaks every site that
assumes a bot posts a **new** comment per review. Three sites known, in one bundle:

| Site | Predicate | Verdict |
|---|---|---|
| `_github_pr.py` § `cmd_pr_wait_for_comments` | unresolved **row count** vs baseline | ⛔ broken — PR-001 |
| `github_pr.py:486` § `_has_update_movement` | `(bot_kind, id)` **then** `updated_at != created_at` | ✅ **correct — the model** |
| `github_pr.py:776` § `cmd_fetch_findings` "Pre-filter 5" | `(bot_kind, comment_id)` **alone** | ⛔ broken — PR-005 |

⛔ **The derivation question is "which sites decide whether a comment represents NEW INFORMATION" — NOT
"which detectors are on the await path."** The `poll_until`-caller seam inherited from a sibling would
have missed two of the three. Corrected in PR-001's D4.

⭐⭐ **`comment_id` alone is not an identity for "have I seen this review" — and it fails in BOTH
directions.** Our own `post_responses` replies carry a **new id every turn**, so dedup cannot fire and a
start-anchored body filter was needed to stop re-ingesting our own replies; pr-agent reuses **one id
forever**, so dedup over-fires and drops real content.

⛔ **Archetype recurrence n≥7 — the widening that caused it was itself a fix.** The in-source comment
records it: dropping an earlier `not thread_id` restriction closed a phantom re-surface loop, and in doing
so pulled thread-less comments (pr-agent's Guide is exactly that) into a dedup that cannot see an edit.

⚠ **It is COUNTED but MISLABELLED, not uncounted** — `skipped_duplicate += 1` fires, and a reader of that
counter concludes correct dedup. Useful: the counter is an existing observable a regression can assert on.

### ⛔⛔ `#1066` — this epic's own record was WRONG, and the true defect is worse

Recorded here (from a sibling, twice) as *"landed with one-bot coverage; CodeRabbit's awaitable refusal
was never waited out."* **Refuted 2026-07-30** by running the check the standing rule already required
and which *no one had run*: `ci pr comments --pr-number 1066`.

| Claim | Verified reality |
|---|---|
| CodeRabbit never reviewed | ⛔ **False** — 8 comments, incl. a **Major**; 3 inline at **11:58:43Z** |
| Merged one-bot-deep | ⛔ **False** — merged **12:06:46Z**, 8 minutes *after* the review |
| The `SUCCESS` check flip may be an auto-resolve | ⛔ **No** — it reflected a genuine review |
| — | ⭐ **All 8 comments are UNRESOLVED. A Major finding merged unaddressed.** |

⇒ **Two corrections follow, both already applied to the specs:**

1. **The arming decision has ONE measured instance (`#1067`), not two.** ⛔ Do not count `#1066` toward
   the "third instance re-surfaces it early" trigger.
2. ⭐ **The real defect is sharper than the reported one.** The `11/11 checks pass` aggregate was
   *factually correct* — CodeRabbit's check WAS success because it genuinely reviewed. **The error was in
   what "success" was taken to mean**: a check reports that the bot **RAN**, never that its **OUTPUT was
   HANDLED**. Owned by `PLAN-PR-014` D4 (representation) and `PLAN-PR-013` (freshness — a review that
   arrives between the last fetch and the merge is invisible, with **no HEAD change** to detect it).

⚠ **The lesson about the lesson**: this epic recorded a sibling's unverified claim, repeated it into an
anchor and a spec, and only caught it because a later message said *"that has not been run by anyone."*
**A forwarded claim is a lead however many times it is forwarded** — and a claim repeated across two
messages is still one source.

### Bot gating — CONFIG, and per-repo

`.plan/marshal.json` `plan-marshall:automatic-review`: `required_bots: "pr-agent"`,
`optional_bots: "coderabbit,sourcery"`, `bot_lists_provenance: "answered"`. Operator rationale: for this
repo CodeRabbit is optional; it matters more on API-Sheriff (production code). ⚠ **Gating is per-repo —
never carry this to another repo without reading its config.**

⛔⛔ **"Optional" is a GATING classification, NOT a VALUE one.** On `#1067` the *optional* bot found 5
genuine defects on a diff the *required* bot answered with none. **On the evidence so far the optional
bots' findings have mattered MORE, not less.**

### ⭐⭐ Archetype: "true when written, false when read"

Four instances on four surfaces in a single day. **Name it rather than re-analysing the fifth.** A
persisted artifact snapshots a still-moving fact, is never re-derived, and reads as current.

⛔ **The remedy is NOT "add an outcome field"** — a correct field beside a false sentence leaves the
false sentence. **Either regenerate, or carry the HEAD the artifact describes** so a consumer can compare
before trusting. The general defence is this epic's standing rule: **re-derive at read time.**

⚠ Instances and their evidence: [`decisions-archive.md`](decisions-archive.md); the remedy is owned by
`PLAN-PR-010` (D0 derives the population, D3b applies it).

## Relocated narrative — see `settled.md`

Eight dated sections were relocated to [`settled.md`](settled.md) on 2026-08-23, verbatim and with
nothing dropped. Each pointer below names its destination heading in the form the
`relocated_pointer_reachable` invariant resolves.

> ↪ Relocated to `settled.md` § "⛔⛔ #1071 opened a latent false-positive on PR-Agent — CODE-VERIFIED 2026-08-01" — the false positive was code-verified and the plan that carried it shipped.

> ↪ Relocated to `settled.md` § "Retained from the PR #1070 drain — assigned, not unowned" — every retained item was assigned to a plan; none is unowned.

> ↪ Relocated to `settled.md` § "⛔⛔ RETIRED FRAMING — 'the merge-queue enqueue does not take' is REFUTED. Do not propagate it." — the framing is retired; the rule it leaves behind is restated in § Standing Constraints.

> ↪ Relocated to `settled.md` § "PLAN-PR-007 landed (#1118) + a live cross-epic duplicate — 2026-08-08, after the queue audit" — PLAN-PR-007 shipped; the duplicate finding is restated in § Standing Constraints.

> ↪ Relocated to `settled.md` § "Queue audit — 2026-08-08 (full reconciliation of all outstanding specs)" — superseded by the 2026-08-23 cloud-wave reconciliation.

> ↪ Relocated to `settled.md` § "Inbox drain — 2026-08-08 (13 messages, queue emptied)" — the drain completed; all 13 messages are archived.

> ↪ Relocated to `settled.md` § "Corpus review + drain — 2026-08-09 (full reconciliation of all outstanding plans)" — superseded by the 2026-08-23 cloud-wave reconciliation.

> ↪ Relocated to `settled.md` § "Inbox drain — 2026-08-09 (second drain, 1 message / 2 items, both folded)" — the drain completed; the message is archived.

⛔ **Two of them carry rules that still bind and are NOT superseded**: the retired merge-queue framing
(do not propagate it) and the cross-epic-duplicate finding (a ledger cannot see a duplicate living in
another ledger). Both are restated in § Standing Constraints, which is where they bind.

## Open Defects

### ⭐⭐⭐ 2026-09-18 — THE COMPONENT RE-CUT: 9 theme specs → 10 component plans

**Why.** The staged specs were cut by SUBJECT and every subject crossed the same components:
`_findings_core.py` was declared by **7 of 9**, `automatic-review/SKILL.md` by 6,
`bot-participation-contract.md` by 6, `review_completeness.py` and `github_pr.py` by 5 each. `corpus
cross-check` reported **5,545** overlap rows. At `parallelization_scope: 2` that meant the second slot
could never be filled, and five plans would each have re-derived the same file in sequence.

**What was done.** Every deliverable of the nine specs was mapped to its primary component and its
actual symbols (101 deliverables + 1 amendment = 102 units, 100% mapped), then moved as a POINTER ROW —
no body was rewritten. The nine specs are `parked` with a SUPERSEDED banner naming their successors, and
are **not deleted**: they remain the pointer chain between a successor's `Carried from` column and the
retired source spec holding each body, and they hold the claim labels the successors do not restate.

| # | New plan | WS | D | Component it owns |
|---|---|---|--:|---|
| 1 | `PLAN-PR-067` the comment pipeline on the way IN | WS-03 | 10 | provider-github READ path + the merge-queue read |
| 2 | `PLAN-PR-068` the response path and what it drops | WS-03 | 5 | provider WRITE path, all three providers |
| 3 | `PLAN-PR-069` refusal recognition and the rate window | WS-01 | 10 | `bot_registry.py` + the bot standards + the window |
| 4 | `PLAN-PR-070` participation and what the gate may credit | WS-01 | 12 | `review_completeness.py`, its states and call surface |
| 5 | `PLAN-PR-071` reviewed-at-all and the numbers | WS-03 | 11 | the handoff + `review_gate_delta.py` |
| 6 | `PLAN-PR-072` the findings store and its dispositions | WS-03 | 5 | `manage-findings` |
| 7 | `PLAN-PR-073` the landing record and the PR body | WS-04 | 5 | `emit-landing`, `pr_intent_section`, the inbox payload |
| 8 | `PLAN-PR-074` the merge gate and the finalize dispatcher | WS-04 | 11 | `phase-6-finalize` gates + the dispatch boundary |
| 9 | `PLAN-PR-075` the telemetry channels of finalize | WS-04 | 4 | `manage-status` / `manage-metrics` / `manage-logging` |
| 10 | `PLAN-PR-076` the retrospective and what it can establish | WS-03 | 4 | `finalize-step-review-retrospective` |

**Result, measured**: overlap rows **5,545 → 2**. The two that remain are intrinsic and already
sequenced — `PLAN-PR-066` renames `cuioss-review-bot.md` while `PLAN-PR-069` edits its patterns, and
`PLAN-PR-067`/`068` are the read and write halves of one module. ⭐ **Every other pair is disjoint**, so
the second slot is usable for the first time; `PLAN-PR-075` is disjoint from everything.

**Deleted as duplicates, not carried**: `PLAN-PR-060` D2 (the four `mark_finding_responded` call sites,
discharged by `PLAN-PR-068` D1) and `PLAN-PR-057` D6 (a Sourcery refusal LEAD whose body is unreachable,
folded into `PLAN-PR-069` D2). The `reviewed_commit_sha` duplicate (`PLAN-PR-056` D4's companion clause
vs `PLAN-PR-058` D3) resolved to one deliverable, `PLAN-PR-070` D5.

**Routed OUT of the epic** (inbox `review-apparatus-043.md` to `truthful-signals`): the self-review
instrument deliverables (`PLAN-PR-062` D5/D8/D9 + the D0 count-prose arm) and the pyprojectx build-gate
half (`PLAN-PR-062` D4 bullets G5/G8/G9/G12). Neither is the PR-review pipeline. ⛔ If that epic declines
them, they are unowned — they were not silently kept.

### ⛔ 2026-09-18 — ORCHESTRATOR HOUSEKEEPING: work that reaches NO repository diff

Seven deliverables were removed from the plan queue because they produce no PR surface. `cloud-runs/` is
git-ignored, so an edit there appears in no commit and survives only on this machine; the remainder are
`AskUserQuestion` records. They are the orchestrator's own work, not a `/plan-marshall` lifecycle:

| Was | Work |
|---|---|
| `PLAN-PR-060` D5/D6/D7 | Correct false symbol/PR/state claims, 8 disputed figures, and plan 060's own unfinished report, across the landed `cloud-runs/` records |
| `PLAN-PR-060` D8 (cold-read items 1-3, 8) | Discharge owed obligations or give each a git-tracked handle — its standards limb went to `PLAN-PR-069` |
| `PLAN-PR-060` D9 | Re-anchor the `cloud-plan-lane` proposals and put them to the operator ⚠ its items 1-3 were already dropped by the standing amendment (#1416 landed) |
| `PLAN-PR-061` D7 | Record three open decisions instead of taking them (one limb was superseded into `PLAN-PR-071` D2) |
| `PLAN-PR-062` D6 | Record the measurement-semantics proposals; correct two restating records |
| `PLAN-PR-064` D6 (proposals) | Three lifecycle proposals — its `manage-metrics` code half went to `PLAN-PR-075` D3 |
| `PLAN-PR-057` D4 | A dispatch PLACEMENT rule (no wall-clock wait in a leaf) — persona surface, not review apparatus |

⚠ **This is a queue, not a dismissal.** `PLAN-PR-060`'s own source spec said its record half *"is ledger
hygiene, not a reviewable change"*; keeping it in a plan meant paying a full lifecycle for a diff that
does not exist. Do it in a cleanup pass.

### ⛔⛔ 2026-09-18 — THE BACK-FEED ROUTE LAPSED, AND THE EPIC DID NOT NOTICE FOR ~400 PRs

Derived during the lessons absorption. `review-practice.md` § 5 requires a finding document at
`findings/PR-{n}.md` per run — that document **is** the detector accumulation list. Every populated one
is from the `#1055`–`#1067` era; `PLAN-PR-012` shipped 2026-08-13 (#1204) and consumed that backlog;
**no `findings/PR-{n}.md` exists for any PR above #1067.** The three later documents in `findings/` are
bot-comparison corpus passes carrying no back-feed column (`back-feed`, `_detect_`, `detector`, "Could
we have found" → 0 hits across all three).

⇒ **The epic kept MEASURING reviewers and stopped BACK-FEEDING them.** The obligation was never
retired; it lapsed silently, which is why three absorbed lessons had no home to land in. The reopening,
the three waiting inputs, and the one admissibility ruling they need are written into
[`review-practice.md`](review-practice.md) § 6. ⚠ Unowned by any staged spec — decide at the next
`next` whether reopening the route is a plan or an orchestrator act.

### ⭐ 2026-09-18 — LESSONS ABSORBED: 41 of 172, and where each landed

A full pass over the global corpus (`.plan/local/lessons-learned/`): **172 active lessons scanned by
title, 52 bodies read (30.2%), 43 judged in-epic, 41 absorbed or retired here, 2 routed out.** The
corpus went **172 → 131**. Every body is archived verbatim at
[`archive/lessons/`](archive/lessons/README.md) with its bucket, destination and per-lesson evidence;
every retirement carries a tombstone naming its verdict (`completely_covered` ×17, `redundant` ×4,
`obsolete` ×3, `superseded` ×17).

| Bucket | n | Disposition |
|---|--:|---|
| COVERED | 17 | already carried by a staged spec, a landing or the practice — removed, covering clause named in the tombstone |
| DUPLICATE | 4 | retired in favour of a named keeper |
| STALE | 3 | claim no longer reproduces at HEAD; each verified against a symbol read first-party |
| CARRY | 17 | incorporated: `PLAN-PR-056` D13, `PLAN-PR-058` D0/D7, `PLAN-PR-061` D13, `PLAN-PR-062` D0/D4/D5/D8, `PLAN-PR-063` D13 + D8, `PLAN-PR-064` D8 + D3, `review-practice.md` §§ 6–9 |
| ROUTED OUT | 2 | `2026-09-13-20-003`, `2026-09-15-06-002` → `truthful-signals` (inbox `review-apparatus-042.md`); left in the global corpus, not archived here |

⚠ **Twelve of the seventeen COVERED removals are covered by a STAGED spec, not a shipped one.** If such
a spec is ever retired without shipping, re-read its covering deliverable in the archive index before
assuming the lesson's defect is closed. ⛔ Three CARRY rows reproduce at HEAD and had **zero** prior
coverage in this epic: `await_fresh_review`'s missing author gate (`PLAN-PR-056` D13), `pr merge-queue`
reporting an attempt as an observation (`PLAN-PR-064` D8), and the `review_commitments` population being
wrong rather than merely empty (`PLAN-PR-062` D4).

### ⭐⭐⭐ 2026-09-08 (drain) — GUARD THE EXTRACTION LIST, NOT ONLY THE DETECTION LIST

This is the **mechanism** behind an item five independent reports had circled without naming, and it
generalises well past CodeRabbit.

A paired detect-then-extract design has **two** lists, and only one is guarded:

| List | Decides | Drift detector |
|---|---|---|
| `refusal_patterns` | **whether** a notice is a refusal | ✅ `refusal_pattern_drift[]` + `unrecognised_refusal[]`, the latter **state-determining** |
| `rate_limit_eta_patterns` | **what value** to pull out of a recognised notice | ⛔ **nothing** |

⇒ A notice that IS recognised as a refusal but whose ETA cannot be extracted **produces no signal
anywhere**: detection succeeded so no drift is reported, and extraction failed silently to `""`.

⭐⭐ **That asymmetry is why the gap survived five reports.** Every reporter saw the empty ETA; none of
them saw a *signal*, because the guarded half was working. Folded to **PLAN-PR-043 D7 limb A**.

### ⛔⛔ NEW 2026-09-08 (drain) — the ETA gap now has a MEASURED COST: ~5 hours against a 21-minute window

Rounds 5, 6 and 7 were each ~1h45m apart under a **90-minute standing wait floor**, and **all three
refused**. Round 7's notice stated its own reset — *"Next included review available in 21 minutes"* —
and a retry timed to that **succeeded immediately**. `refusal_eta` read `""` throughout.

⇒ ⭐ **A PUBLISHED ETA BEATS A CONFIGURED WAIT FLOOR.** The floor is a guess made without the number
the bot is already publishing.

### ⛔⛔ NEW 2026-09-08 (drain) — the trigger RESETS the window, now MEASURED across three PRs

Every trigger fired while the window was still closed **restarted** it rather than being ignored
(PRs #1430 / #1442 / #1443):

| Trigger | Time | New window advertised |
|---|---|---|
| force-push | 13:43:40Z | 50 minutes |
| close-and-reopen | 14:45:25Z | 52 minutes |
| force-push | 16:05:03Z | 40 minutes |

⭐ The 16:05:03Z refusal was an **in-place EDIT re-stamped at the exact second of the push** — so
PLAN-PR-052's mutable-refusal surface **produced the evidence for this finding**. The recovery
succeeded only on: **wait for FULL expiry → then trigger.**

⇒ ⛔ **NEVER TRIGGER INSIDE A CLOSED WINDOW.** This is the operational rule the whole cluster was
circling, and it is compatible with the 2026-09-06 refutation: close+reopen does not RESET a window,
it is simply one of the trigger forms that **EXTENDS** it.

### ⚠ OPEN TENSION 2026-09-08 — free-OSS vs Team, deliberately NOT resolved

`one-format-…-002`'s notice says *"You've used all free OSS reviews for now"*. `truthful-signals-051`
recorded a sender **retracting** a plan-tier explanation after finding `Plan: Team` in its own
persisted envelopes.

⛔ **Both readings are first-party and they concern DIFFERENT runs.** They are recorded side by side
rather than collapsed; **PLAN-PR-043 D0 must establish which tier each observed notice came from**
before any tier-dependent behaviour is written. ⭐ Recording an unresolved tension is cheaper than
inheriting the wrong half of it — which is what the prior two rounds nearly did in both directions.

### ⭐⭐⭐ NEW 2026-09-08 (drain) — the discrimination this epic keeps trying to build ALREADY EXISTS

`review_completeness` **emits `bot_states`** during `automatic-review` — `participated` /
`participated_but_empty` / `participated_stale` / `refused_structural` / `absent`. ⛔ **Nothing
persists them.**

A post-merge step can read only the `pr-comment` findings store, **which by construction holds records
for reviewers that PRODUCED FINDINGS**. ⇒ participated-and-found-nothing, refused-outright, and
never-asked are **all indistinguishable to every post-merge consumer.**

⭐⭐ **This is the substrate under two observations already recorded here** — PLAN-PR-036's
`reviewer_coverage: 0/3` over an empty store, and PLAN-PR-042's *"1 measured, 2 unmeasurable"*.
**Neither was a measurement bug: the states were computed and thrown away.**

⇒ Folded to **PLAN-PR-053 D1a**, which **makes D1 smaller** — persist what already exists rather than
invent a second discrimination beside it. ⛔ Building the second one is how two producers come to
disagree, which is the defect class this epic keeps finding.

### ⛔ NEW 2026-09-08 (drain) — the documentation is the caller, and the call it prescribes is rejected

`review_completeness.py check` rejected `--measured-diff-size ""` with **exit 2, at the pre-merge
review barrier** — the worst place for this gate to refuse. The call was made **exactly as
`branch-cleanup.md` § "Predicate 2" prescribes**: *"the scalar to the empty string … the empty
fallback, never a hard failure."*

⛔ Sharper than the invited-mistake shape PLAN-PR-051 already covers: here **anyone following the
contract produces the rejection.** Folded to **PLAN-PR-051 D1a**, whose done-when requires a test that
EXECUTES the prescribed invocation so doc and script cannot drift apart again.

### ⭐⭐⭐ 2026-09-07 — `head_sha_verified` IS NOW LOCATED, after three sightings as "still unfixed"

This epic recorded the `head_sha_verified` comment-arm defect **three times** as an unfixed cause of
`barrier-ask-override` grants. `truthful-signals-051` item 1 supplies the mechanism, first-party:

`cuioss-review-bot` publishes the commit it reviewed **in the BODY** of its Reviewer Guide comment
(*"Review updated until commit `<sha>`"*) and populates **no structured reviewed-commit field**,
because its participation arrives as an `issue_comment` rather than a review object.
⛔ **`github_re_review.py` calls `_references_head_sha` EXACTLY ONCE — line 571, inside the REVIEW
branch. The `issue_comment` branch (lines 363, 617) never calls it.**

⇒ **`head_sha_verified: true` is UNREACHABLE for that bot** — the correct outcome is not merely
unproven, it cannot be produced. Every override this epic granted on that bot rests on this.

⭐⭐ **The reason it survived three sightings is that the SYMPTOM is DOCUMENTED**:
`workflow-integration-github/SKILL.md:39` records the state as *"`matched_signal: issue_comment` with
`head_sha_verified: false`"*. **A described defect reads as an accepted design to every later reader.**
That is the transferable lesson, and it is worth more than the fix.

Staged as **PLAN-PR-043 D5a** — which converts D5's standing `HYPOTHESIS` about that file into an
`OBSERVED` located cause.

### ⛔⛔⛔ NEW 2026-09-07 (PLAN-PR-025B landing) — the plan shipping the guards reported a review that never happened

The run stated *"CodeRabbit round 4 came back clean"* for `1af15958`. CodeRabbit's last completed
review covered only `d75ded9e`. A **`count_stored: 0`** fetch was read as *reviewed and clean*; a
**fresh `cause=quota` refusal** was dismissed as a stale comment in the same pass. Caught by
`finalize-step-review-retrospective` **after the merge**.

⛔ **The hidden delta contained a Major** — `parse_toon` deleting the first character of a
shallow-indented block-scalar payload, character-level corruption of the shared TOON transport,
**reported by nothing**. Fixed post-merge in #1441.

⇒ The `nobody-reviewed`-vs-`reviewed-clean` collapse at a **third layer** (fetch), on this epic's own
plan, at n≥3. Staged as **PLAN-PR-053 D1**, together with its substrate (D2) because either alone is
sufficient to cause the false-clean call.

### ⭐⭐ NEW 2026-09-07 — a standing PROSE WARNING is now a located PRODUCER defect

This ledger has carried, in prose, *"never run the producer FIND during a refused window — it falsely
stamps `reviewed_commit_sha`."* That was a **workaround for a bug**, and the bug is now located:
the field is **re-stamped at FETCH time**. One comment (`IC_kwDOQ3xasM8AAAABS4ng4A`) appears under
**three** distinct shas, another (`PRRC_kwDOQ3xasM7rTFi6`) under **two**.

⛔ Every consumer reads it as *which commit this review covered*; it is *which commit was HEAD when we
last fetched*. Staged as **PLAN-PR-053 D2**, with **D3 retiring the workaround only once the fix is
proven** — the removal and the proof land together or neither does.

### ⛔⛔ CORRECTION 2026-09-07 — `any_phase_missing_end_time=false` does NOT make a token total settled

That flag attests to phase **end-times** and to nothing else. On this run **three channels went dark
over `6-finalize`** — no accumulator file, no dispatch-boundary file, and `check-dispatch-audit`
classified **16/16 finalize steps `no_evidence`** — while the flag read `false`.

⛔ **This ledger read it the stronger way** in `landings/PLAN-PR-042.md` (*"a real figure, not a
floor"*). **Corrected in place there**, and that run's 8.63 M is a floor for the same reason. Staged
as **PLAN-PR-050 D2a**.

### ⭐⭐ NEW 2026-09-07 — the strongest reviewer-yield data point this epic holds

**CodeRabbit found FOUR Majors across three rounds that five self-review rounds, a clean 37-rule
plugin-doctor gate, and six whole-tree verifies all missed**: cap bypass across PRs; an
`escalate_exhausted` arm with **no correct reachable path**, discarding a paid-for claim; `.strip()`
corrupting bodies in the close-and-reopen path; and the `parse_toon` truncation.

⇒ Direct corroboration of **PLAN-PR-011** (shipped #1239) at a higher yield than the original.
⭐ Item 2 is notable alone: an escalation arm with **no reachable correct path** is the same shape as
PLAN-PR-052's `refusal_structural` finding — **two unreachable escalation arms in the same subsystem,
found independently.** That is a pattern, not two bugs.

### ⛔ RECURRENCE 2026-09-07 — the `pr` fact was stale for the THIRD time

`step.create-pr.pr_number=1431`; the plan's **own close-and-reopen recovery** — the deliverable it was
shipping — replaced it with **#1433**. No step re-recorded the substitution.

Three occurrences, three distinct mechanisms: #1411 → #1416 (review-acquisition churn), the #1419
split (two successors), and now a recovery replacing its own PR. ⛔ **A step that creates a PR and a
recovery that replaces it need a write-back seam; there is none.** Folds onto the existing
`create-pr` producer-gap entry rather than becoming a fourth.

### ⚠ NEW 2026-09-07 — the trigger RE-ARMS the window, which SHARPENS 2026-09-06's refutation

Both findings stand and neither may be dropped for the other. Close + reopen does **not RESET** the
window (the same-instant ETA evidence). **Triggering actively EXTENDS it**: six `@coderabbitai`
triggers over ~12 h and five 90-minute waits produced **no review**; close-and-recreate got a full
review in **under 15 minutes**. ⛔ **Read the limit notice BEFORE triggering.**

⛔⛔ **The free-OSS-vs-Team explanation is REFUTED, not open** — the reporting run checked its own
persisted envelopes: *"all three, on both PRs, record `Plan: Team` with the same `0 remain` footer."*
One sibling sender still carries the plan-tier attribution; flagged at source in
`review-apparatus-035.md`.

### ⛔⛔⛔ NEW 2026-09-06 (PLAN-PR-036 landing) — TWO OF THIS EPIC'S OWN BELIEFS ARE REFUTED

Recorded first because a refuted belief left standing keeps producing the behaviour it justified.

**1. Closing and reopening a PR does NOT push the CodeRabbit window.** Converting the stated ETAs to
absolute instants: #1419's `12:49:31 +38m` and #1428's `13:06:37 +21m` **both resolve to `13:27:3x`**
— the same instant, 6 seconds apart, **spanning a close and a fresh open.** The window is
**ORG-scoped**: any other PR in the org spends the same bucket, and no reset mechanism is needed to
explain a later shift.

⇒ **The five trigger PRs closed during PLAN-PR-032's finalize (#1411–#1415) bought nothing.** Lesson
`2026-09-05-07-008`, which this orchestrator promoted on 2026-09-05, has been **AMENDED IN PLACE**
(not deleted) with the refutation at the top of its body. What survives there is the org-scoped
contention reading; what does not survive is the remedy.

**2. The four review refusals were NOT all quota.** Three were **91–94 minutes apart**, which an
hourly quota cannot explain. `"Review rate limited"` names **two structurally different conditions**:
a quota wall (wait) and `@coderabbitai review` being the **INCREMENTAL verb with no unreviewed
commit** (change the verb — waiting does nothing at any duration).

⭐⭐ **What worked was `@coderabbitai full review`, accepted in 10 SECONDS on the same PR and the same
HEAD.** Staged as **PLAN-PR-052 D1**.

### ⛔⛔⛔ NEW 2026-09-06 (PLAN-PR-036 landing) — an under-declared footprint GATES WHAT A PLAN CAN LEARN

`lessons-consult` **ran, SUCCEEDED, and searched exactly ONE component** (`tools-integration-ci`),
derived from a **9-file declaration against a realized 158-file footprint**.

Lesson `2026-08-27-16-005` carries `component: plan-marshall:phase-6-finalize` and **its proposed
action is verbatim what the operator later redirected the plan to do.** It came from **PR #1356, the
immediately preceding plan**, and was invisible because its component fell outside the shrunken
consult set. **Cost: a six-hour detour.**

⛔ **A successful `lessons-consult` return is indistinguishable from a complete one** — it reports that
it searched, never that it searched everywhere it should have.

⛔⛔ **This is the same under-declaration that produces THIS epic's disjointness-gate residual class.**
We measured roughly two thirds of a landing's touched files never declared, and we carry a live
Open Defect recording that the union-with-spec workaround cost five plans an unnecessary sequencing.
**One defect, two surfaces.** Compounding it, candidate-lesson `-005` reports that
`affected_files_recall` is **EASIER TO PASS the more the declaration under-records** — the metric that
would catch it rewards it.

⇒ Forwarded to `truthful-signals` as `review-apparatus-034.md` items 1 and 2 (the recording and the
consult-set derivation are theirs), **and recorded here** because a fix on their side retires a defect
on ours. ⛔ Not staged here — we do not own `manage-references` or `lessons-consult`.

### ⛔⛔ NEW 2026-09-06 (PLAN-PR-036 landing) — a bot refusal is a MUTABLE surface

#1419's refusal comment originally said *"158 files, 58 over the limit of 100"*. **The same
`issue_comment` was later EDITED IN PLACE** and now carries a rate-limit body describing a
**63-file diff that did not exist when it was posted.**

⇒ Any corpus that reads refusal bodies after the fact reads a surface that **can be rewritten under
it.** ⭐ This is the sharper form of a shape this epic already carries — a re-review editing one
comment in place, invisible in `new_count` — and it extends it: not only can *participation* hide in
an edit, **the recorded reason can be replaced by a different reason for a different diff.**

⛔⛔ **The standing note "THE CORPUS MEASURES A DEAD CONFIG" now has a second form: the corpus may
measure a BODY THAT WAS EDITED AFTER THE EVENT IT DESCRIBES.** Staged as **PLAN-PR-052 D3**.

### ⛔⛔ NEW 2026-09-06 (PLAN-PR-036 landing) — `automatic-review` does not follow a PR split

#1419 was split into #1423 + #1429. The findings filed against #1419 were **not carried across**, the
`pr-comment` store stayed **EMPTY**, and `review-retrospective` returned **`indeterminate` with
`reviewer_coverage: 0/3`** — on a run where CodeRabbit filed **7 findings and 5 were fixed.**

⇒ **The measurement said *no reviewer covered this* about a run that was reviewed and repaired.** The
producer already records `superseded_prs=1419,1428`, so the input to follow the split exists and is
simply not consumed. Staged as **PLAN-PR-052 D4**.

### ⛔ NEW 2026-09-06 (PLAN-PR-036 landing) — the `pr` fact cannot express a split landing

`landing-facts` carries a single `pr` key; this plan landed as **two merged PRs**. The producer did
the right thing within the schema — it preserved `step.branch-cleanup.pr_part1=1423`, both merge shas,
and `superseded_prs` — but a one-value key **cannot express the landing**, and the queue's own `pr`
row field has the same shape. Stamped here as `1423,1429`, which is a **convention this ledger just
invented**, not something either schema sanctions.

⚠ Related but distinct from the PLAN-PR-032 defect (`create-pr`'s number goes stale when a run
replaces its PR): that one is a **stale** value, this one is a **too-narrow** field. Both reach the
same wrong place from opposite directions.

### ⛔ RECURRENCE 2026-09-06 — the registry pin gap WIDENED, and this finalize's own sync widened it

Cache is now **0.1.1613**; `installed_plugins.json` still pins **0.1.1592** — 21 versions behind.

⭐⭐ **The mechanism is now named, and it is not drift**: `sync-plugin-cache` advances the cache and
regenerates the executor **but never touches the registry**, so **every successful finalize re-opens
the gap by one version.** It is left behind, not drifting — which is why it recurs on roughly every
run rather than occasionally. Finding `73fd9c`.

⛔ **Operator-only repair**: `.plan/temp/repair-plugin-pin.py --target 0.1.1613` (the target is a
VERSION, never a bundle name), followed by a **full restart** — nothing less re-seats skill bodies.

### ⛔ NEW 2026-09-06 (PLAN-PR-036 landing) — four defects found INSIDE guards written to close a completeness gap

A vacuous `assert X == X`, a false universal, an order-dependent classifier, and a reachability-first
test that would accept a forbidden heading. Two caught locally, **two by CodeRabbit**, and **43 % of
CodeRabbit's findings on that PR landed on the coverage claim of the instrument itself.**

⭐ The *vacuous-guard-introduced-by-its-own-fix* archetype at **n ≥ 4 in a single plan** — the densest
single-run instance either epic has recorded. Forwarded (the component is the plan's own test guards,
not the review instruments), and recorded here because the count belongs to the archetype's tally.

### ⛔⛔ NEW 2026-09-05 (PLAN-PR-042 landing, PR #1410) — `bd825d` RECURRED, second confirmed occurrence

After `branch-cleanup` merged and removed the worktree, `metadata.use_worktree` stayed `true` and
`metadata.worktree_path` still named the **deleted** directory, so **every** later phase-entry
assertion refused with `worktree_unresolved` and the finalize **could not be resumed** until it was
hand-repaired with two `manage-status metadata --set` calls.

**Root cause:** `worktree-remove` is **not the symmetric counterpart** of `worktree-create`, which
sets both fields. ⛔ **Not staged in this epic** — `plan-marshall:workflow-integration-git` is outside
the review subject. Forwarded to `truthful-signals` in `review-apparatus-033.md`. Recorded here
because it is the second occurrence and the epic keeps the count.

### ⛔ NEW 2026-09-05 (PLAN-PR-042 landing) — finalize was 72 % of an 8.63 M-token run for a 3-file change

`6-finalize` consumed **6.20 M of 8.63 M tokens** across **4 loop-back iterations** (ceiling 17) and
**32 dispatched step firings**. 28 h 44 m wall / 6 h 31 m worked / 22 h 13 m idle. Billing-weighted
**142.5 M**.

✅ Two things make this figure trustworthy where earlier ones needed caveats:
`any_phase_missing_end_time=false`, so **the total is a real figure and not a floor**; and the run
**converged at iteration 4 of 17** rather than exhausting its budget as PLAN-TRUTH-089 did.

⛔ **Not staged here** — candidate-lesson `-004` states the re-firing bound as its remedy and the
subject is the whole finalize step roster, not the review steps. Forwarded to `truthful-signals`.
⭐ It is the highest-value item in that forward and is named as such.

### ⚠ NEW 2026-09-05 (PLAN-PR-042 landing) — `manage-logging read --phase` appears not to filter

Two reads with different `--phase` values returned the same `total_entries: 396`, and the shorter
result was **exactly the tail of the longer one**. A declared filter that silently no-ops is the
**vacuous-filter** archetype.

⚠ **This one was never emitted as a candidate-lesson at all** — it was observed during
`lessons-capture`, **outside that step's candidate population**, so it exists only in the landing's
Residue and in our forward. ⭐ A defect that falls outside every emitting step's population is
invisible to the whole lesson pipeline by construction; that is worth more than the defect itself.

### ⭐ CLOSED-BY-MEASUREMENT 2026-09-05 — the union-with-spec surface reading has a measured cost

While PLAN-PR-042 ran, `corpus cross-check`'s `live_plan` rows named exactly
`bot-participation-contract.md` and `cuioss-review-bot.md` — **precisely the two production files it
actually touched** (`git show --stat` on `497261525`: those two plus one test file). This
orchestrator treated that as a partial reading and cleared candidates against the **union** of the
live rows and the spec's five declared entries.

**The cost is now measurable.** The union reading correctly serialized `PLAN-PR-025B` (which declares
`test/plan-marshall/automatic-review/`, where the plan did write), but also serialized **`PLAN-PR-026`,
`-030`, `-031`, `-047` and `-048`** behind `review_completeness.py` and `review_retrospective.py` —
**two files this plan never wrote.** Five plans sequenced behind two files that never moved.

⛔ **The rule still stands and is NOT relaxed**: a running plan's live surface can be genuinely partial
because it grows as the plan works, so clearing against the live arm alone remains unsafe. What is
recorded here is that the conservative reading has a **throughput** cost, not a safety one — it lost
five pairings; it admitted no collision. ⭐ **Correctness in the safe direction is still a cost, and
naming it is how the next reader knows the trade was made deliberately.**

### ⛔⛔ NEW 2026-09-05 (PLAN-PR-032 landing, PR #1416) — the landing's own PR fact points at an UNMERGED PR

`step.create-pr.pr_number=1411`. **#1411 closed WITHOUT merging** (`ci pr view` → `state: closed`,
`merge_commit_sha: null`) during the CodeRabbit acquisition; **#1416** is what merged
(`5f810002571fc98f86479527be96c46391d630d3`). `create-pr` never re-fired, so its fact went **stale
rather than wrong-at-write-time**, and there is **no refresh path**.

The landing message handled it correctly on its own side — it carries `pr=#1416` under
`emit-landing`'s derived-figure timing rule and **preserves** `step.create-pr.pr_number=1411`
alongside, with the discrepancy in its Residue. ⛔ **The producer gap is the defect**: the landing
spec sources `pr` from `create-pr`'s fact, which is correct only when the PR that was created is the
PR that merged. `branch-cleanup` **knows** the real number and records it only in prose
`display_detail`, not as a typed fact. A run that replaces its PR mid-finalize — close/reopen as a
review trigger is a **sanctioned technique in this repo** — breaks that sourcing assumption every time.

⭐⭐ **This is the exact case "stamp PR ids from PR state, never from the landing message" exists for.**
The row was stamped `1416` from PR state. Had it been stamped from the step fact, this epic would
carry a merged-plan row pointing at an unmerged PR.

*Remedy shape:* `branch-cleanup` emits the merged PR number as a **typed fact**, and `emit-landing`
sources `pr` from it in preference to `create-pr`'s.

### ⛔⛔ NEW 2026-09-05 (PLAN-PR-032 landing) — `finalize-step-preference-emitter` is STRUCTURALLY unreachable, not merely idle

Four admissible dispositions aggregated into two tuples; the `accepted` tuple **recurred 3 times and
cleared** `preference_min_recurrence=2` — then was dropped by the attribution gate as an unattributed
`default` bucket.

**Cause:** `pr-comment` finding records carry **no `module` and no `component` field at all**, so
module attribution always falls back to `default` and the gate always drops them.

⇒ **For any plan whose dispositioned findings are exclusively `pr-comment` — every doc-only and every
review-driven plan — this step can never promote a pattern at ANY recurrence strength.** ⛔ The
threshold knob is **not** the binding constraint; the missing attribution is. Tuning
`preference_min_recurrence` would be a fix aimed at the wrong mechanism.

### ✅ CORRECTED-AND-CLOSED 2026-09-05 — `2-refine` drift was REAL but did NOT survive the archive

`phases[]` records `2-refine` as `in_progress` while the plan sat at `6-finalize`, and `progress`
reports `completed_phases: 4` where **five** are genuinely complete. The **light planning lane
collapses refine+outline+derive into one envelope and never closes `2-refine`.**

⛔⛔ **THIS ORCHESTRATOR'S CONCLUSION WAS WRONG AND IS RETRACTED HERE.** Inbox message
`apply-the-cloud-plan-lane-contract-amendments-016.md` (a self-correction filed by the same plan)
establishes that the drift **did NOT survive the archive**: the archived record at
`.plan/local/archived-plans/2026-09-05-apply-the-cloud-plan-lane-contract-amendments/status.json`
does not carry it. The first half of the claim was accurate **when written** — the drift was read off
the live `status.json` during `emit-landing` and corroborated by `manage-status progress` returning
`completed_phases: 4` at `6-finalize`. The *conclusion* — that it would ship into the archive — is the
part that was wrong. ⭐ **A defect that self-resolves at archive is not an open defect**, and leaving
this standing would have sent a future plan hunting a condition that no longer exists.

⭐ **The run deliberately did NOT repair it, and that was still the right call** — a hand-write to
`status.json` that close to `archive-plan` risks more than the inaccuracy does, and the accurate
record is that the machinery skipped the phase, not that it completed. Recorded here so the next
reader does not treat a light-lane plan's `completed_phases` as a count.

⛔ Also on the same record: `phase_steps["6-finalize"]` carries BOTH `plan-marshall:plan-retrospective`
(written by the step) and a bare `plan-retrospective` (written by the orchestrator), both `done` with
different `display_detail`. It inflates any count over `phase_steps` and defeats a naive
`len(phase_steps) == len(manifest.steps)` handshake. **Staged as PLAN-PR-050 D4.**

### ⛔ RECURRENCE 2026-09-05 (PLAN-PR-032 landing) — `head_sha_verified` comment arm, THIRD occurrence on this epic

Folds into the existing entry *"⛔⛔ NEW 2026-09-04 (PLAN-PR-038 landing) — `head_sha_verified` is
UNREACHABLE for pr-agent"* below. **Not a second entry — a recurrence recorded on the first.**

PR #1416's merge crossed a review barrier under an explicit `barrier-ask-override` at head
`30b32598457c9d221771392625b770c65853e71f`, gap class `review-barrier-gap`. The grant was given
because `cuioss-review-bot`'s participation read as unproven **solely** through this defect:
`github_re_review.py:394` hard-codes `matched_signal == 'review'`, so the comment arm can never
verify a SHA. The bot's own comment body names the reviewed commit verbatim, which is what the grant
rested on. ⛔ **Still unfixed. Three grants now rest on it.**

### ⚠ RECURRENCE 2026-09-05 (drain of `truthful-signals-046`) — the `bot_kind` rename has no propagation mechanism

Folds into the existing entries *"THE RENAME BROKE TokenSheriff, 1h41m AFTER IT LANDED"* and
*"D5's foreign propagation did NOT happen; its corroboration was false-green"* below. **Recurrence,
not a new entry.**

What `truthful-signals-046` adds, first-party at `c3a1aacbc`: `unregistered_kind` is a member of
`_UNPROVEN_STATES` (`review_completeness.py:310-313`, `:323-335`), and its own comment says so
verbatim — *"Blocking exactly as `absent` is … so the barrier still fails closed."*

⇒ **A consumer repository whose `marshal.json` still carries `bot_kind: pr-agent` is now
MERGE-BLOCKED, not warned.** #1392 made a stale token **detectable**; it did not **migrate** anyone.

- ⛔⛔ **OBSERVED 2026-09-05, and the population was DERIVED rather than sampled** — settled by
  `truthful-signals-047.md`, which walked **every** `.plan/marshal.json` under `~/git/` instead of
  taking the operator's one data-point: **30 repos walked, 9 carrying a `marshal.json`, 0
  unreadable, 2 carrying the retired `pr-agent` token.** Clean: `API-Sheriff`, `cui-http`,
  `cui-jsf-test-basic`, `cui-llm-rules`, `cui-open-rewrite`, `cuioss-parent-pom`, `plan-marshall`.
  ⛔⛔ **THE OPERATOR NAMED ONE; THERE ARE TWO — `nifi-extensions` was not in the report.**
  ⭐⭐ This is the *derive-completeness-never-assert-it* rule paying off: taking the anecdote would
  have left the second repo blocked and unknown. The prior HYPOTHESIS line is retired by this.
- ⭐ **A THIRD independent report** arrived the same day via `truthful-signals-048.md` item 1
  direction 2 (TokenSheriff PLAN-01, PR #713), and it adds the one thing the first two did not:
  *what the failure LOOKS LIKE at the gate.* Their sentence is the one to keep — **"a
  configuration defect wearing the costume of a review outcome."** The quorum can never be
  satisfied, and it presents at the merge gate **as a REVIEW outcome**, as if a reviewer had
  declined or gone silent, while the real reviewer participated normally throughout.
- ⛔ The generalized half is **already owned elsewhere and must not be re-staged here**:
  `truthful-signals/PLAN-TRUTH-132` (*a frozen manifest param has no staleness detector*), whose
  in-repo-rename hypothesis that paste corroborated. What remains ours is the
  **reviewer-config / propagation** side.

### ⚠ NEW 2026-09-05 (PLAN-PR-032 landing) — `CLAUDE.md` was realized but never declared

The merged diff is `.claude/skills/cloud-plan-lane/SKILL.md` **and `CLAUDE.md`** (+4/−4, narrowing
the `.plan/` access carve-out). The spec declared five deliverables (D0–D4) and a three-entry surface;
the run shipped **six** deliverables and touched the repository's highest-traffic contract file
**outside its declaration**.

The added work is sound. The **declaration** is the defect: the disjointness gate could not have
serialized this plan against anything else touching `CLAUDE.md`. This is the under-declaration
residual class, observed live. ⛔ **Not retro-corrected** — the spec is shipped, and a shipped spec's
surface has no consumer (the same rule the 2026-09-04 cleanup applied to 8 stale citations).

### ⛔ NEW 2026-09-05 (this drain) — the emit-time sibling-epic rationale was WRONG ON ITS FACTS

The 2026-09-04 emit cleared PR-032's five sibling-epic overlaps by recording that
`PLAN-TRUTH-061/063/075/081/092` were *"all STAGED in that epic, NOT in flight"*. Read back from
`truthful-signals`' own queue: **061, 063, 075 and 081 are `shipped`; 092 is `retired`.** Only
`PLAN-TRUTH-125` and `-129` are genuinely staged, and those are **PR-042's** overlaps, not PR-032's.

The *conclusion* held — none was in flight, so there was no live collision, and none occurred. ⛔ **The
basis did not, and it must not be reused as precedent.** PR-032's own spec had flagged `PLAN-TRUTH-075`
as **`launched`** at ingestion with a "do not emit without confirming with the operator" caveat; that
caveat was not read at emit time either.

⇒ **A sibling-epic overlap is cleared by READING that epic's queue, never by assuming a status.**

### ✅ 2026-09-04 SECOND DRAIN — 1/1 consumed, staged as PLAN-PR-047; ⛔ ONE SENDER CLAIM REFUTED BEFORE STAGING

`truthful-signals-044.md` arrived at 08:29:22Z, **after** the first drain closed. `messages_scanned: 1`,
`archived: 1`, `invalid: 0`. Disposition **staged** — a `kind: finding` escalated, not absorbed.

**Staged as `PLAN-PR-047` (WS-03, D0–D4)** — *the counting stage reasons from inputs that were never
persisted, and each gap changes a published number*. Declared surface **10 entries, `declarative`,
`admits_disjointness_check: true`, 0 unresolved** (parser-verified). Corpus now **49/49** both directions,
0 `rows_without_spec`, 0 `specs_without_row`, `blocking_count: 0`.

⛔ **NOT folded onto `PLAN-PR-030`** despite the shared measurement subject — PR-030 already carries seven
items (one gate + six deliverables), over the split guard. Nor onto `PLAN-PR-043`, which **this session's
own earlier fold** took to six. Recorded so both omissions read as decisions.

⛔⛔ **One of the sender's four claims was REFUTED before staging, and the spec carries the refutation so
it cannot be re-adopted.** The claim: *"the PR-Agent registry doc states this bot posts no inline comments
at all"*, making an observed `kind=inline` record a contradiction. **At `31d42db87` — the registry version
the source run actually read, predating PR #1386's merge (`71279cc02`, 2026-09-03 17:53:36Z) — the doc
declared BOTH publish shapes**: `issue_comment` unconditional plus `inline` under `/improve`, with the
explicit note *"An absent inline count is therefore NOT evidence of non-participation, while a present one
IS evidence of participation."* ⇒ The observed record is what the registry **predicts and endorses**, and
the sender's drawn consequence (*a counting stage would have concluded this bot found nothing*) is
backwards.

⭐ **The inverted form survives and is what D4 carries**: the Guide `issue_comment` is declared
**unconditional**, yet **zero** `issue_comment` records were observed for `cuioss-review-bot`. An
unconditional shape that did not appear is a genuine mismatch — in the opposite direction.

⭐ **Three claims verified first-party at HEAD `cc5ea40a1` before staging**: `sourcery.md:20-22` (no
`review_body_summary_patterns`; the empty default keeps every `review_body` **COUNTED**), `sourcery.md:51`
(`rate_limit_class: hard_quota`), and `github_re_review.py:394`
(`'head_sha_verified': matched_signal == 'review'`) — the last corroborating both `9f7923` and this epic's
own `e8bde7`.

⛔⛔ **The compounding selection effect is why this is a MEASUREMENT defect, not a coverage gap.**
`finalize-step-simplify` (order 8) and `finalize-step-security-audit` (order 9) mutate source **after** the
gates (5, 7), and a forward pass never re-gates their edits ⇒ **the only measurable PRs are those where
neither step committed anything** — systematically the PRs that needed no fixing. A biased population, not
a random sample. ⛔ **A run of `excluded` rows means those PRs were never measurable. It does NOT mean the
gates were clean.**


### ✅ 2026-09-04 INBOX DRAINED — 20 of 20 consumed, 0 invalid, queue at the EMPTY zero

`messages_scanned: 20`, `messages_archived: 20`, `messages_invalid: 0`, `messages_archive_failed: 0` —
the closure equation holds. Post-drain `live_count: 0`, `closed_senders` **empty**, `invalid_count: 0`
⇒ the **EMPTY** state, ⛔ **NOT finished**: neither sender declared closure, so more messages are expected.

| Disposition | N | What |
|---|:-:|---|
| **promoted** | 15 | lifted to the global lessons corpus as `2026-09-04-08-001` … `-015` |
| **folded** | 3 | into `PLAN-PR-031`, `PLAN-PR-043`, `PLAN-PR-025B` + `PLAN-PR-046` |
| **discarded** | 2 | one dedup, one **refuted** — neither dropped silently |

**The 15 promotions** span `phase-6-finalize` (4), `plan-retrospective` (2), `phase-5-execute` (2),
`ext-self-review-plan-marshall` (2), and one each of `manage-solution-outline`, `manage-change-ledger`,
`persona-module-tester`, `script-shared`, `automatic-review`. ⭐ Two are worth naming: `-005` *reject a
fix-task whose files fall outside its deliverable declared surface* is the **direct remedy for the 12-of-23
scope drift** recorded above, and `-013` *completeness asserted again inside the fix for three
asserted-completeness defects* is the recurring archetype re-firing inside its own repair.

**The 3 folds, and the same-act surface obligation discharged on all of them:**

| Message | → | Surface |
|---|---|---|
| `rpp-015` | `PLAN-PR-031` **D6** — a posted disposition is a promise nothing re-checks against what landed | +3 entries; `claimed_count` **8**, parser-verified |
| `rpp-009` | `PLAN-PR-043` **D6 limb A** — the rate window is a retry policy, not a flat timeout | +3 entries; `claimed_count` **14** |
| `truthful-signals-043` | split 3 ways as its sender intended — item 1 → `PLAN-PR-025B` **D10**, item 2 → `PLAN-PR-046` **D3**, item 3 → `PLAN-PR-043` **D6 limb B** | PR-025B +4, PR-046 +2 (`claimed_count` **11**), PR-043 covered above |

⭐⭐ **`truthful-signals-043` item 2 is `e8bde7` reached from the other side** — an in-place republish read as
`declined` — observed in TokenSheriff and **corroborated first-party** on our own PR #1388. Two independent
observations of one mechanism. ⛔ The foreign PR ids are **LEADS**, not corroborated in this checkout.

⛔ **Two stale-surface corrections made in the same pass**: `PLAN-PR-031` and `PLAN-PR-043` both declared
`standards/pr-agent.md`, **retired by #1392** — corrected to `standards/cuioss-review-bot.md`. A spec
declaring a path that no longer exists is a surface the disjointness gate cannot match.

⚠ **`PLAN-PR-025B`'s surface remains unverifiable from the parser** — it still collapses onto `plan_id`
`PLAN-PR-025` under the known 025-family defect recorded above. The fold's +4 entries were written, but
`corpus surfaces` cannot attribute them. **Pre-existing, not introduced here.**

⛔ **`rpp-016` was DISCARDED AS REFUTED, and the distinction matters**: it reported findings *"die with the
plan directory — there is no carry-out route"*. The store is intact and all 8 hash ids resolved on the first
read. Its *proposal* (a carry-out route) names a real gap; its *premise* (the data is lost) is false, and
recording it as a live signal would have preserved the false half.


### ⭐⭐ RESOLVED 2026-09-04 — THE EIGHT "UNREACHABLE" FINDINGS WERE RECOVERED; THE DATA SURVIVES ARCHIVAL

PLAN-PR-038's landing reported eight findings *"pending in a store that just died with the plan
directory"* with *"no route out of the archive"*. ⛔ **The premise was wrong in the way that matters: the
store did not die.** `.plan/local/archived-plans/2026-09-03-review-packs-become-published-artifacts/artifacts/findings/`
is intact and readable — 13 JSONL files — and **all 8 hash ids resolved on the first read**, every one at
`resolution: pending`, `promoted: false`.

⭐ **The missing thing was a ROUTE, not the data.** Recording that distinction matters: a future run that
believes findings are destroyed by archival will stop looking. They are not. The carry-out is a read.

| Hash | Type / sev | Component | Subject | Routed |
|---|---|---|---|---|
| `e8bde7` | bug / warn | `workflow-integration-github` | `head_sha_verified` can never be true for pr-agent ⇒ the `participated_stale` remedy is unreachable | **stays here** (PR/review) |
| `18f362` | triage / warn | `tools-integration-ci` | CI payload cannot establish WHICH commit was verified — `head_sha` and `elapsed_sec` contradict | → `truthful-signals` `review-apparatus-025.md` |
| `1d5140` | bug / warn | `phase-6-finalize` | `ci_verify` reports `persisted=false` / `persist_skipped_reason=head_sha` while it DID persist | → `-026.md` |
| `1f0c43` | improvement / warn | `manage-architecture` | script startup ~18s cold makes subprocess budgets marginal under `-n auto` | → `-027.md` |
| `5a5761` | improvement / warn | `manage-references` | `affected_files` under-records loop-back work ⇒ every derived finalize step under-scopes | → `-028.md` |
| `c8e4a9` | **bug / ERROR** | `manage-build-server` | a `timeout` verdict kills the daemon job but **orphans the whole pytest tree** | → `-029.md` |
| `d4501c` | improvement / warn | `phase-6-finalize` | `review_commitments reconcile` returns `verdict=clear` over `commitments_considered: 0` | → `-030.md` |
| `79a483` | insight / info | `phase-6-finalize` | **two ADR proposals awaiting operator confirmation** | **operator action** |

Routing follows the three-way rule — PR/review here, everything else not-ours to `truthful-signals`. Six
were filed through the sanctioned `inbox write` channel as `sender_type: orchestrator`, so this is a
**transfer, not an offer**: each is enumerable in that epic's own queue and no longer depends on this
ledger being read.

⭐⭐ **Three of the six independently reproduce archetypes already on record**, which raises their weight:
`c8e4a9` confirms lesson `2026-09-02-21-002` **that housekeeping had just retained as NOT covered**, with
live pids (a killed pytest master left ten xdist workers running); `5a5761` is a **second independent
observation** of the `affected_files` under-recording defect; `d4501c` is the **vacuous-guard archetype**
verbatim — a `clear` verdict over an empty population, the exact thing the standing rule
*"every set-guarding detector must publish its population size"* exists to forbid.

⛔ **`79a483` is why `adr-propose` is `skipped`, not `done`** — Step 5 needs an `AskUserQuestion` per
proposal and a dispatched leaf cannot reach the operator. Two proposals await confirmation: (1) *a published
artifact set is orthogonal — cross-cutting text is emitted exactly once*; (2) *a fan-out CLI parameter is a
request, not a contract*. Decisive decision-log entry `abe291`.

### ⛔⛔ NEW 2026-09-04 (PLAN-PR-038 landing) — 100% COVERAGE OVER A SET THAT EXCLUDES THE WORK

All 5 deliverables reported **100% coverage of their declared paths**, yet **12 of 23 landed files sit
outside every declared surface** — the build-server `--timeout` work landed under a deliverable scoped to
`marketplace/targets/pr_agent`.

⛔ **Recall computed over the DECLARED set can never be lowered by out-of-surface work.** The metric is
not merely imprecise, it is structurally incapable of falling: adding unrelated files leaves it at 100%.
This is the **instrument-reports-perfect archetype**, and it is the literal subject of staged
`PLAN-PR-030-the-instrument-that-measures-our-gates-can-report-them-perfect`. ⚠ It also compounds `5a5761`
above — the declared set is the same `affected_files` union that cannot learn unpredicted paths.

### ⚠ NEW 2026-09-04 — PLAN-PR-038 cost and reviewer measurability

- **4.06M tokens against a 2.5M anchor (1.63×), 86.2M billing-weighted.** `6-finalize` alone was **48%**;
  one **errored dispatch returned nothing for 344K**. ⛔ An `error` is not "produced nothing" — it is
  produced-and-discarded, and it bills.
- **CodeRabbit was the ONLY measurable reviewer** (8 actionable / 8 fixed / 0 rejected). The gate-delta is
  **excluded, not clean**: the loop-back left two reviewed trees, so no single `reviewed_commit_sha` exists.
  ⛔ Do not read the exclusion as a passing comparison.
- ⚠ Two self-corrections from the run, recorded so neither reads as settled: the **merge mutex was NOT held
  through the landing** (it had lapsed, another plan holds it; the queue serialized the merge regardless),
  and **`branch-cleanup` was first marked done without its typed facts**, which `emit-landing` reads
  directly — re-recorded with `merge_state=merged`, `merge_mechanism=merge_queue`.


### ⛔⛔ NEW 2026-09-04 (PLAN-PR-044 landing) — THE RENAME BROKE TokenSheriff, 1h41m AFTER IT LANDED

`PLAN-PR-044` (#1392, merged `cc5ea40a1`) retired `bot_kind: pr-agent` — `standards/pr-agent.md` became
`standards/cuioss-review-bot.md` with `bot_kind: cuioss-review-bot`. The registry kind set is now
`{coderabbit, cuioss-review-bot, sourcery}` and **`pr-agent` is no longer a registered kind.**

| Event | UTC |
|---|---|
| #1392 merges — `pr-agent` stops being a kind | **2026-09-03 22:32:44** |
| TokenSheriff #699 *"correct required_bots"* sets `coderabbit,pr-agent` | **2026-09-04 00:13:27** |

⛔⛔ **TokenSheriff was "corrected" to a token the registry had already stopped recognising 1h41m
earlier**, and is now permanently merge-blocked by exactly the mechanism the plan set out to fix.
⭐ The shipped `unregistered_kind` state is what makes it *diagnosable* rather than silent — the
instrument works; the fleet is what is out of step.

⛔ **The durable generalisation: renaming a `bot_kind` invalidates every consumer configuration in the
fleet, and NO propagation mechanism exists.** Denominator unknown — ~21 org repos, 9 local checkouts,
4 configuring the key. **Unowned by any staged spec.**

### ⛔⛔ NEW 2026-09-04 (PLAN-PR-044 landing) — D5's foreign propagation did NOT happen; its corroboration was false-green

The landing narrative claims *"all three foreign PRs (#249, #192, #693) are MERGED, corroborated at the
foreign PR."* **Those are the original defective sweep PRs**, merged 2026-09-02, before the plan existed —
not its deliverables. Re-derived from the last commit touching each `.plan/marshal.json`:

| Repo | Last `marshal.json` commit | Current value | Changed by the plan? |
|---|---|---|---|
| plan-marshall | `cc5ea40a1` (#1392) | `cuioss-review-bot` | ✅ |
| API-Sheriff | `1f4fc24` (#252, steward sync) | `coderabbit,cuioss-review-bot` | ❌ dates from the sweep |
| cui-http | `c7862d0` (#192, the sweep) | `coderabbit,cuioss-review-bot` | ❌ untouched since |
| TokenSheriff | `6c1bd849` (#699) | `coderabbit,pr-agent` | ❌ and now wrong |

⇒ **One checkout changed, not four.** Two hold the post-rename-correct value **by accident of the
defective sweep**. This is the recorded *"corroborate a foreign landing against the FOREIGN PR"* failure
in its exact form: merged-state read against an already-merged unrelated PR returns green and proves
nothing. ⚠ Open Defect 6 below (the foreign gate that can never pass) is *why* this went unexamined.
**Unowned by any staged spec.**

### ⛔⛔ NEW 2026-09-04 (PLAN-PR-038 landing) — `head_sha_verified` is UNREACHABLE for pr-agent

`PLAN-PR-038` (#1388, merged `ef974632c`) cleared its review barrier by **authorization, not
participation**: `participation_complete: false`, `unproven_bots=[pr-agent, sourcery]`, cleared by a
HEAD-bound `barrier-ask-override` over gap-class `review-barrier-gap` at `0a6fa35f7`.

⭐⭐ **The gap is a DETECTOR gap, not a review gap** (finding `e8bde7`). `head_sha_verified` derives from
the signal **type** — a review object verifies, an `issue_comment` does not — and pr-agent re-reviews by
**editing one issue comment in place**, so it can **never** yield `head_sha_verified: true`. ⇒ A plan with
pr-agent required **cannot clear a `participated_stale` block by the remedy the contract prescribes for
that state.** pr-agent did review that exact HEAD and reported no major issues.

⚠ **All three configured reviewers failed to produce a clearing signal on that PR, each differently**:
pr-agent (detector unreachable), Sourcery (structural size refusal, cap 150000 vs 2963 lines), CodeRabbit
(budget spent, `0 remain`). The override covered **three simultaneous instrument failures**.
**Unowned by any staged spec.**

### ⛔ NEW 2026-09-04 (PLAN-PR-044 landing) — four self-reported defects, all corroborated

1. **The shipped fix does not close its own defect.** `unregistered_kind` fires only for *unregistered*
   tokens; `coderabbit` is a correctly-registered kind sitting in `optional_bots`, so the state never
   applies. A well-named required reviewer in the wrong list still buys `participation_complete: true`
   with zero diff-readers. Lesson `2026-09-03-23-003`.
2. **The durable config fix is owed.** The correction landed in the plan-local manifest only; tracked
   `.plan/marshal.json` still reads `optional_bots: "coderabbit,sourcery"`. `/marshall-steward` is owed or
   every future plan inherits it.
3. **Orchestration context mis-asserted — six lessons mis-routed to the global store** (three reached this
   inbox). Mechanism found and real: the manifest runs `plan-retrospective` (995) **before**
   `lessons-capture` (991) while the verdict is resolved inside the latter — **producer after consumer**.
4. **The pre-archive foreign gate can never pass** (filed `8fe5be`): it classifies the checked-out branch,
   and a merged PR's head is never `main`. Archived on evidence rather than bypass — the right call.


### ⛔⛔ NEW 2026-09-03 (analyze, API-Sheriff paste) — THE THREE-REPO SWEEP IS A REVERT, AND THE BLOCK IT CAUSES IS PERMANENT

Fifth data-point, second on API-Sheriff. It corroborates the fourth-data-point sweep and adds **two
derivations neither the sweep nor the reporting run had**. Both were read first-party; the operator's
relay was the lead, our own git history and our own code are the evidence.

**⭐⭐⭐ (1) THE REMEDY IS A REVERT, AND THE CORRECT VALUE IS PROVEN BY EACH REPO'S OWN HISTORY.**
The reporting run framed the durable fix as a *proposal* — "the durable fix is `coderabbit,pr-agent`;
changing project config is your call". It is not a proposal and it is not a config judgement. Read the
three sweep commits' diffs:

| Repo | Commit | Before | After |
|---|---|---|---|
| TokenSheriff | `05818bc4` (#693) | `coderabbit,pr-agent` | `coderabbit,cuioss-review-bot` |
| API-Sheriff | `1c7308c` (#249) | `coderabbit,pr-agent` | `coderabbit,cuioss-review-bot` |
| cui-http | `c7862d0` (#192) | `coderabbit,pr-agent` | `coderabbit,cuioss-review-bot` |

All three read **exactly `coderabbit,pr-agent`** before the sweep, and all three were changed by a
commit with the identical subject. ⇒ The owed action is a **one-line revert per repo**, and the value
to restore is not inferred, chosen, or designed — it is what each repository already had. This RETIRES
the "your call" framing: nobody has to decide what the required set should be.

**⭐⭐ (2) THE BLOCK IS DETERMINISTIC AND PERMANENT, NOT "IT WOULD HAVE BLOCKED THIS MERGE".**
Derived from OUR code at this HEAD, not from the run's report. In `review_completeness.py`, the quorum
loop builds `classified = list(required_bots) + [...]` — the **configured token strings, verbatim, with
no registry check** (:1040) — then matches evidence with `f.get('bot_kind') == bot` (:1048) while
`proven` is likewise keyed by `bot_kind`. A token that is not a kind therefore matches **no finding and
no participation record, ever**, and `absent` is the documented **fail-closed default** for "no evidence
of any kind" (:711). ⇒ The required quorum for that token can never be satisfied by any amount of real
reviewing, so **every future merge in that repo is blocked**, not merely the one observed.

⛔ **And it is unrecoverable by retrying** — re-triggering re-fetches the same comments, re-classifies
them identically, and re-emits `absent`. That is the **NON-CONVERGENCE archetype, THIRD INSTANCE** in
this epic (after PLAN-PR-043 D1 and the foreign CodeRabbit data-point): a retry loop whose input cannot
change by retrying. Same signature, third distinct cause.

**⭐ (3) IT IS A FALSE `absent`, CORROBORATED — the bot did review.** API-Sheriff PR #254 (merged, and
the repo's current HEAD `6ba8879`) carries comments from **7 coderabbitai, 1 cuioss-review-bot, 2
sourcery-ai** — read via the CI abstraction against `cuioss/API-Sheriff`. pr-agent participated; the
config could not see it.

**⛔ (4) ALL THREE TRACKED FILES ARE STILL WRONG ON MAIN — 3 of 3, derived not assumed.** Checked this
pass: TokenSheriff `.plan/marshal.json:107`, API-Sheriff `:115`, cui-http `:103` all still read
`coderabbit,cuioss-review-bot`, and **all three working trees are clean**. The reporting run's
"I fixed it plan-locally only" is corroborated in the direction that matters: the fix reached no main.
It therefore **re-fires on the next plan in each repo**, exactly as recorded for cui-http.

**Disposition — ABSORBED, no spec written and none amended.** `PLAN-PR-044` already owns every ours-side
limb: D0 (name the observed mechanism, reject the other two), D1 (validate each token against
`bot_registry.bot_kinds()` and give a non-kind its own blocking state), D2 (say it at configuration
time), D3 (the message names the discriminating question). D0's answer is now **fully settled** —
mechanism (1), the login placed in the kind slot — and D1's target mechanism is the `classified` loop
named above. ⛔ The spec is NOT amended: its row is `running` and the running-row exclusion binds.

⛔⛔ **THE OPERATOR RELAY IS STILL THE ONLY CHANNEL AND IS NOW MORE URGENT.** `inbox write --target-plan`
refuses a running plan by construction (`undeliverable_to_running_plan`); there is no orchestrator→
running-plan path. Without the relay, D0 re-derives from scratch what is now settled here, and D1 is
authored without knowing the exact loop it must fix.

**Owed operator action, still NOT ours and still unowned:** revert `required_bots` to `coderabbit,pr-agent`
in TokenSheriff, API-Sheriff, and cui-http. Outside plan-marshall's write boundary; tracked here so it is
not assumed someone noticed. ⚠ The org fan-out is ~21 repos and only 9 are checked out locally, so the
true denominator remains **UNKNOWN** — three is a floor, never a total.


### ⛔⛔ NEW 2026-09-03 (cleanup) — THREE specs collapse onto ONE `plan_id` in `corpus surfaces`

Found while re-grounding. `corpus surfaces` attributes all three members of the 025 family to the
same id:

| Spec file | Reported `plan_id` | Row status |
|---|---|---|
| `PLAN-PR-025-…md` | `PLAN-PR-025` | retired |
| `PLAN-PR-025A-…md` | `PLAN-PR-025` | **shipped** (#1368) |
| `PLAN-PR-025B-…md` | `PLAN-PR-025` | **staged, emittable** |

⛔ **The `claimed[]` list keys by `plan_id`**, so a live spec's declared paths are merged with a
retired one's and a shipped one's under a single key, and a consumer reading `claimed[]` for
`PLAN-PR-025B` finds **nothing** — silence, not an empty surface. This pass hit exactly that: the
intersection sweep initially scored 025B `0/0` and would have reported it undisturbed when its
declared surface actually contains `.plan/marshal.json`, which **did** move in the window.

⭐ **Scope it correctly rather than over-claiming — the WRITE path is fine.** `corpus set-verdict`
resolves through `_spec_matches_row` (`orchestrator.py:1119`), `path.stem == plan_id or
path.stem.startswith(f'{plan_id}-')`, which matches `PLAN-PR-025B-…` for `--plan PLAN-PR-025B`
correctly and uniquely. The per-spec `corpus surfaces` ROW is also correct (it keys by `spec`
filename and reports 025B `declarative`, `claimed_count: 5`, `admits: true`). Only the derived
`plan_id` field, and therefore the flat `claimed[]` attribution, is wrong.

⛔ **Root cause is a grammar gap this epic created itself.** The documented plan-id forms
(`inbox detect`) all require **trailing digits** — `PLAN-{DIGITS}`, `PLAN-{SLUG}-{DIGITS}`,
`{SLUG}-{DIGITS}`. The letter-suffixed `025A` / `025B` naming was invented by this epic's own
mandatory 025 split and was never taught to the parsers, so the id derivation stops at the digits
and drops the suffix.

⇒ **ROUTED to `truthful-signals`** under the three-way rule — the subject is the epic-spec parser,
not the PR-review apparatus. ⚠ Local consequence to carry until it lands: **do not trust `claimed[]`
attribution for any letter-suffixed spec**; read that spec's own row by `spec` filename instead.

### ⛔⛔⛔ ESCALATED 2026-09-03 — it is not one project's mistake, it is a COORDINATED THREE-REPO SWEEP

A fourth data-point named PR #693. Sweeping every local checkout for `required_bots` turned the
single-project defect into a fleet pattern. **Derived, not asserted** — 9 checkouts under `~/git`:

| Repo | `required_bots` | Introducing commit |
|---|---|---|
| **TokenSheriff** | `"coderabbit,cuioss-review-bot"` | `05818bc4` (#693) |
| **API-Sheriff** | `"coderabbit,cuioss-review-bot"` | `1c7308c` (#249) |
| **cui-http** | `"coderabbit,cuioss-review-bot"` | `c7862d0` (#192) |
| plan-marshall | `"pr-agent"` — **correct** | — |
| cui-jsf-test-basic, cui-llm-rules, cui-open-rewrite, cuioss-parent-pom, nifi-extensions | *no `required_bots` key* | — |

⭐⭐⭐ **All three carry the IDENTICAL commit subject**: `chore(config): rename the pr-agent reviewer
token to cuioss-review-bot`. Three separate repositories, three separate reviewed PRs, one wrong
change, all landed. **This was deliberate and coordinated** — someone concluded the token should be
the author login and rolled it out. It is not a typo and it will not stop on its own: whatever
produced those three will reach further repos.

⛔⛔ **The one repo that got it right is the one that DEFINES the registry.** The sweep landed
precisely where nobody could see `bot_kind: pr-agent / author_login: cuioss-review-bot` side by side.
That is the strongest possible argument for PLAN-PR-044 D2: the naming is confusing enough that a
maintainer inverted it *on purpose*, and three reviews agreed.

⛔ **The five key-less repos are NOT a clean bucket.** An absent `required_bots` defaults EMPTY, and
an empty required set makes the quorum **vacuously satisfied** — no required bot, so nothing can
fail. That is a different posture, not a healthy one, and it must not be counted as "unaffected".

⚠ **POPULATION HONESTY — this is a SAMPLE, not the fleet.** Nine local checkouts, of which four
configure `required_bots` at all and three of those four are wrong. The org fan-out is ~21
repositories (see the PLAN-PR-038/039 sequencing note), so the true denominator is unknown and the
three PR numbers only prove the sweep visited *at least* three. ⛔ Do not restate "3 of 4" without
"of the locally-checked-out repos that configure it".

**Two owed actions, and only one is ours:**

1. **plan-marshall** — validate the configured token against the live registry. That is PLAN-PR-044,
   already staged and running, and this evidence does not change its deliverables.
2. **The three repos** — revert the rename. ⛔ **Not plan-marshall's write boundary and nobody owns
   it.** Named here so it is a tracked debt rather than an assumption that someone noticed.

### ⛔⛔ NEW 2026-09-03 — PLAN-PR-044's D0 IS ANSWERED FROM OUTSIDE, and the running plan cannot be told

A data-point reported *"live defect on main — `.plan/marshal.json:103` has `required_bots:
"coderabbit,cuioss-review-bot"`"*. **Corroborated first-party, with one correction to the framing:**

| Claim | Verdict |
|---|---|
| the file is `.plan/marshal.json:103` with that value | **corroborated** — but in **`cui-http`**, not plan-marshall |
| plan-marshall's own `main` carries the defect | ⛔ **contradicted** — ours reads `"required_bots": "pr-agent"` at `:117`, which is correct |
| commit `c7862d0` (#192) introduced it | **corroborated** — `chore(config): rename the pr-agent reviewer token to cuioss-review-bot (#192)` |

⭐⭐ **This settles `PLAN-PR-044` D0: mechanism (1) — the configured token was the LOGIN, not the
kind.** Not a stale resolved registry, not an unmapped login. The other two arms are rejected.

⭐⭐⭐ **And it is worse than a typo, in the way that most strengthens the plan.** The commit subject
states the intent outright — someone *deliberately renamed the token to the login*, and the change
**landed through a reviewed PR**. Nothing in the config, the schema, or the review told anyone that
`required_bots` takes a `bot_kind`. ⇒ **PR-044 D2 (validate at configuration time) is not a nicety;
it is the only layer that could have caught this**, because the human layer already looked at it and
approved.

⛔⛔ **THE RUNNING-PLAN PROBLEM, stated because it is a real gap and not a formality.** PLAN-PR-044 is
`running`. The running-row exclusion forbids amending its spec, and there is **no orchestrator→plan
delivery path**: `inbox write --target-plan` refuses a running plan by construction
(`undeliverable_to_running_plan`), and the inbox is drained between plans. ⇒ The one channel is the
**operator relaying it by hand**. Recorded here so that if the relay does not happen, the plan's own
D0 will have re-derived from scratch what was already known — and this entry is the evidence it was
known.

⚠ The tracked `cui-http` file is still wrong; only that plan's local snapshot was fixed, so it
**re-fires on the next plan in that repo**. ⛔ Fixing a consumer repo's `marshal.json` is not this
epic's write boundary and not plan-marshall's to do — it is named here as an owed action for the
operator, not as a deliverable.

### ⛔⛔ NEW 2026-09-03 — a reviewed-clean CodeRabbit run scored `absent`, and the run's own diagnosis of WHY does not survive first-party reading

Foreign-system data-point, relayed by the operator. **No landing, no ship semantics** — recorded for
the observation and for the correction. CodeRabbit's comment carried a machine-readable coverage
stamp naming `4f8b0733a` as both `sourceCommitId` and `coveredCommitId`, `kind: reviewed`, all 48
changed files, `Merge Risk: Minimal`, both pre-merge checks passing. **It reviewed the exact tree
being merged and found nothing actionable — and earned no participation credit.**

⭐ **THE OBSERVATION IS THIS EPIC'S THESIS IN ONE RUN**: *reviewed-clean* and *nobody-reviewed*
resolved to the same signal. That is PLAN-PR-026's title, observed live.

⛔⛔ **BUT THE RUN'S STATED MECHANISM IS REFUTED AT HEAD `30cd8aaf8` — do not re-adopt it.** The run
attributed the missing credit to the noise pre-filter consuming *"No actionable comments were
generated"* (`count_skipped_noise: 3`). Two limbs, and only the first holds:

| Limb | Verdict | Basis |
|---|---|---|
| that string is in CodeRabbit's `ignore_patterns` | **corroborated** | `coderabbit.md:47` — `"No actionable comments were generated"  # no-op review` |
| ⇒ therefore the bot earns no participation credit | ⛔ **contradicted** | the noise filter and the participation credit are in **two different loops over `raw_comments`** |

`github_pr.py:1313` is the participation loop; `:1446` is the finding-persistence loop, and the noise
drop is at `:1551` **inside the second one**. The predicate's own docstring scopes it: *"drop obvious
automated/acknowledgment noise **before each surviving comment is persisted as a `pr-comment`
finding**."* The participation loop consults no noise predicate at all. ⇒ At this HEAD a
noise-filtered clean review **still credits participation**.

⭐ **THE LIVE ALTERNATIVE, and it is checkable in one read.** CodeRabbit declares
`participation_evidence: [review_body, inline]` (`coderabbit.md:41-43`) — **`issue_comment` is NOT a
credited shape for it.** If the clean-review notice was published as an `issue_comment`, participation
is denied by the evidence-shape gate, not by the noise filter. ⚠ **HYPOTHESIS** — the comment's `kind`
was not observable from here. **The discriminating check: read the `kind` of the comment carrying the
coverage stamp.** `review_body` ⇒ something else is wrong and this entry is incomplete;
`issue_comment` ⇒ the gate is the cause and the remedy is a registry question, not a filter question.

⚠ A third possibility not to skip: the observing system may be running an older cached version. ⛔ The
registry-pin leak makes that the ordinary case, not an exotic one — establish the observed system's
version before treating any of this as a defect in current main.

⭐⭐ **A NON-CONVERGENCE ARCHETYPE, SECOND INSTANCE.** The run reports that re-firing re-fetches the
same comment, re-filters it identically, and re-emits `absent` — burning all 5 iterations on an
unchanging input. **Same signature as PLAN-PR-043 D1** (trigger B cannot select the bot that gates),
**different cause**. The archetype: *a retry loop whose input cannot change by retrying.* ⛔ Worth a
detector of its own — an iteration budget spent on a fixed input should be reported as
non-convergence, never as exhaustion.

### ✅ 2026-09-03 — a CONTROL that worked, recorded because this section is otherwise all failures

From the same data-point. The operator minted the override through the designed mechanism: flipped
the barrier to `ask` mode (whose *"Merge anyway"* branch is the documented `barrier-ask-override` mint
site) and granted it **HEAD-bound** against `4f8b0733a` with the evidence recorded.

⭐ **The gap-class binding was observed doing its job live**: `barrier-ask-override` read admissible
for `review-barrier-gap`, while `pre-merge-consent` read **inadmissible** for that same class —
refusing to let a routine merge confirmation authorize past a participation gap the operator never
saw. That is the fail-closed guard behaving exactly as specified, and it is the matched positive
control for the merge-authorization work PLAN-PR-015 landed. Do not let this section's density of
defects imply the barrier is broadly unsound; this limb is confirmed working.

### ⛔⛔ NEW 2026-09-02 — CodeRabbit FABRICATED a finding, with a committable suggestion attached

Operator paste from a `cuioss/TokenSheriff` run. CodeRabbit filed a finding for a `the the` typo
**present in no revision of the file**, and attached a **committable suggestion** to it.

⛔ **The committable suggestion is what makes this different in kind from a false positive.** An
ordinary wrong finding costs a triage decision. A one-click suggestion for a defect that does not
exist invites *applying* a change to code nobody found wrong — the reviewer stops being a source of
claims to evaluate and becomes a source of edits to accept.

⚠ **n = 1, relayed, NOT re-derived.** The run's own inbox messages went to TokenSheriff's store, so
this did not come through the drain. ⛔ Do NOT generalise to "CodeRabbit hallucinates" — the standing
record across this epic is that CodeRabbit carries most of the actionable yield, and one fabrication
does not move that. What is recorded here is the CLASS and its blast radius, not a rate.

⛔ **NOT STAGED — deliberately.** No spec owns reviewer fabrication, and one instance does not size a
plan. **Escalation condition, so this is not left to drift:** a SECOND observed fabrication, or any
observation of a fabricated suggestion being *applied*, promotes this to a spec immediately. Until
then it is a Watch with a named trigger, which is the same discipline the currency-blind gap was held
under — and that trigger did eventually fire.

⭐ Adjacent, and worth checking when it is staged: our own triage path treats a bot finding as a claim
to disposition, never as a patch to apply. Confirm that a committable suggestion cannot enter any
auto-apply path before deciding this is only a reviewer-quality problem.

### ⚠ NEW 2026-09-02 — a consumer repo's plan writes its epic inbox message into ITS OWN store, so the finding never arrives

The TokenSheriff run reported *"Both are in the epic inbox."* This epic's inbox was empty at that
moment — `inbox list`: `count 0`, `live_count 0`, `invalid_count 0`, `inbox_state present`. The
operator confirmed the messages are in **TokenSheriff's** inbox.

⭐ **This explains a thing already in the record rather than only itself:** `truthful-signals-042.md`
originated from the same TokenSheriff plan (`refresh-identity-and-scope-defences`, PR #682) and
reached us **only because a sibling orchestrator forwarded it by hand**. Two findings from the same
repo, one arrived by human relay, one did not arrive at all.

⚠ **The mechanism is a LEAD, not a corroborated finding.** The likely cause is that the orchestrator
store resolves main-anchored to the **current checkout's** git-common-dir — the same CWD-keyed
resolution that makes cross-repo `manage-lessons` removal unsafe — so `inbox write --slug
review-apparatus` from inside TokenSheriff creates a `review-apparatus` tree *there*. ⛔ **This was
NOT verified first-party**: reading TokenSheriff's store was declined, correctly, and no local
evidence settles it. Do not transfer this to a sibling epic as a finding until someone re-derives the
resolution path from the resolver, not from this inference.

⛔ **The consequence stands regardless of the mechanism:** consumer-project review findings — the
exact intake this epic most needs — have no path into this ledger and arrive only when a human
relays them. Treat "the inbox is empty" as saying nothing about consumer repos.

### ⛔⛔ NEW 2026-09-02 — the accepted currency-blind gap's OWN reopening trigger has FIRED ⇒ PLAN-PR-045

Drained from `truthful-signals-042.md` (forwarded from `refresh-identity-and-scope-defences-002.md`).
`bot-participation-contract.md` § *"The currency-blind path for append-per-review bots — an accepted,
bounded gap"* names its reopening condition, and the first of its two observations has now occurred.

**Re-corroborated first-party before staging — including the foreign limb the sender filed as an
uncorroborated lead:**

| Claim | Verdict | Basis |
|---|---|---|
| currency test gated on `_requires_update` | corroborated | `github_pr.py:1317`, `:1338` at HEAD `30cd8aaf8` |
| CodeRabbit declares the flag `false` | corroborated | `coderabbit.md:44` |
| ⭐ **Sourcery declares it too — the population is TWO bots** | corroborated | `sourcery.md:36` (the message named only CodeRabbit) |
| the gap is documented with a named trigger | corroborated | the § passage, read verbatim |
| `PLAN-PR-024` excluded it for unobservable behaviour + missing sign-off | corroborated | `PLAN-PR-024:421-424`, verbatim |
| CodeRabbit reviewed head `99c36992` at `20:26:12Z` | corroborated | `ci pr comments` on `cuioss/TokenSheriff#682`; the review body names `379afb77...99c36992` |
| head advanced to `82e6597d` at `20:50:49Z` | corroborated | `git -C` — author and committer date identical |
| ⭐ **no CodeRabbit review of the advanced head for ~10.7 HOURS** | corroborated, **stronger than filed** | next review body is `2026-09-01T07:30:21Z`; its range `99c36992...cf8acb8` did eventually cover `82e6597d` — the next morning |
| the `20:51:18Z` "Review limit reached" decline | ⚠ **unverifiable** | absent from the PR's current comment set, read two days post-merge. ⛔ **NOT a refutation** — such notices are transient and are removed |
| findings `3ff3c0`/`dcf252`/`6b6f49` carry the stale `reviewed_commit_sha` | ⚠ **not checked** | the foreign plan's findings store was not read — an unchecked limb, not a clean one |

⛔ **HALF the `PLAN-PR-024` blocker is discharged, not all of it.** That exclusion cited two things:
nobody had observed the real publishing behaviour (now discharged) and the change needs sign-off
across every consumer project whose `required_bots` names an append-per-review bot (**still open —
an operator decision, not a technical one**). ⇒ `PLAN-PR-045` D1 is a DECISION with rejected arms
recorded, not a fix; arms (a) and (b) are gated on that sign-off, arm (c) is not.

⭐ **The compose is the part neither path predicts alone.** The contract's mitigation — an
append-per-review bot re-triggered on the advanced HEAD posts a NEW comment — assumes the re-trigger
is **served**. Declined for quota, no new comment arrives and the stale credit stands. The rate-limit
path (`PLAN-PR-043`, `PLAN-PR-025B`) and the currency-blind path (`PLAN-PR-045`) compose into a false
green.

⚠ **Three green-looking signals, one review.** `review_completeness` `participated`,
`bot_completion completed: true`, and a green CodeRabbit CI check are all satisfiable while the
review is stale — only the first is even about a review, and it does not say *of what*.

### ⛔⛔ NEW 2026-09-02 — `corpus cross-check`'s live-plan arm compared THREE EMPTY SURFACES and published no tally saying so

Derived first-party while re-deriving the live-plan collision set the resume anchor demanded before
the next emit. `corpus cross-check` reported `plans_scanned: 3` and **zero** `candidate_kind:
live_plan` rows among 639 file overlaps (492 `corpus_spec`, 147 `sibling_epic_spec`).

⛔ **That zero is SILENCE, not a checked negative.** All three live plans are at phase `1-init` and
declare no footprint at all: `manage-references get --field affected_files` returns `field_not_found`
for `documented-invocations-cannot-succeed-as-written` and
`dual-homed-hook-install-renders-identically`, and `file_not_found` for
`planning-lane-change-type-scope-execution-manifest` (no `references.json` at all). The live-plan arm
therefore compared each of our 43 comparable specs against an EMPTY path set three times.

⭐ **The asymmetry is the defect.** `corpus cross-check` publishes a five-member
`spec_surface_states[]` tally for OUR OWN specs — so an indeterminate spec of ours is visible — and
publishes **no equivalent tally for the live-plan candidates**. A reader gets `plans_scanned: 3` and
cannot tell three surface-bearing plans from three empty ones. This is ADR-019 applied to our own
specs and not to the candidates we compare them against.

⇒ **ROUTED to `truthful-signals`** under the three-way finding rule: the subject is the orchestrator's
own instrument, not the PR-review apparatus. Delegated as an inbox message; **removed from this
ledger's work**, retained here only as the derivation record.

### ⛔ NEW 2026-08-27 — the merge-queue routing section omits a precondition the queue enforces

From the PLAN-PR-027 landing. #1359 landed mid-finalize on the same four files, and #1356 went
`mergeable: conflicting`. The rebase that resolved it replayed 33 commits, skipped 0, and resolved all
four conflicts additively.

⛔ **The contract gap: `branch-cleanup`'s merge-queue path documents SKIPPING the rebase — but the
queue cannot accept a conflicting PR.** A conflict-resolving rebase is therefore a **precondition the
routing section does not name**, and a run following the documented path on a conflicting PR stalls
with no instruction. ⇒ Belongs with the branch-cleanup routing surface; **not staged** — PLAN-PR-033
and PLAN-PR-028 `540b` both touch that document, and this is one sentence, not a plan.

### ⚠ 2026-08-27 — pin gate re-opened again (5 versions), and the landing-facts regression did NOT recur

Executor `0.1.1561` vs registry `installPath 0.1.1556`. **Third consecutive landing with the gap open**
(6 versions at #1349, 5 now) — the per-landing leak is confirmed steady-state, not intermittent.
Operator-only repair.

⭐ **The #1349 landing-facts regression did NOT recur**: #1356's landing returned `complete: true`, 0
missing. ⇒ That defect is **intermittent, not a removed feature** — which narrows what PLAN-PR-028 D2's
producer-side assertion must catch, and is recorded on that spec.

### ⛔⛔ NEW 2026-08-26 — the landing-facts block REGRESSED to prose-only, and the pin gap re-opened by SIX versions

From the PLAN-PR-024 landing ([`landings/PLAN-PR-024.md`](landings/PLAN-PR-024.md)).

**1. `emit-landing` emitted NO `landing-facts` block.** `landing-check` on
`participation-credit-anchored-to-merge-candidate-010.md` returns `complete: false` with **all 8
required keys missing**, and `grep -c 'landing-facts'` returns **0**. ⛔ **This is a REGRESSION, not a
standing gap**: PLAN-PR-034's landing on 2026-08-25 (#1344) returned `complete: true`, 0 missing, from
the same step. ⇒ The drain reconciled that plan from narrative alone. ⭐ **PLAN-PR-028 D2 now has a
live first-party instance** — folded onto that spec.

**2. `executor == installPath` FAILS: executor `0.1.1550`, registry `installPath 0.1.1544`.** This
run's `sync-plugin-cache` minted `v0.1.1550` and, as always, did not re-pin the registry — the known
per-landing steady-state leak, now **six versions** wide. ⚠ Repair is OPERATOR-ONLY. ⛔ **Not asserted
as the cause of defect 1** — the two are recorded independently, and PLAN-PR-034 shipped a complete
landing while the same gap was open at a smaller width.

### ⛔ NEW 2026-08-25 — an ad-hoc `NO_PLAN` landing can NEVER satisfy `landing-check`, by construction

Recorded at the 2026-08-25 drain, per [`workflow/analyze.md`](…) Step 4's `complete: false` branch. Two
queued sibling landings failed the drain-completeness check:

| Message | `complete` | `missing_keys` |
|---|---|---|
| `truthful-signals-031.md` (PR #1337) | `false` | `plan_id`, `deliverables_total`, `deliverables_done`, `total_tokens`, `steps` — the whole plan-lane half |
| `truthful-signals-032.md` (PR #1336) | `false` | `total_tokens`, `steps` |

⭐ **The `-031` failure is STRUCTURAL, not a producer bug.** #1337 was an ad-hoc `NO_PLAN` foreign-machine
landing: it has no plan id, no deliverable count, no token ledger and no step list, because no plan
lifecycle ran. The check's `n/a` allowance is scoped to `pr` and `merge_state` only — at
`plan_id` / `deliverables_*` / `total_tokens` / `steps`, `n/a` reads as MISSING. ⇒ **A truthful ad-hoc
landing is unrepresentable in the required-key set**, so it can only ever report `complete: false`.

⚠ **This epic has already shipped one such landing itself** — PLAN-PR-041 (`cuioss/pr-agent-settings#15`),
whose row is stamped `NO_PLAN` with "no metrics by construction". The same gap would fire on it.

⇒ Either the required set needs an ad-hoc/`NO_PLAN` shape (a declared landing *kind*), or `n/a` needs to
be legal at the plan-lane keys when the landing declares itself ad-hoc. **PLAN-PR-028 owns the landing
message contract** and is the natural home — but it is UNEMITTABLE AS WRITTEN (only blocking verdict,
must be re-authored), so this is recorded here rather than folded into a spec that cannot ship.

### ⛔⛔ NEW 2026-08-25 — PLAN-PR-034 declared 5 files and touched 19, and it moved ten staged specs' ground

From the PLAN-PR-034 landing ([`landings/PLAN-PR-034.md`](landings/PLAN-PR-034.md) § Surface
Under-Declaration). Established by `git show --stat dfabe3d8e` against the spec's own
`## Expected Surface` — a derivation, not an estimate.

The spec declared **5** files. The merge touched **19**. The 14 undeclared files are the most
contended in this corpus: `automatic-review/SKILL.md`, `review_completeness.py`, `bot_registry.py`,
`coderabbit.md`, `sourcery.md`, `branch-cleanup.md`, `workflow-integration-github/SKILL.md`,
`github_re_review.py`, and five test modules. **Ten staged specs claim at least one of them** —
PR-024, -025, -026, -028, -029, -030, -031, -033, -036, -040.

⛔ **Every one of those specs is now written against code that has moved, and their verdicts were
ALREADY stale before this landing** (stamped at `f6d058b4b`/`77c9dc70a`). ⇒ **A re-grounding
`cleanup` pass is a PRECONDITION for any emit, not an optional tidy-up.** Emitting against an
unre-grounded spec here is how a plan ships a fix for a defect that no longer exists.

⭐ **Root cause is NOT a faulty read.** The plan itself filed the correcting lesson: `affected_files`
is a **missing write path after outline** — nothing reconciles the declared surface against the real
diff at finalize. The two findings corroborate each other, and the remedy is a tooling write path,
which is not this epic's surface. Recorded here because the *consequence* — an unreliable
disjointness matcher — is entirely this epic's problem.

### Live in merged `main` after the cloud wave — 2026-08-23

Established by the thirteen post-run verifications, not inferred. Each is owned by a staged plan; none
is closed. Full evidence in [`cloud-wave-audit.md`](cloud-wave-audit.md) § 4 and in the per-run
`cloud-runs/*/verification.md`.

| # | Defect | Sev | Owner |
|---|---|---|---|
| 1 | A currency-subject bot's **second** evidence comment bypasses the currency test and credits an advanced HEAD; the subtraction then clears the stale set too. Reproduced end-to-end against the shipped producer, twice, independently. | blocker | PLAN-PR-024 D1 |
| 2 | `structural_share: 100.0` at `reviewer_coverage: 1/1` the moment the caller-supplied roster shrinks — the named inversion the plan said must not ship. | blocker | PLAN-PR-030 D1 |
| 3 | A landing message is emitted for a run whose merge did not land. `emit-landing` is unconditional; five terminal `branch-cleanup` branches record `done` without merging. | blocker | PLAN-PR-028 D1 |
| 4 | `execution-context.md:23` tells every dispatched leaf that `--plan-id` after a `ci` verb is an argparse rejection. **Ten** subcommands declare it themselves, all `required=True`. | blocker | PLAN-PR-027 D1 |
| 5 | The foreign-PR gate clears on a payload with no `foreign` classification, clears `unpushed`, and passes no `--branch`. A stale remote-tracking ref makes a pushed branch read `unpushed` — and clear. | major | PLAN-PR-028 D4 |
| 6 | A delivered thread reply whose resolve mutation fails is re-sent next round **and** counted `untransmitted`. | major | PLAN-PR-029 D2 |
| 7 | `_is_obvious_noise` reads the CodeRabbit AI-agent block; four of twelve `ignore.low` regexes are unanchored substrings, so a phrase inside the block silently destroys the whole finding. | major | PLAN-PR-029 D1 |
| 8 | The recovery Branch 0 branches on a `cause` neither producer emits, so a Sourcery size refusal is offered a wait. | major | PLAN-PR-025 D1 |
| 9 | `--stale-participation-bots` silently drops a non-admissible pair → `absent` instead of `participated_stale`. | major | PLAN-PR-025 D3 |
| 10 | GitLab `pr merge-queue` issues the merge-train POST **before** any callee-side state read; the shared GitLab preflight fails **open** on an unresolvable project scope while its docstring claims the opposite. | major | PLAN-PR-027 D3 |

⛔ **A refusal nobody recognises is filed as an ordinary finding** — `_is_refusal_notice` matches by
enumeration in both layers, and PR-Agent (the one *required* bot) declares **zero** `refusal_patterns`,
so its registry layer can never fire. When neither layer fires there is no drift to record. Owned by
PLAN-PR-034; it is listed apart from the table because no cloud run measured an instance — the
mechanism is confirmed, the incidence is not.

⚠ **13 of 43 observed PR findings received no posted answer** (#1167 ×4, #1158 ×2, #1198 ×6, #1195 ×1).
Recorded as a run-report finding and as residue, never as a `gaps.md` entry, so no staged plan
inherited it. Owned by PLAN-PR-035, whose D0 attributes the thirteen before anything is fixed.

### ⛔ NEW 2026-08-23 — our own comment is ingested as a review finding (drained from the inbox)

Live in merged `main`. **Corroborated FIRST-PARTY before staging**, not taken from the message that
reported it: `github_pr.py`:393 is `body.lstrip().startswith(_SELF_RESPONSE_HEADING)` with
`_SELF_RESPONSE_HEADING = '## Triage dispositions'` (:347). The self-response filter therefore keys on
a **heading literal**, so any comment we author opening with anything else is not recognised as ours
and enters the finding set. An author-identity comparison already exists one module over
(`_github_pr.py`:982, `viewer_login`), so the fix is a re-key rather than new plumbing.

⭐ The module's own docstring already concedes the filter "cannot be complete" (`github_pr.py`:17) and
carries a bounded `(self-response-loop)` guard for what it misses — **documented, not corrected**, the
same shape as the pr-agent `issue_comment` bucketing.

⛔ **This is a measurement defect, not just a noise defect.** An epic that exists to measure its
reviewers is counting its own text among their output. It corrupts PLAN-PR-035's `13 of 43` ratio at
BOTH ends, and that caveat is now recorded on PR-035's own spec.

Owned by **PLAN-PR-040**. Source: inbox `truthful-signals-030.md`.

#### ⭐⭐ UPDATED 2026-08-29 — the real cause is a BYPASS, and the chosen remedy trades detection for it

Drained from `truthful-signals-040.md`, itself routed from a foreign-repo defect report (API-Sheriff
PR #230, plan `distroless-health-check`). **Every claim below was re-derived first-party at HEAD
`a1cae6102` before being recorded**; the drained message's own § 3 diagnosis did NOT survive that.

⚠ **LINE DRIFT CORRECTED ON THE SPEC — all three citations above are stale.** At HEAD:
`github_pr.py`:**404** (was :393), `_SELF_RESPONSE_HEADING` :**358** (was :347), and — the one the
drained message did NOT name — `viewer_login` at `_github_pr.py`:**1121/:1182/:1211** (was :982).
The third is the load-bearing one: D1 depends on that site being a usable identity comparison.

⛔ **A RELAYED DIAGNOSIS IS REFUTED — quarantined on the spec so it cannot re-enter.** An older
forwarded framing claimed the filter was anchored on `## Review responses` while the emitter emitted
other headings, i.e. emitter/recognizer drift. **Both halves are false.** `## Review responses` has
**0 hits over the whole inventoried tree** (5268 files scanned, 0 unreadable, not truncated — a
clean-coverage derived zero), and emitter (:1965) and recognizer (:404) read **one shared constant**,
with the comment at :352-357 stating that design explicitly. ⇒ **Acting on it would have "fixed"
working code.** ⭐ PLAN-PR-040 never carried the refuted framing — its OBSERVED claim is accurate and
re-corroborates at HEAD. The note is defensive only.

⛔⛔ **THE ACTUAL FINDING, and it is a COUNTER-ARGUMENT to PLAN-PR-040 D1/D2.** On PR #230 a dispatched
finalize agent **hand-authored** the batched response comment instead of routing it through
`github_pr post_responses`. Its heading was not the constant, `_is_self_authored_response` correctly
returned `False`, and the next `fetch_findings` ingested our own comment as a fresh `pr-comment`
finding. **The filter did its job.** It excludes what the sanctioned *emitter* produces and makes no
claim about arbitrary text an agent invents — so the shared-constant guarantee is **one-directional**:
it stops a *rename* reopening the loop, but cannot bind a caller that never uses the emitter at all.
**Nothing detects the bypass. That gap is the finding.**

⇒ Under D1/D2's author-identity re-key, a hand-authored bypass is **recognised as ours and silently
swallowed** — the bypass becomes *invisible* rather than merely mis-filed. ⭐ This is **not** an
argument that D1 is wrong; it is that D1 buys robustness at the cost of **detection**, and the spec
must **choose that trade explicitly rather than inherit it**. Both amendments are folded onto the
spec, together with a **third arm that preserves detection** (file an `issue_comment` by the PR actor
carrying the emitter's structural signature `### In reply to comment_id:` but not the heading, as a
`triage` finding) and the **cheapest arm** (state at the call site that an agent must never compose
the batch body itself).

⭐ **A SECOND limb, first-party and NOT in the drained message:** the recognizer's docstring
(:390-394) names the start anchor as a **load-bearing false-positive boundary** — a human comment
quoting the heading is real feedback and must still be filed. `cuioss-oliver` is **both** the emitter
identity and a genuine reviewer (8 `inline` + 2 `issue_comment` rows on #1361 alone), so a naive
identity test would swallow the operator's own review comments. D1 must preserve that boundary.

⛔ **THE DRAINED MESSAGE'S § 3 INSTRUMENT CAVEAT IS ITSELF CONTRADICTED — do not adopt it.** It warned
that D4 must avoid `ci pr comments` because the verb "structurally excludes" `issue_comment`, citing
its help string *"Get PR inline code comments"* (`ci_base.py`:1095 — the help string is real). **The
help is narrower than the behaviour.** Run first-party against #1361, `ci pr comments` returned
`inline`, `review_body` **AND** `issue_comment` (≥6 of the latter). ⇒ D4 **may** use it. What remains
genuinely unexplained is the observation that prompted the warning: the same verb against the FOREIGN
repo (`--project-dir …/API-Sheriff`, PR #230) returned `total: 48` with **zero** `issue_comment` rows
— an open question about the **foreign-targeting path**, not the verb's population. D4 carries the
surviving obligation: **name the instrument and publish its coverage as a derived figure.**

⭐ Recorded as correct behaviour, no action: the foreign run's finalize `lessons-capture` **correctly
refused** to file this locally (`add` → `error: wrong_store` for a bundle-prefixed component) and
declined to launder it with `--allow-foreign-store`. The store guard worked as designed.

Disposition: **FOLDED onto PLAN-PR-040** (D1, D2, D4, Claim Labels, Expected Surface). No new spec —
the signal lands entirely inside an already-staged one. Source: inbox `truthful-signals-040.md`.

### ⛔⛔ NEW 2026-08-24 — the cloud-imported specs were never fully transformed, and it BREAKS THE DISJOINTNESS MATCHER

Operator question at the 08-24 session ("are they properly transformed, or do they still have cloud-plan
aspects built in?"). Answer: **not fully.** Measured over the 17 staged/launched specs, 195 declared
`## Expected Surface` paths. Three residues, in descending severity.

**1. ⛔⛔ A PATH-DIALECT SPLIT MAKES REAL COLLISIONS INVISIBLE.** Only **134 of 195** declared paths are
repo-rooted and matchable. The rest are cloud-lane shapes: **13 ELIDED** (`.../automatic-review/SKILL.md`
— PR-025, -028, -030) and **27 BARE / non-rooted** (`standards/api-contract.md`, `SKILL.md`, `build.py`
— across nine specs). `corpus cross-check` scores an **exact normalized path overlap**, so the two
dialects partition into **two non-communicating sets**: elided matches elided, rooted matches rooted,
and a cross-dialect collision is *structurally invisible*.

⭐ **PROVEN, not inferred — with the epic's own binding constraint as the oracle.** § Sequencing says
PLAN-PR-024 and PLAN-PR-025 must NEVER run concurrently because three adjacent bullets of ONE list in
`bot-participation-contract.md` belong to the two plans *inside a single git hunk*. The matcher reports
that pair overlapping on **3 files — and `bot-participation-contract.md` is NOT one of them.** PR-024
declares it rooted; PR-025 declares it `.../automatic-review/standards/bot-participation-contract.md`.
The same elided string matches PR-001, -005, -006, -008 and -013 (all cloud-wave siblings sharing the
dialect) and a sibling epic's `PLAN-TRUTH-091` — so the string is not inert, it is matching the *wrong
population*.

⛔ **CONSEQUENCE FOR EMIT: a `collision-free` verdict from `corpus cross-check` is a POSSIBLE FALSE
NEGATIVE for any spec carrying a non-rooted path.** It is not evidence of disjointness for those specs.
The recorded § Sequencing constraints — derived by hand — are currently the *stronger* instrument, which
inverts the intended relationship between the parser and the prose. ✅ **PLAN-PR-034, launched 2026-08-24,
is CLEAN** — all five of its declared paths are repo-rooted, it carries no lane-contract prose and no
`cloud-runs` reference, so this defect does not bear on the in-flight plan.

**2. ⛔ PRESCRIPTIVE LANE-CONTRACT INSTRUCTIONS THAT ARE WRONG IN THE LIFECYCLE.** Four specs instruct
their executor to run **`./pw verify`** *"per the lane contract"* — PLAN-PR-024:474, PR-026:683,
PR-027:590, PR-030:674. ⛔ CLAUDE.md's hard rule is **"Build commands: resolve via architecture — never
hard-code `./pw`"**; the `./pw` carve-out exists ONLY inside the `doc/plans/` standalone lane, which
these specs no longer run in. Two specs also route CI through the **GitHub MCP**, the lane's path, not
the `tools-integration-ci` abstraction. A spec is ingested as the plan's REQUEST BODY at `phase-1-init`,
so these are instructions an executing agent reads as its brief — not commentary. ⚠ **Distinguish
PRESCRIPTIVE from DESCRIPTIVE before fixing**: PR-030:586 and PR-031:329 discuss a past run's `./pw`
totals and are legitimate; PLAN-PR-032 is *about* the lane and legitimately names it throughout.

**3. ⚠ WRITE-BOUNDARY CONTRADICTION ON EPIC-TREE ARTIFACTS.** 17 `../cloud-runs/*` paths are declared as
Expected Surface across PR-028, -029, -030, -031, -032, and § Sequencing states PR-030 and PR-031 *"both
edit `cloud-runs/090-…/report-01.md`"*. But every spec's own `## Write-Boundary` says it edits **NO file
under `.plan/local/orchestrator/`** other than its inbox message — and `.plan/` is **git-ignored**, so
such an edit can never appear in a PR. The specs declare a surface their own boundary forbids and the
repository cannot carry.

**4. ⚠ One stale rooted path.** PLAN-PR-029 declares `test/plan-marshall/manage-findings/test_findings_store.py`,
which does not exist at HEAD — it was split into `test_findings_store_add.py` / `test_findings_storage.py`.
Ordinary surface drift, listed for completeness.

### ✅ RESOLVED 2026-08-24 — the normalisation pass ran, directly, by operator instruction

Applied to the **16 `staged` specs**. ⛔ **PLAN-PR-034 was EXCLUDED** — it was `launched` at the time and
a launched spec is the live brief of a running plan, never edited mid-flight (it was already clean:
5 rooted paths, no lane prose). Shipped/retired specs were out of scope per the operator.

**What changed.** 36 path rewrites + 1 brace-form expansion, **each existence-checked against
`git ls-files` before writing** — a path was rewritten only if the result is a real file, so a wrong
expansion (which would manufacture a FALSE collision, worse than the missing one it fixes) could not be
written. Bare tokens were resolved by inheriting the skill directory from the rooted sibling **in the same
bullet**, then existence-checked like any other. 3 paths were deliberately left alone: `plan.md`
(a cloud-run artifact) and two FOREIGN-repo files. Also corrected: 5 prescriptive `./pw verify`
instructions → the architecture-resolved form (PR-024, -026, -027, -028, -030); 2 plugin-cache claims
that were **inverted** — they said no sync was owed, true only in the lane, false here (PR-026, -031);
1 GitHub-MCP CI path → the `ci` abstraction (PR-031); 1 stale test path (PR-029 →
`test_findings_store_resolve.py`, applying the correction that spec's own re-grounding note already named).

⭐⭐ **PROOF THE MATCHER WAS REPAIRED, on the case that exposed it.** PR-024 ↔ PR-025 went from **3
overlapping files to 6**, and `bot-participation-contract.md` — the file § Sequencing names as the reason
they must never pair — is now among them, along with `branch-cleanup.md` and
`workflow-integration-github/SKILL.md`, the "third shared contract surface no split governs". **The parser
now independently derives what the prose asserted.** Corpus-wide `file_overlap_match_count` 447 → 520.

⭐ **A FALSE NEGATIVE WAS CONFIRMED, not merely suspected.** `PLAN-PR-025` — which this ledger listed as
COLLISION-FREE and emittable — overlaps the now-running `a-refusal-nobody-recognises-is-filed-as-a-finding`
on **11 files**, led by `automatic-review/SKILL.md`, elided in PR-025 until this pass. Had it been emitted
from that list it would have collided head-on with the running plan.

✅ **Sanity check against phantom collisions:** the set of staged specs colliding with live plans OTHER
than PR-034's is **unchanged at 8** (PR-024, -026, -027, -028, -030, -032, -033, -037). The normalisation
revealed collisions; it did not invent any. The rise to 15 is PR-034 starting, plus its overlaps becoming
visible against the de-elided specs.

⛔ **STILL OPEN — a SCOPING defect the normalisation deliberately did not decide.** PLAN-PR-031's D1–D4 are
largely corrections to `cloud-runs/*` records, which are **git-ignored**: they were moved out of
`doc/plans/review-apparatus/` at the cloud-wave ingest (`26f2f417b`, #1333, confirmed by
`git log --diff-filter=D`). So most of that plan's output can reach **no PR** and is machine-local. Every
affected spec now carries an explicit marker saying so; **re-scoping PR-031 — e.g. restoring the records to
`doc/plans/` first so the corrections become reviewable — is an operator decision, not taken here.**

### Epic-level open items — deliberately not plans

- **`020 G6`** — that an executing agent can ignore correct prose is the house convention for all eight
  `phase-6-finalize` scripts, not a defect of one gate. An epic-wide architectural question.
- **`130 G18`** — a mutation sweep over four test suites (~80 tests). Real work, nobody scheduled;
  folded into PLAN-PR-031's split rather than staged separately.
- **Plan 090's three other residue items**, all confirmed open and closed by no later plan: the
  run-report placeholder scan (belongs to `cloud-plan-lane`), the authoritative-set → doc-prose-list
  mirror drift, and the disposition-flow evidence asymmetry (a rejection needs a rationale but never a
  source).

### Pre-wave register — carried forward, NOT re-verified at this ingestion

⛔ **Read this heading before acting on any entry below.** These were recorded between 2026-07-29 and
2026-08-09. The cloud wave landed thirteen plans across this epic's whole surface, so an entry here may
have been closed, half-closed, or invalidated by a landing — and **the ingestion did not re-check them
one by one**. Two are annotated where the wave's evidence speaks to them directly. Every other entry is
dated evidence, not a durable fact: re-derive it at the moment of the claim.

- ⛔⛔ **NEW, SOURCE-CONFIRMED 2026-08-08 — the shipped coverage-shortfall disclosure computes its
  shortfall against the ROSTER, not the required set. Staged as `PLAN-PR-021`.**
  ⭐ **ANNOTATED 2026-08-23 — HALF CLOSED.** `PLAN-PR-021` shipped as **#1170**: the in-lifecycle
  instrument gained the `comparison` grade and the required/optional distinction. **The lane's own
  contract half did NOT ship** and could not, because a cloud-lane run may not amend the contract
  governing it — the disclosure in `cloud-plan-lane/SKILL.md` still has no `reviewed-empty` verdict, no
  required/optional classification, and no required-set shortfall predicate (`grep` for
  `reviewed-empty`, zero hits at `e8324d241`). Now owned by **PLAN-PR-032**, which runs outside the
  lane and applies rather than proposes. ⛔ Two further defects the shipped half introduced are live and
  owned by PLAN-PR-026: `clean` has no producer for its discriminating input anywhere in the tree, and
  `vacuous` asserts "no roster configured" from an argument the caller may simply have omitted.
  `PLAN-TRUTH-061` (#1112) shipped the disclosure at `cloud-plan-lane` § Step 8. Verified first-party
  by the orchestrator at this drain: the population is *"the `author_login` of every such registry
  doc"* (§ "Record per-reviewer participation"), and condition 4 fires when **any** roster member's
  verdict is not `reviewed`. **`required_bots` / `optional_bots` are never read.** With
  `required_bots = pr-agent` and `optional_bots = coderabbit,sourcery`
  (`bot_lists_provenance: answered`, all read first-party), the mechanism announces a "shortfall"
  whenever an OPTIONAL bot is silent on a PR whose required quorum is fully met.
  ⭐ **This is the mirror image of the vacuous-guard class** — not a gate that passes having examined
  nothing, but a gate that reports a gap that is not one. A disclosure that cries wolf gets tuned out,
  and then the real shortfall reads as noise.
  ⛔⛔ **CONSEQUENCE FOR THIS LEDGER, AND IT IS RETROACTIVE: every "1 of 3" / "2 of 3" coverage figure
  recorded in this epic — including the six-consecutive-PRs COVERAGE REGIME line in the resume anchor
  — was computed against the roster, which is the wrong denominator.** Recomputed against
  `required_bots`, those landings met quorum at 1 of 1. The *qualitative* finding those figures
  supported survives untouched (the required bot repeatedly returning "no major issues" on diffs where
  an optional bot found real defects — quorum proves participation, explicitly not review quality).
  **The RATIOS do not.** Do not reuse them; re-derive with the denominator named.

- ⛔ **NEW 2026-08-08 — RETIRED PREMISE: "plan-marshall cannot target a foreign checkout" is REFUTED.**
  `ci.py` DOES declare `--project-dir` — `:9-21` (module docstring) and `:121-131` (router consumes it
  via `extract_routing_args`, applies `set_default_cwd`), verified first-party by the orchestrator, and
  USED by this drain to corroborate cuioss-organization#235. The claim reached us in PLAN-PR-002's own
  landing message and was refuted pre-emptively by `truthful-signals-019`.
  ⭐⭐ **LESSON — verify an absent-flag claim against the ROUTER, never against the argparse table.**
  `--project-dir` is a top-level router flag consumed manually, not an `add_argument` declaration, so
  an argparse-table sweep returns a clean-looking zero. Asserted absence is the higher-risk half of the
  verify-first contract: this one would have staged a plan to build a capability that already ships.
  ⚠ `--repo` genuinely does not exist and that is NOT a gap (`gh` resolves from cwd; `--project-dir`
  sets it). The real limit is narrower: **a foreign repo with no local checkout is unaddressable.**
  ⇒ The surviving half — finalize manufacturing an empty host PR for a foreign-repo plan — is
  **ROUTED OUT to `truthful-signals`** (machinery integrity, not review-apparatus ground).

- ⛔⛔⛔ **`ci pr merge` RETURNS `merged: true` FROM AN EXIT CODE, THEN DELETES THE BRANCH — SOURCE-CONFIRMED 2026-08-03. Highest-severity defect in this epic.**
  Two independent first-party reports (`fail-closed-signal-integrity-001`; `truthful-signals-016` § 1)
  plus an **orchestrator source read**. #1081 returned `merged: true`, `branch_deleted: …`,
  `already_gone: false` — and closed with **`mergedAt: null`**. The work landed only as **#1082**, after a
  re-push. Verified three ways by the plan, and #1082's merged state re-verified here.
  **`_github_pr.py` § `cmd_pr_merge`**: `gh_args = ['pr','merge',id,f'--{strategy}']` — **no
  `--delete-branch` passed to `gh`** — then `if returncode != 0: error`, then, **inside
  `if args.delete_branch:`**, `result['merged'] = True`, then a **separate REST branch delete**.
  ⇒ **Three defects on forty lines:**
  1. **`merged: true` derives solely from `gh pr merge` exiting 0.** Under a required merge queue that
     command **enqueues** and exits 0. **The filers' hypothesis is confirmed at the source**, and it is
     systematic under `use_merge_queue: true`. ⭐ Explains the narrowing contrast they flagged:
     `pr merge-queue` is honest because it is a **different function**. Per-verb mapping.
  2. ⭐⭐ **`merged` is set ONLY when `--delete-branch` is passed** — the success field's *presence* is
     coupled to an unrelated option, so `result.get('merged')` is `None` on a real merge without delete.
     **Opposite polarity, and neither filer saw it** — both observed the delete path. Found only by reading.
  3. ⭐ **The assertion precedes the destructive action**, under a comment asserting the very thing not
     established (*"The merge has already succeeded"*). Defending-documentation, at the site.
  ⛔ **`cmd_pr_safe_merge` carries the identical shape ⇒ ≥2 sites. The list is a SAMPLE** — `gitlab_ops.py`
  also emits `branch_deleted` and is unread.
  ⭐ **Leading causal hypothesis, NOT confirmed**: deleting the head branch **dequeues and closes the PR**,
  so the verb may **manufacture the failure it misreports**. ⚠ Competing: `gh` exited 0 without enqueuing.
  **Discriminator — observe queue state BEFORE any delete; re-reading #1081 cannot separate them.**
  ⇒ Absorbed into **PLAN-PR-009 as deliverable 0**, which is now the **emit head**. ⛔ **Stamp PR ids from
  PR state, never from a landing message** — the originating plan's landing message names #1081.

- ⛔⛔ **A MERGED PR IS NOT A COMPLETED PLAN — orchestrator error, operator-caught 2026-08-02.**
  `branch-cleanup` is step **9 of 12**; `record-metrics`, `archive-plan`, `plan-retrospective`,
  `sync-plugin-cache` and the operator dialogue report all run after the merge. I transitioned
  PLAN-PR-016 to `shipped` on **verified** `ci pr view` evidence that #1078 merged, while
  `manage-status list` showed `correct-review-scores-as-maximally-wrong` at `6-finalize / in_progress`.
  Reverted to `running`.
  ⭐ **The instructive part**: I had already hardened against trusting the landing message and replaced
  it with the PR state — **another wrong oracle**, which felt rigorous *because* it was first-party and
  verified. **Verifying a claim against the wrong artifact is indistinguishable, from the inside, from
  verifying it against the right one.**
  ✅ **THE COMPLETION ORACLE**: a plan is done when it **leaves `manage-status list`** (i.e. reached
  `archive-plan`). Confirmed by contrast in the same query — `barrier-override-not-head-bound` (#1077)
  is absent from the list and IS complete. Cheap, and it discriminates.
  ⇒ This also **corrects `review-apparatus-013`**, whose remedy anchored on the merge. Amendment filed
  as `review-apparatus-014`: **a terminal report must be a terminal action.** On #1077, ELEVEN of
  eighteen inbox messages postdate the "landing" by ~1h36m, so the summary cannot reference its own
  siblings and the drain splits into two disconnected halves.

- ⛔⛔ **`reviewed_commit_sha` NEVER advances for an edit-in-place bot — SOURCE-CONFIRMED 2026-08-02.**
  ⭐ **ANNOTATED 2026-08-23 — CLOSED FOR THE SINGLE-COMMENT PATH, AND THE CLASS IS STILL OPEN.**
  `PLAN-PR-013` shipped as **#1141**: `_has_update_movement` is gone, the credit is now a comparison
  against a recorded merge-candidate SHA held in a currency ledger, and the observer effect on one
  evidence comment is genuinely closed with tests that fail pre-fix. **What is still live** is the
  second-comment bypass — the participation loop short-circuits per bot and stages a ledger row only
  for the credited comment, so a second evidence comment has no history and credits at any advanced
  HEAD. Reproduced end-to-end against the shipped producer by two independent verifications. Row 1 of
  the live table above; owned by **PLAN-PR-024 D1**. ⚠ The rule is also applied to **one of three**
  registered bots while the contract claims it governs every crediting site (`PLAN-PR-024 D5`).
  From `barrier-override-not-head-bound-018`, and verified against the implementing source rather than
  accepted on report: `github_pr.py:783-785` `continue`s on the `(bot_kind, comment_id)` dedup;
  `reviewed_commit_sha` is passed **only** into `add_finding` at `:824`, below that `continue`; and
  `_findings_core.py:290-291` writes it at record creation with **no update path anywhere in the
  codebase**. Meanwhile `automatic-review/SKILL.md:245` asserts the opposite verbatim — *"this re-stamps
  every finding's `reviewed_commit_sha` to the new HEAD … no separate update call is needed."*
  pr-agent edits ONE persistent comment, so its `comment_id` is stable ⇒ **for pr-agent the documented
  re-stamp has never once happened.** Observed live on #1077 (`ae6c5615…` → `a2855290…`, sha frozen,
  `count_skipped_duplicate: 1`).
  ⚠ **I part-refute the reporting message's stated consequence.** It predicts a comparison against a
  two-generations-stale SHA. The *direction* matters: since the frozen sha can never equal live HEAD,
  the `head_sha == reviewed_commit_sha` skip at `SKILL.md:236` can **never be satisfied**, so trigger B
  re-fires on every advance regardless of whether the bot already re-reviewed. **Fail-CLOSED (redundant
  re-review), not a missed review** — materially less severe than filed, and it changes PLAN-PR-013's
  scoping. ⚠ Gated by `re_review_on_loopback` (default `false`; enabled in this repo).
  ⭐⭐ **THREE independent paths reached this mechanism** — msg `-018` (first-party), the sibling's
  `truthful-signals-010` § `lane-router-…-007`, and our own `review-apparatus-011`. Their synthesis
  (*the edit is DROPPED from findings while the movement it caused CREDITS participation*) was filed as
  HYPOTHESIS; **the dedup half is now OBSERVED. The movement half is still unverified and is ours.**
  → **PLAN-PR-013**, which must first check whether #1071's timestamp path supersedes the SHA read.

- ⛔ **`automatic-review/SKILL.md` documents a CLI surface the script no longer has — LIVE in merged
  main.** From `correct-review-scores-as-maximally-wrong-006`, explicitly filed as NOT fixed by #1078.
  Documented `--enabled-bots` / `--settled-bots` and returns `complete` / `unfetched_bots`; the shipped
  parser takes `--required-bots` / `--optional-bots` / `--participated-bots` / `--in-progress-bots` /
  `--refused-bots` and returns `participation_complete` / `unproven_bots` / `bot_states`. **Every
  documented invocation is an argparse rejection (exit 2)**; every documented return-field read resolves
  to nothing. Not cosmetic — the two vocabularies model different things.
  ⭐ **Paired with the `ci pr view --pr-number` drift found this session** (see
  `findings/2026-08-02-erroring-poll-reads-as-negative.md`): **two CLI-vs-doc divergences in the
  review/merge path, both producing exit 2 on every documented invocation. That is a population.**

- ⛔ **A leaf can return a finding in its TOON and persist nothing.** From
  `correct-review-scores-as-maximally-wrong-007`: `pre-submission-self-review` pass 3 found a genuine
  defect, returned it, and never wrote it to the qgate store — so it lived in transcript, not state, and
  nothing downstream (blocking-findings gate, triage, finalize summary, retrospective) could see it.
  ⭐ The return path and the persistence path are independent and only one is durable: a leaf can be
  fully successful by its own contract while contributing **zero** to the state the pipeline gates on.
  Silent both ways — nothing errors, and the finding *appears* reported to whoever is looking.
  ⚠ Kept here (not delegated) because self-review is this epic's local-review surface.

- ⚠ **An erroring poll is indistinguishable from a negative poll** — see
  `findings/2026-08-02-erroring-poll-reads-as-negative.md`. #1077's merge-queue waiter polled an
  invalid-flag command for 30 min; the PR had already merged. ⛔ A never-succeeding poll **launders
  itself into a legitimate-looking timeout**, which is an authorized reason to proceed. → PLAN-PR-009,
  whose spec must be re-read for whether it assumes the *enqueue* is the only failure point.

- ⚠ **Executor strips falsy args — real mechanism, ALREADY HANDLED by PLAN-PR-014. Open residual only.**
  ⛔⛔ **This entry previously claimed PR-014's remedy was REFUTED and needed urgent relay. That claim was
  WRONG and is withdrawn — it was filed from the spec's wording without reading the shipped branch.**
  Recorded as an error, not silently deleted: it is the epic's own *"a claim is a lead, not a fact"* rule
  broken by the orchestrator, on the same day it wrote that rule into a sweep document.
  **What is TRUE**: the executor strips every falsy argument (`.plan/execute-script.py:988-989`,
  generated from `tools-script-executor/templates/execute-script.py.template:768`), so `--flag ""`
  reaches argparse as a bare `--flag`.
  ✅ **What PR-014 actually shipped handles exactly that** — `nargs='?', const=''` on all five flags
  (`review_completeness.py`), so a bare flag is now VALID and reads as the empty list, PLUS an
  UNKNOWN-verdict branch recording `loop_back` on any non-zero exit. The quoting was added alongside;
  the `nargs` change is what is load-bearing. **No correction is owed to that plan.**
  ⭐ **The genuine residual**: PR-014 hardened *its own* five flags at two sites. The generator-level
  strip still converts `--flag ""` to a bare `--flag` for **every other** marketplace script with an
  optional flag that lacks `nargs='?'`. Whether any such site is reachable with an empty value is
  **UNMEASURED** — a population question, not a known defect. ⛔ Do not restate it as one.
  Full write-up: [`findings/API-Sheriff-PR-138.md`](findings/API-Sheriff-PR-138.md) § 1.

- ✅ **RETIRED 2026-08-08 — `refused_hard` fall-through: HALF REFUTED, remainder RE-HOMED to `PLAN-PR-006`.**
  All three bots now declare `rate_limit_class` (coderabbit `awaitable_window`, sourcery `hard_quota`,
  pr-agent an explicit `unknown`), so the *absent-field* half is fixed. What survives — `review_completeness.py:237`
  is a binary over a three-valued field, so a declared **unknown** renders as *"refused_hard (hard quota)"* — is now
  a deliverable of PLAN-PR-006's absence-cause partition. ⛔ Do not re-open here; the spec is the authority.

Live and unowned only. ⛔ **Everything with an owning spec has been relocated** — the spec is the
authority, and duplicating a defect write-up here is the source-of-truth-duplication archetype
`PLAN-PR-003` exists to fix. Resolved entries: [`decisions-archive.md`](decisions-archive.md).

- ⛔⛔ **The pre-merge review barrier does NOT fail closed when its own producer call dies — CONFIRMED
  ON A MERGED PR (#1071), no owning plan.** From inbox `-008`, reconciled against the operator's own
  correction of that artifact:

  | Predicate | Verdict at merge | Basis |
  |---|---|---|
  | 1 — zero pending `pr-comment` findings | ✅ **evaluated** | operator re-ran with correct flags, `status: success`, pending 0 |
  | 2 — required-bot participation vs this HEAD | ⛔ **never ran** | the executed (stale-cached) doc has no Predicate 2 at all |

  ⚠ **The plan's own retrospective claimed BOTH were unevaluated; that OVERSTATES it and the operator's
  correction is accepted.** But the corrected version is not an all-clear: a required-bot participation
  predicate was **structurally absent at merge**, and `branch-cleanup` still recorded
  `outcome: done, "merged PR #1071 via queue"`. ⭐ **Same archetype PLAN-PR-014 just fixed, one door
  over** — a producer call exits non-zero and the step records success. PR-014's shipped pattern
  (`nargs='?'` + an UNKNOWN-verdict `loop_back` branch) is the model to copy.
  ⛔ **The ROOT CAUSE is delegated, not ours**: the stale plugin cache made the step execute a
  four-day-old `branch-cleanup.md`. Owned by `truthful-signals` (msg `review-apparatus-008` § 2).
  **Fixing the barrier without that signal leaves the next stale cache free to disarm a different gate.**
  ⇒ Belongs in **PLAN-PR-008**'s scope (it owns the barrier predicates), not a new plan.
  Also from `-010`: the barrier logs nothing on the clean path, so **silence is ambiguous between
  "passed" and "never ran"** — in #1071's 86-entry decision.log there is no barrier line at all. The
  general form of that rule is delegated; the barrier-specific one stays here.

- ⛔ **PR-Agent's "## PR Reviewer Guide" boilerplate is missing from its registry `ignore_patterns`**
  (`automatic-review/standards/pr-agent.md`) — so it survives the producer pre-filter and is filed as a
  **pending hand-triage finding on every PR PR-Agent reviews**. Fix is ONE data row; the pre-filter
  already consumes the list. ⛔ **Do NOT land it alone** — see the paired defect below.

- ⛔ **review-retrospective maps `resolution: accepted` → `false_positive`**, so on a clean PR
  PR-Agent's sole meta record scores it **100% false-positive / 0.0% resolved-as-fixed** — precisely
  when it behaved correctly. Silent: the numbers are well-formed, only the denominator is wrong.
  ⭐⭐ **PAIRED WITH THE ROW ABOVE — SEQUENCE DELIBERATELY.** They touch the SAME comment. Filtering the
  Guide at the producer makes PR-Agent's clean-PR record **empty** rather than one-accepted, which
  *changes this defect's shape rather than fixing it*, and may flip a participation detector to
  non-participation. ⛔ Neither subsumes the other; landing either alone converts one wrong metric into
  a different wrong metric. ⇒ These two are ONE plan, not two.
  ⚠ Directly contradicts nothing in [`2026-08-01-sweep-4day.md`](findings/2026-08-01-sweep-4day.md), but
  it does explain why that sweep's per-reviewer quality numbers must never be taken from
  `pct_resolved_as_fixed` alone.

- ✅ **RETIRED 2026-08-08 — `post_responses` non-idempotency: OWNED by `PLAN-PR-019` since 08-03.**
  The entry still read *"no owning plan … left unstaged deliberately"* six days after the plan was staged.
  Its full diagnosis — the inverted `verification-feedback.md` Step 8 rationale, and the Sonar reference
  implementation (`mark_finding_responded` / `finding.get('responded')`, the `grep responded` parity trap) —
  is relocated INTO that spec. ⭐ Re-verified first-party at HEAD this drain: `cmd_post_responses` (`:1333`)
  still has no prior-transmission term.

## Watches

### ✅ WATCH CLOSED 2026-09-15 (operator decision) — ex "we are wholly Tier 1, and this epic's defect list IS the Tier 1 trade billed back to us"

⛔⛔ **PREMISE REFUTED BY THE OPERATOR — do not re-open on the original framing.** The apparatus is already
hybrid: **Tier 1** = CodeRabbit + Sourcery, **Tier 2** = pr-agent (`cuioss-review-bot`, org CI, our model
ladder and charter), plus the in-house finalize self-review. "Adopt Tier 2" was never an open decision.

⭐ **The only residual question was merge-gate composition, and it is DECIDED: CodeRabbit stays a REQUIRED
reviewer until pr-agent achieves similar review quality — which the operator states is not yet the case.**
No fallback, no bypass policy, no gate change; the unattended CodeRabbit recovery protocol stays in force
unchanged. Config agrees (verified 2026-09-15): `.plan/marshal.json` `required_bots:
"cuioss-review-bot,coderabbit"`, `optional_bots: "sourcery"`. **Reopen condition**: pr-agent review quality
comparable to CodeRabbit's, **measured by the existing comparison protocol** —
[`review-practice.md`](review-practice.md) § 1 (the comparative deficit rule and its four scoring outcomes,
run at every post-merge PR revisit). ⛔ An earlier draft of this note claimed no such instrument existed —
REFUTED by the operator; that protocol is it. Decision logged in `decision.log`.

The original watch text is kept below for its evidence (the four vendor-runtime defects remain real and
remain owned by their specs):

From `next-level-001` (sibling orchestrator, relaying *Spec-Driven Production Grade Development in the
Age of Vibe Coding*, Boonstra, May 2026). ⚠ **An outside document: the tier model is asserted, not
measured, and the one supporting anecdote carries no figure.** The reason it is filed here anyway is
that its diagnosis is checkable against **our own record**, and it holds.

The model splits continuous automated review by **who owns the runtime and who writes the criteria** —
**Tier 1** managed SaaS (*"you get the vendor's review opinions, not yours"*), **Tier 2** hybrid (a
review skill committed to the repo, run by our CI via a coding-agent CLI in non-interactive mode, on a
model we choose), **Tier 3** custom deployed agent with durable memory.

⛔ **The argument that earns the watch**: every one of these is a property of NOT owning the runtime,
and all four are already in this ledger — CodeRabbit's one-review-per-hour window that **resets on
every trigger**; a refusal arriving as an **in-place comment edit** invisible to `movement_matched_bots`;
a run **reporting a review that never ran** (`count_stored: 0` read as reviewed-and-clean); and a
vendor-side `bot_kind` rename that invalidated consumer config fleet-wide with no propagation
mechanism, leaving TokenSheriff permanently merge-blocked. ⇒ **None is fixable inside Tier 1**, and the
standing rule that a CodeRabbit review is mandatory makes that dependency load-bearing on the merge path.

⚠ **What it does NOT argue, kept because it is the honest half**: not leaving Tier 1 — the managed
reviewers find real findings, and a self-owned reviewer grading its own repository has an independence
problem a vendor does not. The credible reading is **Tier 2 ALONGSIDE Tier 1**, covering house-specific
criteria and removing the single points of failure from the merge gate.

⛔ **Filed as a Watch, not staged.** It is a scoping question the message deliberately does not settle,
and it would be the largest architectural decision this epic has taken. **Surfaced to the operator
2026-09-14; awaiting a decision.** Note the standing-rule collision if it is ever taken: the
unattended-recovery protocol (≥90-min sleeps, max 10 waits, close-and-reopen) exists to survive a
constraint Tier 2 does not have.

### ✅ LANDING 2026-09-14 — `PLAN-PR-065` shipped #1491, 10/10, and the FOREIGN half landed as `pr-agent-settings` #64

Full record: [`landings/PLAN-PR-065.md`](landings/PLAN-PR-065.md). Landing `complete: true`; `#1491`
corroborated first-party (`ci pr view` → `merged`).

⭐⭐ **The plan repaired its own instrument BEFORE using it** — D1 made `ci pr list` derive a complete
population instead of a page (the exact defect this orchestrator hit at staging, when the verb returned
30 rows against an operator-reported 46), and only then did D2 derive the population and D3 close
against it. The gate that decided what to close was fixed before it decided anything.

⛔ **The review coverage of #1491 is a recorded BYPASS, not a clean review.** Bot review was explicitly
skipped by operator decision (empty rosters, `skip-bot-review`). `0 comments found` here means **nobody
looked** — which is precisely the conflation `PLAN-PR-061` exists to end, and the ledger must never
later read it as evidence of quality. ⚠ The retrospective's own `indeterminate` over a "roster of 3"
was a **false alarm**: it reads rosters from `marshal.json` rather than the plan's step-params
override. Transferred.

⛔⛔ **Declared vs realized diverged in BOTH directions for the first time**: 19 declared against a
13-path realized footprint, not nested — 5 realized-but-undeclared (including `branch-cleanup.md`, a
fix task appended during execute) and **4 declared-but-never-realized** (the GitLab half of the
`--limit` contract, declared in scope and never touched). ⇒ Fourth consecutive landing with the drift,
and over-declaration is the more dangerous half for this epic's gate: a spec that declares what it will
not touch makes the disjointness check sequence siblings behind files nothing ever claims.

⭐⭐ **Promoted as lesson `2026-09-14-19-001`** — the run's best finding: D1 fixed a producer while
`branch-cleanup.md`'s Safety Check, **the consumer gating a branch DELETION**, still read a bare count
with no `--limit`. A page read as a population, in the exact code path the deliverable existed to
correct. The scope-criterion validator caught it; **nothing in the outline's own success criterion
would have.**

⭐ **`PLAN-PR-039`'s precondition is DISCHARGED** — `packs/` exists on that repository's `main` for the
first time. ⛔ It stays unemittable for a *different* reason, and its `prose` surface was deliberately
NOT corrected: the exemption is named, and inventing a plan-marshall path to move the metric would
destroy the foreign-only property that makes WS-02 disjoint by construction. Emitting it is an operator
decision to accept a candidate the gate cannot check.

**Drain 22/22 archived** — `-017` promoted; `-001`…`-016`, `-018`…`-020` transferred to
`truthful-signals` as `review-apparatus-041.md` (an invocation-discipline cluster of **ten rejections in
one run**, three of them the same mistake repeated after the correct form had been displayed — plus
`-014`, which is NOT discipline but a real tooling defect: the generated executor rejected a flag the
dispatched script declares, and two regenerations did not clear it); `next-level-001` is the Watch above.

### ⛔⛔ WATCH 2026-09-13 — the marker gate `PLAN-PR-046` just shipped is UNEXERCISED, and it fails CLOSED

From `plan-pr-046`'s own finding `-001` item 3: **the declared `recent_review_start` marker is ABSENT
from CodeRabbit's live summary comment on #1477.** So the `issue_comment` credit gate that plan shipped
is **not exercised in production**, and its canonical layout is pinned by **no observation**.

⇒ The failure direction is **fail-closed**: a verdict comment without the marker resolves a clean review
`absent`, **which blocks a merge**. Every plan now relying on a CodeRabbit clean review to clear its
barrier inherits that, and the first evidence will be a blocked merge, not a report.

⭐ **The plan's judgement stands and is not to be re-litigated**: it DECLINED CodeRabbit's *"anchor the
marker"* Major **twice**, because tightening an unanchored match against a layout nobody has sampled is
the larger, less reversible risk. ⇒ **The open action is to SAMPLE the live layout, not to tighten the
match.** Assigned to `PLAN-PR-058` D0 (it already re-grounds the credit surface); until then, treat a
`absent` clean-review verdict on a CodeRabbit-reviewed PR as suspect rather than as a finding.

### ✅ LANDING 2026-09-13 — `PLAN-PR-046` shipped #1477 (`77cb2e251`), 5/5, and BOTH SLOTS ARE NOW FREE

Full record: [`landings/PLAN-PR-046.md`](landings/PLAN-PR-046.md). Merged squash through the merge
queue; landing `complete: true`; corroborated first-party (`ci pr view` → `merged`, `git show --stat`
→ 31 files).

⭐⭐ **Three refusals to publish a number, all correct** — this is the behaviour the epic exists to
produce: `gate_tree_unsubstantiated` with `structural_share: null` (three distinct
`reviewed_commit_sha` values across loop-backs, so no tree was ever reviewed whole);
`permission-prompt-analysis` recorded `coverage: not_evaluated` rather than letting an empty list read
as a clean zero; `branch-cleanup` recorded NO `merge_mechanism` fact because it merged nothing — the
absent key is the honest signal.

⚠ **Against that**: `check-manifest-consistency` graded `branch_cleanup_changes` **fail over no
evidence** while reporting `diff_available: true`, on a post-merge empty diff — transferred to
`truthful-signals`.

⛔ **Cost: 6.77M tokens / 5h07m worked against a 1.3M / 90-min anchor — 5.2×, finalize 48.5%.** The
overrun is the review loop, not the change (self-review 7×, quality-gate 5×, automatic-review 4×). Six
operator-mandated 90-minute waits, and **every trigger RESET CodeRabbit's window** (20 → 48 → 52 min).
Fourth consecutive plan whose dominant cost is the review window.

**Drain, 14/14 archived** — 11 from `plan-pr-046` plus three foreign senders that arrived in the same
window. Dispositions: `-011` landing reconciled · `-001` split — the stale-refusal sampling to
`PLAN-PR-052` 3a (**third** sighting of one mechanism: a missed wake, a wrong recovery, and now a spent
90-minute operator wait) and the unmatched ETA phrasing to `PLAN-PR-043` D7 (**fifth** phrasing, and it
differs from the fourth only in its number — the decisive argument that the pattern set is the wrong
shape) · `truthful-signals-055` split three ways — `5cbc17` (a vacuous `review_commitments` clear) to
`PLAN-PR-030` D4, `f0bd9d` to `PLAN-PR-056` D6's audit half, `10f565` (optional bots counted as
unproven) to `PLAN-PR-048` D0b · `truthful-signals-056` item 1 to `PLAN-PR-029` (a prefix pattern
deciding the disposition of a whole document: `actionable_count` read 15 where the substantive output
was 17, and the round's most consequential Major was in neither the count nor the escape set) ·
`plan-truth-139-001` to `PLAN-PR-048` D0b · `-007`/`-008`/`-009`/`-010` promoted as lessons
`2026-09-13-20-005` … `-008` · `-002`…`-006` transferred to `truthful-signals` as
`review-apparatus-038.md`.

⛔⛔ **`PLAN-PR-057` D1 ABSORBED a fold rather than taking a thirteenth row, and the displacement is
recorded**: `PLAN-PR-048` D0b is the INVERSE direction of D0 (a genuine clean verdict read as NO
participation, into a `participated_stale` **no available action can clear** — the quorum becomes
structurally unsatisfiable and the gate can only block or be overridden). D1 is now that plan's
heaviest deliverable; if its D0 finds the two directions need separate mechanisms, **split D1 and drop
something else** rather than shipping half a classifier.

⚠ **Second consecutive landing whose realized footprint exceeded its declaration** (10 undeclared files,
threshold 5). `reconcile-scope` detects it; nothing in finalize calls it.

### ✅ LANDING 2026-09-13 — `PLAN-PR-033` shipped #1473 (`38af136ed`), and it shipped ANOTHER PLAN'S DELIVERABLE

Full record: [`landings/PLAN-PR-033.md`](landings/PLAN-PR-033.md). 2/2 deliverables, 23/23 steps,
merge-queue landing, `cleanup_owed=false`, landing message `complete: true`. PR state corroborated
first-party via `ci pr view` (`state: merged`) and `git log` — not taken from the narrative.

⛔⛔ **THE FINDING: the realized footprint was 28 files against a declaration of 14, and the undeclared
half discharged `PLAN-PR-056` D6.** Under an operator-directed in-PR scope expansion at that plan's
merge gate, #1473 also fixed the `head_sha_verified` issue-comment defect — `github_re_review.py` now
decides it through `_verifies_head_sha` over the comment BODY. Verified first-party in the code at
`38af136ed`, not inferred. ⇒ **A staged plan's deliverable was completed with no ledger row moving**,
and the disjointness gate — which compares DECLARED surfaces — could not see any of it.

- `PLAN-PR-056` D6 re-scoped in place to the **audit half** (confirm the fix reaches every consumer),
  with its claim stamped `contradicted` / `rescoped: yes` at `38af136ed` through `corpus set-verdict`.
- `PLAN-PR-058` D6–D9 flagged for re-grounding: the same PR shipped a `--measured-diff-size` bare-flag
  fix with a 404-line failing-first test, on that plan's surface. ⛔ Its D0 derives what remains rather
  than assuming either way.
- ⚠ **The clean 033/046 pairing is NOT evidence the gate was right** — it is evidence the undeclared
  half happened not to intersect PR-046's. Recorded so the next pairing does not read it as a pass.
- ⚠ `reconcile-scope` already detects this drift and **nothing in finalize calls it** — unowned.

**Drain, 9/9 messages, all archived.** `-008` landing reconciled above · `-003` (`852b0f`, a thread
acknowledgement credited as a fresh review — a false green on the merge gate, **live on main**) folded
to `PLAN-PR-057` D1 as a FOURTH artifact class · `-004` (`658eec`, `wait-for-comments` samples the
newest comment by CREATION time so an in-place refusal edit is invisible, **live on main**) folded to
`PLAN-PR-057` D10, which now has its mechanism located · `-002` (a required bot gated the whole run
while producing nothing actionable) folded to `PLAN-PR-061` D4 as a fourth instance · `-005` (the
quota window priced in-run remediation out of reach) folded to `PLAN-PR-056` D8 · `-001` and `-007`
promoted to the corpus as `2026-09-13-09-001` / `-002` · `-006` transferred to `truthful-signals` as
`review-apparatus-037.md` at its sender's own routing request (not this epic's charter) · `-009`
recorded as the Open Defect below.

⛔ **OPEN DEFECT (`2343b2`, resolved `accepted`, live)** — `ci --plan-id {plan} pr view` returns
`error_cause: auth_failed` while `gh` is genuinely authenticated (`ci_health verify` confirmed it, and
the same read via `--plan-id NO_PLAN` returned `merged`). The real condition is a **worktree-resolution
failure**: `branch-cleanup` removed the worktree but left `metadata.use_worktree` / `worktree_path`
pointing at it. It matters because `output-template.md` routes `auth_failed` into the UNANSWERED arm →
`[FAILED]` **over a cleanly merged PR** — the arm that exists to prevent a false green manufactures a
false red. ⛔ It also contradicts the documented resolver contract, which promises a
`WorktreeResolutionError` refusal rather than a degrade. Shares a root with the already-tracked
`bd825d` (stale metadata blocking archive); fixing only the classification leaves the resolver failing
on a path that no longer exists. **Unowned by any staged spec** — it is `tools-integration-ci`, not
`automatic-review`.

### ⭐⭐⭐ REDISTRIBUTION 2026-09-12 — the staged corpus regrouped into 9 composed plans (operator-directed)

**Operator decision: the scope-bloat split guard is raised from ~6 deliverables to 12, and staged work is
grouped by shared target surface.** ⛔ This supersedes the ~6 presumption for THIS epic's staging and
folding decisions; the marketplace standard is unchanged and a future fold here is measured against 12.

⭐ **The derived arithmetic changed the approved map, and the change is recorded rather than absorbed.**
The 19 staged specs carried **~105 deliverables**, so a 12-ceiling needs **9** plans, not the 7 the
operator's option sketched at "~12 each". Whole specs were never split across plans — the re-pairing
took the count, not the axis.

| New plan | Absorbs | Deliverables | WS |
|---|---|---|---|
| `PLAN-PR-056` the refusal-recognition and re-trigger stack | `PLAN-PR-043` + `PLAN-PR-045` | 12 | WS-01 |
| `PLAN-PR-057` a bot that could not review, and the refusal that says so | `PLAN-PR-048` + `PLAN-PR-052` | 12 | WS-01 |
| `PLAN-PR-058` the coverage ledger and the gate its callers cannot invoke | `PLAN-PR-053` + `PLAN-PR-051` | 10 | WS-01 |
| `PLAN-PR-059` what the pipeline loses on the way IN | `PLAN-PR-029` + `PLAN-PR-040` | 10 | WS-03 |
| `PLAN-PR-060` what the pipeline drops on the way OUT | `PLAN-PR-035` + `PLAN-PR-031` | 11 | WS-03 |
| `PLAN-PR-061` reviewed-at-all, and the numbers computed from it | `PLAN-PR-026` + `PLAN-PR-047` | 12 | WS-03 |
| `PLAN-PR-062` the instruments that measure our own gates | `PLAN-PR-030` + `PLAN-PR-049` | 10 | WS-03 |
| `PLAN-PR-063` the finalize record and the disposition it carries | `PLAN-PR-050` + `PLAN-PR-037` | 12 | WS-03 |
| `PLAN-PR-064` a landing that cannot outrun its merge — restored | `PLAN-PR-028` whole; supersedes `-054` + `-055` | 7 | WS-04 |

⭐ **`PLAN-PR-039` is deliberately NOT absorbed** — its surface is foreign-repo-only and overlaps nothing
in this corpus, so grouping it with anything would manufacture a collision that does not exist.

⛔ **NO deliverable body was retyped.** Per the operator's authoring choice, each composed plan carries
the objective, the deliverable ROSTER with a pointer per row, the consolidated Expected Surface and the
sequencing; every body stays in its source file, which is retained and now carries a `SUPERSEDED` header
naming its successor and the D-number mapping. This is the `PLAN-PR-028` → `540a`/`540b` precedent
applied corpus-wide, and it is what keeps reconstruction drift out of a 105-deliverable move.

⚠ **TWO bodies were MERGED by judgement, and both are named rather than silently folded**: `PLAN-PR-052`
D3 + 3a → `PLAN-PR-057` D10 (one subject stated twice — the mutable refusal as an archival problem and
as a live-wait problem); `PLAN-PR-026` D1 + `PLAN-PR-047` D0 → `PLAN-PR-061` D1 (the same artifact from
the producing and the consuming side). ⛔ Both are NUMBERING changes: every *Done when* clause stands.

⛔⛔ **THE 18 SUPERSEDED ROWS ARE RECORDED `parked`, AND THAT IS NOT WHAT THEY ARE.** The queue cannot
express `retired`: `orchestrator.py`'s `VALID_STATUS_VOCABULARY` is
`{staged, launched, running, parked, shipped, landed}` and `--transition` refuses `retired` with
`invalid_field` — **while four rows in this very ledger already carry it** (`PLAN-PR-004`, `-018`,
`-025`, `-028`, written by the unvalidated bulk rewrite before the single-row forms existed). `parked`
is the only expressible non-emittable state and `next` walks `staged` only, so the queue is SAFE; it is
not TRUE. The real status lives in each spec's `SUPERSEDED` header, this table, and `logs/decision.log`.
⛔ The bulk `update-field --field plans` rewrite was **refused** as the alternative — re-serialising 66
rows to change 18 is the lost-update path the single-row forms exist to remove. **Filed to
`truthful-signals` as `review-apparatus-036.md`** (2026-09-12); it is not this epic's to fix.

⭐ Parser-verified after the move, not asserted: `corpus enumerate` 66/66 both directions; `corpus
surfaces` 63 declarative / 3 prose over 66, and **all nine new specs `declarative` with `unresolved: 0`**
(claimed counts 19/15/15/22/14/13/24/17/23); `corpus verdicts` `blocking_count: 0` over 374 claims with
**66/66 claim sections parsed**.

### ⭐ DRAIN 2026-09-11 — `truthful-signals-054.md` (finding, 8 items + 1 FYI) — disposition `folded`

Forwarded by `truthful-signals` from two consumer-repo lessons drains (API-Sheriff `deployment-configurability`,
Token-Sheriff `lessons-handling-26-09-04-01`). Every mechanism claim re-read first-party at HEAD `356973d80`
before any write. Per-item routing — **no new spec staged, no queue row touched**:

| Item | Disposition | Destination | Surface |
|---|---|---|---|
| 1(b) `issue_comment` re-review reads as decline | recurrence | `PLAN-PR-043` D5a | unchanged |
| 1 correction — `fetch_findings` stamps the PR head, parses no comment | **remedy direction REFUTED**, recorded | `PLAN-PR-043` D5a | unchanged |
| 1(c) clean review + `coveredCommitId == HEAD` read as never-reviewed | recurrence | `PLAN-PR-053` D2 (+ watch below for `PLAN-PR-046`) | unchanged |
| 1(d) + 2 barrier remedy inert under `re_review_on_loopback: false` (69 s explicit re-trigger) | recurrence + added *Done when* | `PLAN-PR-043` D7 limb C | **+1** `branch-cleanup.md` (HYPOTHESIS) |
| 1(e) fresh PR reviewed outside the exhausted window vs `SKILL.md` Branch 5 | **contradiction DISSOLVED** — see below | none | — |
| 3 CodeRabbit "Already reviewed the last commit" + no `full review` form | sharpening + added *Done when* | `PLAN-PR-052` D1 | **+1** `github_re_review.py` |
| 4 Fair-Usage ETA vs blanket ≥90-min floor | recurrence | `PLAN-PR-043` D7 limb A | unchanged |
| 5 reviewer rebuttal landed after FIND closed, never filed | **WATCH** — below | none | — |
| 6 triager's own mechanism claim asserted unverified (×2) | recurrence on corpus lesson | `2026-09-03-16-001` § Recurrences | n/a |
| 7(a) two-axis triage `fix_correct` / `premise_verified` | recurrence on corpus lesson | `2026-09-03-16-001` § Recurrences | n/a |
| 7(b) `branch-cleanup.md` clean line states an unscoped zero | sharpening + added *Done when* | `PLAN-PR-026` D3a | unchanged |
| FYI `-039` stale `--settled-bots` prose | discarded (not reproducible at HEAD) | none | — |

⭐ **1(e) — why the contradiction dissolves rather than needing a measured check.** `automatic-review/SKILL.md`
§ Branch 5 already states that a fresh PR buys back no quota **and** that the one observed successful reopen
worked *only because the window had already elapsed*. The sender's own observation places the fresh-PR review
**outside** the exhausted window — which is what that passage predicts, not a counter-instance. It would
become one only if a fresh PR were reviewed INSIDE a still-closed window; the sender does not claim that.
Same reconciliation this ledger reached on `truthful-signals-045` §2.1.

⚠ **WATCH (item 5) — does anything re-observe a reviewer's reply to our disposition?** Relayed, single
sighting (Token-Sheriff `lessons-handling-…-031`): FIND closed 18:13:09Z, CodeRabbit's rebuttal to a WRONG
dismissal landed 18:28:23Z and was never filed; found only by a hand check. ⛔ **The "nothing re-checks" half
is partly CONTRADICTED at `356973d80`**: the pre-merge barrier re-fetches from the provider and blocks on any
unhandled comment (`automatic-review/SKILL.md`, the `re_review_on_loopback` default rationale). **Open
question, not settled:** does that re-fetch file a reply posted INSIDE an already-dispositioned thread as a
new finding, or does the responded marker absorb it? Confirm/refute at `github_pr.py` § `cmd_fetch_findings`'s
thread/comment dedup against the `responded` marker. ⛔ Filed as a watch, not a spec: staging on a relayed
mechanism the first-party read half-contradicts would ship against an unverified premise. Nearest owners if
it hardens: `PLAN-PR-029` (loses findings) / `PLAN-PR-035` (response path).

⚠ **WATCH (item 1(c)) — check at the `PLAN-PR-046` landing.** 046 is launched, so nothing was folded into
it. When it lands, check whether it credits the *"No actionable comments were generated"* shape **and**
reads `coveredCommitId` (zero readers in `marketplace/` at `356973d80`); whatever it leaves is
`PLAN-PR-053` D2's.

### ⭐ WATCH 2026-09-04 — a review bot reasons over NAMES, not over the symbol graph

From `truthful-signals-045.md` §2.9 (foreign LEAD, not corroborated here). CodeRabbit proposed re-pointing
an ADR reference from `DecodingStage` to `NormalizationStage`, reasoning that Unicode normalization belongs
to the class **called** `NormalizationStage`. **The source said the opposite.**

⭐ *"A review bot reasons over names and diff context, not over the symbol graph."* **Wherever two
similarly-named classes do not partition responsibility the way their names suggest, this class of
confidently-wrong suggestion recurs.** Verify by locating the actual call/symbol; reply with symbol-level
evidence rather than a bare disagreement.

⚠ Filed as a **Watch, not a spec**: it is a property of LLM reviewers rather than a defect in our
apparatus, so there is nothing here for us to fix — but a triage pass that accepts such a suggestion on
its face will regress the code it touches.


Open questions only. Retired watches: [`decisions-archive.md`](decisions-archive.md).

- ⭐ **NEW 2026-09-02 — A HEAD-BOUND MERGE AUTHORIZATION OVER A ONE-STATEMENT DELTA, IN A USING
  PROJECT.** Operator paste, recorded as an instance rather than a defect: a merge authorization was
  granted and it was **HEAD-bound**. Both required bots had reviewed the substantive diff but **not
  the final one-statement delta**; `sourcery` — an OPTIONAL bot — approved that delta, and the merge
  queue re-tested against `main`.

  ⭐ **The machinery behaved as designed.** `merge_authorization` is HEAD-bound AND gap-class-bound
  (`{head, gap_class, granted_over}`, `_cmd_merge_authorization.py`), so the accepted gap is recorded
  structurally, not merely in prose. Nothing here is a malfunction; the entry exists because the
  epic's subject is what a confident signal leaves unsaid.

  ⛔⛔ **DO NOT ADD THIS TO THE n=5 COVERAGE INVARIANT POPULATION.** That invariant ("the REQUIRED bot
  contributed nothing; an OPTIONAL bot carried whatever review happened") was derived over
  **plan-marshall** PRs. This observation is from a **using project**, and it is a **partial
  counter-instance in one direction and a confirming instance in the other**: the required bots DID
  review — of the substantive diff — while the delta that actually merged was covered only by the
  optional bot. Mixing the populations would let a foreign instance move a local invariant.

  **The open question:** the barrier's HEAD-binding is all-or-nothing — it cannot distinguish *"the
  reviewed diff differs by a one-statement delta"* from *"the reviewed diff is stale in substance"*,
  so a trivial post-review commit's only remedy is an override that discards the whole binding.
  Whether that is worth grading is NOT decided here; n=1, second-hand, and no counterfactual exists.
  ⛔ Do not stage a delta-grading plan off this entry alone — it would weaken a barrier this epic
  spent PLAN-PR-014/-015/-024 hardening.

- ⛔⛔ **NEW 2026-08-26 — ON TWO CONSECUTIVE PRs THE EXTERNAL REVIEWER SET CONTRIBUTED NOTHING, AND
  BOTH TIMES THE BARRIER REPORTED A COMPLETED ROUND.** Two independent observations, one first-party
  and one forwarded:

  | PR | Required (`pr-agent`) | `coderabbit` | `sourcery` | Barrier said |
  |---|---|---|---|---|
  | **#1349** (ours, first-party) | contentless | \| 1 empty / 2 refused — no bot produced a finding | | round complete |
  | **#1340** (forwarded, `truthful-signals-037`) | empty clean guide | **credited on STALE evidence** (rate-limited off final HEAD) | **reviewed nothing at any point** — one size refusal, then silence across six HEADs | `participation_complete: true` |

  ⭐ **On #1349 the in-house `pre-submission-self-review` found FIVE real defects to the bot set's
  zero** — including `5de248`, a live bug where a **lexicographic timestamp compare ranked `-05:00`
  before `Z`**, so the guard fired on comments that post-dated the commit; and `906944`, a hole in the
  merge barrier's own positive-validation enumeration, in a document that argues that exact case
  eleven lines below.
  ⛔ **This does NOT retire the reviewer-plurality evidence — it re-frames it.** The standing record
  (#1336/#1337/#1338/#1343) is that CodeRabbit catches what pr-agent misses. Both new observations are
  consistent with that AND with something sharper: **the failure mode is REFUSAL AND STALENESS, not
  reviewer quality.** On #1349 two of three bots never read the diff; on #1340 one was credited off a
  superseded HEAD and one never reviewed at all. ⇒ The lever is coverage, not roster composition.
  ⭐ **Sizes PLAN-PR-026 D3** (folded there: a required set of ONE whose member's default output is
  contentless renders identically to an empty set) **and PLAN-PR-025 D7** from the other direction —
  a quorum of one cannot be a quorum. ⛔ n=2; do not read it as "the bots are useless".

  ⭐⭐ **RECURRENCE 2026-08-29 — #1361, and this one is FULLY RE-DERIVED FIRST-PARTY.** Drained from
  `truthful-signals-039.md`, which forwarded #1361 alongside #1359 and explicitly weakened its own
  earlier "single data point, drawing no conclusion" caveat. The sender labelled its figures
  **OBSERVED but NOT re-derived** and asked for corroboration before acting; that corroboration was
  performed here against the PR itself, and **every material claim held**:

  | Reviewer | Marked | First-party observation on #1361 (`ci pr comments`, HEAD `a1cae6102`) |
  |---|---|---|
  | **pr-agent** (`cuioss-review-bot`) | **REQUIRED** | 2 `issue_comment`, **both empty** — "⚡ No major issues detected" and "PR Code Suggestions ✨ No code suggestions found". **0 actionable.** |
  | **CodeRabbit** | optional | **20 rows** (16 `inline` + 2 `review_body` + 2 `issue_comment`) — the entire actionable yield |
  | **Sourcery** | optional | **1 `review_body`, a refusal**: *"your pull request is larger than the review limit of 150,000 diff characters"* — reviewed nothing |

  ⇒ **The coverage invariant is now n=5** (#1340, #1349, #1356, #1359, #1361), up from n=4: the
  REQUIRED bot contributed nothing in all five, and an OPTIONAL bot carried whatever review happened.
  ⛔ Read it precisely, as before — this is a claim about **COVERAGE AND ROSTER**, not model quality:
  *a required set of one whose member is reliably empty is a gate that cannot fail.*

  ⭐ **The 150,000-character cap is now corroborated VERBATIM from the refusal body** (previously
  carried as a figure). And it bites far below what line count suggests: #1361 is **2,857 changed
  lines across 18 files** (`git show --shortstat 5f972ac15` → 2741+/116−), derived first-party, not
  taken from the message. ⚠ A PR an author would confidently expect to be reviewable was refused at
  every push. **Sizes the split guard's review-coverage dimension** — see the measured watch below.
  ⛔ **NOT established, in either direction:** whether Sourcery would have found anything under the
  cap. It reviewed nothing, so neither run has a counterfactual.

  ⛔ **Two MECHANISM claims, not tallies — these do not decay with n.**
  1. **`pr-agent` is `issue_comment`-only, so it can never HEAD-bind through a check**, and needs an
     explicit `/review` trigger at each HEAD. A required bot that cannot bind to a HEAD is one whose
     participation the barrier **cannot verify against the merge candidate**. Structural, not luck.
     ⭐ Corroborated incidentally here: the #1361 guide comment's `updated_at` (17:53:54Z) ≠ its
     `created_at` (14:43:48Z) — the known **edits-in-place** trap, live again.
  2. **Sourcery's refusal is HONEST** (`refused_structural`, cause `size`). The concern is not the
     refusal but that **a PR can be reviewed by no one on that arm while the barrier still resolves
     clean**.

  ⚠ **A reviewer-quality observation recorded for PLAN-PR-030, not acted on here:** on #1361
  CodeRabbit correctly diagnosed a population derived by literal text matching, then proposed an AST
  count that misses an aliased import — **it reproduced its own finding's class one rung up.** *Name
  matching at a higher rung is still name matching.* Relevant if any spec scores reviewer quality:
  the finding was right and the proposed remedy carried the same defect.

- ⭐⭐⭐ **SUPERSEDED-AND-ENLARGED 2026-08-30 — THE SIX-REPO CORPUS PASS. Full report:
  [`findings/2026-08-30-pr-agent-vs-coderabbit-multirepo.md`](findings/2026-08-30-pr-agent-vs-coderabbit-multirepo.md).**
  ⭐ **NEXT-PASS LOWER BOUND = `2026-08-30T20:16:39Z`.** (This pass used `2026-08-23`, the prior corpus.)

  Window 2026-08-23 → 2026-08-30 over **six** repositories: plan-marshall, cui-http, TokenSheriff,
  API-Sheriff, cui-test-juli-logger, cui-test-mockwebserver-junit5. **93 PRs** opened in window after
  excluding 63 `skip-bot-review` PRs. Measured from **PR state**, not the local `.plan/` substrate.

  | Reviewer | Coverage | Artefact | Substantive |
  |---|---:|---|---:|
  | **pr-agent** | 44 / 93 | 44 guides + 24 `/improve` | **2** and **0** |
  | **CodeRabbit** | 50 / 93 | 396 inline + 243 reviews | **217** (self-declared) |
  | **Sourcery** | 56 / 93 | 61 reviews | 18 were size refusals |

  ⛔⛔ **42 of 44 pr-agent guides are the identical ~200-byte canned table** ("No major issues
  detected" + "No security concerns identified"), corroborated by body length — an axis independent
  of the parser, so the near-zero yield is a property of the OUTPUT, not of the counting.
  ⛔ **PAIRED RECALL: pr-agent reported a finding on 1 of the 35 PRs where CodeRabbit filed ≥1
  actionable.** ⛔ **`/improve` is now n=24, ALL empty** — at 24/24 this is a verdict, not an anecdote.
  ✅ **The "corpus measures a dead config" caveat is DISCHARGED** — this population is entirely
  post-#1130 and post-#1334.

  ⭐⭐ **BUT THE DEFECT IS VOLUME, NOT CORRECTNESS — do not re-frame this as a precision problem.**
  Both substantive pr-agent findings are genuinely good, and one is a **security defect CodeRabbit did
  not file**: cui-http #162, a fail-open in the RFC 7239 `Forwarded` parser (whitespace before `=`
  bypasses malformed-directive detection, so reconciliation does not fail closed). The other is
  API-Sheriff #230's stale `-T1C` flag. ⛔ **This does NOT support dropping pr-agent**, and the #1335
  counter-instance stands. It supports PROMOTING CodeRabbit — PLAN-PR-025B D7, whose premise this
  enlarges from 3 PRs to 35 paired PRs.
  ⛔ **CodeRabbit's 217 is SELF-DECLARED and NOT adjudicated** (prior corpus: 12.1% rejected). The
  robust comparison is the zero-vs-nonzero shape and the 1-of-35 recall — **never a 100:1 ratio**.
  ⛔ Coverage outside plan-marshall and cui-http is TOO THIN to compare (1, 1, 0, 1 reviewed PRs);
  those rows report coverage and support NO quality claim.
  ✅ **INSTRUMENT ANOMALY REFUTED, closing the PLAN-PR-040 D4 open question**: `ci pr comments`
  DOES return `issue_comment` on foreign repos (API-Sheriff#230 → 6, confirmed independently by
  `gh api`); the earlier zero was the observer's COUNTING, not a population exclusion.
  ⚠ **A classifier defect was found and corrected mid-analysis** — CodeRabbit also posts
  `issue_comments`, which the first pass missed: coverage 38→50, no-reviewer bucket 46→37, and a
  false "two substantive PRs went unreviewed" claim withdrawn. Yield figures were never affected.

- ⭐⭐ **UPDATED 2026-08-25 — the post-#1130 pr-agent population is NO LONGER ZERO. It is now n=4, and
  every observation is empty.** ⚠ **SUPERSEDED IN SCALE by the 2026-08-30 six-repo pass above**; kept
  for its per-PR detail. Drained from `truthful-signals-031` / `-032` (PRs #1337, #1336, forwarded
  as NOTIFICATIONS with the sender explicitly staging nothing) plus `plugin-doctor-…-001` (#1343) and
  `-035` (#1338). This retires the standing "the corpus measures a dead config, population currently
  zero" note as a *blocker on measuring*: there is now a population.

  | PR | pr-agent (required) | coderabbit (optional) | sourcery (optional) |
  |---|---|---|---|
  | #1336 | one content-free comment — **quorum passed on it alone** | — | — |
  | #1337 | "No major issues detected" + `/improve` empty list | found a real accepted+fixed issue | — |
  | #1338 | **0 comments** | 10 comments | 2 comments |
  | #1343 | "No major issues detected" ×2 | 8 actionable / 6 real, then **the merge blocker** | structural refusal (size) ×2 |

  ⛔ **The figures for #1336 and #1343 are the sending runs' own reports, NOT re-fetched by us**; #1337
  and #1338 were taken first-party via `ci pr comments`. Re-derive before pricing anything.
  ⭐ `/improve` is now n=2 observed outputs, **both empty lists**, on PRs of very different shape (28
  files/+290−63 vs 3 files/+745−2). Two empty lists is not a verdict, but it is no longer an anecdote.
  ⛔ **The evidence supports PROMOTING CodeRabbit (PLAN-PR-025 D7, where it is folded), NOT dropping any
  reviewer** — the #1335 counter-instance (Sourcery alone found `bug_risk`) still stands.

- ⭐⭐ **RESOLVED-TO-MEASURED 2026-08-25 — the split guard's review-coverage dimension now HAS a
  measurement.** From `truthful-signals-034`. This epic recorded at the 2026-08-08 drain that the
  scope-bloat split guard had an *unmeasured* review-coverage dimension — "the larger the change, the
  less of it gets reviewed", a structural incentive pointing the wrong way. A live finalize measured it:

  | Quantity | Value |
  |---|---|
  | Sourcery diff-size cap | **150,000** chars |
  | Actual | **179,695** — 19.8% over |
  | `test/` alone | 129,556 |
  | everything except `test/` | 50,139 |

  ⇒ ⭐⭐ **A source/test split would have gotten BOTH halves reviewed rather than neither** (50,139 and
  129,556 are each under the cap). The dimension is no longer unmeasured, and the remedy is now concrete:
  split on the `test/` boundary when the combined diff approaches the cap. ⚠ Figures are the sending
  run's own first-party measurement, not re-derived by us — n=1.

- ⚠ **NEW 2026-08-25 — a truncated CI fan-out SELF-HEALS on the next push, so absence is not a
  configuration defect until re-pushed.** From `plugin-doctor-…-001` finding 3, which UPDATES an earlier
  finding that had diagnosed PR #1343 as structurally missing its `pull_request` event (4 checks, no
  CodeRabbit, no `dependency-review`, no `auto-merge`). After a `force-push-with-lease` to the same PR
  the fan-out was **complete**: 10 checks, two distinct Python Verify runs, plus every missing job.
  ⇒ **A no-op push is the cheapest diagnostic — re-push before treating a truncated fan-out as a workflow
  defect.** ⛔ Note the reading was CORRECT when taken and would read differently now: this is the
  remote-state-vs-HEAD distinction, not an error.

- ⚠ **NEW 2026-08-25 — PLAN-PR-034's fix ships INERT, so its shipped behaviour is verified only by
  tests.** From the PLAN-PR-034 landing, corroborated first-party rather than taken from the paste:
  `_github_pr.py:297` declares `UNRECOGNISED_REFUSAL_MAX_CHARS: int | None = None`, and the
  enumerative arm's non-firing branch 1 (`:367-369`) returns `False` on the absent threshold — placed
  FIRST deliberately, so with no measured bound there is no admissible way to fire. ⭐ **This is
  correct, not a shortfall**: D0 measured the population and found no local instance, so no bound was
  derivable, and the alternative — tightening on an unmeasured corpus — is the archetype this epic
  exists to remove. ⛔ But it means the epic's WS-01 defect is closed **in code and in tests, not in
  observed runtime behaviour**. Closing evidence is a real refusal classified as `unrecognised_refusal`
  on a live PR, which cannot happen until a threshold is derived from a corpus that does not yet
  exist. **Deliberately NOT staged** — there is no deliverable until that corpus accumulates.
- ⛔ **NEW 2026-08-25 — the 6-finalize billing figure is off by two orders of magnitude, and the
  published total inherits it.** From the PLAN-PR-034 landing's phase breakdown. Every phase but one
  bills at 12.6×–28.2× its token count; **6-finalize bills at 0.08×** (3,498,973 tokens →
  277,383 billing). ⭐ **The column sums to the published 95,810,061 exactly**, so the total is
  internally consistent and INHERITS the anomaly rather than contradicting it — which is what makes
  it dangerous: nothing in the report looks wrong. 6-finalize is the **re-entered** phase, precisely
  the class `truthful-signals` PLAN-TRUTH-055 made representable and where one defect is known to
  have escaped to main. ⛔ **NOT this epic's surface — routed to `truthful-signals`, nothing staged
  here.** ⚠ Before any cross-epic emit, check `manage-status list` + `source_id` for a live duplicate:
  a ledger cannot see a duplicate held in another ledger.

- ✅✅ **CLOSED 2026-08-30 — THE CLOSING EVIDENCE HAS BEEN READ FIRST-PARTY. The entitlement holds.**
  The `PR Agent Review` run log for plan-marshall PR #1370 (run `33333426580`) carries
  `"model": "vertex_ai/gemini-3.7-flash"` in its `Relevant configs` record AND the line
  `Generating prediction with vertex_ai/gemini-3.7-flash`. ⇒ The **WIF service account is served the
  leading model**; the ladder did **not** fall through. The proxy is discharged by the exact evidence
  this watch demanded, so the "true when written, false when read" risk is retired rather than merely
  unfired.
  ⛔⛔ **AND THE RESULT IS THE OPPOSITE OF REASSURING.** That same run — leading model, FULL diff
  (`Tokens: 203455, total tokens under limit: 256000, returning full diff`), complete domain-routed
  charter — published the canned *"No major issues detected"* table. **The model ladder was never the
  cause of the empty reviews.** ⇒ Sizes **PLAN-PR-042**, now the epic's highest-priority spec.
  The original watch text, kept because it records why the proxy was accepted:

- ⚠ **NEW 2026-08-24 — the 3.7-flash entitlement proof is a PROXY, and the runner's identity is
  unconfirmed.** From the PLAN-PR-041 landing ([`landings/PLAN-PR-041.md`](landings/PLAN-PR-041.md)).
  The `HTTP 200` that cleared deliverable 1 came from a direct `generateContent` call using
  **operator USER credentials**; the workflow authenticates as a **WIF service account**. Publisher-
  model entitlement is project-scoped, which is what makes this the right proxy — but a proxy is what
  it is. ⭐ **The failure mode is bounded and self-healing**: if 3.7 is not served to that identity the
  ladder falls through to `3.6-flash` and the review still publishes, so the cost is a wasted call and
  never a lost review. **Closing evidence is `"model": "gemini-3.7-flash"` in the next real review run
  log.** ⛔ Do not mark this closed until that line has been read first-party — an untested identity
  boundary that merely *has not failed yet* is the "true when written, false when read" archetype this
  epic already tracks.
- ⛔ **NEW 2026-08-24 — the repo that CONFIGURES the third reviewer is the one repo that reviewer
  cannot review.** Established at the PLAN-PR-041 landing, not inferred: `git ls-tree -r origin/main`
  on `cuioss/pr-agent-settings` returns exactly two paths (`.pr_agent.toml`, `README.adoc`) — there is
  no `.github/` tree, so no workflow invokes pr-agent there. CodeRabbit and Sourcery review that repo
  because they are org-level GitHub Apps; pr-agent runs from a workflow and therefore does not. ⭐ The
  absence is **expected and structural, not a defect** — recorded because an unexplained absent bot is
  exactly the signal this epic exists to keep legible, and because the shape is PLAN-PR-030's one level
  up: every change to the reviewer's own configuration is reviewed by everyone except the reviewer it
  configures. Deliberately NOT staged — no deliverable is obvious, and PLAN-PR-026 and PLAN-PR-030
  already own the surrounding surface.
- ⚠ **NEW 2026-08-23 — bot-review CADENCE is measured, but only on ONE foreign run, and the sender
  advises against acting yet.** From inbox `truthful-signals-030.md`, forwarded by the
  `truthful-signals` orchestrator as a dispatcher (they stage no plan for it; the cadence machinery is
  ours). Their run of `fix-provider-abstraction-mismatch` (shipped #1332 `be2a030e9`, follow-on #1335
  `51ff9e59e` — **both landings verified first-party against `origin/main` by us**) reports: cycle 1
  → 4 fix tasks including a genuine runtime defect six self-review rounds, the quality gate and 21,726
  passing tests all walked past; cycle 2 → **0 fix tasks for ~835K tokens**; all-in ~1,671,300 tokens,
  26.3% of the plan's dispatched total.
  ⛔ **EVERY TOKEN FIGURE IS THEIR MACHINE'S LEDGER AND WE REPRODUCED NONE OF IT.** The originating
  plan archive is machine-local. Lead, never fact.
  ⭐ Their own framing, which we find internally consistent and adopt as the reason NOT to act yet:
  the 438,748-token "review" band re-fire is **not review cost** — it is the settle band re-running
  because a review-driven commit advanced HEAD, billed under a review heading. So decide "run review
  once" and "gate cycle N+1 on cycle N's yield" **after** their `verdict_inputs` (PLAN-TRUTH-097)
  lands and per-cycle amplification is re-measured. Cycle 2's zero yield is n=1; cycle 1's catch is
  exactly the class of defect no in-house gate finds.
  ⭐ **Independently corroborated first-party, and it cuts against dropping a reviewer:** on #1335,
  Sourcery returned `bug_risk` findings on an 18-line documentation diff where **CodeRabbit returned
  "No actionable comments were generated" and pr-agent "No major issues detected"** — verified via
  `ci pr comments --pr-number 1335`. A third instance of one bot finding what the other two missed.

- ⛔⛔ **NEW 2026-08-08 — A LEDGER CANNOT SEE A DUPLICATE THAT LIVES IN ANOTHER LEDGER.** PLAN-PR-018
  and `code-intelligence-substrate` PLAN-CIS-031 were staged on the same subject in two epics; nothing
  in either ledger could detect it, and it surfaced only because a **live `manage-status list`** showed
  the sibling's plan running. ⭐ **The `source_id` in a running plan's `request.md` is the only
  cross-epic ownership oracle we have, and nothing consults it routinely.** ⇒ **Standing check to adopt:
  before emitting, read `manage-status list` and resolve each live plan's `source_id` — a plan running
  out of another epic on your subject is the one collision no disjointness test can catch.** ⚠ Root
  cause is the routing rule, not either orchestrator: **the three-way test does not cleanly assign
  *self*-review**, and both epics routed it correctly by their own reading.
- ⛔⛔ **NEW (drain 2026-08-08) — PLAN-PR-002's deliverable PR is OPEN and UNMERGED while its plan
  lifecycle has ENDED.** `cuioss/cuioss-organization#235`, corroborated first-party at the drain
  (`state: open`, `review_decision: none`). The plan is absent from `manage-status list`, so nothing is
  running that will finish it. ⇒ **The row is deliberately left `launched`, not `shipped`** — the ship
  claim in its own landing message is contradicted by PR state. Full analysis:
  [`landings/PLAN-PR-002.md`](landings/PLAN-PR-002.md). ⭐ **METHOD RULE established here: a landing
  message from a plan whose deliverable lives in a FOREIGN repo must be corroborated against the
  FOREIGN PR's state — the local oracle (absence from `manage-status list`) proves only that the plan
  stopped running.** The status disposition is an operator decision, because at `N=1` it decides `R`.
- ⚠ **NEW (drain 2026-08-08) — cuioss-organization R1 residual, operator-accepted.** Once step (2)
  lands there, a `synchronize` run whose every model call failed will be UNGATED, and there is no
  runner state that can fix it (the runner exposes no discriminator). The `/review` comment path stays
  fully gated. Step (2) is owed by a follow-up plan **in that repo**: set `handle_push_trigger` +
  `push_commands = ["/review"]` in `cuioss/pr-agent-settings` AND add `synchronize` to callers'
  `types:`. ⛔ Do not enable the trigger without re-reading R1.
- ⭐ **NEW (drain 2026-08-08) — the scope-bloat split guard has an unmeasured REVIEW-COVERAGE
  dimension.** Splitting a plan is currently argued on landing-and-analyzing as one unit; a size/diff
  ceiling means it also decides whether a reviewer looks at the diff **at all**. ⭐ **The larger the
  change, the less of it gets reviewed** — every other absence cause is bad luck, this one is a
  structural incentive pointing the wrong way, reachable by the author's own scoping decision.
  ⚠ The 150,000-diff-character figure is SECOND-HAND and unverified as universal or non-configurable.
  Not a deliverable of any plan — an argument about how we scope them.
- ⚠ **NEW (drain 2026-08-08) — a project that has NOT answered `required_bots` runs a vacuously
  satisfied review quorum by default.** The contract states `required_bots` defaults to the empty
  string and that an empty set means the quorum is *vacuously satisfied*. This project has answered it
  (`bot_lists_provenance: answered`), so we are unaffected. ⛔ **LEAD, not a finding** — no other repo
  has been checked. `PLAN-PR-021` D3 makes the vacuous case visible where it occurs; auditing other
  repos is separate work owned by whoever owns them.
- ⚠ **CARRIED (drain 2026-08-08) — on a merge-queue repo, merge is a TWO-STEP action.** #1087 closed
  the first half (an optimistic enqueue inference reported as `merged: true`). The sibling's added ask
  survives it: any wrapper collapsing accept-then-land into ONE boolean is wrong for the whole window
  between the two steps. ⛔ Verify against #1087's merged diff before staging anything — staging a plan
  for an already-landed fix is the failure mode this epic keeps hitting.

- ⭐ **AWAITING A SCOPE VERDICT — executor falsy-arg-strip population, handed to the RUNNING PLAN-PR-014
  (2026-08-01).**
  ⛔ **CORRECTED at cleanup 2026-08-23 — "RUNNING" is FALSE and has been since 2026-08-01.**
  `PLAN-PR-014` shipped as **#1070**; its row has read `shipped` for three weeks. The scope verdict was
  therefore handed to a plan that had already ended, and **nobody has held this question since**. The
  watch stays open — the question below is unanswered — but it is unowned, not pending. ⚠ Re-home it or
  retire it; do not read the hand-off as live.
  The question: which *other* marketplace scripts have an optional argparse flag lacking
  `nargs='?'` AND an invocation site interpolating a possibly-empty `{placeholder}`? **UNMEASURED — a
  population question, never a defect claim.** ⛔ PR-014's own fix is CORRECT and is not in question; do
  not re-open it (see § Open Defects for the withdrawn claim). Two acceptable returns: the plan derives
  and widens, or it declines at the scope-deviation gate and hands the question back as a new staged
  spec. ⚠ It arrived mid-finalize, so a decline is the more likely and entirely legitimate outcome —
  **a decline is not a failure and must not be re-pushed.**

- ⭐⭐ **NEW — the PR-Agent deficit has a CONFIGURATION cause, and it is ours.** Measured over 52 PRs
  (`findings/2026-08-01-sweep-4day.md`): PR-Agent posted **zero** inline review threads in either repo,
  because the org reusable workflow defaults `auto-improve: false` and `/review` emits only a single
  PR-level comment. ⛔ **The toggle's stated rationale — "committable suggestions are already
  CodeRabbit's job" — is falsified in this window**: CodeRabbit produced no substantive review on 19 of
  36 plan-marshall PRs and Sourcery refused ~33 of 36. ⚠ Before treating this as settled, note the
  cost the workflow itself records: enabling `/improve` roughly doubles tokens per PR. Owned by
  `PLAN-PR-004`, whose current scope does not yet carry it.
- ⚠ **OPEN — how often does `default:finalize-step-security-audit` actually run?** It is `lane: full`
  (VERIFIED in `marshal.json`), and every other finalize step sits at `minimal`/`standard`. The
  per-plan activation rate is **unmeasured**: no orchestrator-reachable script enumerates archived
  plans, and `review-practice.md` § 3 requires reading each archived plan's manifest for **both** drop
  paths. ⛔ Until it is measured, do NOT choose between an activation remedy and a detector remedy —
  they are opposites.
- ⚠ **Charter tuning is currently unmeasured.** `pr-agent-settings` #13 (07-29T12:07Z) did not raise
  the observed finding rate (3/18 before vs 1/13 after). ⛔ **HYPOTHESIS only** — small n, uncontrolled
  diffs. Settle it with the fixed-diff re-run named in the sweep's Recommendation B, which also
  answers the merged-PR re-review question below at no extra cost.

- ⭐ **`#1057` recovery is actionable and UNCLAIMED.** CodeRabbit's refusal named the re-trigger and said
  "next review available in **2 minutes**" (2026-07-29T15:14:56Z). None was issued, so the merged diff
  has been reviewed by exactly one bot, which returned nothing.
- **Unanswered, common to the five-revisit batch**: does an explicit re-review trigger still recover a
  review on a **MERGED** PR?
- ⚠ **A recorded note about `#1058` does not match the evidence.** It was recorded as "CodeRabbit
  reviewed the first HEAD and refused the second"; the fetched comments show CodeRabbit reviewing and
  posting 2 findings, with the later `@coderabbitai review` returning "Review finished".
  **Re-verify before citing the partial-participation shape from this PR.**
- ⭐ **OPEN — does a `pull_request`-triggered workflow run get created while a PR is
  `mergeable_state: dirty`?** From `API-Sheriff#133` (`findings/API-Sheriff-PR-133.md`): **zero
  `pull_request`-event runs for ANY workflow** while `mergeable: false`; only a `push`-event run exists.
  HYPOTHESIS (one PR, correlation only): GitHub cannot materialize `refs/pull/{n}/merge` for a conflicted
  PR. ⚠ **Competing mechanism still live** — the v0.17.0 guard produced a `skipped` run elsewhere, and
  ⛔ **a created-but-skipped run is a DIFFERENT state from no-run-created; do not merge them.**
  **Re-check** via `reopened` / `ready_for_review` / `issue_comment` — a plain push does not re-fire
  `opened`, so a push-only retest proves nothing.
  ⭐ **If confirmed**, every required-bot gate is structurally unsatisfiable on a conflicted PR and
  `fail_into_loopback` cannot fix it — the loop-back does not resolve conflicts.
- ⚠ **Plugin cache is stale against the executor — MEASURED, three live wrong-diagnosis consequences.**
  ⭐ **RE-SAMPLED at cleanup 2026-08-23; the figures below are SUPERSEDED, the condition persists in a
  different and much smaller shape.** Double-sampled 08:53:00Z / 08:53:14Z, both agreeing: executor pins
  `0.1.1527`, while all 11 registry `installPath` entries and the sole unmarked cache dir are
  `0.1.1526` — so `executor == installPath` still FAILS, but the 1526↔1527 delta is **one markdown file**
  (`phase-6-finalize/standards/dispatch-inline-split.md`) and **zero script bytes**. Nothing on this
  epic's surface differs, and no script behaviour diverges. ⛔ **The replacement risk is different from
  the old one**: `0.1.1527` is itself ORPHAN-MARKED, so a foreign GC sweep that collects it breaks every
  `execute-script.py` call. Repair is operator-only. ⚠ Size the staleness and the GC exposure separately
  — they are not the same quantity, and the old "32 versions coexisting" framing conflated them.
  Cache `0.1.1240` vs executor `0.1.1271`, 32 versions coexisting; **no** pin/orphan inversion (that
  hypothesis is refuted — the executor embeds exactly one version). Re-check: `/sync-plugin-cache`, then
  confirm the loaded skill matches `marketplace/bundles/`. The tool-layer fix is owed.

## Standing Practice: local-review back-feed

⛔ **Every rule lives in [`review-practice.md`](review-practice.md) — the single source of truth. This
section MUST NOT restate any of them.**

A recurring orchestrator obligation at every post-merge PR revisit: apply the per-bot verdict rules, then
ask one question per finding — **could we have found it ourselves?** — reading the **answer posted on the
PR** as the signal. Output: one document per run at `findings/PR-{n}.md` (cross-repo:
`{Repo}-PR-{n}.md`). Detector batches stage as plans, the first being `PLAN-PR-012`.

## Tree map

| Path | Authority |
|---|---|
| `status.json` | ⭐ **Machine authority** — queue, statuses, `resume_anchor` |
| `epic.md` | This file. Live state only; START-HERE block is GENERATED |
| `review-practice.md` | Single source of truth for review-run rules |
| `plans/` | Staged specs — **self-sufficient**, each carries its own evidence and prohibitions |
| `findings/` | One document per analysed review run |
| `workstreams/` | WS charters |
| `decisions-archive.md` | Relocated chronological narrative and retired entries |
| `reference-config-repos.md`, `references.json` | Config-repo knowledge captured at init |
| `logs/`, `inbox/archive/` | ⛔ Append-only audit trail — **never pruned, never rewritten** |
