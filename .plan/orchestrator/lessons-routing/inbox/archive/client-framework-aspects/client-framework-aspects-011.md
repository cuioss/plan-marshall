envelope_version=1
sender_type=orchestrator
sender_id=client-framework-aspects
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:04:54Z

> Routed from epic `client-framework-aspects` (repository Token-Sheriff) by its orchestrator on 2026-11-24, at the operator's direction. Original message `plan-15-plan-12-residual-fixes-005.md`, sender plan `plan-15-plan-12-residual-fixes`, created 2026-11-24T11:11:41Z. The lessons store of that repository refuses bundle-prefixed `plan-marshall:*` components (`wrong_store`), so the lesson is handed to this repository, which owns the components.
>
> Orchestrator note: record 3 (`manage-change-ledger append --changed-paths-file`) independently confirms the drift in the message from plan-12-documentation-review-consolidation, `-007`, filed beside this one; the orchestrator verified the drift against plugin 0.1.2184 (`phase-5-execute/SKILL.md:830` versus `manage-change-ledger append --help`).

# Candidate lesson: argparse rejections from flags carried over from a sibling verb or a stale workflow doc (manage-findings, orchestrator, manage-change-ledger)

**Source plan:** plan-15-plan-12-residual-fixes
**Signal:** signal_script_failure_clusters_count=3. This message covers 2 of the 3 notations (manage-findings, plan-orchestrator) plus one related uncounted `[ERROR]` line (manage-change-ledger).
**Suggested category:** anti-pattern for the first two; bug (documentation/script drift) for the third
**Suggested components:** plan-marshall:manage-findings, plan-marshall:plan-orchestrator, plan-marshall:manage-change-ledger, plus whichever workflow doc names the stale flag

## Records

### 1. `plan-marshall:manage-findings:manage-findings list --full` (work log 10:38:55Z, exit 2, argparse_rejection)

The call passed `--full`, which `manage-findings list` does not declare. Its declared flags are `--any-checkout --author --bot-kind --component --file-pattern --include-qgate --kind --plan-id --preference-admissible --promoted --resolution --type`. `--full` is a real flag on the sibling `manage-lessons list`, so the caller assumed the two `list` verbs share a flag surface. The need behind it, the full comment bodies, is already met: `manage-findings list` returns the `body` and `raw_input` columns by default, and the output is large enough to be persisted to a result file.

**Rule:** do not carry a flag from one `manage-*` script's `list` to another's. Each `list` has its own flag set, so check its canonical-invocation block. To get full detail from `manage-findings list`, narrow with `--type`, `--resolution` or `--file-pattern`; no flag is needed.

### 2. `plan-marshall:plan-orchestrator:orchestrator inbox detect` with no `--source-id` (work log 07:55:19Z, exit 2, argparse_rejection; phase 5, TASK-007)

`inbox detect` requires `--source-id`. The call omitted it while recording PR #952 review dispositions. Per the lessons-capture workflow, the canonical chain is to read `source_id` first with `manage-plan-documents request read --section source_id`, then pass it to `inbox detect --source-id`. The orchestration verdict is also resolved once at finalize Step 3 entry and forwarded on the prompt body, so a phase-5 task has no need to re-detect.

**Rule:** inside a task, use the forwarded `orchestrated` and `epic` inputs. Call `inbox detect` only with the `source_id` obtained from the request document.

### 3. Related, not in the signal count: `plan-marshall:manage-change-ledger:manage-change-ledger append --changed-paths-file` (work log 07:46:53Z, exit 2)

The logged error reads: "workflow doc names it, script declares --changed-paths". This is a real drift between a workflow document and the script, not an agent invention. The phase-5 per-deliverable commit path (after the TASK-2 commit 9665a889) told the caller to pass a flag the script does not accept. The signal scan did not count it because the line uses the `[ERROR] ... Script ... failed` form, not the `script_failure notation=` marker.

**Corrective action:** fix the workflow document that names `--changed-paths-file`, or add the file variant to the script. Also consider why this failure line does not carry the standard `script_failure` marker, since it escaped signal counting.
