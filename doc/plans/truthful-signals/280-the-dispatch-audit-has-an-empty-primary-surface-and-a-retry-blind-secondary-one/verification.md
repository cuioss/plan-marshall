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
| D0 | GATE: derive the emission population both directions + token-mismatch sweep | Both directions enumerated with population stated; token-mismatch sweep reports population and hit count separately | yes (report-only, mutates nothing) | yes | yes | partly | `report-01.md` § D0 states both directions, and "Sweep population: 14 … Hit count: 1" separately. The 6-site mismatch set is re-confirmed present at HEAD (all six paths moved), but it is **incomplete** — the orchestrator lane's canonical dispatch form was never swept (G7). Direction 1's "14 co-located dispatch sites" is re-derivable at the merge base and is consistent; the token-mismatch sweep's own 14-site population is not |
| D1 | Move the emission into the seam | A re-fire that reuses the envelope still emits; emission is per firing, not per role | yes (mechanism) | yes | yes | **no** (rollout) | `_cmd_effort.py:449-517` `_emit_dispatch_records`, `:546-566` the `--workflow` gate; `manage-config.py:494-520` the three CLI args; migrated callers = `execution.md:136,291` and `phase-6-finalize/SKILL.md:622,951,1015,1498` (the latter migrated later by #1232). 11 hand-written `[DISPATCH]` blocks across 7 docs, 6 zero-emission dispatch sites and the orchestrator lane's canonical form remain |
| D2 | State the corroboration limit where consumers meet it | Audit records that its two ledgers share an emitter → consistency, never completeness | yes | yes | yes | yes | `plan-retrospective/standards/execution-context-dispatch-audit.md:40` (the "Corroboration limit" block-quote) + the mirrored sentence at `ref-workflow-architecture/standards/dispatch-logging.md:48`. Both present at HEAD and survived #1225 |
| D3 | Tests (a)–(e), each verified to FAIL pre-fix | All five pass, each seen red first | 4 of 5 | mostly | **one vacuous** | no | `test_dispatch_seam_emission.py` — (a) `test_re_fired_step_emits_one_record_per_fire`, (b) `test_resolve_target_now_emits_a_dispatch_line`, (c) `test_role_fired_n_times_produces_n_records`, (d) `test_emission_set_equals_envelope_set` + `test_dispatch_line_fields_match_the_resolved_envelope`; (e) deferred by the run, since **superseded** by #1288. The backward-compat test is vacuous (mutation-proven) |

### D0 — gate satisfied as a report; its findings are still open in the tree

D0 is a report-only deliverable and it did report both directions with the population stated, and the
token-mismatch sweep with population (14) and hit count (1) stated separately — the plan's *Done when*
is met on its own terms. Three qualifications.

First, the two "14"s in the report are different figures and re-derive differently. Direction 1's
"14 live co-located dispatch sites" **is** reconstructible at the merge base:
`git grep -n -- '--message "\[DISPATCH\]' 1da26b13^ -- marketplace/ .claude/` returns **19 blocks
across 11 files**; excluding the three that are the standard's own worked examples
(`dispatch-logging.md:49,70`, `dispatch-walkthrough.md:55`) leaves **16 blocks in 9 files**, which
collapses to 14 *sites* if `phase-6-finalize/SKILL.md`'s three restatements of one dispatch pattern
(`:599,972,1405`) are counted as one. The figure is therefore **consistent under a stated reading**,
not unverifiable — an earlier draft of this document called it not re-derivable, which was wrong.
The token-mismatch sweep's separate "14 comparison/membership sites" population depends on the
sweep's own selection criteria and is **not** reconstructible from the tree; its hit (1) and the
named site are.

Second, the enumerated mismatch set is **incomplete**. It swept the plan lifecycle and missed the
orchestrator lifecycle: `persona-plan-orchestrator/standards/orchestration-model.md:130-135` is the
canonical `execution-context-{level}` dispatch shape for the whole orchestrator lane, resolves with
`--default` and no dispatch context, and `grep -rn DISPATCH` over `persona-plan-orchestrator/` and
`plan-orchestrator/` returns **zero matches**. See G7.

Third, the enumerated mismatch set is not merely a finding, it is a still-open defect: all six sites named in the report still dispatch an execution-context envelope with
**zero** emission at HEAD — `plan-marshall/workflow/planning.md:233` (light lane),
`plan-marshall/workflow/research-best-practices.md:15` (reader variant),
`persona-plan-marshall-agent/standards/agent-behavior-rules.md:85,93`,
`phase-6-finalize/standards/finalize-step-simplify.md:113`,
`extension-api/standards/ext-point-dynamic-level-executor.md:164`,
`pm-plugin-development/skills/plugin-doctor/standards/doctor-marketplace.md:45`. `grep -c DISPATCH`
returns 0 for **five** of those six files (all but `planning.md`, whose 2 hits are the G2 sites at
`:286,326`, not the light-lane site at `:233`). See G3.

### D1 — the mechanism is right; the rollout is 6 of 22 sites

The seam itself is correct on every property I could check. `_emit_dispatch_records`
(`_cmd_effort.py:449`) writes both surfaces unconditionally once called; the call is gated on
`--workflow` at `_cmd_effort.py:546`; it sits **after** the `read_result.get('status') != 'success'`
early return at `:536-537`, so a failed resolve cannot emit; and best-effort is genuine —
`plan_logging.log_entry` wraps its whole body in `except Exception: pass`
(`plan_logging.py:313-315`), so a logging failure cannot turn a successful resolve into a failed one.
Per-firing rather than per-role is structurally true (the emission rides the resolve) and is pinned by
`test_role_fired_n_times_produces_n_records` for N ∈ {1,2,3,7}.

What is not complete is the caller migration, and the incompleteness now conflicts with a rule this
same PR shipped. `dispatch-logging.md:44` states the caller "MUST NOT also hand-write a separate
`manage-logging work "[DISPATCH]"` line", `:102` lists that shape under **"Anti-pattern
(forbidden)"**, and `:105` says "The seam emission specified above is the **sole permitted**
dispatch-emission shape." At HEAD, `grep -rn -- '--message "\[DISPATCH\]'` returns **11 matches
across 7 files** — `planning-outline.md` (4), `planning.md` (2), `workflow-pr-doctor/SKILL.md`,
`lessons-capture.md`, `adr-propose.md`, `pre-submission-self-review.md`,
`outline-workflow-detail.md`. Only two live caller docs carry a `--workflow`-bearing resolve — `execution.md` (2 sites) and
`phase-6-finalize/SKILL.md` (4 sites); the remaining `--workflow` occurrences are the specifications
and worked examples themselves (`dispatch-logging.md`, `dispatch-walkthrough.md`,
`manage-config/SKILL.md`, `api-reference.md`, `execution-context-dispatch-audit.md`). The run
disclosed this as residue, honestly and in detail; the defect is that the standard was flipped to
"forbidden" in the same commit that left 11 instances of the forbidden shape in the shipped corpus.
See G2. Worse, `planning.md:275` still tells the reader to emit the hand-written line and cites
`dispatch-logging.md § Emission contract` as its authority — the cited section now forbids exactly
what the doc instructs; the same instruction recurs without the citation at `:315`. See G2.

### D3 — one of the eight landed tests constrains nothing

`test_bare_resolve_without_workflow_emits_nothing` is the guard for the plan's and the report's
backward-compatibility promise ("a bare resolve stays a pure read, byte-identical"). It invokes
`effort resolve-target --phase phase-5-execute` with **no `--plan-id`**, then asserts
`_dispatch_lines('bare') == []` and `_resolve_records('bare') == []`. Because the emitter routes an
absent `plan_id` to the dated global log (`_cmd_effort.py:501` → `plan_logging.get_log_path`'s global
fallback, which I executed and confirmed), those two assertions read a log the emission would never
have been written to. Both are also negative-only assertions. Mutation-proven: replacing
`if workflow:` with `if True:` at `_cmd_effort.py:546` — i.e. making every bare read-only resolve
write two log records — leaves all 9 tests **green**, and (re-run during adversarial review) all
**1151** tests in `test/plan-marshall/manage-config/` green. See G1.

The report is candid that this test "passed because the pre-fix behaviour is 'emit nothing'", so it
was never seen red; the plan's *Done when* for D3 ("all five pass, **each seen red first**") is
therefore not met for this test either.

D3(e) was deferred to plan 290 on ownership grounds. That deferral is now moot: Rule M3 was fixed by
`eb0124c9` (#1288), which introduced `normalize_verification_step`
(`check-manifest-consistency.py:378-395`) and a test that names the exact counterfactual
(`test/plan-marshall/plan-retrospective/test_footprint_oracle_classification.py:327-356` — "M3 must
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
  (`check-manifest-consistency.py:403-407`).
- "The literal `--plan-id none` passes through (`names_real_plan('none')` is True) and reaches the
  global log via `get_log_path`'s no-such-plan fallthrough" — confirmed by execution.
- "`log_entry` never raises" — confirmed at `plan_logging.py:309-311`.
- "the mismatch set: 6 sites" — all six still present at HEAD, and **every one** of the six line
  references has drifted, not the two originally named: `planning.md:232-244`→`:233`,
  `research-best-practices.md:100-108`→`:15`, `agent-behavior-rules.md:101-108`→`:85,93`,
  `finalize-step-simplify.md:124-129`→`:113`, `ext-point-dynamic-level-executor.md:171-179`→`:164`,
  `doctor-marketplace.md:51`→`:45`. The set is also **incomplete**: the orchestrator lane's canonical
  dispatch form (`orchestration-model.md:130-135`) creates execution-context envelopes and emits on
  neither surface, and D0 never swept it. See G7.
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
| Remaining caller migrations to the seam | **Open.** 11 hand-written `[DISPATCH]` blocks across 7 files — 9 at real dispatch sites in 5 files (G2), 2 doc-echoes in 2 files that hold no resolve at all (G4). Only `execution.md` and `phase-6-finalize/SKILL.md` carry `--workflow` resolves. The named `phase-6-finalize/SKILL.md` sites were migrated by #1232, not by a follow-up to this plan; every other named site is unchanged. G2, G4 |
| The `until_clean` / triage loops needing rewording to "re-run the resolve (which re-emits)" | **Open** for the planning-lane loops — the re-fire wording lives at `planning-outline.md:130` (`outline_prompt` re-dispatch), `:203` and `:508` (the two `until_clean` q-gate auto-loops) and `planning.md:304` (`refine_prompt` re-dispatch), **not** at the `:138,484,326` command lines an earlier draft cited; done for the two `execution.md` loops (`:132`, `:287`) |
| Token-mismatch M3 → plan 290 | **Closed, elsewhere.** Fixed by `eb0124c9` (#1288) via `normalize_verification_step`, with a test at `test_footprint_oracle_classification.py:328` |
| `branch-cleanup` absent from the trail → detector/roster concern | **Open as a classification question**, but correctly characterised: it is an inline step (`dispatch-inline-split.md:45`), so it legitimately emits nothing from the emitter side |
| Deferrals the plan carried (session-identifier leaf overwrite, per-dispatch billing columns, last-write-wins phase-step record) | **Open**, as the plan directed. Out of scope for this verification |

## What could NOT be verified

- **D0's token-mismatch sweep population of 14 comparison/membership sites.** That denominator
  depends on the sweep's own selection criteria and is not reconstructible from the tree. The *hit*
  (1) and the named site were re-confirmed. Stated, not assumed pass. (Direction 1's separate
  "14 co-located dispatch sites" **was** re-derived at the merge base during adversarial review — see
  § D0 above — so it is no longer listed here.)
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

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked.** Every `high` gap, every clean-pass deliverable row, and every "swept, clean" claim, plus
a representative slice of the figures:

- **Baseline.** `git merge-base --is-ancestor a884110e HEAD` → ancestor;
  `git diff a884110e HEAD -- .../_cmd_effort.py` → **empty**. The file has not moved since `1da26b13`,
  so the line references in the first draft were transcription errors, not drift. Every `_cmd_effort.py`
  reference in both documents was re-derived with `grep -n` and corrected (`544`→`546`, `539-541`→
  `536-537`, `500`→`501`, `449-527`→`449-517`, `556-560`→`553-557`).
- **G1 re-run and widened.** `git diff --quiet` on `_cmd_effort.py` → exit 0; bytes snapshotted to the
  scratchpad; `if workflow:` → `if True:`. The 9-test file stayed green **and so did all 1151 tests in
  `test/plan-marshall/manage-config/`** — a stronger result than the original 9-test claim. Restored
  from the saved bytes (md5 match), `git diff --quiet` → exit 0.
- **G1's proposed Fix executed, not merely reviewed.** Patched the test to pass `--plan-id bare`,
  re-applied the `if True:` mutation, and observed the required red:
  `Left contains one more item: '[DISPATCH] … workflow=None plan_id=bare'` — 1 failed / 8 passed.
  Restored source, re-ran → 9 passed; restored the test, `git diff --quiet` on both → exit 0.
- **G6's mechanism executed.** `_emit_dispatch_records` was called directly with
  `plan_id ∈ {'NO_PLAN', None, 'none', 'real-plan'}` under a captured `log_entry`. `'NO_PLAN'` emits
  `plan_id=NO_PLAN`; the other three behave as documented. Separately executed
  `get_log_path('NO_PLAN','work')` → the dated **global** log, which narrows the defect to the display
  field alone (the routing guard is belt-and-braces).
- **Both "swept, clean" sweeps re-run, and one re-run broader.** `grep -rn -- '--message "\[DISPATCH\]'`
  over `marketplace/` + `.claude/` → 11 matches / 7 files (confirms the figure). The **broader** sweep —
  every `DISPATCH` token in every `.md` under both trees, then every `effort resolve-target` invocation,
  then every `Task: plan-marshall:{target}` dispatch block — surfaced what the narrow phrasing missed:
  the orchestrator lane (**G7**), and `phase-5-execute/SKILL.md:933`, a third prose echo of the
  now-migrated emission (a by-reference pointer to `execution.md`, so not filed separately).
- **D0's merge-base figures re-derived** with `git grep` at `1da26b13^` — 19 blocks / 11 files — which
  refutes this document's earlier "not re-derivable today" for Direction 1.
- **Landed-commit facts re-derived:** `git show 1da26b13 --name-only` → 12 files ✅;
  `git show 1da26b13:test/.../test_dispatch_seam_emission.py | grep -c '^def test_'` → 8 ✅.
- **Supersession re-checked at symbol:** `normalize_verification_step` at
  `check-manifest-consistency.py:378-395`, its consumer's docstring at `:403-407`, and the D3(e)
  counterfactual test (`TestTestsOnlyRuleFires`, `test_footprint_oracle_classification.py:327-356`,
  with a negative control) — all present. Supersession upheld.
- **Every cited doc line re-opened**: `dispatch-logging.md` (whole file, all 13 cited lines),
  `execution-context-dispatch-audit.md:40`, `check-dispatch-audit.py:104-110`, `plan_logging.py:295-315`
  (including the `LOG_ENABLED` kill switch — hard-coded `True`, not a gap),
  `marketplace_paths.py:60-100`, `orchestration-model.md:125-150`, `lessons-capture.md:50-70`,
  `adr-propose.md:38-56`, all four `phase-6-finalize/SKILL.md` resolve sites, `planning.md:225-330`,
  `planning-outline.md:128-215,470-510`.

**NOT re-checked.** The `./pw verify` figures, per-commit quality gates, CI conclusions, reviewer
participation, auto-merge arming, and everything sourced from `.plan/` (the 15-vs-23 and 11-vs-17 trail
counts, the 125-entry decision-log claim, the 5×/7×/7× observation) — all absent from this clone, as the
plan's own claim-label table warns. The D2 cold-read experiment was not re-run (the text was re-read and
still says the right thing). The token-mismatch sweep's 14-site denominator was not reconstructed. No
full-repository build was run; the mutation work was scoped to `test/plan-marshall/manage-config/`.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| G1 | `test_bare_resolve_without_workflow_emits_nothing` is vacuous; `high` | **upheld and strengthened** | Mutation survives the whole 1151-test `manage-config` suite, not just the 9-test file. Textbook `high` (a guard that passes against the defect it names). Refs `271`→`273`, `544`→`546`. Proposed Fix **executed** and observed red |
| G2 | 11 hand-written blocks / 7 files; `medium` | **re-scoped + re-severitied to `high`** | 2 of the 7 files (`lessons-capture.md`, `adr-propose.md`) hold **no `effort resolve-target` call at all**, so the Fix ("add `--workflow` to the call that already precedes the dispatch") was uncarryable there; those blocks moved to G4. Now 9 blocks / 5 files. `high` because the un-migrated re-fire loops (`planning-outline.md:130,203,508`, `planning.md:304`) still ship the exact retry blindness D1 was declared load-bearing to close, and `planning.md:275` instructs the forbidden shape citing the forbidding standard. Second instance found at `:315`. `274`→`275`, `:100`→`:102`, `:106`→`:105` |
| G3 | 6 zero-emission sites; `medium` | **upheld, corrected** | All six re-confirmed at HEAD. "`grep -c DISPATCH` returns 0 for four" → **five**. Added a caveat: `research-best-practices.md:15` also mis-describes what `resolve-target` returns (contradicts `data-model.md:262` / `effort-roles.md:86`), which an implementer must fix in the same edit |
| G4 | 2 finalize doc-echoes; `medium` | **upheld, refs corrected + scope widened** | Blocks are at `lessons-capture.md:63-67` and `adr-propose.md:48-52` (not `62-66` / `42-51`); headings at `:59` / `:44` must go too. Now explicitly owns both blocks, and states the G2 overlap |
| G5 | `role` Source cell stale; `low` | **upheld, refs corrected** | The `role` row is `dispatch-logging.md:31`, not `:32` (`:32` is `workflow`). Fallback chain is `_cmd_effort.py:553-557` + `:495`, not `556-560`. Confirmed by executing the resolver: `--default` returns no `role` key, so `role=` renders `default` |
| G6 | `NO_PLAN` emits the sentinel; `low` | **upheld by execution** | Function run on all four argument shapes; `plan_id=NO_PLAN` confirmed. `dispatch-logging.md:35`→`:33`. Narrowed: routing already lands in the global log for the sentinel, so only the display field is defective. `low` correct — reachable but no current caller passes it to this verb |
| G7 | *(new)* | **added** | `orchestration-model.md:130-135` is the canonical `execution-context` dispatch shape for the orchestrator lane, resolves `--default` with no dispatch context, and `grep -rn DISPATCH` over `persona-plan-orchestrator/` + `plan-orchestrator/` returns **zero**. `dispatch-logging.md:3,64,105` scope the obligation to it and supply the `--plan-id none` affordance. D0 never swept this lane, so its "both directions enumerated" population was incomplete. `medium` |
| Verdict | `implemented-with-gaps` | **upheld** | No deliverable is unimplemented. D0's gate was met on its own terms (report-only), D1's seam meets its *Done when* at the seam, D2 is complete, and D3's five test obligations all exist in the tree once #1288's supersession is counted. What fails is completeness (rollout) and one test's constraining power — gaps, not absence. `partially-implemented` would over-state it |
| D1 row (clean-pass sub-properties) | seam correct on every checkable property | **upheld** | Early return, `--workflow` gate, best-effort `log_entry`, and per-firing emission all re-read at symbol; the emission genuinely rides the resolve |
| D2 row (clean pass) | corroboration limit stated where consumers meet it | **upheld** | `execution-context-dispatch-audit.md:40` block-quote re-read in full; it states consistency-vs-completeness twice and names the absent third source. Mirrored at `dispatch-logging.md:48` |
| D3(e) supersession | "superseded, not a gap" | **upheld** | The named test exists, fires M3 on a production-file footprint under the canonical `verify:module-tests` shape, and carries a negative control |
| "12 files", "8 tests" | landed-diff figures | **upheld** | Both re-derived from `git show 1da26b13` |
| "14-site sweep population not re-derivable" | *(this document's own claim)* | **refuted** | Direction 1's 14 **is** reconstructible at `1da26b13^` (19 blocks / 11 files → 16 excluding the standard's own examples → 14 sites under one stated collapse). Only the token-mismatch sweep's separate 14 remains unreconstructible. Corrected in § D0 and § What could NOT be verified |
| "the mismatch set: 6 sites — line numbers have drifted (two named)" | | **corrected** | **All six** drifted, not two. And the set is incomplete (G7) |
| "Only three docs carry a `--workflow`-bearing resolve" | | **corrected** | Two *live caller* docs (`execution.md`, `phase-6-finalize/SKILL.md`); the other `--workflow` occurrences are specs and worked examples, including `dispatch-walkthrough.md`'s two migrated examples, which the original sentence omitted |
| `plan_logging.py:309-311`, `check-manifest-consistency.py:406-409` | cited line ranges | **corrected** | Actual `313-315` and `403-407` |

**Documents corrected.** In `gaps.md`: G2 re-scoped from 11 blocks / 7 files to 9 / 5 and re-severitied
to `high`, with its Fix made carryable per file and its loop-rewording targets re-pointed at the actual
loop prose; G4 given the two blocks G2 could not fix, with exact extents; G1, G3, G5, G6 given corrected
file:line references and execution-backed evidence; **G7 added**; a `## Refuted during adversarial review`
section added recording that nothing was refuted and why the G2/G4 overlap is not a duplicate to delete;
**Open items 6 → 7**. In `verification.md`: the D0 "not re-derivable" claim refuted and replaced with the
merge-base derivation; the D0 mismatch set marked incomplete; the D1 rollout restated as 6 of 22 sites;
"four of those files" → five; the `--workflow`-bearing-docs claim corrected; the residue table's loop and
migration rows re-pointed; every stale line reference fixed; this section appended. The verdict is
unchanged.

**Residual doubt — what a third reviewer should look at first.**

1. **Whether G7 is one gap or a lane-wide class.** I confirmed the canonical shape emits nothing and
   that `analyze.md:38` / `decompose.md:34` point at it, but I did not enumerate every orchestrator
   sub-step dispatch. If other verbs compose their own dispatch rather than using the canonical form,
   G7 under-counts the same way D0 did.
2. **The instance-granularity convention.** The brief says a finding is recorded per instance; G2 (9
   blocks), G3 (6 sites) and G4 (2 files) each group by remediation unit instead. I preserved the
   existing convention for citability rather than shredding stable IDs, but a third reviewer may
   legitimately want 17 rows where there are now 3.
3. **G2's severity.** I raised it to `high` on the "shipped false signal" limb of the rubric. The
   counter-argument is that the *false clean* is produced by the detector, and the plan's Out-of-scope
   block assigns the detector to `code-intelligence-substrate/170` and `/290`. If a reviewer weights
   that mediation heavily, `medium` is defensible.
4. **`test_bare_resolve_without_workflow_emits_nothing` is not the only candidate.** I mutation-tested
   one guard. The other seven landed tests were confirmed to bite only via the original document's
   Surface-B control; a per-test mutation sweep was not run.
