envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:47:40Z

component=plan-marshall:manage-execution-manifest
category=anti-pattern

# A monkeypatch kept a test green while the same PR inverted the production fact the fixture stood for

A test fixture used `default:lessons-capture` as its stand-in for an **immune `core` floor element** and asserted that an `off` request against it is neutralized. The same pull request reclassified `lessons-capture` from `core` to `prunable` — a non-immune class whose `off` BINDS.

The test kept passing. It passes because `_resolve_element_lane` is monkeypatched, so the fixture's abstract class label never meets the frontmatter that contradicts it. The mock insulated the test from the exact change under review.

## Evidence

CodeRabbit inline comment on PR #1541, finding `d3eb20` (`test_step_params.py:485`), resolved `fixed`:

> "This fixture uses `lessons-capture` as an abstract `core` floor element, but the test seeds that same step and asserts its `off` request is neutralized. Production declares `lessons-capture` as `prunable`, so the snapshot test does not represent its production behavior."

The accepted remedy is the instructive part — it is not "update the label":

- use a genuinely immune element (`push` / `archive-plan`) for the neutralized-`off` case, and
- **keep `lessons-capture` as a negative control whose `off` request binds and removes the step.**

One fixture change yields a matched positive/negative control pair across the very boundary the PR moved.

## Rule

When a test monkeypatches the resolver that would otherwise read a production declaration, the fixture's stand-in value becomes an **unchecked claim about production**. Two obligations follow:

1. A change that moves a production classification must sweep the fixtures that name that element as an exemplar of the OLD classification. A green test is not evidence here — it is the symptom.
2. Prefer deriving the exemplar from the live resolver, or pin it with a matched control on the other side of the boundary, so an inversion breaks something.

The generalisation: a mocked boundary converts every constant on the mock's far side into an assertion nothing verifies. The more faithfully the fixture NAMES real production entities, the more convincing — and the more silently wrong — it becomes when production moves.

## Why it matters here

This is the sharpest instance available of the archetype, because the PR that invalidated the fixture is the PR that contained it. It was caught by an external review bot, not by the suite, not by the self-review, and not by the plan.
