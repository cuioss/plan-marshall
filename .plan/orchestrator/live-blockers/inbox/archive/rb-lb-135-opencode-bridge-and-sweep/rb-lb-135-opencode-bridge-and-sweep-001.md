envelope_version=1
sender_type=plan
sender_id=rb-lb-135-opencode-bridge-and-sweep
epic=live-blockers
kind=landing
created=2026-11-12T18:13:46Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-135-opencode-bridge-and-sweep
epic=live-blockers
pr=#1972
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=4
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2076
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=10
review_body_findings_handled=10
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present

## 1. Deliverables

Every Done-when below was seen failing against unfixed code in the plan worktree while it sat at the failing commit, before the fix was written (`test-first`), or through a deliberate mutation of the committed fix (`mutation-after`). Failing-run identifiers are marshalld job logs under `/home/oliver/.plan-marshall/marshalld/job-logs/`.

### D1 — Setup survives any baseline or bridge bytes (commit `f257d36c1`)
| Done-when | Verdict | Order | Test | Failing run | Passing run |
|---|---|---|---|---|---|
| setup re-run over a `\xff\xfe` CLAUDE.md completes with `bridge_written: false`, `bridge_reason: baseline_unreadable`, bridge unchanged | met | test-first | `test_an_unreadable_baseline_never_overwrites_the_bridge` | `7ac64124b`, `321a42e8c68646aaa81d63607df4e0e2.log` (`UnicodeDecodeError`, `opencode_runtime.py:144`) | `f257d36c1`, `8c5595ea12be4540adb105a07eefa4ae.log` |
| a non-UTF-8 bridge does not raise from setup or the drift status | met | test-first | `test_a_non_utf8_bridge_never_raises_from_setup_or_drift` | `7ac64124b`, `a118d88118de4e529c5b626ff4173dc9.log` (`UnicodeDecodeError`, `opencode_runtime.py:224`) | `f257d36c1` |
| the unreadable-baseline test uses a real non-UTF-8 file with no `_baseline_text` monkeypatch | met | test-first | same test | the monkeypatch is gone; real `write_bytes(b'\xff\xfe …')` | — |

### D2 — Setup reports the drift it healed, from what the write did (commit `6ca920ef3`)
| Done-when | Verdict | Order | Test | Failing run | Passing run |
|---|---|---|---|---|---|
| setup after CLAUDE.md is deleted (non-stub bridge) reports `bridge_drift: true` and writes the stub | met | test-first | `test_a_deleted_baseline_replaces_the_bridge_with_the_stub` | `f257d36c1`, `2ce06b1089504447ac81ab952f80f9c4.log` | `6ca920ef3`, `605b4f4f87f5451fb4654b11284eeca6.log` |
| setup over a hand-edited body (marker+hash intact) reports `bridge_drift: true` | met | test-first | `test_setup_reports_drift_for_a_hand_edited_bridge` | `f257d36c1`, `2ce06b1089504447ac81ab952f80f9c4.log` | `6ca920ef3` |
| `test_a_deleted_baseline_replaces_the_bridge_with_the_stub` asserts `bridge_drift` | met | test-first | same test | `f257d36c1`, `2ce06b10…` (`assert False is True`) | `6ca920ef3` |
| the drift status for a missing baseline plus a non-stub bridge is `drift: true` | met | test-first | `test_standing_rules_drift_baseline_missing_with_bridge` (+ stub control `…_with_stub_bridge`, order `none`) | `f257d36c1`, `e6f97ece3a08445ea83a72f4ea7042c3.log` | `6ca920ef3` |
| every caller of `standing_rules_drift_status` read and recorded | met | none | only `OpenCodeRuntime.project_initial_setup` (`opencode_runtime.py:1590`); `configure_harness._reconcile_standing_rules_bridge` reads the bridge directly; `antigravity_runtime` is an independent copy | — | — |

