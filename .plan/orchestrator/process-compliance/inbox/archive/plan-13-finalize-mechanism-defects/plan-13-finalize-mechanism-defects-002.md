envelope_version=1
sender_type=plan
sender_id=plan-13-finalize-mechanism-defects
epic=process-compliance
kind=finding
created=2026-09-27T14:34:15Z

# Correction + further process-rule issues (plan-13-finalize-mechanism-defects, refine boundary)

## 1. Correction to message -001 item 1 — the filename theory was wrong; the real defect is two classifiers disagreeing

Message -001 blamed the `PLAN-13-…` filename for missing a code segment. That is refuted:
`orchestrator inbox detect --source-id .plan/orchestrator/process-compliance/plans/PLAN-13-finalize-mechanism-defects.md`
returns `orchestrated: true, epic: process-compliance, detection: orchestrated`.

But the defect I observed is real. The same plan, with the same `request.md` `source_id`, got this from
`manage-status transition --completed 1-init`:

```text
mailbox: checkpoint: phase-transition
  probe: not_orchestrated
  reason: "request.md source_id is not an orchestrator plan-spec pointer (detection=not_orchestrator_pointer)"
```

So the phase-transition mailbox probe in `manage-status` (`MAILBOX_PROBES`, `_cmd_lifecycle.py`) and
`orchestrator inbox detect` give opposite answers for the same input. The transition probe reports
`not_orchestrated` as a *measured fact*, which is the exact confident-but-wrong signal the vocabulary was
built to prevent. Possible causes: the probe ran from a cwd/store where the pointer did not resolve, it
reads a different field, or it matches a stricter pattern. Whatever the cause, the two must share one
classifier.

## 2. The refine clean-main assertion is not concurrency-aware and trips on sanctioned writes

The orchestrator's post-refine assertion (`planning.md` § 2-Refine → Post-dispatch contract assertion) runs
`git -C . status --porcelain` and must stop on any output. After the refine returned, the output was:

```text
 M .plan/orchestrator/process-compliance/epic.md                          <- operator/orchestrator session edit
?? .plan/orchestrator/process-compliance/inbox/plan-12-tool-triage-00{1..5}.md   <- a concurrent sibling plan's inbox writes
?? .plan/orchestrator/process-compliance/inbox/plan-13-finalize-mechanism-defects-001.md   <- this plan's own inbox write
```

The refine wrote none of these. Every entry is a *sanctioned* write to the git-tracked orchestrator store:
the spec's write-boundary explicitly permits the plan's own `inbox/{sender}-{seq}` message, sibling plans
write theirs, and the orchestrator/operator edits `epic.md`. Yet the assertion has no exemption for
`.plan/orchestrator/**`, so a plan in a multi-plan epic hits `refine_contract_violation` whenever anything
else in the epic moves. The same applies to the 1→2 assertion and to the `main_dirty` handshake invariant.

The assertion's guarantee ("this phase did not edit the main checkout") needs a baseline diff: snapshot
porcelain before the dispatch and compare after, or exempt the orchestrator store the same way untracked
`.plan/local/**` is exempt by construction.

## 3. Shared literal staging filename collides across concurrent refine dispatches

The refine sub-agent reported that `.plan/temp/module_mapping.toon` (a fixed filename staged before
`manage-files write --content-file`) was overwritten mid-run by a concurrent phase-2-refine for another
plan (content about "manage-status transition silent-failure triage"). This plan's copy was already persisted
and intact, but the staging path is not plan-scoped, so two concurrent refines can persist each other's
module mapping. Staging paths under `.plan/temp/` must include the plan id.
