# Verification — 180-orchestrator-cleanup-verb

**Verified against:** commit `4ea24cbd3134905810a4b9c17755798e3e6c2dff`   **Landed as:** PR #1183, commit `91a1c77131a855d8d2bd07ae39b44affc58b99ae`   **Verdict:** implemented-with-gaps

## Method

Read `plan.md` and `report-01.md` in full. Located the landing with
`git log --oneline --all --grep '#1183'` → squash commit `91a1c771` (19 files, +1541/−62). Read the
landed diff (`git show --stat`, `git show --name-status --find-renames`) and the pre-change state of
every claim-table artifact (`git show 91a1c771^:<path>`) to re-derive the plan's HYPOTHESIS table
against the tree the run actually faced.

Files opened at HEAD:

- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` —
  `cmd_compact`, `_build_ordered_queue`, `_replace_block`, `_marker_indices`, `_invariant_queue_spec`,
  `_invariant_no_terminal_in_live_queue`, `_invariant_pointers_reachable`, `_settled_headings`,
  `_abstained_sections`, `_queue_cell`, `_row_surface`, `_build_summary`, `cmd_resume_summary`,
  `cmd_corpus_enumerate`, the `compact` argparse wiring, and the module constants block
  (`GENERATED_BLOCKS`, `FILE_SETTLED`, `CLOSED_PHASE`, `LIVE_QUEUE_EXCLUDED_STATUSES`,
  `_RELOCATION_POINTER_RE`).
- `.../plan-orchestrator/templates/epic.md`, `.../plan-orchestrator/SKILL.md`,
  `.../plan-orchestrator/workflow/cleanup.md`, and every other workflow doc named in the diff.
- `.../persona-plan-orchestrator/standards/orchestration-model.md` (§ Persist/Stop-Resume, § Carve-outs,
  § Cleanup Contract, § Ledger-Compaction Stage, and the tree-layout contract).
- `.../manage-status/standards/status-lifecycle.md` § Orchestrator Status.
- `test/plan-marshall/plan-orchestrator/test_orchestrator_compact.py`,
  `test_cleanup_contract.py`, `test_orchestrator.py`.
- `.../script-shared/scripts/build/_build_execute_factory.py` and
  `test/plan-marshall/script-shared/test_build_execute_factory.py` (residue check).

Tests executed:

- `uv run python -m pytest test/plan-marshall/plan-orchestrator/test_orchestrator_compact.py -o addopts="" -q`
  → **32 passed** in 2.91s.
- `... test_cleanup_contract.py test_orchestrator.py -o addopts="" -q` → **76 passed** in 1.54s.

Mutations applied (file bytes saved to the scratchpad first; restored by byte copy, md5 re-checked
identical `eb9f27c4d67fedea8460df1da9c0b7f2`; **no** `git checkout`/`restore`/`stash` used):

1. `if phase == CLOSED_PHASE:` → `if phase == 'NEVER_MATCHES':` **and**
   `updated = lines[: begin_idx + 1] + new_lines + lines[end_idx:]` →
   `updated = lines[: begin_idx + 1] + new_lines` (truncating everything after the block).
   Result: **14 failed, 18 passed** — including
   `TestNarrativeSurvivesVerbatim::test_a_retraction_survives_a_pass_byte_identical`,
   `TestRefusals::test_refuses_a_closed_epic_and_leaves_it_byte_identical`, and
   `TestCompactCli::test_refuses_a_closed_epic_through_cli`. Both of the plan's headline guards bite.
2. In `test_orchestrator_compact.py`, replaced the disjunctive assertion
   `assert after == text or after == _epic_text(plan_context)` with `assert after == text` alone.
   Result: **1 failed** — proving the first disjunct is False in this fixture and the assertion
   passes only via its tautological second disjunct (see G1).

Greps re-derived at the moment of the claim: `settled.md` across the tree (**21 matching lines / 22
occurrences** in `marketplace/` + `test/`, excluding `__pycache__` — 2 in the standard, 9 in
`orchestrator.py`, 4 in `cleanup.md`, 6 in `test_orchestrator_compact.py`; an earlier draft of this
document said "17 sites", which does not re-derive); `resume-summary` across `*.md`/`*.adoc`/`*.py`;
`Ordered Queue` across the two skills and `doc/`. Verb-routing rows counted from the § Verb Routing
section of `plan-orchestrator/SKILL.md` → **10**, unchanged (no `compact` router row, as designed).

Supersession check: `git log --oneline 91a1c771..HEAD` over `orchestrator.py`, `templates/epic.md`,
and `orchestration-model.md` returns three later commits (`94bcddf2` #1189, `51d1c9bc` #1198,
`5a5446d3` #1215); a `git log -p` filtered on `compact|settled|ordered.queue|GENERATED` over the
standard returns **nothing**, so no later plan altered this plan's contract.

Final `git status --porcelain` shows only files modified by other concurrent sessions plus my two
output files; `orchestrator.py` and `test_orchestrator_compact.py` are absent from it.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D1 | GATE: verb name, relocation target, idempotence | all three decided and recorded | yes | yes | yes | yes | `orchestration-model.md:221` (verb-name settlement, **pre-existing** — confirmed via `git show 91a1c771^:…` line 220); `:253` (`settled.md` target); `:255` (idempotence); `orchestrator.py:268` `FILE_SETTLED`; `TestIdempotence::test_a_second_run_is_a_no_op_on_disk` passes |
| D2 | GENERATED-block mechanism on every derivable surface + annotation-zone tension | each derivable surface guarded and regenerable | yes | yes | yes | partial | `templates/epic.md:50-54` (`BEGIN/END GENERATED: ordered-queue`), `:56-63` (`### Queue annotations`), `:65-71` (Decisions declared narrative, authority `logs/decision.log`); `orchestrator.py:286` `GENERATED_BLOCKS = ('resume-summary','ordered-queue')`; `orchestration-model.md:249` annotation-zone contract. **Gaps:** no migration path for a block already hand-annotated *inside* the markers (G2); and the `ordered-queue` marker pair is NEW here, so on every epic scaffolded from the pre-change template the surface is never regenerated and no doc instructs inserting the markers (G7) |
| D3 | Relocate settled narrative, with pointers | each item verbatim at destination and reachable from a pointer at origin | yes (judgement half is doc-only, by design) | yes | yes | partial | `cleanup.md:82-86` (verbatim move, pointer template, present-for-confirmation); `orchestrator.py:2137` `_invariant_pointers_reachable`, `:300` `_RELOCATION_POINTER_RE`; `TestPointerReachability` (4 tests) passes. **Gap:** `settled.md` missing from the standard's tree-layout contract and carve-out enumeration (G3) |
| D4 | Report what moved; never trim silently | report names every mutation and every abstention | yes | partly | **no** | partial | `orchestrator.py:2291-2303` returns `regenerated[]`, `invariants[]`, `abstained[]`, `abstained_count`, `epic_changed`; `test_abstained_names_the_narrative_sections_left_verbatim`, `test_carries_three_invariants_each_with_verdict_evidence_population` pass. **Gaps:** `_abstained_sections` (`:2192`) labels a derivable section whose markers are absent `preserved_verbatim` — the same value a narrative section gets — so the report presents a surface the stage COULD NOT touch as one it CHOSE to preserve, and inflates `abstained_count` (executed, see § Adversarial review; **G6, high**); and the `cleanup` verb's own Output contract (`cleanup.md:154-173`) omits the three fields line 97 tells it to fold in (G4) |
| D5 | Invariant verification + four tests | all four pass, each seen to fail pre-fix | yes | yes | yes | yes (one vacuous assertion, G1) | three invariants at `orchestrator.py:2285-2289`; bidirectionality supplied by `cmd_corpus_enumerate` (`rows_without_spec` **and** `specs_without_row`, never collapsed — `orchestrator.py:1320-1385`); 32/32 tests pass (re-run independently); closed-epic refusal + retraction survival both went RED under mutation 1. **Note:** `_invariant_queue_spec` duplicates the pre-existing `_corpus_signal` (`:1805-1841`) branch for branch (G8, low) |

