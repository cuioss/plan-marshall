# Verification — 080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory)
**Tree state:** `61a43e5` on `claude/code-intelligence-substrate-analysis-kah884`
**Overall verdict:** CONFIRMED WITH GAPS

The run halted at the plan's own D0 gate and reported the plan **blocked on corpus availability**. That
determination is correct, and I re-derived it independently against the tree as it stands now. Every
process claim in the report (PR number, files changed, review threads, comment bodies and ids, commit
trailers, `.gitignore` line citation) is accurate to the byte. The gaps are in the report's *technical
justification*: twice it states that the instrument D1 needs already exists in
`.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`. It does not — no shipped check reads
the three exploration sub-source fields (`exploration_{index_answerable,doc_residency,unattributed}_bytes`)
that define D1's split, and the closest check pools all phases into one per-plan figure, which D1
explicitly forbids. The consequence lands on the handoff: the residue tells a resuming corpus-bearing
session that "nothing needs building", which is false.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D0 | GATE — is an instrumented population reachable in this clone? | HALT on outcome (b): none reachable; plan blocked | Re-derived: no `metrics.toon` tracked in git (`git ls-files "*metrics.toon"` → 0), no `.plan/local/archived-plans/` on disk (`.plan/local/` contains only `logs`), `.gitignore:46` at the run's base sha ignores `.plan/*`. HALT was the plan-mandated action. | CONFIRMED |
| D1 | Per-phase index-answerable / doc-residency / unattributed split over a declared population | Unreachable; not attempted | Not attempted; correctly gated by D0. But the report's stated reason ("the instrument already exists, only the corpus is missing") is false — see Correctness review. | CONFIRMED (deliverable not attempted, legitimately) — with a false supporting claim |
| D2 | Classify the unattributed **byte** remainder | Unreachable; not attempted | Not attempted. Note: D2's *Done when* has an escape hatch ("or reported with a named reason it cannot be"), which the report arguably satisfies by naming corpus absence; the run took the conservative reading and claimed nothing. | CONFIRMED (conservative, not overstated) |
| D3 | State the epic's value case against the measurement | Unreachable — strictly downstream of D1 | Not attempted. `doc/plans/code-intelligence-substrate/README.md:5-7` still carries the pre-measurement framing; no cold-read artifact exists. Correctly deferred. | CONFIRMED (not attempted) |
| D4 | Every figure names population, phase, sampling point | Vacuous — no figures exist | No figures were emitted anywhere in `report-01.md` beyond the sub-agent's own token/tool-call usage, which is labelled with its population (`report-01.md:150-157`). | CONFIRMED |

## Per-deliverable detail

### D0 — GATE: is an instrumented population reachable in this clone at all?

- **Required (plan):** `plan.md:59-66` — "the run has established from git-reachable evidence either (a) a
  population it can measure, or (b) that none is reachable here… On (b): HALT and report the plan blocked
  on corpus availability. Do not substitute a hand-assembled corpus, and do not proceed on a single
  record."
