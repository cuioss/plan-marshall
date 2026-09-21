# Epic: Multi-target architecture completion

slug: multiplattform

> Ledger document for one epic under `.plan/orchestrator/multiplattform/`. The layout and
> authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

Finish the multi-target architecture so that plan-marshall is genuinely target-opaque: runtime
seams that name no product, a scoping mechanism for components that exist on only some targets,
zero Claude literals outside the sanctioned homes, and a one-command OpenCode developer loop. The
epic is too large for one plan because the couplings are spread across four independent surfaces —
the `platform-runtime` seam, the `marketplace/targets` build machinery, the bundle prose and
scripts, and the developer/distribution tooling — each with its own review burden and its own
collision profile.

Done, at the epic level, means: the `Runtime` ABC and its router carry no target vocabulary; every
Claude-specific rule in the marketplace is either target-resolved or declared as Claude-target
material; the coupling inventory is empty or every remaining row is a recorded, justified
exception; and a developer can generate and deploy the OpenCode tree in one command. Live-runtime
confirmation on a real OpenCode install is deliberately **outside** the plan set — it is carried as
a blocked workstream (WS-05) gated on an operator with an install.

This epic was ingested from the standalone `doc/plans/multiplattform/` tree, which is now fully
absorbed into this ledger and removed from version control. The three plans that had already
shipped were ground-truth verified against HEAD `2cd1a19c` rather than trusted from their run
reports.

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary --slug multiplattform
     Paste the returned `summary` block verbatim between the markers (the same
     invocation also emits `ordered_queue` for the Ordered Queue section below).
     Anything a reader wants to add BY HAND goes in the annotation zone below,
     outside the markers — never inside them. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: 2026-09-15: cleanup complete (compact epic_changed:false, restart_verdict:ready). WS-05 resolved via sibling epic tooling-truthfulness/PLAN-07. Next: close, then archive.
**Phase**: orchestrating
**Inbox (derived)**: 0 queued, 13 archived
**Parked**:
- PLAN-17 (WS-05)
- PLAN-18 (WS-05)
**Queue** (staged, in order):
- (empty)
- PLAN-01 (WS-01) — plan=n/a — PR #1291 — landing=landings/PLAN-01.md — status: landed
- PLAN-02 (WS-02) — plan=n/a — PR #1313 — landing=landings/PLAN-02.md — status: landed
- PLAN-03 (WS-03) — plan=n/a — PR #1319 — landing=landings/PLAN-03.md — status: landed
- PLAN-04 (WS-04) — plan=n/a — PR #1372 — landing=landings/PLAN-04.md — status: landed
- PLAN-19 (WS-02) — plan=n/a — PR #1374 — landing=landings/PLAN-19.md — status: landed
- PLAN-16 (WS-02) — plan=n/a — PR #1375 — landing=landings/PLAN-16.md — status: landed
- PLAN-13 (WS-03) — plan=n/a — PR #1376 — landing=landings/PLAN-13.md — status: landed
- PLAN-15 (WS-02) — plan=n/a — PR #1420 — landing=landings/PLAN-15.md — status: landed
- PLAN-05 (WS-02) — plan=n/a — PR #1379 — landing=landings/PLAN-05.md — status: landed
- PLAN-08 (WS-01) — plan=n/a — PR #1393 — landing=landings/PLAN-08.md — status: landed
- PLAN-06 (WS-03) — plan=n/a — PR #1456 — landing=landings/PLAN-06.md — status: landed
- PLAN-07 (WS-03) — plan=n/a — PR #1458 — landing=landings/PLAN-07.md — status: landed
- PLAN-09 (WS-01) — plan=n/a — PR #1405 — landing=landings/PLAN-09.md — status: landed
- PLAN-10 (WS-03) — plan=n/a — PR #1449 — landing=landings/PLAN-10.md — status: landed
- PLAN-12 (WS-03) — plan=n/a — PR #1460 — landing=landings/PLAN-12.md — status: landed
- PLAN-11 (WS-02) — plan=n/a — PR #1438 — landing=landings/PLAN-11.md — status: landed
- PLAN-14 (WS-01) — plan=n/a — PR #1408 — landing=landings/PLAN-14.md — status: landed
- PLAN-20 (WS-04) — plan=n/a — PR #1418 — landing=landings/PLAN-20.md — status: landed
- PLAN-21 (WS-03) — plan=n/a — PR #1444 — landing=landings/PLAN-21.md — status: landed
- PLAN-22 (WS-03) — plan=n/a — PR #1452 — landing=landings/PLAN-22.md — status: landed
<!-- END GENERATED: resume-summary -->

### Annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated markers.
     A regeneration replaces only what sits BETWEEN the markers, so everything written
     here survives it. -->

- **`plan_marshall_plan_id` is `n/a` for PLAN-01/02/03/04 and this is correct, not a gap.** The first
  three shipped in the standalone `doc/plans/` cloud lane; **PLAN-04 shipped from OpenCode**. Neither
  route creates a plan-marshall plan id, and a scan of `.plan/local/plans/` at PLAN-04's landing
  confirmed no plan directory exists for it. ⛔ Do not "fix" these rows by inventing an id.
- **PLAN-17 and PLAN-18 are `parked`, and the `next` verb must never emit them.** Their gate is an
  operator with a live OpenCode install, not a predecessor plan. See `workstreams/WS-05-live-validation.md`
  for the unpark sequence.
- **No plan in this epic has ever run through the plan-marshall lifecycle** — still true. The four
  five terminal rows landed outside it — three ingested as history, **PLAN-04 and PLAN-19 shipped
  from the OpenCode lane**. ⛔ Do not expect a `.plan/local/plans/` directory, a plan id, or
  lifecycle phase state for any of them; `plan_marshall_plan_id` is `n/a` by design.
- ⚠️ **A `running` row in this epic rests on ONE operator statement and nothing else — no heartbeat,
  no lifecycle state to query.** PLAN-19 carried such a row and has since landed, so no row is
  `running` now; the rule is kept because it applies to every future OpenCode run. A resuming session
  that finds a `running` row has learned only that nobody has reported otherwise. ⛔ **Never
  regenerate or "correct" this from a machine field — there is none, which is why it lives in
  narrative.** Confirm with the operator, or look for the PR.
- ⚠️ **43 of 50 re-grounding verdicts are STALE — and as of the PLAN-04 landing the reason to care
  has CHANGED. Re-ground them; do not bulk re-stamp them.** They were checked at `2cd1a19c`. HEAD is
  now `5dc7efd5`, **36 commits** past the `3bc01075` this note previously named.
  ⛔ **The old rationale is RETRACTED and must not be re-derived.** It read: "the two intervening
  commits touched … none of which is the subject of any of the 43 claims." That was true at
  `3bc01075` and is **false now** — the 36-commit span touches **20 files** under
  `platform-runtime/` and `marketplace/targets/`, including `runtime_base.py`,
  `opencode_runtime.py`, `_claude_runtime_impl.py`, `platform-runtime/standards/contract.md`,
  `body_transform_engine.py` and `opencode/emitter.py`. Those **are** the claim subjects. So the
  verdicts are no longer "stale but probably still true"; some may be genuinely **refuted**, and
  nobody has looked.
  **What follows, and what does not.** Still binding: re-stamping at a new sha without re-running the
  verification manufactures freshness the check never established. Still true: **staleness does not
  change admission** — the standard reports it alongside, never as a block, and `blocking_count` was
  0 at last measurement. What has changed is the *priority*: a `cleanup` re-grounding pass over these
  43 claims is now genuinely warranted before a large emit, where previously it was optional.
  ⚠️ **And the 7 comparatively-fresh verdicts were PLAN-19's, which has now LANDED** — so every
  verdict still attached to a LIVE spec dates from `2cd1a19c`. The corpus no longer holds a single
  recently-checked live claim.
  — *corrected by: PLAN-04 landing analysis, verified by `git diff --name-only 3bc01075..HEAD`*

## Ordered Queue

<!-- GENERATED BLOCK — never hand-write or hand-edit the table between the markers.
     Regenerated from status.json and the staged specs: emitted as `ordered_queue` by
     orchestrator.py resume-summary --slug multiplattform (paste it verbatim after a queue change),
     and rewritten in place by the compact stage (orchestrator.py compact --slug multiplattform) at
     cleanup. Only the LIVE queue is rendered here — a shipped/landed row belongs in its
     landing record, not in the live queue. Per-row notes a reader wants to ADD go in the
     annotation zone below, outside the markers — never inside them. -->

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-17-pin-opencode-install-path | WS-05 | parked | doc/developer/distribution.adoc; doc/user/installation.adoc; marketplace/targets/opencode/** |
| 2 | PLAN-18-opencode-user-documentation | WS-05 | parked | doc/developer/marketplace-build.adoc; doc/user/installation.adoc |
<!-- END GENERATED: ordered-queue -->

### Queue annotations

- ⛔ **THE RE-DERIVE OBLIGATION IS NOW BINDING AND IT REACHES THREE PLANS, NOT TWO.** PLAN-15 ran
  PAST D1 — the anchor's own test — so the order inversion is no longer moot. Two of the six files
  it touched undeclared are exactly the contested ones its sequencing note named:
  **`manage-metrics/standards/data-format.md`** (PLAN-12's D3, and three-way contested with PLAN-07)
  and **`plugin-architecture/references/frontmatter-standards.md`** (PLAN-06's — the spec's own
  "Overlaps with PLAN-06 … if D3 lands there" case, and it landed there).
  ⛔ **PLAN-07, PLAN-12 AND PLAN-06 must each re-derive over those files rather than trust their hit
  lists.** PLAN-06 is the one the inversion note did not anticipate — it was added here because the
  landing, not the plan, is what settled where D3 went.
  — *source: PLAN-15 landing, verified against the merged diff at `713f9017`*

- ✅⛔ **The `unreviewed-merge-gate-holes` live collision is RELEASED, and it converted into
  re-grounding debt for PLAN-07 and PLAN-12.** That plan merged on 2026-09-05 as PR #1409, squash
  `66320e70d`; its worktree is gone, so the hand-checked three-way concurrency this epic was
  tracking is down to PLAN-15 and the sibling epic's PLAN-110. But its 19 realized files
  (`git show --stat 66320e70d`) land squarely inside two staged declarations:
  **PLAN-07** claims `marketplace/bundles/plan-marshall/**` and `test/plan-marshall/**`, which
  together contain **19 of 19**; **PLAN-12** claims `manage-metrics/SKILL.md` (touched directly)
  and `test/` (contains all six touched test files). Both must re-derive over
  `manage-metrics/`, `automatic-review/`, `manage-tasks/` and
  `plan-marshall/workflow/execution.md` before they are emitted. ⚠️ This is a **second,
  independent** source of the same duty the PLAN-15 order inversion already imposed on this exact
  pair — they now owe a re-derive for two unrelated reasons.
  — *source: `ci pr view --pr-number 1409` (merged, `review_decision: none`) plus the merge
  commit's own file list; declarations from `corpus surfaces --slug multiplattform`*

- ✅ **TYPO FIXED at the 2026-09-06 cleanup; THE PARSER GAP REMAINS OPEN AND IS THE REUSABLE FINDING.** ~~PLAN-12's `data-format.md` claim names a path that does not exist, and the parser called it resolved.~~ The declaration read
  resolved.** The declaration reads
  `marketplace/bundles/plan-marshall/skills/manage-metrics/manage-metrics/standards/data-format.md`
  — the segment `manage-metrics/` is duplicated. The real file is
  `.../manage-metrics/standards/data-format.md` (`architecture find` returns that path and only
  that path), and **#1409 touched it**. `corpus surfaces` reports PLAN-12 with
  `unresolved_count: 0` and lists the malformed path among its resolved entries, so the surface
  parser validates path *syntax* and never asks the filesystem whether the path exists. The
  consequence is a permanent false-disjoint: no disjointness check can ever match that claim
  against a real edit. ⚠️ This is a **third** member of the declaration-form family the sibling
  `test-quality` epic tracks — after containment blindness and unenumerated populations, a claim
  that resolves to nothing. All three return a clean zero. Fixing the typo fixes one file; the
  parser gap is the reusable finding.
  — *source: `corpus surfaces --slug multiplattform`, cross-checked against
  `architecture find --pattern '**/manage-metrics/**/data-format.md'` (count 1 real path)*
  ✅ **APPLIED at cleanup:** the spec's `## Expected Surface` line carried the abbreviated span
  `` `.../manage-metrics/standards/data-format.md` ``, which the parser expanded against the
  preceding entry's directory and so doubled the segment. It now carries the full path, and the
  correction was verified by **MEMBERSHIP** — the real path appears as its own `claimed[]` row for
  PLAN-12 — never by the `claimed_count` cardinality, which moves identically for a wrong path.
  ⛔ **The parser gap is NOT fixed and must not be read as fixed by this closure**: `corpus surfaces`
  still validates path *syntax* only and never asks the filesystem whether a path exists, so the next
  malformed declaration will resolve just as silently. That gap belongs to the tooling cluster, whose
  members all share the shape of returning a clean zero where they should return could-not-evaluate.

