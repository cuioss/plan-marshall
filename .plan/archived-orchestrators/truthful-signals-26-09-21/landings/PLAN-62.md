# Landing Analysis: PLAN-62 — Build-Timeout Learned-Value Truthfulness

epic: truthful-signals
workstream: WS-01
pr: 1022

> Landing record. Merge verified first-party: `origin/main` head `4f740a997` —
> `fix(build-timeout): make learned timeouts truthful, not silent caps (#1022)`.
> Sourced from the operator narrative PLUS the plan's own six inbox messages
> (`inbox/build-timeout-learned-value-truthfulness-001..006`), all read first-party at drain.

## Deliverable Fidelity vs Spec

4/4 shipped, 21/21 finalize steps. Spec asked for the learned value never to override the resolved
bound downward, a truthful floor per engine, and the bounded-wait `inner < outer` invariant — all
delivered, plus one loop-back fix.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — `--timeout` is a true override, no silent downward cap | shipped-as-specified | commit `b4a1fa0d9` |
| D2 — truthful floor across all engines + single harness ceiling | shipped-as-specified | `bb27a93b4`: `PYTEST_OUTER_FLOOR_SECONDS` 600s, maven/gradle/npm 300s; `architecture resolve` now computes `bash_timeout_seconds` from the **same** floor the run enforces |
| D3 — CI-complete wait margin clamp | **shipped-MODIFIED after a loop-back** | `19d22ae3f` + fix `017dbbe3f`; `HARNESS_BASH_CEILING_SECONDS = 600` declared ONCE in `tools-file-ops/scripts/constants.py`, imported by both consumers |
| D4 — cross-cutting regression coverage | shipped-as-specified, then corrected | `70f725b20`; one shipped test was rewritten in `017dbbe3f` — see below |
| (unplanned) invariant codified in `plan-marshall/standards/waiting.md` | added-unplanned | `b01f19c59` |

## ⛔ The plan reintroduced its own archetype, and every in-house gate passed it

**D3 introduced a fresh instance of the exact defect class the plan existed to eliminate.** The clamp
rebound `timeout_seconds` at the settle point, and the ratchet then used that same rebound name as its
comparison base — so with a persisted `ci:wait` above the clamp, every deadline-exceeded finalize fed
`compute_weighted_timeout` an observation strictly BELOW the persisted value. **The learned value
drifts downward on every run — silently self-capping.** The module docstring simultaneously asserted
the value "stays honest / is free to exceed the clamp": code and prose disagreed *inside the change
written to make them agree*.

**And the shipped test codified the drift as the contract.** It seeded a persisted ceiling of 5000s
and asserted only that ~571s was recorded, with no assertion connecting input to output — the test
said "recording an order of magnitude below the persisted value is correct", and would have defended
the defect against any future correct fix.

What caught it, and what did not:

| Gate | Result |
|------|--------|
| `pre-push-quality-gate` | GREEN — 15452 tests passed |
| `pre-submission-self-review` | **CLEAN — 75 candidates examined** |
| plugin-doctor | clean, 9 skills gated |
| **CodeRabbit** | **CAUGHT IT** — rated 🟠 Major, named the exact remedy (preserve a `requested_ceiling` local), AND separately flagged the test as codifying the drift |
| **PR-Agent** | **CAUGHT A SECOND, DIFFERENT REAL DEFECT** — `_clamp_wait_ceiling` had no lower bound, so `--timeout 0` or a corrupt negative persisted value reaches `subprocess.run` and raises an uncaught `ValueError` (only `TimeoutExpired` is handled at the call site) |
| Sourcery | refused — weekly rate limit (500000 diff chars). **A refusal, not a review** |

Both defects fixed in one loop-back (`017dbbe3f`), re-verified, merged.

**This is the THIRD recorded member of "a fix for archetype X introduces a fresh instance of X"**
(cf. `_split_bundle_version`, where `pre-submission-self-review` also reported CLEAN and two bots
caught it). ⚠ **The durable signal is not the defect — it is that `pre-submission-self-review` reports
CLEAN on precisely this class, now n=2 with an identical shape.** Routed to PLAN-81.

⭐ **Review-bot convergence, n=2 independent bots on one PR, each finding a different real defect.**
This is the strongest evidence yet for the operator's standing decision to keep multiple reviewers,
and it directly contradicts any reading of the bots as low-signal. It also re-confirms that a green
in-house gate chain is not evidence of correctness.

## Metrics and Anomalies

