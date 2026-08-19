# Gaps — 300-freshness-gate-cannot-distinguish-test-authored-evidence

The shipped cross-check is correct and non-vacuously tested; nothing here disputes the mechanism.
What remains falls in three clusters. **(1) A false mechanism claim about the architecture crawl's
cost** — that it shells out to Maven/Gradle/npm discovery verbs — propagated into four surfaces
including the crawl's own docstring. ⚠ **The companion claim that the shipped 1–5 s cost range is
too low did NOT survive adversarial re-measurement and has been withdrawn** — see G1. **(2) Three
test gaps**, two of them on code the verification rounds *themselves* added — including round 3's
reproduced runtime bug, whose fix was reverted with the suite staying green — and one where an
anti-vacuity control cannot perform the detection its docstring claims, which adversarial review
reproduced directly and re-rated **high**. **(3) A latent, undocumented and untested coupling**
between the executor's stamp allow-list and the architecture's classifier map, where a future
mismatch would hard-block the gate project-wide. Plus five stale claims confined to `report-01.md`.

---

## G1 — Qualify the crawl-cost range in `manage-tasks/SKILL.md` as host- and load-dependent

⚠ **This entry was filed at `medium` on a measurement that adversarial review could not reproduce.
The original claim — that the shipped 1–5 s range is roughly 2× too low — is WITHDRAWN. The shipped
figure is correct on an unloaded host. What survives is a much smaller documentation point, and the
severity is corrected to `low` accordingly.**

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md:411-415`
- **Evidence:** The shipped text reads *"Measured on this repository — Python-only — the first crawl
  took roughly 1 to 5 seconds, across four independent measurements in different sessions and
  filesystem-cache states; the spread is the honest answer and a point estimate would not be."*
  ⭐ **Nine fresh measurements taken during adversarial review, each in a new process, all fall
  INSIDE that range:** five of `resolve_project_build_notations(<repo root>)` — **3.70, 3.41, 3.12,
  3.09, 2.99 s** — and four of `crawl_all_modules(<repo root>)` — **3.23, 3.31, 3.46, 3.27 s**. The
  memoized second call in the same process costs **0.0014 s**, confirming the once-per-process claim.
  ⛔ **The original 7.64 / 10.62 / 10.11 / 8.45 s readings are a concurrency artifact, not a host
  property.** This working tree is shared with other agents running full pytest suites; re-measured
  deliberately under artificial CPU contention on the same 4-core container, the same
  `crawl_all_modules` call returns **11.56, 7.93, 7.19 s** — reproducing the original figures almost
  exactly. The audit measured contention and attributed it to the machine.
- **Why it matters:** The residual point is real but small: the range is stated as a property of
  *the repository*, and it is a property of the host and its load as much as of the repository. An
  operator budgeting the gate's two wiring points (phase-5 Step 12a, phase-6 `push`) on a busy CI
  runner can legitimately see 2–3× the stated figure. Nothing in the shipped text warns of that.
- **Action:** Add a host/load qualifier to the existing sentence — the measurements are from an
  unloaded developer host, and a contended one can multiply them severalfold. ⛔ **Do NOT widen or
  replace the numeric range:** it is accurate for the condition it names, and the two properties that
  actually bound the cost (paid only after the primary predicate matched; never on the `stale` path)
  are already stated and correct.
- **Done when:** the cost sentence in `manage-tasks/SKILL.md` § step 7 names the measurement
  condition (unloaded host) alongside the range.
- **Effort:** S
- **Risk if fixed:** None — documentation only.

---

## G2 — Correct the "shells out to each build tool's discovery verbs" claim in `manage-tasks/SKILL.md`

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md:408-411`
- **Evidence:** Shipped text: *"It shells out: `git` on every project, plus each build tool's own
  discovery verbs on a Maven/Gradle/npm one (`crawl_all_modules` documents `help:all-profiles
  dependency:tree` per Maven module)."* Independently re-instrumented during adversarial review:
  with `subprocess.run`/`Popen`/`check_output`/`check_call`/`call` all wrapped before import,
  `resolve_project_build_notations(<repo root>)` issues **exactly ONE child process —
  `git rev-parse --git-common-dir`**. ⚠ The audit originally reported "2 subprocess calls"; that is a
  double-count, because `subprocess.run` is itself implemented over `Popen` and both wrappers fired
  on the same invocation. ⭐ **The one `git` call is also not what any of these documents implies.**
  Its captured stack is `plugin_discover.attach_lsp_references` → `lsp_harvest.resolve_binding` →
  `lsp_client.resolve_language_server` → `run_config.get_run_config_path` →
  `marketplace_paths.resolve_main_anchored_path` → `_main_checkout_root` — a main-checkout-root
  resolution for LSP configuration, **not** a worktree-sha computation and not a build-tool verb.
  Maven module discovery is explicitly subprocess-free —
  `build-maven/scripts/_maven_cmd_discover.py:220-224`: *"Discover all Maven modules with complete
  metadata — subprocess-free … No Maven subprocess is invoked."* `help:all-profiles dependency:tree`
  lives in `enrich_maven_module`, whose only caller is `_cmd_client_query._enrich_maven_module_cached`
  (`:80-108`), reached from `resolve_command`'s profile fallback and the dependency-graph path —
  **neither of which `resolve_project_build_notations` calls**. `build-gradle/scripts/` and
  `build-npm/scripts/` contain no discovery subprocess at all.
