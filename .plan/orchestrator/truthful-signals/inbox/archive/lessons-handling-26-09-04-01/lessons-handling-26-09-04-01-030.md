envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-09T06:45:29Z

component=plan-marshall:persona-plan-orchestrator
category=anti-pattern

Relayed from Token-Sheriff PLAN-10 (`refresh-2a-coverage-priorities`, PR #725 / `6953b03c`). ⚠ **Self-reported by the plan.** ⛔ The durable half is the CONTRAST inside one run: the same plan later ran a controlled two-form experiment against a challenge to ADR-0011 and the reviewer WITHDREW its finding. Same situation, opposite method — which is what makes this a method lesson rather than a one-off mistake.

# A specification claim used to dismiss a reviewer finding was asserted from memory, then promoted into a fix-task hard constraint and shipped as production Javadoc

**Proposed component**: `plan-marshall:persona-plan-orchestrator` (the orchestrator's own dismissal reasoning, not a script or tool defect)
**Proposed category**: `anti-pattern`
**Plan**: `refresh-2a-coverage-priorities` (PR #725, merged)
**Evidence**: findings `97b350` (pr-comment) and `5b35ad` (Q-Gate, phase `6-finalize`)

## What happened

CodeRabbit filed inline finding `97b350` against
`token-sheriff-client/.../lifecycle/TokenLifecycleManager.java:418`:
`switch (classification.kind())` is a switch **statement** over an enum, so a
future `Kind` constant can compile, take no lifecycle action, and fall through
to the caller's `throw refusedExchange`. The reviewer asked for a switch
expression or an explicit throwing `default` arm.

The orchestrator dismissed it as a false positive, reasoning from memory that
"the switch uses arrow syntax, making it an enhanced switch statement, which the
compiler already enforces exhaustively — a future `Kind` constant left unhandled
is a compile error, not a silent fall-through."

That claim is wrong. Under **JLS SE21 §14.11.1** an enum is a **legacy selector
type**. A switch *statement* is enhanced — and therefore exhaustiveness-checked —
only when it carries a pattern label, a null label, or a non-legacy selector
type. None applied. Arrow labels govern **fall-through between arms**, not
exhaustiveness classification. The silent fall-through the dismissal declared
impossible was exactly what the code did.

## Why it was worse than an ordinary wrong disposition

The claim did not stop at the disposition. It was carried into the TASK-011 fix
dispatch as a **hard constraint** — "the no-default shape is load-bearing, not
style… adding a default arm would destroy that property" — and the executing
agent, following the instruction faithfully, wrote the argument into
`handleRefusedExchange`'s Javadoc **as an explicit JLS citation**.

So the shipped code documented a compile-time guarantee it did not have, in the
direction that invites a later reader to remove the runtime guard *on purpose*.
The error was only caught because CodeRabbit rebutted a second time (review
comment 3961018824); the fix (commit `0d2e17b8`) added a real throwing `default`
arm and rewrote the Javadoc to state the actual rule, explicitly recording that
the earlier claim was wrong so it cannot be re-derived.

Three amplifiers, in order of severity:

1. A **dismissal** is the one disposition that produces no artifact anyone
   re-reads — the finding is closed and the reasoning is not re-examined.
2. Promoting a claim into a **dispatch constraint** removes the executing
   agent's licence to question it. Faithful execution is the failure mode, not
   the safeguard.
3. Landing it in **Javadoc as a spec citation** converts a private reasoning
   error into a durable, authoritative-looking artifact that outlives the run.

## The generalisable rule

> A specification claim used to **dismiss** a reviewer finding must be verified
> against the specification **before it is asserted** — and doubly so before it
> is promoted into an instruction another agent will implement faithfully.

Operationally:

- Dismissing a finding on a **language/spec/tool-semantics** claim requires the
  claim to be checked against the primary source (the JLS section, the argparse
  declaration, the plugin's parameter binding) — not recalled. Memory is enough
  to *raise* a hypothesis, never enough to *close* a finding with it.
- A claim that is about to become a **hard constraint in a dispatch prompt**
  crosses a verification threshold, because the downstream agent will not
  re-derive it. Constraint-grade claims get evidence attached.
- A claim asserted from memory must never be written into **production
  documentation** as a cited guarantee. Documenting a guarantee the code does not
  have is strictly worse than omitting the documentation.
- The reviewer's **second** rebuttal on the same point is a strong signal that
  the first dismissal was wrong. Treat repetition as evidence, not as noise.

## The contrast worth recording — the same run got it right later

Later in the same run, CodeRabbit challenged the ADR-0011 precedence claim
(comment 3962116699: "`-DskipITs` as a user property overrides plugin
`<configuration>`"). Having already been wrong once on this PR, the orchestrator
did **not** argue from memory. It ran a **controlled two-form experiment** — same
command, same tree, only the binding form differing:

- shipped `<properties>` form → `verify -pl token-sheriff-client -am -DskipITs=true`
  printed `failsafe:3.6.0:integration-test … Tests are skipped`
- temporary `<configuration><skipITs></skipITs></configuration>` form → the
  identical command printed `Using auto detected provider` and **ran** the ITs

The CLI override was demonstrably discarded by the configuration form. CodeRabbit
**withdrew** the finding: *"Your controlled comparison shows that the explicit
Failsafe `<configuration>` binding suppresses the `-DskipITs=true` override in
this build. The ADR correctly rejects that binding form. I withdraw this
finding."* The probe edit was reverted and the tree confirmed clean.

The companion comment on the same ADR (3962116711) was **accepted** on the same
evidentiary footing and the ADR was narrowed in commit `a42cda6e`.

The two halves of one run are the lesson: **assert-from-memory produced a shipped
false guarantee and needed two reviewer rounds to unwind; run-the-experiment
settled a harder claim in one round and got the reviewer to withdraw.** The cost
of the experiment was a single reverted probe edit.

## Why this is not covered by the six lessons already filed in this run

`2026-09-08-09-001`, `-11-001`, `-15-001`, `-16-001`, `-18-001`, `-18-002` and
`-18-003` are all **tooling** defects — a missing canonical entry, a store
resolution gap, a clean-tree assertion, a false-positive diff, an argparse
surface, an unresolvable notation, a mis-parsed test count. This one is about the
orchestrator's **own reasoning discipline**, which no tool change closes. It
belongs to a different class and needs its own record.
