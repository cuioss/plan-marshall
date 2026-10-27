# Landing Analysis: PLAN-LB-97 — A flat install finds its sibling skills

epic: live-blockers
workstream: WS-04
pr: #1872 (`2001a8a13`, merge queue, base `main`, merged 2026-10-27T10:48:21Z)

> Landing record for one shipped plan. **(re-read)** = read again in git, the CI abstraction, the merged tree, `guard.log`,
> the script execution log or the lane's own build logs. **(store)** = read from the OpenCode session database, read-only
> (counts, tool names, command words, paths, times; no message text). Nothing was executed except the read-only checks named.
> Token usage is out of scope by the 2026-10-23 ruling. The fix was not re-run on a real flat install: it rests on the PR's
> tests, green CI, the lane's cited job logs and the merged diff of the helper and the layout module read in full.

## Verdict

**Grade: B.** Runbook lane, `deepseek-v4.1-flash/high` on all four sessions **(store)** (root plus three self-review
sub-agent sessions), 15 h 41 min wall clock (2026-10-26T19:37Z to 2026-10-27T11:18Z; merged 15 h 11 min in).

All four deliverables are delivered and the code does what the spec asked **(re-read)**: one helper family in
`marketplace_bundles` (`resolve_sibling_skill_path`, the fail-loud `require_sibling_skill_path`, `SkillPathNotFound` naming both
shapes, `describe_sibling_skill_shapes`) built on `deployed_layout.flat_skill_paths`, with the flat name constructed through
`flat_skill_dir_name` and never spelled twice; every join in the spec's list routed through it (`configurable_contract`,
`_manifest_validation`, `extension_discovery`, `determine_mode`, plus the seven `parent.parent` sibling joins of D3); an AST
guard that finds undeclared bare joins and fails when a declaration is dropped or a scratch join is added; and the upgrade
reconcile verbs driven on the flat fixture and compared with the source checkout. Twenty files (+1675/-95), CI green at every
head, six of six review threads resolved, main clean **(re-read)**. The lane's cited failing job logs all exist, and the two I
read show exactly what the landing says: `compose` answering `unresolvable_step` on the flat fixture where nested returned
`success`, and the generator failing with `ModuleNotFoundError: argparse_surface` when started without an inherited
`PYTHONPATH` **(re-read, job logs)**.

Debits: the run broke the shared main executor for a concurrent lane; it edited and created files in the main checkout; a
restart is not reported; the Sonar gate never became decidable and the PR merged with that gap on the operator's instruction;
shell read-class calls are partly undisclosed. Credits: the guard count is exact (3 against 3), the question (5) and
sub-agent (3) counts are exact, no spoofed identity, the lane found and fixed six real defects CodeRabbit raised (one of which
disproved the lane's own declaration that the generator bootstrap was flat-safe), the evidence is honestly labelled
`mutation-after`, and the residue is complete and specific.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D1 step docs, build extensions and the generator resolve through one flat-aware helper | shipped-as-specified | `resolve_sibling_skill_path` / `require_sibling_skill_path`; four named step ids resolve on the flat fixture; the four build skills' `extension.py` resolve; the generator path exists. `mutation-after` with the flat leg removed: job log `c8201bd1…` (2 failure lines), `ce6e1785…` (7) **(re-read, job logs)** |
| D2 a guard keeps every sibling-skill join honest | shipped-as-specified | AST scan of `marketplace/bundles/**/scripts`; red on the pre-fix tree with 17 undeclared joins (`python-2026-10-26-203652.log`: 2 failed, 4 passed, a pre-commit draft, disclosed); dropping a declaration and adding a scratch join each turn it red (`0aac4317…`, `a91887ab…`) |
| D3 the remaining sibling joins are classified and the broken ones fixed | shipped-as-specified | all seven `parent.parent` sites read and found broken (silent degradation, not crashes); `_ci_log_filter`, `ci_base`, `_build_queue_slot`, `_build_execute_factory`, `integrate_into_main`, `git-workflow`, `prepare_execute` routed. The generator's own `sys.path` bootstrap was declared flat-safe, proved not to be by CodeRabbit, and fixed (derives the flat prefix from its own directory name, probes both shapes, empty-`PYTHONPATH` test) |
| D4 the upgrade reconcile runs on a flat install | shipped-as-specified | `sync-defaults --backfill-bot-roster`, `step get`, `compose`, `validate-loadable --all` and `_manifest_validation`'s import-time resolution all driven on the flat fixture and compared with source; red logs `b48c6132…` (`step body doc not found: …/skills/automatic-review/SKILL.md`, the operator's exact message) and `bcbf3518…` |

