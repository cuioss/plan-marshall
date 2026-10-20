envelope_version=1
sender_type=plan
sender_id=rb-lb-67-standing-review-authorization
epic=live-blockers
kind=landing
created=2026-10-18T22:16:41Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-67-standing-review-authorization
epic=live-blockers
pr=#1813
merge_state=merged
cleanup_owed=false
deliverables_total=6
deliverables_done=6
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
```

Guard note beside the block: `guard: present` (the resolve result reported a tool-call guard installed for this harness).

## Deliverables

Six deliverables, each met as written, each with its test seen failing first.

**D1 — standing review authorization in the merge gate.** Met. `runbook-lane/SKILL.md` §7 names all four conditions, makes the quota policy conditional on "no qualifying review exists", excludes reviewers that are not quota-limited, and §8 requires the reviewed head, the current head and per-finding handling. Tests: `test_merge_gate_names_the_four_standing_authorization_conditions`, `test_quota_policy_is_conditional_on_no_qualifying_review`, `test_standing_authorization_scope_excludes_non_quota_limited_reviewers`, `test_landing_report_requires_the_standing_authorization_evidence`, `test_standing_authorization_stays_repository_neutral` — four seen failing (`AssertionError`, condition absent) then passing. Commit `fb56b3d72`.

**D2 — `quota_limited` per reviewer from configuration.** Met. Declared in the three bot standards (`coderabbit` and `sourcery` true — not named in the skill, which stays literal-free; `cuioss-review-bot` false), read through `bot_registry` (fail-closed `false`), surfaced on every resolve row. Source choice: the bot's own standard, the same place `trigger_comment` comes from, because a quota is a property of the reviewer, not of the project. Tests: `test_resolve_reports_a_quota_limited_reviewer`, `test_resolve_reports_a_reviewer_that_is_not_quota_limited`, `test_bot_standard_without_a_declaration_resolves_not_quota_limited`, `test_optional_reviewers_also_carry_the_flag` — seen failing (`KeyError: 'quota_limited'`, `AttributeError`) then passing. Commit `814becde7`.

**D3 — personas as standards.** Met. §1 carries a persona-per-work-kind table, states they are loaded as standards only (machinery ignored), and gives the code-reviewer its adversarial-refute lenses in §5 and §6. Tests: the five persona tests — seen failing (no persona named, no `adversarial-refute`, no standards-only sentence, no persona list) then passing. Commit `f678ddd53`.

**D4 — per-deliverable skills and persona.** Met. `resolve` parses each deliverable's `Skills:`/`Persona:` lines, normalises the persona, and fails closed with `named_skill_not_found`; step 2 names the check and the stop-and-ask and the `bundle:skill` notation; §8 requires the per-deliverable list and `skills added: …, reason: …`. Tests: `test_setup_names_the_skill_existence_check_and_the_stop_and_ask`, `test_landing_report_requires_per_deliverable_skills_and_drift_additions`, `test_resolve_reports_each_deliverables_skills_and_persona`, `test_resolve_fails_on_a_nonexistent_named_skill`, `test_resolve_fails_on_a_nonexistent_named_persona`, `test_spec_without_skill_or_persona_lines_says_none_named` — six seen failing then passing. Commit `b46a28076`.

**D5 — docs-only change skips the full local build.** Met. New `build-classify` verb reads the project's own footprint rule (its CI opt-in plus `extra-buildable`, else the architecture's module directories). Tests: `test_build_classify_treats_a_docs_only_diff_as_docs_only`, `…_bundle_markdown_change_as_buildable`, `…_python_change_as_buildable`, `test_build_classify_without_an_opt_in_falls_back_to_the_architecture`, `test_skill_build_gate_documents_the_docs_only_path` — seen failing (`invalid choice: 'build-classify'`); the fail-first run also exposed a real defect (a `.py` classified docs-only under the CI rule), fixed. Commit `aa890329f`, hardened in `845f07ab0`.

**D6 — the ten weakened rules restored.** Met. Bare `sleep` qualifier dropped; the merge gate names `verify`; the named review verbs are used; `{guard_log}` from resolve; the facts fence is `landing-facts` with every line `key=value`; `{branch} = {prefix}{plan}` with the configured prefix set; `build_timeout_seconds` from the architecture's stamp; the sub-agent tool rewritten per target; a concrete forbidden-binary list; `base_branch` from `project.default_base_branch`. Plus the "pending" merge-question rule and a rule-level parity table. Tests: `test_rule_level_parity_per_section`, `test_skill_never_spells_the_base_branch_literally`, `test_the_subagent_tool_is_rewritten_for_opencode_and_antigravity`, `test_the_skill_landing_facts_example_parses_with_no_dropped_line`, `test_resolve_returns_the_base_branch_and_build_timeout` — all five seen failing against the pre-D6 code then passing. Commits `64a55a95f`, `45cb0df8e`, `51aa7b9df`, `0f4dc5a8a`.

## Personas and skills

Per step, the persona applied: step 3 implementation — `persona-implementer` (production code: `runbook_lane.py`, `bot_registry.py`) and `persona-documenter` (the skill and standards prose); step 5 self-review — `persona-code-reviewer`; step 6 PR triage — `persona-code-reviewer`; step 4 build gate and step 7 merge — no persona (no code, tests or docs written, nothing reviewed).

Per deliverable, `skills: none named` — this spec (staged before PLAN-LB-69 D4) carries no `Skills:` lines, and `resolve` reports `skills_note: none named` for it, which the run verified by running its own resolve. Domain skills were still loaded for the modules the work touched (`plan-marshall:runbook-lane`, `plan-marshall:automatic-review`, `plan-marshall:manage-architecture`, `pm-plugin-development` for the plugin-create surface-drift edit). `skills added: plan-marshall:runbook-lane, plan-marshall:automatic-review, plan-marshall:manage-architecture; reason: the two targets' mappings are registry-global, so the emit-time `Task` rewrite reaches other bundles' bodies and those surfaces had to be read before they were reworded`.

## Hypotheses

- "the bot standards carry a machine-readable header the verb parses" — CONFIRMED. The fenced-YAML block is parsed by `bot_registry`; `quota_limited` was added to the same block (`automatic-review/standards/coderabbit.md:39`).
- "`.github/workflows/python-verify.yml` is the footprint source for this repository" — CONFIRMED (`.github/workflows/python-verify.yml:53-58`: `skip-on-docs-only: true` plus `extra-buildable`).
- "`runbook_lane.py` carries the skill existence check, the drift additions and the footprint resolution" — CONFIRMED. The existence check (`_skill_exists`) and the footprint resolution (`build-classify`) are both there.
- "`doc/developer/opencode.adoc`, the runbook-lane section (D1, D3, D5)" — CONFIRMED as existing, no edit needed: it documents the lane's entry point and prerequisites only, and states none of the rules these deliverables change.
- "`bot-participation-contract.md` documents the new declaration" — CONFIRMED. A section now documents `quota_limited`.

## Findings

Self-review (three rounds, dispatched to a general sub-agent):

1. **Blocking — the registry-global `Task` rewrite falsified per-harness enumerations.** Fixed: the enumeration was removed from `execute-task/SKILL.md` and the "tool unavailable" rationale was restated as the orchestrator contract in `phase-2-refine` (2 sites), `phase-3-outline` and `phase-4-plan` (2 sites). Commit `51aa7b9df`.
2. **Blocking — the rewritten OpenCode name contradicted the target's own `Task → task`.** Resolved by the operator's selected option: `tool_permissions.Task` is now `subagent` and `plugin-create/SKILL.md`'s first mention is backticked so both mentions rewrite together. Commit `0f4dc5a8a`.
3. **Should-fix — the classifier's document classes did not mirror the gate.** Fixed: classes narrowed to the gate's own set; `.rst`/`.txt` removed. Commit `845f07ab0`.
4. **Should-fix — the architecture fallback classified an unlisted root build file `docs-only`.** Fixed: outside every module, only a provably-document path is docs-only. Commit `845f07ab0`.
5. **Should-fix — the skill claimed no project literal while naming one.** Fixed: §4 states the CI opt-in generically.
6. **Should-fix — a bare `Skills:` name was undocumented and could stop a valid run.** Fixed: `bundle:skill` is documented in step 2.
7. **Should-fix — a stale §8/§1 sentence still placed the guard state in the facts fence.** Fixed in both places.
8. Nits: item 8 added to the parity table; docstring and test names corrected; `--project-dir` noted; a duplicated base-branch read, a non-globstar `fnmatch` case and "every target" wording recorded as accepted.

CI / PR comments — CodeRabbit raised five findings on `0f4dc5a8a`; all five were fixed in `845f07ab0`, each thread answered and resolved (footprint classes; unlisted build file; branch-prefix row; guard rule wording; invalid `git fetch` form). Two of them were real defects and got their own fail-first tests. CodeRabbit's second review was refused on quota; the PR review summary, the walkthrough and the bot guides are not findings.

## Reviewers

- `cuioss-review-bot` (required, not quota-limited): reviewed `0f4dc5a8a`, then **reviewed the current head `845f07ab0`** (both Guides name that commit) — reviewed.
- `coderabbit` (required, quota-limited): reviewed `0f4dc5a8a` (formal review, 5 findings). Re-triggered after `845f07ab0`; `REFUSED` on quota ("Review limit reached", "Next included review available in 17 minutes"; the command reply "Review rate limited"). Covered by the D1 standing authorization: qualifying review on `0f4dc5a8a`, all findings fixed and all threads resolved, one re-trigger after the last push with the refusal recorded, and every other gate condition holds on `845f07ab0`. Triggers: comment 6255013643 on `0f4dc5a8a`; comment 6255419030 on `845f07ab0`.
- `sourcery` (optional): `REFUSED` on quota both times ("used your own review budget of 250,000 diff characters for the last 7 days ... request another review in 1 day and 15 hours"). Optional, so it does not gate. Triggers: comments 6255016537 and 6255425785.

## Operator questions

One question-tool call:
- "D6 item 8 names OpenCode `subagent` but the opencode target declares `Task -> task`; how to resolve?" — options: *use `subagent` and align the mapping* / *use the repo's `task`* / *keep `subagent`, leave the rest*; **selected: "Use `subagent` and align the mapping"**.

No free-text operator messages.

## Rule check

Guard refusals recorded for this run's sessions in `.plan/temp/guard.log` — three, all `rule=R1` at `2026-10-18T17:53:19Z`, from three attempted `ls` invocations carrying `2>&1`:

```
2026-10-18T17:53:19.117Z | tool=shell | rule=R1 | session=ses_eafdaba27ffeVBf4mjUwRLDRII | call=call_00_gj6nisahef5e0tyv6t2o5v75 | ls -la .plan/temp/rb-lb-67-standing-review-authorization/ 2>&1
2026-10-18T17:53:19.125Z | tool=shell | rule=R1 | session=ses_eafdaba27ffeVBf4mjUwRLDRII | call=call_01_lpes9bgepmtssu8x1pssrir3 | ls -la .plan/temp/ 2>&1
2026-10-18T17:53:19.135Z | tool=shell | rule=R1 | session=ses_eafdaba27ffeVBf4mjUwRLDRII | call=call_03_5lot7eh1gdrp0ul5tdo2xhqa | ls .plan/orchestrator/live-blockers/landings/ 2>&1
```

Section 1 rules not kept: the shell rule "files are read and searched with the file tools, never with shell `ls`" — three attempts, each refused by the guard, after which the run switched to the glob and read tools and used no shell file operation again. Every other section 1 rule was kept: no `.plan/` write outside `.plan/temp/`, the `ci` body slots and the one inbox message; no edit under `.plan/orchestrator/`; no forbidden binary, `sleep`, `python3 -c` or direct CI CLI; one command per shell call; commits staged by name with the resolved trailer; the base branch merged rather than rebased.

## Residue

1. **Cross-component naming residue (operator-scoped out).** `platform-runtime`'s OpenCode dispatch still returns `task` (`opencode_runtime.py`, pinned by `test_opencode_runtime.py`), and four verbatim standards still say OpenCode `task` (`phase-5-execute/standards/operations.md:49`, `extension-api/standards/dispatch-granularity.md:5`, `plan-marshall/workflow/execution.md:178`, `plan-marshall-opencode/skills/target-rules/standards/opencode-rules.md:61`). The target mapping now says `subagent`; resolving the two owners' disagreement was explicitly outside the operator's decision.
2. **The classifier's document classes remain a local mirror** of a gate that lives in a foreign reusable workflow, so a future gate change is not read automatically. The direction is fail-closed (an unmatched path builds), so the drift can only cost a local build, never skip one the CI would run.
3. **`fnmatch` is not globstar-aware**: `marketplace/**/*.md` matches nested paths (its `*` spans `/`) but would not match a Markdown file directly under `marketplace/`. No such file exists today.
4. **`_resolve_base_branch` re-implements `orchestrator_worktree.default_base_branch()`** deliberately — it reads the project's marshal.json under `--project-dir` rather than the main-anchored store — but the duplication is real.
5. **The dispatched self-review sub-agent's model pin is not readable** from the lane's surfaces, so it is not named in the `model` fact.
