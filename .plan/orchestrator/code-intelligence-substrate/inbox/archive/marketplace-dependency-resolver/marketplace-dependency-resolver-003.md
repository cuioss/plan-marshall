envelope_version=1
sender_type=plan
sender_id=marketplace-dependency-resolver
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-01T19:15:07Z

component=plan-marshall:manage-tasks
category=bug
title=Falsy-zero validation rejects the exact sentinel the governing workflow tells callers to write

# Falsy-zero validation rejects the exact sentinel the governing workflow tells callers to write

## What happened

`phase-6-finalize/workflow/triage.md` Step 3c instructs a fix-task body to carry
`deliverable: 0` — `0` being the documented sentinel for "this task belongs to no
deliverable". `manage-tasks commit-add` validates that field with a **truthiness**
test, so `0` is indistinguishable from absent and the call is rejected as a missing
required field.

The two are individually defensible and jointly broken: the workflow's sentinel
choice is reasonable, the script's presence check is the ordinary Python idiom, and
neither surface is wrong when read alone.

## Why it is worse than an ordinary doc-contract divergence

The failure is **100% reproducible for anyone following the documented workflow
verbatim**. There is no lucky path. Every fix task allocated by executing
`triage.md` Step 3c as written hits the rejection — which means the failure rate of
the documented path is 1.0, and it has been that way for as long as both sides have
existed.

That is the signature worth generalising: a divergence whose failure rate is 1.0 has
survived not because it is rare but because **nobody executed the documented path
and checked the exit code**. It is invisible to review of either surface in
isolation, and invisible to any test that constructs its own arguments instead of
constructing the ones the doc prescribes.

## Corrective rule

1. **Never use a truthiness test for presence on a numeric or string field whose
   documented domain includes a falsy member** (`0`, `""`, `False`). Test
   `is None` / `not in payload` explicitly. A required-field check must answer
   "was it supplied", never "is it interesting".

2. **When a workflow doc prescribes a literal argument value, that literal is part
   of the script's contract surface.** A test that exercises the verb with
   hand-chosen arguments does not cover it. The covering test is the one that
   constructs the argument the doc tells the caller to construct — including its
   sentinel values.

## Detection heuristic for the corpus

Grep the workflow corpus for prescribed literal field values that are falsy in the
target language (`: 0`, `= 0`, `: ""`, `: false`) and cross-check each against the
consuming script's presence check. The population is small and the check is
mechanical.
