# Verification — 240-deep-lane-bought-by-one-signal-while-the-discriminating-field-is-null

**Verified against:** commit `ac06e4fc94782328f87d1395472a72b7e7a8559d`   **Landed as:** PR #1188, commit `01e8c8f8025117690d613bce2b822df44ac72e50`   **Verdict:** implemented-with-gaps

## Method

What was actually done, in order:

- Read `plan.md` and `report-01.md` in full.
- Located the landed squash commit (`git log --all --grep '#1188'` → `01e8c8f8`) and read its
  `--name-status` / `--stat`: five paths — `plan.md` (R100 rename into the plan directory),
  `report-01.md` (A), `manage-status/SKILL.md` (M), `manage-status/scripts/_cmd_planning_lane.py`
  (M, +197/−25 — re-derived with `git show --numstat`; the commit's whole-diff totals are +891/−29), `test/plan-marshall/manage-status/test_planning_lane_corroboration.py` (A, 429
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
| D2 | Require corroboration for prose-only routing | chosen rule implemented **and** rejected alternative recorded | yes | yes | **partly — see G2** | yes | `_cmd_planning_lane.py:704-714` (`scope_resolved_noncommittal` + `fired == ['S7:risk_prose']` ⇒ suppress); rejected lever (provenance-exemption) recorded in report § Design decisions and in the module comment `:696-699` and `SKILL.md:965`. Verify-first discharged: `_RISK_PROSE_RE` at `:185-189` scores semantic vocabulary (`multi-PR`, `codebase-wide`, `largest`, `riskiest`, `expect a split`, `foundation`, `campaign`, prose `epic`), not the ⛔/⚠/⭐ markup — corroborated by the eight-phrase `_WARNING_SENTENCES` list at `test_planning_lane_risk_prose.py:69-78`. Mutation M2 shows the guard is live. **But** the "resolved contradicting signal" includes the zero-evidence `pathless_non_empty_body` band, and the residue is a set-complement that admits every unrecognised band value (G2 — re-severitied `high` on adversarial review — and G5) |
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
  "lines ~172-176" — the figure re-derives at neither surface: it is `185-189` at HEAD **and** at the
  landed commit itself (`git show 01e8c8f8:…` → line 185). The intermediate commit it must have been
  read from was squashed at merge, so the figure cannot be re-derived at all; it is unsourced, not
  merely drifted. And
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
- ~~**The "9 files, +2,083 / −16" realized footprint.**~~ **Located and CONFIRMED on adversarial
  review.** The commit is reachable without knowing the plan's name: scanning every commit's
  `--numstat` for the exact triple returns a **unique** match — `967ba03f5` *"fix(phase-6-finalize):
  bind pre-merge barrier override to the HEAD it was granted against (#1077)"*, `9 files changed,
  2083 insertions(+), 16 deletions(-)`. The plan's OBSERVED footprint claim is therefore verified, and
  the over-routed plan is identifiable as #1077.
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

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked.** Every `high`/`medium` gap, every clean-pass row in the deliverable table, and every
"swept, clean" claim, by these means:

- **Re-derived figures.** The landed commit's `--numstat` (`+197/−25` on `_cmd_planning_lane.py`, not
  the `+222/−29` stated — corrected above); the five landed paths; `01e8c8f8` as the newest commit on
  `_cmd_planning_lane.py`; the 429-line test file; `12` `def test_` and `12 passed`; `685 passed` for
  `test/plan-marshall/manage-status/`; `_WARNING_SENTENCES` = exactly 8 entries at
  `test_planning_lane_risk_prose.py:69-78`, one per `_RISK_PROSE_RE` alternative; the
  `_RISK_PROSE_RE` line number at HEAD **and** at the landed commit (185 at both — the report's
  "~172-176" is unsourced, not drifted); `phase-1-init/SKILL.md:827` and `:297`;
  `manage-status.py:699-708`; `manage-status/SKILL.md:945,951,965,967,988-994`;
  `audit.py:1978-1983`. Two gap line references did not re-derive and were corrected in `gaps.md`
  (G1's test citation `:225-241` → `:214-233`; G2's comment citations `:216-219` → `:216-218` and
  `:702-704` → `:701-704`).
- **Functions executed** (`uv run python`, importing the module through `conftest.load_script_module`),
  not read: `evaluate_signals_pure` on the recorded vector pre- and post-bridge, on a bridged vector
  with `change_type` set, on a free-form plaintext vector, and on eight `scope_estimate` values
  including two out-of-enum ones; `classify_scope_pure` / `_request_is_concrete` /
  `_request_has_risk_prose` on a pathless fenced-block body carrying `codebase-wide` + `riskiest`; and
  `classify_scope_pure` on a 100 000-character line to reach the `scan_incomplete` row.
- **The producer was run, not assumed.** `_documents_core.render_template` was executed against the
  real `manage-plan-documents/templates/request.md` with and without `source_id`, and
  `_REQUEST_SOURCE_RE` / `_REQUEST_SOURCE_ID_RE` run over the result. The bridge resolves the real
  template's output and correctly declines the placeholder-stripped plain-text shape — D3(b) is not
  vacuous against a hand-shaped fixture. `phase-1-init/SKILL.md:417-421` confirms
  `--source description --source-id`, and `plan-orchestrator/{templates/plan-spec.md:70,
  workflow/orchestrate.md:82,152, workflow/analyze.md:214}` confirm the single emitted
  `implement {path}` shape, so D0's *categorical* generalisation holds rather than being asserted.
- **Mechanism clauses confirmed at their own file and symbol.** The report's D3(b) lever rationale
  ("writing `status.metadata.plan_source` would activate phase-2-refine Step 13.5 for the whole
  orchestrated population") is **supported**: `phase-2-refine/SKILL.md:265,290` gate on "`plan_source`
  present and not the literal `recipe`", so a spec-path value would activate it. The S1⊂S5 argument
  re-derives from `:644-648`. A tree-wide `plan_source` sweep across `marketplace/bundles/` found no
  seeding site outside phase-1-init Steps 5b.5/5c and the recipe workflow, so the "never bridged"
  diagnosis holds.
- **Three mutations**, each preceded by `git diff --quiet` (exit 0), each restored by copying back a
  byte snapshot taken beforehand and re-verified with `git diff --quiet` (exit 0) — never
  `git checkout`/`restore`/`stash`. **M1** `lane = LIGHT`: 3 red, including `test_d3d_control…` — the
  control has teeth against a globally de-escalating fix. **M2** corroboration disabled: exactly 2 red
  (`test_d3a…`, `test_recorded_case_end_to_end_routes_light`), 683 green — the D2 guard is live and the
  report's "other 10 stayed green" re-derives. **M3** G1's own proposed threshold
  (`signals_null >= 3`): **685 passed, nothing red** — no existing test pins the `low_confidence`
  predicate in either direction.
- **Sweeps re-run with broader patterns than the originals.** The residue sweep was re-run as
  `context (helper|gather)|outline[- ]phase context|can never succeed` over `doc/plans/` (still only
  this plan's own three files). G4's site list was re-derived with a tree-wide
  `deep-precondition|forces deep` over `marketplace/bundles/` **and** `.claude/`, which surfaced two
  further occurrences the gap had not named (`manage-config/standards/data-model.md:576`,
  `manage-status/SKILL.md:1149`) — both already qualified in place, so G4's scope survives and its text
  now says so.

**Not re-checked.** `./pw verify` (19,243 passed / 14 skipped) — still not re-run; the
`manage-status` subset was run instead. All PR-side facts (reviewer participation, merge-gate
conditions, "no inline review threads"). The three squashed intermediate commits. The archived decision
log under `.plan/`. The mutation check remains confined to `_cmd_planning_lane.py`.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| G1 | `low_confidence` is unreachable "in the standard phase-1-init flow" | **upheld, rewritten** (severity `medium` held) | Executed: bridged recorded vector → `{resolved 4, null 3, low_confidence False}`. But the scope claim was over-broad — a free-form plaintext request (`plan_source` null, `scope_estimate` resolved, 4 nulls) executes to `low_confidence True`, so the flag is not dead in general. Rescoped to the orchestrated population. Test citation `:225-241` corrected to `:214-233`. M3 shows the proposed threshold is drop-in (685 green) |
| G2 | Zero-evidence `single_module` band corroborates against S7 | **upheld, re-severitied `medium` → `high`, two clauses corrected** | Executed: pathless fenced body + "codebase-wide … riskiest" → `single_module` / `pathless_non_empty_body` / `distinct_path_count 0` → `lane=light`, `suppressed=['S7:risk_prose']`. Pre-fix that request routed `deep`, so this change shipped a false negative into the seam whose prior fix (#1068) closed one — the plan's own "the two must not fight" constraint. `high` because D3(d), the plan's designated guard against a de-escalating fix, passes against it (its vector fires S1–S5, so the corroboration branch is unreachable for the control). The `(or scan_incomplete)` clause in Fix and Done-when was **refuted and removed**: `scan_incomplete` bands `multi_module` (`:523-524`, executed), which fires S2, so it can never reach the singleton branch — the test it demanded was unwritable. Added the three shipped doc sites the defect falsifies |
| G3 | Test name contradicts its assertion | **upheld unchanged** | `test_planning_lane_corroboration.py:89` is exact; the function asserts `lane == 'light'` and never runs a pre-fix router. Kind `doc-drift` / severity `low` are right — it is a naming defect with no behavioural consequence |
| G4 | CLI `description` states an unqualified predicate | **upheld, scope widened** | `manage-status.py:699-708` re-derived exactly (the literal grep misses it only because the sentence is split across two string fragments at `:702-703`). Broader tree sweep found two more occurrences, both qualified in place; the argparse blob remains the only self-contained one. `low` is right — a help string nobody's behaviour keys on |
| G5 | *(new)* Corroboration residue is a set-complement | **added** | Executed on S7-alone vectors: `'module_pair'`, `''` and `' single_module'` all route `light` with S7 suppressed, refuting the shipped comment at `:700-701` ("residue is exactly `{single_module}` … adapts automatically if the band set changes"). Fails **open** in the de-escalating direction. `medium`: the false comment is present-tense, the behavioural exposure is latent behind the closed enum |
| Verdict | `implemented-with-gaps` | **upheld** | All four deliverables are implemented and live (M1/M2 confirm D2 and D3(d) are non-vacuous); every gap is a correctness-partial inside a delivered deliverable, not an absent one. A `high` gap does not by itself demote the verdict to `partially-implemented` — that label is for an unimplemented deliverable |
| Footprint claim | "not verifiable from this clone" | **refuted** | A `--numstat` scan of all history for `9 files / +2083 / −16` returns a **unique** match: `967ba03f5` (#1077, `fix(phase-6-finalize)`). The plan's OBSERVED claim is confirmed and the over-routed plan is named |
| Report figure `+222/−29` | landed diff on `_cmd_planning_lane.py` | **corrected** | `git show --numstat 01e8c8f8` → `197 / 25`. The stated pair conflated `--stat`'s combined-change count (222) with the commit's whole-diff deletions (29) |

**Documents corrected.**
`gaps.md`: open items **4 → 5**; G2 re-severitied to `high`, its unreachable
`scan_incomplete` requirement removed, its false-documentation sites added, two line references fixed;
G1 rescoped to the orchestrated population with the free-form counter-case stated, its test citation
fixed, and the M3 mutation result recorded; G4's sweep basis widened and stated; **G5 added**; a
`## Refuted during adversarial review` section records the one refuted clause and the fact that no whole
gap was refuted.
`verification.md`: the `+222/−29` figure corrected to `+197/−25`; the `_RISK_PROSE_RE` line-drift
*explanation* replaced (it attributed the drift to squashed nit commits, but the number is 185 at the
landed commit too, so the figure is unsourced rather than shifted); the D2 table row now points at G5
as well and flags G2's new severity; the realized-footprint entry moved out of "could NOT be verified"
and into a confirmed identification of commit `967ba03f5` / PR #1077.

**Residual doubt — what a third reviewer should look at first.**

1. **`_read_request_body`'s title strip never fires on a script-created `request.md`.**
   `templates/request.md` opens with a two-line HTML comment, so `lines[0]` is that comment and
   `_REQUEST_TITLE_RE.match(lines[0])` (`:321`) fails — verified by executing the real
   `render_template`. The document's own `# Request: {title}` line is therefore scored as request
   narrative by both S5 and S7, so a plan whose *title* contains `campaign`, `epic`, `foundation` or
   `largest` fires S7 from chrome. This predates #1188 (the line-1 anchor arrived in `ef80c1c8`) and is
   not a defect in what this plan shipped, so it is **not filed as a gap here** — but it is the same
   sensor, and it is the most consequential thing this review found outside the plan's scope.
2. **The premise, now that #1077 is identified.** The over-routed plan is a 9-file, +2,083-line change
   that added three test files. That is a large realized footprint, which weakens — without refuting —
   the framing that `deep` was *wrong* rather than merely bought for the wrong reason. The plan's own
   argument survives (a 1-of-4 signal decision is unreadable regardless of whether it landed on the
   right lane), but a reviewer sizing the epic's payoff should re-open this.
3. **G2 and G5 interact.** Both narrow the same branch, and fixing G2 by requiring
   `band_rule == 'path_count_middle_band'` would incidentally close most of G5. They are filed
   separately because the fixes are independent (one adds a parameter, one replaces a set-complement
   with an allowlist) and a partial fix of either leaves the other live — but they should be
   implemented together and re-tested as one.
