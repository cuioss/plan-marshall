# PLAN-04: Enforcement Gates & Yardstick Re-Measurement

epic: test-suite-quality
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-04-enforcement-gates-and-measurement.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline. See `persona-marshall-orchestrator/standards/orchestration-model.md` for
> the tier and hand-off contract.

## Objective

Arm the pytest enforcement gates whose migration cost is provably zero **right now**, and close the
epic's measurement gap by re-taking both yardstick axes. This is deliberately the *cheap, safe* half
of the original PLAN-04: the dependency-bump half was split out to PLAN-06 because it crosses a
boundary with recorded empirical breakage and must not hold this work hostage.

Two things make this plan urgent rather than routine. First, the zero-cost proof is perishable — the
moment PLAN-06's dependency bump lands, pytest 9 / xdist / mypy deprecations will flood in and the
gates become expensive to arm. Second, `--durations=25` is the **unblocking prerequisite** for the
PLAN-05 capstone: without it, per-test hotspot attribution is unobtainable and PLAN-05 can only work
at module granularity.

## Re-Scope Record (2026-07-22)

This plan was re-scoped from the original `PLAN-04-runtime-dependency-modernization` before emission,
by operator decision. Deliverables 1–4 of that spec (dependency-cap lift, bump fallout, Python-floor
parity, runtime-floor documentation) moved to **PLAN-06**; deliverable 5 (the enforcement gates)
stayed here and grew the measurement deliverable.

**Why the split.** The original coupling was decided on 2026-07-21, when splitting the gates forward
was considered and rejected because *"`--strict-markers` would immediately fail the tree PLAN-02 is
about to rewrite"*. **That blocker has expired**: PLAN-02 registered the markers and PLAN-03 finished
rewriting the tree. Meanwhile `pyproject.toml:18-29` records that the bump target is *known-breaking*
(pytest 9 + xdist 3.8 "crashes xdist workers — node down: Not properly terminated"; xdist 3.8.0
"internal-errors (KeyError) aborting the whole session"). Coupling a zero-cost change to a
known-breaking migration risks losing both.

**Verified at `1cfa37044` before staging — enumerated, not inferred:**

| Premise | Status |
|---------|--------|
| Custom markers in use across the whole tree | **VERIFIED**: a sweep of `@pytest.mark.<name>` returns exactly `parametrize`, `skipif`, `usefixtures` (built-ins) and `xdist_group`. `xdist_group` and `allow_pollution` are both registered at `pyproject.toml:101-112`. `--strict-markers` therefore has **zero** migration cost |
| `--strict-markers` / `--strict-config` / `filterwarnings` / `--durations` absent | **VERIFIED**: `addopts = ["-v", "--tb=short"]` (`pyproject.toml:86`) carries none of them; no `filterwarnings` key exists |
| Stale suite-duration comment | **VERIFIED**: `pyproject.toml:88` still claims "~13 min" against a measured 137 s |

**LABELLED HYPOTHESIS — verify before sizing, do NOT treat as fact.** The claim *"0 warnings across
the suite, so `filterwarnings = ["error"]` costs nothing"* comes from the PLAN-01 baseline measured at
commit `b591b7d9`. That baseline is **stale**: the tree has since taken PLAN-02 (net −1099 lines) and
PLAN-03 (+741/−249), and the suite has grown 14 423 → 14 620 tests. The confirming artifact is a real
suite run, not the baseline document. Run the suite first and read the actual warning count; if
warnings now exist, clear them or record them and stage the clearing as a follow-up rather than
shipping a red gate.

## Deliverables

1. **Arm `filterwarnings = ["error"]`** in `[tool.pytest.ini_options]`, with per-item ignores only where
   a warning is genuinely out of the project's control. Precondition: measure the real warning count
   first (see the labelled hypothesis above). If the backlog is too large to clear inside this plan,
   record the count and stage the clearing as a follow-up — **do not ship a red gate**.

2. **Arm `--strict-markers` and `--strict-config`** in `addopts`. Verified zero-cost: `xdist_group` is
   the only custom marker in use and both registry entries are present. This converts the currently-clean
   state from luck into an invariant — without it, a single typo (`xdist_groupp`) silently loses worker
   pinning on exactly the concurrency tests that depend on it.

3. **Add `--durations=25`** so per-test hotspot attribution becomes possible, and **refresh the stale
   `pyproject.toml:88` comment** ("~13 min") against the real measured figure. Note `build.py`'s
   `cmd_module_tests` / `cmd_coverage` construct their pytest argv explicitly — confirm the flag
   actually reaches those paths, and add it there too if `addopts` does not cover them.

4. **Re-measure both yardstick axes and report the numbers.** The epic defines success as measurable
   gains in BOTH suite duration and coverage, and **both are currently unobserved across two
   consecutive plans** (PLAN-02 moved coverage but never re-took duration; PLAN-03 reported neither).
   Capture: total suite duration, line + branch coverage, pass/fail/skip/warning counts, and the top-25
   per-test durations now that deliverable 3 makes them available. **State the cache state explicitly**
   — `pm-plugin-development` has measured a ×9.7 warm/cold spread on an identical commit, so an
   unqualified before/after number is not comparable. Baseline to beat: **137 s** uninstrumented /
   **83.63 % line** / **78.01 % branch** at `b591b7d9`, and PLAN-03 removed ~13.2 s of unconditional
   sleeping that should show up here. Report the figures in the plan summary so the orchestrator can
   seed the epic's trend table.

