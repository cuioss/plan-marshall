# PLAN-PRQ-07: Cross-repo telemetry archive and analyze

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `plan-marshall-mcp/doc/known-defects/post-run-quality-carry-over.md` as PM-MCP input.
> **Do NOT emit; un-park only by explicit operator decision.** The spec body below stays intact as the evidence chain.

epic: post-run-quality
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-PRQ-07-cross-repo-telemetry-archive-and-analyze.md` and is queued in
> the epic `status.json` `plans[]` field. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line
> pointer and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Stand up a new `plan-marshall-telemetry` repository as the durable, cross-project home for
archived plan and orchestrator ledgers, and the machinery to move data into it and analyze it
once there. Today `archived-plans/` and `archived-orchestrators/` live inside each project's
own `.plan/local/`, subject to that project's own retention/GC and invisible to any query
spanning more than one repo; `.claude/skills/audit-archived-plan-retrospectives` — the only
corpus-level quality auditor that exists — lives inside THIS repo and can only be pointed at
this repo's own archive. This plan creates the telemetry repo; a `transfer` project-level
skill there that moves (never copies) one project's archived plans/orchestrators into it and
commits/pushes; an `analyze` project-level skill there that produces a report over
already-archived data; a new `analyze-marshall-quality` finalize step in this repo that
produces the SAME report structure at finalize time; and relocates the existing auditor into
the telemetry repo as the shared analysis backbone both paths call.

⛔ Creating the new GitHub repository is a hard-to-reverse, externally-visible action. The
executing plan MUST confirm the exact repo name, visibility, and org/account with the
operator before creating it — this is not a decision the plan makes unilaterally.

## Deliverables

1. Scaffold `plan-marshall-telemetry`: a new repository, main-branch-only (direct commits,
   no PR/branch-protection workflow — the repo stores data and two project-level skills, not
   code under active multi-contributor review), with one subdirectory pair per source project
   (`{project-slug}/archived-plans/`, `{project-slug}/archived-orchestrators/`), a README
   describing the layout and the two skills, and never onboarded to any automated
   review-bot pipeline (no CodeRabbit/Sourcery/pr-agent GitHub App installed on it, no
   `automatic-review` config expecting bot coverage).
2. `transfer` project-level skill (telemetry repo): given a local filesystem path to a
   project checkout (e.g. `/Users/oliver/git/cui-http`), moves — `git mv`/relocate, never
   copies — that project's `.plan/local/archived-plans/*` and
   `.plan/local/archived-orchestrators/*` into `{project-slug}/archived-plans/` and
   `{project-slug}/archived-orchestrators/` inside the telemetry repo, then commits and
   pushes to main.
3. `analyze-marshall-quality` finalize step (this repo, plan-marshall): a finalize-phase
   mechanism that analyzes a plan's own retrospective quality using the shared analysis
   engine (deliverable 5), emitting a report.
4. `analyze` project-level skill (telemetry repo): runs the identical analysis mechanism as
   deliverable 3 against a given number of already-transferred, archived plans/orchestrators
   sitting inside the telemetry repo, producing a report of EXACTLY the same structure as
   deliverable 3's report. Both consume one shared analysis engine and report schema so
   structural identity is a property of shared code, never of two independently-authored
   formatters.
5. Relocate `.claude/skills/audit-archived-plan-retrospectives` (this repo, including its
   `checks/` corpus and `scripts/audit.py`) into the telemetry repo as a project-level skill
   there, and resolve its relationship to deliverables 3/4's shared analysis engine
   (becomes the engine's backbone vs. coexists as a separate tool) — sequenced strictly
   AFTER PLAN-PRQ-01 and PLAN-PRQ-03 land (both currently staged to fix defects inside this
   exact skill; relocating it out from under either plan's in-flight edit is a live-file
   collision).

## Claim Labels

- OBSERVED: `.claude/skills/audit-archived-plan-retrospectives/` exists at this path with
  `SKILL.md`, a `checks/` directory of 24 per-aspect markdown check docs, and
  `scripts/audit.py` — read directly via `find` over the skill directory.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: audit-archived-plan-retrospectives/SKILL.md + audit.py --check enumerates exactly 24 names 1:1 with checks/; D5's relocation target intact and unchanged
- OBSERVED: archived plan and orchestrator ledgers are main-anchored at
  `.plan/local/archived-plans/{dated-slug}/` (per
  `phase-6-finalize/standards/archive-plan.md` — corrected 2026-09-21; the original citation,
  `orchestration-model.md` § Directory Layout, documents only the orchestrator-tree half and does not
  cover `archived-plans/` at all) and `.plan/local/archived-orchestrators/{slug}/` (per
  `persona-plan-orchestrator/standards/orchestration-model.md` § Directory Layout) respectively — read
  directly. ⚠ Incidental, not this epic's to fix: `archive-plan.md:21` itself writes the path as
  `.plan/archived-plans/`, missing the `local/` segment — a live doc defect on this spec's own declared
  surface.
  - verdict: contradicted | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: yes | evidence: archived-plans half holds (.plan/archived-plans/{date}-{plan_id}); archived-orchestrators half is now WRONG at HEAD -- orchestration-model.md:45/50/53 + ADR-024 place it at the git-tracked .plan/archived-orchestrators/{slug}/, not main-anchored, and 'NO retention/cleanup policy applies'. Cross-repo defect survives; premise needs a path/tier correction and D2 needs re-derivation over two different storage tiers
- OBSERVED: this repo's project-local finalize-step skills follow the
  `.claude/skills/finalize-step-{name}/SKILL.md` pattern with frontmatter
  `implements: plan-marshall:extension-api/standards/ext-point-finalize-step` (read verbatim
  from `finalize-step-review-retrospective/SKILL.md`), and every existing instance
  (`finalize-step-lessons-housekeeping`, `finalize-step-plugin-doctor`,
  `finalize-step-review-retrospective`, `finalize-step-era-stamp-fill`,
  `finalize-step-deploy-target`, `finalize-step-sync-plugin-cache`) is meta-project-only —
  it applies to plan-marshall's own repo, never exported to consumer projects.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: manage-config list-finalize-steps returns exactly 6 project: rows matching spec's enumeration 1:1; architecture find for finalize-step* under marketplace/bundles returns 0 -- meta-project-only confirmed, derived not asserted
- HYPOTHESIS: `analyze-marshall-quality` (deliverable 3) should ship as a
  MARKETPLACE-bundled finalize step
  (`marketplace/bundles/plan-marshall/skills/finalize-step-analyze-marshall-quality/`),
  distributed to every consumer project via `ext-point-finalize-step`, rather than following
  the meta-project-only precedent above — because its purpose (per-project post-run quality
  reporting, feeding the telemetry repo) is meant to run in every project that installs
  plan-marshall, not only in this repo — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md`
  § registration and at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/`'s
  step-selection logic (verify-at-outline).
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: no analyze-marshall-quality/plan-marshall-telemetry surface exists at HEAD (0 hits/3097 files); ext-point-finalize-step.md:47 supports the bundled {bundle}:{skill} registration form the hypothesis needs -- live design choice, correctly deferred to outline
- HYPOTHESIS: the relocated `audit-archived-plan-retrospectives` (deliverable 5) becomes the
  implementation backbone the shared analysis engine (deliverables 3/4) calls into, rather
  than a second, parallel auditor living alongside it — confirm/refute by comparing its
  `checks/` coverage against what deliverables 3/4 must report, once PLAN-PRQ-01 and
  PLAN-PRQ-03's fixes have landed on it (verify-at-outline).
  - verdict: unverifiable | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: structurally undecidable: comparison target is post-PRQ-01/PRQ-03 checks/ coverage and both are still staged (corpus enumerate confirms), no shared analysis engine exists to compare against either yet
- HYPOTHESIS: the telemetry repo's `analyze` skill (deliverable 4) reuses the shared
  analysis engine by installing plan-marshall as a Claude Code plugin in the telemetry repo
  (so it can call the same `python3 .plan/execute-script.py plan-marshall:...` scripted
  surface the finalize step uses), rather than vendoring a duplicate copy of the engine —
  confirm/refute against how a consumer project installs the plan-marshall marketplace,
  per `doc/developer/marketplace-build.adoc` (verify-at-outline). This decides the whole
  Expected Surface shape of deliverables 2-4 and MUST settle before Deliverables 3/4 are
  built, not after.
  - verdict: unverifiable | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: deciding facts are outside this repo -- plan-marshall-telemetry appears nowhere in the inventory (0/3097 files); this envelope cannot reach a remote repository. Verify-first clause is correctly placed
- HYPOTHESIS: "excluded from review agents" (deliverable 1) is achieved operationally —
  never installing the CodeRabbit/Sourcery/pr-agent GitHub Apps on the new repo, and never
  configuring `required_bots`/`optional_bots` for it — rather than by any code change in
  this codebase, since bot onboarding is a per-repo GitHub App installation outside this
  repository's control — confirm/refute against `.plan/marshal.json`'s `automatic-review`
  schema (verify-at-outline).
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: manage-config plan phase-6-finalize step get --step-id automatic-review returns required_bots/optional_bots as a per-repo config string; no cross-repo bot registry or code path exists -- omission-plus-never-installing IS the whole mechanism, as the hypothesis states
- Verify-first clause: at outline, settle the plan-marshall-plugin-installation question
  above before scoping deliverables 3/4's implementation — a refutation (the telemetry repo
  cannot or should not install plan-marshall as a plugin) changes the shared-engine
  mechanism from "one scripted surface, two callers" to "one engine, vendored into two
  repos," which changes both deliverables' file lists.
  - verdict: unverifiable | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: same blocker as claim 5 -- needs the telemetry repo to exist. Sequencing constraint confirmed still binding from the parser: corpus surfaces shows PRQ-01/PRQ-03/PRQ-07 all declarative with PRQ-01 and PRQ-03 both still staged; D5's relocation correctly gated behind both

## Expected Surface

- OBSERVED: `.claude/skills/audit-archived-plan-retrospectives/` (whole directory — relocated
  out of this repo)
- OBSERVED: `test/plan-marshall/audit-archived-plan-retrospectives/` (moves with the skill)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/finalize-step-analyze-marshall-quality/`
  (new; path depends on the marketplace-vs-project-local claim above — verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/` (step-registration
  wiring for the new finalize step; verify-at-outline — same surface PLAN-PRQ-04 and
  PLAN-PRQ-06 already touch, see Dependencies and Sequencing)
- OBSERVED: `plan-marshall-telemetry` (new external repository — entirely out of this repo's
  tree and therefore structurally invisible to this epic's own surface-disjointness gate,
  which reads only this repo's specs and `references.json`; recorded here so a reader knows
  the gate cannot see it, not because the gate will check it)

## Dependencies and Sequencing

- Depends on: PLAN-PRQ-01, PLAN-PRQ-03 (both touch
  `.claude/skills/audit-archived-plan-retrospectives/**`; this plan must not relocate that
  skill out from under either plan's in-flight edits — land both first)
- Overlaps with: PLAN-PRQ-04, PLAN-PRQ-06 (both touch
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/**` if the new finalize step
  lands marketplace-bundled per the HYPOTHESIS above — never pair PRQ-07 with either while
  that surface is in flight)
- Adjacent to: PLAN-PRQ-05 (lessons corpus provenance and quality) — both are "the learning
  loop must survive past one project" in theme, but PRQ-05 owns the lessons corpus itself and
  is untouched by this plan; no shared surface.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/post-run-quality/plans/PLAN-PRQ-07-cross-repo-telemetry-archive-and-analyze.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests, plus the
new `plan-marshall-telemetry` repository it stands up (an explicitly scoped exception to the
usual single-repo write boundary, since deliverables 1, 2, 4, and 5 live there by design — the
operator confirms the new repo's existence and identity before any write lands in it, per the
Objective's confirmation note). It creates and edits NO file under
`.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR(s) and
its inbox message. The inbox exception's qualifiers and the sole sanctioned write mechanism
are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
