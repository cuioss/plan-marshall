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
  `finalize-step-preference-emitter` / `disposition-to-hint-routing` (30 files) checked for stale
  routing prose.
- Checked for a duplicate copy of the skill (`find … -name audit.py`) — exactly one copy exists, so
  no marketplace mirror was left stale.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | GATE: population before the filter | count reported alongside population scanned | yes | yes | yes | **partial** | `report-01.md` § D0; re-derived `git ls-files '.plan/project-architecture/*enriched.json'` → 11 files (default + 10 modules), matching the report exactly; `.gitignore` at `d3462f95` lines 46-48 = `.plan/*`, `!.plan/marshal.json`, `!.plan/project-architecture/` — the exception the report cites is real. Text-scan re-run today over 34 entries: no hint encodes "unattributed / pipeline-self PR comments are routinely taken into account". **But** the published "no corpus repair" decision never examined the D2 half — see G2 |
| D1 | Authorship discrimination at the emitter | a self-authored comment cannot reach the disposition corpus | yes | yes | yes | yes | `audit.py:2271` `_preference_admissible` + call site `audit.py:2338` inside `cross_preference_pattern`; executed: no-`bot_kind` `pr-comment` → `False`, `coderabbit` → `True`, unrecognized `sonarcloud` → `False`, `lint-issue` → `True`. Arm choice + rejected arm recorded in `report-01.md` § D1 as the plan's Verification section requires |
| D2 | Fallback-bucket promotability decision | decision implemented and recorded | yes | yes | yes | yes | `audit.py:2216` `_UNATTRIBUTED_MODULE`, gate at `audit.py:2360` (post-aggregation, separate loop from D1's pre-aggregation `continue`), `unattributed_excluded_count` in the return dict (`audit.py:2391`) and in `emit_preference_pattern_block` (`audit.py:5934`); contract § (d) at `disposition-to-hint-routing.md:79`. Visibly separate from D1 in the diff, as the plan's Verification demands |
| D3 | Test that fails pre-fix + matched negative control | both halves pass, each seen red first | yes | yes | yes | yes | `test_audit_check_preference_pattern_detector_filters.py` — 8 tests across `TestPreferenceAuthorshipFilter` / `TestPreferenceUnattributedBucketNotPromoted`; 26 tests pass; in-memory mutation drives the D1 suppression test 0→1 and the D2 suppression test 0→1 (rows `['default']`), so neither guard is vacuous. Negative controls `test_bot_attributed_pr_comment_remains_a_preference`, `test_non_comment_finding_unaffected_by_authorship_filter`, `test_module_attributed_survives_alongside_default` all promote |

### D0 — the one deliverable that is not a clean pass

The plan's D0 question is literally the D1 question ("hints minted from **self-authored** comments"),
and `report-01.md` answers it honestly: it labels the precise provenance count *not recoverable*
(the store keeps only the generalized hint string, per privacy invariant (c)), publishes the
text-scan proxy, and names the population. That is exactly the *looked-and-found-nothing* the plan
demanded, and re-deriving it today reproduces the report's figures.

What it does **not** do is assess the corpus against D2, the other gate this same plan shipped. Today
`.plan/project-architecture/default/enriched.json` carries 14 insights, of which **at least nine**
(indices 2, 3, 4, 7, 9, 10, 12, 13, 14 in the `insights[]` array) are disposition-recurrence
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

Two statements the tree does **not** support:

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
  checked, by design. The *checkable* halves were checked: the aggregation shape, the fallback
  routing rule, and the ingest verb's author handling all match the plan's description.
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
