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

Greps re-derived at the moment of the claim: `settled.md` across the tree (17 sites, all in the
standard, the script, `cleanup.md`, and the tests); `resume-summary` across `*.md`/`*.adoc`/`*.py`;
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
| D2 | GENERATED-block mechanism on every derivable surface + annotation-zone tension | each derivable surface guarded and regenerable | yes | yes | yes | partial | `templates/epic.md:50-54` (`BEGIN/END GENERATED: ordered-queue`), `:56-63` (`### Queue annotations`), `:65-71` (Decisions declared narrative, authority `logs/decision.log`); `orchestrator.py:286` `GENERATED_BLOCKS = ('resume-summary','ordered-queue')`; `orchestration-model.md:249` annotation-zone contract. **Gap:** no migration path for a block already hand-annotated *inside* the markers (G2) |
| D3 | Relocate settled narrative, with pointers | each item verbatim at destination and reachable from a pointer at origin | yes (judgement half is doc-only, by design) | yes | yes | partial | `cleanup.md:82-86` (verbatim move, pointer template, present-for-confirmation); `orchestrator.py:2136` `_invariant_pointers_reachable`, `:298` `_RELOCATION_POINTER_RE`; `TestPointerReachability` (4 tests) passes. **Gap:** `settled.md` missing from the standard's tree-layout contract and carve-out enumeration (G3) |
| D4 | Report what moved; never trim silently | report names every mutation and every abstention | yes | yes | yes | partial | `orchestrator.py:2292-2304` returns `regenerated[]`, `invariants[]`, `abstained[]`, `abstained_count`, `epic_changed`; `test_abstained_names_the_narrative_sections_left_verbatim`, `test_carries_three_invariants_each_with_verdict_evidence_population` pass. **Gap:** the `cleanup` verb's own Output contract (`cleanup.md:154-172`) omits the three fields line 97 tells it to fold in (G4) |
| D5 | Invariant verification + four tests | all four pass, each seen to fail pre-fix | yes | yes | yes | yes (one vacuous assertion, G1) | three invariants at `orchestrator.py:2285-2289`; bidirectionality supplied by `cmd_corpus_enumerate` (`rows_without_spec` **and** `specs_without_row`, never collapsed — `orchestrator.py:1320-1385`); 32/32 tests pass; closed-epic refusal + retraction survival both went RED under mutation 1 |

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
`cleanup.md:154-172` declares only `ledger_compaction: compacted` and carries no key for any of the
three. An implementer working from the Output block alone emits a compaction line with no mutation and
no abstention detail — precisely the "a report that lists only what changed" failure the plan's
Verification section names. No test covers the Output block's field list
(`test_cleanup_contract.py` checks router closure, verb-enumeration agreement, canonical-invocation
coverage, apply-idempotence, and verdict-field single-definition — not the Output field set). See G4.

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
- **Confirmed.** The residue it discloses is still real: `test_build_execute_factory.py:934`
  `test_a_real_plan_id_still_writes_the_work_log` monkeypatches only `factory.log_entry` (`:909-914`)
  and calls `_record_resolution(..., 'socket_absent', ...)`, which reaches `_update_fallback_streak`
  (`_build_execute_factory.py:387`) and reads/writes `home_root()/'marshalld'/'fallback-streak.json'`
  (`:218-249`). Nothing isolates it.
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
- **Refuses a closed epic.** `orchestrator.py:2254-2263`; `TestRefusals` and `TestCompactCli` both
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
| `script-shared` test-isolation flaw in `test_a_real_plan_id_still_writes_the_work_log` | **still open.** Verified by reading the test and `_update_fallback_streak`; nothing monkeypatches `home_root` or `_fallback_state_path`. Recorded as G5. |
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
