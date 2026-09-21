envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:56:28Z

component=plan-marshall:tools-script-executor
category=bug

# A wholly corrupt previous executor was indistinguishable from one that carried no surfaces

Source: PR #1489 CodeRabbit inline finding 34704f (resolution=fixed, TASK-036).

The closing comprehension silently removed every wrong-shaped entry and still returned
outcome='read'. If ALL entries are invalid and the new generation emits zero surfaces,
BOTH fail-open guards pass and the generator replaces the executor with one that has no
pre-spawn validation.

That is precisely the discrimination this function's own docstring promises when it says
an unreadable previous cannot be cited as proof that no surfaces are being stripped.

## Solution

Reject the WHOLE map as 'unreadable' when any key or value has the wrong shape, with a
detail naming the offending entries.

The rule: a filtering comprehension that drops malformed input is a silent data loss
wearing the shape of a cleanup. When the consumer's decision depends on whether the
input was READABLE, the filter must not answer "read" over a set it pruned.

## Impact

The failure mode disables a security-relevant pre-spawn validation while every guard
reports green.
