# Landing Analysis: PLAN-110 — Every test runs, and the suite does not get slower

epic: test-quality
workstream: WS-05
pr: [#1426](https://github.com/cuioss/plan-marshall/pull/1426) — merged `1c4e6febb664cd0d65d14ababca420b61641b93d`

> Landing record for one shipped plan. Lives at `landings/PLAN-110.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

**Corroboration basis.** PR state read through the CI abstraction (`state: merged`,
`merge_commit_sha: 1c4e6feb…`); the merge diff read from git (29 files, +2390/−328);
the residual skippable set parsed out of the merged `test/conftest.py`; three
content sweeps over the inventoried tree; the archived plan tree at
`archived-plans/2026-09-06-every-test-runs-and-the-suite-does-not-slow-down/`.
Every figure below is either re-derived here or explicitly marked self-reported.

## Deliverable Fidelity vs Spec

Seven deliverables, **all seven complete** — corroborated, with the spec's own
estimates undershooting reality in three places and **two of its stated premises
refuted outright**.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — derive and classify the live skip inventory | shipped-as-specified | **80 skip sites across 27 files** classified. The spec's halting clause *fired as designed*: a member fitting none of the five named classes halted the run, and a sixth class (in-suite policy / data-driven) was added on operator decision. That is the gate working, not a deviation. |
| D2 — tool guards → one session-scoped preflight | shipped-as-specified | **42 sites, against the spec's "~30"** — 33 in `test_staleness_guard.py` (28 `git` + 5 `rsync`), 9 `rsync` in `test_sync_engine.py`. `REQUIRED_TOOLS` preflight in `test/conftest.py`; demonstrated red against an emptied `PATH`. |
| D3 — tree-presence guards → plain assertions | shipped-as-specified | **17 sites, against the spec's "~12"**; negative control (a deliberately broken path) turned the run red without inflating the skip count. |
| D4 — executor guard → fixture-built executor | shipped-as-specified | Executor built under `tmp_path`; `ExecutorBootstrapError` raised instead of skipping. One `collect_ignore` entry removed, +3 tests at −0.91 s. |
| D5 — bounded residual set behind an always-on gate | shipped-as-specified ⚠️ two premises refuted, one arm weaker than intended | See below. |
| D6 — both run conditions measurable from the canonical command | shipped-as-specified | `-rsfE` added to `addopts` beside the existing `--durations=25`; verified present in `pyproject.toml`, `test/README.md`, `_pyproject_cmd_parse.py` and `measurement-protocol.adoc`. |
| D7 — report the measured deltas | shipped-as-specified | `work/d7-report.md` carries every figure with its command. |

### D5 in detail — the deliverable that moved the epic's own knowledge

**The exception list is real and is enforced on the right axis.** Parsed out of the
merged `test/conftest.py`: **11 nodeids across 4 guard sites** — 10
`absent-dependency` (all `pyright-langserver`) plus 1 `in-suite-policy`. An entry
approves a specific *cause* for a nodeid, not the nodeid itself, so a listed test
that starts skipping for a different reason fails the run exactly as an unlisted one
does. The `PLAN_MARSHALL_STRICT_NO_SKIP` opt-in was **deleted rather than left
dormant** — a content sweep over the inventoried tree returns `count: 0`.

⛔ **The deleted docstring records that the gate had never once rendered a verdict.**
No producer in this repository ever set the flag, so `pytest_sessionfinish` returned
at its first line on every run. For the whole of this epic's executed half, the
`skipped == 0` gate the ledger relied on was dead code.

⛔ **Spec premise refuted #1 — `pytest-randomly` was never a dependency of this
project.** The spec asserted the absent-dependency class had *two* members and that
`pytest-randomly`'s absence is "why PLAN-060's randomised hermeticity arm went unrun
across all three of its runs". A content sweep finds **zero occurrences tree-wide**
with every coverage field clean. No proposal was made because there was nothing to
propose against. The arm went unrun because the plugin was never asked for — a
different fact with a different remedy, and the epic carried the wrong one.

⛔ **Spec premise refuted #2 — the platform-variable class emptied.** The spec named
"genuinely variable platform (Windows symlink semantics, `/proc`)" as a kind that
would legitimately remain. The realized list contains **zero** platform-variable
entries.

⚠️ **The reverse-order arm ran green, but is weaker than the spec intended.** The
plan's own `work/d5-evidence.md` heads the section *"RAN, and green, but a weaker arm
than intended"*: the arm ran under parallel workers, with proof the reversal reached
pytest, while the **strict serial** arm (~53 min CPU) was not run. The done-when is
met literally — "the whole-tree reverse-order arm has run and its result is recorded"
— and the run said so itself rather than papering over it. But order-independence is
only half-settled, and that matters here specifically: PLAN-105's candidate-lesson
009 item 1 asked for exactly this and was **deliberately not folded into PLAN-110**,
so it now sits half-answered in the Unowned list rather than owned anywhere.

**The pyright proposal is properly recorded** — 4 guard sites, 10 nodeids, with the
install/leave-out trade named on both sides — and one branch was lifted out of the
dependency entirely: `preflight` reaching `STATE_READY`, the sentinel every consumer
gates its LSP path on, is now covered against a fake subprocess server.

### Realized vs declared surface — the third failure mode

Applying the check this epic adopted at PLAN-145's landing: **16 of 29 realized files
(55.2%) fall inside PLAN-110's declared surface**, and **8 of its 15 declared entries
were never touched at all**.

Of the 13 outside, **7 fall inside the spec's own explicit exclusion** —
`marketplace/bundles/**`, which the spec put out of scope ("a production defect found
here is recorded, never fixed") and which the operator then explicitly authorised as
a widening to fix two build-tooling defects. That is a recorded expansion, not drift.
**6 fall outside the declaration entirely**: `doc/developer/measurement-protocol.adoc`,
`pyproject.toml`, `test/plan-marshall/build-pyproject/test_pyproject_cmd_parse_collection_errors.py`,
`test/plan-marshall/script-shared/test_routed_errors_carry.py`,
`test/sync-opencode/test_sync_opencode.py`, and `test/test_skip_gate.py`.

⛔ **This is the third distinct way the declaration form fails, and it is the one
that indicts the form itself.** The epic now has all three measured:

| | PLAN-145 | PLAN-105 | PLAN-110 |
|---|---|---|---|
| Declared | 5 entries, narrow and specific | 10 entries, two of them whole trees | 15 entries + 1 explicit exclusion |
| Realized inside | **0 of 3** | **514 of 521 (98.7%)** | **16 of 29 (55.2%)** |
| Declared entries realized | 0 of 5 | — | 8 of 15 |
| Failure mode | inaccurate — the declaration described a different plan after a pivot | accurate but not narrow — no discriminating power, everything collides | **accurate AND narrow, and still missed 45%** |

PLAN-110's declaration is the first in this epic that is honest on both axes the
prior two landings identified — and it still captured barely half the diff. The
reason is structural, not sloppiness: a path list enumerates **where the plan expects
to work**, and cannot express **what the work will drag in**. Changing the shared
`conftest.py` pulls in the build wrapper that parses its output; adding an always-on
gate needs a new gate-test file at the test root; making a command's output readable
needs the command's own config. None of those are scope creep — each is entailed by a
declared deliverable — and none is expressible as a path a human could have listed at
outline time.

⚠️ **This retires "be accurate and narrow" as the remedy.** Accuracy and narrowness
were the two properties PLAN-105's landing named as jointly sufficient. PLAN-110 has
both and the gate still under-reads its surface by 45%. The declaration-form defect
therefore needs a *different shape* of answer — a predicate, an entailment closure, or
a declared-plus-observed reconciliation — not a better-written list.

## Metrics and Anomalies

- **Tokens**: 7,240,427 across 6 phases. **6-finalize 3.03 M against 5-execute's 2.34 M
  (1.29×)** — the fourth consecutive landing where finalize outspends execute, and the
  mildest of the four (PLAN-105 was 3.33×).
- **Duration**: 116,483 s wall (32 h 21 m); 5 h 9 m worked, 16 h 23 m idle (n=5/6).
- **Re-entry**: 5-execute re-entered; 6-finalize boundaries non-monotonic.
- **Anomalies**:
  - ⛔ **Three head-dependent gates rendered verdicts over a tree that is not the one
    that merged, and all three read `outcome: done`.** The fourth loop-back was taken
    under the operator's standing unattended instruction but was handled *inside*
    `automatic-review` rather than admitted as a loop-back, so it never went through
    `manage-status set-phase` — the path that re-arms head-bound steps:

    | Step | anchored at | merged head |
    |---|---|---|
    | `project:finalize-step-plugin-doctor` | `150ead51` | `c8cf10d5` |
    | `pre-submission-self-review` | `150ead51` | `c8cf10d5` |
    | `pre-push-quality-gate` | `b5400e55` | `c8cf10d5` |

    ⛔ The consequence is not theoretical: `pre-submission-self-review` had **already
    caught two contract-drift defects in `build-pyproject/SKILL.md`**, and that same
    file was edited twice more after its anchor without the step looking again. Build
    and test coverage held (`ci-verify` green at `c8cf10d5`); the **structural** half
    — component gating and pre-submission self-review — was lost silently. Lesson
    `2026-09-06-10-001`.
  - ⚠️ **This is the epic's head-currency problem seen from the opposite side.** The
    `verdict_inputs` gap this epic has measured three times is gates **over**-firing
    on an invalidated verdict. Here the same missing capability makes them
    **under**-fire and stay green. The lesson names the contrast itself and is
    explicit that its remedy (a pre-merge staleness assertion independent of the
    loop-back path) *complements* rather than duplicates `2026-09-04-17-001`'s
    `verdict_inputs` proposal. The silent direction is the worse one.
  - ⛔ **Scope-creep measurement was unavailable for the entire run.**
    `references.json` carries no `plan_creation_sha`, so `scope_creep_check` returned
    `could_not_look` on every task and `residual_count` is **absent, not zero** — on
    the one run that took an operator-authorised write-boundary widening into 7
    `marketplace/bundles/**` files.
  - The loop-back ceiling was breached 3/3 → 4, logged at WARNING **without mutating
    `max_iterations`**. All four loop-backs were productive: the 6-finalize dispatch
    ledger carries 4 `returned_with_findings` against 9 `step_complete` and **zero**
    `error`. The ceiling counts productive detection and fix-break churn identically.
  - The run **fabricated a SHA once** — padded an abbreviated hash with invented
    characters while marking a step — and caught and corrected it itself.

## Routing and Merge Behavior

- **Review**: three reviewers enabled (`coderabbitai`, `cuioss-review-bot`,
  `sourcery-ai`); `reviewer_coverage: 2/3` — **Sourcery did not review at all**, and
  `cuioss-review-bot` participated but filed nothing the store can score. Only
  CodeRabbit produced findings: **9 raw / 7 actionable / 2 meta**, resolved 5 `fixed`,
  1 `accepted`, 3 `taken_into_account`, **0 rejected, 0 pending, 0 false positives**;
  71.4% resolved-as-fixed. `unmeasurable` is the absence of a measurement, not `0%`.
- ⛔ **The review-coverage gap is not only a size problem.** PLAN-105 lost every
  reviewer to diff-size refusals on 515 files. PLAN-110's diff is **29 files** — inside
  every published ceiling — and still only **one of three** enabled reviewers produced
  anything scoreable. Two landings, two different causes, same outcome.
- ⚠️ **The review-versus-gate delta could not be computed, for the third landing
  running.** `verdict: excluded`, `exclusion_reason: gate_tree_unsubstantiated`,
  `structural_share: null`. Two independent reasons: the `pr-comment` findings carry
  **two** different `reviewed_commit_sha` values (`b5400e55` round 1, `a7fa0c46`
  round 2) because the plan looped back and re-pushed, and `reviewed_head_sha` was not
  supplied. The run passed nothing rather than deriving one SHA from a mixed set —
  correct behaviour. But the instrument has now been excluded on PLAN-105
  (`gate_head_sha != reviewed_head_sha`) and PLAN-110 (`gate_tree_unsubstantiated`)
  and **has never once rendered a share**.
- 7 gate escapes recorded — 6 `gate_addressable`, 1 `gate_structural`, 0 unpartitioned.
- **CI/merge**: three CI runs (`34018023035`, `34021472168`, `34023853700`); merged via
  the platform merge queue as `1c4e6feb`; branch and worktree removed; `main` up to
  date.

⚠️ **`main` is red on the local whole-tree quality gate, and it is a false positive.**
Two `plugin-doctor` errors at `build-server-client/SKILL.md:161` claim `--timeout` is
undeclared on `build_server submit`. **Verified false** — `build_server submit --help`
declares it. Both failures reproduce on the parent commit `0fde908d0`, so this is
pre-existing and not PLAN-110's. Lesson `2026-09-06-10-002`.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-110 --status shipped`
- [x] row `pr` stamped `#1426`
- [x] row `landing` stamped — `landings/PLAN-110.md`
- [x] row `plan_marshall_plan_id` stamped — `every-test-runs-and-the-suite-does-not-slow-down`
- [x] epic.md queue reconciled from status.json; both generated blocks regenerated
- [x] 2 inbox messages drained and archived (1 landing → reconciled, 1 finding → observed)
- [x] `## Run Conditions` section added to epic.md — conditions 3 and 4 now carry the
      literal command PLAN-110 built, discharging the finding message's mirror request
      and superseding the scoping brief's "until it lands" clause
- [x] Watch RETIRED — the pre-launch warning on `test/plan-marshall/workflow-integration-github/`
- [x] Open Defect added — three head-dependent gates anchored to a superseded tree
- [x] Open Defect added — the review-versus-gate instrument has never rendered a share
- [x] Open Defect added — `plan_creation_sha` absent, scope-creep unmeasurable
- [x] Defect UPDATED — the declaration-form root cause, now with its third failure mode
- [x] resume_anchor updated

## Follow-Ups

- ⛔ **The `launched` transition for PLAN-110 was never recorded.** Its row read
  `staged` right up to this reconciliation, so for the whole 32-hour run the ledger
  said nothing was running. `auto_emit` is `false` by design and the operator-confirmed
  launch step is the gap; this is the second consecutive emit where it went unrecorded.
  Recorded as a defect against the emit→launch handshake, not against the operator.
- ✅ **The pre-launch warning resolved as a non-event, and the check was worth making.**
  The 2026-09-05 anchor flagged that PR #1409 had modified
  `test/plan-marshall/workflow-integration-github/test_github_pr.py` inside PLAN-110's
  declared surface. PLAN-110 **never touched that directory** — it is one of the 8
  declared-but-unrealized entries. The warning is retired as satisfied, and the
  underlying **unorchestrated-plan blindness** is unchanged and still carried.
- ⚠️ **The epic's most-repeated build-gate figure is stale.** `… 14 skipped` appears
  across the landed reports of plans 010, 020, 030, 040, 050, 060, 070, 080, 090 and
  100 — from `20066 passed, 14 skipped` to `21334 passed, 14 skipped` — and PLAN-110's
  own spec carried it as the HYPOTHESIS gating D1. The live figure at plan start was
  **11**, and 11 after. Whether the three disappeared through drift or because the
  archived reports measured `./pw verify` while PLAN-110 measured `module-tests` is
  **not settled here** and should not be asserted either way. What is settled: the 14
  was never re-derived and must not be carried forward.
- **Premise corrections carried in from the finding message, all corroborated**:
  `.github/workflows/` holds **eight** files, not seven (the stale claim was deleted
  with the flag rather than corrected); `test/conftest.py`'s `collect_ignore` had
  **four** entries, not five, and **three** remain; the residual set is **11 nodeids
  from 4 guard sites**, not the 9 source sites the brief assumed —
  `test_lsp_integration.py` carries one **module-level** guard covering seven tests.
- ⚠️ **Lessons were routed to the global corpus, not this inbox.** The orchestration
  verdict resolved late, so `review-retrospective`, `plan-retrospective` and
  `lessons-capture` each ran with `orchestrated=false`. Nothing is lost:
  `2026-09-06-10-001` and `2026-09-06-10-002` are both live in the corpus (verified),
  plus recurrence sections on `2026-08-25-09-001/003/004/009`, `2026-09-04-14-007`,
  `2026-09-04-17-004`, `2026-09-06-08-001`, `2026-09-04-17-014` and
  `2026-09-03-11-002`. Recorded as a defect against the verdict-resolution ordering:
  **the epic's inbox channel is only as good as the point at which a run learns it is
  orchestrated.**
- **The four-of-four finalize-outspends-execute count is recorded but not folded.**
  The shapes are not commensurable — PLAN-170 and PLAN-145 measured *wasted* finalize
  share (59%, 66%), PLAN-105 and PLAN-110 measure the finalize/execute ratio (3.33×,
  1.29×). The trend is worth watching; it is not yet a measurement. Out of scope,
  belongs to the measurement-instrumentation cluster.
