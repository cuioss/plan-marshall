envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:48:20Z

component=plan-marshall:marshall-steward
category=bug

# The same plan stated a caution in one document and reintroduced exactly that misreading at the operator surface in two others

`manage-execution-manifest/SKILL.md:279` states the caution explicitly: a `lane_report` row with `declared: '-'` and `binds: false` "is the accurate statement that no stored setting is in force for it, **not a claim that one was ignored**."

The same plan then added, to two operator-facing documents, a render instruction producing precisely that claim: display each row as `{step}: asked for {declared}, running at {effective}`. Because `lane_report` emits `declared: '-'` for every step with no stored declaration — and most candidates have none — the wizard renders long runs of `{step}: asked for -, running at minimal`, asserting a request nobody made.

## Evidence

Two findings, filed as a 2-member cohort, both 6-finalize, both `fixed`:

- `436d49` — `menu-configuration.md:469-472`
- `bc2ce5` — `wizard-flow.md:580-583`, "carries the identical render instruction"

`436d49`'s detail names the contradiction directly: "The same plan therefore states the caution in one doc and reintroduces it at the operator surface in another."

## Two distinct rules

**1. A caution written in a reference document does not propagate to the surfaces that could violate it.** When a document records "do not read X as Y", the change that records it should also sweep for renderers, messages, and templates that produce the Y reading. The caution and its violations were added in the same plan — the author knew the rule at the moment of breaking it, in a different file.

**2. Duplicated blocks are filed and fixed per site, deliberately.** `bc2ce5` records why it was filed separately rather than folded into `436d49`: "the two docs are edited independently and a fix applied to one would leave the other stating the superseded form." That is the correct handling of a cohort — one finding per site, each independently resolvable — and it is worth keeping as the pattern, because the alternative (one finding, two sites) is how half-applied fixes happen.

## The underlying design question

The deeper fix is at the producer: `'-'` is a sentinel doing double duty as both "no declaration" and a displayable value. A renderer that must branch on a sentinel to avoid asserting something false is a sign the value should carry its own absence marker — which is exactly what the sibling `binds: false` field already does, and which the render instruction ignored.
