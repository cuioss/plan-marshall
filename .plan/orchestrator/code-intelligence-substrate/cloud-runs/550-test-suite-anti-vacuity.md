> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# Restore falsifiability to the epic's test suite

**Epic:** code-intelligence-substrate
**Branch prefix:** fix — the defects are shipped tests that do not test what they claim

## Problem

A post-landing audit of this epic's 36 plans found, across 30 of them, a recurring class of defect
that is invisible to every signal the project uses: **tests that cannot fail**. Not tests that fail
for the wrong reason, and not missing tests noticed as missing — tests that are present, named after
a real property, cited in a run report as the guard for a deliverable, green on every run, and
incapable of going red if the property they name is deleted. The suite reports health it does not
have, and the deliverables those tests were written to lock are unprotected.

Six anchor instances, each reproduced by mutation rather than argued from reading:

- A test's final assertion reads back its own `print` from the line above, with `len(files)`
  interpolated on both sides — no state of the production code can make the two sides disagree
  (`test/pm-plugin-development/plan-marshall-plugin/test_path_attribution.py:131-132`).
- A population-derived corpus whose published size is `help_checks=1750 flag_invocation_checks=662`
  refuses **0** of the 1750 when every attribute is stripped from the derivation it guards: 72.6% of
  the corpus is surface-insensitive, and the validator short-circuits before it ever reads a surface
  (`test/plan-marshall/tools-script-executor/test_population_derived_surface_guard.py`).
- An anti-vacuity control whose docstring promises that "an import path … that stopped working is a
  test failure rather than a silent no-op" stays **green** when exactly that fault is injected,
  because a sibling test module registers the same module name in `sys.modules` and is collected
  first (`test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py:544-584`).
- A regression lock whose probe bundle is named `probe-bundle` while the mapping under test targets
  `plan-marshall:ref-toon-format:…`, so the lookup misses on the bundle segment whether or not the
  guard exists: disabling the guard leaves all 96 tests in the file green while the live corpus
  silently drops from `unresolved 61` to `unresolved 50` — 11 genuine findings resolved away
  (`test/pm-plugin-development/tools-marketplace-inventory/test_resolve_dependencies.py:1432-1468`).
- A one-line comment in the archived-plan auditor states *"`.get(check)` — NOT `.get(check, 0)`"*
  and explains why; making exactly that substitution survives **all 640 tests** in the check's own
  suite directory (`.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:5613-5616`).
- A "correctness property over the roster's classifications" derives its population from the
  registry, discovers 26 implementor docs against 25 registered steps — and then compares exactly
  **one** of them, because only one doc happens to carry the prose sentence the detector matches
  (`test/plan-marshall/phase-6-finalize/test_dispatch_roster_closure.py:197`).

**The mechanism is not one bug.** These sit in different bundles, were written by different plans,
and share no code. What they share is one of five *shapes*, and the shapes are what generalise:

1. **The guard derives its expectation from the thing it guards.** A hand-built dict, a mirrored
   constant, or the test's own output stands in for the production oracle, so the assertion is an
   identity.
2. **The assertion is negative-only, or weaker than the property it names.** The test asserts
   something true of both the correct and the defective state — a `!=` where the property is a
   value, a set cardinality where the property is a prefix, a `<=` where the property is an equality.
3. **The fixture reaches the asserted state by a different route than the test names.** A stub of a
   retired seam shape, a sibling module that pre-registers a name, an autouse fixture that supplies
   the very value the test claims to control — the test passes through the fallback while its
   docstring describes the real path.
4. **The population is empty, degenerate, or invisible, so the check passes vacuously.** A corpus of
   one, a sweep scoped to one section of one file, a set-guarding test over a set that is empty, a
   published count that pytest captures and discards on a green run.
5. **No direct test exists at all**, while a run report, a docstring, or a deliverable's *Done when*
   records the behaviour as covered.

The five shapes are the deliverable boundaries below. Grouping by shape rather than by source plan
is deliberate: a run that fixes eleven instances of one shape learns the shape, and the corrections
converge on one mechanism per deliverable instead of thirty unrelated edits.

## Goal

Every test named in this plan either goes red against the specific defect it exists to catch, or is
deleted, or is honestly re-documented as covering less than it claimed — and each of those outcomes
is backed by a recorded mutation reading, red before and green after, taken in this clone. The suite
stops reporting coverage it does not have, and a later reader sizing any of these guards from its
docstring or from a run report gets a figure the tree supports.

## Deliverables

Six deliverables. **D1 is gating**: if its premise fails, the run halts and reports, because every
*Done when* below is stated as a mutation reading and none of them can be discharged without it.

### D1 — The mutation-evidence protocol, and the baselines every other deliverable cites (GATING)

Establish, once, that a mutation can be applied to a tracked file, the affected suite run, and the
file restored byte-identically inside this clone; and record the protocol in the run report so every
later reading is reproducible.

The protocol is: snapshot the target file's bytes to the system temp dir (never into the repository,
never into `.plan/`), apply the named mutation, run the named test selection, record the exact
pass/fail line, restore from the snapshot, and verify `git status --porcelain` is clean for that
path. Every *Done when* in D2–D6 is a **red/green pair** taken this way: the fixed test red against
the defect it names, green after — both readings pasted into the run report.

⛔ **Stop condition.** If the suite cannot be run in this clone — the build gate reports the Python
toolchain unavailable, or a bare `python -m pytest` over one of the named directories cannot
collect — the run **halts**, records which command failed and its output, and reports the plan
blocked. Do **not** substitute reading for measurement: a plan whose entire value is proving that
guards can fail cannot discharge a single item by inspection, and a run that ships "verified by
reading" here has reproduced the defect class inside its own fix.

Re-derive, and record in the report, the baselines this plan quotes as leads — **do not trust the
numbers written here; the tree has moved.** The named baselines are: the test count for
`test/plan-marshall/manage-tasks/`, for `test/plan-marshall/audit-archived-plan-retrospectives/`,
for `test/pm-plugin-development/tools-marketplace-inventory/test_resolve_dependencies.py`, and for
`test/pm-plugin-development/tools-corpus-language-server/`.

**The prerequisite probe.** Six entries in D2–D6 pin behaviour whose production fix belongs to a
**sibling 5xx plan**, not to this one (they are named in § Out of scope). For each, the run reads the
named production symbol and applies this rule with no judgement:

- **Sibling fix present in the clone** → write the test; it must pass, and the mutation that removes
  the sibling fix must turn it red. Record both readings.
- **Sibling fix absent** → do **not** implement the sibling's production change. Write the test body
  into the run report verbatim under `HELD — prerequisite {source-plan}/gaps.md § Gn absent from the
  clone`, and do not add it to the suite. The report entry discharges the item.

*Done when:* the run report carries (a) the protocol as executed, including one worked example with
its snapshot/restore and its `git status --porcelain` check, (b) the four re-derived baselines with
the command that produced each, and (c) the six prerequisite-probe outcomes, each naming the symbol
read and the branch taken. If the stop condition fired, the report says so and the run is blocked.

### D2 — Shape 1: guards that derive their expectation from the thing they guard

Eleven sites where the oracle is not independent of the subject. The mechanism shared across all of
them: **replace the hand-built or self-referential stand-in with the real producer, or tie the two
registries together with a structural-equality assertion.**

The sites, with the defect and the observable fix:

