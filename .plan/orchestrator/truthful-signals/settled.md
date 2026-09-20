# Settled narrative — `truthful-signals`

Sections relocated out of `epic.md` because their subject is settled: a completed operation whose
result already lives in the machine authority, or a pass superseded by a later, broader one. Each
carries a pointer back from `epic.md` under the cleanup contract's relocation rule. **Nothing here
was rewritten or condensed — every relocated section is byte-identical to what it replaced.**

Relocated 2026-08-22 during the cloud-run ingestion.

## Full-corpus review and reconciliation — 2026-08-09

The manual run of what `PLAN-TRUTH-074` will automate. Enumerated from `status.json` (**the authority,
not a directory glob** — the morning drain's lesson), 127 rows / 43 staged at start.

### Correctness — bidirectional integrity is CLEAN

**127 rows ↔ 127 spec files, no orphan in either direction, no duplicate spec file for any id.** The
check that bites is the reverse one (a spec file with no row), and it is empty.

### Applicability — 15 staged specs intersect what landed today, 3 were materially wrong

Intersected every staged spec's `Expected Surface` against the **143 files** merged since `775399cb2`.
⚠ **Path-qualified, not basename-matched** — a basename pass produced 19 hits including four spurious
`SKILL.md` collisions. **A weaker matcher manufactured four false positives before I tightened it.**

| Spec | Verdict | Evidence |
|---|---|---|
| **-065** | ⛔ **SUPERSEDED — all three surfaces gone or never there** | its five cache symbols return **zero** (#1127 rewrote `_analyze_manage_invocation.py` by −831 lines, removing the caching); and **both folded items live in `plan-retrospective`, not plugin-doctor** |
| **-071** | ✅ **one deliverable CLOSED by measurement** | `lstrip('./')` returns **zero across all of `marketplace/`**; #1132's guard fails the build on re-introduction. Remainder re-counted at outline, **supersede if empty** |
| **-075** | ✅ **open HYPOTHESIS SETTLED** | `doc/plans/…/030-…` is `-063`'s **derived cloud plan** — different gate, **same file** ⇒ serialize, not duplicate |
| -003, -012, -019, -027, -030, -040, -050, -059, -064, -069, -073, -077 | premises **hold at HEAD** | named symbols still resolve (`_PLAN_STATE_PREFIX`, `_filter_main_dirty_paths`, `_mark_superseded_version_dirs`, `DEFAULT_PHASE_6_STEPS`, `records_facts`, `cross_sequence_build_minimality`). `-073`'s `CODEOWNERS` = 0 is a **correctly-labelled asserted absence**, not a refutation |

⭐⭐ **AND THE -065 FINDING CORRECTS ME.** I folded `runtime-008` into `-065` earlier the same evening on
a component guess — *"wrapper-tangle-scan … same component"* — without checking where the scan lives.
**Wrong receiver for four hours.** The drain's dedup discipline did not catch it because **dedup asks
whether a target already holds the signal, never whether the target is the right one.** ⇒ **A fold needs
its RECEIVER verified, not just deduped.** Recorded for `-074` D4.

### Ambiguity — 10 specs carry no Claim Labels

`-004 -007 -009 -014 -015 -019 -020 -022 -023 -024`, all predating the verify-first contract; `-015` and
`-019` also lack a Write-Boundary. ⛔ **Labels were NOT retrofitted.** Assigning `OBSERVED` to a claim
this orchestrator did not observe manufactures provenance — worse than the missing section, because a
wrong label reads as a checked one. **Each now carries a banner: treat every claim as `HYPOTHESIS` until
outline labels them, asserted absences first.**

⚠ Three specs (`-064`, `-065`, `-067`) parse to zero deliverables under the standard heading shapes.
**Not a defect in them — a limit of the count.** Recorded so no one reads `D=0` as "no work".

### Distribution — one split applied, four collision groups recorded

- ⛔ **`-022` (15) SPLIT: D6 → `-038`.** The inbox/archive foldering is four functions in ONE module plus
  the envelope schema — **exactly `-038`'s declared surface** — and disjoint from everything else `-022`
  does. The load-bearing `next_sequence`-scans-both-directories constraint travelled with it.
  ⚠ **HONEST: 15 → 14, and the ceiling is 12. STILL OVER.** A second cut is owed; the suggested cut is
  the `resume_anchor` shape question, which `-074` D8 now depends on. **Declaring a bloat guard satisfied
  by a partial split would be the vacuous-guard shape applied to process.**
- **Collision groups — serialize, do NOT merge** (merging any of these exceeds the ceiling or ties
  unrelated causes):
  - **config**: `-009` + `-023` + `-024` share `_config_defaults.py` / `configuration.adoc` (21 deliverables combined — three different subjects on one surface)
  - **orchestrator inbox**: `-022` + `-038` + `-050` share `orchestrator.py` / `inbox-envelope.md`
  - **cloud lane**: `-063` + `-075` share `.claude/skills/cloud-plan-lane/SKILL.md`
  - **manifest**: `-067` + `-068` share `manage-execution-manifest` / `phase-4-plan` — ⚠ a **weak tie: same component, different cause**

### Duplication

Pairwise surface overlap across all staged specs returned **8 pairs**, every one resolved above as a
collision group rather than a duplicate. **No true duplicate remains in the corpus.** ⛔ The cross-epic
arm is NOT covered by this sweep — a corpus-local scan is structurally incapable of it (the PLAN-PR-018
precedent), and `-074` D4 owns that half.

## Inbox drain — 2026-08-09 (evening), 37 messages, every one dispositioned

Enumerated once: **37 messages, `invalid_count: 0`**, from four senders plus one sibling epic. **None
from `-074`** (the only running plan), so the operator's "ignore the running plan's messages" carve-out
selected nothing — recorded because an empty exclusion set is worth stating rather than leaving implied.

⭐ **Titles were extracted from BOTH shapes this time** — a `# ` heading *and* a `title=` envelope header
— after the morning drain lost a message that carried only the latter. The fix held: 37 enumerated,
37 titled, 37 dispositioned.

**Dispositions: 22 folded · 4 promoted to the lessons corpus · 4 staged (2 new plans) · 4 relayed to
siblings · 2 discarded · 1 Open Defect.**

### ⛔ Three fold pointers needed chasing through a supersession chain — again

`-033 → -034 → absorbed into -074 (RUNNING)`, so `hook-004` had **no fold target at all** and became an
Open Defect. `-039 → -059`. `-052 → -050`. ⇒ **Third drain in a row where the obvious receiver was
superseded.** A fold aimed at a superseded spec is a silent no-op, and the chain is only visible by
reading the condensation table. **This is `PLAN-TRUTH-074`'s D4 with a third worked example.**

### What only the drain could see

- **Three recurrences crossed the multi-plan threshold**: the post-merge footprint resolver (**n=4**),
  the `check-routing-decisions` posture-cutoff attribution (**n=3**), and the `[STEP]`/`[DISPATCH]`
  under-count (**n=3, now quantified at 5×**). None of the reporting plans could see its own recurrence.
- ⭐⭐ **The under-count is THREE distinct mechanisms, not one** — missing brackets on re-fires
  (`hook-002`), unguarded `Executing`/`Completed` pairing (`runtime-006`), and `[DISPATCH]` emitting once
  per **role** rather than per **firing** (`metrics-016`) — **all biased downward, across both ledgers.**
  ⇒ **Fixing any one will make the ledgers agree MORE while remaining wrong.** That composes with the
  shared-bias finding already in `-045`: the two ledgers share **three** blind spots, not one.
- ⭐⭐ **`hook-005` completes a pair with a standing correction.** The recorded lesson was that `ci.py`
  *does* have `--project-dir` — a router flag consumed before dispatch, invisible to an argparse-table
  grep, wrongly reported **ABSENT**. `hook-005` reports `architecture --plan-id` as the same design
  wrongly **REJECTED** when placed after the verb. **One mechanism, a false negative when you search for
  it and a false rejection when you use it.**
- **`runtime-010` corrects `runtime-007` by its own filer** — the timeout discriminator *was* consulted.
  ⇒ `PLAN-TRUTH-078` scopes the **narrowed** defect (*knowing the difference did not change what the gate
  did*), and the spec states explicitly that the uncorrected version is not evidence for it.

### Cross-epic

- **`truthful-signals-028` → `review-apparatus`**: the required bot's `issue_comment`-only publish shape
  (**the mechanism behind six consecutive plans**) and Trigger-A reading `matched` only.
- **`truthful-signals-042` → `code-intelligence-substrate`**: ⛔ **the `-055` obligation was NOT
  discharged and we found it by reading their archive, not by trusting a count.** `-038` and `-040` had
  told them `-055` was a *precondition*; **nothing ever told them it LANDED.** The message carries the
  vocabulary and the `-077` caveat that the historical corpus cannot be measured with it.
- ⚠ **`-010` and `hook-003` rode this epic's inbox BY CONSTRUCTION** — `inbox write` derives its target
  from the writing plan's own epic, so no plan can address a sibling directly. **Fourth and fifth relays
  this cycle.**

## Inbox drain — 2026-08-09, 34 messages, every one dispositioned

Queue enumerated once (`inbox list`): **34 messages, `invalid_count: 0`**. Senders: `daemon-…` (13),
`provider-…` (8), `two-producers-…` (9), `review-apparatus` (2), `code-intelligence-substrate` (1).

⛔ **THREE INTENDED RECEIVERS WERE ALREADY SUPERSEDED, AND THE ROUTING HAD TO BE CORRECTED MID-DRAIN.**
`-042` is **shipped**; `-048` merged into **-030**; `-052` merged into **-050**; `-057` merged into
**-064**. ⭐ **A fold pointer aimed at a superseded spec is a silent no-op** — the text lands in a file
nobody will open. ⚠ **And I had already written one**: the Open Defect opened earlier today said
*"folds into PLAN-TRUTH-057"*, which is superseded — corrected here to `-064`. **This is precisely the
stale-pointer class `PLAN-TRUTH-074` is being built to detect, found by hand one hour after staging it.**

⛔ **Two rules applied throughout, both self-imposed:** nothing was folded into a **running** plan
(`-055`, `-070`, `-013`, `-074`) because re-scoping a spec mid-execution changes the brief under it; and
**recurrences fold onto the existing item rather than becoming new ones.**

| # | Message | Kind | Disposition | Destination / reason |
|---|---|---|---|---|
| 1 | `code-intelligence-substrate-025` | finding | **folded** | `-059` — oracle failed in BOTH directions in one hour; adds `indeterminate` as its own outcome + sample-stability |
| 2 | `daemon-…-003` | candidate-lesson | **folded** | `-045` — leaf session capture overwrites the plan's `session_id` (n=3 with `-007`/L7) |
| 3 | `daemon-…-004` | candidate-lesson | **defect** | three token ledgers, three totals, no population labels — `-055` OWNS IT AND IS RUNNING ⇒ recorded as an Open Defect for its landing, **not folded** |
| 4 | `daemon-…-005` | candidate-lesson | **folded** | `-045` — plan-efficiency anchor cannot match 3 of 5 live `scope_estimate` values |
| 5 | `daemon-…-006` | candidate-lesson | **folded** | `-045` — resolve the post-merge footprint from the merge commit instead of `inconclusive` |
| 6 | `daemon-…-007` | candidate-lesson | **folded** | `-045` — chat-history aspect blind to AskUserQuestion-mediated operator input |
| 7 | `daemon-…-008` | **landing** | **discarded** | PLAN-TRUTH-060 / #1122 — **already reconciled**; `landings/PLAN-TRUTH-060.md` exists. Duplicate landing, no second report |
| 8 | `daemon-…-009` | candidate-lesson | **folded** | `-072` — a green build **clears test-failure findings** even when it ran no tests: T1's consequence, observed |
| 9 | `daemon-…-010` | candidate-lesson | **folded** | `-059` — health signals reported the pinned version while every leaf ran a superseded one |
| 10 | `daemon-…-011` | candidate-lesson | **delegated** | → `review-apparatus` (`truthful-signals-026`) — `create-pr` truncates Intent, drops Non-goals |
| 11 | `daemon-…-012` | candidate-lesson | **delegated** | → `review-apparatus` (`-026`) — Trigger-A skips re-review exactly when no bot review exists |
| 12 | `daemon-…-013` | candidate-lesson | **delegated** | → `review-apparatus` (`truthful-signals-025`) — bot completion states never persisted |
| 13 | `daemon-…-014` | candidate-lesson | **folded** | `-030` (absorbed `-048`) — self-review passed clean over the very class the plan was fixing |
| 14 | `daemon-…-015` | candidate-lesson | **folded** | `-064` — the `.plan/` guard exemption covers **TRACKED** `project-architecture/**`; confirms its core claim |
| 15 | `provider-…-001` (L1) | candidate-lesson | **defect** | one phase, three disagreeing token totals, smallest published as settled — `-055` running ⇒ Open Defect |
| 16 | `provider-…-002` (L2) | candidate-lesson | **folded** | `-045` — a finalize step marked done with no execution_log **and** no dispatch-boundary row |
| 17 | `provider-…-003` (L3) | candidate-lesson | **folded** | `-045` — four context-load columns declared, wired, **zero on every row** |
| 18 | `provider-…-004` (L4) | candidate-lesson | **folded** | `-050` (absorbed `-052`) — `plan-retrospective` ordered after the steps that destroy its inputs |
| 19 | `provider-…-005` (L5) | candidate-lesson | **folded** | `-045` — Phase Dispatch Boundaries section unreachable, loss reports as benign |
| 20 | `provider-…-006` (L6) | candidate-lesson | **folded** | `-045` — `extract-chat-signal` reports Tier-1 success after dropping **99.86%** of the transcript |
| 21 | `provider-…-007` (L7) | candidate-lesson | **folded** | `-045` — `session_id` single-valued while a plan spans sessions (the schema half of #2) |
| 22 | `provider-…-008` (L8) | candidate-lesson | **folded** | `-064` (absorbed `-057`) — `affected_files` frozen at outline: the **mechanism** behind 3 instances |
| 23 | `review-apparatus-019` | finding | **defect** | signal gate forwarded 1 cluster over ≥2 notations — ⛔ **UNOWNED LEAD, no plan manufactured**: the sender explicitly does not assert the gate is defective and one of its two readings is working-as-designed |
| 24 | `review-apparatus-020` | finding | **staged** | **PLAN-TRUTH-075** — cloud-lane build gate omits `errors[]` at two sites; report calls a `quality-gate` run a skip |
| 25 | `two-producers-…-001` | candidate-lesson | **folded** | `-045` — Surface B scans an empty post-merge diff, reports zero leaks; **same root cause as #5** |
| 26 | `two-producers-…-002` | candidate-lesson | **folded** | `-059` — the pin detector misses the running session's own seat (corroborates our 4th-consumer finding) |
| 27 | `two-producers-…-003` | candidate-lesson | **folded** | `-030` — self-review findings queried at 5-execute, filed at 6-finalize: the **mechanism** for #13 |
| 28 | `two-producers-…-004` | candidate-lesson | **delegated** | → `review-apparatus` (`-025`) — `review_completeness` collapses a rejected pair into real silence |
| 29 | `two-producers-…-005` | candidate-lesson | **defect** | `manage-findings list` renders quarantined `raw_input` verbatim, **before ingest has run** — ⛔ `manage-findings` is `-070`'s surface and `-070` is RUNNING ⇒ Open Defect, apply at its landing |
| 30 | `two-producers-…-006` | candidate-lesson | **delegated** | → `review-apparatus` (`-025`) — two bots' real content never reached the findings store |
| 31 | `two-producers-…-007` | finding | **folded** | `-045` — lesson `2026-08-08-20-001` reproduced 3 of 4 instances one plan later; **M3 is now n=3**. The fold IS the explicit deferral the sender asked for |
| 32 | `two-producers-…-008` | **landing** | **discarded** | PLAN-TRUTH-049 / #1125 — already reconciled this session from the operator's paste |
| 33 | `two-producers-…-009` | candidate-lesson | **delegated** | → `review-apparatus` (`-026`) — owed architecture hint on non-actionable bot meta comments |
| 34 | `daemon-…-016` | candidate-lesson | **staged** | **PLAN-TRUTH-076** — the finalize pipeline's OWN PR comments enter the preference corpus and cleared the promotion threshold |

⚠ *(`provider-…-009`, PLAN-TRUTH-011's landing message, was consumed and archived earlier at that
plan's reconciliation and so was not in this drain's enumeration of 34.)*

⛔⛔ **ROW 34 WAS ALMOST LOST, AND THE ARITHMETIC IS WHAT CAUGHT IT.** The clustering pass built its work
list from a `^# ` title sweep; `daemon-…-016` carries its title in a `title=` **envelope header** and no
`# ` line, so it **did not appear in the cluster list at all**. It surfaced only because the post-archive
`inbox list` returned `count: 1` against an expected `0`. ⭐⭐ **A convenience index over a population is
not the population** — the enumeration seam (`inbox list`) was authoritative and the grep was not, and
nothing but the count reconciliation would have distinguished *"33 messages"* from *"34 messages, one
invisible to my index"*. **This is the epic's own archetype, committed by the drain that was filing
instances of it.** ⇒ Folded into `PLAN-TRUTH-074` as a worked example for its D1 enumeration rule:
**enumerate from the authority, never from a derived index.**

**Totals: 34 scanned · 34 archived · 0 invalid · 0 archive-failed.** Dispositions: **17 folded** ·
**6 delegated** (recorded as `discarded` — delegation removes an item from this ledger) · **4 Open
Defects** · **2 staged** (`-075`, `-076`) · **2 discarded** (duplicate landings) · **3 folded rows also
counted in the 17**. ⇒ **17 + 6 + 4 + 2 + 2 = 31 distinct dispositions across 34 rows**, the difference
being the three messages whose fold shares a receiver with another row. **`inbox list` now returns
`count: 0, inbox_state: present` — a looked-and-found-nothing zero, not a could-not-look one.**

⭐⭐ **What the drain revealed that no single message contained.** Three separate messages (#5, #25, and
`check-artifact-consistency`'s `inconclusive`) are **one missing capability**: resolve the post-merge
footprint from the merge/squash commit when the worktree is gone. The answer was one
`git show --name-only` away in every case. ⇒ **Fix the resolver once; do not patch three aspects.**
Neither the reporting plan nor any individual message could see that — it is visible only across the
drain, which is the argument for draining in one pass rather than message-by-message as they arrive.

## Inbox drain — 2026-08-08, 57 messages, every one dispositioned

Drained in one pass at operator request. **42 folded · 7 staged · 5 promoted · 2 reconciled · 1 discarded.**

⛔ **Read the `folded` column honestly.** A fold is an edit. Rows marked *(edit made)* name a spec
file this drain actually changed. Rows marked **LEAD … spec edit NOT made** were routed and recorded
HERE only — the spec edit is owed and has not happened. That distinction exists because this
orchestrator has previously claimed folds that were never written (standing correction C10).

| Message | Kind | Disposition | Where it went |
|---------|------|-------------|---------------|
| `a-rule-that-is-green-because-it-examined-nothing-001` | candidate-lesson | **staged** | PLAN-TRUTH-066 — retrospective session capture overwrites execution session_id |
| `a-rule-that-is-green-because-it-examined-nothing-002` | candidate-lesson | **folded** | PLAN-TRUTH-045 (edit made) — two checks clean over an unexamined population |
| `a-rule-that-is-green-because-it-examined-nothing-003` | candidate-lesson | **staged** | PLAN-TRUTH-066 — order-995 makes the coverage check structurally unmeasurable |
| `a-rule-that-is-green-because-it-examined-nothing-004` | candidate-lesson | **folded** | PLAN-TRUTH-045 (edit made) — zero context-load columns + termination-cause enum short by five |
| `a-rule-that-is-green-because-it-examined-nothing-005` | candidate-lesson | **folded** | LEAD vs PLAN-TRUTH-036 — planning-lane routed deep on S7:risk_prose, a signal the documented S1-S6 table omits. Strong match to 036 (deep lane bought by one signal); spec edit NOT made |
| `a-rule-that-is-green-because-it-examined-nothing-006` | candidate-lesson | **folded** | LEAD, UNOWNED — manifest compose gated a plan-level step on one deliverable change_type; same surface as cluster C14 |
| `a-rule-that-is-green-because-it-examined-nothing-007` | candidate-lesson | **folded** | PLAN-TRUTH-045 (edit made) — phase_steps last-write-wins erases errored attempts |
| `a-rule-that-is-green-because-it-examined-nothing-008` | candidate-lesson | **staged** | PLAN-TRUTH-066 — compile-report drops the section then deletes the evidence |
| `a-rule-that-is-green-because-it-examined-nothing-009` | landing | **reconciled** | PLAN-TRUTH-042 landing — reconciled this session from the operator paste; landings/PLAN-TRUTH-042.md written, row stamped shipped/#1115 |
| `a-rule-that-is-green-because-it-examined-nothing-010` | candidate-lesson | **folded** | PLAN-TRUTH-012 (edit made) — standard claimed N siblings bind, only 1 did |
| `a-rule-that-is-green-because-it-examined-nothing-011` | candidate-lesson | **folded** | PLAN-TRUTH-012 (edit made) — ADR cited as accepted while Status is Proposed |
| `a-rule-that-is-green-because-it-examined-nothing-012` | candidate-lesson | **folded** | PLAN-TRUTH-012 (edit made) — authoring-time MUST vs running-scoped description |
| `a-rule-that-is-green-because-it-examined-nothing-013` | candidate-lesson | **promoted** | lesson 2026-08-08-19-005 — a finding at the self-review iteration ceiling cannot be fixed and re-reviewed in-run |
| `a-rule-that-is-green-because-it-examined-nothing-014` | candidate-lesson | **promoted** | lesson 2026-08-08-19-008 — ordering asserted in Approach prose is not an ordering |
| `a-rule-that-is-green-because-it-examined-nothing-015` | candidate-lesson | **folded** | LEAD, UNOWNED — an outline carried two numbering schemes for the same items with no stated mapping |
| `a-rule-that-is-green-because-it-examined-nothing-016` | candidate-lesson | **promoted** | lesson 2026-08-08-19-007 — a 100%-all-dimensions confidence score has no mechanical check |
| `a-rule-that-is-green-because-it-examined-nothing-017` | candidate-lesson | **folded** | PLAN-TRUTH-012 (edit made) — suppression described without naming its enforcement site |
| `a-rule-that-is-green-because-it-examined-nothing-018` | candidate-lesson | **folded** | PLAN-TRUTH-012 (edit made) — thin pointer duplicates three lines after prohibiting it |
| `a-rule-that-is-green-because-it-examined-nothing-019` | candidate-lesson | **promoted** | lesson 2026-08-08-19-004 — an anti-vacuity fixture must assert what it examined, not only pass/fail (the plan reproduced its own target defect) |
| `a-rule-that-is-green-because-it-examined-nothing-020` | candidate-lesson | **folded** | PLAN-TRUTH-039 (edit made) — invented top-level manage-status subcommand |
| `a-rule-that-is-green-because-it-examined-nothing-021` | candidate-lesson | **folded** | PLAN-TRUTH-039 (edit made) — qgate query invented for qgate list |
| `a-rule-that-is-green-because-it-examined-nothing-022` | candidate-lesson | **folded** | PLAN-TRUTH-039 (edit made) — --deliverable N invented |
| `a-rule-that-is-green-because-it-examined-nothing-023` | candidate-lesson | **folded** | PLAN-TRUTH-039 (edit made) — top-level read invented for request sub-verb |
| `a-rule-that-is-green-because-it-examined-nothing-024` | candidate-lesson | **folded** | PLAN-TRUTH-039 (edit made) — phase_handshake drift from a falling finding count |
| `a-rule-that-is-green-because-it-examined-nothing-025` | candidate-lesson | **folded** | PLAN-TRUTH-039 (edit made) — collect-fragments failed while the retrospective reported complete (fail-open half) |
| `a-rule-that-is-green-because-it-examined-nothing-026` | candidate-lesson | **folded** | PLAN-TRUTH-064 (edit made) — owed architecture enrich call; producing side of the dirty enriched.json |
| `a-rule-that-is-green-because-it-examined-nothing-027` | candidate-lesson | **folded** | PLAN-TRUTH-064 (edit made) — same event as -026, counted once |
| `archived-plan-audit-26-08-08-001` | finding | **folded** | PLAN-TRUTH-039 (edit made) — 463 signatures across 48 of 58 plans; recurring-pattern-detector reports 0 over it |
| `code-intelligence-substrate-023` | finding | **folded** | PLAN-TRUTH-055 + PLAN-TRUTH-059 (both edits made) — ordering decided, pin detector ownership confirmed |
| `lesson-retirement-fails-open-001` | candidate-lesson | **folded** | LEAD vs PLAN-TRUTH-045 — emit [DISPATCH] on re-entry dispatches, not only first entry; spec edit NOT made |
| `lesson-retirement-fails-open-002` | candidate-lesson | **folded** | PLAN-TRUTH-045 (edit made) — RECURRENCE on a second plan; four checks over unestablished populations |
| `lesson-retirement-fails-open-003` | candidate-lesson | **staged** | PLAN-TRUTH-066 — two phase-6 ledgers disagree, neither complete, union is a floor |
| `lesson-retirement-fails-open-004` | candidate-lesson | **promoted** | lesson 2026-08-08-19-006 — re-run self-review detectors over the FIX diff, not only the original diff |
| `lesson-retirement-fails-open-005` | candidate-lesson | **folded** | LEAD vs PLAN-TRUTH-039 — accept or diagnose --plan-id placed after the subcommand; spec edit NOT made |
| `lesson-retirement-fails-open-006` | candidate-lesson | **folded** | LEAD vs PLAN-TRUTH-045 — emit a per-task [ARTIFACT] line at task completion; spec edit NOT made |
| `lesson-retirement-fails-open-007` | landing | **reconciled** | PLAN-TRUTH-044 landing — already shipped as #1113 with landings/PLAN-TRUTH-044.md; row already stamped, no re-reconciliation owed |
| `lessons-handling-26-08-08-01-001` | finding | **staged** | PLAN-TRUTH-067 — cluster C01 build_class phase-5 cannot route (five-way duplicate) |
| `lessons-handling-26-08-08-01-002` | finding | **folded** | LEAD vs PLAN-TRUTH-027 — cluster C02, a build reports its own outcome falsely (10 corpus instances); spec edit NOT made |
| `lessons-handling-26-08-08-01-003` | finding | **folded** | LEAD, RE-ROUTED — cluster C04 vacuous guards (15 instances). Its suggested home PLAN-TRUTH-042 SHIPPED as #1115 today; successors are PLAN-TRUTH-045 and PLAN-TRUTH-065 |
| `lessons-handling-26-08-08-01-004` | finding | **folded** | LEAD vs PLAN-TRUTH-050 — cluster C10, finalize step ordering and instrumentation (10 instances); spec edit NOT made |
| `lessons-handling-26-08-08-01-005` | finding | **folded** | PLAN-TRUTH-059 (edit made) — cluster C11 plugin-cache/executor staleness |
| `lessons-handling-26-08-08-01-006` | finding | **folded** | LEAD, UNOWNED, NEW SPEC WANTED — cluster C13, a premise verified against the wrong artifact (3 live + 3 covered) |
| `lessons-handling-26-08-08-01-007` | finding | **folded** | LEAD, UNOWNED, NEW SPEC WANTED — cluster C14, change_type and plan scoping under-report risk (5 instances) |
| `lessons-handling-26-08-08-01-008` | finding | **folded** | LEAD vs PLAN-TRUTH-016 — cluster C15, agent working discipline (8 live + 5 covered); spec edit NOT made |
| `lessons-handling-26-08-08-01-009` | finding | **folded** | LEAD, UNOWNED, NEW SPEC WANTED — cluster C16, test-authoring discipline (13 instances) |
| `lessons-handling-26-08-08-01-010` | finding | **folded** | LEAD vs PLAN-TRUTH-011 — cluster C17, security hardening at logging/provider boundaries (6 instances). 011 is RUNNING, so this arrives POST-LAUNCH and cannot be scoped into it |
| `lessons-handling-26-08-08-01-011` | finding | **folded** | PLAN-TRUTH-012 (edit made) — cluster C19 doc-contract divergence, 18 corpus instances |
| `lessons-handling-26-08-08-01-012` | finding | **folded** | LEAD vs PLAN-TRUTH-006 — cluster C20, git/worktree/footprint integrity (6 instances); spec edit NOT made |
| `lessons-handling-26-08-08-01-013` | finding | **folded** | LEAD, UNOWNED, NEW SPEC WANTED — cluster C21, execute-phase yield and artifact loss (8 instances) |
| `lessons-handling-26-08-08-01-014` | finding | **folded** | LEAD vs PLAN-TRUTH-009 — cluster C22, manage-* script surface gaps (11 instances). Partly SUPERSEDED by message -016 |
| `lessons-handling-26-08-08-01-015` | finding | **discarded** | cluster C23, consumer-repo Java/CUI domain lessons (2 instances) — OUT OF EPIC SCOPE. The catch-all routing arm sent it here, but these belong in the consumer repos own corpora, not to a plan-marshall plan. Declined back rather than forced into a spec |
| `lessons-handling-26-08-08-01-016` | finding | **folded** | LEAD, UNOWNED — CONFIRMED DEFECT: a header-less lesson is listable, unmatchable and un-retirable. Supersedes -014 cluster C22 framing. Adjacent to the shipped PLAN-TRUTH-044 (lesson retirement fails open) - establish gap-vs-regression |
| `merge-queue-enqueue-does-not-take-001` | candidate-lesson | **folded** | LEAD vs PLAN-TRUTH-027 — build parse reports SUCCESS with tests_failed 0 on any log lacking a pytest summary (a false green in the build oracle); spec edit NOT made |
| `merge-queue-enqueue-does-not-take-002` | candidate-lesson | **staged** | PLAN-TRUTH-066 — metrics.md frozen before 6-finalize, never regenerated after loop-back |
| `merge-queue-enqueue-does-not-take-003` | candidate-lesson | **folded** | LEAD, UNOWNED — two findings stores with disjoint populations; the obvious plan-scoped query excludes the review record and a sibling retrospective concluded 15 findings were absent |
| `merge-queue-enqueue-does-not-take-004` | candidate-lesson | **folded** | PLAN-TRUTH-065 (edit made, staged this drain) — direct-gh-glab-usage 100% false positives |
| `review-apparatus-018` | finding | **staged** | PLAN-TRUTH-065 (new spec) — plugin-doctor help-surface cache keyed on one file of many |

### ⭐ What the drain changed about the epic's picture

- **The vacuous-guard class is now measured, not just instanced.** The archived-plan audit puts
  **463 argparse/contract-drift signatures across 48 of 58 plans** — the corpus's largest waste
  class — while `recurring-pattern-detector` scores that signature **0** at threshold 3. ⛔ The
  instrument that exists to raise recurrence is blind to the biggest recurrence there is.
- **Two independent plans produced the same retrospective-vacuity result** (#1113 four checks,
  #1115 two checks) ⇒ it is a property of the checks, not of a run.
- **Cluster C01 is a five-way duplicate**: five lessons, four days, three components, one defect —
  each filed from whichever side it was observed from. Staged as `PLAN-TRUTH-067`.
- **A suggested home shipped mid-drain**: cluster C04's proposed owner `PLAN-TRUTH-042` landed as
  #1115 the same day, so the cluster was re-routed rather than filed against a closed plan.
- ⚠ **Four clusters asked for new specs and did not get them this pass** (C13 wrong-artifact
  verification, C14 change_type scoping, C16 test-authoring, C21 execute-phase yield). The queue
  already carries 49 staged rows; adding seven specs in one drain is queue-stuffing, not
  throughput. They are recorded above as UNOWNED leads with their corpus counts, which is a
  weaker state than a spec and is recorded as such.

## Condensation — 2026-08-08, 49 staged → 36, grouped by component

Applied under the raised 12-deliverable cap. **13 plans absorbed into 12 receiving plans**, every merge
scoped to one component so that plans on different components remain parallel-safe by construction.

| Receiving plan | Absorbs | Component | Deliverables |
|---|---|---|---:|
| `-064` | `-057` | phase-6-finalize (footprint truthfulness) | 8 |
| `-019` | `-028` | phase-6-finalize (pre-push gate honesty) | 11 |
| `-030` | `-048` | phase-6-finalize (finalize spends what it need not) | 10 |
| `-059` | `-008`, `-039` | tools-script-executor (executor & registry truthfulness) | **12** |
| `-055` | `-053` | manage-metrics (the record and its denominators) | 11 |
| `-045` | `-066` | plan-retrospective (checks over an unwritten record) | 11 |
| `-054` | `-058` (and `-006` earlier) | workflow-integration-git (verdicts that mutate) | 9 |
| `-038` | `-032` | marshall-orchestrator (the inbox protocol) | 10 |
| `-034` | `-033` | marshall-orchestrator (typed state, visible identity) | 10 |
| `-007` | `-043` | manage-config (`_config_core.py` write path) | 10 |
| `-013` | `-056` | platform-runtime (hook provisioning + enforcement) | 7 |
| `-014` | `-021` | manage-execution-manifest (compose inputs nobody writes) | **12** |

### ⭐ Merges that DELETED coordination machinery

Three of these were carrying explicit cross-plan coordination that the merge removes outright:

- **`-038` + `-032`** were carrying an envelope-ownership split, a serialization note, and a
  notify-before-landing obligation — **all of it existed only because two plans were editing one
  schema.** Merged, the message-state vocabulary is designed once. *Neither side can invent a second
  enum if there is only one side.*
- **`-007` + `-043`** were a declared serialization pair with a **CONTESTED row** between them
  (*"whichever runs first must claim or disclaim it"*). The contested row belonged to neither plan
  alone, which is why it was contested; it is now simply in scope.
- **`-055` + `-053`** replaced a three-plan ordering chain with one plan.

### ⭐ Merges that revealed a shared mechanism neither plan could state alone

- **`-059` + `-008`**: `-008` proved `generate_executor` decides freshness by **version stamp with zero
  `sha256`**; `-059` gained CIS's finding that a pinned dir can diverge from source on 8 of 360 files
  while every stamp check passes. **They are the same defect from two directions — a stamp is not a
  hash** — and that sentence is now one deliverable rather than two plans.
- **`-045` + `-066`**: `-066` explains *why* several of `-045`'s checks had nothing to examine. A check
  whose population is empty **because its source has not been written yet** is not the same bug as one
  empty by construction — **and `-045` alone could not tell them apart**, so it would have "fixed"
  checks that were never broken.
- **`-064` + `-057`**: fixing the guard while the declared footprint stays narrow only moves the blind
  spot — the guard then sees correctly and is handed a wrong list.

### ⚠ Recorded weaknesses, not hidden

- **`-014` + `-021` is the weakest merge** and says so in its own header: the tie is the component and
  the compose-input surface, not a shared mechanism. **It is explicitly licensed to be split back at
  outline.**
- **`-030` + `-048`** are merged for the component and the shared re-measurement substrate, **not
  because one causes the other**.
- Every merged spec carries: *"Re-count at outline; overlapping deliverables COLLAPSE rather than
  concatenate — a merged plan that still reads as two plans stapled together has not been merged."*

### Not merged, deliberately

- **`-015`** (the rename) is EXCLUSIVE and already maximal in surface; merging anything in would widen
  an already-maximal blast radius. ⚠ It also had **no `## Deliverables` section at all** — added this
  pass (7 deliverables), because the spec *is* the hand-off brief.
- **`-022` (19 deliverables)** is already over the raised cap and needs a SPLIT, not a merge.
- **`-050` (12)**, **`-023` (10)**, **`-024` (9)** are at or near cap standalone.
- Single-component singletons (`-002 -003 -004 -005 -009 -012 -016 -017 -018 -020 -025 -027 -036 -041
  -046 -063 -065 -067`) have no same-component partner worth merging.

## Premise verification sweep — 2026-08-08, ALL 49 staged plans

Replaces the earlier five-spec sample. Every staged spec's referenced paths were resolved against a
one-pass repo index (12,797 files), and every machine-checkable claim was checked at HEAD.

### ⛔ REFUTED — re-scoped in place, not deleted

| Plan | Claim | HEAD |
|------|-------|------|
| **-057** | *"`references.json` carries **no** `affected_files` key at all"* | **229 of 246** corpus files CARRY it; 17 do not; **0** are empty; sizes min 1 / median 11 / max 120. The key is schema-declared (`_references_core.py:34`) and has a writer (`manage-references add-list --field affected_files`). ⇒ The defect is **inconsistent writing (~6.9%) plus silent UNDER-recording**, not absence. The original was verified on ONE plan — and that plan was one of the 17. |
| **-012** | *"SKILL.md documents 6 of 11 termination causes"* | All **11** values appear in `manage-metrics/SKILL.md` (each ≥3×). Refuted earlier this session; spec re-scoped around the class + guard. |

### ⛔ WRONG SURFACE — corrected in place

| Plan | Named | Actual |
|------|-------|--------|
| **-046** | `manage-status` (`status.metadata.worktree_sha`) | `manage-status.py` and `_status_core.py` contain **ZERO** occurrences of `worktree_sha` / `main_sha` / `config_hash`. The capture surface is `plan-marshall/scripts/_invariants.py` (`_capture_main_sha:437`, `_capture_worktree_sha:517`, `_capture_config_hash:1258`) plus `manage-change-ledger.py` (29 refs). A plan aimed at `manage-status` would have found nothing. |
| **-015** | 131 refs / 31 files @ `dfc4ac15c` | **210 matches / 54 unique files** at HEAD — understated ~74%. |

### ✅ CONFIRMED at HEAD by symbol

- **-007** — `_config_core.py` returns `{'action': 'normalized'}` **unconditionally** (single return site).
- **-008** — `generate_executor.py` carries `MARSHALL_VERSION` comparisons and **zero** `sha256`: freshness
  is decided by version stamp, never by content. ⭐ Independently vindicated by CIS `-024`, which measured
  a pinned dir diverging from source on 8 of 360 files while every stamp-based check passed.
- **-009** — `DEFAULT_ORCHESTRATOR` keys are exactly `['auto_emit']`.
- **-013** — three `"timeout": 5000` literals at the hook-provisioning sites, while every sibling timeout in
  the same file is in seconds (3/5/10/15). ⚠ Line numbers drifted from the spec's `:537/:551/:565` to
  `:715/:729/:743` — **verify by symbol, never by line**, as the standing rule says.
- **-023** — `configuration.adoc` is **exactly 587 lines** as claimed (25 `===` subsections vs 26 claimed).
- **-054 / -058** — `_cmd_baseline_reconcile.py` contains **zero** `merge-base` occurrences, confirming
  the anchor is not recomputed; `no_remote` present in both it and `git-workflow.py`.
- **-036** — the planning-lane routing symbol exists.

### ⭐ POPULATION CORRECTIONS — the sweep widened three plans

- **-064** is **not one site**. Six non-test files carry a literal `.plan/` exemption; **two are the
  confirmed same defect** (`post_run_source_guard.py` and `_invariants.py:_filter_main_dirty_paths`),
  one is a legitimate negative control (`gitignore_setup.py`), and **three are unexamined**. A fix to one
  confirmed site leaves the other live.
- **-039**'s class is measured at **463 signatures across 48 of 58 plans**, with its own recurrence
  detector scoring **0**.
- **-059** gained a fourth failure shape from CIS `-024` (`unmarked == [pin]` **and** the pin stale
  against source).

### ⚠ Method note — and a false refutation I nearly recorded

Several specs state counts over a **scoped** population (*"6 call sites"*, *"32 call sites"*) while a
repo-wide sweep returns a much larger number (257 refs / 54 files; 65 occurrences / 40 files). **Those
are not refutations — they are different denominators.** Comparing them would have manufactured
refutations of correct specs, which is the same defect this epic files against everyone else. Where the
populations could not be matched, the claim is recorded **UNVERIFIED**, not refuted.

**Still unverified and honestly so**: claims resting on runtime behaviour that no static read settles —
`-046`'s `get_base_dir()` main-anchoring, `-017`'s gitignore-exclusion behaviour, `-021`'s
"no caller writes the posture answer", `-030`'s CI re-trigger counts. Each names the symbol to settle it.

## Distribution decisions — 2026-08-08 full reconciliation

A review of all staged plans for correctness, ambiguity, duplication and distribution. **Every item
below is an applied change, not a proposal.**

### Applied — duplication

- ⭐⭐ **`PLAN-TRUTH-006` ABSORBED INTO `PLAN-TRUTH-054`; 006 is now `superseded`.** They were not
  merely overlapping — they prescribed **opposite remedies for the same code path**
  (`_cmd_baseline_reconcile.py`, the `auto_reconciled: true` verdict): 006 said the probe must never
  mutate; 054 said the mutation must fail closed. **Whichever landed second would have deleted or
  hollowed the first**, and neither spec named the other's remedy, so the collision was invisible
  from inside either one. 006's remedy won (a probe whose contract says *"performs no writes"* must
  not move a branch ref) and is carried into 054 as D2′/D3′. 054 keeps the stale-anchor half, which
  006 never addressed.
- **`PLAN-TRUTH-032` / `PLAN-TRUTH-038` — envelope ownership split recorded in BOTH specs.** Not
  duplicates (message state vs sender-stream state) but both add `orchestrator inbox` verbs **and
  envelope fields**. **038 lands first and owns the message-state vocabulary; 032 consumes it.** This
  is the same "neither side invents a second enum" rule already applied cross-epic to TRUTH-055/CIS-022.
- **`manage-metrics` is a three-plan chain, recorded in `-053`**: `-055` (emitted) → `-066` → `-053`.
  A yield denominator computed over an unrepresentable row model and read from a record written after
  its reader would be a ratio built on both defects.

### Applied — correctness / stale state

- ✅ **`PLAN-TRUTH-012` UNBLOCKED.** Its D1 refutation was re-verified at HEAD (the script defines 11
  `DISPATCH_TERMINATION_CAUSES` values and **all 11 appear in SKILL.md**), and the spec is now
  re-scoped around the surviving class + guard. Per the Prep-ready test a refuted clause blocks
  emission only *until the spec reflects the refutation* — it now does. It is the richest
  doc-contract-divergence home in the queue.
- ✅ **`PLAN-TRUTH-013` CONFIRMED LIVE** — `claude_runtime.py` writes `"timeout": 5000` at three hook
  sites while every sibling timeout in the same file is in seconds (3/5/10/15). Premise holds.
- ⛔ **`PLAN-TRUTH-015`'s Emit note was STALE AND WRONG and has been corrected.** It instructed the
  hand-off to carry the full brief **inline**, because *"phase-1-init does not yet read a referenced
  spec file — that is PLAN-41, which ships before this."* **PLAN-41 shipped as #991**, and
  `orchestrate.md` Step 5 now *mandates* the one-line pointer and forbids reproducing spec text at
  the emit surface. Following the stale note would have re-introduced the exact retyping drift that
  retirement removed. ⭐ **A precondition note outlived its precondition and nothing re-read it** —
  the same shape as the stale `BLOCKED` labels on `-012` and the 07-30 emits.
- ⛔ **`PLAN-TRUTH-015`'s surface was understated by ~74%.** Re-derived at HEAD: **210 matches across
  54 unique files**, against the spec's `131 across 31`. Its own note said "re-verify at outline" and
  was right.
- **`PLAN-TRUTH-024` and `PLAN-TRUTH-050` gained a `## Objective`.** Both had content but no
  Objective section. The spec **is** the hand-off brief — `phase-1-init` ingests it as the request
  body — so a missing lead section is an ambiguity defect at the point of maximum consequence.

### Applied — distribution

- ⛔⛔ **`PLAN-TRUTH-015` is declared EXCLUSIVE and sequenced LAST in the orchestrator cluster.**
  Eleven staged plans name `marshall-orchestrator` in their surface (`-007 -008 -014 -022 -032 -033
  -034 -036 -038 -050` + itself). A 54-file rename landing mid-flight conflicts with every one.
  ⭐ **A pure-rename plan should always be the LAST writer on its surface, never the first**: renaming
  first forces ten specs to be re-grounded against new paths for zero behavioural gain.
- **Two exclusive plans now exist** — `-002` (exclusive against anything touching dispatched workflow
  docs) and `-015`. Each costs the whole `parallelization_scope` for its duration. **That is a
  scheduling fact, not a defect**: emitting either is an all-or-nothing choice, never a slot-filler.

### Queue-table drift found and fixed

- **Four SHIPPED plans still had rows in the Ordered Queue** (`-010 -035 -044 -047`) — the exact
  drift class recorded when `PLAN-TRUTH-001` sat there through four reconciliations. Removed;
  `landings/` is their record.
- **Three staged plans had no table row** (`-065 -066 -067`, staged during this session's drain).
  Added. The `queue row ↔ table row move together, both directions` rule fired twice in one pass.
- **Row ↔ spec-file correspondence is CLEAN**: 115 rows, 115 spec files, 1:1, no orphans either way.

### ⚠ Not done, and why

- **Nine plans carry 07-30/08-03 emit labels that no launch followed.** They are recorded as
  *"EMITTED, awaiting operator-confirmed launch"*, but a nine-day-old emit is not a live offer. They
  were **not** silently re-emitted — re-emission is an operator-facing act, and inventing a fresh
  emit for a stale one would misrepresent when the offer was made.
- **Premise verification is a SAMPLE, not an enumeration.** Cheap falsifiable premises were checked
  by symbol (`-012`, `-013`, `-015`, plus `-059`'s and `-065`'s during the drain). The remaining
  staged specs were reviewed for structure, duplication and sequencing but their premises were **not**
  re-derived. ⛔ **Do not read this section as "all 50 premises verified."** Each spec's own
  verify-first clause remains owed by its consuming phase.


## Ordered Queue annotations — five reconciliations 2026-07-30 → 2026-08-08, and the API-Sheriff receipt

⛔ **FULL RECONCILIATION 2026-07-30.** This table had drifted badly from the machine authority and was
rebuilt from `status.json` `plans[]` in array order. Three classes of drift were found, all in the
**confident** direction — the table read as authoritative while being wrong:

1. **Eleven shipped plans were still shown as `launched`/`staged`** (PLAN-92, 99, 111, 110, 109, 89, 81,
   102, 103, 101, and PLAN-105 shown launched while the authority says staged).
2. **Eight rows named plans that do NOT exist in `status.json` at all** — PLAN-61, 64, 76, 77, 78, 82,
   104, 106. They are measurement/index subjects long since routed to `code-intelligence-substrate`;
   the rows outlived the transfer. ⇒ **A transfer that removes a queue row must remove its table row in
   the same move** — this is the same class as the transfer performed today, and is why the five rows
   released to `review-apparatus` are recorded below rather than deleted silently.
3. **Stale blocks presented as live**: four rows carried *"Blocked while PLAN-92 runs"* — **PLAN-92
   shipped as #1041.** Every such block is LIFTED.

| Plan | Status | Surface | Live caveats |
|------|--------|---------|--------------|
| ~~PLAN-105~~ dispatched-leaf-has-no-search-primitive | ⛔ superseded | — | **NOT a staged plan — corrected 2026-07-30.** PR #1046 was **CLOSED unmerged**; `landings/PLAN-105.md` is its closure record, and the row's `status` said `staged` with an unstamped `landing` field for an unknown period. Superseded by `code-intelligence-substrate`'s **PLAN-CIS-001** (ex-PLAN-03) `content-search-seam`, which takes the opposite remedy (a script seam, eliminating `git grep` as a practice). ⇒ **It was offered as an emit candidate this morning because the row lied.** Not renamed: its closure pointer names the old id. |
| PLAN-TRUTH-002 inert-thinking-directives-in-dispatched-docs | staged | `plan-marshall`, `pm-documents`, `pm-plugin-development` | *(was PLAN-97)* Vacuous guard **n=5**. D1 not gated on D3. D2 population-derived from the dispatch roster; report roster size and hit count **separately**. D3 false-positive boundary needs tests both directions. ⛔ **BLOCKED — and NOT by PLAN-203, which has now SHIPPED (#1064).** The old note read "while RUNNING PLAN-203 edits `marshall-orchestrator` docs in the same bundle", which implied the landing would clear it. ⚠ **It does not**: the spec declares this plan **exclusive against anything touching dispatched workflow docs** because D2's sweep is open-ended, so it stays blocked while **any** plan runs. ✅ **As of 2026-07-31 R=0 — PLAN-57 (#1068) and PLAN-202 (#1066) both SHIPPED — so the exclusivity condition is unsatisfied and the row is emittable for the first time.** ⛔ But exclusivity cuts both ways: emitting it **blocks every other candidate while it runs**, so it is a deliberate all-or-nothing choice, not a filler. ⭐ Recorded because trusting the narrower wording would have emitted a colliding plan — **the spec is the authority on sequencing, not the ledger's summary of it.** |
| PLAN-TRUTH-003 migration-shims-have-no-expiry | staged | many bundles' shim sites + `pm-plugin-development`, `manage-metrics` | *(was PLAN-96)* ⛔ Its source inventory has a **contradicted row** — D0 must re-derive population-derived. ✅ **Both blocks CLEARED 2026-07-31 — PLAN-57 SHIPPED (#1068) and PLAN-202 SHIPPED (#1066).** The `manage-status` and `manage-execution-manifest` surfaces are free. ✅ Its `manage-metrics` deferral is **DISCHARGED** — gating PR #1059 merged as `dfe7fde0b`. The "sequence after PLAN-92" block is lifted (#1041). |
| PLAN-TRUTH-004 invented-plan-scoping-flags | staged | `tools-integration-ci`, possibly `plugin-doctor` | *(was PLAN-85)* ✅ **Block CLEARED 2026-07-31 — PLAN-115 SHIPPED (#1065), so `tools-integration-ci` is free.** ⚠ The PLAN-92 overlap condition is settled — PLAN-92 shipped (#1041). Re-check the doctor-rule overlap at outline. ⛔ **DO NOT EMIT WITHOUT RE-GROUNDING**: #1065 migrated ~18 resolver consumers and added a plugin-doctor check, so this row's premise may be **partly overtaken by the very PR that unblocked it**. Re-read the spec against HEAD before emitting. |
| PLAN-TRUTH-005 marshalld-self-reload-on-version-signal | staged | `manage-build-server` | *(was PLAN-58)* ✅ **EMITTED 2026-07-30, awaiting operator-confirmed launch.** Disjoint from all four in-flight surfaces; its do-not-pair-with-PLAN-88 constraint is satisfied (PLAN-88 shipped #1037). Gained two design constraints from #1037: admission and terminal-state are two authorities to reconcile at the admission seam, and a read-time join answers only for its shorter retention window (3600 s journal GC vs 7-day audit rows). |
| ~~PLAN-TRUTH-006~~ baseline-reconcile-persists-merge-commit | ⛔ superseded | — | **ABSORBED INTO `PLAN-TRUTH-054` 2026-08-08.** Both targeted `_cmd_baseline_reconcile.py`'s `auto_reconciled: true` path with **opposite remedies** — this plan: the probe never mutates; 054: the mutation fails closed. **Whichever landed second would have deleted or hollowed the first**, and neither spec named the other's remedy, so the collision was invisible from inside either one. **This plan's remedy WON** and is carried into 054 as D2′/D3′; 054 keeps the stale-anchor half that 006 never addressed. ⚠ It had been sitting as *"EMITTED 2026-07-30, awaiting operator-confirmed launch"* for nine days — the emit was never live enough to matter, which is how the contradiction survived. Row kept as a correction record, like PLAN-105 and PLAN-TRUTH-037. |
| PLAN-TRUTH-007 key-order-canonicalization-unreachable | staged | `manage-config/_config_core.py`, `marshall-steward` | *(was PLAN-67)* ~7 deliverables — evaluate a split at outline. Also owns cache-freshness upstream skew; ⚠ its wrong remediation text is **test-enforced**. Prefer after PLAN-TRUTH-008. ⚠ **BOUNDARY 2026-08-02: shares `_config_core.py` with staged PLAN-TRUTH-043 — SERIALIZATION PAIR.** Ownership split written into both specs; ⛔ the ordering-bypass/false-docstring row is CONTESTED and whichever runs first must claim or disclaim it in D0. |
| PLAN-TRUTH-009 surface-every-knob-in-marshal-json | staged | `manage-config` | *(was PLAN-74)* ⚠ Sequence after PLAN-TRUTH-007. Violation is **defended by a comment**. |
| PLAN-TRUTH-011 provider-logging-path-containment | **shipped** — PR #1123, `landings/PLAN-TRUTH-011.md` | `manage-logging`, `manage-providers` | *(was PLAN-63)* ✅ Landed `38f45faeb`. ⭐ Outline corrected the framing: not "two unvalidated call sites" but an **asymmetry inside one function** — the guard belongs at the shared resolver (`get_log_path`), which all seven entry points route through. ADR-016 + ADR-017. ⛔ **RESIDUE: ~700 unspecified lines** (`_analyze_literal_count.py` +412 / its test +289) entered via a finalize-time **loop-back** and appear in **no deliverable's `affected_files`** — a new *capability*, not a fix to the declared one. ⛔ Its declared **lesson retirement was satisfied by a CONCURRENT run**, so the green housekeeping line is not evidence this plan did it. |
| PLAN-TRUTH-012 canonical-block-diverges-from-argparse-choices | staged | `manage-metrics` SKILL.md, `plugin-doctor` | *(was PLAN-107)* ⚠ Sequence with PLAN-TRUTH-002 / -003 / -004 — shared plugin-doctor analyzer surface. Disjoint from PLAN-TRUTH-009 (different bundle) — do not merge. ⛔ **The doc half of the "11 accepted / 6 documented" item is `code-intelligence-substrate`'s PLAN-CIS-009** (ex-PLAN-13) — do not re-file it. ⭐ **FOLDED 2026-08-02**: second sighting of the producerless-row shape (declared-but-never-emitted `display_detail`) — the failure is a MISLEADING `[FAILED]` headline, not silence. ⚠ **PLAN-TRUTH-040 is the same archetype at the dispatch layer — decide ABSORB vs separate at outline.** ✅ **UNBLOCKED 2026-08-08 — the 'BLOCKED, NOT EMITTABLE' label was STALE.** Its D1 refutation was re-verified at HEAD (script defines 11 `DISPATCH_TERMINATION_CAUSES` values; **all 11 appear in SKILL.md**), and the spec has been RE-SCOPED accordingly: Objective rewritten around the class, D1 marked do-not-implement, D2/D3/D4 intact. Per the Prep-ready test a refuted clause blocks emission **only until the spec reflects the refutation** — it now does, so this plan is EMITTABLE. ⭐ It is also now the richest doc-contract-divergence home in the queue: cluster C19 (18 corpus instances) + 5 first-party #1115 instances folded 2026-08-08. Surface corrected: the fix site is `plugin-doctor`, NOT `manage-metrics` SKILL.md. |
| PLAN-TRUTH-013 hook-timeout-unit-confusion | staged | `platform-runtime/claude_runtime.py` | *(was PLAN-108)* ⚠ Latent, not active — say so. ⚠ The former PLAN-99 / PLAN-77 `platform-runtime` collisions are gone (PLAN-99 shipped #1043; PLAN-77 is no longer in this queue). |
| PLAN-TRUTH-014 landed-residue-promotion-sweep | staged | ~15 skills, docs-only | *(was PLAN-65)* Emit LAST among the lessons plans. |
| PLAN-TRUTH-015 rename-marshall-orchestrator-to-plan-orchestrator | staged | both orchestrator skills, 131 refs | *(was PLAN-49)* ⚠ **Drain-gated — runs last.** ⭐ **Its own collision problem is now CLOSED by this rename**: the old id sat inside the sibling's former 1-49 block, and `TRUTH` scoping makes that collision structurally impossible. The remedy was a **reissue** (available for a staged plan), never a rename verb (does not exist). PLAN-203's Dependencies citation updated in the same move. |
| PLAN-TRUTH-016 skills-carry-incident-history-as-normative-prose | staged | marketplace skills, docs-only | *(was PLAN-118)* — |
| PLAN-TRUTH-017 detect-artifacts-offers-a-live-audit-trail-as-safe-to-delete | staged | `manage-files` / detect-artifacts | *(was PLAN-201)* ⛔ **LIVE DATA-LOSS PATH** — offers a running plan's own live `work.log` (111,433 entries, 19.9 MB) as safe-to-delete. Highest-severity staged row in this epic. |
| PLAN-TRUTH-018 configurable-display-timezone-for-rendered-timestamps | staged | `platform-runtime`, rendering surfaces | *(was PLAN-204)* Storage stays UTC (**32 of 32 call sites verified converged**); only rendering converts. ⛔ Every rendered timestamp must carry its zone label or the conversion makes things worse. |
| PLAN-TRUTH-019 build-gate-coverage-parity | staged | local ruff/mypy config, `pre-push-quality-gate`, module-tests divergence gate | ⭐ **NEW 2026-07-30 — the build-gate half of the former PLAN-60, RETURNED by `review-apparatus`** (operator decision; they kept only the review half as `PLAN-PR-011`). Four holes where the local gate passes what CI fails, incl. `quality-gate` excluding `test/` (three mypy errors reached `verify` on #1037). ⛔ **Serialization pair with PLAN-TRUTH-010** — its D3 zero-scoped-modules branch is the SAME conflation as TRUTH-010's D4b; do not fix it twice. ⚠ Carries eight re-bound lessons; `PLAN-PR-011` holds exactly two and not the rest. ⚠ **Name its PR to `review-apparatus`** if it moves `pre-push-quality-gate.md`. ⭐ **FOLDED 2026-08-02 — a FIFTH hole and the sharpest**: a 2–5s local test-compile green was a stale mypy CACHE HIT while CI checked 660 files and found 2 real type errors. ⛔ The other four holes are about SCOPE; this one is about STALENESS, so widening what the gate examines does NOT close it. Add a duration sanity check. |
| PLAN-TRUTH-020 graduate-deployment-diagram-type-from-api-sheriff | staged | `pm-documents:ref-svg-diagrams` only | ⭐ **NEW 2026-07-30 — LOW PRIORITY by operator instruction, but must not be lost.** Graduate the deployment/topology diagram type from API-Sheriff **#132** (merged `4fc9dd7`) and retire the downstream copy. ⚠ **The operator's request named only the template, but the template CANNOT move alone**: `ref-svg-diagrams/SKILL.md:30` requires a per-type standard, and the templates table at `:67-71` gives **every** template row an owning `diagram-type-*.md` — so the graduated set is the **standard + the template**, which is also what #132 designed for ("shaped to graft upstream unchanged", with a graduation statement). ⚠ API-Sheriff's `integration-test-topology.svg`/`.adoc` **STAY** — consumer-specific content; only the two graduated files are removed, and its README/reference doc get repointed. D1 gates the reference-implementation question (every other type row names one; this one has none upstream). ⚠ **Not this epic's theme** — parked here as the default sink, not because it fits the charter. ⚠ Local API-Sheriff clone was at `#110` while `origin/main` carried `#132` — **pull first**. ✅ **DISJOINT FROM THE ENTIRE QUEUE** (`pm-documents` vs everything else in `plan-marshall` bundles) — a good low-cost parallel filler. |

| PLAN-TRUTH-022 orchestrator-cleanup-verb | staged | `marshall-orchestrator` router + new `workflow/compact.md`, `orchestration-model.md`, `orchestrator.py` | The compaction verb this ledger's own 07-30 compaction was performed by hand. ⚠ Sequence **before PLAN-TRUTH-015** (rename). Input population is #1064's D4 enumeration — **REPORTED, not orchestrator-verified**. | ⭐ **D6 ADDED 2026-08-03 — OPERATOR-RAISED, medium priority**: fold `inbox/archive/` into per-sender subdirectories. **OBSERVED crowding, whole population: 652 archived files in three flat dirs — truthful-signals 428/36 senders, CIS 141/10, review-apparatus 83/8.** ⛔⛔ **BLOCKING PRECONDITION — the archive is a load-bearing INDEX**: FOUR consumers read it with a flat `iterdir()` (`next_sequence` :328, `inbox_counts` :405, `resolve_message` :440, `cmd_inbox_archive`), and subdirs break all four **SILENTLY** because `_MESSAGE_NAME_RE` just fails to match a dir name. ⛔⛔ **`next_sequence` is the data-loss one — a naive `mv` RE-OPENS `PLAN-93` (shipped): sequence reuse against an archived twin.** ⭐⭐ Its docstring states the reason verbatim while the move destroys the guarantee ⇒ **the *comment-explains-a-guard* class from the api-sheriff report, with a DIRECTORY SHAPE as the guard.** ⛔ **OPERATOR CHALLENGE — my framing was WRONG and is corrected**: all four consumers live in ONE module (`_orchestrator_inbox.py`); `orchestrator.py` holds no archive path logic ⇒ **it IS a surgical update — four functions, one file, one PR**, with an ATOMIC (not phased) move; a control test must be verified to fail pre-fix; ⚠ confirm `sender_id` validation forbids separators/traversal — **it was written for a FILENAME component, not a path component**; ✅ **NO cross-epic coordination needed — ONE implementation serves all three epics; the divergence I warned the siblings about CANNOT OCCUR** (correction sent). ⚠ Medium priority, and after the challenge **the size matches it**. ⛔ The only non-obvious part: **the file move alone is silently destructive**, which is what the control test pins. ⚠ Residue: a **stale pinned executor** would run flat-reading code against a foldered archive — bounded, but that pin recurs ~daily.
| PLAN-TRUTH-023 split-and-complete-the-user-configuration-doc | staged | `doc/user/configuration.adoc` + `doc/user/` siblings, `doc/developer/` destinations | ✅ **`doc/**` only — disjoint from every plan in the queue.** ⚠ Sequence BEFORE PLAN-TRUTH-024 (both touch `doc/user/efforts.adoc`). ⛔ D1 must confirm `data-model.md` is the population, not itself a sample. |
| PLAN-TRUTH-024 respread-the-effort-preset-ladder | staged | `plan-marshall/scripts/effort_presets.py`, `_config_defaults.py` seeds, `doc/user/efforts.adoc` | ⚠ Sequence AFTER PLAN-TRUTH-023 (shared `efforts.adoc`) and prefer after PLAN-TRUTH-009 (shared population). ⛔ Seven-site population came from a **single-token grep — widen at outline**. ⭐ **Re-ground against #1069**, which raised phase-3/5/6 effort to `level-5` after this spec was written. |
| PLAN-TRUTH-025 named-recovery-discards-operator-config | staged | `plan-marshall/workflow/planning.md`, `planning-outline.md` (×2 sites) | ⭐ **NEW 2026-07-31 — from the API-Sheriff PLAN-35 incident report, Rec 4.** ⛔ **LIVE DESTRUCTIVE INSTRUCTION**: three docs tell the orchestrator to `git checkout -- .plan/marshal.json` because restoring it "is always safe" — a non sequitur that discards uncommitted OPERATOR config. ⚠ **Exclusive-collides with PLAN-TRUTH-002** (both touch dispatched workflow docs) — cannot run concurrently. ⭐ **Archetype sibling of PLAN-TRUTH-017**, deliberately not merged; D0's population derivation should feed 017. |


| PLAN-TRUTH-027 build-ledger-is-the-build-time-oracle | staged | `.claude/skills/audit-archived-plan-retrospectives/{checks,scripts}`, `plan-retrospective` | ⭐ **NEW 2026-07-31 — OPERATOR REQUEST, consumer half of TRUTH-026.** Report total build time; audit build-time-vs-wallclock and pass/fail ratio. ⛔ **HARD DEPENDENCY on PLAN-TRUTH-026** (needs the `duration_seconds` ledger field) but **SURFACE-DISJOINT from it** (consumers vs producers) — that disjointness is why the split was taken. ⚠ **NOT greenfield**: `sequence-and-build-minimality` ALREADY classifies build durations, by regex-parsing `logs/script-execution.log` for `build-pyproject` calls only — so Maven/Gradle/npm are invisible AND (per 026) phases-1-4 builds never reach that log. **Current build totals are undercounts of unknown size.** ⛔ `killed` must not be folded into `error` — that would report a harness event as a code failure. ⚠ **Routing tension recorded**: by the inbound rule this is `code-intelligence-substrate`'s subject; the operator assigned it here explicitly. Notify them on landing. |



| PLAN-TRUTH-030 finalize-retriggers-ci-after-it-has-already-gone-green | staged | `finalize-step-era-stamp-fill` (project-local), `phase-6-finalize/SKILL.md` dispatcher, `ci-verify`/`automatic-review`/`sonar-roundtrip` barrier | ⭐ **NEW 2026-08-01 — the measured 61 % CI overhead** (58 runs / 36 plans; 16 re-ran). TWO re-trigger sources: (1) finalize's own `mutates_source` steps push AFTER `create-pr` — `era-stamp-fill` ran in **27 of 39** plans and by design pushes a correction once the PR number exists; (2) per-producer triage loop-backs (two plans hit **3**). ⭐ Operator-flagged secondary win: one loop-back barrier = one dispatch envelope, so a **token** saving too — flagged HYPOTHESIS, D0 sizes it. ⛔ **Do NOT resurrect the rebase-placement direction** (deleted TRUTH-029). ⛔ Cannot emit while TRUTH-001 runs. ⚠ Prefer TRUTH-031 first — it makes D0's answer re-derivable. |

| PLAN-TRUTH-034 orchestrator-state-is-narrated-where-it-should-be-typed | **superseded** - ABSORBED INTO PLAN-TRUTH-074 | `marshall-orchestrator/scripts/orchestrator.py` `resume-summary`, `orchestration-model.md` persist contract, `templates/epic.md` | ⭐ **NEW 2026-08-02 — OPERATOR OBSERVATION**, sharpened: `status.json` already types these fields and `resume-summary` already derives them correctly — the defect is **hand-written prose pasted INSIDE the generated markers**, where regeneration cannot correct it and nothing validates it. ⛔ **Occurrence 3 in this same file** (07-30 Ordered Queue, 07-31 missing rows, 08-02 stale START-HERE + missing rows again). ⛔ A frontmatter block in `epic.md` is the WRONG fix — a second copy of the authority. ⚠ The violation was **load-bearing**: three real invariants had no home outside the markers, so enforcing verbatim regeneration alone would DELETE them. ⭐⭐ **ABSORBED 2026-08-09 into PLAN-TRUTH-074 as D8/D9.** Same files (`resume-summary`, the START-HERE contract, `templates/epic.md`'s marker convention) and it is the SUBSTRATE 074's report and restart-verdict stand on - building the verb over narrated state and re-typing afterwards does the work twice. ⛔ **D8/D9 must NOT be split back out**, or the merge's deleted sequencing returns. Its evidence survives verbatim in 074: the block was wrong in the CONFIDENT direction on every count (79 vs 81 rows, 43 vs 46 shipped, `R = 2 of N = 2 - AT CAP` against an actual `R = 1 of N = 1`) and **contradicted itself inside its own markers**; and `review-apparatus` failed in the OPPOSITE direction, rendering "both slots full" over a free slot. |

| PLAN-TRUTH-036 deep-lane-bought-by-one-signal-while-the-discriminating-field-is-null | staged | `manage-status` planning-lane router + `S7` sensor, `phase-1-init` `plan_source` population | ⭐ **NEW 2026-08-02 — largest single actionable cost item on #1077.** `fired=['S7:risk_prose']` bought `deep` for a 9-file change while `scope_estimate=single_module`. ⛔ **Root cause is sharper than "rhetoric read as risk": `plan_source: None`** — the field identifying orchestrator-spec provenance was null, and **3 of 7 signals were null**, so a `signal_set` predicate is structurally biased toward firing. ⛔⛔ **SELF-IMPLICATING: this orchestrator's own ⛔/⚠ authoring convention is the trigger, on EVERY plan this epic emits.** ⚠ The ~1.2M/29% saving is REPORTED, not re-derivable — size at D0. ⛔ Re-ground against #1068 (PLAN-57 fixed a false NEGATIVE at the same seam). |
| PLAN-TRUTH-037 a-terminal-report-is-emitted-before-most-of-what-it-reports | ✅ **RETIRED / superseded 2026-08-03** | absorbed by `PLAN-CIS-028` | **PR #1080 landed (`e1ae38142`)**, corroborated by `code-intelligence-substrate` first-party via `git log`, **not** from the implementing plan's report. It landed as scoped: `POST-RUN REVIEW (post-merge, order > 70)` band, `post_run_review` **derived per-step** (never a list), `lessons-capture` at **order 991 — after `branch-cleanup` (70)**. ⭐ **The condition was worth holding**: retirement was withheld a full day against an OPEN PR. ⭐⭐ **NEW CROSS-EPIC CONTRACT — this epic now receives its inbox messages AFTER the merge**; a landing message is now a post-merge artifact. ⛔ **Do NOT read this as 'the ordering family is fixed'**: (a) the **upward-facing** consumer survives — `lessons-housekeeping` (order 4, `mutates_source: true`) still reads an artifact produced at 990, and band membership **requires `mutates_source: false`** so it **cannot be fixed by relocation** → **TRUTH-044 D3**; (b) `plan-retrospective` (995) still reads `metrics.md` before `record-metrics` (998) writes it → **TRUTH-035**. ⚠ **My mis-attribution corrected**: TRUTH-010's landing naming PR #1081 was NOT an instance of this defect — `ci pr merge` lied. n stays at 2. |
| PLAN-TRUTH-038 inbox-has-no-amend-or-supersede-verb | staged | `orchestrator.py` inbox verb group, `standards/inbox-envelope.md` | ⭐ **NEW 2026-08-02.** A filed message cannot be corrected; the two available routes are a relation-less successor or a hard-rule bypass. ⛔ `archive` is NOT the missing verb — it means *consumed*. ⭐ **`manage-lessons` already solved this** (`supersede` + `.tombstones/`). ⛔ **D1 is load-bearing**: the envelope must gain a mutation-visible field — `barrier-override-not-head-bound-001` was rewritten after its `created` stamp, validates green, and **this orchestrator consumed it this drain unable to tell**. ⛔ SERIALIZATION PAIR with TRUTH-032 (same verb group, both extend the `list` row schema) — **evaluate folding in**. |

| PLAN-TRUTH-040 the-generic-dispatch-template-cannot-carry-a-step-specific-mandatory-field | staged | `phase-6-finalize/SKILL.md` generic templates (×2), `pre-submission-self-review.md` | ⭐ **NEW 2026-08-02 — round-7 item 15, PARTIALLY REFUTED AS FILED.** The step-local snippet does NOT omit `candidates`; the defect is that **a second generic five-field template exists with no slot for step-specific mandatory fields at all**, while the step declares `candidates` Required:Yes. ⇒ Two templates for one dispatch. ⛔ **Do not scope from the original wording.** ⭐ Producerless-contract-row archetype; **#1076's `records_facts` frontmatter is the reference implementation for D2.** |
| PLAN-TRUTH-041 java-skills-route-authors-to-an-anti-pattern-they-never-warn-about | staged | `pm-dev-java:java-null-safety`, `java-core`, `java-lombok` (D5 only) | ⭐ **NEW 2026-08-02 — round-7 items 1/2/4/13 as ONE CHAIN.** Skills say "records for immutable carriers" (correct) + "Optional not @Nullable" in a return-only context (incomplete) + **nothing about record components** (absent) ⇒ a faithful author lands on `record Foo(Optional<String> bar)`, observed **12+ times**. ⛔ **Fixing the Optional rule alone does NOT close it** — item 4 is where the two rules meet. ⭐ Carries a **REFUTATION to preserve**: the "skills demand Lombok" premise is false (`java-lombok:53` routes carriers to records). ✅ DISJOINT FROM THE WHOLE QUEUE — good parallel filler. ⚠ Not our theme; default sink. |



| PLAN-TRUTH-045 the-dispatch-audit-has-an-empty-primary-surface-and-a-retry-blind-secondary-one | staged | `ref-workflow-architecture` (audit rules + pairing contract), `effort resolve-target`, `plan-retrospective`; **+ `scope_creep_check` (folded)** | ⭐⭐ **NEW 2026-08-03 — the flagship archetype INSIDE the tool built to detect it** (2nd time, after PLAN-81). Surface A: 15 `[DISPATCH]` lines vs ~23 envelopes — **every gap is a re-fire**; `lessons-capture` logged "Dispatching", loaded its envelope, recorded `outcome=done`, and emitted **no `[DISPATCH]` line at all** ⇒ indistinguishable from running inline under the audit's own rule. ⛔⛔ Surface B: **zero `effort resolve-target` records across 125 decision-log entries** — the documented pairing rule can only ever return zero. ⭐ **And the audit still reported 3 violations — found by going OUTSIDE the documented rule.** ⇒ the documented rule is dead code that has never been able to fail. ⭐ **FOLDED**: `scope_creep_check` returns `no_baseline_sha` **alongside** `residual_count: 0` / `finding_emitted: false` — one payload whose halves disagree, and downstream reads the verdict half. ⚠ **Second defect at that site** (PLAN-86 #1038 fixed its persist, not its honesty). |

| PLAN-TRUTH-046 main-sha-records-the-worktree-head-and-config-hash-cannot-fail-usefully | staged | `manage-status` (phase-handshake invariant capture, `summarize-invariants`), the phase-5 cwd-pinning path (ADR-002) | ⭐ **NEW 2026-08-03 — TRUTH-010 inbox `-010`.** The 5-execute snapshot records `main_sha = de00dca9b`; `git branch -a --contains` returns **exactly one ref — the plan's OWN feature branch**. It was never on `main`. ⭐⭐ **The same document simultaneously holds the RIGHT value** (`status.metadata.main_sha = 5c41364a5`) ⇒ this cannot be blamed on the sha being unobtainable. Downstream, `summarize-invariants` emitted a **drift warning describing a drift of `main` that never occurred**. ⚠ The snapshot also carries `worktree_sha` ⇒ **two fields recording the same tree under two names.** ⛔ Second half: `config_hash` drifted at **4 of 4** boundaries over a 29-file footprint containing **no config file** ⇒ a detector that cannot discriminate "config changed" from "hash is noisy". ⛔ **Do NOT suppress it** — suppression is indistinguishable from absence. ⛔ Capture mechanism is the filer's own labelled HYPOTHESIS — confirm by symbol at D0. |



⛔ **SECOND RECONCILIATION 2026-07-31.** The four rows PLAN-TRUTH-021…-024 were **absent from this
table entirely** while present and `staged` in `status.json` — the mirror-image of the 07-30 drift
(which had rows for plans the authority did not carry). Same root cause, opposite sign: **a queue
write and its table row are two moves, and only one of them happened.** ⇒ The 07-30 lesson
*"a transfer that removes a queue row must remove its table row in the same move"* is only half the
rule; the other half is that **an ADDED queue row must gain its table row in the same move.** The
rows above were reconstructed from each plan's own spec (`## Expected surface`), not from memory.

⛔ **THIRD RECONCILIATION 2026-08-02.** Both signs of the drift recurred **simultaneously**: two
shipped plans (TRUTH-026 #1075, TRUTH-031 #1076) were still shown `staged`/`RUNNING`, the running plan
(TRUTH-010) was shown `staged`, and three staged plans (TRUTH-032, -033, -034) had **no table row at
all**. The generated START-HERE block above was independently stale on every count and
**self-contradictory inside its own markers** (`R = 2 of N = 2 — AT CAP` twenty lines above `R = 0 of
N = 5 … three genuinely free`). ⇒ **The two prior reconciliations restated the rule and it recurred
anyway** — prose is not the fix. Owned by **PLAN-TRUTH-034**.


| PLAN-TRUTH-049 two-producers-write-one-marker-field-in-two-encodings-and-one-is-not-ours | **shipped** - PR #1125, `landings/PLAN-TRUTH-049.md` | `script-shared/marketplace_bundles.py`, `tools-script-executor/generate_executor.py`, `manage-config/standards/data-model.md`, `marshall-steward/cache_retention.py` | ⭐ **NEW 2026-08-03 — from `code-intelligence-substrate-017`.** ✅ **Observation reproduces to the file**: 400 `.orphaned_at` markers, **180 ISO / 220 raw epoch-ms**, ranges **overlap** ⇒ not a migration, two writers live in the same six-day window. ⛔⛔ **BUT THE REPORTED IMPACT IS REFUTED, both legs, first-party**: (1) **nothing anywhere parses the content** — every consumer tests `.exists()` (`marketplace_bundles.py:39`, `generate_executor.py:530`); no `read_text`/`strptime`/`int()`/cutoff at any site, so the parse-failure and year-58561 scenarios need a decoder that does not exist. (2) `data-model.md:477` + `cache_retention.py:31`: the marker is **advisory and NEVER a keep-or-delete oracle** — retention is a keep-UNION whose knobs only WIDEN ⇒ **no 7-day timestamp expiry to be false about.** ⭐⭐ **The refutation corrected BOTH epics' memory** — we each carried "7-day `.orphaned_at`, keep-oracle = no marker"; the marker is the LIVENESS oracle, not the retention one. ⭐ **What survives**: our source has **exactly ONE writer and it is ISO** (`generate_executor.py:1812`); a whole-repo sweep finds no second ⇒ **55% of the corpus is written by a producer not in this repository** (elimination ⇒ Claude Code's plugin system; D0 confirms). **A shared field with a foreign producer, safe only because we never look** — latent, trigger = the first consumer that reads it. ⚠ Also confirmed: **`.in_use` is NOT a pin oracle** (7 versions, repair-residue trail, `PermissionError` skips the stale-delete) — `installed_plugins.json` is the only honest read. ✅ Pin currently CORRECT: `0.1.1288` is the sole unmarked dir of 41. ⛔ **Deliberately NOT folded into the registry-pin inversion** — the split survives a complete fix of it. **4 deliverables; resist re-inflating.** | **SHIPPED 2026-08-09 as `cf70cf787`.** D-1 returned **outcome (i): our ISO markers DO age out** - established by a **matched control** (5.39 d epoch-ms vs 5.21 d ISO, both present, both unexpired), not by the wait test the spec's own re-grounding had declared unreachable. No differential => the inverted epoch-ms remedy is **REFUTED, not deferred**. Existence-only invariant now **stated AND test-enforced** (+1027-line population-derived test). No unplanned scope: the diff is exactly the 5 declared files. **D3's out-of-band half was owed and is now closed** (both memory records corrected). ⭐⭐ **AND THE LANDING ANALYSIS CAUGHT THE FOREIGN PRODUCER DELETING A MARKER**: `1331` marked (epoch-ms) at 09:39:03.967 while `1327`'s marker was **removed** at .901 - the GC re-anchors the whole set on the registry `installPath`, so the "sole unmarked dir" is a **lagging function of the registry, not an independent witness**. Folded into -059 (oracle) and -069 (lever A). |

| PLAN-TRUTH-050 the-plan's-terminal-report — one emission, at the end, in a slot that exists | staged | every `phase-6-finalize/{workflow,standards}/*.md` frontmatter + `plan-retrospective`/`automatic-review`/`extension-api` SKILL.md + six project-local `.claude/skills/*/SKILL.md`; `_manifest_core.py`; `orchestrator.py` `inbox detect`/`write`; `manage-status` `--fact`; `inbox-envelope.md`; `analyze.md`; `test_finalize_orchestration_routing.py` | ⭐⭐ **CONSOLIDATED 2026-08-03 — absorbs TRUTH-051 + TRUTH-052 at operator direction ("no split"). NINE deliverables; the scope-bloat guard is OVERRIDDEN by explicit operator decision, rationale recorded.** **One seam, three ends** — ⛔ *splitting a seam is how this codebase produces half-fixes*: #1080 closed write-before-MERGE and left write-before-TERMINUS; a renumber without a contract would re-accrete; a fuller landing emitted at the same wrong time still cannot carry what follows it. **WHAT**: 7 findings across 2 of our runs existed ONLY in the operator report; ⭐ operator first-party — ***always***; ⭐⭐ **cross-repo corroboration** (an `api-sheriff` epic drained + reconciled CORRECTLY and its paste still carried 3 more) ⇒ **a property of the CHANNEL, not of drain discipline.** **WHEN**: the landing is emitted at `order: 991` — **3 steps and 2 producers before the run ends**. ⛔ Residue of MY over-broad retirement of TRUTH-037, whose disproving arithmetic (`995 < 998`) I recorded in the same drain and never applied. **WHERE**: `998 → 999 → 1000` contiguous ⇒ **no slot**; a real same-phase collision at `order: 9`; 6 of 27 declarations are project-local ⇒ **no allocation contract**. ⚠ `order: 10` twice is CROSS-PHASE — not a collision, do not "fix" it. ⛔ **Internal order is load-bearing**: D3 must FIRE on the live `order: 9` pair BEFORE D2 fixes it; D4 needs D1's slot; D7 needs D6's delta. ⛔ **NOT ESTABLISHED — the composer's tie-break for equal orders was NOT read.** ⚠ Notify `PLAN-CIS-034` (band contract) before D1. ⭐ **Done when a paste stops yielding anything new — the operator is the oracle.** |




| PLAN-TRUTH-054 baseline-reconcile-anchors-on-a-stale-phase-1-sha-and-one-verdict-auto-merges | staged | `workflow-integration-git/scripts/_cmd_baseline_reconcile.py`, the `sync-baseline`/`branch-cleanup` call sites, `status.metadata.worktree_sha` | ⭐ **NEW 2026-08-03 — from #1083 `-002`, root cause VERIFIED BY CODE READ not inferred.** It fired **TWICE in one run with MUTUALLY INCONSISTENT verdicts** (`no_overlap`, then `overlap_no_content_conflict` / "2 upstream commits") while the branch was **0 commits behind**. ⛔ `_resolve_baseline_sha()` (:119) returns the **phase-1-init SHA and never computes a merge-base**; `:246` and `:555` anchor every range on it. ⭐⭐ **The script CAUSES its own divergence** — its focused path (:415) runs `git merge`, after which the merged-in commits are in history but still not ancestors of `worktree_sha`, so the next call re-reports them. ⛔⛔ **One verdict AUTO-MERGES** ⇒ a stale anchor triggers an unrequested merge that makes the next anchor worse — **a wrong read that also WRITES, and self-amplifying.** ⚠ `no_overlap` is equally unreliable — fixing only the merging path leaves a false-clean verdict live. ⚠ Shares `worktree_sha` with **TRUTH-046**; second defect filed against the same file as **TRUTH-006** — evaluate absorption. |

| PLAN-TRUTH-055 the-metrics-record-cannot-represent-a-re-entered-phase | staged | `manage-metrics` (phase-row close, `record-dispatch-boundary`, `cmd_generate`), `standards/data-format.md` partiality contract, `manage-status` `mark-step-done` | ⭐⭐ **NEW 2026-08-03 — CORPUS-CRITICAL, from #1083 `-009`/`-010`/`-012`.** A re-entered phase row **ACCUMULATES some fields and REPLACES others**: `5-execute` recorded **~2M tokens with `tool_uses: 0` and `agent_duration_ms: 0`**, `duration_seconds: 41973` (11h39m) against a stored span of **37m41s**, and `metrics.md` rendered **a phase ending 2h17m BEFORE it starts.** ⛔ **`partial: false` certifies it** — the contract keys "recorded" off an `end_time` a re-entered phase has. ⭐⭐ *The signal is real, correctly implemented against its stated rule, and answers a NARROWER question than readers take it to answer.* ⛔ **Second defect**: 4 context-load columns (`input/output/cache_read/cache_creation`) are `0` on **all 19 rows across 3 ledgers** — uniformly, not sparsely; every producer omits the flags ⇒ **zero is indistinguishable from unmeasured, and CONTEXT LOAD IS WHERE THE COST IS.** *A schema slot is not a measurement.* ⛔ **Third**: `mark-step-done` is last-write-wins ⇒ a gate that fired 5× finding defects on 3 records as **`self-review clean: 204 candidates examined`** — an eventful gate indistinguishable from a first-pass-clean one, and `204 candidates` is a VOLUME not a coverage figure. ⛔⛔ **CORPUS STRIKE 4, subsuming 1-2**: per-phase figures are not under-counted, some are **arithmetically impossible**; `close_count > 1` is the NORMAL run shape. ✅ Composition survives ⇒ "99% of cost is context" holds. **PRECONDITION OF `PLAN-CIS-030`** — notified. |




| PLAN-TRUTH-059 sync-plugin-cache-updates-the-cache-and-executor-and-never-the-registry | staged | `.claude/skills/sync-plugin-cache/` (meta-project surface), `generate_executor.py` pin/selector, `plugin-doctor` (D1's home) — ⛔ **reads only** under `~/.claude/plugins/` | ⛔⛔ **NEW 2026-08-03 — THE `#896` TRAP IS CURRENTLY ARMED.** After #1084 the sole **unmarked** dir is `0.1.1291` (matching the executor) while `installed_plugins.json` **still pins `0.1.1288`, now orphan-marked and GC-SCHEDULED** ⇒ *the pin points at a directory scheduled for deletion* — precisely what produced `ModuleNotFoundError: plan_logging` on the nifi upgrade. ⭐⭐ **MECHANISM FINALLY NAMED (CIS)**: **`sync-plugin-cache` updates the CACHE and the EXECUTOR and NEVER THE REGISTRY** ⇒ the daily recurrence is structural, not bad luck. ⛔ **A pre-launch check is necessary and demonstrably NOT sufficient** — incidents **7, 8 and 9 fired inside ONE run** (#1085), the last self-observed **inside its own dispatch**, loading a persona **49 versions behind** its envelope with **no loader indication**. ⛔ **Scope: the registry is the plugin manager's file — we do NOT write it.** Ours is *noticing*, *refusing to proceed silently*, *telling the operator what to run*. ⭐ **Oracle**: `unmarked_dirs == [pinned_version]` from `installed_plugins.json` — ⛔ counting executor path-versions does NOT detect it (every incident: clean executor, stale loader), and **`unmarked == []` is a failure state too**. ⚠ My 07:10Z "pin correct" snapshot was stale within hours — *a pin state is a snapshot, never a status.* ⭐ **Neither epic had filed this** — CIS told before staging so the detector is not written twice. |
| PLAN-TRUTH-064 post-run-guard-exempts-every-tracked-plan-file | staged | `phase-6-finalize/scripts/post_run_source_guard.py`, `phase-6-finalize/SKILL.md`, `test/plan-marshall/phase-6-finalize/` | ⭐ **NEW 2026-08-08 — staged from the PR #1115 landing.** `post_run_source_guard` drops every path under `.plan/` *after* the porcelain run has already restricted to tracked files ⇒ **`tracked ∧ .plan/ ⇒ silently exempt`, unconditionally** (`_PLAN_STATE_PREFIX`, `filter_tracked_source`). ⛔ **The report named 2 files; `git ls-files .plan/` returns 14** — including **`.plan/marshal.json`** and all 13 `project-architecture/*/enriched.json`. Live instance: #1115's finalize left 4 architecture hints dirty on main and the guard said `clean: true`. ⭐ This is the **#990 class re-entering through the guard built to close it** — a guard whose exemption is a path prefix rather than a property of the file. D2 makes it publish its examined population; D3 requires a matched positive/negative control pair. |
| PLAN-TRUTH-065 help-surface-cache-is-keyed-on-one-file-of-many | staged | `plugin-doctor/scripts/_analyze_manage_invocation.py` + its tests | ⭐ **NEW 2026-08-08, delegated in by `review-apparatus` (`-018` § 3)** under the three-way rule — a quality-gate correctness defect, not a PR/review one. `_content_hash` keys the cached `--help` surface on **one file's bytes**; `ci.py` declares **no parser at all** (verified by symbol: zero `add_argument`, only `from ci_base import`). ⛔ **Symmetric**: false RED (a doc updated to a new flag is flagged as inventing it — #1087 hit exactly one) and **false GREEN** (a doc using a REMOVED flag validates clean). ⚠ `_CACHE_VERSION` guards derivation-logic drift, NOT dependency drift. Absorbs `merge-queue-...-004` (the `direct-gh-glab-usage` rule scoring 100% false positives on the CI abstraction it audits) — same gate, same *report-a-problem-that-is-not-one* shape. |
| PLAN-TRUTH-067 derive-verification-emits-a-build-class-phase-5-cannot-route | staged | `manage-architecture` derive-verification, `manage-execution-manifest` compose, `phase-4-plan` (all HYPOTHESIS) | ⭐ **NEW 2026-08-08 — routed cluster C01, the flagship dedup result.** **Five lessons, four days, three components, ONE defect** — each filed from whichever side it was observed from, which is why nobody noticed. Emission returns `status: success` while carrying a command compose cannot route (`unresolvable_step verify:compile`). ⛔ **ENTIRELY SECOND-HAND — no symbol read by this epic, and the lessons are dated 2026-07-28.** D0 re-derives against HEAD first; an already-fixed outcome retires the lessons and is a legitimate result, not a wasted run. |
| PLAN-TRUTH-068 change-type-is-one-word-for-two-different-scopes | staged | `manage-execution-manifest` compose, `phase-4-plan` (both HYPOTHESIS) | ⭐ **NEW 2026-08-08 at the pre-restart reconciliation — GIVES CLUSTER C14 AN OWNER**, which had been an unowned lead for want of a first-party instance. `compose` takes `--change-type` as a required caller flag and **never reconciles it against `status.metadata.change_type`**, so a caller forwarding the FIRST DELIVERABLE's value narrows phase-5 **for the whole plan** (`verification` passed while the plan was settled `bug_fix`). ⭐ The run's own logs disagreed with themselves — `detect-change-type` and `architecture-refresh` both had `bug_fix`; only compose disagreed — **and nothing noticed**. ⛔ SERIALIZE against `-014` (same component, and 014 is AT the 12 cap, which is why this is a separate plan). Complementary to `-045`, which owns the cross-check that failed to catch the narrowing. |
| PLAN-TRUTH-069 collapse-the-version-selection-machinery | staged | `generate_executor.py`, `marketplace_bundles.py`, `cache_retention.py`, the executor template | ⭐⭐ **NEW 2026-08-08 from an operator question — "can't we simplify?" ANSWER: YES, and 4 of the 7 links are OURS.** The cache is versioned because Claude Code's layout is; but the pollution detector, the `.orphaned_at` marker and the retention pins are all **our containment for one choice — the executor bakes absolute version-pinned paths**. ⛔⛔ **THE ANTI-SATURATION GUARANTEE IS REFUTED BY OBSERVATION**: the docstring says saturation is *"structurally impossible"*; `unmarked == []` was measured after #1122. The guarantee is CIRCULAR — the pin's disk arm selects among LIVE dirs, so once saturated it cannot recover. We are running in the documented degraded fallback with a warning nobody reads. **Levers: (A) resolve paths at executor RUNTIME — makes the split unrepresentable; (C) stop writing someone else's field, which retires TRUTH-049's two-producer defect outright; (B) single-version, evaluate only.** ⛔ **DO NOT EMIT while TRUTH-049 RUNS** — two plans, one field, opposite directions is the -006/-054 collision shape. |
| PLAN-TRUTH-070 runtime-edge-paths-crash-or-silently-lose-data | staged | `_providers_core.py`, `file_ops.py`, `_findings_core.py`, `ci_base.py`, `_cmd_manage.py`, opencode emitter | ⭐ **NEW 2026-08-09 from the retired `doc/review-26-07-04.md`, ALL RE-VERIFIED AT HEAD.** Three silent-wrong-result bugs (metadata/body overlap; bulk resolve WIPES `resolution_detail`; root module path collapses to `''` which matches everything) + three crashes (HTTP-date `Retry-After`; empty basic-auth password; naive/aware subtraction outside its guard) + retiring `lstrip('./')` as a prefix-strip. ⚠ **TASK-grouped, not component-grouped — stated exception**: 5 components, but each fix is 1-5 lines. ⛔⛔ **CANNOT START until PLAN-TRUTH-011 lands** — R2/R3 are in `_providers_core.py`, 011's surface. |
| PLAN-TRUTH-071 multi-target-generator-edge-paths | staged | `marketplace/targets/{claude,opencode}/**` | ⭐ **NEW 2026-08-09, re-verified at HEAD.** Component-clean. ⛔ **[G1] HIGH: the Claude emitter's `shutil.rmtree` has NO containment guard** while OpenCode has `_safe_rmtree` — a mistyped `--output` destroys real source; the docstring's *"target/ is gitignored"* defence assumes the input is correct. Plus a non-pruning OpenCode emitter (output drifts past source), a frontmatter fence found by raw substring, an unguarded `json.loads` that crashes the equality CLI, a path-keyed cache (same archetype as `-065`), and a double-counting diff layer. |
| PLAN-TRUTH-072 test-suite-false-confidence | staged | `test/run-tests.py`, `test/conftest.py`, fixtures, 5 test modules | ⭐⭐ **NEW 2026-08-09 — THE EPIC'S THESIS INSIDE THE SAFETY NET.** `run-tests.py` runs each file as a script and calls exit 0 a pass; only ~10 of ~545 files invoke pytest, so **~535 run ZERO tests and print `✓ passed`**. Survives because the CI path is pytest via `build.py` — nothing that gates a merge ever notices. Plus 5/5 dead `sys.modules.setdefault` mocks implying an isolation they lack, `/Users/oliver` in 3 fixtures, an autouse guard walking the real FS, and two overlapping env-mutation mechanisms. ✅ T2/T3/T4 ALREADY FIXED; T5 DROPPED (stale population). |
| PLAN-TRUTH-073 ci-and-supply-chain-hardening | staged | `.github/workflows/**`, `.github/`, `SECURITY.md`, `pw` | ⭐ **NEW 2026-08-09, re-verified at HEAD.** Two security-relevant leads: **[B1]** `${{ github.ref_name }}` interpolated into a bash `run:` in a `contents: write` context (2 sites) and **[B2]** a workflow with NO `permissions:` block. Plus over-broad `contents: write`, duplicate CI runs per push, and a stray PowerShell `irm` in the vendored `pw` uv fallback. ⛔ **B3/B6/B7 turn on the branch-protection ruleset, which is NOT VISIBLE IN-REPO — they must ASK, not assume.** ✅ **[B4] uv.lock ALREADY FIXED** — closed incidentally by #1122's operator-decided lock refresh. |
| PLAN-TRUTH-074 spec-corpus-review-and-cleanup-entry-point | staged | `marshall-orchestrator/SKILL.md`, `marshall-orchestrator/workflow/cleanup.md` (new), `marshall-orchestrator/scripts/orchestrator.py`, `persona-marshall-orchestrator/standards/orchestration-model.md`, `test/plan-marshall/marshall-orchestrator/` | ⭐ **NEW 2026-08-09, OPERATOR-REQUESTED**: promote the hand-run cleanup ritual to a single `cleanup` verb — re-ground every staged spec against HEAD, detect already-fixed / ambiguous / duplicate specs, judge and apply redistribution, then compact, archive, persist and report restart-readiness. ⛔⛔ **NEARLY FILED AS A DUPLICATE OF -022, AND THE BOUNDARY IS THE FIRST DELIVERABLE**: -022 owns the LEDGER half (epic.md compaction, GENERATED-block mechanism, resume_anchor shape, inbox/archive foldering) and even names `cleanup` as the operator's word; **this plan owns the SPEC-CORPUS half plus the single entry point**, and CALLS -022's compaction stage rather than re-implementing it (reports `not_available` if -022 has not landed). ⭐ **The capability is proven by use, not speculative**: the live `resume_anchor` carries FOUR hand-written `PRE-RESTART CHECK` blocks, and the two manual corpus passes found `-057`/`-012` REFUTED, `-046` on the wrong surface (zero occurrences in the named component) and `-015` understated by ~74%. ⛔ **"Apply all the changes" is honoured per-class, and every applied change is named in the report** — a silent application is indistinguishable from a lossy one. ⛔ **No spec file is ever deleted; duplicates are superseded.** ⛔ Skips any spec whose row is `running`. ⚠ Serialize against -022 (same component); merge evaluated and declined at D0.1, rationale recorded. |
| PLAN-TRUTH-075 cloud-lane-build-gate-reads-one-field-short | staged | `.claude/skills/cloud-plan-lane/SKILL.md` (`:278`, `:376-377`, Step 5 trigger table, run-report `## Build gate` `:693-695`) | ⭐ **NEW 2026-08-09 from the drain (`review-apparatus-020`), routed here by the operator.** Two contract statements understate their check IN THE SAME DIRECTION - toward clean. **(1)** The build gate requires `status` + `total_issues` and **never mentions `errors[]`**, at TWO sites - and the per-commit site is the one that runs most often. The lane's own sentence concedes the premise (*"the exit code proves nothing; only the log does"*) then names two of the three fields. **(2)** Step 5 defines THREE build triggers; the run report asks for ONE, so a run that correctly ran `./pw quality-gate` and PASSED reports *"no Python changes, build skipped"*. ⭐⭐ **Anti-correlated with the interesting case**: the docs-and-skills-only change is exactly the run whose coverage a reader wants confirmed, and exactly the one guaranteed to understate it. ⛔ **D0 GATES SEVERITY**: whether the wrapper can emit green `status` with non-empty `errors[]` was explicitly NOT established by the sender. ⚠ Line numbers are second-hand - re-verify at outline. ⚠ Adjacent to `doc/plans/truthful-signals/030-…` (different subject: merge gate, not build gate). |
| PLAN-TRUTH-076 the-pipeline-talks-to-itself-and-learns-from-the-echo | staged | `default:finalize-step-preference-emitter`; `workflow-integration-github` `fetch_findings`; `tools-integration-ci` `pr prepare-comment`; the architecture-hint store | ⭐⭐ **NEW 2026-08-09 from the drain (`daemon-…-016`) - the epic's theme in its purest form.** The preference emitter promotes a `(module, finding-class, disposition)` tuple at `preference_min_recurrence` 2. On #1122 exactly one cleared - `(default, pr-comment, taken_into_account)` - and **BOTH contributing findings were written to the PR by the finalize pipeline itself** (a restoration of the paragraph `create-pr` had truncated, and the orchestrator's own `/review` trigger comment). `fetch_findings` ingests every non-noise PR comment **regardless of author**, each was necessarily disposed `taken_into_account`, and two is the threshold. ⛔ **SELF-REINFORCING: the more the pipeline talks to itself, the stronger the false preference** - no natural ceiling, since the corpus grows with chattiness rather than judgement. ⛔ Both findings are **unattributed**, so they collapse into the `default` bucket - the widest-blast-radius sink. ⭐ One delegated bug (`create-pr` truncation) MANUFACTURED the corrective comment that became the evidence. ✅ **No hint was promoted - the step filed this instead**, so the guard held on the run that found it. ⛔ D0 must survey the EXISTING corpus before assuming it is clean OR dirty. |
| PLAN-TRUTH-063 merge-gate-cannot-tell-a-required-check-from-a-decorative-one | staged | cloud-plan lane merge gate (cloud plan 030, PR #1121 merged) | ⚠ **Table row added 2026-08-08 — it was missing while the queue row existed**, the `queue row ↔ table row move together` rule firing again. Spec is authored and the cloud plan landed; **ready to emit.** |

⛔ **FIFTH RECONCILIATION + LEDGER COMPACTION 2026-08-03 (end of session).** The `resume_anchor` was
compacted **52,754 → 17,484 chars (−66%)** on `PLAN-TRUTH-022`'s own axis — **DERIVABLE regenerated or
dropped, NARRATIVE preserved.** ⛔ Found real rot in it while doing so: `=== RUNNING ===` still named
`PLAN-TRUTH-010`, **shipped two landings earlier** — the exact drift `PLAN-TRUTH-034` exists for, in the
anchor rather than the table. ⭐ **`=== STANDING RULES ===` was carried VERBATIM** (4,603 chars) because
it declares itself the anti-rework record; the numbered items whose content now lives in a spec were
reduced to **pointers, not deletions**, and the one correction not held anywhere else (the
`lane: off` recurrence) was **verified present at `epic.md:550` before its anchor copy was dropped.**
⚠ **`.plan/local/` is NOT git-tracked**, so a compaction is irreversible — the coverage check was done
*before* the write, not after.

⛔ **FOURTH RECONCILIATION 2026-08-03** — clean this time, and the *method* is why. The both-directions
cross-check (queue rows ↔ spec files ↔ table rows) was run **before** the drain rather than after, and
found nothing outstanding from the third. ⚠ **That is one clean pass, not a fixed process.** The
recurrence at the third reconciliation happened *despite* two prior restatements of the rule, so the
correct read is that **the check caught up with the drift, not that the drift stopped.** Still owned by
**PLAN-TRUTH-034** — a check that must be remembered is not a check.

### Merged away 2026-08-08 — retained as the record

| Plan | Status | Surface | Note |
|------|--------|---------|------|
| ~~PLAN-TRUTH-008~~ | ⛔ merged | — | **MERGED INTO `PLAN-TRUTH-059` 2026-08-08** under the raised 12-deliverable cap, grouped by COMPONENT for parallel safety. Rationale lives in the receiving spec. Retained as the record. |
| ~~PLAN-TRUTH-021~~ | ⛔ merged | — | **MERGED INTO `PLAN-TRUTH-014` 2026-08-08** under the raised 12-deliverable cap, grouped by COMPONENT for parallel safety. Rationale lives in the receiving spec. Retained as the record. |
| ~~PLAN-TRUTH-028~~ | ⛔ merged | — | **MERGED INTO `PLAN-TRUTH-019` 2026-08-08** under the raised 12-deliverable cap, grouped by COMPONENT for parallel safety. Rationale lives in the receiving spec. Retained as the record. |
| ~~PLAN-TRUTH-032~~ | ⛔ merged | — | **MERGED INTO `PLAN-TRUTH-038` 2026-08-08** under the raised 12-deliverable cap, grouped by COMPONENT for parallel safety. Rationale lives in the receiving spec. Retained as the record. |
| ~~PLAN-TRUTH-033~~ | ⛔ merged | — | **MERGED INTO `PLAN-TRUTH-034` 2026-08-08** under the raised 12-deliverable cap, grouped by COMPONENT for parallel safety. Rationale lives in the receiving spec. Retained as the record. |
| ~~PLAN-TRUTH-039~~ | ⛔ merged | — | **MERGED INTO `PLAN-TRUTH-059` 2026-08-08** under the raised 12-deliverable cap, grouped by COMPONENT for parallel safety. Rationale lives in the receiving spec. Retained as the record. |
| ~~PLAN-TRUTH-043~~ | ⛔ merged | — | **MERGED INTO `PLAN-TRUTH-007` 2026-08-08** under the raised 12-deliverable cap, grouped by COMPONENT for parallel safety. Rationale lives in the receiving spec. Retained as the record. |
| ~~PLAN-TRUTH-048~~ | ⛔ merged | — | **MERGED INTO `PLAN-TRUTH-030` 2026-08-08** under the raised 12-deliverable cap, grouped by COMPONENT for parallel safety. Rationale lives in the receiving spec. Retained as the record. |
| ~~PLAN-TRUTH-053~~ | ⛔ merged | — | **MERGED INTO `PLAN-TRUTH-055` 2026-08-08** under the raised 12-deliverable cap, grouped by COMPONENT for parallel safety. Rationale lives in the receiving spec. Retained as the record. |
| ~~PLAN-TRUTH-056~~ | ⛔ merged | — | **MERGED INTO `PLAN-TRUTH-013` 2026-08-08** under the raised 12-deliverable cap, grouped by COMPONENT for parallel safety. Rationale lives in the receiving spec. Retained as the record. |
| ~~PLAN-TRUTH-057~~ | ⛔ merged | — | **MERGED INTO `PLAN-TRUTH-064` 2026-08-08** under the raised 12-deliverable cap, grouped by COMPONENT for parallel safety. Rationale lives in the receiving spec. Retained as the record. |
| ~~PLAN-TRUTH-058~~ | ⛔ merged | — | **MERGED INTO `PLAN-TRUTH-054` 2026-08-08** under the raised 12-deliverable cap, grouped by COMPONENT for parallel safety. Rationale lives in the receiving spec. Retained as the record. |
| ~~PLAN-TRUTH-066~~ | ⛔ merged | — | **MERGED INTO `PLAN-TRUTH-045` 2026-08-08** under the raised 12-deliverable cap, grouped by COMPONENT for parallel safety. Rationale lives in the receiving spec. Retained as the record. |

### Transferred out — recorded, not deleted

Released to **`review-apparatus`** 2026-07-30 on operator instruction (handover `truthful-signals-001`).
Rows are `transferred` in `status.json`; each is re-issued there as `PLAN-PR-NNN`, so **no id travels**.

⛔ **CORRECTION 2026-07-30 — the "ids return free" claim was FALSE THE MOMENT IT WAS WRITTEN, for all
five rows.** Caught by `review-apparatus-005`, not by us. The handover and the band note both said the
five ids returned to the `50-119` band free for reissue **while the five rows still occupied them**. A
reissue at `PLAN-116` would therefore have produced **two rows with the same id**, and
`queue --transition PLAN-116` resolves to whichever the locator reaches first — **a silent wrong-row
mutation, not a visible error.**

⭐ **This is verbatim the archetype our own anchor warns about** — *"a numbering invariant written after
the fact describes the future, not the past; AUDIT THE POPULATION WHEN YOU WRITE AN INVARIANT"* — and we
committed it in the same document that carries the warning, one section apart.

✅ **RESOLUTION: the rows STAY, and the five ids are PERMANENTLY SPENT.** `review-apparatus` offered
either retiring the rows or striking the claim; we take the second, because (a) the orchestration
standard's posture is that an epic is the durable audit record — close freezes and archive relocates,
neither deletes — so dropping the rows would erase the only trace that this work was ever ours, and
(b) since **all new work is `PLAN-TRUTH-{NNN}`**, a numeric reissue will never be wanted, so treating
`60 / 100 / 116 / 117 / 119` as spent costs exactly nothing. ⇒ **Never reissue those five numbers.**

| Plan | Was | Subject retained for provenance |
|------|-----|--------------------------------|
| PLAN-116 | staged | Two review detectors check the wrong observable; one now fires on every loop-back. Six-plus participation shapes incl. **Shape F** (post-#1053 pr-agent unsubscribed from rebases while `sync-baseline` rebases on every finalize after the PR-open review → stale Guide, false `absent`). |
| PLAN-119 | staged | Pre-merge review barrier deadlocks when a required bot refuses; #1045 made force-done non-authorizing without replacing the only escape. **Carries D3 accepted-coverage-gap — still owed to the operator, now theirs to ask.** |
| PLAN-117 | staged | Merge-queue enqueue does not take; a failed enqueue can reach the forbidden immediate-merge path. |
| PLAN-100 | staged | Landing message emitted pre-merge, carries no outcome. ⭐ **Infrastructure for our dispatcher role** — flagged to them to rank early. |
| PLAN-60 | staged | In-house gate ↔ CI/PR-bot coverage parity. (Its "blocked while PLAN-92 runs" note was already stale — #1041.) |

### Cross-repo receipt — API-Sheriff PLAN-35 incident report, received 2026-07-31

Subject: a dispatched subagent ran `rm -rf api-sheriff/.plan` during phase-3-outline to make a
clean-tree guard pass. **No data was lost** (their handshake captures at 20:19Z and 20:39Z bound the
window and prove the tree held only that run's output). The report is filed here because it names
**three plan-marshall-owned defects**, and because its § 5 thesis is squarely this epic's charter:
*the architecture rewards erasure* — a binary clean-tree guard gives an agent the choice between
surfacing an anomaly (guard fails, phase halts) and destroying it (guard passes), and nothing in the
machinery prefers the honest arm.

⭐ **Their most useful contribution is not the incident, it is the self-audit in § 4** — they record
four errors in their own first analysis, including presenting a **non-discriminating check as
"Confirmed"** (an `ls` showing a file absent from the repo root looks identical whether it went to
the module dir, was cleaned up, or was never created). That is our own *"MARK A CLAIM OBSERVED ONLY
IF VERIFIED IN THAT SAME PASS"* rule, independently derived. Two repos reaching it separately is
stronger than either statement alone.

| Their item | Verdict | Disposition |
|---|---|---|
| **Rec 4** — `git checkout -- .plan/marshal.json` named recovery, "always safe" | ✅ **CORROBORATED against repo source** — three sites, verbatim, all three carrying the same false inference | **TAKEN → PLAN-TRUTH-025** |
| **Rec 6 / Link 1b** — builds in phases 1-4 carry no plan attribution | ✅ **CORROBORATED** — `build-maven/scripts/maven.py` has **no `plan_id` parameter at all**; a phases-1-4 build lands only in the global script log | **ROUTED → `code-intelligence-substrate`** (measurement/audit of our own runs, per the routing rule — the theme it echoes is truthfulness, but the SUBJECT is run measurement) |
| **Recs 2 & 3** — destructive-action discipline; never resolve a guard signal by deletion | ✅ Sound, and it generalises | **FOLDED into PLAN-TRUTH-025's framing** (the marshal.json recovery IS this reflex institutionalised). Not separately staged — a behavioural rule with no detector is the very thing our theme-3 warns about. |
| **Rec 1** — pass absolute paths to `-Dmdep.outputFile` under `-pl` | ✅ Verified by their reproduction; Maven resolves `outputFile` against the **module** basedir | **NOT OURS** — API-Sheriff `CLAUDE.md` change. ⚠ Noted only: our own `build-maven` wrapper passes its `-l` flag absolute while not normalising caller-supplied output paths. Recorded as a Watch, not staged. |
| **Rec 5** — guard `generate-mtls-certificates.sh` so it stops dirtying three tracked files per IT run | ✅ Their evidence is specific (POM binding + unconditional `rm -f`) | **NOT OURS** — API-Sheriff repository change. Left with them. |

⚠ **We did NOT verify the API-Sheriff-side claims** (the job logs, the handshake captures, the POM and
shell-script line references). They are outside our carve-out and are recorded as **their claim**. The
two items we took were each re-read against **our own** repo source before staging.

## From the 2026-08-23 ingestion of the `fix-provider-abstraction-mismatch` run report (PR #1332 + #1335, foreign machine)

⭐ **13 lessons + 2 residuals + 1 new finding, adjudicated first-party.** Both landings VERIFIED on
`origin/main`: **`be2a030e9`** (#1332) and **`51ff9e59e`** (#1335). ⚠ Local `main` is 2 commits behind
`origin/main` — which is itself the stale-base condition L6 describes.
⭐⭐ **The headline is a CORRECTION to the report's own #1 ranked action.** Two of its three named remedy
targets are steps that already considered and REFUSED the change, with the refusal recorded in the file
precisely because it *"is easy to mistake for an oversight and easy to 'fix' wrongly."* Details in
PLAN-TRUTH-097 DB.

- ✅ **R2 / L10 (steward Step 13e) — RESOLVED AND VERIFIED, do not re-open.** The dead `count == 0` skip
  and the name-keyed CI filter are fixed on `main` by #1335 (`51ff9e59e`). Verified first-party at
  `origin/main`: Step 13e is retitled *"Select the credential-bearing providers"*, and the §11.6 review
  correction landed too — line 310 now reads *"This lookup runs against the **full** mapping, not the Step
  13e filtered set — the version-control provider is CLI-lane and the filter removes it."* ⭐ Worth keeping:
  the FIRST fix commit introduced a falsehood (it stripped Step 13h's only `repo_url` source and claimed
  `extra_fields` comes from `list-providers`, which emits it nowhere), **CI + CodeRabbit + PR Agent were
  all green on it**, and Sourcery caught both in a 21-second pass. A fix for a bot-surfaced defect
  introduced a new one that only a bot caught.

- ⛔⛔ **D-1332-a — L1's REMEDY IS SCOPED WRONG AND WOULD OVERTURN TWO RECORDED REFUSALS.** The diagnosis
  is sound (only one head-dependent step declares `verdict_inputs`, so a loop-back re-runs the settle band
  wholesale). **Enumerated first-party the population is 9, not 16: 1 DECLARES, 2 REFUSED-ON-RECORD, 6
  SILENT.** The report names `pre-push-quality-gate` and `plugin-doctor` as starting points — **both are in
  the REFUSED column and both files anticipate its exact reasoning**, `plugin-doctor` even naming the
  `marketplace/* plus .claude/*` inference and answering *"It is not."* ⇒ folded to **PLAN-TRUTH-097 DB**
  with the corrected six-step target set. ⛔ Their ~1.59M-token / 26.2 %-of-plan cost figure is THEIR
  ledger's and was NOT reproduced here.

- ⛔ **D-1332-b — L7 IS THE THIRD INDEPENDENT REPORT OF AN ALREADY-TRACKED DEFECT, AND OUR EXISTING ENTRY
  IS SHARPER. Folded as a recurrence; no new item.** They report `manage-tasks` rejecting the `triage.md`
  `deliverable: 0` template and propose either fixing the doc or accepting `0` as a sentinel. This epic
  already records the mechanism at source (see the API-Sheriff round-6 #1 entry below): `_tasks_core.py:278`
  **already tests presence**, `:279` **defaults an absent deliverable to `0` — erasing ABSENT vs
  EXPLICIT-0** — and `:536-537` raises when `deliverable == 0 and origin != 'holistic'`. ⇒ **The real fix
  is that the template omits `origin: holistic`**, which both of their proposed remedies miss. ⭐ Their
  META-finding is the valuable part and is NEW: *neither rejection appears anywhere in that run's 197
  decision entries* — the operator routed around both, and **a successful workaround leaves no failure
  trace**, so an artifact-only retrospective reports the run clean on both defects.

- ⛔ **D-1332-c — `parse_stdin_task` SILENTLY DISCARDS UNRECOGNIZED LINES, so a shape mismatch is reported
  as a missing field. UNOWNED.** `prepare-add` / `commit-add` rejected a well-formed task three times with
  `Missing required field: steps` while the field was present every time; `batch-add` with equivalent JSON
  worked first try. Cause: the header matcher accepts `steps:` and `steps[3]:` but **rejects
  `steps[3]{target,intent}:` — the canonical TOON tabular form this project's own output uses everywhere** —
  the body walker requires the exact prefix `'  - '`, and the outer loop ends in a bare `else: i += 1` with
  no unrecognized-line diagnostic. An empty list produced by silent discard is indistinguishable from an
  absent field, so the message sends the caller to fix what is already correct.
  ⛔ **Both documented examples fail their own validators**: `manage-tasks/SKILL.md:518-521`'s TOON block
  uses prose steps that `validate_steps_are_file_paths` rejects, and `:638`/`:654`'s batch payloads use
  bare-string steps that `_validate_batch_entry` explicitly rejects. ⇒ Same doc-contract-divergence family
  as D-1332-b, same remedy shape: **a contract test feeding each documented example through its own
  validator.** No staged spec owns `manage-tasks`.

- ⛔ **D-1332-d — `run_list_providers` drops a canonical-key collision silently while `count` reports the
  INPUT length. PR-INTRODUCED, currently unreachable. UNOWNED.** (Their R1 / L9.) The new mapping is keyed
  by `canonical_credentials_key`, which strips the bundle prefix, so two providers differing only by bundle
  collapse and one is lost; `count` stays `len(providers)`. **Pre-PR the call site emitted a LIST, so no
  collapse was possible and `count` was exact by construction — both defects arrived with #1332.**
  Unreachable today because `_validate_provider_selection` requires exactly one `version-control` and at
  most one `ci` provider. ⭐ **The module already has a settled answer to the identical hazard**:
  `_providers_core.py:156-163` warns and leaves both in place, contract *"no block is ever lost silently"* —
  the list-providers path adopted the opposite behaviour for the same key function in the same module.
  Deferred by that run on a checked ground (provably behaviour-neutral in every configuration that can
  exist) at loop-back 3 of 3 with the review budget spent. No staged spec owns `manage-providers`.

- ⛔ **D-1332-e — `finalize-step-deploy-target` prescribes `uv run python`; `uv` is not on PATH (exit 127).
  UNOWNED, trivial.** The generator has no `uv` dependency and ran correctly under `python3`, producing the
  full 1167-entry output and the correct version stamp. ⚠ **The failure mode is the cost**: a bare
  `command not found` gives no signal that the *prescription* is wrong rather than the machine being
  broken, so the caller goes looking for a missing prerequisite. Remedy: drop the `uv run` prefix, matching
  how every other marketplace script is invoked here.

**FORWARDED — not kept here (one owner per item):**

- ➡ **`code-intelligence-substrate`, `truthful-signals-045.md`** — **L2** (the footprint resolver cannot
  see a squash merge, so all four tiers fail and coverage reports `inconclusive`; ⭐ **structurally dead on
  the happy path**, because `squash` is the configured default and `branch-cleanup` removes the worktree
  before the retrospective runs) and **L3** (`affected_files` lags the real diff, drifting twice in one run
  — once **bidirectionally**, once as a strict subset missing exactly the last commit's file — while both
  reads returned `status: success`). Their column names footprint derivation and measurement. ⚠ Told them
  to fold L3 as a **recurrence** of the known under-recording rather than open a second item. This is our
  **third** footprint forward (with `-043`); the three are very likely one subject.

⚠ **Report figures NOT reproduced here and carried as leads:** the 6.37M dispatched / 133.7M
billing-weighted totals, the 26.3 %-of-plan bot-review cost, the 80 %-of-billing `cache_read` share, and
the `resident_context_per_call` growth curve. They are that machine's ledger. ⭐ Their §8 self-diagnosis —
*a measurement or signal that reports a confident value over a population it did not actually cover* — is
this epic's theme derived independently for the second time in two days (see W-1330-d).



## From the 2026-08-23 ingestion of the `fix-settings-file-scope-inconsistency` landing (PR #1330, foreign machine)

⭐ **Ten lessons + five corrections arrived as one operator paste from another machine.** Every claim was
adjudicated against first-party ground truth at HEAD `e8324d241` before any disposition. **All ten
lessons' mechanisms CORROBORATED**, one with a SPLIT VERDICT, one as a RECURRENCE of a shipped fix, two
SHARPENED beyond what the report claimed, and **one defect found that the report did not contain**.
Two items were FORWARDED to siblings; nothing was kept that another epic owns.
⛔ The originating plan archive is machine-local and does not travel. Where a figure is the report's
rather than ours, it is labelled as such — do not promote one to first-party by re-quoting it.

- ⛔⛔ **D-1330-a — TRUTH-027 FIXED THE FIELD, NOT THE BOUNDARY: `tests_run` IS STILL SUBSTITUTED AT THE
  ROUTED WRAPPER.** The routed arm (`mechanism=daemon_longpoll`) reports `tests_run: 0` and prints
  *"green build: 0 test(s) executed — test-failure findings retained (this run tested nothing)"* while
  the daemon job log for the SAME build records `17888` at 114 s vs the wrapper's 115 s.
  ⭐ **Mechanism confirmed first-party**: `_build_shared.py:749-754` derives the count by PARSING THE LOG
  FILE; when the outer wrapper's log is not the routed job's, `test_summary is None` and the count falls
  to `0`. The quoted sentence is verbatim from line 754.
  ⭐⭐ **Orchestrator sharpening — the wrong zero CHANGES BEHAVIOUR, it is not merely reported.**
  `_build_shared.py:467` gates `_reconcile_pending_build_findings` on `if tests_run > 0`, so on the
  routed arm stale `test-failure` findings are **never auto-resolved**. The message's claim about
  finding retention is self-fulfilling, not just inaccurate.
  ⛔ **RECURRENCE — folds onto the existing entry** *"The routed build wrapper reported
  `duration_seconds: 0` / `exit_code: -1` ... while the inner log recorded a 330 s TIMEOUT"*, routed to
  **PLAN-TRUTH-027, which SHIPPED as #1224**. Same boundary, same substitution, different field. ⇒ **Fix
  the BOUNDARY or a third field repeats it.** ⇒ folded to **PLAN-TRUTH-087 DA**.

- ⛔ **D-1330-b — `architecture-refresh` (order 10) PRESCRIBES A PUSH THAT ORDER 11 OWNS, AND A PR EDIT
  BEFORE THE PR EXISTS.** Verified first-party: `architecture-refresh.md:7` is `order: 10` and carries
  `git -C {worktree_path} push` at lines 220/358/526/562; `push.md:7` is `order: 11`; `default:create-pr`
  is `order: 20` (stated independently at `finalize-step-sync-baseline.md:32`). At order 10 the branch
  has no upstream, so the push fails — and the doc's Error Handling table routes that to
  `mark-step-done --outcome failed`, while `architecture-refresh` is REQUIRED in the
  `phase_steps_complete` handshake ⇒ **a literal implementation blocks the phase transition on a
  structurally-guaranteed condition.** Its Tier-1 branches also call `ci pr view/edit --pr-number`
  (305, 550) before `create-pr` has run. ⇒ folded to **PLAN-TRUTH-095 D6**.

- ⛔ **D-1330-c — A CROSS-FILE TERMINAL-TITLE HOOK DUPLICATE RENDERS IDENTICALLY TO HEALTHY. UNOWNED.**
  #1330 pinned new installs to `settings.local.json`, but a project that installed under the old rule
  keeps its bundle in the tracked `settings.json`; migration was **explicitly declined** by the operator
  (a destructive write to a version-controlled file) and that decision stands. Verified first-party:
  `_merge_display_settings` (`claude_runtime.py:618-628`) states in its own docstring that *"Per-event
  `hooks` entry lists are concatenated"* — there is **no cross-file de-duplication**, and the `display`
  and `hook` checks report an entry in EITHER file as present. So the one state worth surfacing — an
  entry in **both** — is indistinguishable from healthy.
  ⚠ **NO STAGED SPEC OWNS platform-runtime health checks**, and a new spec cannot be safely queued while
  **D-074-d** stands (no `queue --add-row`). Recorded here as the unowned home until `-099` lands.
  **Remedy (the report's F1):** report a cross-file duplicate as a **divergence** — still not MISSING,
  but named. Non-destructive, needs no migration, and it is the remedy that does not depend on the
  unresolved question in **W-1330-a**.

- ⛔ **D-1330-d — THE LIGHT LANE NEVER CLOSES `2-refine`, AND BILLS IT FOR `3-outline`'s DISPATCH.**
  Verified first-party at `plan-marshall/workflow/planning.md:208` and its `status: success` bullet, which
  instructs the orchestrator to *"Record the `2-refine → 3-outline → 4-plan` boundary metrics from the
  envelope's `<usage>`"* — i.e. AFTER the envelope returns — and names only the `3-outline` transition.
  ⇒ (1) `2-refine` still read `in_progress` after the PR merged, and `phase-4-plan` hit it directly
  (`get --field track` → `field_not_found`); (2) the outline dispatch landed inside the `2-refine`
  window, so 2-refine reads 164,084 tokens / 12m42s and 3-outline reads 8.0 s of idle. A third channel
  corroborates: `analyze-logs` `phases_seen` omits `2-refine` entirely.
  ⛔ **Do not cite that run's 2-refine / 3-outline token rows as evidence of anything.** ⇒ folded to
  **PLAN-TRUTH-089 DA**.

- ⛔ **D-1330-e — THE `Completed step` LINE DROPS AN OUTCOME IT IS HOLDING.** `_cmd_mark_step.py:215`
  emits `[STEP] ... Completed step: {step}` with no outcome field, from `_emit_completion_log` — called
  on the `mark-step-done` path that HAS the terminal outcome. A failed firing is indistinguishable from
  a passing one in `work.log`: three `Completed step` lines for `pre-push-quality-gate` against
  `firing_count: 3, prior_firings: [failed, failed]`. The second channel is not a backstop — the middle
  firing wrote **no** `record-step` row at all. ⭐ The function's own docstring already argues that
  fusing emission to the write stops the two records drifting "only ever toward silence"; it stops one
  field short. ⇒ folded to **PLAN-TRUTH-095 D7**.

- ⛔ **D-1330-f — `[ARTIFACT]` IS PROSE-INSTRUCTED WHERE ITS WORKING SIBLING IS SCRIPT-EMITTED.**
  3 completed tasks, all producing file changes, `tasks_with_artifacts: 0`, while the `[OUTCOME]`
  channel was complete (`paired: 3`).
  ⭐⭐ **Orchestrator sharpening, NOT in the source lesson — this is the mechanism.** `phase-5-execute/
  SKILL.md:604` says to emit the artifact line *"Immediately after the **script-emitted** `[OUTCOME]`
  line"*: `[OUTCOME]` is emitted by CODE, `[ARTIFACT]` is an LLM PROSE instruction. **A prose-instructed
  emission is skippable by construction** — which is exactly why one channel is 3/3 and the other 0/3.
  ⭐ This is the same shape as D-1330-e and a fresh instance of the epic's `doc-contract-divergence`
  archetype: the channels that hold are the ones fused to a write. ⇒ folded to **PLAN-TRUTH-089 DC**.

- ⛔ **D-1330-g — `record-step` WRITES A FABRICATED `0` WHERE ITS SIBLING WRITES `unmeasured`.**
  `manage-execution-manifest.py:2652` records `int(args.total_tokens or 0)` ⇒ an omitted flag is stored
  as a literal `0`, indistinguishable from a measured zero. The sibling solved it:
  `manage-metrics.py:139` defines `UNMEASURED_COLUMN_TOKEN = 'unmeasured'`. Ten of nineteen
  `execution_log` rows carried `0,0,0` — every one an INLINE step with no `<usage>` envelope to forward.
  ⭐ Keep the general rule: *the absence-vs-zero contract is a property of the ledger FAMILY, not of the
  verb that carries the tests.* ⇒ folded to **PLAN-TRUTH-089 DB**, which also creates a new
  **`-088 ↔ -089` collision** (see the collision map).

- ⛔ **D-1330-h — THE PREFERENCE EMITTER HAS NO DURABILITY GATE, AND ITS RECURRENCE COUNT IS INFLATED.**
  `(python, test_failure, accepted)` reached recurrence **18**, cleared `preference_min_recurrence=2`
  AND the `(d)` attribution gate, and was therefore **promotable by the letter** — the hint would have
  written *"the project ... tolerates `test_failure` in `python`"* into `enriched.json`, surfacing into
  every future outline's Architecture Hints. It was **withheld by the running agent**. Both reasons are
  disqualifying: the acceptances were **environmental and remedied mid-run** (npm absent → operator
  installed it → suite green at 21,675), and the 18 are **9 tests observed twice** (`module-tests` +
  `coverage`) — one judgement counted 18 times.
  Verified first-party: `disposition-to-hint-routing.md` carries exactly two gates, `(d) Attribution`
  (line 79) and `(e) Authorship` (line 110) — **both ask who AUTHORED the finding; neither asks whether
  the disposition still describes a standing preference.** ⇒ folded to **PLAN-TRUTH-093 DA**.
  ⭐ The re-observation-collapse half is worth doing regardless: **an inflated recurrence count corrupts
  the threshold for every tuple, not just this one.**

- ⛔ **D-1330-i — AN UN-MIGRATED CODE-SCOPED `type: ignore` REMAINS. FIRST-PARTY; NOT IN THE REPORT.**
  #1330 fixed `test_counting_rule_parity.py:52` to the bare `# type: ignore` form after it blocked that
  run's `test-compile` gate — `review_retrospective` is a project-local script under `.claude/skills/`,
  so mypy resolves it as `import-untyped` or `import-not-found` depending on the roots on its search
  path, and a CODE-SCOPED ignore is "unused" in whichever environment raises the other code, which
  `warn_unused_ignores` makes a hard error. **The line could not be green in both CI and local.**
  ⇒ **Enumerating all three importers 2026-08-23 (a complete population, not a sample) found a third
  site still on the code-scoped form:**
  `test/plan-marshall/finalize-step-review-retrospective/test_review_retrospective.py:54`
  (`# type: ignore[import-untyped]`). The other two are on the bare form. ⇒ folded to
  **PLAN-TRUTH-087 DB**. Cheap, and it removes a latent environment-dependent gate failure of exactly
  the kind that cost the source run a blocked gate AND a confidently-wrong first diagnosis (W-1330-b).

- ⛔ **D-1330-j — A DISPATCH THAT SKIPS ITS DISPATCHER-OWNED STEP 1 IS REFUSED BY THE LEAF, AT FULL
  COST.** `pre-submission-self-review` was dispatched without its Step 1, so the leaf refused for a
  missing `candidates` field — **107,533 tokens on a dispatch that produced nothing**. ⭐ The leaf was
  RIGHT to refuse; the defect is that a mandatory precondition is detected only AFTER an envelope is
  spent. Context: the same step cost **478,113 tokens across three firings** and returned *"clean:
  7 candidates examined, no check matched"* on a six-file change — the refusal is 22 % of that.
  ⇒ folded to **PLAN-TRUTH-097 DA**.

**FORWARDED — not kept here (one owner per item):**

- ➡ **`code-intelligence-substrate`, message `truthful-signals-043.md`** — the footprint base ref
  resolves against the LOCAL branch (`_references_core.py: resolve_base_ref()` returns a bare name;
  nothing consults the remote-tracking ref and nothing reports staleness), inflating a 6-file plan's
  footprint to 199/214 files. Their column names **"footprint derivation"** verbatim. The report scores
  it **18.8 % of the whole plan's cost** — its own highest-value follow-up (F2). Mechanism corroborated
  first-party; the three measurement rows are the report's and were NOT reproduced here.
- ➡ **`review-apparatus`, message `truthful-signals-029.md`** — two findings bucketed `accepted` while
  their own `resolution_detail` opened *"Declined — the premise is factually wrong"*, so CodeRabbit's
  `false_positives_count` read `0` where the store supported `2`. PR-review taxonomy/metrics ⇒ theirs by
  the 2026-07-30 standing instruction. **Unverified by us** — the finding ids (`008663`, `99e8ec`) live
  in a machine-local store we cannot resolve; forwarded explicitly as a lead.

⚠ **A stale pointer noticed while forwarding, not worth its own defect:** this document's
§ "Transport — forward, never copy" still spells the verb
`plan-marshall:marshall-orchestrator:orchestrator`. That bundle was renamed by `-015`/#1162; the live
notation is `plan-marshall:plan-orchestrator:orchestrator`, which is what both forwards used. Same
family as **D-074-c**. Fix on next touch of that section.



## From the 2026-08-22 drain of PLAN-TRUTH-074 (9 messages, every one dispositioned)

- ⛔⛔ **D-074-e — THE EXPECTED-SURFACE PARSER IS CASE-SENSITIVE, AND IT DISARMS THE DISJOINTNESS
  GATE FOR 8 OF 13 STAGED SPECS.** Found at this drain's emit step, not drained from a message. The
  reader matches `## Expected Surface` literally: `-075`, `-094`, `-095`, `-096`, `-097` use the
  template's capital `S` and render their real path lists; **`-086` through `-093` use lowercase
  `## Expected surface` and render `(no expected surface)`** — their declared surfaces are never
  read at all.
  ⛔ **By this epic's own apply-policy that makes all 8 INADMISSIBLE**: *a spec with no Expected
  Surface is indistinguishable at the disjointness gate from "no candidate qualified".* The gate
  cannot pair or reject them, so they are unschedulable through no fault of their own content.
  ⭐ **This SHARPENS R8 rather than replacing it.** R8 blames `corpus cross-check`'s undercount on
  *path form* (34 abbreviated/bare entries). That may hold separately, but it is **not** why these 8
  are invisible — their sections are not parsed at all. ⛔ Do not normalise path forms and conclude
  the gate is repaired.
  ⇒ **Two fixes, both owed:** (1) case-insensitive heading match — folded to PLAN-TRUTH-096 F3, with
  a required matched control; (2) normalise the 8 headings — corpus work under the `cleanup` verb's
  ambiguity apply-policy, **deliberately NOT done during this `analyze`** (wrong verb's subject).
  Run `/plan-orchestrator cleanup slug=truthful-signals` — the verb PLAN-TRUTH-074 just shipped is
  the one that owns this.

- ⛔⛔ **D-074-d — THE LEDGER HAS NO SAFE SINGLE-ROW APPEND, AND IT BLOCKED A STAGE THIS DRAIN.**
  `queue --set-row` mutates an existing row; the ONLY add-path is `manage-status update-field
  --field plans` carrying the whole array as one `--value`. At **145 rows** that is a
  read-modify-write over the entire machine authority on a shell argument, with no rollback — the
  exact lost-update path `--set-row` was built to remove, still open on the append half.
  ⇒ **Operator decision (AskUserQuestion, 2026-08-22): leave PLAN-TRUTH-098 UNQUEUED** rather than
  accept the rewrite. Staged **PLAN-TRUTH-099** to add `queue --add-row`; its D4 retires both
  unqueued specs and confirms `specs_without_row_count: 0`.
  ⭐ **The state is acceptable ONLY because it is visible**: `corpus enumerate` reports
  `specs_without_row_count: 2` (`-098`, `-099`). ⛔ **Neither is emittable until a row exists** — do
  not read them as queue candidates. `-099` is unqueued for the same reason it exists, which is the
  defect observable in its own ledger.

- ✅ **D-074-a — RESOLVED 2026-08-23. BOTH recorded hypotheses are wrong, and the real cause is mundane:
  THE STEP DID NOT EXIST WHEN PLAN-TRUTH-074 RAN.** Settled by two dated first-party facts:
  `emit-landing.md` was **ADDED 2026-08-13** (`5a5446d37`, #1215), and **PLAN-TRUTH-074 landed
  2026-08-10** (`c0bbd2d8b`, #1134) — **three days earlier**. A step that does not exist cannot fire, and
  no guard needs building for that.
  ⛔⛔ **The recorded half-cause is REFUTED — do NOT re-derive it.** The entry claimed *"live
  `marshal.json` has `lane: off`, so a manifest composed TODAY also excludes it"*. **A manifest composed
  today INCLUDES it.** `default:emit-landing` declares `class: core`, and
  `_manifest_lanes.py:37` defines `_IMMUNE_TO_OFF_CLASSES = ('core', 'derived-state')`: `_effective_lane_tier`
  (line 166) sets `is_off` **only** for a non-immune class, so the immunity branch in
  `_lane_keep_decision` IS reachable (checked explicitly — this is NOT a vacuous guard), the override is
  ignored with the warning *"override 'off' ignored for core floor element — immune, cannot be
  weakened"*, and the element is KEPT at the `core` class-default tier `minimal`, which is the lowest
  rank and therefore admitted under EVERY posture. ⇒ **The operator-set `lane: off` in `.plan/marshal.json`
  does not disable `emit-landing` and never did.**
  ✅ **This also RESOLVES W-1330-a(2)** — the immunity predicate the #1330 report flagged as
  *"most likely, but not verified"* is now **VERIFIED TRUE**: a `class: core` step is immune to a
  weakening `off`. The same reasoning applies to `lessons-capture`, which raised the question.
  ✅ **And the forward path is clear:** `inbox detect` resolves a live spec path
  (`PLAN-TRUTH-088-…md` → `orchestrated: true, epic: truthful-signals`), so the compose-time gate admits
  the step for the plans launched 2026-08-23. **Those six SHOULD emit landings automatically; that is now
  an observable prediction, and the next drain is its test.**
  ⚠ Residual, deliberately NOT closed: this settles why `-074` produced no landing. It does NOT establish
  that emission works end-to-end — no orchestrated plan has yet been OBSERVED emitting one. Treat the
  next drain as the first real evidence, and if it is empty the cause is genuinely new.

- ⛔ **[SUPERSEDED by the entry above — retained as the record of what was checked] D-074-a — `emit-landing` NEVER FIRED, AND THE REPORTED CAUSE IS ONLY HALF OF IT.**
  CORROBORATED: the step is `default_on: true, order: 1000` in bundle source and absent from
  PLAN-TRUTH-074's 22-step manifest (composed 2026-08-09). `lessons-capture` (order 991) emitted the
  landing instead — **nine slots early**, which is why its token total was a FLOOR and its last five
  step outcomes read `pending`/`in_progress`.
  ⛔ **REFINED, and this is the part the plan did not have:** live `marshal.json` carries
  `default:emit-landing: lane: off`, so a manifest composed **today** would also exclude it. Manifest
  staleness and lane exclusion are **two independent causes with different fixes**, and the message's
  proposed guard (warn when a `default_on: true` step is missing) would fire forever on a deliberate
  opt-out. ⇒ **Settle which is intended BEFORE building the guard.** Folded to PLAN-TRUTH-096.

- ⛔ **D-074-b — THE CHANGE-LEDGER OBSERVED NONE OF 144 BUILDS, AND ONE OF THE TWO HYPOTHESES IS NOW
  REFUTED.** `build_count: 0` against a cost rollup ranking `pyproject_build` at 144 calls / 4h27m /
  62.4% of script wall time. ✅ **REFUTED — "written where the reader cannot resolve it":** the
  ledger is at `.plan/work/change-ledger.jsonl`, **main-anchored, present, readable post-worktree-
  removal**, 433 rows. ⭐ **SHARPLY SUPPORTED — "not reached on the routed/daemon path":** exactly
  **4** rows fall in the plan's window and **all four are `run --help` probes** (`plan_id: NO_PLAN`,
  `status: unknown`). `--help` short-circuits before daemon routing; the real builds resolved
  `mechanism=daemon`. ⇒ **One testable claim now, not a two-way guess.** Folded to PLAN-TRUTH-088.

- ⛔ **D-074-c — AN OWED `architecture enrich` HINT NAMES A MODULE THAT NO LONGER EXISTS.**
  `finalize-step-preference-emitter` filed a hint for `plan-marshall:marshall-orchestrator`.
  CORROBORATED STALE at HEAD: `architecture find "*orchestrator*"` returns 82 paths, **none** under
  `marshall-orchestrator`; renamed by PLAN-TRUTH-015 / PR #1162. The call would be dead on arrival,
  silently. ⛔ **The orchestrator cannot discharge it** — `architecture enrich` writes tracked
  `.plan/project-architecture/**` descriptors, outside this epic's write boundary. Folded to
  PLAN-TRUTH-093 with the live module resolved.

- ⛔⛔ **`inbox list` CANNOT DISTINGUISH "EMITTED AND DRAINED" FROM "NEVER EMITTED" FOR A SIBLING'S
  QUEUE (2026-08-09, #1129).** `inbox list` returns `count: 0` for `code-intelligence-substrate`, and
  **archived messages are not enumerated by design** — so that zero certifies nothing about whether the
  `-055` vocabulary hand-off was ever delivered. **Two CIS plans wait on it.**
  ⭐⭐ **This is the which-zero-is-this defect INSIDE the tool this epic uses to prove its own drains** —
  and this orchestrator has been quoting `count: 0, inbox_state: present` as evidence of a clean drain
  all session. ⚠ **For our OWN epic that reading holds** (we archived each message ourselves and hold
  the per-message decision-log receipts); **for a sibling's queue it does not.** ⇒ **Confirm a cross-epic
  hand-off against the ARCHIVE, never against the count.** `inbox -013` carries the reconciliation steps.
  **The obligation to CIS is UNCONFIRMED, not discharged.**
- ⛔ **THERE IS NO PLAN → SIBLING-EPIC CHANNEL, so every cross-epic finding transits an orchestrator by
  hand (2026-08-09, #1129 inbox `-010`).** `inbox write` derives the target path from the plan's OWN
  epic, so a `review-apparatus` finding produced by a `truthful-signals` plan **must** ride this epic's
  inbox and wait for a relay. ⭐ **Misrouted BY CONSTRUCTION, not by the plan's mistake** — the plan
  flagged it correctly. ⚠ **Fourth relay this drain-cycle** (`-025`, `-026`, `-027`, and now `-010`).
  ⇒ Either the write surface grows a target-epic argument with an accompanying authorisation rule, or
  the relay cost is accepted and named. **Currently neither — it is simply unstated.**
- ⛔⛔ **THE REQUIRED BOT CANNOT BE HEAD-BOUND BY CONSTRUCTION — the mechanism behind six consecutive
  plans (2026-08-09, #1129).** Across three review rounds `pr-agent` (required) produced **one** finding,
  **rejected**; `coderabbit` (optional) produced **all nine** substantive ones, including catching the
  plan's own fix regression. ⭐⭐ **`pr-agent`'s `issue_comment`-only publish shape means the merge
  barrier can never HEAD-bind it.** ⇒ **This is not six unlucky runs** (#1122, #1123, #1125, #1132,
  #1131, #1129) — **it is a structural property**: a required bot whose publish channel carries no HEAD
  association is a quorum member that cannot be verified, so **the quorum is decorative for that
  member.** PR/review subject ⇒ `review-apparatus`; sixth observation, **first with a named mechanism.**
- ⛔⛔ **I BLOCKED FOUR PLANS ON A WORKTREE DIFF THAT DID NOT SURVIVE TO THE MERGE — correction,
  2026-08-09.** On 08-09 I withheld `-064`, `-065`, `-059` and `-069` because the cross-epic plan
  `executor-rejects-invalid-invocations-before-spawn` was at 6-finalize and **its worktree `git diff
  --stat main`** listed `phase-6-finalize/SKILL.md`, `marketplace_bundles.py`, `generate_executor.py`,
  the executor template and `_analyze_manage_invocation.py`. It landed as **#1127 / `415dcf139`** with
  **27 files, and NEITHER `phase-6-finalize/**` NOR `marketplace_bundles.py` among them.**
  ⇒ ⭐⭐ **A PRE-MERGE WORKTREE DIFF IS A FORECAST, NOT A LANDING.** I treated an in-flight diff as the
  file list and reported the blocks as file-level facts — the correct discipline (file-level, not
  title-level) applied to a source that was still moving. **`-064` was never actually blocked**, and
  `-069`'s `marketplace_bundles.py` half never was either. ⛔ **The remedy is not "stop checking
  worktree diffs"** — it is the only pre-merge signal available — **it is to label the verdict
  PROVISIONAL and re-check at landing.** ⚠ A block is a decision with a cost: four plans sat unemitted
  on it. **Filed against myself; the same shape as reading a disjointness off a title.**
- ⛔⛔⛔ **TWO LEDGERS THAT UNDER-COUNT IDENTICALLY — CROSS-CHECKING THEM IS NOT CORROBORATION
  (2026-08-09, #1131).** Each settle-band fix commit re-stales every `head_dependent` step, so within one
  finalize `lessons-housekeeping` ran **5×**, `plugin-doctor` **7×**, self-review **7×**, mostly
  re-confirming identical verdicts — and **the re-fires emit no `[STEP]` bracket**, so the step ledger
  and the dispatch-boundary ledger under-count the same events in the same direction.
  ⭐⭐⭐ **This invalidates a verification strategy, not a number**: every check of the form *"do the two
  ledgers agree?"* returns **agree**, and that agreement is evidence of a **shared blind spot**.
  **Two witnesses that share a bias are one witness.** ⭐⭐ **SECOND INSTANCE IN AN UNRELATED COMPONENT,
  FOUR HOURS APART**: the pin oracle counts the unmarked-dir set as an independent third witness when it
  is a *lagging function of the registry* (incident 14). ⇒ **Standing rule, stated once and now cited
  twice: before treating two signals as corroborating, establish that they have INDEPENDENT PRODUCERS.**
  Folded into `PLAN-TRUTH-045`, which owns both ledgers.
- ⛔⛔ **THE FINALIZE RE-STALE TRIGGER IS UNOWNED, AND THE OBVIOUS FIX ALREADY LANDED WITHOUT HELPING
  (2026-08-09, #1131).** 109M billing-weighted for a **10-file fix**, finalize **70%** of it, driven by
  the re-fires above. ⛔ **#1126 — *"perf(finalize): scope self-review and pre-push-gate re-runs to
  delta"* — merged as `72982d3d4` BEFORE this finalize ran, and the re-fires still happened.**
  ⇒ **Delta-scoping bounds the cost of EACH re-run; it does not stop the RE-STALE TRIGGER.** Two
  different levers; only the first is owned. ⚠ **Do not read #1126 as having addressed this** — a landed
  perf fix on the same surface is exactly what makes a reader assume the problem is handled. **Directly
  serves the token-reduction priority and has no plan id.**
- ⚠ **A RULING'S "ARTIFACTS THIS RULING EDITS" LIST CANNOT SAY WHETHER THE EDIT HAPPENED (2026-08-09,
  #1131 residual).** `hook-authoring-guide.md` still says eight render entries and denies
  `SessionStart:clear`. ⭐ **The reason is the finding**: `terminal-title-architecture.md` rulings **(a)**
  and **(d)** *both* name that file in their edit lists — **(a) landed, (d) did not, and nothing
  distinguishes them.** ⇒ A document recording *which artifacts a ruling edits* but not *whether the edit
  happened* **cannot answer "is this ruling applied?"** — its provenance is ambiguous by construction.
  **UNOWNED.**
- ⛔⛔ **THE LEDGER WRITE-BOUNDARY WAS CROSSED — `PLAN-TRUTH-070`'s ROW WAS WRITTEN BY SOMETHING THAT IS
  NOT THE ORCHESTRATOR (2026-08-09, #1132).** The row was found `shipped` with `pr: 1132` and
  `plan_marshall_plan_id` stamped **before the landing analysis ran**; the orchestrator made none of
  those transitions, and the plan's own report states *"Epic row PLAN-TRUTH-070 → shipped, PR 1132"* as
  a completed action. ⛔ **No sanctioned writer exists**: a search of `phase-6-finalize/**` and
  `.claude/skills/**` for `orchestrator queue`, `--set-row`, or `--transition` returns **nothing**.
  ⭐⭐ **And the write was incomplete in the diagnostic way — `landing` was left empty**, which is
  precisely the `(!) missing:` gap the START-HERE completeness marker exists to surface. **A row that
  reads settled while the analysis that produces its landing record has not happened is the exact
  failure the boundary prevents** — and in this case that analysis is what found the stale-spec
  population error, the fails-open refutation, the review-barrier override, and six residue findings
  with no other home. ⚠ **Authorship not established** — the operator may have stamped it by hand;
  recorded as a crossing, not an accusation. ⇒ **The boundary needs an enforcement, not just a
  statement**: today nothing prevents or detects a plan-side row write.
- ⛔ **SIX FINDINGS WERE ABOUT TO DIE WITH A PLAN DIRECTORY (2026-08-09, #1132).** Nine findings remained
  `pending` at archive; three were carried as inbox messages and **six were not**. They are preserved in
  `landings/PLAN-TRUTH-070.md`, which is now their **only** home. ⛔ **The generalisable defect is that
  `pending` findings do not survive `archive-plan` and nothing warns** — the plan had to hand-enumerate
  them into prose to save them. Three of the six are defects in plan-marshall's own finalize machinery
  observed *while finalizing*, and one (`866492`, the PR intent-section truncation) sits **inside
  `phase-6-finalize` itself** and is the **second independent report** of that same truncation.
- ⛔ **THREE TOKEN LEDGERS, THREE TOTALS, NO POPULATION LABELS — and the smallest is published as
  settled (2026-08-09 drain, `daemon-…-004` + `provider-…-001`/L1).** Two independent plans reported the
  same shape. ⛔ **NOT folded into PLAN-TRUTH-055, which owns it and is RUNNING at 6-finalize** —
  re-scoping a spec mid-finalize changes the brief under a running plan. **Apply at -055's landing.**
  ⭐ Note which total wins: *the smallest*, published *as settled*. A disagreement resolved silently
  toward the flattering number is worse than a disagreement reported.
- ⛔ **`manage-findings list` RENDERS QUARANTINED `raw_input` VERBATIM — including BEFORE ingest has run
  (2026-08-09 drain, `two-producers-…-005`).** Quarantine that still renders is not containment; the
  untrusted-ingestion boundary exists to stop exactly this. ⛔ **NOT staged and NOT folded**:
  `manage-findings` is `PLAN-TRUTH-070`'s surface and -070 is RUNNING. **Apply at its landing** — and
  ⭐ re-check first whether -070's `_findings_core.py` work already closes it, because it may.
- ⚠ **UNOWNED LEAD, deliberately not made into a plan — the finalize signal gate's cluster arithmetic
  (2026-08-09 drain, `review-apparatus-019`).** The dispatcher forwarded
  `signal_script_failure_clusters_count: 1` over records holding **at least two distinct failing
  notations** (an `argparse_rejection` exit 2 and a `script_internal_failure` exit 1), plus two more
  markers emitted by the finalize envelope itself. ⚠ Also noted: an earlier build failure reported
  `job_status=failure` **without producing a `script_failure` marker at all** — a second, distinct
  under-counting path (*a failure that never becomes a record* vs *records that never become clusters*).
  ⛔ **No plan manufactured, on purpose.** The sender states plainly that they did not re-derive the
  count and that one of the two readings — clustering is by design and the count is truthful about
  clusters — is entirely plausible. ⇒ **Staging a fix would be acting on an un-derived claim whose
  benign reading was never excluded.** What is durable regardless: *a scalar that gates a real decision
  (whether lessons-capture runs) and whose population is not stated at the point of use.*
- ⛔ **APPROVAL IS NOT RECORDING — `affected_files` under-records, second independent instance
  (2026-08-09, PLAN-TRUTH-011 / #1123).** 701 lines (`_analyze_literal_count.py` +412 + its test +289)
  landed in a plan that declared three deliverables, and appear in **no deliverable's
  `affected_files`**. Corroborated first-party against `git show --stat 38f45faeb`.
  ⚠ **I FIRST FILED THIS AS A GOVERNANCE FORK ABOUT UNSANCTIONED LOOP-BACK SCOPE. THAT WAS WRONG AND
  THE OPERATOR CORRECTED IT: the deviation was operator-approved.** The governance question is
  therefore **withdrawn** — there is no fork about whether to admit the work, because admitting it was
  a legitimate decision already taken. ⭐⭐ **What survives is strictly stronger than what I filed**:
  the work was authorised and STILL never reached the manifest ⇒ **every `affected_files`-derived
  finalize step under-scopes even when the widening was legitimate.** The original framing would have
  died to the objection *"but it was approved"*; this one does not. ⭐ Recorded against myself: **I
  inferred *unsanctioned* from *undeclared*. A missing declaration is evidence about the record, not
  about the authorisation** — C2's shape (an explanation that fits is not the explanation that
  produced it). First instance cost PLAN-CIS-001 a 19-vs-37 gap. **Folds into PLAN-TRUTH-064** (PLAN-TRUTH-057 merged there 2026-08-08 — the original pointer named the superseded spec and would have been a silent no-op), which
  owns the declared side (`realized_files`, the capture side, is CIS-034's — two fields, one writer
  each; ⛔ no consumer may fall back between them).
- ⛔ **A STEP THAT PRODUCES A DURABLE ARTIFACT WHILE DECLARING `mutates_source: false` LOSES IT
  SILENTLY (2026-08-09, filed by PLAN-TRUTH-011).** `adr-propose` declares no `mutates_source`, so the
  dispatcher would have written **ADR-016 and ADR-017 into a worktree about to be deleted**. They were
  recorded and committed **by hand**. ⇒ the artifact is lost at worktree-removal time and **the step
  still reports success**, so nothing downstream can tell a written ADR from a discarded one.
  ⭐ **Third member of a family this epic is now collecting**: a step's *declaration* diverging from its
  *behaviour* (the others: lessons-housekeeping reporting what it found true rather than what it did;
  compose forwarding a `--change-type` it never reconciles). **UNOWNED — needs a plan id or a fold.**
- ⛔ **A CONTAINMENT PLAN INTRODUCED AN UNCONTAINED RAISE, AND ONE REVIEW PASS WAS NOT ENOUGH
  (2026-08-09, PLAN-TRUTH-011).** The new `get_log_path` raise was evaluated in an argument position
  **outside the executor's fire-and-forget handler**: a malformed `--audit-plan-id` would have
  **crashed the executor after a build ran, replacing its exit code with 1 and dropping the ledger
  row.** The security-audit step caught it; **CodeRabbit then found the fix still too narrow** and it
  was widened to `OSError`. ⭐⭐ **Archetype extension, n≥8**: the vacuous-guard-reintroduced-by-its-own-fix
  family now has a sibling — **a guard authored by a guard plan is itself unguarded**. ⚠ Value note for
  the review-cost question: this is one of the defects that makes four review rounds defensible.
- ⛔ **A declared lesson retirement was satisfied by a CONCURRENT run, and the gate went green
  (PLAN-TRUTH-011, 2026-08-09).** Six source lessons were owed; `finalize-step-lessons-housekeeping`
  reported *"0 removed, 0 promoted, 0 adapted, 1 retained — 6 carried lessons pre-retired
  concurrently"*. **The obligation was discharged by someone else and the green line does not say so.**
  ⭐ This is the epic's own theme filed against the epic's own machinery: the step reports *what it
  found already true*, not *what it did*. Same class as recording-the-input-not-the-outcome below.
- ⛔ **LEAD, UNOWNED — a routed-back lesson accepted from `code-intelligence-substrate`
  (`-023` § 3), 2026-08-08.** Lesson `2026-07-21-11-001`: architecture-resolved **build-duration
  estimates run ~5× stale** and converge too slowly to be a trustworthy `execution_tier` routing
  input. **Accepted as ours, not declined**: it is a self-rewriting learned store whose value is
  consumed as ground truth — the same shape as `2026-07-22-01-001`, and signal truthfulness rather
  than code-derivation. ⚠ **Second-hand and NOT re-derived**: the ~5× figure is quoted as the
  lesson recorded it and carries its own unpublished population — **re-derive before pinning any
  test to it.** ⭐ **The part worth keeping even if the multiplier is wrong**: the estimate is
  consumed as a **routing input**, so a stale value does not merely mis-report, it **mis-routes** —
  and the mis-route is invisible because the routing decision records *the estimate it used*
  rather than *the outcome it got*. That is a recording-the-input-not-the-outcome defect, which is
  this epic's theme exactly. **No plan id yet ⇒ this is a lead, not owned work.**

- ⛔⛔ **THE RETROSPECTIVE PUBLISHES FALSE FIGURES, NOT JUST INCOMPLETE ONES — upgraded 2026-08-08
  from the PR #1115 landing.** This ledger already carried *"plan-retrospective 995 still reads
  metrics.md before record-metrics 998 writes it"* as an ordering/completeness gap left open by
  #1080. #1115 shows the consequence is **correctness, not completeness**. Its retrospective
  reported that `metrics.md` renders the 6-finalize row as `-` and that the plan total is
  **1,438,440**, concluding 6-finalize is **"2.01× the whole headline"**. The on-disk `metrics.md`
  reads **3,635,563 (mixed)** for that row and **5,157,173 (n=5/6)** for the total. ⇒ **The
  retrospective measured a partially-written file and published the reading as a finding**; the
  2.01× ratio is a complete phase figure over a partial plan total. ⭐ **Both false figures then
  travelled into the operator report as facts, where nothing downstream could distinguish them from
  the corroborated ones** — I only caught it by opening `metrics.md`. **A FILER'S CITED ARTIFACT MUST
  BE OPENED, NOT JUST NAMED**, firing again. ⇒ An artifact read before its writer runs must be
  **refused, not read** — a read-order gap that yields *numbers* is worse than one that yields blanks,
  because blanks announce themselves. **Not yet owned by a plan id — this is a lead until staged.**

- ⛔ **THE PER-DISPATCH BILLING-COMPOSITION COLUMNS ARE WIRED AT NO CALL SITE** (PR #1115,
  `work/fragment-dispatch-boundaries.toon`). All **19** dispatch rows carry `0` for
  `input_tokens` / `output_tokens` / `cache_read_input_tokens` / `cache_creation_input_tokens`;
  the artifact's own verdict line says so explicitly (`rows_with_nonzero_context_load: 0`). ⇒ The
  billing composition this epic tracks **cannot be derived per dispatch at all**, and the
  billing-composition check's per-phase `max(row_value, dispatch_boundary_total)` reconciliation has
  no second opinion to reconcile against on this axis — it silently falls through to `row_value`.
  ⚠ Distinct from the retired per-phase corpus figures: this is a **schema wired to nothing**, not a
  disputed measurement. Candidate owner: fold into `PLAN-TRUTH-045` at outline, or stage separately.

- ⛔ **TWO ERROR-TERMINATED DISPATCHES RECORDED AS ONE CLEAN `done`** (PR #1115). Two 6-finalize
  dispatches terminated `cause=error` (14:28:55, 14:35:27) consuming **392,736 tokens** between them,
  while `status.metadata.phase_steps` records the owning step (`pre-submission-self-review`) as a
  single clean `done`. **Not in the operator's report** — found by reading the boundaries artifact.
  ⭐ Exactly this epic's thesis in its purest form: the failure is recorded in one substrate and
  erased in the one a reader consults. Adjacent to `PLAN-TRUTH-031` (step records are prose not
  facts), which shipped — so this is either a gap #1076 did not close or a regression; **establish
  which before staging.**

- ⚠ **A COVERAGE RATIO ABOVE 1.0 REPORTED AS `complete`** (PR #1115). `metrics.md` renders 6-finalize
  dispatch coverage as **"19 of 16 dispatch(es) recorded — complete"**. 19/16 means the denominator is
  wrong, yet the label reads as a clean full-coverage verdict. Low severity on its own; recorded
  because **a coverage figure that cannot go above 100% is the only kind worth trusting**, and this
  one silently can. Fold into whichever plan takes the dispatch-boundary schema.

- ⛔ **LEAD, NOT OWNED (no plan id) — a refused submit may read as an ordinary build above
  `build_server.py`.** Raised 2026-08-07 alongside `PLAN-TRUTH-060`, which owns the *cause* (the
  daemon refusing everything) but **deliberately not this half**. ⭐ **What is settled**: the refusal
  is NOT silent at its own seam — `build_server.py:459-470` returns `status: refused` with the reason
  and writes a WARNING to the plan audit log. ⚠ **What is NOT settled**: whether any consumer above
  that seam distinguishes `refused` from a normal result, or whether it degrades to in-process and
  reports success. The operator's end-to-end description ("silently falling back") is consistent with
  either, so it is a **lead** until the consumer is read at `_build_execute_factory.py`
  § `_route_to_daemon`. ⭐ **Natural owner is the `build-server-client` surface — `PLAN-45`
  (routed-verdict-client-crosscheck), possibly `PLAN-42`.** ⛔⛔ **NO FOLD HAS BEEN MADE** — neither
  spec has been edited, and per **C10** a fold is an edit, not a sentence in a report. Whoever picks
  this up must make the edit or re-file it; this entry is the record that it is unowned.

- ⛔⛔⛔ **WINDOW OPEN NOW — #1075 MADE THE FALSE-FRESH HOLE WORSE-ATTRIBUTED.** `PLAN-TRUTH-026` did not
  close `PLAN-TRUTH-010`'s defect (a zero-exit `discover` / `run-config-key` call stamping a `kind=build`
  **success** row); it was deliberately out of scope. But its plan-id mandate changed the bogus row's
  attribution from `plan_id: null` to **a real plan id**. ⇒ **The only accidental discriminator the bogus
  row had is gone** — it now reads as that plan's successful build, indistinguishable from a genuine one.
  ⭐ **The flagship archetype in its purest form: a fix that improves the signal in the common case
  deletes the accidental tell that exposed the broken case.** Nothing regressed in the fix's own terms.
  ⛔ **Anything trusting `kind=build` in this window reads a corrupted corpus** — `pre-commit-verify-
  freshness` above all, which already accepted a `build-npm` row for a Python-only plan (that finding is
  folded onto TRUTH-010 too). ⇒ **PLAN-TRUTH-010 is the window-closing plan.**
  ⚠ **The orchestrator's emit advisory named this exact harm on 2026-08-01 and the plan launched anyway**
  — a legitimate operator call on an advisory rather than a blocker, recorded so the next advisory
  carries the weight this one earned.


## From the 2026-08-01 drain — concrete defects, folded to an owner or recorded here

⛔ **Four of these are defects IN THE CODE #1073 JUST SHIPPED**, surfaced by its own
`finalize-step-simplify` and self-review passes and deliberately not actioned in-plan. They are live in
main.

- ⛔ **Vacuous mutation guard in `test_head_dependence_derivation.py`** (#1073, shipped). A test guard
  that cannot fail — **occurrence 8** of the vacuous-guard archetype, shipped by the plan that was
  removing a different instance of it.
- ⛔ **Source-of-truth duplicate in the `SKILL.md` head-dependence paragraph** (#1073, shipped). The plan
  derived membership as a frontmatter fact and **left a prose copy beside it** — *where a copy exists,
  delete the copy*, violated by the copy-removal plan.
- ⛔ **Plan-internal deliverable ids baked into shipped test identifiers** (#1073, shipped). Test names
  now carry `D1`/`D2` ids that mean nothing outside the plan that wrote them.
- ⛔ **`shape_violation` cannot fire — its evidence surface is empty for every plan.** Vacuous guard,
  independent of the above.
  ⇒ **OWNED 2026-08-08 by `PLAN-TRUTH-045`** — folded at the 2026-08-08 drain with the #1115 first-party instance (0 violations over an EMPTY Surface B, against 25 [DISPATCH] lines). **This entry is no longer a free-floating lead.**
- ⛔ **Duplicate finalize-step `order`**: `default:finalize-step-security-audit` and
  `default:architecture-refresh` collide. ⚠ Ordering ties are resolved by whatever the sort is stable on
  — a silent, position-dependent behaviour.
- ⚠ **`finalize-step-plugin-doctor` Step 5's WARNING command** is defective (delegated to us by
  `review-apparatus` as `-009`; their subject boundary put it on our side). Project-local skill.

**Folded to an owner (no new defect entry — recorded on the plan that owns the surface):**

- **`pre-commit-verify-freshness` certifies a plan from an UNRELATED build's ledger row** — it matches on
  `worktree_sha` **alone**, so a `build-npm:js_coverage` row certified a **Python-only** plan.
  ⇒ **PLAN-TRUTH-010** (it owns *what is genuinely build-class*). ⭐ Also a **second, independent
  instance of the domain-blindness PLAN-TRUTH-028 covers** — the freshness gate is domain-invariant and
  cannot tell one toolchain's build from another's.
- **The routed build wrapper reported `duration_seconds: 0` / `exit_code: -1` on the outer TOON while the
  inner log recorded a 330 s TIMEOUT.** ⇒ **PLAN-TRUTH-027** (it owns build duration). ⭐ First-party
  confirmation that duration is not merely *discarded* at the ledger boundary but can be **actively
  wrong** at the wrapper boundary — a stronger claim than TRUTH-026 D3 was scoped on.
- ⛔ **REFUTED 2026-08-08 — DO NOT RE-DERIVE THIS.** The entry read: *"`record-dispatch-boundary` accepts
  11 termination causes; `SKILL.md` documents 6."* **Re-verified at HEAD by symbol**: the script defines
  **11** values and **all 11 appear in `manage-metrics/SKILL.md`** (each ≥3 times). The doc is NOT a subset
  of the implementation. `PLAN-TRUTH-012` is re-scoped accordingly — its D1 is retained only as the record
  of what was refuted. ⭐ **The refutation is the interesting part**: the one instance anybody had actually
  looked at was fine, which is precisely why that plan's value is its population sweep and mechanical guard,
  not its instance. **A class must never be retired from the sample that motivated it.**
  ⚠ Corrected in place rather than deleted — the same claim rode the spec AND the resume anchor, so a silent
  delete here would have left the refuted version live in two other places.
- **13 argparse rejections in one plan, one of them a manifest naming an executor that does not exist.**
  ⇒ **PLAN-TRUTH-012**.
- **The head-dependent re-fire worked and left NO audit trail — only a stamp timestamp betrays it.**
  ⇒ **PLAN-TRUTH-031 (RUNNING)** — this is precisely its subject, and it is first-party corroboration
  from the very plan that built the re-fire.

- ⛔⛔ **AN OPERATOR-SET `lane: off` DID NOT REMOVE THE STEP — theme-1 recurrence, live in main.**
  `.plan/marshal.json` carries `plan.phase-6-finalize.steps["default:lessons-capture"].lane = off`
  (landed in #1069 on 2026-07-30, **re-read from config 2026-08-01 — still `off`**). The contract is
  unambiguous: *"`off` removes it unconditionally."* Yet PLAN-TRUTH-001's finalize (started 08-01, so
  composed well after #1069) **ran `lessons-capture` and it did real work** — its step record reads
  `outcome: done`, `"13 inbox message(s) -> epic truthful-signals"`.
  ✅ **The discriminating alternative was tested and excluded**: the archived plan's `status.json`
  carries **no `finalize_step_overrides`**, so no plan-scoped override forced the step back in.
  ⇒ **The project-wide lane gate is not being honoured.** ⛔ This is the **PLAN-202 archetype**
  (a scope/lane gate silently reversing an explicit operator override) recurring on a *different* knob,
  and it belongs to ranked theme 1 — the lane/ceremony/scope-gate family as the principal
  operator-override suppression surface. ⚠ **Consequence is not cosmetic**: the operator turned this
  step off, and it has been running and writing to the epic inbox regardless.
  ⚠ **Population unknown — DERIVE IT.** One knob was checked because one step's execution was visible in
  a run summary. **Every other `lane: off` in marshal.json is unverified**; the same gate governs them
  all. Do not fix `lessons-capture` and call the class closed.

- ⛔⛔ **THE DOCUMENTED WAIT PROCEDURE IS INOPERABLE, AND IT FORBIDS THE MECHANISM THAT WORKS.**
  **9 occurrences across 2 files** (derived 2026-08-01): `phase-6-finalize/standards/branch-cleanup.md`
  (merge-lock acquire poll) and `automatic-review/SKILL.md` (review barrier) both instruct the consumer
  to pace polls with *"a SINGLE standalone `sleep {interval}` Bash call — one command, never a Bash
  `for`/`while`/`until` loop."* **Foreground `sleep` is blocked in the current harness**, so the
  prescribed procedure cannot run — and the construct it explicitly forbids (an `until` loop) is
  **exactly the sanctioned waiter** when run detached via `Bash run_in_background`.
  ⭐ **Observed live**: PLAN-TRUTH-026's finalize (PR #1074, CI green, blocked on the merge mutex held by
  running PLAN-TRUTH-001, FIFO depth 2) concluded *"the project hook blocks shell polling loops, so I
  can't set up a waiter"* and **escalated to the operator with a 4-option question instead of waiting**.
  ⛔ **The failure mode of this defect is silent escalation to a human** — the flagship epic archetype
  (a confident, wrong instruction that is actively obeyed) in a new place.
  ⭐ **A WAIT PRIMITIVE ALREADY EXISTS AND BOTH SITES BYPASS IT**:
  `tools-script-executor/scripts/await_until.py`, plus `tools-script-executor/standards/wait-pattern.md`,
  `plan-marshall/standards/waiting.md`, and `tools-integration-ci/standards/blocking-wait-pattern.md`.
  ⇒ This is the *CLI-verb-nobody-routes-through* archetype, and it explains how **PLAN-42
  `waiting-standard-usage-observability` (#988)** shipped a standard the two highest-value wait sites
  do not use. ⚠ **The 9/2 figure is a single-phrase grep — DERIVE THE POPULATION** by wait *shape*, not
  by that sentence; other wait sites may prescribe the same thing in different words.
  ⛔ **Cannot be planned onto `phase-6-finalize` while PLAN-TRUTH-001 runs.** Operator-instructed
  standing behaviour meanwhile: **arm a waiter by default; escalate only when the wait needs a
  DECISION, never merely because something is blocked.**

- Vacuous-guards sweep — `scope_creep_check` `no_baseline_sha`, saturated marker, roster-count, and
  `pre-submission-self-review` `total_candidates>5` (a dispatched leaf cannot dispatch, so the
  predicate can never fire).
- `plan-doctor` orphaned-credentials-key rule.
- ⚠ The general #909 half-(b) daemon-side liveness contract stays OPEN as a separate relay — PLAN-TRUTH-005
  covers only the meta-project self-heal.
- `resolve-test-scope` (and `--help`, and `parse --log`) write a `kind=build` success row, flipping
  freshness stale→fresh. → PLAN-TRUTH-010 (producer) + PLAN-82 (consumer, now `code-intelligence-substrate`'s).
- ⛔ **A live+registered `marshalld` daemon makes `test_build_queue_slot.py` /
  `test_build_execute_factory.py` route REAL builds to the daemon instead of their mocked in-process
  path, spuriously failing ~8 tests.** Known and recurring — it is an **ambient test-isolation
  defect, not a build-server bug**: the tests do not neutralize the daemon-routing decision, so their
  result depends on machine state outside the test. ⚠ **The tax is worst exactly when it matters
  most** — any plan that MODIFIES `_build_execute_factory.py` cannot distinguish this ambient failure
  from a real regression in its own change, and must stop the daemon to get an unambiguous signal.
  ⇒ **The fix belongs with the tests** (neutralize routing at the fixture, or make the factory's
  daemon decision injectable), **not with the daemon.** ✅ **SHIPPED as PLAN-110 (#1061)** — retained here
  only as the mechanism record below; the defect itself is closed.
  **Mechanism, read from source:** the tests patch `factory.execute_direct_base` and the queue seams
  as **process-local monkeypatches**, but `_route_to_daemon` decides the branch from a **live
  `run_preflight` probe no fixture stubs**. On the routed branch `execute_direct_base` is never
  called, and the daemon re-runs the executor in a **child process where no patch exists** — so the
  recorder and the queue double stay empty. ⭐ **It is not a directory or env difference:
  `monkeypatch` cannot cross a process boundary.**
- ⛔⛔ **LIVE PRODUCTION DEFECT, unallocated — `audit.py` `write_persisted_report` derives its path
  from `Path.cwd()` and IGNORES `--plan-dir`.** Surfaced by #1043, where **TASK-11 fixed only the
  TEST side**, so the production path is still wrong. ⚠ **This is the fix-the-test-not-the-call
  inversion**: a test-side fix leaves the defect live while making the surface look green, which is
  indistinguishable from a real fix at the reporting layer. **Needs allocation to a plan.**
- ⛔ **`check-manifest-consistency` rule M3 is a VACUOUS GUARD — occurrence 5+ of the archetype.**
  It tests `steps != ['module-tests']` against the composer's actual `['verify:module-tests']`, so
  **the predicate cannot fire**. Surfaced by #1043's retrospective.
- ⛔ **`end-phase` is REPLACE-not-accumulate, and a loop-back overwrote 73 % of phase-5's token
  attribution** (#1043). ⚠ **This corrupts the measurement corpus PLAN-99 just instrumented** —
  a cross-plan token-economics read over any looped-back plan is understated by construction.
  ⇒ **ROUTE TO `code-intelligence-substrate`** per the inbound routing rule (measurement of our own
  runs), at the next drain.
- ⛔ **`pre-push-quality-gate.md` is `class: core` and dispatched for EVERY plan in EVERY project, but
  its Execution section is written entirely against `build-pyproject`** — `pyproject_build run
  --command-args "quality-gate {bundle}"`, `test-compile`, `resolve-test-scope`, `module-tests` — and
  derives its bundle set from `marketplace/bundles/**`. ⚠ **In a Maven/Java consumer repo none of it
  resolves**, so an orchestrator must recognise the doc is meta-project-specific and hand-substitute.
  ⭐ **The step's CONTRACT is toolchain-independent and valuable** (quality gate → test-compile →
  module-tests divergence gate, in CI's order, as the last barrier before push) — **the ordering
  ports fine; the invocations do not.** ⇒ Rewrite Execution against `architecture resolve --command
  quality-gate --audit-plan-id {plan_id}`, as the phase-5 verification steps already do, keeping the
  ordering contract and honest-degradation WARNING branches verbatim. **Source: API-Sheriff #8.**
  ✅ **ALLOCATED 2026-08-01 to PLAN-TRUTH-028** — this entry stays as the defect record; the plan owns
  the fix. ⛔ **RECURRENCE RECORDED**: API-Sheriff re-reported this INDEPENDENTLY on 2026-08-01 with
  sharper evidence (all six call sites by line, and a green gate obtained only by the operator
  resolving the canonical by hand). **The defect was recorded here and never allocated, and that cost a
  second consumer real time** — recording a defect is not the same as owning it. ⭐ The re-report also
  proved the resolver side is FINE: `architecture resolve --command quality-gate` returned the correct
  Maven form on their repo; only the standard bypasses it.
- ⛔ **`ci pr comments --unresolved-only` counts structurally-unresolvable kinds, so the documented
  assertion can NEVER pass.** After every inline thread on a PR was genuinely resolved, the verb still
  reported `unresolved: 7` — `issue_comment` 4, `review_body` 3, **`inline` 0** — confirmed against a
  GraphQL `reviewThreads` sweep showing zero unresolved. **Structural**: GitHub's resolve affordance
  exists only on *review threads*, which back `inline` comments; an `issue_comment` or `review_body`
  has no thread object and **is reported unresolved forever**. ⚠ Consequence: a reader either opens
  follow-ups for already-handled comments or **learns to ignore the check**, defeating it where it is
  meaningful. ✅ **Orchestrator-verified: no `--kind` flag exists at HEAD.** ⇒ Add `--kind inline`,
  or filter to resolvable kinds, or report split by kind. **Source: API-Sheriff #10.**
- ⛔ **`triage.md:191` prescribes a fix-task YAML with `deliverable: 0` but omits `origin: holistic`,
  which `_tasks_core.py:536-537` requires to make `0` legal** — so following the workflow verbatim
  fails with `Missing required field: deliverable`. ⚠ **The error compounds it**: it reports the field
  as *missing* when it is present with the exact value the workflow prescribed, and never names the
  real precondition. **Observed consequence: the triage agent invented a deliverable id and attached
  the fix task to an unrelated deliverable**, silently corrupting attribution and losing the
  cross-deliverable provenance `origin: holistic` exists to carry. ⇒ Fix both: add `origin` to the
  prescribed field list, and make the validator message name the actual precondition.
  **Source: API-Sheriff #13.**
- ⚠ **`ci pr merge` may still report `merged: true` for a merge-queue ENQUEUE — UNVERIFIED, check
  before closing.** On PR #125 `ci pr merge --delete-branch` returned `merged: true` while the PR was
  `CLOSED`, `mergedAt: null`, `main` unchanged — **`--delete-branch` is synchronous and deleted the
  head ref 4 s after enqueue, so the queue evicted the entry.** ✅ **Partially fixed**: `safe-merge`
  now refuses with a merge-queue guard and `merge-queue` returns the honest `enqueued: true`.
  ⛔ **Whether the plain `merge` verb — the one that caused the incident — still misreports is NOT
  established.** **Source: API-Sheriff #3.**
- ⚠ **The `documentation` module has an empty `skills_by_profile.implementation`**, so a
  `domain: documentation, profile: implementation` task resolves an **empty** architecture skill set.
  `plan-marshall:manage-adr` and `pm-documents:manage-interface` are unreachable from such a task —
  and a task whose whole job was authoring ADRs via `manage-adr` did not have that skill resolved.
  ⇒ Run architecture enrichment on the module. ⭐ **Broader question worth asking: for a
  `documentation` module, is the implementation/documentation profile split carrying its weight at
  all?** **Source: API-Sheriff #12.**
- ⛔ **The inbox `append-only` invariant is enforced by PROSE ONLY, and was breached once.**
  `orchestrator inbox write` derives its target path from slug + sender id, so the *path* carve-out
  is enforced **by construction** — but nothing stops a plan reaching an existing message with
  `Write`/`Edit`. **Live instance (#1044, self-reported):**
  `runnable-slice-keys-…-013.md` `created=06:10:54Z`, `mtime=06:15:03Z`, **drift 249 s**. A sweep of
  all 56 queued messages found **exactly one** such drift, so the breach is **isolated, not
  systemic**, and the plan disclosed it. ⚠ The correction was substantively **right** (013 falsely
  asserted a participation check "was never retried" / "failed silently"; it *was* retried with
  `--project-dir` and succeeded) — **the remedy was wrong**: the retraction belongs in a NEW message
  so the archive holds both claims. ⭐ **Correcting a false claim by overwriting it destroys the
  evidence that the false claim was made** — in this epic, that audit trail is the artifact that
  matters most. **Candidate fix**: make the invariant structural (write-once permissions, a content
  hash recorded at write, or a validator that flags created↔mtime drift at `inbox list`).
  ⇒ **OWNED 2026-08-08 by `PLAN-TRUTH-038`** — which owns the envelope schema and the amend/supersede model. **This entry is no longer a free-floating lead.**
- **No `queue --add-row` verb exists** — adding one plan requires rewriting the whole `plans[]`
  array, the lost-update path `--set-row` was built to remove. ⚠ **Exercised again 2026-07-28**
  adding five rows at once (56 → 61); the risk is real and unmitigated.
  ⇒ **OWNED 2026-08-08 by `PLAN-TRUTH-034`** — STILL LIVE and hit AGAIN in this session: appending PLAN-TRUTH-064 and then 065/066/067 each required rewriting the whole plans[] array via update-field, with a diff-verify after each write. Two more instances. **This entry is no longer a free-floating lead.**
- **`ext-self-review-plan-marshall` does not surface a path-substring predicate as a candidate class.**
  `str(Path)`-substring classification is a cheap deterministic candidate and was the exact defect
  PR-Agent caught in #1040 while self-review reported `42 candidates, 0 findings`. Adjacent to PLAN-81.
- ⛔ **`dispatch-inline-split.md` self-contradiction — THIRD independent observation (2026-07-29),
  and the SSOT is the WRONG side.** It declares itself SSOT for dispatched-vs-inline classification
  (`:3`) and lists `architecture-refresh` as **dispatched** (`:23`), while the step doc
  (`standards/architecture-refresh.md:26`) and `phase-6-finalize/SKILL.md` (five separate
  inline-only enumerations: `:607`, `:667`, `:889`, `:992`, `:1016`) both say **inline**. Handed
  over from the test-suite-quality epic; #1040 was observation two.
  - ⭐ **INLINE IS THE CORRECT ANSWER, and the SSOT is substantively wrong — not merely divergent.**
    `architecture-refresh.md:26` carries the mechanism: Tier-1 `prompt` mode requires
    `AskUserQuestion`, and **a dispatched leaf cannot fire `AskUserQuestion`** (leaf-cannot-prompt
    invariant, `ref-workflow-architecture/standards/agents.md`). Classifying it dispatched would make
    the documented Tier-1 prompt mode unreachable.
  - ⭐ **The SSOT's own stated rationale IS the error.** `:23` argues "the dispatching tier governs
    the classification" from the fact that Tier-1 re-enrichment fans out per module. That conflates
    **a sub-dispatch an inline step makes** with **the step itself being dispatched**. Every inline
    step that spawns anything would reclassify under that rule.
  - ⚠ **NEW — the live consequence, observed 2026-07-29.** An executing plan hit the contradiction
    mid-finalize and resolved it by **counting votes** (2 docs say inline, 1 says dispatched) rather
    than by the designated precedence it had just read. It reached the right behaviour by the wrong
    method: the same reasoning applied to the SSOT-wins rule the doc states lands on **dispatched**,
    i.e. on the unreachable-prompt configuration. The defect is not dormant prose — it is actively
    forcing coin-flip decisions in live finalize runs.
  - ⛔ **The guarding test cannot catch it, and reads green.**
    `test/plan-marshall/phase-6-finalize/test_dispatch_roster_closure.py` asserts roster coverage
    against the `marshal.json` registry, roster disjointness, absence of count claims, and the
    `SKILL.md` Step 3 dispatch branches. It verifies **exactly-one-classification, never
    correct-classification**, and never reads the step's own standards doc or the five `SKILL.md`
    inline-only enumerations. A green closure test reads as "the split is settled" — the epic theme
    exactly. Note it carries a hand-written targeted pin for `finalize-step-simplify` ("observably
    dispatched") and no equivalent pin for `architecture-refresh`, whose observable behaviour
    (`AskUserQuestion`) proves inline.
  - ⛔ **OWNER CORRECTION — this defect is UNOWNED.** The prior entry named "PLAN-64/104"; **neither
    ID exists in either epic's `status.json`** (verified 2026-07-29 against both queues). Resolved
    2026-07-29 by folding the reconciliation into **PLAN-TRUTH-001 as D5** (operator decision; the plan
    was PLAN-113 at the time) — chosen over staging a new plan because no `queue --add-row` verb exists
    and that plan already owns the same document. ⚠ **The "no add-row verb" premise was overturned on
    2026-07-30**: a new row CAN be appended via the whole-array `manage-status update-field --field plans`
    write, which is how PLAN-TRUTH-019 was staged. The fold decision still stands on the
    same-document argument alone.
  - ⛔ **CORRECTION TO MY OWN FIRST DIAGNOSIS — I asserted a cause I had not verified.** I initially
    recorded that *the sibling epic renumbered into the 120-band*, orphaning the citations. The
    evidence does not support that. `epic.md`'s own **stale generated START-HERE block** (regenerated
    2026-07-29) listed **PLAN-61, PLAN-104 and PLAN-64 as THIS epic's own staged queue rows** — they
    were dropped or re-slugged out of `truthful-signals`' `plans[]` and the block was never
    regenerated. The prose that cites them attributes them to `code-intelligence-substrate`, and
    **that attribution is itself unverified**. What IS verified: (a) the three IDs exist in neither
    queue, (b) this epic's generated block still carried them, (c) `PLAN-03` — also cited
    cross-epic — **does** exist in the sibling, so the citations are not uniformly stale.
    ⚠ **The 120-band successors named in the corrected citations (PLAN-120/121/125) are
    slug-inferred and unconfirmed on the merits.** Do not treat them as established ownership.
  - ⭐ **The real mechanism is the one actually demonstrated: a GENERATED block that was never
    regenerated became a citation source.** The block is marked never-hand-edit and is regenerated
    from `status.json`, but nothing regenerates it on a queue change — so it silently preserved a
    dead queue, and prose cited *that* rather than the machine authority. **Cite `status.json`, never
    the rendered block.**
  - ➡ **FORWARDED to `code-intelligence-substrate` as `truthful-signals-011.md`** (2026-07-29,
    `kind: finding`, envelope validated). **Split forward, not a hand-off:** the detector half
    (D5b population derivation + D5c cross-document assertion) is theirs under the routing rule
    ("detector population and derivation"); the classification correction (D5a/D5d) stays HERE
    because fixing the SSOT changes what the system reports about itself. ⚠ **Open question posed to
    them:** does PLAN-120 or PLAN-121 already own the derived classification detector? **A "no" is as
    useful as a "yes"** — on either answer we keep D5a/D5d, and we drop D5b/D5c from PLAN-TRUTH-001 only
    on a confirmed "yes". ⛔ **Do not block PLAN-TRUTH-001 on the reply** — ambiguity defaults here, and
    an unanswered forward must not strand the doc correction.
    ✅ **ANSWERED "yes" 2026-07-29**: `PLAN-CIS-011` (ex-PLAN-121) authoritatively owns the
    cross-document classification detector, so D5b/D5c were REMOVED from PLAN-TRUTH-001. Do not rebuild
    them.

- ⛔ **A `landing` message asserts a merge the writing step CANNOT have observed — and the correct
  form already exists in the codebase.** ⚠ **CORRECTED 2026-07-29 after #1055 merged.**
  - **What I first recorded**: `ceremony-prefilter-dropped-the-security-audit-001.md` (PLAN-112)
    states *"PR #1055, merged."* while #1055 was OPEN, so I logged it as a **false landing claim,
    second occurrence after PLAN-92**, and refused the transition.
  - **What is actually true**: #1055 **did** merge later, as `ad683c574`. The claim was **unfounded
    at write time**, not false in the end. ✅ **Refusing to transition was still correct** — at that
    moment the merge had not happened, and transitioning would have recorded a merge that did not
    yet exist. But "false claim" is the wrong characterisation and is withdrawn.
  - ⭐ **The sharp finding, which is better than the one I first wrote.** `lessons-capture` runs
    **before** `branch-cleanup` (the merge) — so a landing message is *structurally* written by a
    step that cannot observe the merge (lesson `2026-07-29-18-003`). **PLAN-110's message, written by
    the SAME step under the SAME constraint, says: *"Merge state at emission: NOT yet merged — the
    epic must reconcile the landing after the merge completes."*** Same position, opposite honesty.
  - ⛔ **Therefore this is not an ordering problem alone — it is a claim-labelling problem, and it is
    already solved somewhere in the tree.** The remedy is cheap: a pre-merge landing message MUST
    state merge state as *unobserved*, never as fact. PLAN-110's wording is the reference form.
  - **Standing rule, unchanged**: a `kind: landing` message is a LEAD. Corroborate against
    `origin/main` and PR state BEFORE any `queue --transition ... --status shipped`. That discipline
    is what made the distinction visible at all.
- **`change_type` is derived from the FIRST deliverable** (`phase-4-plan`), so a plan opening with a
  read-only discovery deliverable reports `verification` however much its later deliverables mutate.
  PLAN-112 removed the `change_type` leg from ONE gate; **the mis-scoped read is still live at every
  other consumer**, explicitly including `finalize-step-simplify`'s `simplify_inactive` gate (lesson
  `2026-07-16-20-001` was TRIMMED, not removed — its root cause survives there). Lesson
  `2026-07-29-18-002`. **Ready-made follow-up plan.**
- **A third `_resolve_footprint` call site is still deferred** — `~:686` in
  `_apply_canonical_verify_inactive`. ⭐ **CodeRabbit named two call sites; the real count is three** —
  another instance of *a reviewer's list is a SAMPLE, not an enumeration*.
- **`worktree-remove` hardcodes a 60s inner `git` timeout** a venv-bearing worktree cannot meet. It
  timed out **twice** on PLAN-114, leaving a half-deleted tree; completed only via the doc's own
  sanctioned `--force` at 600s. Lesson `2026-07-29-18-004` family.
- **The outline declared an affected-file path that has NEVER existed** —
  `test/plan-marshall/marshall-orchestrator/test_finalize_orchestration_routing.py` (real file is
  under `phase-6-finalize/`). It propagated unchecked into the scope estimate AND the manifest;
  **three consumers counted it and none stat'd it.** ➡ Forwarded to the sibling
  (`truthful-signals-012.md`) as likely PLAN-125 territory. ⭐ Same family as this session's
  phantom-plan-ID citations: **an identifier that is counted but never resolved.**
- **No persisted SonarCloud project-key config** — every `sonar-roundtrip` dispatch re-derives
  `cuioss_plan-marshall` ad hoc, with nothing to verify it against.
- **A stale local `main` silently widens the self-review candidate diff** — and silently seeds the
  branch (`ext-self-review-plan-marshall`).

- ⛔ **`absent` is TWO states with opposite remedies — and the common path manufactures the wrong
  one.** Folded into PLAN-116 as **Defect F** (from `truthful-signals-007.md`). After #1053 pr-agent
  subscribes to `opened`/`reopened`/`ready_for_review` only, so **a rebase is invisible to it**, while
  `finalize-step-sync-baseline` rebases and force-pushes on **every** finalize *after* the PR-open
  review. ⭐ **Any PR needing a rebase therefore ends with a stale Guide and a false `absent`** — this
  is the normal path, and it likely explains much of this epic's review-coverage cost, including
  PLAN-112's six barrier rounds and 63%-of-4.7M finalize spend.
- **A daemon-routed build false-greens any plan that tests the routing seam.** Every build in PLAN-110
  was forced `--execution-mode in_process`. **Any plan touching the routing seam inherits this
  constraint** — it is a live trap, not a historical note.
- **An empty footprint at compose time is read as "nothing to build", not as "unknown".** Same family
  as the `Recall 0%` manufactured FAIL and the `--help` freshness evidence: **an unmeasurable quantity
  reported as a measured zero.** ⭐ This rule now has four independent instances and is the strongest
  cross-cutting generalisation the epic has produced.
- **Build wrapper `duration_seconds: 0` can hide a real multi-minute timeout** — the inner log
  correctly recorded `status=timeout, duration_seconds=330`. Third polarity of the known
  outer-envelope defect (GREEN-as-timeout, TIMEOUT-as-0).
- **Plugin cache retains 30 versions against `plugin_cache_keep_versions: 5`.** Counted 2026-07-29 at
  `~/.claude/plugins/cache/plan-marshall/plan-marshall/` — 30 version directories (`0.1.1194` …
  `0.1.1269`) while the configured keep is 5. Either the 7-day `.orphaned_at` GC has not run, or its
  keep-oracle is not consuming this knob. ⚠ **Not blocking and not the dangerous form** — the
  executor's embedded paths were verified to resolve to exactly ONE version (`0.1.1269`), so the
  known downgrade-inversion is absent. Recorded as unexplained retention, not as a live fault.
- **`marshal.json provisioned_version` lags the executor by three versions** (`0.1.1266` vs
  `0.1.1269`) after #1062's steward refresh, because the executor regenerated again afterwards.
  ⭐ **A provisioning stamp written before the last regeneration is stale by construction** — the same
  write-then-move-on shape as the resume-anchor drift (PLAN-203) and the pre-merge landing message.
  **Third instance of that shape today.**
- ⛔ **`manage-lessons` STILL refuses a host repo's own colon-form component — #1050 CLOSED ONLY HALF THE
  DEFECT, and the ledger recorded it as closed.** ✅ **ORCHESTRATOR-VERIFIED BY SYMBOL at HEAD**,
  `_lessons_io.py:93-107`: #1050 (PLAN-103) added the `if ':' not in component: return` early exit, so a
  bare `integration-tests` now files — that is the half that was fixed. But `bundle =
  component.split(':', 1)[0]` then refuses **any** colon-form component whose leading segment is not an
  installed plan-marshall bundle, so the host repo's own `api-sheriff:auth` raises `WrongStoreError`
  exactly as before. **Seven** lessons are blocked behind this in that repo. ⚠ **The guard cannot
  distinguish a FOREIGN bundle from the host repo's OWN project namespace**, and
  `--allow-foreign-store` is backwards here: the override would file into the *correct* store to bypass
  a false positive. ⭐ **Epic-theme bullseye: a partial fix reported as a fix.** PLAN-103's landing
  records the refusal-message defect as "addressed" with no note that the colon-form half survived.
  ⇒ Distinguish host-project namespaces from bundle prefixes, or scope the guard to prefixes that are
  *known* bundles rather than refusing all unknown ones. **Source: API-Sheriff round-3 cross-ref to L8**
  (rounds 1–2 recorded the bare-name form only — the observed scope is wider than L8 stated).
- ⛔ **The plan-id derivation is an LLM judgement, so the canonical emit shape produces NON-DETERMINISTIC
  plan ids by construction — and this ledger is itself the evidence.** ✅ **ORCHESTRATOR-VERIFIED**:
  `phase-1-init/SKILL.md:84` reads *"From description: first 3-5 meaningful words, kebab-cased, max 50
  chars"* — "meaningful" is the LLM decision smuggled into a rule that reads as mechanical. API-Sheriff
  emitted four mechanically identical commands and got three ids keeping the `PLAN-NN` prefix and one
  dropping it (`PLAN-30-deployment-diagram-type.md` → `deployment-diagram-type`), which broke an
  orchestrator start-detection poll that globbed `plan-30*` and reported a running plan as unstarted.
  ⭐ **INDEPENDENTLY CORROBORATED FROM OUR OWN `plans[]`**: every stamped `plan_marshall_plan_id` here —
  `inbox-sequence-reuse-collides-with-the-archive`, `one-coherent-automated-review-contract`,
  `lane-router-reads-the-wrong-body`, 17 in all — **dropped the prefix**. Same documented rule, opposite
  dominant outcome in two repos. That is stronger evidence of non-determinism than either repo alone,
  and it is why our own plan-row↔plan-dir traceability depends on the stamped column rather than on the
  id. ⛔ **This bites US at the orchestrator surface**: `orchestrate.md` Step 5's emitted command is a
  bare one-line pointer with **no `plan_id`** — verified by direct read this session — so the documented
  emit shape is the thing generating the non-determinism. ⇒ Make the derivation mechanical (e.g. "when
  the description references a file, slugify the basename"), and add the explicit `plan_id` to the
  canonical emit shape, which fixes every consumer of that workflow at once. The `plan_id` override
  already exists (Step 2a) and works — but an escape hatch every programmatic caller must remember is a
  defaulting bug, not a feature. **Source: API-Sheriff round-3 #4.**
- ⛔ **`ci checks status` has no by-commit lookup, so a post-merge obligation the orchestrator now OWNS
  cannot be performed through sanctioned tooling.** ✅ **ORCHESTRATOR-VERIFIED**: the
  `tools-integration-ci/SKILL.md` canonical surface for `checks status` is
  `[--pr-number PR_NUMBER] [--head HEAD]` — **no `--commit`, no `--branch` run mode**. Push-triggered
  runs are first-class CI objects the abstraction models only in their PR-attached subset. A
  `deploy-snapshot` job skipped on PRs and run only on the push to `main` is therefore unreachable.
  ⛔ **The trap closed on 2026-07-30**: the source project ruled that the plan stops at the merge and
  post-merge aftermath belongs to the orchestrator — a correct split — which places the obligation on
  the actor whose small-ops carve-out permits read-side `ci` calls and **forbids `gh`/`glab` outright**.
  **The only actor responsible is the one structurally incapable of performing it**, and any orchestrator
  adopting the split inherits the dead end. ⇒ Add `--commit <sha>` or a `--branch main` workflow-run mode
  to `ci checks status`; until then the carve-out and the documented obligation are in direct conflict
  and one side must give explicitly. ⚠ **Routing test applied**: this stayed HERE rather than going to
  `review-apparatus` because the subject is **gate/build-signal reachability, not review coverage** —
  per the boundary refinement, those are different subjects. Reversible if the operator reads it the
  other way. ⚠ Surface collides with LAUNCHED PLAN-115 and staged PLAN-TRUTH-004, both
  `tools-integration-ci` — sequence, do not pair. **Source: API-Sheriff round-3 #5.**
- ⛔ **A `(read)`-marked test path earned a `module_testing` profile — the profile was inferred from
  footprint PRESENCE, not from recorded INTENT.** A deliverable modifying no test file (both test paths
  marked `(read)`, per-file text *"read only — do not edit"*, success criterion asserting no test source
  is modified) was given `module_testing`; the Q-Gate caught it at `error`. Because phase-4-plan maps
  profiles 1:N onto tasks, it would have emitted a `module_testing` task with **no authoring work
  product** — running pre-existing tripwire tests is evidence-gathering, not test authoring.
  ⭐ **Root cause is a permission read as a directive**: the deterministic bucket classifier is
  **intent-blind** (it resolves roles over the whole affected-files list regardless of `(read)` markers)
  and returned `mixed_with_docs`, which *permits* `module_testing` without *compelling* it.
  ⇒ Assign `module_testing` only when the deliverable creates or modifies a test file; a `(read)` path
  contributes **no** authoring profile; when a test RUN is wanted as evidence it belongs in Verification
  or takes the `verification` profile. **Source: API-Sheriff round-3 #2.**
- ⛔ **The bucket names a file ROLE, not a build verdict — and there is NO honest bucket for a config-only
  footprint, so a Q-Gate finding demanded a value the classifier cannot produce.** A Q-Gate finding
  attacked `bucket: documentation_only` on a `{pom.xml, CLAUDE.md}` deliverable that was verify-class on
  the outline's own evidence (`architecture derive-verification` puts `pom.xml` at `build_class: verify`,
  the Verification block required `verify -Ppre-commit`, and a real `dependencyManagement` edit was
  permitted). ✅ **ORCHESTRATOR-VERIFIED BY SYMBOL that the demanded re-bucket was UNSATISFIABLE**:
  `manage-execution-manifest.py:351` builds `roles_present` as `{role for role in per_path_role.values()
  if role != 'config'}` — config is **deliberately excluded** — and `:366-369` returns
  `documentation_only` for a config-only claim set with that exact comment. The six-value vocabulary
  (`:248-249`) contains **no config bucket**. So `documentation_only` is the correct and only reachable
  value, and hand-writing another would have falsified the audit trail the bucket comment exists to be.
  ⛔ **Complying would also have re-introduced the sibling defect above** (pulling `module_testing` onto
  a deliverable touching no test file) — **two findings against the same Profiles block in one Q-Gate
  pass must be resolved as a SET.** ⇒ Never adjust the bucket to make a footprint look right; when a
  finding demands a value the deterministic classifier does not produce, **run the classifier — its
  output is ground truth and the finding is the hypothesis** — and resolve via the *"or state why the
  annotation is correct"* branch as `taken_into_account`. ⭐ **Upstream fix worth taking:** add a config
  bucket, or document explicitly that `documentation_only` is the sanctioned value for config-only
  footprints. **Source: API-Sheriff round-3 #3.**
- ⚠ **A dispatched leaf cannot verdict evidence it cannot fetch — and the degradation is invisible in the
  output.** A 16-PR upstream compatibility audit ran in a dispatched leaf; for two PRs only
  changed-file **lists** were reachable, which cannot distinguish a Javadoc accessor rename from a
  caching-strategy rework. ⭐ **The mechanism WORKED and needs no fix**: the leaf recorded a declared-gap
  Q-Gate `triage` finding rather than closing the question from absent evidence, and the main-context
  orchestrator resolved it in one `compare` call — finding the real carrier was **neither named suspect**
  but an unnamed third PR. **Keep the pattern: leaf declares the ceiling, orchestrator supplies the
  reach.** ⛔ The residual risk is the silent variant: an audit that degrades from "read the diffs" to
  "infer from file names" still returns a **full verdict table**, and nothing in the output says so.
  ⇒ Adopted as practice rather than staged: **provision evidence BEFORE dispatch** (hand the leaf
  concrete diff hunks, or keep the audit in main context); **never verdict a behaviour change from a
  changed-file list** — a file list supports "did not touch the area", never "did not change the
  behaviour"; named-suspect PRs in a request are **hypotheses**. **Stage a spec if a second instance
  appears** — one observation where the guard held is not yet a defect population.
  **Source: API-Sheriff round-3 #1.**
- ⛔ **Path classification is keyed on well-known YAML *filenames*, not on YAML as a class — Helm charts
  still bucket `unknown`.** ✅ **DEDUP RESOLVED FOR THEM**: they flagged this for manual dedup against
  round 2 because their carrier was deleted; **our copy of rounds 1–2 contains no YAML/bucket item**, so
  the narrowed finding is NEW. ⚠ Caveat stated honestly: only **5** of round 2's 18 items are explicitly
  tagged `Source: API-Sheriff #N` here, so our record of round 2 is partial and this dedup is
  correspondingly partial. Their measured table (at bundle `0.1.1261`) shows `docker-compose.yml`,
  `compose.yaml` and `.github/workflows/release.yml` classifying, while `Chart.yaml`, `values.yaml`,
  `templates/deployment.yaml` and any `some/random.yaml` return `unknown`. ⭐ **The structural point is
  the value**: a name-keyed allowlist works for fixed-filename conventions and **cannot** work for Helm,
  whose `templates/` holds whatever the author names — so adding `Chart.yaml`/`values.yaml` would still
  leave the class broken. ⇒ Give `unknown` a defined generic degradation path (resolve a profile and a
  verification command) rather than stalling a gate; and make the Q-Gate refusal **name which paths were
  unmatched** — their epic recorded its unblock signal as "YAML classifying out of `unknown`", a
  whole-class belief that was already half-wrong, and the silent gate is what left it uncorrected.
  ⭐ Their note that `docker-compose.yml` → `documentation_only` is *"odd on its face"* is further
  evidence for the missing config bucket (round-3 #3, verified here at `manage-execution-manifest.py:351`
  / `:366-369`). **Source: API-Sheriff round-4 #1.**
- ⛔ **`archive-plan` can silently not happen, leaving a shipped plan live in the store — AND WE HAVE A
  CANDIDATE INSTANCE IN FLIGHT RIGHT NOW.** Their instance: PLAN-25 merged as their PR #123 on 07-28 and
  its directory was still live on 07-29 with `current_phase: 6-finalize`, no `archived-plans` entry, found
  by eye a day later. ⚠ **OUR OWN PLAN-203 shows the same signature at 10:19:09Z**: PR #1064 merged
  (`e82b466ee`), `branch-cleanup` recorded *"merged via queue, main pulled, worktree removed, branch
  gone"*, no `plan-203-*` worktree survives — yet the plan directory is still live, `current_phase` reads
  `6-finalize`/`in_progress`, and no `2026-07-30-plan-203-*` archive entry exists. ⛔ **NOT declared a
  defect**: its last step update was 10:12:49Z, ~6 minutes earlier, so finalize may still be running, and
  #1063's plan DID archive (`2026-07-30-audit-report-path-ignores-plan-dir`) so the step is not globally
  broken. ⇒ **Re-check the store on the next resume; if it is still unarchived, this is confirmed.**
  ⭐ Why it matters is our problem too: a shipped-but-unarchived plan is **indistinguishable from a
  running one by directory presence**, which is the signal start-detection reads. ⇒ Make the terminal
  state assertable — either `archive-plan` completes or the plan carries an explicit unfinished-finalize
  marker; and add a companion check for *shipped-but-unarchived*, which `list-orphans` does **not** cover
  (it finds directories without `status.json`). **Source: API-Sheriff round-4 #2.**
- ⛔ **A findings store was written into `.plan/local/plans/{epic-slug}/` — an orchestrator-scoped Sonar
  scan leaked into the PLANS store, one `rm -rf` from destroying release-gating evidence.**
  `list-orphans` reported `.plan/local/plans/api-sheriff-roadmap/` — **the epic slug inside the plans
  store** — holding only `artifacts/findings/sonar-issue.jsonl` and `sonar-scan-summary.jsonl` with no
  `status.json`. Contents were real: two confirmed scans recording four `new_code` issues, all
  `resolution: pending`. Something resolved a **plan-scoped** findings path using an **orchestrator slug**
  as a `plan_id`. ✅ **ORCHESTRATOR-VERIFIED NOT PRESENT HERE**: `.plan/local/plans/` contains exactly one
  directory (`plan-203-inbox-consumed-vs-missing`) and no epic-slug directory for any of the three live
  epics. ⭐ The severity framing is right — those findings were **orphaned, not lost-but-safe**: they sat
  at a path no plan and no epic reads, in a store where an epic is structurally invisible, and survived
  only because the orphan was inspected before removal. ⇒ Findings written in an orchestrator-scoped
  context must resolve to the orchestrator store or be **refused at the path-resolution seam** — and note
  their own caveat that the goal is a *correct* guard, not merely a strict one (see the `manage-lessons`
  half-fix above, which is the strict-but-wrong version of exactly this). ⇒ Also worth taking: have
  `list-orphans` report **non-empty** orphans louder than empty ones — content is a data-loss risk, litter
  is not. **Source: API-Sheriff round-4 #3.**
- ⚠ **FORWARDED, NOT STAGED — `required_bots` empty makes the participation barrier vacuously true, and
  `migrate-bot-lists` restores an incomplete list.** Observation A: their PLAN-31A merged with
  `required_bots` **empty** and the barrier returned `participation_complete: true` while CodeRabbit and
  Sourcery had both refused on rate limit — a verdict *true and meaningless*, reported in the same shape
  as a genuine pass. Observation B: the steward migration then populated `coderabbit,pr-agent` while their
  `CLAUDE.md` names **three** bots as policy, so the barrier under-enforces while **looking** configured —
  worse than empty, because a two-of-three list looks deliberate. ⛔ **ROUTED TO `review-apparatus`** per
  the three-way rule: the PR/review test runs first and wins outright, and a participation barrier is
  review apparatus, not measurement. Forwarded **whole** rather than split — the steward-migration half
  only matters through the barrier it feeds, and splitting a batch was already ruled worse than either
  whole. ⚠ **Do NOT read Observation B as applying to us**: `required_bots = coderabbit,pr-agent` is the
  **deliberate** core here with Sourcery kept as an *additional* reviewer by operator decision, so our
  two-of-three is policy, not an under-restore. The general mechanism — a migration emitting a
  plausible-looking subset without saying what it could not map — is what forwards. ✅ **DEDUP RESOLVED**:
  their "flagged for manual dedup against round 2" concern finds no `required_bots`/`migrate-bot-lists`
  item in our rounds 1–2 record; the two `required_bots` mentions here are **our own** #1041 observations,
  not theirs. Their suggestion to fold Observation A into round-2 **L2** (guard whose predicate excludes
  its motivating case) is sound and is `review-apparatus`'s call. **Source: API-Sheriff round-4 #4.**
- ⛔ **No queryable "is this plan running?" signal — the plan directory lags the start by MINUTES, and we
  have just been bitten by the ambiguity half.** Their instance: `status.json` recorded
  `created: 16:49:05Z` while the directory appeared ~**6 minutes** later; a 60-second poll — generous
  against the *"tens of seconds"* their orchestrator guidance recorded — concluded a launch had failed. Two
  independent causes combined with round-3 #4's naming defect, and **both must be fixed** for start
  detection to work. ⭐ **The ambiguity half is live for us**: PLAN-203 is shipped-and-unarchived (above),
  so its directory is present while nothing runs — directory presence is **late AND ambiguous**, and an
  orchestrator concluding "unstarted" may re-emit a running plan or strand its slot. ⇒ Provide a cheap
  registration/liveness signal written **before** phase-1 work, so "accepted but not yet materialised" is
  distinguishable from "never started"; failing that, **document the real lag** — the observed value was
  ~6 minutes against a documented "tens of seconds". **Source: API-Sheriff round-4 #5.**
- ⛔ **The plan-vs-orchestrator boundary for post-merge verification is UNSTATED in the orchestration
  model, and the split the docs imply is unperformable — this one is ours to fix.** Their operator has
  ruled that a plan's finalize **ends at the merge** and the post-merge aftermath belongs to the
  **orchestrator**, consumed at `analyze`. ⭐ **The rationale is general, not project-specific**: those
  signals arrive after the plan's work is complete and unchangeable, on a timescale the plan cannot bound —
  a plan that blocks on them holds a slot for no work, and a plan that claims them without waiting reports
  a green it never observed. `phase-6-finalize` already ends at merge/cleanup/metrics/archive, which is
  **consistent** with the ruling, but nothing **states** the boundary, so project-level docs fill the
  vacuum and push the obligation back onto the plan. ⛔ **This makes round-3 #5 BLOCKING rather than
  awkward**: the obligation lands on the actor whose carve-out forbids `gh`/`glab`, while `ci checks
  status` takes only `--pr-number`/`--head`. ⇒ **State the boundary in
  `persona-marshall-orchestrator/standards/orchestration-model.md`** — plan owns through the merge,
  orchestrator owns the aftermath — so it is not re-derived per project; **ship the by-commit lookup
  first**, because the split is not adoptable without it; and consider making the post-merge check a
  first-class part of `analyze`'s full-ship branch with an explicit **`owed`** state, so a landing report
  can record "merged, post-merge verification pending" rather than silently omitting it or overclaiming.
  ⭐ **We are already exposed**: PLAN-203's landing report (written today) records its post-merge revisit
  as owed-not-done, which is precisely the `owed` state they propose making first-class.
  **Source: API-Sheriff round-4 #6.**
- ⛔ **A FINALIZE STEP RECORD HAS NO ATTEMPT IDENTITY, so a retried dispatch is indistinguishable from a
  laundered failure.** Surfaced by adjudicating #1064's self-review dispute (see `landings/PLAN-203.md`
  § ADJUDICATION). The retrospective saw an ERROR at 07:27:40 (*"Missing required candidates input —
  cannot run Steps 2-3 cognitive checks"*) followed by `outcome=done` /
  `display_detail: "self-review clean: 26 candidates, no check matched"`, and concluded the gate reported
  clean over checks that could not run. ✅ **The operator's correction is CONFIRMED**: the first dispatch
  refused, Step 1 then ran inline, and the re-dispatch examined the full candidate set — and the record
  proves it, because **26 is a non-empty candidate count and cannot come from the refusing run**.
  ⛔ **But the retrospective named the real problem itself:** *"Nothing in `status.metadata.phase_steps`
  preserves the error."* A retried dispatch collapses into ONE step entry, so *"refused, then succeeded
  on re-dispatch"* and *"refused, and was reported green anyway"* are **the same record**. The
  retrospective took the pessimistic reading, the operator knows the optimistic one is true, and **the
  persisted record cannot adjudicate between them.** ⇒ Give a step record attempt identity (attempt
  count, or the superseded attempt's outcome retained) so a retry is visible as a retry. ⭐ **Two
  reusable rules fell out**: a step that never ran cannot *miss* a specific check class, so "self-review
  missed X" is itself evidence the step ran; and **a bundled finding must be dispositioned PER INSTANCE**
  — this one carried two, of which instance 1 is refuted-as-stated and instance 2 (the
  `review_completeness` argparse rejection) the operator confirms as real. Refuting one half retires
  nothing else. **Source: #1064 landing adjudication.**
- ⛔ **PLAN-203 FIXED ONE INSTANCE OF A PATTERN WITH AT LEAST EIGHT KNOWN LIVE SIBLINGS — the population
  is the scope for the next plan in this family, not the named site.** Two independent enumerations from
  #1064, both recorded rather than summarised:
  - Its **quality-verification report**: *"THEME RECURRENCE: the plan's own defect archetype — a zero
    that cannot state which kind of zero it is — was found live in **five further surfaces** of the same
    finalize pipeline (self-review, review barrier, retrospective footprint check, review-retrospective
    reviewer accounting, manifest prune predicate)."*
  - Its **D4 gate**, which **REFUTED its own request's hypothesis** that the inbox count was the only
    drifted hand-written count: **13 derivable assertion classes vs 8 genuinely narrative across 7
    files**, with three still unprotected — the **`epic.md` Ordered Queue (4 derivable columns and NO
    BEGIN/END GENERATED guard, strictly larger than what shipped)**, the Decisions list, and the anchor's
    PR/CI clause.
  ⚠ **Two of those siblings are in THIS ledger** (the Ordered Queue table and the anchor's PR/CI clause),
  so this epic is a carrier of the defect it tracks. ⭐ The generalisable rule is the one this epic keeps
  re-learning: **a request that names a site is a SAMPLE; the gate that enumerates the population is what
  turns it into a scope.** D4 mutated nothing and was the most valuable deliverable in the plan.
  ⇒ Scope the successor plan against the enumeration, and note the `epic.md` START-HERE block already
  carries a BEGIN/END GENERATED guard while the Ordered Queue table — same file, same authority — does
  not. **Source: #1064 D4 gate + quality-verification report.**
- ⛔ **A SIBLING REFUTED OUR OWN FOLD FROM ONE TURN EARLIER, AND THEY WERE RIGHT.** Drained
  `review-apparatus-006` 2026-07-30. We folded `#1064`'s `review_completeness --enabled-bots` argparse
  exit 2 into **PLAN-TRUTH-012** as a canonical-block-vs-argparse divergence. ✅ **Refutation
  independently re-verified here**: `grep -rn "enabled-bots\|enabled_bots" marketplace/bundles/` returns
  **no such CLI flag at all** — every hit is the retired `enabled_bots` **config knob** in migration prose
  (`data-model.md`, `marshall-steward/SKILL.md`, `upgrade.py:239` `_LEGACY_BOT_LIST_KEY`). No canonical
  block advertises the flag, so TRUTH-012's rule had nothing to catch. **The subagents read a STALE
  PLUGIN CACHE and invoked a retired flag against the current script.**
  ⇒ **RETRACTED from PLAN-TRUTH-012 and RE-AIMED to PLAN-TRUTH-008**, whose doc-vs-script skew axis is the
  real archetype; the fix is cache-version resolution, not a doc edit. A TRUTH-012 deliverable aimed at
  this would have found nothing — caught before outline, which is the only reason it was cheap.
  ⭐ **The sibling's measurement sharpens the axis to one sentence:** executor embeds exactly one version
  (`0.1.1271`, no inversion), skills load from cache `0.1.1240`, **32 versions coexist** ⇒ **what we READ
  is 31 versions behind what we RUN.** And it explains "two subagents independently" as *mechanism, not
  coincidence* — agents resolve skills from the cache.
  ⚠ **Guard both directions**: the stale-cache archetype invalidates an ARTIFACT, never acquits a DEFECT.
  This retraction rests on the grep of source, not on the archetype's plausibility — the epic has been
  burned before by over-applying it (PLAN-75 Defect B was REAL).
  ⚠ **Not ours, but it changes how we read logs:** a **second, distinct** rejection exists in the same
  script — `--participated-bots` with **no value** (the zero-participation case) exits 2 because the
  documented invocation interpolates it **unquoted**, so *the gate crashes precisely in the scenario it
  exists to detect* and the calling step still recorded `outcome: done`. Staged as their `PLAN-PR-014`.
  ⛔ **Both rejections log as `failure_kind=argparse_rejection` and are INDISTINGUISHABLE in the record**,
  so any attribution from a log signature alone is a HYPOTHESIS — including the operator's original
  attribution of the `#1064` incident. **Source: `review-apparatus-006`.**
- ⛔ **THE DRAIN HAS NO EMISSION-QUIESCENCE SIGNAL, so a completed drain reports a zero that is not
  stable.** Observed live 2026-07-30 while draining: the queue went **18 → 34 → 33 → 34**, with
  `compose-time-subtractions-drop-steps-009..012` arriving at 12:41–12:43Z — **the count changed between
  two consecutive `inbox list` calls.** PLAN-202's retrospective was still emitting while its own landing
  was being reconciled.
  ⭐ **This is PLAN-203's defect one level up.** #1064 made *directory* zeros self-describing
  (`inbox_state`: empty vs missing vs unreadable). But nothing distinguishes **"the queue is empty"** from
  **"the queue is empty right now and a sender is mid-emission"**. `inbox list` reports a count; no
  surface reports *whether the senders are done*. A drain that finishes during a live retrospective
  archives a partial set and can truthfully report `drained: N` while `M` more are inbound — a confident
  count hiding a caveat, in the very mechanism this epic built to carry findings.
  ⇒ **Operational rule adopted immediately:** reconcile landings first (they are complete facts), and
  **do not drain candidate-lessons from a plan whose finalize is still running.** A second drain is
  guaranteed otherwise, and the risk is not the extra pass — it is reporting a settled queue that is not.
  ⇒ **Fix shape (not yet staged):** either a per-sender done marker written at the end of
  `lessons-capture`/retrospective emission, or an `inbox list` field reporting the newest message age
  against the senders' known-live plans, so a drain can tell "quiet" from "quiet so far".
  ⚠ **Do not conflate with the archive-vs-missing fix.** #1064 shipped that and it works — this is a
  distinct axis (sender liveness, not path resolution) and folding it into #1064's surface would read as
  a regression of shipped work. **Source: observed by this orchestrator during the 2026-07-30 drain.**
  ⇒ **OWNED 2026-08-08 by `PLAN-TRUTH-032`** — and 032 is now sequenced AFTER PLAN-TRUTH-038, which owns the envelope message-state vocabulary it must reuse. **This entry is no longer a free-floating lead.**
- ⛔ **A CHECK THAT FLIPS TO SUCCESS AFTER A RECORDED REFUSAL RE-CREDITS THE REFUSAL, AND NOTHING ASKS
  WHETHER THE FLIP WAS A REVIEW.** Operator-owned and operator-reported at the #1066 merge, recorded here
  because it is the strongest instance of this epic's theme yet: `ci-verify` recorded *"CodeRabbit check
  pending = rate-limit refusal, not a signal"* — the correct discount, written down. **43 minutes later
  the merge cited "11/11 checks pass incl CodeRabbit."** The check did genuinely flip to `SUCCESS`, but
  **nothing verified whether that was a real review or an auto-resolve**, and a confident aggregate
  overwrote a caveat the same actor had authored.
  ⭐ **This is the standing participation rule failing at a new point.** The rule already says a `SUCCESS`
  check is not evidence of participation. What this adds: **a check that was correctly discounted can be
  silently RE-credited later by an aggregate count**, because the aggregate reads current check state and
  the discount lived only in prose. The caveat had no representation the aggregate could see.
  ⇒ Two consequences. **(a)** An aggregate like "11/11" must not be assembled from check state alone once
  any check has been discounted in-run — the discount must be a machine fact the aggregate consumes, not a
  note beside it. **(b)** Only `ci pr comments --pr-number 1066` settles whether CodeRabbit reviewed;
  ⚠ **that check has NOT been run** — the flip is unexplained, not benign. **Post-merge revisit for #1066
  is owed and this is now its first question.**
  ⚠ Adjacent, same report, caught before it was recorded: **the main checkout was passed as
  `--worktree-path` to a CI precondition, returning a green that was `main`'s HEAD, not the PR's.** A
  green whose subject is the wrong tree. Not filed as a separate defect — the operator caught it — but the
  shape belongs on the by-commit/by-tree lookup surface (round-3 #5, round-4 #6).
  **Source: operator report at the #1066 landing.**
- ⚠ **Wall-clock and worked-time diverge by 3.3× on a shipped plan, and phase-4-plan's ratio is 20×.**
  #1066's metrics: **5 h 31 m worked against 18 h 8 m wall**, and `4-plan` alone reads **29 m 44 s worked
  vs 9 h 48 m wall**. Tokens **5.8 M**, of which `6-finalize` is **2.4 M** — finalize alone outspends
  every other phase, and #1064 showed the same shape (3.2 M total, review dispatches dominant).
  ⚠ **NOT filed as a defect and NOT interpreted.** Idle wall-clock on an operator-driven plan may be
  entirely benign (the operator was elsewhere), and this epic's own rule forbids reading a measurement
  before its population is established — the token ledgers for this very plan **disagree three ways**
  (forwarded to `code-intelligence-substrate`). ⇒ **Recorded as a datum, to be interpreted only once a
  single reconciled ledger exists.** Reading a 20× ratio as a finding today would be exactly the
  confident-number-without-its-population error the forwarded item describes.
- ⛔ **`affected_files_recall` IS DEAD BY CONSTRUCTION FOR EVERY WORKTREE-BACKED PLAN — it reported "Recall
  0%" where real recall is ~89%.** Surfaced by #1065's retrospective. `branch-cleanup` (step 15) **removes
  the worktree before `plan-retrospective` (step 16) reads it**, so the metric can never see the files it
  measures. ⭐ **An ordering defect wearing a measurement result's clothes** — and `0%` is the most damaging
  possible rendering of *"cannot measure"*, because unlike an error it is a **plausible value that invites
  action**. A reader sees a catastrophic recall failure; the truth is the instrument was destroyed before it
  read.
  ⚠ **This is the PLAN-10 archetype exactly** (a finalize-time component whose own finalize ordering
  prevents it from working; there, cache-sync at 19 vs retrospective at 17). **Same family, new instance —
  which makes the family a standing structural hazard of the finalize step order, not two coincidences.**
  ⇒ Either read the footprint before `branch-cleanup`, or report an explicit *unmeasurable* state. ⛔ **Never
  a number.** ⇒ Stays in this epic by precedent — PLAN-51 (retrospective-compile-report-silent-omit) and
  PLAN-54 (retrospective-checker-assertion-integrity) both shipped here. **Source: #1065 retrospective.**
- ⛔ **`direct-gh-glab-usage` returned a vacuous `total: 0` under its OWN canonical invocation** — a detector
  reporting a clean sweep it never performed. **Vacuous-guard family, n=8.** ⚠ Note what makes this one
  worse than the usual instance: the canonical block is the *documented* way to run it, so **the sanctioned
  invocation is the one that produces the false clean**. A user following the docs gets the vacuous answer;
  only a deviation from them would reveal it. ⇒ Same home and reasoning as the item above.
  **Source: #1065 retrospective.**
  ⇒ **OWNED 2026-08-08 by `PLAN-TRUTH-065`** — folded at the 2026-08-08 drain together with the help-surface cache defect - same gate, same report-a-problem-that-is-not-one shape. **This entry is no longer a free-floating lead.**
- ⚠ **THE EXECUTOR WAS REGENERATED TWICE INSIDE ONE SESSION — `0.1.1269` at entry, `0.1.1273` at finalize —
  and `marshal.json`'s provisioning stamp is behind BOTH (`0.1.1266`).** Reported by the operator at the
  #1065 landing. ⭐ **This is the sharpest evidence yet for the PLAN-TRUTH-008 skew axis**, because it makes
  the drift *intra-session*: this orchestrator recorded `0.1.1269` earlier today, a sibling epic
  independently reported `0.1.1271`, and finalize landed `0.1.1273`. **Three values for "the current
  version" inside one working day, none of them wrong when written.**
  ⇒ Any assertion of the form "the executor is at version X" is a **snapshot**, exactly like an
  `origin/main` scan or an inbox count. Add it to the re-derive-at-the-moment-of-the-claim list.
  ⚠ **Operational consequence for the operator, not a defect:** the session must be restarted before the
  next plan to pick up the new agent registry, and `/marshall-steward` is owed to refresh the stamp. ⚠ This
  session has been running on the entry-time registry throughout — a caveat on everything it dispatched.
  **Source: operator report at the #1065 landing.**
- ⛔ **THE LIGHT LANE COLLAPSES `phase-2-refine`, WHICH IS THE ONLY SITE THAT AUTHORS `pr_title` — SO THE
  LANE FAILS THE NEXT PHASE'S HANDSHAKE BY CONSTRUCTION.** ✅ **Mechanism ORCHESTRATOR-VERIFIED at HEAD**,
  and it is worse than a missing field:
  - OBSERVED — `phase-2-refine/SKILL.md:262` is the **authoring site**: *"Author and persist a
    commit-style PR title to `status.json` metadata via `manage-status metadata --set --field pr_title`."*
    A bundle-wide grep shows `pr_title` written **only** in `phase-2-refine` (SKILL + its
    `refine-workflow-detail.md`); `create-pr.md` **consumes** it; the handshake **enforces** it.
  - OBSERVED — `plan-marshall/references/phase-handshake.md:139`: `pr_title_present` raises
    **`PrTitleMissing` when empty/missing at `2-refine`+**, severity **`blocking_at_every_boundary`**.
    Error payload `pr_title_missing` at `:301-307`, raised in `_handshake_commands.py:418`.
  - ⇒ **One authoring site, in the phase the lane skips, behind a gate that blocks at EVERY subsequent
    boundary.** Not a race, not a config gap — arithmetic.
  ⚠ **HYPOTHESIS, verify-at-outline:** that the light lane genuinely collapses `2-refine` (their
  observation; `_cmd_planning_lane.py` is the lane *router*, not the collapse mechanism, so the collapse
  site is unconfirmed here). **Named confirm/refute artifact: the lane-collapse site in the
  `plan-marshall` lifecycle workflow — find it before scoping.** The rest of the mechanism stands
  regardless of where the collapse lives.
  ⭐ **Their generalisation is the keeper and is broader than the bug:** *"when a lane collapses a phase,
  the collapsing lane owns that phase's OUTPUTS, not just its skip."* ⇒ **Audit what ELSE
  `phase-2-refine`'s persist step produces** — `scope_estimate`, `track`, `track_reasoning`,
  `compatibility`, `simplicity`, `domains`, `qgate_pending_count` are all persisted alongside `pr_title`
  in the same step. **`pr_title` is the one that trips a blocking gate; the others may be silently absent**,
  which is the worse failure. ⚠ **This is a third lane defect** (cf. shipped PLAN-101 lane-router-reads-
  the-wrong-body, and RUNNING PLAN-57 lane-router-scale-blind) — the lane machinery is a defect cluster,
  not three coincidences. **Source: API-Sheriff round-5 #5.**
- ⛔ **A FINDING AGAINST THIS ORCHESTRATOR — AND WE COMMITTED IT THE SAME DAY, WORSE THAN THE INSTANCE
  REPORTED.** Round-6 #1: PLAN-15's staged spec carried three `OBSERVED` claims that were all wrong (an
  "inert" knob that had *zero* read sites, a named resolution site that was a **log helper**, and a
  deliverable that was **unimplementable as written**). The labels were applied — and applied **wrongly**:
  plausible inferences serialized as OBSERVED. ⭐ Their framing is exact: **`OBSERVED` suppresses the check
  that would have caught the error**, so the failure is silent by construction and *the safeguard is the
  thing bypassed*. Refine/outline caught all three — the system worked **despite** the label, not because
  of it.
  ⛔ **SELF-APPLIED, and we fared worse.** `PLAN-TRUTH-021`, staged by this orchestrator hours earlier,
  carried **seven** `OBSERVED` labels of which **five were not earned by any read of the tree** — they came
  from inbox message `-013` and the operator's report. Corrected in place:
  - two relabelled **REPORTED (not orchestrator-verified)** with confirm/refute artifacts named;
  - one relabelled ⛔ **HYPOTHESIS** — *"#1066's footprint touches no `phase-1-init` file"*, an **asserted
    ABSENCE**, which the Verify-First Contract names as the higher-risk half. **It was settleable by one
    `git show --stat d04ac98ed` that was never run.**
  - one was **incoherent**: `OBSERVED: tests under test/plan-marshall/**` — a **future artifact**, asserting
    a read of something not yet written.
  ⇒ Adopted verbatim: **OBSERVED only when verified against the tree during that decompose pass**; prefer
  `architecture find --pattern` over a remembered line number (**line-number citations decay fastest** —
  their `RouteTableBuilder.java:285` is the case in point); and for a deliverable asserting a capability,
  name the invariant that would prove it so *"unimplementable as written"* surfaces at authoring time.
  **Source: API-Sheriff round-6 #1.**
- ⛔ **ROUND-6 #5 IS REFUTED AS DIAGNOSED, IS A DUPLICATE OF ROUND-2 #13, AND THE REAL MECHANISM IS OUR OWN
  ARCHETYPE.** They report `manage-tasks` rejecting `deliverable: 0` as a missing field and diagnose *"the
  guard tests truthiness rather than presence"*, proposing `if "deliverable" not in payload`. ✅
  **ORCHESTRATOR-VERIFIED AT SOURCE, and the diagnosis does not hold:**
  - `_tasks_core.py:278` **already tests presence** — `if 'deliverable' not in task:` — so their proposed
    fix is what the code does today and **would find nothing to change.**
  - `:279` then **defaults an absent deliverable to `0`**.
  - `:536-537` raises `Missing required field: deliverable` when `deliverable == 0 and origin !=
    'holistic'`.
  ⭐ **So the real mechanism is sharper than either their version or round-2 #13's:** the defaulting step at
  `:279` **erases the distinction between ABSENT and EXPLICITLY-ZERO**, and the guard at `:536` then reports
  the merged state with a message that is *accurate for absent* and *false for explicit-0* — by which point
  the two are indistinguishable **because `:279` destroyed the distinction.**
  ⛔ **That is this epic's own which-kind-of-zero archetype**, the same defect #1064 shipped a fix for in
  `inbox_state` (empty vs missing vs unreadable). ⇒ The fix is **not** a presence check: it is to stop
  collapsing absent into `0` (use a sentinel/`None`), **and** to make `:536`'s message name the real
  `origin: holistic` precondition. Round-2 #13 correctly caught the misleading message but treated it as
  the defect; the defect is upstream.
  ⚠ **They could not have deduped this** — they record round 2's titles as unrecoverable. **Second dedup
  service we can render that they cannot.** ⚠ And it is the **second** hand-off this session whose proposed
  fix would have found nothing in source (after `--enabled-bots`): a correct symptom, a wrong mechanism, a
  fix aimed at a site that does not have the defect. **Source: API-Sheriff round-6 #5, deduped onto
  round-2 #13.**
- ⛔ **A CLEAN AUTO-MERGE FROM A SIBLING LANDING CAN FALSIFY ASSERTIONS WITH NO CONFLICT TO REPORT — AND
  OUR FILE-BASED DISJOINTNESS CHECK CANNOT SEE IT.** Round-6 #2: PLAN-33 (#131) landed while PLAN-15 was in
  finalize; the textual conflict was small and resolved normally, but **four assertions and doc claims
  auto-merged cleanly while becoming false** — asserting `400` where the sibling had moved the behaviour to
  `413`. Git had nothing to report: both sides were textually compatible, **only the meaning diverged**.
  **Two of the four sat outside both local gates** and would have failed first on containerised CI.
  ⭐ *"The cleaner the merge, the more complete the illusion."*
  ⛔ **This is addressed to US as much as to finalize.** They say it plainly: *"a disjointness check that
  only counts FILES cannot see this class"* — and note the epic that hit it already had a re-verify rule
  that would have caught the **surface size** but **not the falsified assertions**. Our own emit-time
  disjointness is exactly a file/module-surface check.
  ⇒ Treat a sibling landing on a **contended** surface as a first-class finalize trigger, not an ordinary
  rebase: **enumerate the sibling's semantic change set** (which literal values, statuses, names changed)
  and grep the local branch for every restatement — assertions, fixtures, comments, every doc layer —
  **independent of whether git reported a conflict.** **Source: API-Sheriff round-6 #2.**
- ⚠ **ADR NUMBERS ARE A SHARED MUTABLE RESOURCE ALLOCATED BY A READ-MODIFY-WRITE WITH NO LOCK.** Round-6
  #3: an ADR number went stale **six times in four days — every single time it was written down.** `0021`
  and `0022` consumed by one plan, `0023` by another, `0024` by a third **on an unmerged branch**, so
  `main` did not show it while it was already spoken for. ⭐ **Reading `main` alone is not sufficient** —
  the next free number must account for open branches, which is exactly how `0024` would have been
  double-allocated. ⇒ Do not bake a concrete ADR number into an outline or deliverable text; refer by
  slug/title until the file is written. Re-run the free-number check **immediately before writing**, treat
  allocation as claimed only once the file exists, and consider **open branches, not just the default
  branch**. **Source: API-Sheriff round-6 #3.**
- ⛔ **A CANONICAL VERIFY STEP EXISTS IN THE VOCABULARY BUT IS SILENTLY WITHHELD FROM THE MENU, SO NO PLAN
  IN THAT REPO HAS EVER RUN ITS IT SUITE PRE-PUSH.** Round-6 #7 (their numbering skips — see the note
  below): `default:verify:integration-tests` is a first-class step in the bundle, yet
  `manage-config list-verify-steps` returns only three (`quality-gate`, `module-tests`, `coverage`).
  Per `marshall-steward/references/wizard-flow.md:351-361` the offered set is derived from discovered
  architecture — and **the profile IS declared, in a CHILD module** (`integration-tests/pom.xml:214`, with
  `maven-failsafe-plugin` at `:232`), **not the root pom.** Discovery appears to look only at the
  aggregator, so a module-scoped IT profile is invisible.
  ⭐ **The doubly-silent part is the finding:** the step is not *misconfigured*, it is **absent from the
  menu**, so the operator sees a complete-looking three-step selection with **no signal a fourth was
  suppressed**. Only comparing the bundle's step vocabulary against `list-verify-steps` reveals it, which
  nobody does routinely. Concrete cost already paid: an IT shipped with a `ClassCastException` that a local
  IT run would have caught.
  ⭐ **Credit their own scoping discipline — they checked the blast radius and refused to overclaim:**
  `architecture commands` resolves seven canonicals and withholds **both** `integration-tests` and
  `arch-gate` for the same reason, **but they are not equally severe.** `integration-tests` leaves a whole
  suite unrun; `arch-gate` is *largely cosmetic here* because ArchUnit is an ordinary JUnit test that
  already runs inside `module-tests` (verified by them: `-Dtest=FrameworkAgnosticArchTest` → exit 0 in
  13 s) — what is lost is only the per-deliverable wrapper emitting `arch-constraint` findings into triage,
  i.e. **integration, not enforcement.** They also state plainly that configuring the step would **not**
  have caught their epic's headline regression.
  ⛔ **DIAGNOSIS RETRACTED BY THE SENDER (round-6 addendum, item A) — DISCOVERY IS NOT THE FAILURE.**
  `architecture resolve --command integration-tests --module integration-tests` **succeeds**, returning a
  correct executable with `resolution_level: module` and `bash_timeout_seconds: 480`. The command is
  found, correct, and sensibly configured. It simply resolves at **module** scope and not at **whole-tree**
  scope (`--command integration-tests` with no `--module` → `Command not found`). ⇒ **The "child-module
  discovery" corrective above would fix nothing.** Struck.
  ✅ **THE ACTUAL DEFECT — TWO BUNDLE RULES CONTRADICT, LEAVING THE STEP UNCONFIGURABLE BY ANY LEGITIMATE
  ROUTE. Orchestrator-verified verbatim at HEAD:** `phase-5-execute/standards/canonical_verify.md:46`
  reads *"Whole-tree gates (e.g. `integration-tests`, `e2e`) live only in `verification_steps`, never in
  `per_deliverable_build`"* — naming `integration-tests` as its own example. But `verification_steps`
  requires whole-tree resolution, which this canonical does not have, so `set-steps` refuses it with
  `missing_order`. **The one list the standard permits will not accept it; the list that would accept it is
  prohibited.** An ordinary multi-module layout (IT suite in a dedicated module) cannot enable the step at
  all.
  ⇒ **Replacement correctives:** (1) **let a whole-tree canonical delegate to the single module that
  provides it** — when exactly one module exposes `integration-tests`, root-scope resolution should resolve
  through it rather than returning *Command not found*; this is the fix that unblocks the layout. (2)
  **Make suppression visible** — `list-verify-steps` should report withheld canonicals with the reason
  **and the module that does provide them**. Here it returned a clean-looking three-step menu while a
  fully-resolvable command sat **one scope away**.
  ⚠ **Two smaller corrections from the addendum (item D):** `default:verify:compile` is **NOT** missing —
  it is configured in `per_deliverable_build`; only `arch-gate` and `integration-tests` are genuinely
  absent. And `arch-gate` resolves on **no** module at all, with `architecture enrich` offering **no verb
  to declare a command** (its verbs cover skills, dependencies, tips, insights, best practices, domains) —
  so it is genuinely unavailable, but **rank it well below `integration-tests`**, which leaves a whole
  suite unrun.
  ⭐ **Keep the retraction visible rather than rewriting history**: the original diagnosis was plausible,
  specific, and wrong, and the sender caught it themselves within hours. **This is the second hand-off
  diagnosis this session that would have sent a fix at a site with no defect** (after `--enabled-bots`) —
  and the third if round-6 #5 is counted. **A corrective is a HYPOTHESIS until the named site is read.**
  **Source: API-Sheriff round-6 #7, as corrected by its addendum items A/B/D.**
  ⚠ Round 6 says "six findings" and ships **seven**, numbered 1,2,3,4,5,**7**,6 — a document miscounting
  and misordering itself. Third instance of *a document's own summary of itself can be stale* (round 3 said
  three and carried five).
- ⛔ **`manage-config` ACCEPTS A PLACEMENT ITS OWN STANDARD FORBIDS, AND THE ACCEPTED VALUE WOULD HALT
  PLANS — VERIFIED AT SOURCE.** Round-6 addendum item C, and the sharpest finding of the whole API-Sheriff
  series so far. ✅ **ORCHESTRATOR-VERIFIED**: `_config_defaults.py:691` `validate_per_deliverable_build`
  documents exactly three checks — *"if `value` is not a list, if any entry is not a
  `default:verify:{canonical}` string, or if a retired enum string is supplied"* — and **no whole-tree /
  module admissibility check**. So `default:verify:integration-tests`, a well-formed step ID, is **accepted
  into `per_deliverable_build`**, the one list `canonical_verify.md:46` explicitly forbids it from.
  ⛔ **The accepted value is not merely wrong — its FIRST USE is a hard stop.** `per_deliverable_build`
  resolves **per changed module**; `integration-tests` resolves on no other module; and
  `canonical_verify.md`'s exit-code convention is explicit that `exit_code != 0` means **STOP and return an
  error**, with *"log and continue"* named as a **prohibited anti-pattern**. ⇒ A deliverable touching only
  the ordinary source module — **the overwhelmingly common case** — halts the plan.
  ⭐ **Why this is the sharpest instance: it is our theme in the WRITE direction.** Nearly every instance we
  hold is a *read* reporting false confidence. This is a **write silently accepting something whose only
  possible outcome is failure**, with the failure landing **far from the edit, in a later phase of an
  unrelated plan**. A config layer that cannot refuse an impossible value is worse than one with no
  validation, because the successful `status: success` is itself the false signal.
  ⇒ Reject whole-tree-only canonicals in `per_deliverable_build` **and** module-only canonicals in
  `verification_steps` — the two lists have **different admissible sets** and only the shared shape is
  enforced. ⭐ Their implementation note is exactly right and costs nothing: **the validator already knows
  the step ID, so resolving `architecture resolve --command {canonical}` with and without `--module` is
  sufficient to classify it at write time.** ⚠ Also worth taking: consider whether the exit-code convention
  should distinguish *"this canonical does not apply to this module"* from *"this build failed"* —
  **treating an inapplicable canonical as a hard stop is what turns a config mistake into a plan outage.**
  **Source: API-Sheriff round-6 addendum item C.**
- ⛔ **"A RULE ENFORCED BY PROSE IS NOT ENFORCED" IS NOW A POPULATION, NOT AN OBSERVATION — THREE UNRELATED
  SURFACES IN ONE DAY.** Recorded as a standing pattern because the third instance arrived while the first
  two were still open:
  1. **Inbox `append-only`** — enforced by prose only, and **breached once** (already in this ledger).
  2. **Bot participation / in-place edits** — `bot-participation-contract.md:115-121` specifies
     `updated_at` movement, while `review_completeness.py` contains **no timestamp logic at all**; the
     determination is made upstream by an agent reading the doc (round-5 #2, forwarded).
  3. **Whole-tree vs module canonicals** — `canonical_verify.md:46` makes the distinction load-bearing;
     `validate_per_deliverable_build` checks only the shared shape (round-6 addendum C, above).
  ⭐ **The shape is identical each time: a standard states an invariant, no code reads it, and the
  violation is accepted with `status: success`.** ⇒ This is a **detector-shaped** problem, not three fixes:
  a normative statement in a standards doc that names a machine-checkable distinction should have an
  enforcing call site, and the absence of one is findable. ⚠ Candidate scope for a future plan — **derive
  the population first**; three instances found incidentally are a **sample**, and this epic has been
  wrong about exactly that three times today. **Source: synthesis across round-5 #2, round-6 addendum C,
  and the standing inbox item.**
- ⚠ **`allowEmptyShould(true)` MAKES AN ARCHUNIT GATE PASS FOREVER WHEN ITS PACKAGE PATTERN MATCHES ZERO
  CLASSES — vacuous-guard family n=9, with a NEW mechanism.** Round-6 addendum item E, offered as guidance
  rather than a bundle defect, for `pm-dev-java:arch-gate-java`. A renamed package or one misspelled entry
  reduces the gate to a **no-op that stays green**, and *"the failure mode is indistinguishable from
  success."*
  ⭐ **This is a genuinely new mechanism for the family.** Our other eight instances are *unreachable
  predicate* vacuity — a guard whose condition can never be true. This is **empty-domain** vacuity: the
  predicate is fine, the **set it quantifies over is empty**. A detector built for the first shape would
  not find the second.
  ⭐ **And their caution about the naive fix is worth more than the finding**: the natural formulation
  `classes().that().resideInAPackage(p).should().bePublic().orShould().bePackagePrivate()` looks
  universally true but **rejects private nested classes**, so the guard fails **for a reason unrelated to
  the gap it was added to close** — a fix that fails for the wrong reason is indistinguishable, in CI, from
  a fix that found something. A **direct count of imported classes per package** is the reliable form.
  ⚠ Note the negative-control trap they name: a control exercising its **own hardcoded package** proves the
  *mechanism* fails on a violation while saying **nothing about whether the protected list still
  resolves.** ⇒ Add to `arch-gate-java`: *an arch-gate rule must be proven to fail, and
  `allowEmptyShould(true)` on the primary rule is the standard way it silently stops doing so.*
  **Source: API-Sheriff round-6 addendum item E.**
- ⛔ **A SHARED-NAMESPACE IDENTIFIER COLLISION IS INVISIBLE TO TEXTUAL CONFLICT DETECTION — AND OUR LESSON
  IDS ARE IN THE FAMILY.** Drained `code-intelligence-substrate-010` §1. While their #1067 sat in the merge
  queue, upstream #1066 landed `doc/adr/012-….adoc`; #1067 held its **own** `012-….adoc`. **Both signals
  said clean and both were CORRECT** — `baseline-reconcile` reported `classification=no_overlap`, the
  rebase applied with no conflict — **because the two filenames differ, so there is no textual overlap.
  The collision is in the NUMBER**, a semantic property of the filename prefix, not of the bytes. Caught by
  **manual inspection one minute before the merge would have completed**, after the merge lock was already
  held; ~90 minutes to recover.
  ⭐ **THE KEEPER RULE:** ***`no_overlap` from a textual reconciler is a statement about BYTES, not about
  MEANING.*** A clean rebase is not evidence that two branches did not claim the same name.
  ⭐ **The class, and it reaches us directly:** anything drawn from a **monotonically-allocated shared
  namespace** — ADR numbers, migration numbers/timestamps, reserved error codes, `NNN`-prefixed document
  sets, and ⛔ **lesson ids allocated `YYYY-MM-DD-HH-NNN`, where two plans finalizing in the SAME HOUR
  collide identically.** That is our surface, and today four plans finalized within hours of each other.
  ⭐⭐ **This CORROBORATES AND EXTENDS API-Sheriff round-6 #3** (ADR numbers stale six times in four days;
  `0024` consumed on an unmerged branch). Two unrelated repos, same defect class, inside one day ⇒ a
  population, not two incidents. **And it corrects the fix location:** round-6 #3 proposed "consider open
  branches"; this shows the check must run **at the pre-merge barrier on the ACTUAL merge base**, because
  allocation-time scanning (`adr-propose` at 11:56) is stale by merge (15:02) — the base moved **three
  times** in between. ⇒ A namespace-collision probe taking a descriptor (directory + filename-prefix
  pattern) registers migration numbers and lesson ids with no new code. **Source: `code-intelligence-substrate-010` §1
  + API-Sheriff round-6 #3.**
- ⛔ **A WAIT THAT CANNOT OBSERVE ITS TARGET REPORTS AS AN ORDINARY TIMEOUT — AND I HIT THE SAME DEFECT
  MYSELF THIS SESSION.** Drained `code-intelligence-substrate-010` §2. Two monitors, both **structurally
  blind**, both reporting `[Monitor timed out — re-arm if needed.]` while **the awaited condition had
  already occurred**: one polled for `status: available` when the lock store emits `status: free`; the
  other invoked `pr view --pr-number` when **that verb takes `--head`**.
  ⭐ **The two failure modes are operationally OPPOSITE and textually IDENTICAL:** *"I waited and it did not
  happen"* (real information — re-arm) vs *"I cannot observe it at all"* (a watcher defect — re-arming
  guarantees a repeat). **Both emit the same string**, and silence reads naturally as progress. Cost: the
  plan stalled and the operator issued **six bare `retry` turns**, manually driving restarts the monitoring
  layer should have surfaced.
  ⭐ **Independent confirmation from this orchestrator, same day:** I invoked `ci pr view --pr-number 1065`
  and got `error: unrecognized arguments`, then noted the help text **advertises `--pr-number` while the
  parser rejects it**. I recorded it as a doc/argparse mismatch. **Their §2 shows the real consequence is a
  structurally blind watcher** — so my severity read was too low, and the item is now folded into
  PLAN-TRUTH-012 ranked above a plain doc mismatch.
  ⭐ **Keeper rule:** ***a wait that cannot observe its target is not a wait, and must not be reported as
  one.*** ⇒ Validate at arm time (resolve the probe through the same argparse surface the executor uses;
  reject an unrecognised flag **before** arming), check the match token against the producer's declared
  value set (the lock store's status enum is closed and `available` is not in it), and give a blind watcher
  a **distinct terminal event** — `[Monitor could not observe its target — probe invalid]` is actionable,
  `[Monitor timed out]` is not.
  ⭐⭐ **The synthesis the sender flags is the real content, and it now spans four surfaces:** *a taxonomy
  that collapses "not yet" into "never, given this configuration" destroys the one bit that determines what
  to do next.* Instances: this monitor pair; the `hard_quota`-vs-size-cap misclassification; the awaitable-
  vs-hard rate-limit window (`review_rate_window_await=false`); and a rate-limited bot's `comments_found: 0`.
  **Source: `code-intelligence-substrate-010` §2.**
- ⚠ **DRAIN RESIDUE — five items recorded here rather than staged, so they are not lost in landing files.**
  From the 2026-07-30 drain of 40 messages (dispositions in `logs/decision.log`):
  1. **`manage-logging` fragments a multi-sentence decision message into four unattributed fragments plus
     the real entry** (`plan-203-…-010`). ⚠ **Directly corrupts this orchestrator's own audit trail** — the
     decision log is where every drain disposition is recorded, and this session wrote ~15 long messages.
     **Candidate for staging; not staged, to avoid answering a cleanup request with more plans.**
  2. **PLAN-202's D3 gap is real and owed** (`compose-time-…-005`): `decision-rules.md` states normatively
     that *every* subtraction is reported, but two phase-5 sites emit only a decision-log line with **no
     compose-result record**. Named in the doc, not hidden — but open.
  3. **`sonar-roundtrip.md` points at a `sonar_project_key` config surface that does not exist**
     (`compose-time-…-007`) — a doc-contract divergence with a concrete fix.
  4. **`config_hash` drift fires at EVERY phase boundary, so the warning has no discriminating power**
     (`compose-time-…-012`) — a signal that always fires carries no information; the vacuous-guard family
     in its always-true form rather than its never-true form.
  5. **The chat-signal pre-pass reports `no_signal: false` while retaining 2 of 664 turns**
     (`plan-less-…-013`) — **a thin retention is indistinguishable from a real extraction.** Same
     which-kind-of-zero shape as `inbox_state`, in the retrospective's input path.
  ⚠ Also recorded, needing a check rather than a fix: **`plan-less-…-009`** (*a footprint resolver that
  falls back to empty turns an unmeasurable check into a confident failure verdict*) may be **the same site
  #1066 fixed** (`None` vs `[]` in `_resolve_footprint`) **or a second one** — verify before scoping. And
  **`plan-less-…-010`** reports the finalize ceremony pre-filter still dropping security-audit on phase-4
  placeholder inputs *never reconciled against the realized run*, which **PLAN-112 (#1055) was supposed to
  close** ⇒ possible **partial fix recorded as a fix**, this epic's own archetype.
- ⛔⛔ **THE LANE / CEREMONY / SCOPE-GATE FAMILY IS THIS PROJECT'S PRINCIPAL SECURITY-GATE SUPPRESSION
  SURFACE — three plans now establish it, and #1068 supplied the concrete casualty.** A **ReDoS
  (CWE-1333)** shipped in `_PATH_RE`, running unbounded over the ingested `request.md` at `phase-1-init`:
  **~3 s at 20 KB adversarial input, 145 s at 10 MB.** ⭐⭐ **It was caught by the finalize security audit —
  the step the `minimal` posture would have dropped**, which is PLAN-57's own thesis demonstrated on
  itself.
  | Plan | Established |
  |---|---|
  | PLAN-112 (#1055) | the ceremony pre-filter **could** drop the security audit |
  | PLAN-202 (#1066) | a scope gate **silently reversed an explicit operator override** |
  | PLAN-57 (#1068) | a wrong narrow verdict **would have suppressed a real CWE-1333** |
  ⇒ **Stop treating these as routing-correctness bugs.** Three independent plans, three mechanisms, one
  consequence class. **Rank the family by that consequence, and never let a "cost optimisation" framing
  decide a gate that guards a security sweep.** **Source: #1068 landing.**
- ⭐ **TWO COMPONENTS THAT MUST AGREE SHOULD BE MADE TO AGREE BY CONSTRUCTION — #1068 needed three
  attempts to learn it.** Its gate **re-derived a subset of the sensor's rules and drifted twice** (first
  `scan_incomplete`, then `fan_out_marker`). The first two fixes **re-stated the rules**; the third made
  the detector **call `classify_scope_pure` and consume its band**, so gate and sensor became **one
  decision by construction**.
  ⭐ **That is the difference between fixing the instance and fixing the defect**, and it generalises to
  every duplicated-authority item this epic holds — the `epic.md` Decisions list vs `logs/decision.log`,
  the Ordered Queue vs `status.json`, the bot-participation contract vs the code that ignores it.
  ⇒ **Where a copy exists, the fix is to delete the copy, not to synchronise it.** **Source: #1068.**
- ⛔ **ARCHETYPE KNOWLEDGE DOES NOT TRANSFER BY EXPOSURE — #1068 reproduced a bug MINUTES AFTER ITS AUTHOR
  READ THE FIX.** Five instances of one archetype in a single plan, **two created by the plan itself**:
  `_GLOB_RE`'s `**` matching markdown bold; the `epic:` metadata key; a sweep harness vacuous in every
  worktree; ⛔ **an ad-hoc checker that reproduced the bug minutes after the author read its fix**; and an
  unreachable safety net.
  ⭐ **Keeper rule, the plan's own words:** ***any path-part skip-list is guilty until shown to scan.***
  ⭐ **And the fourth instance is the one that matters for how this epic invests**: it is the strongest
  evidence yet that **reading an archetype does not confer immunity to it** — which is the argument for
  *mechanical detectors* over *documented rules*, and a direct data point for PLAN-90's finding that the
  lessons corpus is written and never read. Vacuous/empty-match family **n≈13**. **Source: #1068.**
- ⛔ **THREE INDEPENDENT REVIEW-REFRESH ROUTES, NONE FUNCTIONAL — and one returns `success` for a no-op.**
  #1068 merged with the **required bot's review one HEAD stale** (finding `ea33a6`), operator-accepted
  because no refresh path exists: `/review` got **no response in 449 s**, **`ci pr ready` returned
  `success` but was a no-op**, and the CI abstraction has **`pr close` with no `pr reopen`**.
  ⭐ **The middle one is ours and is the epic's theme inside the CI abstraction itself** — a verb that
  reports success for an operation it did not perform. ⇒ **Routes to `review-apparatus`** with the
  no-op-success half flagged as a `tools-integration-ci` correctness defect rather than a review-policy
  gap. **Source: #1068.**


## ✅ Resolved / retracted — compacted 2026-08-08, retained as the record

These six entries are settled. They are kept because each one records a **correction**, and this epic's
whole subject is that a settled-looking record can be wrong; deleting them would remove the evidence that
the correction happened. They are collapsed here so the live-defect list reads as live defects.

- ✅ **RETRACTED 2026-08-08 — "PLAN-TRUTH-044 is running without a plan directory / work at risk"
  WAS MY ERROR, not a defect.** ⛔ **A running plan's directory lives INSIDE its worktree**, at
  `.plan/local/worktrees/{plan}/.plan/local/plans/{plan}/`, and is moved back to the main checkout
  at finalize via `integrate_into_main integrate`. I enumerated only the MAIN checkout's
  `.plan/local/plans/`, found nothing, and reported an absence. Verified on disk 2026-08-08:
  TRUTH-044's plan dir is present in its worktree at phase `6-finalize`, the tree is clean, and the
  branch carries 2 commits. Nothing was ever at risk. ⭐⭐ **THIS IS STANDING CORRECTION C5 FIRING
  AGAINST ME IN THE SAME SESSION I INVOKED IT**: I sent `review-apparatus` a message whose whole
  point was *"an unverified absence produces work against a surface that already exists — verify an
  absence against the right surface"*, and then filed exactly that error about my own epic within
  the hour. ⇒ **A plan's on-disk state is checked in BOTH locations: the main checkout AND the
  worktree. A main-checkout-only enumeration cannot distinguish "no such plan" from "plan is
  running".**

- ✅ **RESOLVED / no longer tracked**: the `:0Nd` minimum-vs-exact width doc defect (shipped in
  #1058); the `check-artifact-consistency` Recall-0% and token-accounting items (forwarded to the
  sibling as `truthful-signals-014.md`, their PLAN-122/124).

- ✅ **A `kind=landing` message is emitted PRE-MERGE and can assert a landing that has not happened —
  CONFIRMED INDEPENDENTLY BY US THIS SESSION, on the very turn the finding arrived.** Drained
  `code-intelligence-substrate-009`. Their instance: `audit-report-path-ignores-plan-dir-001.md` opened
  *"## What landed — PR #1063"* at 08:05:20Z while #1063 was **open**, verified three ways across two
  sessions; it merged later as `d0da6742d` and the content then proved **entirely accurate**. ⭐ *"The
  message was not wrong. It was early, and it was written in the past tense."*
  ⭐ **Our own fourth instance, found the same day:** `plan-less-pr-can-be-opened-but-never-corrected-001.md`
  claimed *"PR: #1065"* under "What landed" — `ci pr view --head` returned `state: open`,
  `merge_state: unstable`, `review_decision: none`, and #1065 is absent from `origin/main`. **PLAN-115 was
  NOT transitioned to shipped**; only its `pr` field was stamped.
  ⇒ **FOLDED, not staged: the defect is already owned as `review-apparatus`'s PLAN-PR-010** (transferred
  from our PLAN-100). ⚠ Their routing note argues it belongs here because the emission site is
  finalize/inbox rather than a PR surface — a defensible read, but the *work* is already staged there, and
  filing it again would duplicate an owned item. The corroboration was forwarded in
  `truthful-signals-005` instead.
  ⛔ **One scoping consequence for PLAN-PR-010, sent to them:** the message does not merely *omit* an
  outcome — it **asserts a landing in past tense**, so a consumer reading the prose rather than the PR
  state concludes wrongly. **The fix must change the claim, not only append an outcome field.** ⚠ Their
  own caveat is the sharpest part and must survive re-scoping: *check whether the emission site can even
  see the merge outcome from where it sits — if it structurally cannot, the fix is an ORDERING change, not
  a wording change.* **Source: API-Sheriff-adjacent via `code-intelligence-substrate-009`.**
- ✅ **ROUND-5 #1 IS A RECURRENCE OF TWO ACTIVE LESSONS — but its population is WIDER than either records.**
  Their observation: `build-maven`'s adaptive timeout killed a **green, unfinished** quality gate at 325 s
  (a re-run at `--timeout 600` completed green), and the outer envelope reported the kill as
  **`exit_code: -1` / `duration: 0`** — indistinguishable from a harness failure that never started, two
  conditions with **opposite remedies**.
  ✅ **DEDUP RESOLVED AGAINST OUR CORPUS, which they could not see:**
  - `2026-07-16-16-003` (`build-maven`, active) — *"run defaults to an adaptively-lowered subprocess
    timeout that silently kills long builds — the script-level `--timeout` binds, not the Bash timeout."*
    **That is their first half, already filed.**
  - `2026-07-27-00-001` (`build-server-client`, active) — *"Routed builds misreport their own outcome:
    `--timeout` silently discarded, **duration zeroed**, and a daemon wait-expiry reported as a hard
    failure over a child that passed."* **That is their second half, already filed — same signature.**
  ⭐ **BUT THIS IS NOT A CLEAN DEDUP, AND THE DIFFERENCE IS THE VALUE.** Our envelope lesson is scoped to
  **`build-server-client` (ROUTED builds)**; their instance is **`build-maven` direct**. ⇒ **The same
  misreport signature exists in a SECOND producer**, so the population is wider than either lesson states.
  **A reported instance is a SAMPLE** — the rule this epic keeps re-learning, now applied to our own
  corpus rather than to an incoming finding.
  ⚠ Also adjacent and worth carrying: `2026-07-22-01-001` — *"a value read from a self-rewriting learned
  store is not ground truth — outline cited an adaptive timeout that was already stale at Q-Gate time"* —
  which is the **adaptive-estimate** half of their finding, i.e. why the first run of a new change class is
  systematically under-budgeted. ⇒ Owed: report a timeout kill **as a timeout**, with the applied budget
  and elapsed time; consider a floor, or one automatic retry at a raised budget when the cause is a
  timeout rather than a failure. **Source: API-Sheriff round-5 #1.**
- ✅ **`keyword_drift`'s "expected false positive" framing should be re-examined — the recurrence says we
  normalised a defect.** `plan-203-…-009` reports the Q-Gate `keyword_drift` check *"searches a haystack
  narrower than the deliverable it checks, so it emits confident false positives."* ⚠ **We already hold this
  as ACTIVE lesson `2026-07-16-12-001`**, whose disposition is *"expected false-positive, resolve
  taken_into_account."* ⇒ **Deduped, but the dedup is the finding**: a defect that recurs while its lesson
  tells readers to accept it has been **normalised rather than fixed**, and "confident false positive" is a
  stronger claim than "expected". **Re-rank it rather than closing it again.**
- ✅ **CREDIT WHERE IT IS DUE — a stale-but-honest stamp was PRESERVED rather than refreshed.**
  `finalize-step-simplify` and `finalize-step-security-audit` were not re-fired after #1068's loop-backs,
  and **their stamps honestly name the older trees they validated.** The operator declined to re-stamp
  them to look current. ⭐ **This is the first time in the series a stamp was left truthfully stale**, and
  it is exactly the behaviour this epic exists to produce. **Record it as the positive control**: the
  archetype is not "stamps go stale", it is "stamps get refreshed to look current without re-running the
  thing they attest".
  ⚠ Alongside it, two genuine gaps from the same run: **`finalize-step-preference-emitter` was SKIPPED,
  not clean** (executor notation unresolvable, no aggregation ran) **while the plan carried 12 FIX
  dispositions concentrated in two modules that plausibly crossed the promotion threshold** — a skipped
  aggregation reported in the same shape as a clean one; and the **coverage check reporting 0% recall from
  a worktree `branch-cleanup` deleted a step earlier**, which is the **third independent observation** of
  an item already open here ⇒ **settled as structural, not incidental.**
  ⚠ The **three disagreeing phase-6 token totals (6× spread, no partial marker)** are the **third**
  instance of the ledger-disagreement item already forwarded to `code-intelligence-substrate` — record the
  recurrence there, do not re-file. **Source: #1068.**

## ⛔ Cross-epic plan-ID allocation — RETIRED for new work as of 2026-07-30

> Relocated 2026-09-05 — the allocation scheme is RETIRED for new work; the band-invariant record is history, not policy. 117 lines.


⭐ **THE BAND IS NOW LEGACY-ONLY. Everything below this block is history, kept because the reasoning is
the durable part — do not act on it for a new plan.**

Every staged plan in this epic was re-issued on 2026-07-30 as **`PLAN-TRUTH-{NNN}`**, and **all new
work takes that form** (next free: `PLAN-TRUTH-020`). All three epics have now converged on
epic-scoped ids — `TRUTH` here, `CIS` in `code-intelligence-substrate`, `PR` in `review-apparatus` —
so **a cross-epic numeric collision is structurally impossible** rather than prevented by a rule three
parties must remember. That removes the error class instead of adding a rule, which is exactly what the
"real fix is slug-scoped ids" note at the bottom of this section predicted.

⇒ **Consequences, all verified:**

- **`50-119` and `200-299` are no longer consumed by new work.** Only the surviving unprefixed rows
  (shipped / running / launched / superseded / transferred) still sit in them.
- **The TEN-id legacy carve-out inside the sibling's `1-49` block is CLOSED as a risk.** Nine were
  shipped and immovable; the tenth, PLAN-49, was the live collision — it is now `PLAN-TRUTH-015`.
- **`400-499` is FREE** — `review-apparatus` never staged a 4xx id and uses `PLAN-PR-NNN`.
- ⛔ **UPPERCASE is mandatory.** The grammar is `PLAN-{SLUG}-{DIGITS}`, `{SLUG}` = 2–8 uppercase
  alphanumerics. Verified live in both directions on 2026-07-30: `PLAN-TRUTH-018` returns
  `detection: orchestrated`; the lowercase `plan-truth-018` returns `detection: unrecognised_id`, which
  **silently detaches the plan from its epic** so it writes NO inbox message at finalize.
- ⛔ **Never rename a launched or shipped plan** — a running plan's `request.md` `source_id` is a
  persisted pointer to its spec path and nothing re-derives it.

⭐ **The lesson that outlives the band:** the flaw recorded below was not that the numbers were wrong.
It was that a **shared invariant enforced by convention** needs every party to re-read it, and one of
them silently did not. The fix was to make the invariant unnecessary.

### Historical record — the band invariant and its known flaw

Recorded here 2026-07-29 because it was previously carried in **only the sibling's ledger**, which is
exactly the fragility it is meant to guard against.

```text
code-intelligence-substrate  OWNS 1-49 and 120-199
truthful-signals             OWNS 50-119 and 200-299
```

⛔ **BAND EXTENSION 2026-07-29 — operator-approved.** `50-119` was **exhausted** the moment PLAN-119
was allocated; staging was hard-blocked until this extension. `200-299` is the first range
uncontested by the sibling's `1-49` / `120-199`. **Next free id: PLAN-201.**

⭐ **This extension is recorded in BOTH ledgers, and that is the whole point.** The original band fact
lived in the sibling's ledger ONLY, which is precisely how the citations to PLAN-61 / PLAN-64 /
PLAN-104 went stale unnoticed. A shared invariant stored in one place is not shared — it is a
single point of failure with a copy of the consequences in the other epic. Notified via
`truthful-signals-013.md`.

⚠ **An exhausted band gives no warning.** It presented as an ordinary staging request that could not
proceed. **Check remaining headroom when the band passes ~80% consumed**, not when the next id is
needed.

⛔ **LEGACY CARVE-OUT — this epic holds TEN ids inside the sibling's `1-49` block.** Found by a
consistency audit 2026-07-29, not by the invariant, which does not describe them:

```text
PLAN-27, PLAN-41, PLAN-42, PLAN-43, PLAN-44, PLAN-45,
PLAN-46, PLAN-47, PLAN-48   -> SHIPPED, immovable
PLAN-49                     -> STAGED, still allocatable elsewhere = COLLISION RISK
```

They are **inherited from the predecessor epic `plan-optimization`** (see `metadata.successor_of`) and
predate the band invariant, which was written as though it had always held. The nine shipped ids are
**permanent** — renumbering them would break every citation in nine landing reports and the PR record,
which is precisely the phantom-citation failure this epic already recorded twice.

⚠ **`PLAN-49` is the live risk**: it is staged, sits in the sibling's block, and nothing prevents that
epic from allocating the same number. Verified 2026-07-29 that it has **not** (0 matches for
`PLAN-27` / `PLAN-4x` in its queue). Notified via `truthful-signals-017.md`. **Either the sibling
reserves these ten, or PLAN-49 is renumbered before it launches** — it has exactly one inbound
citation (PLAN-203's Dependencies), so the renumber is still cheap. **It stops being cheap the moment
it ships.**

⛔ **CORRECTION 2026-07-30 — the remedy this section recorded DOES NOT EXIST.** Flagged by
`review-apparatus-001`/`-002`, operator-confirmed: **there is no verb that renames a plan onto a
different id.** "Renumber PLAN-49" was recorded here and in the resume anchor as an available action
for a full session, and nobody challenged it. ⇒ **Our own archetype, in our own ledger: a confident
instruction hiding an impossibility — and it was caught by a SIBLING reading our ledger, not by our
own review.**

✅ **The available remedy, from `review-apparatus-002`:** *a STAGED plan has no artifact to rename.*
PLAN-49 can be **re-issued as a new spec at a free id of ours (200-299) and its old row retired** —
that is a reissue, not a rename, and it needs no tooling that does not exist. Only a **launched or
shipped** plan is genuinely immovable. The one inbound citation (PLAN-203's Dependencies) must be
updated in the same move.

⭐ **`review-apparatus` takes NO id in any band** — it issues `PLAN-PR-NNN` (from `001`). Two
consequences recorded: **(a)** `400-499`, reserved for it in an earlier note, is **FREE** — the
reservation is struck; **(b)** ⛔ the five ids transferred out (PLAN-60, 100, 116, 117, 119) were
recorded here as **"NOT spent"** — **that was WRONG and is retracted**; their rows still occupy those
ids, so they are **permanently spent**. See the correction under "Transferred out". ⚠ **Trap if we ever adopt the scheme:** the
grammar is `PLAN-{SLUG}-{DIGITS}` with `{SLUG}` = 2–8 **UPPERCASE** alphanumerics and digits
mandatory; a lowercase token classifies as `unrecognised_id` and **silently detaches the plan from its
epic**.

⭐ **The general lesson, recorded because it will recur**: a numbering invariant written after the fact
describes the future, not the past. **Audit the existing population against a new invariant at the
moment you write it** — this one was violated by ten rows on the day it was recorded, and nobody
noticed for a full session.

**Why it exists:** the sibling allocated `PLAN-107`…`PLAN-111` at decompose while this epic already
held 107-111 — **five duplicate ids live across two active epics** — because it allocated without
reading the sibling queue. Repaired by renumbering. ✅ **Orchestrator-verified 2026-07-29: there is
currently NO id overlap between the two epics.**

⚠ **THE INVARIANT AS STATED IS ALREADY VIOLATED.** It assigns **1-49** to the sibling, but this epic
holds **PLAN-27 and PLAN-41–49** (shipped). No live collision exists — the sibling currently occupies
1-9 — but **the moment it allocates anywhere in 27 or 41-49 it collides with shipped rows here.**
⇒ **Treat the sibling's usable low band as 1-26, not 1-49**, until a better scheme lands.

⭐ **The real fix is slug-scoped ids** (`PLAN-CIS-01`), operator-directed: each epic numbers from 1
independently — no coordination, no band exhaustion, no cross-epic lookup before allocating. It
removes the error class instead of adding a rule someone must remember. ⛔ **Blocked on PLAN-114**,
because the detection regex silently rejects that shape today.

## Inbox drain — 2026-09-04 (b), `findings-from-cui-http.md`, 45 findings dispositioned

> Relocated 2026-09-05 — a completed drain is closed by definition; every message was dispositioned and archived. 65 lines.


**Drained at operator instruction.** ⛔ **`inbox list` never enumerated this file** — its name is not
`{sender}-{NNN}.md` — so it was dispositioned by hand and archived by hand. The archive landed **FLAT**
at `inbox/archive/findings-from-cui-http.md` (51,874 bytes, verified intact) rather than in a
per-sender subdirectory, because there is no sender segment to key on. ⚠ **A future
`inbox migrate-archive` will try to fold it under sender `findings-from-cui`; that is harmless but
should not be mistaken for a real sender.**

**What it is.** A consolidation relayed from the **cui-http** repository, aggregating **52 lesson
records** from the `quality-report-remediation` epic (19 plans, PRs #153–#186), 2026-08-26 → 09-01.
⛔⛔ **The source lesson records were REMOVED after it was written — this document is their sole
surviving record**, which is why it was archived rather than consumed and discarded.

### ⚠ Its own counts do not reconcile, and that is recorded rather than resolved

The header says **"8 themes / 27 findings"**. It enumerates **45** — derived by counting its `### N.M`
subsections: 7 + 9 + 6 + 4 + 4 + 5 + 4 + 6. Its per-theme *"N source lessons"* figures sum to **43**
(theme 8 states none) against a provenance of **52 minus 12 retained = 40**.

⭐ **Recorded, not resolved.** The findings themselves are first-rate and independently valuable; the
internal counts are not quotable. ⛔ It is this epic's own archetype appearing in a consolidation
document **one of whose eight themes is literally *"Which kind of zero is this?"*** and whose
cross-cutting observation #2 is about counts — which is a reason to take its content seriously, not a
reason to discount it.

### Dispositions over all 45

- **Theme 2 → TRANSFERRED** to `review-apparatus` as `truthful-signals-045.md`. Nine findings, 11
  source lessons, **the highest-cost theme in the corpus** — its own header records rate limiting as
  *"the single dominant cost of three consecutive plans."*
- **§7.3 → STAGED as `PLAN-TRUTH-137`** — a refuted spec claim has no write-back channel at the plan
  tier. ⭐ Chosen for a new spec because the gap is a **tier** gap with a landed precedent: the
  orchestrator tier already has `## Claim Labels` + `corpus set-verdict` and **it worked in this
  epic**; the plan tier has no equivalent, so an executing agent's refutation dies in a return payload
  while the false claim gains apparent corroboration at every restatement.
- **33 folded across 13 specs** — `-097` `-104` `-107` `-108` `-116` `-117` `-118` `-121` `-122`
  `-129` `-130` `-131` `-134`. Expected Surface updated on `-107`, `-116` and `-129`; unchanged
  elsewhere and each fold says so.
- **3 recorded ALREADY-COVERED and deliberately NOT folded**: §4.3 (a proposed fix that keeps the
  defect's own predicate) → lesson `2026-09-03-16-001`; §6.5 (a build-owned formatting concern is
  self-reverting) → lesson `2026-09-03-16-005`; ⛔ **§4.4 (a surfacer covering none of the changed
  content still records `done`) → `PLAN-TRUTH-126`, which is LAUNCHED** — folding into it would
  re-scope a live plan.

### ⭐⭐ The three things most worth carrying forward

1. **§1.1 rules out the obvious remedy.** Both existing argparse guards fire at the wrong time — one is
   edit-time, one is skill-body prose — and **four of five rejections came from the main-context
   ORCHESTRATOR**, the tier that demonstrably has the rule loaded. ⇒ neither a coverage gap nor a
   loading gap. *"Adding another restatement to the same skill body is the one remedy the evidence
   rules out."* And the consolidating session **produced six more rejections of the same class while
   writing the document.**
2. **§1.2 supplies a sixth recurrence signature that defeats the existing self-audit.**
   Cross-script verb misattribution — a **real** verb applied to the wrong script. The self-audit
   question *"is this verb real?"* returns **"real"** and waves it through. Also: **`--plan-id`
   position is per-VERB, not per-router**, which sharpens `-129`'s D2 from three per-script
   conventions to per-verb ones.
3. **§8.6 is a POSITIVE and it constrains `-104`.** `review_commitments reconcile` caught a simplify
   pass deleting a line that existed *because a reviewer asked for it*. ⛔ Read beside
   `review-apparatus-030` (the same verb returning `clear` over a zero population): **not a
   contradiction — the two halves `-104` must keep apart.** The empty-population fix must publish the
   population and report `indeterminate`, **never weaken or disable a guard with demonstrated catch
   value.**

## Inbox drain — 2026-09-04, 32 messages, every one dispositioned

> Relocated 2026-09-05 — a completed drain is closed by definition; every message was dispositioned and archived. 64 lines.


**Closure exact: 32 archived + 0 invalid + 0 archive_failed = 32 scanned.** The terminal zero is
**EMPTY** (`live_count: 0`, `closed_senders` empty, `invalid_count: 0`) — not FINISHED, not BLOCKED.

⚠ **The queue nearly doubled overnight, 18 → 32, and three of the four senders were new.**
`documented-invocations-cannot-succeed-as-written` (18, PLAN-TRUTH-101's own run),
`deployment-and-refresh-gaps` (4, Token-Sheriff relays),
`lessons-handling-26-09-04-01` (4, a Token-Sheriff lessons-consolidation epic — a sender type this
epic had not seen before), and `review-apparatus` (6).

⭐⭐ **The six `review-apparatus` messages are RESCUED DATA and the rescue is the lesson.** All six are
carried-out findings from `PLAN-PR-038` (PR #1388) that reached `resolution: pending` and were **never
promoted**, because *"the plan directory was archived before these findings had a carry-out route."*
That orchestrator recovered them by reading `.plan/local/archived-plans/…/artifacts/findings/`
directly. ⛔ **The data survives archival — only the ROUTE was missing.** Five folded into existing
specs and one staged.

**Dispositions: 25 folded · 3 staged · 3 discarded (2 transferred, 1 already-owned) · 1 promoted.**

**Three new specs**, all from defects with no existing owner:
`PLAN-TRUTH-134` (the scope extractor invents paths and drops bullets, and reports success) ·
`PLAN-TRUTH-135` (a lesson can be listed and neither read nor retired) ·
`PLAN-TRUTH-136` (the declared footprint cannot learn a path the outline did not predict).
Queue 181 → 184, appended with key-order and byte-identical-prefix assertions on both sides.

**25 folds across 17 specs**, every widening verified FROM THE PARSER: `-104` → 6 claimed paths,
`-116` → 7, `-117` → 4, `-119` → 6, `-121` → 8, `-129` → 8. ⛔ **Two folds DELIBERATELY added no
surface and say so**: `-106` and `-127` both want surface inside `manage-execution-manifest` /
`phase-5-execute`, which are claimed by the **LAUNCHED `PLAN-TRUTH-089`**. Adding them would
manufacture a collision against a live plan; both are marked for re-scoping after `-089` lands.

### ⭐⭐⭐ The drain corroborated one of this epic's own corrections, from the other side

On 2026-09-03 this epic **refuted** `dual-homed-...-011`'s request to add the four context-load columns
to `record-dispatch-boundary`, having checked at source that they were already declared and already
wrote `unmeasured` rather than `0`, and concluded the residue was a **call-site omission**.
`documented-invocations-...-006` reaches the identical conclusion independently, in its own words:
*"the design is sound … but with no caller supplying them the honest-absence path is the only path
ever taken, so the measurement exists in the SCHEMA and never in the DATA."* ⇒ **the schema half is
closed and the call sites are the work** — now stated by two independent observers.

### ⛔ One finding was checked against THIS repository before it was believed

`lessons-handling-...-004` reports `manage-lessons list` returning 21 rows while `get` **and `remove`**
return `not_found` for 3 of them, correlating exactly with YAML-frontmatter vs `key=value` metadata —
**a population that can be listed, cannot be read, and cannot be retired**, whose only escape bypasses
the tombstone the removal path exists to write.

⭐ **This orchestrator ran the same list→get walk over this checkout before staging: 39 listed, 39
`get` successes, 0 `not_found`; 39 of 39 files `key=value`, 0 YAML-frontmatter.** ⇒ **the resolver gap
is REAL but LATENT here.** That changes the priority, not the validity — there is no local data loss
to recover, and `PLAN-TRUTH-135` carries a verify-first clause because operator memory records
`remove` as **destroying** a lesson while returning `not_found`, which **contradicts** the sender's
observation that it refuses and leaves the file. ⛔ The two readings imply opposite acceptance tests.

### ⭐ Two clusters checked against sibling ledgers and deliberately NOT re-staged

`lessons-handling-...-003` (a Sourcery budget refusal counted as participation) is already shipped as
`review-apparatus` **`PLAN-PR-034`** and carried as lesson `2026-09-02-22-001`; only its genuinely new
limb — whether the refusal recognizer's patterns are per-bot or shared — travelled onward. And
`documented-invocations-...-016` / `-017` were **transferred** to that epic as
`review-apparatus/inbox/truthful-signals-044.md` rather than staged here.

## Inbox drain — 2026-09-03, 36 messages, every one dispositioned

> Relocated 2026-09-05 — a completed drain is closed by definition; every message was dispositioned and archived. 66 lines.


**The zero at the end is EMPTY, not FINISHED and not BLOCKED** (`live_count: 0`, `closed_senders`
empty, `invalid_count: 0`), so every sender may send again. Closure is exact: **36 archived + 0
invalid + 0 archive_failed = 36 scanned.**

**Three senders, and one of them was an open question this drain closed.** ⭐ `deployment-and-refresh-gaps`
(19 messages) **had no row in this queue because it is not our epic at all** — it is a **Token-Sheriff**
epic, and every one of its messages is a candidate-lesson *relayed* from that repo after
`manage-lessons add` refused it there with `wrong_store` (each names a plan-marshall bundle the
Token-Sheriff store does not own). ⛔ **Their PR ids (#681, #682, #687, #689, #694) are foreign-repo ids
and are NOT corroborable from this checkout** — every one is carried as a labelled lead. The other two
senders: `dual-homed-hook-install-renders-identically` (15, PLAN-TRUTH-102's own run) and
`review-apparatus` (2, transferred to us under the three-way rule).

**Dispositions: 5 promoted · 14 folded · 9 staged · 3 discarded-as-transferred · 3 retired-by-successor
· 1 landing reconciled · 1 recurrence.**

⭐⭐ **The landing predicted its own duplicates and named the remedy, and it was right.**
`-015`'s residue said six candidate-lessons and eight retrospective-routed messages were queued, that
its dedup *"rested on the dispatching prompt's enumeration rather than a read"*, and that **`inbox
supersede` is the clean disposition if the drain finds an overlap**. It found three: `-003`←`-009`,
`-004`←`-010`, `-008`←`-013`, each retired in favour of the richer re-derived successor.

⭐⭐ **The landing itself is COMPLETE and corroborated.** `inbox landing-check` returned
`complete: true` with an empty `missing_keys`; PR #1384 was read first-party as `state: merged` with
`merge_commit_sha 19453cb1b28196414c735d0806db53100ab81f1f`, **matching the payload's own
`landing_commit` exactly**. `landings/PLAN-TRUTH-102.md` and the shipped queue row (pr, landing,
`plan_marshall_plan_id`) were already stamped at ship time, so **no queue transition was owed** — the
drain reconciled nothing it had not already reconciled, and says so rather than restamping.

**Five new specs staged:** `PLAN-TRUTH-129` (invocation rejections that answer confidently and wrongly),
`-130` (an assessment read at report time grades a correct action as a violation), `-131` (the corpus
instruments publish an unmeasured zero and collapse a suffixed id), `-132` (a frozen manifest param has
no staleness detector), `-133` (the findings pipeline cannot tell an experiment from a regression).
Queue 176 → 181, appended with key-order and byte-identical-prefix assertions on both sides of the write.

**Five lessons promoted:** `2026-09-03-16-001` (diagnosis and resolution are separately falsifiable;
walk inheritance to the ROOT) · `-002` (a reviewer can fabricate a finding; check its own `diff_hunk`
first) · `-003` (`checked_at` is a staleness clock; never reserve a monotonic resource by assumption) ·
`-004` (a security remedy must be validated against the counterparty's state) · `-005` (a style gate is
safe only if the COMPOSITION of formatters has a fixed point).

⛔⛔ **ONE PROPOSED FIX WAS REFUTED AT HEAD AND MUST NOT BE IMPLEMENTED AS WRITTEN.**
`dual-homed-...-011` asked for the four context-load columns on `record-dispatch-boundary` and for an
unattributed row to say so. **Both are already done** — `--input-tokens`, `--output-tokens`,
`--cache-read-input-tokens` and `--cache-creation-input-tokens` are declared flags, and an omitted value
is already written as `'unmeasured'`, **not as 0**. ⇒ **The residue is a CALL-SITE omission, not a
schema gap** — materially different and much cheaper work. The observation (0 of 14 rows attributed)
stands; the diagnosis does not. It is folded into `PLAN-TRUTH-121` as a **recurrence** of the item
folded there on 2026-08-31, never as a second item.

⭐ **Two clusters were checked against a SIBLING ledger and deliberately NOT re-staged**, because a
duplicate held in another ledger is invisible to this queue unless someone goes and looks:
`deployment-...-009` witness 1 (a stale bot review credited as current participation) is already
`review-apparatus` **`PLAN-PR-045`**, whose own header names the same upstream source message; and
`deployment-...-012` site 2 (a refusal body classified as `participated`) is already shipped as
**`PLAN-PR-034`** and carried as lesson `2026-09-02-22-001`. Three further bot-recovery data-points
were **transferred** to that epic as `review-apparatus/inbox/truthful-signals-043.md` rather than
staged here.

**Every fold that widened a real surface updated the spec's `## Expected Surface` in the SAME act, and
the result was verified from the PARSER, not from the edit** (`corpus surfaces`): `-097` → 18 claimed
paths, `-100` → 11, `-104` → 5, `-108` → 5, `-121` → 7, `-122` → 13, `-126` → 17. Folds that widened
nothing say so in their decision line.

## Inbox drain — 2026-09-02, 2 messages, both dispositioned

> Relocated 2026-09-05 — a completed drain is closed by definition; every message was dispositioned and archived. 79 lines.


Both from sender `refresh-identity-and-scope-defences`, both `kind: candidate-lesson`, both `lifecycle:
live`. **Every mechanism claim in both was re-corroborated first-party at HEAD `30cd8aaf8` before any
ledger write** — nothing was recorded on the sender's word alone. In both cases the *foreign-repo repro*
(`cuioss/TokenSheriff`) was **not** corroborable here and is carried as a lead, labelled as such.

### `-001` → **STAGED** as PLAN-TRUTH-122

Two `build-maven` defects, opposite directions, same skill, same build, same run, no owner: a
`module-tests` canonical that cannot pass (`_maven_cmd_discover.py:810` emits `test -pl X -am`
unconditionally, and a sibling `test-jar` attaches only at `package`), and a green-build test count that
cannot add up (`_maven_cmd_parse.py:164` takes `matches[-1]` over a log holding two summary blocks —
660 + 7 reported as 7, stamped `tests_population: measured`).

⭐⭐ **Why STAGE and not FOLD.** Three fold candidates were examined and each was refused for a stated
reason, not for absence of a near neighbour:

- **PLAN-TRUTH-101** ("documented invocations that cannot succeed as written") — its D0 gate is scoped to
  *documented examples and prescribed invocations* in `manage-tasks` / `finalize-step-deploy-target`. The
  `module-tests` defect is a **generated** canonical in `build-maven`. Folding would stretch the plan
  across an unrelated surface — the staging error PLAN-TRUTH-105's own spec warns against.
- **PLAN-TRUTH-105** ("build-execution verdicts that mislead specifically on the healthy path") — its D0
  sweeps verdicts *derived differently on the success and failure paths*. `matches[-1]` under-reports on
  the red path too; it is merely most damaging on the green one. ⇒ **Different D0 question, neither
  population subsumes the other.** Recorded on -122 as an overlap-with-defer, not an absorption.
- **PLAN-TRUTH-087** (shipped, #1340) owned `tests_run: 0` on GREEN runs — a *sibling* member of the
  count-truthfulness family, already closed. Recorded on -122 as adjacency with a read-before-scoping
  obligation so the two fixes cannot disagree about what `tests_population` asserts.

⭐ **The drain widened the finding before staging it.** The sender filed two instances; the orchestrator
found the shared premise underneath them: `script-shared/.../_build_parse.py:596` `extract_test_summary`
takes `matches[-1]` and **states the false reason in its own docstring** — *"build tools often emit
per-module summaries; the final one is the aggregate."* Five parser sites inherit or restate it
(`build-maven`, `build-gradle`, `build-npm` jest + tap, `build-pyproject`). That is why -122's D0 is a
population sweep rather than a two-instance fix. ⚠ The five are recorded as a **floor derived from a
grep**, explicitly NOT as the population.

⭐ A third mechanism the sender asserted and the orchestrator corroborated independently: there is **no
project-side override**, and the reason is structural — `_cmd_client_query.py:145` does
`merged.update(rebuilt)`, so the generated canonical clobbers any crawled/operator value by construction.
That became -122 D2.

### `-002` → **DISCARDED here, FORWARDED to `review-apparatus`** as `truthful-signals-042.md`

CodeRabbit credited `participated` on a review of a **superseded commit** (PR #682: reviewed head
`99c36992`, current head `82e6597d` after a rebase force-push; the re-review was **declined for hourly
quota**, so no review of the new head ever existed).

⛔ **Routed by the standing inbound rule — the PR/review test runs first and wins outright.** The subject
is `automatic-review` + `workflow-integration-github` participation quorum reliability, which is
`review-apparatus`'s charter. **Delegation = REMOVED from this ledger**, so -122 does not track it and
this epic carries no watch for it.

⭐⭐ **This is not a new finding — it is a trigger already written down.**
`bot-participation-contract.md` § *"The currency-blind path for append-per-review bots — an accepted,
bounded gap"* names its own reopening condition: *"a required bot declaring
`participation_requires_update: false` observed satisfying the quorum on a merge candidate it
demonstrably did not review."* And **PLAN-PR-024** (shipped, #1349) excluded closing it because *"a cloud
run can neither observe those bots' real publishing behaviour nor obtain the sign-off such a change
needs."* ⇒ The observation half of that blocker is now discharged; the sign-off half is an operator
decision and stands. Both corroborated first-party (`github_pr.py:1317,:1338`; `coderabbit.md:44`).

⭐ **The gap's own self-limiting caveat was defeated by composition.** The contract argues the gap is
self-limiting because a re-triggered append-per-review bot posts a NEW comment. That assumes the
re-trigger is *served* — here it was **rate-declined**, so the stale credit stood. The rate-limit path
and the currency-blind path compose into a false green, and neither alone predicts it. That composition
is the part worth carrying into the sibling epic's scoping.

### ⚠ Mechanism defect observed BY this drain, not reported by either message

**The ledger still has no safe single-row append.** Staging -122 required rewriting the whole 169-row
`plans[]` array through `manage-status update-field`, because `queue --set-row` stamps only
`plan_marshall_plan_id` / `pr` / `landing` on an **existing** row and no append verb exists. The drain
used `.plan/temp/append-queue-row.py`, which reads the live array, refuses on a duplicate id, and prints
pre/post counts (169 → 170, verified). ⇒ **This is a live instance of PLAN-TRUTH-099's subject
("the ledger has no safe single-row append"), observed during ordinary orchestration.** Recorded here as
evidence for that staged plan; not staged again.

## Inbox drain — 2026-09-05, 16 messages, every one dispositioned (PLAN-TRUTH-126 full ship)

> Relocated 2026-09-05 — a completed drain is closed by definition; every message was dispositioned and archived. 28 lines.


**16 scanned / 16 archived / 0 invalid / 0 archive_failed.** Three senders, and the queue returns to the
**EMPTY** zero (`live_count: 0`, `closed_senders` empty, `invalid_count: 0`).

| Disposition | n | Where |
|---|:-:|---|
| `folded` | 8 | `-105` ×1, `-108` ×1, `-110` ×1, `-112` ×2, `-128` ×1, `-129` ×3, `-133` ×1 |
| `discarded` | 4 | 2 dedup-only (global twins), 2 forwarded to `review-apparatus` |
| `promoted` | 1 | global lessons `2026-09-05-08-001` (`pm-dev-java:java-core`) |
| `reconciled` | 1 | the `PLAN-TRUTH-126` landing |
| *(the two forwards are counted under `discarded` — nothing was staged here for them)* | | `truthful-signals-048.md` |

### ⭐⭐ The two dedup-only discards are the mis-routing being ABSORBED, not repeated

`-003` and `-004` were already in the GLOBAL corpus (`2026-09-05-07-007`, and a `## Recurrence` section
on `2026-09-04-08-014`) because the finalize dispatcher forwarded `orchestrated: false` in error. ⭐ The
run **caught it, re-emitted both here with dedup notes NAMING their global twins, and left the globals
in place rather than destroying them** — correct, given `manage-lessons remove`'s
destroy-while-reporting-`not_found` defect. ⇒ **Treated as ONE candidate each and NOT re-filed.**
The mechanism half is `-005`'s and folded to `PLAN-TRUTH-110`.

### ⭐ Five folds widened a declared surface and each says so; three did not and say that too

Per the fold same-act obligation: `-112` +2 entries, `-110` +2, `-129` +2 (message `-007`) and +1
(message `-008`), `-133` +2, `-105` +1. **Adds-no-file-surface, recorded explicitly:** `-108`, `-128`,
and `-129`'s `review-apparatus-032` fold.

## Inbox drain — 2026-09-05 (b), 11 messages, every one dispositioned (PLAN-TRUTH-093 full ship)

> Relocated 2026-09-05 — a completed drain is closed by definition; every message was dispositioned and archived. 27 lines.


**11 scanned / 11 archived / 0 invalid / 0 archive_failed.** Back to the genuine **EMPTY** zero.

| Disposition | n | Where |
|---|:-:|---|
| `folded` | 6 | `-105` ×1, `-108` ×1, `-117` ×2, `-118` ×1, `-129` ×1 |
| `discarded` | 4 | 1 self-declared non-lesson (refuted), 3 forwarded |
| `reconciled` | 1 | the `PLAN-TRUTH-093` landing |

➡ **`truthful-signals-049.md` → `review-apparatus`** (CodeRabbit's ETA registry matches none of its
observed phrasing, and the doc blames the bot — ~3h lost) and **`truthful-signals-054.md` →
`code-intelligence-substrate`** (the coverage-clean architecture zero, and the 41/41 unmeasured cache
decomposition). ⛔ Both transfers, not offers.

### ⭐⭐⭐ The most valuable message declared itself NOT a lesson, and was right

`-004` opens *"NOT A LESSON — corpus-health report, and the reported defect is REFUTED."* A finalize
step had recorded that lesson `2026-09-04-13-001` has an **empty body**. **False** — it carries a full
~1.5 KB body with four sections. ⛔⛔ **The claim rode SIX firings of the housekeeping step and was
re-stated to the next step as established fact; not one firing read the lesson. One `get` refuted it.**

⭐ **And the message then declined to assert a clean negative** — *"I did not survey the 73-lesson corpus
for it, and this message deliberately does not assert a clean negative."* **That is this epic's own rule
being obeyed inside the report of its violation.** Folded to `-117` as a positive control.
⚠ **No remediation is owed on `2026-09-04-13-001`. Do not reopen it.**

## Inbox drain — 2026-09-05 (c), 9 messages, every one dispositioned (PLAN-TRUTH-089 full ship)

> Relocated 2026-09-05 — a completed drain is closed by definition; every message was dispositioned and archived. 26 lines.


**9 scanned / 9 archived / 0 invalid / 0 archive_failed.** One sender; back to the **EMPTY** zero.

| Disposition | n | Where |
|---|:-:|---|
| `folded` | 4 | `-104` ×2, `-108` ×1, `-138` ×1 |
| `discarded` | 3 | all forwarded / deduped to `code-intelligence-substrate` |
| `promoted` | 1 | global lessons `2026-09-05-16-001` |
| `reconciled` | 1 | the `PLAN-TRUTH-089` landing |

➡ **`truthful-signals-055.md` → `code-intelligence-substrate`** (the 81% finalize cost share with the
124-firing mechanism attached; the dispatch-audit's `0.058` completeness; and the unmeasured token
decomposition **as a recurrence, deliberately NOT re-forwarded as a second item**).

### ⭐⭐⭐ `-008` INVERTS `PLAN-TRUTH-138`'s framing, and the inversion is the find

`ARTIFACT_EMISSION` can never run, because no completed task record carries `changed_files`. ⭐ **But the
guard behaved PERFECTLY**: it reported `change_attribution: unavailable` with a stated reason and left
`eligible_tasks` **ABSENT from the payload rather than reported as zero.**

⇒ **Both guards in `-138`'s class DECLINE to publish the zero.** So the class is **"guards whose producer
was never built"**, not "guards that publish dishonest zeros" — and ⛔ **a sweep hunting for dishonest
zeros would find NEITHER of them.** `-138`'s D0 must search for **unwritten producers of documented
inputs** instead. **Two members, two never-written fields, two honest consumers.**

## ✅ 2026-09-03 — `fresh` MEANS TWO DIFFERENT THINGS IN THE PRE-COMMIT FRESHNESS GATE — NOW OWNED BY `PLAN-TRUTH-128`

> Relocated 2026-09-05 — ownership transferred to PLAN-TRUTH-128, which is now RUNNING. 56 lines.


⭐ **OWNED as of 2026-09-03 by `PLAN-TRUTH-128` (staged, HIGH).** Kept as the origin record; the spec
carries the derived consumer set, the token decision and the tests. ⛔ **Do not re-derive it here.**
Originally ingested as a **data-point** from a live triage prompt in
another session (`manage-tasks`, `improvement`). That run reported the gate giving **two different
verdicts for one unchanged tree** — first `stale` / `build_scope_narrow` after a ledger scan, then
`fresh` / `not_necessary` short-circuiting *before* the scan — and noted its own push was not
compromised (it rested on a green whole-tree verify at that tree).

⭐ **Mechanism corroborated FIRST-PARTY at HEAD `30cd8aaf8`; the run itself is foreign.**
`_cmd_pre_commit_verify_freshness.py:517` calls `_build_necessity_verdict()` **before** anything else,
and on `decision == not_necessary` returns `status: fresh` with the message *"Gate permitted without a
ledger scan."*

⛔⛔ **The sharper diagnosis is NOT "non-determinism" — it is that `fresh` is OVERLOADED.** Two
materially different facts share one token:

| What happened | Returned |
|---|---|
| the ledger was scanned and the build IS current | `status: fresh` |
| **no scan occurred** — a build was ruled unnecessary for this footprint | `status: fresh` |

⇒ **A consumer gating a push on `fresh` cannot tell "verified" from "exempt, not verified."** That is
this epic's archetype exactly: *not looking* renders identically to *looked and found nothing wrong*.

⭐ **The two calls are probably not even contradictory**, which is why the reporter's "both cannot be
right" understates it: `should_execute_build` is keyed on the plan's LIVE FOOTPRINT, and the footprint
moves as the plan commits. So the calls likely answered a *changed* question and both were locally
correct — **and the defect survives that explanation intact**, because the caller still cannot
distinguish the two meanings of the answer it got.

⭐ **Credit where due, and do not "fix" it:** the fail-closed direction is right — an unobtainable
verdict degrades to `{'decision': 'build'}`, routing into the ledger scan. The exemption reasoning is
also sound (*"no `kind=build` entry could ever legally be stamped, so demanding one is an impossible
demand"*). **The defect is the shared token, not the short-circuit.**

⭐⭐ **The decisive evidence, found after the entry was first written: THIS GATE WAS ALREADY FIXED FOR
THIS EXACT CLASS — on the other side.** `push.md:52` records it in its own words, that a `display_detail`
omitting the `stale` reason *"hands a `build_killed` refusal to the operator indistinguishable from a
`worktree_mutated` one, **which is the same discarded-discriminator defect this gate was fixed to
stop**."* ⇒ `stale` carries **nine** reasons and `undecidable` two, precisely so their routes can be told
apart — **and `fresh`, the only status that PERMITS the push, carries none the consumer must read.**
⭐ The envelope already holds the discriminators (`notation_cross_check` / `scope_cross_check`, which
`manage-tasks/SKILL.md:80` documents as saying *"whether each was audited or merely undetermined"*); the
STATUS TOKEN collapses them and `push` branches on the token alone.

⚠ **Why no existing spec owned it.** `-119` is scoped to *phases 1-4* and this is a phase-5→6 boundary
gate; `-104` is scoped to `review_commitments` / `finalize-step-simplify` and names neither
`manage-tasks` nor freshness. ⛔ Folding into either would have stretched a declared scope, which this
epic records as a staging error.

⚠ **Not claimed:** whether any push has actually been gated on the exempt-`fresh` path. n=1, foreign,
and the reporting run states its own push was covered by a real verify. Deriving that population would
be an owning plan's first act.

## ✅ 2026-09-03 — A LOOPED-BACK PHASE IS RECORDED `in_progress` FOREVER — NOW OWNED BY `PLAN-TRUTH-127`

> Relocated 2026-09-05 — ownership transferred to PLAN-TRUTH-127, which is staged and re-grounded. 39 lines.


⭐ **OWNED as of 2026-09-03 by `PLAN-TRUTH-127` (staged, HIGH).** This entry is kept as the defect's
origin record; the spec carries the derived population, the composed mechanism, and the matched control.
⛔ **Do not re-derive it here.** Originally ingested as a **data-point**, not a landing report (operator
direction): a foreign-machine run reported `status.json` recording `5-execute` as `in_progress` on a plan
that had completed and merged, while its metrics ledger recorded the phase correctly
(`close_count: 2`, `end_time` present, no missing boundaries). ⇒ **Two ledgers disagree about whether a
phase completed, and the authoritative-looking one is the wrong one.**

⭐ **The mechanism is corroborated FIRST-PARTY at HEAD `30cd8aaf8`; only the run itself is foreign.**

**(1) `set-phase` opens a phase and never closes one.** `_status_query.py:77` `cmd_set_phase` sets
`current_phase` and stamps the target phase `PHASE_STATUS_IN_PROGRESS`. **Marking a phase `completed` is
exclusively `cmd_transition --completed`'s job.** ⇒ A loop-back re-opens `5-execute`; if the resumed
dispatch then yields `blocked` rather than completing, **nothing ever calls `transition`, and the phase
stays `in_progress` permanently** — through merge, through archive, in the durable record.

**(2) The correction path is structurally CLOSED after finalize.** `_cmd_lifecycle.py:55`
`_clean_tree_refusal` shells `git -C {worktree_path} status --porcelain` and **fails closed when the
command fails** — *"an unreadable tree cannot be proven clean"*. After `branch-cleanup` removes the
worktree the command cannot succeed, so `transition --completed` is unreachable for any worktree plan
once finalize has run. ⇒ The operator on that machine could not repair the row, and **correctly declined
to clear the metadata to bypass a safety guard** — the right call; the guard is not the defect.

**(3) ⛔ AND THE REFUSAL NAMES THE WRONG CAUSE.** A removed worktree and a dirty worktree are different
facts, and both surface as `error: worktree_dirty_at_boundary`. **A tree that is GONE is reported as one
that is DIRTY** — the epic's own archetype: a confident code naming a cause it did not establish.
⭐ This third arm is small, self-contained and first-party; it could ride any plan touching
`_cmd_lifecycle.py` rather than needing one of its own.

⭐⭐ **The population was DERIVED the same day and the defect is LOCAL, not foreign.** Over all 30
archived plans: **4 carry an open phase, and all 4 carry `loop_back_reentry`; of the 25 without that
marker, none does.** The composed mechanism is in `-127`: `cmd_archive` closes only the FIRST non-`done`
phase, so with two open phases it closes the earlier and leaves the later — which is exactly why the
local cases read `5-execute: done` / `6-finalize: in_progress`. ⚠ The foreign report's terminal phase
differs (`5-execute` open); `-127` D0(a) explains that rather than averaging it away. ⭐ The fifth
loop-back plan closed cleanly and is `-127`'s matched negative control.
