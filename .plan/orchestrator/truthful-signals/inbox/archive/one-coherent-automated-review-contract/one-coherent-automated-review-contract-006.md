envelope_version=1
sender_type=plan
sender_id=one-coherent-automated-review-contract
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T21:06:03Z

component=plan-marshall:manage-locks
category=bug
bundle=plan-marshall

# An early-return branch that omits fields the doc declares unconditionally is a doc-contract divergence, not a style nit

## Observation

PR #1041 (PLAN-92), finding `1a69d5`, raised by pr-agent and fixed in-run at `b9692bebe`.

`_run_rate_window_check` returned two differently-shaped dictionaries. The claimed-window branch
returned `expires_at`, `seconds_remaining`, and `expired`; the `record is None`
(unclaimed-window) early-return branch omitted all three. `manage-locks/SKILL.md` documented the
field list as **unconditional**. A consumer reading `result['expired']` or
`result['seconds_remaining']` on an unclaimed window would hit a `KeyError`, or the TOON output
would simply be missing the field — precisely the case a caller checking "is the window free?"
takes most often.

The fix added the three keys to the `record is None` branch (`expired: True`,
`seconds_remaining: 0.0`) and added a regression asserting **field-set parity between the two
branches**.

## Do this instead

- When a function's documented output contract declares a field list unconditionally, **every**
  return branch must satisfy it — including the early-return / empty / not-found branch, which is
  the one most likely to be written first and reviewed least.
- Assert this structurally: a **field-set-parity test** across the function's return branches,
  not a per-field spot-check on the happy path. A spot-check on the populated branch passes while
  the omission survives.
- The empty/None branch is the highest-risk site for this class precisely because its return
  literal is written by hand rather than derived from the populated shape.

## Recurrence context

Instance of the recurring **doc-contract-divergence** archetype: the documentation states an
invariant the code satisfies on only some paths. It is also a **slipped-then-caught** defect
inside the plan's own delivered surface — the only reason it was caught is that pr-agent
reviewed. On this PR the other two bots refused, so a single reviewer was the entire barrier
between this and merged main.
