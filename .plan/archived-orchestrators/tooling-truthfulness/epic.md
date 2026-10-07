# Epic: The orchestration machinery reports what it actually checked

slug: tooling-truthfulness

> Ledger document for one epic under `.plan/orchestrator/tooling-truthfulness/`. The
> layout and authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

The `multiplattform` epic spent twenty landings making plan-marshall's *content* honest about which
assistant it assumes. Along the way it accumulated a set of defects in the machinery that was doing
the checking, and they share one shape: **a could-not-evaluate reported as a clean result.** A gate
that compares an empty set and reports no collision. A ledger that records six failures for a run
that was green. A status transition that accepts a token nobody validated. A test that asserts on
its own source text and calls that a behavioural pin.

This epic closes that set. It is not a continuation of `multiplattform` — that epic's subject was
multi-target architecture, and these are its own tools — but it inherits the standard
`multiplattform` established and holds itself to it: **an audit separates what it could not evaluate
from what it evaluated and found wanting** (ADR-019). Every member here is an instance of failing
that separation.

"Done" is: every recorded member either fixed with a red-first guard that distinguishes *checked and
clean* from *could not check*, or closed with a positive account of why it needs no fix. ⛔ The
standard applies reflexively — a fix that cannot be shown to fail before it lands is exactly the
vacuous pin this epic exists to remove.

## Provenance and inherited constraints

⚙️ **Every member was verified live against HEAD before staging**, not carried over on the strength
of a ledger entry. `multiplattform` demonstrated repeatedly that its own defect list went stale as
plans landed — six entries were found already closed during the survey that produced this epic — so
each row here names what was observed and when.

⚙️ **EMIT FORM — this epic emits `/plan-marshall` one-line pointers.** Resolved on operator direction
2026-09-10 (supersedes the earlier runbook-command form). Per `orchestrate.md` Step 5, every emitted
command takes this shape, verbatim:

```text
/plan-marshall task="implement .plan/orchestrator/tooling-truthfulness/plans/PLAN-NN-{plan-name}.md"
```

The pointer is the whole hand-off: `phase-1-init` ingests the referenced spec file's contents through
the `request create --body-file` seam, so the spec becomes the request body and no brief is
transcribed into the command. The spec is the single source of the brief.

⛔ **`multiplattform` CANNOT CLOSE until its leftovers are staged here.** Recorded as that epic's
close precondition on operator direction. This epic's existence discharges it; a member dropped from
this queue without a recorded disposition re-opens it.

