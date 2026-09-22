# PLAN-160: Sweep the Three Single-Instance Defect Classes

epic: test-quality
workstream: WS-03

> Staged plan spec. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

> **Authored by the orchestrator during epic ingestion**, from PLAN-090's own residue — the clearest
> genuinely-unowned item in the whole epic.

## Objective

PLAN-090 found and fixed three defects, and its own residue says plainly that each **rests on a single
instance, with no sweep establishing it was the only one**. Two of the three were found by a review bot
rather than by the run, which is the tell: nothing in the tree looks for these shapes. A two-minute check
during ingestion claimed **two further candidate sites for R4 alone**; re-grounding at HEAD found the real
number is **one**, and that the second hit was the fixed file's own docstring quoting the shape — a false
positive the sweep must be able to classify, and the tell that even the count needs a real scan. Each class is a
way for a guard to keep passing while it has stopped guarding — a false-clean signal, which is the exact
defect class this epic exists to remove. Sweep all three, and where a class admits a mechanical check, ship
the check rather than the sweep's output.

## Deliverables

1. **R1 — Sweep for guards pinned by path literal.** PLAN-090's D3 positive control pinned
   `test/plan-marshall/build_test_helpers.py` **by filename**. PLAN-070 renamed that file mid-run and the
   control broke **invisibly** — `mergeable_state` stayed `clean`, so nothing anywhere reported it.
   Scan every test-module guard and control across `test/` for a hardcoded path literal naming a file owned
   by a **different slice** than the guard's own directory, and re-express each **by role or behaviour**
   rather than by filename, as PLAN-090's own fix did.
   ⛔ **A guard that names a file it does not own is the shape**, not merely a guard containing a string. A
   guard pinning a file in its own directory is fine — the renaming plan would have to touch it.
   *Done when:* the scan's population and command are recorded; every cross-slice path literal is
   re-expressed or named with why it cannot be; and the count is reported before and after.

2. **R3 — Sweep for hand-kept populations mirroring a live source.** `REGISTERING_HELPERS` and
   `WRAPPER_SCRIPTS` were constant lists mirroring `conftest.py`'s loader helpers and its `build_main`
   wrappers — able to fall silently behind what the source actually declares. A reviewer found them.
   Find every other constant list of names or paths in `test/` that mirrors a live source, and convert each
   to a **derivation plus an equality assertion**, as R3's own fix did.
   ⚠️ **Two known instances are declined, correctly, and stay declined**: `CANONICAL_SUBDIRS`
   (`build-pyproject/test_dynamic_mypypath.py:21`) and `REAL_LESSON_IDS`
   (`plan-doctor/_doctor_fixtures.py:25`) were raised on PLAN-070's review threads and declined as
   pre-existing. **Re-examine them under this sweep's criterion** — a decline for "pre-existing" is not a
   decline on the merits — and either convert them or record a decline that says *why the mirror is
   acceptable*, which the original threads did not.
   *Done when:* the scan's population and command are recorded; every mirror is converted or carries a
   merits-based decline; and each conversion's equality assertion is **observed failing** by perturbing the
   live source and watching it go red.

3. **R4 — Sweep for conditional teardown that restores nothing.**
   `monkeypatch.delitem(sys.modules, NAME, raising=False)` restores nothing when the key was **absent** at
   test start, leaking the module into `sys.modules` for the rest of the session. A reviewer found one.
   ⚠️ **One unexamined call site of this exact shape stands at HEAD**:
   `test/plan-marshall/manage-tasks/test_freshness_notation_crosscheck.py:186`.
   ⛔ **Classify every match as a call site or as prose before counting it.** The ingestion count of two was
   wrong because the second hit was `test_conftest_loader_contract.py:168` — a docstring in PLAN-090's own
   fix, quoting the shape to explain it. A sweep that cannot tell those apart reports a population it never
   measured, which is this epic's own defect class turned on the sweep.
   ⚠️ **The sibling shape is where the volume is**: `monkeypatch.delenv(..., raising=False)` returns **63**
   lines at HEAD, none ever examined for conditional teardown. Size this deliverable off that number.
   Scan `test/` for every
   `monkeypatch.delitem(..., raising=False)` call and check whether its teardown is **unconditional** (an
   autouse pop — the correct shape PLAN-090 shipped) or **conditional on prior state** (the defective shape).
   Widen the scan to the sibling shapes — `monkeypatch.delenv(..., raising=False)` and any hand-rolled
   save/restore keyed on the value having been present.
   ⛔ **A leak of this kind is invisible in a default-order run and shows up as an order-dependent failure
   somewhere else entirely** — which is how PLAN-060 lost seven tests and PLAN-030 173. Verify each fix with
   a **reverse-order** run, not only a default one.
   *Done when:* the scan's population and command are recorded; every conditional teardown is made
   unconditional or named with why it must not be; and the affected directories pass in **default and
   reverse** order.

