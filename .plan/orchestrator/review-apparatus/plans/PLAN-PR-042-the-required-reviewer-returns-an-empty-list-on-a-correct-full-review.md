# PLAN-PR-042: The required reviewer returns an empty list on a correct, full review

epic: review-apparatus
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> ⭐⭐⭐ **HIGHEST PRIORITY — operator-set, 2026-08-30.** Emit this first once a slot frees.
> Derived from the six-repo corpus pass
> ([`../findings/2026-08-30-pr-agent-vs-coderabbit-multirepo.md`](../findings/2026-08-30-pr-agent-vs-coderabbit-multirepo.md))
> and a first-party workflow-log investigation performed the same day.

## Objective

`pr-agent` is this organisation's **required** reviewer. It returns the identical canned
*"No major issues detected / No security concerns identified"* table on **42 of 44** reviews and an
empty suggestion list on **24 of 24** `/improve` runs. Every mechanical explanation has been
eliminated first-party. **Find the actual cause by controlled experiment, then act on it** — this
plan is an INVESTIGATION whose deliverable is evidence and a decision, not a pre-chosen fix.

⛔ **This plan does NOT authorise writing more charter text.** Charter exhortation is retired, and
§ Claim Labels records the first-party observation that closes that door again.

## Why this is the epic's top item

A required reviewer that answers empty on 95% of PRs is **a gate that cannot fail**. The merge
barrier cannot distinguish it from a reviewer that was never asked. Every other reliability item in
this epic is downstream of the question this plan answers.

## What has ALREADY been eliminated — do not re-investigate

All four were read first-party from the `PR Agent Review` run log for **plan-marshall PR #1370**
(run `33333426580`, 2026-08-30) and from the corpus. ⛔ **Re-deriving these is wasted effort; the
plan starts after them.**

| Hypothesis | Verdict | Evidence |
|---|---|---|
| The model ladder fell through to a weaker model | **REFUTED** | `Generating prediction with vertex_ai/gemini-3.7-flash` — the LEADING model, no fallback |
| The diff was clipped to fit the context | **REFUTED** | `Tokens: 203455, total tokens under limit: 256000, returning full diff` |
| The charter is absent or not applied | **REFUTED** | The full domain-routed pack is in `extra_instructions`, including *"Severity is not a reporting threshold"* and *"There is no such bar"* |
| The bot was never triggered | **REFUTED** | The run executed and published; coverage is 44 of 93 PRs |
| Yield degrades with diff size | **REFUTED** | Hit rate by size bucket: 0–100 lines **0%** (n=5), 100–300 **0%**, 300–1k **11%**, 1k–3k **6%**, 3k+ **0%**. The two hits are 2200 lines/39 files and 754/13 — the larger sits ABOVE the empty median of 1942 lines |

⇒ **On a correct model, with the full diff, under a maximally permissive charter, pr-agent returned
an empty finding list.** That is the defect, stated precisely.

## Deliverables

### D0 — Reproduce the null result under controlled conditions

Pick **three** PRs from the corpus where CodeRabbit filed a substantiated finding that pr-agent
missed (the corpus names 35 candidates). For each, re-run `/review` unchanged and confirm the empty
result reproduces. ⛔ **If it does not reproduce, STOP and report** — the effect would then be
non-deterministic (`temperature: 1.0` is a live suspect), and that finding supersedes D1–D3.

*Done when:* three re-runs are recorded with their run ids and outcomes, and the report states
whether the null result is deterministic.

### D1 — A/B the knobs that plausibly suppress a finding list

