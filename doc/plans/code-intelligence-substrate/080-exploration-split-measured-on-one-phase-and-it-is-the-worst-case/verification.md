# Verification — 080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory)
**Tree state:** first pass at `61a43e5`; re-derived under adversarial review at `57c63a8`, both on
`claude/code-intelligence-substrate-analysis-kah884`
**Overall verdict:** CONFIRMED WITH GAPS

The run halted at the plan's own D0 gate and reported the plan **blocked on corpus availability**. That
determination is correct, and I re-derived it independently against the tree as it stands now. Every
process claim in the report (PR number, files changed, review threads, comment ids, CI conclusions, commit
trailers, `.gitignore` line citation) is accurate. The gaps are in the report's *technical justification*:
in three places it states that the instrument D1 needs already exists in
`.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`. It does not, in three separate
respects — no shipped check reads the three exploration sub-source fields
(`exploration_{index_answerable,doc_residency,unattributed}_bytes`) that define D1's split; the closest
check pools all phases into one per-plan figure, which D1 explicitly forbids; and that same check applies
neither of the two schema reads `plan.md:98-104` obliges nor the re-entry guard `plan.md:106-109`
obliges, though sound implementations of all three exist elsewhere in the same file. The consequence
lands on the handoff: the residue tells a resuming corpus-bearing session that "nothing needs building",
which is false — and the work in question is git-derivable, so it did not need the absent corpus and
could have been done in the cloud clone.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D0 | GATE — is an instrumented population reachable in this clone? | HALT on outcome (b): none reachable; plan blocked | Re-derived twice: no `metrics.toon` tracked in git (`git ls-files "*metrics.toon"` → 0), no `.plan/local/archived-plans/` on disk and no `metrics.toon` anywhere outside `.git/`, `.gitignore:46` at the run's base sha ignores `.plan/*`. HALT was the plan-mandated action. | CONFIRMED |
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
  - `.gitignore` at the PR's base sha `3a5e2ca` (read with `git cat-file -p 3a5e2ca:.gitignore`): line 44
    `# Planning system`, 45 `# Runtime state`, **46 `.plan/*`**, 47 `!.plan/marshal.json`,
    48 `!.plan/project-architecture/` — the report's citation was exactly right at run time. The same
    directive now sits on line 45; the single intervening edit to `.gitignore` is `c0b4f3e` (2026-08-15,
    **#1252**). *(An earlier draft of this document also credited #1250; `git log -- .gitignore` shows only
    three commits ever touching the file — `c0b4f3e`, `47ace15`, `59b716d` — and #1250 is not among
    them.)*
  - On-disk state: `.plan/local/archived-plans/` does not exist, and
    `find . -name metrics.toon -not -path ./.git/*` → **nothing**. The corpus is genuinely absent from
    this clone class, not merely from git. (The rest of `.plan/local/` is volatile working state — it held
    `logs` alone at the first pass and `logs` + `marshall-state.toon` at re-derivation — so only the two
    durable facts above are quoted here.)
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
- **Verdict:** CONFIRMED that D1 was not attempted and could not have been *completed* here (the records
  are absent either way). REFUTED as to the report's justification: the instrument that would produce
  D1's output does not exist, and building it needs no corpus. See Report accuracy and gaps
  G1/G2/G3/G4/G7.

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
3. **The two schema readers D1 inherits exist and are sound — but D1's host consumes neither.**
   The readers themselves are real. The three-state partiality read is `audit.py:1043-1180`:
   `METRICS_SCHEMA_CURRENT` / `METRICS_SCHEMA_OLD` / `METRICS_SCHEMA_PRE_812`, with
   `_RETIRED_PARTIALITY_KEYS = ("partial", "unrecorded_phases")` recognised and refused rather than
   defaulted, `None` value fields on both degrades, and `forces_floor` returning `True` on any unreadable
   state (`:1113-1115`). The three-way `unmeasured` cell read is defined at `audit.py:7205-7224`
   (`_BC_LEDGER_UNMEASURED_TOKEN`, `_BC_LEDGER_UNMEASURABLE_FIELDS`, the five-column legacy floor
   `_BC_LEDGER_MIN_COLUMNS`) and applied at `:7357-7394`, where a token cell dates the row without
   measuring, an unparseable cell dates nothing, and a literal `0` is admitted only in a
   fingerprint-dated row. Both readers match `plan.md:98-104` as written, and I mutation-tested both
   (see Test adequacy) rather than only reading them.

   **What does not hold is the inference the report draws from that.** `exploration-share` — the check
   that would host D1 — calls neither reader: `parse_metrics_end_time_presence` is consumed at
   `audit.py:1700`, `:4454` and `:7477` (the metrics, input-integrity and billing-composition checks) and
   **nowhere** in the exploration-share region, and `_collect_exploration_share_rows` (`:6862-6888`)
   applies only the absent-is-not-zero exclusion. Nor does it honour `plan.md:106-109`'s ⭐ obligation to
   read the published value-scope fields: `close_count` / `value_scope` / `cumulative_fields` /
   `last_close_fields` (`data-format.md:128-130`) are read by billing-composition (`audit.py:7515`
   labels a `close_count > 1` row `unabsorbed_loop_back`) and by no part of exploration-share, so a
   re-entered phase's counters are summed into a rate with no exclusion and no label. The correct
   statement is therefore: the reusable readers exist and are sound, and wiring them into D1's host is
   outstanding work — see gap G7.