- **Claimed (report):** `report-01.md:3,7-18` — outcome (b), HALT, blocked on corpus availability.
- **Found / checks run** (all re-derived by me, not copied from the report):
  - `git ls-files "*metrics.toon"` → **0** files. `git ls-files "*archived-plans*"` → **0**.
    `git ls-files "*.toon"` → **39** files, every one a template
    (`marketplace/bundles/plan-marshall/skills/manage-plan-documents/documents/request.toon`,
    `…/manage-tasks/templates/task-template.toon`,
    `…/pm-plugin-development/skills/plugin-doctor/templates/tool-coverage-results.toon`) or a test fixture
    (`test/plan-marshall/phase-6-finalize/fixtures/ci-wait/*`,
    `test/plan-marshall/plan-retrospective/fixtures/*`, `test/…/coverage/coverage-analysis.toon`,
    `test/plan-marshall/workflow-integration-sonar/*`).
  - False-negative control: the same `git ls-files` glob machinery returns hits where I know they exist
    (`git ls-files "*audit.py"` → 5 files), so the zero results are trustworthy negatives.
  - `git ls-files .plan/` → **13** paths: `.plan/marshal.json` plus twelve
    `.plan/project-architecture/**` files. No `.plan/local/`.
  - `.gitignore` at the PR's base sha `3a5e2ca` (fetched via GitHub): `.plan/*` is on **line 46**, with
    `!.plan/marshal.json` and `!.plan/project-architecture/` as the only exceptions — the report's citation
    was exactly right at run time. (At `61a43e5` the same directive sits on line 45; `.gitignore` was
    edited later, in #1250 and #1252.)
  - On-disk state now: `ls .plan/` → `execute-script.py.probe.tmp  local  marshal.json  project-architecture  temp`;
    `ls .plan/local` → `logs` only; `find . -name metrics.toon -not -path ./.git/*` → **nothing**. The corpus
    is genuinely absent from this clone class, not merely from git.
  - The two candidate substitutes the report named are as described:
    `test/plan-marshall/plan-retrospective/fixtures/archived-plan/` contains 17 files and **no**
    `metrics.toon` (only `fragment-*.toon`, logs, `status.json`, `references.json`); the replay fixtures are
    single-phase ledgers named `metrics-dispatch-boundaries-5-execute.toon`.
- **Verdict:** CONFIRMED. Outcome (b) is the true state of this clone, and the plan's mandated action on
  (b) — HALT — is what the run did. Per `plan.md:149-150` that is a D0 *success*.

### D1 — collect the split across all six phases

- **Required (plan):** `plan.md:67-75` — per-phase index-answerable / doc-residency / unattributed split
  **with the population size** and the contributing-plan count **per phase**; no pooling of phases; a
  per-phase RANGE, never one band.
- **Claimed (report):** `report-01.md:37` — "Unreachable — pure measurement over the absent corpus. Not
  attempted; gated by D0." Supporting claim at `report-01.md:44-48`: the `exploration-share` /
  `billing-composition` checks "read each plan's `work/metrics.toon`
  `{exploration,work,execute,orchestration,unclassified}_result_bytes` / `_tool_calls` counters — **the
  exact per-phase exploration counters D1 collects**."
- **Found:** the split D1 names is carried by a *different* field family:
  `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:3411` —
  `_EXPLORATION_SUBSOURCES = ('index_answerable', 'doc_residency', 'unattributed')`, materialised at
  `:3418-3420` as `exploration_{sub}_bytes`, and *"Deliberately SEPARATE from `_EXPLORATION_COUNTER_FIELDS`…
  they partition ONE bucket's bytes, they are not a sixth bucket"* (`:3413-3417`).
  `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md:184` states the
  partition invariant. The audit skill does not read those fields at all:
  `grep -rn "index_answerable\|doc_residency" .claude/skills/audit-archived-plan-retrospectives/` → **0
  matches** (control: the same pattern returns **33** matches across `marketplace/` and `test/`, so the
  zero is a real absence and not a broken search).
  `audit.py:6784-6786` builds `_ES_COUNTER_FIELDS` from the five coarse buckets only, and
  `audit.py:6789-6793` sums them **across phases** — `checks/exploration-share.md:16-18` says so in words:
  *"the script reads the ten per-phase exploration counters from `work/metrics.toon` and sums them across
  the plan's phases. No other input is consulted."*
- **Checks run:** greps above; read of `audit.py:6747-6910`, `audit.py:7176`, `audit.py:7229-7259`;
  read of `checks/exploration-share.md:1-40`; read of `manage-metrics.py:2320-2360` (the per-plan render
  site that *does* emit the sub-source bullets, per phase, for one plan at a time).
- **Verdict:** CONFIRMED that D1 was not attempted and could not have been completed here (the records are
  absent either way). REFUTED as to the report's justification: the instrument that would produce D1's
  output does not exist. See Report accuracy and gaps G1/G2/G3.

### D2 — classify the unattributed remainder, byte half only

- **Required (plan):** `plan.md:76-83` — classify the **byte** remainder into the existing buckets, or
  report a named reason it cannot be; state explicitly that the cached-read remainder is a different
  population owned by a sibling plan.
- **Claimed (report):** `report-01.md:38` — "Unreachable… Not attempted; gated by D0."
- **Found:** nothing was claimed about the remainder, and nothing was widened into the cached-read
  population — I checked: `report-01.md` contains no cached-read figure and no cross-population statement.
  The `unattributed` byte residual's own render spec lives at `manage-metrics.py:419` (`_UNATTRIBUTED_RENDER`)
  and is denominator-bearing, so a resumed run has the per-plan raw material.
- **Verdict:** CONFIRMED. Not attempted, correctly gated, and nothing overstated. The one nuance: D2's
  *Done when* would arguably have been satisfiable by naming the corpus absence as the reason; the run did
  not claim that credit. Understating is the safe direction under the lane contract.

### D3 — state the epic's value case against the measurement

- **Required (plan):** `plan.md:84-90` — the epic's written value case matches D1's evidence, plus a cold
  read by the verification sub-agent.
- **Claimed (report):** `report-01.md:39` — "Unreachable — its Done-when is 'matches D1's evidence';
  strictly downstream of D1."
- **Found:** `doc/plans/code-intelligence-substrate/README.md` is unchanged in substance and still frames
  the epic as owning "the levers that reduce what enters context and the instrumentation that makes those
  reductions verifiable" (`README.md:5-7`). No value-case restatement exists anywhere in the epic
  directory attributable to this plan, and no cold-read artifact was produced.
- **Verdict:** CONFIRMED (correctly deferred). The refuted framing named in `plan.md:38-44` is therefore
  still un-restated in the epic — declared residue, not a run defect.

### D4 — every figure names its population, its phase, its sampling point

- **Required (plan):** `plan.md:91-92`.
- **Claimed (report):** `report-01.md:40` — "Vacuous — a property of D1–D3 figures; with no figures there
  is nothing to satisfy."
- **Found:** the report emits no measurement figures. The only quantities it states are its own cost
  (`report-01.md:148-157`), and those *do* carry an explicit population statement including a ⛔ that they
  are not comparable to a plan-marshall `metrics.toon` total — the D4 discipline applied to the one place
  it could apply.
- **Verdict:** CONFIRMED.

## Correctness review

No production code, test, or bundle file was shipped by this run (PR #1178: 2 files changed — a rename of
`080-….md` → `080-…/plan.md` and the addition of `report-01.md`, 216 additions), so there is no shipped
code path to review for fail-open branches, guards, rounding or `None` handling. What I reviewed instead
is the code the report *cites as already sufficient*, because the residue's correctness depends on it:

1. **`audit.py` cannot produce D1's split — the fields are never read.**
   `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:6778` defines
   `_ES_BUCKETS = ("exploration", "work", "execute", "orchestration", "unclassified")` and `:6784-6786`
   derives the ten counter names from it. `:7176` builds billing-composition's byte fields from the same
   five buckets. Neither `exploration_index_answerable_bytes`, `exploration_doc_residency_bytes` nor
   `exploration_unattributed_bytes` appears anywhere in the skill directory. Consequence: the split whose
   1:4 ratio motivates the entire plan has **no cross-plan reporter**.
2. **`audit.py`'s exploration reading pools phases, which D1 forbids.**
   `audit.py:6789-6833` (`_parse_exploration_counters`) sums each counter "across the plan's phase
   sections" and returns a single `phases_measured` count; `_ExplorationShareRow` (`:6836-6859`) carries no
   per-phase structure. `plan.md:70` says ⛔ "Do not pool phases into one headline". Consequence: even for
   the coarse buckets, the existing check produces the shape D1 rules out.
3. **The two schema obligations D1 inherits are, by contrast, genuinely already implemented** — the one
   part of the report's "already exists" claim that holds. The three-state partiality read is
   `audit.py:1043-1180`: `METRICS_SCHEMA_CURRENT` / `METRICS_SCHEMA_OLD` / `METRICS_SCHEMA_PRE_812`, with
   `_RETIRED_PARTIALITY_KEYS = ("partial", "unrecorded_phases")` recognised and refused rather than
   defaulted, `None` value fields on both degrades, and `forces_floor` returning `True` on any unreadable
   state (`:1113-1115`). The three-way `unmeasured` cell read is `audit.py:7205-7224`
   (`_BC_LEDGER_UNMEASURED_TOKEN`, `_BC_LEDGER_UNMEASURABLE_FIELDS`, the five-column legacy floor). Both
   match `plan.md:98-104` as written. I found no defect in either.

No other defect was found. What I read to conclude that: `audit.py:1040-1181`, `:6747-6910`, `:7176-7259`,
`:7390-7460`; `checks/exploration-share.md:1-40`; `manage-metrics.py:2320-2360`, `:3400-3440`, `:3505-3545`;
`manage-metrics/standards/data-format.md:162-184`.

## Test adequacy

**No test was warranted by this run** and none was added: the run shipped no executable surface (PR #1178
changed exactly two Markdown files). There is therefore nothing here to prove vacuous, and I performed **no
mutation sweep** — a mutation sweep needs shipped production code to mutate. I verified the absence of an
executable footprint from the PR's own file list rather than assuming it (`get_files` on #1178: one
`renamed`, one `added`, both under `doc/plans/`).

