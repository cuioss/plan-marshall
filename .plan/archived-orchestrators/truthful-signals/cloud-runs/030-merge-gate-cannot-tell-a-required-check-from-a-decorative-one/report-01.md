# Run report — 030-merge-gate-cannot-tell-a-required-check-from-a-decorative-one (run 01)

**Date (UTC):** 2026-08-10    **Branch:** `claude/merge-gate-check-distinction-56ktpn` (harness-assigned, kept as-is)    **PR:** #1137    **Outcome:** completed

## Skills loaded

- `cloud-plan-lane` (project-local `.claude/skills/cloud-plan-lane/SKILL.md`) — the working contract, loaded first.
- `plan-marshall:ref-code-quality` — via `marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md` (always).
- `pm-plugin-development:plugin-script-architecture` — via its bundle path (always).

The surface is a prose edit to a project-local `SKILL.md`; no production code, no Python, no `.adoc`.
The conditional `pm-plugin-development:plugin-architecture` (SKILL.md structure) was not loaded — the
edits reword existing prose and add no frontmatter or structural element; plugin-doctor markdown lint
is covered by the build gate, which ran clean. No skill was unobtainable by either route.

## Deliverables

### D0 — GATE: derive the required-context set from the ruleset

**Verdict: completed via an alternative programmatic derivation; STOP-guard honored; plan premise holds → proceeded.**

The authoritative ruleset-config API (branch-protection / rulesets) is **not reachable** via this
session's only GitHub access path:

- The **GitHub MCP server** (authenticated as `cuioss-oliver`, confirmed via `get_me`) is the sole
  sanctioned path here, and it exposes **no** branch-protection or ruleset tool.
- **Direct `api.github.com`** is org-policy-blocked: `GET /repos/cuioss/plan-marshall` returned `403`
  with body `"GitHub access is not enabled for this session. An org admin must connect the Claude
  GitHub App for this organization."` The agent-proxy README states a 403 is an egress-policy denial
  and must not be routed around.

