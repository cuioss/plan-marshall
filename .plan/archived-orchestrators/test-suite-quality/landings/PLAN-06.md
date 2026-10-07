# Landing Analysis: PLAN-06 — Runtime & Dependency Modernization

epic: test-suite-quality
workstream: WS-02
pr: #987 — merged as `183e4df40` (2026-07-22)

> Landing record. Claims corroborated against the real diff and the real `pyproject.toml`.
> The significant finding is that **two of the three cap rationales this plan was staged
> against were false** — including one I amplified into the plan's framing.

## Deliverable Fidelity vs Spec

Spec carried 4 deliverables; 3 shipped, by folding D4 (document the runtime floor) into D1. All
scope accounted for.

| Deliverable | Verdict | Corroboration |
|-------------|---------|---------------|
| 1. Establish CI's Python + reconcile declarations | shipped-as-specified | `lock-python-version` **deleted**; `UV_PYTHON = "3.12"` at `:54`; `requires-python = ">=3.12"` unchanged at `:7`; `doc/developer/build.adoc` +52 |
| 2. Lift pytest + xdist, absorb fallout | shipped-as-specified | `pytest>=9.0` (`:24`), `pytest-xdist>=3.8` (`:26`), now under `[dependency-groups].dev`; `uv.lock` +361 |
| 3. Lift mypy, absorb fallout | shipped-as-specified | `mypy>=1.10` uncapped (`:29`) |

**All four of the checks written into the resume anchor pass:**

1. **Hypothesis tested first** — yes; the bump-and-run established the failure surface before any
   fallout work.
2. **No re-pin** — the "partial honest migration" escape hatch went unused. No cap was silently
   reverted.
3. **No gate weakened** — verified directly: `addopts` still carries `--strict-markers`,
   `--strict-config`, `--durations=25` (`:110`) and `filterwarnings = ["error"]` (`:121`) survives
   with **zero** added ignore entries. No skip, no xfail.
4. **mypy surface bounded** — trivially, see below.

**Surface: 9 files.** `pyproject.toml`, `uv.lock`, `pw.lock`, `build.adoc`, one architecture
artifact, and exactly 4 test files — matching the "16 class-scoped fixtures across 4 files" root
cause. Spot-checked `test_architecture_refresh.py`: the fix is a clean `@classmethod` conversion,
not a suppression.

## The finding: two of three cap rationales were false

This plan was staged — by me — as a **KNOWN-BREAKING migration**, on the strength of the rationale
comments written into `pyproject.toml:18-38`. The outcome:

| Recorded rationale | Reality |
|--------------------|---------|
| "pytest 9 + xdist 3.8 crashes xdist workers (node down: Not properly terminated); loadscope KeyError aborts the session" | **Did not reproduce.** 10/10 workers under LoadGroupScheduling, no node-down, no KeyError |
| "mypy 2.x is stricter and surfaces pre-existing latent findings across the tree" | **Guarded a hypothetical.** Removing `<2` re-resolves the *identical* mypy 1.20.2 — no 2.x exists. The cap was never binding |
| `lock-python-version = "3.12"` pins the interpreter | **Never honoured.** Pyprojectx consumes it at exactly one site (`lock.py:64`, `uv pip compile --python-version` — lockfile resolution only); `env.py:64-73` hardcodes the venv interpreter from whatever `python3` invoked `./pw` |

The real fallout was a **third thing nobody predicted**: 73 setup errors from one root cause — 16
class-scoped fixtures declared as instance methods, which pytest 9 stopped tolerating. The
`assert not self._finalizers` shape was a cascade of that same defect, not a second failure mode.

### What this says about the orchestrator's framing — recorded against itself

I amplified those comments into "plan for breakage as the expected case" and "budget the
`filterwarnings` flood as likely the largest single source of work." **There was no flood** — the
zero-warning census held through a two-major bump — **and no crash.**

This is the *mirror image* of the PLAN-03 error, and the same root cause. There I under-verified a
population and under-scoped a premise; here I over-trusted a recorded rationale and over-scoped the
risk. Both are the same defect: **treating a recorded claim as ground truth.** A comment in a
tracked file is provenance, not proof — it records what someone observed once, under conditions
that may no longer hold, and it ages exactly like an analysis document does.

The harm was low (over-caution is cheap, and the plan proceeded cleanly), so this is recorded as a
calibration finding rather than a defect. But the asymmetry is worth naming: this epic has now
produced one under-scope and one over-scope from the identical failure to distinguish observed
from recorded.

