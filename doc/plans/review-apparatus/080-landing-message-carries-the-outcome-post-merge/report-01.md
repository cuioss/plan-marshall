# Run report — 080-landing-message-carries-the-outcome-post-merge (run 01)

**Date (UTC):** 2026-08-12    **Branch:** `claude/landing-message-outcome-j5up5s` (harness-assigned)    **PR:** (recorded to operator at finalize)    **Outcome:** completed — plan **REFUTED** at the verify-first gate

## Summary

This plan is **REFUTED**. Its explicit verify-first gate — *"re-read `lessons-capture.md` at HEAD before scoping — If a landing has since moved the emission, this plan is REFUTED — close it rather than re-implementing it. Report the refutation as the result"* — fires. The landing-message emission is already **post-merge** at HEAD, and every concrete defect the plan enumerates has been resolved by intervening work, most of it by **sibling plans 040 and 050 in this same `review-apparatus` epic**. The deliverable of this run is this report plus the establishment of the plan directory (per the plan's own Verification: *"If the stop condition fired, that report is the deliverable"* — the analogous rule holds for a refutation).

An independent verification sub-agent, dispatched adversarially to *find a live defect that would refute the refutation*, read every referenced file at HEAD and returned **REFUTATION CONFIRMED** on all six checks, finding no live defect.

## Skills loaded

- `cloud-plan-lane` (`.claude/skills/cloud-plan-lane/SKILL.md`) — the governing contract, loaded first.
- No domain/implementation skills were loaded: the run resolved at the verify-first gate **before scoping**, so no source was changed. The contract's Step 1 conditional skills are keyed on "what the plan touches"; a refutation touches no code, so the code-quality / python / bundle skills do not apply. Recorded here per the "a skipped step is reported as skipped" rule.

## Deliverables

The plan's six deliverables (D0–D5) are **not implemented**, by design — the verify-first gate short-circuits the whole implementation flow. Their target state is nonetheless verified as already-present at HEAD:

| Plan deliverable | Target | State at HEAD |
|---|---|---|
| D1 — emission site (pre- vs post-merge); never-merges case | landing emitted post-merge; no false landing when finalize halts | **Already post-merge.** `lessons-capture` `order: 991` runs after merge step `branch-cleanup` `order: 70`. Doc is architecturally built around post-merge (`post_run_review: true`, `mutates_source: false`, discover-after-merge routing). **Never-merges is already correct:** a finalize that halts pre-merge never reaches order 991, so it emits **no** landing rather than a false one. |
| D3 — one landing per landing; no batch self-description | singular, unconditional | **Already the documented invariant.** "Exactly one `kind: landing` message per orchestrated finalize run, emitted unconditionally" (`lessons-capture.md:82`; `inbox-envelope.md:92`). `finalize-step-preference-emitter.md:219-221` explicitly emits **no** second landing. Grep for `batch`/`same batch`/`two lesson` in `lessons-capture.md` → no matches; the batch self-description is gone. |
| D4 — staleable artifact regenerated or declares its as-of point | HEAD stamp + append-only derivation | **Already done** for `review-retrospective.md`: `head_dependent: true`; `--head-at-completion {sha}` on every terminal record; metrics derived from the append-only `pr-comment` store; `unmeasurable`/`indeterminate` grading prevents absence-inference. Landed by plans 040 (#1165) and 050 (#1170, #1175). |
| D0 — create-pr PR-body member | Non-goals kept; truncation visible | **Already done.** "Explicit non-goals" is a first-class required part of the composed Intent (`create-pr.md:148-149`); truncation is at a word boundary with a visible marker inside the budget (`create-pr.md:180-182`), deterministically owned by the `pr_intent_section render` script. |
| D2 — landing message carries the outcome | outcome-bearing claim | Root cause cured by post-merge emission (see § D2 assessment). Content-field mandate not present, and its OUT-OF-SCOPE constraint forbade authoritative fields — assessed by both this run and the sub-agent as **not a live defect**. |
| D5 — tests | — | N/A (no implementation). |

## D0 — derived population of staleable finalize artifacts

**Derivation method:** enumerate the composed phase-6-finalize step roster by `order:` frontmatter across `phase-6-finalize/workflow/*.md`, `phase-6-finalize/standards/*.md`, and the project-local `.claude/skills/finalize-step-*`; identify every step that (a) is generated at a fixed step, (b) asserts a claim about PR/review/merge state, and (c) persists an artifact. For each, record whether its claim can go stale between generation and merge. Ordering semantics verified: `SKILL.md:149` and the ascending-order validator (`SKILL.md:219`) confirm higher `order` = later runtime; the post-run-review band (`order > 70`, post-merge) is defined at `SKILL.md:214-217`.

Composed finalize order (relevant subset):

| order | step | asserts PR/review/merge state? | staleable? |
|---|---|---|---|
| 20 | `create-pr` (PR body) | yes — Intent/Non-goals scope statement | **was** — now visible truncation + kept Non-goals |
| 22 | `ci-verify` | CI state, transient | no persisted stale artifact |
| 40 | `sonar-roundtrip` | Sonar findings, not PR/review | no |
| 62 | `adr-propose` | ADR, not PR/review | no |
| **70** | **`branch-cleanup` (MERGE GATE)** | — | — (the merge boundary) |
| 990 | `finalize-step-review-retrospective` (`review-retrospective.md`) | yes — reviewer comparison | **was** — now HEAD-stamped + append-only-derived |
| 991 | `lessons-capture` (`kind: landing` message) | yes — landing narrative | **was** — now post-merge-emitted |
| 992 | `finalize-step-preference-emitter` | preferences, post-merge; emits no landing | no |
| 998 | `record-metrics` | metrics, post-merge | no |
| 1000 | `archive-plan` | terminal | no |

**Population = exactly the three floor members the plan named** (landing message, `review-retrospective.md`, PR body). **Zero additional** staleable PR/review/merge-state artifacts were found beyond the three. The D0 split-and-stop condition ("more than about two additional") does **not** fire. And all three members are already resolved at HEAD — the reason the plan is refuted rather than split.

## D2 assessment (why the residual is not a live defect)

The plan's D2 wanted the landing message *content* to carry merge state / SHA / cost. At HEAD the landing payload body is authored **free-form** at emission time (`lessons-capture.md:95-107`; `inbox-envelope.md:88-92` — the `landing` payload contract is "the plan's landing narrative: what shipped, the PR reference, and any residue", not a mandated field set). Two facts make the missing SHA/cost field **not** a blocking live defect (concurred by the independent sub-agent):

1. **The root-cause defect is cured by the ordering.** The plan's observation 1 — *"the message ASSERTS a landing in its prose while the PR is open"* — is a direct consequence of pre-merge emission. Post-merge emission (order 991 > 70) means the message is authored after the merge; it can no longer assert a landing while the PR is open.
2. **The plan's own OUT-OF-SCOPE forbade the enrichment that would matter here.** "⛔⛔ Making the channel TRUSTED … D2 must not add any field that reads as authoritative", and "Making the `landing` payload shape contractual unless D2 forces it" is out of scope. A free-form, post-merge landing narrative labelled as the plan's own report is exactly what that constraint asks for.

## Consumer check (the asserted absence)

The plan flagged as its higher-risk HYPOTHESIS: "No consumer relies on the landing message arriving pre-merge." Verified TRUE and moot: the orchestrator drain (`plan-orchestrator/workflow/cleanup.md:111`) **never derives quiescence from a merge landing** and drains at epic-archive time, well after any plan's merge. The system already operates with post-merge landing emission; no pre-merge dependency exists.

## Findings

Recorded per instance (source · finding · disposition):

| Source | Finding | Disposition |
|---|---|---|
| Verify-first read (`lessons-capture.md` at HEAD) | The plan's foundational OBSERVED claim "`lessons-capture` precedes `branch-cleanup`" is **false at HEAD**: `lessons-capture` `order: 991` runs after `branch-cleanup` `order: 70`. The emission is post-merge. | Refutation trigger — the gate fires. |
| D0 population sweep | All three named floor members already resolved; no additional staleable member found; split condition does not fire. | Confirms refutation, not split. |
| Git provenance | `source-edit-pushability.md` (the post-merge "post-run band" ordering discipline) landed by plan 050 (#1175); `review-retrospective` fixes landed by plans 040 (#1165) and 050 (#1170). Sibling plans immediately preceding 080 in this epic. | Substantiates "a landing has since moved the emission." |
| Independent verification sub-agent (adversarial) | REFUTATION CONFIRMED on all six checks (Q1 emission post-merge; Q2 singular landing/no batch text; Q3 review-retrospective all four sub-points; Q4 create-pr Non-goals + visible truncation; Q5 no live defect; Q6 foundational claim false). Strengthened the never-merges and single-landing corroborations. | Accepted. |

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → no Python changes (the diff is the plan-directory move + this report, all under `doc/plans/**`). **Build skipped: no buildable footprint.**

## Reviewer participation

The change is docs-only (`doc/plans/**` prose — no `*.py`, no `.claude/skills/**`, no `marketplace/bundles/**`), so the PR carries `skip-bot-review` and no automated reviewer is expected to run. The expected-reviewer population (derived from `automatic-review/standards/{bot_kind}.md` registry docs) is therefore intentionally not invoked for this PR.

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| (all registry reviewers) | `silent` | `skip-bot-review` applied at PR creation — docs-only diff with no reviewable code footprint. |

Coverage: **0-of-M by design** (suppressed footprint). The § Step 8 shortfall disclosure is not applicable in the "reviewer scored a diff" sense; the suppression is disclosed here and in the PR label.

## Cost

- **Tokens:** not available to the agent in this session as a countable figure.
- **Wall-clock:** single interactive cloud session on 2026-08-12; the independent sub-agent ran ~192 s / 12 tool uses / ~115k subagent tokens (from its usage report).
- **Population:** this single Claude Code cloud session's usage plus one sub-agent. ⛔ NOT comparable to a plan-marshall `metrics.toon` total — a different billing boundary (orchestrator-plus-agent dispatch tree), which a single interactive cloud session does not share.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — `cloud-plan-lane` loaded first; domain skills correctly not loaded (refutation, no code change), recorded. |
| 2 Branch | Done — harness-assigned `claude/landing-message-outcome-j5up5s`, already on `origin`. Branch form: harness-assigned. |
| 3 Plan directory | Done — `doc/plans/review-apparatus/080-landing-message-carries-the-outcome-post-merge/plan.md` exists; opens with the first-instruction block (verified pre-move). |
| 4 Implement | N/A — refuted before scoping; no source change. Commits carry the trailer. |
| 4 Per-commit gate | N/A — no `*.py` touched. |
| 4 Pushed | Done at finalize — no unpushed commit remains. |
| 5 Build gate | Done — git-derived verdict: no Python changes; build skipped. |
| 6 Verification sub-agent | Done — adversarial refutation check returned REFUTATION CONFIRMED; findings recorded above. |
| 7 PR cycle | Done — docs-only PR opened with `skip-bot-review`; no code footprint to review. |
| 8 Merge gate | Conditions 1–3 met; auto-merge armed. Landing self-confirmed or delegated to orchestrator collect (recorded to operator). |
| 8 Bridge | No status/bookkeeping write outside this plan's directory; report carries the outcome for collect. |
| 9 This check | This table. |

GitHub access path used: **GitHub MCP server** (cloud session). Branch form: **harness-assigned**. A cloud run owes **no** `/sync-plugin-cache` (machine-local build step).

## What have we learned (Step 9)

The `cloud-plan-lane` contract handled a refutation-shaped run cleanly, but it never explicitly names the case: every step is written for an *implementation* run, and a plan that refutes at a verify-first gate must map its own outcome onto Steps 3–9 by analogy (report-is-the-deliverable, docs-only PR, skip-bot-review). This run did that mapping without friction, so the evidence for a contract change is **weak** — the analogy held. **No contract change proposed**, because the contract's existing "report is the deliverable" (Verification) and docs-only-PR rules already cover the refutation shape adequately; adding a bespoke refutation branch would be speculative rather than evidenced by a gap this run actually hit.

## Residue

- **D2 content enrichment** (landing message carrying an explicit, non-authoritative outcome summary) is the one residual the refutation does not deliver. It is a *smaller, separate* concern than the plan as scoped, deliberately constrained by the plan's own OUT-OF-SCOPE, and cured at the root by post-merge emission. The epic may open a fresh, correctly-scoped plan for it if still wanted. Recorded here so it is not lost.
- Nothing else open.