**D2 — annotation-zone tension.** The chosen horn (a zone *outside* the markers) is implemented and
documented, and it is structurally sound for content written after this landing. It is silent about
the situation the plan's own problem statement names: a live block that is *already* hand-annotated
between the markers. `_replace_block` (`orchestrator.py:2018-2038`) discards `before` and reports only
`lines_before`/`lines_after`; `cmd_compact` never surfaces the discarded text, and neither
`cleanup.md` § Step 8 nor § Ledger-Compaction Stage instructs migrating in-marker annotations to the
zone before the first compaction. The first `compact` on such an epic is therefore lossy, and the
report distinguishes it from a clean pass only by a line-count delta. See G2.

**D3 — `settled.md` is undeclared in the layout contract.** `orchestration-model.md:22-35` is the
epic tree's layout contract and lists `epic.md`, `status.json`, `history.md`, `references.json`,
`workstreams/`, `plans/`, `landings/`, `inbox/`, `logs/` — nine entries, no `settled.md`. The same
standard at `:253` mandates `settled.md` as a live-epic sibling of `history.md`, and `cleanup.md:82`
links to `#carve-outs` for its creation, but `:85`'s enumeration of ledger documents (`epic.md`,
workstream charters, plan specs, landing records, `history.md`, `references.json`) does not name it
either. A reader following either contract finds no home for the file the verb is told to write. See G3.

