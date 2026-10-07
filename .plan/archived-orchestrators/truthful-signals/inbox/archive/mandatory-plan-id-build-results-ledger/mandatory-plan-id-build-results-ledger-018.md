envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T07:20:15Z

component=plan-marshall:script-shared
category=bug
title=A presence guard on a never-empty field must become a meaning guard AT THE DECODE BOUNDARY

# A presence guard on a never-empty field must become a meaning guard at the decode boundary

**Status: LIVE IN MAIN.** The plan that authored ADR-015 shipped its counterexample in the
same commit.

## The defect

PR #1075 (`PLAN-TRUTH-026`) made `plan_id` never-null across the build-class dispatch
boundary and authored **ADR-015 — "An absent identity is a stated sentinel value and every
presence guard becomes a meaning guard."**

`script-shared/scripts/build/_build_server_protocol.py` carries:

```python
_JOB_SPEC_REQUIRED = ('command', 'exec_path', 'project_path', 'plan_id')
```

and `JobSpec.from_dict` does:

```python
missing = [key for key in _JOB_SPEC_REQUIRED if key not in data]   # presence only
if missing:
    raise ValueError(...)
command = data['command']
if not isinstance(command, list) or not all(isinstance(t, str) for t in command):
    raise ValueError('job spec command must be a list of strings')   # meaning guard — for command
return cls(
    ...
    plan_id=str(data['plan_id']),        # <-- '' passes; None becomes the string 'None'
)
```

`command` gets a **meaning** guard. `plan_id` gets only a **presence** guard and then
`str()` coercion. So `''` survives, and `None` is silently converted to the four-character
string `'None'` — a value that is truthy, passes `names_real_plan()`'s sentinel comparison,
and would be recorded as a plan id.

The class docstring states the contract and justifies it by the caller:

> `plan_id`: The submitting plan id — the `NO_PLAN` sentinel for a plan-less build
> (**the client resolves it before constructing the spec, so the wire value is never the
> empty string**).

This is the **same failure shape** as the sibling `get_build_results_dir` regression: a
contract asserted in a docstring, justified by an assumption about who calls it, with no
mechanism at the boundary. Here it is worse in one respect — `from_dict` is a **socket
decode path**. Its input is by definition not the in-process client value the docstring
reasons about; it is whatever arrived over the wire.

## Why this matters beyond one field

The whole point of PR #1075 was to make an absent identity a *stated* value so the
`kind=build` ledger row could be never-null and every row attributable. A wire boundary that
accepts `''` and manufactures `'None'` re-opens exactly the ambiguity the plan closed — and
re-opens it at the one place where the value is least trustworthy.

`_JOB_SPEC_REQUIRED` is literally a presence guard. ADR-015 says every presence guard becomes
a meaning guard. The ADR and its violation are in the same diff.

## Do this instead

- When a plan promotes a field to never-null, the sweep must include every **decode /
  deserialize / `from_dict` / wire-ingress** site for that field, not just the producers.
  Producers were swept on this plan (`_record_job` / `_latest_job_id_for_plan` were found as a
  pair); the ingress boundary was not.
- A `_REQUIRED = (...)` presence tuple next to a field with a stated value contract is a
  **detector target**: presence-checked but not meaning-checked is a mechanically findable
  shape.
- Reject at the boundary rather than coercing. `str(data[k])` on an untrusted wire value is
  never a validation; it is a way of guaranteeing the field is a string while saying nothing
  about whether it means anything.

## Proposed fix (from CodeRabbit, verified sound by the audit)

```python
plan_id = data['plan_id']
if not isinstance(plan_id, str) or not plan_id:
    raise ValueError('job spec plan_id must be a non-empty string')
```

This needs a plan spec rather than a lesson-corpus lift: it is a live contract hole in a
shipped deliverable, not a behavioural pattern to remember.
