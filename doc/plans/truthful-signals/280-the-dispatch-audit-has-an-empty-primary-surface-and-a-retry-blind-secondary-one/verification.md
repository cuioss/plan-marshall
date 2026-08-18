# Verification — 280 the-dispatch-audit-has-an-empty-primary-surface-and-a-retry-blind-secondary-one

**Verified against:** commit `a884110e`   **Landed as:** PR #1200, commit `1da26b13`   **Verdict:** implemented-with-gaps

## Method

What was actually done, in order:

- Read `plan.md` and `report-01.md` in full; extracted D0–D3, their *Done when* conditions, the
  Out-of-scope block, the Expected surface, the Claim-labels table and the Verification section.
- Located the landed commit: `git log --oneline --all --grep '#1200'` → `1da26b13`
  ("fix(dispatch-audit): emit the dispatch record from the resolve-target seam, per firing").
  Read the full message and `--name-only` file list (12 files) and the per-file diffs for
  `_cmd_effort.py`, `manage-config.py`, `execution-context-dispatch-audit.md`.
- Opened at HEAD: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_effort.py`
  (lines 449–570), `.../manage-config/scripts/manage-config.py` (lines 471–520),
  `.../manage-config/SKILL.md:1194-1197`, `.../manage-config/standards/api-reference.md:376,385`,
  `.../ref-workflow-architecture/standards/dispatch-logging.md` (whole file),
  `.../ref-workflow-architecture/standards/dispatch-walkthrough.md:30-70`,
  `.../ref-workflow-architecture/SKILL.md:22`,
  `.../plan-retrospective/standards/execution-context-dispatch-audit.md:37-40`,
  `.../plan-marshall/workflow/execution.md:120-145,275-305`,
  `.../plan-marshall/workflow/planning.md:225-300`,
  `.../phase-6-finalize/standards/dispatch-inline-split.md:25-60`,
  `.../phase-6-finalize/workflow/lessons-capture.md:57-66`,
  `.../plan-retrospective/scripts/check-manifest-consistency.py:375-420`,
  `.../plan-retrospective/scripts/check-dispatch-audit.py` (Surface-B parsing),
  `.../manage-logging/scripts/plan_logging.py:162-320` (`get_log_path`, `log_entry`),
  `.../script-shared/scripts/marketplace_paths.py:73-96` (`names_real_plan`, `NO_PLAN_SENTINEL`).
- Ran the plan's own test file: `uv run python -m pytest
  test/plan-marshall/manage-config/test_dispatch_seam_emission.py -o addopts="" -q` →
  **9 passed** (8 landed by this plan, 1 added later by #1232).
- **Executed** the routing claim rather than reading it:
  `uv run python -c "... get_log_path('none','work') / get_log_path(None,'work')"` → both resolve to
  `.plan/local/logs/work-2026-08-18.log`, and `names_real_plan('none') is True`. This confirms the
  report's "Minor — routing comment precision" finding.
- **Mutation check 1 (the highest-risk guard).** `git diff --quiet` on `_cmd_effort.py` → exit 0
  (not concurrently modified); byte-snapshot saved to the scratchpad; replaced `if workflow:` with
  `if True:` in `cmd_effort_resolve_target`. Result: **9/9 tests still passed** — the guard is not
  pinned by any test. Restored from the saved bytes; `git diff --quiet` → exit 0.
- **Mutation check 2 (control, to prove the suite is not inert).** Disabled the Surface-B
  (decision-log) write. Result: **2 failed** (`test_emission_set_equals_envelope_set`,
  `test_both_surfaces_written_from_the_seam`) — the suite does bite where it claims to. Restored from
  the saved bytes; re-ran → 9 passed, `git diff --quiet` → exit 0.
- Re-derived every count stated below at the moment of statement with `grep -rn`/`grep -rln` over
  `marketplace/` and `.claude/`.
- Checked supersession with `git log --oneline -- <path>` and
  `git log -S 'normalize_verification_step' --oneline`.

No file in the repository was modified except the two this task writes; both mutations were restored
from saved bytes, never via `git checkout`/`restore`/`stash`.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | GATE: derive the emission population both directions + token-mismatch sweep | Both directions enumerated with population stated; token-mismatch sweep reports population and hit count separately | yes (report-only, mutates nothing) | yes | yes | partly | `report-01.md` § D0 states both directions, and "Sweep population: 14 … Hit count: 1" separately. The 6-site mismatch set is re-confirmed present at HEAD (paths moved). The 14-site sweep population is not re-derivable today |
| D1 | Move the emission into the seam | A re-fire that reuses the envelope still emits; emission is per firing, not per role | yes (mechanism) | yes | yes | **no** (rollout) | `_cmd_effort.py:449-527` `_emit_dispatch_records`, `:543-565` the `--workflow` gate; `manage-config.py:494-520` the three CLI args; migrated callers = `execution.md:136,291` only (plus `phase-6-finalize/SKILL.md`, migrated later by #1232). 11 hand-written `[DISPATCH]` blocks across 7 docs and 6 zero-emission dispatch sites remain |
| D2 | State the corroboration limit where consumers meet it | Audit records that its two ledgers share an emitter → consistency, never completeness | yes | yes | yes | yes | `plan-retrospective/standards/execution-context-dispatch-audit.md:40` (the "Corroboration limit" block-quote) + the mirrored sentence at `ref-workflow-architecture/standards/dispatch-logging.md:48`. Both present at HEAD and survived #1225 |
| D3 | Tests (a)–(e), each verified to FAIL pre-fix | All five pass, each seen red first | 4 of 5 | mostly | **one vacuous** | no | `test_dispatch_seam_emission.py` — (a) `test_re_fired_step_emits_one_record_per_fire`, (b) `test_resolve_target_now_emits_a_dispatch_line`, (c) `test_role_fired_n_times_produces_n_records`, (d) `test_emission_set_equals_envelope_set` + `test_dispatch_line_fields_match_the_resolved_envelope`; (e) deferred by the run, since **superseded** by #1288. The backward-compat test is vacuous (mutation-proven) |

### D0 — gate satisfied as a report; its findings are still open in the tree

D0 is a report-only deliverable and it did report both directions with the population stated, and the
token-mismatch sweep with population (14) and hit count (1) stated separately — the plan's *Done when*
is met on its own terms. Two qualifications. First, the 14-site sweep population is a figure about a
corpus state I cannot reconstruct without checking out the merge base, so it is **not verifiable
today** rather than confirmed. Second, the enumerated mismatch set is not merely a finding, it is a
still-open defect: all six sites named in the report still dispatch an execution-context envelope with
**zero** emission at HEAD — `plan-marshall/workflow/planning.md:233` (light lane),
`plan-marshall/workflow/research-best-practices.md:15` (reader variant),
`persona-plan-marshall-agent/standards/agent-behavior-rules.md:85,93`,
`phase-6-finalize/standards/finalize-step-simplify.md:113`,
`extension-api/standards/ext-point-dynamic-level-executor.md:164`,
`pm-plugin-development/skills/plugin-doctor/standards/doctor-marketplace.md:45`. `grep -c DISPATCH`
returns 0 for four of those files. See G3.

### D1 — the mechanism is right; the rollout is 6 of ~17 sites

The seam itself is correct on every property I could check. `_emit_dispatch_records`
(`_cmd_effort.py:449`) writes both surfaces unconditionally once called; the call is gated on
`--workflow` at `_cmd_effort.py:544`; it sits **after** the `read_result.get('status') != 'success'`
early return at `:539-541`, so a failed resolve cannot emit; and best-effort is genuine —
`plan_logging.log_entry` wraps its whole body in `except Exception: pass`
(`plan_logging.py:309-311`), so a logging failure cannot turn a successful resolve into a failed one.
Per-firing rather than per-role is structurally true (the emission rides the resolve) and is pinned by
`test_role_fired_n_times_produces_n_records` for N ∈ {1,2,3,7}.

What is not complete is the caller migration, and the incompleteness now conflicts with a rule this
same PR shipped. `dispatch-logging.md:44` states the caller "MUST NOT also hand-write a separate
`manage-logging work "[DISPATCH]"` line", `:100` lists that shape under **"Anti-pattern
(forbidden)"**, and `:106` says "The seam emission specified above is the **sole permitted**
dispatch-emission shape." At HEAD, `grep -rn -- '--message "\[DISPATCH\]'` returns **11 matches
across 7 files** — `planning-outline.md` (4), `planning.md` (2), `workflow-pr-doctor/SKILL.md`,
`lessons-capture.md`, `adr-propose.md`, `pre-submission-self-review.md`,
`outline-workflow-detail.md`. Only three docs carry a `--workflow`-bearing resolve
(`execution.md`, `phase-6-finalize/SKILL.md`, and `manage-config/SKILL.md`'s own synopsis). The run
disclosed this as residue, honestly and in detail; the defect is that the standard was flipped to
"forbidden" in the same commit that left 11 instances of the forbidden shape in the shipped corpus.
See G2. Worse, `planning.md:274` still tells the reader to emit the hand-written line and cites
`dispatch-logging.md § Emission contract` as its authority — the cited section now forbids exactly
what the doc instructs. See G2.

### D3 — one of the eight landed tests constrains nothing

`test_bare_resolve_without_workflow_emits_nothing` is the guard for the plan's and the report's
backward-compatibility promise ("a bare resolve stays a pure read, byte-identical"). It invokes
`effort resolve-target --phase phase-5-execute` with **no `--plan-id`**, then asserts
`_dispatch_lines('bare') == []` and `_resolve_records('bare') == []`. Because the emitter routes an
absent `plan_id` to the dated global log (`_cmd_effort.py:500` → `plan_logging.get_log_path`'s global
fallback, which I executed and confirmed), those two assertions read a log the emission would never
have been written to. Both are also negative-only assertions. Mutation-proven: replacing
`if workflow:` with `if True:` at `_cmd_effort.py:544` — i.e. making every bare read-only resolve
write two log records — leaves all 9 tests **green**. See G1.

The report is candid that this test "passed because the pre-fix behaviour is 'emit nothing'", so it
was never seen red; the plan's *Done when* for D3 ("all five pass, **each seen red first**") is
therefore not met for this test either.

D3(e) was deferred to plan 290 on ownership grounds. That deferral is now moot: Rule M3 was fixed by
`eb0124c9` (#1288), which introduced `normalize_verification_step`
(`check-manifest-consistency.py:378-395`) and a test that names the exact counterfactual
(`test/plan-marshall/plan-retrospective/test_footprint_oracle_classification.py:328` — "M3 must
recognise `verify:module-tests` — what the composer actually emits"). **Superseded, not a gap.**

## Report accuracy

I re-derived every tree-checkable figure and claim in `report-01.md`. No contradiction found, with
these confirmations:

- "8-test file" — the landed blob has exactly 8 `def test_` functions
  (`git show 1da26b13:test/.../test_dispatch_seam_emission.py | grep -c '^def test_'` → 8). The file
  today has 9; the extra is `test_finalize_dispatch_emits_one_line_per_spawn`, added by #1232.
- "`default:branch-cleanup` is classified **INLINE**" — confirmed:
  `phase-6-finalize/standards/dispatch-inline-split.md:45`, under the `## Inline steps` heading.
