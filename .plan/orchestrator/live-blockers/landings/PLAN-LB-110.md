# Landing Analysis: PLAN-LB-110 — a Maven consumer's test results read true

epic: live-blockers
workstream: WS-02
pr: #1921

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-110.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Merge commit `9c8eb94c26ebfea1e4eb268f262a333735e159a1`, a squash commit with ONE parent, `1d2b559fd1a3f56a1a755788d7e144c4914dbd7f` (the merge of PLAN-LB-107, read with git and named in the leaf prompt). Landing message `rb-lb-110-maven-consumer-test-truth-001.md` (runbook lane; harness opencode, model `deepseek-v4.1-flash/high`). `landing-check` reports `complete: false`, missing `total_tokens` only (the known gap; out of scope); its surface delta is `unmeasured`, so the surface was read from the diff: 26 files, +1470/−62 (`git show --stat 9c8eb94c2`). The lane reports 3 of 4 deliverables done (D2 not fully met), `self-review: budget-exhausted` after three rounds, a spec read from the ledger copy. The merge is the lane's claim for CI and reviews; git confirms the squash commit and its subject.

Surface against the spec's Expected Surface: the diff touches four files the spec did not declare, all in shared build code — `_build_execute_factory.py`, `_build_parse.py`, `_build_server_protocol.py`, `_build_shared.py` — plus `_maven_cmd_resolve_scope.py`, `build-pyproject/test_build_findings_store.py` and `build-server/test_build_execute_routing.py`. The spec said shared build code stays untouched by default. No verb or flag was added (`git diff 1d2b559fd 9c8eb94c2 -G 'add_parser|add_argument' --stat` is empty, orchestrator), so no executor regeneration is owed.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — the parser files diagnostics only | shipped | Headers matched by `fullmatch`, continuation fields attached to the compiler error's detail, an orphan still filed (leaf, `_maven_cmd_parse.py:76-94,197-243`; tests `test_maven_cmd_parse.py:712-827`). Not re-read. |
| D2 — a reactor root resolves `module-tests` / `test-compile` | shipped-modified; the "re-run discover" Done-when is rightly dropped, the canonical rule is too wide (L3-1) | Pass 3 grants both canonicals to a root `pom` when ANY discovered module has tests (`_maven_cmd_discover.py:269-307`, re-read). The lane's refutation of the spec premise holds (L1-1). |
| D3 — a selector that matched nothing is a named reason | shipped-modified; the relabel drops real failures of two categories it does not protect (L3-2) | `apply_selector_miss_guard` (`_maven_execute.py`, about `:56-150`, re-read) relabels to `indeterminate` and keeps the reason. The routed leg carries the reason through a shared-code change that reaches every tool (L1-4). |
| D4 — the per-task gate derives the scope verb | shipped | `execute-task/SKILL.md:280-292` carries no literal pyproject notation (leaf); the doc-contract test is at `test_narrow_unit_doc_contract.py:257-271` (leaf). Not re-read. |
| not a deliverable | not measurable | `landing-check` surface delta `unmeasured`; read from the diff as above. |
| executor regeneration | corroborated | The `add_parser|add_argument` diff is empty. |

## Three-Layer Analysis

One read-only leaf (`execution-context-level-5`, resolved on `orchestrator.analyze`) read the landing at the merge commit (its `HEAD` equalled the merge). Its first run died on a weekly rate limit and was resumed from its saved work; nothing was lost or re-run from scratch. It reported two reads outside the allowed tools (a `python3 -c` and a `git grep -n`, both read-only) and re-read the cited lines with `Read`. The orchestrator re-read the points marked `re-read`. It was a reading only: no build, no test run, no write.

- **Dispatch:** one read-only leaf per landing — the read crosses 26 files, with 18 narrative claims passed one by one.
- **Verdict:** layer 1 findings (one major, minor, info); layer 2 findings (minor, info); layer 3 findings (**two major, one major collision**, minor, info). No blocker.
- **Orchestrator re-read:** L1-4 (both factory hunks), L3-1 (pass 3 and its docstring), L3-2 (the guard), L3-7 (the stale line), C6 (`_load_module_or_raise` and the `_architecture_core.py` module docstring). Every other row is a lead the leaf checked and I did not re-read.
- **Leaf line numbers corrected.** The leaf cited `_maven_execute.py:438-510`; that file has 190 lines at the merge commit. The substance it reports is in the file (the readable-log fall-through, the "ONLY failure" comment, the two-category check, the selector named from the command), so its claims are carried and the citations are given as approximate. Treat the leaf's other line numbers in this file accordingly.
- **Prompt check.** The 18 claims went into the prompt as separate items.