**D4 — the verb-tier report contract lags the stage.** `cleanup.md:97` instructs "fold the stage's
`regenerated[]`, `invariants[]`, and `abstained[]` into this report", but the canonical Output block at
`cleanup.md:154-173` declares only `ledger_compaction: compacted` and carries no key for any of the
three. An implementer working from the Output block alone emits a compaction line with no mutation and
no abstention detail — precisely the "a report that lists only what changed" failure the plan's
Verification section names. No test covers the Output block's field list
(`test_cleanup_contract.py` checks router closure, verb-enumeration agreement, canonical-invocation
coverage, apply-idempotence, and verdict-field single-definition — not the Output field set). See G4.

**D4 — the abstention field mislabels an unreachable derivable surface.** `_abstained_sections`
(`orchestrator.py:2192`) marks a `##` section abstained-from "unless it CONTAINS a GENERATED marker".
A section that IS a derivable surface but whose markers are absent — precisely the `markers_absent`
case — therefore lands in `abstained[]` with `treatment: preserved_verbatim`, the value reserved for
genuine narrative. Executed against an `epic.md` in the pre-change template shape, the function
returns `Vision`, **`Ordered Queue`**, and `Decisions`, all three `preserved_verbatim`. The
function's own docstring claims the opposite ("This is what lets a reader tell 'nothing needed
touching' from 'the stage could not see it'"). Because every epic scaffolded before this landing has
no `ordered-queue` markers (G7), this is the default output on the population the verb was built for,
not an edge case. See G6.

**D5 — one vacuous assertion.** `test_every_hand_authored_section_survives_verbatim` ends with
`assert after == text or after == _epic_text(plan_context)`; the second disjunct compares a value to a
fresh read of the same unchanged file and is a tautology. Mutation 2 showed the first disjunct is
False here, so the line asserts nothing. The four substantive `assert fragment in after` checks above
it are real, and idempotence is genuinely covered by `TestIdempotence`, so this is a dead line rather
than a hole — but its comment ("A second pass changes nothing at all") describes a second pass the
test never performs. See G1.

## Report accuracy

Checked every re-derivable figure and path in `report-01.md`. Findings:

- **Confirmed.** `templates/epic.md` at `91a1c771^` had `BEGIN/END GENERATED: resume-summary` markers
  (lines 24/26) with the regeneration invocation at line 19, and the Ordered Queue table (lines 44-46)
  had **no** markers — the report's "CONFIRMED" and "CONFIRMED (count re-derived)" verdicts hold.
- **Confirmed.** The pre-change Ordered Queue header is
  `| # | Plan | Workstream | Status | Surface (expected) | Notes |` — **five** derivable columns plus
  `Notes`, exactly as the report re-derived against the plan's "four".
- **Confirmed.** Pre-change `templates/epic.md:50-51` did say "also logged via `manage-logging`
  (decision verb)", so the plan's "no stated authority" claim is partially refuted as reported.
- **Confirmed.** Pre-change § Verb Routing carried **10** rows including `cleanup`; the post-change
  table still carries 10 (no `compact` router row).
