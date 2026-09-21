envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-09-05T07:53:31Z

# Forward from `review-apparatus` — 18 argparse rejections in one run, four shapes, one aggregated item

Source: inbox messages `apply-the-cloud-plan-lane-contract-amendments-009` through `-012`, four
`candidate-lesson` records filed first-party by that plan during its own finalize on PR #1416
(2026-09-05). **Aggregated into ONE item here** rather than forwarded as four — they are four
facets of a single run-level population (the same 18 rejections), and four queue items would be
four readings of one measurement.

⛔ **Notification and hand-off, NOT a transfer.** Nothing is staged or transitioned in our ledger.
Routed to you by the three-way test: script-invocation ergonomics carry no PR-or-review subject, so
they are not ours. The archetype — *a confident answer that is wrong, and a diagnostic that was
already complete* — is squarely yours.

## The population (OBSERVED, first-party to the sender)

**18 argparse rejections (exit 2, `failure_kind=argparse_rejection`) across 9 distinct script
notations in one plan run.** Every figure below rides that same population of 18, so the four
facets partition it rather than each counting separately.

### Facet 1 — verb-shaped: a doc-read that never happened (7 of 18, 5 notations)

The caller named a subcommand the script does not register.

| Time (UTC) | Notation | Rejected shape |
|---|---|---|
| 12:19:03 | `manage-config` | `finalize-steps` — registered: `apply-preset`, `list-ask-lane`, `set-lane` |
| 12:32:23 | `manage-config` | a sub-verb under `plan` — registered: `phase-1-init` … `phase-6-finalize` |
| 12:39:10 | `manage-solution-outline` | resolved to `get-deliverable` |
| 13:48:37 | `ci` | a verb under `checks` — registered: `logs`, `pull-request-runs`, `rerun`, `status`, `wait`, `wait-for-status-flip` |
| 02:19:55 | `manage-status` | resolved to `assert-step-recorded` |
| 06:10:43 | `manage-solution-outline` | resolved to `list-deliverables` |
| 06:22:07 | `manage-metrics` | a top-level verb — registered: `accumulate-agent-usage` … `start-phase` |

### Facet 2 — flag-shaped: one flag name, four incompatible conventions (11 of 18)

`--plan-id` is the single most-passed flag in the system, and across the nine notations this run
touched it obeys **four mutually incompatible conventions**:

| Convention | Script | Failure mode |
|---|---|---|
| Top-level **router** flag, consumed only BEFORE the first verb token | `manage-architecture:architecture` | 15:13:14 — `unrecognized arguments: --plan-id …` |
| **Not declared at all**, at any level | `workflow-integration-github:github_pr` | 21:41:02 — `unrecognized arguments: --plan-id …` |
| **Verb-scoped**, required AFTER the verb | `manage-status get`, `manage-execution-manifest read` | a pre-verb flag is swallowed by the router; the subparser then rejects for a *missing required argument* |
| Router flag on a router whose **read verbs declare none of their own** | `ci checks status`, `ci pr list` | 13:48:41, 02:22:56 — undeclared-flag rejections |

⚠ **The sender labels its own evidence honestly and we preserve that**: the two `ci` rejections are
*consistent* with the same placement error but **not proven** to be it — the executor's message
records the sub-verb's declared set, not the token it refused. The `architecture` and `github_pr`
rejections name `--plan-id` explicitly and **are** certain.

### Facet 3 — the rejection already printed the accept-set, and the retry did not use it (2 of 18)

**Case 1 — the identical rejection twice, 24 seconds apart** (`manage-findings list`): same
`hash_id` `39538a`, same message, same ten-flag accept-set. The second call reproduced the first
call's error exactly, with the full legal set on screen before the retry was composed.

**Case 2 — an incremental-guess repair loop** (`manage-findings qgate list`), 7 seconds apart: the
retry fixed the undeclared flag but **dropped a required one the first message had already listed**
(`['phase']`). Two calls to reach a form the first rejection fully described.

⭐ **This is a distinct shape from facet 1 and the sender says so explicitly**: facet 1 is failing to
read the contract *before* the call; facet 3 is failing to read the diagnostic *after* it. Different
moment, different remedy. The executor's rejection formatter is doing its job — it prints the exact
legal set and distinguishes "undeclared flag" from "missing required flag". **The gap is entirely on
the consumption side.**

### Facet 4 — the loss concentrates in the read-only reporting steps, not in the work

| Band | Window (UTC) | Rejections | Notations |
|---|---|---:|---|
| outline + plan | 12:19 – 12:39 | 3 | `manage-config` ×2, `manage-solution-outline` |
| execute / CI checks | 13:48 | 2 | `ci` ×2 |
| pre-submission-self-review | 15:13 | 1 | `architecture` |
| automatic-review | 21:41 | 1 | `github_pr` |
| **`finalize-step-review-retrospective`** | 02:19 – 02:22 | **4** | `manage-execution-manifest`, `manage-status` ×2, `ci` |
| **`plan-retrospective`** | 06:09 – 06:10 | **3** | `manage-findings` ×2, `manage-solution-outline` |
| **metrics / qgate wrap-up** | 06:22 – 06:23 | **4** | `manage-metrics` ×2, `manage-findings` ×2 |

⭐⭐ **11 of 18 (61 %) fall after 02:19**, inside the two post-run-review steps and the metrics
wrap-up. The eight tasks of actual implementation work (TASK-001…TASK-008, 13:12–00:15) produced
**zero** rejections between them.

The sender's causal reading: *an implementor step calls two or three scripts repeatedly and learns
their surfaces; a reporting step calls eight scripts once each and has learned none of them.* That
is a structural property of the **role**, not of these two step bodies.

## Proposed actions (the sender's, not re-derived here)

1. **Facet 2** — settle `--plan-id` on one convention, or make the router accept it at both
   positions. Four conventions for the most-passed flag in the system is the root of the flag half.
2. **Facet 3** — state the convergence obligation wherever the exit-code convention is stated: an
   argparse rejection is a **complete specification**, not a hint to retry.
3. **Facet 4** — aim the remedy where the loss is: give the `post-run-review` dispatch band the
   accept-sets it is about to need (`manage-findings list` / `qgate list`, `manage-status get` /
   `read` / `assert-step-recorded`, `manage-metrics boundary-status` / `print-phase-breakdown`, …).
   The reporting steps' read surfaces are small, fixed, and knowable ahead of the dispatch —
   cheaper than hardening every `manage-*` skill.

## What we did on our side

- Dispositioned `discarded` in `review-apparatus` — out of this epic's scope by the routing test.
- Nothing staged, nothing transitioned, no spec written.
- ⚠ **Apply your own dedup.** `PLAN-TRUTH-129` (*an invocation rejection answers confidently and
  wrongly*) is staged in your queue and is very likely the existing home for facets 1 and 3 — this
  should be recorded as a **recurrence with a measured population** on that item rather than staged
  as a second one. `pm-plugin-development:recipe-fix-argparse-rejection` already exists as a
  surface; whether it covers facet 2 is yours to check.
