# Landing Analysis: PLAN-LB-121 — a Maven reactor root runs only the tests it builds, and a selector miss keeps every real failure

epic: live-blockers
workstream: WS-02
pr: #1929

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-121.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Merge commit `74ddc39a8918a846cd32b57ffeb6dd36d1490e16`, a squash commit with ONE parent, `47d4a5b70a03a725175831465505501175d1a8ad` (the ledger land of PR 1928, read with git and named in the leaf prompt); it equals the checkout HEAD. Landing message `rb-lb-121-maven-consumer-gate-truth-fixes-001.md` (runbook lane; harness opencode, model `deepseek-v4.1-flash/high`). `landing-check` reports `complete: false`, missing `total_tokens` only (the known gap; out of scope); its surface delta is `unmeasured`, so the surface was read from the diff: 17 files, +1601/−114 (`git show --stat 74ddc39a8`). The lane reports 3 of 3 deliverables, `self-review: budget-exhausted` after four rounds (the operator chose a fourth), a spec read from the ledger copy. No verb or flag was added (`git diff 47d4a5b70 74ddc39a8 -G'add_parser|add_argument' --stat` is empty, leaf), so no executor regeneration is owed. A harness sync is.

Surface against the spec's Expected Surface: inside it, except `test_maven_pom_parse.py` (the mechanical consequence of the new `modules` key) and, as spec HYPOTHESIS entries, `maven-impl.md` (touched) and `_maven_cmd_resolve_scope.py` (not touched). Five new log fixtures and a README sit under the declared `fixtures/log-test-data/`. No shared build file was edited: the shared build tree is byte-identical between `f84eb0e36` and `74ddc39a8` (leaf).

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the reactor root's test canonicals follow what the root builds | shipped; one fail-closed clause not met (L1-9) | The root's reactor is its `<modules>` plus the `activeByDefault` profile modules, followed through nested aggregators (`_maven_cmd_discover.py:317-370,690-742`); the stray-POM fixture gives the root neither key; the control fixture was rewritten with a stated reason and still asserts both keys (L1-2). The zero-test guard is `apply_zero_test_guard` (`_maven_execute.py:382-445`, re-read). |
| D2 — a selector miss keeps every real failure | shipped | The relabel backs off on any real failure; `-fae` module a keeps its error and rows; the pattern is named from the log; a reactor miss beside an executed module says what the run did; an unreadable log on an exit-0 `-Dtest` run is `indeterminate` (`_maven_execute.py:45-66,270-330`; leaf). A Failsafe exit-0 miss under `verify` is not caught and not in the recorded limit (L1-6). |
| D3 — guide texts and tests | shipped | The grammar sentence and its guard, `pre-push-quality-gate.md:419,479,491,495,500`, the gate test calling `resolve-test-scope` (leaf). `pytest` remains at 574, 607 and 622-623, outside the named branches, as the lane says. |
| executor regeneration | not owed | The argparse diff is empty. |

## Three-Layer Analysis

One read-only leaf (`execution-context-level-5`, resolved on `orchestrator.analyze`) read the landing at the merge commit. It reported its tool deviations (a skill load, no logging writes, `git show <rev>:<dir>/` in place of denied Grep and Glob) and no write. The orchestrator re-read the points marked `re-read`. It was a reading only: no build, no test run, no write.

- **Dispatch:** one read-only leaf — the read crosses 17 files, with 12 narrative claims passed one by one.
- **Verdict:** layer 1 findings (minor, info); layer 2 findings (minor, info); layer 3 findings (**two major**, minor, info). No blocker.
- **Orchestrator re-read:** L3-1 (the guard body and the gate branch text that reads `indeterminate`), L1-9 (the unreadable-POM default). Every other row is a lead the leaf checked and I did not re-read.
- **Prompt check.** The 12 claims went into the prompt as separate items.
- **Not read by the leaf:** `_build_shared.cmd_run_common`, `_build_examined.py`, the ledger row writer, the primary predicate in `_cmd_pre_commit_verify_freshness.py`, the CI workflow and its uv flags, the daemon child's launch path and code version, the new fixture bodies.

### Layer 1 — Specified

