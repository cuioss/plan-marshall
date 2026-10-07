envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=candidate-lesson
created=2026-09-02T20:14:32Z

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, plan `coverage-gate-visibility` (PR #681), original message `coverage-gate-visibility-001.md`.
> Filed there as a candidate-lesson and refused by `manage-lessons add` with `wrong_store`: the component names a `plan-marshall` bundle that the Token-Sheriff store does not own. Content is unmodified below.

component=plan-marshall:automatic-review
category=bug
source_plan=coverage-gate-visibility
source_epic=deployment-and-refresh-gaps

# The executor's empty-string stripping is only safe for flags declaring nargs='?' — a scalar flag becomes a bare flag and argparse rejects it

## Observation

`review_completeness check --measured-diff-size ""` exits 2 (`expected one argument`).

The plan-marshall script executor strips empty-string arguments from the argv it
constructs. For the six bot-observation list flags that is harmless, because each
of them declares `nargs='?', const=''` — so the stripped, now-bare flag still
parses and reads as the empty list. `automatic-review/scripts/review_completeness.py`
lines 1573-1660 (`_add_bot_observation_flags`):

```python
sub.add_argument('--required-bots',      nargs='?', const='', default='')
sub.add_argument('--optional-bots',      nargs='?', const='', default='')
sub.add_argument('--participated-bots',  nargs='?', const='', default='')
sub.add_argument('--in-progress-bots',   nargs='?', const='', default='')
sub.add_argument('--refused-bots',       nargs='?', const='', default='')
```

`--measured-diff-size` is declared on the `check` subparser alone, and it is a
SCALAR with no `nargs='?'` and no `const` (same file, lines 1787-1801):

```python
check_parser.add_argument('--measured-diff-size', default='', help=...)
```

Same stripping, opposite outcome: the flag is left bare, argparse demands its one
value, and the call is rejected before the script body runs.

## Why a caller following the docs hits this

`phase-6-finalize/standards/branch-cleanup.md` § Predicate 2 explains at length
that the executor strips empty-string args so passing a bare flag is safe. Its
safe-when-empty reasoning is correct — but it is derived by enumerating the LIST
flags, and it never carves out the scalar that shares the same subcommand. A
caller who reads that passage and applies it uniformly to every flag on
`review_completeness check` produces the rejection.

The flag's own help string already states the remedy ("Omit it (the default) when
unmeasured — reported as unknown, never as zero"), so the fix and the trap live
one screen apart and neither points at the other.

## Remedy

Omit `--measured-diff-size` entirely when the value is empty. Never pass it as
`--measured-diff-size ""`.

## Generalizable rule

Empty-string stripping is safe for a flag **iff that flag declares `nargs='?'`
with a `const`**. Any narrative that says "a bare flag is fine here" must scope
itself to the flags whose declaration actually supports it, and must name the
scalars on the same subcommand that it does NOT cover. Absent that carve-out, the
prose is an accurate description of a subset presented as a property of the
command.

Candidate doc fix: add the scalar carve-out to `branch-cleanup.md` § Predicate 2,
naming `--measured-diff-size` and the omit-when-empty remedy.

## Adjacent observation from the same run

The executor's own unknown-notation diagnostic mis-routes this script. Invoking
`plan-marshall:phase-6-finalize:review_completeness` returns:

```
Correct format: plan-marshall:phase-6-finalize:ci_complete_precondition review_completeness
```

That suggestion is wrong — `ci_complete_precondition` declares only the `resolve`
subcommand, so following the suggestion produces a second argparse rejection. The
script actually lives at `plan-marshall:automatic-review:review_completeness`.
The executor infers "third segment must be a subcommand of some script in this
skill" without checking that the named script accepts it, so a wrong-bundle
notation is answered with a confidently-worded wrong correction.
