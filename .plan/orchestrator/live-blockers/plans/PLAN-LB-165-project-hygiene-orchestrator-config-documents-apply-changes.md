# PLAN-LB-165: Project hygiene — a null `orchestrator` block fails closed, the `handle-open` and root documents are corrected, and `/apply-changes` is operator-only

epic: live-blockers
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> Plan D of the module regrouping of 2026-11-18: small, independent corrections in the project-hygiene surfaces (`manage-config`, `plan-orchestrator`, `extension-api`, the repository root documents and the three `/apply-changes` entry points). No path is shared with the review-gate, functional-review, build-server or execution-manifest plans, so it runs in parallel with them.

## Objective

Five small decisions of the 2026-11-18 handle-open run, each the operator's, none large enough for its own plan, are carried together by the operator's rule (as few plans as possible, grouped by module so they run in parallel):

1. a JSON-`null` `orchestrator` block in `marshal.json` takes the seeded default where it must fail closed;
2. two wording defects in `handle-open.md`, and the minors of the two three-layer leaves of 2026-11-15 that the outline confirms;
3. the `CLAUDE.md` heading `Standalone Plan Lane (doc/plans/)` was dropped when the Merge Authorization section was inserted before its opening paragraph;
4. the `ext-point-domain-verb.md` row calls `marker-detect` an automatic "marker gate" that does not exist;
5. `/apply-changes` writes the plugin registry, an operator-consent act (ADR-025), yet a model can invoke the skill unprompted.

## Deliverables

1. A JSON-`null` `orchestrator` block fails closed on `get`. In `_cmd_orchestrator.py` the check `orch_block is not None and not isinstance(orch_block, dict)` treats an explicit JSON `null` like an absent block, because `config.get('orchestrator')` returns `None` for both, so `get` answers `success` with the seeded threshold (90) where the contract resolves an unreadable setting to 100 (the comment above the check names that as the fail-open direction; it needs a hand edit to occur). The fix distinguishes a present-but-null block from an absent one and answers `error` for the former, with a test for the null block, the absent block (still the seeded default) and the non-dict block (still an error). Minors the two three-layer leaves of 2026-11-15 recorded, taken ONLY if the outline re-reads each in the file and confirms it: the stale "Unreachable" comment at `_cmd_orchestrator.py` lines 355-363, the unpinned `kinds[]` of the `handle-open` output, and the figure 90 repeated in `manage-config/standards/data-model.md`; an unconfirmed one is dropped with the reason recorded, not widened.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, plan-marshall:manage-config
   - Persona: implementer
2. The `handle-open` document is corrected. In `plan-orchestrator/workflow/handle-open.md` Step 6 (line 72) the sentence "an item whose decision changes another item's analysis is re-analysed" is reworded so "its" can no longer be read as the deciding item (Step 7 is right and is the model), and the Output example (line 142) loses the date it carries, per the documentation standard "no timestamps". `plan-orchestrator/workflow/analyze.md` states in the review-and-Sonar paragraph (line 155) that `runbook_lane review-gate --pr-number {N}` is "the one parser that produces them from `ci pr comments`"; the gate reads the review through the single-read path now, so the outline re-reads the line and corrects it if still stale (verify-at-outline). `test_handle_open_contract.py` is extended where it pins the reworded text.
   - Skills: plan-marshall:ref-code-quality, pm-plugin-development:plugin-architecture
   - Persona: documenter
3. The dropped heading is restored. `CLAUDE.md` line 72 links `#standalone-plan-lane-docplans` and says "see [Standalone Plan Lane] below", but no heading of that name exists: a sweep of `^## ` headings finds only `## Merge Authorization (Standing)` at line 88, and the paragraph that opens the lane section (line 94) sits directly under the merge-authorization text, because PR #1974 inserted the Merge Authorization section before that paragraph and dropped the heading line. The plan restores `## Standalone Plan Lane (doc/plans/)` immediately before the line-94 paragraph. `AGENTS.md` does NOT carry the same gap (its line 39 points at `CLAUDE.md` § "Standalone Plan Lane", which the restored heading satisfies), so it is not edited. The outline checks that no other document links the anchor and finds the heading in the same form.
   - Skills: plan-marshall:ref-code-quality, pm-documents:ref-documentation
   - Persona: documenter
4. The `marker-detect` row states what the verb is. The row at `extension-api/standards/ext-point-domain-verb.md` line 110 calls the verb a "marker gate" that "simply does not run" when java-cui is inactive, which describes an automatic gate that does not exist. The operator ruled that no automatic gate is wired and that the verb is run on demand: the row says it is run on demand and keeps the fact that the java-cui extension supplies it. One sentence changes; the rest of the table is untouched.
   - Skills: plan-marshall:ref-code-quality, pm-plugin-development:plugin-architecture
   - Persona: documenter
