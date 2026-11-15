envelope_version=1
sender_type=plan
sender_id=rb-lb-128-coderabbit-roster-save-and-summary-concern
epic=live-blockers
kind=landing
created=2026-11-09T20:04:58Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-128-coderabbit-roster-save-and-summary-concern
epic=live-blockers
pr=#1946
merge_state=merged
cleanup_owed=false
deliverables_total=2
deliverables_done=2
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2076
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=0
review_body_findings_handled=0
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present. Runbook-lane mode, no `/plan-marshall` lifecycle.

## Deliverables

### D1 — the retired-bot strip is saved, and an emptied required list re-seeds CodeRabbit — met

- Done-when (a) — met. Test: `TestLiveConfigVerb::test_verb_saves_a_strip_when_no_legacy_key_remains`. Order: `mutation-after` (reverted the committed fix: state forced to `noop`, re-seed disabled). Failing run: commit `2538a13d5`, job `704b536f96924344be2987f4e04e0e88` (`/home/oliver/.plan-marshall/marshalld/job-logs/704b536f96924344be2987f4e04e0e88.log`, 4 failed). Commit: `2538a13d5`.
- Done-when (b) — met. Test: `TestLiveConfigVerb::test_a_strip_that_empties_required_reseeds_coderabbit`. Order: `mutation-after`, same red run. Commit: `2538a13d5`.
- The two pure-function pins amended to `retired_stripped` — met. Tests: `test_a_retired_bot_kind_is_stripped_from_either_roster_list`, `..._from_an_answered_roster`. Order: `mutation-after`, same red run. Commit: `2538a13d5`.
- The `ImportError` fallback is read and reported — met. Test: `test_a_degraded_retired_bot_tombstone_is_reported` (strengthened to empty `_RETIRED_BOT_KINDS` and prove the name survives after the PR review). Order: `none` (guard added in review rounds). Commit: `020de0249`.
- Hold-at-base set (states 1/2, self-disarming, no-step/uninitialized, sync-then-migrate) — met, unchanged pre-existing tests. Order: `none`. Green at `b6fdb064d` — full `verify`, job `d80b57b9236045d99bbefa77a19390b5` (33115 passed).

### D2 — a Merge Risk concern is filed, and the clean verdict does not swallow a nitpick section — met

- Done-when (a) — met. Test: `TestSummaryConcernIsFiled::test_the_observed_concern_merge_risk_block_is_filed`. Order: `mutation-after` (concern veto disabled on the committed fix). Failing run: commit `91ba256dd`, job `15c5acd0c4ff41d2a8f86fc7ce846afa` (`/home/oliver/.plan-marshall/marshalld/job-logs/15c5acd0c4ff41d2a8f86fc7ce846afa.log`, 3 failed; stored 0). Commit: `91ba256dd`.
- Done-when (b) — met. Tests: `test_the_clean_verdict_does_not_swallow_a_nitpick_section`, `test_the_clean_verdict_does_not_swallow_a_merge_risk_concern`. Order: `mutation-after`, same red run. Commit: `91ba256dd`.
- Done-when (c) — met. Tests: `test_the_file_limit_summary_notice_is_a_counted_refusal` (hold-at-base control — the refusal arm runs before the noise filter; order `none`), `test_a_marker_bearing_skip_notice_drops_as_noise` (order `mutation-after`, same red run; filed 1 at base, noise 1 after). Commit: `91ba256dd`, test-strength rounds at `656ea5bb5`.
- Hold-at-base controls (in-progress, plain walkthrough, clean verdict alone, actionable-only, the observed clean Merge Risk wording, the second observed clean wording) — met. Order: `none`. Green at `b6fdb064d` — `verify`, job `d80b57b9236045d99bbefa77a19390b5`.
- Captures: #1942 clean block `IC_kwDOQ3xasM8AAAABkOyUGA`, #1931 concern block `IC_kwDOQ3xasM8AAAABj8Aypw`, second clean wording #1946 `IC_kwDOQ3xasM8AAAABkgH-rg` — all OBSERVED verbatim in `_github_pr_fixtures.py` / the registry.

### Per-head test runs

- `2538a13d5` — module-tests `marshall-steward`: 387 passed (job `cf9987ffa442448a92750c9a0d46aea2`).
- `91ba256dd` — module-tests `workflow-integration-github`: 1561 passed (job `3520193153b9438da2c1dc6b060e428a`).
- content of `b75af1a62` — module-tests `workflow-integration-github` (job `77462286a9e84472a63555d6320dda17`), `marshall-steward` (job `c653e535dc6242b79e6ff580dfb27e43`), `automatic-review` (job `91dbcc6b218d4063af1020c295f9e164`) — green.
- content of `656ea5bb5` — module-tests `workflow-integration-github` (job `0cac24d2fa0e4d449ba25980bd9de1c1`), `marshall-steward` (job `912428a8d55a416e81b90df3a9de93fa`) — green.
- `227604f18` — full `verify`: 33114 passed (job `ab6899fd03044269a8fb221891c155ea`).
- `020de0249` — module-tests `workflow-integration-github` (job `8951e7c3d86240a09eb8b44bf7a8bddd`), `marshall-steward` (job `1dc3cae0bcdc478ab75a0da0b1f05b55`), `automatic-review` (job `903f20af8b624393a35d36e5f5c5fece`) — green.
- `b6fdb064d` (merge head) — full `verify`: 33115 passed (job `d80b57b9236045d99bbefa77a19390b5`); CI `verify / verify` SUCCESS.

## Personas and skills

