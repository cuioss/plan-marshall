# Verification — 050-migration-shims-have-no-expiry

**Verified against:** commit `ac06e4fc94782328f87d1395472a72b7e7a8559d`   **Landed as:** PR #1153, commit `1296ede1e5afc37431b4e5002dc6f38e5fb5811e`   **Verdict:** implemented-with-gaps

## Method

What was actually done, in order:

1. Read `plan.md` and `report-01.md` in full.
2. Located the landed commit. `git log --grep '#1153'` returned nothing (the clone is shallow, graft
   root `87c677bb`); `git log -- <analyzer path>` found `1296ede1` — *feat(shims): give
   migration/back-compat shims an owner, floor, and removal trigger (truthful-signals/050) (#1153)*,
   28 files, 1347 insertions, 0 deletions. Read the full `--stat` and the `_runner.py` hunk.
3. Opened every artifact named by the deliverables at HEAD:
   `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/standards/shim-marker-convention.md`,
   its `SKILL.md` § 8 pointer,
   `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_shim_marker.py`
   (all 483 lines), `_runner.py` (`run_quality_gate` and `run_analyze_marketplace_rules`),
   `_rule_registry.py`, `references/rule-catalog.md`, `references/rule-provenance.md`,
   `test/pm-plugin-development/plugin-doctor/test_analyze_shim_marker.py` (all 350 lines),
   `_fixtures.py`, `test_runner.py`.
4. Re-derived the marker inventory at HEAD: 6 `# SHIM(A):` + 19 `# SHIM(B):` in production scripts
   (plus 2 doc-example occurrences inside the analyzer itself). Re-derived the landed inventory from
   the commit diff: exactly 5 `SHIM(A)` + 19 `SHIM(B)` = 24.
5. **Executed the detector on the real tree** (`enumerate_script_files` + `analyze_shim_marker` over
   `marketplace/bundles`): **population 412, findings 0**.
6. **Ran the plan's own test file**: `uv run python -m pytest
   test/pm-plugin-development/plugin-doctor/test_analyze_shim_marker.py -o addopts="" -q` →
   **28 passed**.
7. **Recall mutation sweep (non-destructive).** For each of the 25 marker anchors in production
   scripts, stripped *that one* marker block (anchor + its three field lines) into a temp copy and
   re-ran `_scan_file` on it. Result: **4 fire, 21 stay silent.**
8. **Destructive mutation + restore.** Saved `_cmd_mark_step.py` bytes to the scratchpad, inserted
   `# tolerate a pre-migration key shape here` at line 1, ran the plan's own real-tree test →
   `test_real_marketplace_tree_produces_zero_findings` **FAILED** with a `shim_unmarked` finding at
   line 1 (the guard is live, not inert). Restored from the saved bytes (28008 bytes, byte-identical),
   re-ran the file → **28 passed**, and `git status --porcelain` shows `_cmd_mark_step.py` unmodified.
9. Re-derived the landing-time population from git: `git ls-tree -r 1296ede1` → **387** scripts under
   `bundles/*/skills/*/scripts/**.py`; at `1296ede1^` → **386**.
10. Verified the two OBSERVED claims first-party: `legacy_string_entry` exists in `_cmd_mark_step.py`
    (lines 363, 563); `_read_status_created` (`manage-metrics.py:2709`) contains no "older
    orchestrator versions" phrase and documents *"missing status.json, malformed JSON, missing
    'created' key, non-string value all return None"*.
11. Independent sweep for shim vocabulary in comments across the whole script population, excluding
    marker lines, and read every strong candidate by symbol (`_manifest_decide.py`,
    `_manifest_lanes.py`, `_config_core.py`, `_cmd_quality_phases.py`, `analyze-logs.py` WARN→WARNING,
    `_cmd_lifecycle.py`, `inject_project_dir.py`, `merge_lock.py`, `permission_fix.py`).
12. Verified the convention doc's two outbound cross-references rather than trusting them: the
    phase-3-outline "clean break vs deprecation shim" decision table exists
    (`outline-workflow-detail.md:806-807`) and `SIMPLICITY_BACKWARD_COMPAT_REEXPORT` exists
    (`_analyze_simplicity.py:52`).

Note: the working tree carried three unrelated uncommitted modifications from a concurrent session
(`_display_time.py`, `effort_presets.py`, `git-workflow.py`). None touches a shim marker; the
`effort_presets.py` diff deletes three lines in `_LEGACY_PRESETS` classification, well away from its
`SHIM(A)` block at line 233. Results above were computed against that state. The adversarial review
below re-ran every measurement at `9afba956` with those modifications gone; `git log ac06e4fc..HEAD
-- marketplace/ test/` is empty, so the scanned tree is byte-identical and every figure reproduced
unchanged.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | GATE: re-derive the inventory, population-derived | derived inventory + method stated + survived/dropped/new partition reported | Yes | Yes | Yes | **No** | `report-01.md` § D0 states method, discriminator, volume-vs-coverage split, and the three-way partition. STOP CONDITION fired (24 vs 11) and was reported. But an unmarked category-B site survives: `_manifest_decide.py:31` `_LEGACY_CI_WAIT`, dated to `d04ac98e` (#1066, 2026-07-30) — eleven days before the plan landed, so a genuine sweep miss (G3) |
| D1 | Shim-marker convention | convention documented + D0-confirmed category-A sites carry a conforming marker | Yes | Yes | Mostly | Yes | `shim-marker-convention.md` (99 lines) + `plugin-script-architecture/SKILL.md:54-57`; 5 `SHIM(A)` markers in the landed diff, 6 at HEAD; analyzer reports 0 `shim_marker_malformed` over 412 scripts (all three fields non-empty everywhere). Two markers sit on sites with no actual tolerate-branch (see below) |
| D2 | plugin-doctor rule flagging an unmarked shim | rule ships with tests in both directions + publishes the population size examined | Yes | **Partly** | Yes, within its stated precision-first design | **No** | `_analyze_shim_marker.py`; 28 tests pass (9 positive-indicator params, 5 negative-boundary params, 2 malformed, suppression, 2 cover-window, out-of-scope-dir, derivation, population, empty-population ×3, shape, 2 real-tree = 28). Population published in `details.population_size`; executed → 412. **Not wired into `analyze`** (`_runner.py:329-378` has no `analyze_shim_marker` call), contradicting the report. Measured recall over the tree's own shims: **4 of 25** — and the miss is not theoretical: commit `7951ada9` (#1276, 2026-08-17) landed a new unmarked category-B shim (`check-routing-decisions.py:170`) a week after the guard shipped, past a green gate (G6) |
| D3 | Retirement sweep over surviving category-B sites | every surviving category-B site marked or deleted; each deletion cites extinction evidence | Yes | Yes | Yes | Relative to D0's inventory, yes | 19 `SHIM(B)` markers in the landed diff; 19 in production at HEAD (B7+B9 consolidated into `_footprint_resolver.py:158` by a later refactor, `claude_runtime.py:1585` added by a later plan). Zero deletions, so the "cite the evidence" obligation is vacuously satisfied and the report explains why (persisted state, not showable extinct) |

**D0 — incomplete sweep.** `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_decide.py:29-31`
defines `_LEGACY_CI_WAIT` with the comment *"The retired phase-6 step id Rules 2 and 5 drop
defensively, against project marshal.json files that still list it as a candidate."* This is a
permanent read-path accommodation of a persisted shape an older version of this tooling wrote — a
category-B shim under the convention's own discriminator ("does this code accommodate a shape a past
version of our own writer produced?"). It carries no marker, and it appears neither in D0's 24-row
inventory nor in the report's NOT-A-SHIM negatives list, even though its comment uses the word
`legacy`, one of D0's own sweep terms. `manage-execution-manifest` is a bundle the D0 sweep reports
no hits from at all.

**D1 — two markers on sites with no tolerate-branch.** At
`_cmd_sync_defaults.py:290` the `SHIM(B)` block sits above `_deep_merge_missing`'s merge loop, but
that function contains no branch on the legacy `{}` shape: the docstring itself says *"the read path
coerces all of {absent, `null`, `{}`, TOON-`''`} to an empty dict, so the two on-disk shapes read
identically"*, and the tolerance is emergent from `if key not in live`. There is no shim code to
delete when `shim-remove-when` fires. `_invariants.py:747` is the weaker sibling: the marker sits on
the constant `_REFERENCES_REQUIRED_KEYS`, where the tolerance is the *absence* of `modified_files`
from a tuple. The report itself flagged both as "⚠ borderline / soft"; the convention explicitly says
marking a non-shim "is as wrong as leaving a real shim unmarked — it dilutes the signal"
(`shim-marker-convention.md:29-30`). These are two distinct sites in two bundles, so they are filed
per instance: G4 (`_cmd_sync_defaults.py`) and G7 (`_invariants.py`).

**D2 — wiring and recall.** The rule is wired into `run_quality_gate` (`_runner.py:206`) with
`severity='error'`, so it is genuinely build-failing — the destructive mutation confirmed the gate
turns red on a new unmarked indicator. It is **not** wired into `run_analyze_marketplace_rules`, so
`plugin-doctor analyze` never runs it; the landed `_runner.py` hunk adds exactly two lines (an import
and one `emit`), so this was never present and was not removed later. Separately, the per-marker
mutation sweep measures the guard's recall over the very inventory it was built for: strip one marker
block and only 4 of 25 sites produce a `shim_unmarked` finding — `_cmd_mark_step.py`,
`_cmd_assert_step_recorded.py`, `gitignore_setup.py`, `upgrade.py`. The design is deliberately
precision-first and both the module docstring and the convention doc say so ("a backstop, not a
substitute"), so this is not a hidden defect — but the test at
`test_analyze_shim_marker.py:343-349` asserts in its own docstring that *"A regression on either side
(a new unmarked shim, or an over-broad indicator) turns this red"*, which the measurement contradicts
for 21 of the 25 known shim shapes. The same docstring also asserts *"Every migration/back-compat
shim in the tree carries a conforming marker"*, which `_LEGACY_CI_WAIT` (G3) and
`posture_cutoff_legacy_aggregate` (G6) each falsify.

**D2 — the guard has already let one through.** `check-routing-decisions.py:170` defines a
`_REMOVAL_CAUSE_PATTERNS` entry named `posture_cutoff_legacy_aggregate`, commented *"LEGACY — the
RETIRED aggregate `lane_resolution` shape, kept for ARCHIVED decision logs only. The composer stopped
emitting this when it moved to one line per dropped step."* That is a category-B shim by the
convention's own discriminator, it carries no marker, and it landed in `7951ada9` (#1276,
2026-08-17) — after `1296ede1` (2026-08-10) shipped the build-failing rule whose stated purpose is
that "the next shim cannot land unmarked". The gate was green through it. It is in `plan-retrospective`,
a bundle D0 *did* sweep, so this is a recall failure of the running guard rather than an unreached
corner. The convention is otherwise being adopted — `#1181` and `#1287` each added a conforming
marker to a new shim in the same period.

## Report accuracy

Contradictions found:

- **"wired build-failing into quality-gate + analyze"** (§ Deliverables, D2). The `+ analyze` half is
  false. `run_analyze_marketplace_rules` (`_runner.py:329-378`) lists 29 analyzers; `analyze_shim_marker`
  is not among them. The landed diff adds only the `run_quality_gate` emit. By contrast the sibling
  rule this one mirrors, `analyze_thinking_directive_in_workflow_docs`, is in both.
- **"publishes `population_size` (386 on the real tree)"**. Re-derived: at the landing commit the
  population is **387** (`git ls-tree -r 1296ede1 | grep -cE '^marketplace/bundles/[^/]+/skills/[^/]+/scripts/.*\.py$'`);
  386 is the count at `1296ede1^`, i.e. the figure measured before the analyzer itself joined the
  population it scans. Off by one, in the direction of a stale measurement.
- **"400+ scripts swept for vocabulary"** (§ D0, volume-vs-coverage). The declared population —
  every `*.py` under `bundles/*/skills/*/scripts/` — was 386/387 at the time. "400+" overstates the
  volume figure the same section is careful to keep separate from coverage. (It is 412 today.)
- **"D3 … all 19 category-B sites"** is accurate as landed, but the D0 partition it rests on is not
  exhaustive — see `_LEGACY_CI_WAIT` above. The report's claim that `manage-metrics.py ::
  _read_status_created` and `tools-permission-fix/permission_fix.py` yield no shim site is confirmed
  first-party (the former is defensive `None`-handling; the latter's only migration is the explicit
  user-invoked `migrate-executor` subcommand, not a read-path accommodation).

Confirmed accurate, having checked each against the tree: the two OBSERVED claims (`legacy_string_entry`
present at `_cmd_mark_step.py:363`; the "older orchestrator versions" phrase absent from
`_read_status_created`); the 5-A/19-B landed marker split; every marker carrying three non-empty
fields (0 `shim_marker_malformed` over 412 scripts); "0 findings on the real tree" (still true today);
both-direction tests (28 pass); the empty-population guard and its convention-doc anchor; the derived
(not hard-coded) population; the firing fixture in `_fixtures.py:468`; the `GOLDEN_QG_LABELS` entry
(`test_runner.py:82`); the catalog row (`rule-catalog.md:228-235`) and provenance row
(`rule-provenance.md:156`); the `_ABOVE_DEF_GAP` review fix (value 5, with its regression test at
`test_analyze_shim_marker.py:191`); and "no duplicate detector framework" — the 040 analyzer scans a
markdown-doc population with entirely different helpers, so the two share a pattern, not code.

## Out-of-scope compliance

Clean. The landed diff is 28 files, **1347 insertions and 0 deletions** — it adds markers, one
analyzer, one standards doc, two reference rows, two `_runner.py` lines, and tests. No behavioural
code was changed, so the "do not relitigate whether each shim was a good idea" boundary held by
construction. Files touched outside the plan's *Expected surface* (`manage-locks`, `manage-run-config`,
`plan-retrospective`, `script-shared`, `workflow-permission-web`, `plan-marshall/_invariants.py`) are
in scope by the plan's own instruction that "D1 and D3 scope on D0's output". No undeclared collateral
change. The "build one detector pattern, not two" boundary was respected.

## Residue carried forward

- **CLA `not_signed` on PR #1153** — moot; the PR merged as `1296ede1` and is in `main`'s history.
  Closed.
- **Sibling-040 detector overlap** — no action was owed and none is open. The two analyzers coexist
  with no shared scaffolding module; if anything, the duplicated empty-population/finding boilerplate
  is a (small, non-blocking) invitation to factor later.
- **Local `/sync-plugin-cache`** — a developer-machine concern by the lane's own carve-out; not open
  against this repository.

## What could NOT be verified

- **The D1 cold-read result.** The report claims a context-free sub-agent correctly marked the
  category-B sample and not the defensive-`None` sample. That is a transcript artifact, not a tree
  artifact. What *is* checkable: the convention doc's "What counts as a shim (and what does not)"
  section carries the defensive-`None` example verbatim as a named non-shim and states the
  discriminator as a single question, so the wording plausibly supports the claimed outcome.
- **The landing-time build numbers** — "18808 passed, 14 skipped", "387 source files", "`./pw
  quality-gate` pass". Not reproducible at HEAD (a different tree, ~3 weeks of commits later) and not
  re-run here.
- **The `population_size` value at landing time as the rule itself reported it.** Re-derived from git
  as 387; the report's 386 could only be reconciled by re-running the analyzer against a checkout of
  `1296ede1`, which was not done.
- **Whether the sweep is now exhaustive.** Two independent vocabulary sweeps — the one above and the
  adversarial review's deliberately broader re-run (412 scripts, comment tokens only, 181 hits across
  78 files) — each found a credible miss (`_LEGACY_CI_WAIT`, G3; `posture_cutoff_legacy_aggregate`,
  G6). Both read every strong candidate by symbol, but both are vocabulary-bounded, so neither can
  certify that no further unmarked shim exists — only that the ones they surfaced were classified.
  That two independent sweeps each found a *different* miss is itself evidence the boundary is not
  yet established.

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked.** Re-derived at HEAD `9afba956`; `git log ac06e4fc..HEAD -- marketplace/ test/` is empty,
so the scanned tree is identical to the one this document was written against (34 unrelated commits
in between, all under `doc/plans/`).

- **Re-executed, not re-read.** Imported `_analyze_shim_marker` and ran `enumerate_script_files` +
  `analyze_shim_marker` over `marketplace/bundles` → **population 412, findings 0**. Wrote an
  independent mutation script (own anchor regex, own field-line stripper) and re-ran the recall sweep
  over all **25** production marker anchors → **4 fire, 21 silent**, the same four files. Ran
  `pytest test_analyze_shim_marker.py -o addopts="" -q` → **28 passed**; `--collect-only` → 28 ids.
- **Counts re-derived.** `# SHIM(A):` / `# SHIM(B):` at HEAD → **6 + 19** in production scripts plus
  2 doc-example occurrences in the analyzer. Landed diff `1296ede1` → **5 + 19 = 24**, and
  `--stat` confirms **28 files, 1347 insertions, 0 deletions**, `_runner.py` **+2**.
  `git ls-tree -r 1296ede1 | grep -cE '…/scripts/.*\.py$'` → **387**; at `1296ede1^` → **386**.
  `run_analyze_marketplace_rules` (`_runner.py:329-378`) → **29** `issues.extend` calls, none of them
  `analyze_shim_marker`. The 6→19→24→412→387/386→28→29 chain all reproduces.
- **Line references opened.** `_cmd_mark_step.py:363,563`; `manage-metrics.py:2709`;
  `_manifest_decide.py:29-31,175,221`; `_cmd_sync_defaults.py:290-293`; `_invariants.py:739-751`;
  `_analyze_shim_marker.py:442-483` (file is 483 lines); `test_analyze_shim_marker.py:191,337,342-350`;
  `_fixtures.py:468`; `test_runner.py:82`; `rule-catalog.md:231`; `rule-provenance.md:156`;
  `plugin-script-architecture/SKILL.md:54-57`; `shim-marker-convention.md:29-30` (99 lines);
  `_analyze_simplicity.py:52`; `outline-workflow-detail.md:806`. All accurate.
- **"Swept, clean" re-run with a broader pattern.** An independent comment-token sweep over the same
  412 scripts with a deliberately wider vocabulary than D0's (adding `deprecat`, `obsolet`,
  `grandfather`, `superseded`, `stop-gap`, `no longer written/emitted/produced`, `historical
  shape/form`, `before this change/field/key … existed`) → **181 hits in 78 files**. Every strong
  candidate was read by symbol; the classifications are recorded in gaps.md § "Refuted during
  adversarial review". This surfaced one new shim (G6) that both the D0 sweep era and the running
  detector missed.
- **Provenance dated.** `git log -S` established that `_LEGACY_CI_WAIT` predates the plan
  (`d04ac98e`, 2026-07-30) while `posture_cutoff_legacy_aggregate` postdates it (`7951ada9`,
  2026-08-17), and that the two later markers at HEAD came from `#1181` and `#1287`.

**Not re-checked.** The destructive mutation of `_cmd_mark_step.py` (method step 8) was **not**
repeated — no source file was modified during this review; the guard's liveness rests instead on the
25-site mutation sweep, which exercises the same `_scan_file` path in a temp copy. The landing-time
build numbers (18808 passed / 14 skipped, `./pw quality-gate`) were not re-run. The D1 cold-read
remains a transcript artifact. `report-01.md`'s claim that four sub-agents performed the D0
classification is unverifiable from the tree. The `~18` NOT-A-SHIM negatives were not individually
re-classified — only the ones the broader sweep re-surfaced.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| G1 | Real-tree test's docstring overstates recall; measured 4 of 25 | **upheld, evidence strengthened** | Recall reproduced independently (4 fire / 21 silent, same four files). Severity `high` confirmed against the rubric: this is a guard that passes against the defect it names. Added the empirical falsification (`7951ada9`) and a second false docstring sentence ("every shim … carries a conforming marker"); corrected the docstring line span to 343-349 |
| G2 | `analyze_shim_marker` absent from `run_analyze_marketplace_rules` | **upheld unchanged** | 29 `issues.extend` calls at `_runner.py:329-378`, none of them the shim rule; `analyze_thinking_directive_in_workflow_docs` present in both methods; landed hunk is +2 lines (import + gate emit), so it was never wired. `rule-catalog.md:231` does claim `cmd_analyze`. Severity `medium` correct — the gate is genuinely build-failing, so no shipped false *behaviour*, only a false doc line and a missing edit-time surface |
| G3 | `_LEGACY_CI_WAIT` is an unmarked category-B shim D0 missed | **upheld, evidence strengthened** | Symbol read at `_manifest_decide.py:29-31`, consumed as `drop=` at 175/221; `decision-rules.md:628` confirms `ci-wait` is retired as a phase-6 step id; the drop is silent accommodation, not a refusal. Dated to `d04ac98e` (2026-07-30) — before the plan landed, so a genuine sweep miss and not a later regression |
| G4 | Two markers sit on sites with no shim code to delete | **split (per-instance) and narrowed** | Both sites confirmed by reading the code: `_deep_merge_missing`'s body has no `{}` branch; `_REFERENCES_REQUIRED_KEYS` is a bare tuple. Two distinct sites in two bundles are two findings — G4 now covers `_cmd_sync_defaults.py:290-293` only, G7 covers `_invariants.py:747-750`. Severity `low` upheld for both (dilution, no wrong behaviour) |
| G5 | `population_size` is unreadable on a clean run | **upheld unchanged** | `emit` in `run_quality_gate` records only `{'rule', 'findings'}`; a clean tree returns `[]`, so the 412 appears nowhere. `_analyze_shim_marker.py:442-483` and the `>= 100` floor at `test_analyze_shim_marker.py:337` both confirmed |
| G6 | *(new)* `posture_cutoff_legacy_aggregate` is an unmarked category-B shim that landed after the guard | **added, medium** | `check-routing-decisions.py:170-183`, comment names the RETIRED aggregate `lane_resolution` shape kept for archived logs; introduced by `7951ada9` (#1276, 2026-08-17), a week after the rule shipped, past a green quality gate |
| G7 | *(new, split from G4)* `_REFERENCES_REQUIRED_KEYS` marker has no deletable code | **added, low** | Marker at `_invariants.py:747-750` sits on `('base_branch', 'branch')`; the tolerance is the absence of `modified_files` from the tuple, so `shim-remove-when` can never trigger a removal |
| Verdict | `implemented-with-gaps` | **upheld** | All four deliverables are implemented and each done-when condition is met on its own terms; the defects are completeness and honesty-of-claim, not an unbuilt deliverable. `partially-implemented` would be wrong |

**Documents corrected.** In `gaps.md`: open items 5 → **7**; G1 gained the empirical falsification, the
second false docstring sentence, per-site line numbers and a corrected docstring span; G3 gained the
retirement evidence, the refusal-class exclusion, and the commit date proving it is a sweep miss; G4
was narrowed to one site and G7 added for the other; G6 added; a `## Refuted during adversarial
review` section records that no gap was refuted and lists five candidate sites checked and rejected
as non-shims, so they are not re-litigated. In `verification.md`: the D0 and D2 rows gained the new
provenance and the G6 instance; a new "D2 — the guard has already let one through" paragraph; the
docstring reference corrected from `342-348` to `343-349`; the 28-test enumeration completed (it named
25 of 28); the concurrent-modification note updated to record that every figure reproduced on a clean
tree; and "Whether the sweep is now exhaustive" updated to reflect two independent sweeps each finding
a different miss. The verdict is unchanged.

**Residual doubt — what a third reviewer should look at first.** (1) The `~18` NOT-A-SHIM negatives
from D0 were never re-classified individually by anyone; a false *negative* there is invisible to
every sweep run so far, because a site classified out is a site nobody re-reads. (2) Both sweeps are
comment-vocabulary-bounded and read only `bundles/*/skills/*/scripts/**/*.py`; a shim whose comment
uses none of the vocabulary, or one living outside that population (`marketplace/targets/`, `test/`,
`.claude/`), is out of reach of the method entirely — the rule's own population derivation shares that
blind spot. (3) `_cmd_quality_phases.py:61` `_CANONICAL_VERIFY_PREFIXES = ('default:verify:',
'verify:')` was judged too soft to file: its comment calls the bare form "legacy", while
`check-manifest-consistency.py:386-390` says the same form is still produced today. One of those two
comments is wrong, and settling which would decide whether a marker is owed.