4. **R5 — Sweep for a parametrize bound to a runtime-resolved collection.** ⛔ **FOLDED IN from
   PLAN-165's landing (2026-09-13, candidate-lesson -013)** — a fourth instance of this plan's own class,
   found by a shipped plan rather than by a sweep, which is the same tell R1 and R3 carry.
   `test_configure.py` parametrized over `CLI_AUTH_TYPES` read as an attribute off a **runtime-loaded
   module** rather than as a literal. `empty_parameter_set_mark` is not overridden in `pyproject.toml`
   and its pytest default is `skip`, so if that attribute ever resolves empty — renamed, relocated,
   emptied upstream — the test is SKIPPED, the suite stays green, and the coverage it exists to provide
   is gone with no signal. The test is not wrong; it simply stops running, and a skip is not a failure.
   Scan `test/` for every `parametrize` whose argvalues resolve from a runtime-loaded attribute rather
   than a literal in the test file, and close each one.
   ⛔ **Assert non-vacuity at the BINDING site, never in the test body** — a body-level assert never runs
   in the empty case, because there is no parameter set to run it with.
   ⚠️ **The project-wide fix is the stronger one and is in scope to EVALUATE, not to assume**:
   `empty_parameter_set_mark = fail_at_collect` in `pyproject.toml` converts every such skip into a
   collection error tree-wide. Measure how many existing parametrizations it would turn red before
   proposing it — a config flip that reddens the suite is a different deliverable from a per-site guard.
   *Done when:* the scan's population and command are recorded; every runtime-bound parametrize carries a
   binding-site non-vacuity assertion or a named reason it cannot; the `fail_at_collect` evaluation
   reports the count it would affect and an explicit adopt-or-decline verdict; and the affected
   directories pass in **default and reverse** order.

5. **D4 — Report the measured deltas, and say which classes now have a check.** Each class's swept
   population with its command; the instances found, fixed, and declined-with-reason; the observed-failing
   demonstrations for R3's equality assertions; the reverse-order result; and the collected test count
   before and after.
   ⛔ **Name, per class, whether it is now mechanically checked or only swept.** A swept class regrows; a
   checked one does not. Where a class admits a rule or a guard test, **ship it** — that is the difference
   between this plan and a fourth instance-fix. Where it does not, say so plainly.
   *Done when:* the report carries every figure with its command, and each of R1, R3, R4, R5 carries an explicit
   *checked* or *swept-only* verdict.

## Claim Labels

- OBSERVED: PLAN-090's residue states each of R1, R3 and R4 rests on a single instance with no sweep
  establishing it was the only one — read at `.plan/orchestrator/test-quality/archive/090-harness-and-rule-gaps/report-01.md` § Residue
  - verdict: corroborated | checked_at: 9853a7ab | by: test-quality/cleanup | rescoped: n/a | evidence: re-confirmed at HEAD 9853a7ab against the FROZEN archive reports under archive/090-harness-and-rule-gaps/ (report-01.md and report-02.md both present, report-01 carrying its Residue section). Claims reading an archived report are stable by construction and cannot drift the way this spec's live-source claim 4 did. Re-stamped to record that the question was re-asked at this HEAD rather than carried forward on the bf1b7ed6 stamp.
- OBSERVED — **still the strongest evidence this plan is needed, but not the evidence ingestion recorded**:
  the `delitem(... raising=False)` sweep returns **2 unique files** at `bf1b7ed6` — one genuine call site
  (`test_freshness_notation_crosscheck.py`) and one prose hit (`test_conftest_loader_contract.py`). ⚠️ **A
  third hit recorded at `09f92b5e` (`test_epic_spec_parser.py:287`, a fixture string literal) no longer
  matches**, so this population moves in both directions and a naive count is unstable across shas. The
  volume sits in the sibling shape instead: `delenv(..., raising=False)` returns **64** lines across **32
  files** (re-scoped from 63), none examined
  - verdict: corroborated | checked_at: 8fc353b6 | by: test-quality/cleanup | rescoped: n/a | evidence: re-derived at 9853a7ab AND again at 8fc353b6 after upstream #1456 landed mid-cleanup touching two of this spec's newly-declared directories (test/pm-plugin-development/plugin-doctor/ and tools-marketplace-inventory/). The figures are IDENTICAL at both shas: delitem(... raising=False) returns 2 unique files, delenv(..., raising=False) returns 64 lines across 32 files. The re-scoped population is stable across three landings and one upstream commit, which is what makes it safe to size the deliverable against - unlike this epic's budget population, which moved during the same pass.
