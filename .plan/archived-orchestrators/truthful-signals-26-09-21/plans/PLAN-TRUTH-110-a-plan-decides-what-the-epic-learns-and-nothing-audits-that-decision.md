# PLAN-TRUTH-110: A plan decides what the epic learns, and nothing audits that decision

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance, and a RETRACTION this spec is built on

Staged 2026-08-24 on operator direction: *"My problem is less the bugs itself but the visibility /
auditability / verification."*

⛔⛔ **THE FIRST VERSION OF THIS SPEC WAS BUILT ON A FALSE MEASUREMENT BY THIS ORCHESTRATOR. READ THIS
BEFORE ANYTHING ELSE.**

It claimed *"`PLAN-TRUTH-095` archived with 29 findings pending — filed, never resolved, archived
anyway"*, and proposed a gate to stop it. **That is false.** On the operator's challenge (*"I thought
we have invariants preventing this?"*) the population was finally broken down by type:

| Type | Total | Pending |
|---|---:|---:|
| `assessments` | 29 | **29** |
| `qgate-6-finalize` | 19 | **0** |
| `test-failure` | 44 | **0** |
| `qgate-3-outline` | 3 | **0** |
| `build-error` / `pr-comment` / `qgate-5-execute` | 1 / 1 / 1 | **0** |

⭐ **All 29 "pending" were `assessments`, and an assessment is NOT a defect record.** Its schema carries
no `resolution` field at all — `{hash_id, file_path, certainty, confidence, agent, detail, evidence}` —
it is a scope judgement from `phase-3-outline` with its own `manage-findings assessment` subcommand.
The orchestrator's sweep defaulted a missing `resolution` to `pending` and counted them as unresolved
defects.

⇒ **`PLAN-TRUTH-095` archived with ZERO unresolved defects. The invariant works.** The same error
inflated the live figure from **7 pending to 26**; corrected, the live set is 183 findings / **7**
pending, all in plans still running, where pending is the normal in-flight state.

⛔ **CONSEQUENCES FOR THIS PLAN, BINDING:**
1. **The "no gate" gap is RETRACTED.** There is no demonstrated failure to prevent, and the archive
   gate that was D1 **has been removed**. ⛔ **Do not re-propose it without evidence this spec does not
   contain.**
2. **The remaining two gaps stand on their own evidence** and neither depended on the false figure.
3. ⭐ **The episode is itself the argument for D3 (the audit):** the orchestrator could not tell a
   healthy plan from a leaking one without hand-reading raw JSONL, and got it wrong when it tried.
   **A count over a population nobody inspected is exactly what an audit exists to prevent — and this
   spec's own first draft is the worked example.**

## Objective

**A plan files findings into a ledger nobody else reads, and emits a curated subset it chooses. Nothing
reconciles the two.**

Measured on `PLAN-TRUTH-095` (merged `b95d78437`, archived 2026-08-24):

| | Count |
|---|---|
| Findings in the plan's own ledger at archive | **98** (69 defect-bearing, 29 assessments) |
| Messages emitted to the epic | **13** — 12 candidate-lessons + 1 landing |
| **Findings transported to the epic** | **0** — the ledger is never emitted |

⇒ **The plan decides what the epic learns**, and the selection is invisible: a candidate-lesson is
authored, not derived from a finding, so nothing connects the 98 to the 13.

**Two gaps, and they are separate:**

**1. NO TRANSPORT.** The findings ledger is never emitted in any form. What the epic receives is what
the plan chose to write about.

**2. NO AUDIT.** Nothing reconciles *filed* against *transported*. ⚠ **And nothing distinguishes a
record type that HAS resolution semantics from one that does not** — which is precisely how this
spec's first draft went wrong.

⛔ **What is NOT a gap, verified:** the pre-merge barrier is a **review-completeness** barrier over
`pr-comment` findings, and the defect-bearing types resolved to zero before archive without it. **The
gating story is healthy. Do not report it otherwise.**

## Deliverables

Four deliverables. D0 is a gate.

**D0 — GATE: derive the population, WITH its type taxonomy.** For a sample of archived plans compute
per plan: findings by type, **which types carry resolution semantics and which do not**, resolution
distribution over the ones that do, messages emitted, and the traceability between them.

⛔⛔ **THE TYPE TAXONOMY IS NOT OPTIONAL AND IS NOT A DETAIL.** Conflating `assessments` with
defect-bearing types is the exact error that produced this spec's retracted first draft. **Publish the
taxonomy before any count, and state for each type whether an absent `resolution` means unresolved or
means the field does not apply.**

⚠ Publish the denominator. The archived stores are git-ignored, so **name which plans were reachable
and which were not** — an unreachable archive is not a zero.

**D1 — the findings ledger is transported, not curated away.** The epic must receive the plan's
findings, or a machine-readable summary, alongside the landing. ⛔ **This does NOT mean 98 inbox
messages.** Options to price at D0: a `findings` block in the landing payload
(`landing-payload-spec.md` already defines a required-key contract), a persisted artifact the epic
reads, or a summary carrying counts by type and resolution. ⭐ **Minimum bar: the epic can see what a
plan found without reading the plan's raw store** — which is the capability whose absence produced the
retraction above.

