# Landing Analysis: PLAN-70 — Retire the Gemini bot registry; ground the PR-Agent standard

epic: truthful-signals
workstream: WS-01
pr: #1014 (https://github.com/cuioss/plan-marshall/pull/1014) — merged as `b7a2242f`

> Landing record. Claims verified against shipped source and the live plugin cache, not the finalize
> narrative. **This landing produced the epic's most consequential finding to date — it very likely
> REFUTES a staged plan's core premise.** See § Follow-Ups.

## Deliverable Fidelity vs Spec

6/6 shipped; 21/22 finalize steps green (the 22nd — plugin-cache sync — refused correctly, see below).

| Deliverable | Verdict | Evidence |
|---|---|---|
| D1 — classify every gemini reference; settle the unknown-bot contract | shipped-as-specified | 46 files classified; unknown-bot verdict came out **fail-safe by inspection, not by assumption**: an unregistered bot's comment is filed with an empty `bot_kind` and **never dropped** (`_findings_core.py:247`). So retiring the registry was not fail-open and **no new path was needed** — a correctly-declined addition |
| D2 — delete registry record + class-(a) operative refs | shipped-as-specified | registry record and operative references removed |
| D3 — sweep class-(b) prose; verify residual as a checked claim | shipped-as-specified | residual verified as a *checked* claim rather than asserted |
| D4 — ground `pr-agent.md` in observed review output | shipped-as-specified, **evidence-gated** | the gate passed, so **nothing was written from assumption** — this is the plan's best structural feature and the direct answer to the placeholder it replaced |
| D5 — fix two structural PR-Agent gaps the grounding surfaced | shipped-as-specified, **self-validating** | the transmit fix **validated itself live on this very PR**: Sourcery's comment was thread-less — exactly the case that used to be silently dropped — and routed through the new path with `count_untransmitted: 0` |
| D6 — migrate bot-registry and producer test coverage | shipped-as-specified | 15207 tests green; plugin-doctor clean |

**D5 is the model to copy.** A fix whose first production exercise was the precise edge case it
targeted, with a counter proving nothing was dropped. Contrast the epic's recurring
`test-pins-the-defect` archetype: this is a test-pins-the-*fix* instance.

## Metrics and Anomalies

- Total 4h44m worked / 12h26m wall / 3.63M tokens. **6-finalize alone: 2h2m worked, 9h11m wall,
  1.47M tokens** — 41% of all tokens in one phase, and a 7h idle gap inside it.
- Planning (phases 1–4) 1.32M vs execute 837K = **1.6 : 1**. Notably healthier than #1012's 4.3 : 1,
  which weakens any general "planning always dominates" reading — see PLAN-57's candidate-mirror note,
  which should NOT be over-read on n=1.
- Anomalies: two self-corrections by the executing agent (both recorded honestly, both material — see
  below) and a correctly-refused cache sync.

## Routing and Merge Behavior

- **Review: ZERO bots substantively reviewed this diff.** CodeRabbit noise-filtered; **Sourcery
  refused on size (>150k chars)**; PR-Agent silent behind a green check. Merge proceeded on the
  deterministic gates, which was the right call given 15207 green tests — but the PR page's green
  state **overstated review coverage**.
- CI/merge: squash `b7a2242f`, main clean; worktree removed.
- Surface collisions: none. PLAN-70 ran concurrently with PLAN-69/54/55 and stayed inside the bot
  registry + `automatic-review` surface.

## Reconciliation Actions

- [x] status.json `plans[]` — PLAN-70 `launched` → `shipped`, `pr=1014`, `landing=landings/PLAN-70.md`
- [x] epic.md queue reconciled from status.json
- [x] **PLAN-75 Defect B gated with a MUST-VERIFY-FIRST retraction** (below)
- [x] PLAN-72 strengthened to n=3 with a NEW failure mode
- [x] PR-Agent behavioural-proof claim **DOWNGRADED** (below)
- [x] resume_anchor + START-HERE regenerated

## Follow-Ups

### ⛔ 1. PLAN-75's Defect B is very likely REFUTED — and the orchestrator's own confirmation was wrong

The retrospective found the plugin cache **never received PR #990**: it carried
`order: 80` and no `mutates_source` for `finalize-step-preference-emitter`, where source carries
`61` / `true`. The executing agent self-corrected accordingly: *"I flagged a manifest ordering defect
that turned out to be the stale cache, not the composer."*

