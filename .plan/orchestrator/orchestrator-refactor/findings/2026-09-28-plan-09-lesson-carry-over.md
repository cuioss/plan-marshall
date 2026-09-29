# PLAN-09 landing — lesson carry-over awaiting a target

Held here by operator decision (2026-09-29): "keep — we will later introduce a target". Source: the four
`candidate-lesson` messages that arrived with the PLAN-09 landing (#1652, archived under
`inbox/archive/orchestrator-worktree-substrate/orchestrator-worktree-substrate-001..004.md`) plus two
landing-residue rules from `landings/PLAN-09.md`. Each remedy is a Python or process-prose change, so under the
PM-MCP supersession each was dispositioned `discarded` for plan-marshall and is kept here as an
implementation-free rule for the future target. The original target, `plan-marshall-mcp/doc/known-defects/`, no
longer exists. Move this file's rows to the new target when it is introduced, then retire this file.

| Source | Carry-over (implementation-free) | Kind |
|---|---|---|
| lesson 001 (retrospective) | A payload whose delivered size is far below its produced size is truncated, never "small": when delivered_bytes ≪ produced_bytes, a budget gate derived from the delivered figure must not pass, and the analysis tier must degrade with a named reason. Fixture: 69 of 236,070 reduced transcript bytes delivered, Tier 1 selected (block-scalar continuation lines emitted at column 0). | invariant + fixture |
| lesson 002 (metrics) | Every dispatch-boundary record carries the step key and the leaf's usage figures, so it joins its step record by key, never by timestamp window. Fixture: 35/35 boundary rows keyless, 11 execute rows at 0 tokens, 0 of 63 paired. An unmeasured field is `unmeasured`, never `0`. | invariant + fixture |
| lesson 003 (self-review) | A coverage-class step lacking the tool to establish coverage returns a coverage-gap verdict. It does not spend a loop-back, and a verifier refusal caused by a missing tool does not count against the ceiling. Fixture: 7 firings, 5/5 loop-backs, 263 candidates, operator override (finding 5f65bb). | rule + fixture |
| lesson 004 (outline) | An outline that marks a path certainly-excluded while a deliverable declares it for modification is rejected at validation; declared lists are reconciled against the realized footprint after execute. Fixture: manage-logging/SKILL.md; 9 undeclared test modules; 1 declared test untouched. | invariant + fixture |
| landing residue | A landing's merge-commit fact comes from the PR's merge record, never local HEAD after a pull (recorded 438a0a71f while main was at c9c67839c). | invariant + fixture |
| landing residue | A reserved never-removed resource has a dedicated refusal on every destructive path, not an incidental one; a reused long-lived worktree is verified on its expected branch before any commit. | invariant |
