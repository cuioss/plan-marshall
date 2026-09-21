# WS-03: Durability and sharing — a finding that lives on one machine is not a finding

epic: lessons-routing
status: active

## Charter

Make a client-local finding survive the machine that produced it and reach the client's other
developers.

**The cause is structural, not accidental.** `.gitignore:45` is `.plan/*` with exceptions only for
`marshal.json` and `project-architecture/`; `git ls-files .plan` returns 15 tracked files, none under
`local/`. ⇒ **`.plan/local/lessons-learned/` is untracked by construction.** A lesson is visible to
exactly one developer on exactly one checkout, forever.

## In scope

- Whether the client-local corpus becomes shared state, and by what substrate.
- The operator's stated direction — *"eventually we should streamline here to issues anyway"* — priced
  against keeping a file store. ⚠ **This workstream's gate exists to test that reading**, because it is
  the assumption most worth falsifying early: issues-for-everything is simpler to reason about but puts
  every routine finding into a tracker the client may not want it in.
- If a file store survives: where it lives such that it is committable without dragging the rest of
  `.plan/local/` into version control.

## Out of scope

- The upstream class (WS-02) — it is already leaving the repo.
- Changing what `.plan/*` ignores for anything other than this corpus. ⛔ A broad un-ignoring is a much
  larger change with its own blast radius and is explicitly not licensed here.

## Done when

A client-local finding is visible to a second developer on a second checkout without either of them
copying files by hand.
