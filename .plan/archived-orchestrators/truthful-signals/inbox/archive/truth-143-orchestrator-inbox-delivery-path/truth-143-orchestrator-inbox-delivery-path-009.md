envelope_version=1
sender_type=plan
sender_id=truth-143-orchestrator-inbox-delivery-path
epic=truthful-signals
kind=candidate-lesson
created=2026-09-20T08:27:41Z

# Candidate lesson: a hand-maintained doc enumeration of a code-declared set is the dominant defect class of this run

## Signal source

Q-Gate `6-finalize` self-review findings (contract_drift class): `cae00c`, `20276e`, `8af8e3`, `613869`, `d67222`, `32ea8e`, `a24d1d`, `087589`, `a79fd5`, `4f314a`, `e9862b`, `4f4183`, `22a436`, `037198`.
PR #1539 CodeRabbit comments: `f97bff`, `3bcf06`, and outside-diff item 2 of `15ddea`.

## Observation

Seventeen findings across two independent detectors (the plan's own pre-submission self-review and CodeRabbit) reduce to one shape: a **documentation or test enumeration that restates a set declared in code, with nothing tying the restatement to its declaring source**.

Concrete instances from this run:

- `plan-orchestrator/SKILL.md` restated the `inbox read` return field list, the `inbox list` row schema, the `inbox validate` rejection-code table and the message-state field set. Each drifted the moment `_message_row` / `_validate_state_fields` gained a field (`consumption`, `consumed_at`, `invalid_consume_state`).
- `orchestrator.py`'s module docstring carried a brace-enumerated inbox verb set that omitted `read` while the adjacent prose described it.
- `test_orchestrator_corpus.py` pinned the literal membership and cardinality of `CANDIDATE_KINDS` / `CANDIDATE_DERIVATION_STATES`, so a valid vocabulary extension breaks CI while production stays correct.
- `test_inbox_channel_contract.py` used a manually maintained rejection-code tuple that omitted `invalid_consume_state`, so the documentation check passed over an incomplete population.

## Corrective rule

When a document or test needs to refer to a set that code declares:

1. **Point at the declaring source** rather than restating its members. A cross-reference cannot go stale; an enumeration can.
2. When the enumeration must exist (a rendered table, a schema doc), **derive it** — parse the declaring source at test time and assert equality, and **guard the parsed population non-empty at import** so an empty parse cannot masquerade as agreement.
3. Never write a cardinality phrase ("the four message-state checks", "three documentation blocks") beside an enumeration. This run produced `7fa03a` (four counts stale in one paragraph) and `037198` (a closed-population claim of three that was actually four) from exactly that habit. The terminating move is to **delete the cardinality sentence**, not to bump the number.

## Why it is worth recording at epic level

This is not a one-plan accident: two independent reviewers converged on it, and it accounted for roughly two thirds of this plan's finalize findings. The repo's own path instructions already state the rule ("treat a hardcoded list that must mirror a set defined elsewhere as a defect unless it is derived from that source"), so the gap is between a stated rule and the absence of an edit-time instrument that enforces it.
