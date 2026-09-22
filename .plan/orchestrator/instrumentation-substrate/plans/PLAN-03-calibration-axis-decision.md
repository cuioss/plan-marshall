# PLAN-03: Calibration-axis decision

epic: instrumentation-substrate
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
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: marketplace/targets/__init__.py TARGET_REGISTRY confirmed; CLAUDE.md only-Claude-tested sentence corroborated
- HYPOTHESIS: The shared body-transform engine applies exactly three line-level transforms — structural
  load directives, the slash-command rewrite, and registered tool-idiom rewrites — all data-driven from
  each target's `mapping.json`, and none of them can vary emphasis or verification scaffolding —
  confirm/refute at `marketplace/targets/body_transform_engine.py` (verify-at-outline). Carried from
  absorbed inbox message `truthful-signals-009`, which measured it at `77cb2e251`; **not** re-measured
  in this session, so it is a lead and not a fact.
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: body_transform_engine.py docstring: exactly 3 mapping.json-driven transforms, none touching emphasis/scaffolding; Transform 1 now covers 2 directives (widened, count unchanged)
- ⛔ **REFUTED at cleanup 2026-09-22 (was HYPOTHESIS).** Component-level `targets:` scoping is NOT
  all-or-nothing, and the count is NOT 6. `marketplace/targets/component_targets.py` module docstring:
  "A single `*.md` file *inside* a skill MAY also declare a `targets:` field that governs only itself …
  A file's declaration may only NARROW its parent skill's scope" — a file-level narrowing tier exists
  beneath the component-level switch. A re-derived sweep for `^targets:` finds 6 file hits, but one —
  `plugin-architecture/references/frontmatter-standards.md` — carries NO frontmatter at all (the hit is
  prose, not a declaration); the 5 real declarations are 1 command, 1 skill manifest, and 3 skill-
  internal reference files, all `[claude]`. **Consequence, absorbed into this spec's scope**:
  deliverable 2's "count and listing" must report the two-tier mechanism (component-level switch +
  file-level narrowing) and the corrected 5-declaration count, not the flat 6-component reading.
  - verdict: contradicted | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: yes | evidence: component_targets.py: file-level narrowing tier exists (not all-or-nothing); re-derived sweep finds 5 real declarations not 6 (one hit is prose, no frontmatter); deliverable 2 corrected
- ⛔ **REFUTED at cleanup 2026-09-22 (was HYPOTHESIS), on "untracked" only.** A third runtime target for
  the Gemini models is in development and imports the same vocabulary-only transform engine — that half
  holds. But it is NOT "present but untracked": `git ls-files marketplace/targets/antigravity` returns 9
  tracked files (emitter, frontmatter, mapping, target, variant_emitter, templates), it is registered in
  `TARGET_REGISTRY` (`marketplace/targets/__init__.py`), tested
  (`test/marketplace/targets/antigravity/test_body_transforms.py`), and documented
  (`doc/developer/antigravity.adoc`). **Consequence, absorbed into this spec's scope**: this is now
  shipped contract, not uncommitted snapshot — the cost-of-retrofitting argument in the Objective has
  already advanced one notch since this spec was staged, which makes deliverable 5's SkCC read and the
  decision itself MORE time-sensitive, not less.
  - verdict: contradicted | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: yes | evidence: antigravity target is tracked (9 files), registered in TARGET_REGISTRY, tested, and documented — not uncommitted; Objective's time-sensitivity argument strengthened accordingly
- OBSERVED: The variance axis is **model**, not target, because one target hosts several models —
  recorded in absorbed inbox message `truthful-signals-009`, whose reasoning is reproduced here: a
  per-target mechanism cannot distinguish two models behind the same target, so any design keying on
  target is insufficient by construction. ⚠ **Downgraded at cleanup 2026-09-22**: the cited
  `truthful-signals-009` is no longer reachable in this epic's tracked inbox at HEAD (only
  `inbox/archive/next-level/next-level-001..010.md` and `inbox/truthful-signals-001.md` remain; a
  same-named file elsewhere in the repo belongs to `code-intelligence-substrate` and is unrelated). The
  reasoning stands as **spec-internal reasoning**, not an externally-corroborated finding, until a
  reachable source is re-attached.
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: instrumentation-substrate/cleanup | rescoped: n/a | evidence: cited truthful-signals-009 not reachable in this epic's tracked inbox at HEAD; same-named file belongs to code-intelligence-substrate; downgraded to spec-internal reasoning in spec text
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
/plan-marshall task="implement .plan/orchestrator/instrumentation-substrate/plans/PLAN-03-calibration-axis-decision.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
