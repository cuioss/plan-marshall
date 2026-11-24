envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:06:59Z

component=plan-marshall:phase-3-outline
category=improvement
title=Outline and plan: search the whole doc corpus for statements of the old state before naming the affected files
source_lesson=2026-11-18-07-001
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-18

# Outline and plan: search the whole doc corpus for statements of the old state before naming the affected files

# Candidate lesson: outline missed stale "JGit approval pending" statements outside the deliverable

- Source signal: Q-Gate finding 9fe2d8 (phase 3-outline, scope_criterion_validator, under_coverage, deliverable 3, severity warning)
- Resolution in run: taken_into_account. The operator chose to add both files to deliverable 3.

## What happened

Deliverable 3 updated the documentation for JGit becoming a managed, declared dependency. Two documents outside its affected files still said the owner's approval of JGit was pending:

- doc/specification/git-core.adoc line 9
- doc/concepts/git-as-document-persistence.adoc, Open Questions item 2

## Candidate rule

When a plan changes the state of a dependency or decision, search the whole doc corpus for statements of the old state (for example "pending approval" or "planned"). Do not search only the files the outline already names. The affected-files list should come from that search.


## Recurrence in the same run (second finding of the same kind, one phase later)

- Source signal: Q-Gate finding 8feafc (phase 4-plan, scope_criterion_validator, under_coverage, deliverable 3, severity warning)
- Resolution in run: fixed. Task 5 was changed to name the two sentences. The outline stayed unchanged.

## What happened

A success criterion said that no changed document may still say the owner's approval of JGit is pending. Two changed files still held sentences that the change list for the file did not name:

- doc/concepts/module-structure.adoc lines 97-98 ("Every one of these dependencies, JGit included, needs the owner's approval")
- doc/specification/general.adoc lines 28-30 ("Every other dependency below is planned and needs the owner's approval")

## Candidate rule

This is the second finding of the same kind as 9fe2d8 in this run, and it came one phase later. When a criterion is a content rule over changed files ("no file says X"), run that content search during planning. Name every match in the change list for its file. Do not list only the obvious state cells.


## Recurrence in the next plan (git-core-import, inbox git-core-import-006 and -007)

- Source signal: Q-Gate findings 900556 (doc/README.adoc) and 26b80e (README.adoc), phase 3-outline, scope_criterion_validator, under_coverage, deliverable 5. Resolution in run: taken_into_account; the operator added both files to deliverable 5.

## What happened

Deliverable 5 ("documentation agrees with the code") listed AGENTS.md and the specification but not README.adoc (lines 40-42, "git-core and git-worktrees are scaffolds") nor doc/README.adoc (lines 111-113, "only GDR-TEST-1/2 are implemented"). After the code deliverables the index would have contradicted the specification.

## Candidate rule

The same rule, third and fourth hit in two plans. In this repository the module state is stated in three places (AGENTS.md "Current state", README.adoc module paragraph, doc/README.adoc Specification section), so a plan that moves a module out of the scaffold state or implements GDR requirements lists all three up front. The orchestrator side of this is folded into the staged specs of the epic.


## Recurrence in a later plan (git-core-incore-write-cas, inbox git-core-incore-write-cas-003)

- Source: Q-Gate finding 04f7cd (phase 4-plan, `scope_criterion_validator` under_coverage, deliverable 4), resolved `taken_into_account`.
- Deliverable 4 stated GDR-CORE-4 and GDR-CORE-5 as implemented across the documents, but its affected files omitted the root `README.adoc`, whose module table and `git-core` content list would then have described the module state incompletely and differently from `doc/README.adoc`, `general.adoc`, `module-structure.adoc` and `AGENTS.md`. A content search over the implemented-state wording surfaced it; `README.adoc` was added as step 6 of TASK-009.
- The `git-core` implemented-state wording lives in at least five places (root `README.adoc`, `doc/README.adoc`, `doc/specification/general.adoc`, `doc/concepts/module-structure.adoc`, `AGENTS.md`). Four of them (`doc/README.adoc`, `AGENTS.md`, `README.adoc`, `doc/specification/general.adoc`) also conflicted by hand at the finalize rebase onto `origin/main`, because sibling plans update the same state lists.

Same root cause and same rule: derive the documents to list by a content search over the state wording, not from memory. A deliverable that changes a module's state must list all of them.


## Recurrence in a later plan (plan-20-leftover-fixes-2, inbox plan-20-leftover-fixes-2-002)

Q-Gate finding 16006b (phase 3-outline, under_coverage): D2 documented the bare-root refusal (PATH_REFUSED) and corrected a stale reservation sentence in the Javadoc and the git-core specification only; `doc/specification/general.adoc` (GDR-GEN-3 row PATH_REFUSED) and `doc/clients/pm-mcp-core.adoc` (Concurrent additions) carried the same stale wording and were not in the affected files, against the Done-when clause "no document lists an outcome the code does not return". Rule restated: when a deliverable corrects a sentence, content-search all documents for that sentence and list every hit, instead of fixing the file where the defect was first seen.
