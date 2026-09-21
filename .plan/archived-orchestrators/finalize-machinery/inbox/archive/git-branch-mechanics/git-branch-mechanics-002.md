envelope_version=1
sender_type=plan
sender_id=git-branch-mechanics
epic=finalize-machinery
kind=finding
created=2026-09-17T12:37:29Z

# Session-identity hard-block fires on a runtime with no session concept (abstraction bug)

Sender: plan `git-branch-mechanics` (operator-directed finding).

## Observation

At `6-finalize` entry for plan `git-branch-mechanics`, the `execution.md`
session-id resolver hard-blocked:

- `manage-status metadata --get --field session_ids` → `not_found`
- retired scalar `session_id` → `not_found`
- late `platform_runtime session capture --plan-id` → `status: error`,
  `error: hook_not_configured` (`$CLAUDE_CODE_SESSION_ID` unset)
- `platform_runtime session bind --plan-id` (target-exposed fallback) →
  `bound: false`, `reason: no_session_id`

The resolver contract (`plan-marshall/workflow/execution.md` Finalize Phase +
`phase-6-finalize/SKILL.md` "How to obtain session_id") aborts finalize here
rather than inventing a filler value.

## Why this is a bug, not a configuration gap

The session identity's sole downstream consumer is metrics enrichment:
`session_id` is forwarded to `default:record-metrics` for `manage-metrics
enrich` → platform-runtime `metrics normalized-tokens`, which on OpenCode
returns a `no-op` (`transcript_not_found`) by design — `enrich` degrades
gracefully and the final report simply carries no transcript-sourced session
tokens. Push, PR creation, CI verification, merge, and archive do not consume
the session identity at all.

So on a runtime that exposes no session concept, a telemetry-only input
gates the entire shipping pipeline. The abstraction is wrong: the
Claude-Code-specific wake/hook identity (`$CLAUDE_CODE_SESSION_ID`,
SessionStart hook) leaks through the platform-runtime seam as a hard
finalize precondition instead of degrading to unenriched the way `enrich`
itself already does. The `bind` verb proving `no_session_id` is the seam
admitting the runtime has nothing — and the caller treating that admission
as fatal is the defect.

## Suggested repair direction

- Make the finalize session resolver target-aware: when the active target
  exposes no session identifier (`bind` → `no_session_id`), proceed
  unenriched with a logged decision instead of aborting.
- Keep the hard-block for the Claude target, where an absent identity means a
  broken hook rather than a missing concept.
- Alternatively, demote `session_id` from required to optional on the
  `phase-6-finalize` input contract, with `record-metrics` skipping `enrich`
  when it is absent.

## Disposition of the current plan

Operator waived enrichment and directed proceed. Finalize for
`git-branch-mechanics` continues without session identity; its final metrics
report will carry no transcript-sourced session tokens by explicit waiver,
not by silent omission.
