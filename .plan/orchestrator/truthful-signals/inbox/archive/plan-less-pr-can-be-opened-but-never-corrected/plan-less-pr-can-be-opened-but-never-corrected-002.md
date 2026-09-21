envelope_version=1
sender_type=plan
sender_id=plan-less-pr-can-be-opened-but-never-corrected
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T12:04:38Z

component=plan-marshall:manage-run-config
category=anti-pattern
bundle=plan-marshall

# A parity test that hand-reconstructs the production path can never fail on production drift

## Observation

`test/plan-marshall/manage-run-config/test_cleanup.py` asserted that the cleanup surface
retains sentinel bodies under the right directory. The assertion compared against a
**hand-reconstructed literal** — the test rebuilt the expected path from its own string
parts — rather than against `ci_base.get_body_path()`, the production accessor that decides
the real layout.

The test passed. It would have kept passing after any production layout change, because the
only thing it compared was its own literal against itself. The signal was green and carried
no information about the property it claimed to check.

Caught in PR #1065 by CodeRabbit, remediated as TASK-015.

## Why this is the epic's theme

This is confident-signal-hides-a-caveat in its purest test form: a *parity* test that does
not consult the production side of the parity. The name of the test ("parity") is precisely
the claim it fails to make.

## Corrective rule

**When a test asserts that two sides agree, exactly one side may be a literal.** The other
side MUST come from the production accessor / constant / resolver that owns the value. If
both sides are literals, the test is an identity assertion wearing a parity test's name.

Detection heuristic for review: read the assertion and ask "which production symbol is
evaluated here?" If the answer is "none", the test cannot fail for the reason it exists.

## Generalization

The same shape recurs whenever a test mirrors a production layout, schema, enum, or default:
- expected path rebuilt from string parts instead of calling the path accessor
- expected default re-typed instead of read from the defaults module
- expected enum members re-listed instead of read from the enum

Every one of these is a test that pins the *test's* belief, not the *production* behaviour.