- ⛔ **PLAN-15 IS BEING RUN FIRST, INVERTING ITS RECORDED ORDER — PLAN-07 AND PLAN-12 MUST RE-DERIVE
  AFTER IT.** PLAN-15's spec says *"Depends on: none. D1 is buildable today"*, and its
  "sequence after PLAN-07 and PLAN-12" instruction governs only the CONTESTED files at D2+ (the §M10
  sites and `manage-metrics/standards/data-format.md`, which is PLAN-12's D3). With PLAN-110 running
  in the sibling epic, PLAN-15 is the ONLY multiplattform plan whose declared surface it does not
  touch, so it was emitted out of the recorded order deliberately. ⚠️ The instruction "re-derive
  rather than assuming what they left" was written for PLAN-15 running LAST; running it FIRST turns
  that obligation around — **PLAN-07 and PLAN-12 now inherit it**. Neither may trust its hit list
  over the contested files once PLAN-15 lands. ⭐ The compensation is real: PLAN-15 conditionally
  unblocks PLAN-11's design, so this ordering buys the queue a move it otherwise did not have.
  — *source: the PLAN-110 round; PLAN-15's own Dependencies section is the authority for "depends on
  none"*

- ⚠️ **PLAN-07 and PLAN-10 must RE-DERIVE `marketplace_paths.py` before acting — PLAN-09 moved the
  boundary they share.** `_DEFAULT_RUNTIME_TARGET` no longer exists: PLAN-09 D4 replaced the
  constant with a lazy `_default_runtime_target()` reading `platform_runtime._DEFAULT_TARGET`, plus
  a `_DEFAULT_RUNTIME_TARGET_SENTINEL` fallback. Both specs' hit lists over that file predate the
  change. ✅ **The three-owner partition itself HELD and is now evidenced rather than assumed** —
  PLAN-09 declared the file as "`_DEFAULT_RUNTIME_TARGET` only" and the diff confirms it touched
  nothing else there, leaving `get_base_path`'s scopes (PLAN-07) and the fallback-composer
  constants (PLAN-10) untouched. A moved boundary, not a broken one.
  — *source: PLAN-09 landing, verified against the merged diff at `c3a1aacbc`*

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated table markers. -->

⚙️ **EMIT FORM (operator directive) — this epic emits OpenCode runbook commands, NOT
`/plan-marshall` pointers.** `orchestrate.md` Step 5's one-line `/plan-marshall task="implement …"`
form does **not** apply here. Every emitted command takes this shape, verbatim:

```text
Plan: .plan/local/oc-plans/{epic}/{NNN}-{plan-name}/plan.md
Staged orchestrator spec: .plan/orchestrator/{epic}/plans/PLAN-{NN}-{plan-name}.md

Execute it per the runbook at .plan/local/opencode/RUNBOOK.md — it is the working contract
(Step 3 authors the plan from the staged spec; Steps 4–9 then apply). Do not delete the
orchestrator spec; it remains the source record.
```

- **`{NNN}` is the plan number × 10, zero-padded to three** — PLAN-15 → `150`, PLAN-20 → `200`.
  Grounded in `archive/original-staged-specs/` (`040`…`080`). `{plan-name}` is the queue slug verbatim.
- **What does NOT change:** the emit-only hand-off rule, the emit≠running invariant, and the
  disjointness / prep-readiness admission tests. Only the command TEXT differs.

⚠️ **This form REPLACED a much longer one, and the shortening is the point — do not re-expand it.**
The emit previously carried the step-by-step runbook reminder and a paragraph of derive-from-spec
instructions. Those are **static mechanics**, identical on every run, and they now live in the
contract itself: RUNBOOK § Step 3 owns the two arrival shapes, the verbatim carry-across set, the
"never delete the spec" rule, and the canonical first-instruction blockquote. ⛔ Re-inlining any of
that into an emitted command creates a second copy that drifts from the runbook — the emit carries
**plan-specific values only**.

⚠️ **The tree moved once already** (PLAN-19 landing): OpenCode plans live under the git-ignored
`.plan/local/oc-plans/`, never `doc/plans/`. A command against the old path authors somewhere the
RUNBOOK no longer recognises.

- ⚠️ **Every spec carries a `## Hand-Off Command` section, and 19 of the 20 are STALE.** They were
  authored at decomposition with the `/plan-marshall task="implement …"` form, which this epic no
  longer uses. Only PLAN-20's has been updated (it carried an OpenCode form that the template
  shortening then superseded, so it was actively contradictory). ⛔ **The ledger's EMIT FORM above is
  authoritative** — a spec's block is a convenience copy and loses on any divergence. Deliberately NOT
  bulk-rewritten here: 19 mechanical edits is exactly the duplicated-mechanics problem the template
  shortening just removed, and `cleanup`'s apply-policy is the verb built for corpus-wide corrections.
  **Cleanup options, for whoever runs it:** strip the section entirely (the ledger already carries the
  form), or regenerate all 19. Stripping is preferred — it removes the second copy rather than
  refreshing it.
- ⚠️ **Reading CI status mid-flight can return a SUPERSEDED run's conclusion.** Observed by the
  PLAN-13 run: pushing review fixes retriggered CI, and the gate briefly reported the older run's
  conclusion; `ci checks wait` was needed to get the real head outcome. **For this orchestrator's own
  landing corroboration the exposure is small but real** — a `ci checks status --pr-number N` read is
  settled once the PR is MERGED (every landing analysed so far was read post-merge), but the same
  call against an in-flight PR can attribute a stale conclusion to the current head. ⛔ When
  corroborating anything before merge, tie the verdict to a **head SHA**, not to a bare status read.

- ⚙️ **SUPERSEDED — the OpenCode lane now DOES emit inbox landings.** This entry previously read that
  the OUTBOX was structurally unused here and that an empty inbox meant *the lane does not use it*.
  That held until RUNBOOK **Step 10 — Emit the landing to the epic inbox** was added: a run now writes
  one `kind: landing` message after the merge is confirmed, and § Recording discipline names it as the
  single sanctioned write outside the plan directory. ✅ **PROVEN END-TO-END at the PLAN-05 landing**:
  message written, enumerated `valid`/`live`, completeness-checked, reconciled, archived to
  `inbox/archive/structural-directive-coverage/`. Drain future landings with `analyze` (no paste).
  ⚠️ **Reading a zero still needs care.** The four landings before PLAN-05 (PLAN-04, PLAN-19, PLAN-16,
  PLAN-13) predate Step 10 and were analysed from pastes, so an empty inbox is the **EMPTY** zero —
  `live_count: 0`, `closed_senders` empty, `invalid_count: 0` — meaning nothing is queued and a later
  message is still possible. It is not the *finished* zero (no sender has declared closure) and not
  the *blocked* one. Read all three fields, never `live_count` alone.
- ⛔ **The Step 10 `--sender-id` is the plan's orchestrator SLUG, never the `{NNN}-` prefixed
  directory name.** `validate_plan_id` requires `^[a-z][a-z0-9-]*$` (`input_validation.py:61`), so a
  digit-prefixed id is rejected outright. This ledger's own first draft of the runbook step got it
  wrong and the operator corrected it at `RUNBOOK.md:735`; the slug also maps to the `slug` field of
  the plan's `status.json` row, so attributability is kept rather than traded away.
- ⚠️ **Expect `complete: false` on `total_tokens` in this lane.** The required-key set is
  plan-marshall's, and `total_tokens` comes from its `record-metrics` step, which this lane has no
  analogue for. The runbook instructs `unknown` (a could-not-read, a gap at every key) rather than
  `n/a` (an observed absence, legal only at `pr`/`merge_state`), so an OpenCode landing is expected to
  drain INCOMPLETE naming that one key. ⛔ That is the honest encoding, not a defect to fix by
  writing `n/a` — which would launder an unread value into an asserted one. Record it and move on.
- **The operator paste is NOT retired by Step 10.** The narrative half of a landing — an anomaly no
  step recorded, a bot withdrawal, a contradicted merge claim — is irreducibly prose and correctly
  keeps a manual channel; the payload spec names two such items as narrative-only by design. The orchestrator may also read the run's own
  report directly at `.plan/local/oc-plans/{epic}/{NNN}-{slug}/report.md` (read-only analysis; the
  filename is FIXED — a resumed run appends a new run section to the same file rather than creating a
  numbered sibling, so there is never more than one report per plan to find);
  that report was first-party ground truth for the PLAN-19 landing record.
