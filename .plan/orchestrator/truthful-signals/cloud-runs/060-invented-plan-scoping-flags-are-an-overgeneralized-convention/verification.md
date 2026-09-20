# Verification — 060-invented-plan-scoping-flags-are-an-overgeneralized-convention

**Verified against:** commit `ac06e4fc94782328f87d1395472a72b7e7a8559d`   **Landed as:** PR #1150, commit `c586d2cbe0e5ee2d5c84607de2b688073e6ce0da`   **Verdict:** partially-implemented

The plan is a **gate-only plan**: D1 is a read-only GATE with an explicit ⛔ STOP CONDITION, and
D2/D3 are conditional on the gate passing. The run halted at the STOP CONDITION. Verification
therefore tests two things: (i) was the halt legitimate, and (ii) is every claim D1 recorded true
of the tree. Both were checked against source; the halt is legitimate, and the recorded claims are
largely exact, with the exceptions recorded below.

**On the verdict.** Two of the plan's three deliverables (D2, D3) carry no implementation, and the
plan's stated Goal — "the invented-flag failure is structurally impossible or self-correcting" — is
not met, so the honest headline is `partially-implemented`, not `implemented-with-gaps`. The
partiality is the plan's **own designed outcome**, not a run defect: the ⛔ STOP CONDITION forbids
D2/D3 without the corpus, and the corpus is verifiably absent. Recording it as
`implemented-with-gaps` would overstate delivery in exactly the direction this epic exists to
correct. (Changed during adversarial review — see § Adversarial review.)

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
  `_root_router_option_strings(parser)` → `set()` (the function returns a `set[str]`; an earlier
  draft of this document wrote `[]`).
- Searched the tree for a committed `argparse_rejection` corpus:
  `git grep -l argparse_rejection -- '*.jsonl' '*.log' '*.toon' '*.json'` → empty;
  `git grep -c argparse_rejection` over the test tree → **five** files, all test modules
  (`test_review_completeness.py`, `test_configurable_contract.py`, `test_script_failure_analysis.py`,
  `test_dispatch_boundary_error.py`, `test_github_pr.py`), none a record corpus. An earlier draft
  said "six"; the figure did not re-derive and was corrected during adversarial review.
