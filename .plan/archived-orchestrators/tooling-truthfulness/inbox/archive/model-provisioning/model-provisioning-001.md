envelope_version=1
sender_type=orchestrator
sender_id=model-provisioning
epic=tooling-truthfulness
kind=finding
created=2026-09-13T16:29:55Z

# Finding — Muse Spark plan-following failure, 3rd occurrence (orchestrator-side variant)

Filed from the `model-provisioning` epic orchestrator on operator direction, as
recurrence data for the `tooling-truthfulness` Watch "Executing agent skipped
the plan lifecycle on Muse Spark 1.3 (2nd occurrence)", whose re-check trigger
is a third occurrence escalated as an epic-external finding. This is that third
occurrence, in an orchestrator-side variant: the pipeline was worked, but a
convention the docs leave implicit was mis-filled.

## What happened

During `model-provisioning` decompose (Step 5, populating `status.json`), the
orchestrator filled every plan row's `slug` with the **epic** slug
(`model-provisioning`) instead of a per-plan short slug. All four rows staged,
all four spec files written as `PLAN-0N-model-provisioning.md`. The ledger was
structurally green and the defect survived until the operator read the queue.

## Why nothing caught it

- `decompose.md` Step 5's placeholder shows `{id, slug, workstream, …}` but
  never states `slug` is the plan's own short slug. The only slug in context
  was the epic slug — plausible-filler bias did the rest.
- No queue verb validates slug semantics: id grammar and status enum are
  checked, slug uniqueness and slug≠epic-slug are not. Every write returned
  success.
- `resume-summary` renders `{id}-{slug}` verbatim, so the derived blocks agreed
  with `status.json`; `corpus enumerate` joins rows to specs by `PLAN-NN-`
  prefix, so rows still reconciled. Semantic indistinguishability is invisible
  to every structural check in the chain.
- Caught only by human reading — the same detection story as occurrences 1–2.

## Remediation in the filing epic (done, reference only)

Re-suffixed per plan (`schema-resolve-slot`, `steward-pin-materialization`,
`emitter-reenable`, `live-verification`) across `status.json`, spec files,
hand-off commands, dependency pointers, and charters; re-verified
bidirectionally (`corpus enumerate`: 0 orphans); regenerated both `epic.md`
blocks; superseded the earlier `next` emission. Evidence: `model-provisioning`
decision log, 2026-09-13.

## Candidate remedies for this epic to consider (not directives)

- State slug semantics at the Step 5 write site (`slug` = plan's own short
  slug, unique within the queue, never the epic slug).
- Add a duplicate-slug lint (plan-doctor or queue-write path) — mechanical,
  red-first-testable.
- Add a `resume-summary` self-validation detector for N rows sharing one slug,
  beside the existing detectors.
