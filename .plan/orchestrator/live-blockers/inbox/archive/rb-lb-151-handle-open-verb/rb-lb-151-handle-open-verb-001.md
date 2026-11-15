envelope_version=1
sender_type=plan
sender_id=rb-lb-151-handle-open-verb
epic=live-blockers
kind=landing
created=2026-11-15T02:07:53Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-151-handle-open-verb
epic=live-blockers
pr=#1987
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=4
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2123
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=10
review_body_findings_handled=10
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present (OpenCode pre-tool-use guard; this run's refusals are recorded in the rule-check section).

# PLAN-LB-151 landing — the `handle-open` verb

Merged as `2f0630bc02f69b5681f76756980a714016239357` via PR #1987 (merge queue, merge_group run 43664413631 SUCCESS). Branch deleted locally and remotely; worktree removed after a clean `status --porcelain`; main switched and pulled to `2f0630bc0`.

## 1. Deliverables

| D | Done-when | Verdict | Test | order | Failing run (commit, output id) | Commit |
|---|---|---|---|---|---|---|
| D1 | standard carries `## Handle-Open Contract`; persona attribute 9 names `handle-open`; Terminal-Title list contains it and the count word equals the list length | met | `test_handle_open_contract.py::TestContractPresence` | test-first (base-sha recipe) | `72ef749af`, job `1a9d32e2ffe2409cba5a68cd1836d47d` → `the standard carries no '## Handle-Open Contract' section`, `the persona's identity attribute 9 does not name 'handle-open'` | `62e26c5d5` (+`965ad66b9`) |
| D1 | holds at base: `test_cleanup_contract.py` group (b) passes against the edited standard; no other marketplace file defines the cap rule | met (the `'thirteen'` count-word entry was required — see §7) | `TestVerbEnumerationAgreement` + `TestSingleCapDefinition` | test-first | base run passed with the unedited standard; at head the enumeration is 13 | `62e26c5d5` |
| D2 | document exists; routing both directions; Usage lists it; no `AskUserQuestion` block; names the knob and states no default; carries the eight prohibitions by name | met | `test_handle_open_contract.py` groups (a)-(f) | test-first (base-sha recipe) | `72ef749af` → 20 failed, all in this module (`handle-open.md` absent; `7 of 8 prohibitions…`) | `d7e36e6db` (+`965ad66b9`, `7bb19e6db`, `6fe58abad`) |
| D3 | set 0/100 persist; 101/-1/true/90.5/ninety refused with nothing written; typo refused; get on an unset field returns the seeded default with `set: false`; sync-defaults backfills without touching a set value | met (under the body's own "unset field" wording — see §7) | four manage-config modules | test-first | base tree CLI: `orchestrator get --field decision_confidence_threshold` → `error_type: unknown_field`; `sync-defaults` added 139 paths with no `orchestrator.decision_confidence_threshold` | `573d4b8b9` (+`6f1dd8d54`, `33fc5662b`) |
| D4 | the new module fails at base and passes after; every matched control fails when its planted violation is removed; the three named pre-existing suites pass unchanged | met | `test_handle_open_contract.py` (11 controls), `test_orchestrator_dispatch_workflow_pin.py` (2 added controls) | test-first | 20 live pins red at `72ef749af`, all controls green there | `830220de2` (+`6fe58abad`, `33fc5662b`) |

Per-head test runs (module-tests): `830220de2` 1695 (job `35ff83ec…`), `600ab7106` 1701 (job `7379725b…`), `6f1dd8d54` 1703, `6fe58abad` 1703 (job `6b3605f7…`), `33fc5662b` 1703 (job `cf244c81…`). manage-config: 1553/1570/1572/1574. `verify` at `600ab7106` 33928 (job `5d1c8d17…`), at `6f1dd8d54` (job `77043896…`), at `6fe58abad` (job `c74714d8…`), at `607fa1710` (job `2ce71fc9…`), at `33fc5662b` (job `8aa81950…`). Quality gate green at each head. One earlier `verify` at `830220de2` failed on a pre-existing parallel-only race in `test_target_tree_foundational_skill_freshness.py` (module-scoped fixture runs `pw generate --target all` once per xdist worker into the same `target/`); that module passes standalone in both modes and no file it exercises is in this diff.

## 2. Personas and skills

- D1/D2 — `persona-documenter`; `pm-documents:ref-documentation`, `pm-plugin-development:plugin-architecture`.
- D3 — `persona-implementer`; `pm-dev-python:python-core`, `plan-marshall:ref-code-quality`.
- D4 — `persona-module-tester`; `pm-dev-python:python-core`, `pm-dev-python:pytest-testing`.
- Self-review and every PR-comment triage — `persona-code-reviewer`.
- `skills added: none` — no deliverable touched a module outside the Expected Surface. One file outside the declared surface changed: `test/plan-marshall/plan-orchestrator/test_cleanup_contract.py` (see §7).

## 3. Hypotheses

- `orchestration.adoc` carries a verb enumeration — **REFUTED** (`doc/concepts/orchestration.adoc:67` defers to the router).
- the dispatch-pin test enumerates dispatching verb docs, so the new doc must be added — **CONFIRMED** (`test_orchestrator_dispatch_workflow_pin.py:60-64` floor + tree derivation; the count derivation was hard-coded).
- the seeded default changes the config seed and the seed tests pin the block as a literal — **CONFIRMED** (`_config_defaults.py:297`, and four dict-equality assertions).
- `--field` is whitelist-validated, not argparse `choices`, so no executor regeneration is owed — **CONFIRMED** (`_cmd_orchestrator.py:70`, `:229`, `:280`; `add_field_arg` has no `choices`).
- `effort-roles.md` needs no change — **CONFIRMED** for the effort surface; **but** its scalar-knob sentence did need the fourth knob (review finding, fixed).
- `plan-marshall/README.md` does not enumerate orchestrator verbs — **CONFIRMED**.

## 4. Findings

Self-review (4 rounds): 10 + 6 + 4 + 2 findings, all implementation findings fixed in `965ad66b9`, `7bb19e6db`, `600ab7106`; the 2 remaining are spec-owned (§7).

CodeRabbit (the only reviewer obtained): 10 findings across two reviews, all fixed in `6f1dd8d54`, `6fe58abad`, `33fc5662b`; every thread replied to with a commit and resolved; `review-gate` reports 0 unresolved threads and 10/10 handled. Highlights: the scalar whitelist and the two help lists are now derived; the confidence-cap prohibition population is parsed from the contract's decision-acts bullet (scoped to it); the dispatch-index population is derived from the tree; the anchor replacement must be built from the current anchor; leave-open/stop/skip no longer get a decided marker; a stale analysis is refreshed before presentation on BOTH the decision and the operator-answer paths; a stored threshold is validated strictly on the read path and a malformed `orchestrator` block fails closed.

CI: green on every pushed head. No CI review comments to triage.

## 5. Reviewers

| Reviewer | Required | Outcome | Head reviewed | History |
|---|---|---|---|---|
| coderabbit | yes | reviewed | `600ab7106` (qualifying review, coverage marker `kind=reviewed`), then re-reviewed `607fa1710` and `33fc5662b` | 4 quota refusals (16:26Z, 18:31Z, 20:13Z, 21:44Z) with a 90-minute wait before each re-trigger and one escalated `full review`; accepted at 23:16Z |
| sourcery | no | refused (quota) | — | one trigger at 16:26Z; hard quota ("4 days and 11 hours"); optional, so not re-triggered |

Standing review authorization was not needed: a qualifying review exists and all 10 findings are handled, so `review-gate` passes on the current head. `review_complete_after_handling: true` for coderabbit — no re-trigger was posted for the later heads.

## 6. Operator questions

1. "Section 2 requires clean `git status` but the main checkout shows modified `uv.lock` (ruff lock churn)" — options [Proceed with the run, Stop the run as blocked]; **selected "Proceed with the run"**.
2. "Self-review at the 3-round limit — 3 implementation findings fixed, 2 spec-owned items open" — options [Run one more confirming round, Stop at the limit, Stop and open the PR unmerged]; **selected "Run one more confirming round"**.

Free-text operator messages: none.

## 7. Rule check

- `executor-skew`: **not_applicable** (source checkout; executor 0.1.2123, lane text in the bundle checkout) — answered, recorded, not asked about.
- Spec read: `spec_source=ledger_worktree`, no `spec_differ`.
- Guard: **present**. Two refusals: (a) a `cp --parents …` file copy for the base-evidence tree — the sanctioned base-tree recipe requires copying a committed test file in and restoring tracked files afterwards, and the guard refused the shell form, so the copy was redone with the Write tool; (b) a `grep -rn` used once to locate `add_field_arg` — replaced with the Grep tool immediately. Both were retried the sanctioned way; no workaround was attempted.
- One non-lane tool use: `date -Is` for timestamps (no file access).
- Base evidence used the sanctioned detached tree (`worktree-create --detach --base 72ef749af`, `executor_in_worktree: present`, owner marker written, removed with `git worktree remove` after a clean status). Restoring the tracked `.plan/marshal.json` I had temporarily pointed at a fixture, and the build's `uv.lock` churn, was done with the Edit/Write tools — no `git checkout`/`restore`.
- `uv.lock`: the project's own build refreshed it; its content equals what `origin/main` already carries (its #1985), so it was committed as `f35172ad8` to keep the branch mergeable and contributes no delta against main.
- No `sleep`; every wait was `ci pr wait-for-comments` / `ci checks wait` / `build_server wait`.
- **Open residues.**
  - `test/plan-marshall/plan-orchestrator/test_cleanup_contract.py` is edited (`_NUMBER_WORDS += 'thirteen'`) but is not in the spec's `## Expected Surface`. The edit is required: the count-word lookup returns `None` for `thirteen`, so the edited standard's own pin cannot pass without it. The spec is internally inconsistent here (D1 says group (b) passes "against the edited standard" while the Expected-Surface list omits the file).
  - D3's Done-when says `get` on a *fresh seed* returns `set: false`, which is unsatisfiable because D3 requires the seed to materialise the key. Implemented to the deliverable body's own wording ("`get` on an **unset** field … `set: false`, as `auto_emit` does"), which is what the tests pin.

## 8. Build server

Setup preflight: **ready**. Every build reported `mechanism=daemon_longpoll` (compile, module-tests ×7, quality-gate ×6, verify ×6, plus the base-tree module-tests); **no fallback and no retry**. One daemon-routed build returned `status: running`/`queued` twice under machine-wide slot contention (`queued_seconds` 1204 and 1807) and was re-attached with `build_server wait`; none was backgrounded and none was killed. No `runtime_stamp_reason`.

## 9. Residue

- The two spec-owned items in §7 (Expected-Surface gap; D3's fresh-seed sentence) — for the orchestrator to reconcile in the spec.
- Whether the Sourcery quota (4 days 11 hours) clears is outside this run; it is an optional reviewer, so nothing is owed.
