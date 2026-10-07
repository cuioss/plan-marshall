# Verification — 410-the-pipeline-talks-to-itself-and-learns-from-the-echo

**Verified against:** commit `a54cd20ec046a80db54e5c0f5125efc57fa0cf95`   **Landed as:** PR #1231, commit `d3462f95ebd49e64c084f85b54bb0e8204c623f4` (confirmed ancestor of HEAD)   **Verdict:** implemented-with-gaps

## Method

What was actually done, in order:

- Read `plan.md` and `report-01.md` in full.
- Located the landed commit (`git log --oneline --all --grep '#1231'` → `d3462f95`), read its full
  `--numstat` (8 paths) and the complete diff for `audit.py`, `disposition-to-hint-routing.md`,
  `finalize-step-preference-emitter.md`, and the auditor `SKILL.md`.
- Opened at HEAD: `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`
  (`_UNATTRIBUTED_MODULE`, `_preference_module`, `_recognized_bot_kinds`, `_preference_admissible`,
  `cross_preference_pattern`, `emit_preference_pattern_block`, `_classify_zero`,
  `suspect_zero_census`, the driver at ~9223), the auditor `SKILL.md` § Step 4c,
  `checks/preference-pattern-detector.md`,
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/disposition-to-hint-routing.md`,
  `.../standards/finalize-step-preference-emitter.md`,
  `marketplace/bundles/plan-marshall/skills/manage-findings/scripts/_findings_core.py`,
  `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/bot_registry.py`,
  `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
  (`_is_self_authored_response`, the `bot_kind` sites) and `github_re_review.py`
  (`bot_kind_for_author`), `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py`
  (`prepare_body`), `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/constants.py`
  (`FINDING_TYPES`), and `.gitignore`.
- **Executed** the code rather than reading it: loaded `audit.py` by path and ran
  `_recognized_bot_kinds()` → `frozenset({'coderabbit', 'pr-agent', 'sourcery'})`, then
  `_preference_admissible` on four shapes → self/no-`bot_kind` `False`, `coderabbit` `True`,
  unrecognized `sonarcloud` `False`, `lint` finding `True`.
- **Ran the tests**: `uv run python -m pytest
  test/plan-marshall/audit-archived-plan-retrospectives/test_audit_check_preference_pattern_detector_{filters,aggregation,emit}.py
  -o addopts="" -q` → **26 passed in 0.30s**.
- **Mutation-checked both gates without touching any file.** `git diff --quiet -- <audit.py>` returned
  0 (not concurrently modified), but the mutation was still done purely in memory in a scratch script:
  (a) `audit._preference_admissible` replaced with `lambda *_: True` → the D1 self-authored fixture
  goes from `candidate_count 0` to **1**; (b) `audit._preference_module` replaced with the pre-fix
  literal-`default` fallback plus `_UNATTRIBUTED_MODULE = '__never__'` → the D2 fixture goes from
  `candidate_count 0 / excluded 1` to **`candidate_count 1 / rows ['default'] / excluded 0`**. Both
  guards are therefore non-vacuous; no repository file was modified by this verification other than
  `verification.md` and `gaps.md`.
