# Landing Analysis: PLAN-LB-29 — Harness sync

epic: live-blockers
workstream: WS-04
pr: #1724 (https://github.com/cuioss/plan-marshall/pull/1724)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-29.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox message `plan-lb-29-harness-sync-014.md` (kind `landing`, `landing-check`
`complete: true`; its surface delta is `unmeasured`, because neither a declared nor a
realized set was supplied to the check). Checked against:

- `ci pr queue-state --pr-number 1724`: `pr_state: merged`,
  `merge_commit_sha: 35b5589b5ab6d007656c30cbf18e26332f9e3fec`, merge-group run `success`.
- `git show --shortstat 35b5589b5`: 72 files, 13108 insertions, 2048 deletions.
- A read-only review of the commit against the spec, deliverable by deliverable, by a
  delegated agent that ran nothing. Its verdicts are the table below.
- The `opencode.json` hunk of the commit, read here (first part; the diff is about 80 KB).

Not read by that review: `targets/README.md`, `marketplace-build.adoc`, ADR-025, the three
sync command files (searched only), the antigravity skill-directory test, the nine symlink
test modules, the `script-shared` tests, the run-config and manifest tests, and most of the
`test_plugin_pin_trap.py` diff. No test was run here; the merge-group run is the evidence
that the suite passes. Every "fails before the change" condition of the spec is unverified.

## Deliverable Fidelity vs Spec

The spec lists nine deliverables; the plan reports fifteen. The nine are judged here by
their source tag; the additions are listed after the table.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| PLAN-LB-15 D1 — the sync reports registry parity | shipped, with a deviation | `sync.py` `_sync_claude` / `_registry_parity` attach a `registry_parity` block with one row per entry and scope. `behind` gives `status: partial` and exit 3. A fourth verdict, `ahead`, was added and is not red — the re-scope note of 2026-10-08 asked for it. Tests assert behind, in-parity, absent, ahead and dry-run on fixtures |
| PLAN-LB-15 D2 — one reader for registry and executor version | shipped-as-specified | `script-shared/scripts/plugin_registry.py` (`read_registry`, `read_executor_version`, `classify_parity`) is used by the sync, the pin trap and the orchestrator. The executor version is read from `MARSHALL_VERSION`, as the re-scope note required |
| PLAN-LB-15 D3 — a repin that is ordered, backed up and atomic | partly shipped | `marketplace/targets/claude/registry_pin.py` (`repin`, `_apply`) has the order, the backup, the atomic replace and the gate; tests prove order, an injected failure and the dry run. Two gaps: the finalize "run" is asserted against a resolver defined inside the test that mirrors the skill's table, so only the document text is checked; and foreign registry entries are preserved by value, not byte for byte, because the file is re-serialised |
| PLAN-LB-15 D4 — the restart check scores registry parity | shipped, with a deviation | `orchestrator.py` `_registry_parity_signal` and `_cache_parity_signal` score the arm and it joins the floor. The tests are in a new module (16 arrangements), not the file the spec named |
| PLAN-LB-15 D5 — every harness command states the same post-sync steps | shipped-as-specified | `test_harness_command_parity.py` asserts a byte-identical post-sync block and the order sync, repin, restart. Remaining `/reload-plugins` mentions all say it is not sufficient |
| PLAN-LB-17 D1 — the emitters ship the whole skill directory | shipped, with a deviation | `_emit_skill` in both emitters copies what `iter_emitted_skill_files` yields; the fixed sub-directory list is gone. Dot-files are excluded here while the Claude emitter still ships them; the difference is documented |
| PLAN-LB-17 D2 — the install mirrors the generated skill | shipped-as-specified | `sync.py` `_deploy_skill` and `_remove_absent_from_source`; `TestDeploySkillMirror` covers install, prune and dry-run for both targets, including a `workflow/` file |
| PLAN-LB-17 D3 — every routed file is emitted, proven on the real bundles | shipped-as-specified | `test_skill_route_emission.py` generates every target that emits a bundle tree, asserts a non-zero route count and has a negative control on `workflow/planning.md` |
| PLAN-LB-17 D4 — the fixed list is gone everywhere | shipped-as-specified | a search finds the constant only in two absence assertions |

Added during the run, as far as the diff shows:

- `.plan/project-architecture/` is classified as infrastructure configuration
  (`_manifest_core.py`, `decision-rules.md`), and the Q-gate module-mapping check reads a
  project mapping list (`q-gate-validation.md`, a new `test-impl-mapping.adoc`). These are
  the fixes for the two accepted quality-check findings.
- A `registry-repin get/set` setting in `run_config.py`, default `disabled`; ADR-025.
- Symbolic-link hardening at five sites (emit output, source walk, install sync, cache
  sync, repin) with a new `targets/fs_safety.py`. This class came from CodeRabbit over two
  review passes and is beyond the staged spec; the PR body says so.