- Checked for supersession by later work:
  `git log -S '_augment_misplaced_router_flag' --oneline` → `4ac41326` (#1213), read and executed.

No file was modified. No mutation test was applied: the plan added no guard and no test to mutate
(D2/D3 were correctly not executed), so there was nothing to break. The finding list below is
non-empty and every entry names a file and a symbol.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D1(a) | Quantify the argparse-rejection corpus, or halt | classified corpus recorded in the report | Halted (correct) | Yes | Yes | Yes | `git grep -l argparse_rejection -- '*.jsonl' '*.log' '*.toon' '*.json'` → **0 files**; `git grep -c argparse_rejection` over tests → **5** files, all test modules, none a record corpus (`test/plan-marshall/plan-retrospective/test_script_failure_analysis.py:17` hits etc.). Re-swept adversarially with a broader pattern and no extension filter: `git grep -lE 'argparse_rejection\|unrecognized arguments\|exit_code.{0,3}:.{0,3}2' -- '*.jsonl' '*.json' '*.log' '*.toon' '*.ndjson' '*.csv'` → **one** file, the synthetic fixture `test/plan-marshall/plan-retrospective/fixtures/archived-plan/logs/script-execution.log`. `analyze-logs.py:9-12` and `:133-135` (`resolve_logs_dir`, at `c586d2cb^`) resolve under `.plan/`; `.gitignore:45` = `.plan/*`. Corpus genuinely absent → STOP CONDITION legitimately met. |
| D1(b) | Enumerate non-plan-scoped verbs, publishing the population scanned | carve-out set recorded, denominator published | Yes | Yes | Yes | **No** — see G1 | Re-derived at `c586d2cb`: `.add_parser(` over `manage-*/scripts/*.py` = **334** across **22** scripts (report: 334 / 22 ✔); `ci_base.py` = **45** (✔); `--plan-id` additions = **120** across **15** scripts (✔). Every per-skill figure in the carve-out table reproduces exactly (manage-config 85/1, manage-run-config 28/0, manage-lessons 17/4, manage-adr 7/0, manage-architecture 35/1, manage-providers 11/0, manage-personas 1/0, manage-build-server 9+1/0, manage-interface 6/0, manage-maven-profiles 4). **But** the grep population is blind to the `create_workflow_cli` declarative shape: 3 manage-* scripts, 10 verbs, 7 `--plan-id` declarations are absent from the denominator entirely. |
| D1(c) | Choose a remedy with an explicit bias away from more prose | chosen remedy + rationale recorded | Yes (recommendation only, gate halted) | Partly — see G2 | **No** — see G6 | **No** — see G2, G6 | Cluster exists as described: `_analyze_argument_naming.py:3-70` — `ARGUMENT_NAMING_FLAG_UNKNOWN` / `_SUBCOMMAND_UNKNOWN`, "unconditionally active across all marketplace markdown", names the `tools-integration-ci:ci` shape; positive controls at `test/pm-plugin-development/plugin-doctor/test_analyze.py:1721,1745,1769,1798` (all four line numbers exact). Shared-seam claim CONFIRMED at the exact cited lines. **Two conclusions do not survive execution:** the prose-rule claim is overstated — `agent-behavior-rules.md:342` names the *mirror* shape (G2) — and the "doctor check would be duplicate work" rejection is wrong for this plan's own signature: the cluster is provably blind to a documented misplaced router flag wherever that flag is root-declared (executed, G6), and mis-scopes the correct pre-verb form (executed, G7). |
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

Re-derived at the moment of stating. Contradictions found: **two**. (i) G2 — the "already names this
exact signature" inference; the citation itself is exact, the inference is not. (ii) G6 — the
"a plugin-doctor doc-check ALREADY EXISTS … D1(c)'s 'doctor check' candidate would be **duplicate
work** — REJECTED on that basis" conclusion; the cluster exists and is active, but is provably blind
to this plan's own signature wherever the router flag is root-declared. Both were confirmed by
execution, not by reading. Two further imprecisions, neither rising to a contradiction:

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
| **D2/D3 for a corpus-enabled run** — re-derive D1(a), complete the D1(b) denominator, implement a runtime actionable argparse error in `parse_args_with_toon_errors`'s fall-through | **Open** — and with a misleading near-miss, see G3 | Commit `4ac41326` (#1213) added `_augment_misplaced_router_flag` (`input_validation.py:982-1016`) into exactly that fall-through. It does **not** fire for the `ci` surface: executed at HEAD, `ci checks status --plan-id X` still yields a bare `unrecognized arguments: --plan-id X` / exit 2, because `_root_router_option_strings(parser)` returns `set()` — `ci`'s router flags are stripped by `extract_routing_args` and never declared on the parser. Re-executed during adversarial review, including the proposed remedy: declaring `--plan-id` / `--project-dir` on the parser object returned by `build_parser` makes the note fire and leaves `ci --plan-id X checks status` parsing cleanly. |
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
- **Whether the `ARGUMENT_NAMING_*` cluster reports the seventeen real router-flag-first invocations
  in the tree** (one `manage-architecture` line in `tools-script-executor/SKILL.md`, sixteen
  `tools-integration-ci:ci --project-dir …` lines across `automatic-review/SKILL.md`,
  `phase-6-finalize/standards/branch-cleanup.md`, `phase-6-finalize/workflow/create-pr.md`). The
  cluster's *rule-level* behaviour on both placements is now settled by execution against its own
  fixture helpers (see G6 and G7), but whether a given real notation is in the script index at all
  depends on the help-derived surface from `script-shared`'s `argparse_surface`, which needs
  `.plan/execute-script.py` — absent from this clone. The blindness in G6 is derivation-independent
  (the union can only widen the accept-set); the false positive in G7 is not.
- **The verification sub-agent's alternative denominators (324 / 119) — CLAIM RETRACTED.** An earlier
  draft of this document said no glob scope reproduces them. That is wrong. The scope is
  `marketplace/bundles/plan-marshall/skills/manage-*/scripts/*.py` — the `plan-marshall` bundle alone
  — which yields exactly **324** `.add_parser(` nodes and **119** `--plan-id` additions at
  `c586d2cb`. The 10 / 1 difference from the report's 334 / 120 is exactly
  `pm-dev-java:manage-maven-profiles` (4 parsers, 1 `--plan-id`) plus `pm-documents:manage-interface`
  (6 parsers, 0). Both figures are therefore exact and deterministic; `report-01.md`'s
  characterisation of the spread as "glob-scope noise" understates it — it is a bundle-scope
  difference with a named cause.
- **Whether the run's Step-6 sub-agent dispatch and Step-8 merge gate happened as the contract check
  claims.** Those are process assertions with no tree artifact; only their outcome (a clean,
  in-scope, merged diff) is observable.

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked.** Every gap (G1–G4), every clean-pass row, every published figure, and every "swept,
clean" claim. Specifically:

- **Re-derived, not repeated.** All four D1(b) figures were recomputed from scratch at `c586d2cb`
  by iterating `git ls-tree -r --name-only c586d2cb` over
  `marketplace/bundles/*/skills/manage-*/scripts/*.py` and counting per file: **334** `.add_parser(`
  across **22** scripts (per-script breakdown summed by hand to 334), **120** `--plan-id` additions
  across **15** scripts (summed to 120), `ci_base.py` = **45**. Every per-skill cell in the carve-out
  table reproduces. The 11 cluster figures sum to 113 and to 120 with the four carve-out additions.
  The landed diff was re-read (`git show --name-status -M c586d2cb` → exactly one R100 rename and one
  added 224-line file) and both cited SHAs were resolved (`ac06e4fc`, `c586d2cb` — both real, both
  ancestors of HEAD; `git diff --name-only ac06e4fc HEAD` touches only `doc/plans/**`, so no source
  drift separates the verification tree from HEAD).
- **Executed, not read.** (1) The live `ci` parser: `build_parser` + `add_pr_create_args` +
  `parse_args_with_toon_errors` with `argv = ['ci','checks','status','--plan-id','X']` →
  `unrecognized arguments: --plan-id X`, exit 2, `_root_router_option_strings(parser)` → `set()`.
  (2) G3's proposed remedy, applied in memory to the same parser object → the note fires and
  `ci --plan-id X checks status` still parses (`command='checks'`, `plan_id='X'`). (3) A parser
  replicating `architecture.py`'s real root (`:31-38`) → `PROG = 'architecture.py'`, and the shipped
  note's worked example is `` `architecture.py --project-dir VALUE <subcommand> ...` `` (G5).
  (4) The `ARGUMENT_NAMING_*` cluster, driven through its own fixture helpers
  (`_build_fixture_root` / `_write_fake_script(root_flags=…)` / `_write_skill_md` /
  `write_dispatching_executor` from `test_analyze.py`) under the repo venv's pytest:
  misplaced router flag → **zero findings** (G6); correct pre-verb placement → a **false**
  `ARGUMENT_NAMING_FLAG_UNKNOWN` on `--pattern` (G7); genuinely unknown flag → correctly reported.
- **Sweeps re-run broader.** The D1(a) corpus sweep was re-run without the extension filter
  (`git grep -l argparse_rejection` over the whole tree — every hit is skill prose, the mining tooling, the executor template, the recipe, a plan document, or a test module; none is a record corpus) and
  with a broader pattern over data extensions (`argparse_rejection|unrecognized arguments|exit_code:
  2` over `*.jsonl *.json *.log *.toon *.ndjson *.csv`) → one synthetic fixture. The
  `create_workflow_cli` sweep behind G1 was re-run tree-wide to confirm exactly three `manage-*`
  users and no fourth construction shape (`manage-terminal-title` was opened and is a pure library
  with no CLI).
- **Not re-checked.** The `.plan/`-resident corpus (unreachable, as before); the dispatched-leaf PATH
  truncation (claim #7, unreproducible here); whether the real tree's seventeen router-flag-first doc
  lines currently trip G7 (needs `.plan/execute-script.py`); the run's Step-6 / Step-8 process
  assertions; and `recipe-fix-argparse-rejection/SKILL.md`'s `:22-29` range, which was spot-read
  rather than line-counted.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| Verdict | `implemented-with-gaps` | **corrected → `partially-implemented`** | D2 and D3 carry no implementation and the plan's Goal is unmet. The halt is plan-sanctioned, but "implemented-with-gaps" reports delivery that did not occur. |
| G1 | D1(b) population blind to the `create_workflow_cli` shape | **upheld and strengthened** | Exactly 3 `manage-*` users, 10 verbs, 7 `--plan-id` — each verb and each declaration re-derived with line numbers. Newly added: three of those verbs (`worktree-sha`, `classify-outcome`, `query`) are genuinely **non**-plan-scoped and so are missing from the carve-out set itself, not merely from the denominator. Two corrections to the gap text: there is no "22-script list" in the report (only the count), and the "upper-bound proxy" hedge is *accurate* about parser-nodes-vs-leaf-verbs — the missing statement is about scan coverage, a separate thing, so the Fix now adds a sentence instead of replacing the hedge. |
| G2 | Prose signature #2 names the mirror shape, not this one | **upheld; Fix rewritten** | All four signatures read at `agent-behavior-rules.md:341-344`; #2 is scoped to `manage-architecture` / `manage-config` verb-scoped flags, #3 is the only ci-specific one (doubled prefix). Position-dependence re-proved by execution. The original Fix told an implementer to add a plugin-doctor positive control beside the existing four; that is not implementable today (see G6 — the flag rule is position-blind by construction), so the clause now says to pin it only after G6 lands. |
| G3 | #1213's note does not reach the `ci` surface | **upheld; Done-when corrected** | `_augment_misplaced_router_flag` at `:982-1016`, wired at `:1079`, introduced by `4ac41326` (#1213) — all confirmed. Executed: no note on the `ci` surface. The original **Done when** demanded a message naming `ci --plan-id X checks status`; the shipped template emits `{prog} --plan-id VALUE <subcommand> ...`, so the gap asked for something its own Fix does not produce. Done-when now names the observable the fix actually yields, and cross-references G5 for the example-text defect. |
| G4 | `report-01.md:3` still says `**PR:** _pending_` | **upheld, exact** | Line 3 verified verbatim; PR #1150 confirmed from the commit subject of `c586d2cb`. Severity `low` is correct — nothing acts on it. |
| G5 | *(new)* The shipped router-flag note names a raw script path and a `<subcommand>` placeholder | **added, medium** | Executed against a replica of `architecture.py`'s real root parser: `PROG = 'architecture.py'`. No marketplace script sets `prog=`. Fails `plan.md` § Verification's cold-read bar and names a call form CLAUDE.md § "Script Execution Convention" forbids. |
| G6 | *(new)* `ARGUMENT_NAMING_*` is blind to a documented misplaced router flag | **added, high** | `_entry_from_surface` (`:296-303`) sets each subcommand's accept-set to `root_flags \| child_flags`, justified at `:283-286` by the claim that "argparse honours a root-declared flag … on every subcommand" — which execution refutes (that exact invocation exits 2). Executed through the cluster's own helpers: a doc writing the failing form yields `analyze_argument_naming(...) == []`. This is the "guard that passes against the defect it names" shape, and it refutes `report-01.md` § D1(c)'s rejection of the doctor candidate as duplicate work. |
| G7 | *(new)* The same cluster mis-scopes the correct pre-verb form and can flag a valid document | **added, medium** | `_INVOCATION_RE` (`:131-136`) cannot capture a subcommand behind a leading flag, so `scan_flag` falls to the `<root>` branch (`:537-543`). Executed: the correct form produced `` Flag `--pattern` not declared on `…architecture <root>` ``. Kept at `medium` rather than `high` because live incidence in the real tree could not be confirmed from this clone. |
| Method claim | "`git grep -c argparse_rejection` over the test tree → six files" | **corrected → five** | Re-run: 5 files. |
| Method claim | "`_root_router_option_strings(parser)` → `[]`" | **corrected → `set()`** | The function is annotated `-> set[str]` and returned `set()` when executed. |
| Could-not-verify claim | "No glob scope reproduces the sub-agent's 324 / 119" | **refuted** | `marketplace/bundles/plan-marshall/skills/manage-*/scripts/*.py` gives exactly 324 / 119; the difference from 334 / 120 is `manage-maven-profiles` (4, 1) + `manage-interface` (6, 0). Retracted in place. |
| Clean-pass row D1(a) | STOP CONDITION legitimately met | **upheld** | Broader sweeps (see above) find no record corpus. `analyze-logs.py:9-12` / `:133-135` and `.gitignore:45` re-read at the run's tree. |
| Clean-pass rows D2 / D3 | Not executed, correctly gated | **upheld** | `git show --name-status -M c586d2cb` → two `doc/plans/**` paths, no `*.py`, no `test/**`. |
| Claim #1 / #4 / #5 / #6 / #8 / #9 citations | All exact | **upheld** | `ci_base.py:1072-1075` (`checks status`, no `--plan-id`); `constants.py:118-143` (14 members enumerated, no `escalation` — and, newly checked, `manage-findings.py:391` is the `--type required=True, choices=FINDING_TYPES` site the plan asserts); `ci_base.py:891-902` (`pr view` **does** declare `--pr-number`); `add_head_arg` registered on exactly **7** subparsers (`:902, 961, 973, 990, 1034, 1041, 1074`), all 7 also declaring `--pr-number`; `check_auth_cli` at `:750-769` with `127` / `124` from `run_cli:736-740`; `parse_args_with_toon_errors` at `input_validation.py:963-1023` with the fall-through `orig(message)` at `:1013`, and `github_ops.py:1817`, both exact at `c586d2cb^`. |

**Documents corrected.** `verification.md`: verdict changed to `partially-implemented` with its
reasoning; the "six files" count corrected to five and the sweep restated with the broader pattern;
`[]` corrected to `set()` in two places; the D1(c) row's Correct/Complete columns flipped to **No**
with the G6/G7 evidence; the contradiction count raised from one to two; the 324 / 119
"could-not-verify" bullet retracted and replaced with the reproducing scope; the
`ARGUMENT_NAMING_FLAG_UNKNOWN` could-not-verify bullet narrowed to what genuinely remains open.
`gaps.md`: open items 4 → 7; G1 strengthened with the carve-out-membership consequence and two
over-reads trimmed; G2's and G3's Fix/Done-when text corrected so each names a step an implementer
can carry out and an observable the fix actually produces; G5, G6, G7 added; a "Refuted during
adversarial review" section records that no gap was refuted and names the one refuted
`verification.md` claim.

**Residual doubt — what a third reviewer should look at first.** Whether G7 fires in the real tree.
The rule-level behaviour is proven, but the real accept-sets come from `argparse_surface`'s
help-derived surface, which needs `.plan/execute-script.py`. If `plan-marshall:tools-integration-ci:ci`
and `plan-marshall:manage-architecture:architecture` are in the doctor's script index, the seventeen
router-flag-first doc lines named above should be producing `ARGUMENT_NAMING_FLAG_UNKNOWN` findings
today and are not reported as doing so — which would mean either those notations are silently omitted
from the index (the fail-closed path, itself worth knowing) or the derived root-flag sets are wider
than the declared ones. Either answer changes how much of `report-01.md` § D1(c) survives. Second
priority: re-run the D1(b) figures once the `create_workflow_cli` shape is folded in, since G1's
+10 verbs / +7 declarations shift the "near-total convention" premise the whole diagnosis rests on.
