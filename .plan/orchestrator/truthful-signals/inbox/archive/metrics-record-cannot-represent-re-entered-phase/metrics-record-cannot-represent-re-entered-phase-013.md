envelope_version=1
sender_type=plan
sender_id=metrics-record-cannot-represent-re-entered-phase
epic=truthful-signals
kind=finding
created=2026-08-09T21:05:37Z

# Finding: the cross-epic CIS notification is UNVERIFIABLE from this envelope — needs orchestrator reconciliation

**Kind**: finding (requires orchestrator action, not a lesson)
**Source**: PLAN-TRUTH-055 finalize / lessons-capture
**Blocks**: nothing in this plan; blocks two `code-intelligence-substrate` plans

## The obligation

This plan's **D6** extended the population vocabulary that two `code-intelligence-substrate` plans
depend on:

- **CIS-022** consumes the vocabulary.
- **CIS-030 / L3** is gated on it.

The plan's own `request.md` records this notification as **REQUIRED before landing** rather than
conditional — the Constraints block's notify-CIS-if-the-vocabulary-moves trigger FIRED when
operator ruling 3 added D6 (see Q-Gate finding `2805d1`).

The dispatch brief for this step stated the message had already been emitted during execute, and
instructed: *"Confirm it exists rather than assuming."*

## What was checked, and what it proves

```
orchestrator inbox list --slug code-intelligence-substrate
  → status: success
    inbox_state: present
    count: 0
    invalid_count: 0
    messages[0]:
```

The CIS inbox is scaffolded and **empty**.

**This result does not discriminate between two different worlds:**

1. The message WAS emitted and has since been consumed — `inbox archive` relocates a drained
   message to `inbox/archive/`, and `inbox list` explicitly does not enumerate archived messages.
2. The message was NEVER emitted, and the required cross-epic obligation was silently dropped.

No read verb in the `orchestrator inbox` surface enumerates `inbox/archive/`, and this envelope's
hard rules route all `.plan/` access through `manage-*` scripts, so the archive cannot be inspected
from here. **This is a genuine coverage gap, reported rather than papered over.**

No message was emitted to CIS from this step, deliberately: re-emitting risks a duplicate that the
CIS ledger cannot detect (a ledger cannot see a duplicate in another ledger), and the
lessons-capture workflow's orchestrated branch scopes emission to this plan's own epic.

## Requested orchestrator action

1. Inspect `.plan/local/orchestrator/code-intelligence-substrate/inbox/archive/` for a message
   whose `sender_id` is `metrics-record-cannot-represent-re-entered-phase`.
2. If absent → the obligation was dropped. Emit the vocabulary-extension notification to CIS,
   carrying: the D6 denominator + mandatory sampling-point field, the reuse of the D1 discriminator
   vocabulary, the explicit prohibition on introducing a second vocabulary, and the
   not-persisted-if-undatable rule. PR #1129 is the landing reference.
3. If present → no action; record the obligation as discharged.

## Secondary observation worth a rule

The `inbox` surface can report `count: 0` for both "never sent" and "sent and drained". Any
obligation whose discharge is verified against `inbox list` is verified against an
**ambiguous oracle**. Either a `--include-archived` read flag or an explicit discharge stamp on
the emitting plan's ledger row would make cross-epic obligations auditable after the drain.