- `test/pm-plugin-development/plan-marshall-plugin/test_path_attribution.py:131-132` — the final
  assertion reads back the test's own `print` with `len(files)` on both sides. Drop the
  self-referential assertion; publish the walked population through a channel pytest surfaces on a
  **passing** run (`record_property`, not a bare `print` — `capsys.readouterr()` drains the buffer,
  so even `-s` does not show it). *(`140-project-local-artifact-provider/gaps.md` § G1)*
- Same test, `:117` and `:144` — the walked population is a live `rglob`/`iterdir` over the working
  tree, so the published count moves with `__pycache__` and `settings.local.json` state. Derive it
  from the tracked corpus (`git ls-files .claude`) instead. No assertion weakens: every extra entry
  still resolves the same way. *(§ G7)*
- `test/plan-marshall/extension-api/test_path_attribution_merge.py:641-654` — the comment calls two
  `_StubAttributor` instances "the two real attributors" and "the shipped claims"; the real shipped
  set is larger and comes from three attributors. Correct the comment to say what the fixture is
  (the real merge over stub records) or drive the real attributors. *(§ G8)*
- `test/plan-marshall/build-gradle/test_gradle_rides_the_maven_join.py:125-128` — asserts
  `metadata['group_id'] and metadata['artifact_id']` on a dict the test's own helper hard-codes two
  lines above. Call the real `_extract_gradle_module`; ⛔ do **not** take the "it needs a Gradle
  daemon" escape — it receives `gradle_data` as a parameter and runs no subprocess, so a temp dir
  with an empty `build.gradle` plus a literal `gradle_data` dict is a complete hermetic call. Add
  the no-`group` case, which publishes no joinable coordinate.
  *(`210-native-coordinate-resolvers/gaps.md` § G7)*
- `manage-metrics.py`'s `DISPATCH_BOUNDARY_EXCLUDED_CLASSES` — the constant's preamble claims it is
  "Derived from the DISPATCHING code"; nothing enforces that, and the only guard asserts membership
  against the same hand-written literal. Add a structural-equality test that scans the bundle for
  `record-dispatch-boundary` invocations and derives the registering `--phase` set. The repository's
  own analogous lock-step guard for `DISPATCH_TERMINATION_CAUSES` is the shape to copy.
  *(`060-dispatch-boundary-ledger-is-not-a-commensurable-population/gaps.md` § G4)*
- `test_dispatch_boundary_ledger_population.py:195-220` — the test named
  `test_negative_control_dispatched_phase_shortfall_is_declared_not_silent` removes no registration;
  two of its three assertions hold for *any* report with a boundary surface. Implement the control
  the plan specified (remove a class's registration in a fixture copy and assert it appears in the
  rendered exclusion list) **after** the previous item lands, and rename the current test to what it
  actually checks. *(§ G5)*
- `execute-script.py.template`'s `_BUILD_CLASS_PREFIXES` versus `_cmd_client_build._BUILD_NOTATIONS`
  — no test relates the two, and a notation the executor can stamp but the architecture cannot
  classify blocks every pre-commit transition project-wide. ⚠ **Correction carried from adversarial
  review:** the two registries **agree exactly today** (four entries each; the "nine" in the
  original entry was the prefix-matching population, not the stampable one). This is a regression
  pin, not a present defect — say so in the test's failure message.
  *(`300-freshness-gate-cannot-distinguish-test-authored-evidence/gaps.md` § G9)*
- `_dep_detection.CANONICAL_COMMAND_PREFIXES` — its docstring says it "mirrors
  `_CANONICAL_VERIFY_PREFIXES`"; nothing ties them. Assert equality across the two modules using the
  existing path-loading helper so no import package is implied.
  *(`230-validate-precision/gaps.md` § G10)*
- `architecture-persistence.md` restates the `CONCEPT_TYPES` vocabulary verbatim; the shipped test
  checks only the code constant. Parse the accepted-types list out of the standard and assert
  set-equality. Anchor on a stable marker, not on line position.
  *(`150-architecture-store-concept-model/gaps.md` § G15)*
- `test_self_review_check_coverage.py:55,65-78` — the numbered-check block is extracted as
  "everything from the first `^\d+\.\s` line to the region end", an assumption stated in a comment
  and pinned by nothing. Assert over the **real** document that the extracted block's openers are a
  contiguous run and that no heading occurs inside it.
  *(`100-self-review-surfacing-integrity/gaps.md` § G10)*
- `test/plan-marshall/manage-tasks/test_qgate_closure.py:696` — `assert len(hits) <=
  _closure._MAX_HITS_NAMED` where `hits` is a live expansion of a production scripts directory, so
  adding files there turns an unrelated change into a hard red. Point the glob at a fixture
  directory the test creates, or monkeypatch the cap. **The margin is a lead — re-derive the current
  file count and cap; do not trust any number quoted for it.**
  *(`350-outline-derived-set-closure-integrity/gaps.md` § G11)*

*Done when:* for each of the eleven sites, the run report carries a red/green pair per D1 — the
mutation named in the bullet (or, where none is named, deletion of the production symbol the site
claims to guard) turns the fixed test **red**, and the unmutated tree turns it **green**. The two
`060-` items are landed in order (derivation guard first, negative control second); a report that
shows the negative control passing without the derivation guard in place has not discharged it.

### D3 — Shape 2: assertions weaker than the property they name

Thirteen sites where the assertion is true of both the correct and the defective state. The shared
mechanism: **assert the discriminating value directly** — the branch's own return, the prefix rather
than the whole string, the exact triple rather than one member of it.

- `test/conftest.py:116-132` (`_ensure_executor_present`) — **HIGH.** The bootstrap's only failure
  detection is `subprocess.run(..., check=True)`, and the generator's `main()` ends
  `print(serialize_toon(result)); return 0` with no branch on `result['status']`. `check=True`
  therefore cannot fire on **any** expected error: template-not-found, all four shape guards, the
  fail-open guard, and the unresolvable-base-path error all report `status: error` at exit `0`. The
  bootstrap returns having written nothing and raised nothing; downstream tests then fail with
  unrelated diagnostics or go vacuously green. Fix: drop `check=True`, capture stdout, and treat a
  non-success generation as the failure. Two acceptable mechanisms — (a) parse the TOON and branch
  on `status != 'success'`, (b) re-check `executor_path.exists()` after the subprocess returns.
  ⚠ **If (a) is chosen**, `_ensure_executor_present()` runs *before* `_setup_marketplace_pythonpath()`,
  so a bare `import toon_parser` raises `ImportError`; the fix must extend `sys.path` first, or use
  (b), or a plain `'status: error' in stdout` check. ⛔ **Do not make `main()` return non-zero** —
  `ref-workflow-architecture/standards/manage-contract.md` mandates exit `0` for an expected error
  and forbids it. ⚠ **Narrowing carried from adversarial review:** the fail-open guard specifically
  is *not* reachable through this bootstrap (it returns early when the executor already exists, so
  the previous-surfaces map is always empty). The gap stands on the other six refusal paths; a fix
  must not be sold the fail-open story. ⚠ **The original *Done when* was unsatisfiable** (it stubbed
  the generator in-process, which a `subprocess.run` cannot see) and is replaced below.
  *(`040-generator-fails-open-and-its-fixtures-cannot-see-it/gaps.md` § G1)*
- Same file, `:123` — the bootstrap allows the generator `timeout=120` while the generator's own
  default surface-derivation budget is `180.0` seconds before discovery, probe writing and the
  atomic write. Raise it above the budget with margin, or derive it from the budget constant, and
  state the coupling in a comment at **both** sites so neither can move without the other's comment
  becoming wrong. ⚠ **The consequence is a HYPOTHESIS, not a measurement** — the "four minutes under
  load" reading was taken in a shared tree running concurrent suites. The *static* inequality
  (120 < 180) is readable in git and is what the fix rests on. *(§ G14)*