⚠️ **Scope note.** `parallelization_scope` is **2**, but expect the second slot to go unfilled more
rounds than not: most members touch overlapping orchestrator surfaces (`orchestrator.py`, the
executor, the surface parser). A shortfall at scope 2 is the normal case here, not a failure. The
genuinely disjoint work is the repo-hygiene chore and the test-falsifiability survey.

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary --slug tooling-truthfulness
     Paste the returned `summary` block verbatim between the markers (the same
     invocation also emits `ordered_queue` for the Ordered Queue section below).
     Anything a reader wants to add BY HAND goes in the annotation zone below,
     outside the markers — never inside them. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: PLAN-01..08 shipped (#1466/#1468/#1469/#1472/#1476/#1482/#1484/#1487); inbox drained 5/5. Queue empty. NEXT: close the epic.
**Phase**: orchestrating
**Inbox (derived)**: 0 queued, 37 archived
**Queue** (staged, in order):
- (empty)
- PLAN-01 (WS-02) — plan=plan-01-script-surface-validation — PR 1466 — landing=landings/PLAN-01.md — status: shipped
- PLAN-02 (WS-04) — plan=plan-02-repo-hygiene-residues — PR 1468 — landing=landings/PLAN-02.md — status: shipped
- PLAN-03 (WS-03) — plan=build-path-evidence — PR 1469 — landing=landings/PLAN-03.md — status: shipped
- PLAN-04 (WS-01) — plan=implement-plan-04-gate-comparability — PR 1472 — landing=landings/PLAN-04.md — status: shipped
- PLAN-05 (WS-01) — plan=implement-plan-05-declaration-currency — PR 1482 — landing=landings/PLAN-05.md — status: shipped
- PLAN-06 (WS-05) — plan=implement-plan-06-test-falsifiability-survey — PR 1476 — landing=landings/PLAN-06.md — status: shipped
- PLAN-07 (WS-06) — plan=implement-plan-07-opencode-install-docs — PR 1484 — landing=landings/PLAN-07.md — status: shipped
- PLAN-08 (WS-02) — plan=implement-plan-08-slug-semantics-model-compliance — PR 1487 — landing=landings/PLAN-08.md — status: shipped
<!-- END GENERATED: resume-summary -->

### Annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated markers.
     A regeneration replaces only what sits BETWEEN the markers, so everything written
     here survives it. -->

- {PLAN-NN} — {annotation the generator does not produce}

## Ordered Queue

<!-- GENERATED BLOCK — never hand-write or hand-edit the table between the markers.
     Regenerated from status.json and the staged specs: emitted as `ordered_queue` by
     orchestrator.py resume-summary --slug tooling-truthfulness (paste it verbatim after a
     queue change), and rewritten in place by the compact stage at cleanup. Only the LIVE
     queue is rendered here. Per-row notes a reader wants to ADD go in the annotation zone
     below, outside the markers — never inside them. -->

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| — | (empty) | — | — | — |
<!-- END GENERATED: ordered-queue -->

### Queue annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated table markers. -->

- {PLAN-NN} — {sequencing / disjointness / caveat the generator does not derive}

## Decisions

- 2026-09-10 — **Epic created for the `multiplattform` leftovers.** Alternative considered and
  rejected: folding them into `multiplattform` as further WS-03 plans. Rejected because that epic's
  subject is multi-target architecture and these are its own tooling; keeping them there would have
  made its close conditional on unrelated work. Recorded instead as `multiplattform`'s close
  precondition.
- 2026-09-10 — **`parallelization_scope` = 2** (operator override of the project default 1).
  Rationale: the chore and survey members are genuinely disjoint from the orchestrator cluster.
  ⚠️ The orchestrator members are not disjoint from each other, so shortfall is expected.
- 2026-09-10 — **Emit form is the OpenCode runbook command**, carried from `multiplattform` by
  operator direction, not re-derived.
- 2026-09-10 — **Emit form REVERSED to `/plan-marshall` one-line pointers** on operator direction.
  The runbook-command form is retired; the OpenCode plan lane is no longer the execution path for
  this epic. Every plan spec's Hand-Off Command was rewritten in the same act, and this epic's own
  constraints are updated to match. The `multiplattform` provenance that carried the runbook form
  does not bind this epic beyond the operator's direction, which has now changed.
- 2026-09-11 — **PLAN-07 staged despite an accepted cross-epic duplication.** On operator direction,
  this epic stages `PLAN-07-opencode-install-docs` (WS-06, new workstream) for the README + user-guide
  OpenCode install documentation. This deliberately duplicates `multiplattform` PLAN-18
  (opencode-user-documentation) and PLAN-17 (pin-opencode-install-path), both PARKED in that epic's
  WS-05. The operator was offered the routing fork (route to multiplattform / unpark multiplattform /
  stage here) and chose to stage here. The duplication is recorded in the WS-06 charter and PLAN-07's
  Dependencies; whichever of the two lands second must re-read the other's spec first. ⛔ The park's
  reason is NOT lifted: the OpenCode consumption path against the published refs is still unvalidated
  on a live install, so PLAN-07's docs label every consumer-path step OBSERVED/HYPOTHESIS rather than
  claiming validation.
- 2026-09-11 — **D0 folded into PLAN-07** (on operator direction, after research). Research
  established OpenCode has no native marketplace command; its plugin surface is npm/local JS-TS
  files, skills/agents/commands are discovered from config dirs, and `opencode plugin` installs
  npm-style packages, not a plan-marshall-style bundle. D0 tests the three candidate consumption
  paths from `multiplattform`'s validation protocol against a live install, pins the primary, and
  produces a consumer install script only if the pinned path needs one. Expected Surface updated in
  the same act (+1 HYPOTHESIS entry, `marketplace/targets/opencode/**`); PLAN-07 remains
  declarative.
- 2026-09-11 — **`/sync-opencode` excluded as a D0 consumer candidate** (operator direction). It is
  a command that exists only in the plan-marshall repo, so a consumer of the published refs cannot
  run it. D0 retains the deploy *shape* (generated tree → config dir, singular→plural rename) as
  candidate (a); the command itself is out of scope. Recorded in PLAN-07's Claim Labels and the
  WS-06 charter.
- 2026-09-11 — **PLAN-01 shipped as #1466** (squash `53ab7dd`, report `landings/PLAN-01.md`).
  Both deliverables corroborated at HEAD; no collision with concurrently-running PLAN-02
  (disjoint surfaces held). PLAN-04/PLAN-05 sequencing hold lifts — both were held behind
  PLAN-01's landing analysis and are now pairable. Inbox drained 6/6 (1 landing reconciled,
  2 candidate-lessons promoted to corpus `2026-09-11-19-001`/`-002`, 3 discarded with rationale).
