# Scope-Deviation Escalation

Defines what counts as "softening a request-level hard requirement" at execute time and the contract every component MUST follow when the softening would otherwise be applied silently.

This standard is the single source of truth for the deviation taxonomy, the prompt shape, and the prohibited "log-and-continue" anti-pattern. Two callers reference it: `phase-5-execute` (Step 11 triage loop) and `execute-task` (Handle Verification Results). Both callers are **dispatched leaves** — neither fires `AskUserQuestion` itself. A leaf that detects a softening returns the canonical three-option payload as an `escalate_ask` envelope (`prompt_options[]`); the main-context orchestrator fires the `AskUserQuestion` and applies the resolution's side effects. See [`agents.md`](agents.md#leaf-cannot-fire-askuserquestion--return-a-prompt-required-envelope) § "Leaf cannot fire AskUserQuestion".

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

When an execute-time dispatched leaf (execute-task per-task verifier at Handle Verification Results; the phase-5-execute Step 11 triage loop that collects the leaf's return) detects that the impending decision would soften a request-level hard requirement, the leaf MUST NOT fire `AskUserQuestion` in-leaf, MUST NOT log-and-continue, MUST NOT auto-select ACCEPT, and MUST NOT record the decision via a `[STATUS]` work-log line. Instead the leaf leaves the task not-done and returns an `escalate_ask` envelope carrying the canonical three-option shape below as a `prompt_options[]` entry; the main-context orchestrator fires the `AskUserQuestion` and owns the resolution. When multiple deviation / `smart_and_ask` gates fire within one task or envelope, they batch into ONE `escalate_ask` envelope (one `AskUserQuestion` covering all of them).

### Canonical Prompt Shape (fired by the orchestrator from the envelope)

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
    description: "Stop the current plan at the additive boundary; the deletion / strict-mode portion ships as a separate follow-up plan. Follow-up-split pattern: the current plan (PLAN A) ships only the additive surface and lands on main; a successor plan (PLAN B) removes the old surface against the already-merged additive base, so PLAN B's verification gates run against PLAN A's landed code rather than in-flight worktree edits. Current plan continues with only the additive work."
multiSelect: false
```

### Resolution Handling (orchestrator-owned, applied post-return)

After the orchestrator fires the batched `AskUserQuestion`, each option triggers a deterministic side effect applied by the orchestrator once the leaf has returned; none of them is "log and silently continue":

| Option | Side Effect (applied by the orchestrator post-return) |
|--------|-------------|
| **Hold the line** | The orchestrator re-dispatches the phase so the leaf refuses the softening and routes back through the standard triage path (FIX or BLOCKED), the hard requirement intact. No softening recorded. |
| **Accept with rationale** | The orchestrator prompts for the rationale text via a follow-up `AskUserQuestion` (free-form). Rationale is persisted to `decision.log` at INFO level with a `(scope-deviation:accept)` caller-name marker. The PR body MUST include the rationale verbatim under a "Scope Deviation Accepted" subsection. |
| **Split into follow-up plan** | The orchestrator creates a successor lesson via `manage-lessons add` capturing the deferred portion (title, narrative, the original hard requirement, the reason the split was chosen). The current plan continues with only the additive scope. The lesson seeds the follow-up plan at the next planning cycle. |

## Prohibited Anti-Pattern: Log-and-Continue

The work-log line shape `[STATUS] Gate N deferred status accepted` (or any equivalent — "deferred", "skipped", "deferred to follow-up", "accepted as scope reduction") is **documentation, not authorization**. Recording the decision to `work.log` without a corresponding `AskUserQuestion` thread is the failure mode this standard exists to prevent.

When a dispatched leaf encounters a path that would historically have emitted such a line:

1. STOP. Do not write the work-log line.
2. Detect whether the decision softens a hard requirement (see Definition above).
3. If yes → leave the task not-done and return the `escalate_ask` envelope (`prompt_options[]`) for the orchestrator to fire the `AskUserQuestion`. If no → continue with the standard non-deviating path.

A `[STATUS]` line confirming the user's chosen option (e.g., `[STATUS] (plan-marshall:phase-5-execute) Scope deviation accepted by user — rationale logged to decision.log`) IS allowed and recommended after the orchestrator's `AskUserQuestion` has resolved. The prohibition is on the order: log MUST follow user decision, never replace it — and the decision itself is owned by the orchestrator, never fired from the leaf.

## Caller References

Two dispatched-leaf callers reference this standard, and the main-context orchestrator owns the prompt. When the deviation taxonomy or the prompt shape changes, all three should be reviewed for drift.

| Caller | Role | Reference | Purpose |
|--------|------|-----------|---------|
| `plan-marshall:execute-task` (Handle Verification Results § Scope-Deviation Escalation) | dispatched leaf — returns `escalate_ask` | Full standard | Per-task guard: detects a softening, leaves the task not-done, returns a `prompt_options[]` entry (batched with any `smart_and_ask` entry) |
| `plan-marshall:phase-5-execute` (Step 11 triage loop) | dispatched leaf — yields `escalate_ask` | Full standard | Collects the leaf's `prompt_options[]` and yields the batched `escalate_ask` envelope to the orchestrator as a TASK-boundary yield reason |
| `plan-marshall:plan-marshall/workflow/execution.md` (§ Post-return `escalate_ask` batched deviation dispatch) | main-context orchestrator — fires the prompt | Resolution Handling | Fires ONE batched `AskUserQuestion`, applies each option's side effect post-return, re-dispatches phase-5-execute with the resolutions baked in |

## Related

- Rationale: Plans have silently descoped hard requirements by deferring them to `work.log` entries without an `AskUserQuestion` — this standard makes the escalation contract explicit so silent softening is structurally prevented.
