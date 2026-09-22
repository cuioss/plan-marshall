envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-22-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-22T07:15:02Z

# Candidate lessons routed from lessons-handling-26-09-22-01

Bundled batch of 18 lessons from the local `.plan/local/lessons-learned/` corpus (2026-08-24 through
2026-09-21 vintage), ground-truth-scanned and matched to this epic's "confident signal hides a caveat"
theme. Each is still `active` in the source corpus at routing time; none is known superseded by shipped
work (spot-checked the closest lookalike — `2026-09-21-13-003` below — against `PLAN-TRUTH-144`/PR#1560
and confirmed it is a DIFFERENT code path, not already fixed).

## Self-review / loop-back staleness
- **2026-09-21-10-003** + **2026-09-21-10-005** (cross-ref pair): a round-loop fix can self-seed the next
  instance of its own defect class; self-review findings go stale against a moving HEAD, costing no-op
  finalize loops. Likely overlaps this epic's own `PLAN-TRUTH-173` (self-review instrument vacuity modes)
  — check for absorption before staging as new.

## Test-methodology vacuity (persona-module-tester)
- **2026-09-19-21-006**: a monkeypatched resolver turns every fixture constant on its far side into an
  assertion nothing verifies — a production element was reclassified mid-PR, the fixture kept passing
  because the resolver that would have read the reclassification was mocked.
- **2026-09-21-10-009**: a publisher and its registration row are one edit, not a follow-up.
- **2026-09-21-10-011**: a guard's stated scope must be derivable from its mechanism (frozenset
  within-set vacuity — a guard that can't see outside its own frozenset can't detect the class it
  claims to guard).

## Meta-project tooling (pm-plugin-development:plugin-script-architecture)
- **2026-09-21-10-006**: a population-derived guard walking ONE document under-covers a roster split
  across TWO governing documents.
- **2026-09-21-10-007**: a deliverable named the dispatch wrapper, not the module actually defining the
  symbol. No dedicated owner epic exists for this component; routed here as the closest tooling-defect
  fit — reroute if you disagree.

## manage-lessons write-path (NOT covered by PLAN-TRUTH-144)
- **2026-09-21-13-003**: `set-body` writes the new body over the returned path and destroys the
  metadata header `add` wrote. Verified: PLAN-TRUTH-144/PR#1560 (`05b5d1ac4`) touched `manage-lessons.py`,
  `_lessons_io.py`, `_lessons_query.py` for the `add`/`remove`/resolution paths only — `cmd_set_body` was
  untouched by that diff. This is a live, distinct gap in the same "confident write corrupts a record"
  archetype.

## Early-phase gate decidability (phase-2-refine / phase-3-outline)
- **2026-09-19-21-005**: when a deliverable names a verification command, run that command's rule
  against the specified change before writing it — a deliverable was self-contradictory against its own
  named gate, decidable at outline time.
- **2026-09-20-08-011**: orchestrator-authored staged specs systematically trip phase-2-refine's
  suspicious-perfect-confidence heuristic. Six dimensions scoring 100 is EXPECTED for a spec an
  orchestrator already pre-verified with OBSERVED/HYPOTHESIS claim labeling, not suspicious — the check
  may need an orchestrated-spec-aware arm. Provenance: surfaced during `orchestrator-refactor` PLAN-04
  (PR #1543); that epic is independently tracking its own staged-spec 2-refine score population as a
  Watch and can supply the derived count this needs before you act on it — cross-reference rather than
  re-derive.

## Doc/hook/skill drift (each independently verified against its stated skill)
- **2026-09-20-07-001**: `finalize-step-deploy-target` documents a bare `./pw generate-claude`, blocked
  by the hard-rule hook; `architecture resolve` has no registered canonical form for it either.
- **2026-09-20-07-002**: `finalize-step-sync-plugin-cache` SKILL.md still prescribes the retired
  underscore notation `manage_status` (fallout from commit `4804b6976`'s identifier-vocabulary decision).
- **2026-09-21-10-002**: hand-maintained doc enumeration of a code-declared set drifts (17 findings
  across two independent detectors on one plan reduced to this one shape) — corrective rule: point at
  the declaring source, never restate its members; derive-and-assert-equality when a rendered table is
  unavoidable.

## Footprint/PR-landing prose-vs-structured divergence (cross-referencing pair)
- **2026-09-20-08-007**: `realized_footprint` is captured from pre-rebase worktree state and never
  re-derived against the merge commit — a rebase collapsed one file's change to a no-op and the record
  over-claimed it as shipped.
- **2026-09-21-08-004** (see below, bundled with the other 3 malformed-header ones) cross-references this
  one from the opposite direction (capture-before-branch-cleanup vs reconcile-after-merge) — read both
  together.

## Four lessons with unparseable metadata headers (all from plan `tracked-orchestrator-store-resolver`, 2026-09-21)
`manage-lessons aggregate`/`get` cannot parse these — they read as well-formed retrospective analysis
(not a script bug; they look hand-authored directly into files rather than filed via `manage-lessons add`)
but carry no `component=`/`category=` header. Forwarding their full content since it's substantive and
otherwise invisible to any tooling:

- **2026-09-21-08-001** — "Gate PR diff size before finalize enters the review-bot wait region": three
  finalize steps each measured a 4028-file diff privately and published nothing; no consumer between
  measurement and `create-pr` reads a footprint-size fact. 69.2% of the plan's script wall time was
  spent polling two bots structurally incapable of reviewing the diff. Proposed: publish
  `files_total`/`insertions_total`/source-vs-data split from `compute-footprint`, gate at push/create-pr
  against GitHub's 65536-char comment cap and Sourcery's 300-file fetch cap.
- **2026-09-21-08-002** — "A sweep deliverable must re-derive its population against scope a sibling
  changes": a sweep's declared survey scope was correct for the repo as it stood when the sweep ran, and
  wrong for the repo the SAME plan was creating (a `.gitignore`→tracked transition mid-plan). Live
  residue: `code-intelligence-substrate/cloud-runs/_audit/analyze.py` still hardcodes the pre-relocation
  address on `origin/main` today — see the direct notice sent to that epic.
- **2026-09-21-08-003** — "Step records done claiming findings fixed while its findings ledger stays
  pending": `automatic-review` recorded `outcome: done` while `manage-findings list --resolution pending`
  returned all 5 of its findings still pending; one (`6f47cd`, hardcoded paths in `analyze.py` — same
  file as 08-002 above) was never actually fixed. Prose and the structured ledger diverged and nothing
  cross-checked them.
- **2026-09-21-08-004** — "An ad-hoc PR split leaves the plan PR pointer naming a closed-unmerged PR":
  `create-pr` stamped `pr_number: "1555"`; the operator closed it unmerged and landed as `#1557`+`#1558`
  instead, recorded only in a `display_detail` prose sentence. Four of sixteen retrospective aspects
  could not grade the plan because every footprint tier resolved against the dead PR. Cross-references
  `2026-09-20-08-007` above from the opposite direction.

## Disposition
All 18 are `standalone`/`clustered-into` per the local dedup pass — none `already-covered` except the
verified-live check on 13-003. Source lesson files will be removed from `.plan/local/lessons-learned/`
after this message is confirmed queued (per the mode contract's integrate-then-remove ordering).
