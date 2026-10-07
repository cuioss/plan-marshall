envelope_version=1
sender_type=plan
sender_id=pr-065-settings-repo-accumulates-never-lands
epic=review-apparatus
kind=candidate-lesson
created=2026-09-14T19:21:53Z

component=plan-marshall:manage-execution-manifest
category=bug
source_signal=script_failure_cluster
source_plan=pr-065-settings-repo-accumulates-never-lands
evidence=work-log ERROR 1763dc (2026-09-14T08:34:18Z and 08:34:19Z)

# `step-params set --value` failed as "expected one argument" and the identical call was retried one second later

Two rejections against
`plan-marshall:manage-execution-manifest:manage-execution-manifest`, one second
apart, with byte-identical detail:

```text
manage-execution-manifest.py step-params set: error: argument --value:
expected one argument
```

`--value` was supplied but reached argparse with nothing after it — an empty or
whitespace-only value, or a value the shell consumed. The retry one second later
was identical and failed identically.

## Two candidate signals, not one

1. **Producer**: a `--value` whose content is empty or shell-fragile does not
   survive the argument vector. The repo already routes multi-line and
   `#`-bearing content through a staged file rather than an argument
   (`manage-lessons set-body --file`, `orchestrator inbox write --payload-file`);
   `step-params set` has no such route, so a value that cannot ride a shell
   argument has nowhere to go.
2. **Caller**: the immediate retry of a byte-identical failing call. An argparse
   rejection is deterministic — the identical call fails identically, always.
   Principle 8 (establish provenance before re-attempting a failing fix) covers
   the general case; a one-second identical retry of an `exit_code=2` argparse
   rejection is the narrowest, cheapest instance of it.
