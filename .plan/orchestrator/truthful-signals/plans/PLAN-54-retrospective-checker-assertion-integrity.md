# PLAN-54: Retrospective Aspect-Checkers Assert Nothing, Then Assert Too Much

epic: truthful-signals
workstream: WS-01

> Staged plan spec. Surfaced 2026-07-22 by the retrospective of the archived plan
> `2026-07-22-modernize-python-toolchain`, which found **two defects in its own tooling** rather
> than in the plan under review (lessons `2026-07-22-22-001`, `2026-07-22-22-002`). Both verified
> at ground truth @ `287c3c86d`, one of them empirically. Split out of PLAN-51 rather than folded
> into it — see Dependencies.

## Objective

Two aspect-checkers in `plan-retrospective` reach verdicts they have not earned, in opposite
directions. `check-artifact-consistency` cannot parse the canonical `Affected files:` bullet form,
so its declared set is silently empty and its strict peer then compares ∅ against ∅ and reports
"agree exactly" — a **double false green** in which the declared-vs-achieved assertion is never
made at all. `check-routing-decisions` infers *why* a step was pruned from the bare fact that it is
absent, so a step legitimately dropped by the posture tier is reported as a mis-prune — a **false
positive** that trains readers to distrust the checker. Make the first checker fail loudly when it
cannot parse, and the second attribute absence only to a cause it actually established.

## Deliverables

1. **D1 — fix the affected-files extractor.** `_AFFECTED_FILE_BULLET_RE` must match the canonical
   `` - `path` (intent) `` bullet, not only the bare `` - `path` `` / `- path` forms. Re-ground the
   canonical bullet grammar against the solution-outline standard before widening the pattern —
   the outline authority, not this script's docstring, defines the shape.
2. **D2 — a parse that yields nothing must not read as "nothing to check".** An extractor returning
   ∅ from a solution outline that visibly contains an `Affected files:` heading is a **parse
   failure**, not an empty declaration. Distinguish "no `Affected files:` section present"
   (legitimately skip) from "section present but zero bullets parsed" (loud failure). This is the
   half that survives even if the grammar drifts again — D1 fixes today's regex, D2 stops the next
   grammar change from silently reproducing the same false green.
3. **D3 — remove the vacuous ∅ == ∅ pass.** `check_affected_files_exact_match` returns
   `pass, 'Outline and references agree exactly'` when both sets are empty, which its docstring
   states as intended ("including both empty"). Two empty sets are not agreement, they are absence
   of evidence; the verdict must be a skip or a failure carrying why, never a pass claiming an
   assertion that was not performed.
4. **D4 — stop inferring prune cause from absence.** `evaluate_mis_prunes` computes
   `absent = step not in bare_final` and then attributes that absence to the hard-coded
   `_PRUNABLE_PREDICATES` entry (`'sonar-roundtrip': 'no_code_delta'`), failing the check when the
   realized footprint touched production. A step dropped for a *different* legitimate reason — the
   posture/lane tier — is misreported. The checker must establish the actual recorded prune reason
   before re-evaluating a predicate against it, and must return an explicit "cause unknown" verdict
   rather than assuming the only cause it knows about.
5. **D5 — tests pinning both polarities.** (a) The canonical `` - `path` (intent) `` bullet is
   extracted; (b) a present-but-unparseable `Affected files:` section fails loudly and does **not**
   reach the exact-match check as ∅; (c) ∅ vs ∅ never returns `pass`; (d) a step absent because the
   posture tier dropped it does not produce `mis_prune:*` `fail`; (e) a genuine mis-prune still
   fails (the checker must not be defanged into uselessness by D4).

Five deliverables, under the split guard.

## Claim Labels

