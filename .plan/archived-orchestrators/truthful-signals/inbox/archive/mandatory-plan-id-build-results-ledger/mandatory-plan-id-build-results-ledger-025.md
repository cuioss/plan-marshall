envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T07:20:56Z

component=plan-marshall:phase-6-finalize
category=improvement
title=A reviewer's claims are fallible in BOTH directions and each must be verified before disposition
forward_to=review-apparatus

# Reviewer claims are fallible in both directions

**CROSS-EPIC — belongs to `review-apparatus`.** Filed here for forwarding; do not action
locally.

## The evidence, from one review

CodeRabbit's post-merge review of PR #1075 (2026-08-02T06:28:09Z) produced 14 items. Two were
verified in depth by this audit, and they land on opposite sides:

**Right, and materially so** — `_cmd_cleanup.py:356`:

> `get_build_results_dir(plan_dir.name)` can raise `ValueError`... **Unlike this same call
> path's own docstring, which says production callers are protected by an upstream
> `validate_plan_id`, this call site iterates real on-disk directories directly and has no such
> upstream guard.**

Verified by reading both sites and by enumerating all three call sites. It is a MAJOR live
regression, and the reviewer's reasoning is *better* than the docstring's — it noticed that the
safety argument was scoped to a caller population this call site is not in.

**Wrong** — `test_manage_change_ledger.py:363`:

> `_ledger_core.py` **has no future annotations import**, and this project targets Python
> `>=3.12`; `inspect.signature().parameters['plan_id'].annotation` returns `<class 'str'>`, so
> the `annotation == 'str'` assertion will fail.

`_ledger_core.py:36` is `from __future__ import annotations`. The annotation *is* the string
`'str'`, the assertion is sound, and the comment must not be actioned. Notably CodeRabbit
**ran a verification script** for this one (`fd -a '_ledger_core.py' | xargs -I{} head -n 10 {}`)
— and `head -n 10` truncated 26 lines before the import it was looking for. The bot verified,
and its verification method was the thing that was wrong.

## The generalisation

The existing rule in this project is *"a reviewer's list of call sites is a SAMPLE, not an
enumeration"* — a claim about **completeness**. This adds the orthogonal axis: an individual
reviewer claim is also fallible on **correctness**, and in both polarities:

| | Reviewer says defect | Reviewer says clean |
|---|---|---|
| **Truth: defect** | `_cmd_cleanup` — act on it | PR-Agent's *"No security concerns identified"*, on the same commit where the internal security audit found an unconstrained `plan_id` reaching a path join |
| **Truth: clean** | `_ledger_core` — do NOT act | (unremarkable) |

Three of the four cells were populated by a single PR. Accepting a finding because a bot filed
it, and accepting a clean bill because a bot issued it, are the same error.

## Do this instead

- **Verify each claim against the source before dispositioning it**, including the ones you
  intend to accept. The cost is one `Read`; the cost of not doing it is either a wrong fix or a
  missed one.
- **Distrust a bot's own verification transcript** as much as its conclusion. CodeRabbit showed
  its work here and the work contained the bug (`head -n 10` over a 36-line preamble). A
  displayed script is evidence about *what was checked*, not that the check was adequate.
- **A clean bill is a claim too.** "No security concerns identified" on a commit that contains a
  path-join hardening is a falsifiable statement, and on this PR it was false. Record
  content-free clean bills as *absence of coverage*, never as coverage.
- When triaging a batch, record per-claim `verified: confirmed | refuted | not_checked`. This
  audit's untracked-findings table does exactly that, and the one REFUTED row is the reason the
  table is worth more than the list.
