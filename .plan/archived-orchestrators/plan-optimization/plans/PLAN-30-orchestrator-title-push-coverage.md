# PLAN-30: Orchestrator Terminal-Title Push Coverage

epic: plan-optimization
workstream: WS-10

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-30-orchestrator-title-push-coverage.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never
> launches the plan inline.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

The `Orchestrator-{SlugName}` terminal title is fully built end-to-end — `manage-terminal-title`
composes the body for `kind: orchestrator` + `slug` (`manage_terminal_title.py:121`), and
`platform-runtime` carries the `session push-title-token --store orchestrator --slug {slug}` seam
in BOTH runtimes (`_claude_runtime_impl.py:432`, `opencode_runtime.py:204`). What is missing is
call-site coverage: only 4 of 8 `marshall-orchestrator` verbs invoke the seam (`init` twice,
`resume`, `close`, `archive`), while **`status`, `next`, `analyze`, `decompose`, and `lessons`
never push**. The governing prose in `init.md:16` / `resume.md:15` — "Session-opening verbs surface
the epic in the terminal title" — is the root cause: it presumes a session begins with `init` or
`resume`, but a session opens with whatever verb the operator types, and the uncovered set is
exactly the daily-driver set. Observed 2026-07-21: a session opened with `status slug=plan-optimization`
produced no title push at all. This plan closes the coverage gap and corrects the mis-cut rule.

## Deliverables

1. **Push the title from every epic-resolving verb.** Add the `session push-title-token
   --store orchestrator --slug {slug}` invocation to `workflow/orchestrate.md` (covering both
   `status` and `next`), `workflow/analyze.md`, `workflow/decompose.md`, and
   `workflow/lessons-handling.md`, matching the existing best-effort / silent-no-op framing used
   in `resume.md`. Placement is at verb entry, after the slug is resolved.
2. **Correct the governing rule text.** Replace the "session-opening verbs" categorization in
   `init.md` and `resume.md` with the accurate rule — *every verb that resolves an epic repaints
   the title, because any verb may open a session* — so the next verb added to the router inherits
   the obligation instead of re-deriving it. State the rule ONCE in the skill (or the persona
   standard) and have the per-verb docs reference it rather than restating it.
3. **Preserve the existing restore semantics.** `close` and `archive` already push a restore after
   the epic leaves scope; verify this plan does not disturb that, and that the terminal verbs'
   restore still wins over any new entry push.

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/workflow/orchestrate.md`
- `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/workflow/analyze.md`
- `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/workflow/decompose.md`
- `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/workflow/lessons-handling.md`
- `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/workflow/init.md` (rule text)
- `marketplace/bundles/plan-marshall/skills/marshall-orchestrator/workflow/resume.md` (rule text)
- possibly `marketplace/bundles/plan-marshall/skills/persona-marshall-orchestrator/standards/orchestration-model.md`
  (if the rule is stated centrally)

Documentation-only surface — no script changes expected. Docs-only footprint means the CI
footprint gate (`skip-on-docs-only`) applies.

## Dependencies and Sequencing

- Depends on: none for IMPLEMENTATION.
- **Verification dependency on PLAN-26 (live).** PLAN-26's verified root cause is that the title's
  `/dev/tty` write silently no-ops off the controlling terminal, whereas the footer rides the
  continuously-polled `statusLine`. Until PLAN-26 lands, a correct PLAN-30 fix is **unobservable
  end-to-end** — the added push calls will fire and render nothing. Do NOT treat a blank title
  during verification as a PLAN-30 defect; verify PLAN-30 by asserting the invocation is present
  and well-formed in each verb doc (and that the seam is reached), not by eyeballing the terminal
  tab. Full visual confirmation is deferred until PLAN-26 ships.
- Overlaps with: **none on files.** PLAN-26 owns `platform-runtime` title / `_status_core` /
  session-binding; PLAN-30 owns `marshall-orchestrator` workflow markdown. Surface-disjoint →
  the two MAY run concurrently. The coupling is semantic (shared symptom), not textual.
- Related: PLAN-31 also edits `marshall-orchestrator/workflow/analyze.md` and `decompose.md`.
  PLAN-30 and PLAN-31 are therefore **ADJACENT** — sequence them (PLAN-30 first, it is the smaller
  mechanical change) or accept a rebase on those two files.

## Hand-Off Command

```text
/plan-marshall The Orchestrator-{SlugName} terminal title is built end-to-end (manage-terminal-title composes the kind=orchestrator body; platform-runtime carries the `session push-title-token --store orchestrator --slug {slug}` seam in both runtimes) but only 4 of 8 marshall-orchestrator verbs actually invoke it: init, resume, close, archive. The verbs an operator lives in daily — status, next, analyze, decompose, lessons — never push, so opening a session with `status` leaves the title unset. Root cause is the governing prose in init.md:16 and resume.md:15, "Session-opening verbs surface the epic in the terminal title", which wrongly presumes sessions begin with init or resume. Add the push-title-token invocation (best-effort, silent no-op when the surface is unconfigured, matching resume.md's framing) at verb entry after slug resolution in workflow/orchestrate.md (covers status and next), workflow/analyze.md, workflow/decompose.md, and workflow/lessons-handling.md. Correct the rule text in init.md and resume.md to state that EVERY epic-resolving verb repaints the title because any verb may open a session, stating that rule once and referencing it from the per-verb docs rather than restating it. Preserve the existing close/archive restore-push semantics. This is a documentation-only change to marketplace/bundles/plan-marshall/skills/marshall-orchestrator. IMPORTANT verification note: PLAN-26 (currently in flight) is fixing a verified defect where the title's /dev/tty write silently no-ops off the controlling terminal, so until PLAN-26 lands these added pushes will fire but render nothing — verify by asserting the invocation is present and well-formed in each verb doc, NOT by looking at the terminal tab, and do not treat a blank title as a defect of this plan.
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when the landing analysis is recorded at landings/PLAN-30.md}
