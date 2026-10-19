envelope_version=1
sender_type=plan
sender_id=rb-lb-71-lb-67-completion
epic=live-blockers
kind=landing
created=2026-10-19T09:22:51Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-71-lb-67-completion
epic=live-blockers
pr=#1817
merge_state=merged
cleanup_owed=false
deliverables_total=3
deliverables_done=3
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
```

guard: present

## Deliverables

**D1 — the skill-existence check resolves a named skill in every deployed layout.**
- *Flate install resolves `plan-marshall:persona-implementer` and the bare `persona-implementer`* — met. `test_resolve_resolves_bundle_and_bare_persona_in_a_flat_install`; before the fix the resolve errored `named_skill_not_found` with `missing: plan-marshall:persona-implementer, persona-implementer`; after, both rows carry a resolvable persona. Commit `05be52678`.
- *Nested versioned cache resolves `pm-dev-python:python-core`* — met. `test_resolve_resolves_a_cross_bundle_skill_in_a_nested_cache`; the mutation to the flat-blind probe made it error `named_skill_not_found` with `missing: pm-dev-python:python-core`. Commit `05be52678`.
- *Source tree resolves the same names* — met. `test_skill_exists_resolves_the_source_tree_across_two_bundles`; the mutation returned `False` for `pm-dev-python:python-core`. Commit `05be52678`.
- *A name in none returns `named_skill_not_found`, naming every probed path* — met. `test_resolve_missing_skill_names_every_probed_path`; the base had no `probed` key. Commit `05be52678`.
- *The pass case names skills in two bundles* — met. `test_resolve_passes_with_skills_from_two_bundles` (`plan-marshall:runbook-lane` + `pm-dev-python:python-core`). Commit `3217d573b`.

**D2 — the docs-only classifier derives its rule from the project and never fails open.**
- *`test/README.md` → buildable* — met, fail-first: `test_build_classify_globstar_matches_a_direct_child` returned `docs-only` under the non-globstar mutation. Commit `05be52678`.
- *`marketplace/README.md` → buildable* — met, fail-first: `test_build_classify_globstar_matches_a_marketplace_root_markdown` returned `docs-only` under the mutation.
- *`doc/developer/build.adoc` → docs-only* — met: `test_build_classify_keeps_a_doc_as_docs_only`, `source: ci-workflow`.
- *An unreadable rule → buildable, with the reason* — met: `test_build_classify_treats_an_unreadable_rule_as_buildable`.
- *The source holds no workflow filename and no non-building suffix list* — met: `test_classifier_source_holds_no_workflow_name_or_suffix_list`.

**D3 — the rules PLAN-LB-67 D6 restored read the same everywhere and the parity tests can fail.**
- *§1 and §8 give one location for the guard state* — met, fail-first: `test_guard_state_has_one_location_in_rules_and_landing` failed against the reverted §1.
- *The branch rule lists the canonical prefixes as a closed set* — met, fail-first: `test_branch_rule_states_the_canonical_prefix_set_as_closed` failed against the reverted row.
- *§6 step 6 names the "no qualifying review" condition* — met, fail-first: `test_quota_policy_step_names_the_no_qualifying_review_condition` failed against the reverted step.
- *The `sleep` parity test fails when "bare" is put back* — met: `test_sleep_parity_keyword_is_the_qualifier_free_sentence`; observed failing with "never a bare `sleep`".
- *The timeout test fails when the fallback is returned* — met: `test_build_timeout_comes_from_the_architecture_stamp`; observed `assert 1800 == 1234`. Commit `73bbf606a`.

## Personas and skills

- Per step: `persona-implementer` for D1–D3 (production code + docs); `persona-module-tester` for the tests; `persona-code-reviewer` for the two self-review rounds and PR-comment triage.
- Per deliverable: D1, D2 and D3 each declared `pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester` and persona `plan-marshall:persona-implementer`.
- `skills added:` none — no surface drift beyond the spec's Expected Surface (the two read-only resolver modules, `deployed_layout.py` and `marketplace_bundles.py`, were used as the spec's HYPOTHESIS predicted).

## Hypotheses

- `deployed_layout.resolve_skill_path` resolves the flat `{bundle}-{skill}` names — **confirmed** (`marketplace/bundles/plan-marshall/skills/script-shared/scripts/deployed_layout.py:183-207`).
- The classifier's workflow filename and non-building classes can be derived from the project — **confirmed** (`runbook_lane.py` workflow discovery + `_architecture_documentation_surfaces`); the first implementation keyed off a `purpose` field the architecture never emits and was corrected in review to the `build_systems: documentation` marker.
- Verify-first clause (Antigravity flat layout) — **confirmed**: Antigravity deploys `skills/{bundle}-{skill}` (`marketplace/targets/antigravity/emitter.py:232`), the same dash-joined shape as OpenCode's installed `skills/`; `deployed_layout.SKILL_ROOT_NAMES` covers both.
- Verify-first clause (unreadable rule) — decided to reuse the fail-closed direction with a `reason` field on the `build-classify` payload rather than adding a bespoke error type.

## Findings

- Self-review round 1: 8 findings. Addressed: the D2 prose-surface discriminator (load-bearing) at `c78843ef8`; the over-eager unreadable-workflow read; a vacuous assertion. Deferred (low): the probe-list assertion strength; the timeout seam is unit-level.
- Self-review round 2: all three deliverables met; addressed the `resolve_skill_path` use and made `_skill_exists` non-dead at `a365aa6fd`; open: none but the spec-mandated §0 wording and the fail-closed breadth.
- PR #1817: cuioss-review-bot (block-scalar `|` indicator) fixed at `77b9843f0`; CodeRabbit (quoted-scalar normalization; exclude documentation modules from the architecture fallback) fixed at `77b9843f0`; CodeRabbit (a pre-existing Claude `PreToolUse` predicate) answered not-applicable and withdrawn. All four threads resolved.

## Reviewers

| Reviewer | Required | Outcome | Head reviewed | History |
|---|---|---|---|---|
| cuioss-review-bot | yes (not quota-limited) | reviewed | `77b9843f0` (current head) | triggered 08:02 → reviewed `a365aa6fd`; re-triggered 08:24 → guide updated to `77b9843f0`, review + code-review checks pass |
| coderabbit | yes (quota-limited) | reviewed; standing authorization | `a365aa6fd` (a head of this PR) | triggered 08:02 → reviewed with 3 findings; re-triggered 08:26 → rate-limited ("next included review in 36 minutes"), recorded. Qualifying review exists; all findings handled and threads resolved |
| sourcery | optional (quota-limited) | refused | n/a | triggered 08:02 → refused on quota (16h 31m). Optional, does not gate the merge |

## Operator questions

None asked — no `question`-tool call was made in this run. Free-text operator messages: none.

## Rule check

- `guard: present` on this harness (OpenCode). The guard log `.plan/temp/guard.log` has one line for this run's session `ses_ead1d5aedffeUlmR0QStyD4cRa`:
  - `2026-10-19T06:39:19.346Z | tool=shell | rule=R1 | ... | test -f .plan/temp/rb-lb-71-lb-67-completion/progress.md && echo EXISTS || echo ABSENT` — a shell-chaining probe (R1) refused; retried as separate calls.
- One surface/naming symptom, not a rule break: `runbook_lane build-classify` is not a registered verb in the machine's stale executor (its generated verb list predates the verb). No source was changed to silence it; the build gate was taken fail-closed (full `verify` parts run, not skipped). Recorded as residue.

## Residue

- The stale executor does not register `build-classify`; a `marshall-steward` executor regeneration will pick it up.
- `_claude_guard_installed` reports `guard: present` for any Claude `PreToolUse` entry carrying a command, so a render-only hook can read as an enforcement guard. Pre-existing, outside this plan's Write-Boundary; CodeRabbit withdrew its thread and offered a follow-up issue.
