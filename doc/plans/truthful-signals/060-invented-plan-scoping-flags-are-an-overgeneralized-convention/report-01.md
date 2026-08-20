# Run report — 060-invented-plan-scoping-flags-are-an-overgeneralized-convention (run 01)

**Date (UTC):** 2026-08-10    **Branch:** `claude/invented-plan-scoping-flags-arkvxj` (harness-assigned, kept as-is)    **PR:** _pending_    **Outcome:** completed — D1 gate executed and **halted at its STOP CONDITION** (script-failure corpus unmineable from this clone); D2/D3 correctly **not** executed, per the plan's own instruction. Mutates nothing beyond the plan directory + this report.

## Skills loaded

- `plan-marshall:ref-code-quality` — read via bundle path (always-required).
- `pm-plugin-development:plugin-script-architecture` — read via bundle path (always-required).
- Conditional skills loaded as the surface is confirmed (recorded below).

## Deliverables

D1 is a GATE that mutates nothing; D2/D3 are conditional on D1's outcome.

### D1(a) — Quantify the corpus → STOP CONDITION met (corpus unmineable)

The `argparse_rejection` exit-2 script-failure corpus lives under `.plan/` (git-ignored) and/or in
another repository. The mining tool `plan-retrospective/scripts/analyze-logs.py` reads its records
from `<plan_dir>/logs/` (live mode) or `<archived_plan_path>/logs/` (archived mode) — both resolve
under `.plan/plans/` / `.plan/archived-plans/`, which a fresh cloud clone does not have
(`analyze-logs.py:10-12`, `:133-135`). A tree-wide search for `argparse_rejection` across **tracked**
files returns only concept references in skill docs, the mining tooling, the executor template, the
recipe, and tests with **synthetic** fixtures — **no corpus of actual failure records** is committed.

⇒ The corpus **cannot be mined** and claim-table row #2 (invented `--plan-id` = "2 of 4 clusters")
**cannot be re-derived**. Per the plan's ⛔ STOP CONDITION ("If the corpus cannot be mined … halt and
report that. Do not proceed to D2 on the strength of the handful of instances"), this run **halts at
the D1 gate**. It does not implement D2 or D3. The plan itself anticipated this: "scoping a structural
change from anecdote is what this deliverable exists to prevent."

### D1(b) — Carve-out enumeration (non-plan-scoped verbs + published denominator)

**Population scanned (the denominator).** Reproducible greps over the argparse surface:

- `manage-*/scripts/*.py`: **334** `.add_parser(` nodes across **22** scripts (includes intermediate
  noun parsers and, for `manage-config`, per-key subparsers — an upper-bound proxy for leaf verbs, not
  an exact verb count).
- `tools-integration-ci` (`ci_base.py`): **45** `.add_parser(` nodes.
- `--plan-id` argument additions (`add_plan_id_arg(` / `add_argument('--plan-id'` / `add_body_consumer_args(`):
  **120** occurrences across **15** `manage-*` scripts.

**Where `--plan-id` concentrates (the near-total convention, quantified).** The 120 additions cluster
in the **plan-lifecycle** skills — `manage-status` (26), `manage-tasks` (19), `manage-findings` (14),
`manage-solution-outline` (10), `manage-metrics` (9), `manage-execution-manifest` (8),
`manage-references` (8), `manage-files` (7), `manage-plan-documents` (6), `manage-logging` (3),
`manage-ci-artifacts` (3). In this cluster `--plan-id` is effectively universal — which is exactly the
muscle-memory the plan says a caller over-generalises.

**The carve-out (non-plan-scoped), and it is scope-principled.** A substantial set of skills carry an
argparse surface with **no** (or nearly no) `--plan-id`, because they operate on a *different scope*:

| Scope | Skills / surface |
|---|---|
| repo / PR / issue / branch | the entire `ci` surface (`pr`, `checks`, `issue`, `branch`, `repo`) except its body-consumer verbs, which take `--plan-id` only to bind a body-store slot |
| project config | `manage-config` (85 parsers, 1 `--plan-id`), `manage-run-config` (28 parsers, 0) |
| global knowledge | `manage-lessons` (17 parsers, 4 `--plan-id`; lessons key on `--lesson-id`), `manage-adr` (7, 0) |
| module | `manage-architecture` (35 parsers, 1 `--plan-id`; uses `--module` / `--audit-plan-id`) |
| global infra | `manage-providers`/`credentials` (11, 0), `manage-personas` (1, 0), `manage-build-server` (9+1, 0), `manage-interface` (6, 0), `manage-maven-profiles` (4) |