- ✅ **Authoring route (operator-decided): THE RUN DERIVES ITS OWN PLAN.** Every emitted command
  carries a pre-Step-3 preamble instructing the OpenCode run to author
  `.plan/local/oc-plans/multiplattform/{NNN}-{slug}.md` from its staged spec at
  `plans/PLAN-NN-{slug}.md`, carrying across problem/mechanism, deliverables, out-of-scope, expected
  surface and every claim label verbatim (a `HYPOTHESIS` stays a `HYPOTHESIS` with its artifact).
  RUNBOOK Step 3 then `git mv`s it into `{NNN}-{slug}/plan.md`. ⛔ **The orchestrator spec is never
  deleted** — it remains the source record.
- ⚠️ **The first-instruction block differs from the cloud lane's.** A plan authored for THIS lane
  opens with a *follow-the-runbook* instruction naming `.plan/local/opencode` (RUNBOOK § Step 3),
  **not** the `Skill: cloud-plan-lane` block that `author-cloud-plan` mandates. Authoring a plan for
  this lane with the cloud block silently disables every runbook gate.

✅ **SUPERSEDED — all three "lossy extractor" limits below were fixed by the parser upgrade. Do not
re-derive them.** This block previously warned that the Surface column was lossy in three ways and
told authors to keep exclusions OUT of `## Expected Surface`. That advice described the **retired**
parser and is now wrong. Re-measured with `corpus surfaces` at executor `0.1.1573` (the version the
PLAN-16 run regenerated), the shared `epic_spec_parser` resolves all three cases:

| Former limit | Status at 0.1.1573 | Evidence |
|---|---|---|
| 1. A glob-only bullet contributes nothing | **fixed** | `marketplace/bundles/plan-marshall/**` and `test/plan-marshall/**` resolve with kind `recursive_glob` |
| 2. A repo-root file without a `/` contributes nothing | **fixed** | `pyproject.toml` (PLAN-16), `AGENTS.md` and `CLAUDE.md` (PLAN-07) all resolve with kind `file` |
| 3. An excluded path is extracted as if owned | **fixed** | the payload partitions `claimed[110]` / `excluded[11]` / `unresolved[25]`; PLAN-16's `marketplace/targets/` exclusion sits in `excluded[]` |

⛔ **The instruction "keep exclusions out of `## Expected Surface`" is RETRACTED** — an exclusion is
now parsed as an exclusion, and moving one out of that section hides information the gate can use.
Corpus-wide the reading is clean: **20/20 specs `declarative`, `indeterminate_count: 0`**, so every
candidate now admits a real disjointness check.

⚠️ **What remains true:** the declared surface is still a *spec-authored* quantity, so the gate is
only as honest as the declarations — PLAN-04's landing touched an undeclared `pyproject.toml`. The
parser is no longer the weak link; **under-declaration is.**

- ~~**PLAN-04** — the standing fully-disjoint concurrency partner.~~ **LANDED** (PR #1372, see
  `landings/PLAN-04.md`). ⚠️ **And the disjointness claim was WRONG — this is the correction, keep
  it.** PLAN-04's spec asserted it was "disjoint from every plan in the epic across all of code and
  tests"; its landing edited **`pyproject.toml`** (registering the new `test/sync-opencode/` path),
  which **PLAN-16 declares** (`## Expected Surface` line 61, the lint-command edit). Had the two run
  concurrently under `parallelization_scope: 2` they would have collided. The gate never saw it for
  **two compounding reasons**: PLAN-04 never declared the file, *and* limit 2 below means a
  slash-less repo-root path is unextractable even when declared. No live harm — PLAN-04 ran alone
  and PLAN-16 is still staged.
  ⛔ **The generalizable rule this yields: any plan that adds a new test module touches
  `pyproject.toml`, and `pyproject.toml` is PLAN-16's.** Before pairing PLAN-16 with anything, ask
  whether the partner adds a test module — the declared surfaces will not tell you.
  — *source: PLAN-04 landing analysis, verified against both specs*
- **PLAN-13** — ⚠️ **NOT fully disjoint. The caveat this row used to state as a conditional is now a
  MEASURED collision.** Machine-derived from `corpus cross-check` at executor `0.1.1573` (the
  measurement the retired parser could not make): PLAN-13 collides with **PLAN-08** and **PLAN-09**,
  on the same two paths each — `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/runtime_base.py`
  and `test/plan-marshall/platform-runtime/**`. Its third row, against PLAN-01, is a **dead** overlap
  (PLAN-01 landed). ⛔ Never pair PLAN-13 with PLAN-08 or PLAN-09.
  **Clean against everything else:** no `live_plan` and no `sibling_epic_spec` collision, so it
  remains a safe solo emit and a safe partner for any WS-02/WS-03 plan outside the three above.
  — *measured at the PLAN-16 landing; supersedes the conditional wording this row previously carried*
- **PLAN-16** — sequenced first among the three `marketplace/targets/**` plans on purpose: it makes
  the lint gate real *before* PLAN-05 and PLAN-11 add code to that tree. Running it later conflates
  "pre-existing violations" with "violations the neighbours just added".
- **PLAN-15** — D1 (the ADR) touches only `doc/adr/` and is effectively disjoint from everything;
  the contention starts at D2. It conditionally blocks PLAN-11's design.
- **PLAN-06 / PLAN-07** — ⛔ never concurrent: both conditionally touch
  `platform-runtime/standards/contract.md`.
- **PLAN-08 → PLAN-09 → PLAN-14** — strictly sequential within WS-01; all three edit
  `platform-runtime/scripts/**`.
- **PLAN-07 → PLAN-10** — `marketplace_paths.py` is a **three-owner file**: PLAN-07 owns the
  `get_base_path` scopes, PLAN-10 the fallback-composer constants, PLAN-09 `_DEFAULT_RUNTIME_TARGET`.
  Sequence all three; each re-derives rather than assuming what the last left.
- **PLAN-05 / PLAN-06** — concurrent-safe *only because* of one deliberate carve-out:
  `pm-plugin-development/skills/ext-triage-plugin/standards/pr-comment-disposition.md` belongs to
  PLAN-05. ⛔ That carve-out is load-bearing — widening either plan across it is a partition defect.
- **PLAN-15 / PLAN-12 / PLAN-07** — `manage-metrics/standards/data-format.md` is contested three
  ways. Sequence PLAN-15 last of the three.

## Decisions

{One entry per recorded decision — append-only, newest last. This section is a curated
human-facing VIEW; the authoritative append-only record is `logs/decision.log`. Because entries
carry rationale and alternatives the log summary need not, this section is NARRATIVE — the compact
stage preserves it verbatim and never regenerates it.}

- **Epic created by ingesting the standalone `doc/plans/multiplattform/` tree.** That tree was a
  *standalone epic* by design — no orchestrator ledger, everything in git, so a cloud session could
  clone and run it. The ingestion reverses that choice. Alternative considered: leave it standalone
  and run the remaining plans through the cloud lane. Rejected because the epic now has 15 live
  plans across five workstreams with a dense collision graph, and the standalone lane has no queue,
  no disjointness check, and no landing analysis — exactly the machinery this scale needs.

- **The three shipped plans were ground-truth verified, not trusted.** Each run report was treated
  as a claim set and re-derived against HEAD `2cd1a19c` from the implementing source. All three
  landed fully. The verification was worth its cost anyway: it produced the entire PLAN-09 through
  PLAN-16 gap set, none of which was visible from the reports alone.

- **`parallelization_scope` set to 2** (project default was 1). Operator chose one-disjoint-pair-at-
  a-time so PLAN-04 can run beside whichever plan holds the sequential lane. 3 was rejected: the
  ingested README's own partition table is hand-written and it says so, and three-way disjointness
  would rest entirely on that unverified basis.

- **Coupling-inventory row retirement moved from the plan to the orchestrator.** The inventory now
  lives in this ledger, which the [Ledger Write-Boundary] puts off-limits to an executing plan — so
  a plan can no longer retire its own rows, which is how the original epic worked. Plans now
  **report** each row's re-run detection through their inbox message and PR; the orchestrator
  re-derives and retires. ⛔ **The re-derivation test is unchanged and still gates every closure** —
  a row is retired because the coupling is gone from the tree, never because a plan claiming it
  merged. Only the actor moved. Alternatives considered: keeping the inventory in git (rejected —
  it would leave the source directory non-empty, against the ingestion goal) and retiring the
  registry entirely by folding rows into their claiming specs (rejected — it would make an
  *unclaimed* coupling invisible, and unclaimed rows are precisely what produced five of the eight
  new plans).

- **Live OpenCode validation carried as a blocked workstream (WS-05), not as queue rows that could
  be emitted.** The protocol needs a human at an interactive terminal; the cloud lane cannot supply
  one. PLAN-17 and PLAN-18 are `parked` with an explicit unpark sequence. The protocol itself is a
  Watch, not a plan row — staging a row for work the orchestrator can never emit would misrepresent
  the queue.

- **Two specs proceed unsplit at five deliverables each** (PLAN-06, PLAN-07), against the ~6
  scope-bloat guard. PLAN-06: D1–D5 share one authoring toolchain and one three-surface schema
  (`frontmatter-standards.md` ↔ `cmd_validate.py` ↔ `fix-templates.json`); splitting would leave
  those three disagreeing across two PRs, which is the exact defect D1 exists to close. PLAN-07:
  D1–D5 are all "one bundle, one sweep" work whose done-conditions are bundle-wide sweeps over the
  same tree; splitting would run the same sweep three times against a moving surface. Both specs
  carry an instruction to report rather than absorb if the run finds them separable in practice.

- **PLAN-10 also proceeds unsplit at five deliverables**, on a different rationale: all five are the
  same one-line argument (a host/target fact stops living in a general script) applied to five
  small independent sites with self-contained tests. Review burden is additive, not multiplicative.

- **PLAN-19 re-grounded at `3bc01075`, and one of its four deliverables was closed by someone else.**
  Two commits landed on this branch after the ingestion — the `test-quality` epic's own ingestion
  (`9c2894c6`) and the retirement of the whole `doc/plans/` tree (`3bc01075`). The second de-referenced
  `transforms.md`'s dangling link as declared collateral, closing **PLAN-19 D2** — the deliverable this
  ledger had flagged as *the most consequential of the four*, because it was the one in shipped bundle
  content. D2 is now verify-only; D1, D3 and D4 remain open and re-derived at that HEAD.
  ⭐ **The scheduling consequence is larger than the deliverable:** D2 was the only reason PLAN-19
  touched `marketplace/targets/**`, so its collisions with PLAN-05 and PLAN-16 are **dissolved** and
  all three may now run concurrently. Both specs were corrected in place rather than left stale.
  ⚠️ The earlier "`doc/plans/test-quality` was deleted by something outside this session" alarm is
  **resolved and was a false alarm**: it was `9c2894c6` ingesting that epic, not data loss.