- The staleness guard rejects a sentinel that is not a JSON object.

The operator decision the spec left open — whether the sync may write Claude Code's plugin
registry — landed as: report by default; write on `sync.py --repin`, on
`registry_pin.py --apply`, or at finalize when the `registry-repin` setting is `enabled`.
The setting gates the finalize step only, not the two direct forms.

Realized surface against the declared one: 26 of the 72 changed files are declared; 46 are
not (5 scripts, 3 configuration or generated files, 10 documents, 28 tests). Both declared
and untouched files were conditional entries. Among the undeclared files are
`plan-orchestrator/workflow/cleanup.md` and `plan-marshall/workflow/q-gate-validation.md`.

## Metrics and Anomalies

- Tokens: 16,838,118; the landing message says the figure spans populations (dispatched
  plus one inline phase).
- Duration: 94,828 seconds wall time (about 26 hours), including an overnight pause and two
  90-minute waits on CodeRabbit's quota. The execute phase's 21.5 hours absorbs finalize
  time, because a loop-back stamps no phase boundary (lesson `2026-10-09-15-003`).
- The pre-submission self-review ran six rounds and returned 29 findings, nearly all prose
  claims, and was closed by the operator at the round limit; the facts carry
  `acceptance=accepted` with `may_close=no`. The fixes of its last commit were not
  re-reviewed in-house.
- The loop-back ceiling of 5 was exceeded twice on operator authorisation; the counter
  ended at 7. Both extra rounds fixed further sites of the symbolic-link class.
- 11 of 17 execute dispatches stopped to hand a whole-tree test run to the main session,
  at 3.9 million tokens, because no scoped test target resolves for the changed paths.
- `scope_creep_check` failed six times; 26 files outside the declared surface were
  modified and none of that reached the findings store.
- Task planning ran twice: adding three deliverables after tasks existed cleared and
  re-created all of them.
- All 38 dispatch-boundary rows lack a step id.
- `archive-plan` is listed `pending` because the message was written before it ran.
  `cleanup_owed=false`.

## Routing and Merge Behavior

- Review: CodeRabbit reviewed over several passes and found the symbolic-link class at
  four sites. Its hourly quota refused a re-review twice. Sourcery refused the PR for diff
  size. cuioss-review-bot left an empty review on the final head. The in-house review saw
  the install-sync write-through one round before CodeRabbit filed it and did not file it.
- CI/merge: squash-merged through the merge queue; the merge-group run concluded `success`.
- Collisions with plans in flight: `plan-orchestrator/scripts/orchestrator.py` and
  `plan-orchestrator/SKILL.md` were rebased onto PLAN-LB-14's landing, as the ledger
  required. PLAN-LB-24 (running) declares none of the files this commit changed, as far as
  the earlier cross-check measured; the 46 undeclared files were not in that measurement.
- The registry on the machine that ran the plan was repinned once at the operator's
  direction, from 0.1.1886 and 0.1.1875 to 0.1.1888; the setting stays `disabled`, so the
  next finalize there reports `behind` again.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-29 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-29 --field pr --value 1724`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-29 --field landing --value landings/PLAN-LB-29.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-29 --field plan_marshall_plan_id --value plan-lb-29-harness-sync`
- [x] epic.md narrative reconciled against the queue rows (queue annotations)
- [x] Open Defects added: the root `opencode.json`, `--repin` scope, the symbolic-link leftovers
- [x] Watches retired or updated: the PLAN-LB-14 rebase, the harness-install lag
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated with the row change

## Follow-Ups

- **The root `opencode.json` was rewritten into a shape nothing in this repository reads.**
  `permission.bash`, a map of command pattern to `allow`/`ask`/`deny`, became a
  `permissions` array of `{action, resource, effect}` objects; `agent` became `agents`;
  `skills.paths` became a bare list. The file grew from about 650 to about 2730 lines.
  `opencode_runtime.py` reads `permission` and the OpenCode emitter writes `agent`. The
  change is in no deliverable and has no producer in the diff. If OpenCode does not read
  the new shape, the deny rules for `gh`, `rm`, `git restore` and the rest are inert there.
  The upstream schema was not checked. Recorded as an Open Defect.
- **`sync.py --repin` can repin bundles the run did not sync**: it passes the one synced
  version as the target for every registry bundle, so `--bundles X --repin` also moves
  other bundles that have a directory of that version. Recorded as an Open Defect.
- Three symbolic-link leftovers the plan itself names, all confirmed in the code:
  check-then-act windows between the link check and the write (`registry_pin.py`, `sync.py`,
  `cache_sync.py`); the two `variant_emitter.py` files write with a bare `write_text` when
  called directly; a version string containing a slash is not checked for an intermediate
  link.
- The finalize repin step is tested through a resolver copied into the test.
