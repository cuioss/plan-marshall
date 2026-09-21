# PLAN-06: Runtime & Dependency Modernization

epic: test-suite-quality
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-06-runtime-dependency-modernization.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline. See `persona-marshall-orchestrator/standards/orchestration-model.md` for
> the tier and hand-off contract.

## Objective

Lift the capped test/type-check dependencies across their major boundaries and resolve the
local-vs-CI Python-version divergence, so the suite runs on a current, pinned toolchain with local
and CI resolving the same interpreter.

Split out of the original PLAN-04 on 2026-07-22 (operator decision). The enforcement gates that were
bundled with it moved to the re-scoped PLAN-04 and ship first, because their migration cost is
provably near-zero today and becomes expensive the moment this bump lands.

## Framing: this is a KNOWN-BREAKING migration, not a routine bump

The original spec directed "lift each to its current latest major and pin" as though routine. The
file it would edit says otherwise, and this is the single most important input to the plan:

> `pyproject.toml:18-22` — *"pytest 9 + xdist 3.8 on the CI Python crashes xdist workers ('node down:
> Not properly terminated') on pre-existing tests. Adopting pytest 9 is a deliberate migration, not a
> transitive consequence of a plugin bump."*
>
> `pyproject.toml:25-28` — *"the floated 3.8.0 crashes workers ('node down: Not properly terminated')
> and then its loadscope scheduler internal-errors (KeyError &lt;WorkerController&gt;) aborting the whole
> session."*
>
> `pyproject.toml:32-37` — *"mypy 2.x is stricter and surfaces pre-existing latent findings across the
> tree; adopting it is a deliberate project-level decision."*

**Plan for breakage as the expected case.** Budget the work accordingly, and treat "the bump is clean"
as the surprise, not the baseline.

