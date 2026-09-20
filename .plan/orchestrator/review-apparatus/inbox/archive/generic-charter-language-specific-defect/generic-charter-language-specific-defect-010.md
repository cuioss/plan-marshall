envelope_version=1
sender_type=plan
sender_id=generic-charter-language-specific-defect
epic=review-apparatus
kind=candidate-lesson
created=2026-08-09T17:08:52Z

# A deliverable that mandates a sweep in one field and lists files in another has two populations and no comparator

component: plan-marshall:phase-3-outline
category: bug
confidence: high
source_signal: signal_qgate_pending_count

## Context

The 3-outline Q-Gate raised six findings on this plan; the two carrying `severity: error` are the same structural defect seen at two altitudes.

**Instance 1 — inside one deliverable (`dc3ba1`).** D4 widened pr-agent's `participation_evidence` with `inline`. Its own **Change per file** text *mandated* extending the sweep to `bot-participation-contract.md`, `coderabbit.md`, and `sourcery.md`. Its **Affected files** listed `pr-agent.md` alone. Two lists, same deliverable, both machine-readable, in direct contradiction — and the contradiction is not cosmetic, because phase-5 execution cannot edit a file absent from `affected_files`. A mandated edit was made structurally impossible by the sibling field three lines away. The sweep was not hypothetical: `bot-participation-contract.md:122` attributed the inline publish shape to CodeRabbit alone, `:124` justified `issue_comment` with "For a bot whose ONLY publish shape is a PR-level comment" naming PR-Agent, and `:140` asserted PR-Agent "publishes exactly one persistent Guide comment" — three statements the widening falsifies.

**Instance 2 — across the whole plan (`785806`).** D5 renamed the emitted agents file to `AGENTS.md` and listed only the command doc. `marshall-steward/scripts/determine_mode.py:149` hard-codes the lowercase name in `CONTENT_CHECKS`, and `check_docs()` at `:401` **silently skips a non-existent file**. So the rename would have turned the steward's doc-check into a permanent no-op for the agents file on a case-sensitive filesystem — the exact fail-open class D5 existed to close, reintroduced by D5. Two test modules pinned the old behaviour. The gate's fix widened D5 by five files and moved its bucket from `documentation_only` to `mixed_with_docs`.

**Instance 3 — the grounding pass itself (`86791e`).** Sixteen component assessments were filed for this plan. **Fourteen are `CERTAIN_EXCLUDE` on skills matched incidentally by an `agents.md` content filter.** Only two `CERTAIN_INCLUDE` exist, both on the agents-file surface. D1 (eight paths under `marketplace/targets`), D2 (six paths), and D3 (one path) — fifteen in-worktree, fully assessable paths, including the generator core the other deliverables depend on — carry **no `CERTAIN_INCLUDE` at all**. The assessment pass swept the surface its *matcher* happened to reach and never touched the plan's core deliverable. The pre-existing foreign-repo carve-out excuses only D6–D8. This was accepted as recorded residue, with the honest consequence stated: D1–D3 affected-file lists are author-asserted, not independently assessed.

## Root cause

In all three, a **declared** population and a **realized** population diverge and nothing compares them:

- `Change per file` prose declares a sweep; `Affected files` realizes an edit set. No check pairs them.
- A deliverable declares a rename; the consumer set that must move with it is discovered by whoever thinks to look.
- The assessment pass declares coverage of "the plan"; its realized coverage is whatever its content matcher hit. Fourteen exclusions on incidental matches is a *matcher* footprint, not a *plan* footprint — and the ratio (14 of 16 excludes, all from one filter) is itself the tell that nobody read.

Each declared population is already machine-readable. Only the comparison is missing.

## Proposed action

1. **Compare a deliverable's own two fields.** When `Change per file` names a concrete path that `Affected files` does not list, that is a deterministic, zero-inference finding. This is the cheapest of the three and would have caught `dc3ba1` outright.
2. **Publish the assessment pass's coverage ratio next to its verdict.** An assessment set that is 14/16 `CERTAIN_EXCLUDE`, all traceable to a single content filter, must not read as "the plan was assessed". Report per-deliverable assessment coverage — deliverables with zero `CERTAIN_INCLUDE` named explicitly — so an unassessed core deliverable is visible rather than inferred by a reviewer counting rows. This is the same *set-guarding check must publish its population* rule the epic already tracks; here the unguarded population is the assessment pass's own reach.
3. **Treat "renames a name that other code hard-codes" as a first-class consumer sweep**, with the silent-skip fail-open (`check_docs` continuing past a missing file) as the specific hazard to enumerate — a consumer that *fails loudly* on the rename is self-reporting; one that *skips silently* is not, and only the second kind needs the sweep.

## What worked, recorded so it is not lost

The outline Q-Gate caught both `error`-severity instances **before** any code was written, with clean sweep coverage (`files_scanned: 4177`, no unreadable, no elided, not truncated), and both fixes were verified against disk rather than asserted. `dc3ba1`'s fix additionally surfaced an ordering hazard nobody had stated — `test_bot_participation_contract.py:638` reads `participation_evidence(bot)[0]`, so `inline` had to be appended *after* `issue_comment` or seven registry-derived consumers would have been silently re-pointed without a test failing. That is a defect the gate did not look for and the fix found by reading. The gate is doing real work; its blind spot is the pairing, not the reading.

## Relation to the epic

`dc3ba1` sits directly on this epic's surface — `bot-participation-contract.md`, `coderabbit.md`, `sourcery.md` — and its ordering hazard (`participation_evidence(bot)[0]` as a load-bearing element) is a constraint **PLAN-PR-005** (*participation derived from a lossy view*) and **PLAN-PR-006** must both respect: the first element of that list is read as a bot's synthesized publish shape by seven modules, so any plan reordering it changes behaviour with no failing test.

## Evidence

- Q-Gate `dc3ba1` (3-outline, `severity: error`) — Change per file mandates a three-file sweep; Affected files lists one
- Q-Gate `785806` (3-outline, `severity: error`) — `determine_mode.py:149` lowercase entry, `check_docs():401-402` bare continue past a missing file
- Q-Gate `86791e` (3-outline) — 16 assessments, 14 `CERTAIN_EXCLUDE` from one incidental content filter, D1–D3 with zero `CERTAIN_INCLUDE`; resolved `taken_into_account` as accepted residue
- Q-Gate `373ef9`, `8a0b28` — a stale `CERTAIN_EXCLUDE` contradicting D2, and D2 declaring `module: default` for paths resolving to `plan-marshall`; both corroborate that the assessment set was not read against the deliverables
- `test_bot_participation_contract.py:638` — `participation_evidence(bot)[0]`
