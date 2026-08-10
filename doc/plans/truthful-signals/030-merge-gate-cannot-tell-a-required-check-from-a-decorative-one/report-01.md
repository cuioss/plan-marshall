# Run report — 030-merge-gate-cannot-tell-a-required-check-from-a-decorative-one (run 01)

**Date (UTC):** 2026-08-10    **Branch:** `claude/merge-gate-check-distinction-56ktpn` (harness-assigned, kept as-is)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `cloud-plan-lane` (project-local `.claude/skills/cloud-plan-lane/SKILL.md`) — the working contract, loaded first.
- `plan-marshall:ref-code-quality` — via `marketplace/bundles/plan-marshall/skills/ref-code-quality/SKILL.md` (always).
- `pm-plugin-development:plugin-script-architecture` — via its bundle path (always).

The surface is a prose edit to a project-local `SKILL.md`; no production code, no Python, no `.adoc`.
The conditional `pm-plugin-development:plugin-architecture` (SKILL.md structure) was not loaded — the
edits reword existing prose and add no frontmatter or structural element; plugin-doctor lint is
covered by the Step 5 build gate. No skill was unobtainable by either route.

## Deliverables

### D0 — GATE: derive the required-context set from the ruleset

**Verdict: completed, with a disclosed API-reachability limitation. The plan's central premise holds → the plan proceeds.**

The authoritative ruleset-config API (branch-protection / rulesets) is **not reachable** via this
session's only GitHub access path:

- The **GitHub MCP server** (authenticated as `cuioss-oliver`, confirmed via `get_me`) is the sole
  sanctioned path here, and it exposes **no** branch-protection or ruleset tool.
- **Direct `api.github.com`** is org-policy-blocked: `GET /repos/cuioss/plan-marshall` returned `403`
  with body `"GitHub access is not enabled for this session. An org admin must connect the Claude
  GitHub App for this organization."` The agent-proxy README is explicit that a 403 is an egress-policy
  denial and must not be routed around.

So the *positive required-context list* could not be enumerated from a ruleset-config API. But
required-ness **is** derivable programmatically from GitHub's own merge computation, which is exactly
what the merge queue enforces from the ruleset. Re-derived (not trusting the plan's restatement), via
MCP `pull_request_read` methods `get` and `get_status`:

| PR | head SHA | `license/cla` (combined status) | merged? |
|---|---|---|---|
| #1112 | `25a6c4ba…` | **pending** — "Contributor License Agreement is not signed yet." | `merged: true`, `merged_at 2026-08-08T13:51:26Z` |
| #1117 | `0abb1953…` | **pending** — same | `merged: true`, `merged_at 2026-08-08T16:57:13Z` |

A merge queue never admits a PR whose **required** contexts are unsatisfied. Both PRs landed with
`license/cla` still `pending` → **`license/cla` is not a required context**. This is *read* from the
API (the combined commit-status surface + the merge outcome), not assumed, and **no hand-maintained
list of required checks was written into the contract** (the D0 STOP-condition's actual guard).

The point-in-time `mergeable_state: unstable` the plan cites is no longer recoverable — both PRs are
merged, so `mergeable_state` now reads `unknown` — but the merged-despite-pending-CLA fact is a
stronger, still-programmatic signal of the same conclusion. Live first-hand confirmation is captured
on this run's own PR at Step 8 (a cloud PR carries the same red `license/cla`, and the queue admits it).

**API surface it came from:** GitHub MCP `pull_request_read` → `get` (`state`/`merged`/`merged_at`)
and `get_status` (combined commit status, context `license/cla`). CLA membership: **not required**,
stated as read.

### D1 — Step 8 condition 1 asks about required-ness, not greenness

**Verdict: implemented.** Reworded `SKILL.md` § Step 8 condition 1. It now:

- opens "**Every required context is present on the exact head SHA and concluded successfully**" —
  not "all checks green";
- names the **ruleset** as the source of required-ness ("Required-ness is the ruleset's to define,
  never this document's"), and **names no individual check** (grep of the whole SKILL.md for
  `cla`/`license` returns only `CLAUDE.md` / `Claude` / `.claude/` / `claim` / `declared` — never
  `license/cla` in the rule);
- operationalises required-ness through GitHub's own `mergeStateStatus` computation (`BLOCKED` = a
  required context unsatisfied incl. absent; `UNSTABLE` = only non-required pending/failed) and notes
  the merge queue is the final enforcer — a reachable method, since the ruleset-config API is not
  (see D0);
- keeps the "**present on the exact head SHA**" half: a required context that is failing, pending, or
  **absent** is explicitly **not** satisfied, "absence never reads as success";
- distinguishes **disclose** from **block** as condition 4 does: a non-required context that is
  pending/failed/absent does not block but is disclosed to the operator.

### D2 — Record the CLA root cause as an operator proposal, not a fix

**Verdict: recorded as an operator proposal (see § What have we learned). No authorship change made.**

Re-derived on this run's own commit: `git log -1 --format='author: %an <%ae> | committer: %cn <%ce>'`
returned `author: Claude <noreply@anthropic.com> | committer: Claude <noreply@anthropic.com>`. The
`license/cla` status checks the commit **author's** email; `noreply@anthropic.com` has no CLA on file,
so the check stays pending on every cloud run. The repository convention is a `Co-Authored-By:` trailer
(which the lane already mandates) atop a human author identity. Fixing this is an authorship-identity
decision with no operator present — **out of scope for this run**, recorded for the operator.

### D3 — Correct the documented merge command

**Verdict: pending — re-derived live against this run's own PR at Step 8 before any edit.** The plan
requires running the documented `--squash --auto` form against this PR and recording what it returns;
if it succeeds here, D3 is refuted and drops. Result recorded at Step 8.

### D4 — Warn about lockfile churn; stage explicitly

**Verdict: implemented.** Canonical hazard + rule added to `SKILL.md` § Step 4 ("Commit and push"):
stage deliverable paths explicitly, never `git add -A`, and check `git status` for stray `uv.lock`
churn before committing. A one-line cross-reference added to § Step 5 (where `./pw` produces the churn).

### D5 — Reword the Step-9 Bridge row

**Verdict: implemented.** The row now prohibits **status/bookkeeping** writes under `doc/plans/`
outside the plan's own directory (no ledger, no status file, no other plan's directory) while
explicitly permitting a **declared-deliverable** edit to a shared lane doc (`cloud-bridge.md`,
`README.md`, the template). Wording now matches intent and no longer forbids a legitimate deliverable.