- production code: `persona-implementer`; unit/module tests: `persona-module-tester`; documentation: `persona-documenter`; self-review and PR triage: `persona-code-reviewer`.
- Per deliverable: `skills: none named` (the spec carries no `Skills:`/`Persona:` lines).
- Surface drift: no domain skill added — the extra files (`bot-participation-contract.md`, `automatic-review/SKILL.md`, `marshall-steward/SKILL.md`, four `test_bot_participation_contract_*.py`, `test_bot_registry_markers.py`) are inside the spec's own two skills and were forced by a pin or a statement the change makes false.

## Hypotheses

- Merge Risk clean-vs-concern marker not stored anywhere, capture from live comments — **confirmed**: nothing stored; captured `Merge Risk:` and the two observed no-risk literals. The sub-claim that the risk level marks clean is **refuted**: #1931 carries a concern under `Low`, #1942 is clean under `Minimal`, #1946 is clean under `Minimal`; only the verdict sentence discriminates.
- The #1931 concern is also posted through a formal review — **refuted**: the 14 formal reviews carry two review-body summaries, neither states the contract-test concern; it appears only in summary `IC_kwDOQ3xasM8AAAABj8Aypw`. No duplicate-channel loss.
- `test_upgrade.py` / `upgrade-flow.md` do not pin or branch on `noop` for a strip-only input, and `_cmd_sync_defaults --backfill-bot-roster` does not re-introduce the retired name — **confirmed** (`test_upgrade.py:470-483`, `_cmd_sync_defaults.py:637-644`; the `upgrade-flow.md` prose was corrected).

## Findings

Self-review (3 rounds, `persona-code-reviewer`, report-only):
- Round 1 — 15 items: fail-open on the `ignore_patterns` path, docs made false by the change, `</details>` boundary, unclosed-comment handling, "four states" references, untested arms. Fixed in `b75af1a62`; the state-label nit left as the spec's five states.
- Round 2 — 6 items: a lost `def` line merged two tests, two untested fail-closed arms, the missing optional-list/no-reseed arms, two doc drifts. Fixed in `656ea5bb5`.
- Round 3 — 5 non-blocking: two comments fixed in `227604f18`; one accepted test-strength nit; two recorded in the PR (the file-limit control holds at base; the boundary deviation). State `budget-exhausted`; the operator chose to proceed.
CodeRabbit: one review-body nitpick (the degraded-tombstone test did not prove the strip could not fire) — fixed in `020de0249`. A second clean-verdict wording observed on this PR was added as data (`coderabbit.md`, `IC_kwDOQ3xasM8AAAABkgH-rg`) with a control.

## Reviewers

- `coderabbit` (required, quota-limited): reviewed `227604f18` (review `PRR_kwDOQ3xasM8AAAABW2p6rw`; summary marker covered `227604f18`, `kind=reviewed`). Re-triggered after each later push: refused for quota at `020de0249` (`IC_kwDOQ3xasM8AAAABki61lQ`, 17:59:20Z) and at `b6fdb064d` (`IC_kwDOQ3xasM8AAAABkkOTyw`, 19:07:25Z). Standing review authorization applies: qualifying review exists, its only finding is fixed in `020de0249`, the post-push re-trigger refusal is recorded, and every other gate is green on `b6fdb064d`.
- `sourcery` (optional): triggered, refused for its own budget notice both times; not required.

## Operator questions

1. Asked: "The self-review loop reached its 3-round limit … A fourth review round would re-check these without changing behaviour. How should I proceed?" Options: `Proceed to the PR (Recommended)`, `Run a fourth review round`. Selected: **Proceed to the PR**.
Free-text operator messages: none.

## Rule check

- `executor-skew`: `not_applicable` (source checkout; the lane text is the checkout's own) — answered, recorded, not asked.
- Spec read: `spec_source=ledger_worktree`, `spec_differ` absent (the two copies agree).
- Guard: `present`; the guard log has no line attributable to this run's session tree, and the run's own actions kept every shell rule (no `&&`/`;`/pipes/substitution; file reads via the file tools; writes only under `.plan/temp/`, the `ci` body slots, and the source tree inside the worktree).
- Builds: 27 routed builds, all `daemon_longpoll`; no launch-fault retry, no `degraded` fallback, no `killed` job. Two red builds were real: a module-tests run where an edit had merged two tests (fixed), and a quality-gate run whose first pass reformatted one file (re-run green). One `verify` failed only in the unrelated target-tree generation precondition (`[Errno 39] Directory not empty`) and passed on re-run.
- No rule break was committed; every failed check was fixed in a pushed commit before the merge.

## Build server

- Setup preflight: `ready` (registered, version 1).
- Mechanism: `daemon_longpoll` for every one of the 27 builds; no `in_process_fallback`.
- Fallbacks/retries: none (no launch fault, no `degraded`, no `directory_busy`).
- Killed jobs: none. `runtime_stamp_reason`: none.

## Residue

- **Review-gate parser gap (belongs to PLAN-LB-129).** `runbook_lane review-gate` does not match CodeRabbit's current `<picture>`-decorated section title with a `: N` count (`Nitpick comments: 1`), so it reported `review_body_findings_total: 0` while the live review body carried one nitpick. The finding was triaged and fixed by hand; the gate's reported numbers are its own fact (0/0/0). This is a fail-open in the gate parser, out of this plan's surface.
- The `## Review skipped` trade-off (a reworded refusal under that heading drops as noise instead of reaching the enumerative arm) is recorded in `coderabbit.md` and the PR body.
- The concern-section boundary deliberately deviates from the spec's literal `<!--` terminator (comments are stripped first, then the section is bounded at the next heading / `<details>` / `</details>`), because the literal rule truncates the captured Merge Risk text; documented in code and the registry.
- Operator-run harness sync is owed for the `marketplace/bundles/` edits (the lane does not run it).
