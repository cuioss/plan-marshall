# Landing: PLAN-PR-003 — CodeRabbit AI-agent block: strip vs extract

epic: review-apparatus · workstream: WS-03 · shipped 2026-08-13
cloud run: `cloud-runs/100-coderabbit-ai-agent-block-strip-vs-extract/`
PR #1212 (`71dd3779b`)

> Landing analysis over the cloud-wave corpus. `report-01.md` is the run's claim; `verification.md`
> is ground truth. Where they disagree, verification wins.

**Verification verdict: `verified-with-gaps`.**

## What landed

The contradiction is genuinely gone: the extract reading exists nowhere in the tree, both changed
documents state a single STRIP + never-execute rule, `pr-agent.md` was correctly left alone, D1 honestly
reported a **no-op** instead of inventing work (the plan's "there is an enacting script" HYPOTHESIS was
refuted — the strip is prose-only), and D3 correctly refused to run.

**Deliverables: 4 — 2 done, 2 partial.**

## ⛔ The run got the one thing D0 singled out as load-bearing wrong: the recorded cause

`coderabbit.md` asserts that the architecture already strips the block and that no consumer can
re-parse it. **Both halves are false**, settled by executing the ingestion chain: the block arrives
byte-identical in the promoted top-level `body`, and `triage.md` instructs reading exactly that field.
The `triage-reads-top-level-only` invariant guards `raw_input.*` — a different namespace, and its
analyzer has no notion of the block.

## ⭐⭐ `_is_obvious_noise` reads the AI-agent block and can destroy a real finding

Four of twelve shared `ignore.low` regexes are unanchored substrings (`\blooks good\b`, `\bship it\b`,
`\bno objection\b`, `\[bot\]`). A phrase occurring **only inside** a CodeRabbit `<details>` block flips
`_is_obvious_noise` from `False` to `True`; the call site increments `skipped_noise` and `continue`s —
indistinguishable from a genuine "lgtm". Reproduced by execution. Latent only because
`enable_prompt_for_ai_agents` is off. **A length threshold alone does not close it** — PLAN-PR-029 D1
is right to require the structural guard too.

## Report claims the verification found false

- D2 evidence item 2 — "There is no supported path by which a consumer re-parses the block for
  fields" — **false**, mechanism above.
- D2 evidence item 1 — "No consumer, in the machine sense" — accurate about *parsing*, overstated as
  written (the noise pre-filter above).
- Absence-claim scope — match counts published with no denominator, and the totals are
  self-referential: they rise with every document added to the plan directory.
- A pre-existing falsehood the run read past: *"the finding's full body is in `detail`"* stands at
  **seven** sites across four bundles; D1 quoted one of them verbatim without noticing.

## Gaps: 9 — 9 full, 0 partial, 0 uncovered

`100 G6` re-verified live at HEAD: `coderabbit.md:88` still names `scripts/comment-patterns.json`,
a path that does not exist.

## Standing facts

- ⛔ **The untrusted comment body lives in the promoted top-level `body`, never in `detail`.** `detail`
  carries producer-built structured metadata only. The wrong claim stands at **seven** sites across
  four bundles, and a prior sweep corrected two sibling sentences and stopped — the canonical case of
  *a claim is corrected at every site or it is not corrected*.
- ⭐ **`triage-reads-top-level-only` does not strip anything.** Any rationale leaning on an invariant
  must be checked against what that invariant's analyzer actually matches. This one was falsifiable by
  calling four functions.