- **Why it matters:** This is the stated basis for "treat that range as a floor" on Maven/Gradle/npm
  and for the residue item asking for a Maven measurement. It overstates the gate's cost on exactly
  the toolchains the project most wants to protect, and an overstated cost is the argument a future
  author will reach for when proposing to weaken or skip the check — the doc-only carve-out this plan
  deliberately refused, re-entering through a cost claim instead.
- **Action:** Replace the build-tool clause with what the crawl actually does: parse each build file
  with stdlib parsers, walk the filesystem, and issue a single `git rev-parse --git-common-dir` while
  resolving the main checkout root. ⛔ **Do not describe that `git` call as a worktree-sha
  computation** — it is not one, and writing it that way would ship a fresh invented rationale of
  exactly the class this plan exists to close. Keep the `git` half, which is true as to *whether*
  `git` runs.
- **Done when:** `SKILL.md` § step 7's cost paragraph names only subprocesses the instrumented crawl
  actually issues, describes the `git` call by the purpose its call stack shows, and a test or a
  comment records how that was established.
- **Effort:** S
- **Risk if fixed:** None — documentation only.

---

## G3 — Correct the same false Maven claim in `resolve_project_build_notations`'s docstring

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py:800-803`
  (`resolve_project_build_notations`, § **Cost**)
- **Evidence:** *"This runs the same live crawl `architecture resolve` runs (memoized per process,
  but the first call pays for it, and **for Maven that means a per-module `help:all-profiles
  dependency:tree`**)."* Falsified by the same instrumentation and call-graph read as G2 — the enrich
  path is not on this function's call chain.
- **Why it matters:** This is the production-source copy, i.e. the one a maintainer of this function
  reads first. It is also a *new* docstring written by this run, not inherited — the run propagated an
  unverified mechanism claim into its own new API, which is precisely the invented-rationale class
  the report names three times.
- **Action:** State the real cost mechanism (build-file parsing + filesystem walk + one `git`
  invocation) and, if the Maven enrich path is worth mentioning, say explicitly that this function
  does **not** reach it.
- **Done when:** the docstring's Cost section names no subprocess the function does not cause.
- **Effort:** S
- **Risk if fixed:** None — documentation only.

---

## G4 — Correct the same false Maven claim in `_forbid_builds`'s re-scoped docstring

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** tests
- **Where:** `test/plan-marshall/manage-execution-manifest/test_plan31_docs_only_deadlock_regression.py:150-155`
  (`_forbid_builds`)
- **Evidence:** *"that resolution runs the live module crawl — which does shell out (`git`, **and a
  build tool's own discovery verbs on a Maven/Gradle/npm project**)."* Same falsification as G2.
- **Why it matters:** This docstring exists to tell a future reader why the "nothing shells out"
  invariant was narrowed. Narrowing it for a reason that is false invites someone to widen it back
  incorrectly, or to leave the candidate path permanently unguarded on a premise that does not hold.
- **Action:** Keep the narrowing (the `git` call alone justifies it) and delete the build-tool clause.
- **Done when:** the docstring's justification names only `git`.
- **Effort:** S
- **Risk if fixed:** None — comment only.

---

## G5 — Correct the root claim in `crawl_all_modules`'s own docstring

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** architecture-core
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_architecture_core.py:492` and `:543-545`
- **Evidence:** *"Memoization: the crawl is expensive (it shells out to the build tools — e.g. Maven
  runs `help:all-profiles dependency:tree` per module)."* (`:543-545`; the same claim again in the
  `_CRAWL_CACHE` comment at `:492`, which adds *"O(N²) subprocess invocations"*). This is the claim
  G2–G4 all cite as their authority, and it is pre-existing (not introduced by this plan). It is
  contradicted by **two** other first-party surfaces, not one: `_cmd_client_query.py:56-58` states
  *"The cheap architecture crawl is subprocess-free: it parses each pom.xml with stdlib XML and does
  not run Maven"*, and `build-maven/SKILL.md:38` states *"**discover**: Subprocess-free — parses each
  `pom.xml` with stdlib XML … Resolved coordinates, inherited profiles, and the resolved dependency
  tree are filled lazily … by `enrich_maven_module`"*. Instrumentation (G2) settles it in favour of
  the two: one child process, and it is not a build tool.
