# Domain-Knowledge Authoring Reflexes

Authoring-time reflexes that apply whenever a plan authors **new domain-knowledge content** — security-mechanism explanations, "why this is WRONG" examples, best-practice rules, or any prose that makes a substantive domain claim a reader will rely on.

These reflexes **shift left**: they reduce the surface that reaches review, rather than duplicating the reviewer. They are authored discipline, not an automated gate (see "Why no in-house gate" below).

## Reflex 1: Verify the mechanism for the SPECIFIC example shown, not just the general family

A mechanism explanation that holds for a broad category can be **false for a particular example** inside or adjacent to that category. The failure shape: a correct-for-the-family explanation is attached to an example that the family rule does not actually cover.

Concrete instance: a split-step "the value is frozen in an upstream layer and therefore cannot leak" explanation was applied to a *same-step* example that was excluded from one layer but still leaked through history/metadata. The mechanism statement was true for the split-step family and wrong for the same-step example shown next to it.

**Reflex**: Before asserting a mechanism for an example, confirm the mechanism holds for that **exact example** — not merely for the broad category the example appears to belong to. Trace the specific example through the mechanism end to end.

## Reflex 2: Enumerate EVERY failure/leak vector, not just the most obvious one

For any security or robustness claim, a single named vector is rarely the whole story. The first vector that comes to mind is the one the author already understands; the dangerous vector is the second one.

**Reflex**: For each claim, explicitly ask "is there a *second* mechanism by which this still fails?" — and answer it before writing the claim as settled. A claim that names one leak path and stops is incomplete until the search for additional paths has been run and recorded.

## Reflex 3: Sweep the fan-out when a domain claim is corrected

A domain-claim correction is a **contract change**. Every doc that restates the claim, or whose guidance depends on it, is a consumer of that contract — and each consumer drifts the moment the claim changes.

**Reflex**: When you correct a domain claim, enumerate and update its consumers. Use the existing doc-contract-drift / consumer-sweep discipline rather than re-deriving the enumeration procedure here — see [`plan-marshall:phase-3-outline` contract-surface-enumeration.md](../../../../plan-marshall/skills/phase-3-outline/standards/contract-surface-enumeration.md) for how to surface the consumer fan-out.

## Why no in-house gate

In-house gates — Q-Gate, plugin-doctor, pre-submission self-review — verify **structure and internal consistency**, not **domain correctness**. A claim can be structurally perfect, internally consistent, and still be a plausible-but-imprecise domain error.

Only **external domain-expert review** separates a correct claim from a plausible-but-wrong one. An in-house "domain-accuracy self-check" would be the authoring model re-grading its own claim — a strictly weaker duplicate of external review, and itself a fresh instance of the very anti-pattern these reflexes guard against.

So the reflexes above are authoring-time discipline that shrinks what reaches the external reviewer. They do not replace, and must not be mistaken for, that review.