- `test_generate_executor_behavior.py:372-507` — every fail-open assertion is on the returned dict;
  no test exercises the refusal through the CLI. Add one subprocess-level test asserting the
  observed triple — exit `0` **with** `status: error` **and** the `surface-stats:` line on stdout —
  beside the three existing exit-code tests, so the four state one contract together. A forcing
  recipe exists: stage a previous executor carrying one surfaces entry under a tmp tracked-config
  dir and set the surface budget to `0`. *(§ G2)*
- `test_resolve_dependencies.py:1432-1468` — the import-retarget guard's probe bundle is named
  `probe-bundle` while the mapped module targets a different bundle, so the candidate lookup misses
  on the *bundle* segment whether or not the guard exists. Rebuild the fixture so the mapped
  module's target bundle **is** the fixture bundle. **The corpus deltas quoted for this
  (`unresolved 61 → 50`) are leads — re-derive them; the `circular` count is explicitly not a stable
  witness in a shared tree.** *(`230-validate-precision/gaps.md` § G1)*
- `_dep_index.py:562-567` — the self-edge skip has no test; replacing it with `if False:` leaves the
  file green while the index gains edges and manufactures cycles. Add a case building a skill whose
  entry script cites its own notation, asserting no self-edge and no cycle containing it. **Assert
  on the branch, not on the edge-count figure**, which moves with the corpus. *(§ G2)*
- `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:5613-5616` — the
  `.get(check)`-not-`.get(check, 0)` guard survives its substitution across the whole suite
  directory. Add the pair of cases: a dict *missing* one registered check asserting `no_count` and
  an empty rendered signal, and the mirror where the dict carries `0` asserting `disciplinary`, so
  the two states are discriminated rather than one asserted alone.
  *(`290-auditor-detector-integrity/gaps.md` § G3)*
- `test_qgate_keyword_drift_reads_prose.py:147` — restoring the defect this test names leaves not
  only the file but the **entire owning bundle's suite** green, because a later plan widened
  `ambiguous = not parseable` to `not parseable or not population_complete` and the fixture trips
  the second disjunct. Assert the discriminating value directly (call the loader and assert
  `parseable is False`), or add a case whose task references no missing deliverable.
  *(`280-outline-plan-scope-derivation-integrity/gaps.md` § G6)*
- `test_lsp_harvest.py:421-448` — `test_every_failure_mode_states_a_distinct_reason` builds four
  fully-interpolated reason strings and asserts `len(reasons) == 4`; the strings already differ by
  an interpolated binary path, so two modes can share a *prefix* and the set still has four members.
  Collect `reason.split(':', 1)[0]` and assert the **prefix** set. ⚠ Derive the expected prefix set
  from the module's reason constants rather than hard-coding it, so a fifth failure mode landed by a
  sibling plan does not turn this red. *(`200-lsp-derivation-resolver/gaps.md` § G12)*
- `test_corpus_index.py:219-253` — both cache tests observe only that the cache is *written*: one
  compares the dict to itself, the other derives its verdict from what the cache *contains*.
  Deleting the cache **read** leaves the directory green. Count actual filesystem walks (wrap the
  walk or monkeypatch `rglob`) and assert it runs once across two calls on the same owner.
  *(`240-skill-lsp-server/gaps.md` § G5)*
- `test_corpus_lsp_protocol.py:53-57` — the docstring says "the next frame must still be readable",
  the body builds the next frame and never reads it. Read it and assert it parses.
  *(§ G6)*
- `test_manage_metrics.py:2156-2160` — the trailing loop asserts only `' of ' in line`, so two
  residuals sharing an identical bare label over an identical denominator (the exact prohibited
  state) pass it. Collect each rendered bullet's label and named denominator and assert both sets
  are duplicate-free and consistent with the render map.
  *(`030-attribution-populations-and-the-cost-decomposition/gaps.md` § G8)*
- `test_branch_cleanup_merge_queue_routing.py:589` — the predicate scans `tokenize` NAME tokens, so
  it silently finds nothing on any interpreter where an f-string is one STRING token. It goes
  **vacuous-then-red** rather than loudly wrong if the `requires-python` floor moves. Add the
  version assertion, or state the PEP 701 dependency in the predicate's docstring.
  *(`190-frozen-manifest-diverges-from-live-config/gaps.md` § G16)*
- `test_dispatch_waste_and_finalize_scope.py:15-21` — the module docstring specifies a stronger
  claim than the code makes ("a dispatch that … returned nothing"). Restate as terminal-error spend
  with the finding-yield proof deferred. *(`070-dispatch-spend-on-dispatches-that-produced-nothing/gaps.md` § G7)*

*Done when:* each of the thirteen carries a red/green pair per D1. Specifically: the conftest item is
settled by a test that drives the bootstrap **through the subprocess boundary** — stubbing the
generator in-process changes nothing the bootstrap can see — with the stub returning exit `0` and a
`status: error` payload, and asserts the bootstrap emits a warning carrying that error string. The
timeout item is settled by the two comments, each of which becomes wrong if the other number moves,
plus the report's re-derived reading of both constants.

### D4 — Shape 3: fixtures that reach the state by a route the test does not name

Eighteen sites where the test passes through a path other than the one its name or docstring
describes. The shared mechanism: **make the fixture take the named route, or rename the test to the
route it takes.** Both are acceptable outcomes; what is not acceptable is a name that survives while
describing a path nothing exercises.

- `test_freshness_notation_crosscheck.py:544-584` — **HIGH.** The control's docstring promises that a
  broken import path is "a test failure rather than a silent no-op". `resolve_expected_notations`
  imports the resolver by name, which consults `sys.modules` *before* any finder; a sibling test
  module loads the same module by absolute path and registers it under that same name, and is
  collected first in the real suite. **Reproduced end to end in adversarial review:** with a
  `meta_path` finder refusing the module *by name only*, the crosscheck file alone gives **1 failed**
  (the control fires) while the sibling-then-crosscheck invocation gives **fully green**. Fix by
  either (a) exercising the import in a clean interpreter (subprocess with a controlled `sys.path`)
  or (b) `monkeypatch.delitem` on `sys.modules` for the duration of the case, plus `register=False`
  in the sibling so it stops publishing a shared name it does not need. Then correct **both**
  docstrings — the control's own and the sibling's "the pair does" claim, which is false for the
  same reason. ⚠ **The original *Done when* was unreachable** (a cruder `sys.path` fault surfaces as
  a *collection* error in another file, never via this control) and is replaced below.
  *(`300-freshness-gate-cannot-distinguish-test-authored-evidence/gaps.md` § G8)*
- Same file, `:166` (autouse fixture) and `:563` — both stub the worktree seam with a retired
  boolean shape, so the consumer discards the value and resolves to the harness cwd rather than to
  the stubbed path. All tests in the module run through the autouse one. Replace with the shared
  `worktree_query_result(...)` helper, exactly as a sibling module already does. The verified
  positive control for completeness is the regex
  `grep -rnE "lambda [^:]*: *\((True|False) *," test/ --include=*.py`, which returns exactly these
  two lines today and nothing after the fix; ⛔ do **not** use the looser
  `_query_worktree_path`-plus-`(True,` form, which also matches the correct helper calls and can
  never go clean. *(`280-outline-plan-scope-derivation-integrity/gaps.md` § G1, § G2)*
