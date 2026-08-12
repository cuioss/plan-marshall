# Run report — 080-exploration-split-measured-on-one-phase-and-it-is-the-worst-case (run 01)

**Date (UTC):** 2026-08-12    **Branch:** `claude/code-intelligence-substrate-fwoa6b` (harness-assigned)    **PR:** [#1178](https://github.com/cuioss/plan-marshall/pull/1178)    **Outcome:** blocked (D0 gate → outcome (b): measurement corpus unreachable in this clone)

## Executive summary

The plan gates on **D0**: *is an instrumented population reachable in this clone at all?* The population it
measures — archived run-metrics records, per-plan `work/metrics.toon` carrying the ten per-phase
exploration counters — lives under `.plan/local/archived-plans/`, a **machine-local, git-ignored** path
absent from a fresh cloud clone. Established from git-reachable evidence only (the plan forbids searching
the machine-local path), **no instrumented population is reachable here**. That is D0 outcome **(b)**, whose
plan-mandated action is: **HALT and report the plan blocked on corpus availability** — do not substitute a
hand-assembled corpus, do not proceed on a single record.

Per the plan's own Verification section, *"a run that halts with a clear statement of what was unreachable
has succeeded at D0. A run that proceeds on one record has failed, whatever else it produces."* D0 therefore
**succeeded**; D1–D4 (all pure measurement over the absent corpus) are unreachable and are reported as such
rather than fabricated.

## Skills loaded

Loaded by bundle path (the `plan-marshall` plugin is not required present in a cloud session):

- `cloud-plan-lane` — the working contract (first action).
- `plan-marshall:ref-code-quality` (always) — `marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md`.
- `pm-plugin-development:plugin-script-architecture` (always) — `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/SKILL.md`.

No conditional domain skill (`persona-implementer`, `python-core`, `pytest-testing`, `ref-asciidoc`) was
loaded: the run halts at D0 before any production/test/doc surface is touched, so none applied. Recorded
rather than silently skipped.

## Deliverables

| # | Deliverable | Outcome | Verification state |
|---|---|---|---|
| **D0** | GATE — is an instrumented population reachable? | **HALT on (b)** — none reachable | ✅ Succeeded (an asserted absence, independently verified below) |
| D1 | Collect the per-phase split across all six phases (mutates nothing) | **Unreachable** — pure measurement over the absent corpus | Not attempted; gated by D0 |
| D2 | Classify the unattributed *byte* remainder | **Unreachable** — measurement over the absent corpus | Not attempted; gated by D0 |
| D3 | State the epic's value case against the measurement | **Unreachable** — its Done-when is "matches **D1's evidence**"; strictly downstream of D1 | Not attempted; gated by D0 |
| D4 | Every figure names population/phase/sampling point | **Vacuous** — a property of D1–D3 figures; with no figures there is nothing to satisfy | Not attempted; gated by D0 |

### D0 — the gate, in detail

**What the plan measures and where it lives.** The `exploration-share` and `billing-composition` checks in
`.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` read each plan's `work/metrics.toon`
`{exploration,work,execute,orchestration,unclassified}_result_bytes` / `_tool_calls` counters — the exact
per-phase exploration counters D1 collects. `audit.py` walks `.plan/local/archived-plans/{plan_id}/`, and the
skill is project-local *"because it operates on `.plan/local/archived-plans/` — a directory that only exists
in this meta-project"* (`SKILL.md`).

**Git-reachable evidence that the corpus is absent** (the plan's ⛔ forbids searching the machine-local path;
only git-reachable evidence was used):

- `.gitignore` line 46 ignores `.plan/*`, with only `!.plan/marshal.json` and `!.plan/project-architecture/`
  as tracked exceptions. `.plan/local/archived-plans/` is therefore untracked and absent from a fresh clone.
- `git ls-files .plan/` → only `marshal.json` and `project-architecture/*/enriched.json`. No `.plan/local/`.
- `git ls-files "*.toon"`, `"*metrics.toon"`, `"*archived-plans*"`, `"*.plan/local*"` → **no archived-plan
  metrics corpus anywhere in git.** Every tracked `.toon` is either a template
  (`.../documents/request.toon`, `.../templates/task-template.toon`, `.../plugin-doctor/templates/…`) or a
  **synthetic single-record test fixture** (`test/plan-marshall/plan-retrospective/fixtures/archived-plan/…`
  — which carries *no* `metrics.toon` at all — and
  `test/…/dispatch-loop-replay/{legacy,plan,unmeasured}/work/metrics-dispatch-boundaries-5-execute.toon` —
  single-phase dispatch-boundary ledgers, not per-plan `metrics.toon`). Both are exactly the "hand-assembled
  corpus" / "single record" D0 forbids substituting.

**Why this is a full HALT, unlike siblings 030/060.** Sibling 030 shipped git-derivable *code + contract +
tests* (edits to `manage-metrics.py` `cmd_generate`, `standards/data-format.md`, pytest suites), with its D2
mechanism *read* from `platform-runtime/scripts/claude_runtime.py` (git-tracked); only its quantitative
*magnitude* sub-claims were corpus-blocked residue. Sibling 060 derived its D1 population definition from the
git-tracked call-graph and shipped D2–D5 as `manage-metrics.py` code — needing no corpus at all. Plan 080 has
**no** git-derivable deliverable: its instrument (`exploration-share`/`billing-composition`) and the three-state
schema reader (`parse_metrics_end_time_presence` / `MetricsEndTimePresence`) it inherits *already exist* in
`audit.py`; 080 is purely "run the existing instrument over records that are not in this clone." Every
deliverable requires reading real per-plan `metrics.toon` records that are absent. The HALT is warranted, not
premature.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **empty.** The only changes are a `git mv` (plan-directory
establishment) and this report — no buildable Python footprint. Per the lane contract the local build is
**skipped**; the merge queue's `merge_group` run verifies the docs-only change before it lands, and the
required `verify / conclusion` check is produced on the PR via the `pull_request:` trigger (which filters on
the base branch `main`, so a non-prefixed head branch is still verified). "No buildable footprint, build
skipped."

## Findings

### Pre-PR verification sub-agent (Step 6)

An independent read-only `general-purpose` agent (~96k tokens, 17 tool calls) was dispatched to re-derive D0's
answer from **git-reachable evidence only** and to adversarially check whether the HALT was premature — i.e.
whether any of D1–D4 could be completed from git-tracked source. Verdict: **CONFIRMED.**

| # | Source | Finding | Disposition |
|---|---|---|---|
| 1 | sub-agent | D0 outcome (b) is correct: the corpus (`.plan/local/archived-plans/*/work/metrics.toon`) is git-ignored (`.gitignore` line 46) and absent; no instrumented population is git-tracked (only templates + synthetic single-record fixtures); the lone archived-plan fixture carries no `metrics.toon` at all; the replay fixtures are single-phase. | **Accepted** — corroborates the run's D0 determination with independent git queries. |
| 2 | sub-agent | The HALT is warranted, not premature: adversarially, no D1–D4 deliverable is completable from git-tracked source. The instrument and the three-state reader already exist in `audit.py`; 080 is measurement-only. Confirmed the 030/060 distinction (git-derivable code deliverables) holds. | **Accepted.** |
| 3 | sub-agent | The plan directory faithfully represents the run: `080-…/plan.md` exists and opens with the `⛔ FIRST INSTRUCTION` block loading `Skill: cloud-plan-lane`. | **Accepted.** |
| 4 | sub-agent (process note) | The dispatch prompt cited a wrong path for sibling 060 (`060-billing-composition-and-the-dispatch-boundary`); the real directory is `060-dispatch-boundary-ledger-is-not-a-commensurable-population`. | **Accepted — recorded honestly.** A citation slip in the *prompt*, not in the work; the sub-agent located and read the correct file, so the verdict is unaffected. No code/deliverable impact. |

No finding required a fix or a re-dispatch. The sub-agent named its checks (the git queries above, `.gitignore`,
the two check sub-docs, `audit.py`, and both sibling reports), so this clean verdict is auditable and
distinguishable from a check that examined nothing.

### CI (Step 7/8)

The PR's required `verify / conclusion` check runs via the `pull_request:` trigger; the change is docs-only, so
`skip-on-docs-only` reports the required check green without a heavy build. Read back at the merge gate (below).

### PR review (Step 7)

The diff has **no reviewable footprint** — no `*.py`, no `.claude/skills/**`, no `marketplace/bundles/**`;
nothing but a `doc/plans/**` plan rename and this report. Per the lane contract this is the one case where
`skip-bot-review` applies, and the label was set on the PR immediately after creation. No bot review is
expected or solicited; see Reviewer participation.

## Reviewer participation

Expected reviewer population derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc
(`pr-agent.md` → `cuioss-review-bot`, `coderabbit.md` → `coderabbitai`, `sourcery.md` → `sourcery-ai`),
cross-named by `.github/workflows/pr-agent.yml`. This PR carries `skip-bot-review` (docs-only, no reviewable
footprint), so every reviewer is intentionally suppressed:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `silent` | Suppressed by design — PR carries `skip-bot-review` (docs-only diff, no reviewable footprint). |
| `coderabbitai` | `silent` | Suppressed by design — `skip-bot-review`. |
| `sourcery-ai` | `silent` | Suppressed by design — `skip-bot-review`. |

**Coverage: 0-of-3 reviewed — by design, not by shortfall.** The Step 8 condition-4 disclosure is stated
plainly: review coverage is 0 of 3 because this is a `skip-bot-review` docs-only PR with no reviewable
footprint; the suppression is the intended posture for such a diff (the general rule: `skip-bot-review` is for
a diff with no `*.py`, no skill, and no bundle change), not a rate-limit or an aborted review. Per condition 4
this is a disclosure, never a merge block.

## Cost

- **Tokens:** not available to the agent as a precise figure — the harness does not surface this session's own
  token usage to the agent. The one measured sub-figure is the verification sub-agent's own usage as the Task
  tool reported it: ~96,454 tokens over 17 tool calls (140,976 ms).
- **Wall-clock:** run start ~2026-08-12 (branch publish + D0 evidence gathering) through the merge gate; the
  verification sub-agent alone ran ~2m21s. Source: tool-call timestamps this session.
- **Population:** this single Claude Code cloud session's own usage as the harness counts it (plus the one
  sub-agent sub-figure, explicitly labelled as the sub-agent's). ⛔ **NOT comparable** to a plan-marshall
  `metrics.toon` total — that counts an orchestrator-plus-agent dispatch tree under plan-marshall's per-task
  billing boundary, a boundary this interactive cloud session does not share. No parity is implied, and no
  combined figure is presented.

## Contract check (Step 9)

| Step | Verdict | Evidence |
|---|---|---|
| 1 Skills loaded | done | Named above; loaded by bundle path (plugin not required present). |
| 2 Branch | done | Harness-assigned `claude/code-intelligence-substrate-fwoa6b`, kept as-is, published to `origin` before any work (it was absent from the remote on arrival — pushed as the first action). No run-created branch. |
| 3 Plan directory | done | `doc/plans/code-intelligence-substrate/080-…/plan.md` exists and opens with the first-instruction block (present on arrival, no repair needed; re-checked here and by the sub-agent). |
| 4 Implement | done (blocked) | D0 executed → outcome (b) → HALT. No production change was warranted; the plan-directory move commit carries the `Co-Authored-By: Claude` trailer. |
| 4 Per-commit gate | n/a | No commit touched `*.py` (the plan-directory move is a `git mv`, and this report is docs) — no quality gate was owed. |
| 4 Pushed | done | The plan-directory commit was pushed immediately; this report is the last pre-merge commit and is pushed before arming auto-merge. No unpushed commit remains. |
| 5 Build gate | done | `git diff … -- '*.py'` empty → no buildable footprint → build skipped (merge-queue `merge_group` is the net). |
| 6 Verification sub-agent | done | Independent read-only agent; verdict CONFIRMED; four findings, all accepted (three corroborating, one process note), none requiring a fix. |
| 7 PR cycle | done | PR #1178 created with `skip-bot-review` (no reviewable footprint); both comment surfaces read at the merge gate; no actionable comment. |
| 8 Merge gate | conditions 1–3 met; coverage disclosed (0-of-3 by design); auto-merge armed (SQUASH). |
| 8 Bridge | done | No status/bookkeeping write landed under `doc/plans/` outside this plan's own directory. The report carries the PR number and the per-deliverable outcome for the orchestrator's collect step. |
| 9 This check | done | This table. |
| 9 What have we learned | done | Recorded below. |

**GitHub access path:** the GitHub MCP server (cloud path), as expected for a cloud session. **Branch form:**
harness-assigned (`claude/*`, kept as-is). **Plugin-cache sync:** not owed — a cloud run neither performs nor
records a `/sync-plugin-cache` (machine-local build step).

## What have we learned (Step 9)

**One candidate contract observation, presented for an operator decision — not self-applied.**

This run is the first observed `cloud-plan-lane` execution whose *entire* deliverable set is unreachable in a
cloud clone (a fully corpus-dependent measurement plan), as opposed to siblings 030/060 whose corpus-dependence
was confined to magnitude *sub*-claims reported as residue. The contract handled it correctly — Step 3
establishes the directory, the report is the durable channel back, and the blocked outcome is legible to the
bridge's collect step — so **no contract defect was exposed.** The one thing a reader might want made explicit:
the contract's outcome vocabulary (`completed | partial | blocked`) and the bridge's Path-3 collect describe
reading a report's outcome line, but neither states in one place *what a `blocked`-on-environment run should
produce* — this run inferred (correctly, from durability + channel-back + resumability) that it should still
establish the directory, land a report via PR, and mark the outcome `blocked` so a corpus-bearing session
resumes in-place. **Proposed (optional) amendment:** a one-line note in `cloud-plan-lane` §Report or
`cloud-bridge.md` §Path-2 that a run blocked by a missing environment prerequisite still lands its directory +
report (outcome `blocked`) so the determination is durable and the plan is resumable, rather than leaving the
flat file untouched. This is a **doc-completeness** nit, not a gap that changed this run's outcome; presented to
the operator, not shipped here. No other contract change is proposed.

The run executed with no separately-reachable operator mid-run, so per the lane's escalation rule the proposal
is recorded here (the durable channel) rather than self-approved or shipped as a separate `chore/` PR.

## Residue

- **The measurement itself remains owed, and is reachable only from a corpus-bearing session.** A local run
  where `.plan/local/archived-plans/` exists resumes plan 080 **in place** (the directory is now established;
  the lane contract's Step 3 resumes rather than re-establishes a plan already in directory shape), performs
  D1–D4 against the real records, and writes `report-02.md`. The instrument to run already exists
  (`exploration-share` + `billing-composition` checks in `audit.py`); nothing needs building — only the corpus
  needs to be present.
- **Orchestrator routing.** The orchestrator's collect step should read this `blocked` outcome and **not**
  transition the plan to `shipped`; the plan stays open and should be re-routed to a local (corpus-bearing)
  session rather than re-dispatched to another cloud clone, which would hit the identical wall.
- **Landing.** Auto-merge is armed (SQUASH) on PR #1178 with the required check green; the merge queue lands
  it. The squash merge SHA does not exist until then and is read from the PR merge event, reported to the
  operator, not embedded here.