- **Re-derived D0's population**: `git ls-files '.plan/project-architecture/*enriched.json'` → **11**
  files (`default/` + 10 modules), and re-read every `best_practices[]`/`insights[]`/`tips[]` entry
  (**34** entries corpus-wide today) via a JSON scan for the comment-provenance signature.
- **Swept the tree for stale restatements**: `--module default` across all tracked files; every file
  referencing `preference-pattern-detector` / `preference_min_recurrence` /
  `finalize-step-preference-emitter` / `disposition-to-hint-routing` checked for stale routing prose.
  **The "(30 files)" figure originally stated here does not re-derive** and has been removed: the same
  four-term sweep at HEAD, excluding `.git`/`.pytest_cache`/`.ruff_cache`, returns **51** files (of
  which 21 are `doc/plans/**` prose that accreted after the sweep was run). The figure was a
  point-in-time process detail, not a checkable claim; the *substance* — no stale routing prose in any
  `marketplace/` or `.claude/` file — was re-verified independently.
- Checked for a duplicate copy of the skill (`find … -name audit.py`) — exactly one copy exists, so
  no marketplace mirror was left stale.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | GATE: population before the filter | count reported alongside population scanned | yes | yes | yes | **partial** | `report-01.md` § D0; re-derived `git ls-files '.plan/project-architecture/*enriched.json'` → 11 files (default + 10 modules), matching the report exactly; `.gitignore` at `d3462f95` lines 46-48 = `.plan/*`, `!.plan/marshal.json`, `!.plan/project-architecture/` — the exception the report cites is real. Text-scan re-run today over 34 entries: no hint encodes "unattributed / pipeline-self PR comments are routinely taken into account". **But** the published "no corpus repair" decision never examined the D2 half — see G2. *(Adversarial review: D0's literal done-when — "the count is reported alongside the population scanned" — is fully met; the `partial` is against the SCOPE the report's published decision claims, not against the deliverable's own condition. Verdict unaffected.)* |
| D1 | Authorship discrimination at the emitter | a self-authored comment cannot reach the disposition corpus | yes | yes | yes | yes | `audit.py:2275` `_preference_admissible` + call site `audit.py:2343` inside `cross_preference_pattern`; executed: no-`bot_kind` `pr-comment` → `False`, `coderabbit` → `True`, unrecognized `sonarcloud` → `False`, `lint-issue` → `True`. Arm choice + rejected arm recorded in `report-01.md` § D1 as the plan's Verification section requires |
| D2 | Fallback-bucket promotability decision | decision implemented and recorded | yes | yes | yes | yes | `audit.py:2219` `_UNATTRIBUTED_MODULE`, gate at `audit.py:2361` (post-aggregation, separate loop from D1's pre-aggregation `continue` at `:2343`), `unattributed_excluded_count` in the return dict (`audit.py:2392`) and in `emit_preference_pattern_block` (`audit.py:5934`); contract § (d) at `disposition-to-hint-routing.md:79`. Visibly separate from D1 in the diff, as the plan's Verification demands |
| D3 | Test that fails pre-fix + matched negative control | both halves pass, each seen red first | yes | yes | yes | yes | `test_audit_check_preference_pattern_detector_filters.py` — 8 tests across `TestPreferenceAuthorshipFilter` / `TestPreferenceUnattributedBucketNotPromoted`; 26 tests pass; in-memory mutation drives the D1 suppression test 0→1 and the D2 suppression test 0→1 (rows `['default']`), so neither guard is vacuous. Negative controls `test_bot_attributed_pr_comment_remains_a_preference`, `test_non_comment_finding_unaffected_by_authorship_filter`, `test_module_attributed_survives_alongside_default` all promote |

### D0 — the one deliverable that is not a clean pass

The plan's D0 question is literally the D1 question ("hints minted from **self-authored** comments"),
and `report-01.md` answers it honestly: it labels the precise provenance count *not recoverable*
(the store keeps only the generalized hint string, per privacy invariant (c)), publishes the
text-scan proxy, and names the population. That is exactly the *looked-and-found-nothing* the plan
demanded, and re-deriving it today reproduces the report's figures.

What it does **not** do is assess the corpus against D2, the other gate this same plan shipped. Today
`.plan/project-architecture/default/enriched.json` carries 14 insights, of which **nine**
(zero-based `insights[]` indices 1, 2, 3, 6, 8, 9, 11, 12, 13 — the original text gave 1-based
positions and included an index 14 that a 14-element array does not have) are disposition-recurrence
generalizations sitting in the `default` bucket — "consistently folded into the work
(`taken_into_account`)", "routinely dispositioned as accepted-without-action", "across 9 dispositions
on one PR …". Those are precisely the artifact class § (d) now declares non-promotable. The report's
conclusion is stated as covering the plan ("**filter alone, no corpus repair**"), so a reader takes it
as settling the whole corpus question; it settled half. See G2.

## Report accuracy

Re-derived at the moment of writing. **No contradiction found** in the following, each checked:

- **"all 11 tracked `enriched.json` files — `default/` plus 10 modules"** — `git ls-files` returns
  exactly 11, and the ten module names listed match one-for-one. (CR-2's off-by-one correction from
  12 to 11 landed correctly.)
- **"`.gitignore` (lines 46-48) carries `!.plan/marshal.json` and `!.plan/project-architecture/`"** —
  true at `d3462f95` (lines 46/47/48 = `.plan/*`, `!.plan/marshal.json`, `!.plan/project-architecture/`).
- **"`prepare_body` stamps no marker/attribution/signature"** — confirmed: `ci_base.py:141`
  `prepare_body` only resolves a slot, guards the plan context, and returns a scratch path.
- **"`bot_kind_for_author` returns `None` for a human author *and* for the pipeline's own posting
  account alike"** — confirmed: `github_re_review.py:450`, a registry-login lookup returning `None`
  for any login not in the registry.
- **"the ingest verb records the pipeline's own PR comments with `bot_kind` absent"** — confirmed on
  the surrounding code: `github_pr.py:942` derives `bot_kind` from the author login, and
  `_is_self_authored_response` (`github_pr.py:368`) documents the pipeline's own PR-level comment as
  `bot_kind` `None`, `kind` `issue_comment`.
- **"the only preference surface with unit-testable aggregation; the per-plan emitter is an
  LLM-orchestration doc"** — confirmed: `finalize-step-preference-emitter.md` has no script, and a
  tree-wide `find -name audit.py` shows exactly one copy of the auditor script.
- **Reviewer population M = 3** — `bot_registry.bot_kinds()` executed → `{'coderabbit', 'pr-agent',
  'sourcery'}`.
- **"the D3 negative controls … genuinely still promote"** — confirmed by running them.
- **CR-1's fix ("validate `bot_kind` ∈ registry", "degrades to presence-only")** — both behaviours
  present and executed; the degrade branch is `recognized_bot_kinds is None → return True`.

Four statements the tree does **not** support (items 3 and 4 added by adversarial review):

1. **"all four docs … mutually consistent"** (§ Findings, re-verification second pass). They are not.
   `disposition-to-hint-routing.md` § (e) opens by requiring a **recognized** `bot_kind` "validated
   against the registry-derived set" and closes (line 126-127) by telling the per-plan emitter to
   exclude "`pr-comment` findings without a `bot_kind`" — presence-only, the exact weaker rule CR-1
   closed on the auditor side. `finalize-step-preference-emitter.md:131` states the stronger rule, so
   the contract disagrees with itself and with its own consumer. See G1.
2. **"the two remaining `--module default` hits (`phase-6-finalize/workflow/lessons-capture.md:142`,
   `standards/lessons-integration.md:94`)"**. Neither file contained the literal string `--module
   default` at `d3462f95` (verified with `git show d3462f95:<path> | grep`). Both files do carry a
   `default`-module routing rule for cross-cutting *lessons-capture* facts, so the substance of the
   scoping judgement holds; the quoted hit is a mis-citation, not a live defect. Not filed as a gap.
   **Adversarial review dissents on the second half of that dismissal:** those two files do not merely
   fail to contain the quoted string, they assert the *opposite* of what § (d) asserts —
   `lessons-capture.md:142` reads "The `default` module is the first-class home for cross-cutting
   project knowledge", and `outline-workflow-detail.md:707` reads it back the same way, while § (d)
   says `default` "only ever means *unattributed*, never *cross-cutting*". Two documents in one skill
   directory make opposite normative claims about the same `enriched.json` bucket. Now filed as **G4**.
3. **"the ingest verb takes every non-noise PR comment regardless of author"** (the plan's HYPOTHESIS,
   which this document's § "What could NOT be verified" originally reported as matching the tree). It
   does not match in full. The ingest verb already carries **two** structural pipeline-self exclusions
   that predate this plan: `_is_self_authored_response` (`github_pr.py:368`, called at `:447`), whose
   docstring states explicitly that it is *not* a noise filter — "a self-authored response is not noise
   — it is our own output" — and `is_registered_trigger_comment` (`github_re_review.py:488`), which
   drops exactly the pipeline-authored re-review trigger the plan names as one of its two contributing
   findings (landed in PR #936, before #1231). Both key on body shape rather than on author, so they
   are partial and the plan's conclusion survives — the *description-restore* comment, the plan's other
   contributing finding, matches neither shape — but "regardless of author" is too strong, and this
   document should not have passed it through unqualified. Not filed as a gap: it strengthens rather
   than weakens the shipped fail-closed fix, and no shipped statement repeats the overstatement.
4. **"`unattributed_excluded_count` is published in the same block"** (this document's own G3
   rationale, as originally written). `emit_suspect_zero_census_block` (`audit.py:5645`) emits a
   separate `check: suspect-zero-census` block; its rows carry only
   `{check, genuine_signal_count, zero_class, quiet_run_count, suspect, reading}`. G3's severity has
   been raised from `low` to `medium` accordingly.

Unverifiable-but-uncontradicted: the `./pw verify` totals (19639 / 19641 passed) cannot be re-derived
— the tree has advanced well past `d3462f95`.

## Out-of-scope compliance

Clean. The landed diff touches exactly 8 paths: `audit.py`, its test file, the auditor `SKILL.md`,
`checks/preference-pattern-detector.md`, the two `phase-6-finalize/standards/` docs, plus the
plan-directory move and the run report. **No file under
`marketplace/bundles/plan-marshall/skills/workflow-integration-github/**` or
`.../tools-integration-ci/**` was modified** — the two surfaces the plan declared read-only. The
ingest arm was not touched and no cross-epic hand-off was opened, matching the plan's stated
preference. No undeclared collateral change appears in the diff.

## Residue carried forward

| Residue declared in report-01.md | Still open at HEAD? |
|---|---|
| **`default` sentinel overloading** — `default` is both the unattributed sink and the alias for the real project-root module, so D2 also suppresses a recurrence genuinely attributed to `module: "default"` | **Open.** `_UNATTRIBUTED_MODULE = "default"` at `audit.py:2216`, and `test/plan-marshall/manage-architecture/test_cmd_resolve.py:573` still asserts "``--module default`` resolves to the real root module". Correctly declared, correctly deferred |
| **Unmeasurable historical corpus pollution (D0)** | **Open**, and wider than declared — the declared residue covers only the self-authored (D1) provenance question; the `default`-bucket (D2) pollution that is directly observable in the store was never surfaced. See G2 |
| **Local plugin-cache sync (informational)** | Not owed by the lane; `CLAUDE.md` § Standalone Plan Lane confirms a cloud run neither performs nor owes it. No action |

## What could NOT be verified

- **The plan's originating observation** — that one tuple `(default, pr-comment, taken_into_account)`
  cleared at count 2 from two pipeline-authored comments — is first-party to another run under
  `.plan/`, which is git-ignored. The plan itself labels it HYPOTHESIS and forbids re-derivation. Not
  checked, by design. The *checkable* halves were checked: the aggregation shape and the fallback
  routing rule match the plan's description; **the ingest verb's author handling matches only in
  part** — see § "Report accuracy" item 3. The plan's other checkable lead, its
  minimum-recurrence threshold, re-derives as **two** for the surface the incident occurred on
  (`.plan/marshal.json:161` `preference_min_recurrence: 2`, default `2` per
  `finalize-step-preference-emitter.md:146`), matching the plan's "two, here"; the cross-plan
  auditor's own threshold is a different constant and is **3**
  (`audit.py:650` `THRESHOLDS["preference_disposition_occurrences"]`, executed).
- **The `./pw verify` pass counts** (19639, then 19641) — not reproducible against today's tree.
- **Whether any of the nine `default`-bucket disposition hints now in the store was minted by the
  preference emitter specifically** — the store retains no provenance (the report's own point). What
  is verifiable is their *shape* and *bucket*, which is what G2 rests on; the gap is stated as
  "assessment not published", not as "these were emitter-minted".
- **The per-plan LLM emitter's runtime behaviour** — it is a prose contract with no script, so only
  its documented rules could be checked, not its execution.
- **Interaction with the `suspect-zero-census`** — the census did **not** exist in `audit.py` at
  `d3462f95` (`git show d3462f95:… | grep -c 'def suspect_zero_census'` → 0). Its present interaction
  with D2's gate-produced zero is therefore a later-plan interaction, not this plan's omission; it is
  recorded as G3 at low severity for whoever owns the census.

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked.** Everything below was re-derived at HEAD (`6dbf0657`), not read off this document.

*Executed (not read):* loaded `audit.py` by path and ran `_recognized_bot_kinds()` →
`frozenset({'sourcery','pr-agent','coderabbit'})`; `_preference_admissible` on five shapes → no-`bot_kind`
`False`, `coderabbit` `True`, `sonarcloud` `False`, whitespace-only `bot_kind` `False`, `lint` `True`, plus
the degrade branch (`recognized_bot_kinds=None`, `sonarcloud`) → `True`; `_preference_module` on
`{}` / `{component}` / `{module,component}` → `default` / `x` / `y`;
`THRESHOLDS["preference_disposition_occurrences"]` → `3`; and
`_classify_zero(emit_preference_pattern_block({...unattributed_excluded_count: 2, candidate_count: 0,
plans_in_corpus: 17}), 0, 17)` → `disciplinary` (G3's premise, confirmed by running it).

*Mutations, both purely in memory in `$TMPDIR` against a private fixture corpus, no repository file
touched (`git diff --quiet -- audit.py` → clean first):* neutralising `_preference_admissible` drives the
D1 fixture `candidate_count` 0 → 1 (row `('python','pipeline note')`); neutralising the D2 gate (pre-fix
literal-`default` `_preference_module` + `_UNATTRIBUTED_MODULE='__never__'`) drives the D2 fixture 0 → 1
with `rows ['default']`. Both reproduce this document's mutation claims exactly.

*Tests:* the three `test_audit_check_preference_pattern_detector_*.py` files re-run → **26 passed**; the
8-test split across `TestPreferenceAuthorshipFilter` (6) / `TestPreferenceUnattributedBucketNotPromoted`
(2) re-counted by reading the file.

*Figures re-derived:* `git ls-files '.plan/project-architecture/*enriched.json'` → 11; corpus entry
count by JSON load → 34; `default/enriched.json` → 14 `insights[]`, 2 `best_practices[]`, 5 `tips[]`;
`.gitignore` at `d3462f95` lines 46-48 (exact); `d3462f95` `--numstat` → 8 paths, and
`git merge-base --is-ancestor d3462f95 HEAD` → true; `git show d3462f95:… | grep -c 'def
suspect_zero_census'` → 0; `find -name audit.py` → 1 copy; `git ls-files | grep
disposition-to-hint-routing.md` → 1 copy.

*Files opened at HEAD:* `audit.py` (the `2179-2400` preference region and the `5460-5700` census
region in full), all three preference test files, `disposition-to-hint-routing.md` (whole),
`finalize-step-preference-emitter.md` §§ Step 1-4, `checks/preference-pattern-detector.md`,
the auditor `SKILL.md` hits, `ci_base.py:prepare_body`, `github_re_review.py:bot_kind_for_author` and
`is_registered_trigger_comment`, `github_pr.py:_is_self_authored_response`,
`tools-file-ops/scripts/constants.py:FINDING_TYPES`, `manage-architecture`'s `manage-api.md` §
"Write Commands (Enrichment)" and `_cmd_enrich.py`, `test/plan-marshall/finalize-step-preference-emitter/test_preference_emitter.py`,
`lessons-capture.md`, `lessons-integration.md`, `outline-workflow-detail.md`, and the landed diff.

*Broader sweeps than the originals:* `--module default` tree-wide (4 hits, all
`architecture resolve` build-command usage or the `audit.py` comment — none a live hint-routing
instruction); the four-term reference sweep re-run (51 files, not 30); and a **new** sweep the
original did not run — `cross-cutting` co-occurring with `default` across `marketplace/` and
`.claude/`, which is what surfaced G4.

**NOT re-checked.** The `./pw verify` totals (19639 / 19641) — unreproducible, as stated. The plan's
originating observation under `.plan/` — absent from this clone by design. "Each half seen red first"
as a historical fact — substituted by the mutation reproduction, which is the strictly stronger check.
Whether any of the nine `default`-bucket hints was emitter-minted — no provenance is retained. The
per-plan LLM emitter's runtime behaviour — prose, not code. `report-01.md` § Findings items 1-5 and the
review-retrospective table were read but not independently re-derived against GitHub.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| **Verdict** | `implemented-with-gaps` | **upheld** | All four deliverables implemented, correct, and pinned by guards that were independently mutation-proved non-vacuous. No deliverable is unimplemented, so `partially-implemented` does not apply. |
| **D0 row** | Complete? `partial` | **re-worded, not re-rated** | D0's literal done-when (count + population) is met and re-derives exactly. The `partial` is against the scope the report's published decision *claims*, not against the deliverable's condition; the cell now says so. |
| **D1 row** | clean pass | **upheld, line refs corrected** | `_preference_admissible` executed on five shapes incl. the whitespace and degrade branches. Cited lines were off by 4: `2271`→`2275`, call site `2338`→`2343`. |
| **D2 row** | clean pass | **upheld, line refs corrected** | Gate confirmed post-aggregation and structurally separate from D1's pre-aggregation `continue`. `2216`→`2219`, `2360`→`2361`, `2391`→`2392`; `5934` was correct. |
| **D3 row** | clean pass | **upheld** | 26 tests re-run green; 8-test split re-counted; both mutations reproduced 0→1. The landed test file was `test_audit_checks.py` (later split into the three `..._preference_pattern_detector_*.py` files by PR #1258, `88894aef`, and deleted) — the split is post-landing, not a mis-citation of this plan. |
| **G1** | § (e) closing sentence states presence-only | **upheld** | `disposition-to-hint-routing.md:127` still reads "`pr-comment` findings without a `bot_kind`"; `finalize-step-preference-emitter.md:131` and `checks/preference-pattern-detector.md:37` both read "recognized reviewer `bot_kind`". Fix's CR-1 line refs corrected (`2277-2280` → `2237` and `2309`); Done-when's `grep` was not runnable as written (backticks inside double quotes) and has been rewritten. |
| **G2** | D0 never assessed the corpus against D2 | **upheld; two clauses refuted** | The nine entries exist and are disposition-shaped; the `insights[]` → `get-module-context` → phase-3-outline path is real (`outline-workflow-detail.md:376,707`). **Refuted:** the index list was 1-based and cited an index 14 a 14-element array cannot have; and "retire it via `architecture`" names a verb that does not exist — `_cmd_enrich.py` is append-only (`_append_to_list`) and `manage-api.md` lists no delete verb. Fix rewritten with the two paths that do exist, and scoped so it cannot destroy legitimately-routed lessons-capture facts. |
| **G3** | `low`; census misreads a gate-produced zero | **upheld, re-severitied `low` → `medium`** | Premise confirmed by execution. The stated mitigation is false: the census is a **separate** block (`emit_suspect_zero_census_block`, `audit.py:5645`) whose rows carry no `unattributed_excluded_count`, and whose `census_note` asserts "a disciplinary zero is evidence the corpus was clean". That is a shipped false signal; it stays below `high` only because the census is reporting-only and the correction is cross-block recoverable. Fix and Done-when rewritten against named symbols and a runnable assertion. |
| **G4** | — | **added** | § (d)'s unscoped "`default` only ever means *unattributed*, never *cross-cutting*" (and `audit.py:2214-2218`'s matching comment) contradicts `lessons-capture.md:142` and `outline-workflow-detail.md:707`, which designate the same bucket the first-class home for cross-cutting facts. This document had dismissed the collision as "the substance of the scoping judgement holds"; it does not — the two are opposite claims about one store. `low`: no behaviour is wrong today, but it is directly load-bearing for G2's remediation. |
| **"ingest verb takes every non-noise comment regardless of author"** | passed through as matching the tree | **refuted in part** | `_is_self_authored_response` (`github_pr.py:368`, whose docstring insists it is *not* a noise filter) and `is_registered_trigger_comment` (`github_re_review.py:488`, PR #936) already drop two classes of pipeline-authored comment pre-ingest. Recorded as § "Report accuracy" item 3, not as a gap. |
| **"(30 files)" sweep figure** | 30 files checked | **does not re-derive** | The same four-term sweep returns 51 files at HEAD. Removed as a point-in-time process detail; the substantive claim was re-verified independently. |
| **"exactly one copy of `audit.py`" / "no marketplace mirror"** | clean | **upheld** | `find` → 1; `git ls-files` for `disposition-to-hint-routing.md` → 1. |
| **`prepare_body` stamps no marker** | confirmed | **upheld** | `ci_base.py:141-186` read in full: resolves a slot, guards the plan context, `mkdir`s, returns a path. No marker, attribution, or signature. |
| **"the only preference surface with unit-testable aggregation"** | confirmed | **upheld** | `test/plan-marshall/finalize-step-preference-emitter/test_preference_emitter.py` exists but tests **seed wiring only** — step discovery, ordering, `post_run_review`/`mutates_source` flags, and the `preference_min_recurrence` default. Its own docstring: "The step body is an LLM-orchestration doc". |
| **Reviewer population M = 3** | confirmed | **upheld** | `bot_registry.bot_kinds()` executed → 3 members. |

**Documents corrected.** In `verification.md`: five `audit.py` line references fixed; the "(30 files)"
figure withdrawn and replaced with the re-derived 51 plus the reason it does not re-derive; the D0
narrative's 1-based/out-of-range index list corrected; the D0 table cell qualified so `partial` is not
read as a done-when failure; § "Report accuracy" grown from two unsupported statements to four (the
ingest-verb overstatement and this document's own G3 rationale); § "What could NOT be verified"
amended to record the ingest-verb partial match and to publish the two thresholds (per-plan emitter
`2`, auditor `3`) the plan asked to be re-derived from source and this document had left unstated. In
`gaps.md`: open items 3 → 4; G1's Fix line refs and unrunnable Done-when `grep` fixed; G2's index list,
fabricated `architecture` retire verb, and over-broad remediation scope fixed; G3 re-severitied to
`medium` with a corrected rationale and a symbol-level Fix/Done-when; G4 added; a
`## Refuted during adversarial review` section added recording the five refuted clauses.

**Residual doubt — what a third reviewer should look at first.**

1. **G3's severity is the closest call in this document.** A shipped false signal ordinarily earns
   `high`. It is held at `medium` on two judgements a third reviewer may reject: that a reporting-only
   census is lower-stakes than a gating one, and that cross-block recoverability counts as mitigation.
   The condition's real-world frequency is unmeasurable here — no archived-plan corpus exists in this
   clone (`.plan/` holds only `execute-script.py`, `local/`, `marshal.json`, `project-architecture/` and
   `temp/`), so the census was never run against real data by either reviewer.
2. **The surface that produced the incident is still enforced only in prose.** The observed tuple came
   from the per-plan emitter (threshold `2`); the structural, tested enforcement landed in the
   cross-plan auditor (threshold `3`). `finalize-step-preference-emitter.md` Steps 1 and 3 are the
   emitter's whole implementation, and G1 shows the shared contract's normative sentence for that very
   surface still states the weaker rule. Both documents call D1 a clean pass; a third reviewer should
   decide whether "a self-authored comment cannot reach the disposition corpus" is genuinely satisfied
   when the corpus in question is the emitter's, not the auditor's.
3. **G2's nine entries were classified by reading their text, not their provenance.** The partition
   between "disposition-recurrence generalization" (retire candidate) and "cross-cutting
   lessons-capture fact" (keep) is a judgement made twice by two agents from the same substrate — the
   hint strings — and never from a producer record, because none is kept. Zero-based `insights[]` entry 10 ("The project
   tolerates async review-bot latency as a non-defect…") in particular reads either way and was
   excluded from the nine by both reviewers.