| Finding | Claim | Verdict | Evidence (file:line at 74ddc39a8) |
|---------|-------|---------|-----------------------------------|
| L1-9 (minor, re-read) | Standing constraint: an unreadable POM is a named stop | **not met.** An unreadable or malformed POM parses as packaging `jar` with `modules: []`; the root loses its canonicals, the gate records DEGRADED and passes, and nothing names the stop. | `_maven_cmd_discover.py:636-648` |
| L1-2 (minor, leaf) | Standing constraint: a rewritten control is disclosed as a correction | the control fixture `_AGGREGATOR_POM` became `_AGGREGATOR_LISTING_CORE_POM`; the docstring gives the reason but does not label it a correction | `test_discover_modules.py` about 746-758, 1011-1044 |
| L1-3 (minor, leaf) | D1: a zero-test run is not `success` | met for code that contains this merge; a routed build gets it only if the daemon child runs post-merge code, and a daemon reconcile is not listed as owed (L3-3) | `_maven_execute.py:382-445,448-482` |
| L1-5 (info, leaf) | D2: back off on any real failure | met with deviation: a line of category `other` counts only at `[ERROR]` level; a test pins that every parser category is classified | `_maven_execute.py:45-66,296-306` |
| L1-6 (minor, leaf) | D2: an exit-0 config-set miss | met on the failure path; the exit-0 miss is caught only for a leading `test` or `package` goal, so a Failsafe `-Dit.test` miss under `verify` is undetected | `_maven_execute.py:308-313`; `SKILL.md:86` |
| L1-10 (minor, leaf) | Test-order labels; current-state wording | tests are labelled `mutation-after` where the spec asked `test-first`; the fixtures README row says "the shape that reported a green test run while executing nothing", which describes the old behaviour | fixtures `README.md` |
| L1-1, L1-4, L1-7, L1-8, L1-11 (info, leaf) | the other Done-whens and the shared-file constraint | met / kept | see the fidelity table |

**Layer 1 verdict:** findings — one clause not met, four minor, the rest met.

### Layer 2 — Implemented

- **Confirmed (leaf):** C1, C2 (the rewritten control still asserts both keys), C4 (`_parse_pom_xml` had no `modules` key; `test_maven_pom_parse.py` follows and adds one test), C6 (one test name differs: `test_exit_zero_config_selector_miss_is_detected_without_a_command_selector`), C8, C9, C10.
- **C3 partly contradicted:** the lane says the guard reaches in-process builds only. The wrapper docstring says both checks run inside the daemon child (`_maven_execute.py:448-456`); the routing client does not re-apply them (`_build_execute_factory.py:752-774`). Whether a given daemon runs post-merge code was not read (L3-3).
- **C5:** the gate side holds (the gate branches on `status: success`, `pre-push-quality-gate.md:493,516`, and the freshness check reads zero tests only after the canonical, `_freshness_crosscheck.py:746-757`); the `cmd_run_common` half was not read.
- **C7:** the limit text exists (`SKILL.md:86`); the Surefire 3.5.2 source claim is unverifiable.
- **C11 corroborated:** `uv.lock:381,530` pins types-pyyaml 20260906 while `pyproject.toml` requires `>=6.0.12.20261103`; the cause is the dependency merge `ddb893c96`, which changed `pyproject.toml` only. Effect: `uv run` without `--locked` re-locks and dirties `uv.lock` in a worktree; `uv sync --locked` would fail. Whether CI uses `--locked` was not read.
- **C12:** the process claims (four self-review rounds, 31 findings, CodeRabbit and Sourcery history, eleven routed builds, the two operator questions, two guard refusals, one `git restore` of `uv.lock` after an operator selection) are unverifiable and are the lane's account.