The observed config (read from the #1370 log, re-read it at run time rather than trusting this list):

```text
model: vertex_ai/gemini-3.7-flash     temperature: 1.0        reasoning_effort: medium
num_max_findings: 12                  restricted_mode: true   require_security_review: true
max_model_tokens: 256000              large_patch_policy: clip
```

Vary **one at a time**, against the same three PRs from D0:

1. `temperature` 1.0 → a low value. A sampling temperature of 1.0 on an extraction task is the
   single most suspicious knob.
2. `reasoning_effort` `medium` → `high`.
3. `model` → `vertex_ai/gemini-2.5-pro` (already declared in `fallback_models`, so it is entitled
   and needs no new provisioning).

⛔ **One variable per run.** A combined change that produces findings identifies nothing.
⛔ **Report the null results too.** A knob that changes nothing is a result, and omitting it turns
this into a search for a confirming instance.

*Done when:* a table of (PR × knob × findings-count) covering every cell attempted, each row naming
its run id, and an explicit statement of which knob — if any — moved the outcome.

### D2 — Decide, and record the decision with its rejected alternatives

From D0/D1 evidence, take exactly one arm and record why the others were rejected:

- **(a) Config fix** — a knob demonstrably restores yield ⇒ change it in `cuioss/pr-agent-settings`
  and state the expected effect on the other 20 repos.
- **(b) Model change** — only the stronger model restores yield ⇒ record the cost/latency trade
  explicitly; a flash-tier model is cheap and a pro-tier one is not, across 21 repos.
- **(c) Roster change** — nothing restores yield ⇒ pr-agent cannot serve as the *required* reviewer,
  and the required set must change. ⛔ **This is PROMOTE-CodeRabbit, never DROP-pr-agent**: see the
  Claim Labels below — pr-agent found a **security** defect CodeRabbit did not, so its marginal value
  is non-zero even at this yield. Coordinate with **PLAN-PR-025B D7**, which already promotes
  CodeRabbit to required; this plan supplies the evidence that D7 alone is insufficient.

*Done when:* one arm is chosen, the rejected arms carry a recorded reason, and — if (a) or (b) — the
change is applied and a post-change PR is measured to confirm the yield actually moved.

### D3 — Make the null result observable without a corpus pass

Today, discovering this took a six-repo, 93-PR analysis. **A required reviewer answering empty is a
condition the tooling should surface by itself.** Add a signal — a counter, a retrospective field, or
a barrier disclosure — that reports *"required reviewer produced a canned-empty review"* distinctly
from *"required reviewer produced findings"* and from *"required reviewer did not run"*.

⛔ **Three states, never two** — collapsing empty into absent is the exact defect PLAN-PR-026 exists
to close; coordinate rather than duplicate. ⛔ This deliverable **depends on the sibling defect
filed on PLAN-PR-037** (`_is_actionable` buckets `issue_comment` → meta unconditionally, so
pr-agent's `actionable_count` is structurally 0): a signal built on the unfixed classifier would
read every pr-agent review as empty, including the two that were not.

*Done when:* the three states are separately representable and a test pins each, including a
**matched negative control** — a pr-agent review carrying a real finding must NOT report as empty.

Four deliverables, comfortably inside the split guard.

## Claim Labels

- OBSERVED: pr-agent returned the canned empty table on 42 of 44 review guides and an empty list on
  24 of 24 `/improve` runs, over 93 PRs opened 2026-08-23 → 2026-08-30 across six repositories.
  Confirm/refute at [`../findings/2026-08-30-pr-agent-vs-coderabbit-multirepo.md`](../findings/2026-08-30-pr-agent-vs-coderabbit-multirepo.md)
  § Yield. ⭐ Corroborated on an axis independent of the parser: body length partitions the 44 guides
  as 42×~200 bytes, one 1001, one 1798.
  - verdict: corroborated | checked_at: 19453cb | by: review-apparatus/cleanup | rescoped: n/a | evidence: Re-grounded at HEAD 19453cb (was 7845a4b9a). METHOD CHANGED THIS PASS: intersection of the spec's DECLARED Expected Surface (via corpus surfaces, the single shared reader) against git diff --name-only 7845a4b9a..HEAD (204 paths). The former whole-spec-file method is RETIRED as non-discriminating - it scored hits on prose mentions of CLAUDE.md and .plan/marshal.json. ZERO declared paths moved in this window, so no premise of this spec was disturbed. NOT a line-by-line re-audit: this establishes the surface is UNDISTURBED, not that the premise was re-read.
- OBSERVED: on plan-marshall PR #1370 the review used `vertex_ai/gemini-3.7-flash` with the full
  diff (`Tokens: 203455 … returning full diff`) and the complete domain-routed charter, and still
  produced the canned empty table. Confirm/refute in the `PR Agent Review` run log, run
  `33333426580` — ⛔ **GitHub Actions logs expire; if it is gone, re-run the observation on a current
  PR rather than citing this id as fact.**
- OBSERVED: yield does not correlate with diff size — hit rate 0% / 0% / 11% / 6% / 0% across
  ascending size buckets, and the two hits are not the smallest PRs. Confirm/refute by re-deriving
  the bucket table from PR `additions + deletions`.
- OBSERVED: pr-agent's two substantive findings are both real, and one is a **security** defect
  CodeRabbit did not file — cui-http #162, a fail-open in the RFC 7239 `Forwarded` parser where
  whitespace before `=` bypasses malformed-directive detection so reconciliation does not fail
  closed. The other is API-Sheriff #230's stale `-T1C` Maven flag. ⛔ **This is why the remedy is
  never "drop pr-agent".**
- OBSERVED: `temperature: 1.0`, `reasoning_effort: medium`, `num_max_findings: 12` and
  `large_patch_policy: clip` are the live values. Confirm/refute in the run log's `Relevant configs`
  record — **re-read them; a settings change in `cuioss/pr-agent-settings` moves them.**
- HYPOTHESIS: the empty list is produced by the model/prompt-schema combination rather than by any
  repository-side configuration — confirm/refute at D1's knob table (verify-at-outline). ⛔ n=1 run
  log; this is precisely what D0/D1 exist to settle, and it must not be reported as established.
- HYPOTHESIS: `temperature: 1.0` is the highest-yield single suspect — confirm/refute at D1 item 1
  (verify-at-outline). Reasoning from the task shape, NOT from any observation of a temperature
  change; if D1 refutes it, that is an ordinary outcome and not a surprise to explain away.
- ⛔ **NOT ESTABLISHED, and out of scope to assert:** that pr-agent's yield was ever adequate. The
  prior corpus measured 70.6% empty guides against today's 95.5% — different substrates and
  populations, so treat the decline as INDICATIVE, never as a measured regression with a cause.

## Expected Surface

- OBSERVED: `cuioss/pr-agent-settings` — the org-level review configuration (foreign repo; D1/D2's
  knob and model changes land here, not in this repository).
- OBSERVED: `cuioss/cuioss-organization/.github/workflows/reusable-pr-agent-review.yml` — the
  workflow that composes the charter and invokes the reviewer (foreign repo).
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md` — the
  registry doc, if D2 changes what the reviewer is expected to produce (verify-at-outline).
- HYPOTHESIS: `.claude/skills/finalize-step-review-retrospective/scripts/review_retrospective.py` and
  `marketplace/bundles/plan-marshall/skills/automatic-review/scripts/review_completeness.py` — D3's
  three-state signal (verify-at-outline; the exact seam depends on D3's chosen surface).
- HYPOTHESIS: `test/plan-marshall/automatic-review/` and
  `test/plan-marshall/finalize-step-review-retrospective/` — D3's tests and its negative control.

## Dependencies and Sequencing

- ⛔ **Depends on the PLAN-PR-037 fold** (`_is_actionable`'s unconditional `issue_comment` → meta
  bucketing) for **D3 only**. D0–D2 are independent and can proceed regardless.
- Coordinates with **PLAN-PR-025B D7** (promote CodeRabbit to required): D7 changes the roster, this
  plan establishes whether the required member can be repaired. Neither blocks the other, but D2's
  arm (c) is D7's justification, so **report D2's outcome to D7 before D7 runs**.
- Coordinates with **PLAN-PR-026** (nobody-reviewed and reviewed-clean are one signal): D3 is the
  same three-state distinction. ⛔ Do not build a second mechanism — fold into PR-026's if it lands
  first.
- ⚠ **Mostly FOREIGN-REPO work.** D1/D2 change `cuioss/pr-agent-settings`, which fans out to ~21
  repositories. State the blast radius in the run report and follow the epic's foreign-PR discipline:
  corroborate a landing against the FOREIGN PR, never against a local message.
- ⚠ Re-derive the live-plan collision set before launch.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-042-the-required-reviewer-returns-an-empty-list-on-a-correct-full-review.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests, plus the foreign
configuration repositories named in § Expected Surface. It creates and edits NO file under
`.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
