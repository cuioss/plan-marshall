# Landing Analysis: PLAN-56 — Orchestrator Inbox Pickup

epic: truthful-signals
workstream: WS-01
pr: 1027

> Merged as `a1a9176ee`. **The live regression is closed:** #1016 shipped the inbox producer with no
> consumer; every orchestrated plan was writing into a queue nothing drained.

## What shipped

3/3 — `inbox list` + `inbox archive` deterministic verbs, a fourth **inbox-scan** input mode on
`analyze` (per-kind routing, archive-on-consume), and `test_inbox_drain_contract.py` pinning the drain.

⭐ **Dogfooded immediately:** this analysis drained the 13 accumulated messages with the verbs the plan
shipped, on its first use. `inbox list` reported `count: 13, invalid_count: 0` — the envelope validator
accepted every message written by three different plans across two days.

## What the review layers caught — 18 real defects

| Layer | Found | Notable |
|---|---|---|
| Self-review (6 rounds) | 5 | 2 vacuous guards |
| **CodeRabbit** (4 rounds) | **13** | TOCTOU race, archived-fallback on a mutation, a third vacuous guard |
| **PR-Agent** | **0** | *"no major issues"* on code containing **2 Major defects** |
| **Sourcery** | **0** | never reviewed — weekly diff-cap exhausted throughout |

**Three findings that are load-bearing for the epic:**

1. ⛔ **The TOCTOU race falsified a property the plan advertised.** `cmd_inbox_archive`'s docstring and
   D5 both promised *"idempotent on repeat"* and *"safe to resume"*. **Six self-review rounds validated
   the prose; only an external reviewer tested the interleaving.** The sharpest instance of the epic's
   theme this run produced — a confident correctness claim that no in-house gate could falsify because
   none of them execute the interleaving. → **PLAN-81**.
2. ⛔ **A fix is the highest-risk moment in the pipeline.** **Five defects were introduced by the fix
   for a prior defect**, two of them re-introducing the vacuous-guard archetype *through its own
   remedy*. What broke the chain — twice — was an explicit adversarial re-read of the fix's own diff,
   which happened **only because the executor asked for it in the dispatch prompt. Nothing requires
   it.** Lesson `2026-07-28-08-001`. → **PLAN-81**.
3. ⛔ **A vacuous guard was cleared *as* vacuous.** Self-review examined `_section()`, reasoned
   correctly about the `####` nesting case, and never checked the `##` boundary. CodeRabbit found it
   four rounds later. **Examining a candidate and clearing it is not the same as covering it** — and
   the self-review reported CLEAN either way. → **PLAN-81** (n=4 for the CLEAN-over-real-defects shape).

## A post-merge finding — real defect, OPERATOR-TRIGGERED review

A **Sequence Number Reuse** defect was raised against this PR after merge: `next_sequence` scans only
`inbox/`, so once `cmd_inbox_archive` moves messages to `inbox/archive/`, allocation restarts at `001`
and collides irrecoverably with the archived copy at link time. **Verified first-party against `main`**
(`_orchestrator_inbox.py:250-265`) — the defect is real regardless of provenance, and the proposed fix
(scan both directories) is correct. Staged as **PLAN-93**.

⛔ **Orchestrator correction.** This was first recorded here as evidence that *"a review artifact can
change after the merge"*, with a new post-merge-sweep requirement inferred for PLAN-92 D6. **The
operator corrected it: they explicitly started that review to test Gemini.** The update was **induced,
not spontaneous** — so the general claim is withdrawn and the sweep requirement removed from PLAN-92.
**The finding stands; the inference around it did not.** Recorded as an over-generalization instance.

⚠ **Attribution unresolved:** the comment carries PR-Agent's Guide format, but the operator triggered
the review to test **Gemini**, which #1014 retired from the registry. **The "PR-Agent: 0" row below is
therefore still accurate for the finalize-time review**, and this later finding must not be credited to
PR-Agent until D1 establishes authorship.

## PR-Agent's participation record — the measured data point for decision 6

PR-Agent posted its Guide — *participation* — and reported **"no major issues" on a diff containing two
Major defects that CodeRabbit found.** Under PLAN-92 decision 6, PR-Agent is a **required** bot, and
under D6 the Guide is *positive participation evidence*. **Both are satisfied here while its review
contributed nothing.** ⚠ **This does not refute the classification** — a required bot's job is to be
present and answerable, and a zero-findings review is a legitimate verdict (D3(b)
`participated-but-empty`). **But it sets the ceiling on what the quorum can promise:** quorum proves
*participation*, never *quality*. PLAN-92 must not let a satisfied quorum read as a reviewed diff —
that would be the flagship archetype rebuilt inside the fix for it. **Recorded against PLAN-92 D6.**

Sourcery's zero has the opposite cause — a **hard weekly quota**, exhausted throughout — confirming
PLAN-92 D2's awaitable-window-vs-quota split with a live instance: no sleep could have recovered it.

## Reconciliation

- [x] `status` → shipped; `pr` = 1027; `landing` = landings/PLAN-56.md
- [x] The **hand-drain obligation is retired** — the drain verb exists and was used here
- [x] Inbox drained (13 messages) and archived via the shipped verb
- [ ] `plan_marshall_plan_id` — not reported; left empty rather than guessed

## Two items the plan left open rather than silently closing — both correct calls

- **The final commit `a50fb8cc0` was never bot-reviewed** (the operator closed the loop). ⚠ This is
  the same gap PLAN-92 owns: a merged commit carrying no fresh review. Recorded as a **live instance**,
  not a new defect.
- **CodeRabbit's round-4 review body carried a fifth vacuous guard** — an over-reaching
  paragraph-capture regex — triaged as Trivial and deferred. Left open deliberately; if it recurs it is
  a real instance rather than a nitpick.