- "M3 compares `steps != ['module-tests']` (BARE) while the composer emits `verify:module-tests`" —
  confirmed as having been true, by the fixing commit's own docstring: "Comparing the raw list against
  a bare `['module-tests']` made this rule unreachable on every manifest composed that way"
  (`check-manifest-consistency.py:406-409`).
- "The literal `--plan-id none` passes through (`names_real_plan('none')` is True) and reaches the
  global log via `get_log_path`'s no-such-plan fallthrough" — confirmed by execution.
- "`log_entry` never raises" — confirmed at `plan_logging.py:309-311`.
- "the mismatch set: 6 sites" — all six still present at HEAD (line numbers have drifted; the report's
  `research-best-practices.md:100-108` is now that file's line 15, and `planning.md:232-244` is now
  line 233).
- "No undeclared collateral change" — confirmed against the 12-file `--name-only` list.
- Cross-plan coordination note (Surface-B format vs the audit's illustrative CLI-flag rows) — handed
  off correctly and since closed: `check-dispatch-audit.py:109-110` now matches **both** forms
  (`_RESOLVE_ROLE_RE = re.compile(r'\brole=(?P<eq>\S+)|--role\s+(?P<flag>\S+)')`), with the comment at
  `:106-108` naming the seam's format explicitly.

Two statements I would call *incomplete* rather than false:

- The report presents `test_bare_resolve_without_workflow_emits_nothing` as one of the 8 tests
  covering D3 without noting that it cannot fail. Its own sentence — "the backward-compat test passed
  because the pre-fix behaviour is 'emit nothing'" — is the right observation and stops one step
  short of the conclusion (G1).
- The report's Step-6 verification verdict records "D1 PASS on every sub-property (… CLI args present;
  five-field shape byte-compatible)" but does not record that the "bare resolve stays a pure read"
  sub-property is asserted only by the vacuous test.

