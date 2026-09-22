# PLAN-TRUTH-020: Graduate the deployment/topology diagram type from API-Sheriff into `pm-documents:ref-svg-diagrams`

epic: truthful-signals
workstream: WS-01

> Staged plan spec. **LOW PRIORITY — not urgent, but must not be lost.** Requested by the operator
> 2026-07-30: *"move the template to `marketplace/bundles/pm-documents/skills/ref-svg-diagrams/templates`
> and remove it from the API-Sheriff."*
>
> ⚠ **THEME NOTE, stated openly:** this is a documentation-tooling graduation, NOT an instance of this
> epic's `confident-signal-hides-a-caveat` theme. It is parked here because `truthful-signals` is the
> default sink for new non-PR work, not because it fits the charter. If a documentation-surface epic is
> ever opened, this moves there.

## Objective

API-Sheriff's PR **#132** (merged `4fc9dd7`, 2026-07-30) authored a deployment/topology diagram type
downstream, deliberately *"shaped to graft upstream unchanged"* with an explicit graduation statement.
Graduate it into `pm-documents:ref-svg-diagrams` and retire the downstream copy.

## ⚠ Scope correction the operator should see — the template CANNOT move alone

The request named only the template. **Moving the `.svg` alone would violate the target skill's own
documented contract**, so this spec moves the *pair*:

- OBSERVED — `ref-svg-diagrams/SKILL.md:30`: *"Per-diagram-type standards live under
  `standards/diagram-type-{name}.md`."* A type without its standard is undefined.
- OBSERVED — `SKILL.md:67-71`, the templates table: **every template row names its owning standard** in
  the second column (`diagram-type-block.md`, `diagram-type-graph.md`, …). A `deployment` row would have
  nothing to name.
- OBSERVED — `SKILL.md:79`: *"If none of the existing types fit, treat this as a sign that a new
  diagram-type standard is needed."* The new type is exactly that case.
- OBSERVED — #132's own non-goals: *"does not modify the upstream `pm-documents:ref-svg-diagrams`
  standard itself — the new type is written to graft on unchanged, not merge it in this PR."* The
  graduation was designed to include the standard.

**Therefore the graduated set is the standard + the template.** The reference implementation is a
separate question — see D1.

## Source artifacts (OBSERVED — from `git show --stat 4fc9dd7`)

| API-Sheriff path | Lines | Disposition |
|---|---|---|
| `doc/development/diagram-type-deployment.md` | 429 | **GRADUATE** → `standards/diagram-type-deployment.md` |
| `doc/resources/templates/deployment-diagram-skeleton.svg` | 129 | **GRADUATE** → `templates/deployment-diagram-skeleton.svg` |
| `doc/resources/diagrams/integration-test-topology.svg` | 192 | **STAYS** — API-Sheriff's real IT topology, consumer-specific content |
| `doc/development/integration-test-topology.adoc` | 112 | **STAYS** — documents the above |
| `doc/development/README.adoc` | +12 | **EDIT** — repoint the graduated entries, keep the topology entries |
| `.plan/project-architecture/**/enriched.json` | — | plan tooling artifact, not content — ignore |

## Deliverables

### D1 — GATE: decide the graduation set and the reference-implementation column (mutates nothing)

Every existing type row in `SKILL.md:53-57` names a **reference implementation** that lives in
plan-marshall's own docs (findings-pipeline, plan-worktree-topology, post-execute-shipping-flow,
audit-trail-layers, build-dispatch-sequence). The graduated type has none, because its only reference
implementation is API-Sheriff's IT topology. Decide between:

- **(a)** graduate standard + template only, and give the type row no reference implementation (or an
  explicit "no reference implementation yet" note), accepting asymmetry with the other five rows;
- **(b)** additionally author a plan-marshall-native deployment diagram as the reference implementation
  — **larger scope, and it must depict real plan-marshall infrastructure, not a synthetic example**;
- **(c)** cite API-Sheriff's diagram — **rejected up front**: a marketplace skill must not depend on a
  consumer repo's file as its reference.

Also settle: does the `state` future-placeholder pattern (`SKILL.md:59-61`) apply here, i.e. should the
type land as authored-and-indexed or as a placeholder? **Default recommendation: (a)**, authored and
indexed, reference-implementation column explicitly empty.

### D2 — land the standard and the template

Copy both into `ref-svg-diagrams/`. The standard was written to graft unchanged, but **verify rather
than assume**: strip or rewrite any API-Sheriff-specific reference, and comply with the marketplace doc
rules — **no transitionary prose, no version history, no dated sections, no "recently added" framing**.
The 429-line standard covers five affordances (containment, protocol-and-port edges, trust boundaries,
external-actor notation, deployment-target labeling), file naming, theme strategy, a render recipe, and
its own graduation statement — ⚠ **the graduation statement itself is transitional and must be dropped
on landing**, since upstream *is* the destination.

