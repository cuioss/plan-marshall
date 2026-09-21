envelope_version=1
sender_type=plan
sender_id=freshness-gate-says-fresh-unexamined-tree
epic=truthful-signals
kind=candidate-lesson
created=2026-09-06T17:33:59Z

# Candidate lesson: `github_re_review re-review --push-time` is a REQUIRED flag whose own help text says it does nothing

## Proposed component

`plan-marshall:workflow-integration-github`. Category: `bug`.

## Observation

`github_re_review re-review` rejects any call that omits `--push-time`. The flag's own help
string, read from the live parser at HEAD, is:

```text
--push-time PUSH_TIME
                      ISO-8601 push time (retained for routing uniformity;
                      every registered bot posts an explicit trigger
                      comment)
```

So the parser states two things at once, and they contradict each other:

- **argparse says the value is mandatory** — `required=True`, no default, and the call is refused
  without it.
- **the help text says the value is not used** — it is "retained for routing uniformity", and the
  stated reason it is not needed is that "every registered bot posts an explicit trigger comment",
  i.e. the actual routing signal is the trigger comment, not the push time.

The full required set on this verb is `--pr-number`, `--bot-kind`, `--head-sha`, `--push-time`;
`--timeout` and `--plan-id` are optional. `--plan-id` is documented as "accepted for routing
uniformity" too — but it is OPTIONAL, which is the shape a genuinely inert flag should have.
`--push-time` is the same kind of flag with the opposite enforcement.

## Why this is a defect and not a nit

A required argument that the implementation declares it does not consume is pure caller burden
with no corresponding guarantee. It has three costs, all of which were paid in this run:

1. **It manufactures rejections.** This was one of four argparse rejections in a single
   `6-finalize` run, and it is the one with no caller-side lesson available: there is nothing a
   caller can reason out from the surrounding contract, because the contract says the value does
   not matter.
2. **It invites a fabricated value.** The cheapest way past a required-but-unused ISO-8601 flag is
   to synthesize a plausible timestamp. That is a value nothing validates and nothing reads,
   entering a re-review path whose whole purpose is establishing that a review is genuinely fresh
   for the current HEAD. A synthesized freshness input on a freshness-proving verb is exactly the
   confident-signal-hides-a-caveat shape this epic tracks.
3. **It contradicts the sibling flag.** `--plan-id` carries the identical "routing uniformity"
   rationale and is optional. Two flags with the same stated rationale and opposite enforcement
   means at least one of them is wrong.

## Suggested direction (for the orchestrator to judge)

Two candidate resolutions, and the choice is a real decision rather than an obvious fix:

- **Make it optional** (matching `--plan-id`, its own stated twin) if the value truly is retained
  only for uniformity. Cheapest, and removes the fabrication incentive.
- **Make it load-bearing** if the re-review path should in fact be anchored to a push instant —
  in which case the help text is the thing that is wrong, and the flag needs a consumer plus
  validation, not a demotion.

What should NOT happen is leaving it required and inert, because that is the state that both
produces the rejection and rewards inventing a value for it.

## Relationship to the sibling candidate

Filed alongside the flag-shape rejection-cluster candidate from this same run. That one is about
**caller discipline and doc/parser agreement** across four calls; this one is a **single concrete
parser defect** with its own remedy. They are separately actionable, which is why they are two
messages rather than one.

## Provenance

Signal source: `signal_script_failure_clusters_count` for plan
`freshness-gate-says-fresh-unexamined-tree`. The help text quoted above was read from the live
parser at HEAD during this step, not from documentation.
