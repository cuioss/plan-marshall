# Landing Analysis: PLAN-LB-95 — The executor puts only the resolved script's own plugin version on PYTHONPATH

epic: live-blockers
workstream: WS-04
pr: #1865 (`972683f0f`, merge queue, base `main`, merged 2026-10-26T07:02:16Z)

> Landing record for one shipped plan. **(re-read)** = read again in git, the CI abstraction, the merged tree, `guard.log`,
> the script execution log or the lane's own build logs. **(store)** = read from the OpenCode session database, read-only
> (counts, tool names, command words, paths, times; no message text). Nothing was executed except the read-only checks named.
> Token usage is out of scope by the 2026-10-23 ruling. The fix was not re-executed here: it rests on the PR's tests, green CI
> and the merged diff read in full.

## Verdict

**Grade: B+.** Runbook lane, `deepseek-v4.1-flash/high` on all five sessions **(store)** (root plus four self-review
sub-agent sessions), 11 h 14 min wall clock (2026-10-25T20:20Z to 2026-10-26T07:34Z; merged 10 h 42 min in).

All four deliverables are delivered in the merged tree and the code does what the spec asked **(re-read, diff read in full)**:
`_same_root_script_dirs` no longer globs the install root; `_version_dir_of` reads `(version, bundle)` off the segment before
`skills/`, `_version_script_dirs` enumerates the sibling bundles of that one version and falls back to a bundle's newest version
through the existing `_version_key`, and the flat shape and tree paths keep their handling. Four files (+446/-25), CI green,
the one review thread resolved (withdrawn by the reviewer), Sonar `0` on the PR, main clean **(re-read)**. The evidence is
test-first for every deliverable but one, and the failing run is quoted in the PR body from a log that exists and shows what it
says **(re-read)**.

Debits: the landing contradicts its own failing log on one point (below); seven read-class shell calls are understated; the
fix changed a sentence in a file outside the declared surface (explained). Credits: the guard count is exact (1 against 1), the
question count is exact (3), no spoofed identity, no main-checkout edit, the required reviewer reviewed the final head so no
standing authorization was needed, and the run reported its own rule deviations.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D1 the walk returns only the script's own version | shipped-as-specified | `_version_dir_of` + `_version_script_dirs`; flat and tree paths unchanged; cache keyed by root, version and bundle. `test_d1_a_cached_script_imports_its_own_versions_helper` failed at `cff686064` with the reported `ImportError` **(re-read, log)** |
| D2 a bundle without that version uses its newest, numeric | shipped-as-specified | `_newest_version_dir` orders by `_version_key`; `test_d2_a_sibling_bundle_without_the_script_version_uses_its_newest` failed at `cff686064` |
| D3 other shapes keep working; one version per skill | shipped-as-specified | 36 existing tests unmodified and green; the no-skill-twice guard and the `{root}/{version}` shape failed at `cff686064`; a hidden-version case added by review (`mutation-after`) |
| D4 reproduction with eight cached versions | shipped-as-specified | `test_d4_eight_cached_versions_still_import_the_newest_helper` failed at `cff686064`, output quoted in the PR body |

Claimed `deliverables_done=4` of 4; agrees.

**The contradiction.** The landing (§1) and the PR body label `test_d2_the_fallback_orders_versions_by_numeric_tuple` a
"forward guard, passes unfixed by string-order accident", order `none`. The run's own failing log
(`python-2026-10-25-203558.log`, 6 failed) lists that test as FAILED at `cff686064` at the line `assert '0.1.999' not in
pythonpath`: at the unfixed tree both `0.1.1000` and `0.1.999` are on the path. The label came from my spec, which said the
case passes at HEAD; the lane's test asserts more than the spec sentence (it asserts the absence of `0.1.999`), so it is
regression evidence and the landing under-claims. The spec sentence was wrong (mine); the lane carried the label forward
without checking it against its own log. No harm to the shipped code.

**Surface.** The spec declared five entries; the PR touches four files **(re-read)**: the template, `SKILL.md`, the new test
module, and `plugin-script-architecture/standards/cross-skill-integration.md`, which the spec did not name. That standard
described the old "all script directories" behaviour and the landing lists it under skills added. Explained, not a violation.
`harness_independent_resolver.py.template` was not edited (the spec's hypothesis that `_version_key` is available at the call
site was confirmed instead).

## Findings by the orchestrator

