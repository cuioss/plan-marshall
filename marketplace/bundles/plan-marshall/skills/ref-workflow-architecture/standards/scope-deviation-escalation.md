# Scope-Deviation Escalation

Defines what counts as "softening a request-level hard requirement" at execute time and the contract every component MUST follow when the softening would otherwise be applied silently.

This standard is the single source of truth for the deviation taxonomy, the AskUserQuestion shape, and the prohibited "log-and-continue" anti-pattern. Two callers reference it: `phase-5-execute` (Step 11 triage loop) and `execute-task` (Handle Verification Results).

## Hard-Requirement Softening: Definition

A request-level hard requirement is any acceptance criterion authored in the plan's request, solution outline, or deliverable narrative that:

- Names a measurable gate (e.g., "`grep -rn '--project-dir' marketplace/` returns zero hits"), OR
- Declares a structural intent (e.g., "Breaking change. No transition window."), OR
- Specifies a complete deletion (e.g., "Remove the flag entirely").

A **softening** is any execute-time decision that would relax the requirement at runtime: deferring the gate, retaining a legacy code path, downgrading the deletion to "remove only newly-added callers", accepting a non-zero grep count, etc. Softening can be motivated by real engineering caution (cache-sync timing, in-flight task dependencies, dependency on an upstream merge), but the motivation does not bypass the escalation contract — it only affects which option the user chooses.

### Concrete Examples

| Original Hard Requirement | Softened Decision (would-have-been-silent) | Escalation Path |
|---------------------------|---------------------------------------------|-----------------|
| `grep -rn '--project-dir' marketplace/ doc/ test/` returns zero hits | "Two-state contract: `--plan-id` preferred; `--project-dir` retained as escape hatch" — and merging with 430 hits across 77 files | AskUserQuestion at the moment the gate is about to be deferred |
| "Breaking change. No transition window." | "Until auto-routing has fully landed, callers may still see `--project-dir` for legacy compatibility" | AskUserQuestion before any task adds the hedge to the central narrative |
| "Remove the `--legacy-mode` flag entirely" | "Remove the flag from the public CLI surface but keep the `_legacy_mode` private parameter" | AskUserQuestion before the deletion task is reduced in scope |

The pattern in every case: the implementor concludes mid-execution that the request as written is structurally riskier than estimated, and the conservative response is to keep both surfaces. The escalation contract converts that conclusion from a silent runtime override into an explicit user decision.

## Escalation Contract

When an execute-time component (phase-5-execute orchestrator at Step 11 triage; execute-task per-task verifier at Handle Verification Results) detects that the impending decision would soften a request-level hard requirement, it MUST raise an `AskUserQuestion` with the canonical three-option shape below. The component MUST NOT log-and-continue, MUST NOT auto-select ACCEPT, and MUST NOT record the decision via a `[STATUS]` work-log line ahead of (or instead of) the AskUserQuestion thread.

### Canonical AskUserQuestion Shape

```yaml
question: |
  The current decision would soften a request-level hard requirement.

  **Hard requirement:** {verbatim quote from request / outline / deliverable narrative}

  **Softening detected:** {one-line description of the relaxation — what would change vs. the requirement}

  **Engineering motivation:** {one-line — cache-sync timing, in-flight task dependency, etc.}

  How would you like to proceed?

header: "Scope Deviation"
options:
  - label: "Hold the line"
    description: "Continue refusing the softening. The component re-runs verification / continues triage with the hard requirement intact. The implementor must find a path that satisfies the requirement as written, or escalate again with a different motivation."
  - label: "Accept with rationale"
    description: "Record the deviation as a deliberate scope reduction. A written rationale is mandatory and will be persisted to decision.log AND surfaced in the PR body. The plan may proceed with the softened scope."
  - label: "Split into follow-up plan"
    description: "Stop the current plan at the additive boundary; the deletion / strict-mode portion ships as a separate follow-up plan (see self-modifying-classification.md PLAN A / PLAN B pattern). Current plan continues with only the additive work."
multiSelect: false
```

### Resolution Handling

Each option triggers a deterministic side effect; none of them is "log and silently continue":

| Option | Side Effect |
|--------|-------------|
| **Hold the line** | Component refuses the softening and routes back through the standard triage path (FIX or BLOCKED). No softening recorded. |
| **Accept with rationale** | Component prompts for the rationale text via a follow-up `AskUserQuestion` (free-form). Rationale is persisted to `decision.log` at INFO level with a `(scope-deviation:accept)` caller-name marker. The PR body MUST include the rationale verbatim under a "Scope Deviation Accepted" subsection. |
| **Split into follow-up plan** | Component creates a successor lesson via `manage-lessons add` capturing the deferred portion (title, narrative, the original hard requirement, the reason the split was chosen). The current plan continues with only the additive scope. The lesson seeds the follow-up plan at the next planning cycle. |

## Prohibited Anti-Pattern: Log-and-Continue

The work-log line shape `[STATUS] Gate N deferred status accepted` (or any equivalent — "deferred", "skipped", "deferred to follow-up", "accepted as scope reduction") is **documentation, not authorization**. Recording the decision to `work.log` without a corresponding `AskUserQuestion` thread is the failure mode this standard exists to prevent.

When a component encounters a path that would historically have emitted such a line:

1. STOP. Do not write the work-log line.
2. Detect whether the decision softens a hard requirement (see Definition above).
3. If yes → raise the canonical AskUserQuestion. If no → continue with the standard non-deviating path.

A `[STATUS]` line confirming the user's chosen option (e.g., `[STATUS] (plan-marshall:phase-5-execute) Scope deviation accepted by user — rationale logged to decision.log`) IS allowed and recommended after the AskUserQuestion has resolved. The prohibition is on the order: log MUST follow user decision, never replace it.

## Caller References

Two callers reference this standard. When the deviation taxonomy or the AskUserQuestion shape changes, both callers should be reviewed for drift.

| Caller | Reference | Purpose |
|--------|-----------|---------|
| `plan-marshall:phase-5-execute` (Step 11 § Scope-Deviation Escalation) | Full standard | Phase-level guard before any "deferred / accepted" path in the FIX/SUPPRESS/ACCEPT triage branch |
| `plan-marshall:execute-task` (Handle Verification Results § Scope-Deviation Escalation) | Full standard | Per-task guard before recording a verification deviation that softens a hard requirement |

## Related

- `plan-marshall:ref-workflow-architecture/standards/self-modifying-classification.md` — outline-time/plan-time classification for plans whose edits touch their own runtime infrastructure; covers the structural half of the failure mode that motivates this escalation rule.
- Lesson `2026-05-08-09-004` — original failure case (PR #346 silently descoped a "no transition window" requirement to a two-state contract; the deferral was logged to `work.log` without an `AskUserQuestion`).
