envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=finding
created=2026-08-01T21:28:18Z

## Finding: `finalize-step-plugin-doctor`'s canonical WARNING message is unexecutable as written (literal `;` trips the one-command-per-Bash-call hook)

**Observed in**: main, during finalize of `mandatory-plan-id-build-results-ledger`.
**Scope**: outside every deliverable of this plan. Deliberately NOT fixed here.

### What was observed

The canonical WARNING message documented in `finalize-step-plugin-doctor` contains a
**literal `;`** inside the `manage-logging` message text. The one-command-per-Bash-call
enforcement hook rejects the call outright, because the `;` is read as a command separator
before the message text is ever treated as an opaque argument.

The documented command is therefore **unexecutable exactly as written**.

### Why it matters

Every scoped run that reaches the WARNING branch has only two available behaviours, and
both are bad:

- **fail once and improvise** — the agent hits the rejection, rewrites the message by
  hand, and the emitted warning text no longer matches the documented canonical form; or
- **silently skip the warning** — the branch produces no record at all, and a scoped
  plugin-doctor run that *should* have warned looks identical to one that had nothing to
  warn about.

The second outcome is the on-theme one: a missing warning is indistinguishable from an
absent condition. It also means the WARNING branch has effectively never been exercised in
its documented form, so its wording has never been validated in practice.

This is a known recurrence class — `manage-logging` messages containing a literal `;` trip
the one-command hook — appearing here in a *documented canonical invocation*, which is the
worst place for it because the documentation is what the agent is instructed not to
improvise away from.

### Suggested shape of a fix (not implemented)

- Rewrite the canonical WARNING message to remove the literal `;` (an em dash or a comma
  carries the same meaning).
- Add a lint over marketplace documentation that rejects any documented `manage-logging`
  invocation whose `--message` payload contains a shell-significant separator — this class
  is mechanically detectable and should not rely on being hit at run time.
