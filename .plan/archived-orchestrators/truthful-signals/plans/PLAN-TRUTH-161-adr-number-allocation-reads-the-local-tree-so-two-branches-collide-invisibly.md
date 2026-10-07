# PLAN-TRUTH-161: ADR number allocation reads the local tree, so two open branches take the same number and the collision lands invisibly

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-09-15 from `adhoc-token-economy-analysis-002.md`, filed directly into this epic's inbox by an
ad-hoc analysis session. The defect occurred live in this repository during this same session's work.

## Objective

**`manage-adr create --title ...` allocates the next ADR number by scanning the local working tree. A
branch opened before a sibling branch's ADR lands never sees that sibling, so both allocate the same
number — and the collision is invisible to git, because the number is only a filename prefix: different
filenames, no merge conflict, no CI failure, no review signal. Both merge cleanly.**

This happened live: two ADRs landed as **021** minutes apart (#1490, `021-machine-local-effort-to-
model-map-and-resolve-chain-slot.adoc`; #1492, `021-Economy_rules_bind_the_persisted_artifact_never_the_
reasoning_that_produced_it.adoc`). `manage-adr scan` on the resulting `main` reported `20, 21, 21`. Fixed
by #1493 renumbering the second to 022 — a whole extra PR to clear a collision nothing caught at landing
time.

The failure mode is this epic's own theme exactly: a confident signal (clean merge, green CI, no
conflict) hides the caveat that the tree holds two ADRs with one identity. Any existing cross-reference
written as "ADR-021" (one exists: `_cmd_effort.py` cites ADR-021 meaning the effort-map one) is ambiguous
from the collision moment on.

**A cost factor that makes the live instance harder to fix cheaply than it should be.** Enqueuing a PR
into the platform merge queue locks the head branch — after `ci pr merge-queue`, both `git push` and
`git push --force-with-lease` are refused with `protected branch hook declined`. The window in which a
renumber can ride along in the same PR closes at enqueue, not at merge.

## Deliverables

Two deliverables.

**D0 — A landing-time uniqueness check.** `manage-adr scan` already computes the numbers it would need. A
check that fails when two entries share a number catches every instance of this regardless of how it
arose, and needs no change to allocation — this is the highest-leverage option, named first by the source
finding because it closes the class, not merely the one cause. `manage-adr scan` currently emits duplicate
numbers as two ordinary rows; surface the duplicate as a distinct, named state instead.

**D1 — Matched control.** A fixture asserting two branches allocating against the same stale local view
land on the same number (the failure this class produces), and a fixture asserting the landing-time check
catches it. ⛔ Do not additionally implement remote-allocation (consulting `origin/main` at `create` time)
as part of this deliverable — the source finding names it explicitly as narrower than the check (it cannot
catch two branches created after the same fetch) and worth considering only alongside the check, never
instead of it; D0's check is the complete fix this spec ships.

## Claim Labels

- OBSERVED: `manage-adr scan` reported `20, 21, 21` on `main` between #1492 and #1493, and `20, 21, 22`
  after #1493 (source finding's own live observation; re-verify at outline that the historical record —
  `doc/adr/` — still shows this state).
  - verdict: corroborated | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: manage-adr scan at this HEAD confirms clean 20,21,22 (post-#1493 fix); ADR-022 title matches the #1492 commit exactly. The transient 20,21,21 collision state itself is historical and was not directly re-observed (already resolved)
- OBSERVED: `git log origin/main` shows `fb8aadc9c` (#1490) and `fea2f3ea3` (#1492) both adding a distinct
  `021-*.adoc` file, neither conflicting with the other (re-verify at outline).
  - verdict: corroborated | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: git log confirms both commits exist: fb8aadc9c (#1490, effort-map ADR) and fea2f3ea3 (#1492, economy-rules ADR), titles match the spec's description
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_effort.py` cites ADR-021
  by number (re-verify at outline that this citation still resolves unambiguously post-renumber).
  - verdict: corroborated | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: _cmd_effort.py:278 still cites ADR-021 verbatim, and this resolves unambiguously to the surviving effort-map ADR-021 at this HEAD
- OBSERVED: a queued PR's head branch refuses both `git push` and `git push --force-with-lease` with
  `protected branch hook declined` (observed live on PR #1492 per the source finding).
  - verdict: unverifiable | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: The queued-PR push-refusal behavior was not independently reproduced at cleanup time (would require enqueuing a live PR); trusted as a first-party live observation by the source session but not re-verified here
- ⚠ HYPOTHESIS: `doc/adr/` carries two filename conventions (`Title_With_Underscores` from `create`,
  `lowercase-hyphenated` hand-named) with no stated canonical form. ⛔ Recorded by the source finding as an
  adjacent observation, NOT proposed as work — this spec does not act on it; noted here only so a future
  reader does not rediscover it as new (verify-at-outline if ever picked up).
  - verdict: unverifiable | checked_at: 7a028157e | by: truthful-signals/cleanup | rescoped: n/a | evidence: The two-filename-convention observation in doc/adr/ was not independently re-swept at cleanup time; explicitly out of scope for this spec per its own text

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-adr/scripts/**` — the `create` allocator and
  the `scan` reader (D0, D1)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-adr/SKILL.md` — the documented `scan`
  output contract, if the duplicate-state change is user-visible (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-adr/**` — coverage for D0/D1 (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-adr/templates/adr-template.adoc` — the template
  header set (folded 2026-09-15 (c))
- OBSERVED: `marketplace/bundles/pm-documents/skills/ref-asciidoc/scripts/_cmd_validate.py` — the required
  header set (folded 2026-09-15 (c))
- HYPOTHESIS: `test/pm-documents/ref-asciidoc/**` — the generate-then-validate round-trip control
  (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- plan-truth-148 and plan-truth-157 had already landed when this plan was staged.

## ⭐ FOLDED 2026-09-15 (c) — EVERY TEMPLATE-GENERATED ADR FAILS THE SIBLING VALIDATOR

Forwarded from `lessons-handling-26-09-04-01-061.md` (Token-Sheriff PR #744, which decided the validator —
not its 13 ADRs — was wrong and edited none). Expected Surface extended in the same act (above). Folded here
because this spec is the `manage-adr` output-integrity owner; the deliverable count rises from two to three.

Re-grounded at `7a028157e`: `ref-asciidoc/scripts/_cmd_validate.py` requires `:toclevels: 3`,
`:toc-title: Table of Contents` and `:source-highlighter: highlight.js` and reports `missing_header`
(severity `error`) when absent; `manage-adr/templates/adr-template.adoc` emits `:toclevels: 2` and
`:sectnums:` with neither `:toc-title:` nor `:source-highlighter:`. Two marketplace components give opposite
verdicts on one document, so every consumer's `manage-adr` ADR set validates as broken by construction — and
the obvious "fix the ADRs" edit pulls them out of line with their own template (Token-Sheriff: 12 of 14 ADRs
non-compliant).

**D2 (added) — One header source of truth, with a round-trip control.** Either the validator recognizes the
`manage-adr` header set for ADR documents, or the template emits the validator's required attributes; a
freshly generated ADR must then validate clean, pinned by a generate-then-validate test the pair lacks today.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-161-adr-number-allocation-reads-the-local-tree-so-two-branches-collide-invisibly.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