- **Questions** **(store)**: three `question` calls (20:20Z, 20:24Z, 00:02Z) = the landing's three. Two of them are the
  `executor-skew` `could_not_check` verdict, which a flat OpenCode install cannot make (no `{bundle}/{version}` directory to
  derive the lane version from); the operator answered "Regenerate the executor first", then "Proceed now". The third
  (00:02Z) is the fourth self-review round past the limit. The landing's Residue states the first two cannot be resolved by
  regeneration.
- **Sub-agents** **(store)**: four `subagent` calls (22:43Z, 23:05Z, 23:29Z, 06:23Z), four child sessions, all completed =
  the landing's rounds 1 to 4. No restart notice in the tree. The rounds found 16, 3, 6 and 0 items.
- **Guard** **(re-read)**: `guard.log` holds one line for the five session ids: R1 at 22:45:23Z in the first review child
  (`git … ls-files .claude | head -30`), refused (`error`) = the landing's one. Exact.
- **Shell read-class calls** **(store)**: 29 in the root session (grep 11, ls 9, diff 4, tail 4, sed 1) and 3 in the
  children (grep, find, wc) = 32; the landing says "about two dozen". The five root calls with a pipe or separator character
  in them are regex alternations inside quoted `grep` arguments and a multi-`-m` commit message, not shell constructs. A seven
  call understatement, similar in kind to LB-94's, smaller in size.
- **Identity** **(store)**: one `generate_executor` call from the root session at 20:24:12Z (`prefix=` empty); no
  `CLAUDE_CODE_SESSION_ID` or `OPENCODE` prefix anywhere. No spoofed identity.
- **Main-checkout edits** **(store)**: 0 tracked-file edits outside the worktree `lb-95-executor-pythonpath-own-version`
  (35 worktree edits, 15 under `.plan/temp`). Main is clean **(re-read)**.
- **Executor** **(re-read)**: the operator's "Regenerate the executor first" answer rewrote the MAIN executor at
  20:24:35Z (`plan-marshall:…generate_executor generate`, 22.88 s, after a verb sweep of nine generator verbs at 20:24:27Z
  under the fixture notation `default-bundle:…`). It still carries `GENERATED_FOR = 'any'` (LB-94), so nothing flipped. But the
  regeneration used the template as it was before this fix: `.plan/execute-script.py` has no `_version_dir_of`, and neither has
  the Claude cache `0.1.2010`. The fix is in source only.
- **PR threads** **(re-read)**: 1 of 1 thread resolved. CodeRabbit flagged that a digit-bearing unversioned bundle would be read
  as a version in the single-segment form; the lane answered with the resolver's own model and the three declared roots, the
  reviewer withdrew it. The accepted residual (a hand-authored `SCRIPTS` mapping into `{root}/{bundle}/skills/…`) is stated in
  the thread.
- **Reviewers** **(re-read)**: CodeRabbit (required) reviewed `d2c5b6f08`, the merged head: `sourceCommitId =
  coveredCommitId`, merge risk Low. Sourcery (optional) refused on quota. No unreviewed head.
- **Sonar** **(re-read)**: `0` open issues on the PR.
- **Local gate**: the whole-tree `verify` could not complete locally (two 300 s load timeouts under 16-way xdist, then a
  bound at 1411 s and at 2400 s); the split form was recorded and CI's `verify` is the authority. Both timeouts are the
  pre-existing `test_harness_shape_guards` AST predicates; not a defect of this plan.

## Open Items

- The fix is not live anywhere yet. It needs `/sync-harnesses` here (Claude cache, OpenCode, Antigravity), then a regeneration
  of each project's executor, because an executor is generated per checkout and bakes the template at generation time. On the
  operator's second machine it needs the new plugin version installed and the executor regenerated there.
- `executor-skew` answers `could_not_check` on every flat OpenCode install, so each OpenCode lane asks the operator two
  questions that cannot change the outcome (medium, not staged; the operator's focus rule is high and blocking only).
- The `forward guard` label for the numeric-ordering test is wrong in the landing and the PR body; the test is regression
  evidence. Recorded here; no action.

## Reconciliation actions

- Row PLAN-LB-95: `shipped`, pr `1865`, landing `landings/PLAN-LB-95.md`, plan id `rb-lb-95-executor-pythonpath-own-version`.
- Inbox message `rb-lb-95-executor-pythonpath-own-version-001.md` archived.
- Epic: queue annotation, Open Defect marked fixed in source, Decisions entry, model-comparison entry.