### Layer 1 — Specified

| Finding | Claim | Verdict | Evidence (file:line) |
|---------|-------|---------|----------------------|
| L1-1 (info, re-read) | The spec's D2 premise — "a consumer sees the change only after `architecture discover` is re-run, because the command map is persisted at discovery" — is false. The resolver reads the live worktree: `resolve_command` loads through `_load_module_or_raise`, which calls `iter_modules` / `load_module_derived`, and the architecture core's own module docstring says `derived.json` "is ephemeral — computed on demand by crawling the live worktree filesystem on every read. It is NOT persisted to disk". The on-disk read is the fallback only when live discovery finds no modules (leaf). The lane's "not met as written" is correct and its correction is sound. | corroborated | `_cmd_client_query.py:38-48`; `_architecture_core.py` module docstring |
| L1-4 (major, re-read) | The spec: shared build code stays untouched unless the zero-test check cannot live in build-maven, and then "keep the shared change to the one reason value". The diff changes the shared routed result mapping for every tool. On the routed failure leg a child verdict that is neither success nor error is now re-rendered as itself (timeout, killed, indeterminate) instead of becoming `error/build_failed` (`_build_execute_factory.py:786-799`), and an indeterminate result now carries the child's own `message:` (`:943-963`); `LogVerdict` gains a `message` field (`_build_server_protocol.py`, leaf). No new reason value is added in shared code (the selector reason lives in `_maven_cmd_parse.py`), but the first change is not needed for D3 and moves behaviour for pyproject, Gradle and npm. The leaf says a routed child that reports timeout or killed and arrives on the wire as `failure` changes from Mark Failure to STOP at the gates; that gate reaction was not read. The narrative's justification ("section 4") is the Findings section and holds none; whether the PR body does is not read. | checked (code); gate effect leaf | `_build_execute_factory.py:786-799, 943-963`; `_build_server_protocol.py` (leaf) |
| L1-2 (minor, leaf) | The grammar sentence the spec dictated, "a list joined with `+` is one pattern, and it matches nothing", is right for the class position and wrong for Surefire's documented method form `Class#one+two`. | checked (text); Surefire behaviour from knowledge | `build-maven/SKILL.md:42` |
| L1-3 (minor, leaf) | D2's Done-when asks for step 0 "reaching `resolve-test-scope`"; the gate test only checks that `maven.py --help` lists the verb and never calls it over the fixture. | checked (leaf) | `test_finalize_maven_reactor_root_test_canonical.py:207-224` |

**Layer 1 verdict:** findings — one major, two minor, one info.

### Layer 2 — Implemented