For the record, the code the residue leans on *is* covered independently of this plan: the three-state
reader has dedicated suites at
`test/plan-marshall/audit-archived-plan-retrospectives/test_audit_check_metrics_end_time_markers.py` and
`test_audit_check_metrics_core.py`, and the sub-source fields are exercised at
`test/plan-marshall/manage-metrics/test_manage_metrics.py:1773,1865-1866,2080-2081,2127-2128` and
`test/plan-marshall/platform-runtime/test_metrics_tokens.py:758`. I did not audit those suites for vacuity
— they belong to the plans that shipped them, not to this one.

## Report accuracy

Claims checked one by one against the tree, GitHub, and git. **Two are false**; the rest held.

**False — 1.** `report-01.md:44-48`: the audit checks read counters "— **the exact per-phase exploration
counters D1 collects**." They are not. D1 collects
`exploration_{index_answerable,doc_residency,unattributed}_bytes`
(`manage-metrics.py:3411-3420`, `data-format.md:162-184`), a family deliberately kept separate from the ten
`{bucket}_{measure}` counters the audit checks read, and no check reads it
(`grep -rn "index_answerable\|doc_residency" .claude/skills/audit-archived-plan-retrospectives/` → 0).

**False — 2.** `report-01.md:208-210` (Residue): "The instrument to run already exists
(`exploration-share` + `billing-composition` checks in `audit.py`); **nothing needs building** — only the
corpus needs to be present." Building is needed: no reporter emits the per-phase sub-source split, and the
existing exploration reader pools phases (`audit.py:6789-6793`, `checks/exploration-share.md:16-18`)
contrary to `plan.md:70`. The same claim is repeated inside the sub-agent finding table
(`report-01.md:97`: "The instrument and the three-state reader already exist in `audit.py`; 080 is
measurement-only"), so the independent check corroborated the error rather than catching it.

**Held — everything else**, each verified rather than assumed:

| Claim (`report-01.md`) | Verification |
|---|---|
| PR #1178, outcome blocked, branch `claude/code-intelligence-substrate-fwoa6b` (l.3) | GitHub: PR 1178, `merged: true`, `merged_at 2026-08-12T09:24:46Z`, head ref matches. |
| `.gitignore` line 46 ignores `.plan/*`, two exceptions (l.54-55) | True at base sha `3a5e2ca` — I counted the file fetched at that sha: `.plan/*` is line 46, `!.plan/marshal.json` 47, `!.plan/project-architecture/` 48. (Now line 45 at `61a43e5`; drift caused by later edits, not an error.) |
| `git ls-files .plan/` → only `marshal.json` + `project-architecture/*` (l.56) | Re-run: 13 paths, exactly that set. |
| No archived-plan metrics corpus anywhere in git (l.57-64) | Re-run: `"*metrics.toon"` → 0, `"*archived-plans*"` → 0, all 39 tracked `.toon` are templates or fixtures. |
| The archived-plan fixture "carries *no* `metrics.toon` at all" (l.61-62) | `find` over that fixture: 17 files, none named `metrics.toon`. |
| Replay fixtures `{legacy,plan,unmeasured}`, single-phase (l.62-63) | Correct at run time. A fourth (`undatable`) was added 2026-08-17 by #1278 (`d1c3153`), five days after this run — drift, not an error. |
| `audit.py` walks `.plan/local/archived-plans/{plan_id}/` (l.47-48) | `audit.py:5` and `:9374-9375` (the `--plan-dir` default). |
| SKILL.md quote "because it operates on `.plan/local/archived-plans/` — a directory that only exists in this meta-project" (l.48-50) | Verbatim at `SKILL.md:18-20`. |
| Three-state reader `parse_metrics_end_time_presence` / `MetricsEndTimePresence` exists (l.71-73) | `audit.py:1052` and `:1139`. |
| Siblings 030/060 shipped git-derivable deliverables, unlike 080 (l.65-71) | Both sibling reports state outcome **completed** (`030-…/report-01.md:3`, `060-…/report-01.md:3`), consistent with the contrast drawn. |
| Sub-agent process note: real sibling dir is `060-dispatch-boundary-ledger-is-not-a-commensurable-population` (l.99) | Directory listing confirms that exact name; no `060-billing-composition-…` exists. |
| Build gate: no `*.py` footprint (l.79-84) | PR file list: two `doc/plans/**` Markdown paths only. |
| 0 inline review threads (l.115-116) | `get_review_comments` on #1178 → `totalCount: 0`. |
| Two conversation comments, ids `5264644499` (coderabbit skip) and `5264650522` (cuioss-review-bot clean guide), neither actionable (l.118-123) | Both fetched: bodies and ids match verbatim, authors `coderabbitai[bot]` and `cuioss-review-bot[bot]`. |
| Coverage 1-of-3, two silent by design (l.133-144) | Consistent with the fetched comments; `sourcery-ai` posted nothing. |
| Plan-directory move is a `git mv` carrying `Co-Authored-By: Claude` (l.166) | Commit `30e72b8`: "establish plan 080 directory… No content change", trailer present; PR file status is `renamed`. |
| Report is the last pre-merge commit, pushed before arming auto-merge (l.168) | Three commits, last is `2f49698` (the reviewer-participation correction), i.e. the report was amended after the review bodies existed — consistent with l.133-135. |
| Sub-agent cost ~96,454 tokens / 17 tool calls / 140,976 ms (l.150-151) | **UNVERIFIABLE** — session-internal telemetry, not reachable from the tree or GitHub. |
| "the harness does not surface this session's own token usage" (l.148-149) | **UNVERIFIABLE** — same reason. Correctly labelled as unavailable rather than guessed, which is the right posture. |

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| The measurement itself remains owed; a corpus-bearing session resumes 080 in place and writes `report-02.md` | **Open** | The plan directory contains only `plan.md` and `report-01.md` — no `report-02.md`. No other plan in the epic reports the split: `grep -rln "index-answerable"` over `doc/plans/` matches only `080-…/plan.md`, `010-lsp-in-execute-lookup-and-write/plan.md`, and `020-corpus-residency-admission-control/report-01.md` (which is itself a D0-blocked run, `020-…/report-01.md:3`). |
| "nothing needs building — only the corpus needs to be present" | **Open and wrong as stated** | See Report accuracy #2 and gap G3: the per-phase population aggregator does not exist and must be built. |
| Orchestrator routing: the plan must not be transitioned to `shipped`; re-route to a local session | **UNVERIFIABLE** | The orchestrator ledger lives under `.plan/`, which is git-ignored and absent here (`ls .plan/local` → `logs`). Nothing in the tree records the plan's status either way. |
| Landing: auto-merge armed (SQUASH), merge queue lands it | **Closed** | PR #1178 `merged: true`, `merged_at 2026-08-12T09:24:46Z`, `merged_by cuioss-oliver`. |
| Proposed (optional) `cloud-plan-lane` / `cloud-bridge.md` amendment: a run blocked on a missing environment prerequisite still lands its directory + report | **Open, by design** (operator decision, deliberately not shipped) | `.claude/skills/cloud-plan-lane/SKILL.md:1552-1554` says the report "must state the PR number and the outcome per deliverable — including a run that ended **blocked or partial**, and why", but neither that section nor `doc/plans/cloud-bridge.md` states that a run blocked on a missing *environment prerequisite* still establishes the directory and lands a report. `grep -rn "prerequisite\|corpus-bearing"` over both files → no such note. |

## Out-of-scope and collateral

Nothing was built that the plan excluded, and nothing was changed outside the plan's own directory. Checked:
PR #1178's complete file list is two paths, both under
`doc/plans/code-intelligence-substrate/080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case/`.
Specifically, none of the four exclusions in `plan.md:115-121` was violated — no old plan was re-run or
re-instrumented, no cached-read population was measured or mentioned as a figure, the retired per-phase cost
ranking is not revived anywhere in the report, and no re-scoping of the epic was acted on (the epic README
is untouched by this plan). The run also did not substitute the two fixture corpora it identified, which is
the specific failure mode `plan.md:64-66` forbids.

## Method and coverage

**What I checked, and how.** Read `plan.md` and `report-01.md` in full, plus the epic README. Re-derived
D0's answer from scratch: `git ls-files` over four globs (with a positive control to rule out a
false-negative glob), an on-disk inspection of `.plan/` and a repository-wide `find` for `metrics.toon`, and
a fetch of `.gitignore` at the PR's *base* sha to check the line citation against the tree the run actually
saw. Read the cited instrument code (`audit.py` exploration-share and billing-composition regions, the
three-state and three-way readers) and the field definitions it would need
(`manage-metrics.py`, `data-format.md`, `platform-runtime/standards/contract.md`). Verified the whole PR
cycle against GitHub: PR object, file list, commits, review threads, and both comment bodies.

**What I could not check, and why.**

- The run's own token/tool-call figures and the existence of the verification sub-agent dispatch —
  session-internal telemetry, not durable in the tree or on GitHub. Recorded as UNVERIFIABLE.
- Whether the orchestrator honoured the routing residue — the orchestrator's state lives under the
  git-ignored `.plan/`.
- Whether an instrumented population exists on *some* machine — out of reach by construction, and the plan
  forbids searching for it. My negative is scoped to this clone, which is the same scope D0 claims.
- The full `./pw verify` suite was not run (out of scope for this audit, and the run itself shipped no
  Python).
