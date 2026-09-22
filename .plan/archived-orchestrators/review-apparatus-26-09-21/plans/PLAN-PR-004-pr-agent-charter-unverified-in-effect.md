# PLAN-PR-004: The PR-Agent security charter is unverified in EFFECT

epic: review-apparatus
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

`pr-agent-settings` `#13` landed: `main` is at `765e23f`, `num_max_findings` is raised 5 → 12, and
the charter's closing paragraphs contest the empty-list permission and deny that severity is a
reporting threshold. What is entirely unverified is whether the MODEL's behaviour changed. The
charter is the thing that governs review depth — measured previously, across five PRs, four models
and diffs from 5 k to 57 k tokens, every published review was byte-identical at 242 bytes with zero
findings, which is why depth is treated as charter-governed rather than model-governed.

Verify the charter in effect against a known-answer oracle, and read the result by SHAPE rather
than by count. If the charter did not take, determine whether it CAN take from
`extra_instructions` at all, and report that as the finding rather than iterating on wording.

## Deliverables

1. An oracle review executed and captured: a `/review` on plan-marshall#1042, where CodeRabbit
   found six substantiated findings across the same diff — which is what justified raising the cap
   in the first place.
2. A SHAPED verdict on the result, not a counted one, against explicit pass criteria written down
   BEFORE the review is read. At minimum: does the returned set include findings below Major
   severity (if only Major returns, the severity clause did not take), and are the findings
   substantiated against the actual diff rather than plausible-sounding.
3. A recorded conclusion in one of three forms: charter took (record and close the epic defect);
   charter did not take AND cannot from `extra_instructions` (record the structural limit, escalate
   the remaining options to the operator); charter partially took (name exactly which clause
   carried and which did not).

## ⭐ New evidence 2026-07-30 — the oracle may already be on record

The five owed post-merge revisits were analysed (`findings/PR-*.md`) and produced **two direct
contradictions of the charter's intent, on real diffs, with `num_max_findings: 12` live**:

- `#1055` — CodeRabbit **4 findings**, PR-Agent **0**.
- `#1058` — CodeRabbit **2 findings, one 🟠 Major**, PR-Agent **0** while positively asserting *"No
  major issues detected"*. ⭐ **A direct contradiction of a specific claim on the same input** — a
  better-grounded oracle than a `/review` still to be induced on `#1042`.

⚠ **But `#1061` is genuine counter-evidence and must be weighed, not dropped**: there CodeRabbit
actually reviewed and also found nothing, so PR-Agent's zero was corroborated. **A verdict must account
for all three runs.** Two deficits and one corroborated clean is a different finding from "the charter
never takes", and the difference is exactly the kind this epic exists to keep honest.

**Consequence for scoping**: consider whether the `#1042` oracle is still needed, or whether the
already-recorded contradictions plus a re-read of `#1061` settle it more cheaply. If the oracle IS run,
these three runs are its comparison set.

## Claim Labels

- OBSERVED: `#13` is landed and live. `pr-agent-settings` `main` at `765e23f`, `num_max_findings`
  = `12`, and the contesting paragraphs are present in `.pr_agent.toml`. Confirmed by direct read
  at epic init.
- OBSERVED: review depth is charter-governed, not model-governed. Across five PRs, four models, and
  diffs from 5 k to 57 k tokens, every published review was byte-identical at 242 bytes — a result
  invariant under model swap is not a model result.
- OBSERVED: the residual suppressor is NOT reachable from configuration.
  `pr_reviewer_prompts.toml:150` describes `key_issues_to_review` as "A concise list
  (0-{{num_max_findings}} issues)… Only include issues you are confident about… An empty list is
  acceptable" — four suppressors in one sentence — and `extra_instructions` is appended as a
  separate block that argues ALONGSIDE it rather than replacing it. **Consequence for reading the
  result: a null result means the charter cannot win that argument from `extra_instructions`, NOT
  that the charter is wrong.** Verify by symbol (`key_issues_to_review` in the pinned image's
  prompts file), not by that line number.
