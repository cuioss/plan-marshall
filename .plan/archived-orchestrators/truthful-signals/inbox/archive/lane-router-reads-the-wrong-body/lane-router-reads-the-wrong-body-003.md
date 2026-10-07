envelope_version=1
sender_type=plan
sender_id=lane-router-reads-the-wrong-body
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:53:46Z

component=plan-marshall:phase-3-outline
category=anti-pattern
proposed_title=Re-verify a spec's stated mechanism at HEAD before implementing it — same verdict, wrong evidence still means a wrong fix

# Re-verify a spec's stated mechanism at HEAD before implementing it — same verdict, wrong evidence still means a wrong fix

## What happened

The plan spec for `lane-router-reads-the-wrong-body` stated the mechanism of Defect A confidently:

> `## Original Input` is EMPTY (0 bytes), so the scorer falls back to scoring the `source_id` header.

Both halves were **refuted at HEAD** during D1 investigation:

1. `_read_request_body` **never returns `_header`** — there is no source_id fallback path at all.
2. An empty section yields `''`, which classifies as `single_module`, **never `surgical`** — so the spec's stated chain could not have produced the observed verdict.

The real mechanism: the `## Original Input` section is **TRUNCATED, not empty**. It retains the spec title and the template blockquote, and that blockquote's citation is the single path the scorer counted.

The spec's *verdict* ("the scorer reads the wrong body") was correct. Its *evidence* was wrong. The fix corrected the mechanism and the implementation follows the real one. Write-up at `work/d1-verdict.md`.

## Why it matters

A spec that is right for the wrong reason is the most dangerous input to an implementation phase, because:

- the deliverable still "matches the spec," so no gate fires;
- the tests get written against the spec's stated mechanism, pinning the wrong invariant (`test-pins-the-defect`);
- the residual real mechanism survives the fix untouched.

Here it would have produced a fix guarding an empty-section case that cannot occur, while the truncated-section case — the actual live one — kept firing.

## The rule

**A plan spec's stated MECHANISM is a hypothesis, not a finding.** Before implementing, re-derive it against HEAD:

- read the cited function and confirm each claimed branch actually exists (`_read_request_body` returning `_header`);
- confirm the claimed input value actually produces the claimed output classification (empty → `single_module`, not `surgical`);
- when mechanism and verdict disagree, **the mechanism loses** — re-derive it and write the correction down before touching code.

Agreeing with the spec's conclusion is NOT confirmation of the spec's mechanism. Record the corrected mechanism as an artifact (here: `work/d1-verdict.md`) so the divergence between spec-as-written and reality is visible at review time.

## Related

Sibling of the `defending-documentation` / `vacuous-authority` archetype: the spec was treated as authority over the code it describes.
