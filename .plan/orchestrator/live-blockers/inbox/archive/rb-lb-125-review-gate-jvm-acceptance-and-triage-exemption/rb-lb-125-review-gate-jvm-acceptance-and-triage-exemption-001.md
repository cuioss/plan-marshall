envelope_version=1
sender_type=plan
sender_id=rb-lb-125-review-gate-jvm-acceptance-and-triage-exemption
epic=live-blockers
kind=landing
created=2026-11-08T09:25:49Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-125-review-gate-jvm-acceptance-and-triage-exemption
epic=live-blockers
pr=#1939
merge_state=merged
cleanup_owed=false
deliverables_total=5
deliverables_done=5
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2076
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
step.sonar-roundtrip.open_issue_count=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

# PLAN-LB-125 landing — merged as bbe421f15

## 1. Deliverables

**D1 — a disabled JVM test is decided per method, and an acceptance pairs each marker with its test** — all Done-whens met.
- Java: branch adds `@Disabled` to `a()`, accepted by a close, then to `b()` → row not covered — **met**, `mutation-after`, `test_a_java_method_added_after_an_accepted_one_is_raised`, failing run `f5a16312f` / job `03f4deacc37448d2a7c3c73612aa85e1`.
- Control: only `a()` disabled raises nothing beyond the accepted row — **met**, `none`, `test_a_java_class_with_only_the_accepted_method_disabled_raises_nothing`.
- Base disables `a()`, branch disables `b()` → row — **met**, `mutation-after`, `test_a_base_disabled_jvm_method_does_not_mask_a_second_one`, failing run `b1415b69d` / job `4bf2ada9f13c48399fcdd8d2d8843b38`.
- Accepted `{skip on a, xfail on b}`, `b` switched to skip → row — **met**, `mutation-after`, `test_an_accepted_skip_on_a_and_xfail_on_b_does_not_accept_skip_on_b`, failing run `b1415b69d` / job `1a960f0e119041918e15b01aac259ca0`.
- Existing Python and JS fixtures keep their results — **met**, full `module-tests` green (job `905f2c1b05994cde9d6d71e2474f8010`).
- Extra regressions: Python `assert is_valid(cfg)` is not a JVM identity (`mutation-after`, job `bf2a2fe9a3e2427ca11b58ed2695bf56`); Kotlin class header is scope (`mutation-after` via the disabled arm); Kotlin semicolon-free statements and anonymous-class initializers are not identities (unit fixtures).

**D2 — triage honours a dropped functional review** — all Done-whens met.
- Verify-first (1) confirmed: the manifest drops only `functional-review` on surgical scope, the `automatic-review` carve-out keeps that producer, so `finalize-feedback` triage still fires; recorded in the PR.
- Verify-first (2) confirmed: `_write_snapshot_locked` returns `refreeze_requires_decision` for a frozen snapshot; `phase-3-outline` now routes it to the operator and `criteria-refreeze-authorize`.
- Dropped review reports no open row — **met**, `mutation-after`, `test_open_criteria_reports_review_dropped_for_a_dropped_review`, failing run `b1415b69d` / job `cc38148edf54414da9f87b0497227819`.
- Scheduled review + ungraded criterion still reported — **met**, `none`, `test_open_criteria_keeps_a_scheduled_review_open`.
- Dropped review + tampered snapshot still open — **met**, `none`, `test_open_criteria_still_reports_a_tampered_snapshot_with_a_dropped_review`.
- Doc test pins the sentence once — **met**, `none`, `test_triage_states_the_drop_exemption_once`.

**D3 — the placement and the coverage marker fail closed** — all Done-whens met.
- Node with both stable fields null is not credited — **met**, `mutation-after`, `test_placement_refuses_the_mutable_commit_when_no_stable_field_exists`, failing run `b1415b69d` / job `a7d9e3fa3e8e4a389ef79b219f0ec11d`.
- Unterminated fence before an in-progress marker: neither credited nor admitted — **met**, `mutation-after`, `test_a_marker_after_an_unterminated_fence_is_a_claim_nobody_can_read` and `test_a_marker_after_an_unterminated_fence_is_not_admitted_as_an_answer`, failing run `b1415b69d` / job `f9a354b37b3a42408b29defbe8677c6d`.
- Finished single-line marker still credited (control) — **met**, `none`.
- Two-line payload read — **met**, `mutation-after`, failing run `b1415b69d` / job `729eb66b7483400a9878b4a514c7ae57`.

**D4 — the close and the move proof state their reach** — all Done-whens met.
- JS `A::renders` not absorbed by a new `B::renders` — **met**, `mutation-after`, `test_a_js_identity_is_qualified_by_its_enclosing_describe`, failing run `b1415b69d` / job `1b103704d362431ea650db5efc865bc0`.
- Accepted removal with no review-validated head refused — **met**, `mutation-after`, `test_a_close_accepting_a_removal_with_no_validated_head_is_refused`, failing run `b1415b69d` / job `c71930447ed14bb4b5cfa3ba4a43156f`; the cross-step laundering case is pinned by `test_closing_another_step_does_not_launder_a_review_removal`.
- Non-review step close at an unvalidated head refused — **met**, `none` (pins existing behaviour), `test_a_close_of_another_step_at_an_unvalidated_head_is_refused`.

