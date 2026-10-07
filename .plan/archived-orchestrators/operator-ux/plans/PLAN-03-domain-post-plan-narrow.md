# PLAN-03: Re-resolve and narrow the domain set once the plan is known

epic: operator-ux
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-03-domain-post-plan-narrow.md` and is queued in the epic `status.json`
> `plans[]` field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Over-provisioning at init (PLAN-01) is the right posture when nothing is known yet, but it is
a starting point rather than an answer. Once the plan has been outlined and its deliverables
carry real file lists, the system knows which domains it actually needs — that is precisely
the operator's point that "then the system should know which one to select". Add a
re-resolution pass at that point which can **narrow** the set, not only widen it. Today's
re-merge in `phase-2-refine` is union-only by construction, so no code path in the lifecycle
can currently remove a domain that early over-provisioning added. This plan closes the loop
that makes over-provisioning safe to be generous with.

**Observed cost, 2026-09-02 (this plan's motivating evidence, not a hypothetical).** A live
plan resolved `reason=over_provisioned_resolve` with zero narrative matches and was given
EVERY offerable domain, including `javascript`, which it does not touch. The executing agent
recorded in its own report that the set was wrong and named the exact remedy — "narrowing
references.json domains to java,java-cui,documentation is a one-call fix" — then persisted the
wrong set anyway, because the workflow treats a non-ambiguous resolve as final and gives it no
correction path. The judgement existed; the mechanism to act on it did not. That mechanism is
this plan.

## Deliverables

1. A narrowing re-resolution invoked once the deliverables' file set is known (the natural
   site is the end of `phase-3-outline`, where the declared footprint first exists; the exact
   site is settled at outline per the claim below).
   ⛔ **The site question now has a second candidate and outline must decide between them, not
   assume the first.** The 2026-09-02 evidence shows the executing agent often knows the set is
   wrong AT INIT, before any outline exists. Two shapes are therefore in scope: (i) narrow at
   the end of outline from the derived footprint (mechanical, trustworthy, late), and (ii)
   allow the agent to narrow at init when it has explicit grounds (early, cheap, judgement-
   based). They are not exclusive — (i) is the safety net, (ii) is the fast path — but adopting
   BOTH raises this spec's deliverable count and triggers the scope-bloat split guard. Decide
   at outline and record the verdict; splitting into two plans is the recorded default if both
   are adopted.
2. A narrowing rule expressed as a **safety-bounded** operation: a domain may be dropped only
   when no already-resolved task depends on it and its glob/always_on legs do not claim it.
   `always_on` is never narrowed away — the operator asked for it unconditionally.
3. A recorded provenance on the resulting `references.domains` write, so a reader can tell an
   over-provisioned set from a narrowed one, and a narrowed set names what it dropped and why.
4. The system reports the narrowing to the user in one line rather than silently — a domain
   set changing under a plan is exactly the kind of thing that must be visible, and it is
   cheap to state.
5. Tests covering: over-provisioned set narrows on a single-language footprint; a domain
   claimed by `always_on` survives narrowing; a domain a resolved task depends on survives;
   an empty or unreadable footprint narrows nothing (fail-open, never to an empty set).

## Claim Labels

- OBSERVED: A re-resolution point already exists and passes the real affected files — read at
  `marketplace/bundles/plan-marshall/skills/phase-2-refine/SKILL.md` § "Domain Re-merge
  (file_globs against real `affected_files`)". It is explicitly a *re-merge*, and
  `domain-detect` composes a union, so it can only add.
  - verdict: corroborated | checked_at: 9fd0957 | by: operator-ux/cleanup | rescoped: n/a | evidence: phase-2-refine/SKILL.md L196 still declares the re-merge; L212 states 'The union is monotonic (widen-only)' verbatim, so no narrowing path exists
- OBSERVED: `domain-detect` accepts `--affected-files` as the file signal for the glob leg and
  is a read verb that writes nothing — read at
  `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md` § `domain-detect`.
  A narrowing pass therefore needs a WRITE path that today's re-merge does not have.
  - verdict: corroborated | checked_at: 9fd0957 | by: operator-ux/cleanup | rescoped: n/a | evidence: manage-config/SKILL.md still documents domain-detect as a read verb accepting --affected-files
- OBSERVED: On a zero narrative match the detector has NO ranking signal — it emits
  `[{'domain': d, 'matched_aliases': []} for d in offerable]`, i.e. every offerable domain with
  no reasons attached. Read at
  `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_detect.py`
  § the zero-match branch and `_offerable_domains`. ⛔ Consequence for this plan's framing: the
  detector cannot be made to over-provision more precisely on its own, because it has nothing
  to be precise WITH. Narrowing must come from a later, better-informed reader — which is why
  this plan exists rather than a "rank the candidates better" plan.
- OBSERVED: The write path this plan needs already exists and is cheap — the executing agent
  described narrowing `references.json` domains as "a one-call fix". Corroborate the exact verb
  at outline before relying on the cost estimate.
- HYPOTHESIS: `phase-3-outline` is the earliest phase at which a trustworthy file set exists,
  because the solution outline's structured deliverables are where the declared footprint is
  first derived — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/manage-references/SKILL.md` § the declared-footprint
  derivation from the solution outline (verify-at-outline).
