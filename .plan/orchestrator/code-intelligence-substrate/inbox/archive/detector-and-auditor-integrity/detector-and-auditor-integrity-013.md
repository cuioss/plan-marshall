envelope_version=1
sender_type=plan
sender_id=detector-and-auditor-integrity
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-31T08:34:59Z

module: plan-marshall:plan-retrospective
enrich_verb: best-practice
pattern: (plan-marshall:plan-retrospective, proposal (record only, do not decide), accepted)
recurrence: 2
threshold: 2
plan_id: detector-and-auditor-integrity

# Owed architecture hint — a producerless-row proposal is escalated, not implemented in-plan

## The owed call

```bash
python3 .plan/execute-script.py plan-marshall:manage-architecture:architecture \
  enrich best-practice --module plan-marshall:plan-retrospective
```

## The generalized hint

> When a `plan-retrospective` change surfaces a `SECTION_SPEC` row whose renderer is
> live but whose producer does not exist, the settled disposition is to RECORD the
> choice as an operator proposal carrying both options and a recommendation — and to
> escalate it — rather than to pick one inside the plan that found it. Registering a
> producer and deleting the row are both defensible and they diverge on a standing
> invariant (whether the compiler stays a pure assembler), so the decision belongs to
> whoever owns that invariant, not to the plan that happened to notice the row.

## Why this pattern and not the others

This plan produced six `(module, finding-class, disposition)` tuples that cleared the
`preference_min_recurrence: 2` threshold. Five were **dropped as inadmissible** and only
this one was promoted. The five are recorded in the plan's decision log; the short form:

every one of them was `(python, "test failure in test/…", taken_into_account)`, and all
fifteen underlying findings are **deliberate RED observations from deliverable 9's
mutation proof** — auto-filed by the build-runner while a mutation was applied, and
resolved `taken_into_account` with a detail saying exactly that. They are an artifact of
the mutation methodology, never an operator preference about how test failures should be
dispositioned. Promoting them would emit a durable hint asserting that python test
failures are routinely accepted, which is false and actively harmful.

## The admissibility gap this exposes

The step's authorship-admissibility rule excludes one kind of pipeline control traffic —
a `pr-comment` finding with no recognized reviewer `bot_kind` — but nothing excludes a
**build-runner-produced `test-failure` finding that the run induced on purpose**. Both are
the pipeline observing itself rather than an operator expressing a preference, and only
the first is filtered.

The gap is latent for an ordinary plan and only fires for one that mutates deliberately,
which is why it has not surfaced before. A plan running a mutation proof will reliably
manufacture a threshold-clearing recurrence out of its own methodology.

Candidate remedy for the orchestrator to weigh: extend the admissibility rule to exclude
findings whose `resolution_detail` attributes them to an induced or reverted state, or
give the build-runner a distinct finding provenance the gate can filter on. Either is a
change to the shared `disposition-to-hint-routing.md` contract, so it is named here rather
than made by this plan.
