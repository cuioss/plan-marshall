# PLAN-05: Measurement Protocol & Duration/Coverage Remediation

epic: test-suite-quality
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-05-duration-coverage-remediation.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline. See `persona-marshall-orchestrator/standards/orchestration-model.md` for
> the tier and hand-off contract.

## Objective

The epic's capstone. Establish a **measurement protocol that can actually detect the effects this
campaign produces**, then use it to deliver and *demonstrate* gains in suite duration and coverage.

The original charter — "convert the baseline into demonstrable duration+coverage gains" — was written
before the epic knew its own instrument was too coarse. It has been amended: **protocol first, then
optimization.** Optimizing against an instrument that cannot see the result would produce unfalsifiable
claims, which is the one outcome this epic must not ship.

## Re-Scope Record (2026-07-22)

Amended before emission on evidence from PLAN-04 and PLAN-06, plus a direct CI-history analysis.

### Why the original charter was unachievable

| Finding | Evidence |
|---------|----------|
| **Local wall-clock carries a ~59 s noise floor** | PLAN-04 measured the identical tree at 210.50 s cold → 151.69 s warm. That 58.8 s swing is **4.5× the ~13.2 s** PLAN-03 removed |
| **CI wall-clock is relatively steadier but absolutely noisier** | `verify / verify` across PRs #966/#977/#982/#985/#986/#987: **446, 463, 477, 494, 456, 484, 378, 476 s** — a 116 s range, ~25 % of mean |
| **The instrument has already failed once, demonstrably** | #966 → #977 spans the whole of PLAN-03's sleep removal and went **up** 17 s |
| **Per-test normalization does not rescue it** | 9.50 → 10.25 ms/test still compares two single runs at unrecorded cache states |

**Why CI's job duration is a *less* sensitive instrument than it looks:** `verify / verify` includes
checkout, uv resolution, install, mypy, ruff, tests *and* coverage. The pytest portion is diluted by
fixed overhead that itself varies with runner hardware and network.

**But CI is still the right surface — for free repetition, not for single comparisons.** Every PR
yields one or two samples in a controlled environment at zero marginal cost. That is a *distribution*,
which detects a trend; single before/after attribution is what is impossible.

### Confounds that must be annotated, not silently spanned

- **PLAN-06 toolchain shift** (`183e4df40`): pytest 8 → 9.1.1, xdist → 3.8.0, and the interpreter is
  now deterministically **3.12.3** where local previously ran **3.14.6**. Any comparison spanning this
  point crosses both a toolchain and an interpreter change.
- **Suite growth**: 14 423 → 14 794 tests since baseline (+2.6 %). Raw wall-clock is not comparing
  like with like.
- **The `b591b7d9` baseline's cache state is unrecorded**, so 137 s is not a sound comparator at all.

### Standing discipline for this plan (both halves learned the hard way here)

- **Enumerate before sizing.** PLAN-03 was under-scoped from an unverified population count
  (lesson `2026-07-21-22-001`, 5th occurrence). Verify every population this plan sizes work on.
- **Recorded rationales are provenance, not proof.** PLAN-06 falsified two of three cap rationales
  written into `pyproject.toml`, and the orchestrator over-scoped that plan by amplifying them. The
  PLAN-01 hotspot list is now **two weeks and four plans old** — re-derive from live data, do not
  trust it.

## Deliverables

