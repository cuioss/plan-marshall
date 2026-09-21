# History — Epic: Unit-Test Suite Quality & Cleanup

**slug**: `test-suite-quality` · **closed**: 2026-07-28 · **outcome**: 10 of 10 plans shipped

> ⚠ **This record SUPERSEDES the 2026-07-24 close.** That close was written while PLAN-10 was
> still outstanding and before WS-03 existed, and it waved four verified defects through as
> "out-of-epic". The epic was reopened on 2026-07-25 by operator decision on exactly that
> ground — *"deferring known, verified defects is how they evaporate"* — and WS-03's four
> plans (#998, #1012, #1026, #1036) closed them. The reopen was correct and this record is
> the authoritative one.

> Frozen record of a closed epic. The live tree (`epic.md`, `status.json`, `landings/`,
> `plans/`, `logs/`) remains on disk untouched — close freezes, never deletes. This document is
> the derived summary; where it and `status.json` disagree, `status.json` was the machine
> authority at close.

## Vision as pursued

Raise the plan-marshall Python test suite (`test/**`, ~14 400 tests across 149 marketplace
components) to a uniform, standards-compliant, low-redundancy baseline with unified
bootstrapping and shared fixtures — a campaign too large for one plan.

"Done" was defined as: an actionable redundancy/fixture/bootstrapping map; test packages
compliant with `pm-dev-python:pytest-testing`; unified bootstrapping and fixtures; the
parallel-plan hardening patterns propagated suite-wide; **and measurable gains in BOTH suite
duration and coverage**.

**Nine tenths of that was delivered as written. The duration half of the success criterion was
not — and the epic's most important methodological outcome is that it refused to fake it.**
See "The measurement arc" below.

## Final queue outcome — 10 shipped, 0 dropped, 0 parked

| # | Plan | WS | PR | Outcome |
|---|------|----|----|---------|
| 1 | scrupulous-test-suite-analysis | WS-01 | #955 | Shipped 4/4. Scope gap (baseline + cleanup-scout) closed out-of-band by #960 |
| 2 | test-standards-compliance | WS-02 | #966 | Shipped 14/14 against a 5-deliverable spec — ×2.8 growth, the epic's cautionary no-split case |
| 3 | propagate-parallel-plan-hardening | WS-02 | #977 | Shipped 7/5 — a *decomposition*, not growth. Skip guards 39→15; ~13.2 s of sleeping removed |
| 4 | enforcement-gates-and-measurement | WS-02 | #982 | Shipped 3/4 (D1+D2 merged into a better census-then-arm pair). All four gates armed. Most efficient plan (1.90 M tokens) |
| 5 | runtime-dependency-modernization | WS-02 | #987 | Shipped. All three caps lifted, no re-pin, no gate weakened. **Two of three cap rationales were false** |
| 6 | duration-coverage-remediation | WS-02 | #992 | **CAPSTONE.** Shipped 8/5. 4 modules lifted; measurement protocol with an explicit detection limit |
| 7 | unit-test-truthfulness | WS-03 | #1012 | Shipped 5/5, net −4173/+168 across 56 files |
| 8 | finalize-dispatch-audit-integrity | WS-03 | #1026 | Shipped 6/6 (4 staged + 2 dogfooding). Most expensive plan (3.5 M tokens) |
| 9 | retrospective-check-correctness | WS-03 | #998 | Shipped 5/5, each with a fail-when-voided regression test |
| 10 | retrospective-completeness-and-phase5-marker | WS-03 | #1036 | Shipped 4/4. **The outline refuted three of its own spec's asserted facts** |

Workstreams: **WS-01** Discovery & Analysis (1) · **WS-02** Remediation (5) · **WS-03**
Carried-Lead Remediation (4, added at the 2026-07-25 reopen).

## What was demonstrably achieved

- **Coverage up, with four modules lifted**: `pm-dev-java` 56.87 → 76.78, `pm-dev-java-cui`
  64.71 → 82.35, `pm-documents` 76.35 → 80.33, `pm-dev-frontend` 76.82 → 82.40 — three of four
  clearing the 80 % gate (java stops at 76.78 by design; residual is defensive glue).
  Suite-level 83.63 → 83.85 line / 78.01 → 78.32 branch.
- **Four enforcement gates armed** (`filterwarnings=["error"]`, `--strict-markers`,
  `--strict-config`, `--durations=25`) — and armed only *after* measuring 0 warnings across
  14 794 tests, never on assumption.
- **Isolation and determinism**: skip guards 39 → 15 (survivors are genuine environment
  guards), the `_test_env` singleton removed, ~13.2 s of unconditional sleeping defused,
  per-session `--basetemp` closing the shared-root GC race **at its source** rather than
  silencing it.
- **Toolchain modernized**: pytest 8 → 9.1.1, xdist → 3.8.0, mypy uncapped, interpreter
  deterministically 3.12.3. No gate weakened, no skip or xfail added.
- **~5 100 lines of dead and duplicated test code deleted**, including two never-collected
  tiers already sitting in `collect_ignore`.
- **A documented measurement protocol** (`doc/developer/measurement-protocol.adoc`) that states
  its own sub-20 s detection limit.

## The measurement arc — the epic's central methodological outcome

The success criterion demanded gains in **both** duration and coverage. Half of it turned out
not to be answerable as posed, and establishing that took four plans:

1. **PLAN-04** measured the identical tree at **210.50 s cold / 151.69 s warm** — a **58.8 s
   cache-state swing, 4.5× the entire ~13.2 s saving PLAN-03 had just delivered**.
2. A CI investigation confirmed no escape: `verify / verify` spans 378–494 s across eight
   samples (~25 % of mean), and the #966→#977 pair — which brackets the whole of PLAN-03's
   sleep removal — went **up** 17 s.
3. **PLAN-05, the capstone, resolved the tension by refusing to overclaim**: it authored a
   protocol stating an explicit detection limit and reported the suite-level duration delta as
   *below* it.

**Coverage is the demonstrated gain; duration is honestly bounded.** That is a better ending
than a fabricated wall-clock win, and the amended PLAN-05 charter was written to produce it —
it sanctioned in advance that *"a bounded or negative result, honestly reported, is an
acceptable outcome for the duration axis"*.

## The recurring defect archetypes this epic identified

The campaign's durable output is arguably not the test-suite state but the archetype catalogue:

- **Vacuous guards** — a predicate that cannot take the other value where it is read. **Five
  occurrences**, one of them introduced *by a fix for the archetype*, and PLAN-10's D2 was a
  textbook case (`phases[5-execute].status == "pending"`, already falsified by the preceding
  transition).
- **Recorded-claim-as-ground-truth** (`2026-07-21-22-001`) — hit on **six distinct surfaces**:
  an analysis document, a `pyproject.toml` rationale comment, a plan's own PR body, two phantom
  lesson IDs in orchestrator-staged specs, and a plan's review self-report.
- **A confident signal hiding a caveat** — the epic's own theme, and it kept appearing *inside
  the instruments built to detect it*: a green "Review finished" from a rate-limited bot, a
  0 % coverage score that meant "not measured", a decision-log line that read like a
  measurement but described the clock.
- **Volume read as coverage** — "N candidates examined" is a volume, not a coverage number.
- **A reviewer's list of call sites is a SAMPLE, not an enumeration.**

**Standing rule adopted and repeatedly re-earned: every set-guarding detector MUST be
population-derived** (`test/_shared/_dispatch_roster.py` is the reference shape). PLAN-10's
landing shows why it is still not sufficient — a correctly-derived population can carry a
**stale non-degeneracy anchor**, which is exactly what three of its own new detectors did.

## Errors recorded against this orchestrator

Kept in the record deliberately — they are the calibration data:

1. **PLAN-03 under-scope** — sized a migration from symptom volume (~520 teardown errors)
   instead of an enumeration; ground truth was 235 `monkeypatch.chdir` vs 11 raw `os.chdir`,
   so the directed work would have been a near-total no-op.
2. **PLAN-06 over-scope** — amplified `pyproject.toml`'s rationale comments into "plan for
   breakage as the expected case". Two of three rationales were false; there was neither flood
   nor crash. The mirror image of (1), identical root cause.
3. **Two phantom lesson IDs** serialized into staged specs *and* an emitted hand-off command
   without a store lookup — inside the very specs that bind lessons for retirement. **Rule
   adopted: resolve every lesson ID via `manage-lessons get` before staging.**
4. **PLAN-07 surface under-declaration** — named only `discover_modules/**` when
   `test/conftest.py`'s `collect_ignore` already enumerated all three dead files in one place.

The distinction that came out of (3) is worth carrying: **a lesson's absence is not evidence
its defect was fixed** — it refutes the binding only.

## Controls that demonstrably worked

- **Explicit off-limits declarations in specs.** Three consecutive plans honoured them exactly;
  PLAN-04's declared surface matched its actual diff file-for-file.
- **Verify-still-open before retiring a lesson.** Across four WS-03 plans, lesson dispositions
  were checked against the **live store**, never the plan's report — and it prevented false
  retirements three separate times (PLAN-09 trimmed 2, PLAN-07 correctly kept 1 active).
- **Corroborating landings against the diff, not the PR prose.** This caught PLAN-07's PR body
  describing a "revived" tier that the merged tree had **deleted**, which all three review bots
  missed.
- **Dogfooding — running the machinery against itself — was the highest-yield verification
  control available**, well ahead of automated review. PLAN-08 found four defects that way; the
  defect it was fixing cost it 5.5 % of its own token budget mid-run.

## Carried-forward leads — NOT resolved by this epic

**⚠ Three defects are LIVE in merged main at close.** They are listed here and in `epic.md`
§ Open Defects rather than deferred silently. **They need a home in the `truthful-signals`
epic — not a third reopen of this one.**

1. **Three confirmed CodeRabbit findings, untriaged** (#1036). The review posted **2m42s after
   the merge**; all 12 PR comments remain unresolved. Confirmed against merged main: a
   non-degeneracy anchor that omits the member the fix just added
   (`test_step_completion_emission.py:136-147`); a guard that skips rather than fails on a
   missing roster document (`test_registered_aspects_render.py:100-102`); and an assertion
   that does not bind to the artifact it verifies (`test_execute_phase_markers.py:64-65`).
   ⛔ **A fourth finding is CONTRADICTED and must not be actioned** — acting on it would break
   a working detector.
2. **`architecture-refresh` carries two classifications**, and the runtime obeys the
   non-authoritative one. The closure test opens both documents but never cross-checks them.
3. **`dispatch_boundaries` is a `SECTION_SPEC` row no producer can fill** — the mirror
   direction of the defect PLAN-10's D1 closed, failing quietly into the benign bucket while
   carrying the report's largest payload.

**Structural findings needing an owner** (all filed as corpus lessons):

- **No plan can self-verify a finalize-pipeline fix** (`2026-07-28-19-005`) — `plan-retrospective`
  at step 17 runs after `branch-cleanup` destroys its input and before `sync-plugin-cache`
  makes the plan's own code live. This is the measurement floor of the entire epic.
- **A rate-limited bot's review arrives after the merge** (`2026-07-28-19-002`) — twice
  consecutively, so causal rather than coincidental.
- **Markdown under `marketplace/bundles/` is a build input** (`2026-07-28-19-007`) — and this
  **corrects** a fix proposed twice in `2026-06-20-16-002`; adopting that doc-only exemption
  would ship a false green.
- **The lane router's pre-override input is unrecoverable** (`2026-07-28-19-004`).
- **`architecture-refresh` dual classification** (`2026-07-28-19-003`).
- **Detector anchors go stale when the fix widens the population** (`2026-07-28-19-006`).
- **Compose-time footprint pruning is vacuous** (`2026-07-27-23-003`, now with a verbatim
  second occurrence) — the pre-push quality gate is protected only by `finalize.qgate=always`
  coincidentally being set.

**Out-of-epic observations** kept in `epic.md`: the duration noise floor, cold-cache variance,
finalize cost being independent of diff size, `references.json` never reconciled after phase 4,
`build.py` being structurally unplannable, and manifest re-validation against live frontmatter.

## Closing rationale

The epic met its charter on every axis it could measure and reported honestly on the one it
could not. WS-03 — added at the reopen specifically to stop known defects from evaporating —
closed every lead it was created for and generated seven new corpus lessons in the process.

The remaining live defects are **finalize- and review-machinery** concerns, not test-suite
quality: they belong to the `truthful-signals` epic, whose theme (*a confident signal hides a
caveat*) is the direct descendant of what this campaign kept finding. Closing here is not
deferral — the defects are enumerated, verified, and pointed at a specific owner.

**Close freezes, never deletes.** The tree remains on disk as the audit record: ten landing
analyses under `landings/`, the full decision log under `logs/`, three workstream charters, ten
plan specs, and eight drained inbox messages under `inbox/archive/`.
