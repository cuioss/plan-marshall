envelope_version=1
sender_type=plan
sender_id=test-fidelity-rules-follow-up
epic=process-compliance
kind=finding
created=2026-09-19T21:03:33Z

# Process-rule gap: installed skill copy carries no workflow documents

## Observed

- `plan-marshall-plan-marshall` resolved action `outline` for plan `test-fidelity-rules-follow-up` (current phase `3-outline`) and routed to `workflow/planning-outline.md`.
- The installed copy at `~/.config/opencode/skills/plan-marshall-plan-marshall/` holds only `references/`, `scripts/`, `SKILL.md`, `standards/` — no `workflow/` directory, so that read failed with file-not-found.
- Continued from the marketplace source of truth at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md` (598 lines, read whole).

## Conflict

- The action-routing table names the workflow document as the execution authority; the installed skill is the runtime copy the router points at.
- With the document absent from the installed copy, strict step-following forces a fallback read outside the installed tree.

## What was done on this run

- Read the canonical marketplace copy and followed it verbatim; no step was improvised from memory.
- No installed-tree files were modified.

## Request

- Either ship `workflow/` with the installed skill copy or document the marketplace-tree fallback as the sanctioned read path when the installed copy lacks it.