- OBSERVED: R1's instance broke **invisibly** — the control was pinned by filename, PLAN-070 renamed the
  file mid-run, and `mergeable_state` stayed `clean` throughout
  - verdict: corroborated | checked_at: 9853a7ab | by: test-quality/cleanup | rescoped: n/a | evidence: re-confirmed at HEAD 9853a7ab against the FROZEN archive reports under archive/090-harness-and-rule-gaps/ (report-01.md and report-02.md both present, report-01 carrying its Residue section). Claims reading an archived report are stable by construction and cannot drift the way this spec's live-source claim 4 did. Re-stamped to record that the question was re-asked at this HEAD rather than carried forward on the bf1b7ed6 stamp.
- OBSERVED: **two of the three classes were found by `coderabbitai`, not by the run** — R3 and R4 both. The
  tree has no check for either shape
  - verdict: corroborated | checked_at: 9853a7ab | by: test-quality/cleanup | rescoped: n/a | evidence: re-confirmed at HEAD 9853a7ab against the FROZEN archive reports under archive/090-harness-and-rule-gaps/ (report-01.md and report-02.md both present, report-01 carrying its Residue section). Claims reading an archived report are stable by construction and cannot drift the way this spec's live-source claim 4 did. Re-stamped to record that the question was re-asked at this HEAD rather than carried forward on the bf1b7ed6 stamp.
- OBSERVED: PLAN-090's fixes are present and correct at HEAD — the role-based control at
  `test_conftest_loader_contract.py:247-253`, the derived `registering_helpers_in_conftest` import, and the
  autouse teardown at `:164-177`. ⛔ **This plan extends them to their classes; it does not revisit them**
  - verdict: contradicted | checked_at: 9853a7ab | by: test-quality/cleanup | rescoped: yes | evidence: the SUBSTANCE holds but EVERY line reference is stale, and one descriptor matches nothing. At HEAD 9853a7ab the autouse teardown _probe_registration_is_not_leaked begins at :175, not within the claimed :164-177 (that range is the PROBE_* constant block); the derived registering_helpers_in_conftest import is at :31 and consumed at :301, present and correct; and the claimed role-based control at :247-253 resolves to a different test entirely - the token role appears NOWHERE in the file. PLAN-090's fixes ARE present, so the claim's operative premise (this plan extends them, does not revisit them) stands. Re-scoped on all line references and on the role-based descriptor, which should be re-worded to name the autouse teardown it evidently means.
- HYPOTHESIS: R1's and R3's populations are also larger than one — confirm/refute at each sweep
  (verify-at-outline). ⛔ **An asserted absence is verified exactly like an asserted presence**: a sweep
  returning one instance is a *result*, and a sweep never run is not
- OBSERVED — **standing, correctly pinned, and NOT this plan's**: **17** live `sys.modules` registration
  collisions and **86** statically-unresolvable loader call sites, both at their guard's baseline
  (re-scoped from 23 and 90; both FELL across `bf1b7ed6`, which also added +83 lines to that guard file). They are
  **bounded by a guard that fails on growth**, which is the right posture; this plan must **not relax that
  baseline** to accommodate its own fixes
  - verdict: unverifiable | checked_at: 9853a7ab | by: test-quality/cleanup | rescoped: n/a | evidence: SPLIT VERDICT, recorded as unverifiable because only half was checkable. The collision half is CORROBORATED exactly: KNOWN_REGISTRATION_COLLISIONS holds 17 names at HEAD 9853a7ab, read directly from the frozenset, and the guard file was NOT touched by #1455. The 86-statically-unresolvable-call-sites half could NOT be checked: re-deriving it requires the guard's own whole-tree scan, which is a build and outside the orchestrator boundary. CI green on #1455 establishes only that the RATIO sits inside the [10%, 14%] bound pair, not that the count is still 86 - and PLAN-155 changed 97 test files including 31 in script-shared, which is exactly the population that scan walks. Stamping corroborated would claim a verification of 86 that was never performed.

## Expected Surface

