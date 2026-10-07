envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:45:44Z

component=plan-marshall:phase-3-outline
category=bug

# A deliverable specified an edit that its own named verification command mechanically rejects

Deliverable 5 specified exactly one edit — change `lane.class` from `core` to `prunable` in `lessons-capture.md` — and named as its verification command the plugin-doctor quality gate over that directory. That gate **rejects that exact edit**: `_analyze_lane_frontmatter.py` appends `class: prunable requires a prunable_when predicate id` when `prunable_when` is absent, under `RULE_ID lane-frontmatter-invalid`, severity error, build-failing.

The deliverable was self-contradictory as written, and it was decidable at outline time by reading the validator the deliverable itself pointed at.

## Evidence

- `703895` (3-outline) — the finding, with the validator line numbers and the normative requirement in `ext-point-lane-element.md`. It also names the sibling evidence: `plan-retrospective/SKILL.md` and `adr-propose.md` both already declare `class: prunable` WITH a `prunable_when`.
- `6349d9` (3-outline) — the same deliverable's class-choice **rationale was refuted**: it justified `prunable` over `adversarial` on the ground the two are "behaviourally identical here", while the central standard's resolution lattice gives `prunable` a third, predicate-driven drop route `adversarial` does not have. The deliverable's own success criteria required stating "both consequences" — there were three.

## Rule

Two cheap checks, both available before any code is written:

1. **When a deliverable names a verification command, run that command's rule against the specified change.** A validator's source is the authority on whether an edit passes it; a deliverable that cannot satisfy its own gate is a plan defect, not an execution surprise.
2. **An equivalence claim between two enum values is a claim about the resolution lattice.** Read the lattice. `6349d9`'s resolution is the model — it replaced the refuted "behaviourally identical" argument with an argument from MEANING, and then verified the third consequence's implementation status by reading the whole resolution path (`_apply_lane_resolution`, `_lane_keep_decision`, `_effective_lane_tier`, `_lane_override_for`) to establish that predicate-driven skip is contract-live but composer-dormant.
