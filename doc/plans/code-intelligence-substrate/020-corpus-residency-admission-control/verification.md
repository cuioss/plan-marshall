# Verification — 020-corpus-residency-admission-control

**Audited:** `plan.md`, `report-01.md` (the only two files in the plan directory)
**Tree state:** `61a43e5` on `claude/code-intelligence-substrate-analysis-kah884`
**Overall verdict:** CONFIRMED WITH GAPS

The run's load-bearing outcome — the **D0 gate halted on outcome (b)**, no git-reachable population of
instrumented corpus-residency records exists — is independently re-derived and holds at `61a43e5`. The
gaps are entirely in the *supporting* claims of the run report: one materially wrong equation between
the metrics field the run identified and what D1 actually asks for, plus five stale or inaccurate
citations. No shipped code, no out-of-scope work, no collateral.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D0 | GATE: can the residency population be derived in this clone? | HALT (b) — no git-reachable population | Re-derived at `61a43e5`: zero tracked `metrics.toon`, no `.plan/plans/`, no `.plan/local/`, no tracked archived-plan record, no tracked transcript | **CONFIRMED** |
| D1 | Derive the corpus-residency population | Not attempted — gated by D0 | Nothing in the tree derives per-phase residency/consumption; no three-state record read exists | **CONFIRMED (correctly not attempted)** |
| D2 | Section-granular corpus read verb | Not attempted — gated by D0 | No section-granular read verb over `SKILL.md` / `standards/*.md` exists on any surface | **CONFIRMED (correctly not attempted)** |
| D3 | Re-read elimination within an envelope | Not attempted — gated by D0 | Not built; not dropped-on-evidence either (D1 never ran to supply the refutation) | **CONFIRMED (correctly not attempted)** |
| D4 | Restate the epic's value case | Not attempted — gated by D0 | `doc/concepts/token-management.adoc:35` § 4 still carries the unrevised skill-driven-guidance claim | **CONFIRMED (correctly not attempted)** |

## Per-deliverable detail

### D0 — GATE: can the residency population be derived in this clone at all?

- **Required (plan):** `plan.md:56-65` — *"the run has established, from git-reachable evidence alone,
  either (a) a population of instrumented records it can measure, or (b) that no such population is
  reachable here. ⛔ On (b): HALT. Report the plan blocked on corpus availability and stop."*
- **Claimed (report):** `report-01.md:38` — HALT (b), established from git-reachable evidence alone.
- **Found / checks run** (each re-run by me at `61a43e5`, not copied from the report):
  - `git ls-files "*metrics.toon"` → **empty**. Control: `git ls-files "*.toon"` returns 36 paths, so
    the pattern is not silently failing.
  - `git show HEAD:.gitignore` → `.plan/*` at line 45, un-ignored back only `!.plan/marshal.json`
    (46) and `!.plan/project-architecture/` (47). Report claim 1 exact.
  - `ls -la .plan/` and `find .plan -maxdepth 2` → only `marshal.json` and
    `project-architecture/{11 modules,_project.json}`. No `.plan/plans/`, no `.plan/local/`. Report
    claim 3 exact.
  - `grep -l "exploration_\|residency" .plan/project-architecture/*/enriched.json` → **no output**.
    The only tracked `.plan/` content carries no metrics field.
  - `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:2720,4923,4990,9374` — the
    archived-plan audit walks `.plan/local/archived-plans`, which is absent. Report claim 2 exact.
  - `git grep -l exploration_doc_residency_bytes` → 6 paths, of which one is `report-01.md` itself;
    the other **five** are `manage-metrics/standards/data-format.md`,
    `platform-runtime/scripts/runtime_base.py`, `platform-runtime/standards/contract.md`,
    `test/plan-marshall/manage-metrics/test_manage_metrics.py`,
    `test/plan-marshall/platform-runtime/test_metrics_tokens.py`. Exactly the "five tracked files, all
    non-data (two tests, two schema/contract docs, one producer)" the sub-agent reported. Report
    claim 5 exact.
  - `git ls-files "*.jsonl"` → **empty**; no committed transcript corpus.
  - Adversarial extension of my own: `git ls-files "*.toon" | grep -v "^test/"` → three template/document
    fixtures under `marketplace/bundles/**` only; `git ls-files | grep -i archived-plan` outside
    `test/` and the audit skill → **empty**; sibling plan `080-…` (`report-01.md:3`) records
    **`Outcome: blocked (D0 gate → outcome (b))`** on 2026-08-12, two days *after* this run, so no
    sibling has since landed a population.
