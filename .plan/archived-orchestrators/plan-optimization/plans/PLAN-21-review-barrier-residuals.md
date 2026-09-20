# PLAN-21: review-barrier-residuals

epic: plan-optimization
workstream: WS-10

> Staged plan spec. The direct residual of PLAN-10 #936 (review-barrier-noise-filter) plus a second
> barrier defect that recurred alongside it. Both fired again at PLAN-17 #948, which SATISFIED the
> "plan-worthy on recurrence" trigger recorded against 13-21-001. Re-ground call sites at outline.

## Objective

Stop the finalize review barrier from manufacturing work that isn't there: bot rate-limit notices filed
as actionable findings, and a completeness guard that loops back on findings pending for a triage step
that has not run yet. Both force manual intervention on nearly every run — the operator has had to
hand-suppress notices and hand-prune a sunset bot from `enabled_bots` per-plan.

## Deliverables

### D1 — bot-agnostic rate-limit classifier

**Lesson `2026-07-13-21-001`, STILL OPEN, recurred at PLAN-17 #948.** PLAN-10 #936 dropped the
**CodeRabbit-specific** rate-limit notice only; a **Sourcery** weekly-rate-limit notice was filed as an
actionable finding again at #948 and had to be **suppressed by hand**. The per-bot allowlist approach
does not generalize. **Fix:** a bot-agnostic rate-limit / service-notice classifier in the noise
pre-filter, so a new or renamed bot's rate-limit notice is dropped without a code change naming that bot.
**Acceptance:** rate-limit notices from CodeRabbit, Sourcery, and an arbitrary unknown bot are all
classified as noise and never stored as findings; a genuine finding from those same bots is unaffected
(the false-negative risk is the real hazard here — test both directions). Regression test per bot shape.

### D2 — completeness guard must not loop back on not-yet-triaged findings

**Lesson `2026-07-18-05-001`, recurred at PLAN-17 #948.** automatic-review's D3 completeness guard fires
`loop_back` on findings that are pending precisely because the **unified triage has not run yet** — an
ordering defect, not a real incompleteness. It manufactures a loop-back that the operator then has to
break manually. **Note the shipped context:** PLAN-10 #936 and the unified-finalize-triage work (#920)
established the per-signal FIND gating and the single dispatcher-owned triage; this is the guard's
ordering relative to that triage. **Fix:** make the completeness assertion aware of triage state — a
finding awaiting a triage step that has not yet executed is not an incompleteness. **Acceptance:** a run
with findings pending pre-triage does NOT loop back; a run with genuinely untriaged-and-triage-already-ran
findings still DOES. Regression test both.

### D3 — retire the sunset gemini reviewer project-wide

Gemini was sunset 2026-07-17, but it is still in `enabled_bots` defaults, so **every plan has to prune it
by hand** (done again at PLAN-09 #935 and PLAN-17 #948) — and the stale entry participates in D2's
loop-back. **Fix:** remove gemini from the shipped `enabled_bots` default configuration and reconcile the
docs that reference it. **Important caveat (learned, do NOT lose):** a pruned/sunset bot can still post a
VALID finding — this deliverable removes it from the *default enabled set*, it does NOT add logic that
ignores comments already posted by it. **Acceptance:** a fresh plan requires no manual gemini prune;
existing gemini-authored comments are still ingested normally.

## Out of scope / do NOT expand
- Re-doing PLAN-10 #936's CodeRabbit-specific filter or the pipeline-authored-trigger drop — D1 GENERALIZES
  that work, it does not replace it.
- The unified triage's own behavior (#920) — D2 fixes the guard's ORDERING against triage, not triage.
- Leaf verification (PLAN-20) and lock staleness (PLAN-22) — sibling plans, disjoint surfaces.

## Absorbs
- Open Defect "bot-agnostic rate-limit filtering" (PLAN-10 #936 residual, lesson `2026-07-13-21-001`) → D1.
- Lesson `2026-07-18-05-001` (completeness guard vs not-yet-run unified triage) → D2.
- The standing "prune sunset gemini from `enabled_bots`" memory note → D3.

## Expected Surface
- `github_pr.py` / `github_re_review.py` noise pre-filter (D1)
- automatic-review step + `_ci_barrier.py` completeness/FIND gating (D2)
- `enabled_bots` default configuration + referencing docs (D3)
- tests: per-bot and unknown-bot rate-limit classification (both directions); pre-triage-no-loopback vs
  post-triage-loopback; default-config has no gemini while gemini-authored comments still ingest

## Dependencies and Sequencing
- Depends on: none. PLAN-10 #936 and #920 are shipped preconditions to build on.
- Surface-disjoint from PLAN-20 and PLAN-22 (startable in parallel) and from in-flight PLAN-18.
- **Self-validating:** this plan's own finalize run exercises D1/D2/D3 directly — if it needs no manual
  suppression or prune, that IS the acceptance evidence. Note the observation in the landing.

## Size / split guard
3 deliverables — under the ~6 presumption. D3 is small and tightly coupled to D2 (the stale entry feeds
the loop-back), so it is deliberately not split out.

## Hand-Off Command
```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-21-review-barrier-residuals.md"
```

## Status Trail
- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-21.md is recorded}