## Build gate

`git diff --name-only origin/main...HEAD` touches `.claude/skills/cloud-plan-lane/SKILL.md` and this
plan directory — **no `*.py`**. Per Step 5 row 2 (no `*.py`, but `.claude/skills/**` changed), the
gate is `./pw quality-gate`. Result recorded below once run.

## Findings

_Verification sub-agent (Step 6), CI, and PR review findings recorded here as they arrive._

## Reviewer participation

_The diff changes no source (a prose contract + this report), so the PR carries `skip-bot-review`.
Population and per-reviewer verdicts recorded at Step 7/8 from the stored comment bodies._

## Cost

- **Tokens:** not available to the agent in this session.
- **Wall-clock:** run start ≈ report-creation time; end recorded at close.
- **Population:** this single Claude Code cloud session's usage. **Not comparable** to a plan-marshall
  `metrics.toon` total (that counts the orchestrator-plus-agent dispatch tree under plan-marshall's
  per-task billing boundary, which this interactive session does not share).

## Contract check (Step 9)

_Filled at Step 9 as the last pre-merge commit._

## What have we learned (Step 9)

Two candidates, both grounded in this run's evidence — presented to the operator, not self-approved:

1. **D2 — cloud-run commit authorship leaves `license/cla` permanently red.** Cloud runs author
   commits as `Claude <noreply@anthropic.com>` (re-derived above), which has no CLA on file, so
   `license/cla` is pending on every cloud PR. This is harmless *now* only because the CLA is
   non-required (D0); it is a standing authorship-identity decision for the operator. **No change made
   this run** — the lane forbids self-approving an authorship change with no operator present.

2. **D0-as-written assumes a reachable ruleset-config API, which the cloud MCP path does not provide.**
   This run could not read branch-protection/rulesets from any available surface (MCP exposes none;
   direct `api.github.com` is org-blocked). The workable programmatic derivation in the cloud lane is
   the **merge-state / combined-status** surface, which is what D1's reworded condition now uses. Worth
   considering whether the contract should say so explicitly. Recorded for the operator.

## Residue

- D3 outcome (merge-command re-derivation) is filled at Step 8.
- The plan edits `.claude/skills/`, **not** `marketplace/bundles/`, so **no `/sync-plugin-cache` is
  owed** (that surface is bundle-only).
