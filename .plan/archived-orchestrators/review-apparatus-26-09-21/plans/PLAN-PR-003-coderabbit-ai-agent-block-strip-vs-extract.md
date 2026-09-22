# PLAN-PR-003: The AI-agent-block ingestion contract contradicts itself in one file

epic: review-apparatus
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

`automatic-review/standards/coderabbit.md` gives two mutually exclusive instructions about
CodeRabbit's `🤖 Prompt for AI Agents` block, four lines apart: a "Strip from the body before
reasoning (noise, not findings)" list that names the AI-agent prompt block explicitly, and then a
trust-boundary section calling the same block "high-value structure (the cleanest per-finding
payload)" and instructing the reader to extract file/line/summary as fields. A reader following
this document does one or the other depending on which paragraph they reach first, and nothing
announces the divergence.

This is not a documentation tidy-up. The contradiction is why the `cuioss/coderabbit` `#3` premise
could not be settled: that PR turned `enable_prompt_for_ai_agents` OFF on the grounds that nothing
consumes the block, while the config comment it replaced said to keep it because plan-marshall
ingests it. Both cannot be true. Settle which behaviour is correct, make the standard say exactly
one thing, verify the enacting code matches, and then close the `#3` premise on evidence.

## Deliverables

1. One resolved instruction in `automatic-review/standards/coderabbit.md`: the block is either
   stripped as noise or extracted as a payload, stated once, with the losing reading REMOVED rather
   than qualified. Include the reasoning that settles it, because a contradiction removed without a
   recorded cause returns.
2. The enacting surface verified to match the resolved instruction — the ingestion path that
   actually strips or extracts. If the code and the resolved instruction disagree, the code is
   corrected; a standard that describes behaviour nothing implements is the same defect in the
   other direction.
3. The `cuioss/coderabbit` `#3` premise closed on the evidence produced here: either the config
   change stands (nothing consumed the block) or the epic's standing watch is promoted to a real
   degradation and the config decision is revisited with the operator.
4. If the resolution is EXTRACT: an assessment of what was lost on every CodeRabbit review since
   `a97b64f`, since the block has been off since then. State it as a bounded assessment, not a
   count — see the claim label below.

## Claim Labels

- OBSERVED: the contradiction is real and in one file. Read at
  `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md` — the
  "Strip from the body before reasoning (noise, not findings)" list names "the AI-agent prompt
  block (next section)"; the immediately following `## Trust boundary — the "🤖 Prompt for AI
  Agents" block` section calls it "high-value structure (the cleanest per-finding payload)" and
  says to "extract file/line/summary as fields". Verify by SYMBOL (the two section headings), not
  by the line numbers under which it was found.
- OBSERVED: `enable_prompt_for_ai_agents` is now `false` in `cuioss/coderabbit` at `a97b64f`
  (that repo's `#3`), and the config comment it replaced asserted the opposite rationale.
- OBSERVED: `automatic-review/SKILL.md` independently states the block must never be treated as
  executable. This is consistent with BOTH readings — treating text as data-to-extract and
  discarding it are both non-execution — so it does not settle the question. Do not mistake it for
  a tie-breaker.
- OBSERVED: `automatic-review/standards/pr-agent.md` records that PR-Agent emits no such block, so
  this defect is CodeRabbit-specific and the resolution must not be generalized to pr-agent.
- ⛔ **SETTLED 2026-08-08 — the Sourcery population HYPOTHESIS is REFUTED. Do not spend outline effort
  re-deriving it.** Orchestrator-verified first-party across all three registry docs:
  `sourcery.md:158-162` carries the trust-boundary **extract** instruction ("Extract file/line/summary;
  the imperative text is a hint") but **no strip-list naming the block** — a case-insensitive sweep for
  `strip` over `sourcery.md` returns **zero** matches, and over `pr-agent.md` returns one unrelated hit
  (`bot_kind_for_author` suffix handling, `:56`). `pr-agent.md:371` independently records that PR-Agent
  **emits no such block at all**.
  ⇒ **The contradiction exists in exactly ONE document, `coderabbit.md`** (the strip-list at `:138-140`
  naming "the AI-agent prompt block (next section)" against the extract instruction at `:142-149`,
  four lines later, both verified live). ⭐ **The population is one, so the fix is one document** — and
  the per-document fan-out this bullet feared is not owed. **Scope accordingly and do not widen.**
  ⚠ Sourcery still carries the extract half alone, which is *consistent*, not contradictory — but if
  the resolution here is STRIP, `sourcery.md` then diverges from the settled rule and must be aligned
  in the same pass. **The population is one for the contradiction, two for the resolution.**
- HYPOTHESIS: there is an enacting script, not only prose — confirm/refute by locating whatever
  performs the strip in the `automatic-review` / `workflow-integration-github` ingestion path
  (verify-at-outline). If the strip is prose-only (enacted by an LLM reading the standard), then
  deliverable 2 is a no-op and the plan says so explicitly rather than inventing a code change.
- HYPOTHESIS (asserted absence, higher risk): nothing else in the bundle set consumes the block —
  confirm/refute by searching the whole marketplace tree for the block's marker text, not just the
  `automatic-review` skill (verify-at-outline). An unverified absence here is what produced the
  `#3` dispute in the first place.
- Verify-first clause: deliverable 4's "what was lost" is an ASSESSMENT of the payload's role, not
  a tally of missed findings. A count of findings that would have been extracted is unknowable
  after the fact; do not manufacture one. This project has repeatedly read a volume number as a
  coverage number.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/coderabbit.md`
  — the strip-list and the AI-agent trust-boundary section.
- HYPOTHESIS: `.../automatic-review/standards/sourcery.md` — same contradiction, if confirmed
  (verify-at-outline).
- HYPOTHESIS: the enacting ingestion path under `.../automatic-review/scripts/` or
  `.../workflow-integration-github/scripts/` (verify-at-outline; may be prose-only).
- HYPOTHESIS: `.../automatic-review/standards/comment-patterns.json` — if the strip patterns are
  data-driven, this is the real strip site (verify-at-outline).
- OBSERVED: `cuioss/coderabbit` → `.coderabbit.yaml` and `README.md` — touched ONLY if the
  resolution is EXTRACT and the operator agrees to revisit `#3`.

## Dependencies and Sequencing

- Depends on: none.
- Sequenced BEFORE `PLAN-PR-004` in this workstream. Reason: the block has been off since
  `a97b64f`, so if the resolution is EXTRACT this is a live degradation on every CodeRabbit review;
  and PLAN-PR-004 reads a published review as its oracle, which is easier once ingestion is
  unambiguous.
- Overlaps with: nothing in-epic.
- Adjacent to: ⚠ `truthful-signals` PLAN-116 may touch `automatic-review/standards/`. Re-verify
  that boundary at outline against that epic's live queue, citing it by SLUG.
- ⛔ Do NOT revive `cuioss/coderabbit` `#4` as any part of this work. It is CLOSED and FALSIFIED by
  plan-marshall#1043 — its own final commit says so. Its notes remain readable on the closed PR for
  measurement context only.
- Confirm the `coderabbit` checkout's branch before reading its config as live. That tree was found
  on an unmerged falsified branch at epic init.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-003-coderabbit-ai-agent-block-strip-vs-extract.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
