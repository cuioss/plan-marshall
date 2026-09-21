# WS-02: Script surfaces refuse input they cannot honour

epic: tooling-truthfulness

## Charter

Own the orchestrator script surfaces that accept input without validating it and then report
success. Both members are CONFIRMED live rather than inferred: `queue --transition` was observed
accepting an arbitrary status token and writing it to a real ledger row, and `corpus set-verdict`'s
claim index was observed landing five verdicts on the wrong claims because the ordinal is positional
over all bullets and no consumer surfaces that mapping.

⚠️ Both were found by USING them, not by reading them. That is worth stating: the surfaces are
documented, and the documentation did not prevent either failure.

The workstream closes when each surface either refuses what it cannot honour or reports what it
actually addressed — with a red-first guard for both.