- **Confirmed.** Pre-change `cleanup.md:78-80` was "Call the ledger-compaction stage … report
  `ledger_compaction: not_available` … no spec yet owns the compaction surface" — the report's
  "REFUTED at the verb tier, CONFIRMED at the stage tier" reading is accurate.
- **Confirmed.** The verb-name settlement at `orchestration-model.md:220` pre-dates this plan, so D1's
  "settled by the standard" is not a post-hoc rationalisation.
- **Confirmed.** The Expected-surface deviation is real: `test_cleanup_contract.py:287`
  `test_every_workflow_doc_on_disk_is_referenced` asserts every `workflow/*.md` is reachable from a
  routing row, so a `workflow/compact.md` without a router verb would have failed. The report's
  refutation is checked, not asserted.
- **~~Confirmed~~ — WITHDRAWN under adversarial review.** This document originally read: "The
  residue it discloses is still real … Nothing isolates it." That is **false**. The residue
  `report-01.md` disclosed was real *at the time of that report* but has since been fixed:
  `test_build_execute_factory.py:433-451` carries an **autouse** `_isolated_home_root` fixture setting
  `PLAN_MARSHALL_HOME` to a per-test `tmp_path`, added in `d4ae2e81` (#1193) — later than this plan's
  `91a1c771` (#1183). Running the class five consecutive times in one session leaves
  `~/.plan-marshall/marshalld/fallback-streak.json` byte-identical and all four tests green. The
  original conclusion came from a symbol search for `home_root` / `_fallback_state_path`, which the
  env-var-based isolation does not match, and from reading the callee rather than running the test.
  See gaps.md § Refuted during adversarial review.
- **Minor contradiction (own text).** "All in commit `63b9630`" under § Deliverables is contradicted
  by its own § Findings, which places fixes in `8e160d3`, `dbe474b`, `14e23a3`, and `d232913`.
- **Not verifiable.** None of `63b9630`, `8e160d3`, `dbe474b`, `14e23a3`, `d232913`, `7ea2b75` is a
  valid object in this clone (`git cat-file -t` → "Not a valid object name") — the branch was squashed
  into `91a1c771` and deleted. This is expected for a squash merge, not a report defect, but no
  per-commit claim can be checked.
- **Slight imprecision, not a contradiction.** "`templates/epic.md` lines 17-26" is quoted for the
  START-HERE markers; the markers themselves are at lines 24 and 26, with the comment block at 17-22.

No other contradiction found, having checked: the template's pre- and post-change state, the standard's
pre- and post-change state, the verb-routing table row count, the workflow-doc consumer sweep, the
test names it cites (all 12 named test symbols exist and pass), and the residue's mechanism.

## Out-of-scope compliance

The run stayed inside its boundaries.

- **`resume_anchor` shape — not touched.** `_build_summary` still renders `resume_anchor` verbatim
  (`orchestrator.py:703-712`, `:721`); no reshaping, no truncation. Recorded as owed work in the
  report's § Residue, as the plan required.
- **Inbox archive foldering — not touched here.** It landed later in PR #1198 (`51d1c9bc`), the
  sibling plan that owns it.
- **Deletes nothing.** `cmd_compact` writes only `epic.md`, only between marker pairs; no `unlink`, no
  directory removal, no truncation of narrative. Verified by reading `_replace_block` and by
  `TestNarrativeSurvivesVerbatim` (3 tests) plus mutation 1.
- **Refuses a closed epic.** `orchestrator.py:2256-2263`; `TestRefusals` and `TestCompactCli` both
  cover it, and mutation 1 turned both red.
- **No LLM judgement over the whole file.** The script is purely mechanical; the settled-versus-live
  call is doc-only and explicitly "present for confirmation on a first run" (`cleanup.md:82`).

Collateral in the landed diff beyond the plan's Expected surface: `doc/concepts/orchestration.adoc`,
`persona-plan-orchestrator/SKILL.md`, `templates/landing-analysis.md`, and six workflow docs
(`analyze`, `close`, `decompose`, `init`, `lessons-handling`, `orchestrate`, `resume`). All are
consumers of the now-two-block `resume-summary` emission; each is a doc-consistency edit forced by the
D2 change and each is disclosed in the report's Findings passes 1-3. `git show 91a1c771 -- <standard>`
shows the removed lines were all replaced in place, none dropped. This is in-scope collateral, not
undeclared scope creep.

## Residue carried forward

| Report residue | Status in today's tree |
|---|---|
| `resume_anchor` shape question needs its own plan | **still open.** No plan under `doc/plans/truthful-signals/` addresses it (directory listing re-derived: 44 plan directories, none naming `resume_anchor` or anchor shape). |
| `inbox/` per-sender foldering owned by the sibling inbox plan | **closed.** Landed in PR #1198 (`51d1c9bc`, "inbox amend/supersede/close-stream + per-sender archive foldering"). |
| `script-shared` test-isolation flaw in `test_a_real_plan_id_still_writes_the_work_log` | **CLOSED — this row was wrong.** An autouse `_isolated_home_root` fixture (`test_build_execute_factory.py:433-451`) sets `PLAN_MARSHALL_HOME` to a per-test `tmp_path`; added in `d4ae2e81` (#1193), after this plan. Re-running the class 5× in one session leaves the machine-global streak file byte-identical and all tests green. G5 is refuted — see gaps.md § Refuted during adversarial review. |
| Proposed lane skill note about machine-global test-state poisoning ("What have we learned") | **still open / operator-gated.** By design it was to ship as a separate `chore/` PR only on operator approval; nothing in `.claude/skills/cloud-plan-lane/SKILL.md` was checked for it, and no approval is recorded. Not actionable from the tree. |

## What could NOT be verified

- The five branch commits and the CI head sha the report cites are unreachable in this clone (squash
  merge + branch deletion), so no per-commit attribution, and no "seen to fail pre-fix" claim from the
  authoring session, can be checked. I substituted my own mutation testing for the two guards the plan
  calls load-bearing.
- The `./pw verify` figures (16097/16098 passed, 1 skipped) — not re-run; a full verify exceeds the
  time budget for this check and the figure is machine- and session-dependent.
- The D3 cold-read result (the Step 6 sub-agent answering "A,B REGENERABLE / C,D PRESERVE") is a
  transcript artifact of the authoring session, not a tree artifact. The *written boundary* it was
  testing is present and, read cold by me, does classify correctly
  (`orchestration-model.md:243`-`:245`), but the sub-agent's answer itself cannot be re-derived.
- PR #1183's review threads, check conclusions, and reviewer-participation table were not queried;
  they are GitHub state, not tree state.
- Whether a real live epic's `epic.md` currently carries in-marker hand annotations (the G2 exposure)
  — every orchestrator ledger lives under the git-ignored `.plan/`, absent from this clone.

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked.** Every `high` gap (there were none on entry; one was added), every clean-pass deliverable
row, and every "swept, clean" claim.

- **Mutations re-applied from scratch**, bytes saved to a scratchpad first, `git diff --quiet` checked
  on both files before touching them, restored by byte copy and md5-verified
  (`orchestrator.py` → `eb9f27c4d67fedea8460df1da9c0b7f2`,
  `test_orchestrator_compact.py` → `f5352bfa11ca46e0f09319a04312eff5`); no
  `git checkout`/`restore`/`stash`. Mutation 1 (`CLOSED_PHASE` → `'NEVER_MATCHES'` **and** dropping
  `+ lines[end_idx:]`) reproduced **14 failed, 18 passed** exactly, including the three named guards.
  Mutation 2 (`assert after == text` alone) reproduced **1 failed, 31 passed**, the failure diff
  showing the regenerated `**Inbox (derived)**` line.
- **Functions executed, not read.** `_abstained_sections` was run on an `epic.md` in the pre-change
  template shape (this produced G6). `_RELOCATION_POINTER_RE` was run against the exact pointer
  template at `cleanup.md:85` and does extract the heading. The `script-shared` test class was run
  five consecutive times in one session with the machine-global streak file md5'd before and after.
- **Counts re-derived.** 32 passed / 76 passed (both reproduced); 19 files and +1541/−62 in
  `91a1c771`; 10 verb-routing rows; 44 plan directories under `doc/plans/truthful-signals/`; the
  three supersession commits and their PR numbers; `settled.md` occurrences (**21 lines / 22
  occurrences**, not 17). Pre-change state re-read at `91a1c771^` for `templates/epic.md`
  (markers 24/26, invocation 19, queue table 44-46 unmarked, six-column header) and
  `orchestration-model.md` (verb-name settlement at line 220).
- **Sweeps re-run broader.** The supersession sweep was widened from the standard alone to
  `orchestration-model.md` + `cleanup.md` + `templates/epic.md` filtered on
  `compact|settled|ordered.queue|GENERATED|abstain|annotation` → still nothing; and over
  `orchestrator.py` filtered on `compact|_abstained|_replace_block|_invariant` → 0 changed lines. The
  `resume-summary` consumer sweep was re-run across all `*.md`/`*.adoc` outside `doc/plans/` — every
  consumer names both blocks. A `marker` sweep across `plan-orchestrator/workflow/` and
  `doc/concepts/orchestration.adoc` found no marker-insertion instruction anywhere (this produced G7).
- **NOT re-checked.** The `./pw verify` totals (16097/16098 passed) — still not re-run. The full
  plan-marshall suite. PR #1183's GitHub state (threads, checks, reviewers). Whether any real live
  `epic.md` carries in-marker annotations or lacks the `ordered-queue` markers — that tree is under
  the git-ignored `.plan/` and unobservable from this clone, so G2's and G7's exposure sizes remain
  uncounted. The D3 cold-read transcript. `report-01.md`'s unreachable branch SHAs.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| G1 | tautological disjunct at `test_orchestrator_compact.py:369`, medium | **upheld** | Mutation re-applied: `assert after == text` alone → `1 failed, 31 passed`; the failing diff is the regenerated resume-summary body, so the first disjunct is genuinely False. Line numbers 362/364/369 confirmed. "two lines earlier" tightened to name line 364. |
| G2 | no migration path for in-marker annotations, medium | **upheld, one clause corrected** | `_replace_block:2033` computes `before` and returns only `len(before)`; confirmed. But the gap said "neither § Step 8 nor § Ledger-Compaction Stage contains a step" — `orchestration-model.md:249` *does* state "the annotations move to the zone". Rewritten: the standard states the intent abstractly, no procedure operationalizes it, nothing gates the first compaction on it. |
| G3 | `settled.md` undeclared in tree-layout + carve-out lists, medium | **upheld, figures corrected** | Layout entries re-read at `:24-35` (fence `:23-36`) — nine entries, no `settled.md`; `:85` parenthetical re-read — not named; `:48` one-to-one claim confirmed; `:59` and `:253` are the only two `settled.md` sites in the standard. The "17 sites" figure does not re-derive → **21 lines / 22 occurrences**. Range corrected from `:22-35`. |
| G4 | Output block omits the three folded fields, medium | **upheld, line refs corrected** | `cleanup.md:97` instruction and the Output fence re-read: fence is `:154-173` (not `:154-172`), `ledger_compaction: compacted` at `:168`, no key for any of the three; `declined[]`'s required-never-omitted sentence is at `:177` (not `:176`). The `test_cleanup_contract.py` coverage claim re-derived from its 24 test symbols — no Output-field-set test. |
| G5 | `script-shared` fallback-streak test not isolated, medium | **REFUTED** | Autouse `_isolated_home_root` (`test_build_execute_factory.py:433-451`) sets `PLAN_MARSHALL_HOME` to `tmp_path`; `git log -S` dates it to `d4ae2e81` (#1193), later than #1183. Class run 5× consecutively: `4 passed` each time, streak file md5 unchanged (`f21dab08…`), no `a-real-plan` key written. Moved to gaps.md § Refuted. |
| G6 | *(new)* `abstained[]` labels an unreachable derivable section `preserved_verbatim` | **added, high** | `_abstained_sections` executed on a pre-change-shape `epic.md` → `{'section': 'Ordered Queue', 'treatment': 'preserved_verbatim'}` alongside `Vision` and `Decisions`. Contradicts its own docstring and D4's stated requirement. |
| G7 | *(new)* no migration inserting the `ordered-queue` markers into a pre-existing `epic.md` | **added, medium** | `git show 91a1c771^:templates/epic.md` — queue table at 44-46, no markers; the marker pair is new in this landing. `orchestration-model.md:247` forbids the stage inserting them. A `marker` sweep across all workflow docs returns only paste-between-existing-markers instructions. |
| G8 | *(new)* `_invariant_queue_spec` duplicates `_corpus_signal` | **added, low** | `orchestrator.py:2051-2086` versus `:1805-1841` — same `cmd_corpus_enumerate` call, same population string, same four branches, same evidence strings; only the verdict vocabulary differs. |
| Verdict `implemented-with-gaps` | — | **upheld** | All five deliverables are implemented and none is missing; the open items are one dead assertion, three doc-contract divergences, one report-field defect, one un-migrated path, and one duplication. No deliverable is unimplemented, so `partially-implemented` would be wrong. |
| "32 passed" / "76 passed" | test totals | **upheld** | Both reproduced (`32 passed in 0.46s`, `76 passed in 1.63s`). |
| Supersession: no later plan altered the contract | — | **upheld, and widened** | Three commits confirmed by SHA and PR number; widened filter over three docs plus `orchestrator.py` returns zero compact-related changed lines. |
| "Deletes nothing" | out-of-scope compliance | **upheld** | `cmd_compact` writes only `epic.md` and only between marker pairs; `cmd_corpus_enumerate` re-read and confirmed read-only ("resolves the archived read-fallback and writes nothing"). |
| Report-accuracy § "residue is still real" | — | **refuted, withdrawn in place** | Same evidence as G5. |

**Documents corrected.**

- `verification.md`: the D4 row's *Correct?* flipped `yes` → **no** and *As documented?* to `partly`
  (G6); the D2 row now also carries G7; the D5 row notes G8; a new **D4 — the abstention field
  mislabels an unreachable derivable surface** paragraph added; the § Report accuracy bullet asserting
  the `script-shared` residue "is still real … Nothing isolates it" **withdrawn in place** with its
  refuting evidence; the § Residue carried forward row for that residue flipped to **CLOSED — this row
  was wrong**; the `settled.md` grep figure corrected 17 → 21/22; line references corrected
  (`:2292-2304`→`:2291-2303`, `:2136`→`:2137`, `:298`→`:300`, `:2254-2263`→`:2256-2263`,
  `cleanup.md:154-172`→`:154-173`). The headline verdict is unchanged.
- `gaps.md`: **Open items** 5 → **7**; G1–G4 upheld with their imprecise line numbers, ranges and the
  "17 sites" count corrected and G2's mis-stated clause rewritten; **G5 refuted** and relocated to a
  new § Refuted during adversarial review with its evidence; **G6 (high)**, **G7 (medium)** and
  **G8 (low)** added, continuing the sequence. No existing ID was renumbered.

**Residual doubt — what a third reviewer should look at first.**

1. **G6 and G7 interact and neither was reproducible against a real epic.** Both were demonstrated
   against a synthesised `epic.md`. If any live epic in fact already carries the `ordered-queue`
   markers (someone hand-inserted them), G7 shrinks and G6 stops being the default path. That is one
   `ls`/`grep` away for anyone with a `.plan/` tree, and it should be the first thing checked.
2. **D5's "each was seen to fail pre-fix" is still unverified and now unverifiable.** Mutation testing
   substitutes for two of the four tests (the closed-epic refusal and the retraction survival). Tests
   (c) *a stale derivable row is corrected* and (d) *the report names every mutation* were confirmed
   to pass but were never seen to fail — no mutation was aimed at `_build_ordered_queue`'s status
   derivation or at the `regenerated[]`/`abstained[]` assembly.
3. **`_invariant_no_terminal_in_live_queue` reads the freshly-built body, never the on-disk table.**
   Its docstring concedes this. When the `ordered-queue` markers are absent the body is never written,
   yet the invariant still reports `ok` — a second instance of the G6 shape, in the invariant channel
   rather than the abstention channel. It was not filed as a gap because the code discloses it and
   pairs it with `markers_absent`, but a third reviewer may reasonably disagree with that call.
4. **`report-01.md`'s per-commit claims remain permanently uncheckable** (squash merge, branch
   deleted), including its self-contradiction over which commit carries the fixes.
