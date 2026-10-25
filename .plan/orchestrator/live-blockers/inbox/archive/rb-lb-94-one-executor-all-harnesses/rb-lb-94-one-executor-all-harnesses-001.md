envelope_version=1
sender_type=plan
sender_id=rb-lb-94-one-executor-all-harnesses
epic=live-blockers
kind=landing
created=2026-10-25T18:31:19Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-94-one-executor-all-harnesses
epic=live-blockers
pr=#1861
merge_state=merged
cleanup_owed=false
deliverables_total=5
deliverables_done=4
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2007
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
step.sonar-roundtrip.open_issue_count=0
step.sonar-roundtrip.open_issue_rules=none
```

guard: present

# PLAN-LB-94 — one generated executor serves every harness

Merged as #1861 (`ee00687b802ccf212445feb4231687baf758cb55`). The executor is no
longer a per-harness artifact: bytes are a function of the checkout and the
installed harnesses, any harness's call resolves and dispatches, staleness is
judged per runtime harness, and an unchanged regeneration writes nothing.

## 1. Deliverables — per Done-when

| # | Done-when | Verdict | Test | Order | Failing run | Commit |
|---|---|---|---|---|---|---|
| D1 | 3 `--target` × ambient signals → byte-identical; fails at HEAD | met | `test_d1_the_three_targets_emit_byte_identical_executors` | `mutation-after` | `da1edacba` mutated, `python-2026-10-25-114758.log` (3 distinct files) | `da1edacba` |
| D1 | stamp informational; plugin root + recovery roots list every harness | met | `test_d1_the_stamp_is_informational`, `test_d1_the_plugin_root_and_recovery_roots_list_every_harness` | `mutation-after` | same log (stamp carried the target) | `da1edacba` |
| D1 | (prose) bytes not a function of `--target` in a consumer project | met | `test_d1_a_consumer_project_generates_one_canonical_install`, `test_d1_generation_uses_the_canonical_base_for_every_target` | `none` | — (added after review; forward guard) | `bd2e5bdd5` |
| D2 | dispatch under each of the other two harnesses, exit 0 | met | `test_d2_one_generated_executor_dispatches_under_every_harness` | `mutation-after` | same log (`executor_target_mismatch`, exit 2) | `da1edacba` |
| D2 | foreign-only install resolves + one-line note | met | `test_d2_a_foreign_install_resolves_with_one_note`, `test_d2_a_normal_path_stays_silent` | `mutation-after` | same log | `da1edacba`, restored in `00be9a82d` |
| D2 | unreadable executor still produces the recovery refusal | met | `test_executor_recovery.py` (unchanged contract) | `mutation-after` | same log | `da1edacba` |
| D2 | LB-43 D5 tests rewritten, not deleted | met | `test_executor_target_stamp.py`, `test_executor_target_resolution.py` | n/a | — | `da1edacba` |
| D3 | tree fixture: all notations incl. the four nested ones → tree under both envs | met | `test_d3_nested_and_flat_notations_resolve_to_the_tree`, `test_d3_the_four_real_nested_notations_rewrite_to_the_tree` | `mutation-after` | same log (`{script}.py`-only join left them on the install path) | `da1edacba`, `2cca092c8` |
| D3 | consumer fixture: each env resolves its own file, PYTHONPATH from that root | met | `test_d3_each_harness_resolves_its_own_install_and_its_own_pythonpath`, `test_d3_a_script_from_an_env_declared_root_gets_that_root_on_pythonpath`, `test_d3_pythonpath_on_a_tree_script_never_puts_a_foreign_install_first` | `mutation-after` | same log | `da1edacba`, `d171cfbcc` |
| D3 | a surface rejects nothing for a script it was not derived from | met | `test_d3_a_surface_is_only_applied_to_the_script_it_came_from` (with a rejection control arm) | `mutation-after` | same log | `da1edacba` |
| D4 | preflight and executor-skew report the running harness's own staleness | met | `test_d4_preflight_reports_the_running_harness_own_staleness`, `test_d4_executor_skew_judges_the_running_harness`, `test_d4_executor_skew_follows_the_ambient_signal`, `test_d4_the_executor_carries_a_version_per_harness` | `mutation-after` | same log (target-independent read) | `da1edacba`, `566a6c7a7`, `d171cfbcc` |
| D4 | an empty per-harness entry never borrows another harness's version | met | `test_d4_the_shared_reader_reports_no_version_as_empty`, `test_d4_the_roster_matches_the_target_registry` | `mutation-after` | same log | `2cca092c8`, `00be9a82d` |
| D5 | interleaved generations converge; killed generation keeps the previous file; no-change leaves mtime | met | `test_d5_interleaved_generations_converge_on_one_valid_file`, `test_d5_a_killed_generation_leaves_the_previous_executor_intact`, `test_d5_a_no_change_regeneration_leaves_the_file_untouched` | `mutation-after` | same log (mtime moved, bytes differed) | `da1edacba` |
| D5 | no shipped lane/steward/finalize text regenerates on a target mismatch | met | `test_d5_no_shipped_text_regenerates_on_a_target_mismatch` | `none` | — (the texts were already clean; forward guard) | `da1edacba` |
| D5 | generator tests leave the checkout's executor byte-identical | met | `test_d5_generation_leaves_the_checkout_executor_untouched` + the pre-existing autouse `_plan_base_dir_sandbox` | `none` | — (forward guard) | `da1edacba` |

**D5 is NOT FULLY MET AS WRITTEN**: its clause "Each fails at HEAD except the last"
is false for two of its five components (the killed-generation atomic write
predates this change, and the shipped texts already carried no target-mismatch
instruction). Those two are forward guards, reported with order `none`. Every
other D5 component was seen failing under the mutation. Hence
`deliverables_done=4`.

Per-head test runs on pushed heads: `da1edacba` executor suite green; `f636216aa`,
`057bdbe6d` full verify green (32209); `2cca092c8`, `d171cfbcc`, `bd2e5bdd5`,
`00be9a82d` executor+steward suites green, `bd2e5bdd5` and `00be9a82d` full verify
green (32224 / 32226). CI `verify` green on every pushed head.

## 2. Personas and skills

- D1–D4 production code: `persona-implementer`; their unit tests:
  `persona-module-tester`.
- D5 documentation text and the doc test: `persona-documenter`.
- Self-review rounds and PR-comment triage: `persona-code-reviewer`.
- The spec declares no `Skills:`/`Persona:` lines → `skills: none named`.
- `skills added:` none. Surface drift beyond the declared Expected Surface:
  `script-shared/scripts/plugin_registry.py` (the shared version reader D4 needs)
  and `marshall-steward/scripts/upgrade.py` (its second reader) — both named in the
  PR body rather than left implicit.

## 3. Hypotheses

- HYPOTHESIS (spec L133, antigravity resolver joins the same function): **confirmed**
  — one body serves all three; `test_every_target_renders_the_same_body`.
- HYPOTHESIS (L134, PYTHONPATH can follow the resolved root): **confirmed** — it is
  assembled at the dispatch boundary (`pythonpath_for`), so it follows the resolved
  script; `test_d3_*pythonpath*`.
- HYPOTHESIS (L135, status metadata keys can keep their names): **confirmed** — no
  consumer outside `_cmd_lifecycle.py`; the keys keep their names and mean
  "generated for" (`_cmd_lifecycle.py:1446-1477`).
- HYPOTHESIS (D5, the generator tests address the real checkout executor): **refuted
  as a live defect** — every test is redirected by the autouse
  `_plan_base_dir_sandbox`, and the new module asserts the checkout executor's bytes
  and mtime are untouched.

## 4. Findings

**Self-review round 1** (subagent, 14 findings; fixed in `566a6c7a7`): executor-skew's
verdict read the target-independent stamp (major); no per-harness skew test (major);
the nested-rewrite test was satisfied by the tree probe rather than the rewrite
(major); two D5 components already pass at HEAD (open → reported); a module-local
guard instead of suite-wide; four false template comments; three docs claiming the
stamp names a harness; dead `version_for_harness` / `_PYTHONPATH`; a legacy-reader
docstring; `plugin_registry.py` outside the Expected Surface (recorded as drift);
four lost resolver assertions; a near-vacuous PYTHONPATH assertion; the foreign
embedded leg outranking the cwd walk; two near-vacuous assertions.

**Self-review round 2** (12 findings; fixed in `2cca092c8`): flat-sourced nested
entries were not rewritten (major — the suffix keyed on `skills/{skill}/scripts/`,
absent in the flat shape); stamped roots were session-env-derived (major); a blank
per-harness version fell back to another harness's version (major); tree-only
generation lost the version; steward's upgrade read a target-independent version;
D4's evidence bypassed the env wiring; the checkout-executor guard's scope; more
stale comments; the foreign install outranking a cwd tree; a duplicated root
predicate; two test names.

**Self-review round 3** (11 findings; fixed in `d171cfbcc` except one, then closed in
`bd2e5bdd5` per the operator): env roots were invisible to the PYTHONPATH family and
lost to the stamped root; D3's four-notations evidence was narrower than written;
preflight was driven by `--target`; finalize wording; recover rationale; cwd-vs-own-
install precedence undocumented; SKILL leg numbering; a negative-only hidden-dir
test; missing progress entries. **Left open at the round limit:** consumer-project
bytes still depended on `--target` — the operator chose to close it, done in
`bd2e5bdd5` with a canonical-install base and three tests. The self-review state is
therefore `budget-exhausted` (round limit reached with items open), never `clear`.

**CodeRabbit** (`bd2e5bdd5`, 3 actionable + 1 nitpick): a target-scoped empty
version read as a broken executor → recovery loop (major — fixed in `00be9a82d` via
`fallback_on_empty`); `_env_harness_roots` missed `$XDG_CONFIG_HOME/opencode/skills`
(minor — fixed); a test-function header was swallowed so the foreign-install case ran
inside the D1 test (minor — fixed); `_HARNESS_ROSTER` is a hardcoded copy of the
harness set (nitpick — answered with a roster-vs-target-registry drift test rather
than deriving the roster at runtime, because the emitted bytes must not move when an
upgraded `target_context` reorders its signals). All three threads resolved.

**Sourcery** (optional): refused — the diff exceeds its 150 000-character review
limit.

## 5. Reviewers

| Reviewer | Reviewed | Head reviewed | Trigger / wait history |
|---|---|---|---|
| coderabbit (required, quota_limited) | reviewed — "Merge Risk: Moderate", coverage marker `kind=reviewed` | `bd2e5bdd5` (current head is `00be9a82d`) | triggered at PR creation; re-triggered at 17:15:52Z after the last push and **rate-limited** ("Review rate limited"); its own notice named a ~19-minute reset. Standing review authorization applied: qualifying review exists, every finding handled, one re-trigger recorded, all other gates green on the current head. |
| sourcery (optional, quota_limited) | refused | — | refused on size ("larger than the review limit of 150,000 diff characters") at creation and on the re-trigger; optional, so it does not gate. |

## 6. Operator questions

1. "The runbook lane cannot start — two independent blockers" (missing spec; executor
   stamped for the wrong harness) — options: stop and report blocked / regenerate then
   stop / point at another spec. Selected: **"plan did land by now, regenerate and
   recheck"** (free text, i.e. a custom answer).
2. "The mandated pre-resolve skew check cannot decide" (`could_not_check`, empty
   version) — options: proceed and record / regenerate for a version stamp / stop.
   Selected: **regenerate to get a version stamp first**.
3. "The regeneration worked, but the recheck still cannot decide" (flat install has no
   version directory) — options: proceed and record / stop / point `--lane-dir` at the
   versioned install. Selected: **proceed and record `could_not_check`**.
4. "The run is at the 3-round self-review limit" (one open item: consumer-project byte
   equality) — options: proceed to PR with it open / close it first / stop. Selected:
   **close the consumer-project gap first**.

Free-text operator messages: none beyond answer 1's custom text.
No surface/naming error prompted a question; the question tool was available
throughout.

## 7. Rule check

guard: present. The guard log is `.plan/temp/guard.log`; the runs below are the
run's own account, not a count taken from that log alone.

- **Rule 1 — Executor only.** Two deviations, both forced and disclosed:
  1. Before any executor call could succeed, the executor was **stamped `claude`**
     while OpenCode was running, so every call — including `generate_executor` —
     returned `executor_target_mismatch`. Recovery therefore ran the generator by
     direct path twice (`generate_executor.py generate --marketplace …` from the repo
     source, then `preflight`), which is the script's own printed remedy. The first
     attempt through the printed `recover` command failed with
     `ModuleNotFoundError: argparse_surface` (the flat OpenCode install's generator
     cannot find its sibling libs).
  2. The `runbook-lane` skill's own commands, all builds and every CI action went
     through the executor (`verify`, `quality-gate`, `module-tests`, `ci pr …`,
     `sonar read_open_issues`, `runbook_lane …`). No `gh`/`glab`, no test/lint
     binary, no `sleep`.
  One guard refusal, recorded: `python3 .plan/execute-tool.py` was refused by R5
  (direct interpreter path) — that call was a typo and was not retried.
- **Shell.** One command per call throughout; no chaining, pipes, loops or heredocs.
  Several `git` commands were used (`status`, `log`, `show`, `fetch`, `push`,
  `diff`, `add`, `commit`, `worktree remove`, `rev-list`) — none is a shell file
  operation or a CI action. Files were read with the file tools. One `grep` and one
  `tail` shell call were issued (log inspection) — both are shell file reads and are
  reported here as deviations.
- **`.plan/` state.** Only `.plan/temp/` (progress file) and the two `ci` body slots
  under `.plan/local/plans/NO_PLAN/work/ci-bodies/` were written before the landing.
- **Git.** Nothing was staged with `git add -A`; no `stash`, `restore`,
  `checkout -- <path>`, `rebase` or force-push. The single commit covering D1–D5 was
  a deliberate deviation from the one-commit-per-deliverable convention because the
  edits interleave in the same files; its subject names `(D1-D5)` so git still shows
  which deliverables are committed.
- **Build server.** Setup preflight `ready`. The first routed build (`auto` →
  `daemon_longpoll`) failed with exit 1, no structured errors and an **empty job
  log**; every later build ran `--execution-mode in_process` (`in_process_fallback`),
  recorded as a degraded routed build with that reason. No `killed` job.
- **Restarts / re-dispatches.** Three self-review sub-agents (rounds 1–3); no session
  restart, no killed sub-agent.
- **Runtime stamp.** `harness=opencode`, `model=deepseek-v4.1-flash/high`,
  `effort=high`, `plugin_version=0.1`, `executor_version=0.1.2007` — read from a
  `resolve` re-run at landing time. No model or effort switch during the run.

## 8. Build server

Preflight at setup: `ready` (registered). Every build after the first ran
`in_process` with reason `in_process_fallback` (the routed attempt produced an empty
daemon job log). Final gate on the merge head `00be9a82d`: `verify` green, 32 226
tests, mypy + ruff + plugin-doctor. CI's own `verify` was green on the same head.

## 9. Residue

- **D5 graded not fully met as written** (§1): two of its five components are forward
  guards that already passed at HEAD. The behaviour they guard is intact; the
  evidence claim in the spec is what fails.
- **D1's consumer-project half is now closed** (`bd2e5bdd5`) with a canonical-install
  discovery base, but it carries order `none` (a forward guard, no failing-at-HEAD
  output) — it was found by review, not by the spec.
- **`plugin_registry.py` and `upgrade.py` are surface drift** beyond the spec's
  Expected Surface; both are named in the PR body.
- **cwd-reachable tree vs a live embedded own-install path**: the runtime harness's
  own install still wins over a tree reachable only from `cwd`; this precedence is now
  documented in the docstring and the SKILL rather than changed.
- **`executor_target` metadata is the constant `'any'`** by design (a constant is what
  keeps the bytes harness-independent); the metadata field therefore no longer
  distinguishes harnesses. Its name and value semantics are documented.
- **The operator step the spec names after the merge** — regenerate the main
  checkout's executor once from the merged template, then `/sync-harnesses` — was
  executed for the executor during this run (the `preflight` recovery) and remains
  owed for the harness sync.
