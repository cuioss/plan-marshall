# PLAN-LB-170: PLAN-LB-165 completion — two unrequested document rules come out, the null-block fix gets its tests, and `/apply-changes` operator-only is finished on every harness

epic: live-blockers
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> Staged on the operator's word. Source: `landings/PLAN-LB-165.md` (layer-2 findings L2-1 to L2-6 and layer-3 findings L3-1 to L3-6, one leaf, the majors re-read by the orchestrator at the merge commit `a3a1907e5`), and the Open Defect of the PLAN-LB-165 landing in `epic.md`.
> Disjoint from every running plan: PLAN-LB-167 and PLAN-LB-168 live in the runbook lane and the Sonar skill, PLAN-LB-169 in `manage-solution-outline` and `phase-6-finalize`; this plan lives in `manage-config`, two `plan-orchestrator` workflow documents and the three `/apply-changes` entry points.

## Objective

PLAN-LB-165 merged on 2026-11-19 and left four things behind. Two documents carry a normative rule no deliverable asked for, one of which weakens the contract the orchestrator uses to detect a false landing claim. The null-`orchestrator`-block fix has no test. `/apply-changes` is operator-only on the Claude skill alone, and the gap on the other two harnesses is written in no repository file. This plan takes the two rules out (or gives each a justified form the contract can carry), adds the missing tests, and finishes D5.

The plan decides nothing new about the orchestrator's behaviour: each deliverable restores what the contract already says or completes what PLAN-LB-165's own spec already required.

## Deliverables

1. The false-claim contract of `plan-orchestrator/workflow/analyze.md` is head-bound again. The paragraph that begins "The four review-and-Sonar numbers are re-read from the provider" (line 155 at `a3a1907e5`) was changed from reading the numbers "on the merged head" to reading them "against the PR's current state", and gained a sentence exempting a difference "caused by activity after the merge" from being a false claim. The same paragraph still calls a difference a false claim "not … a stale read", and `plan-orchestrator/standards/landing-payload-spec.md` (lines 108-111 and 255) defines the values as the merge gate's read on the head, so the exemption is a rule that contradicts its own paragraph and its standard, and the re-read has no way to tell a post-merge change from a wrong claim. The outline settles one of two forms and records why: (a) the added sentence and the "current state" wording are removed and the original head-bound wording is restored, with only the stale clause "the one parser that produces them from `ci pr comments`" corrected, and only if the outline confirms by reading `runbook_lane.py` that the parser no longer reads `ci pr comments` (the parent's `analyze.md` and the cited commit message are leads, not facts); or (b) a post-merge exemption stays, but only in a form the drain can decide from observable data (for example a review or comment submitted after the PR's merge time, read from the provider), stated in the same paragraph and in `landing-payload-spec.md` so the two do not disagree. A test pins the chosen form.
   - Skills: plan-marshall:ref-code-quality, pm-documents:ref-documentation, plan-marshall:plan-orchestrator
   - Persona: documenter
2. The `handle-open.md` Step 6 reopen/supersede sentence is removed, or routed through the contract. At `a3a1907e5` Step 6 carries the added sentence "Decisions are applied in item-number order; an item decided earlier that a later decision invalidates is re-analysed and, if it already carries a decided marker, reopened by recording a new decision entry that supersedes the previous one." It contradicts the same file's Idempotence rule (line 115: an item already marked decided "is not decided again"), it is not one of the contract's four bounded decision acts (`persona-plan-orchestrator/standards/orchestration-model.md`, handle-open contract), and the Output contract has no row for a superseded decision. The PLAN-LB-165 reword of the "its" ambiguity ("An item whose analysis is changed by another item's decision is re-analysed") stays. The outline settles whether the item-number ordering is worth keeping as a stand-alone sentence with no reopen clause. A reopen rule exists only if the contract gains the act, its Idempotence carve-out and its Output row in the same plan, which this plan does not intend: the default is removal. `test_handle_open_contract.py` pins the reworded sentence and the absence of a reopen act.
   - Skills: plan-marshall:ref-code-quality, pm-documents:ref-documentation, plan-marshall:plan-orchestrator
   - Persona: documenter
3. The null-block fix of `manage-config` has its tests, and its behaviour beyond the spec is settled. `cmd_orchestrator_get` (`_cmd_orchestrator.py` lines 279-313 at `a3a1907e5`) answers `error` for a JSON-null `orchestrator` block, and the tests PLAN-LB-165's D1 owed do not exist: a test for the null block, the absent block (still the seeded default) and the non-dict block (still an error), written against the unfixed tree first, in the files that already exercise `get` (`test_orchestrator_scope.py`, where the absent-block and non-dict tests live, and `test_orchestrator_use_worktree.py`; `test_orchestrator_seed.py`, which PLAN-LB-165's spec named, never calls `get`). The plan also settles what the diff changed beyond the spec: the null and non-dict check now runs before the `use_worktree` branch, so a malformed block in the caller's own `marshal.json` makes `get use_worktree` error, and invalid JSON there raises a `ValueError` that `main()` does not catch, though the knob is read only from the main-anchored file; the main-anchored check swallows `OSError` and `ValueError` and answers success `False`; both errors carry the same message and name neither file; the main file is read three times in one branch. The outline records for each whether it stays, and the docs follow the code: `manage-config/standards/data-model.md` line 314 and the docstring at `_cmd_orchestrator.py` lines 263-266 still say `get use_worktree` answers with the value the store seam uses, which is false for a null block. The three minors PLAN-LB-165's D1 listed are settled and each reason is recorded in the plan's landing message: the figure 90 repeated in `data-model.md` is taken or dropped with a reason; the "Unreachable" comment and the `kinds[]` pin are, by the analysis' reading, already accurate and already pinned, and are dropped only if the outline re-reads them so.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, plan-marshall:manage-config
   - Persona: implementer
