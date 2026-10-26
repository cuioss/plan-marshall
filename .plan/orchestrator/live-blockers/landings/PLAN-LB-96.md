# Landing Analysis: PLAN-LB-96 — A flat OpenCode install works end to end — it resolves its bundles root without a bundle marker, and extension discovery finds the domain bundles in it

epic: live-blockers
workstream: WS-04
pr: #1868 (`a1f981b94`, merge queue, base `main`, merged 2026-10-26T15:22:34Z)

> Landing record for one shipped plan. **(re-read)** = read again in git, the CI abstraction, the merged tree, `guard.log`,
> the script execution log or the lane's own build logs. **(store)** = read from the OpenCode session database, read-only
> (counts, tool names, command words, paths, times; no message text). Nothing was executed except the read-only checks named.
> Token usage is out of scope by the 2026-10-23 ruling. The fix was not re-executed against a real flat install: it rests on the
> PR's tests (which build a flat fixture and use the real emitters), green CI, the seven cited logs and the merged diff of the
> resolver, the layout helpers, discovery and both emitters read in full.

## Verdict

**Grade: B+.** Runbook lane, `deepseek-v4.1-flash/high` on all four sessions **(store)** (root plus three self-review sub-agent
sessions), 8 h 02 min wall clock (2026-10-26T07:44Z to 15:46Z; merged 7 h 38 min in).

Three of four deliverables are delivered as written, and the fourth is delivered in substance with one clause the lane reported
as not met and counted accordingly (`deliverables_done=3`) **(re-read)**: `resolve_bundles_root` gains a flat leg after both
nested probes, with the predicate single-sourced as `deployed_layout.is_flat_skill_root`; the six import-time modules import in
a marker-less flat fixture and an AST-derived guard compares the call-site population (6 import-time, 8 function-level) with the
declarations in both directions; the failure message names both shapes, the flat directory pattern and one doc home; and both
emitters now deploy `implements:` and the step fields under `metadata`, with `discover_all_extensions` and the implementor scan
enumerating a flat root through the recorded identity. Twenty files (+1444/-50), CI green, Sonar `0` on the PR, three of three
review threads resolved, main clean **(re-read)**. Every failing-run log the landing cites exists and shows what it says
(1 failed at the base; 64 passed; 1 failed on `undeclared=[…_cmd_extension.py]` then 1 passed; 10 failed / 2 passed with
`implements` reverted then 12 passed) **(re-read, logs)**.

Debits: read-class shell calls are understated (below); the first D1 test edit went to the main checkout (disclosed and
reverted); two concurrent in-process builds in one worktree (disclosed). Credits: it reported the unmet D2 clause instead of
dressing it, the guard count is exact (5 against 5, each line identified), the question and sub-agent counts are exact, no spoofed
identity, a CodeRabbit review of the second-to-last head exists, the re-trigger after the last push is recorded, and every
finding was handled, including an outside-diff Major one.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D1 `resolve_bundles_root` flat leg | shipped-as-specified | nested probes run over the whole chain first, then the flat leg returns the directory containing the skill root; `test_flat_tree_resolves_to_the_containing_directory[skills\|skill]` failed at the base (`…-075800.log`, 1 failed) and passes at `a88a7c42e` (`…-075932.log`, 64 passed) **(re-read, logs)** |
| D2 six import-time modules import; a guard covers every call site | shipped, one clause unmet | import half test-first (`…-080630.log`: 1 failed, 2 passed); guard mutation red on a dropped declaration (`…-082730.log`, `undeclared=[…/_cmd_extension.py]`) and green restored (`…-082805.log`). The `runbook_lane resolve` clause is NOT MET as written (below) |
| D3 the failure names both shapes and the fix | shipped-as-specified | message names nested and flat shapes, `plan-marshall-<skill>`, and points at one doc home (`tools-script-executor/SKILL.md` § "Deployed (flat) installs") |
| D4 extension discovery finds the domain bundles in a flat tree | shipped-as-specified | `implements_metadata_lines` / `step_metadata_lines` in both emitters, `discover_flat_extensions`, `_flat_bundle_optional_records`; `mutation-after` with the declaration reverted 10 failed / 2 passed (`…-083647.log`) and restored 12 passed (`…-083308.log`) **(re-read, logs)** |

Claimed `deliverables_done=3` of 4; agrees with the lane's own reading.

**The unmet D2 clause is the spec's error, not the lane's.** My spec said the `runbook_lane resolve` test "fails at
`cff686064`". The lane reverted the flat leg and the test stayed green, because that verb's own `resolve_bundles_root` calls are
function-level and exception-guarded and it reads build commands from the persisted architecture. The lane kept the test as a
smoke test, said so in its docstring, anchored the regression on the call-site test, and counted D2 as not fully met. That is
the right handling of a false spec parenthetical, and it is the second time a lane has caught one of mine (LB-95's numeric-order
label). The claim was in the unverifiable group at outline.

**Surface.** The PR edits three `extension-api/standards/*.md` files and creates `test/plan-marshall/_flat_install_fixtures.py`,
neither in the declared surface; both are disclosed with a reason (the contract changed; three test trees consume the fixture).
`tools-script-executor/SKILL.md`, `_manifest_validation.py` and the other declared files are touched as specified. One further
behaviour change worth stating: `read_implements_field` now splits an inline value on commas for the nested layout too.

## Findings by the orchestrator

- **Questions** **(store)**: two `question` calls (07:45Z, 11:12Z) = the landing's two (`executor-skew` `could_not_check`,
  then the third self-review round).