5. `/apply-changes` is operator-only on all three harnesses. `.claude/skills/apply-changes/SKILL.md` declares `user-invocable: true`, `mode: script-executor` and `allowed-tools: Bash` and no `disable-model-invocation`, so a model can invoke it unprompted in Claude Code; the skill's own Step 5 says running it "is the operator's consent to the write" to the plugin registry and ADR-025 keeps that write operator opt-in, which a model-initiated run would not honour. The Claude skill gains `disable-model-invocation: true`. The OpenCode command (`.opencode/commands/apply-changes.md`) and the Antigravity skill (`.agents/skills/apply-changes/SKILL.md`) gain the equivalent their harness honours; the outline reads each harness's documented key and records it, and where a harness has no such key, says so and states what keeps a model from invoking the command there (verify-at-outline). `test/apply-changes/test_apply_changes_command_parity.py` is updated in the same plan so the three entry points stay mirrors and the new key is pinned for the Claude skill and its equivalents. The other minors of PR #1986 stay as recorded.
   - Skills: plan-marshall:ref-code-quality, pm-plugin-development:plugin-architecture, pm-dev-python:pytest-testing
   - Persona: implementer

## Standing Constraints

- Deliverable 1 never turns a failing read into a passing one: the null block moves from the fail-open direction to fail-closed, and the absent-block default and the non-dict error are unchanged.
- Each correction is its own deliverable and independently shippable; none depends on another, so the outline may order them freely.
- No file outside the surfaces below is touched. The runbook-lane skill and `runbook_lane.py` belong to the review-gate plan; `analyze.md` is edited only at the one stale statement of deliverable 2.
- The documentation standards bind every document edited here (no timestamps, no version history, current state only, `xref:` cross-references in AsciiDoc).
- No change under `.plan/orchestrator/` other than the plan's own inbox message.
- Scope-bloat note: five deliverables, at the presumptive-split guard; they are independent one-file corrections and are kept together by the operator's rule, so proceeding unsplit is recorded here as the rationale.

## Claim Labels

- OBSERVED (re-read at `main` on 2026-11-18): `_cmd_orchestrator.py` line 296 refuses a present `orchestrator` block that is not a dictionary and the test is `orch_block is not None`; `config.get('orchestrator')` returns `None` for an absent block and for an explicit JSON `null` alike (confidence 93; it needs a hand edit to occur).
- OBSERVED (re-read at `main` on 2026-11-18): `CLAUDE.md` has no `## Standalone Plan Lane (doc/plans/)` heading, line 72 links the anchor, and `AGENTS.md` has no gap of its own (its line 39 points at `CLAUDE.md` § "Standalone Plan Lane").
- OBSERVED (re-read at `main` on 2026-11-18): `.claude/skills/apply-changes/SKILL.md` carries `user-invocable: true` and no `disable-model-invocation`; the Antigravity skill's front matter holds `name` and `description`, and the OpenCode command's front matter holds `description` only.
- OBSERVED (content sweep over the inventory, 3 753 files, none unreadable, not truncated): `marker-detect` appears in 31 files and in none under `phase-5-execute`, `phase-6-finalize` or `execute-task`, so no automatic caller exists in the inventoried tree; `.claude/**` and `.github/**` lie outside that sweep and `build-maven/SKILL.md` (one mention) was not read.
- HYPOTHESIS: `handle-open.md` lines 72 and 142 and `data-model.md`'s repeated 90 are still as described; the outline re-reads each (verify-at-outline).
- HYPOTHESIS: the harness honours `disable-model-invocation` on a Claude skill; confirm from the harness documentation or the skills already using it in this repository (verify-at-outline).
- Verify-first clause: the outline settles (a) which of the three minors of deliverable 1 are confirmed; (b) whether the `analyze.md` statement is still stale; (c) the equivalent key (or its absence) for OpenCode and Antigravity; (d) that no other document links the `CLAUDE.md` anchor in a form the restored heading would not satisfy.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_orchestrator.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/standards/data-model.md`
- OBSERVED: `test/plan-marshall/manage-config/test_orchestrator_seed.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/handle-open.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md`
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_handle_open_contract.py`
- OBSERVED: `CLAUDE.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-domain-verb.md`
- OBSERVED: `.claude/skills/apply-changes/SKILL.md`
- OBSERVED: `.opencode/commands/apply-changes.md`
- OBSERVED: `.agents/skills/apply-changes/SKILL.md`
- OBSERVED: `test/apply-changes/test_apply_changes_command_parity.py`

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none staged or running; PLAN-LB-162 edits the runbook lane and the review gate (and leaves the `analyze.md` line to this plan), and the other plans of the 2026-11-18 regrouping touch the functional review, the build server and the execution manifest.
- Adjacent to: `plan-orchestrator/workflow/analyze.md` outside line 155, which this plan does not edit.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-165-project-hygiene-orchestrator-config-documents-apply-changes.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
