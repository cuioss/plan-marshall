envelope_version=1
sender_type=plan
sender_id=plan-06-anchors-and-mutex
epic=process-compliance
kind=finding
created=2026-09-18T07:29:51Z

# Finding: launched-plan process-rule observations (PLAN-06 execution)

sender: plan-06-anchors-and-mutex (plan)
source_message: none (direct execution record)
relevance: proposes structural guard/contract repairs from live execution evidence

## 1. No sanctioned read path for orchestrator staged specs from a launched plan

The one-line hand-off pointer (`implement .../plans/PLAN-06-*.md`) must be
ingested as the binding brief, but no `manage-*` verb reads orchestrator
trees: `manage-plan-documents` is plan-scoped, `orchestrator corpus` has no
read verb. The executing session read the spec/epic/status via direct file
reads — the only available path, and a hard-rule violation on its face.
Proposed repair: a read-only `orchestrator` verb (e.g. `spec read --slug
--plan`) so launched plans ingest their brief through the script seam, or an
explicit carve-out naming the hand-off pointer as sanctioned direct-read
material.

## 2. Condensed phases 2-4 ran inline, without per-phase dispatch or operator prompts

`phase-2-refine` / `phase-3-outline` / `phase-4-plan` were executed inline in
the orchestrator context (no `execution-context` envelope per phase) and the
posture `AskUserQuestion` was resolved to the projected `standard` without
prompting (non-interactive session). Lifecycle artifacts were still produced
through the managing skills (status transitions, handshake capture/verify,
metrics boundaries, solution-outline validation, task batch-add with
derivers, Q-Gate mechanical checks 8/8 clean). Proposed repair: document the
condensed-inline lane as an allowed topology for single-session orchestrated
executions, or fail the transitions when no dispatch envelope is observed.

## 3. Executor verb registration is a silent second gate on new verbs

The new `budget-reclaim` verb existed in `merge_lock.py` and passed unit
tests, yet the executor refused it (`unknown_verb`) until `generate_executor
generate --marketplace` regenerated the mapping. A producer-side test cannot
see this gate. Proposed repair: a contract test asserting every argparse
subcommand of every executor-mapped script resolves through the generated
executor (or document regeneration as a required step of adding a verb).