## Expected Surface

Declared in full, including non-test files — PLAN-03's spec under-declared its surface and this
corrects that habit:

- `pyproject.toml` — `[tool.pytest.ini_options]` **only** (`addopts`, `filterwarnings`, the `:88` comment).
- `build.py` — only if `--durations` does not reach `cmd_module_tests` / `cmd_coverage` via `addopts`.
- Narrow test fixups **only** where arming a gate surfaces a genuine defect (e.g. a warning that proves
  a real bug). A broad test rewrite is out of scope — that work already shipped in PLAN-02/03.
- Possible: one analysis/summary artifact carrying the measurement figures.

**STRICTLY OFF-LIMITS** — this boundary is load-bearing; the equivalent declaration in PLAN-03 held
perfectly and is the reason that plan did not sprawl:

- **The dependency version caps** (`pytest>=8.0,<9`, `pytest-xdist>=3.0,<3.8`, `mypy>=1.10,<2` at
  `pyproject.toml:23-38`). These belong to PLAN-06. Do not lift, float, or "try" them — their comments
  record real observed breakage.
- **`requires-python`, `lock-python-version`, `[tool.mypy] python_version`** — the Python-parity
  question is PLAN-06's.
- **The marker registry** at `pyproject.toml:101-112` — shipped by PLAN-02, retained by design.

## Dependencies and Sequencing

- Depends on: PLAN-02 (marker registry) and PLAN-03 (tree rewrite complete) — **both shipped**, so this
  plan is unblocked.
- Precedes PLAN-06 (dependency bump): arming the gates while the warning backlog is provably near-zero
  is far cheaper than arming them after a major bump floods it.
- Precedes PLAN-05 (capstone): `--durations=25` is PLAN-05's prerequisite for per-test attribution.
- Surface disjointness: touches `[tool.pytest.ini_options]` only. Disjoint from PLAN-06's dependency
  block in the same file — but same-file, so **sequence rather than pair** them.

## Hand-Off Command

```text
/plan-marshall Arm the pytest enforcement gates whose migration cost is provably zero today, and close this epic's measurement gap by re-taking both yardstick axes. STRICTLY OFF-LIMITS: do NOT touch the dependency version caps in pyproject.toml (pytest>=8.0,<9, pytest-xdist>=3.0,<3.8, mypy>=1.10,<2) — their comments record real observed breakage (pytest 9 + xdist 3.8 crashes xdist workers with "node down: Not properly terminated"; xdist 3.8.0 internal-errors with a KeyError and aborts the session) and lifting them is a separate later plan; likewise do NOT touch requires-python, lock-python-version, [tool.mypy] python_version, or the marker registry at pyproject.toml:101-112. Deliver: (1) arm filterwarnings=["error"] in [tool.pytest.ini_options], but FIRST measure the real warning count with an actual suite run — the "zero warnings" figure comes from a stale baseline at commit b591b7d9 and the tree has since taken two large plans and grown to 14,620 tests, so treat zero-warnings as a hypothesis to verify, not a fact; add per-item ignores only where a warning is genuinely outside the project's control, and if the backlog is too large to clear here, record the count and stage the clearing as a follow-up rather than shipping a red gate; (2) arm --strict-markers and --strict-config in addopts — this is verified zero-cost, since a whole-tree sweep of @pytest.mark.<name> returns only the built-ins parametrize/skipif/usefixtures plus xdist_group, and both xdist_group and allow_pollution are registered at pyproject.toml:101-112; without the flag a single typo like xdist_groupp silently loses worker pinning on exactly the concurrency tests that depend on it; (3) add --durations=25 so per-test hotspot attribution becomes possible, and refresh the stale comment at pyproject.toml:88 that still claims the suite runs in "~13 min" when it measures 137 seconds — note build.py's cmd_module_tests and cmd_coverage construct their pytest argv explicitly, so confirm the flag actually reaches those paths and add it there too if addopts does not cover them; and (4) re-measure BOTH yardstick axes and report the numbers in your summary — total suite duration, line and branch coverage, pass/fail/skip/warning counts, and the top-25 per-test durations now that (3) makes them available — stating the cache state explicitly, because pm-plugin-development has measured a 9.7x warm-versus-cold spread on an identical commit and an unqualified number is not comparable; the baseline to beat is 137 seconds uninstrumented, 83.63 percent line and 78.01 percent branch coverage at commit b591b7d9, and the immediately preceding plan removed about 13.2 seconds of unconditional sleeping that should be visible in the new figure. Resolve all build commands through the architecture-resolved executor and read the TOON status and errors after each build call.
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when the landing analysis is recorded at landings/PLAN-04.md}