- **Verdict:** **CONFIRMED.** Outcome (b) is the correct answer, was correct when reported, and is
  still correct at `61a43e5`. The run halted, reported blocked, and did not substitute a stand-in —
  exactly what `plan.md:62-65` demands. Per `plan.md:139-141` this is a **success at D0**.
- **Prohibition respected:** `plan.md:129` forbids going looking for the machine-local measurement.
  The run established structural absence via `git ls-files` and a top-level `ls .plan` — the same two
  observations I re-ran — which establishes (b) without mining anything. **No violation.**

### D1 — derive the corpus-residency population

- **Required (plan):** `plan.md:66-73` — per-phase residency **and consumption** figures, each with
  its own population size, plus a three-state (`current` / `old-schema` / `pre-migration`) archived
  record read.
- **Claimed (report):** `report-01.md:39` — not attempted, gated by D0.
- **Found:** No per-phase residency figure is derived anywhere in the tree; no three-state record read
  exists (`git grep` for `old-schema` / `pre-migration` in `manage-metrics` returns nothing).
- **Verdict:** **CONFIRMED (correctly not attempted).** The gate fired; `plan.md:63` forbids
  proceeding.
- ⚠ **But the report mis-identifies the instrument D1 would use.** See § Report accuracy, item 1, and
  `gaps.md` G1/G2 — this is the audit's most consequential finding, because it means the re-run's
  premise is wrong even once the corpus becomes reachable.

### D2 — a section-granular read verb for the corpus

- **Required (plan):** `plan.md:74-80` — a leaf retrieves one named section of a `SKILL.md` or
  `standards/*.md` without loading the file, carrying the existing content reader's coverage contract,
  with three separately-representable states verified by **three negative controls**.