Claimed `deliverables_done=4` of 4; agrees.

**Order labels.** The spec said each clause "fails at `a1f981b94`". The lane could not run its tests against that tree (an
in-process build always runs in the main checkout and its venv bootstrap diverged), so it labelled the evidence
`mutation-after` and said so, instead of claiming a base run it never made. That is the honest handling of the situation my
"fails at a SHA" wording keeps creating (fourth time in this epic).

**Surface.** Every touched file is in the declared surface, plus `generate_executor.py` (reached by D3's own generator clause)
and `test_extension_discovery_behavior.py` (a seam retarget the helper forced); both disclosed.

## Findings by the orchestrator

- **Questions** **(store)**: five `question` calls (19:39Z, 19:56Z, 20:32Z, 23:14Z, 10:28Z) = the landing's five: executor-skew;
  the four test files created in the main checkout; the guard blocking the deletion; two files to restore; the Sonar gap.
- **Sub-agents** **(store)**: three `subagent` calls (22:16Z, 22:46Z, 05:52Z), three child sessions, all completed = the
  landing's three self-review rounds.
- **Guard** **(re-read)**: `guard.log` holds three lines for the four session ids, all in the root session: R1 `grep -rn … | head
  -5` (19:38Z), R2 `rm -f` of the four test files (19:55Z), R2 `rm -f` of one of them (20:32Z) = the landing's three. Exact.
- **Shell read-class calls** **(store)**: `ls` 5, `grep` 1 (the refused one), `rm` 2 (refused), `date` 1. The landing names the
  refused `grep` and the two `rm` calls; the five `ls` calls are undisclosed.
- **Identity** **(store)**: no `CLAUDE_CODE_SESSION_ID` or `OPENCODE` prefix on any executor call. No spoofed identity.
- **Restart** **(store)**: one restart notice in the root session at 09:16Z (the same minute two other OpenCode lanes started
  or restarted, so it looks like a harness-wide event). The landing reports none.
- **Main-checkout edits** **(store)**: 18 tracked-file operations in the MAIN checkout between 19:49Z and 19:55Z: seven edits
  to the tracked `test/plan-marshall/_flat_install_fixtures.py`, four new test files (each written, then edited) and a final
  write of the fixtures file. The landing discloses the four new test files and a restore of "two files" before the merge; it
  does not name the edits to the tracked fixtures file separately. Both checkouts were clean afterwards (main clean **(re-read)**).
- **Executor interference (landing §Rule check, execution log, session store)**: the lane regenerated the MAIN checkout's
  `.plan/execute-script.py` against a scratch worktree at `a1f981b94` (session store: a `generate_executor generate` call at
  21:47:03Z on 10-26) and later again with `generate --marketplace-root .`. The PLAN-LB-58 lane hit "the main checkout's
  executor is broken by another session" at 21:47Z and the operator regenerated it at 21:47:28Z, 25 seconds later. That settles
  the cause I had recorded as unexplained: it was this lane's scratch-worktree regeneration. It cost the LB-58 lane an operator
  question. The guard does not cover it because the executor is untracked.
- **Current main executor** **(re-read)**: `MARSHALL_VERSION = '0.1.2019'`, `GENERATED_FOR = 'any'`, 169 mappings, and scripts
  map to the source tree under `marketplace/bundles/` (one entry per notation) rather than to the installed copies. It works.
  That differs from the dual flat and nested entries my own regeneration of 2026-10-27 produced; whoever regenerated last (this
  lane, per its report) set the source-tree mapping.
- **Sonar** **(re-read)**: the gate never became decidable. The landing reports eight reads across five heads answering
  `undecidable` / `analysis_revision_unavailable`, with `head_revision` resolving to `origin/main` (meaning the PR entry carried
  no branch, so the provider listed no analysis for the pull request). The operator selected "Merge anyway, gap accepted".
  The open new-code count on the merged head is unknown, not zero. My own read after the merge is `undecidable` by the same
  rule, which tells nothing about the live state. See Open Items.
- **PR threads** **(re-read)**: six review threads, eighteen comments, all resolved. CodeRabbit's findings: `_load_parse_log`
  lost its generic fallback; `_load_persist` broke its "returns None" degradation; `deployed_skill_md` appended a duplicate
  `metadata:`; `ROUTED_MODULES` was hand-kept (now derived); the generator bootstrap was not flat-safe; and it let a flat lib
  shadow the nested one. All six fixed with tests.
- **Reviewers** **(re-read)**: CodeRabbit (required) reviewed `89043af24`, `61bc78abc` and `dc57837d4` (the walkthrough carries
  `coveredCommitId = dc57837d4`, `kind = reviewed`). The merged head `0407ab40d` fixed the sixth finding and drew a rate-limit
  refusal on the re-trigger at 10:28Z; the standing authorization applies, a note only. Sourcery approved `dc57837d4` and the
  approval was dismissed by the next push.
- **Local gate**: two whole-tree local runs failed only the two `test_harness_shape_guards.py` predicates on their 300 s timeout
  under load, green in isolation (37/37) and green on CI at every head. Routed builds ran through the daemon throughout (72
  invocations, no degradation) once `--project-dir` was passed absolute; a relative path fell back to a system `pwx` that is not
  installed. This lane therefore did not hit the worktree routing failure the five earlier lanes reported, and shows what
  triggers it: a relative `--project-dir`.

## Open Items

- **Sonar never decidable on this PR.** The first live use of LB-58's gate on a PR where the provider listed no analysis. Either
  Sonar did not analyze PR 1872 or the list omitted it. The merged PR can no longer be queried. If the next code PR (LB-93)
  also ends `undecidable`, the gate blocks every merge until the operator overrides, and that is a high item; recorded as a
  Watch, not staged.
- Residue 1: "naming both shapes" holds only where the lookup is fail-loud; `_manifest_validation`, `extension_discovery` and
  `prepare_execute` still print only the nested path on a genuine miss.
- Residue 2: the D4 roster assertion is not evidence of the doc read (the roster comes from `_config_defaults` constants); the
  doc read is proven by `sync-defaults` succeeding and `step-get`'s params matching.
- Residue 4: the guard cannot see a `for` over a parameter, an f-string-composed name or `os.path.join`.
- A lane can rewrite the main checkout's executor from a scratch worktree; nothing stops it (see above).
- The fix is source-only here until the next `/sync-harnesses`, executor regeneration and repin; on the second machine until
  the new plugin version is installed.
- PLAN-LB-93 D1 and D2 overlap what LB-97 D3 fixed (the generator bootstrap and sibling entry scripts on a flat install);
  re-ground LB-93 before emitting it.

## Reconciliation actions

- Row PLAN-LB-97: `shipped`, pr `1872`, landing `landings/PLAN-LB-97.md`, plan id `rb-lb-97-flat-install-skill-resolution`.
- Inbox message `rb-lb-97-flat-install-skill-resolution-001.md` archived.
- Epic: queue annotation, the high Open Defect marked fixed in source, the medium flat-install entry narrowed to R3 and R4,
  Decisions entry, model-comparison entry, Watches entries.