- The same plan's run report claims *"Every stub SITE is covered, and the coverage is structural
  rather than per-file"* while those two sites are neither converted nor in its exclusion table.
  Amend the section to name both sites and replace the absolute coverage claim with one bounded by
  what the re-run sweep actually returns. *(§ G3)*
- `test_verify_failure_scope.py:316-346` — the test stubs the worktree query to **raise**, so it
  exercises only that route, while its docstring and failure message claim the broader property
  ("no diff is attempted at all"). Narrow the docstring to the route it covers — always doable — and
  add the `pending`-state case. **Prerequisite-probe item** (see D1): the `pending` case is only
  green once the sibling plan's production gate lands.
  *(`250-footprint-read-outside-its-window/gaps.md` § G6)*
- `test_npm_derivation_resolver.py:141-143` with `fixtures/workspace-monorepo/` — the no-fallback
  rule is stated normatively in three shipped documents, and mutating the resolver to fall back to
  the module's own name leaves the whole suite green, because no fixture package depends on the
  string a fallback would invent. Add that one dependency line to the fixture. **Measured safe in
  adversarial review:** with the line added the shipped code stays green and the mutant turns red;
  the shipped edge set does not change, so the existing exact-edge-set assertions stand.
  *(`210-native-coordinate-resolvers/gaps.md` § G5)*
- Same module, `:22-24` — the docstring's account of that fixture names a failure mode the fixture
  cannot exhibit. Rewrite it to name the dependency the previous item adds, in the same change.
  *(§ G6)*
- `test_graph_family_bundle_project.py:353-357` and the run-report row that wrote it — both claim "a
  developer's local binding would redden this". No test can see a developer's store: an **autouse**
  fixture redirects the plan base dir into a per-test tmp sandbox for every test, and the opt-out
  marker is locked shut. Reproduced: running the named file against a store disabling all shipped
  resolvers gives a fully green run. Rewrite both to state the real reason — the two quantities
  differ once a dispatch control exists — and, where the harness is mentioned, name the autouse
  sandbox rather than "a fresh clone and CI". The assertion the comment justifies is correct on its
  own merits and **stays**. *(`220-resolver-configuration/gaps.md` § G6)*
- `test_chat_provenance.py:63-83` — every pinned nesting case is *balanced*, which is why the
  unbalanced same-name hole survived twelve verification rounds and a 240-probe mutation campaign.
  Add predicate-level and verdict-level cases for **both** unbalanced shapes, naming the tag
  literally rather than iterating a constant, and include one case in the real nested-envelope shape
  — the flat one does not discriminate. **Prerequisite-probe item**: these cases are red until the
  sibling plan's pairing fix lands. *(`260-chat-signal-provenance-filter-under-inclusive/gaps.md` § G3)*
- `corpus_lsp.py:261-274` and `:292` — no test calls the document-sync handlers, so every test
  resolves through the file-read fallback and the synced-buffer branch never runs, although the
  capability set advertises sync. Add tests that open a buffer differing from disk, assert
  resolution from the buffer, then change and close it and assert the fallback resumes.
  *(`240-skill-lsp-server/gaps.md` § G9)*
- `fixtures/archived-plan/work/fragment-plan-efficiency.toon` — the fixture was renamed to the new
  key and nothing asserts the key name, so reverting the contract to the old key leaves the suite
  green. Assert the ratios block carries the new key and not the old one, and that totals carries
  its companion. Key on the identifier only — a prose-file assertion is brittle to rewording.
  *(`340-token-ledgers-disagree-and-the-smallest-is-named-actual/gaps.md` § G8)*
- `fixtures/archived-plan/work/fragment-log-analysis.toon` — the fixture stops short of the current
  section-4 contract, so the render path for the newer keys is exercised by nothing. Extend it and
  assert the rendered section names them. The fixture is shared: widening it can move assertions in
  sibling render tests, which is expected work, not a reason to stop.
  *(`270-aggregate-cost-invisible-to-per-call-ceiling/gaps.md` § G11)*
- `test_phase_handshake_findings.py` at `:9`, `:156-168`, `:171-183`, `:571`, `:574-591`,
  `:594-611`, `:614-634`, `:833`, `:868` — nine sites in one file whose test **names** and
  docstrings attribute guards to production boundaries that have no call site; the owning plan swept
  this claim out of six production and standards files and left the suite untouched. Rename and
  re-document each to the predicate it actually pins. ⚠ Two of the sites carry the claim in a test
  *name* and do **not** contain the word a keyword sweep would key on — a grep-only fix misses them.
  *(`110-blocking-boundary-arms-on-a-call-not-a-state/gaps.md` § G7, § G8, § G9, § G10)*
- `test_skills_by_profile_staleness_guard.py:4-11` — the module docstring describes a two-signal
  guard in the file whose own tests cover a third. Rewrite it to name all three.
  *(`160-empty-skill-resolution-indistinguishable-from-minimal/gaps.md` § G6)*
- `test_plan31_docs_only_deadlock_regression.py:150-155` — the docstring justifying a deliberate
  narrowing cites a build-tool subprocess the instrumented crawl does not issue. Keep the narrowing
  (the single `git` call alone justifies it) and delete the build-tool clause. ⛔ Do not describe
  that `git` call as a worktree-sha computation — its captured stack shows a main-checkout-root
  resolution, and writing it the other way ships a fresh invented rationale.
  *(`300-freshness-gate-cannot-distinguish-test-authored-evidence/gaps.md` § G4)*

*Done when:* every renamed or re-documented site names a route that exists, and every fixture change
carries a red/green pair per D1. For the two HIGH-adjacent items the readings are specific: the
crosscheck control must go from **fully green** to **at least one failure** under the two-file
invocation with the sibling collected first — not only when its own file runs alone; and the
retired-seam sweep regex above must return the two lines before and nothing after.

⛔ **Cold read required.** Four items here are *text whose whole value is what a later reader does
with it* — the two corrected docstrings on the crosscheck pair, the resolver-comment rationale, and
the nine renamed handshake tests. Verification (below) dispatches an independent reader for these.

### D5 — Shape 4: populations that are empty, degenerate, or invisible

Fifteen sites where the check runs over a population that cannot exhibit the defect, or publishes a
size no reader ever sees. The shared mechanism: **publish the population through a channel a green
run surfaces, and widen or correct the population — or state plainly, in the docstring and in the
output, what the check does not cover.**

- `test_population_derived_surface_guard.py:177-182` — the help-check majority of the corpus cannot
  fail for any derivation reason, because the validator short-circuits on a help spelling before
  reading the surface. The audit measured `help_checks=1750` of `2412` (72.6%) with **0** help
  refusals in all eight per-attribute strip runs, and reddening on exactly two of the seven
  serialized attributes — **re-derive the split by re-running the partitioned mutation; the corpus
  moves with the registered script set.** ⚠ **This entry has two
  defensible remedies and the run must not choose between them mid-flight.** Implement remedy (b) —
  keep the checks as a regression net, rename and re-document them as such, and publish the two
  counts separately — because it is deterministic and cannot destabilise the suite. **Record remedy
  (a)** (route the help spellings through a surface-consulting path) as a written proposal in the
  run report, with the reason it is not taken here: it may surface genuine fail-open behaviour that
  needs triage before it can land. *(`040-generator-fails-open-and-its-fixtures-cannot-see-it/gaps.md` § G11)*
- Same file, `:197-202` — the population count is emitted by a bare `print`, and the repository's
  own pytest flags carry no `-s` and no `-rA`, so a green run shows nothing. Emit it through a
  channel a pass surfaces and name that channel in the docstring. The only automatic backstop today
  is a floor of half the registered count, so a silent shrink to that floor passes green and
  invisible. *(§ G12)*
