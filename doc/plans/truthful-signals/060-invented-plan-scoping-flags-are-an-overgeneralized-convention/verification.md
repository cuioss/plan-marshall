# Verification — 060-invented-plan-scoping-flags-are-an-overgeneralized-convention

**Verified against:** commit `ac06e4fc94782328f87d1395472a72b7e7a8559d`   **Landed as:** PR #1150, commit `c586d2cbe0e5ee2d5c84607de2b688073e6ce0da`   **Verdict:** implemented-with-gaps

The plan is a **gate-only plan**: D1 is a read-only GATE with an explicit ⛔ STOP CONDITION, and
D2/D3 are conditional on the gate passing. The run halted at the STOP CONDITION. Verification
therefore tests two things: (i) was the halt legitimate, and (ii) is every claim D1 recorded true
of the tree. Both were checked against source; the halt is legitimate, and the recorded claims are
overwhelmingly exact, with three substantive exceptions recorded below.

## Method

What was actually done:

- Read `plan.md` and `report-01.md` in full.
- Located the landed commit (`git log --oneline -- <plandir>` → `c586d2cb`, PR #1150) and read its
  full `--name-status -M` diff: one rename (`060-….md` → `060-…/plan.md`, R100) plus one added file
  (`report-01.md`, 224 lines). No other path touched.
- Created a detached worktree at `c586d2cb` so every published count could be re-derived against
  **the tree the run actually saw**, then removed it (`git worktree remove --force`; `git worktree
  prune`). `git status --porcelain` is empty at exit.
- Re-derived every D1(b) figure at `c586d2cb` with the report's own grep patterns:
  `.add_parser(` over `marketplace/bundles/*/skills/manage-*/scripts/*.py`, the same over
  `ci_base.py`, and `add_plan_id_arg(|add_argument('--plan-id'|add_body_consumer_args(` over the
  manage-* population — including the full per-script breakdown behind the carve-out table.
- Opened and read every cited symbol at HEAD **and**, where HEAD line numbers had drifted, at
  `c586d2cb^` via `git show <sha>:<path>`:
  `ci_base.py` (`checks status` parser, `pr view` parser, `add_head_arg`, `add_body_consumer_args`,
  `add_error_style_arg`, `check_auth_cli`, `run_cli`, `extract_routing_args`, `build_parser`),
  `tools-file-ops/scripts/constants.py` (`FINDING_TYPES`),
  `tools-input-validation/scripts/input_validation.py` (`parse_args_with_toon_errors`,
  `_root_router_option_strings`, `_augment_misplaced_router_flag`),
  `workflow-integration-github/scripts/github_ops.py` (`main`, the seam call site),
  `plan-retrospective/scripts/analyze-logs.py` (log-path resolution),
  `plugin-doctor/scripts/_analyze_argument_naming.py` (module contract),
  `persona-plan-marshall-agent/standards/agent-behavior-rules.md` (§ "Never invent script
  subcommands", lines 337 and 342),
  `recipe-fix-argparse-rejection/SKILL.md`,
  `manage-change-ledger/scripts/manage-change-ledger.py` and
  `manage-locks/scripts/{build_queue,merge_lock}.py`.
- **Executed the plan's own failing invocation against the real parser** rather than reading it:
  built the live GitHub CI parser (`ci_base.build_parser`) under `uv run python`, called
  `parse_args_with_toon_errors` with `argv = ['ci','checks','status','--plan-id','X']`, and captured
  the result. Output: `error: unrecognized arguments: --plan-id X`, `EXIT CODE: 2`, and
  `_root_router_option_strings(parser)` → `[]`.
- Searched the tree for a committed `argparse_rejection` corpus:
  `git grep -l argparse_rejection -- '*.jsonl' '*.log' '*.toon' '*.json'` → empty;
  `git grep -c argparse_rejection` over the test tree → six files, all synthetic fixtures.
- Checked for supersession by later work:
  `git log -S '_augment_misplaced_router_flag' --oneline` → `4ac41326` (#1213), read and executed.

No file was modified. No mutation test was applied: the plan added no guard and no test to mutate
(D2/D3 were correctly not executed), so there was nothing to break. The finding list below is
non-empty and every entry names a file and a symbol.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D1(a) | Quantify the argparse-rejection corpus, or halt | classified corpus recorded in the report | Halted (correct) | Yes | Yes | Yes | `git grep -l argparse_rejection -- '*.jsonl' '*.log' '*.toon' '*.json'` → **0 files**; `git grep -c argparse_rejection` over tests → 6 files, all synthetic fixtures (`test/plan-marshall/plan-retrospective/test_script_failure_analysis.py:17` hits etc.). `analyze-logs.py:9-12` and `:133-135` (`resolve_logs_dir`, at `c586d2cb^`) resolve under `.plan/`; `.gitignore:45` = `.plan/*`. Corpus genuinely absent → STOP CONDITION legitimately met. |
| D1(b) | Enumerate non-plan-scoped verbs, publishing the population scanned | carve-out set recorded, denominator published | Yes | Yes | Yes | **No** — see G1 | Re-derived at `c586d2cb`: `.add_parser(` over `manage-*/scripts/*.py` = **334** across **22** scripts (report: 334 / 22 ✔); `ci_base.py` = **45** (✔); `--plan-id` additions = **120** across **15** scripts (✔). Every per-skill figure in the carve-out table reproduces exactly (manage-config 85/1, manage-run-config 28/0, manage-lessons 17/4, manage-adr 7/0, manage-architecture 35/1, manage-providers 11/0, manage-personas 1/0, manage-build-server 9+1/0, manage-interface 6/0, manage-maven-profiles 4). **But** the grep population is blind to the `create_workflow_cli` declarative shape: 3 manage-* scripts, 10 verbs, 7 `--plan-id` declarations are absent from the denominator entirely. |
| D1(c) | Choose a remedy with an explicit bias away from more prose | chosen remedy + rationale recorded | Yes (recommendation only, gate halted) | Partly — see G2 | Mostly | Yes | Doctor-already-exists claim CONFIRMED: `_analyze_argument_naming.py:3-70` — `ARGUMENT_NAMING_FLAG_UNKNOWN` / `_SUBCOMMAND_UNKNOWN`, "unconditionally active across all marketplace markdown", explicitly handles the `tools-integration-ci:ci` shape; positive controls exist at `test/pm-plugin-development/plugin-doctor/test_analyze.py:1721,1745,1769,1798`. Shared-seam claim CONFIRMED at the exact cited lines. **Prose-rule claim overstated** — `agent-behavior-rules.md:342` names the *mirror* shape, not this one. |
| D2 | Implement the D1 remedy | remedy implemented and matching D1's rationale | **Not executed — correctly gated** | Yes | n/a | n/a | Plan D1 ⛔ STOP CONDITION forbids proceeding without the corpus. Landed diff contains no `*.py`. Verified still open at HEAD by execution: `ci checks status --plan-id X` → `unrecognized arguments: --plan-id X`, exit 2. |
| D3 | Tests (a) pinned failing shape, (b) correct invocation unaffected, (c) doctor negative case | all three hold | **Not executed — correctly gated** | Yes | n/a | n/a | Same gate. No test file added in `c586d2cb`. |

### D1(b) — the published population is not the whole population

`report-01.md` § D1(b) publishes its denominator as `.add_parser(` node counts over
`manage-*/scripts/*.py`, hedged as "an upper-bound proxy for leaf verbs, not an exact verb count".
The hedge points the wrong way. The grep is not an upper bound, it is a *partial* bound: three
`manage-*` scripts build their CLI declaratively through `create_workflow_cli(...)` with a
`subcommands=[{'name': …, 'args': [{'flags': ['--plan-id'], …}]}]` literal, so they contain **zero**
`.add_parser(` nodes and **zero** matches for any of the three `--plan-id` patterns, and are
therefore invisible in both the numerator and the denominator:

- `marketplace/bundles/plan-marshall/skills/manage-change-ledger/scripts/manage-change-ledger.py`
  — 4 verbs (`worktree-sha`, `append`, `classify-outcome`, `query`), 1 `--plan-id` declaration
  (`:313`, on `append`).
- `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/build_queue.py` — 2 verbs
  (`acquire`, `release`), 2 `--plan-id` declarations.
- `marketplace/bundles/plan-marshall/skills/manage-locks/scripts/merge_lock.py` — 4 verbs
  (`acquire`, `check`, `release`, `rate-window`), 4 `--plan-id` declarations.

`manage-locks` never appears anywhere in the report — not in the 22-script list, not in the
carve-out table. The report *does* flag `manage-change-ledger` ("has no `.add_parser(` and no
`--plan-id` addition — it uses a different dispatch shape … recorded, not resolved here"), which is
true of the greps but reads as "this skill does not take `--plan-id`"; it does. The plan's
Verification section makes the published population load-bearing ("A list of exceptions with no
denominator is not a carve-out, it is a sample"), so an unstated blind spot in the population is a
real incompleteness rather than a cosmetic one. See G1.

### D1(c) — the "prose rule already names this exact signature" claim

`report-01.md` § D1(c) asserts: "The prose prevention rule ALREADY EXISTS and already names this
exact signature — `persona-plan-marshall-agent` § 'Never invent script subcommands', signature #2
'Top-level `--plan-id`/`--project-dir` where the flag is verb-scoped' (`agent-behavior-rules.md:342`)."

Line 342 exists and reads exactly as quoted (verified verbatim), and line 337's "Why" does concede
the failure is structural — so the citations are accurate. The *inference* is not. Signature #2
describes the opposite defect and prescribes the opposite move:

> placing `--plan-id` or `--project-dir` **immediately after the notation** … where those flags are
> declared **on the subcommand** … Example: `manage-architecture --plan-id X resolve …` → canonical
> `manage-architecture resolve --command quality-gate --audit-plan-id X`.

Plan 060's failure is the mirror image: on `ci`, `--plan-id` is a **router** flag consumed by
`extract_routing_args` (`ci_base.py:570-599`) before argparse ever runs, and is declared **nowhere**
on the parser tree — `_root_router_option_strings(parser)` returns `[]` (executed, see Method). So
`ci --plan-id X checks status` works and `ci checks status --plan-id X` fails, which is precisely
the placement signature #2 tells the reader to adopt. The loaded prose rule therefore does not name
this signature, and its worked example points a `ci` caller *toward* the failing shape. This matters
because the report uses the claim to argue the prose lane is saturated; a future corpus-enabled run
reading that conclusion would skip a genuinely uncovered signature. See G2.

## Report accuracy

Re-derived at the moment of stating. Contradictions found: **one** (G2, above — the "already names
this exact signature" inference; the citation itself is exact, the inference is not). Two further
imprecisions, neither rising to a contradiction:

- The carve-out table lists `manage-maven-profiles (4)` under "global infra … no (or nearly no)
  `--plan-id`". It has 4 `.add_parser(` nodes and **1** `--plan-id` addition (`profiles.py`). The
  row's own hedge ("or nearly no") covers it; the bare `(4)` is inconsistent with the `(n, m)` form
  used in every other cell.
- The report header still reads `**PR:** _pending_` although the plan landed as PR #1150. See G4.

Everything else re-derived clean. Specifically checked and **confirmed exact**:

- D1(b) counts: 334 `.add_parser(` / 22 scripts / 45 in `ci_base.py` / 120 `--plan-id` across 15
  scripts — all four reproduce byte-for-byte at `c586d2cb` with the report's stated patterns; the
  per-skill cluster figures (26/19/14/10/9/8/8/7/6/3/3) sum to 113 and, with architecture 1 +
  config 1 + lessons 4 + maven-profiles 1, to exactly 120.
- Every per-skill parser/`--plan-id` pair in the carve-out table (10 rows) reproduces exactly.
- Claim #1 CONFIRMED: `ci_base.py:1072-1075` — `checks status` declares `--pr-number`, `--head`
  (via `add_head_arg`), `--error-style`; no `--plan-id`.
- Claim #4 CONFIRMED: `tools-file-ops/scripts/constants.py:118-143` — exactly 14 members, no
  `escalation`. Count re-derived by enumeration.
- Claim #5 REFUTED correctly: `ci_base.py:891-902` — `pr view` **does** declare `--pr-number`;
  `add_head_arg` is registered on exactly **7** subparsers (re-counted: `pr view`, `pr merge`,
  `pr auto-merge`, `pr safe-merge`, `pr merge-queue`, `pr update-branch`, `checks status`), matching
  its docstring's "exactly seven … every one of them also declares `--pr-number`" invariant.
- Claim #6 CONFIRMED: `ci_base.py:750-769` — `if returncode != 0: return False, login_message`, with
  `run_cli` returning `127` on `FileNotFoundError` (`:736-738`) and `124` on timeout (`:739-740`).
  Cited line numbers are exact at HEAD.
- Claim #8 CONFIRMED: `recipe-fix-argparse-rejection/SKILL.md:9-13` and `:22-29` — line ranges exact;
  self-describes as the post-rejection remediation procedure and explicitly disclaims duplicating the
  prevention rule.
- Claim #9 REFUTED correctly: `parse_args_with_toon_errors` at `input_validation.py:963-1023` **at
  the run's tree** (verified via `git show c586d2cb^:…`), with the fall-through `orig(message)` at
  `:1012-1013` — both citations exact to the line. Consumer `github_ops.py:1817` — exact at
  `c586d2cb^` (it is `:1855` at HEAD after later drift).
- D1(c) doctor claim: `_analyze_argument_naming.py:3-70` — the quoted "unconditionally active across
  all marketplace markdown" phrasing and the `tools-integration-ci:ci` handling are both present.
- Exit-2 mechanism narrative: confirmed by reading `extract_routing_args` (`:570-599`) **and** by
  executing the parser. The report labelled this "code-confirmed, not empirically reproduced"; this
  verification supplies the empirical reproduction and it matches the narrative exactly.
- Build-gate claim (no `*.py` in the diff): confirmed by `git show --name-status -M c586d2cb`.
- Verification sub-agent's "no undeclared collateral change": confirmed.

## Out-of-scope compliance

Clean. The landed diff is exactly two paths, both inside the plan's own directory: an R100 rename of
`060-….md` into `060-…/plan.md`, and the new `report-01.md`. No `*.py`, no `marketplace/bundles/**`,
no `test/**`, no `.claude/**`. The three declared out-of-scope areas were respected:

- **Fail-open survivability** — not touched, correctly attributed to another plan.
- **Remediation overlap** — the run *read* `recipe-fix-argparse-rejection/SKILL.md` to confirm
  non-overlap (as the plan required) and changed nothing in it.
- **Leaf PATH truncation** — recorded as unverifiable, not investigated further, and the report
  explicitly states that fixing the diagnostic alone would not fix the environment. That is exactly
  what the plan's out-of-scope clause asked for.

The plan's ⛔ hard constraint ("no verb's real argument surface may be widened merely to absorb the
mistake") is trivially satisfied: no argument surface changed.

## Residue carried forward

| report-01 residue item | Still open at HEAD? | Evidence |
|---|---|---|
| **D2/D3 for a corpus-enabled run** — re-derive D1(a), complete the D1(b) denominator, implement a runtime actionable argparse error in `parse_args_with_toon_errors`'s fall-through | **Open** — and with a misleading near-miss, see G3 | Commit `4ac41326` (#1213) added `_augment_misplaced_router_flag` (`input_validation.py:982-1016`) into exactly that fall-through. It does **not** fire for the `ci` surface: executed at HEAD, `ci checks status --plan-id X` still yields a bare `unrecognized arguments: --plan-id X` / exit 2, because `_root_router_option_strings(parser)` returns `[]` — `ci`'s router flags are stripped by `extract_routing_args` and never declared on the parser. |
| **`check_auth_cli` misattributed diagnostic** (`ci_base.py:750-769`) | **Open, unchanged** | Read at HEAD: the function is byte-identical to the cited form; `127` and `124` still surface as "Not authenticated". |
| **Leaf PATH truncation** | **Open, still unverifiable from the tree** | Requires a dispatched leaf; no in-repo artifact settles it. |
| **`FINDING_TYPES` has no `escalation`** — whether that absence is a defect | **Open** | `constants.py:118-143` unchanged at HEAD; the question needs the external corpus. |
| **Two refuted claims vindicating HYPOTHESIS labelling** | Not residue — informational, and both re-verified above | — |

## What could NOT be verified

Stated explicitly rather than passed silently:

- **The D1(a) corpus itself.** Its absence is verified (no tracked record files; `.plan/` git-ignored
  at `.gitignore:45`), so the STOP CONDITION trigger is verified. What the distribution would have
  shown — and therefore whether claim #2's "2 of 4 clusters" is true — remains unverifiable from this
  repository. The report says so, and that remains correct.
- **The dispatched-leaf PATH truncation** (claim #7). Cannot be reproduced without a dispatched leaf.
- **Whether `ARGUMENT_NAMING_FLAG_UNKNOWN` would actually flag a *document* writing
  `ci checks status --plan-id X`.** The rule cluster's existence, activation and ci-awareness are
  verified from `_analyze_argument_naming.py` and its four positive-control tests, but exercising the
  cluster requires `.plan/execute-script.py`, which this clone does not have. The report's claim was
  the narrower "it already flags a documented flag a script's argparse does not declare", which *is*
  verified; the ci-specific behaviour is not.
- **The verification sub-agent's alternative denominators (324 / 119).** No glob scope was found that
  reproduces them, and the sub-agent's own commands are not recorded in the report. The report's own
  figures (334 / 120) reproduce exactly, so the reconciliation paragraph's conclusion holds
  regardless; the 324/119 pair itself could not be re-derived.
- **Whether the run's Step-6 sub-agent dispatch and Step-8 merge gate happened as the contract check
  claims.** Those are process assertions with no tree artifact; only their outcome (a clean,
  in-scope, merged diff) is observable.