⛔ **RE-SCOPED AT CLEANUP (2026-09-09, HEAD `9853a7ab`) — the three `test/**` claims were replaced by the
directories the classes actually live in.** `test/**` is a ROOT claim, and the disjointness matcher
compares exact normalized paths: `test/**` never matches a sibling's `test/plan-marshall/…/` entry, so the
gate reported this plan **clean against every sibling whose surface `test/**` plainly contains**. That
silence was an unchecked negative, not a checked one (ADR-019) — a recurrence of lesson
`2026-08-25-09-016` — and it forced the orchestrator to refuse this plan by hand-applied judgement every
round. Directory entries match sibling directory entries exactly, so the gate now works on this spec.

⚠️ **The population is derived, and growth INSIDE these directories needs no re-scope** — that is why
directories were chosen over the 34 exact files. A hit in a directory NOT listed here is out of surface
and is a re-scope, not a silent widening.

- OBSERVED: `test/plan-marshall/script-shared/test_conftest_loader_contract.py` — the three shipped fixes
  this plan extends; read, and edited only if a sweep finds a further instance inside it
- OBSERVED: `test/plan-marshall/build-pyproject/test_dynamic_mypypath.py` (`CANONICAL_SUBDIRS`) and
  `test/plan-marshall/plan-doctor/_doctor_fixtures.py` (`REAL_LESSON_IDS`) — R3's two known declined mirrors,
  re-examined on the merits
- HYPOTHESIS: R1's, R3's and R4's outputs across the seventeen directories below (verify-at-outline).
  ⚠️ **Re-derived at `9853a7ab`: 2 delitem files and 64 delenv lines across 32 files — 34 files in 16
  directories.** The earlier figures (1 delitem site, 63 delenv lines) were stale. The seventeenth
  directory is `test/plan-marshall/plan-doctor/`, which carries R3's named `REAL_LESSON_IDS` mirror and
  no delenv/delitem hit — it is declared because the spec names a file in it, not because the sweep derived it
- HYPOTHESIS: a rule or guard test for whichever classes admit one — location per
  `pm-plugin-development:plugin-script-architecture` if it is a doctor rule, beside the existing guard if it
  is a meta-test (verify-at-outline). ⛔ **A doctor rule lands in WS-03's tree; check the sequencing below**
- OBSERVED: `test/plan-marshall/build-pyproject/`
- OBSERVED: `test/plan-marshall/build-server/`
- OBSERVED: `test/plan-marshall/extension-api/`
- OBSERVED: `test/plan-marshall/manage-config/`
- OBSERVED: `test/plan-marshall/manage-lessons/`
- OBSERVED: `test/plan-marshall/manage-providers/`
- OBSERVED: `test/plan-marshall/manage-run-config/`
- OBSERVED: `test/plan-marshall/manage-tasks/`
- OBSERVED: `test/plan-marshall/marshall-steward/`
- OBSERVED: `test/plan-marshall/plan-doctor/`
- OBSERVED: `test/plan-marshall/plan-marshall/`
- OBSERVED: `test/plan-marshall/platform-runtime/`
- OBSERVED: `test/plan-marshall/script-shared/`
- OBSERVED: `test/plan-marshall/tools-file-ops/`
- OBSERVED: `test/plan-marshall/tools-script-executor/`
- OBSERVED: `test/pm-plugin-development/plugin-doctor/`
- OBSERVED: `test/pm-plugin-development/tools-marketplace-inventory/`
- OBSERVED: `pyproject.toml` — R5 only, for the `empty_parameter_set_mark` evaluation; the sweep
  itself lands inside the directories above

## Dependencies and Sequencing

- Depends on: PLAN-090 (landed — it is the source of all three classes).
- ⛔ **Must not run concurrently with**: PLAN-135 (it converts loader call sites, which is exactly what R4's
  registration shape governs — the worst pairing in the epic), PLAN-105 (§ D7's migration touches the same
  loader mechanics; § D3 and § D7 are in the same tree as any doctor rule this plan ships), PLAN-145 or
  PLAN-120 if either lands under `marketplace/bundles/**`.
- ⚠️ **Sweeps read broadly and write narrowly.** R1 and R3 touch scattered files across every slice, so
  confirm no `test/`-editing plan is in flight before the write half, even though the read half collides with
  nothing.
- **May run concurrently with**: PLAN-110, PLAN-140, PLAN-150, PLAN-155 — ⚠️ **subject to the caution above**;
  the write half is scattered and a campaign run holding a slice is a genuine collision.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/test-quality/plans/PLAN-160-sweep-the-three-single-instance-defect-classes.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