- Same file, `:20-22` and `:131-134` — the module docstring claims "a derivation that drops an
  attribute fails a test here". Narrow it to the two attributes that actually redden, and list the
  five that do not **with the reason each is invisible**. Mirror the correction into the owning run
  report's finding row. *(§ G13)*
- `test_self_review_check_coverage.py:103,110` — the signature requests `capsys` and never uses it;
  the population is emitted by a discarded `print`. Same fix as the second item above, and remove
  the unused fixture. *(`100-self-review-surfacing-integrity/gaps.md` § G6)*
- `test_dispatch_roster_closure.py:256-281` — the seam-pairing sweep reads one file and blanks every
  line outside one section, so two real out-of-section violations are invisible to it while the
  detector itself is alive (mutating an in-section line does turn it red). Extend the population to
  every markdown file under the finalize skill, keeping the per-file section scoping that avoids the
  documented false positive and keeping both mutation guards. **Prerequisite-probe item**: widening
  the population turns the suite red until the sibling plan fixes the two violating sites.
  *(`180-finalize-dispatch-manifest-observability/gaps.md` § G5)*
- `test_dispatch_seam_emission.py:144-173` — `test_finalize_dispatch_emits_one_line_per_spawn` reads
  no finalize document and passes against the very document mutation it claims to catch; its
  in-tree comments assert the opposite. Delete it and point the verification at the roster-closure
  check that genuinely holds the property. ⛔ Its sibling `test_role_fired_n_times_produces_n_records`
  must survive — do not delete both. *(§ G7)*
