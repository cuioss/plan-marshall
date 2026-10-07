# History: Multi-target architecture completion

slug: multiplattform
closed: 2026-09-15

> Frozen record of a closed epic. Written once, at close, from the epic's final state. `epic.md` and
> the rest of the tree remain on disk unchanged as the full audit record — this document is a
> summary and a closing rationale, not a replacement for it. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the close-freezes-never-deletes
> contract.

## Vision, as pursued

The epic set out to make plan-marshall genuinely target-opaque: runtime seams naming no product, a
scoping mechanism for target-specific components, zero Claude literals outside sanctioned homes, and
a one-command OpenCode developer loop — deliberately carrying live-runtime confirmation on a real
OpenCode install as an out-of-plan-set workstream (WS-05), gated on an operator with an install.

That vision was met. WS-01 through WS-04 shipped 20 plans across their four surfaces (the
`platform-runtime` seam, `marketplace/targets` build machinery, bundle prose and scripts, and the
developer/distribution tooling), all ground-truth verified rather than trusted from run reports. WS-05
closes **resolved, not executed** — see below.

## Queue outcome, per plan

| Plan | Workstream | Outcome | PR / Landing |
|------|------------|---------|--------------|
| PLAN-01 runtime-seam-neutrality | WS-01 | landed | #1291 — landings/PLAN-01.md |
| PLAN-02 target-scoped-components | WS-02 | landed | #1313 — landings/PLAN-02.md |
| PLAN-03 claude-literal-residuals | WS-03 | landed | #1319 — landings/PLAN-03.md |
| PLAN-04 sync-opencode-inner-loop | WS-04 | landed | #1372 — landings/PLAN-04.md |
| PLAN-19 repoint-ingested-epic-citations | WS-02 | landed | #1374 — landings/PLAN-19.md |
| PLAN-16 lint-scope-marketplace-targets | WS-02 | landed | #1375 — landings/PLAN-16.md |
| PLAN-13 chat-signal-transcript-boundary | WS-03 | landed | #1376 — landings/PLAN-13.md |
| PLAN-05 structural-directive-coverage | WS-02 | landed | #1379 — landings/PLAN-05.md |
| PLAN-08 permission-skills-through-the-registry | WS-01 | landed | #1393 — landings/PLAN-08.md |
| PLAN-09 runtime-seam-completeness | WS-01 | landed | #1405 — landings/PLAN-09.md |
| PLAN-14 permission-web-and-rule-pack-class | WS-01 | landed | #1408 — landings/PLAN-14.md |
| PLAN-20 sync-opencode-prune-boundary | WS-04 | landed | #1418 — landings/PLAN-20.md |
| PLAN-15 repo-scoping-design | WS-02 | landed | #1420 — landings/PLAN-15.md |
| PLAN-21 worktree-executor-root-resolution | WS-03 | landed | #1444 — landings/PLAN-21.md |
| PLAN-22 permission-grammar-residue | WS-03 | landed | #1452 — landings/PLAN-22.md |
| PLAN-06 authoring-surface-target-awareness | WS-03 | landed | #1456 — landings/PLAN-06.md |
| PLAN-07 runtime-fact-prose-and-single-sources | WS-03 | landed | #1458 — landings/PLAN-07.md |
| PLAN-12 cross-bundle-assistant-prose | WS-03 | landed | #1460 — landings/PLAN-12.md |
| PLAN-11 target-scoping-adoption | WS-02 | landed | #1438 — landings/PLAN-11.md |
| PLAN-10 layout-and-executor-residuals | WS-03 | landed | #1449 — landings/PLAN-10.md |
| **PLAN-17** pin-opencode-install-path | WS-05 | **parked, discharged via sibling epic** | not run from this epic |
| **PLAN-18** opencode-user-documentation | WS-05 | **parked, partially discharged, residual accepted** | not run from this epic |

20 of 22 specs landed. PLAN-17 and PLAN-18 close `parked` — not `shipped`, not `dropped` — because
their objective was substantially met by work outside this epic, and the vocabulary has no
"superseded" state; see below.

## WS-05: resolved via a sibling epic, not executed

WS-05's charter blocked on a precondition no plan inside this epic could satisfy: an operator running
`reference/opencode-validation-protocol.md` against a live OpenCode install. On 2026-09-15 the
operator reported that OpenCode plans had since run for real. Verified against ground truth rather
than accepted on the report alone:

- `tooling-truthfulness/PLAN-07-opencode-install-docs.md` (PR #1484, squash `14fe203c869f`, shipped
  2026-09-13) ran D0 — testing the candidate consumption paths from THIS epic's own validation
  protocol — against a **live OpenCode 1.18.30 install**, per its own landing report: marketplace-add
  and the npm-plugin path tried-and-rejected, no fourth path invented, the manual config-dir deploy
  via the generator + `/sync-opencode` pipeline pinned as the primary observed-working path.
- Corroborated three ways: the sibling epic's own landing record; `corpus cross-check` reporting a
  live surface collision between `PLAN-17` and `tooling-truthfulness/PLAN-07` on
  `marketplace/targets/opencode/**` and `doc/developer/distribution.adoc`; and that sibling epic's own
  2026-09-11 Decisions entry recording the operator's deliberate choice to stage this duplicate work
  there rather than unpark WS-05 here.
- PLAN-07 also shipped README + split `install-claude.adoc`/`install-opencode.adoc` install
  documentation and consistent multi-assistant framing, discharging PLAN-17's D1/D2 and PLAN-18's
  D1/D4.