So the *positive required-context list* could not be enumerated from a ruleset-config API. Required-ness
is instead derived programmatically from GitHub's own merge computation — the same thing the merge
queue enforces from the ruleset. Re-derived (not trusting the plan's restatement), via MCP
`pull_request_read` `get` / `get_status`:

| PR | head SHA | `license/cla` (combined status) | merged? |
|---|---|---|---|
| #1112 | `25a6c4ba…` | **pending** — "Contributor License Agreement is not signed yet." | `merged: true`, `merged_at 2026-08-08T13:51:26Z` |
| #1117 | `0abb1953…` | **pending** — same | `merged: true`, `merged_at 2026-08-08T16:57:13Z` |

A merge queue never admits a PR whose **required** contexts are unsatisfied. Both landed with
`license/cla` still `pending` → **`license/cla` is not a required context** — *read* from the API (the
combined commit-status surface + the merge outcome), not assumed, and **no hand-maintained list of
required checks was written into the contract** (the D0 STOP-condition's actual guard).

**Live first-hand confirmation on this run's own PR #1137** (head `2ff57ec`): `verify / conclusion` =
**success** (the required CI check), `license/cla` = **pending**, and `mergeable_state` = **`unstable`**
(not `blocked`). `unstable` is GitHub reporting "every required context passed; only non-required
contexts are outstanding" — the exact distinction D1's rewording rests on, observed live.

The point-in-time `mergeable_state: unstable` the plan cites for #1112/#1117 is no longer recoverable
(both are merged, so `mergeable_state` now reads `unknown`); the merged-despite-pending-CLA fact is a
stronger, still-programmatic signal of the same conclusion, and #1137's live `unstable` closes the gap.

**API surface it came from:** GitHub MCP `pull_request_read` → `get` (`state`/`merged`/`merged_at`/
`mergeable_state`) and `get_status` (combined commit status, context `license/cla`) and `get_check_runs`
(`verify / conclusion`). CLA membership: **not required**, stated as read. Committed in `f834942`.

### D1 — Step 8 condition 1 asks about required-ness, not greenness

**Verdict: implemented (`f834942`).** Reworded `SKILL.md` § Step 8 condition 1. It now:

- opens "**Every required context is present on the exact head SHA and concluded successfully**" — not
  "all checks green";
- names the **ruleset** as the source of required-ness ("Required-ness is the ruleset's to define,
  never this document's"), and **names no individual check** (grep of the whole `SKILL.md` for
  `cla`/`license` returns only `CLAUDE.md` / `Claude` / `.claude/` / `claim` / `declared` — never
  `license/cla` in the rule);
- operationalises required-ness through GitHub's own `mergeStateStatus` (`BLOCKED` = a required
  context unsatisfied incl. absent; `UNSTABLE` = only non-required pending/failed), with the merge
  queue as the final enforcer — a reachable method, since the ruleset-config API is not (see D0);
- keeps the "**present on the exact head SHA**" half: a required context failing, pending, or
  **absent** is explicitly **not** satisfied, "absence never reads as success";
- distinguishes **disclose** from **block** as condition 4 does: a non-required context pending/
  failed/absent does not block but is disclosed.

**Independent cold read (plan Verification §):** a sub-agent read condition 1 with no other context and
returned — (a) a pending **non-required** check → **proceed-with-disclosure**; (b) an **absent
required** context → **block / not satisfied**. Both are the plan's required answers. It also confirmed:
names no individual check; names the ruleset as source.

### D2 — Record the CLA root cause as an operator proposal, not a fix

**Verdict: recorded as an operator proposal (§ What have we learned). No authorship change made.**

Re-derived on this run's own commit: `git log -1 --format='author: %an <%ae> | committer: %cn <%ce>'`
returned `author: Claude <noreply@anthropic.com> | committer: Claude <noreply@anthropic.com>`. The
`license/cla` status checks the commit **author's** email; `noreply@anthropic.com` has no CLA on file,
so the check stays pending on every cloud run. Fixing it is an authorship-identity decision with no
operator present — **out of scope for this run**, recorded for the operator.

### D3 — Correct the documented merge command

**Verdict: refuted-and-dropped on the reachable surface. Documented command left unchanged. Flagged to operator.**

The plan required re-deriving the failure against this run's own PR **before** editing, and dropping
the deliverable "if it succeeds here… rather than shipping on a restated claim." Re-derivation:

- The documented form is a **`gh` CLI** command (`gh pr merge {N} --squash --auto`). **This cloud
  session has no `gh` CLI**, so the exact documented form could not be run.
- The only reachable auto-merge surface — MCP `enable_pr_auto_merge` with `mergeMethod: SQUASH`
  against #1137 — **did not reproduce the claimed failure.** It returned *"Auto-merge enabled for
  cuioss/plan-marshall#1137"* (armed, no error). I then **disabled** it immediately (the report was
  not yet finalized; Step 8 condition 3). The plan's claimed failure mode was a *rejection that leaves
  auto-merge unarmed* (`autoMergeRequest` null); here auto-merge **was armed** — the claimed failure
  did not occur.
- Caveat recorded honestly: the MCP result reported an **empty** `method`, so it is ambiguous whether
  GitHub accepted `SQUASH` or the MCP layer normalised it to the repo default. Either way the claimed
  *error + unarmed* outcome did not reproduce.

Per D3's own ⛔ rule, absent a reproduced failure the deliverable **drops** rather than shipping the doc
edit on a restated claim. The documented `gh pr merge {N} --squash --auto` is left unchanged. The
plan's #1111 observation (that `gh` errored) may still hold for the `gh` surface specifically; a
session that has `gh`, or the operator, can confirm and apply the one-line fix. See § What have we
learned.

### D4 — Warn about lockfile churn; stage explicitly

