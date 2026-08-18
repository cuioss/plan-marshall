# Gaps — 180-orchestrator-cleanup-verb

**Source:** verification.md (same directory)   **Open items:** 5

The plan's core mechanism landed and holds under mutation: breaking the closed-epic guard and breaking
the between-markers write boundary each turned the plan's own tests RED (14 of 32 failing), so neither
the refusal nor the "a retraction survives verbatim" property is vacuous. The five items below are a
dead assertion, two doc-contract divergences of the exact archetype this epic exists to close, one
un-migrated lossy path, and one inherited residue the run disclosed but did not fix.

## G1 — Replace the tautological assertion in the narrative-survival test

- **Kind:** vacuous-test
- **Severity:** medium
- **Where:** `test/plan-marshall/plan-orchestrator/test_orchestrator_compact.py:369` —
  `TestNarrativeSurvivesVerbatim::test_every_hand_authored_section_survives_verbatim`
- **What is wrong:** the closing line is
  `assert after == text or after == _epic_text(plan_context)`. `after` was assigned from
  `_epic_text(plan_context)` two lines earlier and nothing writes the file in between, so the second
  disjunct is a tautology. Replacing the line with `assert after == text` alone makes the test fail
  (verified: 1 failed), proving the first disjunct is False in this fixture and the assertion is
  carrying no weight. The comment above it, "A second pass changes nothing at all", describes a second
  `_run()` the test never performs, and the comment on line 362 (`# after regeneration`) mislabels a
  read taken *before* `_run()`.
- **Why it matters:** a reader counts this test as covering idempotence-of-narrative; it does not. If
  `TestIdempotence` were ever weakened or deleted, the loss would be invisible here.
- **Fix:** perform the second pass the comment claims — call `_run()` again, re-read, and assert the
  bytes are identical to the post-first-pass read; or delete the disjunctive line and fix the two
  misleading comments, leaving the four `assert fragment in after` checks as the test's real content.
- **Done when:** the test contains no assertion whose truth is independent of the code under test, and
  every comment in it describes an operation the test actually performs.
- **Module/topic:** `plan-marshall` / `plan-orchestrator` tests

## G2 — Give an already-hand-annotated generated block a migration path, or name the loss in the report

- **Kind:** omission
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py:2018`
  — `_replace_block`; `.../workflow/cleanup.md:78-97` § Step 8 (Phase B);
  `.../persona-plan-orchestrator/standards/orchestration-model.md:249` (annotation-zone contract)
- **What is wrong:** the plan's D2 is explicit that a live block was found hand-annotated *between* the
  markers and that "pasting the verbatim output as-is would destroy information the annotations carry".
  The landed answer — an annotation zone outside the markers — solves this only for content written
  after the landing. For a ledger that already carries in-marker annotations, the first `compact` run
  overwrites them: `_replace_block` computes `before = lines[begin_idx + 1 : end_idx]` and then
  discards it, returning only `len(before)` and `len(new_lines)`. `cmd_compact` never surfaces the
  discarded text, and neither § Step 8 nor § Ledger-Compaction Stage contains a step to move in-marker
  annotations to the zone before the first compaction.
- **Why it matters:** the plan's own safety property is "a silent compaction is indistinguishable from
  a lossy one". A first pass on a real, hand-annotated epic is exactly a lossy compaction whose only
  trace in the report is a line-count delta — the failure mode this epic exists to close, reproduced
  inside the verb built to close it.
- **Fix:** either (a) add a `discarded[]` (or `replaced_body`) field to `cmd_compact`'s payload
  carrying the pre-write between-marker text for every block whose `outcome` is `regenerated`, so the
  operator can rescue an annotation from the report; or (b) add a step to `cleanup.md` § Step 8 that
  runs before the script call, instructing the orchestrator to move any hand-written line found between
  the markers into the adjacent `### Annotations` / `### Queue annotations` zone, and state the
  one-time migration in § Ledger-Compaction Stage. Option (a) also wants a test asserting the field is
  populated when a block changes.
- **Done when:** running `compact` on an epic whose generated block contains a hand-written line either
  preserves that line, or names its content (not merely its line count) in the emitted report — and a
  test in `test_orchestrator_compact.py` pins the behaviour.
- **Module/topic:** `plan-marshall` / `plan-orchestrator` — compact stage + cleanup workflow

## G3 — Declare `settled.md` in the orchestrator tree-layout contract and the carve-out enumeration

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:**
  `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md:22-35`
  (the epic tree-layout code block) and `:85` (§ Carve-outs, the ledger-document enumeration)
