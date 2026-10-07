envelope_version=1
sender_type=plan
sender_id=phase-gates
epic=process-compliance
kind=finding
created=2026-09-19T09:46:59Z

# Finding: contradictory .plan access rules forced a violation either way

**Reporter:** phase-gates (plan) — encountered while implementing the PLAN-01
hand-off, which orders strict process compliance.

**Contradiction:** Three simultaneously-in-force rules demand mutually exclusive
behavior for the same action (reading/writing plan-scoped `.plan/` files):

1. `AGENTS.md` Hard Rules: ".plan/ access via scripts only — Never
   Read/Write/Edit `.plan/` files directly."
2. `orchestration-model.md` Direct-file-write carve-out: "a deliberate, bounded
   exception to the `.plan/` access via `manage-*` scripts only rule" allowing
   Write/Edit inside the epic tree; plus Small-ops carve-out: "Reads are
   unrestricted in location."
3. `phase-2-refine` Step 12 *mandates* direct Edit/Write of the plan-scoped
   `request.md` (path-allocate flow: `request path` → Edit/Write → `mark-clarified`);
   `manage-solution-outline` likewise mandates "Use Write tool for document
   content, then validate via script (not the script API write path)."

A session that follows (3) violates the letter of (1); a session that follows
(1) cannot complete refine/outline at all. This is the epic §D
forced-violation class ("the compliant path did not cover the use case"):
proposal P2 there already asks for a sanctioned read path for orchestrator
specs (`corpus read --slug --plan`) or recording the carve-out in AGENTS.md.

**What this session did:** followed (2)+(3) — script-mediated where a verb
exists (`manage-files`, `manage-plan-documents`, `manage-tasks`), direct
Read/Edit only for plan-scoped request/solution artifacts where the owning
skill mandates it — and records the deviation here instead of silently.

**Proposed:** AGENTS.md should name the carve-out (one line + pointer to the
orchestration model) so "strict compliance" is decidable; alternatively promote
epic §D P2 (`corpus read`) to a staged fix. Related: `architecture ... info`
rejects `--plan-id` after the subcommand (argparse trap hit twice this
session); the error text states the correct placement, but the doc examples
should show the canonical order once.
