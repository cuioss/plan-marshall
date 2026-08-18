# Verification — 240-deep-lane-bought-by-one-signal-while-the-discriminating-field-is-null

**Verified against:** commit `ac06e4fc94782328f87d1395472a72b7e7a8559d`   **Landed as:** PR #1188, commit `01e8c8f8025117690d613bce2b822df44ac72e50`   **Verdict:** implemented-with-gaps

## Method

What was actually done, in order:

- Read `plan.md` and `report-01.md` in full.
- Located the landed squash commit (`git log --all --grep '#1188'` → `01e8c8f8`) and read its
  `--name-status` / `--stat`: five paths — `plan.md` (R100 rename into the plan directory),
  `report-01.md` (A), `manage-status/SKILL.md` (M), `manage-status/scripts/_cmd_planning_lane.py`
  (M, +222/−29… net), `test/plan-marshall/manage-status/test_planning_lane_corroboration.py` (A, 429
  lines).
- Confirmed `git log --oneline -- .../_cmd_planning_lane.py` shows `01e8c8f8` as the newest commit on
  that file — nothing later superseded the change.
- Opened at HEAD: `_cmd_planning_lane.py` (module docstring, `_RISK_PROSE_RE`,
  `_resolve_orchestrator_plan_source`, `_request_is_concrete`, `_request_has_risk_prose`,
  `classify_scope_pure`, `evaluate_signals_pure`, `_evaluate_signals`, `cmd_planning_lane_route`),
  `manage-status/SKILL.md` (§ planning-lane, the TOON sample, the Scripts table row),
  `manage-status/scripts/manage-status.py` (the `planning-lane` argparse `description`),
  `phase-1-init/SKILL.md` (Step 4 pointer detection, Step 5/5.1, Step 5b.5, Step 5c, Step 8a.5,
  Step 8b), `manage-plan-documents/templates/request.md`,
  `manage-plan-documents/scripts/_cmd_request.py`,
  `manage-plan-documents/scripts/_documents_core.py::_cleanup_unreplaced_placeholders`,
  `test_planning_lane_risk_prose.py`, and the downstream consumer
  `.claude/skills/audit-archived-plan-retrospectives/{checks/track-selection-accuracy.md,scripts/audit.py}`.
- Ran `uv run python -m pytest test/plan-marshall/manage-status/test_planning_lane_corroboration.py
  -o addopts="" -q` → **12 passed** (the report's "12 tests" figure re-derived by counting `def test_`
  and by the pytest count).
- Ran `uv run python -m pytest test/plan-marshall/manage-status/ -o addopts="" -q` → **685 passed**
  (no regression in the sibling lane suites, including the prior false-negative fix's
  `test_planning_lane_risk_prose.py`).
- **Executed** `evaluate_signals_pure` on four vectors through a throwaway probe test (written into
  `test/plan-marshall/manage-status/`, run, then deleted; `git status --porcelain` confirmed clean
  afterwards) rather than reading the code:
  - recorded vector pre-bridge → `lane=light`, `fired=[]`, `suppressed=['S7:risk_prose']`,
    `confidence={total 7, resolved 3, null 4, low_confidence True}`.
  - recorded vector **post-bridge** (`plan_source` resolved) → `lane=light`,
    `confidence={resolved 4, null 3, low_confidence False}`.
  - a pathless body with a fenced block plus `codebase-wide` / `riskiest`:
    `classify_scope_pure` → `single_module`, `band_rule=pathless_non_empty_body`,
    `distinct_path_count=0`; `evaluate_signals_pure` → `lane=light`,
    `suppressed=['S7:risk_prose']`.