- 2026-09-11 — **PLAN-02 shipped as #1468** (squash `db0bfff85`, report `landings/PLAN-02.md`).
  D1 (CROSSING-INVENTORY.md deleted, 68 lines) + D2 (`fmt`/`format` cover `marketplace/targets/`)
  corroborated at HEAD; no collision with concurrently-running PLAN-03 (disjoint surfaces held).
  Residual watch from the PLAN-01 analysis resolves: the file's disposition (removed, not
  relocated) is recorded. Inbox already empty — no drain owed.
- 2026-09-12 — **PLAN-03 shipped as #1469** (squash `ca84fe7e`, report `landings/PLAN-03.md`).
  D1 (`_append_gate_build_row` seam + red-first tests) + D2 (self-heal depth pinned at
  max_depth=6/deepest-4, fail-closed) corroborated at HEAD; no collision with
  concurrently-running PLAN-04 (disjoint surfaces held). Inbox drained 4/4 (1 landing
  reconciled, 1 lesson promoted to corpus `2026-09-12-08-001`, 1 folded as recurrence into
  `2026-09-11-19-001`, 1 discarded as recurrence of the remediated-in-run review class).
  `origin/main` 2 unrelated dependabot commits ahead — no epic action.
- 2026-09-12 — **PLAN-04 shipped as #1472** (squash `367558e3d`, report `landings/PLAN-04.md`).
  D1 (containment-aware overlap, stem + `/`-boundary) + D2 (indeterminate live-plan
  population) corroborated at HEAD; describe-side updates rode the same act; one accepted
  incidental (uv.lock specifier sync, versions unchanged). Inbox drained 9/9 (1 landing
  reconciled, 2 lessons promoted to corpus `2026-09-12-17-001`/`-002`, 5 folded as third-plan
  recurrence into `2026-09-11-19-001` — argparse drift now systemic across 3 plans,
  1 discarded as duplicate of the outline-sync promotion). PLAN-05's sequencing hold lifts —
  its colliding counterpart landed.
- 2026-09-13 — **PLAN-06 shipped as #1476** (squash `dc676c43`, report `landings/PLAN-06.md`).
  D1 (9-site survey, keep 6 / replace 3 — population re-derived per spec, not manufactured) +
  D2 (3 behavioural replacements with matched controls, red-first) corroborated at HEAD
  (merge stat exactly the 4 plan files); no collision with concurrently-running PLAN-05
  (disjoint surfaces held). Review mechanics per paste (CodeRabbit mandatory finding fixed
  with negative control, quota-refusal recovery via close-and-reopen). Inbox drained 3/3
  (1 landing reconciled, 1 lesson promoted to corpus `2026-09-13-09-001`, 1 folded as
  recurrence into `2026-09-06-07-003`). No broad-class hand-off to `test-quality` — the
  survey reported none.
