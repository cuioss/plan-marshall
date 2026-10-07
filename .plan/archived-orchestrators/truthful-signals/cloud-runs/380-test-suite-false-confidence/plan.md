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

# The test suite's false-confidence patterns — a runner that reports pass for zero tests

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

⭐ **This is the epic's thesis inside the safety net itself.**

`test/run-tests.py` executes each test file **as a script** and treats **exit 0 as a pass**. Only about
ten of roughly 545 test files have a `__main__` block that invokes pytest. **The rest import, run zero
test functions, exit 0, and print a pass.** Pure false green.

⭐ **The canonical CI path is pytest via the build command**, so this is a **developer trap, not a CI
hole** — **which is exactly why it survives: nothing that gates a merge ever notices it.**

⛔⛔ **And the vacuous green is CONSUMED.** Observed on a different plan: **a green build CLEARS
test-failure findings even when the command it ran executed no tests.** ⭐ **That changes the severity
argument, not just the evidence.** A harness that reports a vacuous pass is a **measurement** defect; a
harness whose vacuous pass **clears findings** is a mechanism that **destroys signal that already
existed.** The finding was true, was recorded, and was cleared by a command that tested nothing.

Four smaller integrity defects sit alongside it:

- **Dead module-stubbing mocks.** Several files call `sys.modules.setdefault(...)` — but the shared
  conftest **pre-imports the real modules first**, so every one is **a guaranteed no-op**. The tests run
  against the real modules **while implying an isolation they do not have.** ⭐ **On-theme: the mock is a
  claim the code does not honour.**
- **Developer paths baked into fixtures**, leaking a real username and coupling any future path-relative
  assertion to one machine.
- **An autouse pollution guard** that snapshots the real credentials directory and plan state **before
  and after every test**, as a backstop to sandbox fixtures that already make those writes structurally
  impossible — real cost, low marginal value, and it reads real developer state.
- **A manual environment save/restore** that mutates process-global state **while a newer autouse
  sandbox does the same thing, auto-reverted.** Two overlapping mechanisms on one set of globals: an
  exception between enter and exit, or interleaving with the autouse fixture, can **leave a base-path
  variable pointing at a torn-down temporary directory for later tests in the same worker.**

## Goal

The suite's green means something: no runner can report a pass without having executed tests, no
finding can be cleared by a command that ran none, and no fixture implies an isolation it does not have.

## Deliverables

1. **D1 — Kill the false-green runner.**
   *Done when:* it is **deleted** in favour of the canonical build command — or, if kept, it **shells out
   to pytest per file**.
   ⛔ **DELETION is the preferred remedy.** ⭐ **A runner that cannot fail is worse than no runner,
   because it is consulted.**
2. **D2 — The finding-clearing path must require evidence that tests actually RAN.** A **non-zero
   executed-test count**, not a zero exit.
   *Done when:* a build that executes no tests **cannot clear a test-failure finding**.
   ⛔ **The check must PUBLISH the population it counted**, or it reproduces the defect inside its own
   fix — which is this project's most-repeated failure mode.
   ⭐ **This is the deliverable that matters most**, because it is the one where the vacuous green
   destroys existing signal rather than merely failing to create it.
3. **D3 — Delete the dead module-stubbing mocks**, or switch to an explicit fixture if stubbing is
   genuinely intended.
   *Done when:* no file implies an isolation it does not have.
4. **D4 — Normalise developer paths out of fixtures** to a placeholder root.
   *Done when:* no fixture contains a real user's home path.
5. **D5 — Scope the autouse pollution guard** to credential- and plan-touching tests via a marker.
   *Done when:* it no longer runs on every test.
   ⚠ **It was already narrowed once for a large performance regression, per its own docstring** — so
   **treat "it is cheap now" as a claim to MEASURE, not to assume.** Report the before-and-after.
6. **D6 — Retire the manual environment save/restore.** Migrate remaining users to the fixture and
   delete the manual path.
   *Done when:* one mechanism owns those globals.
7. **D7 — A control that proves the runner fix is closed.** After the fix, a file containing a
   **deliberately failing test MUST** make the runner (or its replacement) **fail**.
   *Done when:* the control passes.
   ⛔ **Without this the remedy is UNFALSIFIABLE** — ⭐ **and an unfalsifiable fix for a false-green is
   the same defect wearing a fix's clothes.**

