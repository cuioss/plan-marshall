envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:04:27Z

component=plan-marshall:tools-integration-ci
category=anti-pattern
bundle=plan-marshall

# Script-failure cluster 2 of 4: ci pr prepare-body rejected twice — undeclared flag, then a MISSING required --plan-id

Two consecutive rejections on the same verb, eight seconds apart, at PR-body
preparation time:

1. `[ERROR]` `553184` — "Use a declared flag for `plan-marshall:tools-integration-ci:ci
   pr prepare-body`: ['for', 'plan-id', 'slot']".
2. `[ERROR]` `02936f` — "ci.py pr prepare-body: error: the following arguments are
   required: --plan-id".

The pair is the canonical trap on this surface. `ci.py` declares `--plan-id` as a
ROUTER flag for most verbs (consumed before the provider parser is built, so it must
precede the first positional) — but `pr prepare-body` is a body-consumer verb that
declares its OWN required `--plan-id` AFTER the verb. A pre-verb flag is swallowed by
the router, and the subparser then rejects the call for a missing required argument.
So the second failure is the direct consequence of "correcting" the first in the wrong
direction.

Source records: work-log `[ERROR]` entries `553184` and `02936f` at
2026-09-14T16:33:05Z and 16:33:13Z, marker class `script_failure`. Both rejections
share one notation, so they are one cluster.

## Solution

On `tools-integration-ci:ci`, resolve the `--plan-id` POSITION per verb, never per
script:

- Router-scoped, flag BEFORE the verb: the `checks` read verbs, `pr view`, `pr list`,
  `pr wait-for-comments`.
- Verb-scoped and REQUIRED, flag AFTER the verb: the body-consumer verbs, including
  `pr prepare-body` and `pr prepare-comment`.

Read the canonical-invocation block for the specific verb before issuing the call. The
two documented recurrence signatures (2 and 4 in `persona-plan-marshall-agent`) are
MIRRORS that prescribe opposite moves, and this cluster is what happens when one is
applied without checking which surface it governs.

## Impact

One of four `argparse_rejection` clusters in this run. This one is the most
instructive: the first rejection's own hint listed the declared flags, and the
correction still went the wrong way, because the hint names WHICH flags exist and not
WHERE they go. A remediation hint that reported the required POSITION would have
closed it in one step.