- HYPOTHESIS: Task-level skill resolution happens in `phase-4-plan` and therefore AFTER the
  proposed narrowing site, which is what makes narrowing safe — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md` § the skill-resolution step
  (verify-at-outline). ⛔ If skills are resolved BEFORE the narrowing site, narrowing would
  change execution under already-resolved tasks and the site must move earlier or the rule
  must become advisory-only.
- HYPOTHESIS: No consumer treats `references.domains` as append-only or caches it across
  phases — confirm/refute by sweeping every reader of `references.domains`
  (verify-at-outline).
- Verify-first clause: the narrowing rule must be settled against the actual skill-resolution
  order before it is implemented. A refutation of either sequencing claim above re-scopes this
  plan from "narrow" to "report the over-provision and let the operator narrow", which is a
  materially smaller change and an acceptable landing.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_domain_detect.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-2-refine/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-3-outline/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-config/standards/skill-domains.md`
- OBSERVED: `test/plan-marshall/manage-config/test_cmd_domain_detect.py`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md` — touched only
  if outline adopts shape (ii), the init-time agent-judged narrowing (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-references/` — the
  `references.domains` write path, if narrowing is written there rather than through
  `manage-config` (verify-at-outline)

## Dependencies and Sequencing

- ⛔ **Re-verify against post-PLAN-01 state, not against this spec's assumptions.** PLAN-01
  (#1380, merged `bf012b2cd`) MODIFIED `phase-2-refine/SKILL.md` and `phase-3-outline/SKILL.md`
  without declaring either — they were in THIS spec's Expected Surface, not PLAN-01's. It also
  widened `resolve-outline-skill` into an N-to-1 domain selector, touching
  `_cmd_skill_resolution.py`, `manage-config.py` and `query-config.py`. Every claim below about
  the re-merge point and the outline phase was written against the PRE-PLAN-01 tree and MUST be
  re-read at outline before it is scoped on. The N-to-1 selector in particular may already
  supply part of what this plan proposes to build.
- Depends on: **PLAN-01** only (shipped as #1380 — over-provisioning now exists, so there is
  something to narrow).
  ⛔ **The PLAN-02 dependency is DOWNGRADED to a preference, 2026-09-02.** It was stated as a
  hard dependency on the reasoning that glob knowledge makes a narrowed set accurate rather
  than merely smaller. That still holds as a quality argument, but the observed cost above is
  being paid NOW, on every plan, and narrowing from a derived footprint does not require the
  glob leg to work. Landing PLAN-03 after PLAN-02 is better; landing it before PLAN-02 is
  correct and materially better than not landing it.
- Overlaps with: PLAN-01 (`_cmd_domain_detect.py` — hard sequence), PLAN-02
  (`skill-domains.md`, `manage-config/SKILL.md`).
- Adjacent to: `phase-4-plan` skill resolution — the consumer this plan must not disturb. It
  is read to verify the sequencing claims and deliberately not modified.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/operator-ux/plans/PLAN-03-domain-post-plan-narrow.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
