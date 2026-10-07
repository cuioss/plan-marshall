envelope_version=1
sender_type=plan
sender_id=marketplace-dependency-resolver
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T19:15:36Z

component=plan-marshall:finalize-step-plugin-doctor
category=anti-pattern
title=A documented command template that the project's own enforcement hook rejects is un-emittable, and nothing checks emittability

# A documented command template that the project's own enforcement hook rejects is un-emittable, and nothing checks emittability

## What happened

The plugin-doctor wrapper `SKILL.md` Step 5 WARNING template contains a **literal
semicolon** inside the command it tells the agent to emit. The project's
one-command-per-Bash enforcement hook rejects any Bash call containing `;`. The
documented command therefore cannot be issued as written — by anyone, ever.

## The generalisable shape

This is the second distinct mechanism by which a documented command can be
structurally un-executable, and it is worth separating from the ordinary
doc-contract divergence:

| Mechanism | Rejecting party | Visible to |
|-----------|-----------------|------------|
| Argparse rejection | the consuming script | a test that runs the documented invocation |
| **Policy-hook rejection** | the project's own hard-rule hook | **nothing currently** |

The second row is the gap. A script-level rejection is at least discoverable by
executing the command. A hook-level rejection is not even reachable from a unit
test, because the hook lives in the agent harness, not in the script. So the
template can sit in a shipped skill indefinitely while every agent that reaches
Step 5 silently improvises around it — and an improvised substitute is exactly the
"workflow steps: no improvisation" violation the hard rules exist to prevent.

**The hook does not just forbid the agent from running the command. It forbids the
skill from having documented it.** The project's Bash hard rules are a constraint on
authored command templates, not only on runtime behaviour.

## Corrective rule

Every `bash`-fenced command template in a skill or workflow doc MUST itself satisfy
the project's Bash hard rules:

- exactly one command — no `;`, no `&&`, no `&`, no embedded newline joining two
  commands,
- no `$(...)` substitution, no loops, no subshells,
- no `VAR=val cmd` inline env-var dispatch.

This is mechanically checkable over the corpus: the population is "fenced blocks
tagged `bash` inside `marketplace/bundles/**/*.md`", and the predicate is the same
one the hook already implements. A structural lint rule in `plugin-doctor` closes
the gap permanently, and reusing the hook's own predicate keeps the lint and the
hook from drifting apart.

## Note on the message text this bit

The same constraint applies to `manage-logging` message payloads: a `--message`
string containing a literal `;` trips the one-command hook. Any doc that prescribes
a log line must keep the message body free of `;` as well.
