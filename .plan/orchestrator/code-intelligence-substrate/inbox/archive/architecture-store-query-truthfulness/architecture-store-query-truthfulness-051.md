envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:57:35Z

component=plan-marshall:manage-architecture
category=anti-pattern

# The test already held the authoritative table and keyed into it from a hardcoded tuple

Source: PR #1489 CodeRabbit inline finding dd41ad (resolution=fixed, TASK-040).

test_capabilities.py:252 hardcoded the capability names the test validates. If
client-api.md adds a fourth entry and the runtime omits it, the test never inspects that
entry and stays green.

What makes this the cheap case rather than the registry-requiring one: the test ALREADY
parses the authoritative capabilities table in client-api.md row by row via a per-entry
regex. It holds the source and merely keys into it from a literal.

## Solution

Parse the entry rows out of the table to form the population, keep the existing
per-entry assertions unchanged, and add a non-vacuity guard so a table the parse failed
to read cannot present as a clean pass.

The discriminator worth carrying: "derive the population from its source" is a cheap fix
exactly when the source is already reachable at the assertion site, and a scope expansion
only when it would require building a registry that does not exist.

## Impact

Paired with the SKIP_* vocabulary finding in the same review; both share this shape.