- **Why it matters:** ⭐ **Severity is `medium` rather than `low` because this is the source, not a
  copy.** Three surfaces (G2, G3, G4) state the falsehood because they quoted this docstring as
  authority; G3 is a *new* public API docstring this plan wrote by copying it. Fixing the three
  copies while leaving the authority intact guarantees the next author re-derives the same error from
  the same place — so this entry, not its derivatives, is the one that has to land. It also leaves
  two docstrings in the same skill asserting opposite things about the same function, with the false
  one carrying the more quotable phrasing.
- **Action:** Correct `crawl_all_modules`'s docstring to say the crawl is subprocess-free apart from
  the `git` worktree-sha call, and cross-reference the lazy Maven enrichment as the separate,
  genuinely expensive path.
- **Done when:** `_architecture_core.py` and `_cmd_client_query.py` agree about whether the crawl
  runs Maven.
- **Effort:** S
- **Risk if fixed:** Low — a reader who relied on the "expensive" framing to justify the memo may
  need the memo's justification restated (the filesystem walk is still worth memoizing).

---

## G6 — Add a regression test for the widened import guard (round 3's reproduced runtime bug)

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py:212-225`
  (`resolve_expected_notations`, the `except Exception` on the import)
- **Evidence:** I replaced `except Exception:` with `except ImportError:` — reverting R3-4's fix
  exactly — and ran `test/plan-marshall/manage-tasks/` plus
  `test/plan-marshall/manage-architecture/test_project_build_notations.py`: **504 passed**. The only
  existing case, `test_resolver_reports_an_unimportable_resolver_apart_from_a_failing_one`, raises
  `ImportError`, which the narrowed clause still catches. (File restored from a byte snapshot;
  `git status --porcelain` clean.) ⭐ **Independently reproduced in adversarial review**: the same
  substitution, the same 504 green, the same clean restore — and the 504 baseline itself re-derived
  before mutating.
- **Why it matters:** R3-4 is the one *behaviour* change round 3 shipped, and the report's argument
  for stopping the verification loop rests on it being "small, and its class was just swept". An
  unguarded `RuntimeError` from `_cmd_client_build`'s module-scope `resolve_bundles_root` would hand
  phase-5 Step 12a and phase-6 `push` a traceback instead of a TOON `status` — the gate's never-raises
  contract broken on a deployment fault. Nothing in the suite would notice a regression.
- **Action:** Add a case to `test_freshness_notation_crosscheck.py` that makes the *import* of
  `_cmd_client_query` raise a non-`ImportError` (e.g. a `meta_path` finder raising `RuntimeError`, or
  a `sys.modules` stand-in whose module body raises) and asserts
  `(frozenset(), REASON_RESOLVER_UNIMPORTABLE)` — and, at gate level, that the verdict is `fresh` with
  `notation_cross_check: unverified` rather than an exception.
- **Done when:** narrowing the clause back to `except ImportError:` turns at least one test red.
- **Effort:** S
- **Risk if fixed:** None.

---

## G7 — Cover or delete the non-container guard on the resolver's return value

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `_freshness_crosscheck.py:237-238` (`if not isinstance(notations, (frozenset, set)):`)
- **Evidence:** Replacing the condition with `if False:` leaves the same 504 tests green. Every stub
  in the suite (`_FakeQueryModule`, `_stub_expected`) returns a `frozenset` or raises, so the branch
  is unreachable from any test.
- **Why it matters:** The guard's own comment concedes it defends a future resolver rather than a
  live hazard (R3-14). Untested defensive code that is also unreachable in production is dead weight
  a later reader cannot distinguish from a live guard; if it is kept, it should be pinned so its
  removal is caught.
- **Action:** Either add a one-line case passing a non-container through the `_cmd_client_query`
  stand-in and asserting `REASON_RESOLUTION_FAILED`, or remove the guard and keep only the comment
  explaining why the single `return frozenset(...)` makes it unnecessary.
- **Done when:** either the branch has a test, or it no longer exists.
- **Effort:** S
- **Risk if fixed:** Low — removing the guard reopens a `TypeError` escape if a second `return` is
  ever added; the test option carries no risk.

---

## G8 — Make the gate's anti-vacuity control actually detect an import-path fault

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py:544-584`
  (`test_the_real_resolution_path_refuses_and_corroborates_against_this_repository`), docstring at
  `:548-560`