- **Sub-agents** **(store)**: three `subagent` calls (10:16Z, 10:37Z, 10:53Z), three child sessions, all completed = the landing's
  three rounds. No restart notice in the tree.
- **Guard** **(re-read)**: `guard.log` holds five lines for the four session ids, all in the root session: R1 at 07:45Z
  (`ls -la ~/.claude/plugins/cache/… | head`), R1 at 07:52Z (`grep -rln … | head`), R2 at 08:03Z (`bash -c 'echo test'`), R1 at
  12:30Z (`ls test/… | head`), R5 at 12:39Z (`python3 .plan/execute-python`) = the landing's five, identified one by one. Exact.
- **Shell read-class calls** **(store)**: `ls` 13, `tail` 7, `grep` 5, `wc` 1 = 26 read-class, plus `du` 3 and a `test` 3 times, in
  the root session; none in the children. The landing names the classes (`ls`/`du`/`wc`, `tail`) without a number and says
  "one further shell read used the allowed `grep -n` form", where the store shows five `grep` calls, one of them the guard-refused
  `grep -rln`, so four allowed ones against "one". An understatement of the same kind as LB-95's, no count disclosed to compare.
- **Identity** **(store)**: no `CLAUDE_CODE_SESSION_ID` or `OPENCODE` prefix on any executor call. No spoofed identity.
- **Main-checkout edits** **(store)**: one tracked-file edit outside the worktree `lb-96-flat-install-bundles-root`
  (`test/plan-marshall/script-shared/test_marketplace_bundles.py`, 07:56Z), which the landing discloses and says was reverted
  with the edit tool; 103 worktree edits, 10 under `.plan/temp`. Main is clean **(re-read)**.
- **Sonar** **(re-read)**: `0` open issues on the PR.
- **PR threads** **(re-read)**: three review threads, nine comments, all resolved. CodeRabbit's three inline findings: the
  skill-root predicate accepting a project-local `.claude/skills/` (fixed), a fixture deviation (answered and withdrawn), and a
  string-valued `metadata` / scan-root wiring (fixed in `4ee9a3a5c`). Its outside-diff Major finding (flat steps losing
  `order`/`default_on`/`presets`) was fixed in `570f81541` with the regression tests it asked for.
- **Reviewers** **(re-read)**: CodeRabbit (required) reviewed `7997f735d` and `695cfc6cb` (the walkthrough carries
  `coveredCommitId = 695cfc6cb`, `kind = reviewed`). The merged head `570f81541` changed logic after that review (the step-field
  carry) and drew a rate-limit refusal on both re-triggers, which the lane recorded after the last push. Under the standing
  authorization that is correct; a note, not a finding. Sourcery refused on its 7-day budget (optional).
- **Routed builds** **(re-read, landing §8)**: every routed build from the worktree failed inside the daemon (`pwx` from a cwd
  with no `pyproject.toml`) at the base and at each head; every build ran `--execution-mode in_process`. Fourth landing to report
  the worktree routing failure (LB-55, LB-53, LB-82, LB-96). The fallback works; the Watches condition is already met.
- **Local gate**: two whole-tree local runs hit the 300 s load timeouts in `test_harness_shape_guards.py`, green in isolation and
  in the later idle runs; the lane then ran `verify` green at four heads (32 259, 32 261, 32 291, 32 293 tests), the last at the
  merged head, and the merge-group run passed.

## What this changes for the second machine

The first break (`resolve_bundles_root`, the six import-time sites) and the second (discovery finds no bundle, `architecture
modules` empty) are both closed in source and covered by tests that use a flat fixture and the real emitters. Two things stand
between that and a working second machine: the new plugin version has to be installed there (the fix reaches an installed tree
only through a generated and synced deployment), and the lane's own residue says the file-to-build route derivation
(`get_build_extension_paths`, which joins bare build-skill names) is still flat-blind, so a flat install gets its build
commands from the discovered domain bundles and the persisted architecture but not from build-extension route derivation. Whether
`quality-gate` and `verify` resolve end to end on a real flat install is not shown by any test in this PR. The honest check is
one runbook lane on the second machine after the new version is installed. The hand-made shim on this machine becomes
unnecessary once the new tree is deployed here.

## Open Items

- The fix is source-only until `/sync-harnesses` here, and until the new plugin version is installed on the second machine.
- Residue the lane reported, none regressed: R1 built-in phase-5/phase-6 step docs are undiscoverable on a flat install
  (`resolve_skills_root(...) / 'phase-5-execute'` against the deployed `plan-marshall-phase-5-execute`); R2 Axis-B build
  extensions are flat-blind (`get_build_extension_paths`); R3 `scan_extensions --marketplace-path` expects a marketplace root;
  R4 `PM_MARKETPLACE_ROOT` has two incompatible meanings (`_doctor_shared` wants the parent of `bundles/`, `marketplace_paths`
  the directory containing `marketplace/bundles`). R1 and R2 are the ones that can still bite a flat install; recorded as one
  medium Open Defect, not staged (focus rule), pending the second-machine run.
- Routed-build worktree failure: fourth repeat; the operator has not asked for a plan.

## Reconciliation actions

- Row PLAN-LB-96: `shipped`, pr `1868`, landing `landings/PLAN-LB-96.md`, plan id `rb-lb-96-flat-install-bundles-root`.
- Inbox message `rb-lb-96-flat-install-bundles-root-001.md` archived.
- Epic: queue annotation, the CRITICAL Open Defect marked fixed in source, a new medium Open Defect for the flat-install
  residue, Decisions entry, model-comparison entry, Watches entry updated.
