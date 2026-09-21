# PLAN-PR-034: A refusal nobody recognises is filed as an ordinary finding

epic: review-apparatus
workstream: WS-01

> Staged plan spec, created 2026-08-23 by the cloud-wave ingestion. Carries `040 G13`, whose remedy
> every staged plan recorded as a proposal and none implemented. See `../cloud-wave-audit.md` § 8.

## Objective

The refusal pre-filter recognises a vendor refusal notice by **enumeration** — a registry list of
declared wordings, plus a structural fallback. Both layers are positive matchers over known shapes. The
failure mode nobody owns is the one where **neither layer fires**: a reworded vendor notice is not
recognised as a refusal at all, and is filed as an ordinary review finding.

This is not the drift case. PLAN-PR-025 D2 records a `refusal_pattern_drift[]` entry when the two
layers **disagree** — which requires at least one of them to fire. When neither fires there is nothing
to disagree about, and the pipeline is silent by construction.

## Problem

`_is_refusal_notice` (`_github_pr.py:155-187`) returns a bare bool from two layers:

1. the registry layer, matching the bot's declared `refusal_patterns`;
2. a structural fallback, matching the shape of a rate-limit notice.

**PR-Agent declares zero `refusal_patterns`** (`pr-agent.md:128` — an empty list), so for the one bot
this epic's merge barrier treats as *required*, the registry layer can never fire at all. Its whole
recognition rests on the structural fallback. A vendor wording change that leaves the structural shape
unmatched produces no refusal record, no `rate_limited_bots[]` entry, no `refused_causes[]` entry — and
the notice text itself is filed as a `pr-comment` finding to be triaged like a review.

The consequence compounds with the wave's other findings: a refusal filed as a finding is a finding
that *counts toward participation*, so the bot reads as having reviewed. **The two recognition layers
fail in the same direction — toward "reviewed".**

`040 G13`'s *Done when* offers an escape hatch: *"an epic spec exists naming the remedy and its
trigger."* This spec is that, and it also implements it.

## Deliverables

**D0 — GATE, mutates nothing: measure the population before changing the predicate.** Derive, from the
registry, how many registered bots declare zero `refusal_patterns` and how many declare ≥1; and derive,
from the stored `pr-comment` corpus available locally, whether any filed finding's body matches a
refusal shape neither layer recognised. **Publish both populations with their sizes.** If the corpus
yields no instance, say so — an absence measured over a named population is a result; an absence
asserted over an unnamed one is the archetype this epic exists to remove.

**D1 — Give the predicate a positive-validation arm.** A body that is short, carries no code reference,
no file path and no line anchor, and originates from a registered bot's own login, is **not a review**
— whatever its wording. Classify it as `unrecognised_refusal` rather than filing it as a finding.
⛔ **The arm must be conservative in the direction that costs least**: a false `unrecognised_refusal`
withholds one finding from triage and is visible; a false `finding` credits participation and is not.

**D2 — Make the unrecognised case observable.** `unrecognised_refusal` rides the `fetch_findings`
return as its own field with the body excerpt that triggered it, so an operator can see what the
recognisers missed. It must be distinguishable from both a recognised refusal and an ordinary finding —
three states, three names.

**D3 — State the rule once, in the contract.** `bot-participation-contract.md` gains the statement that
recognition is enumerative, that an unrecognised refusal is a distinct state, and — the load-bearing
sentence — that **a bot whose declared pattern list is empty has only the structural layer**, naming
PR-Agent as the current instance.

**D4 — Pin it.** A test driving a wording that matches neither layer, asserting it does not become a
finding and does not credit participation. The fixture's wording must be **derived from a mutation of a
declared pattern**, not hand-written, so the test cannot pass by exercising the fallback.

## Claim Labels

- OBSERVED: `_is_refusal_notice` is defined at `_github_pr.py:155` and returns a bare bool, swallowing
  which layer fired.
  - verdict: corroborated | checked_at: f6d058b4b | by: review-apparatus/cleanup | rescoped: n/a | evidence: Re-grounded at HEAD f6d058b4b (advance from 26f2f417b = PRs #1332, #1335, #1334) by DERIVATION, not re-audit: 22 paths moved, intersected against the WHOLE spec file rather than a parsed Expected Surface section. Two section-parsers disagreed on which specs intersect, so the whole-file scan was used as the fail-closed superset. Intersects automatic-review/standards/pr-agent.md via #1334. PREMISE RE-VERIFIED FIRST-PARTY AT HEAD: refusal_patterns is still declared EMPTY at pr-agent.md:154, so the registry layer still can never fire for the one required bot. #1334 did NOT touch that field - it added an ignore_patterns entry and rewrote participation_evidence prose. Prior verdict stands, and #1334's corpus analysis strengthens it: pr-agent's non-refusal is STRUCTURAL (no quota, no diff-size refusal - it clips), so the never-firing layer has no counterexample anywhere in 224 PRs. Incidence still unmeasured - D0 measures it first.
- OBSERVED: `pr-agent.md:128` declares an empty `refusal_patterns` list; `coderabbit.md:54-55` declares
  one wording and `sourcery.md:42-44` declares two. Population: three registered bots.
- OBSERVED: `github_re_review._ReReviewStrategy._refusal_record` (`:325-337`) already re-implements the
  two-layer split open, emitting `layer: registry_refusal_patterns | structural_fallback`.
- HYPOTHESIS: no filed `pr-comment` finding in the local corpus is an unrecognised refusal —
  confirm/refute at D0 against the stored findings (verify-at-outline). **An asserted absence is
  verified exactly like an asserted presence.**
- Verify-first clause: **check whether PLAN-PR-025 D2 has landed first.** That plan opens the same
  function to add layer provenance. If it has landed, this plan extends its seam rather than adding a
  third copy; if it has not, this plan must not pre-empt its provenance field.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py`
  — `_is_refusal_notice` and its two call sites
- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/bot-participation-contract.md`
  — a new subsection; **no passage the shared-document split table names**
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/github_pr.py`
  — the `fetch_findings` return literal
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_pr.py`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/pr-agent.md` — only
  if D3's instance statement belongs beside the empty list rather than in the contract
  (verify-at-outline)

## Dependencies and Sequencing

- **Depends on: PLAN-PR-025** — it opens `_is_refusal_notice` for layer provenance. Running after it
  means extending one seam instead of creating a third implementation of the same split.
- **MUST NOT run concurrently with PLAN-PR-024, PLAN-PR-025 or PLAN-PR-029** — all touch `github_pr.py`
  and `test_github_pr.py`.
- ⚠ **`_is_refusal_notice` has two callers and they are owned differently**: `:1040` (the filing
  pre-filter — this plan's) and `:950`, **inside the participation loop `:941-975` that PLAN-PR-024
  rewrites end-to-end**. This plan must not edit the participation loop.
- Adjacent to: PLAN-PR-029 D1, which fixes the *noise* pre-filter destroying real findings — the
  opposite direction on a neighbouring function. Neither subsumes the other.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-034-a-refusal-nobody-recognises-is-filed-as-a-finding.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