**NEW since this spec was staged — the gates are now armed, and that raises the bar.** PLAN-04
(#982, `4002bedb1`) armed `filterwarnings = ["error"]` (`pyproject.toml:97`) plus `--strict-markers`
and `--strict-config` on a measured census of **0 warnings across 14 794 tests**. Consequence for this
plan: **every deprecation the bump emits is now a hard test failure, not a warning.** That is precisely
the flood the caps' own comments predict from pytest 9 / mypy 2.x, and it is *deliberate* — it makes
the migration's true cost visible at the commit that incurs it instead of letting it accumulate
silently. Do not read those failures as a broken gate. The response is to fix the cause, or add a
narrowly-scoped `ignore:{message-prefix}:{Category}:{module}` entry with a recorded rationale —
**never a bare `ignore::SomeWarning`, and never disarming the gate.** Budget for this explicitly: it
is likely to be the single largest source of work in deliverable 2.

**Also new — the build daemon is trustworthy again.** The pre-fix `marshalld` supervisor that forced
PLAN-04 to read job-log verdicts instead of outer build status was fixed by #979, and the daemon has
been restarted on 0.1.1192 (verified). Outer build status can be trusted this run — but the standing
rule that `pyproject_build` exits 0 on failure still applies, so keep reading the TOON
`status` / `errors[]`.

**LABELLED HYPOTHESIS — worth testing early, but do NOT assume it.** The recorded xdist crash signature
("node down: Not properly terminated", worker teardown instability) is *plausibly* related to the
test-isolation defects PLAN-03 has since repaired — ~520 teardown errors were eliminated, the `_test_env`
singleton is gone, and cwd leakage now fails loudly. It is therefore possible the bump now succeeds
where it previously did not. **This is an inference, not a finding.** The confirming artifact is an
actual bump-and-run, and it should be the plan's first experiment because a clean result collapses
most of the plan's risk. If it still crashes, the isolation-repair theory is refuted and the migration
needs real per-failure work.

## Deliverables

1. **Attempt the bump and characterize the result.** Lift `pytest` (`>=8.0,<9`), `pytest-xdist`
   (`>=3.0,<3.8`), and `mypy` (`>=1.10,<2`) to current latest majors, re-resolve the pyprojectx env,
   and run the full suite + quality gate. Record precisely what breaks — per failure mode, not as an
   aggregate — so deliverable 2 is sized on an enumeration rather than an impression.
2. **Absorb the fallout.** Fix what the bump surfaces: mypy 2.x's stricter findings, and any pytest 9 /
   xdist behavior changes. If a failure class proves too large to land here, pin *that one* dependency
   with a comment recording the specific observed failure (matching the existing comment convention)
   and stage it separately — a partial, honest migration beats a red gate or a silently-reverted cap.
3. **Resolve the Python-floor / CI-parity question.** Pre-verified leads, current at `1cfa37044`:
   `pyproject.toml` declares `requires-python = ">=3.12"`, `lock-python-version = "3.12"`, and mypy
   `python_version = "3.12"`; there is **no** `.python-version` or `.tool-versions` pin in the repo;
   local `python3` is **3.14.6**. So the local/CI divergence is an out-of-band interpreter or venv
   artifact, not a repo declaration. **Note the spec's original framing was incomplete: CI's Python is
   not declared in this repo at all** — `.github/workflows/python-verify.yml` delegates to the external
   reusable workflow `cuioss/cuioss-organization/.github/workflows/reusable-pyprojectx-verify.yml`
   pinned at `6278bbd`. Read that workflow to establish what CI actually runs before concluding
   anything about parity.
4. **Document the resolved runtime floor** and reconcile whatever declarations are needed so local and
   CI resolve the same interpreter.

## Expected Surface

Declared in full, including non-test files:

- `pyproject.toml` — the `[tool.pyprojectx.main] requirements` block, and `requires-python` /
  `lock-python-version` / `[tool.mypy] python_version` if the parity work warrants a change.
- **Production source across `marketplace/bundles/**`** — expect this. mypy 2.x's stricter checks
  surface findings in real modules, and its comment explicitly predicts "pre-existing latent findings
  across the tree". This is the deliverable-2 surface and it may be broad.
- Narrow test fixups where pytest 9 / xdist behavior changes break a test.
- Possibly a developer-doc note recording the runtime floor.

**OFF-LIMITS:**

- `[tool.pytest.ini_options]` gates armed by PLAN-04 (`filterwarnings`, `--strict-markers`,
  `--strict-config`, `--durations`) and the marker registry. If the bump makes an armed gate fail, fix
  the cause or add a *targeted* per-item ignore with a recorded rationale — **never disarm the gate**.
- Broad test rewrites — that work shipped in PLAN-02/03.

## Dependencies and Sequencing

- Depends on: PLAN-04 (gates armed while cheap). Also benefits from PLAN-03's isolation repairs, which
  are the basis of the labelled hypothesis above.
- Precedes PLAN-05 (capstone): the capstone must measure on the FINAL pinned toolchain, so the bump
  must land before it. This preserves the 2026-07-21 sequencing decision.
- Same-file contention with PLAN-04 (`pyproject.toml`) — **sequence, do not pair**.

## Hand-Off Command

```text
/plan-marshall Modernize the plan-marshall test/build toolchain in pyproject.toml and resolve the local-versus-CI Python divergence. IMPORTANT CONTEXT ON THE CURRENT GATE STATE: the immediately preceding plan armed filterwarnings=["error"] at pyproject.toml:97 plus --strict-markers and --strict-config, on a measured census of zero warnings across 14794 tests — so every deprecation this bump emits is now a HARD TEST FAILURE rather than a warning. That is exactly the flood the dependency caps predict from pytest 9 and mypy 2.x, and it is deliberate: it makes the migration's true cost visible at the commit that incurs it. Do NOT read those failures as a broken gate and do NOT disarm it — fix the cause, or add a narrowly-scoped ignore:{message-prefix}:{Category}:{module} entry with a recorded rationale, never a bare ignore::SomeWarning. Budget for this as likely the largest single source of work. The build daemon was restarted on the post-fix binary so outer build status is trustworthy again, but pyproject_build still exits 0 on failure, so keep reading the TOON status and errors after every build call. TREAT THIS AS A KNOWN-BREAKING MIGRATION, not a routine bump: the file's own comments record the observed failures — "pytest 9 + xdist 3.8 on the CI Python crashes xdist workers (node down: Not properly terminated) on pre-existing tests", "the floated xdist 3.8.0 crashes workers and then its loadscope scheduler internal-errors (KeyError WorkerController) aborting the whole session", and "mypy 2.x is stricter and surfaces pre-existing latent findings across the tree". Plan for breakage as the expected case. One hypothesis worth testing FIRST, but which you must NOT assume: the recorded xdist crash signature is plausibly related to the test-isolation defects a previous plan has since repaired (about 520 teardown errors eliminated, a module-level test-environment singleton removed, cwd leakage now failing loudly), so the bump may now succeed where it previously did not — the confirming artifact is an actual bump-and-run, and doing it first collapses most of the plan's risk if it comes back clean. Deliver: (1) lift pytest (now >=8.0,<9), pytest-xdist (now >=3.0,<3.8) and mypy (now >=1.10,<2) to their current latest majors, re-resolve the pyprojectx env, run the full suite and quality gate, and record precisely what breaks per failure mode rather than as an aggregate so the next deliverable is sized on an enumeration; (2) absorb the fallout — mypy 2.x stricter findings and any pytest 9 or xdist behavior changes — and if one failure class proves too large to land here, re-pin that single dependency with a comment recording the specific observed failure in the same convention as the existing comments and stage it separately, because a partial honest migration beats a red gate or a silently reverted cap; (3) resolve the Python-floor and CI-parity question, noting these verified leads: pyproject already declares requires-python=">=3.12", lock-python-version="3.12" and mypy python_version="3.12", there is no .python-version or .tool-versions pin in the repo, and local python3 is 3.14.6, so the divergence is an out-of-band interpreter or venv artifact rather than a repo declaration — and note that CI's Python is NOT declared in this repository at all, since .github/workflows/python-verify.yml delegates to the external reusable workflow cuioss/cuioss-organization/.github/workflows/reusable-pyprojectx-verify.yml pinned at 6278bbd, so read that workflow to establish what CI actually runs before concluding anything about parity; and (4) document the resolved runtime floor and reconcile whatever declarations are needed so local and CI resolve the same interpreter. Do NOT touch the [tool.pytest.ini_options] enforcement gates (filterwarnings, --strict-markers, --strict-config, --durations) or the marker registry — if the bump makes an armed gate fail, fix the cause or add a targeted per-item ignore with a recorded rationale, never disarm the gate. Resolve all build commands through the architecture-resolved executor and read the TOON status and errors after each build call.
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when the landing analysis is recorded at landings/PLAN-06.md}
