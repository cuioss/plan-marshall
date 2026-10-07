envelope_version=1
sender_type=plan
sender_id=apply-the-cloud-plan-lane-contract-amendments
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T06:28:57Z

component=plan-marshall:persona-plan-marshall-agent
category=anti-pattern
created=2026-09-05

# The rejection already printed the whole accept-set, and the retry did not use it

## Observation

Two of this run's eighteen argparse rejections are not first-guess errors — they are *repairs
that did not read the error they were repairing*.

**Case 1 — the identical rejection, twice, 24 seconds apart** (`manage-findings list`):

```text
06:09:48  ERROR 39538a  Use a declared flag for `…manage-findings list`:
          ['any-checkout','author','bot-kind','file-pattern','include-qgate',
           'kind','plan-id','promoted','resolution','type']
06:10:12  ERROR 39538a  Use a declared flag for `…manage-findings list`:
          ['any-checkout','author','bot-kind','file-pattern','include-qgate',
           'kind','plan-id','promoted','resolution','type']
```

Same `hash_id`, same message, same accept-set — the second call reproduced the first call's
error exactly. The full set of ten legal flags was on screen before the retry was composed.

**Case 2 — an incremental-guess repair loop** (`manage-findings qgate list`), 7 seconds apart:

```text
06:23:04  Use a declared flag for `…manage-findings qgate list`:
          ['any-checkout','iteration','phase','plan-id','resolution','source']
06:23:11  Add the required flag(s) to `…manage-findings qgate list`: ['phase']
```

Here the retry did fix the undeclared flag — but dropped a *required* one that the first
message had listed. Two calls to reach a form the first rejection fully described.

## Why this is a distinct shape

The sibling candidate ("a registered-verb rejection is a doc-read that never happened") is about
failing to read the contract **before** the call. This one is about failing to read the
diagnostic **after** it. Different moment, different remedy: the first is fixed by making the
accept-set resident at authoring time; this one is fixed only by treating an argparse rejection
as a complete specification rather than as a hint to try again.

The executor's rejection formatter is doing its job well here — it prints the exact legal set and
distinguishes "undeclared flag" from "missing required flag". The gap is entirely on the
consumption side.

## Proposed corrective action

State the convergence obligation explicitly wherever the exit-code convention is stated: **an
argparse rejection is a one-retry budget.** A second rejection of the same notation and verb is
itself the defect signal — it means the printed accept-set was not used to construct the retry.
The `phase-6-finalize` "Exit-code convention for every script call" block is the natural home; it
currently governs how to *react* to a non-zero exit (STOP, preserve the envelope) but says
nothing about what a *correct* repair looks like.

Cheap detector: the work log already carries a stable `hash_id` per distinct rejection message.
Two consecutive `[ERROR] … script_failure` lines with the same `hash_id` are mechanically
identifiable — `39538a` twice, above, is exactly that.