### And the crash's *absence* is still not attributed

The staged spec carried a labelled hypothesis: PLAN-03's isolation repairs may have removed the
xdist worker-crash cause. **The crash did not reproduce — but that does not confirm the
hypothesis.** Equally consistent: xdist 3.8.0 fixed it upstream, or the original diagnosis was
wrong, or the crash was environment-specific. Attributing the clean result to PLAN-03 would be
exactly the inference-as-fact move this epic keeps catching. Recorded as **unattributed**; the
hypothesis is neither confirmed nor refuted, and nothing downstream should lean on it.

## Metrics and Anomalies

- Tokens **2.89 M**; **2 h 32 m worked / 4 h 59 m wall / 2 h 26 m idle**. Three `[BUDGET]` warnings:
  ~5.9× the per-file token threshold over a 9-file footprint. Mitigating and accepted: the fallout
  was measured twice (once on 3.14, then corrected on 3.12), the uv restructure was accepted scope
  expansion, and **1 h 22 m of wall-clock was parked on the merge lock**.
- `6-finalize` again the outlier: **1.06 M tokens (37 % of the plan) over 2 h 32 m wall with 2 h 2 m
  idle**. **Fourth consecutive observation** across diffs of 75, 28, 1 and 9 files — the
  independence of finalize cost from diff size is now well-evidenced.

## Routing and Merge Behavior

- Merged clean at `183e4df40`; main up-to-date, worktree removed, tree clean, plan archived.
- The build daemon restart landed before this run, so outer build status was trustworthy — the
  job-log workaround PLAN-04 needed was not required.
- **Self-correction worth recording as a positive precedent**: the plan fed its executor a wrong
  premise (that pyprojectx honours `lock-python-version`), the executor **refused to build on it**
  after observing py3.14, and the already-committed `build.adoc` claim was corrected as its own
  commit before anything else shipped. A downstream consumer refusing a bad premise is the
  consumer-side half of lesson `2026-07-21-22-001` working as designed.

## Reconciliation Actions

- [x] status.json `plans[]` PLAN-06 → `shipped`
- [x] epic.md queue row reconciled
- [x] Baselines & Trend § — row added (no re-measurement taken; toolchain-shift row)
- [x] Watch **retired**: toolchain-shift risk (PLAN-04-era) — the bump landed clean
- [x] Watch added: **recorded rationales in tracked files are provenance, not proof**
- [x] Watch added (out-of-epic): two retrospective-tooling bugs
- [x] Open decision surfaced to the operator: `filterwarnings` local non-determinism
- [x] resume_anchor updated; START-HERE regenerated

## Open item carried to the operator

**`filterwarnings = ["error"]` makes the LOCAL build non-deterministic** via pytest's own tmpdir
GC (`rm_rf` warning during garbage collection) — lesson `2026-07-22-20-001`. Pre-existing,
unreachable in CI, and **deliberately not absorbed**: an `rm_rf` ignore would also suppress genuine
resource-leak signals. That judgment is sound.

But it is **not** merely a standing annoyance for this epic: **PLAN-05 is a measurement plan**, and
a locally non-deterministic build is a direct threat to the one deliverable it exists to produce.
This must be resolved or explicitly scoped before PLAN-05 is emitted.

## Follow-Ups

- **Out-of-epic — two retrospective-tooling bugs found by the retrospective in itself:**
  - `2026-07-22-22-001` — `check-artifact-consistency`'s affected-files regex cannot match the
    canonical `` - `path` `` (intent) bullet, producing a **double false green**: coverage reports
    `declared: 0`, then the strict peer compares ∅ vs ∅ and passes. **The declared-vs-achieved
    assertion was never actually made.** Note this does not undermine this epic's surface-fidelity
    conclusions — those were reached by reading the real diffs directly, not from that check.
  - `2026-07-22-22-002` — `check-routing-decisions` infers *why* a step was pruned from the fact
    that it is absent, yielding a spurious `mis_prune:sonar-roundtrip` FAIL when the posture tier
    legitimately dropped it.
- **CI's 3.12 is mechanism-verified, not runtime-observed** (finding `8e51fc`): `ci checks logs`
  returns failed-job logs only, so a green run yields nothing to read. Honest caveat, correctly
  recorded rather than smoothed over. Low risk — the mechanism (`UV_PYTHON`) is deterministic — but
  a future green-run log surface would close it properly.