**Layer 2 verdict:** findings — one claim partly contradicted (C3), one unverifiable half (C5), the rest confirmed.

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 (re-read; reach leaf) | `_maven_execute.py:430-445` (re-read); `_maven_cmd_discover.py:488,1151-1153`; `pre-push-quality-gate.md:493,516` (re-read) | A module whose `src/test/java` holds only helpers (a test-jar fixture producer) counts as having test files and gets `module-tests = test -pl X -am`; or `.mvn/maven.config` carries `-q` or `--quiet` (the summary is INFO level), or Surefire has `printSummary=false` | The log has no test summary on a leading `test` goal and no skip marker, so the run becomes `indeterminate` (`TEST_RUN_EXECUTED_NOTHING`). The gate text for branches 4 and 6 says `indeterminate` means STOP the step, so a legitimate green is a stop that a re-run does not clear, and the per-task gate text names only red and green, so it has no route for it. A guard meant to catch a false green now produces a false stop for a consumer whose summary cannot be seen. | major |
| L3-2 (leaf; pre-existing, newly pinned) | `test_discover_modules.py` about 776; `_maven_cmd_discover.py:1126,1153` | A standalone `examples/` POM the root does not build | The new test asserts `examples` gets `test -pl examples -am`. Run at the root, Maven rejects a `-pl` project outside its reactor (from knowledge, not shown by reading), so a change under `examples/` makes branch 6 red, Mark Failure runs and the push halts. The root fix stops granting the root canonical for it but leaves the module's own canonical a command that cannot run. | major |
| L3-3 (leaf) | `_maven_execute.py:448-456`; `_build_execute_factory.py:752-774` | A routed build against a daemon not reconciled to the merge | The guard lives in the daemon child's code. If the child runs pre-merge code, a routed zero-test `test` run stays `success`, and PLAN-LB-120 L3-2 is unchanged on that path. Builds route by default (the lane routed all eleven). A daemon reconcile is owed and not listed. | minor |
| L3-4 (leaf) | `_maven_cmd_discover.py:304-351,690-742`; `_build_discover.py` `EXCLUDE_DIRS` | `<module>child/pom-alt.xml</module>`, `${prop}` module entries, Maven 4.1.0 `<subprojects>`, modules under excluded directory names (`build`, `target`) | The new reactor resolution under-grants: the root loses its canonicals and the gate passes UN-GATED with a WARNING where the previous code ran real tests. `..`, absolute paths, cycles, `<module>.</module>`, namespaces, comments and CDATA are handled. | minor |
| L3-5 (leaf) | `_maven_execute.py:119,359,435-437` | (a) one module with a configured `skipTests` in a reactor whose other modules collected nothing; (b) a fully-qualified `g:a:v:test` goal; (c) a Failsafe exit-0 miss under `verify` | (a) the skip marker is a substring of the whole log, so the reactor run stays green; (b) the run is unguarded; (c) not caught. False negatives of the guard. | minor |
| L3-7 (leaf) | `_build_execute_factory.py:518-519,536-537`; `_freshness_crosscheck.py:746-748,979-989,1163-1165` | A guarded zero-test run | The ledger seam row gets `status=unknown`, `exit_code=0` and the route; freshness candidates must be `success`, so this row cannot certify, which neutralises PLAN-LB-120 L3-2 for runs the guard sees. PLAN-LB-120 L3-1 is unchanged: a green `test -pl X -am` row still lands in `ROW_CANONICAL_UNKNOWN` (UNDETERMINED, passes). The factory docstring warns that an `unknown` row with exit 0 reads as a completed gate to an exit-code-only consumer, and this merge adds such rows. | info |
| L3-8 (leaf) | `_maven_execute.py` (190 to 499 lines); PLAN-LB-115 D4 | — | No shared hunk, so PLAN-LB-115's factory citations hold. Two new Maven `indeterminate` reasons (`test_run_executed_nothing`, `test_log_unreadable`) now travel the routed legs PLAN-LB-115 D4 decides; D4's Done-when pins only the selector reason. Any citation into `_maven_execute.py` moved. | info |
| L3-6, L3-9 (leaf) | `_maven_cmd_discover.py:276`; `:1138` | A symlinked module directory outside the root; a `package` run whose summary names zero tests | the root decision is made for the wrong module (`known_modules['.']` overwritten); a `package` run under a tag filter becomes `indeterminate`. | info |

**Layer 3 verdict:** findings — two major (L3-1, L3-2), minor L3-3 to L3-5, the rest info.

## Reviews and Merge

The lane reports CodeRabbit (required, quota-limited) reviewing `2059eb260`, `12415d8ae` and the merge head `0ae252455` (`kind=reviewed`, risk Low, no actionable comments), with two rate-limited re-triggers recorded; Sourcery (optional) refused on its own budget. I read no review body, no PR body and no CI output: the review history, the CI result and the merge-queue path are the lane's claim and are `not_shown_by_reading`. Git confirms the squash commit `74ddc39a8` and its subject.

## Residue and Watches

- Two major layer-3 findings want a fix plan; it is staged on the operator's word only. The surface is `_maven_execute.py` (the guard), `_maven_cmd_discover.py` (the module canonical for a test-helper-only module, the unreadable POM, the under-grants), `pre-push-quality-gate.md` and `execute-task/SKILL.md` (a route for `indeterminate`), and the discovery tests. It sits on files no running plan declares.
- Settle first at that plan's outline: how a test-helper-only module and a `-q` or `printSummary=false` consumer should be told from a run that collected nothing (decides L3-1's reach), whether a module outside the root's reactor should keep a `-pl` canonical at all (L3-2), and which code the daemon child runs.
- **Interaction watch (the running PLAN-LB-115):** L3-8. PLAN-LB-115 D4 should pin the two new Maven reasons across the routed hop beside the selector reason. PLAN-LB-115 is running, so its spec is not edited; the lane meets it at its outline.
- **Answered:** PLAN-LB-120 L3-2 (a green zero-test Maven row is never refuted) is neutralised for runs the guard sees (L3-7); PLAN-LB-120 L3-1 is unchanged.
- **Watch (owed, operator-run):** the harness sync after this merge, and a daemon reconcile so the routed child runs the guard. Not owed: an executor regeneration. `uv.lock` is stale against `pyproject.toml` on main since the dependency merge `ddb893c96` (C11).
- The ninth landing in a row with a layer-3 fix owed.
- The `landing-check` gap on `total_tokens` is out of scope.
- The lane's rule check (two guard refusals, one `grep` and one `git show` outside the file tools, one `git restore` of `uv.lock` on an operator selection) is its own account and is not re-read.