**Verdict — refines claim #3, does not flatly confirm it.** The carve-out is **not tiny**, but it is
**stable and coherent**: it maps cleanly onto scope (repo/PR, project-config, global-knowledge, module,
build-infra). The plan's premise holds *within the plan-execution `manage-*` cluster*, where `--plan-id`
is near-universal; the over-generalisation is from that cluster onto a **scope-sibling** — `ci checks
status`, which is repo/PR-scoped — whose scoping property is **invisible at the call site**. That
invisibility, not a large/arbitrary exception list, is the actual root: the remedy that "makes the
plan-scoping property visible at the call site" (a D1(c) candidate) targets it directly. `manage-change-ledger`
(named by the plan as a second rejection site) has no `.add_parser(` and no `--plan-id` addition — it
uses a different dispatch shape and needs per-verb inspection in a corpus-enabled run; recorded, not
resolved here.

### D1(c) — Remedy: recommendation only (NOT implemented — gate halted)

Because the gate halted, no remedy is implemented. The in-repo verification (Findings below) already
narrows the candidate space decisively, and is recorded as guidance for a future corpus-enabled run:

- **A plugin-doctor doc-check ALREADY EXISTS** — the `ARGUMENT_NAMING_*` cluster
  (`_analyze_argument_naming.py`), "unconditionally active across all marketplace markdown", already
  flags a documented flag a script's argparse does not declare (`ARGUMENT_NAMING_FLAG_UNKNOWN`), an
  unknown documented subcommand (`ARGUMENT_NAMING_SUBCOMMAND_UNKNOWN`), and canonical-forms drift, and
  explicitly handles the `tools-integration-ci:ci` shape (`_analyze_argument_naming.py:3-70`). D1(c)'s
  "doctor check" candidate would be **duplicate work** — REJECTED on that basis.
- **The prose prevention rule ALREADY EXISTS — but this claim was WRONG about which signature covers
  this shape** (corrected by plan `500`, gap `060/G2`). Signature #2, "Top-level
  `--plan-id`/`--project-dir` where the flag is verb-scoped" (`agent-behavior-rules.md`), names the
  OPPOSITE shape: a flag written ahead of the verb that belongs after it. The CI shape is a
  router-scoped flag written AFTER the verb that belongs before it, and the two prescribe opposite
  moves. Plan `500` added it as signature #4, with both signatures cross-referencing each other so a
  reader cannot collapse them. Its own "Why" concedes the failure "is
  structural" and recurs despite the rule (`:337`). This is the plan's thesis confirmed: a loaded,
  correct prose guard that still fires — a documentation-layer vacuous guard. Adding emphasis is the
  plan's explicitly REJECTED option, and nothing here argues this instance differs.
- **The one genuine, non-duplicate gap is a RUNTIME actionable error.** The existing guards cover
  *documented* invocations at *edit* time (doctor) and *after-the-fact* remediation (recipe). Neither
  turns a caller's runtime `ci checks status --plan-id X` bare exit-2 into a self-correcting message.
  The shared seam that would host it exists — `input_validation.parse_args_with_toon_errors`
  (`input_validation.py:963-1023`), whose fall-through branch (`:1012-1013`) is exactly where an
  "unrecognized arguments" error currently becomes a bare exit-2. **Recommended candidate for a
  corpus-enabled run**, subject to D1(a)'s distribution actually justifying the change.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is empty at halt — the run mutates no Python
(D1 is a gate). No local build footprint; build skipped. Recorded per Step 5.

## Findings

### Claim-label verification (this run's primary job)

Every claim treated as `HYPOTHESIS` until verified against in-repo artifacts. Verdicts:

| # | Claim | Verdict | Confirm/refute artifact |
|---|---|---|---|
| 1 | `ci checks status` is repo/PR-scoped, does not declare `--plan-id` | **CONFIRMED** | `ci_base.py:1017-1021` — `checks status` declares `--pr-number`, `--head`, `--error-style`; not `--plan-id`. PR-scoped. |
| 2 | Invented `--plan-id` = 2 of 4 script-failure clusters in one run | **UNVERIFIABLE (corpus absent)** | Corpus is `.plan/`-resident / external; `analyze-logs.py:10-12,133-135`. Count cannot be re-derived → STOP CONDITION. |
| 3 | Nearly every `manage-*` verb is plan-scoped and takes `--plan-id` | **CONFIRMED-WITH-REFINEMENT** | See D1(b). True *within the plan-lifecycle cluster* (120 `--plan-id` additions concentrated there); the broader surface has a coherent, scope-principled carve-out (config / lessons / architecture / providers / ci). Root cause is the scoping property being invisible at the call site, not a large exception list. |
| 4 | `FINDING_TYPES` has no `escalation` member | **CONFIRMED (absence real)** | `constants.py:118-143` — 14 types; no `escalation`. Whether the absence is a *defect* (should `escalation` be a member) needs the external corpus → unverifiable. |
| 5 | `ci pr view --help` advertises `--pr-number` while the verb does not declare it | **REFUTED** | `ci_base.py:842-848` — `pr view` **declares** `--pr-number`; `add_head_arg` docstring (`:1361-1398`) asserts the invariant that all seven `--head` verbs also declare `--pr-number`; help text is accurate. Plan flagged this as "unsettled / possible observer error" — confirmed observer error. |
| 6 | `check_auth_cli` reports "Not authenticated" for every non-zero exit incl. a missing binary | **CONFIRMED** | `ci_base.py:750-769` — `returncode != 0 → login_message`, so `127` (missing binary; `run_cli:736-738`) and `124` (timeout; `:739-740`) both surface as "Not authenticated". The epic's archetype inside an error message. Affects both `gh` and `glab` (shared helper). |
| 7 | Dispatched leaves receive a truncated PATH, making `gh` unreachable | **UNVERIFIABLE HERE** | Cannot reproduce a dispatched leaf in this cloud session; explicitly out of scope beyond recording. Recorded: fixing the diagnostic (#6) alone would NOT fix the underlying PATH problem — dispatched CI calls would still fail. |
| 8 | `recipe-fix-argparse-rejection` exists and is remediation, not prevention | **CONFIRMED** | `recipe-fix-argparse-rejection/SKILL.md:9-13,22-29` — self-describes as the post-rejection remediation procedure; explicitly complements (does not duplicate) the prevention rule. No overlap with a *prevention* remedy. |
| 9 | No shared argparse error-emission seam exists | **REFUTED** | `input_validation.py:963-1023` (`parse_args_with_toon_errors`) is the shared seam, used by the provider ops (`github_ops.py:1817`); `resolve_project_dir` adds `emit_*_error` helpers. The natural home for an actionable rejection message **exists** — do not build one. |

**Exit-2 mechanism (code-confirmed, not empirically reproduced).** `ci checks status --plan-id X` →
`extract_routing_args` only consumes `--plan-id` **before** the first subcommand token
(`ci_base.py:570-676`), so a post-subcommand `--plan-id` passes through → `checks status` does not
declare it → the root parser raises "unrecognized arguments: --plan-id" → `parse_args_with_toon_errors`
falls through to argparse's default (`input_validation.py:1012-1013`) → **bare exit 2**. Note the
position-dependence: `ci --plan-id X checks status` **works** (router consumes it). Empirical
reproduction is deferred to a corpus-enabled implementation run (D3(a) requires it before the fix);
the executor needed to run it is absent from this clone.

### Verification sub-agent (Step 6)

An independent read-only sub-agent verified the run against the plan (not against the diff's intent).
It re-derived each item from source and returned **all six HOLD, no blocking gaps**:

| Item | Verdict | Note |
|---|---|---|
| STOP-CONDITION trigger legitimate (corpus genuinely unmineable) | HOLDS | `analyze-logs.py` → `base_path('plans', …)` under `.plan/` (git-ignored); only synthetic `argparse_rejection` fixtures are tracked. |
| Claim-label verdicts accurate (5 spot-checks) | HOLDS | All confirmed/refuted verdicts match source; exit-2 position-dependence code-accurate. |
| D1(c) "already exists" claims accurate | HOLDS | `ARGUMENT_NAMING_*` doctor + prose signature #2 + recipe-as-remediation all verified. |
| Carve-out denominator honestly derived | HOLDS | Independent re-run: 324 `add_parser` / 119 `--plan-id` (vs report's 334 / 120) — within noise; caveated as a proxy population, `ci`=45 exact on both. |
| No undeclared collateral change | HOLDS | Diff is only the two `doc/plans/…/060-…/` files. |
| Halt is the correct reading of the plan | HOLDS | D2/D3 gated on the corpus; corpus-independent D1(b) was executed, not skipped. |

**Disposition:** accepted; no fix required. **Denominator reconciliation (accepted correction):** the
`add_parser` / `--plan-id` counts are grep-derived **proxy populations**, not exact verb counts; an
independent re-run over a slightly different glob scope yields 324 / 119 rather than 334 / 120. Both are
consistent with the qualitative verdict (near-total within the plan-lifecycle cluster; coherent
scope-principled carve-out); the one exact figure (`ci` = 45 parser nodes) matches on both runs. The ±10
spread is glob-scope noise, not a substantive disagreement.

## Reviewer participation

This PR's diff is confined to `doc/plans/**` (a plan-directory move + this report) — no `*.py`, no
`.claude/skills/**`, no `marketplace/bundles/**`. Per Step 7 it therefore carries `skip-bot-review`:
there is no reviewable code footprint. Expected reviewer population (derived from the
`automatic-review/standards/{bot_kind}.md` registry) is intentionally not engaged; coverage is N/A for
a no-code-footprint PR. Recorded, not silently omitted.

## Cost

- **Tokens:** not available to the agent in this session (the Claude Code cloud harness does not expose
  a per-run token count to the model). Stated plainly rather than estimated.
- **Wall-clock:** single interactive cloud session; exact start/end not machine-readable to the agent.
- **Population:** this one Claude Code cloud session's usage. ⛔ NOT comparable to a plan-marshall
  `metrics.toon` total (that counts an orchestrator-plus-agent dispatch tree under plan-marshall's own
  per-task billing boundary, which this single session does not share). No comparable figure is
  presented.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — `ref-code-quality`, `plugin-script-architecture` (bundle-path reads). Conditional Python/test/bundle skills not loaded: the run halts at a read-only gate and mutates no code, so their load would be pure context cost. |
| 2 Branch | Done — harness-assigned `claude/invented-plan-scoping-flags-arkvxj` kept as-is; pushed to `origin` before any work. |
| 3 Plan directory | Done — `doc/plans/truthful-signals/060-…/plan.md`; first-instruction block present (verified, not repaired). |
| 4 Implement | Gate only — no code mutated; D1 diagnosis recorded. Commits carry the `Co-Authored-By: Claude` trailer. |
| 4 Per-commit gate | N/A — no commit touches `*.py`. |
| 4 Pushed | Done — no unpushed commit at each checkpoint. |
| 5 Build gate | Done — git-derived Python-change verdict empty; build skipped (no buildable footprint). |
| 6 Verification sub-agent | See below — dispatched before PR. |
| 7 PR cycle | PR opened on the published branch with `skip-bot-review` (no code footprint). |
| 8 Merge gate | Conditions 1–3 to be met; auto-merge armed after the report lands as the last pre-merge commit. |
| 8 Bridge | No write outside this plan's own directory. |
| 9 This check | Recorded here. |
| GitHub access path | GitHub MCP server (cloud path). |
| Branch form | Harness-assigned `claude/*` (not run-created). |
| `/sync-plugin-cache` | Not owed — machine-local build step; a cloud run neither performs nor records it. |

## What have we learned (Step 9)

**No contract change proposed.** This run exercised the cloud-plan-lane end to end as a **gate-only
run that correctly halted at a plan-defined STOP CONDITION with zero code mutation**, and every step
was producible as written:

- The build gate's `*.py`-only predicate handled a docs-only gate cleanly (skipped, recorded).
- Step 6's independent verification worked as intended and caught a real (if minor) over-count in the
  D1(b) denominators, which was reconciled in-report — the sub-agent gate did its job.
- The outcome vocabulary (`completed | partial | blocked`) has no dedicated slot for "gate ran to its
  designed terminal STOP CONDITION with nothing to implement", but the contract already permits a
  **qualified, per-deliverable** outcome in the report ("the outcome per deliverable — including a run
  that ended blocked or partial, and why"), so `completed` + an explicit qualifier expresses it without
  overstatement. No gap that this run's evidence shows the contract failing to handle.

One session-level (not contract-level) note, recorded for honesty: a background enumeration sub-agent
dispatched for D1(b) became unreachable during a burst of session interrupts, and its result was lost;
D1(b) was re-derived inline. That is a harness/session artifact, not a cloud-plan-lane step defect, so
it yields no contract proposal — but it argues for running a gate's load-bearing sub-agent **synchronously**
when its result is a hard dependency of the next step (as Step 6 was here).

## Residue

- **D2/D3 remain for a corpus-enabled run.** They were correctly deferred, not skipped — the plan's
  STOP CONDITION forbids them without the corpus. A future run with `.plan/` failure logs (or the
  originating repository's archive) should: re-derive the D1(a) distribution; complete the D1(b)
  carve-out denominator (see D1(b) above); and — only if the distribution justifies it — implement the
  single non-duplicate candidate (a **runtime** actionable argparse error in
  `parse_args_with_toon_errors`'s fall-through), NOT a new doctor check (already covered by
  `ARGUMENT_NAMING_*`) and NOT more prose (the rejected option).
- **Directly-verified, corpus-independent defect worth a separate decision:** `check_auth_cli`
  (`ci_base.py:750-769`) reports "Not authenticated" for a missing binary (`127`) and a timeout
  (`124`). This is a real misattributed diagnostic (the epic's archetype), fixable without widening any
  argument surface. The plan cabins this instance to *recording* (its PATH-truncation root cause is
  out of scope), so it is **recorded here** rather than fixed in this gate run.
- **Two refuted claims** (#5 `pr view`/`--pr-number`; #9 "no shared seam") vindicate the plan's
  HYPOTHESIS-labelling discipline: a naive run would have built a shared seam that exists and "fixed" a
  help text that is already accurate — duplicate/wrong work against existing surfaces.
