envelope_version=1
sender_type=plan
sender_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
kind=candidate-lesson
created=2026-09-14T19:21:31Z

component=plan-marshall:manage-findings
category=anti-pattern
source_signal=script_failure_cluster
source_plan=pr-065-settings-repo-accumulates-never-lands
evidence=work-log ERROR d556e7 (2026-09-13T18:58:42Z), 601248 (2026-09-13T21:38:55Z, 2026-09-14T07:20:48Z)

# manage-findings rejected three times: an undeclared flag on `list`, then `qgate add` without its required flags

Three `exit_code=2 failure_kind=argparse_rejection` calls against
`plan-marshall:manage-findings:manage-findings` in one run, in two distinct shapes:

1. `list` invoked with a flag outside its declared set. The executor printed the
   accepted set verbatim: `['any-checkout', 'author', 'bot-kind', 'file-pattern',
   'include-qgate', 'kind', 'plan-id', 'preference-admissible', 'promoted',
   'resolution', 'type']`.
2. `qgate add` invoked without one or more of its required flags
   (`--plan-id`, `--phase`, `--source`, `--type`, `--title`, `--detail`). This one
   recurred ~10 hours apart, in two different dispatched envelopes
   (21:38 and 07:20), with the identical usage block echoed back both times.

## Why it matters to this epic

The second shape is a *recurrence across envelopes*: the executor already printed
the full required-flag list at 21:38, and the same call shape was reconstructed
from workflow prose at 07:20 by a later envelope that never saw that output. A
per-envelope rejection message is not a durable correction — nothing carries the
rejection forward to the next envelope that writes the same call.

## Candidate rule

Before composing a `manage-findings qgate add`, quote the required flag set from
the script's own `--help` (or the executor's echoed usage block) rather than from
the surrounding workflow prose. Signature 5 in
`persona-plan-marshall-agent/standards/agent-behavior-rules.md` already names the
missing-`--phase` half of this; the `qgate add` required-flag set is the same
class and is not enumerated anywhere the authoring agent reads.