- **2026-09-15 — WS-05's live-validation precondition is RESOLVED VIA A SIBLING EPIC, not by running
  PLAN-17/PLAN-18.** Operator reported that OpenCode plans have since run for real and asked that the
  WS-05 precondition be treated as satisfied. Verified against ground truth rather than accepted on
  the paste alone (per the Verify-First contract): `tooling-truthfulness/PLAN-07-opencode-install-docs.md`
  (PR #1484, squash `14fe203c869f`, shipped 2026-09-13) ran D0 — testing the candidate consumption
  paths from THIS epic's own `reference/opencode-validation-protocol.md` — against a **live OpenCode
  1.18.30 install**, per its landing report: marketplace-add and npm-plugin tried-and-rejected, no
  fourth path invented, manual config-dir deploy via the generator + `/sync-opencode` pipeline pinned
  as the primary observed-working path. Corroborated three ways: (1) direct read of
  `tooling-truthfulness/landings/PLAN-07.md`; (2) `corpus cross-check --slug multiplattform` reports
  `PLAN-17-pin-opencode-install-path.md` colliding with
  `tooling-truthfulness/PLAN-07-opencode-install-docs.md` on `marketplace/targets/opencode/**` and
  `doc/developer/distribution.adoc`; (3) `tooling-truthfulness/epic.md`'s own 2026-09-11 Decisions
  entry records the operator explicitly choosing to stage this duplicate work there rather than
  unpark WS-05 here — so the discharge was a deliberate routing choice, not a coincidence discovered
  after the fact. PLAN-07 also shipped README + split `install-claude.adoc`/`install-opencode.adoc`
  install documentation and multi-assistant framing, discharging PLAN-17's D1/D2 and PLAN-18's D1/D4.
  ⚠️ **NOT discharged, and recorded as accepted residual scope rather than silently dropped:** PLAN-18's
  D2 (per-operation real-vs-`no-op` orientation layer over `contract.md`) and D3 (confirmed
  limitations) — no artifact in `tooling-truthfulness`'s shipped set addresses either. ⛔ **One part of
  the operator's paste was NOT corroborated and is recorded as an unverified lead, not fact:** "three
  OpenCode plans currently running in parallel" — every active orchestrator epic's `status.json` was
  read (`finalize-machinery`, `model-provisioning`, `operator-ux`, `test-quality`, plus this one); only
  ONE plan anywhere (`model-provisioning/PLAN-02`) carries `running` status, and this checkout's
  `.plan/local/plans/` holds no active plan directory at all. This does not change the disposition
  above — the load-bearing evidence is the already-landed PLAN-07, not the in-flight claim — but it is
  recorded rather than folded silently into the corroborated half. **Disposition:** PLAN-17 and
  PLAN-18 stay `parked` (the `staged`/`launched`/`running`/`parked`/`shipped`/`landed` vocabulary has
  no "superseded" member); both specs are annotated in place naming the discharge and the residual
  gap. The epic closes with WS-05 resolved-via-sibling rather than executed — the second of the two
  options the resume anchor named at the top of this session, not the first (running the protocol
  here).

- **2026-09-15 — Cleanup A1 re-grounding ran over all 128 claims across all 22 specs at HEAD
  `fb8aadc9c`; full per-claim `corpus set-verdict` persistence is DECLINED, and the rationale is
  recorded rather than the step silently skipped.** Dispatched corroboration (execution-context-
  level-3, role `orchestrator.analyze`) read every claim against current source. Result: 20 of 22
  specs are `landed` — a terminal status the `orchestrate.md` disjointness/prep-ready gate never
  re-examines — and this epic is closing, never re-entering that gate again. Persisting ~120
  landed-spec verdicts through 120+ individual script calls would spend real cost for zero remaining
  admission-gate consequence; the substantive findings are folded into this entry instead, which is
  the audit record a closing epic actually needs. The two specs whose verdicts DO still matter
  (PLAN-17/PLAN-18, addressed above) were re-confirmed unchanged: still unverifiable-by-construction,
  no live install exists in this repository's own sources. **Declined-but-named**, per this
  document's own apply-policy: a silent application is indistinguishable from a lossy one, and that
  rule binds a declination too.
  - **Substantive findings preserved from the pass** (none change any landed plan's shipped status):
    the `Runtime` ABC's `@abstractmethod` count has grown to **33** at HEAD, up from the 24–25 baked
    into PLAN-01/08/09's claim text, and `permission_*` operations now number **14** (not 7) — both
    are leads that moved again since every prior stamp, exactly as those specs' own text warned they
    would. `.claude/skills/sync-opencode/` no longer exists anywhere in the tree: an OUT-OF-EPIC
    commit `7fb092a98` (2026-09-10, "move sync-opencode tooling to a project-level command")
    relocated the deploy engine to `.opencode/scripts/sync_opencode.py` and replaced the Claude skill
    wrapper with a native `.opencode/commands/sync-opencode.md` command. This makes the literal path
    citations in PLAN-04's and PLAN-20's Claim Labels **stale-by-relocation, not stale-by-defect** —
    PLAN-20's longest-match fix (D1) is confirmed intact and durable at the new location. Roughly
    half of PLAN-09/13/14/16/19/20/21/22's claim bullets read `contradicted` at HEAD in the narrow
    textual sense because they describe the plan's own PRE-FIX premise and that plan has since landed
    and closed exactly the gap described — a positive outcome, not a landing defect. No spec's
    already-recorded `landed`/`shipped` disposition is disturbed by any of this.

## Open Defects

- ✅ **CLOSED at the PLAN-12 landing — the OpenCode lane CAN report `total_tokens`, and the first
  complete landing shows what was actually missing.** Eleven consecutive landings reported
  `total_tokens=unknown`, and the entry here read as a standing lane property — something the lane
  structurally could not produce. PLAN-12 produced it: `landing-check` → **`complete: true`,
  `missing_keys: []`**, `total_tokens=45,220,283`. ⭐ **The figure is the lesser half.** What closes
  this defect is that the number arrived **with its population named and its exclusions justified**:
  main session 42,575,467 + verification sub-agent 2,299,893 + Step-6 re-check 344,923, summed from
  raw input+output+cache_read at a stated instant with `cache_write` declared untracked — and an
  earlier three-session attribution **refuted by evidence**, the other two sessions proving to belong
  to PLAN-07 and PLAN-06. The figure is further labelled a live snapshot rather than a sealed total.
  ⛔ So the lane's obstacle was never capability; it was that **a count published without its
  population is not a measurement**, and until this run nobody had assembled the population. — *if a
  later landing regresses to `unknown`, this closure is evidence it is a per-run omission, not a
  lane limitation.*

- ⛔ **THIRD CONSECUTIVE DISCLOSED-BUT-UNDECLARED SURFACE EXPANSION — disclosure is not declaration,
  and only one of the two is read by the gate.** PLAN-12 realized 10 paths against 8 declared, and
  both extras — `script-shared/scripts/command_forms.py` and `manage-metrics/scripts/manage-metrics.py`
  — were **disclosed honestly**, in the PR body and again in the landing's Residue section under an
  explicit *"Recorded surface expansions"* heading. One carries a real finding: the spec's premise
  that *"the scripts already normalized"* was **false for exactly those strings**. ⭐ A plan that
  discovers its spec's premise is wrong, fixes the consequence and says so is behaving correctly.
  ⛔ **But `corpus surfaces` still reports PLAN-12 at 8 claimed entries.** The expansions live in
  prose; the artefact the disjointness gate consults never moved. With PLAN-10's D4 and PLAN-22's
  shared helper this is the third consecutive instance of the same shape, and the pattern is now
  established rather than anecdotal: **plans disclose reliably and declare never.** ⚠️ Consequence
  was nil here — PLAN-12 was the last staged plan, so nothing could collide with it — which is
  precisely why the pattern rather than the instance is what this entry records. — *re-check
  trigger: any landing whose report names a surface expansion — check `corpus surfaces` for the
  spec's claimed count before accepting the disclosure as discharged.*

- ⛔ **A STAGED SPEC'S WORK LIST DECAYS SILENTLY AS ITS SIBLINGS LAND — nothing reconciles the two,
  and it took a manual sweep to notice.** PLAN-05 (`30cd8aaf8`, #1379) closed **two of PLAN-12's
  three named D1 sites** — `pm-documents`'s `content-review.md` and `ref-svg-diagrams/SKILL.md`, both
  now measuring **0** Claude hits — while PLAN-12 sat staged, and no surface reported it. The spec
  went on naming them as work for four months of epic time.

  ⛔ **The gap is structural, not an oversight.** Two reconciliations exist and neither covers this:
  the plan lifecycle derives a landed plan's REALIZED footprint, and cleanup re-grounds a staged
  spec's own CLAIMS against HEAD. Nobody compares a landed plan's realized footprint against OTHER
  staged specs' site lists. ⚠️ Note the asymmetry with the under-declaration class this ledger
  already tracks: that one is a spec claiming too LITTLE surface, and the gate at least sequences on
  it. This is a spec claiming work that no longer EXISTS, which no gate reads at all — a plan
  launched on it would open a PR, find nothing to change, and either report a no-op or invent
  something to justify the deliverable.

  ⚠️ **`corpus cross-check` cannot close this**, and the reason is worth stating: it compares
  DECLARED surfaces against each other, so it would have reported PLAN-05 and PLAN-12 as overlapping
  — which is a collision warning, not a *this-work-is-already-done* signal. The two readings need
  different instruments. — *re-check trigger: at every cleanup, re-measure each staged spec's named
  sites against HEAD rather than only re-grounding its claims; a site measuring zero needs the A2
  positive account before it is carried forward.*

- ⚠️ **NARROWED — the lane's report gap reaches the GATE RESULT, but the consequence is
  inconvenience, not unverifiability.** PLAN-06's hand-off carried no verification section at all —
  no test count, no verify statement, no verifier rounds — where every prior landing reported one.
  That reporting defect is real and stands: a hand-off should carry its own gate statement.
  ⛔ **But the "unverifiable landing" framing recorded here at the time was TOO STRONG, and the
  PLAN-07 landing showed why.** The reasoning was that the change ledger is machine-local, so a
  reader elsewhere could not establish the gate ran. That overlooked the instrument that DOES
  travel: **CI, queryable by anyone through the read-side abstraction.** Checked retroactively,
  PLAN-06's `#1456` is `overall_status: success` with `verify / verify` SUCCESS — its landing was
  never unverifiable; the wrong instrument was reached for. ⭐ **The correct recovery order is CI
  FIRST, ledger second.** — *re-check trigger: every landing — read the hand-off for an explicit
  gate statement, and when it is absent go to `ci checks status --pr-number N` BEFORE the change
  ledger.*

- ⛔⛔ **THE CHANGE LEDGER CAN HOLD EVIDENCE THAT CONTRADICTS A TRUE CLAIM — a sharper failure than
  a missing one.** PLAN-07's worktree has SIX build entries and **every one is a failure**: four
  `compile plan-marshall` and two `verify`, at `exit -1` / `exit 1`. No successful local build is
  recorded at all. The hand-off's explanation holds up — the Step 5 gate first hit a pre-existing
  stale `argparse_surface` disk cache, then daemon-mode could not build the worktree project-dir on
  this host (`pwx` unresolved), so the gate ran via **`in_process`, a path that writes no ledger
  entry**. ✅ CI is green and independent: `#1458` is `overall_status: success` with `verify /
  verify` SUCCESS in **1186s** — a real full run, not a skip.
  ⛔ **File this apart from the PLAN-06 case above.** There the ledger held the evidence and the
  report omitted it — absent evidence, recoverable. Here the ledger holds evidence that ACTIVELY
  CONTRADICTS the true state: a reader querying it for PLAN-07 sees six failures and nothing else,
  and would reasonably conclude the plan shipped ungated. **Misleading evidence is worse than
  missing evidence**, because it defeats the check rather than merely failing to answer it. ⚠️ The
  mechanism — an `in_process` gate run writing no entry — belongs to the build-gate surface, which
  no staged spec owns. — *re-check trigger: a ledger query returning only failures for a plan that
  reports a green gate — read CI before concluding anything, and record which path the gate took.*

- ⛔⛔ **THE SAME-ACT SURFACE OBLIGATION DOES NOT REACH AN IN-FLIGHT AUTHORISED WIDENING — and
  that gap just produced the epic's worst under-declaration.** PLAN-10 realized **22** paths against
  **12** declared: **19 undeclared**, beating PLAN-11's 15. ⛔ **Every one of the 19 is downstream of
  ONE authorised mid-flight scope change.** D4 was widened, with operator authorisation, from
  *relocate a constant* to *add a new platform-runtime op* — different KINDS of change: the first
  touches one file, the second necessarily touches both runtime implementations, the router, the
  base, the contract, the op table and every consumer (7 runtime files + 5 runtime tests + 6
  consumers + 1 consumer test).

  ⚠️ **This is NOT another instance of the known authoring pattern, and treating it as one would
  mis-target the fix.** The known pattern is a spec that under-declares when it is written.
  PLAN-10's spec was **accurate when staged** — swept, `declarative`, 12 entries, 0 unresolved — and
  was invalidated mid-flight. The plan behaved honestly throughout: it recorded the widening in its
  own `plan.md` WIDENED annotation and disclosed it in the hand-off. **What nobody did is update the
  orchestrator spec's `## Expected Surface`, and no rule required anybody to.** [`analyze.md`](../../plan-orchestrator/workflow/analyze.md)
  § "A fold that adds scope updates the declared surface in the same act" binds the ORCHESTRATOR
  when it folds a signal into a staged spec; it says nothing about an authorisation issued to a plan
  that is already running. The artefact the disjointness gate reads is the orchestrator spec, and
  nothing kept it true.

  ⛔ **Gate consequence, the third in this epic and the second on the same surface:**
  `platform-runtime/**` is in PLAN-06's AND PLAN-07's declared surface, and PLAN-07's
  `marketplace/bundles/plan-marshall/**` covers **13 of the 19**. PLAN-10 landed deep inside a
  staged sibling's declared surface having declared none of it. PLAN-11 touched the same surface
  undeclared. ⚠️ **UPDATE at the PLAN-22 landing — stating the obligation IN THE SPEC was tried, and the wording
  was too narrow to bind.** PLAN-22 was the first spec staged carrying the same-act instruction
  explicitly. It was worded as *"if D1's remedy turns out to need a platform-runtime op … it updates
  this section in the same act"* — naming the SPECIFIC widening shape that had just burned PLAN-10.
  D1's remedy needed a **shared helper** (`permission_common.is_claude_target()`), not a
  platform-runtime op, so the antecedent was never satisfied and the surface went un-updated. The
  under-declaration was small (2 of 6) and harmless here, but the lesson is not: **an obligation
  written against last landing's failure shape does not generalise.** The next spec should carry the
  general form — *any file this plan creates or touches that the surface does not name updates the
  surface in the same act* — rather than a re-description of the previous incident.
  — *re-check trigger: any operator authorisation that changes a RUNNING plan's scope —
  the authorisation should carry the same same-act obligation a fold does, and until it does,
  re-measure the realized footprint at every landing rather than trusting the declaration.*

- ⛔ **THE COUPLING INVENTORY'S `Drawn by` COLUMN IS STALE, AND A DERIVED COUNT THIS LEDGER RELIED
  ON WAS WRONG BECAUSE OF IT.** The 2026-09-06 re-grounding refuted PLAN-10's scope premise by
  deriving *"rows whose `Drawn by` cell is unclaimed: **17**, not five"*. That figure is not a
  measurement of unowned work — it is a measurement of **unrecorded ownership**. Partitioned
  against the corpus at HEAD `b64db6671` when the operator's widen decision was executed, the 17
  resolve as: **5** already this plan's, **2** shipped by LANDED plans (`extract-chat-signal.py` →
  PLAN-13 #1376; the `opencode_runtime` metrics boundary → PLAN-09 #1405), **8** owned by other
  STAGED specs (PLAN-06, PLAN-07, PLAN-12), and only **2** genuinely unowned. ⛔ **Root cause is
  structural, not neglect:** the inventory is ledger-resident and off-limits to plans by explicit
  constraint — PLAN-11's D4 was report-only for exactly this reason — so no landing has ever been
  able to stamp its own rows, and the column can only ever decay. ⚠️ **The consequence is that
  every future count derived from that column is wrong in the same direction**, always
  overstating unowned work, and a plan widened onto it would duplicate siblings and redo shipped
  work. The widening executed here used a corpus partition instead and came out at **seven**
  deliverables, not seventeen. — *re-check trigger: any claim of the form "N inventory rows are
  unclaimed" — partition against the corpus before acting on N; and if the orchestrator is ever
  permitted to stamp `Drawn by` at landing, this defect closes.*

- ⚠️ **NARROWED (not re-raised) — the post-merge-verify gap is MECHANICAL, and PLAN-21 shows the
  distinction that matters.** The defect recorded at the PLAN-11 landing stands in form: the change
  ledger still records no post-merge verify on main, for either plan. But the two cases are NOT the
  same risk and collapsing them would overstate this one. PLAN-21's ledger row is `21:36:48Z`
  (`exit_code: 0`, 20736 tests, `--project-dir .../worktrees/worktree-executor-root-resolution`)
  against a merge commit at `21:38:37Z`; its merge parent `33c8140f3` (#1443) landed at `20:25:17Z`,
  over an hour EARLIER, and nothing landed in the 2-minute window. **The verified tree equals the
  merged tree.** PLAN-11's did not — PLAN-130 landed inside its 23-minute gap and became its merge
  parent. ⛔ **The remaining exposure is that nothing DISTINGUISHES these two cases automatically:**
  both present identically as "green verify, worktree project-dir, no post-merge run", and only
  reading the merge parent's timestamp against the verify's tells them apart. — *re-check trigger:
  unchanged — confirm any claimed "post-merge verify" is ledger-dated AFTER the merge commit; and
  when it is not, check whether the merge parent predates the verify before treating it as a real
  gap.*

- ⚠️ **PLAN-21's landing message is INCOMPLETE — `total_tokens` missing, now 7-for-7 on the
  OpenCode lane.** `inbox landing-check` -> `complete: false`, `missing_keys: [total_tokens]`;
  every other required key supplied. **FOLDS into the standing OpenCode-lane entry** as its seventh
  consecutive instance. The producer again correctly wrote `unknown` rather than `n/a`.

- ⛔ **NO POST-MERGE VERIFY ON MAIN FOR PLAN-11 — and the pre-merge one never saw the tree it
  landed into.** The PLAN-11 landing narrative labelled `ee4da4bb` a *post-merge* verify. It is
  green and real — build-job log `ee4da4bbc2d34725a3dc59d21b65b26a.log`, `exit_code: 0`,
  `tests_run: 24773`, `tests_population: measured` — but the change ledger dates it
  `2026-09-07T07:18:58Z` with `--project-dir .../worktrees/target-scoping-adoption`, and the merge
  commit `8f6066cab` is `07:41:33Z`. It ran **23 minutes earlier, in the worktree**. ⛔ In the
  interval, PLAN-130's part 1 (`5c1c8b212`, PR #1436) landed at `07:39:22Z` and became PLAN-11's
  merge parent — so the green gate verified a base that was already stale by the time it merged.
  The change ledger's most recent build row IS that `07:18:58Z` entry: no post-merge verify on main
  exists anywhere in it. *Not disputed: the result. Disputed: the label, and the coverage it was
  taken to imply.* — *re-check trigger: any lane run that reports a "post-merge verify" — confirm
  the ledger row's timestamp is AFTER the merge commit and its `--project-dir` is the main
  checkout, not a worktree.*

- ⚠️ **PLAN-11's landing message is INCOMPLETE — `total_tokens` missing, now 6-for-6 on the
  OpenCode lane.** `inbox landing-check` → `complete: false`, `missing_keys: [total_tokens]`; every
  other required key supplied. **This FOLDS into the standing OpenCode-lane entry rather than
  opening a new defect** — it is the sixth consecutive instance of one already-recorded lane
  property, and the recurrence is the information. ✅ The producer wrote `unknown`, not `n/a`, which
  is the CORRECT choice under the anti-`n/a` rule: no session total was observed, so `unknown`
  ("not read") is honest where `n/a` ("no such thing") would not be.

- ⛔ **UNDER-DECLARATION IS A MEASURED, REPEATING PATTERN — and a recorded warning has already
  failed to stop it once.** PLAN-15 declared **two** Expected-Surface entries (`doc/adr/`,
  `marketplace/targets/component_targets.py`) and its landing touched **seven** files, six of them
  undeclared (`_manifest_decide.py`, `_preference_admissibility.py`,
  `manage-metrics/standards/data-format.md`, `finalize-step-preference-emitter.md`,
  `plan-retrospective/scripts/analyze-logs.py`, `frontmatter-standards.md`), while the one declared
  code file went untouched. ⚠️ **This is not a first offence:** the PLAN-04 landing recorded the
  identical class — *"the parser is no longer the weak link; under-declaration is"* — over ONE
  undeclared file. That warning is in this ledger, and it did not bind.
  ⛔ **The consequence is not hypothetical: it invalidated the reasoning that selected PLAN-15 for
  emission.** PLAN-15 was chosen precisely because its declared two paths were the only ones no
  running plan touched. The verdict was sound given its inputs and wrong in fact. The concurrency
  turned out safe — neither `test-quality` PLAN-110 (test-only) nor `unreviewed-merge-gate-holes`
  (checked directly against its `references.json`) touched any of the six — but **the gate predicted
  neither result, because it never saw the six paths**, and the margin was one file inside
  `manage-metrics/`.
  **Fix direction — another ledger warning will not do it, that has now been tried.** The check must
  be mechanical: compare a landing's REALIZED footprint against its DECLARED surface at drain time.
  `manage-references` already computes exactly that three-way reconciliation.
  — *source: PLAN-15 landing, re-derived from the merged diff at `713f9017`; recurrence of the
  PLAN-04 finding*

- ⛔ **`permission_doctor`'s direct-script `detect-*` route reports a FALSE ZERO on a non-Claude
  target.** Self-disclosed by the PLAN-14 run as a deferred follow-up. The Claude rule-pack
  declaration that landed is **structural, not a dispatch path** — the module's own docstring says
  so — so on OpenCode the Claude rules match nothing and the route reports zero findings,
  indistinguishable from a clean audit. The documented `platform_runtime permission analyze` path is
  already honest; the direct route is not. ⚠️ **This is the ADR-019 class this epic keeps meeting** —
  *an audit separates what it could not evaluate from what it evaluated and found wanting* — the same
  shape as the disjointness-gate silence that ADR was written for, now in shipped tooling rather than
  in the orchestrator. Unclaimed: WS-01 is closed, so no chain will pick it up.
  — *source: PLAN-14 landing, run-disclosed and corroborated against the shipped docstring*

- ⚠️ **The executor's self-heal walks the wrong plugin-cache depth — surfaced ONLY because a
  worktree was torn down.** After PLAN-09's worktree was removed, `.plan/execute-script.py` still
  pointed its pinned script paths at the deleted tree, and the self-heal that should have recovered
  did not; the run regenerated the executor via `generate_executor.py generate --force`
  (154 → 162 scripts) to unblock its own inbox write. **Partially corroborated here**: the cache
  nests as `{marketplace}/{bundle}/{version}/`, and for this bundle the two names COLLIDE —
  `~/.claude/plugins/cache/plan-marshall/plan-marshall/0.1.1594/` — which is exactly the depth
  ambiguity a walk can get wrong. ⛔ The failing walk itself was **not** independently reproduced
  (that needs the teardown condition); the nesting is verified, the walk defect is the run's claim.
  Out of epic scope — it belongs to `tools-script-executor/scripts/generate_executor.py`, which no
  plan here owns. **This is the THIRD defect in one class** alongside the `queue --transition`
  status-token hole and the `corpus set-verdict` off-by-one: orchestrator/executor tooling that
  fails quietly rather than loudly. The three want one plan, not three.
  — *source: PLAN-09 landing, run-reported and partially re-derived*

- ⚠️ **`CROSSING-INVENTORY.md` landed at the REPOSITORY ROOT and is tracked on `main`.** It is
  PLAN-08's D1 working artifact (its own first line reads "Crossing Inventory — PLAN-08"), 4,493
  bytes. The spec asked for the enumeration **in the PR body and the inbox message**, not in the
  tree, and the file is undeclared in PLAN-08's `## Expected Surface`. ⛔ **Not folded into any
  staged plan** — no staged spec declares the repository root, and this is a one-file removal, not
  a deliverable. It is a standing cleanup action.
  — *source: PLAN-08 landing, re-derived from the merge diff at `7b0ad0850`*

- ⚠️ **The OpenCode lane drops a spec's "report X in the inbox message" obligation.** PLAN-08's D1
  and D4 each required their enumeration in **both** the PR body and the inbox message. The PR body
  carried both; the inbox message carried **neither** — it is a bare `landing-facts` block. This is
  a **lane contract gap, not a one-off**: RUNBOOK Step 10 produces the facts block and nothing
  carries a per-spec reporting obligation into it, so the next spec asking for a reported
  enumeration loses it the same way. ⛔ The orchestrator absorbed the cost this time by
  re-deriving D4 itself; that is not a repeatable substitute, because the whole point of the inbox
  half is reconciliation without reading the PR.
  — *source: PLAN-08 landing*

- ⚠️ **`orchestrator queue --transition` accepts an ARBITRARY status token — OUT OF EPIC SCOPE,
  recorded here so it is not lost.** Observed directly during the PLAN-08 drain: a transition to
  `bogus` returned `status: success` with `previous_status: staged, new_status: bogus`, and had to
  be corrected by a second call. The status vocabulary may be open by design — `resume-summary`
  renders a residual line for unrecognised statuses — but nothing rejects an obvious typo, and a
  mistyped status silently removes a plan from BOTH the live queue and the terminal set, where the
  residual line is the only thing that keeps it visible at all. ⛔ Same territory as the recorded
  `corpus set-verdict` off-by-one: a `plan-marshall` bundle defect in another epic's ground. It does
  **not** belong to any plan here and must not be folded into one.
  — *source: this drain session, observed directly*
  ⚙️ **FOLDED IN at the PLAN-20 landing — a fourth member of the same cluster.** The run found that
  the daemon re-enters the executor from inside `--project-dir`, so a worktree needs its **own**
  `.plan/local/` plus a generated executor before the build gate will run; the run hand-built that
  state to proceed. ⛔ **These four are not unrelated bugs.** Three of them — the executor self-heal
  walking the wrong plugin-cache depth (PLAN-09), this worktree self-hosting gap, and the
  `set-verdict` index confusion — are **path/state resolution across the executor's own
  boundaries**, and all four share the failure MODE that matters: they fail QUIETLY, returning a
  success or a zero rather than an error. This is now the strongest candidate for a single non-epic
  plan. — *source: PLAN-20 landing, run-disclosed*

- ⚠️ **The `permission_fix.py` permission-DSL residue is now UNCLAIMED.** PLAN-08 owned the
  coupling-inventory row covering it (`Drawn by: 080`) and landed **without touching the file at
  all** — `permission_fix.py` is absent from the merge diff. Re-derivation finds every symbol the
  row names intact (`EXECUTOR_PERMISSION`, `OVERLY_BROAD_PYTHON`, `TIMESTAMP_PATTERN`,
  `DATE_PATTERN`, `normalize_path_perm`, `is_individual_script_permission`, the `Skill(…)` /
  `SlashCommand(…)` wildcard generators), so the row STAYS, unnarrowed, and its `Drawn by` is now
  `— (unclaimed)`. ⛔ **PLAN-14 cannot absorb it**: its own spec names `permission_fix.py` as
  "PLAN-08's surface" and excludes it explicitly. Per the epic's own decomposition history,
  unclaimed rows are what produced five of the eight added plans — this one needs an operator
  decision on whether to stage a plan for it.
  — *source: PLAN-08 landing, D4 re-derivation by the orchestrator*


- ⚠️ **OUTSTANDING WORK, not a code defect: the reviewer-policy change is enacted but unrecorded in
  git.** Per operator direction the policy is *only CodeRabbit is required; sourcery and pr-agent are
  optional*. It is documented in `.plan/local/opencode/RUNBOOK.md` — which is **git-ignored** — and,
  per the runbook's own rule that a contract change ships as its own `chore/` PR, was deliberately
  kept out of PR #1375. **That PR has not been raised.** ⛔ The policy is therefore already in force
  (PLAN-16's landing shows `Sourcery review` SKIPPED) while existing on one machine and nowhere else.
  This is not a plan deliverable and is not folded into one — it is a standing operator action.
  — *source: PLAN-16 landing, self-disclosed by the run*

- ✅ **CLOSED at the PLAN-20 landing — `sync_opencode.py`'s prefix-ambiguous over-prune is FIXED
  and pinned.** The defect: `_derive_synced_bundles` added **every** bundle whose name prefixed an
  entry, so `pm-dev-java-cui-{skill}` entered both `pm-dev-java` and `pm-dev-java-cui`, and an
  unscoped sync from a source holding only `pm-dev-java-cui` entries would prune `pm-dev-java`
  entries it never synced. **Re-derived from the merged diff at `565d4ade7`**: the
  `for kb in known_bundles: ... matched.add(kb)` loop is now a `matches = [...]` comprehension
  followed by `matched.add(max(matches, key=len))` — exactly the "take the LONGEST matching bundle
  per entry" remedy this entry recorded as the fix direction. Two BEHAVIOURAL regression tests drive
  the real script against a real filesystem; red-first was demonstrated for the
  shorter-bundle-preserved case. ⚠️ Both tests `pytest.skip` if no prefix-ambiguous pair exists in
  `marketplace/bundles/` — an honest guard (a skip is visible, unlike a silent pass), but the
  coverage is contingent on the bundle set surviving.
  — *raised: post-landing review of PR #1372; closed: PLAN-20 landing, PR #1418*

- ⚠️ **`AGENTS.md:74` and `CLAUDE.md:115` instruct the BARE `uv run python
  marketplace/targets/generate.py` form — and that instruction is what produced PLAN-19's false F1.**
  Both files tell an agent to invoke the generator through `uv run` directly. On a host where `uv` is
  not on `$PATH` — the normal state, since pyprojectx provisions it into `.pyprojectx/` rather than
  installing it globally — that command fails, and an agent following the instruction literally
  concludes the generator is unrunnable. PLAN-19's run did exactly that and filed F1.
  **The working form is the wrapper** (`./pw generate` / `generate-claude` / `generate-opencode`), and
  `CLAUDE.md`'s own hard rule already says never to hard-code build commands — but the generator is
  absent from its resolved-executor list, so the rule does not reach this case.
  ✅ **OWNED — folded into PLAN-07 D5** ("Command form and agent-instructions file"), the deliverable
  that already single-sources command forms; its Expected Surface gained `AGENTS.md` and `CLAUDE.md`
  in the same edit. ⛔ Still NOT folded into PLAN-16: that plan is lint scope, and widening it across
  the agent-instruction files for an unrelated concern was the wrong home.
  — *source: PLAN-19 F1 root-cause analysis, operator-prompted*

- ✅ **`author-cloud-plan`'s dead-template defect is SUBSTANTIALLY RESOLVED — downgraded at the
  PLAN-19 landing, keep this correction.** The entry previously read: "still cites that path four
  times, so the cloud lane can no longer author a plan." Re-derived at HEAD `ad8297fa`:
  `_template/plan.md` appears **exactly once** in `.claude/skills/author-cloud-plan/SKILL.md`
  (line 29), and that occurrence is a *historical retirement note* whose own sentence says the rules
  are "stated here and cited nowhere else" — the OWNED-ELSEWHERE section does carry them inline.
  **The cloud lane CAN author a plan.** What genuinely remains is a wording defect: two sentences
  (lines 177, 205) still say "the template owns …" for a referent that no longer names a file.
  Cosmetic, still out of epic scope, still must not be folded into any plan here.
  ⚠️ **Lesson recorded, not just the fix:** the overstated version of this entry was repeated
  verbatim in PLAN-19's run report. A stale ledger defect propagated into a run's output, which is
  what leaving a resolved defect standing costs. — *corrected by: PLAN-19 landing analysis*

{Known defects surfaced by landings or observations that are not yet owned by a staged
plan. When a defect is folded into a plan spec, move it out of this list and note the owning PLAN-NN.}

- ✅ **OWNED — `health_check`'s `permissions` check names a file it did not check → folded into
  PLAN-09 D1.** `_claude_runtime_impl.py::health_check` resolves `_claude_project_settings_path()`
  (which prefers `.claude/settings.json`) but hardcodes `settings.local.json` in the check's
  `details`, misdirecting a `settings.json`-only project. PLAN-09 D1 already has `health_check` open
  and already declares `_claude_runtime_impl.py`, so the fold added **no** surface. Retained here as
  a pointer only — the deliverable is the record now.
  — *source: landing PLAN-01; folded at the operator-directed follow-up pass*

- **`Grep` tool absent from the credentials-directory deny set.** `_EXFILTRATION_BASH_VECTORS` denies
  the Bash `grep` command, but no `Grep(...)` tool-permission rule exists — so the tool-level read
  path into a credentials directory is not denied. PLAN-03 left this open deliberately: it is an
  **operator policy question**, not a bug to be fixed by a plan. — *source: landing PLAN-03, round 9*

- ⚠️ **`orchestrator.py corpus set-verdict` has an off-by-one between its documented and actual claim
  indexing — OUT OF EPIC SCOPE, recorded here only so it is not lost.** The range check is
  `0 <= args.claim_index < len(claims)` (0-based), while the payload reports `claims_total` as the
  1-based count and neither the SKILL.md canonical block nor the standard states the base. The
  observable consequence: passing `--claim-index N` for the *last* claim returns
  `claim_index_out_of_range` **while the same payload says `claims_total: N`**, and passing a
  1-based index silently stamps the verdict onto the **wrong claim** — association is by nesting, so
  the misattachment is invisible unless `previous_line` is read. Hit during this ingestion; seven
  verdicts landed on the wrong claims and were corrected. ⛔ This is a `plan-marshall` bundle defect
  in a different epic's territory — it does **not** belong to any plan here and must not be folded
  into one. It needs its own plan against `plan-orchestrator/scripts/orchestrator.py`.
  — *source: this ingestion session, observed directly*

- ✅ **CLOSED at the PLAN-16 landing — the executor was regenerated to `0.1.1573` and the
  disjointness gate works again.** Re-measured with `corpus surfaces`: **20/20 specs `declarative`,
  `indeterminate_count: 0`**. Raising `parallelization_scope` above 1 is no longer blocked on tooling.
  Historical statement of the defect follows. ~~The executor resolves
  `plan-marshall:plan-orchestrator:orchestrator` to cache version **`0.1.1565`**, while the loaded
  skill is **`0.1.1573`**. The 1565 copy's `corpus` subparser accepts only
  `cross-check, enumerate, epics, set-verdict, verdicts` — it has **no `surfaces` verb**, which the
  1573 SKILL.md documents and which [`workflow/orchestrate.md`](…) Step 4 requires as one of the two
  halves of the disjointness test. Observable consequence: `corpus surfaces --slug multiplattform`
  returns `error: invalid_invocation / unknown_verb`, so the `next` verb **cannot establish
  `admits_disjointness_check` for any candidate** and every candidate is `indeterminate` by
  tooling failure rather than by declaration. ⛔ Do not work around this by reading the rendered
  `Surface (expected)` column.~~ Remedy applied: the PLAN-16 run regenerated the executor.
  — *raised: PLAN-04 landing analysis; closed: PLAN-16 landing*

## Watches

- ✅ **CLOSED — the verify test-count instability is not structural; four readings settle it.**
  24773 (PLAN-11) -> 20736 (PLAN-21) -> 25254 (PLAN-10) -> **25270 (PLAN-22, +16)**. All four from
  the same `--command-args verify` invocation shape. After a 16% dip and a full recovery the count
  has now HELD across two consecutive gates, so neither a permanent coverage loss nor an ongoing
  instability is supported by the evidence. ⛔ **What the episode leaves behind is not a defect but
  a measurement gap, and it is the part worth keeping:** nothing in the pipeline compares one gate's
  test count to the previous one, which is why establishing that nothing was wrong took FOUR
  landings and manual arithmetic across three separate drains. A single gate-to-gate delta would
  have answered it at the first reading. Recorded here rather than in a plan because no staged spec
  owns the build gate's reporting surface.

- ✅ **RETIRED — the CodeRabbit unobtainable-arm exposure, closed from BOTH ends in the same
  window.** PLAN-11 shipped with CodeRabbit disclosed-`unobtainable` (account-level 7-day quota, no
  legitimate new head, cosmetic pushes forbidden). Two things have since changed. **(1) The
  standing fix landed:** `29a3dad1c` — *fix(automatic-review): arm the CodeRabbit rate-window
  recovery* (#1433) is on main. **(2) The recovery policy was EXECUTED and it worked:** PLAN-21's
  first PR #1439 stalled for hours on the same quota; it was closed unmerged and reopened as #1444
  on the same head, where the quota had cleared and the review arrived within minutes — CodeRabbit
  then found a real Major defect (the advertised `PLAN_TRACKED_CONFIG_DIR` remedy did not actually
  pin the executor), fixed at `35a3b8532`. #1439 is confirmed `closed` with `merge_commit_sha:
  null`. ⭐ **The finding is the point:** the arm PLAN-11 could not obtain caught a defect that
  would otherwise have shipped a documented remedy that did not work. Retiring the watch records
  that the exposure now has a working recovery, not that the risk never mattered.

- ⛔⛔ **SECOND FALSE-CLEAN VERDICT, FOUND IN THIS SAME SESSION — and this one is a LIVE gate
  failure, not a retrospective one.** The emit round after PLAN-11's landing measured all four
  staged candidates against test-quality **PLAN-130's actual open PR #1435** (112 paths), because
  the anchor's standing ⛔ instruction is to re-derive the live_plan set before any emit. Result:

  | Candidate | `corpus cross-check` says | Measured against live PR #1435 |
  |---|---|---|
  | PLAN-06 | overlaps (sibling spec, `test/pm-plugin-development/**`) | **3 paths** — agrees |
  | PLAN-07 | **CLEAN** against every live plan | ⛔ **106 of 112 paths** |
  | PLAN-10 | **CLEAN** against every live plan | ⛔ **5 paths**, incl. `test_marketplace_paths.py` and `test_generate_executor.py` — its own subject tests |
  | PLAN-12 | overlaps (sibling spec, `test/`) | **112 paths** — agrees |

  ⛔ **Root cause, and it is NOT the containment blindness this ledger already tracks.** It is that
  a live plan contributes its surface from `references.json` `affected_files`, and **PLAN-130 is at
  phase `3-outline`, so it has no `affected_files` key at all**. Its live-plan row therefore
  compares an EMPTY set and matches nothing. The two candidates that came back clean were cleared
  by a comparison that had nothing on the other side. ⚠️ The two that were correctly flagged were
  flagged by the *sibling-epic spec* comparison, not the live-plan one — so the sibling-spec arm
  masked the live arm's total silence, and only re-deriving against the real PR exposed it.

  ⛔ **This is the `could-not-evaluate reported as a clean zero` class in its purest form** and it
  belongs to the recorded orchestrator/executor tooling cluster as its EIGHTH member: a live plan
  before outline-completion must resolve to **indeterminate**, never to disjoint, exactly as ADR-019
  already requires for an unreadable *spec* surface. The spec side honours ADR-019; the live-plan
  side does not. — *re-check trigger: any emit round where a live plan sits at a phase before its
  footprint is captured — measure against its open PR before trusting a clean cross-check.*

- ⛔ **UNDER-DECLARATION HAS NOW PRODUCED A FALSE DISJOINTNESS VERDICT, not merely an inaccurate
  record — and prose/glob declarations are the mechanism.** PLAN-11 realized **22** paths against
  **7** machine-comparable declared ones: 15 undeclared, the epic's worst (PLAN-04: 1, PLAN-15: 6).
  ⛔ The consequence is concrete: PLAN-11 edited
  `marketplace/bundles/plan-marshall/skills/platform-runtime/{SKILL.md,standards/pretooluse-enforcement.md}`,
  and `platform-runtime/**` sits in **PLAN-06's** declared surface AND **PLAN-07's**. Had either
  been launched concurrently the gate would have permitted it, because PLAN-11's declaration never
  named `platform-runtime` at all. ⚠️ **But the 15 do not share one cause, and treating them alike
  would mis-target the fix** — see `landings/PLAN-11.md` for the full partition. Three classes are
  NOT spec-authoring faults: (a) 3 paths are D2's **split output** in a sibling component
  (`marshall-steward-claude-wizards/**`), which no declaration written before the split boundary was
  chosen could have named — a *split* provably cannot stay inside the glob it splits out of;
  (b) 2 are declared in PROSE the parser cannot compare ("both component-tree emitters' consumption
  sites"); (c) 3 were HYPOTHESIS-labelled with an explicit re-derive-at-outline instruction, and the
  plan re-derived them correctly — **that is the spec working, and it must not be counted as a
  miss**. Only **7** are genuine unanticipated misses. ⛔ The actionable target is therefore (a) and
  (b) — a declaration form that admits splits, and a parser-comparable form for "the consumers of
  X" — NOT more diligence on the same form. — *re-check trigger: the next landing whose spec
  declares a split or a prose consumer-set; measure realized-vs-declared before drawing the
  conclusion.*

- ✅ **RETIRED — the ⛔⛔ PLAN-130 containment collision was a genuine near-miss, and the two plans
  were disjoint IN FACT.** The standing prohibition (do not run test-quality PLAN-130 while PLAN-11
  runs; both claim the test tree and the exact-path matcher cannot see containment) was violated:
  both ran, and landed **two minutes apart** — `5c1c8b212` (#1436, PLAN-130 part 1) at `07:39:22Z`,
  which became PLAN-11's merge parent, then `8f6066cab` at `07:41:33Z`. **Measured overlap: ZERO
  files.** PLAN-130 part 1 touched 76 paths, PLAN-11 touched 22, intersection empty; PLAN-130's
  still-open PR #1435 (112 paths) likewise has an empty intersection with PLAN-11's landed set.
  ⛔ **Retiring the watch does NOT soften the rule.** Disjointness here was luck of authorship, not
  a checked property — the very same landing shows the gate returning a false clean verdict on
  `platform-runtime` (watch above). What this retires is the *specific* PLAN-11/PLAN-130 pairing;
  what it records for the next session is that the near-miss was real: PLAN-11's green verify
  predates PLAN-130's landing by 20 minutes, so no gate ever saw the merged tree.

{Mid-flight observations that need monitoring but no immediate action.}

- ⛔ **DEMONSTRATED, not theorised: the disjointness gate is BLIND TO CONTAINMENT, and it is hiding a
  live cross-epic collision right now.** The exact-path matcher compares normalized paths for
  equality, so a spec declaring `test/plan-marshall/**` and a sibling spec declaring
  `test/plan-marshall/platform-runtime/` produce **no overlap row at all**. Concretely, at the
  PLAN-07 re-grounding: sibling epic `test-quality` has already EMITTED its `PLAN-110`, which
  declares `test/plan-marshall/platform-runtime/`, `.../lsp-client/`, `.../tools-file-ops/`,
  `.../build-server/` and `.../workflow-integration-git/` — every one contained inside **PLAN-07's**
  `test/plan-marshall/**` — and `corpus cross-check` reports **zero** rows between the two.
  ⛔ **A clean cross-check between two test-tree plans is SILENCE, not a checked negative.** This is
  the ADR-019 class in the gate itself, and `test-quality`'s own ledger independently records the
  same limitation from the scheduling side, so it is not a quirk of one epic's declarations.
  **Operational consequence, binding until the matcher understands containment:** before emitting
  or launching any plan that declares a test-tree glob, READ the sibling epics' declared surfaces
  by hand rather than trusting a zero. — *re-check trigger: any change to the overlap matcher, or
  either epic closing*

- ⚠️ **PLAN-14's D1 pin does not enforce D1's property.** The done-condition asked for a test that
  sets `runtime.target` to a non-Claude value and asserts no `.claude/settings*.json` is written.
  What shipped is `test_script_performs_no_settings_io`, a SOURCE-SUBSTRING assertion: it calls
  `inspect.getsource` and asserts strings like `'WebFetch('` and `'write_text'` are absent from its
  own module text. It sets no target, drives no project, and touches no filesystem. ⛔ It fails in
  BOTH directions — it breaks on an innocent rename, and it passes for any bypass not using those
  literal spellings (an f-string built in parts, a helper in another module, an `os.write`). It also
  asserts `'json.loads' not in source` while `test_categorize_invalid_json` exercises JSON input, so
  a future refactor reaching for the obvious spelling will trip it for the wrong reason.
  **The property itself HOLDS at this HEAD** — independently re-derived at the landing, no hit for
  `WebFetch(`, `settings.json`, `_load_settings`, `_save_settings` or `claude_runtime`. This is a
  missing-enforcement watch, not a false claim. — *re-check trigger: any edit to `permission_web.py`,
  or a plan that can replace the pin with a target-driven one*

- ⚠️ **PLAN-08's second HYPOTHESIS was never re-derived: "no general skill script outside the three
  named binds `claude_runtime` for permission work."** It is an ASSERTED ABSENCE, and the spec
  carried its own classification test (at authoring time the search returned six non-cache files
  outside the three named, each out of scope for a different reason — a hit refutes **only** if it
  performs permission work). Nothing in the PR body or the run report shows the sweep was re-run and
  classified. The first hypothesis (intent recoverability) WAS settled — D1 stated an intent for
  every site and the plan did not hit its HALT condition — so this is a genuine single gap, not a
  blanket doubt. — *re-check trigger: before PLAN-09 or PLAN-14 edits the permission surface; the
  sweep is cheap and its refutation would widen either plan*

- ⚠️ **A run report can be stale against its own landing — PLAN-08's is.**
  `.plan/local/oc-plans/multiplattform/080-permission-skills-through-the-registry/report.md` still
  reads `D2 — NOT STARTED`, `D4 — NOT STARTED`, `D1 — DONE, not committed`, Step 8 "in progress" and
  Step 10 "pending", while reporting `step-9-self-check:done` and having actually merged and emitted
  its landing. ⛔ **Do not read that file as ground truth for what shipped** — the merged tree is
  authoritative. This is the same class PLAN-19 taught (a stale record propagates into whatever
  reads it next), now observed on the report side rather than the ledger side. The file is outside
  the ledger write-boundary, so the orchestrator records it rather than correcting it.
  — *re-check trigger: if the lane adds a report-finalization gate to RUNBOOK Step 9*

- ✅ **RETIRED, 2026-09-15 — the re-check trigger fired, but the resolution is NOT the one this watch
  anticipated.** `reference/opencode-validation-protocol.md` remained an operator-run runbook that
  never ran from INSIDE this epic. What actually happened: the operator reported OpenCode plans
  running, and ground-truth verification found the protocol's core consumption-path test had been run
  — not by unparking WS-05 here, but by `tooling-truthfulness/PLAN-07-opencode-install-docs.md`
  (PR #1484), a sibling epic's plan, staged there on deliberate 2026-09-11 operator direction as an
  accepted cross-epic duplication of PLAN-17/PLAN-18. See the epic.md Decisions entry dated
  2026-09-15 for the full corroboration chain. WS-05 does not unpark; it resolves closed instead,
  with PLAN-17/PLAN-18 left `parked` and annotated, and PLAN-18's D2/D3 recorded as accepted residual
  scope. — *retired rather than fired-as-anticipated: the trigger's condition (operator reports an
  install) held, but the consequence differs from what this watch predicted.*

- **The `targets-scope-invalid` doctor rule's completeness is 34.5%** (PLAN-02's own final
  self-measurement) — roughly two-thirds of otherwise-invalid `targets:` declarations pass the doctor
  silently and are caught only at build time. Architecturally intentional: soundness over
  completeness, because a consumer install has no PyYAML and the rule is stdlib-only. Disclosed in
  three places in the tree. — *re-check trigger: the stdlib constraint changes, or PLAN-11 extends
  the rule to file level*

- **Is `targets:` the right mechanism at all, versus a per-target ignore manifest?** Recorded in
  PLAN-02's residue as genuinely open and untouched by all 15 of its verification rounds. PLAN-11
  extends the mechanism the repository chose rather than re-opening the choice. — *re-check trigger:
  PLAN-11 or PLAN-15 surfaces evidence the choice is wrong*

- **`component_targets.py`'s degradation default (ship on read fault) is asserted, not proven.** The
  module's own docstring argues both directions and picks fail-open; its own history — multiple
  fail-open defects found and fixed across PLAN-02's rounds 6, 10 and 11 — is evidence against it.
  — *re-check trigger: any further fail-open defect in that module*

- **The `LEVEL_TABLE` / `model_map` cross-target import direction** is recorded as a proposal in
  PLAN-07's D4, but the fix is `marketplace/targets` work that **no plan currently owns**. PLAN-07
  records it rather than fixing it, by its own surface boundary. — *re-check trigger: PLAN-07's
  landing; if the proposal still stands, stage it as a plan in WS-02*

- ⛔ **RETRACTED — PLAN-19's F1 was a MISDIAGNOSIS. The generator gate runs fine here; do not
  re-derive the gap.** F1 reported `generate.py --target all` as unrunnable because `uv` is not on
  `$PATH`. That premise is wrong: **pyprojectx installs `uv` itself** —
  `[tool.pyprojectx.main] requirements = ["uv"]`, whose own comment reads *"uv is the sole tool
  pyprojectx installs"* — and it is already provisioned at `.pyprojectx/uv-0.9.16/uv`. `./pw generate`
  (and `generate-claude` / `generate-opencode`) therefore work on this host today. A bare `uv` lookup
  on `$PATH` is simply the wrong probe for whether the gate can run.
  **Consequence: no plan in this epic is blocked on tooling for the generator gate.** PLAN-16,
  PLAN-05 and PLAN-11 were briefly held on this false premise and are released.
  — *retracted by: operator challenge, verified against `pyproject.toml` and `.pyprojectx/`*

- ⚠️ **A SIBLING EPIC — `test-quality` — targets `test/` trees this epic's staged specs also declare.**
  Surfaced by `corpus cross-check` at executor `0.1.1573`, which reaches sibling epics (the retired
  parser's reading could not). `corpus epics` reports two active epics: `multiplattform` and
  `test-quality`. Its `PLAN-130-sweep-the-prose-…` and `PLAN-135-sweep-the-preambles-…` overlap
  **PLAN-06** on `test/pm-plugin-development/**` and **PLAN-07** on `test/plan-marshall/**` (the
  PLAN-03 rows are dead — that plan landed). ⛔ This is the duplication class a single ledger
  structurally cannot see, and both of ours are still **staged** — so the collision is live, not
  historical. Check the `test-quality` queue before emitting PLAN-06 or PLAN-07, and coordinate rather
  than racing: two epics editing one test tree is a merge conflict neither ledger predicts.
  — *re-check trigger: before emitting PLAN-06 or PLAN-07; or if `test-quality` closes*

- **`lint` covers `marketplace/targets/` but `format` does not.** PLAN-16 widened the `lint` and
  `lint-fix` aliases and `[tool.ruff] src` to include the tree, while `fmt` / `format`
  (`pyproject.toml:100-101`) were deliberately left at their original path set. Self-consistent today
  — `lint-fix` reaches the new tree, so I001 stays auto-fixable — but `./pw format` will not format
  `marketplace/targets/`, and the reason for the asymmetry is recorded in neither file.
  — *re-check trigger: any format-sensitive rule enabled for that tree, or a formatting diff
  appearing there*

- **`distribution.adoc`'s target table can drift from the `claude-distribute.yml` matrix.** Raised
  by CodeRabbit on PR #1372 and **declined on the record** by the operator as a deliberate
  documentation trade-off: the table is a human-maintained current snapshot and the surrounding
  prose already names the workflow as its source of truth, so generating it (or adding a CI check)
  would couple a distribution doc to a workflow file for a two-row table. Verified accurate at this
  analysis — the table's `claude`/`opencode` rows match `.github/workflows/claude-distribute.yml`
  lines 39-46. The bot kept the finding open; it is a watch here, **not a defect**.
  — *re-check trigger: any change to that workflow's `strategy.matrix.include`, or PLAN-17/PLAN-18
  touching `distribution.adoc`*

- **PLAN-04 landing does NOT settle the OpenCode plural-layout assumption.** PLAN-04's own
  HYPOTHESIS — that OpenCode discovers plural `skills/`/`agents/`/`commands/` — stays
  `unverifiable`: its tests are temp-directory only by design and no clone artifact can reach a live
  install. ⛔ Do not read the shipped `/sync-opencode` skill as confirmation. Still owned by WS-05's
  `../reference/opencode-validation-protocol.md` § 1.2. — *re-check trigger: WS-05 unparks*