- `test_dispatch_roster_closure.py:197,420-443,797-816` — the roster-correctness check derives its
  population from the registry (the audit read 26 implementor docs against 25 registered steps —
  **re-derive both by calling the module's own helpers; do not trust these figures**) and then
  compares **one** of them, because only one doc carries the prose sentence the detector matches.
  ⚠ **This needs a decision the run must not make.** The
  preferred remedy adds a required machine-readable classification fact to the finalize-step
  extension-point frontmatter contract — a contract change affecting implementor docs in *consumer*
  projects outside this repository, which the lane forbids self-approving. So: **record the proposal**
  in the run report (both options, the migration hazard, and the excluded discovered-but-unregistered
  doc), and land only the non-contract half here — a coverage assertion that reports, without
  failing, how many registered steps contribute a comparison. *(§ G11)*
- Same file, `:436-441` — the helper hard-asserts that every self-classifying discovered doc
  resolves to a registered key. The unregistered doc is dormant only because it does not currently
  self-classify; the moment it gains the sentence the suite fails with a message about frontmatter
  resolution rather than the real condition. Downgrade to a collected finding naming registry
  absence. ⛔ A silent skip is not the fix — the reported finding is the load-bearing half.
  *(§ G9)*
- `test_registered_aspects_render.py:321-404` — the correspondence is checked in one direction only,
  and the class docstring says so; two registry rows exist with no table row, which is exactly why
  the reverse assertion was not shipped. Add the reverse assertion **with no exemption list**.
  **Prerequisite-probe item**: adding it before the sibling plan resolves those two rows would
  require encoding them as exemptions, which pins them in place — do not.
  *(`330-retrospective-report-sections-structurally-dead/gaps.md` § G9)*
- `test_feasibility_underivable_guard.py:85-93` — the test defines the guard locally and never opens
  the standards document it is supposed to protect; deleting the entire guard block from that
  document leaves the test green. Read the document and assert both arms. Anchor on the stable
  tokens, not on whole sentences. Precedent exists in the same skill.
  *(`130-lsp-shaped-query-api/gaps.md` § G4)*
- `plan-retrospective/SKILL.md` Step 2.5 — the deliverable's entire shipped change is a prose step;
  the test named for it drives the command directly and never reads the document, so deleting the
  step leaves the suite green. Add a document-contract test asserting the invocation is present and
  positioned before the aspect that consumes it, and that the surrounding conditions still stand.
  Anchor on the command string and the ordering, not on headings.
  *(`050-post-run-band-contract-and-ordering-residue/gaps.md` § G7)*
- `phase-6-finalize/SKILL.md`'s step-5c classification contract — no test in the owning directory
  reads it, so editing the table back to the old routing silently reverts the deliverable with every
  test green. Add a document-contract test; two shipped tests in that same directory already
  validate markdown contracts in that same file and are the shape to follow.
  *(`070-dispatch-spend-on-dispatches-that-produced-nothing/gaps.md` § G5)*
- `_cmd_client_handlers.py:1090` and `:1245` — the claimed-path collapse is called at two sites and
  replacing **both** with `pass` leaves the covering directories green, because the unit test
  monkeypatches the attribution resolver and the integration fixture carries no claim, making the
  collapse a deliberate no-op there. Seed a project whose crawled module set genuinely contains both
  a root and a documentation module, and assert one row per physical doc file for the first site and
  the `count`/`file_count` convergence for the second. ⚠ Note the fixture constraint recorded by the
  audit: the crawl reads the live worktree and ignores a fixture's declared module set, so seeding
  alone is insufficient — the tmp tree must make both modules discoverable, or the resolver must be
  injected. *(`120-documentation-surface-provider/gaps.md` § G5, § G6)*
- `test_audit_check_global_log_analysis_cost_rollup.py:71` — the reconciliation test's inputs round
  cleanly at the published precision, so it passes either way; changing the rounding leaves the
  whole tree green. Add a case whose total does **not** round cleanly and assert every row's share
  against the recomputed value. **Prerequisite-probe item**: the sub-decisecond assertion is green
  only once the sibling plan publishes the denominator at the precision its shares are computed
  against. *(`270-aggregate-cost-invisible-to-per-call-ceiling/gaps.md` § G3)*

*Done when:* every widened population carries a red/green pair per D1; every published count is
visible in the output of a **default** pytest invocation on a **passing** run (repo `addopts`
applied, no extra flags) and its channel is named in the owning docstring; and every narrowed claim
enumerates what it does *not* cover, with the reason. The two record-a-proposal items are discharged
by the proposal being written, not by the change being made.

⛔ **Cold read required** for the three narrowed-claim docstrings (the surface-guard module
docstring, the roster-coverage assertion's message, and the one-direction correspondence note): their
value is entirely in stopping a later reader from over-crediting the guard.

### D6 — Shape 5: production behaviour with no direct test at all

Sixteen sites where a branch, a verb, a field or a documented guarantee has no executable coverage,
while a run report or a docstring records it as covered. The shared mechanism is the plainest one:
**write the missing test, or delete the untested guard and keep only the reason it is unnecessary.**

- The fail-closed identity check in the skills-by-profile staleness guard — weakening `is True` to a
  truthy test is caught nowhere in the owning suite, although a non-boolean value is reachable on
  disk. Assert that non-boolean truthy values still surface the condition and only boolean `True`
  silences it. *(`160-empty-skill-resolution-indistinguishable-from-minimal/gaps.md` § G4)*
- The emitter beside it (`_emit_skills_by_profile_staleness_warning`) is referenced by no test at
  all, although it holds every branch that decides whether the condition reaches anyone. Assert the
  emitted message list per branch and that no exception escapes. *(§ G5)*
- The sparse-ratio confidence branch in the dispatch-audit check — the three confidence tests all
  reach their verdicts through *other* branches, so disabling this one leaves the file green. Add a
  sparse-but-nonzero case and the boundary case that pins the strict comparison.
  *(`170-finalize-dispatch-evidence-is-missing/gaps.md` § G6)*
- The corpus language server's enabled `query` and `preflight` verbs — the only tests for them are
  on the disabled path, so the payload contract three shipped documents describe is unpinned. Assert
  the documented keys over the existing synthetic corpus fixture.
  *(`240-skill-lsp-server/gaps.md` § G7)*
- The same server's `corpus_path` field and its missing-corpus degradation branch — a documented
  configuration field with a documented degradation state, and no test sets it. Add the resolving
  case and the non-existent-path case. *(§ G8)*
- The LSP `edit` verb's multi-file path — the only two-file exercise in the suite calls a pure
  helper and never touches the verb, the diagnostics loops, or the footprint that reaches the
  payload. Add a real-server test renaming a symbol used across two modules, asserting the file
  count, the exact path set, that both files changed, and that no third was touched; plus the
  fake-transport mirror for the rollback direction.
  *(`010-lsp-in-execute-lookup-and-write/gaps.md` § G6)*
- The harvest's truncation flag — deleting `truncated = True` leaves both plan test files green, so
  a partial harvest reported as complete regresses silently. Drive the harvest to expire mid-file
  and assert the budget note; add the out-of-workspace note case. ⛔ Drive the deadline
  deterministically (monkeypatch the clock) — a sleep-based test flakes.
  *(`200-lsp-derivation-resolver/gaps.md` § G8)*
- The `lsp` dependency kind is absent from the detection enum the sibling resolvers derive their
  ignore-populations from, so none is asserted to ignore it. Either add the member (check the enum's
  iteration sites first) or hard-code the kind into each sibling's ignore test. *(§ G9)*
- The widened import guard in the freshness cross-check — narrowing `except Exception` back to
  `except ImportError` leaves the owning directories green, although the narrowed clause would hand
  the gate a traceback instead of a status payload on a deployment fault. Make the *import* raise a
  non-`ImportError` and assert both the resolver's return pair and, at gate level, the
  never-raises verdict. **Independently reproduced in adversarial review**, baseline re-derived
  before mutating. *(`300-freshness-gate-cannot-distinguish-test-authored-evidence/gaps.md` § G6)*
- The non-container guard on the same resolver's return value is unreachable from any test — every
  stub returns the right container or raises. **Either** add the one-line case **or** remove the
  guard and keep the comment explaining why the single return makes it unnecessary; both are
  observable, so the run picks whichever leaves the file smaller and says which it picked. *(§ G7)*
- The executor-refresh seam's "non-fatal by contract" property is a two-part claim and only the
  failing-return-code half is pinned; no test makes the seam raise. Add the raising case.
  **Prerequisite-probe item**: it is red until the sibling plan widens the `except` clauses.
  *(`190-frozen-manifest-diverges-from-live-config/gaps.md` § G5)*
- The absent-denominator render fallback in `manage-metrics` — the one place a residual renders
  *without* a denominator, whose exact wording is what makes the omission legible rather than a
  silent bare label, and no test reaches it. Write a metrics row missing the denominator field and
  assert the disclosure. *(`030-attribution-populations-and-the-cost-decomposition/gaps.md` § G9)*
- The unresolved-key WARNING in the architecture core is wrapped in a bare `except Exception: pass`
  and observed by nothing, so the "never silently dropped" guarantee rests on a log call that
  swallows its own failure. Assert the warning is emitted with the key named. The import is deferred
  inside the function, so patch the source module, not a module-level name.
  *(`150-architecture-store-concept-model/gaps.md` § G16)*
- The `capabilities` verb's leaf-context verification, which the owning plan required and the run
  substituted a proxy for. ⚠ Authored as an **either/or with a guaranteed arm**: attempt the
  dispatched-leaf reading and commit the payload beside the orchestrator's if it can be obtained;
  **otherwise** write the reasoning into the client-api standard (the answer is a pure function of
  the project dir plus the producers that ran, therefore independent of the harness tool grant) and
  close the constraint explicitly. The second arm is always available.
  *(`130-lsp-shaped-query-api/gaps.md` § G7)*
- A run-report residue item claiming "38 tests fail when several test directories share one ad-hoc
  invocation". ⚠ **HYPOTHESIS — the claim did not reproduce.** Three multi-directory invocations
  during adversarial review were clean of that mode, and the one failure found was unrelated and
  reproduces when its file runs alone. Authored as a lead to **re-measure, not as an established
  fact**: record the invocations tried and their outcomes, and either name a reproducing invocation
  or strike the residue item. The named legacy files do still bind the patched module at import
  time, so if the item is struck, note that the hazard's precondition remains.
  *(`220-resolver-configuration/gaps.md` § G7)*
- The gate-decision channel has never been exercised against a real transcript — across the reachable
  corpus not one qualifying tool-use block exists, so the channel's count is zero corpus-wide.
  ⚠ **This entry is contingent on an input that does not exist**, and the corpus it would come from
  is machine-local and invisible to a cloud clone. The run must **not** substitute another
  hand-built fixture, which would add nothing. Discharge it by recording the entry as **blocked**,
  naming what input would unblock it. *(`260-chat-signal-provenance-filter-under-inclusive/gaps.md` § G8)*

*Done when:* each added test carries a red/green pair per D1 — the production branch, verb, field or
flag it covers is removed or neutralised, the test goes red, and the restored tree turns it green.
The three non-test items (the delete-or-cover choice, the capabilities either/or, and the two
recorded-as-blocked / re-measured entries) are discharged by the run report stating which arm was
taken and why, with the reading that decided it.

## Out of scope

Each exclusion states its reason, because the run has no operator to ask.

- **The production fixes that six of these tests pin.** Named individually: the verify-failure
  footprint gate, the envelope-pairing hole, the published-denominator precision, the two unmigrated
  finalize dispatch sites, the two dead retrospective registry rows, and the executor-refresh
  `except` widening. *Reason:* every one is a deliverable of a **sibling 5xx plan** authored from the
  same audit; implementing them here would produce two plans changing the same production symbol
  concurrently, and the merge conflict would land on whichever ran second. The prerequisite probe in
  D1 is how this plan behaves correctly whichever order the two run in.
- **Any change to the finalize-step extension-point frontmatter contract.** *Reason:* it governs
  implementor documents in consumer projects outside this repository, so a required new fact breaks
  their builds until they migrate; and the lane forbids a run self-approving a change to a contract
  that governs it. D5 records the proposal instead.
- **Routing the surface-guard's help checks through a surface-consulting path** (remedy (a) of the
  72.6% item). *Reason:* the audit recorded that it may surface genuine fail-open behaviour in the
  resolver that is currently masked, producing new failures that need triage before the change can
  land — which is a separate piece of work, not a test fix. The proposal is recorded.
- **Every non-`tests` gap the audit filed against these same 30 plans** — the architecture-core
  defects, the measurement corrections, the bundle-documentation sweeps, the report-defect
  corrections that do not touch a test file. *Reason:* they are the scope of the other 5xx plans; a
  plan that reaches into them stops being reviewable as one thing.
- **Timing, throughput and duration figures as facts.** *Reason:* every such number in this audit was
  taken in a working tree shared with sibling agents running full suites, and re-measurement under
  deliberate CPU contention reproduced the anomalous readings almost exactly. Where a gap's evidence
  is a duration, this plan carries the *static* fact and authors the duration as a lead.
- **Refactoring or restructuring any test module beyond the change its entry names.** *Reason:* the
  value of every item here is a red/green pair on a named defect; collateral restructuring makes the
  pair unattributable and the review unbounded.

## Expected surface

Test files (the bulk of the change):

- `test/conftest.py` — the executor bootstrap's failure detection and its timeout (D3).
- `test/plan-marshall/manage-tasks/` — the crosscheck control and its seam stubs, the qgate
  discrimination and closure precondition (D3, D4, D5).
- `test/plan-marshall/tools-script-executor/` — the surface-guard population, its docstring, the
  generator's exit-status contract (D3, D5).
- `test/plan-marshall/phase-6-finalize/` — roster closure, seam pairing, the tokenizer predicate (D3, D5).
- `test/plan-marshall/manage-metrics/` — the exclusion-constant derivation, the negative control, the
  render guards (D2, D3, D6).
- `test/plan-marshall/manage-architecture/` — the staleness guard, the feasibility guard, the
  claimed-path collapse, the concept vocabulary (D2, D5, D6).
- `test/plan-marshall/plan-retrospective/` — provenance nesting, the aspect-table correspondence, the
  archived-plan fixtures, the dispatch-audit ratio branch (D3, D4, D5, D6).
- `test/plan-marshall/plan-marshall/test_phase_handshake_findings.py` — nine renames (D4).
- `test/plan-marshall/build-npm/`, `test/plan-marshall/build-gradle/` — the resolver fixtures (D2, D4).
- `test/plan-marshall/audit-archived-plan-retrospectives/` — the census unread-count pair, the
  share/denominator reconciliation (D3, D5).
- `test/plan-marshall/lsp-client/`, `test/plan-marshall/extension-api/`,
  `test/plan-marshall/workflow-integration-git/`, `test/plan-marshall/manage-config/`,
  `test/plan-marshall/phase-5-execute/`, `test/plan-marshall/manage-execution-manifest/` — one or two
  items each.
- `test/pm-plugin-development/` — path attribution, the LSP harvest, the dependency index and the
  corpus language server (D2, D3, D4, D6).

Non-test files, all small and all named by an item above:

- `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py` — the
  exclusion constant's derivation or its source annotation.
- `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` — the
  non-container guard, if the delete arm is taken.
- `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template`
  — the cross-reference comment on the build-class prefix set.
- `marketplace/bundles/plan-marshall/skills/manage-architecture/standards/client-api.md` — the
  `capabilities` constraint paragraph, if the second arm is taken.
- `test/plan-marshall/build-npm/fixtures/workspace-monorepo/package.json` and the archived-plan
  fixtures under `test/plan-marshall/plan-retrospective/fixtures/` — one line and two blocks.
- `doc/plans/code-intelligence-substrate/{280,220,180,040}-…/report-01.md` — four coverage claims
  corrected in place or by appended note.

⚠ **Surface overlap to expect.** `client-api.md` and the manage-architecture render/query scripts are
also touched by the architecture-store and documentation-surface sibling plans; the finalize skill
documents by the dispatch-observability plan. This plan's edits there are additive comments and one
paragraph, so a conflict is a rebase, not a redesign.

## Claim labels

Every premise below is a claim about a tree that will have moved. Confirm/refute artifacts are
git-tracked paths reachable from a fresh clone.

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The two HIGH defects reproduce: the conftest bootstrap cannot detect a failed generation, and the crosscheck control stays green under the two-file invocation | OBSERVED | `test/conftest.py` § `_ensure_executor_present`; `test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py` § the live-resolution case, plus the sibling `test/plan-marshall/manage-architecture/test_project_build_notations.py` module-scope load |
| The fail-open guard specifically is unreachable through the conftest bootstrap (it returns early when the executor exists) | OBSERVED | `test/conftest.py` § the early return in `_ensure_executor_present`; `generate_executor.py` § `read_previous_surfaces` and the guard predicate |
| The generator's `main()` returns `0` on every expected error, and the repository's contract standard forbids changing that | OBSERVED | `generate_executor.py` § `main`; `ref-workflow-architecture/standards/manage-contract.md` § the three-tier exit model |
| Each named test survives the mutation named beside it (the eleven D2 sites, thirteen D3 sites, and the mutation-proved subset of D4/D5) | OBSERVED | Each cited test file and the production symbol named in its bullet; every one was re-derived by execution in the audit **and** in its adversarial re-review |
| The npm fixture line is safe: shipped code stays green, mutant turns red, exact-edge-set assertions unchanged | OBSERVED | `test/plan-marshall/build-npm/fixtures/workspace-monorepo/package.json` and `test_npm_derivation_resolver.py`; measured by applying the change in adversarial review |
| The build-class registries currently agree exactly, so the new assertion passes on the present tree | OBSERVED | `test/_shared/_build_class_roster.py`; `_cmd_client_build.py` § the notation map |
| Raising the conftest timeout prevents real bootstrap kills | HYPOTHESIS | The two constants (`test/conftest.py` and `generate_executor.py` § the default surface budget) settle the *inequality*; the failure it causes was observed once in a contended shared tree and must be re-measured, or the fix carried on the inequality alone |
| The "38 tests fail across shared directories" residue is real | HYPOTHESIS | `doc/plans/code-intelligence-substrate/220-resolver-configuration/report-01.md` § Residue, and the two named test modules — re-run the multi-directory invocations and record the outcome; adversarial review could not reproduce it |
| No reachable transcript carries a real gate-decision exchange (an asserted **absence**) | HYPOTHESIS | `test/plan-marshall/plan-retrospective/fixtures/` and `_plan_retrospective_fixtures.py` are git-reachable and can be read; the transcript corpus itself is **machine-local and invisible to a cloud clone**, so this claim cannot be settled here — which is why the item is authored to be recorded as blocked rather than fixed |
| The corpus-derived counts quoted anywhere in this plan (unresolved findings, edge totals, file counts, cap margins, test-suite baselines) | HYPOTHESIS | Every one is a **lead**. D1 re-derives the four named baselines; every other figure carries "re-derive it" in its own bullet. Do not trust a number written here |

⛔ Note on the gap citations: entries are cited as `{source-plan}/gaps.md § Gn`, relative to
`doc/plans/code-intelligence-substrate/`. Those files are git-tracked and on `main` today — but a
landed cloud plan's directory is deleted at collect, so they may be **gone** by the time this runs.
Every item above therefore restates its defect, its file and its observable fix inline; the citation
is corroboration, never required reading. If a cited path does not exist, proceed from this plan's
own text and note the absence in the report.

## Verification

Beyond the per-deliverable *Done when* conditions:

1. **The mutation ledger.** The run report carries one table row per item: source-plan and gap id,
   the file changed, the mutation applied, the red reading, the green reading, and the
   `git status --porcelain` check after restore. **A row with no red reading has not been
   discharged** — it is reported as such, not counted as done. This table is the only evidence that
   this plan did anything, because every fix here is invisible to a passing suite by construction.
2. **Whole-suite regression.** Run the build gate as the lane requires, and additionally run each
   named test directory alone **and** in the multi-directory combination that the audit used, since
   two of the defects in this plan are *collection-order* effects that a per-file run cannot see.
   Report both.
3. **Prerequisite-probe accounting.** The report states, for each of the six probe items, which
   branch was taken and the symbol read to decide it. A held item is listed with its verbatim test
   body and the sibling plan it waits on.
4. **Independent cold read of the interpretation-bearing text.** Dispatch the lane's pre-PR
   verification sub-agent with a second, separate instruction: read — cold, without this plan —
   the corrected docstrings on the crosscheck control and its sibling, the rewritten resolver-comment
   rationale, the nine renamed handshake tests, the narrowed surface-guard module docstring, the
   roster-coverage message, and the one-direction correspondence note; and **report, for each, what
   coverage the text claims and what it disclaims.** If the reader credits a guard with coverage the
   tree does not have, the wording failed however complete it looks — fix the wording and re-read.
   This is the check that matters: every one of these texts exists to stop a later reader
   over-crediting a guard, which is the defect that produced this plan.
5. **Proposals, not decisions.** The report contains the two written proposals (the frontmatter
   classification contract, and the surface-consulting help-check remedy) with their options, their
   risks and the reason each was not taken here. A proposal that reads as a decision taken is a
   defect in the report.
6. **Self-check on the plan's own shape.** Confirm that no fix in this plan reproduces a shape it
   fixes: no new assertion derives its expectation from the code it guards, no new count is
   published only to captured stdout, no new population is scoped to one file when the property
   spans many, and no new docstring claims coverage the mutation ledger does not show.

## Notes

**Where this came from.** A ground-truth audit of this epic's 36 landed plans, adversarially
re-reviewed. Where a gap entry and its adversarial review disagreed, **the review won** — it was the
later, evidence-bearing pass — and three of its corrections are carried into this plan explicitly:
the conftest bootstrap's mechanism was re-argued over the six refusal paths it *can* hide (the
fail-open guard is not one of them); the crosscheck control's *Done when* was replaced because the
original was unreachable as written; and the build-class registry entry was corrected from "five
divergent notations" to "the two registries agree exactly, so this is a regression pin". Two further
entries had their *Done when* rewritten here for the same reason, and both say so in place.