**D5 — the documents and tests state what they pin** — all Done-whens met.
- `review-rubric.md:42` names `criterion_unparsed` and the generation-2 replay; `_plan_parsing.py:64` states the splitter's limit; the loop-back control docstring; one fence owner (`markdown_fence.py`) — **met**, `none` (document reads).
- Fetch-layer test drives the real fetch — **met**, `mutation-after`, failing run `b1415b69d` / job `9632ba37043b40b3af0def5309c83989`.
- Sourcery signal + multiline footer filed — **met**, `mutation-after`, failing run `08368134f` / job `fa79293a826c4d809ac669295872c228`.
- Currency classifier decides — **met**, `none` (pins existing classifier behaviour).

## 2. Personas and skills

- Production code: `persona-implementer`; unit/module tests: `persona-module-tester`; the self-review rounds and every PR-comment triage: `persona-code-reviewer`.
- The spec declares no `Skills:` or `Persona:` lines for any deliverable (`skills: none named`).

## 3. Hypotheses

- A JVM file has no method identity — **confirmed** (`_review_support_integrity.py:87,102` before the change).
- A review-comment node can carry neither `originalCommit` nor a review commit — **confirmed** (`_inline_comment_placement` had a mutable `commit` fallback).
- The live CodeRabbit marker is single-line — **refuted** for the wrapped shape: the summary shows a two-line payload (`_github_pr.py:387-388`) and the parser read only the opener line.
- A dropped-review plan reaches finalize triage — **confirmed** (D2 verify-first (1)).
- `refreeze_requires_decision` is reachable — **confirmed** (D2 verify-first (2)).

## 4. Findings

- Self-review round 1: JVM arm applied to every file (false rows and a masking acceptance), unclosed-fence flag leak, multi-line join bound, doc drifts, dead fixture — fixed in `08368134f`.
- Self-review round 2: Kotlin class header consumed as a method (cross-file move fail-open), anonymous-class initializer, source-count doc — fixed in `52145c15c`, with the indentation-as-type regex defect fixed in `f5a16312f`.
- PR review (CodeRabbit, head `f5a16312f`): deliverable splitter not fence-aware (major), cross-step accepted-removal laundering (major), `_moved_pre_image` path rebinding (major), hardcoded coverage-marker hint (major), Kotlin statement identities (minor), `snapshot_busy` wording (minor), plus one nitpick — all fixed/answered in `23373612e`, `814a037a5`, `aae638134`; every thread resolved.
- CI: one `verify` run failed on a build-server routing timing test outside this plan's surface (`test_route_hand_back_carries_queued_seconds_when_the_bound_expires`), which passes in isolation — recorded as a flake, not this change.

## 5. Reviewers

- `coderabbit` (required, quota-limited): refused on quota at 03:11:15Z, 05:01:47Z, 06:57:22Z, 08:28:33Z; accepted the 06:33:51Z trigger and reviewed head `f5a16312f` at 06:43:55Z (6 actionable + 1 nitpick), and head `814a037a5` at 07:44:24Z (1 minor). Every finding fixed or answered; every thread resolved. Re-triggered after the last push; the final refusal is recorded. Standing review authorization used: a qualifying marker-bearing review covers `814a037a5` (one of the PR's heads, `coveredCommitId=814a037a5`, `kind=reviewed`), every finding is handled, the re-trigger is recorded, and every other gate is green on the merge head.
- `sourcery` (optional, quota-limited): refused on a hard quota (3 days 23 hours) at 03:11:24Z; optional and non-gating.

## 6. Operator questions

None asked. No free-text operator instruction was used to bypass a gate.

## 7. Rule check

- Guard: `present` on this harness.
- One guard refusal: an attempted `python3 -c …` direct-interpreter call was refused by the plan-marshall guard (R5). No action was taken from it; every subsequent script call went through `python3 .plan/execute-script.py`.
- Shell file operations: none; files were read with the Read/Grep/Glob tools. `git` was used for status/diff/log/fetch/merge/push, never `git grep`.
- Builds: every build went through the resolved build command with the default routing; no direct `ruff`/`mypy`/`pytest` invocation.
- Commits: one commit per logical group, not per deliverable (the deliverables share the same files). Subjects name the deliverables affected.
- Spec read: `resolve` read the ledger-worktree copy (`spec_source: ledger_worktree`); `spec_differ` was not raised.
- `executor-skew`: `not_applicable` (source checkout; the executor maps this checkout's own scripts).

## 8. Build server

- Setup preflight: `ready` (worktree registered).
- Every build ran `daemon_longpoll`; fallbacks: none (no `degraded`, no `launch-fault-retry`, no `executor_absent_from_worktree`).
- Counts: `quality-gate` 9 runs (three failed on formatting/type/plugin-doctor findings and were fixed, six succeeded), `module-tests` 3 full runs plus focused runs, `verify` 6 full runs (one failed on a build-server flake, one on a Kotlin identity regression that was fixed) plus focused runs; the final post-merge `verify` and CI `verify` are green.
- No `killed` job; no runtime-stamp reason was reported.

## 9. Residue

- Documented limits kept: a JVM method header with a wrapped parameter list yields no identity; a JVM return type containing a space after a generic comma yields none; the multi-line coverage payload scan is bounded at 40 lines and stops at a fence or `-->`; the D3 fixture does not carry the literal head-SHA token, so the token-arm fall-through itself is not exercised (the parser verdict and the admission gate are).
- The spec's Expected Surface did not name `script-shared/scripts/markdown_fence.py` (new) or four test files the change touched; recorded here for the orchestrator's disjointness input.
- A harness sync is owed after merge, as the spec's Dependencies section states.