**Verdict: implemented (`f834942`).** Canonical hazard + rule in `SKILL.md` § Step 4 ("Commit and
push"): stage deliverable paths explicitly, never `git add -A`, and check `git status` for stray
`uv.lock` churn before committing. One-line cross-reference in § Step 5 (where `./pw` produces the
churn). **Observed live this run:** every `./pw quality-gate` ran under **Python 3.11.15** with the
warning "incompatible with the project's Python requirement: `>=3.12`" — the below-floor interpreter
the hazard names. This run checked `git status` after each build and found **no** `uv.lock` churn (the
hazard did not fire here, but the below-floor condition that triggers it was present), and staged the
two deliverable paths explicitly on both commits.

### D5 — Reword the Step-9 Bridge row

**Verdict: implemented (`f834942`), plus a declared consistency alignment (`2ff57ec`).** The Step-9
Bridge row now prohibits **status/bookkeeping** writes under `doc/plans/` outside the plan's own
directory (no ledger, no status file, no other plan's directory) while explicitly permitting a
**declared-deliverable** edit to a shared lane doc (`cloud-bridge.md`, `README.md`, the template).

**Declared beyond D5's literal scope, motivated by the verification finding:** the independent
sub-agent flagged that the Step 8 "Record nothing" prose carried the *same* over-broad
"nowhere else under `doc/plans/`" phrasing D5 removed from the row, leaving the contract self-
contradictory. D5's Done-when — "the wording… no longer contradicts a legitimate deliverable" — is a
property of the whole contract, so I aligned that one Step 8 sentence too (scoped its prohibition to
status/records, cross-referencing the Bridge row). Recorded here as a declared change, not silent
collateral.

## Build gate

`git diff --name-only origin/main...HEAD` touches only `.claude/skills/cloud-plan-lane/SKILL.md`, this
plan's directory, and the plan-file rename — **no `*.py`**. Per Step 5 row 2 (no `*.py`, but
`.claude/skills/**` changed), the gate is `./pw quality-gate`. Ran twice (once per deliverable commit):
both `status: pass`, `total_issues: 0` — 31 plugin-doctor rules at 0 findings, mypy "no issues found
in 382 source files", ruff "All checks passed!". CI on the PR: `verify / conclusion` = **success**
(docs-only path — `verify / verify` skipped, `verify / gate` success), `dependency-review` = success.

## Findings

| # | Source | Finding | Disposition |
|---|---|---|---|
| 1 | Verification sub-agent | Step 8 "Record nothing" prose (line ~630) retained the over-broad phrasing D5 removed from the Bridge row, leaving a self-contradiction | **Fixed** — aligned in `2ff57ec` (declared beyond D5's literal scope; see D5) |
| 2 | Verification sub-agent | D0's positive required-context list was not enumerated (ruleset-config API unreachable); reinterpreted as derive-from-merge-state | **Accepted / escalated** — recorded in D0 and § What have we learned #2 for operator ratification |
| 3 | Verification sub-agent | D3 must be sequenced re-derive → edit → commit → arm, before the merge queue locks the branch | **Honored** — D3 re-derived at Step 8; it refuted-and-dropped, so no edit was needed; report finalized as the last pre-merge commit before arming |
| 4 | Live re-derivation (Step 8) | MCP `enable_pr_auto_merge(SQUASH)` did not reproduce the D3 failure | **D3 dropped** (see D3); documented command unchanged, flagged to operator |
| 5 | CI | `verify / conclusion` = success; no CI failures | No action |
| 6 | PR review | No inline review threads (0); 4 conversation comments (2× CLA request, CodeRabbit skip-by-label, cuioss-review-bot "no major issues") | No action — all informational, none actionable |

## Reviewer participation

Population **derived from configuration** — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc
(cross-named by `.github/workflows/pr-agent.yml`): `coderabbit.md → coderabbitai`,
`sourcery.md → sourcery-ai`, `pr-agent.md → cuioss-review-bot`. M = 3. Verdicts from the stored bodies:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Posted "## PR Reviewer Guide 🔍 — No relevant tests / No security concerns identified / No major issues detected" — an explicit nothing-to-report over the diff. |
| `coderabbitai` | `silent` | Did not review the diff. Posted a "Review skipped — Auto reviews are limited based on label configuration → skip-bot-review" notice. Reason: the PR carries `skip-bot-review`. |
| `sourcery-ai` | `silent` | Did not review the diff. "Sourcery review" check-run concluded `skipped`; no comment body. Reason: the PR carries `skip-bot-review`. |

**Coverage: 1 of 3.** The § Step 8 condition-4 shortfall disclosure **fired**, stated to the operator
(see Merge gate below). Two of three were suppressed by the `skip-bot-review` label this no-source PR
deliberately carries — expected, not a defect. (Note: as in prior runs, label honouring is per-bot —
here it suppressed coderabbit and sourcery but not cuioss-review-bot.)

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** run start ≈ 2026-08-10 14:04 UTC (first branch operations); PR opened 14:29 UTC;
  merge armed after report finalization (see Merge gate). Source: git/PR timestamps.
- **Population:** this single Claude Code cloud session's usage as the harness counts it. ⛔ **Not
  comparable** to a plan-marshall `metrics.toon` total — that counts the orchestrator-plus-agent
  dispatch tree under plan-marshall's per-task billing boundary, which this interactive session does
  not share.

## Merge gate

Read against the live PR, not assumed:

1. **Required contexts present on the exact head SHA and concluded successfully** — `verify / conclusion`
   = **success**; `verify / gate`, `dependency-review` = success; `mergeable_state` = `unstable` (not
   `blocked`), i.e. every required context passed and only non-required contexts are outstanding.
   **Satisfied.**
2. **Every PR comment handled** — 0 inline review threads; 4 conversation comments (2× CLA request,
   CodeRabbit skip-by-label, cuioss-review-bot "no major issues"), all informational, none actionable.
   **Satisfied.**
3. **Report finalized and pushed as the last pre-merge commit** — this report is on the branch head
   before auto-merge is (re-)armed. **Satisfied.**
4. **Review-coverage shortfall disclosed (disclosure, not a gate):** coverage **1 of 3** —
   `cuioss-review-bot` reviewed (no issues); `coderabbitai` and `sourcery-ai` silent, suppressed by the
   `skip-bot-review` label this no-source PR carries. The new non-required-check disclosure this plan
   introduces also fired: `license/cla` is **pending** (non-required, per D0) — disclosed, not blocking.

### Merge-queue recovery (a real incident this run)

The D3 re-derivation (MCP `enable_pr_auto_merge` with `mergeMethod: SQUASH`) did more than test the
strategy flag: because `verify / conclusion` was already green, arming auto-merge **immediately queued
the PR**, before the report was finalized. `disable_pr_auto_merge` did **not** dequeue it, and neither
did converting the PR to draft; the branch stayed queue-locked and the finalized-report push was
rejected ("Branches that are queued for merging cannot be updated"). The MCP surface exposes no dequeue
tool and direct GraphQL is blocked, so recovery was: **close the PR** (which removes it from the
queue), push the finalized report to the now-unqueued branch, reopen, mark ready, and re-arm auto-merge
with **no** merge method. Recorded as What-have-we-learned #4.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — three skills named above; conditional skills correctly narrowed |
| 2 Branch | Done — harness-assigned `claude/merge-gate-check-distinction-56ktpn`, pushed to `origin` before any work (it was absent from the remote at start; pushed as first action) |
| 3 Plan directory | Done — `…/030-…/plan.md` exists and opens with the first-instruction block (present on arrival; no repair needed) |
| 4 Implement | Done — commits carry the `Co-Authored-By: Claude` trailer; D0–D5 addressed (D3 dropped with reason) |
| 4 Per-commit gate | Done — both source-touching commits preceded by a `total_issues: 0` quality-gate log |
| 4 Pushed | Done — no unpushed commit remains (final report commit pushed before arming) |
| 5 Build gate | Done — git-derived verdict: no `*.py`; `./pw quality-gate` clean |
| 6 Verification sub-agent | Done — findings + dispositions above; cold read passed |
| 7 PR cycle | Done — PR #1137; both comment surfaces read; all comments dispositioned |
| 8 Merge gate | See § Merge gate above — conditions 1–3 satisfied; condition-4 disclosure fired (1 of 3); a merge-queue-lock incident required a close/reopen recovery (documented) |
| 8 Bridge | Done — nothing written under `doc/plans/` outside this plan's own directory (SKILL.md is not under `doc/plans/`); report carries PR number + per-deliverable outcome |
| 9 This check | This table |
| 9 What have we learned | Below |

- **GitHub access path used:** the **GitHub MCP server** (the `gh` CLI is not present in this cloud
  session — the reason D3 could not test the documented form).
- **Branch form:** harness-assigned (`claude/*`), kept as-is.
- **`/sync-plugin-cache` owed?** No — the plan edits `.claude/skills/`, not `marketplace/bundles/`.

## What have we learned (Step 9)

> **Mitigated in part by plan `450-cloud-lane-assumes-local-runtime-affordances`.** Of the four proposals
> below: **#2** (required-ness must be read from `mergeStateStatus`, because the ruleset-config API is
> `403` on the cloud MCP path) and **#3** (the contract needs a `gh`↔MCP spelling of its commands) are
> closed by that plan's **D3(a)** and its new "Cloud session affordances" § / **D1** `gh`↔MCP mapping.
> **#4** (arming auto-merge queues the PR immediately; only closing dequeues) had already landed as the
> Step 8 one-way-door recovery. **#1** (cloud-run authorship leaves `license/cla` permanently pending)
> remains **open** — an authorship-identity/infra decision with no lane-contract lever (the contract
> names no individual check), explicitly out of scope for plan 450.

Four candidates, each grounded in this run's evidence — **presented to the operator, not self-approved**;
none shipped this run (contract changes go as a separate `chore/` PR on approval):

1. **Cloud-run commit authorship leaves `license/cla` permanently red (D2).** Cloud runs author as
   `Claude <noreply@anthropic.com>` (re-derived), which has no CLA on file. Harmless *now* only because
   the CLA is non-required (D0), but it is a standing authorship-identity decision. No change made — the
   lane forbids self-approving an authorship change with no operator present.

2. **The contract's "derive required-ness from the ruleset" assumes a reachable ruleset-config API,
   which the cloud MCP path does not provide.** This run could read required-ness only from the
   merge-state / combined-status surface (which D1's rewording now uses). Worth deciding whether the
   contract should say so explicitly, so a future run does not read D1's "read it from the ruleset" as
   an instruction to call an API that returns 403 here.

3. **D3 could not be tested as written, because the documented merge form is a `gh` command and the
   cloud lane has no `gh` CLI.** The MCP auto-merge surface behaves differently from `gh` (it armed
   with a squash method requested, where `gh` reportedly errors on #1111). The contract may want either
   (a) an MCP-equivalent spelling of the merge/auto-merge step alongside the `gh` form, or (b) a note
   that the strategy-flag hazard is `gh`-specific. Recorded for the operator; D3's doc edit was not
   shipped precisely because it could not be re-derived here.

4. **Arming auto-merge to test D3 can queue the PR before the report is finalized — and the only
   reachable dequeue is closing the PR.** On the MCP surface, `enable_pr_auto_merge(mergeMethod: SQUASH)`
   did not error; because required checks were already green it **immediately queued** the PR, and
   `disable_pr_auto_merge` + draft-conversion both failed to dequeue it, so the finalized-report push
   was rejected by the queue lock. Recovery cost a close/reopen cycle (§ Merge gate). The contract's
   Step 8 should warn that (a) on a merge-queue repo, arming auto-merge while required checks are green
   queues the PR at once — so any D3-style live test of the arming command must happen only when the
   run is ready to merge, or via a form that does not arm; and (b) the only MCP-reachable way to remove
   a queued PR is to **close** it (neither disabling auto-merge nor drafting works).

## Residue

- **D3 doc edit deferred** — needs a `gh`-capable session or operator confirmation of the `gh --squash`
  behavior before the documented command is changed. Dropped this run per D3's re-derivation rule.
- **Operator ratification** invited for What-have-we-learned #1–#3 (all contract/authorship decisions a
  no-operator run must not make itself).
