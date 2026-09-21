envelope_version=1
sender_type=plan
sender_id=one-format-several-implementations-that-disagree
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T19:18:09Z

category=bug
component=plan-marshall:build-server-client
title=The build-server submit surface is reachable only by guessing across three notations

## Signal

`script_failure_clusters` — two of the eight distinct failing notations in this
run were consecutive attempts to reach one verb:

```text
plan-marshall:manage-build-server:build_server         -> Invalid notation (exit 1)
plan-marshall:manage-build-server:manage_build_server  -> unknown_verb: build_server (exit 2)
plan-marshall:build-server-client:build_server         -> success
```

Three notations tried, two rejected, before an orchestrator-tier build could be
submitted. Then two more rejections on the argument surface of the verb that
worked:

```text
--command "module-tests plan-marshall"       -> must be a JSON array of argv tokens
--command '["./pw","module-tests","..."]'    -> refused by verifier: wrong_interpreter
```

Five failures to issue one build.

## What is actually wrong

Each individual error message is good — the first even prints the corrected
format. The defect is **distribution**: the knowledge needed to reach the verb is
split across skills whose names both plausibly own it.

- `manage-build-server` is the operator control surface (enrol, lifecycle) and
  owns the *name* a caller reaches for.
- `build-server-client` is the consumption surface and owns `submit` / `wait`.

The split is deliberate and documented (`build-server-client/SKILL.md` calls it
"the anti-laundering wall"). But a caller who knows only "I need to submit a build
to the daemon" reaches for the management-sounding notation first, and nothing at
that notation points across the wall.

The `--command` shape compounds it: the canonical invocation shows executor-form
argv, but a caller arriving from `architecture resolve` holds a `--command-args`
string, and the translation between the two is not stated at either end.

## How to apply

Two cheap fixes, neither of which weakens the wall:

1. Make `manage-build-server`'s unknown-verb rejection name the sibling for the
   consumption verbs — the existing "did you mean" machinery already prints a
   correction for the notation case, so extend it to the verb case.
2. State the `architecture resolve` → `build_server submit` translation once,
   where a caller holding a resolved `executable` will find it: the resolved
   command's tokens ARE the `--command` array, prefixed by `python3` and the
   worktree-absolute executor path.