- **What is wrong:** the same standard mandates `settled.md` at `:253` ("a live-epic sibling of
  `history.md`") and `cleanup.md:82` links to `#carve-outs` when instructing the orchestrator to create
  it — but the tree-layout contract lists nine entries (`epic.md`, `status.json`, `history.md`,
  `references.json`, `workstreams/`, `plans/`, `landings/`, `inbox/`, `logs/`) and does not include
  `settled.md`, and `:85`'s parenthetical enumeration of "the orchestrator's ledger documents"
  (`epic.md`, workstream charters, plan specs, landing records, `history.md`, `references.json`) does
  not name it either. Re-derived by grepping `settled.md` across the whole tree: 17 sites, none of them
  the layout block or the carve-out list.
- **Why it matters:** the layout block is the binding statement of what an epic tree contains, and
  `:48` asserts the templates "mirror this layout contract one-to-one". A file the standard orders
  written but does not admit exists is a doc-contract divergence — the archetype this epic files
  against everyone else — and a future audit of tree contents would flag `settled.md` as an
  unrecognised artifact.
- **Fix:** add a `settled.md` row to the layout code block between `history.md` and `references.json`,
  commented as "Relocated settled narrative (written mid-life by the compact stage; pointers in
  epic.md resolve here)", and add `settled.md` to the ledger-document parenthetical at `:85`.
- **Done when:** `settled.md` appears in the tree-layout code block and in the § Carve-outs
  ledger-document list in `orchestration-model.md`.
- **Module/topic:** `plan-marshall` / `persona-plan-orchestrator` standards

## G4 — Carry the compaction stage's report fields into the `cleanup` verb's Output contract

- **Kind:** doc-drift
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/cleanup.md:97`
  (the instruction) versus `:154-172` (the `## Output` TOON block)
- **What is wrong:** line 97 says "fold the stage's `regenerated[]`, `invariants[]`, and `abstained[]`
  into this report". The canonical Output block declares `ledger_compaction: compacted` and no key for
  any of the three; it declares `regrounded[]`, `applied[]`, and `declined[]` only. An implementer
  working from the Output block — which is where a verb's emission contract is normally read — emits a
  compaction line naming no mutation and no abstention. No test covers this: `test_cleanup_contract.py`
  checks router closure, verb-enumeration agreement, canonical-invocation coverage, apply-idempotence,
  and verdict-field single-definition, but not the Output block's field set.
- **Why it matters:** the plan's Verification section states D4's requirement as "a report that lists
  only what changed cannot distinguish 'nothing needed touching' from 'the verb could not see it'". The
  script satisfies that; the verb that wraps it does not, so the operator-facing report — the one a
  human actually reads — can legally omit both.
- **Fix:** add the three keys to the `## Output` block with the same shapes the script emits
  (`compaction_regenerated[R]{surface,outcome,lines_before,lines_after}`,
  `compaction_invariants[I]{invariant,verdict,evidence,population}`,
  `compaction_abstained[A]{section,treatment}`), and state that each is required-never-omitted, as
  `declined[]` already is at `:176`.
- **Done when:** `cleanup.md`'s `## Output` block declares a key for each of `regenerated[]`,
  `invariants[]`, and `abstained[]`, and line 97's instruction names those keys.
- **Module/topic:** `plan-marshall` / `plan-orchestrator` — cleanup workflow doc

## G5 — Isolate the machine-global fallback-streak store in the `script-shared` build-factory test

- **Kind:** bug (test isolation)
- **Severity:** medium
- **Where:** `test/plan-marshall/script-shared/test_build_execute_factory.py:934` —
  `test_a_real_plan_id_still_writes_the_work_log` (helper at `:909`
  `_capture_log_entries`)
- **What is wrong:** inherited residue that `report-01.md` disclosed and did not fix; still open at
  HEAD. The test monkeypatches only `factory.log_entry`, then calls
  `_record_resolution('auto', 'in_process', 'socket_absent', 'n', 'a-real-plan')`. `socket_absent` is
  in `_DEGRADED_ROUTING_REASONS`, so `_update_fallback_streak`
  (`marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py:387`)
  reads and writes the machine-global `home_root()/'marshalld'/'fallback-streak.json'`
  (`:218`, `:242`). After `_FALLBACK_WARN_STREAK` (3) consecutive runs, `suppress_repeat` becomes True,
  the work-log write is correctly suppressed, and `assert len(written) == 1` fails on state the test
  itself wrote.
- **Why it matters:** a full in-session suite run repeated more than three times turns the build gate
  red on a test the diff never touched, and the red gate points at the wrong cause — a run that took it
  at face value would rescope a blameless diff. It is green on a fresh CI checkout, which makes it
  invisible until it bites a local or cloud session.
- **Fix:** in the test (or an autouse fixture for its class), `monkeypatch` `factory.home_root` — or
  `factory._fallback_state_path` — to a `tmp_path`-rooted directory so each test starts from an absent
  streak file. Apply it to the whole `TestRecordResolution`-family class, not only this one test, since
  every `_record_resolution` call with a degraded reason mutates the same store.
- **Done when:** running `test_build_execute_factory.py` three or more times in one session leaves
  `~/.plan-marshall/marshalld/fallback-streak.json` unmodified and the test passes on every run.
- **Module/topic:** `plan-marshall` / `script-shared` — build execute factory tests