- **Claimed (report):** `report-01.md:40` — not attempted, gated by D0.
- **Found:** No such verb exists. `manage-architecture`'s `search --content` still returns location
  and strength only (`doc/concepts/code-intelligence.adoc:236` § "Location and strength, never the
  lines"); there is no section-addressed read on any surface.
- **Verdict:** **CONFIRMED (correctly not attempted).** The plan's own Verification (`plan.md:143-146`)
  requires the three negative controls; building the verb on an unverified population premise is what
  D0 exists to prevent.

### D3 — re-read elimination within an envelope

- **Required (plan):** `plan.md:81-85` — *either* the elimination ships *or* D1 shows intra-envelope
  re-reads are rare and the run records the refutation and drops the deliverable.
- **Claimed (report):** `report-01.md:41` — not attempted, gated by D0.
- **Found:** Neither branch was taken, correctly: the "drop on evidence" branch requires D1's
  magnitude, which the gate blocked. Nothing shipped.
- **Verdict:** **CONFIRMED (correctly not attempted).**

### D4 — restate the epic's value case against the corpus measurement

- **Required (plan):** `plan.md:86-90` — the written value case matches what D1 measured, verified by
  an independent **cold read** (`plan.md:146-148`).
- **Claimed (report):** `report-01.md:42` — not attempted, gated by D0.
- **Found:** `doc/concepts/token-management.adoc:35-41` § 4 "Skill-driven guidance — no tool
  exploration" is unchanged and still asserts pre-loaded skills prevent the exploration loop — which
  is precisely the claim `plan.md:115-117` flags as applying to the *codebase* loop while the skills
  are themselves the larger cost. Nothing was restated; no cold read was dispatched for D4 (the
  sub-agent that ran was dispatched against the D0 halt, `report-01.md:101-141`).
- **Verdict:** **CONFIRMED (correctly not attempted).** With no measurement, there is nothing to
  restate the value case *against*; writing one anyway would be the hand-assembled substitution
  `plan.md:64` forbids.

## Correctness review

**No production code shipped, so there is no shipped behaviour to defect-hunt.** PR #1149 changed
exactly two files (`pull_request_read get_files`): `plan.md` — status `renamed` from
`doc/plans/code-intelligence-substrate/020-corpus-residency-admission-control.md`, **zero content
additions** — and `report-01.md`, `added`, 249 additions. `wc -l report-01.md` = 249, so the PR's
`additions: 249` is fully accounted for by the report and the plan move was a pure rename.

What I read to conclude that, and what I checked in it:

- `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py:700-790` — the
  producer docstring for the three `exploration_{sub}_bytes` keys. Correctness-relevant properties I
  confirmed for the audit's own use (not defects, they are deliberate): the sub-split **fails open**
  into `exploration_unattributed_bytes` for an unrecoverable path, and there is **no matching
  `_tool_calls` sub-split** (stated verbatim at `runtime_base.py:770` and
  `manage-metrics/standards/data-format.md:186`).
- `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md:13,163,175-186`.
- `.claude/skills/cloud-plan-lane/SKILL.md:479-510` — the build gate is `*.py`-only
  (`SKILL.md:501-502`), so the report's "no buildable footprint, build skipped" is contract-correct.

**One correctness observation about the run's reasoning, not about code:** the D0 evidence chain is
sound but the field it anchors on cannot answer D1 (§ Report accuracy item 1). Because the answer at
the gate is HALT either way, this does not change the verdict — it changes what a re-run must do.

## Test adequacy

**No test is warranted and none was added** — the run shipped no executable surface. `git ls-files`
under `test/` shows no file touching this plan, and PR #1149's file list is two `doc/plans/**` files.
No mutation sweep was run and none was needed; nothing was left in a mutated state (`git status
--porcelain` was never dirtied by this audit — I only read).

For completeness, the *existing* coverage of the field the report cites is real, not vacuous:
`test/plan-marshall/platform-runtime/test_metrics_tokens.py` and
`test/plan-marshall/manage-metrics/test_manage_metrics.py` both reference
`exploration_doc_residency_bytes`. They are not this plan's tests and were not audited further, since
this plan neither wrote nor changed them.

## Report accuracy

Six claims in `report-01.md` are false, stale, or overstated against the tree at `61a43e5`. The
report's central conclusion is unaffected by all six.

1. **The equation between the metrics field and D1 is materially overstated.** `report-01.md:47-53`
   states the field is *"exactly D1's 'how much of each read document a step actually consumes.'"*
   It is not. Per its own schema (`data-format.md:163`) and producer
   (`runtime_base.py:754-758`), `exploration_doc_residency_bytes` is **one integer per phase**. It
   therefore cannot answer any of D1's four questions (`plan.md:67-68`):
   - *which* documents are read — no path granularity is retained, only a bytes total;
   - *how often* — `data-format.md:186`: *"There is no matching `_tool_calls` sub-split"*;
   - *how many times within one envelope* — same absence, so D3's magnitude is unmeasurable from it;
   - *how much of **each** read document* — an aggregate, not a per-document figure.
   It also measures **residency** (bytes that entered context) and not **consumption** — the very
   distinction `plan.md:125` insists on: *"D1 must measure **consumption**, not just residency."*
   Correct statement: the field is the closest existing *proxy* for D1's residency half; D1's
   per-document and consumption halves have **no instrument in the tree at all**. → `gaps.md` G1, G2.
2. **`data-format.md:152` is the wrong line.** `report-01.md:112` cites the per-phase definition at
   `data-format.md:152`; it is at **line 163** at `61a43e5` (and was at 154 at the earliest commit
   reachable in this shallow clone, `3cb595f`). The companion citation `data-format.md:13` is exact.
   → G3.
3. **"three synthetic test fixtures … `{legacy,plan,unmeasured}`" is now four.**
   `report-01.md:69-71`. `ls .../fixtures/dispatch-loop-replay/` returns `legacy plan undatable
   unmeasured`; `undatable` was added by `d1c3153` (#1278), after this run. Stale, not wrong at
   write time. → G4.
4. **"carry per-*dispatch* context-load columns (`input/output/cache` tokens)" is false for two of
   the three named fixtures.** `report-01.md:72-73`. The `legacy` and `plan` fixtures carry
   `rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}` — no input/output/cache
   columns — both at `61a43e5` and at the earliest reachable commit `3cb595f`, so this was wrong when
   written, not merely stale. Only `unmeasured` (and the later `undatable`) carry them. The
   conclusion the clause supports — none carries the residency field — is nonetheless true. → G5.
5. **"Committed run reports … grepped for residency/consumption vocabulary — no matches" no longer
   holds.** `report-01.md:115-116`. `git ls-files "doc/plans/**/report-*.md" | wc -l` = **112**;
   `git grep -il residency` over that set returns 7 files (020's own report, plus 030, 090, 200, 240,
   250 in this epic and `multiplattform/010`). All post-date this run. Stale; none of them carries a
   residency *measurement*, so the halt is unaffected. → G6.
6. **The coordination quote is attributed to the wrong document.** `report-01.md:245-246` says plan
   010's *"closing note"* anticipates *"a sibling WS-06 plan [that] wants this same client pointed at
   the document corpus."* That sentence is in 010's **`plan.md:178-179`**, not in its report —
   `grep -rin "document corpus\|WS-06" 010-…/report-01.md` returns nothing (control: the same grep
   over the directory hits `plan.md:178`). The substance is correct: PR #1140 is confirmed at
   `010-…/report-01.md:3`, and `marketplace/bundles/plan-marshall/skills/lsp-client/` exists. → G7.

**Claims that held exactly**, re-verified rather than assumed:

- All six numbered D0 evidence items' *conclusions* (§ D0 above).
- Every reviewer-participation verdict, read from the stored comment bodies via
  `pull_request_read get_comments` on #1149: `cuioss-review-bot` posted the PR Reviewer Guide with
  *"No relevant tests / No security concerns identified / No major issues detected"*; `coderabbitai`
  posted only a skip notice naming `skip-bot-review`; `sourcery-ai` posted nothing; `cla-assistant`
  reported `not_signed`. Coverage 1-of-3 is exact.
- The pr-agent registry claim that `skip-bot-review` gates only inline `/improve` comments and not the
  Guide — `automatic-review/standards/pr-agent.md:263,266,345,352`.
- The build-gate claim — `cloud-plan-lane/SKILL.md:501-502`.
- The Step-8 bridge claim *"No write landed under `doc/plans/` outside this plan's own directory"* —
  PR #1149 `changed_files: 2`, both inside the plan directory.
- PR #1149 is `merged: true`, merged 2026-08-10T21:42:53Z by `cuioss-oliver`, head
  `claude/corpus-residency-admission-control-p6zv1u` — the harness-assigned branch, kept as-is, as the
  lane contract requires.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| The plan is **blocked on corpus availability, not retired**; it becomes runnable when a git-reachable population of instrumented corpus-residency records exists (`report-01.md:238-242`) | **STILL OPEN** | `git ls-files "*metrics.toon"` → empty at `61a43e5`. `.plan/` still holds only `marshal.json` + `project-architecture/`. Sibling plan 080, run 2026-08-12 (two days later), records the *same* D0 outcome (b) — `080-…/report-01.md:3`. No sibling has landed a population. |
| The orchestrator's collect step should **keep 020 queued, not mark it shipped** (`report-01.md:241-242`) | **UNVERIFIABLE** | The orchestrator ledger lives under git-ignored `.plan/`, absent from this clone. Nothing git-reachable records 020's queue state. |
| **Coordination note for the eventual D2** — coordinate with 010's `lsp-client` rather than forking a second one, and re-verify at outline whether an LSP-shaped client suits section-granular markdown reads (`report-01.md:244-249`) | **STILL OPEN, and still correct advice** | `marketplace/bundles/plan-marshall/skills/lsp-client/{SKILL.md,scripts/lsp_client.py}` exists at `61a43e5` with four test files. No corpus-facing client was forked. Note that plan `135-remove-lsp-query-facade` and plan `240-skill-lsp-server` now exist in the epic, so the "right home" question the note leaves open has since acquired more candidates — a re-run must re-verify rather than assume. |

## Out-of-scope and collateral

**None.** Every one of the plan's four exclusions (`plan.md:97-107`) is respected trivially, because
the run shipped no mechanism:

- No skill or standard was dropped from a profile (no `marketplace/bundles/**` change at all).
- No standards document was shortened.
- No token saving was quantified — `report-01.md:186-192` explicitly declines to state a token figure
  rather than guessing one, which is the honest form.
- No second content-search verb was created.

No undeclared change: PR #1149's file list is exactly the two files the report declares.

**One unmet plan instruction, not an out-of-scope violation:** `plan.md:43-45` carries a ⛔ directing
the run to re-derive the size figures in the clone (`wc -c` over the persona skill directory, and a
re-count of registered components). The report does not record doing so. I re-derived them, so a
future run need not: `persona-plan-marshall-agent/SKILL.md` = **14,835 bytes**; its `standards/` =
**5 files, 102,086 bytes**; whole directory = **116,921 bytes**; `find marketplace/bundles -name
SKILL.md | wc -l` = **156** across 11 bundles. All three of the plan's leads hold. → G9.

## Method and coverage

**Checked, with the command re-run at audit time in every case:**

- Plan contract read in full (`plan.md`, 163 lines) and report read in full (`report-01.md`, 249
  lines); epic README read.
- Each of the six D0 evidence items re-derived independently by the command the report names, plus
  four adversarial extensions of my own (non-`test/` `.toon` sweep, tracked-`archived-plan` sweep,
  `enriched.json` metrics-field sweep, sibling-plan outcome check).
- Every `path:line` citation in the report resolved against the tree; six discrepancies found.
- PR #1149 verified live through the GitHub MCP: `get` (merged state, head/base, file count,
  additions), `get_files` (rename + add), `get_comments` (all three bot bodies verbatim).
- The lane contract's build gate and `skip-bot-review` rule read at `cloud-plan-lane/SKILL.md:479-510`
  and `1112-1145`.
- The plan's LEAD size figures re-derived from scratch.
- Grep false-negative discipline: every "found nothing" above is paired with a control that finds
  something with the same pattern shape (e.g. `git ls-files "*metrics.toon"` empty *vs* `git ls-files
  "*.toon"` → 36; `grep "document corpus"` in 010's report empty *vs* the same grep over 010's
  directory → `plan.md:178`).

**Not checked, and why:**

- **The originating per-phase measurement.** Deliberately not sought — `plan.md:129` forbids it and it
  is the condition D0 exists to detect. Its absence is what I verified, structurally.
- **Whether the orchestrator kept 020 queued.** UNVERIFIABLE — the ledger is under git-ignored
  `.plan/`.
- **What the report's citations pointed at *when written*.** The clone is shallow
  (`git rev-parse --is-shallow-repository` → `true`, 50 commits, base `3cb595f`), so pre-#1250 file
  states are unreachable. Where it mattered I checked the shallow base as the earliest reachable proxy
  and said so (items 2 and 4 in § Report accuracy).
- **`./pw verify`.** Not run, per the audit brief; the plan's diff carries no `*.py`, so the lane's
  own gate would skip it too.