- **Evidence:** The docstring claims: *"If the real resolver could not be imported at runtime … the
  cross-check would collapse to a permanent `unverified` pass — and all of those cases would stay
  green … so an import path or a crawl that stopped working is a test failure rather than a silent
  no-op."* `resolve_expected_notations` reaches the resolver with `from _cmd_client_query import …`,
  which consults `sys.modules` **before** any finder. Demonstrated directly: with a `meta_path`
  finder making `_cmd_client_query` unfindable by name, `resolve_expected_notations` returns
  `architecture_resolver_unimportable`; after a `spec_from_file_location` load registered under that
  same name — exactly what `conftest.load_script_module(..., '_cmd_client_query')` does at module
  scope in `test_project_build_notations.py:28`, and what `test_on_demand_crawl.py:29` does
  transitively via `_cmd_client.py` — the identical call returns `reason: None` and the full notation
  set. Collection order makes this certain: `test_project_build_notations.py` is collected at line
  3521 of `pytest --collect-only -q test/plan-marshall`, the crosscheck file at line 8713.
- **Why it matters:** This control is the fix for V1-6, which the report calls "the most serious
  finding of the round" — the demonstrated fault was *a missing `sys.path` entry*. In a full-suite
  run the control cannot see that fault, so the fix for the "nothing ever breaks" defect itself has a
  half that never breaks. The claim is also the exact class R2-4 fixed in the sibling docstring and
  did not re-check here.
- **Action:** Either (a) exercise the import in a clean interpreter — run the resolver reach in a
  subprocess with a controlled `sys.path` and assert it resolves — or (b) pop `_cmd_client_query`
  from `sys.modules` for the duration of the case (via `monkeypatch.delitem`) so the import genuinely
  goes through the finder, and additionally pass `register=False` in `test_project_build_notations.py`
  so it stops publishing a shared name it does not need. Then correct the docstring to state exactly
  which fault each case does and does not cover.
- **Done when:** removing the `manage-architecture/scripts` entry from the suite's `sys.path` turns
  this case red when the whole suite is run, not only when its file is run alone.
- **Effort:** M
- **Risk if fixed:** Low — `register=False` changes which module object other cases in that file
  patch; the file's own monkeypatching targets the returned object, so it is unaffected.

---

## G9 — Pin the executor's stamp allow-list against the architecture's classifier map

- **Kind:** omission
- **Severity:** medium
- **Topic:** tests
- **Where:** `tools-script-executor/templates/execute-script.py.template:313-318`
  (`_BUILD_CLASS_PREFIXES`, a **prefix** set) versus
  `manage-architecture/scripts/_cmd_client_build.py:76-81` (`_BUILD_NOTATIONS`, an **exact-key** map)
