# PLAN-03: Calibration-axis decision

epic: next-level
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off. The orchestrator
> EMITS the command below; it never launches the plan inline. This spec is SELF-SUFFICIENT: the
> emitted command is a one-line pointer and carries no brief, so every per-plan carry is authored here
> and nowhere else.

## Objective

Settle, as a recorded architectural decision, whether the multi-target generator grows an axis that can
vary instruction *calibration* per model or capability tier — or whether it deliberately declines one
and the corpus is held at the weakest supported model's calibration. **Both answers are acceptable.
Drifting into the second by default, while a third runtime ships without an answer, is not.**

This plan produces a decision and an ADR. It implements no axis. Its value is entirely in being taken
now: the cost of retrofitting rises with every target that ships and every consumer repository pinned
to their output, so this is the cheapest moment available and it does not recur.

## Deliverables

1. A **derived** statement of the generator's current expressive limit: what the shared body-transform
   engine can and cannot vary, enumerated from the engine rather than sampled.
2. A derived count and listing of every component using `targets:` frontmatter scoping today, with the
   scope each one declares — the evidence for whether the existing switch is being used as a
   calibration mechanism or not.
3. An ADR recording the decision, its alternatives, and the reasoning — including, if the answer is
   "no axis", what the corpus is thereby committed to and what that costs the strongest model in the
   fleet.
4. A re-confirmed model→target mapping as of the decision date, marked as a snapshot with its source.
5. ⭐⭐ **Read the SkCC study before deciding, and record what it actually says.** Folded from inbox
   `next-level-006`. This is deliverable **zero** in practice — it precedes the decision, and skipping it
   would settle the epic's central question against a second-hand summary.

## Folded finding — `next-level-006`, the sharpest external input this epic has received

An outside course whitepaper cites Ouyang et al., 2026, *SkCC: Portable and Secure Skill Compilation for
Cross-Framework LLM Agents* (`arxiv.org/abs/2605.03353`). **As the whitepaper reports it**: LLM agents
show extreme sensitivity to instruction formatting, with up to a **40% performance drop** from generic
unoptimised Markdown; the optimal format is **model-specific**; for Gemini the reported best strategy is
hybrid Markdown plus conditional YAML at nesting depth > 3, with reported parsing accuracies YAML
**51.9%**, JSON **43.1%**, XML **33.8%**; and their remedy is a compiler emitting one source to each
model's optimal target format.

⛔ **Every figure above is unverified and none may be treated as a measurement of our corpus.** Nobody
here has read the study — only a whitepaper's summary of it. The endnote resolves to an arXiv id, so
verification is cheap, and deliverable 5 exists because it must precede any use.

**Why it lands squarely on this plan.** It is the same architecture as our multi-target generator
arriving at a conclusion our generator does not implement. Our standing position is that the generator
translates vocabulary, not calibration — emphasis and scaffolding ship byte-identical to every target.
SkCC's claim is that format calibration is per-model, mechanical, and worth up to 40%. ⭐⭐ **If that
holds, the byte-identical export is not neutrality; it is a silent per-target regression on every target
but the one the corpus was written against.** And the in-flight third target is Gemini-backed — the exact
model those specific numbers describe.

**Two cautions that cut against over-reading it, and both bind:**

- ⛔ **A per-model format table is the calibration trap, not the escape from it.** A compiler that emits
  Gemini-optimal YAML is safe only if it emits a target-appropriate form for *every* runtime, including
  the ones nobody measures. **A half-built compiler is worse than none** — it improves one target and
  leaves the rest silently behind, which is precisely the failure this epic exists to prevent.
- ⚠ **We already own part of the answer, and its status changes.** TOON is our structured wire format,
  and whether it is the right per-runtime form is now an **empirical** question rather than a settled
  one. ⛔ That is a finding, not a defect claim: nothing here shows TOON is wrong anywhere.

## Claim Labels

- OBSERVED: `TARGET_REGISTRY` is defined at `marketplace/targets/__init__.py` and is the source of
  truth for registered targets — read in this session via `architecture search --content`; corroborated
  by `CLAUDE.md` § "Multi-Assistant Support", which names it as the registry and states that
  "only Claude Code is tested as a runtime".
- HYPOTHESIS: The shared body-transform engine applies exactly three line-level transforms — structural
  load directives, the slash-command rewrite, and registered tool-idiom rewrites — all data-driven from
  each target's `mapping.json`, and none of them can vary emphasis or verification scaffolding —
  confirm/refute at `marketplace/targets/body_transform_engine.py` (verify-at-outline). Carried from
  absorbed inbox message `truthful-signals-009`, which measured it at `77cb2e251`; **not** re-measured
  in this session, so it is a lead and not a fact.
- HYPOTHESIS: Component-level `targets:` scoping is all-or-nothing and is used by 6 components, every
  one of them `targets: [claude]` — confirm/refute at
  `marketplace/bundles/pm-plugin-development/skills/plugin-architecture/references/frontmatter-standards.md`
  and by a derived sweep of the bundle tree (verify-at-outline). Same provenance and same caveat as
  above. ⛔ The count must be **re-derived**, not quoted from this spec.
- HYPOTHESIS: A third runtime target for the Gemini models is in development, present but untracked,
  and imports the same vocabulary-only transform engine — confirm/refute at `marketplace/targets/`
  (verify-at-outline). ⚠ Uncommitted in-flight work: treat every detail as a snapshot, never as
  contract, and re-check its state at outline rather than scoping on this sentence.
- OBSERVED: The variance axis is **model**, not target, because one target hosts several models —
  recorded in absorbed inbox message `truthful-signals-009`, whose reasoning is reproduced here: a
  per-target mechanism cannot distinguish two models behind the same target, so any design keying on
  target is insufficient by construction.
- Verify-first clause: ⛔ Do **not** assert that smaller or flash-tier models need scaffolding that
  stronger models do not. It is the intuitive hypothesis, no evidence for it was gathered about any
  model in the fleet, and asserting it would be exactly the confident-signal-without-provenance defect
  this epic's sibling was created to catch. It is sufficient to *gate* the question and insufficient to
  *design against*.

## Expected Surface

- OBSERVED: `doc/adr/` — the ADR this plan writes
- HYPOTHESIS: `doc/developer/marketplace-build.adoc` — updated only if the decision changes what that
  document states about target scoping (verify-at-outline)

⚠ **Read-only, deliberately NOT declared above**: `marketplace/targets/` (read to derive the
generator's expressive limit and the in-flight third target's state) and `marketplace/bundles/` (swept
to derive the `targets:` usage count). ⭐ **This plan writes an ADR and nothing else** — declaring the
two trees it reads would serialize the whole epic behind a decision plan that modifies no code, which
is exactly the over-declaration the section's authoring rule warns about.

## Dependencies and Sequencing

- Depends on: none. This is the time-sensitive row and should be emitted early regardless of queue
  position.
- Overlaps with: PLAN-04, which depends on this plan's decision but declares a different surface.
- Adjacent to: the in-flight third-target work. ⚠ **This plan does not gate that work and must not be
  read as holding it.** It reads that tree; it does not modify it.

## Non-Goals

⛔ No axis is implemented here and no generator code is modified. ⛔ No instruction prose is edited.
⛔ No upstream project's configuration schema is adopted as the answer — if an axis is chosen, its
shape is designed against this repository's own target architecture.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/next-level/plans/PLAN-03-calibration-axis-decision.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