- 2026-09-13 — **PLAN-05 shipped as #1482** (squash `3a79a9a6`, report `landings/PLAN-05.md`).
  D1 (`corpus declaration-currency` verb) + D2 (`surface_delta` drain field, mechanism not
  prose — spec's verify-first clause honoured) corroborated at HEAD; D2 live-proven by this
  drain's own `surface_delta` block (unmeasured, base `origin/main` fresh). Superseded #1478
  correctly excluded. No collision with concurrently-running PLAN-07 (docs vs orchestrator
  surfaces). Inbox drained 8/8 (1 landing reconciled, 3 lessons promoted to corpus
  `2026-09-13-12-012`/`-013`/`-014`, 2 folded as recurrence into `2026-09-11-19-001` and
  `2026-09-12-08-001`, 2 discarded as shipped-with-tests). Queue now holds only running
  PLAN-07 — nothing left to emit.
- 2026-09-13 — **PLAN-08 staged** (slug-semantics + Muse-compliance instrumentation,
  WS-02) on operator direction after the Watch trigger fired; Open Defect retired as absorbed.
- 2026-09-13 — **PLAN-07 shipped as #1484** (squash `14fe203c`, report `landings/PLAN-07.md`).
  D0 pinned OBSERVED on live opencode 1.18.30 (marketplace-add + npm tried-and-rejected, no
  fourth path, no consumer script); D1–D3 corroborated at HEAD with zero residual
  `installation.adoc` references tree-wide. Realized-vs-declared delta: +1 disclosed
  (`manage-locks/SKILL.md`, operator-accepted fix-in-branch) and −1 unused conditional
  (`targets/opencode/**`). Inbox drained 1/1 (landing reconciled). Queue now holds only
  staged PLAN-08 — emit next.
- 2026-09-14 — **PLAN-08 shipped as #1487** (squash `19143cbe`, report `landings/PLAN-08.md`).
  D1 (decompose Step 5 semantic) + D2 (duplicate-slug lint, `invalid_field` reuse) + D3
  (shared-slug detector + `epic_slug_matches`) corroborated at HEAD; D4 delivered as
  mechanism (in-epic red-first gates + out-of-epic testable proposals, no prose rule —
  spec bar held). Review: 3 Major + 1 Major + 2 Minor across three rounds, all fixed
  (4/4 resolved, Low); merge under second barrier-ask-override in epic (quota refusal,
  0 pending, CI green). Inbox drained 5/5 (1 landing reconciled, 3 folded as fifth-plan
  argparse recurrence into `2026-09-11-19-001`, 1 absorbed folded-log triage with no new
  defect, 1 discarded as third remediated-in-run review instance). Queue EMPTY — close next.

## Open Defects

{Members are staged as plan specs, not carried here. This section holds only defects surfaced
AFTER decomposition that no staged plan yet owns.}

- (none open — the queue-slug-semantics defect staged as PLAN-08 on operator direction;
  entry retired 2026-09-13, see Decisions.)

## Watches

- **`inspect.getsource` appears across 8 test files** and only one (`test_permission_web.py:169`)
  is a confirmed vacuous pin. Whether the rest are legitimate uses or a class is one sweep away, and
  that sweep is the survey member's first act. — *re-check trigger: the survey's finding; if the
  class is real it may belong to the sibling `test-quality` epic, which already owns anti-vacuity
  work (#1430 / #1443), rather than here.*
- **The `targets:` mechanism versus a per-target ignore manifest** is a live design question
  recorded in `multiplattform` and untouched by fifteen verification rounds. It is NOT staged here
  — it needs an operator decision, not a plan. — *re-check trigger: an operator decision, or a third
  plan tripping over the choice.*
- **Re-enabling the OpenCode effort lever.** Commit `2ec552ba4` (#1464) made every
  `execution-context-{level}` / `execution-context-reader-{level}` OpenCode variant inherit-only —
  no `model:`/`reasoningEffort:` frontmatter — so all levels dispatch on the session model,
  ignoring `marshal.json` effort. Delivered out-of-band to unblock dispatch (which was additionally
  held up by an OpenCode billing balance). This epic's plans (01, 04, 05) touch `orchestrator.py`,
  NOT the targets; the change is recorded here because it alters what the effort seam actually does
  for the OpenCode target. — *re-check trigger: operator tops up the OpenCode billing balance and
  directs re-enabling per-level model/effort pins (Claude lockstep) on the OpenCode target, or the
  `multiplattform` epic picks it up as a target-neutral touch-up.*
- **The `execution-context` agent description prose claims per-variant model pinning.** Both
  `marketplace/bundles/plan-marshall/agents/execution-context.md` and
  `execution-context-reader.md` still say "Model and effort pinned by which
  execution-context-{level} variant is dispatched" — accurate for Claude, now false for OpenCode
  (which inherits). The variant bodies themselves carry the same line. A target-neutral touch-up
  belongs to the `multiplattform` epic's shared-source discipline, not here. — *re-check trigger:
  the `multiplattform` epic lands a target-neutral wording, or a new variant is emitted that still
  carries the stale line.*
- **Executing agent skipped the plan lifecycle on Muse Spark 1.3 (2nd occurrence).** The PLAN-04
  agent self-reported bypassing the prescribed pipeline entirely (direct `.plan/` read via
  `python3 -c`, no `generate_executor` preflight, no phase-1-init/handshake/refine) to reach the
  D1/D2 fix faster, and asked the operator whether to restart correctly. Cost-benefit shortcut,
  not confusion: the workflow's cost exceeded its perceived value for a small fix. This is plan-
  lifecycle compliance, not epic tooling scope, so it is tracked here as recurrence data, not
  staged as work. — *re-check trigger: a third occurrence (pattern → escalate as épic-external
  finding to whoever owns lifecycle compliance), or the operator's restart decision changing
  PLAN-04's trajectory.*
  - *Elaboration (same run):* the agent filed a 5-point prevention analysis — (1) hard pretooluse
    gate blocking repo-source reads before preflight+status-create, (2) new `corpus read-spec`
    verb so the file-pointer branch never forces direct `.plan/` reads, (3) `--request-text-file`
    (shell-unsafe verbatim bodies), (4) mandatory usage forwarding or explicit omitted-usage log
    line in dispatch returns, (5) page workflow docs by default, never act on truncated skill
  bodies. Logged-but-accepted deviations in-run: summarized `--request-text`, omitted usage
  flags, deferred execute despite `execute_without_asking=true` per explicit operator instruction.
  Assessment: items 1–3 are fail-closed gates of exactly this epic's class (refuse input the
  surface cannot honour) but owned by plan-lifecycle machinery — routed nowhere until the
  re-check trigger fires; item 4 matches the corpus lesson already promoted as
  `2026-09-11-19-001`-adjacent discipline (explicit omission logging over fabricated zeros).
  - *TRIGGER FIRED 2026-09-13:* third occurrence arrived as inbox `model-provisioning-001.md`
    (orchestrator-side variant — decompose mis-filled plan-row slugs, structurally green,
    human-caught; remediation done in the filing epic). Per the trigger, the pattern escalates
    as an epic-external finding; the filed message IS that escalation, now absorbed as the Open
    Defect above with candidate remedies. Watch retired on this note if the defect gets staged
    (PLAN-08) or closed with a positive account.
  - *RETIRED 2026-09-13:* defect staged as PLAN-08 on operator direction (widened to include
    Muse-compliance instrumentation, mechanism-only). Recurrence record lives in
    `landings/`-adjacent Decisions and `2026-09-11-19-001`-family corpus lessons; nothing
    further to watch here.