- **Confirmed (leaf):** C1, C2, C3 (the detail de-duplication is Maven-local; the shared `Issue` contract changed by docstring only), C4, C5 (with L3-1), C8 for step 0, C9 (the named reason survives both routed legs), C11 (phrase-level guard, as the lane says), C13, C14 (the cascade is real and pinned; no false record arises — branch 6's status names exclusions that actually ran, which understates coverage, and the freshness check reads `args`), C15, C18.
- **C6 confirmed (re-read)** — see L1-1.
- **C7 partly confirmed:** the default-scope probe succeeds for a root `pom` at `.` with tests, so the `-pl`-removal fallback is not reached there; it stays reachable when no module sits at `.` (`get_root_module` falls back to the first module in sorted order, leaf). Whether `test-compile -am` without `-pl` is malformed was not shown by reading, yet a test docstring states it as fact (L2-3).
- **C12 understates the factory change:** four shared files changed; two are docstring or comment only (`_build_parse.py:125-131`, `_build_shared.py:376-380`), one adds a defaulted field, and the factory changes routed behaviour for all tools (L1-4).
- **C16:** the lane cites base `c394a95` for its failing runs; the leaf found the diff over every landing path empty between `c394a95fb` and the true parent `1d2b559fd`, so the base difference does not matter. Per the leaf, the D3 parse and execute tests are red at the parent because their modules fail at import (`test_maven_cmd_parse.py:31-33`, `test_maven_execute.py:213-214`), not on behaviour. Red-at-base for every test is a reading, `not_shown_by_reading`.
- **C17 partly confirmed:** `_build_jvm_patterns.py` is untouched and the Gradle parser is unchanged, but Gradle's routed result mapping moved (L1-4).
- **L2-1 (minor, re-read):** the guard's comment says a miss claims the run only "when it is the ONLY failure in the log", and the code backs off only for `test_failure` and `compilation_error` issues (`_maven_execute.py`, about `:100-107`).
- **L2-2 (info, leaf):** `test_discover_reactor_aggregator_has_no_test_ladder` was renamed and lost its `module-tests` assertion without a docstring saying why (`test_discover_modules.py:729-734`).
- **L2-3 (minor, leaf):** `test_finalize_maven_reactor_root_test_canonical.py:170-177` states the `-am` malformation as fact; the narrative calls the hypothesis refuted.

**Layer 2 verdict:** findings — one claim understated (C12), one partly confirmed (C7, C17), two minor, one info; the rest confirmed.

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 (re-read; effect not settled) | `_maven_cmd_discover.py:251-307` | A root `pom` for which `discover_descriptors` finds a `pom.xml` with tests anywhere on disk that the root does not build — a standalone `examples/` POM, or test modules only inside a profile's `<modules>`. The leaf also reads the lane's own fixture (a root aggregator declaring no `<modules>`) as getting `module-tests = test` (`test_discover_modules.py:737-751`, not re-read). | "Reactor" is every discovered POM, not the root's declared modules (`:273` `any(... for module in modules)`). The docstring says a canonical that would run nothing is "a false green, worse than an absent one" (`:290-293`), which is exactly what a root granted on a count the root does not build would be: default-scope `module-tests` resolves to `test`, builds the root only, runs zero tests, and the build succeeds. Whether the pre-push gate or `cmd_run_common` refuses a green that executed zero tests was not read, so the effect is the lead. | major |
| L3-2 (re-read; category membership leaf) | `_maven_execute.py` about `:100-110`; `_build_parse.py`, `_build_jvm_patterns.py:24-69` (leaf) | `mvn -fae test -Dtest=Foo`: module a fails on `';' expected`, module b prints "No tests matching pattern" | The selector miss backs off only for `test_failure` and `compilation_error` issues. The leaf reads the `compilation_error` category as nine phrases, so `Failed to execute goal … Compilation failure`, `';' expected`, enforcer and checkstyle failures categorise as `other`, and `dependency_error` is also unprotected. The run becomes `indeterminate` with "matched no test, so the run executed nothing" and module a's error, rows and findings are dropped. Not a false green (indeterminate still blocks); it misreports what the build did, the class of defect the spec targets. | major |
| L3-6 (re-read, collision) | `_build_execute_factory.py:786-799, 943-963`; `test_build_execute_routing.py:1245-1344` (leaf) | — | The new `TestIndeterminateReasonCarry` class (five tests) is appended to the routing test file; the two hunks (a) re-render a non-success, non-error child verdict as itself on the routed failure leg and (b) carry the child's `message:` on an indeterminate result. This lands on routed-result mapping, the territory of the running PLAN-LB-108 (routing file) and the held PLAN-LB-115 (routed fault mapping). The spec of PLAN-LB-115 has to be re-read against these hunks before it is emitted. | major (collision) |
| L3-3 (leaf) | `_maven_execute.py` about `:130-150` | Selector matched in module a, module b then fails "No tests matching pattern" (Surefire's default) | The reason still says "the run executed nothing", which is false. | minor |
| L3-4 (leaf) | `_maven_cmd_parse.py:404,450-453`; `_maven_execute.py` about `:109-110` | `-Dtest` set through `.mvn/maven.config`, `MAVEN_OPTS` or a profile; a Failsafe `-Dit.test` miss | The pattern captured from the log is never used; the selector is named only from the command line, so the failed-build reason reads "the -Dtest selector". The exit-0 miss (`failIfNoSpecifiedTests=false`) is not detected at all when `-Dtest` is not on the command line. | minor |
| L3-5 (re-read) | `_maven_execute.py` about `:88-92` | A `-Dtest` exit-0 run whose log cannot be read | `except (KeyError, OSError): return result` keeps `success` — a fail-open on an undecidable read ("no readable log means no evidence", per its comment). The failure-leg `parse_log` call has no handler (leaf). | minor |
| L3-7 (re-read) | `pre-push-quality-gate.md:419` and `:479,491,495,500` (leaf for the latter) | — | Line 419 still says the fix needs "an `architecture discover` refresh so the persisted inventory picks it up", false under the live crawl; branches 3, 4, 5 and 6 still say "pytest" and "non-Python project" for an arm Maven now reaches. | minor |
| L3-8 (leaf) | `_build_examined.py:97-106`; `_freshness_crosscheck.py:326,352-356` | A ledger row for the new root run `--command-args test` | Maven's `test` goal is not in `CANONICAL_ANALYSES`, so the row is `canonical_outside_vocabulary`: coverage UNDETERMINED, which passes with the gap recorded and earns no test credit. This answers the open hypothesis in PLAN-LB-120's spec (Maven `test`/`package` outside the vocabulary) for the `test` goal. | info |
| L3-9 (leaf) | `execute-task/SKILL.md:314` | A task that changes a module with no tests | Through the cascade it now hands back a whole-reactor `test` run per task: a cost increase, not a correctness defect. | info |
| L3-10 (leaf) | test docstrings | — | Transitional wording ("shipped before this plan", "at the branch base"). | info |
| L3-11 (leaf) | `_maven_cmd_parse.py:240-243`; `_build_parse.py:428-489` | — | Rows under `Failures:` are still filed; the continuation window closes on any other line, so it cannot cross modules; wrong attachment needs a collision of the 100-character dedup prefix. No defect. | info |
| L3-12 (leaf) | `_build_shared.py:381-384` | A Maven compile error | Its detail appears under the store label "--- failure detail ---". Cosmetic. | info |

**Layer 3 verdict:** findings — two major (L3-1 lead on effect, L3-2), one major collision (L3-6), minor L3-3 to L3-7, the rest info.

## Reviews and Merge

The lane reports CodeRabbit (required, quota-limited) reviewing `7e8879df5` and `2afd917bd` (seven inline findings and one nitpick across the two reviews, all fixed or answered, threads resolved), refusing on quota for the last head `55a0dd166`, and the standing authorization applied; Sourcery (optional) refused on its budget. I read no review body, no PR body and no CI output: the review history, the CI result and the merge-queue path are the lane's claim and are `not_shown_by_reading`. Git confirms the squash commit `9c8eb94c2` and its subject. The lane's account of two guard refusals (a multi-line commit message, a piped `grep`), a `verify` that hit the daemon bound and a `quality-gate` that hit the 330 s floor is its own and is not re-read.

## Residue and Watches

- Two major layer-3 findings and one major layer-1 finding want a fix plan; it is staged on the operator's word only. The merge's surface is `build-maven` (discovery, parse, execute), the shared routed-result mapping, and the pre-push gate text.
- Settle first at that plan's outline: whether the pre-push gate or `cmd_run_common` refuses a green run that executed zero tests (decides L3-1's impact), whether discovery should key the root canonical to the root's declared modules, and which routed non-Maven verdict changes (timeout, killed) the gates actually receive on the wire (decides L1-4's reach).
- Collision watch: the factory and routing-test hunks (L3-6) sit on PLAN-LB-108's running surface and PLAN-LB-115's held surface; PLAN-LB-115 re-reads its line references at its outline (its spec already says so), and PLAN-LB-108's lane will meet the hunks when it rebases.
- The `+` grammar sentence (L1-2) and the stale text (L3-7) are documentation fixes that can ride any plan touching these files.
- This is the fifth landing in a row (PLAN-LB-114, 117, 118, 107, 110) with a layer-3 fix owed.
- Harness sync is owed outside this plan, operator-run. No consumer needs to re-run `architecture discover`.
- The `landing-check` gap on `total_tokens` is out of scope.
- The lane's rule check (two guard refusals, both corrected) is its own account and is not re-read.
