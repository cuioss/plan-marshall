# PLAN-TRUTH-122: The Maven signal lies in both directions — a canonical that cannot pass, and a count that cannot add up

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-TRUTH-122-the-maven-signal-lies-in-both-directions-a-canonical-that-cannot-pass-and-a-count-that-cannot-add-up.md`
> and is queued in the epic `status.json` `plans[]` field. The orchestrator EMITS the command below;
> it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief, so
> every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-02 from the `truthful-signals` inbox drain — message
`refresh-identity-and-scope-defences-001.md` (`kind: candidate-lesson`, `component: plan-marshall:build-maven`,
`confidence: high`). Both defects were **reproduced first-party by the plan that filed them, during a single
build, in the same skill**, and neither was in that plan's scope. The sender's in-plan workaround was to
abandon the `module-tests` canonical entirely (`per_deliverable_build` switched to `default:verify:verify`).

⭐ **Every mechanism claim below was re-corroborated by the orchestrator at HEAD `30cd8aaf8` before this
spec was staged** — line numbers and code shapes are read from this tree, not carried from the message.
The one class of claim the orchestrator could NOT settle is the foreign-repo observation
(`cuioss/TokenSheriff`), which is labelled as such under Claim Labels and must be re-established or
dropped at outline. ⛔ Do not scope on the TokenSheriff repro as if it were first-party.

## Objective

Two build signals in `build-maven` are wrong in **opposite directions**, and the pairing is the subject:
one manufactures a red from working code, the other under-reports a green by two orders of magnitude. A
consumer cannot tell either from the real thing, and the second one silently punishes the only available
workaround for the first.

⭐ **Why they are one plan and not two.** They are not merely archetype-siblings — this epic has recorded
archetype-grouping across unrelated surfaces as a staging error. These two are **the same skill, the same
build, the same run**, and they interact causally: a project that works around D1 by switching from
`module-tests` to `verify` runs strictly MORE tests and reports FAR FEWER, which reads as a regression and
pushes the operator back toward the broken canonical. Fixing either alone leaves that trap armed. ⚠ If
outline finds the two surfaces genuinely disjoint after D0's sweep, **split rather than stretch**.

## Deliverables

Four deliverables, under the epic's split guard. D0 is a gate.

**D0 — GATE: derive the POPULATION of both defects before fixing either instance.** Two sweeps, two
published counts, neither restated as a literal:

- *(a) The last-match test-count premise.* The shared helper
  `script-shared/scripts/build/_build_parse.py:596` `extract_test_summary` takes `matches[-1]` and
  **documents the reason in its own docstring**: *"Uses the LAST match in content (build tools often emit
  per-module summaries; the final one is the aggregate)."* ⛔ **That premise is FALSE for any tool that
  emits more than one summary block per run** — Maven's `verify` emits a Surefire summary and then a
  Failsafe one, and the last is the smaller of the two, not an aggregate. Enumerate every parser that
  inherits or restates this premise and check each against its tool's real multi-block behaviour.
  Five call sites are known at HEAD and are the **floor, not the population**: `build-maven`
  (`_maven_cmd_parse.py:151`, restates the pattern itself), `build-gradle`
  (`_gradle_cmd_parse.py:207`, calls the shared helper), `build-npm` jest and tap
  (`_npm_parse_jest.py:143`, `_npm_parse_tap.py:145`), and `build-pyproject`
  (`_pyproject_cmd_parse.py:210`, `:302`, `:520`). ⭐ A site where `[-1]` is genuinely CORRECT (a tool
  emitting exactly one summary block) is a **checked negative and must be reported as one** — not
  omitted. Publish enumerated-vs-checked as two numbers.
- *(b) Generated canonicals that cannot succeed.* D1 below is one canonical emitted unconditionally
  without checking whether the requested phase can satisfy the module's own test classpath. Enumerate
  every canonical `_build_commands` emits and state, per canonical, whether its phase is sufficient for
  what that canonical claims to do. ⛔ **Three prior plans in this epic each fixed the one member they
  tripped over; this one does not repeat that.**

**D1 — `module-tests` emits a `test`-phase reactor request that can never resolve a sibling test-jar.**
`_maven_cmd_discover.py:810` generates the canonical unconditionally:

```python
cmd_map['module-tests'] = f'test{pl_arg}'    # :787 — pl_arg = ' -pl {relative_path} -am'
```

`-am` builds upstream reactor dependencies only as far as the **requested phase**. A `test`-phase request
stops at `test`; a `test-jar` artifact is attached at `package`. So when module B's tests consume module
A's test-jar, `test -pl B -am` builds A only to `test`, never attaches A's test-jar, and B fails at **test
discovery** — in classes the branch under test never touched.

⛔ **Why this is a truthful-signals defect and not merely a build bug.** The failure is
indistinguishable at the gate from a real regression: it is a non-zero exit from the module's own test
command, so `phase-5-execute` routes it to triage unconditionally, and triage must spend a full dispatch
establishing provenance to discover the code was never broken. ⭐⭐ **The steady state is worse than the
cost:** an operator who accepts the signature once to stop the noise has disabled module-test
verification for the rest of the plan, and a genuine regression then arrives wearing the same red.

Fix direction — decide at outline, do not pre-commit here. The sibling-test-jar dependency is visible in
the POM at discovery time, so the phase is decidable **without running a build**: emit a phase that
reaches `package` when a reactor sibling contributes a `test-jar` to this module's test classpath, or
drop `-am` and require the upstream chain installed first. ⚠ Whichever is chosen, the governing rule is
that **discovery must not emit a canonical it can determine will fail.**

**D2 — there is no project-side override, and the generated value wins by construction.**
`_cmd_client_query.py:145` merges the discovered map over the crawled one:

```python
merged = dict(derived.get('commands', {}))
merged.update({k: v for k, v in rebuilt.items() if k != 'conflicts'})
```

⇒ **an operator-set command string in `derived['commands']` is clobbered by the rebuilt canonical**, so a
project hitting D1 has no supported correction path and its only workaround is to stop using the
canonical. ⛔ **This deliverable is NOT "add an override"** — it is to settle whether the override belongs
in the model at all, and to make the answer explicit rather than emergent from a `dict.update` ordering.
If D1's fix makes the canonical correct-by-derivation, an override may be unnecessary and saying so is the
deliverable; if it does not, the escape hatch is named and the merge order stops silently deciding it.

**D3 — the green-build parser reports one summary block where the run produced several.**
`_maven_cmd_parse.py:164` takes `m = matches[-1]` over the `Tests run: X, Failures: Y, Errors: Z,
Skipped: W` pattern. A `verify` run emits two such summaries; the reported figure is the last.

⛔⛔ **The reported number is stamped `tests_population: measured`**, which asserts it is a real
measurement rather than an estimate — so a consumer is entitled to trust it. A reviewer, retrospective,
or coverage-trend check reading `tests_run: 7` for a module with 660 unit tests would reasonably conclude
the suite had collapsed. **A partial count MUST NOT be labelled `measured`**: whatever the fix, the label
and the figure must agree.

Fix direction: sum every `Tests run:` **summary** block rather than taking the last, and carry
per-execution detail (surefire vs failsafe) where the log supports it. ⚠ **The regex matches per-class
lines as well as summary lines** — a naive `sum()` over all matches would over-count as badly as `[-1]`
under-counts. Distinguishing summary blocks from per-class lines is part of this deliverable, not an
assumed given.

⛔ **The test for D3 must be population-derived, per this epic's standing rule.** A fixture asserting
`660 + 7 == 667` against one hand-written log is one assertion repeated; the suite must derive its
expected total from the summary blocks present in the fixture and publish the block count, so a fixture
that degenerates to one block cannot report green.

## Claim Labels

Corroborated first-party at HEAD `30cd8aaf8` on 2026-09-02 unless marked otherwise; re-ground at the
plan's own HEAD before relying on any one of them.

- **OBSERVED** — `module-tests` is emitted unconditionally as `test{pl_arg}` with
  `pl_arg = ' -pl {relative_path} -am'`, guarded only by `packaging != 'pom'` and `has_tests` — read at
  `_maven_cmd_discover.py:787` and `:810`. No phase-sufficiency check exists anywhere in `_build_commands`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _maven_cmd_discover.py unchanged since the spec own 30cd8aaf8 grounding (git log shows no commits touching it since)
- **OBSERVED** — the discovered map clobbers the crawled map, so a crawled/operator command string cannot
  survive — read at `_cmd_client_query.py:145`, `merged.update(...)`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _cmd_client_query.py unchanged since 30cd8aaf8; the merged.update(rebuilt) overlay still clobbers crawled commands
- **OBSERVED** — the maven test-summary extractor takes the last regex match — read at
  `_maven_cmd_parse.py:164`, `m = matches[-1]`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _maven_cmd_parse.py unchanged since 30cd8aaf8; the matches[-1] extraction is still present
- **OBSERVED** — the shared helper does the same AND states the false premise in its own docstring — read
  at `_build_parse.py:596-606`. ⭐ This is what makes D0(a) a population sweep rather than a second
  instance: the premise is written down once and inherited.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _build_parse.py unchanged since 30cd8aaf8; the shared helper docstring premise still states the final one is the aggregate
- **OBSERVED** — five parser sites inherit or restate the premise, enumerated in D0(a). ⚠ Labelled
  OBSERVED as a **floor derived from a grep of `extract_test_summary` consumers plus `[-1]` occurrences in
  build parsers**, NOT as the population — deriving the population is D0's job and the count above must
  not be restated as one.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: The population-vs-floor distinction for the 5 enumerated call sites requires a full sweep not performed here
- **HYPOTHESIS** — that `[-1]` is *correct* for pytest and the npm reporters because each emits exactly
  one summary block per run, making the defect Maven-specific in effect while the premise is shared.
  Confirm/refute per site at `_pyproject_cmd_parse.py:210/:302/:520`, `_npm_parse_jest.py:143`,
  `_npm_parse_tap.py:145` (verify-at-outline). ⛔ A refutation here widens D0(a) from a sweep into a
  multi-site fix and is a re-scope trigger, not a detail.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Per-site correctness of [-1] for pytest and npm not analysed here; the spec marks this HYPOTHESIS verify-at-outline
- **REPORTED, NOT CORROBORATED** — the `cuioss/TokenSheriff` repro (`token-sheriff-client` consuming
  `token-sheriff-validation`'s test-jar; `mvn test -pl token-sheriff-client -am` failing discovery in
  `IdTokenValidationBridgeTest` / `ClientSecretAuthTest` / `DiscoveryResolverTest`; the same tree green at
  660 surefire + 7 failsafe under `verify`; the reported `tests_run: 7`). ⛔ **Foreign repo — the
  orchestrator did NOT read it.** This is the sender's evidence, carried as a lead. The MECHANISM claims
  above stand without it; the repro is what makes them concrete. Re-establish it first-party at outline
  (a local multi-module fixture with a sibling test-jar is sufficient and is preferable to depending on a
  consumer repo) or drop it from the brief.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Foreign repo (TokenSheriff); the spec itself labels this REPORTED NOT CORROBORATED
- **Verify-first clause** — before scoping D1, confirm that Maven attaches `test-jar` at `package` and
  not earlier in the versions this project targets, and that the sibling-test-jar relationship is
  readable from the POM at discovery time without invoking Maven. A refutation of either loops back to
  re-scope D1's fix direction, not merely its wording.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Maven test-jar attachment-phase behaviour across the project targeted versions not verified here

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_discover.py`:787,810
  — `_build_commands`, the `pl_arg` construction and the `module-tests` emission (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_parse.py`:151-175 —
  `_extract_test_summary` (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_parse.py`:596 —
  `extract_test_summary`, its `matches[-1]` and its docstring premise (D0a, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_query.py`:118-147
  — the `merged.update(rebuilt)` overlay (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/SKILL.md` — the `module-tests` canonical
  as documented to callers (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/standards/maven-impl.md` — the command
  derivation contract (D1)
- OBSERVED: `test/plan-marshall/build-maven/test_maven_cmd_parse.py` — the D3 tests
- OBSERVED: `test/plan-marshall/script-shared/test_build_parse.py` — the shared-helper tests (D0a, D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/build-gradle/scripts/_gradle_cmd_parse.py`:207,
  `marketplace/bundles/plan-marshall/skills/build-npm/scripts/_npm_parse_jest.py`:143,
  `marketplace/bundles/plan-marshall/skills/build-npm/scripts/_npm_parse_tap.py`:145,
  `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/_pyproject_cmd_parse.py`:210,302,520 —
  touched ONLY if D0(a) refutes the single-summary-block hypothesis for that tool (verify-at-outline).
  ⚠ Declared here deliberately: under-declaring them would admit a concurrent plan that genuinely
  collides if the sweep widens.

- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_jvm_patterns.py`:54 — the `'[deprecation]'` literal compiled as a character class; added 2026-09-11 by the cross-repo drain fold of `api-sheriff-deployment-configurability-001`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-4-plan/` — the task deriver's module_testing verification command (the third `test-compile -pl -am` emission site), added 2026-09-11 by the fold of `lessons-handling-26-09-04-01-033` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md` — the whole-tree widening by argument subtraction and the degraded-arm verdict, added 2026-09-11 by the fold of `-026` / `-046` (verify-at-outline)

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-architecture/` — `derive-verification`’s emission of the same broken `test -pl <mod> -am` shape, added 2026-09-03 by the drain fold of `deployment-and-refresh-gaps-016`. A SECOND emitter: fixing `_maven_cmd_discover.py` alone would not have prevented it (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: **PLAN-TRUTH-105** (build-execution verdicts that mislead on the healthy path) is the
  nearest neighbour and its D0 sweeps green-path-vs-red-path differential build verdicts. ⭐ **D3 is NOT
  such a verdict** — `matches[-1]` under-reports on the red path too; it is merely most damaging on the
  green one — so the two D0 populations are different questions and neither subsumes the other. If
  -105's sweep surfaces D3 as a member, record and defer to this plan; do not absorb.
- Adjacent to: **PLAN-TRUTH-087** (shipped, #1340) owned `tests_run: 0` on GREEN runs — a *different*
  member of the count-truthfulness family, already closed. ⛔ Do not re-derive or re-fix it here; read
  its landing before scoping D3 so the two fixes do not disagree about what `tests_population` asserts.
- Adjacent to: **PLAN-TRUTH-120** touches `build.map` route derivation — the routing of files to a build
  class, not the derivation of command strings. Untouched by this plan.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-122-the-maven-signal-lies-in-both-directions-a-canonical-that-cannot-pass-and-a-count-that-cannot-add-up.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO
file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## ⭐ FOLDED 2026-09-03 — inbox drain (1 message(s))

- **`deployment-and-refresh-gaps-016.md`** (relayed from Token-Sheriff, plan `outbound-hostname-verification-quarkus`, PR #694 merged `cd36dd24`) — *`derive-verification` emits a build command that cannot compile against a test-jar-classifier dependency.*

  ⭐⭐ **This is a SECOND EMITTER of the exact defect D1 targets, and the relay says so explicitly.** `architecture derive-verification` stamped `test -pl <module> -am` onto TASK-2 and TASK-4. Both target modules consume an upstream module with the `generators` **test-jar classifier**, attached by `maven-jar-plugin` at the `package` phase. **A reactor invoked with the `test` goal never reaches `package`**, so `-am` builds the upstream module without attaching the classified test-jar and the downstream `test-compile` dies on unresolvable generator classes.

  The working shape — the one the deliverable itself documents — is the two-step: `./mvnw install -DskipTests` (attaches the classified test-jar into the local repo), then `./mvnw test -pl <module>` (plain, **no** `-am`).

  ⛔ **The consequence for this spec’s scope:** D1 targets `_maven_cmd_discover.py:810`, which emits the same broken shape. **Fixing that alone would not have prevented this occurrence** — `manage-architecture derive-verification` is an independent emitter with no knowledge of the classifier pairing between a module and its upstream test-jar, and it will re-emit `test -pl <module> -am` for every future plan touching such modules. ⇒ **D0’s emitter sweep must be population-derived across every command emitter, not scoped to `build-maven`.**

  ⚠ **Reproduction is stated and cheap:** run `architecture derive-verification` for any module declaring a `<classifier>generators</classifier>` `test-jar` dependency and inspect the emitted command. ⚠ **The evidence is foreign-repo** — the Token-Sheriff module layout is not corroborable from this checkout, and the sender notes their own project already records the human-facing form of this gotcha (`client-test-jar-build-gotcha`). **What is local and corroborable is whether `derive-verification` emits `-am` unconditionally**; settle that at outline.

## ⭐ FOLDED 2026-09-03 (b) — TokenSheriff mid-flight data-point

**Source:** operator-relayed mid-flight observation from `TokenSheriff`, worktree
`plan-09-local-gate-truthfulness`. **RECURRENCE of D3 / D0a — this spec already owns it**; recorded
here rather than staged, and no surface was added (`_build_parse.py` and `_maven_cmd_parse.py` were
already declared, the former explicitly as *"`extract_test_summary`, its `matches[-1]` and its
docstring premise"*).

**Observed:** `verify` reported **0 tests** where `test` reported **724**, on the same tree.

⭐⭐ **The mechanism is SHARPER than "the more thorough gate reports the smaller number", and the
correction matters for the fix.** The number is not *smaller* — it is a **different population**. A
Maven `test` run stops at surefire, so the last summary block IS the surefire aggregate (724). A
`verify` run continues into failsafe, so the last block is the **failsafe (integration-test)
aggregate**, which is `0` when no ITs are configured. ⇒ **The parser returns a TRUE count of a
population nobody asked about.** Reading it as "smaller" invites a max()-style fix that would be wrong
in both directions; the actual fix is to identify WHICH block is being read.

⛔⛔ **The false premise is stated in the function's own docstring, and D0a should quote it:**

```text
Uses the LAST match in content (build tools often emit per-module summaries;
the final one is the aggregate).
```

`_build_parse.py:596-624`, with `m = matches[-1]` at line 624 — **corroborated first-party at HEAD
`71279cc02`**. *"The final one is the aggregate"* is a **HYPOTHESIS presented as fact**, sitting in the
docstring of the function that produces the number. It holds for per-module surefire summaries and
fails for a two-phase lifecycle — and nothing distinguishes the two cases at the call site.

⭐⭐⭐ **Why 51 green tests never caught it.** `test/plan-marshall/script-shared/test_build_parse.py`
declares **51 `def test_` functions and NOT ONE of them mentions `failsafe`, `Failsafe`, or
`integration`** (derived by pattern match over that file at HEAD; the zero is scoped to that file and
to those three terms, and is not a claim about the whole suite). ⇒ **The two-summary-block case — the
only shape that produces the inversion — has no coverage at all.** This is the
coverage-gap-that-reads-as-covered pattern: a green suite over a construct it never exercises.

⚠ **The direction of the error is the damaging one and compounds with `tests_population: measured`.**
Inbox `deployment-and-refresh-gaps-012` (folded into `PLAN-TRUTH-105` earlier today) recorded
`tests_run: 0` stamped `measured` over a log carrying 465 test-result lines. **That is now the THIRD
independent observation of a build wrapper publishing a confident zero over a real suite**, from a
third source. ⛔ **`verify` is the gate the push barrier runs**, so the lane that reports `0` is the
lane that decides whether the tree is safe to push.

⚠ **The foreign numbers (0 / 724) are the operator's own first-party observation in another
repository and are NOT corroborable from this checkout.** What IS corroborated here is the parser, its
`matches[-1]`, its docstring premise, and the absent test coverage.

## ⭐ FOLDED 2026-09-04 — inbox drain (2 message(s))

- **`lessons-handling-26-09-04-01-001`** — *the generated `module-tests` canonical cannot work for a module that consumes a sibling’s test-jar.* ⭐⭐ **Relayed as ONE message consolidating TWO independently-filed lessons** (`2026-08-31-12-001` from the symptom, `2026-09-01-19-003` from the mechanism) **filed a day apart by different plans, neither referencing the other** — the relaying orchestrator states the consolidation is its own judgement and that **the pair should be treated as one fix with two independent reproductions, which is stronger evidence than either alone.**

  **Mechanism:** `test -pl {module} -am` never reaches `package`, and a Maven test-jar is attached by `jar:test-jar` bound to `package`. So `-am` builds the sibling’s classes but **never attaches its test-jar**, and any consuming module fails **at test DISCOVERY** — `NoClassDefFoundError` on the sibling’s test utilities — *“not at compile, and not for any reason that names the real cause.”* ⛔ **Every `module-tests` invocation against such a module is a FALSE RED.** `compile -pl X -am` is unaffected and passes, which is what makes it look like a code regression.

  ⭐ **Two DIFFERENT working remedies were applied on two occurrences, and the difference is informative**: pointing `per_deliverable_build` at `verify` (which reaches `package`; empirically green in 154s, 660 surefire + 7 failsafe), and the two-step `install -DskipTests` then plain `test -pl X`. **The upstream ask is the statically-detectable condition:** emit `verify` rather than `test` whenever any module in the reactor slice publishes or consumes a `test-jar`. ⛔⛔ **And the message itself carries the recurrence note that the fix must cover TWO emitters** — `manage-architecture derive-verification` stamped the identical broken shape on a later plan, so *“fixing `_maven_cmd_discover.py` alone would have left this path emitting the identical broken shape.”* That second emitter was folded into this spec on 2026-09-03.

  ⚠ **Provenance discipline, worth carrying verbatim:** *“Do not read this failure as a regression from the branch under execution … it reproduces on an unmodified tree. Establish that before attempting any fix: a bigger version of a wrong fix is still wrong.”* And: the canonical is **generated live and not cached in `project-architecture`**, so a consuming project has **no local override file to patch** — the defect is unavoidable from their side.

- **`lessons-handling-26-09-04-01-002`** — *the build wrapper’s `tests_run` reports only the LAST summary line, so a full `verify` looks like it ran 7 tests.* ⭐⭐ **This supplies the LOG LINE NUMBERS for the defect this spec folded on 2026-09-03 from the same repository** — two runs, same unchanged worktree, both green: `test -pl token-sheriff-client` → **724** in 93s; `verify -pl token-sheriff-client` → **7** in 26s. The log shows both: **line 228 `Tests run: 724` (surefire total), line 293 `Tests run: 7` (failsafe total)**. The parser takes the last.

  ⛔⛔ **The consequence is an INVERTED heuristic, and the second-order effect is the worse one:** *“the more complete gate reports the smaller number, so `verify` looks like the weaker check when it is the stronger one. An agent applying the ordinary heuristic ‘a suspiciously small test count means the tests did not run’ will chase a non-existent regression, or — worse — will accept a genuinely empty surefire run on some other module because it has learned to discount small counts on `verify`.”*

  ⭐ **And `tests_population: measured` is what makes the wrong number credible** — *“that field asserts the count is a real measurement rather than an unknown.”* **Upstream ask, sharper than “take the max”: SUM the per-plugin totals, or report them separately (`surefire_tests_run` / `failsafe_tests_run`), rather than letting the last match win.** Operational check until then: read every `Tests run:` line in the log the wrapper points at via `log_file`, **not the last one — a `verify` run has at least two.**

## ⭐ FOLDED 2026-09-04 (b) — cui-http consolidation

**Source for every item below:** `inbox/findings-from-cui-http.md`, a consolidation relayed from the **cui-http** repository aggregating **52 lesson records** from the `quality-report-remediation` epic (19 plans, PRs #153–#186). ⛔ **The source records were REMOVED after it was written — that document is their sole surviving record.** ⛔ Nothing in it was corroborable against cui-http from this checkout; the plan-marshall surfaces it names are local and are where the value is. ⚠ Its header says *"8 themes / 27 findings"* and it enumerates **45** — **do not quote its internal counts.**

- **§8.4 — Maven's failure epilogue is filed as ~30 separate findings, all mislabelled.** Two defects in one: **Maven's failure epilogue is parsed line-by-line into ~30 separate `build-error` findings all labelled `deprecation_warning`**, and **one test failure is filed at three granularities.** ⛔ Pure noise inflation of the findings count — and it lands on the pre-merge barrier, which gates on that count.

  ⭐ **This is the third distinct way this spec's subject — the Maven signal lying — manifests, and the three are independent**: a canonical that cannot pass (`test -pl X -am` against a test-jar), a count that cannot add up (`matches[-1]` over two summary blocks), and now **a parse that manufactures ~30 findings from one failure and labels every one wrongly.** ⛔ **D0's emitter sweep should cover the FINDING-EMISSION path as well as the command-emission and count-parsing paths** — all three are the same wrapper reporting something other than what happened.

  ⚠ **Read alongside `deployment-and-refresh-gaps-019`** (19 actionable findings accumulating silently and first surfacing as an opaque merge-barrier count, staged as `PLAN-TRUTH-133`): **this fold explains part of where that volume comes from.** ⛔ Keep them separate — `-133` fixes *when the count is disclosed and whether an experiment is distinguishable*; this fixes *whether the count was ever real*.

## ⭐ FOLDED 2026-09-07 (b) — lessons-handling drain (1 item)

`lessons-handling-26-09-04-01-013` (`build-maven`): **widening a module-scoped test-compile to the whole
reactor is INVALID when modules depend on a sibling's test-jar.**

⭐⭐ **A widening that looks strictly safer and is not** — the intuition *"compile more, miss less"*
fails because reactor-wide test-compile changes which artifacts are resolvable, so a module depending on
a sibling's test-jar builds differently (or not at all) under the widened scope. ⇒ **The widened run is
not a superset of the narrow one; it is a DIFFERENT run.**

⛔ **This bears directly on this spec's `matches[-1]` premise**: a shared helper docstring asserting
*"the final one is the aggregate"* is a claim about reactor structure, and **this item shows reactor
structure is exactly what changes under a scope widening.** ⇒ **D0 must not assume scope is a dial with
a safe direction.**

## ⭐⭐ FOLDED 2026-09-11 — cross-repo lessons drain (5 items: API-Sheriff `-001`, Token-Sheriff `-026` `-033` `-041` `-046`)

Two consumer repos, independently, and every item lands on this spec's two directions. Verified
read-only at HEAD `356973d80` (= `origin/main`) before folding.

### NEW ROOT CAUSE — the `deprecation_warning` miscategorisation is a regex character class (`api-sheriff-...-001` (d))

- OBSERVED: `script-shared/scripts/build/_build_jvm_patterns.py`:54 carries the literal `'[deprecation]'`;
  `_build_parse.py`:487-490 `_is_regex_pattern` returns true for any pattern containing `[`/`]`, so the
  literal is compiled as the character class `[deprecation]` — **one letter out of d/e/p/r/c/a/t/i/o/n**.
  ⇒ nearly every line nothing earlier classified lands in `deprecation_warning`, which is why genuine
  surefire failures and compiler errors were categorised as deprecation warnings.
- Companion misfiles in the same parse (sender-verified, not re-derived here — HYPOTHESIS, confirm/refute
  at `build-maven/scripts/_maven_cmd_parse.py` § the `[ERROR]`/`[WARNING]` loop at :106-130 and
  `_build_jvm_patterns.py` § the `'tests run:'` pattern at :33, verify-at-outline): Maven epilogue
  boilerplate (`Failures:`, `See ... surefire-reports`, `[Help 1]`, `-rf :module`) filed as
  `severity: error` findings; a **passing** `Tests run: 27, Failures: 0` line filed as `test-failure`.
  Measured cost at the sender: 34 findings for a 2-test flake, 21 of them parser artifacts.

### D3 recurrences — `tests_run` is the last block, not the run (`api-sheriff-...-001` (a), `-041`)

- API-Sheriff: `tests_run: 202` for a reactor whose `api-sheriff` module alone runs 1886 — the
  **multi-module** variant (last reactor module's surefire summary).
- Token-Sheriff `-041`: `tests_run: 7` where the log carries Surefire **762** + trailing Failsafe 7 — the
  surefire/failsafe variant already folded from `-002`. ⇒ **Two variants of one `matches[-1]`**; D3 must
  sum every `Results:` block across modules AND phases, and should report `surefire_tests` /
  `failsafe_tests` separately (the sender's suggestion) so unit and integration execution stop being
  inferred from one conflated total.

### D1 — a canonical that cannot pass: four independent sightings of the reactor/test-jar shape (`-026`, `-033`, `-046`, `api-sheriff-...-001` (e))

- `-026` (recurrence of `-013`, **third plan**): `pre-push-quality-gate`'s whole-tree widening removes the
  module argument, and under Maven `-pl <module>` arrives with `-am` — so the widening drops `-am` too and
  the upstream test-jar is never built: 20 missing-package errors in modules outside the diff, while
  whole-tree `verify -Ppre-commit` on the same tree passed. **Sender's framing is the durable half:
  widening by textual argument subtraction is unsound for any build system whose scope selector carries a
  companion closure flag.** Remedy direction: resolve the whole-tree command through the canonical-command
  surface, never by subtracting arguments.
- `-046` (**fourth plan**): both pre-push arms DEGRADED rather than failed — bare `test-compile` cannot run
  whole-tree or module-scoped, and `build-maven` has no `resolve-test-scope` verb. ⚠ A degraded arm still
  reports a verdict computed over a smaller surface than its name claims — it must say `indeterminate`.
- `-033`: the **phase-4 task deriver** stamps `test-compile -pl <mod> -am` as a module_testing
  deliverable's verification command although the outline's own deliverable command was correctly
  `verify -pl <mod> -am`. ⇒ the broken form is emitted at a THIRD site beyond `_build_commands` and
  `derive-verification` (already declared above). Structural detection the sender proposes: test sources
  importing another reactor module's `src/test` package, or a `<type>test-jar</type>` dependency.
- API-Sheriff (e), **UNTRACKED until now**: `-Dtest=X` riding `-pl M -am` fails every sibling module with
  `No tests were executed!`; dropping `-am` tests stale installed artifacts. OBSERVED: `failIfNoSpecifiedTests`
  appears nowhere under `marketplace/bundles/`. Remedy: append `-Dsurefire.failIfNoSpecifiedTests=false`
  when a targeted `-Dtest` rides an `-am` reactor — **never** the blunter `-DfailIfNoTests=false`, which
  also silences the targeted module so a typo'd test name passes green — and document the pitfall in
  `build-maven/SKILL.md` and `standards/maven-impl.md`.

⇒ **Recurrence count on the reactor/test-jar shape is now 4 plans in Token-Sheriff + 1 in API-Sheriff.**
Per this epic's standing rule the count measures the delay, not the defect — the mechanism has been known
since `-013`.

### Claim labels for this fold

- OBSERVED: `_is_regex_pattern` treats `'[deprecation]'` as a character class — `_build_parse.py`:490 and `_build_jvm_patterns.py`:54 at `356973d80`.
- OBSERVED: no `failIfNoSpecifiedTests` anywhere under `marketplace/bundles/` at `356973d80` (tree-wide search, zero hits).
- HYPOTHESIS: the phase-4 task deriver emits `test-compile` for a test-jar-consuming module — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-4-plan/` § the module_testing verification-command derivation (verify-at-outline).
- HYPOTHESIS: epilogue lines and passing `Tests run:` lines are filed as findings — confirm/refute at `_maven_cmd_parse.py` § the `[ERROR]`/`[WARNING]` loop (verify-at-outline).

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-150-build-and-ci-verdicts-that-mislead-specifically-on-the-healthy-path.md` (PLAN-TRUTH-150)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