- OBSERVED (verified **empirically**, not by reading): `_AFFECTED_FILE_BULLET_RE` at
  `check-artifact-consistency.py`:65 is `r'^\s*-\s+`?([^`\n]+?)`?\s*$'` with `re.MULTILINE`.
  Executed against four inputs: `` - `src/foo.py` (adds the thing) `` → `[]`;
  `` - `src/foo.py` `` → `['src/foo.py']`; `- src/foo.py` → `['src/foo.py']`;
  `` - `src/foo.py` (intent) `` (trailing space) → `[]`. The trailing `\s*$` anchor cannot admit a
  parenthetical after the closing backtick, so the canonical intent-annotated form yields nothing.
- OBSERVED: the empty extraction is reported as a benign skip — `check_affected_files_recall`:190-191
  returns `'skip', 'No Affected files declared in solution outline', {'declared': 0}`, which is
  exactly the `declared: 0` the retrospective reported.
- OBSERVED: the strict peer passes on two empty sets — `check_affected_files_exact_match`:228-229
  returns `'pass', 'Outline and references agree exactly'` on `outline_files == references_files`,
  and the docstring at :222-223 states the both-empty case is deliberate.
- OBSERVED: prune cause is assumed, not established — `evaluate_mis_prunes`:206
  (`absent = step not in bare_final`) with the hard-coded map at :69
  (`'sonar-roundtrip': 'no_code_delta'`) and the failure branch at :214-220, whose `detail` asserts
  "skipped as no_code_delta" for any absence whatsoever.
- OBSERVED (doc-contract-divergence): `evaluate_mis_prunes`'s docstring at :198-199 claims "When no
  footprint is available the checks SKIP (**no false positives**)" — it closes one false-positive
  source while the larger one, cause misattribution, stays open under a docstring asserting the
  opposite.
- HYPOTHESIS: the actual prune reason is recoverable from the execution manifest or the routing
  record rather than needing to be inferred — confirm/refute at `manage-execution-manifest`
  § the phase_6 step-composition record and `check-routing-decisions.py` § `_phase_6_steps`
  (verify-at-outline). If no recorded reason exists anywhere, D4 re-scopes to "return
  cause-unknown" only, and closing the gap properly becomes a follow-on against the manifest.
- Verify-first clause: before widening the regex in D1, confirm the canonical bullet grammar
  against the **solution-outline authority** (`manage-solution-outline` standards), not against
  this script's docstring or a sample of archived outlines — matching observed samples rather than
  the specified grammar is how the current pattern got it wrong.

## Expected Surface

- OBSERVED: `plan-retrospective/scripts/check-artifact-consistency.py`:65
  (`_AFFECTED_FILE_BULLET_RE`), :157-175 (`extract_affected_files_per_deliverable`), :178-215
  (`check_affected_files_recall`), :217-232 (`check_affected_files_exact_match`), :324-370 (wiring).
- OBSERVED: `plan-retrospective/scripts/check-routing-decisions.py`:69 (`_PRUNABLE_PREDICATES`),
  :193-223 (`evaluate_mis_prunes`), :270-289 (the summary counts).
- HYPOTHESIS: `manage-solution-outline/standards/**` — read-only grounding for the bullet grammar;
  edited only if the grammar itself is underspecified (verify-at-outline).
- OBSERVED: tests under `test/plan-marshall/plan-retrospective/**`.

Re-verify against HEAD at outline: PLAN-51 may restructure the fragment/section registry these
checkers feed.

## Dependencies and Sequencing

- Depends on: none, but **sequence after PLAN-51**.
- Overlaps with: **PLAN-51** — file-level disjoint (PLAN-51 owns `compile-report.py` and the
  section registry; this plan owns the two checker scripts) but same skill and same test module,
  and PLAN-51's D3 may restructure the registry these checkers emit fragments into. Do **not** run
  the two concurrently; treat as sequenced, not parallel.
- **Split rationale (recorded per the scope-bloat guard):** these two defects were NOT folded into
  PLAN-51. Folding would have taken PLAN-51 to seven deliverables, past the six-deliverable
  presumption, and the root causes are unrelated — PLAN-51 is a *registry-completeness plus
  success-signal* defect in report assembly, whereas this plan is an *extractor-grammar plus
  cause-attribution* defect in the checkers. Splitting along that boundary keeps each plan
  independently landable and analyzable.
- Adjacent to: PLAN-46 (title channel) and PLAN-53 (queue setter) touch unrelated surfaces.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-54-retrospective-checker-assertion-integrity.md"
```

## Notes

- **Archetype membership.** D1–D3 are the epic's flagship `confident-signal-hides-a-caveat` in its
  purest observed form yet — not a caveat suppressed alongside a real result, but a **pass with no
  underlying assertion at all**, produced by two independently-benign behaviours composing (a
  silent parse miss feeding a set-equality that treats ∅ == ∅ as agreement). It is simultaneously
  the third `vacuous-guard` exemplar, after PLAN-46's repaint contract and candidate (a)'s sweep
  list.
- **Polarity note.** D4 is this epic's first **false-positive** instance: nearly every other member
  is a false negative (something wrong reported as fine). A spurious `FAIL` is not merely the
  mirror image — it erodes trust in the checker and trains readers to ignore its output, which
  silently converts a working guard into a vacuous one. Worth carrying as its own sub-pattern.
- **Source note.** Both defects were found by a retrospective inspecting *its own* tooling while
  reviewing an unrelated plan. That is the lessons-pipeline working as intended, and contrasts with
  candidate (f) (the pipeline records but closes nothing) — here the records are being closed.

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/local/orchestrator/` — the orchestrator owns every ledger write — and
reports its outcome through its PR alone. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## Lessons Carried (bound 2026-07-25 · lessons-triage)

The plan lifecycle MUST carry the lessons below so each lives/moves with the plan and leaves the
global corpus when the fix lands: at phase-1-init run
`manage-lessons convert-to-plan --lesson-id {id} --plan-id {plan_marshall_plan_id}` per lesson; the
finalize `lessons-housekeeping` step then retires them (provenance to the tombstone `--reason`).

- `2026-07-22-22-001` — check-artifact-consistency affected-files regex cannot parse the canonical
  backtick-plus-intent bullet, voiding the coverage gate (D1/D2).
- `2026-07-22-22-002` — check-routing-decisions attributes every absent prunable step to its prune
  predicate, misreporting posture-cutoff drops (D4).
- `2026-07-17-11-001` — analyze-logs `dispatch_clustering` wildly overcounts re-entries (76 vs 7).
  **ADJACENT** retrospective-machinery residual (same skill, distinct script `analyze-logs.py`):
  fold as an added checker/reduction fix ONLY if the plan stays within the six-deliverable split
  guard; otherwise the D1 gate spins it to a sequenced follow-on and the carry+retire applies when
  that follow-on lands. Do not retire the lesson until its fix ships.
- `2026-07-22-12-002` — extract-chat-signal reduction keeps full skill bodies and empty user turns.
  **ADJACENT** residual (`extract-chat-signal.py`), same split-guard caveat as above.