- **Two mutations** applied to `_cmd_planning_lane.py`, each preceded by `git diff --quiet` (exit 0 —
  no concurrent modification), each snapshotted to the scratchpad by byte copy and restored by copying
  the snapshot back (never `git checkout`/`restore`/`stash`), each verified restored by
  `git diff --quiet` (exit 0):
  - **M1 — hardwire `lane = LIGHT`** (the plan's named failure mode "a fix that only ever
    de-escalates"): the D3(d) CONTROL went **RED** (`assert 'light' == 'deep'`), along with the two
    other deep-asserting cases. The control has teeth.
  - **M2 — disable the corroboration branch** (`if False:`): `test_d3a_recorded_vector_does_not_route_deep`
    and `test_recorded_case_end_to_end_routes_light` went **RED** (`- light / + deep`), the other 10
    stayed green. The D2 guard is not vacuous.
- Did **not** re-run `./pw verify` (the report's 19,243-passed figure) — out of proportion for this
  check; the manage-status subset was run instead.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | GATE: derive why `plan_source` is null for an orchestrator-launched plan | the break located by symbol and named; generalisation derived; ordering-vs-scoring verdict explicit | yes (diagnostic) | yes | yes | yes | `phase-1-init/SKILL.md:297` (file-pointer branch calls `request create --source-id "{spec_path}"`), `:483` Step 5b.5 and `:625` Step 5c are the only two `plan_source` seeds and are `lesson`/`recipe`-only; `_cmd_planning_lane.py:779` reads `metadata.get('plan_source')`. Generalisation holds: every orchestrator launch takes the file-pointer branch, which has no seeding analogue. Ordering-vs-scoring verdict stated in report § D0 and re-derived here: `s1_deep = free_form_source and s5_deep`, `s5_deep = not request_concrete`, recorded `request_concrete=True` ⇒ S1 could not fire ⇒ the deep verdict was S7-only ⇒ the scoring change is correctly targeted |
| D1 | Make an unresolved signal visible in the decision | route record states resolved-vs-null counts | yes | yes | **partly — see G1** | yes | `_cmd_planning_lane.py:726-745` (`confidence` block), `:756` (returned), `:930-934` (decision-log line), `:948` (route return); `SKILL.md:967` + TOON sample `:988-994`. Asserted-absence claim verified: `git show 7201f8d2:…_cmd_planning_lane.py` route return carried only `scope_provenance` — no prior confidence field. **But** the derived `low_confidence` boolean is structurally unreachable for the orchestrated population (G1) |
| D2 | Require corroboration for prose-only routing | chosen rule implemented **and** rejected alternative recorded | yes | yes | **partly — see G2** | yes | `_cmd_planning_lane.py:704-714` (`scope_resolved_noncommittal` + `fired == ['S7:risk_prose']` ⇒ suppress); rejected lever (provenance-exemption) recorded in report § Design decisions and in the module comment `:696-699` and `SKILL.md:965`. Verify-first discharged: `_RISK_PROSE_RE` at `:185-189` scores semantic vocabulary (`multi-PR`, `codebase-wide`, `largest`, `riskiest`, `expect a split`, `foundation`, `campaign`, prose `epic`), not the ⛔/⚠/⭐ markup — corroborated by the eight-phrase `_WARNING_SENTENCES` list at `test_planning_lane_risk_prose.py:69-78`. Mutation M2 shows the guard is live. **But** the "resolved contradicting signal" includes the zero-evidence `pathless_non_empty_body` band (G2) |
| D3 | Tests (a)–(d), each verified red pre-fix | all four pass, each seen red first | yes | mostly — see below | yes | yes | `test_planning_lane_corroboration.py` — 12 tests, all pass. (a) `test_d3a_recorded_vector_does_not_route_deep`, (b) `test_d3b_orchestrator_spec_resolves_plan_source_nonnull`, (c) `test_d3c_several_nulls_reported_low_confidence`, (d) `test_d3d_control_deep_warranting_vector_still_routes_deep`. Red-first re-derived independently by mutation M1 (control red) and M2 ((a) red). One test is misnamed — G3 |

### D1 — the counts are right, the flag is not (G1)

`evaluate_signals_pure` (`_cmd_planning_lane.py:736-745`) counts nulls over a seven-member `signals`
dict in which two members (`request_concrete`, `risk_prose`) are booleans that are never `None`. So
`low_confidence = signals_null > signals_resolved` can only be true when at least **4** of the 5
nullable fields are null. Two facts close that door for the population this plan exists for:
`scope-estimate-heuristic` "never leaves its field unset" (`phase-1-init/SKILL.md:827`), so
`scope_estimate` is always resolved before the route; and this plan's own D3(b) bridge resolves
`plan_source` for every orchestrator-launched plan. That leaves at most three nullable fields
(`change_type`, `compatibility`, `planning_lane_override`) and therefore `low_confidence: false`
unconditionally for orchestrated plans. Executed against the plan's own motivating vector post-bridge:
`{'signals_resolved': 4, 'signals_null': 3, 'low_confidence': False}`. The plan's Verification section
asked for exactly this cold read ("show the Step 6 verification sub-agent a route record with three
nulls and ask how confident the decision was. If it reads as confident, the new field is not doing its
job") — the report records no such cold read, and the implementation answers "confident".
D1's literal *done-when* ("the route record states resolved-versus-null counts") is nonetheless met:
the counts and the `null_signals` list are on the return and on the decision-log line.

### D2 — the corroborating "resolved scope estimate" can be a band derived from zero evidence (G2)

The corroboration requires `scope_estimate` to be resolved and to sit in the residue band
`single_module`. But `classify_scope_pure` (`_cmd_planning_lane.py:534`) assigns `single_module` with
`band_rule='pathless_non_empty_body'` to any non-empty body in which **no path at all** was found, and
`_request_is_concrete` (`:326-343`) returns True on a bare fenced code block with no path. Executed:
a body containing a fenced block plus "This change is codebase-wide and is the riskiest thing we have
shipped" bands `single_module` (`distinct_path_count: 0`, `band_rule: pathless_non_empty_body`),
scores `request_concrete=True`, `risk_prose=True`, and routes **light** with S7 suppressed. The module
elsewhere states its own conservative direction — "inflation only ever pushes the band UP … the error
mode is conservative (more planning ceremony), never a silent narrowing" (`:216-219`) — and the
`scope_provenance.band_rule` that would distinguish a measured middle band from a no-evidence one is
computed in `_evaluate_signals` (`:793`) but attached *after* `evaluate_signals_pure` has already
decided, so the pure scorer cannot see it.

### D3 — one test's name contradicts what it asserts (G3)

`test_recorded_vector_routes_deep_without_the_corroboration_fix`
(`test_planning_lane_corroboration.py:89`) asserts `result['lane'] == 'light'` and does not run against
a pre-fix router at all — it flips `risk_prose` off on the recorded vector. The name states the
opposite of the assertion.

## Report accuracy

Re-derived, and **contradicted**:

- None of report-01.md's substantive claims is contradicted by the tree. Specifically re-derived and
  confirmed: the 12-test count; the "3-of-7 resolved, 4 null" figure for the recorded vector
  (executed); the asserted-absence check ("the route record carried no prior signal-resolution field")
  against `git show 7201f8d2:…` — the pre-fix return carried `fired_signals`, `signals`,
  `execution_profile`, `profile`, `scope_provenance`, `persisted`, `classification_validation` and
  nothing confidence-shaped; "no existing S7 test is modified" (the landed `--name-status` touches five
  paths, none of them `test_planning_lane_risk_prose.py`); "confirmed against
  `test_planning_lane_risk_prose.py`'s eight-phrase parametrization" (`_WARNING_SENTENCES` has exactly
  8 entries, one per `_RISK_PROSE_RE` alternative); the D3b lever ("router-side resolution, not
  write-time seeding") — `_resolve_orchestrator_plan_source` performs no write and
  `cmd_planning_lane_route`'s `--persist` branch writes only `planning_lane` /
  `execution_profile` / `planning_lane_override`; the S1⊂S5 lane-neutrality argument
  (`s1_deep = free_form_source and s5_deep` ⇒ `s1_deep ⇒ s5_deep`, and since S1 never fires alone the
  bridge cannot create or destroy the `fired == ['S7:risk_prose']` singleton either).
- Two trivial figure drifts, neither material: the report cites `_RISK_PROSE_RE` at
  "lines ~172-176" (actual `185-189` at HEAD — the three post-review nit-fix commits shifted it), and
  the report's own § D0 prose "of D0's three candidate breaks" is accurate while the *plan's* prose
  "three of the seven signals are `None`" undercounts the four the code reports (the report itself
  flags this as an observation).
- One **silence**, not a contradiction: the plan's claim table required the OBSERVED footprint claim
  ("9 files, +2,083 / −16 … the squash commit — this one IS reachable via git; verify it") to be
  verified. The report never mentions it. See § What could NOT be verified.
- One **silence** against the plan's Verification section: the D1 cold read on a three-null route
  record was prescribed and is not recorded as performed. Given what the implementation actually
  reports for such a record (§ D1 above), this is the check that would have caught G1.
- The report's Findings table records the `manage-status.py` argparse-help staleness as an
  "Observation … no action". The tree confirms the text is still there and now understates the
  predicate by two carve-outs rather than one (G4).

## Out-of-scope compliance

Clean. The landed diff touches exactly five paths and every source path is inside the plan's declared
Expected surface (`manage-status/**` plus tests). No `phase-1-init/**` change (the run chose a
router-side bridge and recorded that choice, which is the "keep the fix inside the defective
component" reading of the surface), no `marshall-orchestrator/**` change, no change to how
orchestrator specs are written, no retuning of `_RISK_PROSE_RE` thresholds (the two explicitly
out-of-scope levers), and no work on the excluded "context helper" item. The `plan.md` R100 rename is
the plan-directory lifecycle step, not a collateral edit. No undeclared collateral change found.

## Residue carried forward

| Declared in report-01.md § Residue | Still open at HEAD? |
|---|---|
| Owed work: the "context helper that can never succeed at the outline phase for worktree-using plans" deserves its own plan | **Still open.** `grep -rl "context helper" doc/plans/` matches only this plan's own `plan.md` and `report-01.md`; no successor plan directory exists under `doc/plans/truthful-signals/`. It is recorded, as the plan required, but unowned |
| Sibling plan quantifying the same run from the metrics-renderer side; surface-disjoint | Not contradicted — no metrics-renderer file appears in this plan's landed diff |

Two further items are residue this verification adds rather than the report's:

- `status.metadata.plan_source` is still null for every orchestrator-launched plan; the fix is
  read-time and router-local by design. The one downstream consumer that reads the field directly,
  `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py:1978-1983`
  (`plan_source=inputs.recipe_key`), therefore still scores orchestrated plans as free-form. Impact on
  its verdict is nil (S1⊂S5 again, and the audit passes no `risk_prose`), so this is noted, not filed.
- That same audit counterfactual omits `risk_prose` entirely, so it cannot reproduce a suppressed-S7
  verdict — i.e. the `track-selection-accuracy` check would not have flagged the very over-route this
  plan fixes. That gap predates #1188 (it arrived with S7 in #1068) and is not this plan's to close.

## What could NOT be verified

- **The recorded route entry and its seven signal values, and the `single_module` scope resolving
  seconds before the route.** Both live in the archived decision log under `.plan/`, which is
  git-ignored and absent from this clone — exactly as the plan's claim table anticipated. The vector
  was verified only as *transcribed* in `plan.md` and replayed from that transcription.
- **The "9 files, +2,083 / −16" realized footprint.** The plan calls it reachable via the squash
  commit, but neither `plan.md` nor `report-01.md` names the over-routed plan or its PR, so the commit
  cannot be located from this clone. Neither confirmed nor refuted.
- **The three intermediate commits** (`567c703`, `a80ae4c`, `1ec3b77`) named in report-01.md. They were
  squashed at merge; `git cat-file -e` on them is moot in a clone without the PR branch. The *content*
  they are said to carry is present at HEAD, which is what matters.
- **`./pw verify` — 19,243 passed / 14 skipped in 431s.** Not re-run (disproportionate). The
  `manage-status` subset was run instead: 685 passed.
- **PR-side claims** — reviewer participation (`cuioss-review-bot` reviewed clean; `coderabbitai` and
  `sourcery-ai` rate-limited), the merge-gate conditions, and "no inline review threads existed on any
  surface". These are GitHub-side facts, not tree facts.
- **The mutation check was applied to `_cmd_planning_lane.py` only.** No other file in the landed diff
  carries a guard worth mutating. No file was skipped for concurrent modification — `git diff --quiet`
  returned 0 before each mutation and after each restore.