4. `/apply-changes` is operator-only on every harness, with the gap stated. `.claude/skills/apply-changes/SKILL.md` has `disable-model-invocation: true` (merged in PLAN-LB-165); `.opencode/commands/apply-changes.md` and `.agents/skills/apply-changes/SKILL.md` were not touched. The outline reads each harness's documented key and records it. Where a harness has no such key, a repository file says so and says what keeps a model from invoking the command there, instead of the claim living in a PR body only; the Antigravity entry is a skill with an invocation-trigger description, so "user-invoked by construction" is not assumed for it. Whether Claude Code honours `disable-model-invocation` is not shown by reading (the only in-repository support is a line that cites a third-party blog, and no other `.claude` skill uses the key); the outline states its evidence or marks the claim as unconfirmed in the repository file that makes it. `test/apply-changes/test_apply_changes_command_parity.py` (its `_frontmatter_violations` checks `name` only, lines 159-171) pins the key for the Claude skill and the recorded gap or the equivalent key for the other two, so the three entry points stay mirrors and the key cannot be removed with every test green.
   - Skills: plan-marshall:ref-code-quality, pm-plugin-development:plugin-architecture, pm-dev-python:pytest-testing
   - Persona: implementer

## Standing Constraints

- No new rule is introduced by this plan. A deliverable removes an unrequested rule, restores a stated one, adds a test, or records a gap; the plan does not add a decision act, a false-claim exemption or a reopen rule except in the form deliverable 1 (b) allows.
- The `get` behaviour never turns a failing read into a passing one: the null block stays `error`, the absent block stays the seeded default, the non-dict block stays `error`.
- The documentation standards bind every document edited here (no timestamps, no version history, current state only, `xref:` cross-references in AsciiDoc).
- Tests are written against the current tree first and each is shown to fail for the behaviour it pins.
- No file outside the surface below is touched. No change under `.plan/orchestrator/` other than the plan's own inbox message.
- Scope-bloat note: four deliverables, under the presumptive-split guard; they are the completion of one landing and share no file with each other beyond the plan's own tests.

## Claim Labels

- OBSERVED (re-read at `a3a1907e5` on 2026-11-19): `analyze.md:155` carries the "current state" wording and the post-merge exemption; `handle-open.md:72` carries the added reopen sentence and `:115` the Idempotence rule it contradicts; `landing-payload-spec.md:108-111` defines the review numbers as the merge gate's read on the head; `_cmd_orchestrator.py:279-313` is as described; `test_apply_changes_command_parity.py:159-171` checks `name` only; `orchestrator_worktree.py:128-138` reads a null block as `False` and never errors; the merge commit touches six files and no test, and no test in the inventory passes a null `orchestrator` block (count 0, 3754 files, not truncated).
- OBSERVED (leaf reading, not re-read): the `get` tests live in `test_orchestrator_scope.py` (`:715-728`, `:797-809`) and `test_orchestrator_use_worktree.py`; `main()` catches only `ConcurrentConfigModificationError` (`manage-config.py:1134-1135`) and `load_config` raises `ValueError` on invalid JSON (`_config_core.py:134-140`); the orchestration standard's closed set of four handle-open decision acts is at `orchestration-model.md:541`.
- HYPOTHESIS: `runbook_lane review-gate` no longer reads `ci pr comments`, so the clause "the one parser that produces them from `ci pr comments`" is stale; it rests on a commit message (`2bf7cd83d`) and was not read in code (verify-at-outline, deliverable 1).
- HYPOTHESIS: OpenCode and Antigravity have no key that withholds a command or skill from model invocation; the lane that merged PLAN-LB-165 claimed it and the repository does not show it (verify-at-outline, deliverable 4).
- Verify-first clause: the outline settles (a) which of deliverable 1's forms (a) or (b) the contract can carry, and for (b) which observable data the drain reads; (b) that the head-bound wording of the landing-payload standard and the analyze paragraph agree after the change; (c) which of the `use_worktree` behaviours beyond the spec stay and why; (d) each harness's documented key for operator-only invocation, or its absence, and where that is recorded. A refutation of (a) or (d) loops back to re-scope.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/handle-open.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md`
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_handle_open_contract.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_orchestrator.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md`
- OBSERVED: `test/plan-marshall/manage-config/test_orchestrator_scope.py`
- OBSERVED: `test/plan-marshall/manage-config/test_orchestrator_use_worktree.py`
- OBSERVED: `.claude/skills/apply-changes/SKILL.md`
- OBSERVED: `.opencode/commands/apply-changes.md`
- OBSERVED: `.agents/skills/apply-changes/SKILL.md`
- OBSERVED: `test/apply-changes/test_apply_changes_command_parity.py`

## Dependencies and Sequencing

- Depends on: none (PLAN-LB-165 is merged).
- Overlaps with: none staged or running; PLAN-LB-167 and PLAN-LB-168 touch the runbook lane and the Sonar skill, PLAN-LB-169 `manage-solution-outline` and `phase-6-finalize`.
- Adjacent to: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py`, which deliverable 1 reads to confirm the parser clause and does not edit (PLAN-LB-167 and PLAN-LB-168 own it).

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-170-lb-165-completion-document-rules-and-missing-tests.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox message.