No other defect was found. Read across both passes: `audit.py:1040-1181`, `:6747-6910`, `:7128-7264`,
`:7326-7396`, `:7390-7460`, `:7460-7530`; `checks/exploration-share.md:1-45`;
`manage-metrics.py:2320-2363`, `:3400-3444`, `:3505-3545`;
`manage-metrics/standards/data-format.md:128-130`, `:162-184`.

## Test adequacy

**No test was warranted by this run** and none was added: the run shipped no executable surface (PR #1178
changed exactly two Markdown files). There is therefore no shipped code path of this plan's to prove
vacuous. I verified the absence of an executable footprint from the PR's own file list rather than
assuming it (`get_files` on #1178: one `renamed`, one `added`, both under `doc/plans/`).

**Two mutation sweeps were nonetheless run**, on the code the residue and Correctness-review item 3 lean
on — because "the reader already exists and is sound" is a claim that has to be able to come back false.
Both mutated `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`, ran the owning test
file, and restored the file from a byte snapshot (never `git checkout`), confirmed clean with
`git status --porcelain` and an `md5sum` match against the pre-mutation snapshot.

| Sweep | Mutation | Result |
|---|---|---|
| Three-state partiality read (`audit.py:1170-1175`) | old-schema branch returns `METRICS_SCHEMA_CURRENT` with `any_phase_missing_end_time=False` / `phases_missing_end_time=frozenset()` — i.e. defaults an old-schema record clean, the exact archetype `plan.md:98-101` names | **RED.** `test_audit_check_metrics_end_time_markers.py`: 12 passed → 3 failed, 9 passed (`test_metrics_old_schema_record_explains_nothing`, `test_parse_metrics_end_time_presence_reports_old_schema`, `test_input_integrity_old_schema_execute_stays_blind`). Restored → 12 passed. |
| Three-way `unmeasured` cell read (`audit.py:7368-7372`) | the `unmeasured` token is admitted as a measured zero (`totals += 0; measured.add(...)`) — the absent-read-as-zero defect `plan.md:102-104` names | **RED.** `test_audit_check_billing_composition_ledger_provenance.py` + `..._under_counts.py`: 19 passed → 3 failed, 12 passed (`test_unmeasured_token_fingerprint_keeps_sibling_measured_zeros`, `test_a_fingerprinted_row_does_not_date_its_neighbour[undated-first]` and `[dated-first]`). Restored → 19 passed. |

Both readers are therefore non-vacuously covered, which is what makes item 3's "sound" claim safe. Note
that neither sweep says anything about `exploration-share`, which calls neither reader (item 3, gap G7).

For the record, the sub-source fields are exercised at
`test/plan-marshall/manage-metrics/test_manage_metrics.py:1773,1865-1866,2080-2081,2127-2128` and
`test/plan-marshall/platform-runtime/test_metrics_tokens.py:758,802-876,937-938,1034-1035` (the first
citation in each pair is prose using the hyphenated spelling `index-answerable`, not the field name — a
grep for the underscore form alone will appear to miss them). I did not sweep those suites — they belong
to the plans that shipped them, not to this one.

## Report accuracy

Claims checked one by one against the tree, GitHub, and git. **Three are false** — all three the same
underlying error, stated in three places; the rest held.

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
contrary to `plan.md:70`.

**False — 3.** `report-01.md:70-73`: "Plan 080 has **no** git-derivable deliverable: its instrument
(`exploration-share`/`billing-composition`) and the three-state schema reader … *already exist* in
`audit.py`; 080 is purely 'run the existing instrument over records that are not in this clone.'" The
second half is the same misidentification as False-1, and the first half does not follow from it: the
per-phase sub-source reporter D1 needs is absent, is git-derivable, and could have been built in this
clone (gaps G3/G4/G7). The claim is repeated a fourth time inside the sub-agent finding table
(`report-01.md:97`: "The instrument and the three-state reader already exist in `audit.py`; 080 is
measurement-only"), so the run's independent check corroborated the error rather than catching it.

⚠ **This does not weaken D0.** The plan mandates HALT on outcome (b) unconditionally
(`plan.md:64-66`), so the halt is correct whether or not git-derivable preparatory work existed. What is
wrong is only the report's *reason*, and the handoff it produced.

**Held — everything else**, each verified rather than assumed:

| Claim (`report-01.md`) | Verification |
|---|---|
| PR #1178, outcome blocked, branch `claude/code-intelligence-substrate-fwoa6b` (l.3) | GitHub: PR 1178, `merged: true`, `merged_at 2026-08-12T09:24:46Z`, head ref matches. |
| `.gitignore` line 46 ignores `.plan/*`, two exceptions (l.54-55) | True at base sha `3a5e2ca` — I counted the file fetched at that sha: `.plan/*` is line 46, `!.plan/marshal.json` 47, `!.plan/project-architecture/` 48. (Now line 45 at `61a43e5`; drift caused by later edits, not an error.) |
| `git ls-files .plan/` → only `marshal.json` + `project-architecture/*/enriched.json` (l.56) | Re-run: 13 paths — `marshal.json`, eleven `*/enriched.json`, **and** `project-architecture/_project.json`. The report's `*/enriched.json` spelling misses that twelfth path; the load-bearing half (no `.plan/local/`) is exact. |
| No archived-plan metrics corpus anywhere in git (l.57-64) | Re-run: `"*metrics.toon"` → 0, `"*archived-plans*"` → 0, all 39 tracked `.toon` are templates or fixtures. |
| The archived-plan fixture "carries *no* `metrics.toon` at all" (l.61-62) | `find` over that fixture: 17 files, none named `metrics.toon`. |
| Replay fixtures `{legacy,plan,unmeasured}`, single-phase (l.62-63) | Correct at run time. A fourth (`undatable`) was added 2026-08-17 by #1278 (`d1c3153`), five days after this run — drift, not an error. |
| `audit.py` walks `.plan/local/archived-plans/{plan_id}/` (l.47-48) | `audit.py:5` and `:9374-9375` (the `--plan-dir` default). |
| SKILL.md quote "because it operates on `.plan/local/archived-plans/` — a directory that only exists in this meta-project" (l.48-50) | Verbatim at `SKILL.md:18-20`. |
| Three-state reader `parse_metrics_end_time_presence` / `MetricsEndTimePresence` exists (l.71-73) | `audit.py:1052` and `:1139`. |
| Siblings 030/060 shipped git-derivable deliverables (l.65-70) | Both sibling reports state outcome **completed** (`030-…/report-01.md:3`, `060-…/report-01.md:3`), consistent with the contrast drawn. **The sibling half only** — the "unlike 080 / 080 has no git-derivable deliverable" half of the same sentence (l.70-73) is False-3 above, not a held claim. |
| Sub-agent process note: real sibling dir is `060-dispatch-boundary-ledger-is-not-a-commensurable-population` (l.99) | Directory listing confirms that exact name; no `060-billing-composition-…` exists. |
| Build gate: no `*.py` footprint (l.79-84) | PR file list: two `doc/plans/**` Markdown paths only. |
| 0 inline review threads (l.115-116) | `get_review_comments` on #1178 → `totalCount: 0`. |
| Two conversation comments, ids `5264644499` (coderabbit skip) and `5264650522` (cuioss-review-bot clean guide), neither actionable (l.118-123) | Both fetched: ids, authors (`coderabbitai[bot]`, `cuioss-review-bot[bot]`) and substance match; `get_comments` on #1178 returns exactly these two. The cuioss-review-bot quote is verbatim; the coderabbit quote is **condensed** — the bot's body reads "Excluded labels (none allowed) (1) … skip-bot-review" across a collapsed `<details>`, which the report joins into one clause. Faithful, not verbatim. |
| Coverage 1-of-3, two silent by design (l.133-144) | Consistent with the fetched comments; `sourcery-ai` posted no comment. |
| `sourcery-ai`'s `Sourcery review` check concluded `skipped` (l.137) | `get_check_runs` on #1178: `Sourcery review`, status `completed`, conclusion **`skipped`**. True. *(Left unverified by the first pass.)* |
| CI: the required `verify / conclusion` check went green without a heavy build (l.107-108) | `get_check_runs` on #1178: `verify / conclusion` → **`success`**, `verify / gate` → `success`, `verify / verify` → **`skipped`** — i.e. the docs-only skip fired and the required check still reported green, exactly as claimed. *(Left unverified by the first pass.)* |
| Plan-directory move is a `git mv` carrying `Co-Authored-By: Claude` (l.166) | Commit `30e72b8`: "establish plan 080 directory… No content change", trailer present; PR file status is `renamed`. |
| Report is the last pre-merge commit, pushed before arming auto-merge (l.168) | Three commits, last is `2f49698` (the reviewer-participation correction), i.e. the report was amended after the review bodies existed — consistent with l.133-135. |
| Sub-agent cost ~96,454 tokens / 17 tool calls / 140,976 ms (l.150-151) | **UNVERIFIABLE** — session-internal telemetry, not reachable from the tree or GitHub. |
| "the harness does not surface this session's own token usage" (l.148-149) | **UNVERIFIABLE** — same reason. Correctly labelled as unavailable rather than guessed, which is the right posture. |

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| The measurement itself remains owed; a corpus-bearing session resumes 080 in place and writes `report-02.md` | **Open** | No `report-02.md` exists in the plan directory. No other plan in the epic reports the split. Both spellings were searched, because they do not overlap: `grep -rln "index-answerable" doc/plans/` matches `080-…/plan.md`, `010-lsp-in-execute-lookup-and-write/plan.md` and this audit's own two files — **not** `020-…/report-01.md`, which carries only the underscore field name; `grep -rn "index_answerable\|doc_residency" doc/plans/` adds `020-corpus-residency-admission-control/{report-01.md,verification.md,gaps.md}`. 020 is itself a D0-blocked run (`020-…/report-01.md:3`), so it closes nothing. |
| "nothing needs building — only the corpus needs to be present" | **Open and wrong as stated** | See Report accuracy False-2/False-3 and gaps G3/G4/G7: the per-phase sub-source aggregator does not exist, exploration-share pools phases, and it applies neither schema reader nor the re-entry guard. All three are git-derivable and none needs the corpus. |
| Orchestrator routing: the plan must not be transitioned to `shipped`; re-route to a local session | **UNVERIFIABLE** | The orchestrator ledger lives under `.plan/`, which is git-ignored, so nothing git-reachable records the plan's status either way. |
| Landing: auto-merge armed (SQUASH), merge queue lands it | **Closed** | PR #1178 `merged: true`, `merged_at 2026-08-12T09:24:46Z`, `merged_by cuioss-oliver`. |
| Proposed (optional) `cloud-plan-lane` / `cloud-bridge.md` amendment: a run blocked on a missing environment prerequisite still lands its directory + report | **Open, by design** (operator decision, deliberately not shipped) | `.claude/skills/cloud-plan-lane/SKILL.md:1551-1552` — inside **§ Step 8 — Merge gate** (1310-1558), *not* § Report, which begins at `:1638` — says the report "must state the PR number and the outcome per deliverable — including a run that ended **blocked or partial**, and why"; `cloud-bridge.md:132` (§ Path 2 — Sync) says the same. Neither states that a run blocked on a missing *environment prerequisite* still establishes the directory and lands a report. `grep -rn "prerequisite\|corpus-bearing"` over both files → 0 matches, and reading the surrounding `blocked` occurrences (`SKILL.md:133,209,1098`; `cloud-bridge.md:132`) finds the rule stated in no other words either. |

## Out-of-scope and collateral

Nothing was built that the plan excluded, and nothing was changed outside the plan's own directory. Checked:
PR #1178's complete file list is two paths, both under
`doc/plans/code-intelligence-substrate/080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case/`.
Specifically, none of the four exclusions in `plan.md:113-122` was violated — no old plan was re-run or
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
cycle against GitHub: PR object, file list, commits, review threads, both comment bodies, and the six
check runs. Mutation-tested both schema readers (see Test adequacy).

**Contract obligations checked and found not to bind.** `cloud-plan-lane` § Report now requires a
`> **Verification loop exit:** …` line in every run report, which `report-01.md` does not carry. That is
**not** a defect: the requirement landed in `7d61d67` (2026-08-18, #1297), six days after this run. The
plan's own Verification section (`plan.md:148-158`) imposes four further obligations — D1's reader test,
a record in every schema state, D3's cold read, and a full `./pw verify`. The first three are properties
of D1/D3 output that does not exist, so they are vacuous here; the fourth was correctly discharged as
"no buildable footprint" (verified: the PR's two files are both Markdown).

**What I could not check, and why.**

- The run's own token/tool-call figures and the existence of the verification sub-agent dispatch —
  session-internal telemetry, not durable in the tree or on GitHub. Recorded as UNVERIFIABLE.
- Whether the orchestrator honoured the routing residue — the orchestrator's state lives under the
  git-ignored `.plan/`.
- Whether an instrumented population exists on *some* machine — out of reach by construction, and the plan
  forbids searching for it. My negative is scoped to this clone, which is the same scope D0 claims.
- The full `./pw verify` suite was not run (out of scope for this audit, and the run itself shipped no
  Python).

## Adversarial review

Independent review of this document and `gaps.md`. Attacks run: A1 false positives, A2 false
negatives, A3 vacuous evidence, A4 counts and quotes, A5 actionability, A6 severity/topic,
A7 coverage, A8 internal consistency.

| # | Attack | What was found | Correction applied |
|---|---|---|---|
| A1 | False positives | Every gap's citation was opened and re-read. **No gap was found not to exist** — G3's zero-reader claim, G4's pooling claim and G6's missing-note claim all reproduce. Two citations were stale or wrong: `plan.md:72-73` for the per-phase RANGE requirement (the sentence begins at `:71`), and `plan.md:115-121` for the four exclusions (they span `:113-122`). One near-miss was itself a false positive of mine: `test_manage_metrics.py:1773` and `test_metrics_tokens.py:758` return nothing for the underscore field name, but both point at prose using the hyphenated `index-answerable` — the citations are sound and were kept. | Line ranges corrected to `plan.md:71-72` and `plan.md:113-122`; a note added in Test adequacy that the two test citations are hyphen-spelling prose so a later reader does not re-open the same false alarm. |
| A2 | False negatives | **One material miss.** Correctness-review item 3 certified both schema obligations as "genuinely already implemented … no defect in either". The *readers* are sound, but `exploration-share` — the check that would host D1 — calls neither: `parse_metrics_end_time_presence` is consumed at `audit.py:1700`, `:4454`, `:7477` and nowhere in `:6747-7000`, and `_collect_exploration_share_rows` (`:6862-6888`) applies only the absent-is-not-zero exclusion. The same region reads no `close_count` / `value_scope` (`grep` over `audit.py` returns no occurrence between `:6747` and `:7128`), so `plan.md:106-109`'s re-entry obligation is unmet too — a re-entered phase's counters are summed into a rate unlabelled. Also: the Report-accuracy table marked "Siblings 030/060 … unlike 080" as **Held**, certifying as true the half of that sentence the same document declares false elsewhere. | Item 3 rewritten to separate "reader exists and is sound" from "D1's host consumes it"; new gap **G7** filed (medium, `measurement/metrics`); the sibling row split so only the sibling half is Held, and the 080 half moved into a new **False — 3** entry at `report-01.md:70-73`. |
| A3 | Vacuous evidence | The audit claimed **no** mutation sweep, correctly (nothing executable shipped) — so there was no claimed sweep to re-run. But its residue leans on "the schema readers already exist and are sound", a claim that had been established by reading only. Two sweeps were run to make it falsifiable: defaulting the old-schema branch to `current` (`audit.py:1170-1175`) → `test_audit_check_metrics_end_time_markers.py` **12 passed → 3 failed**; admitting the `unmeasured` token as a measured zero (`:7368-7372`) → the two billing-composition provenance suites **19 passed → 3 failed**. Both restored from a byte snapshot (never `git checkout`), `md5sum` and `git status --porcelain` confirming the file unmodified, and both suites re-run green. | Test adequacy rewritten from "no sweep performed" to the two sweeps with their red/green readings and restore evidence, plus the explicit note that neither sweep says anything about `exploration-share`. |
| A4 | Counts and quotes | Re-derived at check time: `git ls-files` → `*metrics.toon` **0**, `*archived-plans*` **0**, `*.toon` **39**, `.plan/` **13**, `*audit.py` **5** (control) — all reproduce. Grep 0-vs-33 control reproduces (33 = 10+6+3+3+1+4+6 across seven files). Fixture **17 files, no `metrics.toon`** reproduces. PR #1178 re-fetched: 2 files (1 renamed, 1 added), 216 additions, `merged_at 2026-08-12T09:24:46Z`, `merged_by cuioss-oliver`, 3 commits, head `2f49698`, 0 review threads, 2 comments with the stated ids — all reproduce. `.gitignore` at base sha `3a5e2ca` re-read: `.plan/*` **is** line 46. Four defects: (a) `.gitignore` drift credited to "#1250 and #1252" — `git log -- .gitignore` shows only three commits ever, and #1250 is not one; (b) the `grep -rln "index-answerable"` match set named `020-…/report-01.md`, which carries **only** the underscore spelling and does not match that pattern; (c) "bodies and ids match verbatim" — the ids do, but the coderabbit body is condensed, not verbatim; (d) the on-disk `.plan/` listings had already gone stale (`.plan/local` now also holds `marshall-state.toon`). | (a) corrected to #1252 / `c0b4f3e` alone, with the counter-evidence stated; (b) both spellings now searched and the two non-overlapping match sets given, in this document and in G5; (c) softened to "ids exact, coderabbit quote condensed"; (d) the volatile listings replaced by the two durable facts (`archived-plans/` absent, `find` → nothing). Also corrected `git ls-files .plan/` → the twelfth path is `_project.json`, not a `*/enriched.json`. |
| A5 | Actionability | Five of six gaps were executable as written. **G6 was not**: its `Done when` ended "…or an operator decision to decline it is recorded", naming no file, so a later run could not tell "declined" from "never looked at"; and its `Where` pointed at `SKILL.md:1546-1558` labelled "§ Report" — but those lines are in **§ Step 8 — Merge gate**, and § Report begins at `:1638`, so a run following the pointer would edit the wrong section. | G6's `Where` corrected to both real locations (§ Report at `:1638`; `cloud-bridge.md` § Path 2 — Sync at `:112-134`), the quote re-cited to `SKILL.md:1551-1552`, and the `Done when` made observable as a `grep` plus a named file for a declination. G4 additionally given a concrete model to copy (`_parse_billing_phase_fields`, `audit.py:7229-7264`). |
| A6 | Severity and topic | Topics all correct: five `measurement/metrics` entries own `audit.py` / the run's own metrics record, and G6 owns the lane contract → `plan-lane-contract`. One severity mismatch: **G1** sat at `medium` while the calibration puts a claim confined to the run report at `low`, and G1 changed no outcome (the HALT was plan-mandated either way). G2 stays `medium` — it is the same false sentence, but in the handoff a later run acts on, which is a different consequence. G6 stays `low` (a missing note, not a false claim). | G1 re-severitied to `low` with the reason stated in the entry, and the G1-vs-G2 distinction made explicit in both. |
| A7 | Coverage | All five deliverables, out-of-scope compliance, report accuracy and the residue list are covered — no deliverable is silently unmentioned. Three holes: the report's CI claim and the `Sourcery review` check conclusion were asserted but never verified against GitHub; the plan's own Verification-section obligations (`plan.md:148-158`) were never assessed as a group; and `cloud-plan-lane` § Report's `Verification loop exit` requirement — absent from `report-01.md` — was never checked either way. | Two verified rows added to the Report-accuracy table (`verify / conclusion` → `success`, `verify / verify` → `skipped`, `Sourcery review` → `skipped`, all fetched). A "Contract obligations checked and found not to bind" paragraph added: the `Verification loop exit` requirement landed in `7d61d67` (#1297, 2026-08-18), **six days after** this run, so its absence is not a defect; the other four obligations are vacuous or discharged. |
| A8 | Internal consistency | The overall verdict follows from the rows (five CONFIRMED deliverables, false supporting claims, forward work). Every gap traces to a verification finding and vice-versa, including the new G7 ← rewritten item 3. One inconsistency found and one asymmetry: the Report-accuracy table Held a claim the same document called false (see A2); and the gaps preamble asserts the reporter "could be built in a cloud clone today" while the verification never said so, leaving the report's "no git-derivable deliverable" unchallenged at `report-01.md:70-73`. | The Held row split; **False — 3** added; and both documents now state explicitly that the correction does **not** weaken D0, because `plan.md:64-66` mandates the HALT unconditionally — so a later reader cannot mistake "the reason was wrong" for "the halt was wrong". |

**Residual doubt:** the largest remaining exposure is what neither pass could reach — whether an
instrumented population exists on some other machine, and whether the *shape* of a real `metrics.toon`
matches what G3/G4/G7 assume. Every claim about D1's inputs here is derived from the writer
(`manage-metrics.py`) and the contract (`data-format.md`), not from a record; if archived records diverge
from the documented shape, the three build gaps would be right in intent and wrong in detail. Second, I
audited the `audit.py` readers but deliberately did not sweep the `manage-metrics` / `platform-runtime`
suites that write the sub-source fields — they belong to plan 030, and a vacuity defect there would
undermine G3's premise that the fields are trustworthy once read.

**Verdict on the audit:** SOUND AFTER CORRECTION — its central finding (the split has no cross-plan
reporter, and the report's "nothing needs building" handoff is false) survived every attack and was
strengthened, but it under-stated the missing work by one component (G7), certified as Held a claim it
elsewhere called false, and carried four citation or measurement errors that have now been re-derived.
