envelope_version=1
sender_type=plan
sender_id=build-tests-do-not-neutralize-daemon-routing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T17:45:07Z

component=plan-marshall:phase-6-finalize
category=bug

# The architecture-refresh roster contradiction produces a live dispatch-audit violation

**This supplies the observable that candidate-lesson cl-006 (filed by lessons-capture this same run) was missing.** cl-006 reported the contradiction as a documentation defect found in passing. This retrospective's dispatch audit shows it produced an actual hard-rule violation in this very run — it is a defect with a consequence, not a tidiness issue.

The execution-context dispatch audit cross-references the dispatched-step roster against the terminal outcomes in `status.metadata.phase_steps`. Result for this plan:

| | |
|---|---|
| Dispatched-roster steps present in the manifest | 10 |
| Carrying `[DISPATCH]` evidence in `work.log` | 9 |
| `dispatch_coverage_violation` | **1 — `architecture-refresh`** |

`architecture-refresh` reached `outcome: done` with `display_detail: "descriptor clean after discover, 0 modules affected"` and **zero** `[DISPATCH]` emissions. Per the audit's own contract that is `severity: error` — there is no warning tier, because the underlying rule is a hard rule.

The session transcript shows this was **knowing and reasoned**, not a slip:

> Note: `architecture-refresh.md` says **inline** (Tier-1 `prompt` needs `AskUserQuestion`), but `dispatch-inline-split.md` rosters it as **dispatched**. Running inline — a leaf can't fire the prompt. Flagging the contradiction.

That settles which document is wrong. A dispatched leaf **structurally cannot** fire `AskUserQuestion`; the roster's own rationale for classifying the step dispatched is its Tier-1 per-module fan-out, but that same Tier 1 is the part that needs the operator prompt. The roster asks for something the runtime forbids.

The benign reading — "0 modules affected, so Tier 1 never fanned out, so no dispatch was needed" — does not rescue the signal. The roster obligation is unconditional; the audit cannot know Tier 1 was a no-op; and a future run *with* affected modules would need exactly the dispatch the inline path cannot perform. The step reported a confident green from a path whose classification is contested.

Note also that `dispatch-inline-split.md` opens by declaring itself "the single source of truth" and pins a closure invariant with a regression test (`test_dispatch_roster_closure.py`). The invariant checks that every registry step appears in exactly one roster — it does **not** check that a step's roster classification agrees with the step's own document. The guard is real but blind to this failure mode.

## Solution

- **Reconcile the two documents, treating `architecture-refresh.md` as authoritative** on the ground that the `AskUserQuestion` constraint is a runtime fact, not a preference.
- **Prefer splitting the step** over re-labelling it: an inline Tier-0 (discover + diff, deterministic) and a separately-rostered Tier-1 re-enrichment that either runs inline in the orchestrator (so it can prompt) or returns a prompt-required envelope. The hybrid classification is what made a single roster row wrong in the first place.
- **Extend the closure invariant to a consistency invariant.** The regression currently asserts roster membership; extend it to assert that each step's own SKILL/workflow doc does not self-declare a classification contradicting its roster row. This failure was caught by a human reading two documents — that is exactly the check a test should own.

## Evidence

- aspect: `execution-context-dispatch-audit` — `counts.dispatch_coverage_violation: 1`; `roster_crosscheck` row `architecture-refresh,dispatched,done,none,VIOLATION`
- aspect: `chat-history-analysis` — the surviving assistant turn flagging the contradiction at decision time
- `dispatch-inline-split.md` § "Dispatched steps" — `default:architecture-refresh` — "hybrid, classified dispatched … The dispatching tier governs the classification, so the step carries exactly one roster row."
- `work.log` — 15 `[DISPATCH]` lines, none for `architecture-refresh`
- cross-reference: candidate-lesson cl-006 from this plan's lessons-capture pass (same defect, documentation half)