Claims **not verifiable from the tree** (stated, not assumed pass): the `./pw verify` figures
(19341 passed / 14 skipped), the per-commit `quality-gate` runs, CI conclusions, reviewer
participation (M = 3, 1-of-3 coverage), the auto-merge arming, and everything the run derived from
`.plan/` run logs.

## Out-of-scope compliance

Clean. The landed diff is 12 files and every one maps to a declared surface:

- The declared "effort/dispatch resolution path" → `_cmd_effort.py`, `manage-config.py`, and the two
  manage-config docs that describe the verb (`SKILL.md`, `api-reference.md`).
- The declared `ref-workflow-architecture/**` → `SKILL.md`, `dispatch-logging.md`,
  `dispatch-walkthrough.md`.
- D1's demonstration callers → `plan-marshall/workflow/execution.md`.
- D2, the one detector-adjacent item the plan **deliberately kept** →
  `plan-retrospective/standards/execution-context-dispatch-audit.md`, +4/−2 lines, **prose only**;
  no check script was touched.
- Tests + the plan directory.

The Out-of-scope block's central prohibition — "EVERY DETECTOR-SIDE CHANGE" — was respected: no file
under `plan-retrospective/scripts/` appears in the diff, and the token-mismatch was reported rather
than patched, exactly as the ownership block directs. The "two writers for one emitter" outcome the
boundary was drawn to prevent did not occur. The four other declared deferrals (ledger reconciliation
as primary remedy, session-identifier widening, per-dispatch billing columns, last-write-wins
phase-step record) are absent from the diff.

