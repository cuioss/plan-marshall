# PLAN-TRUTH-155: Agent-facing documentation surfaces, and the live-plan defect sweep

## Objective

Two broad sweeps merged because both are populations of independently-verifiable members rather than one
mechanism, and both are gated on the same obligation: re-ground every member at HEAD before fixing any. The
first is the agent-facing documentation surface — standards and user docs that state what the tree no longer
does, including surfaces that claim to verify what they do not. The second is the live-plan sweep: five
observed defects where a producer reports success or cleanliness over something it never read.

## Deliverables

12 deliverables, within the epic's operator-set ceiling of 12 (recorded 2026-09-12: the orchestration-model scope-bloat guard presumptively splits at ~6 and permits proceeding unsplit with a recorded rationale; that decision is the rationale). **D0 is a gate: nothing downstream starts until every carried claim is re-grounded at HEAD.** Each deliverable names the superseded spec it came from, so the audit trail back to the source is a pointer, not a restatement.

1. **D0 — GATE: re-ground every member of BOTH populations at HEAD before fixing any.** ⛔ Neither population may be taken from its source spec's table — both are carried counts, and this epic's recurring defect is exactly a restated count read as a measured one. PLAN-TRUTH-091's own section-scope verdict records that 27 of its asserted gaps were never enumerated. Publish each swept population and its size. (PLAN-TRUTH-111 D0 + PLAN-TRUTH-091's implicit gate, now explicit.)
2. **D1 — The three `high` documentation gaps, landing first.** (PLAN-TRUTH-091 D1.)
3. **D2 — Configuration truth on the five consumer-facing `doc/user/` pages.** (PLAN-TRUTH-091 D2.)
4. **D3 — The `pm-dev-java` maintenance surfaces that claim to verify what they do not.** (PLAN-TRUTH-091 D3.)
5. **D4 — `java-null-safety` and `java-core`: routing, attribution, and an example that matches its heading.** (PLAN-TRUTH-091 D4.)
6. **D5 — `extension-api` build standards: scope, spellings, vocabulary, and one reachable path.** (PLAN-TRUTH-091 D5.)
7. **D6 — The deployment diagram standard and its skeleton.** (PLAN-TRUTH-091 D6.)
8. **D7 — Incident narration and a dated snapshot in normative documents.** (PLAN-TRUTH-091 D7.)
9. **D8 — Remaining stale statements, and one reusable security rule.** (PLAN-TRUTH-091 D8.)
⛔ **REGROUPED 2026-09-18 (cleanup A5) — two deliverables moved OUT, component-first.** This spec's subject
is **documentation surfaces that state what the code does not do**. D10 and D11 were neither: D10 was a
**step record** that satisfies a terminal requirement from a prior firing, and D11 was a **vacuous
verification** (the `Bash` tool swallowing non-zero exits, so every bare `git diff --quiet` proof asserts
nothing). They moved to the specs whose subject they are — `PLAN-TRUTH-170` D4b and `PLAN-TRUTH-153` D12 —
rather than staying in a documentation sweep that would have had to grow a testing half to hold them.
D9 stays: `ci pr view` returning no body IS a documented-contract divergence. Deliverable count re-derived
after the move: **10**.

10. **D9 — `ci pr view` returns no PR body, so read-modify-append on a body is unreachable — and `pr_intent_section`'s 1500-character budget clips mid-sentence.** (PLAN-TRUTH-111 D1 + D2.)
11. ⛔ **D10 — MOVED OUT 2026-09-18, SPLIT TWO WAYS.** Its first half (`assert-step-recorded --require-terminal` passes on a STALE record from a prior firing) is now `PLAN-TRUTH-170` D4b, whose subject is the step record. Its second half (`scope_creep_check` publishes a vacuous clean zero with no baseline sha) is already owned by `PLAN-TRUTH-145` D4/D5, which builds the missing `plan_creation_sha` producer — the vacuous zero is that absent producer's symptom, not a separate defect. (was PLAN-TRUTH-111 D3 + D4.)
12. ⛔ **D11 — MOVED OUT 2026-09-18 to `PLAN-TRUTH-153` D12.** The `Bash` tool swallows non-zero exit codes, so every bare `git diff --quiet` proof in the tree is currently passing for the wrong reason — a vacuous verification, which is that spec's subject. (was PLAN-TRUTH-111 D5.)

## Claim Labels

⛔ Every claim below is a POINTER at the superseded source spec that authored it. The sources are on disk and are the audit record; re-derive each claim **from the source spec's own section at HEAD**, never from this restatement. D0 owns that re-grounding.

- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-091 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-091-agent-facing-documentation-surfaces.md` § `## Claim Labels` (verify-at-outline)
- HYPOTHESIS: every scoping premise carried from PLAN-TRUTH-111 still holds at HEAD — confirm/refute at `.plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-111-observed-defects-from-the-live-plan-sweep.md` § `## Claim Labels` (verify-at-outline)

## Expected Surface

