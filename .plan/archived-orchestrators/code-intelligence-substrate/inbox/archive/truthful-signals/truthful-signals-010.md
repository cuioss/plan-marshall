envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-07-29T13:57:55Z

# FORWARDED — API-Sheriff round-2 hand-off: the substrate-owned subset

**Forwarded from `truthful-signals` 2026-07-29.** Source: cross-repo hand-off from
`cuioss/API-Sheriff` epic `api-sheriff-roadmap`, 18 items observed in real runs against bundle
`0.1.1246` / `0.1.1247`. Full original text recoverable at
`.plan/local/orchestrator/api-sheriff-roadmap/inbox/archive/{id}.md` **in the API-Sheriff repo**.

⚠ **The hand-off's own caveat is load-bearing and was correct**: *"Newer versions exist and may
already fix some of these. Check each finding against current main before working it."* The
orchestrator did so — **two of the four items it checked were already fixed.** Apply the same
discipline to everything below.

## Items owned by this epic

| # | Item | Owner here | Status |
|---|---|---|---|
| **#7** | `compose` evaluates `build-decision` against an **empty footprint at phase-4 time** | **PLAN-122** | **RECURRENCE — third independent observation** |
| **#6** | Phase-5 verification ran module tests where CI runs the **native-image profile** | **PLAN-121** | **NEW** |
| **#2** | `resolve_project_dir` flattens the worktree **tri-state**, hard-errors on `pending` | **PLAN-125** | **RECURRENCE — third observation** |
| **#14** | Retrospective chat-history aspect is **near-blind on gate-steered runs** | **PLAN-123** | **sharpening** |

## ⭐ #6 is genuinely new and is a SELECTION defect, not a coverage one

Phase-5 ran `verify -pl integration-tests -am`; CI runs `verify -Pintegration-tests` for the same
module. **Only the second builds the GraalVM native executable.** A `static final SecureRandom`
without runtime-init registration failed native-image with *"Detected an instance of
Random/SplittableRandom class in the image heap"* — **while the local gate was green.**

⇒ The manifest picked a command **sharing a module name with the CI gate but not its build depth**,
*"which reads as coverage while providing none for the failing class."* ⛔ **Every native-image-only
defect is invisible to the shallower command by construction.**

**Proposed rule for PLAN-121**: when the footprint touches code a **profile-gated build compiles
differently** — GraalVM native image, AOT, a shaded/relocated artifact, an alternate runtime — select
the **profile-gated** command. *"Do not treat 'the module is covered' as sufficient."*

## #2 — the generalizable rule is the valuable half

`manage-status get-worktree-path` publishes a **tri-state** (`disabled` / `pending` / concrete path),
where `pending` is returned as `status: success`. `resolve_project_dir.py:228-237` reads only
`use_worktree` and `worktree_path` — **never the `worktree_state` discriminator** — and raises
`worktree_resolution_failed`. **The exact bytes the producer calls a successful `pending` are
re-read by the consumer as a hard error.**

⭐ **Rule worth adopting bundle-wide**: *"when a producer publishes an explicit discriminator for an
n-state contract, consumers must branch on THAT discriminator, not re-derive the state from primitive
fields. Re-derivation is where 'success' silently collapses into 'error'."*

⚠ **Blast radius**: this is the *shared* routing helper, so **every** script pairing `--plan-id` with
`--project-dir` is unusable with `--plan-id` for the **entire pre-phase-5 window** — phases 1–4,
where outline and planning work live. Observed consequence: `get-module-context` failed at phase 3
and the outline's `## Architecture Hints` section was **omitted silently**, because the section is
*defined* to be omitted when its hint lists are empty — **an errored lookup is indistinguishable from
a genuinely empty one.**

## #14 — the sharpening PLAN-123 should absorb

`extract-chat-signal` reduced a **565-turn** transcript to **2 user turns**, reporting
`no_signal: false, over_budget: false` — a clean Tier 1 extraction — and concluded **zero** corrective
feedback, scope changes and frustration. **All three are literally true and jointly misleading.**

The operator made **eleven** decisions in that run, *every one through an `AskUserQuestion` gate* —
domain widening, planning-lane escalation, execution-posture change (12 → 18 finalize steps), ADR
granularity, and more. **None appear in the reduced transcript, because they arrive as TOOL RESULTS
rather than user turns.** ⇒ *"On a gated run the answer lives entirely in the gate answers; reducing
to free-form turns measures only the channel the operator did not use."*

**Fix**: retain `AskUserQuestion` invocations and their selected answers as a **distinct signal
class**; report `free_form_corrections` and `gate_decisions` as **two counters**. ⭐ *"A run with 0
corrections and 11 gate decisions is well-instrumented, and the aspect should be able to say so."*

## The hand-off's cross-cutting observation — worth reading in full

Six items across both hand-offs share one shape: **a mechanism reported success it had not earned,
and the report was well-formed enough to be trusted.** *"None were crashes. Every one was a
plausible, confident, structurally valid output. The bundle's failure mode is not error, it is
unearned confidence — and the counter is consistently the same: **assert against the artifact that
would have to change, not against another description of it.**"*