- Tokens: 4.5M · Duration: 4h20m worked
- Whole-tree module-tests: 15452 passed
- Release: 0.1.1232, 1120 files → `target/claude/`, 10 bundles synced, executor regenerated
- **Anomaly 1 — `pre-submission-self-review` returned `status: success` without calling
  `mark-step-done`.** The post-dispatch completion guard (`assert-step-recorded --require-terminal`)
  caught it, recorded `failed`, halted, and the resumable re-entry retried. Cost: a full level-3
  re-dispatch — 14 minutes of completed review work discarded (16:06→16:20), retry took 4 minutes.
  The guard can detect the missing record but cannot salvage the work behind it. Routed to PLAN-59 D4.
- **Anomaly 2 — two consecutive `run_in_background` whole-tree builds killed with zero bytes and no
  ledger row**, on a build that genuinely takes ~640s. Foreground + explicit 600000ms timeout (letting
  the harness auto-background at its own ceiling) completed cleanly EVERY time. Routed to PLAN-65.
- **Anomaly 3 — the plugin-doctor gate ran against the pre-amendment `affected_files`**, so it covered
  9 skill dirs but NOT the `plan-marshall/standards/waiting.md` promotion that landed afterwards. Six
  lines of markdown in a standards doc, covered by whole-tree gates but **never structurally linted**.
  Recorded as a watch — a gate whose input snapshot predates the change it is meant to cover is this
  epic's archetype in miniature.

## Routing and Merge Behavior

- Review: 3 actionable pr-comment findings, all FIXed in-run (TASK-8 / TASK-9), RESPOND 3/3.
  Re-review clean. CI green at `017dbbe3f`.
- CI/merge: merged via merge queue; rebased onto origin/main over 2 upstream commits; worktree removed.
- Surface collisions: **none**. PLAN-62 ran concurrently with PLAN-79/56/75/87 throughout and its
  `manage-run-config` + build-engine + `ci_base` surface stayed disjoint, as staged. ⚠ The PLAN-87
  adjacency warning (option 2 would touch `build-maven/scripts/extension.py`) is now MOOT for PLAN-62
  — it has landed, so PLAN-87 may pick option 2 without a concurrency conflict.

## Reconciliation Actions

- [x] row `status` → `shipped`; `pr` = 1022; `landing` = landings/PLAN-62.md
- [x] epic.md queue reconciled; mirror row marked shipped
- [x] six inbox messages DRAINED, dispositioned, and removed
- [x] follow-ups routed (below); one NEW plan staged (PLAN-89)
- [x] resume_anchor updated; START-HERE regenerated
- [ ] `plan_marshall_plan_id` — not stamped; not reported and not recoverable from the PR. Left empty
      deliberately rather than guessed.

## Follow-Ups — inbox drain dispositions (6 messages, all removed after routing)

| Msg | Kind | Disposition |
|-----|------|-------------|
| 001 | landing | Folded into this report. Removed. |
| 002 | candidate-lesson — settle-point rebinding; self-review CLEAN over a Major defect | → **PLAN-81**, as the second identically-shaped instance. Carries the durable rule: *a variable rebound at a settle point must not remain the comparison base for a downstream invariant*, plus the meta-rule that a plan fixing archetype X is MORE exposed to X, not immune. |
| 003 | candidate-lesson — the shipped test codified the drift | → **PLAN-81**, same gate blindness. Durable tell: *a fixture with a dramatic input (5000s) and an assertion on an unrelated small output (~571s), with nothing connecting them* — the gap is where the invariant should be. Prefer relational assertions over equality-to-observed for bounds/directions. |
| 004 | candidate-lesson — `success` without `mark-step-done` | → **PLAN-59 D4** (leaf-return contract invariant), as a RECURRENCE with a costed remedy: detection exists, prevention does not, and the guard's remedy scales with step runtime. Carries the design suggestion that the dispatcher record the outcome from the returned TOON when the contract maps 1:1. |
| 005 | candidate-lesson — empty background output file carries no information | → **PLAN-65** (landed-residue promotion). Three durable pieces not yet in standing knowledge: the **buffering property** that makes the obvious diagnostic vacuous, the **change-ledger as substitute oracle**, and the **foreground-with-ceiling mitigation**. |
| 006 | candidate-lesson — the leaf's runnable build slice is now EMPTY | → **NEW PLAN-89**, staged. The message itself recommended its own plan rather than a fold, and I agree: it changes tiering policy across all four engines and every consumer of the resolve stamp. |

⚠ **Eleven further messages remain in `inbox/`** — 4 from PLAN-75, 7 from PLAN-79. Both plans are
**mid-finalize, not landed** (`origin/main` shows no merge for either), so their messages are HELD
deliberately for their own landing analyses rather than drained now. This is not an accumulation
failure; draining them now would analyse a landing that has not happened.