### D3 — No OpenCode-side surface names the OpenCode 1 shape (commit `55bfbf06c`, extended in `ce942e683`/`7e997df1f`)
| Done-when | Verdict | Order | Test | Failing run | Passing run |
|---|---|---|---|---|---|
| a doc test asserts `target-rules/SKILL.md` carries `shell` and `subagent`, no `bash`/`task` instruction, and describes the hash drift | met | test-first | `test_target_rules_skill_body_names_the_opencode2_tools_and_the_hash_drift` | `d3b5c9bac`, `e158ea5c1cfe4d508b4ad882abac4fbd.log` | `55bfbf06c`, `e4f17a8a67854998ba5dacd0d5e40275.log` |
| a doc test asserts `opencode.adoc` describes the fallback as a list rule and cites only tests that exist | met | test-first | `test_the_role_matrix_describes_the_agent_fallback_as_a_list_rule`, `test_every_cited_test_module_exists` | `d3b5c9bac`, `c9052d841d5e43a99a78dab24f0b5f09.log`, `d43b6136565049a1b5be7afd71e93dff.log` (`test_permission_fix_opencode.py` missing) | `55bfbf06c`, `2059bbe94eea4aaa8a63faecd4f985ed.log` |

### D4 — The guard tests find what they were meant to find (commit `d3b5c9bac`, before D3's edit as the spec requires)
| Done-when | Verdict | Order | Test | Failing run | Passing run |
|---|---|---|---|---|---|
| the widened guard fails at base on `target-rules/SKILL.md` L15, L19, L28, L35 | met | test-first | `test_no_bundle_standard_names_the_opencode_subagent_tool_as_task` | `6ca920ef3`, `55e93b4715e641729766f6e55da41556.log` (exactly those four lines) | `55bfbf06c`, `cfb978d684f64d7ca2c28806d7a64914.log` |
| the precedence test passes at base and fails when `TARGET_ENV_SIGNALS` is reordered | met | mutation-after | `test_env_signal_precedence_is_literal` | mutation run at `6ca920ef3`: `902dab41f147472288bce88e8ed3c628.log` (`'opencode' != 'antigravity'`) | `6ca920ef3`, `087aca49fbf448a093dc2df380c681ad.log` |

Per-head test runs: scoped suites at each pushed head, plus whole-tree `module-tests` at `55bfbf06c`, `5943fa1ea`, `a4d55e0d1` and `verify` at `55bfbf06c`, `5943fa1ea`, `a4d55e0d1`, `da2f86e81`, `7e997df1f` (gates below).

## 2. Personas and skills

- Personas applied: `persona-implementer` (D1/D2 production code), `persona-module-tester` (all tests), `persona-documenter` (D3), `persona-code-reviewer` (both self-review rounds and the PR-comment triage).
- Domain skills: `skills: none named` — the spec declares no `Skills:`/`Persona:` lines.
- Surface drift, recorded: D3's doc test for `opencode.adoc` lives in `test/plan-marshall/platform-runtime/test_opencode_permission_docs.py` (the file that already owns that document) and its SKILL.md test in `test/marketplace/targets/opencode/test_opencode2_dispatch_shape.py` (D4's file); review rounds added `marketplace/bundles/plan-marshall-opencode/README.md` (last OpenCode 1 tool name), `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_core.py` (a comment contradicting the corrected adoc), `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/configure_harness.py` (a steward verdict that certified an unreadable baseline), and `test/plan-marshall/marshall-steward/test_harness_config.py` (the reconcile call sites).

## 3. Hypotheses

- "No other caller of `standing_rules_drift_status` depends on the `baseline_missing` answer for a non-stub bridge" — **confirmed**: the sole production caller is `project_initial_setup` (`opencode_runtime.py:1590`); `configure_harness._reconcile_standing_rules_bridge` (`configure_harness.py:92`) reads the bridge file directly and never calls it; `antigravity_runtime.standing_rules_drift_status` is a separate implementation.
- "`script-shared/scripts/target_context.py` is read-only for D4" — **confirmed**: it is not in `git diff --name-only origin/main...HEAD` (only the mutation run touched it, and the tuple was restored before the commit).

## 4. Findings

Self-review (two rounds, both closed): round 1 fixed the fallback rule spelling (`action: "shell"`, matching the landed `opencode.json`), the bundle README's `bash`, the guard's vacuity check, a fixture docstring that over-claimed, and the `_config_core` comment; round 2 fixed the residual docstrings and the drift sentence's unreadable arm. Every finding was disposed.