**Orchestrator-verified first-party, and it is decisive:**

- OBSERVED — `marketplace/bundles/.../finalize-step-preference-emitter.md:7` → `order: 61`.
- OBSERVED — cache `0.1.1204` and `0.1.1203` → `order: 61` + `mutates_source: true`.
- OBSERVED — **cache `0.1.1194` → `order: 80`, no `mutates_source`.**
- OBSERVED (memory/ledger) — the plugin cache was **pinned at 0.1.1194** until a manual fix on
  2026-07-27. The dormated run that supplied PLAN-75's "confirming artifact" executed **2026-07-26**,
  i.e. under the pin.

**⇒ Under `order: 80`, placing the step after `branch-cleanup` (order 70) is CORRECT ascending
order. There is no inversion. The composer was faithful to the contract it was given — a STALE one.**

This retracts the orchestrator's own escalation. PLAN-75's spec currently says Defect B is
*"CONFIRMED in a real composed manifest"* and that *"PLAN-44's fix is inert at HEAD"*. **Both claims
are now believed false, and both were mine.** The error is the epic's own flagship archetype turned on
its author: I compared a runtime artifact against *source* while the runtime was reading a *stale
cache* — the identical trap the #1014 agent fell into and corrected. It is also the third refuted
hypothesis on this one plan.

⚠ **Not fully closed:** `execution.toon` carries **no manifest/cache version stamp**, so the pin is
established by ledger correlation, not by the artifact. Labelled **HYPOTHESIS-grade refutation**
pending one check — re-compose the manifest at HEAD and confirm the step sorts to its 61 slot. The
spec has been gated so no plan can proceed on the old premise. **Defect A (a configured, enabled step
silently absent from the composed manifest) is untouched by this and still stands.**

**Second-order lesson worth more than the defect:** an execution artifact that records *what ran*
without recording *which version composed it* is unfalsifiable after the fact. That is a candidate
deliverable for whichever plan owns manifest observability (PLAN-64), and it is why this refutation
cannot be closed today.

### ⚠ 2. PR-Agent behavioural proof — my DISCHARGE is DOWNGRADED, not upheld

The executing agent corrected itself: *"I claimed PR-Agent's green check was the behavioural proof its
self-cancel fix worked — it wasn't, it published nothing."* **That correction applies to my #1012
discharge too.** The #1012 evidence was an operator report that PR-Agent *"ran"* — and "ran" is not
"published". This repo already carries the standing rule that **PR-Agent exits 0 when every model call
fails**, so a green check is precisely the signal that cannot discharge this. Proof status returns to
**OWED**: it requires an observed published `## PR Reviewer Guide 🔍` comment on ordinary traffic.

### ⛔ 3. PLAN-72 reaches n=3, with a NEW failure mode — size-based refusal

**Sourcery refused this diff on size (>150k chars).** That is qualitatively different from the two
known modes (rate-limit, self-cancel): it is **deterministic and inversely correlated with risk** —
the largest, most review-hungry diffs are exactly the ones that get refused. Combined with
CodeRabbit noise-filtering to zero and PR-Agent's silent green, this PR achieved **0 of 3 substantive
reviews while presenting a fully green page**. Recorded into PLAN-72.

### 4. Operator-owed — two uncommitted edits on `main` are blocking cache sync

`marshal.json` (`re_review_on_loopback` → `true`) and matching `automatic-review/SKILL.md` prose. The
executing agent correctly left them alone (not its change) and verified the squash lost nothing.
**The sync guard refused correctly** — it saw the source tree change after the emit fingerprint. The
sequence you need: commit-or-revert → re-run deploy-target → sync. Until then the cache stays stale,
and **every skill doc loaded in a session comes from that stale cache** — which is the mechanism
behind follow-up 1.

### 5. Lesson recurrences confirm existing plans rather than opening new ones

Three of five captured lessons merged as 3rd/4th recurrences: **adaptive-timeout self-cap** (owned by
**PLAN-62**, queue position 4 — strengthened), **search-tool denial in dispatched leaves**, and
**stream-idle stall** (both already carried in memory as harness-level constraints). No new plan
staged; the recurrence counts are the signal that PLAN-62's placement is correct.