### D3 — index it in `SKILL.md`

Add the type row to the per-diagram-type table (`:53-57`) and the template row to the templates table
(`:67-71`) **with its owning standard named**, matching the existing column contract exactly. Confirm
the counts stated in prose elsewhere in the file ("six diagram types and five templates" appears in
#132's own summary) are re-derived, not left stale — ⚠ **a hand-written count adjacent to a table that
just grew is this epic's most-repeated defect**; check `SKILL.md` and any `pm-documents` README for such
a count.

### D4 — retire the downstream copy in API-Sheriff

Remove **only** the two graduated files from `cuioss/API-Sheriff`, via `git -C` in that tree with its
own PR flow (this is a consumer repo — plain `git`/`gh -R`, per the consumer-repo convention). Then:

- repoint `doc/development/README.adoc` and `doc/development/integration-test-topology.adoc` at the
  upstream skill instead of the removed local paths;
- **sweep for dangling references to both removed paths** before pushing — the `.adoc` reference doc and
  the README are the two known referrers, but ⚠ **treat that as a SAMPLE, not an enumeration**: grep the
  whole repo.
- ⚠ **The local clone at `/Users/oliver/git/API-Sheriff` was at `#110` on 2026-07-30 while `origin/main`
  carried `#132` — pull before touching anything**, or the files will appear absent.

### D5 — gates

- `plugin-doctor` over `pm-documents` (a new standards file + template + SKILL.md table edits is exactly
  its remit); regenerate the executor / sync the plugin cache per the meta-project flow.
- ⚠ **Render verification is a real open blocker, not a formality.** #132 records that the upstream
  standard treats render-and-read-back as **non-skippable** and that **no rasteriser is installed**; it
  resolved this as its own gate deliverable downstream. Re-establish a render path here, or record
  explicitly why the graduated template's already-verified render carries over.

## Expected Surface

- OBSERVED: `marketplace/bundles/pm-documents/skills/ref-svg-diagrams/standards/diagram-type-deployment.md` (new)
- OBSERVED: `marketplace/bundles/pm-documents/skills/ref-svg-diagrams/templates/deployment-diagram-skeleton.svg` (new)
- OBSERVED: `marketplace/bundles/pm-documents/skills/ref-svg-diagrams/SKILL.md` — the two tables at `:53-57` and `:67-71`
- HYPOTHESIS: a `pm-documents` README or bundle index carrying a diagram-type/template **count** that goes stale (verify-at-outline)
- OBSERVED (cross-repo): `cuioss/API-Sheriff` — the two removals plus `doc/development/README.adoc` and `doc/development/integration-test-topology.adoc`
- HYPOTHESIS: further API-Sheriff referrers found by the D4 grep (enumerated at outline, not guessed here)

**Disjointness:** `pm-documents` only — **disjoint from every plan in the queue**, which all sit in
`plan-marshall` bundles. No live plan touches `pm-documents`. This makes it a good low-cost parallel
filler whenever a slot is free.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none known.
- ⚠ Cross-repo: needs API-Sheriff write access and its own PR there. The two repos' changes should land
  **upstream first, downstream second**, so the downstream README never points at a skill path that does
  not yet exist.

## Notes

- Low priority by operator instruction. Not a defect — a graduation of downstream work that was
  deliberately authored to be graduated.
- ⭐ Worth preserving from #132's approach: its reference implementation was cross-checked
  service-by-service against real `docker-compose.yml` and gateway config rather than being synthetic.
  If D1 picks option (b), hold the native reference diagram to that same standard.

## Write-Boundary

Repository source in `marketplace/bundles/pm-documents/**` plus a cross-repo change in
`cuioss/API-Sheriff`. NO writes to `.plan/local/orchestrator/**` — ledger state is the orchestrator's,
and the plan's only channels back to the epic are its PR and its `inbox/` OUTBOX. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.


---

## ⚠⚠ NO CLAIM LABELS — EVERY CLAIM IN THIS SPEC IS UNLABELLED (recorded 2026-08-09, full-corpus review)

This spec predates the verify-first contract and carries **no `## Claim Labels` section**. The contract
requires every serialized premise to be marked `OBSERVED` or `HYPOTHESIS`, with a `HYPOTHESIS` naming
the file **plus the symbol** that settles it.

⛔ **Labels were NOT retrofitted here, deliberately.** Assigning `OBSERVED` to a claim this orchestrator
did not observe would manufacture provenance — the precise defect the contract exists to prevent, and
worse than the missing section, because a wrong label reads as a checked one.

⇒ **Until outline labels them, treat EVERY claim in this spec as `HYPOTHESIS`**, including its counts,
its file lists, and any asserted *absence*. ⭐ **Asserted absences are the higher-risk half**: an
unverified "X does not exist, build it" produces duplicate work against a surface that already exists,
and nothing downstream trips over it. **Outline owns the labelling before any deliverable is sized.**