- OBSERVED: a review published above `max_model_tokens` must be read as INCONCLUSIVE, not clean.
  `large_patch_policy = "clip"` truncates before the model sees it and manufactures confident wrong
  findings — API-Sheriff#118 logged `total tokens over limit: 128000` and reported an "Uncompleted
  Future Hang" while quoting the opening of the `finally` block that refutes it. The "over limit"
  log line is the ONLY signal. **Check for it before scoring the oracle.**
- HYPOTHESIS: plan-marshall#1042's diff sits below `max_model_tokens` (256 000) so the oracle is
  not silently clipped — confirm/refute by checking the runner log for the over-limit line on the
  oracle invocation itself (verify-at-outline). This is the single claim that can invalidate the
  entire measurement, so settle it before reading any finding.
- HYPOTHESIS: `/review` on a MERGED PR produces a fresh model call rather than a replayed or
  refused one — confirm/refute on the oracle invocation (verify-at-outline). If refused, an
  equivalent open-PR oracle with a comparable known-answer diff must be selected instead, and the
  substitution recorded.
- Verify-first clause: the pass criteria (deliverable 2) are written down BEFORE the review is read.
  Criteria authored after seeing the output are not criteria. A finding count proves nothing on its
  own — this epic's whole subject is confident signals that hide a caveat.

## Expected Surface

- OBSERVED: `pr-agent-settings` → `.pr_agent.toml` (`extra_instructions`, `num_max_findings`) —
  READ in every case; EDITED only if the verdict is "partially took" and a specific clause is
  identified as the cause.
- OBSERVED: `pr-agent-settings` → `README.adoc` — updated with the verification outcome, since that
  repo is self-documenting by convention: every setting carries its rationale and the evidence that
  produced it.
- OBSERVED (absence): NO plan-marshall source file is touched. The oracle is run against an
  existing PR and the verdict is reported through this plan's PR body and inbox message.

## Dependencies and Sequencing

- Depends on: `PLAN-PR-003` (same workstream), sequenced first — that plan settles how a published
  review is ingested, which this plan then has to read.
- Overlaps with: nothing.
- Adjacent to: `PLAN-PR-002` (WS-02). The org workflow, not this config repo, is where the skip
  guards live — `ignore_pr_*` keys are dead config in GitHub Action mode. Do not attempt any
  trigger-side change from here.
- ⛔ **PROHIBITED remedies**, both already falsified:
  - Never reintroduce withholding language into the charter. "Do not duplicate the other
    reviewers", "only when you can name the concrete input", "prefer one well-evidenced finding" —
    these three, stacked on upstream's already-conservative field description, resolved to zero
    findings. Overlap costs one duplicate comment; suppression costs the finding.
  - Do not "promote to pro" as a remedy for thin reviews. Wrong twice: 3.x *pro* ids 404 on this
    project (verified on #1031), and depth is charter-governed anyway.
- 🔒 The anti-fabrication clause in the charter is LOAD-BEARING. Loosening the severity bar while
  HOLDING the substantiation bar is the whole design. Pressure to report more produces invented
  mechanisms — this reviewer did exactly that on API-Sheriff#103.
- Do not touch `custom_model_max_tokens` or `temperature`. Both are REQUIRED, not tuning:
  `gemini-3.6-flash` is absent from the pinned image's `MAX_TOKENS` and `get_max_tokens()` RAISES on
  an unregistered model; `temperature = 1.0` is required by the Gemini 3 generation.
- Use `git -C /Users/oliver/git/pr-agent-settings` and the CI abstraction's `--project-dir` — this
  repo is not covered by plan-marshall's `.plan/` tooling, and `gh` is never called directly.
  Confirm the checkout's branch before reading config as live.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-004-pr-agent-charter-unverified-in-effect.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