- **Not discharged, and explicitly accepted as deferred rather than silently dropped:** PLAN-18's D2
  (the per-operation real-vs-`no-op` orientation layer over `platform-runtime/standards/contract.md`)
  and D3 (the confirmed-limitations record). No artifact in `tooling-truthfulness`'s shipped set
  addresses either.
- One part of the operator's report was checked and **not** corroborated: "three OpenCode plans
  currently running in parallel." Every active orchestrator epic's `status.json` was read; only one
  plan anywhere (`model-provisioning/PLAN-02`) carried `running` status, and this checkout's
  `.plan/local/plans/` held no active plan directory. This did not change the disposition — the
  load-bearing evidence is the already-landed PLAN-07 — but it is recorded as an unverified lead
  rather than folded silently into the corroborated half.

Both specs are annotated in place (see `plans/PLAN-17-pin-opencode-install-path.md` and
`plans/PLAN-18-opencode-user-documentation.md`) naming this discharge and the residual gap, so a
future reader opening either spec directly sees the resolution without needing this document.
**PLAN-18's D2/D3 are open, accepted debt** — should this work be wanted later, it needs a fresh plan
spec staged elsewhere (its premises here predate the sibling epic's actual findings), not a re-run of
this epic's stale PLAN-17/PLAN-18.

## Decision record

The full, dated decision log with rationale and alternatives lives in `epic.md`'s `## Decisions`
section (narrative, preserved verbatim by the compact stage) and the append-only
`logs/decision.log`. Highlights carried forward:

- The epic was created by ingesting the standalone `doc/plans/multiplattform/` tree, trading the
  cloud-lane's no-queue/no-disjointness-check model for orchestrator machinery once the plan count and
  collision graph outgrew it.
- `parallelization_scope` was set to 2, and live OpenCode validation was carried as a blocked
  workstream (WS-05) rather than as emittable queue rows from the start — the cloud lane cannot supply
  the operator-at-a-terminal the protocol needs.
- Two specs (PLAN-06, PLAN-07) and a third (PLAN-10) proceeded unsplit past the ~6-deliverable
  scope-bloat guard, each with a recorded rationale.
- 2026-09-15: WS-05 resolved via the `tooling-truthfulness` sibling epic (this document's own
  subject, above).
- 2026-09-15: cleanup's re-grounding pass (128 claims / 22 specs at HEAD `fb8aadc9c`) declined bulk
  per-claim verdict persistence on the 20 already-landed specs — no admission-gate consequence
  remains for a closing epic — folding its substantive findings into `epic.md` instead. Notable: the
  `Runtime` ABC's `@abstractmethod` count is now 33 (was 24–25 at various staging times);
  `.claude/skills/sync-opencode/` no longer exists, relocated by an out-of-epic commit to
  `.opencode/scripts/sync_opencode.py`.

## Unresolved defects and watches, carried forward as leads

`epic.md`'s `## Open Defects` and `## Watches` sections remain on disk, unmodified by this close, and
are the authoritative carry-forward record — this document does not duplicate them. At close, the
open (non-retired) items of most consequence are:

- **PR #1445 open across seven landings**, its subject now partly overtaken by a later, adjacent fix
  (#1461) — needs re-reading before merge.
- **An `IN_PROCESS` build-gate run writes no change-ledger entry**, the mechanism behind a prior
  misleading all-failures ledger read. No staged spec owns the build-gate surface.
- **An orchestrator/executor tooling cluster** (the `corpus set-verdict` claim-index hazard, the
  `queue --transition` unvalidated status token, the executor self-heal wrong-depth walk, the
  worktree self-hosting gap) — four instances of one failure mode (fails quietly, not loudly),
  identified as warranting its own plan, out of this epic's scope.
- **A staged spec's work list can decay silently as siblings land** — no mechanism compares a landed
  plan's realized footprint against other staged specs' site lists; recorded as a structural gap, not
  an instance.
- **The disjointness gate is blind to path containment** — a glob and a path it contains produce no
  overlap row; binding operational consequence until fixed: hand-check sibling epics' declared
  surfaces before emitting or launching a plan that declares a test-tree glob.
- **`permission_fix.py`'s permission-DSL residue is unclaimed** since PLAN-08 landed without touching
  it; needs an operator decision on whether to stage a plan.
- Several closed/retired items (test-count instability, the CodeRabbit unobtainable-arm exposure, two
  false-clean disjointness verdicts, the PLAN-130 near-miss, the WS-05 protocol watch this document's
  own subject retires) are marked `✅ CLOSED` / `✅ RETIRED` in place in `epic.md` and are not repeated
  here.
- Several standing operator-only items remain genuinely unresolved and are not plan work: the
  Grep-credentials-deny-set policy question (PLAN-03's explicit decision), the reviewer-policy change
  enacted but unrecorded in git (documented only in a git-ignored local file), and whether a local
  OpenCode RUNBOOK edit was made during the PLAN-21 run.

## Closing rationale

WS-01 through WS-04 are complete and ground-truth verified. WS-05's blocking precondition — a live
OpenCode install running the validation protocol — has been satisfied, not by a plan launched from
this epic, but by a sibling epic's deliberately-staged duplicate work, with the resolution documented
above and on both affected specs. The remaining WS-05 scope (PLAN-18 D2/D3) is accepted, deferred
debt rather than executed or silently dropped. `cleanup`'s corpus pass found the queue and specs fully
reconciled (22 queue rows / 22 spec files, both directions), the ledger's two derivable blocks already
correct (`compact` reported `epic_changed: false`), and the restart-readiness verdict `ready` (5 of 5
scored signals). There is no remaining runnable work inside this epic — closing is the correct action
rather than a deferral of unfinished work.