**D2 — the orchestrator can see a live plan's findings.** ⇒ Owned by **`PLAN-TRUTH-109`**. ⛔ **Do not
implement it here**; this deliverable records the dependency, because without it D1's transport is the
only channel and mid-run visibility stays impossible.

**D3 — the audit: reconcile filed against transported, after the fact.** A retrospective-tier check
over an archived plan: how many findings by type, how many transported, and what a reader can and
cannot conclude from the difference. ⭐ **This is the deliverable that makes D1 verifiable**, and the
one this spec's own history most argues for. ⚠ It belongs in the retrospective / audit tier — it must
run on plans that have already archived.

⛔ **The audit REPORTS; it does not gate.** The gating question was retracted above and must not
re-enter through this deliverable.

**D4 — tests, with the control that would have caught the retracted error.** Assert the reconciliation
over a plan whose defect types are all resolved reports **healthy**, and that a fixture mixing
`assessments` with defect-bearing types **does not count the assessments as unresolved**. ⛔ **That
second case is the load-bearing one** — it is the exact false positive this orchestrator produced by
hand, and a check that reproduces it is worse than no check.

## Expected Surface

Provisional — D0 will move it.

- `marketplace/bundles/plan-marshall/skills/manage-findings/**`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md`
- `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md`
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/**`
- `.claude/skills/audit-archived-plan-retrospectives/**`
- `test/plan-marshall/**`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — Step 3 item 4b.a0,
  the once-per-run orchestration resolve and its four forward sites — added 2026-09-05 by the `-126`
  drain fold of message `-005` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/**` — the composed
  manifest as the second, already-persisted orchestration signal (verify-at-outline)

## Dependencies and Sequencing

⛔ **Re-derive with `corpus cross-check` at emit time.**

- ⛔ **`PLAN-TRUTH-109` — hard, for D2.** It fixes the read path; this plan fixes transport and audit.
- ⛔⛔ **`PLAN-TRUTH-106` — SERIALIZE, `-106` first.** It rewrites `emit-landing.md` and
  `landing-payload-spec.md` under the *one payload, two renderings* invariant, and **D1 adds to the same
  payload.** Adding a findings block to a payload `-106` is restructuring would produce two answers.
- ⚠ **`PLAN-TRUTH-100`** owns the mid-run channel; its plan→orchestrator direction reduces D1's
  urgency. Complementary.
- **Depends on:** `-109` (D2), `-106` (D1).

## Claim Labels

- OBSERVED: `PLAN-TRUTH-095` archived with 98 findings — **29 `assessments` and 69 defect-bearing**, the latter at **zero pending** — read at its archived `artifacts/findings/*.jsonl`, broken down by type.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: No .plan/local/archive dir at HEAD; -095 archived findings store unreachable to re-derive the 98/29/69 breakdown
- OBSERVED: an `assessments` record carries `{hash_id, file_path, certainty, confidence, agent, detail, evidence}` and **no `resolution` field** — read first-party; it is a `phase-3-outline` scope judgement, not a defect.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: _findings_core.py:1398-1412 add_assessment record is hash_id/timestamp/file_path/certainty/confidence/agent/detail/evidence -- no resolution field
- OBSERVED: it emitted 13 messages (12 candidate-lessons + 1 landing) and **none transports findings** — read at `inbox/archive/finalize-step-contract-guard-residue/`.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: inbox/archive/finalize-step-contract-guard-residue/ holds exactly 13 files: 12 candidate-lesson plus 1 landing; no kind carries a findings block
- OBSERVED: the four live plans hold 183 findings with **7** pending once assessments are excluded, all in plans still running.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: .plan/local/plans/ now holds only NO_PLAN and one unrelated plan; the four-live-plan population has fully turned over
- OBSERVED: the pre-merge barrier is a review-completeness barrier over `pr-comment` findings — read at `branch-cleanup.md`; the defect-bearing types nonetheless resolved to zero before archive.
  - verdict: corroborated | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: review_completeness.py proves PARTICIPATION only over pr-comment findings via query_findings(finding_type=pr-comment); no defect-type gating exists
- HYPOTHESIS: zero-pending-at-archive is the norm rather than particular to `-095` — confirm/refute at D0 over a sample (verify-at-outline). ⛔ **One plan is not a population — the lesson this spec was built by violating.**
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Explicitly deferred to D0 over a sample; D0 has not run (no matching plan directory exists)
- HYPOTHESIS: a candidate-lesson is authored rather than derived from a finding, so no traceability exists today — confirm/refute at D0 by matching `-095`'s 12 candidate-lessons against its 98 findings (verify-at-outline).
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Explicitly deferred to D0 matching pass; D0 has not run
- Verify-first clause: D0 must publish the resolution-semantics taxonomy per type **before** any count derived from it. A count over a population whose record types were not inspected is the error that produced this spec's retracted first draft.
  - verdict: unverifiable | checked_at: 66320e70d | by: truthful-signals/cleanup | rescoped: n/a | evidence: Forward verify-first clause on D0 own future publication; not yet executed

## ⭐ FOLDED 2026-08-31 — inbox drain (2 message(s))

- **`disjointness-gate-reads-declared-surface-wrong-006.md`** — The finalize dispatcher did not forward orchestrated/epic to plan-retrospective
- **`findings-read-absent-plan-dir-returns-clean-zero-003.md`** — A recall-only coverage check scores an under-declared set 100% by construction, and defers the precision half to an aspect that never looks

⛔ Each is the sending plan's own first-party observation, relayed verbatim by title. **Treat every one as a LEAD** — the drain did not re-derive them, and several were observed against tree states that have since moved. Re-ground at outline.

## ⭐ FOLDED 2026-09-04 — inbox drain (1 message(s))

- **`documented-invocations-...-010`** — *`script-failure-analysis` emits a `lessons[]` block that no downstream aspect consumes.* The aspect computed and published an **11-entry `lessons[]` array** (each with `component`, `category`, `title`, `subtype`, `occurrence_count`) over `total_failures: 16` / `unique_failures: 11`. `lessons_proposal` synthesized **8 proposals**, and their `source_aspects` name seven other aspects — **`script-failure-analysis` appears in NONE of them. Zero of the 11 computed candidates reached the epic inbox.**

  ⛔⛔ **This is exactly this spec’s subject: a plan decides what the epic learns, and nothing audits that decision.** The drop is invisible from both ends — the producer reports success, the consumer never names it.

  ⛔ **It compounds with a rendering failure at the one surface that would show it:** every finding of the aspect was emitted at `[INFO]`, so the report’s headline band shows **eleven bare `- [INFO]` bullets with empty message text** — *“the section renders as visually empty while carrying the run’s entire script-failure signal.”*

  ⭐ **And the trigger fired on it.** The dispatcher’s Signal Gate treats `signal_script_failure_clusters_count` as one of three independent lesson-bearing triggers; in this run it was **9 — the largest of the three by distinct-notation count.** *“A trigger that fires the step and then contributes nothing to the step’s output is a signal that reports work it did not cause.”* **The ask: wire it into `lessons_proposal` as a source population, or stop computing it — and if the drop is deliberate, carry an explicit `routed: false` discriminator so a reader can tell “computed and routed” from “computed and dropped.”**

## ⭐⭐ FOLDED 2026-09-05 — PLAN-TRUTH-126 drain (1 message)

- **`shipped-guards-...-005`** — *the finalize dispatcher forwarded `orchestrated: false` for an
  orchestrated plan, and the compose gate that disagreed was never cross-read.*

  **Observed first-party by the plan, in its own finalize.** `phase-6-finalize` Step 3 item 4b.a0
  requires the dispatcher to resolve the orchestration verdict ONCE per run and forward it to every
  lesson-emitting write-site, each of which is explicitly forbidden from re-deriving it. The verdict
  `orchestrated: false` / `epic: ""` **survived a context compaction** and reached `lessons-capture`,
  which took Branch A (allocate into the GLOBAL corpus) where the contract required Branch B4 (epic
  inbox, zero `manage-lessons add`). The sanctioned resolution returns `orchestrated: true`.

  ⭐⭐⭐ **THE RESIDUE IS THE PART THIS SPEC OWNS, AND IT IS SHARPER THAN THE INCIDENT.**
  `emit-landing`'s presence in the composed manifest was **already persisted, independent evidence that
  the plan is orchestrated** — a second signal, disagreeing with the forwarded one, sitting in the same
  run's own state. ⛔ **No runtime consumer cross-reads it.** *"Resolve once and forward"* is the right
  contract for cost and the wrong one for integrity when the single carrier can be corrupted in transit:
  a forwarded scalar has no witness, while a cross-read against an independently-persisted signal does.

  ⚠ **The recovery was exemplary and must not be read as making the defect minor**: the run caught it
  after the fact, re-emitted the two candidates as inbox `-003`/`-004` carrying dedup notes that NAME
  their global twins, and **left the globals in place rather than destroying them** — correct, given the
  `manage-lessons remove` destroy-while-reporting-`not_found` defect. ⛔ **A defect caught by the agent
  that committed it is still a defect with no detector**; nothing in the machinery would have found it.

---

## Superseded By

⛔ **This spec is SUPERSEDED by `PLAN-TRUTH-149-the-landing-payload-and-what-the-epic-learns-from-it.md` (PLAN-TRUTH-149)**, recorded 2026-09-12 under the operator directive to group plans by shared target at a ceiling of 12 deliverables. It is retained in full as the audit record of why it was retired and as the authority its successor's `## Claim Labels` section POINTS at — the successor deliberately does not restate these claims, so **this document is where they are re-derived from**. Do not implement from this spec; implement from its successor.