**Sequencing.** This plan is **order-independent by construction** but not conflict-free:

- It must not be read as blocked on any sibling. The six items whose production fix belongs to
  another 5xx plan are handled by the D1 prerequisite probe, which produces a correct outcome
  whichever order the two plans run in. If this plan runs first, six tests are held with their
  bodies recorded; if it runs second, they land green with their mutation pairs.
- It **should not run concurrently** with the plans owning the architecture-store query surface, the
  documentation-surface sweep, or the finalize dispatch observability work, because all four touch
  `client-api.md`, the manage-architecture scripts, or the finalize skill documents. The overlap is
  small (comments and one paragraph here) so a conflict is a rebase; but a run that finds those
  files already modified should rebase rather than force.
- Nothing in this plan supersedes another plan's fix, and nothing here should be deferred in favour
  of one. The value of an anti-vacuity fix is highest **before** the production fix it pins lands,
  because that is when the red reading is obtainable.

**Why the mutation evidence is non-negotiable.** Every defect in this plan is a test that passes.
Every fix is a test that still passes afterwards. The *only* observable difference between the two
states is what happens under a mutation — so a run that lands these changes without recording
red/green pairs has produced a diff no reviewer, and no later reader, can distinguish from a no-op.
That is why D1 is gating and why its stop condition is a halt rather than a fallback.