- **Evidence:** Computed with the repository's own helper (`test/_shared/_build_class_roster.py`):
  the executor's stampable build-class domain holds nine notations, `_BUILD_NOTATIONS` classifies
  four, and the difference is `build-gradle:extension`, `build-maven:extension`, `build-npm:extension`,
  `build-npm:js_coverage`, `build-pyproject:extension`. No test relates the two: `test_build_cli.py:746-767`
  pins roster ⊆ `_BUILD_CLASS_PREFIXES` and its converse, and
  `test_project_build_notations.py:47-54` sweeps `_BUILD_NOTATIONS` outward, but nothing checks that
  everything the executor can stamp is something the cross-check can classify.
- **Why it matters:** Before this plan an unclassifiable build notation was harmless. Now a row the
  executor stamps but the architecture cannot classify is `notation_unrelated`, and that refusal
  applies to the **whole candidate list** — so it blocks every pre-commit transition in the project
  until someone finds the two lists. The trigger is ordinary maintenance: adding a build wrapper (or
  giving `js_coverage` a `run` verb) while touching only the executor's prefix list. No live instance
  exists today — `run` is contributed only by `script-shared/scripts/build/_build_cli.build_main`, and
  none of the five divergent scripts routes through it — which is exactly why this will be discovered
  by a hard block rather than by a test.
- **Action:** Add a test asserting that every notation in `build_class_roster()` (the scripts that can
  actually be stamped, i.e. those exposing a build-executing subcommand) is a key of
  `_cmd_client_build._BUILD_NOTATIONS`, with a failure message naming the freshness-gate consequence.
  Record the coupling in `manage-tasks/SKILL.md` § "The notation cross-check" and in the executor
  template's comment on `_BUILD_CLASS_PREFIXES`.
- **Done when:** removing an entry from `_BUILD_NOTATIONS` turns that test red, and both files
  cross-reference each other.
- **Effort:** M
- **Risk if fixed:** Low — the assertion is over static registries; a legitimate build-class script
  with no `run` verb must be excluded from the population or the test will over-assert.

---

