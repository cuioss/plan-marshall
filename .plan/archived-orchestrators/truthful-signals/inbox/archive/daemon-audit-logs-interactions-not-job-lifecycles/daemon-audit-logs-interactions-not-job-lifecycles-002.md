envelope_version=1
sender_type=plan
sender_id=daemon-audit-logs-interactions-not-job-lifecycles
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T15:46:55Z

component=plan-marshall:tools-integration-ci
category=bug
bundle=plan-marshall

# check_auth_cli reports "Not authenticated" for every non-zero exit, including a missing binary

## What was observed

`automatic-review` returned `provider_unconfigured` with
`"Not authenticated. Run 'gh auth login' first."` while `gh` was in fact fully
authenticated — it was simply not on `PATH` for that invocation. The remediation the
message prescribes (`gh auth login`) could not have fixed the actual fault.

## Root cause (verified in code)

Two layers disagree, and the lower one's distinction is thrown away by the upper one.

`ci_base.py::run_cli` already classifies the failure correctly:

```python
except FileNotFoundError:
    msg = not_found_msg or f'{cli_name} CLI not found'
    return 127, '', msg
except subprocess.TimeoutExpired:
    return 124, '', 'Command timed out'
except Exception as e:
    return 1, '', str(e)
```

`ci_base.py::check_auth_cli` (line ~738) then collapses all of it:

```python
returncode, _, _ = run_fn(['auth', 'status'])
if returncode != 0:
    return False, login_message
return True, ''
```

It discards both the returncode distinction and the stderr the lower layer computed.
`127` (binary absent), `124` (timeout), and a genuine auth failure all render as the
one `login_message` supplied by the caller
(`github_ops.py:139` / `gitlab_ops.py:126`).

## Why it matters to this epic

This is the epic's archetype in its purest tool-layer form: a **confident signal naming
the wrong cause**. The message is unhedged and prescriptive, and it is wrong in a way
the calling code already had the information to avoid. It is strictly worse than a
vague error, because it sends the operator down a remediation path that cannot succeed.

## Proposed rule

When a lower layer has already discriminated a failure class, a higher layer MUST NOT
funnel every class into one user-facing message. `check_auth_cli` should branch on the
returncode it already receives — `127` → "gh CLI not found on PATH", `124` → "gh auth
status timed out", other non-zero → the login message — and should surface the stderr
`run_cli` computed rather than discarding it.

## Suggested scope

Tool-layer fix in a surface we own (`ci_base.py::check_auth_cli`), shared by both the
GitHub and GitLab providers, so one change corrects both. A regression test should
assert the three returncodes map to three distinct messages, driven from the
`run_cli` returncode contract rather than from hand-written constants.