1. **Remove the local-build non-determinism via a per-session `--basetemp`** (operator decision;
   closes the epic's one open defect). `filterwarnings = ["error"]` promotes pytest's own tmpdir-GC
   `PytestWarning` — `(rm_rf) error removing .../pytest-of-{user}/garbage-<uuid>`,
   `OSError [Errno 66] Directory not empty` — into a session-killing exception **after every test has
   already passed**, so a fully green suite reports as a failed build (lesson `2026-07-22-20-001`).
   It fires when a prior session was killed mid-flight or two sessions GC the shared root
   concurrently. **Fix the race, do not silence the symptom**: give each invocation a unique
   basetemp so sessions never share the root. Do **not** add an `rm_rf` ignore entry — that was
   considered and rejected because it would also blind the suite to genuine resource-leak evidence.
   Keep the gate fully armed. Note this forgoes pytest's keep-last-3-runs retention; ensure the
   per-session dirs do not accumulate unboundedly.

2. **Establish and document the measurement protocol.** It must be repeatable by someone who was not
   here. At minimum: (a) **trend** from CI `verify / verify` history — `ci checks status` exposes
   `elapsed_sec` per job without needing logs, so samples are free and already accumulating — using
   a **median of N ≥ 5**, never a single run; (b) **attribution** from `--durations=25` per-test
   tables, which are nearly immune to the fixed overhead that ruins wall-clock; (c) an explicit
   statement of what effect size the protocol can and cannot resolve. If the honest answer is that a
   sub-20 s suite-level effect is undetectable, **say so** — a documented detection limit is a real
   deliverable and is worth more than a number nobody can reproduce.

3. **Re-derive the hotspot targets from live per-test data.** PLAN-01's list was module-granularity
   and predates four plans. Use the `--durations=25` table (slowest single test measured at 12.84 s)
   to pick real targets, then fix their specific causes — over-broad fixtures, unnecessary subprocess
   spawns, real sleeps, session-vs-function scope misuse — **without losing assertions**. Prefer
   per-test before/after evidence over suite wall-clock claims.

4. **Fill the highest-value coverage gaps**, targeting behavior not implementation per
   `pm-dev-python:pytest-testing`. Coverage is the axis that *is* reliably measurable (83.63 → 83.85 %
   line has tracked cleanly all campaign), so this is where a demonstrable gain is genuinely
   available. The four sub-threshold modules from the baseline — `pm-dev-java` 58.29 %,
   `pm-dev-java-cui` 70.83 %, `pm-documents` 77.22 %, `pm-dev-frontend` 79.83 % — are the natural
   targets; **re-derive their current values first**, since three plans have landed since.

5. **Report the final numbers with their confounds stated**, and keep the quality gate green. Every
   figure carries its cache state, its sample count, and an explicit annotation where it spans the
   PLAN-06 toolchain/interpreter shift. **A bounded or negative result, honestly reported, is an
   acceptable outcome for the duration axis** — the epic would rather ship a truthful "not detectable
   at this fidelity, here is the limit" than an unfalsifiable win.

## Expected Surface

Declared in full, including non-test files:

- `build.py` and/or `pyproject.toml` — the per-session basetemp mechanism (D1).
- Broad `test/**` — hotspot fixes (D3) and coverage additions (D4).
- Likely a documentation artifact for the protocol (D2) — `doc/developer/` or an epic-local analysis
  doc; the plan should say which and why.
- **OFF-LIMITS**: the armed gates (`filterwarnings`, `--strict-markers`, `--strict-config`,
  `--durations`), the marker registry, and the dependency declarations from PLAN-06. If a gate fails,
  fix the cause — never disarm.

## Dependencies and Sequencing

- Depends on: PLAN-04 (armed `--durations`, first real measurement) and PLAN-06 (final toolchain —
  measured gains must reflect the end state, not one that later shifts). Both shipped.
- **Last plan in the epic.** After it lands, the epic closes.

## Hand-Off Command

```text
/plan-marshall Capstone for the test-suite-quality epic: establish a measurement protocol that can actually detect this campaign's effects, then deliver and demonstrate gains. PROTOCOL FIRST, THEN OPTIMIZATION — the original charter said "convert the baseline into demonstrable duration gains", and that was amended because the epic proved its own instrument too coarse: local wall-clock carries a ~59s noise floor (the identical tree measured 210.50s cold versus 151.69s warm, a swing 4.5x larger than the ~13.2s of sleeping a previous plan removed), and CI verify job durations across recent PRs run 446, 463, 477, 494, 456, 484, 378 and 476 seconds — a 116s range, about 25 percent of the mean. The instrument has already failed once demonstrably: the PR span covering the entire sleep removal went UP 17 seconds. Deliver: (1) remove the local-build non-determinism by giving each pytest invocation a PER-SESSION --basetemp — filterwarnings=["error"] promotes pytest's own tmpdir-GC warning ((rm_rf) error removing .../pytest-of-{user}/garbage-<uuid>, OSError Errno 66 Directory not empty) into a session-killing exception AFTER every test has already passed, so a fully green suite reports as a failed build; it fires when a prior session was killed mid-flight or two sessions garbage-collect the shared root concurrently; FIX THE RACE, DO NOT SILENCE THE SYMPTOM — do not add an rm_rf ignore entry, that was considered and rejected because it would also blind the suite to genuine resource-leak evidence, and keep the gate fully armed; ensure the per-session directories do not accumulate unboundedly since this forgoes pytest's keep-last-3-runs retention; (2) establish and DOCUMENT a repeatable measurement protocol — trend from CI verify-job history (ci checks status exposes elapsed_sec per job without needing logs, so samples are free and already accumulating) using a median of at least 5 runs and never a single run, attribution from --durations=25 per-test tables which are nearly immune to the fixed overhead that ruins wall-clock, and an explicit statement of what effect size the protocol can and cannot resolve — if the honest answer is that a sub-20-second suite-level effect is undetectable then SAY SO, because a documented detection limit is a real deliverable worth more than a number nobody can reproduce; (3) re-derive the hotspot targets from live per-test data rather than the two-week-old module-granularity list (slowest single test measured 12.84s), then fix their specific causes — over-broad fixtures, unnecessary subprocess spawns, real sleeps, session-versus-function scope misuse — without losing assertions, preferring per-test before/after evidence over suite wall-clock claims; (4) fill the highest-value coverage gaps with behavior-focused tests per pm-dev-python:pytest-testing, since coverage is the axis that IS reliably measurable — the four sub-threshold modules were pm-dev-java 58.29, pm-dev-java-cui 70.83, pm-documents 77.22 and pm-dev-frontend 79.83 percent, but RE-DERIVE their current values first because three plans have landed since; and (5) report final numbers with confounds stated — every figure carries its cache state, its sample count, and an explicit annotation where it spans the recent toolchain shift (pytest 8 to 9.1.1, xdist to 3.8.0, interpreter now 3.12.3 where local previously ran 3.14.6), and note the suite has grown 14423 to 14794 tests so raw wall-clock is not comparing like with like; A BOUNDED OR NEGATIVE RESULT HONESTLY REPORTED IS AN ACCEPTABLE OUTCOME for the duration axis. Two standing disciplines this epic learned the hard way: enumerate every population before sizing work on it, and treat recorded rationales in tracked files as provenance rather than proof — re-verify anything you inherit from an older analysis document. Do NOT touch the armed gates (filterwarnings, --strict-markers, --strict-config, --durations), the marker registry, or the dependency declarations; if a gate fails, fix the cause, never disarm. Resolve all build commands through the architecture-resolved executor and read the TOON status and errors after each build call.
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when the landing analysis is recorded at landings/PLAN-05.md}
