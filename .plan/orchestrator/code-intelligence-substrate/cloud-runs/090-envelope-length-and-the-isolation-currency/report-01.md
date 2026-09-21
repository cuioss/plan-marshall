# Run report — 090-envelope-length-and-the-isolation-currency (run 01)

**Date (UTC):** 2026-08-12 (source: harness `currentDate` context; exact wall-clock not available to the agent)
**Branch:** `claude/envelope-length-isolation-currency-kmo78n` (harness-assigned cloud branch, kept as-is per lane contract)
**PR:** [#1185](https://github.com/cuioss/plan-marshall/pull/1185)
**Outcome:** completed (D2 shipped; D1/D3/D4 blocked on corpus availability — landing delegated to the merge queue)

## Skills loaded

- `cloud-plan-lane` — the working contract (loaded first, before reading the plan).
- `plan-marshall:ref-code-quality` — always-load (read from bundle path).
- `pm-documents:ref-asciidoc` — `.adoc` documentation surface (read from bundle path).

`pm-plugin-development:plugin-script-architecture` (an always-load) was **not** loaded: this run edits
no scripts and no bundle skills — the only change is a concept `.adoc` and its diagram SVG, both under
`doc/`. Recorded here rather than silently skipped.

## D0 gate — is an instrumented population reachable in this clone?

**Resolved: no instrumented population is reachable.** The measurements the plan rests on come from
archived run-metrics records under `.plan/`, which is machine-local, git-ignored state (`CLAUDE.md`
§ "Standalone Plan Lane": `.plan/` "lives only on the machine that created it, so a cloud session at
claude.ai/code clones the repository and has none of it"). This is a fresh cloud clone, so the corpus
is absent. Established from that structural fact — **not** by searching for the records, per D0's
explicit ⛔.

**Consequence per D0:** D1, D3, and D4's selection are **blocked on corpus availability**. **D2 is
shippable** — it is a documentation correction whose evidence is the argument itself, not the corpus.
No population was fabricated.

## Deliverables

| Deliverable | State | Notes |
|---|---|---|
| D0 — gate | **done** | Resolved: no population reachable (above). |
| D1 — publish the two factors | **blocked** | Requires the instrumented population (absent). Cannot derive resident-context / turns per phase without the corpus; no figure fabricated. |
| D2 — restate `token-management.adoc` § 6 in the measured currency | **done** | Commit `4b392bf`. See below; verified by cold read. |
| D3 — settle the creation/read inversion | **blocked** | D0 halts D3: the inversion's phase is identified from the population, which is absent. Cannot name the phase, so cannot read the mechanism for _that_ phase. No mechanism inferred from a ratio (there is no ratio to read). |
| D4 — one envelope-length lever, chosen by D1 | **blocked** | D0 halts D4's selection: the split is chosen by D1, which is blocked. |

### D2 — detail

Target: `doc/concepts/token-management.adoc` § 6 "Per-dispatch context isolation", whose defense of
isolation rested on _"independent — and never additive"_ — the orchestrator-context currency the plan
identifies as the mismatch. The same figures and the same currency error were baked into the section's
diagram, `doc/resources/diagrams/context-isolation.svg` (its right-column caption
`~5 K + 3 × ~300 ≈ 6 K` presented orchestrator-context size _as the cost_).

Done (commit `4b392bf`):
1. § 6's argument is restated in billing-weight / turns-resident currency: a byte is billed at creation
   and re-billed on every turn it stays resident (`cost = creation + read × turns_remaining`), so its
   price is dominated by turns-resident, not size. Isolation does **not** make a byte cheaper and **is**
   additive to the bill; what it bounds is **residency** — how many turns a byte is re-read for. That is
   the reason it is the biggest lever, stated in the measured currency.
2. The isolation recommendation is **unchanged**: still "the biggest single token-management lever".
3. § 6's unverifiable numeric figures (`10-15 K`, `30-50 K`, `~6 K`, `~200-500 tokens`) removed rather
   than restated (D1 blocked → cannot re-derive; "delete rather than correct" for a moving system), in
   prose **and** in the diagram; the diagram's `≈ 6 K` orchestrator-cost caption recast into
   bounded-residency framing.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is **empty** — the change is `doc/**` only
(`token-management.adoc`, `context-isolation.svg`, the plan-directory rename, this report). Per the
lane's `*.py`-only gate: **no buildable footprint, build skipped.** The merge queue's `merge_group`
run / the `verify` workflow's docs-only skip path verifies the change (see CI below).

## Findings

| # | Source | Description | Disposition |
|---|---|---|---|
| 1 | Verification sub-agent (Step 6) | Cold read of revised § 6: argument is in billing-weight / turns-resident currency (prose + diagram consistent); isolation clearly recommended, not questioned; no surviving numeric figures in prose or SVG. | **No gap** — D2 verified. |
| 2 | Verification sub-agent (Step 6) | D0/D1/D3/D4 correctly recorded (gate resolved, blocks recorded with reasons, no fabrication); diff scope clean (4 files, all `doc/**`, incl. a pure `R100` rename). | **No gap.** |
| 3 | Verification sub-agent (Step 6, Part C) | Duplicate figure `~10-15 K tokens of variant context` survives in § "Where Plan Marshall deliberately spends more" (Q-Gate bullet). Confirmed **not** made false by D2 (removed for unverifiability, not disproven) and in a different, internally-consistent section. | **Deferred / out of D2's § 6 scope** — flagged in Residue; touching it would be undeclared collateral scope creep. |
| 4 | CI (`verify / conclusion`) | Required check concluded `success` on head `073fe7a`; `verify / verify` skipped (docs-only path); `review / review`, `verify / gate`, `dependency-review` all `success`. | **No gap** — green. |
| 5 | PR review — `cuioss-review-bot` | "PR Reviewer Guide — No relevant tests / No security concerns identified / No major issues detected." | **No action** — explicit nothing-to-report over the diff. |
| 6 | PR review — `coderabbitai` | "Review skipped — only excluded labels are configured: skip-bot-review." | **No action** — bot honored `skip-bot-review`; no findings. |
| 7 | PR review — `sourcery-ai` | "you have reached your weekly rate limit of 500000 diff characters." | **No action** — rate-limit refusal; no findings. Weekly quota; re-request would not help this window. |

## Reviewer participation

Expected reviewer population derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc
(`coderabbit.md` → `coderabbitai`; `sourcery.md` → `sourcery-ai`; `pr-agent.md` → `cuioss-review-bot`);
the same set is named by `.github/workflows/pr-agent.yml`. Verdicts derived from the stored comment /
review bodies, not from check states:

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Issue-comment body "PR Reviewer Guide 🔍 … No major issues detected" — an explicit nothing-to-report over the diff. (Did not honor `skip-bot-review`; reviewed and found nothing.) |
| `coderabbitai` | `silent` | Posted a skip notice ("Review skipped — only excluded labels are configured: skip-bot-review"), no review of the diff. Reason: honored `skip-bot-review`. |
| `sourcery-ai` | `rate-limited` | Review body "you have reached your weekly rate limit of 500000 diff characters" — a quota refusal in place of a review. |

**Coverage: 1 of 3.** Step 8 shortfall disclosure fired: "Review coverage 1 of 3 — `cuioss-review-bot`
reviewed (no issues); `coderabbitai` silent (honored `skip-bot-review`); `sourcery-ai` rate-limited
(weekly diff-character quota)." This is a disclosure, not a merge block — the diff is a doc-only
correction, its cold-read gate (Step 6) passed, and `cuioss-review-bot` reviewed it clean.

## Cost

- **Tokens:** not available to the agent in this session. (One verification sub-agent reported
  `subagent_tokens: 70038`, `tool_uses: 14`, `duration_ms: 213457` for its own dispatch only — not a
  run total.)
- **Wall-clock:** run performed in one interactive cloud session on 2026-08-12 (UTC); PR opened
  17:24 UTC.
- **Population:** this single Claude Code cloud session's usage. **Not comparable** to a plan-marshall
  `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree under plan-marshall's
  own per-task billing boundary that a single interactive cloud session does not share.

## Contract check (Step 9)

| Step | Verdict | Evidence |
|---|---|---|
| 1 Skills loaded | done | Named above; `plugin-script-architecture` intentionally not loaded (no scripts touched), recorded. |
| 2 Branch | done | `claude/envelope-length-isolation-currency-kmo78n` on `origin` (harness-assigned cloud branch, kept as-is). |
| 3 Plan directory | done | `doc/plans/code-intelligence-substrate/090-envelope-length-and-the-isolation-currency/plan.md` exists; opens with the first-instruction block (verified present at Step 3). |
| 4 Implement | done | Commits carry the `Co-Authored-By: Claude` trailer; D2 addressed; D1/D3/D4 recorded blocked. |
| 4 Per-commit gate | n/a | No commit touched `*.py`, so no quality gate was owed. |
| 4 Pushed | done | No unpushed commit remains after the final report push. |
| 5 Build gate | done | No Python in the diff → build skipped; merge-queue/verify docs-only path verifies. |
| 6 Verification sub-agent | done | Dispatched (general-purpose, read-only); clean verdict, no gaps; findings recorded above. |
| 7 PR cycle | done | PR #1185 open; all comments dispositioned (no actionable findings). |
| 8 Merge gate | done | Conditions 1–3 met (required `verify / conclusion` green, `mergeable_state: clean`, comments handled, report finalized and pushed); coverage shortfall disclosed (condition 4); auto-merge armed and landing delegated to the merge queue (cloud session cannot block-wait to self-confirm). |
| 8 Bridge | done | No status/bookkeeping write outside this plan's own directory; report carries PR number and per-deliverable outcome. |
| 9 This check | done | This table. |
| 9 What have we learned | done | See below. |

**GitHub access path used:** the GitHub MCP server (cloud path). **Branch form:** harness-assigned
`claude/*` (kept). **`/sync-plugin-cache`:** not owed — a cloud run never performs or owes it
(machine-local build step); and this run touched no `marketplace/bundles/` anyway.

## What have we learned (Step 9)

**One candidate contract change, presented for operator approval (not self-shipped, not in this PR).**

Evidence from this run: the contract's Step 8 / `gh`↔MCP mapping tells a run to read `mergeStateStatus`
with uppercase values `BLOCKED` / `UNSTABLE` / `clean` from `pull_request_read method=get`. The actual
MCP `get` on this server build returns the REST field **`mergeable_state`** with **lowercase** values
(observed: `"mergeable_state":"clean"`) — there is no `mergeStateStatus` key in the payload. The value
semantics align (`clean`/`unstable`/`blocked`), but a run following the contract literally would look
for a key and case that are not present. Proposed edit: note in Step 8 that the MCP `get` returns
`mergeable_state` (lowercase `clean`/`unstable`/`blocked`/`behind`/`dirty`), so runs read the right
field name and case. Minor; would ship as its own `chore(cloud-plan-lane)` PR on approval.

No other contract change is proposed: the run exercised branch/PR/review/merge-gate mechanics as
written and they held.

## Residue

- **D1, D3, D4 remain blocked on corpus availability.** Pick them up in a run that has a reachable
  instrumented population — a local run on a machine holding the archived `.plan/` metrics, or after
  the WS-04 emission plan publishes the two factors read-only.
- **Pre-existing duplicate figure:** `doc/concepts/token-management.adoc` § "Where Plan Marshall
  deliberately spends more" (Q-Gate bullet) restates `~10-15 K tokens of variant context` — the same
  skill-body figure removed from § 6, but in a different, still-internally-consistent section that this
  edit does not make false. Left in place (out of D2's § 6 scope); a corpus-enabled run may re-derive
  or remove it alongside D1.