Machine-derived: the union of the `## Expected Surface` sections of every superseded source, resolved through `plan-marshall:script-shared`'s `epic_spec_parser` — the single reader the disjointness gate uses. Not retyped.

- `marketplace/bundles/plan-marshall/skills/manage-findings/SKILL.md` — carried from PLAN-TRUTH-091
- `marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md` — carried from PLAN-TRUTH-091
- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/SKILL.md` — carried from PLAN-TRUTH-091
- `doc/user/parallelism-and-locking.adoc` — carried from PLAN-TRUTH-091
- `doc/user/configuration.adoc` — carried from PLAN-TRUTH-091
- `doc/user/recipes.adoc` — carried from PLAN-TRUTH-091
- `doc/user/enforcement-hook.adoc` — carried from PLAN-TRUTH-091
- `doc/user/efforts.adoc` — carried from PLAN-TRUTH-091
- `marketplace/bundles/pm-dev-java/skills/java-maintenance/standards/compliance-checklist.md` — carried from PLAN-TRUTH-091
- `marketplace/bundles/pm-dev-java/skills/java-maintenance/standards/java-maintenance/standards/refactoring-triggers.md` — carried from PLAN-TRUTH-091
- `marketplace/bundles/pm-dev-java/skills/java-core/standards/java-17-features.md` — carried from PLAN-TRUTH-091
- `marketplace/bundles/pm-dev-java/skills/java-core/standards/java-null-safety/SKILL.md` — carried from PLAN-TRUTH-091
- `marketplace/bundles/pm-dev-java/skills/java-core/standards/java-null-safety/standards/null-safety-patterns.md` — carried from PLAN-TRUTH-091
- `marketplace/bundles/pm-dev-java/skills/java-core/standards/java-null-safety/standards/null-safety-core.md` — carried from PLAN-TRUTH-091
- `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-systems-common.md` — carried from PLAN-TRUTH-091
- `marketplace/bundles/plan-marshall/skills/extension-api/standards/persona-plan-marshall-agent/SKILL.md` — carried from PLAN-TRUTH-091
- `marketplace/bundles/plan-marshall/skills/extension-api/standards/plan-marshall/workflow/await-long-running.md` — carried from PLAN-TRUTH-091
- `marketplace/bundles/pm-documents/skills/ref-svg-diagrams/standards/diagram-type-deployment.md` — carried from PLAN-TRUTH-091
- `marketplace/bundles/pm-documents/skills/ref-svg-diagrams/standards/ref-svg-diagrams/templates/deployment-diagram-skeleton.svg` — carried from PLAN-TRUTH-091
- `marketplace/bundles/plan-marshall/skills/automatic-review/SKILL.md` — carried from PLAN-TRUTH-091
- `marketplace/bundles/plan-marshall/skills/automatic-review/automatic-review/standards/bot-participation-contract.md` — carried from PLAN-TRUTH-091
- `marketplace/bundles/plan-marshall/skills/automatic-review/automatic-review/scripts/review_completeness.py` — carried from PLAN-TRUTH-091
- `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/SKILL.md` — carried from PLAN-TRUTH-091
- `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/standards/permission-architecture.md` — carried from PLAN-TRUTH-091
- `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/dispatch-logging.md` — carried from PLAN-TRUTH-091
- `marketplace/bundles/plan-marshall/skills/persona-security-expert/standards/dependency-supply-chain.md` — carried from PLAN-TRUTH-091
- `doc/plans/truthful-signals/170-graduate-deployment-diagram-type-from-api-sheriff/report-01.md` — carried from PLAN-TRUTH-091
- `marketplace//sync-plugin-cache` — carried from PLAN-TRUTH-091
- `marketplace/bundles/` — carried from PLAN-TRUTH-091
- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/**` — carried from PLAN-TRUTH-111
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/**` — carried from PLAN-TRUTH-111
- `marketplace/bundles/plan-marshall/skills/manage-status/**` — carried from PLAN-TRUTH-111
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/**` — carried from PLAN-TRUTH-111
- `test/plan-marshall/**` — carried from PLAN-TRUTH-111

## Dependencies and Sequencing

D0 gates everything downstream. Surface overlaps with other merged plans in this epic are expected; the disjointness gate reports them and sequences accordingly. PLAN-TRUTH-139, -127 and -103 were running when this plan was staged and were NOT re-scoped.

## Supersession Record

This plan SUPERSEDES the following specs, which stay on disk as the audit record of why they were retired (⛔ a superseded spec is never deleted):

- `PLAN-TRUTH-091-agent-facing-documentation-surfaces.md` (PLAN-TRUTH-091)
- `PLAN-TRUTH-111-observed-defects-from-the-live-plan-sweep.md` (PLAN-TRUTH-111)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-155-agent-facing-documentation-surfaces-and-the-live-plan-defect-sweep.md"
```

## Write-Boundary

The executing plan MUST NOT create or edit any file under `.plan/local/orchestrator/truthful-signals/` except its own `inbox/{sender}-{seq}.md` messages, written through `plan-marshall:plan-orchestrator:orchestrator inbox write`. The orchestrator owns every other ledger write.