## G10 — Correct the residue row claiming a third verification round was not run

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/300-freshness-gate-cannot-distinguish-test-authored-evidence/report-01.md:860`
- **Evidence:** *"| **A third verification round was not run.** Round 2's findings still included a
  behaviour change (R2-12) … | The PR's automated reviewers, whose method differs from both rounds. |"*
  The same document has a titled section *"From verification round 3"* (`:456-480`) with thirteen
  numbered findings and states at `:535` that the loop "is stopped after round 3".
- **Why it matters:** § Residue is the hand-off surface. A later reader picking this plan's leftovers
  would schedule a round that already happened, and would trust a table that contradicts its own
  document — which devalues the other six residue rows, all of which are accurate.
- **Action:** Replace the row with the true residue: a **fourth** round was not run despite R3-4
  resetting the loop, and the stopping decision is an argued judgement (`:539-555`).
- **Done when:** no row in § Residue asserts that round 3 did not happen.
- **Effort:** S
- **Risk if fixed:** None.

---

## G11 — Correct the contract-check Step 6 row's "TWO ROUNDS" verdict

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `report-01.md:766`
- **Evidence:** *"| 6 Verification sub-agent | ✅ **TWO ROUNDS** | Round 1: … Round 2 was then
  dispatched … |"* — the body stops at round 2 and never mentions round 3.
- **Why it matters:** The Step-9 contract table is the run's own compliance record; an auditor reading
  only that table gets a materially smaller verification story than the run performed, and would
  under-credit the run while also missing that the loop was stopped by judgement rather than
  convergence.
- **Action:** Change the verdict to THREE ROUNDS and extend the artifact cell with round 3 and the
  stopping decision.
- **Done when:** the Step 6 row's round count matches § Findings.
- **Effort:** S
- **Risk if fixed:** None.

---

## G12 — Correct the "Verification loop — two rounds" section heading

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `report-01.md:518`
- **Evidence:** Heading: *"### Verification loop — two rounds, and the residue is named rather than
  assumed"*. Its own body (`:530-537`) describes the third round and the decision to stop after it.
- **Why it matters:** Third instance of the same stale count, in the heading a reader navigates by.
- **Action:** Retitle without a count (e.g. "Verification loop — and why it was stopped"), per the
  report's own prefer-naming-to-counting rule (R3-11, R3-12).
- **Done when:** the heading carries no round count.
- **Effort:** S
- **Risk if fixed:** None.

---

## G13 — Correct R3-2's "Fixed in both" disposition, which fixed only one of its two claim sites

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `report-01.md:472` (the R3-2 row) against `report-01.md:239-247` (the report's own crawl-cost claim site)
- **Evidence:** R3-2's disposition: *"**Fixed in both**, now 'roughly 1 to 5 seconds across four
  independent measurements', with the spread stated as the answer."* `manage-tasks/SKILL.md:412` does
  say "four independent measurements". The report's claim site still reads *"Three measurements, each
  carrying its own population — **3.95 s** …, **1.1 s** …, **4.85 s**"* and never names round 3's
  fourth measurement (4.23 s).
- **Why it matters:** R3-2 exists to correct R2-15 for claiming a fix at "its claim site" when the
  value had two — and then makes the same claim about the same pair of sites. Left standing, the row
  reads as evidence that the two-site sweep works, when the tree shows it did not.
- **Action:** Update the report's crawl-cost paragraph to four measurements (naming 4.23 s) and amend
  the R3-2 row to record which site was actually swept, or drop the count entirely per G1.
- **Done when:** the report's crawl-cost paragraph and `SKILL.md` state the same population.
- **Effort:** S
- **Risk if fixed:** None.

---

## G14 — Correct the report's claim that the live-repository case uses "the real import path"

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `report-01.md:212-213`
- **Evidence:** *"the case that keeps all the others honest — the live repository resolving its own
  build notation **through the real import path**"*. `test_the_live_repository_resolves_its_own_build_notation`
  obtains the resolver through `conftest.load_script_module` →
  `importlib.util.spec_from_file_location` (`test/conftest.py:421-435`), i.e. by absolute path,
  bypassing `sys.path`. The test's own docstring says so in a ⛔ paragraph
  (`test_project_build_notations.py:183-190`) that round 2 added for exactly this reason (R2-4).
- **Why it matters:** The report over-claims a coverage property the test file itself disclaims — the
  same over-claim R2-4 fixed one layer down. Read together with G8, the run's headline anti-vacuity
  story is stronger in the report than in the tree.
- **Action:** Restate the sentence to attribute the real-import-path half to the gate-level case and
  the live-crawl half to the architecture case, matching the two docstrings.
- **Done when:** no sentence in the report attributes `sys.path` import coverage to the
  absolute-path-loaded case.
- **Effort:** S
- **Risk if fixed:** None.

---

## G15 — Settle D4's scope departure: project-wide union versus the plan's plan-scoped wording

- **Kind:** incomplete
- **Severity:** low
- **Topic:** architecture-core
- **Where:** `plan.md` D4 ("compare the matched notation against the plan's **architecture-resolved
  canonical build commands**") versus
  `manage-architecture/scripts/_cmd_client_query.py:781-830` (`resolve_project_build_notations`,
  documented as *"Deliberately **project-wide, not plan-scoped**"*)
- **Evidence:** The shipped comparison set is the union over every module the crawl reports; `plan_id`
  is never read. The report discloses this as a departure (R3-15) and argues it on D4's own precision
  warning; the commit message repeats the disclosure.
- **Why it matters:** The deliverable's literal *Done when* is not what shipped. The departure is
  defensible and was disclosed rather than glossed, but nothing in the repository records the decision
  as settled — so a later reader comparing plan to code sees an unexplained mismatch, and a future
  author could "restore compliance" by narrowing the set, which would refuse orchestrator-tier builds
  (no plan) and a polyglot project's second toolchain.
- **Action:** Record the ruling in `manage-tasks/SKILL.md` § "The notation cross-check" as a stated
  contract — the set is project-wide by design, and narrowing it is a known regression — citing the
  two cases a plan-scoped set would refuse.
- **Done when:** the skill contract states the project-wide scope as deliberate, with the two refusal
  cases named, so the departure is a documented decision rather than a plan/code mismatch.
- **Effort:** S
- **Risk if fixed:** None — documentation of existing behaviour.
