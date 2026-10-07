envelope_version=1
sender_type=orchestrator
sender_id=orchestrator-refactor
epic=truthful-signals
kind=finding
created=2026-10-05T14:43:13Z

# Transfer from `orchestrator-refactor` (epic closing, routed by operator decision)

`orchestrator-refactor` is being closed and archived. Its queue is complete: 7 shipped, 4 superseded by PM-MCP. These open items have no owner there and are transferred here. Each one is a lead to verify against HEAD before staging, not a settled fact. The source record stays readable in the archived epic's `epic.md` (§ Open Defects, § Watches).

## 1. Disjointness gate: whole-population fail-closed scope

`corpus cross-check` reports `candidate_comparison_determinate: false` repository-wide. Re-measured at `b3aba30aa`: `sibling_epic_spec` indeterminate 95 of 611, and `live_plan` indeterminate 1 of 1 (`plan-pr-078-review-bot-fleet-opt-in`). `orchestrate.md` Step 4 refuses EVERY candidate when the comparison is indeterminate. The result is that `next` emits nothing in any epic, and each launch since 2026-09-22 has needed an operator override. PLAN-11 (#1676) removed the self-snapshot and sentinel contributors, so what remains is honest indeterminacy. There are two remedies. One is to change the gate's scope: an indeterminate candidate would block only what it could collide with, which needs a spec on `orchestrator.py` and `workflow/orchestrate.md`. The other is to give 95 sibling specs declarative `## Expected Surface` sections. This is a design decision, still undecided.

## 2. Orchestrator session UX gap (operator-reported 2026-09-22)

There are three asks. (a) Inside a bound `/plan-orchestrator epic={slug}` session, suggestions should name the bare verb, not the full slash-command form. (b) After a major state change, surface the next-verb options by name. Also surface any emitted `/plan-marshall` command that is still `launched` and has not been confirmed `running`. (c) As the mechanism for (b): one script call that cross-reads `launched` queue rows against the live plan store, joined by `plan_marshall_plan_id` / `source_id`, so the start is detected positively instead of the orchestrator relying on the operator's word. Not sized.

## 3. git-config-injection hardening of production git seams (~20 scripts)

This comes from CodeRabbit finding `5ed953` on PR #1585. The test fixture's env scrub was hardened in that plan. The production git seams were deliberately left unhardened as a cross-cutting policy change: `orchestrator.py` `_git_read`, `_git_tree_diff` and `_resolve_anchor_sha`, plus their counterparts across about 20 other scripts. Treat it as one cross-cutting plan; `orchestrator.py` is only one instance of the pattern. It is a real security finding. Not sized.

## 4. PLAN-09 landing residue (#1652)

- (a) An unreadable main-checkout config silently falls back to the primary checkout. This is a silent fallback on the store-resolver seam (CodeRabbit, noise-filtered).
- (b) `_cutover_refusal` duplicates `_default_base_branch()`. Advisory simplification.
- (c) Branch cleanup records `rev-parse HEAD` as the merge SHA, which is wrong whenever another PR lands before switch-and-pull. The landing recorded `438a0a71f` while main was at `c9c67839c`. The merge fact must come from the PR's merge record.

## 5. `manage-lessons drain-dedup` reports false recurrences

It groups candidates by component alone. On PLAN-11's 9-lesson drain (2026-10-02) it reported 5 of the 9 as recurrences of two unrelated lessons (`2026-09-29-17-001`, `2026-09-27-07-004`) and of each other. A manual read found no real duplicate. A drain that trusted the count would have dropped 5 lessons. This is a confident recurrence count that hides a loss. The same run reported lesson `2026-09-27-19-001` as present but carrying no parseable metadata header.