## Residue carried forward

| Residue item declared in report-01.md | Still open at HEAD? |
|---|---|
| Remaining caller migrations to the seam | **Open.** 11 hand-written `[DISPATCH]` blocks across 7 files; only `execution.md` and `phase-6-finalize/SKILL.md` carry `--workflow` resolves. The named `phase-6-finalize/SKILL.md` sites were migrated by #1232, not by a follow-up to this plan; every other named site is unchanged. G2 |
| The `until_clean` / triage loops needing rewording to "re-run the resolve (which re-emits)" | **Open** for the planning-lane loops (`planning-outline.md:138,484`, `planning.md:326`); done for the two `execution.md` loops (`:132`, `:290`) |
| Token-mismatch M3 → plan 290 | **Closed, elsewhere.** Fixed by `eb0124c9` (#1288) via `normalize_verification_step`, with a test at `test_footprint_oracle_classification.py:328` |
| `branch-cleanup` absent from the trail → detector/roster concern | **Open as a classification question**, but correctly characterised: it is an inline step (`dispatch-inline-split.md:45`), so it legitimately emits nothing from the emitter side |
| Deferrals the plan carried (session-identifier leaf overwrite, per-dispatch billing columns, last-write-wins phase-step record) | **Open**, as the plan directed. Out of scope for this verification |

## What could NOT be verified

- **D0's sweep population of 14 comparison sites and 14 co-located dispatch sites.** Both are counts
  over the corpus as it stood at the merge base; the corpus has moved (#1225, #1232, #1247, #1288 all
  touched these files). The *hit* (1) and the *mismatch set* (6) were re-confirmed; the denominators
  were not. Stated, not assumed pass.
- **Every claim sourced from `.plan/`**, exactly as the plan's own claim-label table warns: the
  15-vs-23 and 11-vs-17 trail counts, the "zero resolution records across 125 decision-log entries",
  and the 5×/7×/7× re-fire observation. `.plan/` is git-ignored and absent here. The code-side
  proxies the plan asked for instead *were* checked and confirm the mechanism claims (the resolver
  emitted nothing pre-fix; emission was hand-written per role).
- **The build, CI, review and merge record** (`./pw verify` counts, per-commit quality gates,
  reviewer coverage, auto-merge). Not derivable from the tree; not checked against GitHub, since the
  brief makes the tree the ground truth.
- **The D2 "cold read" outcome.** The plan required showing a fresh reader the reconciliation output
  and asking what it establishes. I can confirm the text exists and says the right thing
  (`execution-context-dispatch-audit.md:40` states the consistency-vs-completeness distinction
  explicitly, twice, and names the absent third source); I cannot re-run the run's cold-read
  experiment.
- **The plan's own Verification section is partly unmappable.** It names "D5(c)'s control",
  "D4's corroboration-limit statement", and "D2 must distinguish the honest not-applicable from the
  silent skip" — deliverable numbers that do not exist in this plan's narrowed D0–D3 set (they are
  residue of the pre-narrowing six-deliverable version). Those three verification obligations
  therefore have no deliverable to attach to, and the report does not mention the mismatch (it
  disclosed only the D3(e) contradiction). This is a plan-authoring defect, not a tree defect, and is
  recorded here rather than as a gap.