**No fallback to hand-maintenance.** Two items replace a hand-written literal with a derived one
(the exclusion constant, the classification roster). Where the derivation cannot be made to work, the
correct outcome is to **say so and stop on that item** — not to keep the literal and add a test that
asserts the literal against itself, which is the shape this whole plan exists to remove.

## Gap coverage

73 gaps: 2 high, 41 medium, 30 low. Paths are relative to `doc/plans/code-intelligence-substrate/`;
each is cited as `{source-plan}/gaps.md § Gn`. Both high-severity gaps are carried, none is out of
scope.

| Deliverable | Gaps discharged |
|---|---|
| **D1** (gating protocol) | none directly — it is the precondition for every reading below |
| **D2** (guard derives its own expectation) | `140-project-local-artifact-provider` § G1, § G7, § G8 · `210-native-coordinate-resolvers` § G7 · `060-dispatch-boundary-ledger-is-not-a-commensurable-population` § G4, § G5 · `300-freshness-gate-cannot-distinguish-test-authored-evidence` § G9 · `230-validate-precision` § G10 · `150-architecture-store-concept-model` § G15 · `100-self-review-surfacing-integrity` § G10 · `350-outline-derived-set-closure-integrity` § G11 — **11** |
| **D3** (assertion weaker than the property) | `040-generator-fails-open-and-its-fixtures-cannot-see-it` § **G1 (HIGH)**, § G2, § G14 · `230-validate-precision` § G1, § G2 · `290-auditor-detector-integrity` § G3 · `280-outline-plan-scope-derivation-integrity` § G6 · `200-lsp-derivation-resolver` § G12 · `240-skill-lsp-server` § G5, § G6 · `030-attribution-populations-and-the-cost-decomposition` § G8 · `190-frozen-manifest-diverges-from-live-config` § G16 · `070-dispatch-spend-on-dispatches-that-produced-nothing` § G7 — **13** |
| **D4** (fixture takes a route the test does not name) | `300-freshness-gate-cannot-distinguish-test-authored-evidence` § **G8 (HIGH)**, § G4 · `280-outline-plan-scope-derivation-integrity` § G1, § G2, § G3 · `250-footprint-read-outside-its-window` § G6 · `210-native-coordinate-resolvers` § G5, § G6 · `220-resolver-configuration` § G6 · `260-chat-signal-provenance-filter-under-inclusive` § G3 · `240-skill-lsp-server` § G9 · `340-token-ledgers-disagree-and-the-smallest-is-named-actual` § G8 · `270-aggregate-cost-invisible-to-per-call-ceiling` § G11 · `110-blocking-boundary-arms-on-a-call-not-a-state` § G7, § G8, § G9, § G10 · `160-empty-skill-resolution-indistinguishable-from-minimal` § G6 — **18** |
| **D5** (population empty, degenerate or invisible) | `040-generator-fails-open-and-its-fixtures-cannot-see-it` § G11, § G12, § G13 · `100-self-review-surfacing-integrity` § G6 · `180-finalize-dispatch-manifest-observability` § G5, § G7, § G9, § G11 · `330-retrospective-report-sections-structurally-dead` § G9 · `130-lsp-shaped-query-api` § G4 · `050-post-run-band-contract-and-ordering-residue` § G7 · `070-dispatch-spend-on-dispatches-that-produced-nothing` § G5 · `120-documentation-surface-provider` § G5, § G6 · `270-aggregate-cost-invisible-to-per-call-ceiling` § G3 — **15** |
| **D6** (no direct test at all) | `160-empty-skill-resolution-indistinguishable-from-minimal` § G4, § G5 · `170-finalize-dispatch-evidence-is-missing` § G6 · `240-skill-lsp-server` § G7, § G8 · `010-lsp-in-execute-lookup-and-write` § G6 · `200-lsp-derivation-resolver` § G8, § G9 · `300-freshness-gate-cannot-distinguish-test-authored-evidence` § G6, § G7 · `190-frozen-manifest-diverges-from-live-config` § G5 · `030-attribution-populations-and-the-cost-decomposition` § G9 · `150-architecture-store-concept-model` § G16 · `130-lsp-shaped-query-api` § G7 · `220-resolver-configuration` § G7 · `260-chat-signal-provenance-filter-under-inclusive` § G8 — **16** |

Six items are **prerequisite-probe** items (D1's rule decides whether they land or are held):
`250-…` § G6, `260-…` § G3, `270-…` § G3, `180-…` § G5, `330-…` § G9, `190-…` § G5.

Three items are discharged by a **written record** rather than a code change, and are complete when
the record exists: `180-…` § G11 (contract proposal), `040-…` § G11 (remedy proposal),
`260-…` § G8 (recorded blocked), plus `220-…` § G7 (re-measured, then confirmed or struck).
