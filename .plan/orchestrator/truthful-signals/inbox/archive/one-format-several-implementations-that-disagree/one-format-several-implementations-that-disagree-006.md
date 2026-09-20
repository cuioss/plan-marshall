envelope_version=1
sender_type=plan
sender_id=one-format-several-implementations-that-disagree
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T19:18:58Z

category=anti-pattern
component=plan-marshall:tools-script-executor
title=Invocation drift is measurable, and this run measured six clusters of it

## Signal

`script_failure_clusters` = 8 distinct failing notations. Two are filed separately
as their own defects (the build-server notation split; the `--measured-diff-size`
empty-value divergence). The remaining six are **caller drift** — the assistant
guessing an argument surface instead of reading it:

| Notation | Subtype | Occurrences |
|---|---|---|
| `manage-logging` `read` | argparse rejection | 3 |
| `tools-integration-ci:ci` | argparse rejection | 2 |
| `manage-findings` `list` | argparse rejection | 2 |
| `plan-retrospective:analyze-logs` | **invented subcommand** | 1 |
| `manage-status` `transition` | script_internal_error | 1 |

12 total failures, 8 unique. Concretely: `architecture search --path-glob` (not a
flag), `ci checks wait` without `--pr-number`, `manage-findings list --status`
(the flag is `--resolution`), `manage-findings list --kind pr-comment` (the
`--kind` vocabulary is `inline|review_body|issue_comment`; the value belongs to
`--type`), and `analyze-logs --plan-id …` where the first positional must be `run`.

## Why this is worth recording rather than shrugging off

Every one of these was **cheap to prevent and cheaper to detect than to guess**.
The executor already rejects with a complete accept-set:

```text
reason: unknown_flag
rejected: --path-glob
accepted: category, content, ignore-case, literal, pattern, plan-id, pre, project-dir
```

That rejection is a better reference than any document, and it costs one call. The
drift is therefore not a knowledge gap in the tooling — it is a habit of guessing
first. The project's own hard rule already names it ("Never improvise script
subcommands"; "Before invoking any `ci` leaf subcommand whose exact flags you do
not already know, Read the leaf-command-reference").

The `analyze-logs` case is the sharpest: `--plan-id` was passed as the first
positional, which argparse read as the *subcommand*, producing
`invalid choice: 'one-format-...'`. A verb surface with exactly one subcommand
(`run`) is precisely where a caller assumes there is none.

## How to apply

Two habits, in priority order:

1. **When a notation's surface is not already known, call `--help` first.** One
   call, and it returns the authoritative accept-set rather than a guess.
2. **Read a rejection's `accepted:` list as the answer, not as an error.** Several
   of the 12 failures above are second attempts that changed the wrong thing —
   the accept-set naming the right flag was already on screen.

Neither is new policy. The value of this record is the *measurement*: 12 failures
in one plan, all self-inflicted, all one `--help` away.