PR comments: 19 comments/threads across CodeRabbit (2 reviews, 4 + 6 actionable) and Sourcery (2 reviews, 7 + 9 issues). 14 threads were replied to and resolved; `review-gate` reports 0 unresolved threads and 10/10 review-body findings handled. Fixes: `ce942e683` (writer-reported `replaced`, bytes comparison, strict decode, unreadable-baseline drift, doc corrections), `a4d55e0d1` (staged write + path replace), `7e997df1f` (mkstemp staging, symlink never owned, `bridge_body_replaced` reason, steward refuses an unreadable baseline, standard lists the unreadable reasons). Answered with a stated reason: the drift-reason pairing (spec-mandated pre-heal status), the backticked tool-name needle (the spec's), the sweep population (no emitted file outside it today), the transient-baseline stub (the spec's Done-when), the older-rules window (the recorded hash makes it visible and self-healing), the failed-write payload (no such field in the plan's contract), the literal-signal precedence test (the spec requires literals so a reorder fails it).

## 5. Reviewers

- **coderabbitai** (required, `quota_limited`, `review_complete_after_handling`): triggered at 14:15 on `5943fa1ea`; reviewed that head (marker `kind=reviewed`, `coveredCommitId 5943fa1ea`) and again on the merge head `da2f86e81` (marker covers `da2f86e81`). A quota notice arrived at 14:55 for `ce942e683`; the resolvable flag plus the qualifying review on record meant no further trigger was posted. Every finding of both reviews is handled, so the review stands at the final head; `review-gate` accepted it (no `required_review_missing`).
- **sourcery-ai** (optional, `quota_limited`): triggered at 14:15; reviewed `5943fa1ea` twice (7 and 9 issues) and was skipped on later heads. All its findings are handled above; nothing was gated on it.

## 6. Operator questions

None asked. The merge was executed under the repository's standing merge authorization once every merge-gate condition held.

## 7. Rule check

- **Guard**: `guard: present`; the guard log carries two refusal lines for this run's session (`ses_e3119dfe…`): R1 on a shell pipeline (`ci pr comments … | head`, refused before execution — the command was re-issued without the pipe) and R5 on a mistyped interpreter invocation (refused; re-issued as the executor notation). No refused command executed and no workaround was attempted. Every other script call went through `python3 .plan/execute-script.py …` and every build and CI action through the resolved build commands and `ci`.
- **Shell file operations**: none executed by the run — files were read and searched with the file tools; the only shell calls were `git` (status/worktree/diff/fetch/merge/push/rev-list), `date -Is`, and the build/CI/script invocations.
- **Evidence form**: each "fails at" Done-when was seen failing in the plan worktree while it sat at the failing commit, before the fix (none of the four prohibited forms). The post-hoc base-worktree mechanism added to the lane text by the merge was therefore not needed; the failing runs cite their log paths above.
- **Spec read**: `spec_source: ledger_worktree`, no `spec_differ` marker reported.
- **Executor skew**: `not_applicable` — a source checkout, where the executor maps the checkout's own scripts.

## 8. Build server

- Setup preflight: `ready` (registered, version 1). Every one of the run's 38 builds was routed (`mechanism: daemon_longpoll`, `requested=auto`, `resolved=routed`); no build fell back and no launch-fault retry was needed.
- One bound expiry: whole-tree `module-tests` at `55bfbf06c` hit the daemon bound (`timeout`, `timeout_used_seconds: 750`, `timeout_source: explicit`, `a2e8c14485714651af90fc2345990401.log`); it was re-run with a raised bound (1800 s) and passed in 1212 s.
- Queue waits were long at times (up to 1828 s behind other sessions' jobs); every wait was a bounded re-attach, never a background job. No `killed` job occurred.

## 9. Residue

- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py:260` and a docstring in `test/plan-marshall/manage-config/test_config_defaults.py:1095` still describe `runtime.target` as read from `.plan/marshal.json`. CodeRabbit's fact check (and `target_context.py`) shows the resolver reads only the machine-local files; those two pre-existing prose sites are outside this plan's surface and are left for a documentation sweep.
- `test_every_cited_test_module_exists` matches cited basenames across the whole test tree, so a wrong relative path with a same-named module elsewhere would pass. It caught the real defect; path-aware matching is a follow-up.
- `marketplace/bundles/plan-marshall-opencode/README.md` is now inside the widened guard's population, so a future OpenCode 1 tool name there fails the sweep.