Seven deliverables, under the raised cap.

## Out of scope

- ⛔ **`marketplace/bundles/**` — the code under test.** This plan changes the **harness**, never what it
  tests. A harness defect fixed by changing the code under test is not a fix.
- **A coverage push for helper modules without direct unit tests.** An earlier finding claimed a number
  of such modules — ⛔ **it was NOT re-derived, and the source review itself notes no whole skill
  directory is untested and the modules are reachable transitively.** ⭐ **A coverage-shaped aspiration
  with a stale population is not a deliverable.** If it matters, it needs **a fresh population and a
  stated threshold** — file it then.
- **Three findings that have already fixed themselves.** Config-content assertions that no longer skip,
  fixture-presence skips that are gone, and wall-clock sleep dependencies that are gone. ⭐ **Three of
  nine test-integrity findings closed in five weeks** — recorded here **so nobody re-files them**, and as
  the reason every remaining item was re-checked rather than inherited.

## Expected surface

- `test/run-tests.py` — the false-green runner.
- `test/conftest.py` — the pollution guard and the environment sandbox.
- The five test modules carrying the dead module stubs.
- `test/pm-dev-java/fixtures/**` and `test/plan-marshall/build-npm/fixtures/**` — the developer paths.
- The finding-clearing path (D2).

⚠ **`test/conftest.py` is the highest-traffic shared file in the repository.** Any plan adding tests
concurrently will conflict there. ⛔ **Do not pair this with a test-heavy plan; serialize.**

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The runner treats exit 0 as a pass and most test files run zero tests under it | HYPOTHESIS | that runner, **by symbol**, plus a count of files with a pytest-invoking main block. ⛔ **Re-derive the ratio; ~10 of ~545 is a LEAD** |
| The canonical CI path is pytest via the build command, so this is a developer trap rather than a CI hole | HYPOTHESIS | the build command and the CI workflow — ⭐ **this is what makes it survivable, and it is checkable here** |
| A green build clears test-failure findings even when no tests ran | HYPOTHESIS | ⛔ **observed on another plan's run, under `.plan/`, NOT reachable here.** ⭐ **But the CLEARING PATH is checkable from source** — read what it requires before believing or disbelieving it |
| The module stubs are guaranteed no-ops because the conftest pre-imports the real modules | HYPOTHESIS | the conftest and the five files — ⭐ **the ordering is the whole claim** |
| Developer paths appear in fixture files | HYPOTHESIS | those directories — cheap and exact |
| The pollution guard snapshots real state before and after every test | HYPOTHESIS | the conftest, **by symbol** |
| It was already narrowed once for a performance regression | HYPOTHESIS | its own docstring — ⛔ **and the reason to MEASURE rather than assume** |
| Two overlapping mechanisms mutate the same globals | HYPOTHESIS | both, **by symbol** — ⭐ **the interleaving hazard is reasoned, not observed; a reproduction would strengthen D6** |
| The three self-fixed findings are genuinely fixed | HYPOTHESIS | ⛔ **re-verify before relying on it** — the same review's findings have decayed in both directions |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D7 is the deliverable that verifies the plan.** A deliberately failing test **must** turn the
  result red. If it does not, nothing else in this plan matters.
- ⛔ **D2 must be demonstrated with a build that executes zero tests** — and the finding must survive.
  Verifying it against a normal build proves nothing, because a normal build runs tests.
- **D5's cost claim must be measured, not asserted.** Report the suite time before and after. "Low
  marginal value" is a judgement; the cost is a number.
- **D2's published population must be non-empty in a normal run** — a check that reports "0 tests
  counted" on a healthy build has replaced one vacuous signal with another.
- Test-harness changes are expected; the build gate takes its full path.

## Notes

- ⭐ **The recommended ordering, endorsed:** land test-integrity **first**, so the correctness plans in
  this epic inherit a trustworthy safety net. **That is the reason this plan is deliberately small.**
- ⛔ **Do not go looking for the orchestrator spec, the retired review document, the other plan's run
  record, or any landing record.** The first and last live under `.plan/`; the review is being retired
  and its surviving findings are transcribed above. Everything needed is in this file.
