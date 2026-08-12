# Run report — 210-named-recovery-discards-operator-config (run 01)

**Date (UTC):** 2026-08-12    **Branch:** `claude/named-recovery-operator-config-d9v43a` (harness-assigned; kept as-is)    **PR:** _pending_    **Outcome:** completed

## Skills loaded

Loaded by reading bundle-source paths (the `plan-marshall` plugin was not relied on):

- `cloud-plan-lane` (the governing contract, loaded first)
- `plan-marshall:ref-code-quality` (always)
- `pm-plugin-development:plugin-script-architecture` (always)
- `plan-marshall:ref-workflow-architecture` (workflow docs — the change's surface)
- `pm-dev-python:pytest-testing` (the new Python tests)

Conditional skills not loaded because unused: `plan-marshall:persona-implementer` (no production code — the change is workflow prose + a doc-content test), `pm-dev-python:python-core` (the test uses only `re` + stdlib and the conftest helpers), `pm-plugin-development:plugin-architecture` (no SKILL frontmatter/structure change), `pm-documents:ref-asciidoc` (no `.adoc` change), `plan-marshall:persona-security-expert` (not a security-domain change).

## Deliverables

### D0 — GATE: derive the population by assertion shape (mutates nothing)

Derived by **assertion shape** — "a document asserting that an artifact is safe to discard, restore, or delete on the strength of a guard that establishes only that one actor didn't write it" — not by command string. The sweep ran multiple phrasings across the full documentation surface (`marketplace/bundles/**`, `.claude/**`, `doc/**`, whole-repo `*.md`) and the script surface (`*.py`):

- `safe to (revert|delete|discard|remove|restore|drop|throw away|wipe|clean)`
- `(safely|freely|always) (delete|discard|revert|remove|restore|drop)`
- `git checkout --` / `git restore` / `reset --hard` / `git clean` / `rm -rf`
- `spurious write` / `without losing any` / `never a … output artifact` / `MUST NOT have touched`
- `restore … from HEAD` / `loses no` / `nothing is lost` / `no work is lost` / `no data loss`
- `Named recovery` / `Recovery: git` / `recovery case`

**Hit count vs population size (reported separately, per the plan and Verification):**

- **Hit count (raw volume examined):** several dozen matched lines across all phrasings and surfaces — a *volume*, not coverage. The bulk are unrelated uses of the same words: idempotency of an operation ("re-running `upgrade` is always safe", "Stop is always safe"), configuration semantics ("an unconfigured project loses nothing"), lock-guard cleanup ("the guard file is always removed in a `finally`"), and node_modules/apt/temp cleanup commands.
- **Population size (derived by shape): 3.** Exactly the three named-recovery `.plan/marshal.json` sites — planning.md (2-refine boundary), planning-outline.md (3-outline boundary), planning-outline.md (4-plan boundary). No fourth site of this assertion shape exists in the documentation or script surface.

**The three known sites were treated as a sample, not assumed to be the population** — the derivation is a shape sweep, and D3(b) encodes it (sweep by heading across every workflow doc, so a future fourth boundary is covered automatically). The sample-as-population error the plan warns against is avoided: the count of 3 is a *derived* result, not the seed.

**Two counter-postures already in the repo (NOT in the destructive population — they are the correct model):**
- `execute-task/SKILL.md` §"Anti-pattern: never batch a destructive checkout to re-baseline" — states plainly that `git checkout -- <files>` / `git restore <files>` are "destructive of uncommitted working-tree content with no undo" and mandates inspection + per-path proof before any revert. This is the exact correct treatment the three named-recovery sites contradicted; D1's replacement aligns with it.
- `plugin-script-architecture/standards/shim-marker-convention.md` and `plugin-doctor/references/rule-catalog.md` — "nobody can **prove** it is safe to delete" (evidence required), and `risky-fixes-guide.md` — a shim "can be safely removed" only after the live-caller count "must be verified to be ≤1".

**Sibling-plan hand-off (Out-of-scope item):** the sibling plan `truthful-signals/140-detect-artifacts-offers-a-live-audit-trail-as-safe-to-delete` covers the same archetype on a **different surface** — a *tool* (`detect-artifacts`/`scan_artifacts` in `git-workflow.py`) that offered a running plan's live audit trail as safe-to-delete. That plan is already landed (PR #1171). **The two surfaces do NOT share a code root** — one is workflow prose emitting a human-facing recovery line, the other is a Python traversal classifier — so there is nothing to re-scope and nothing fixed "twice in two shapes". D0's population (the 3 doc sites) is disjoint from 140's surface.

### D1 — Replace the false inference at every site

Done at all three sites. The valid inference — *"phase N must not have touched it" → "something other than phase N wrote it (most likely the operator)"* → **inspection, not restoration** — now drives each block. The recovery surfaces the diff (`git diff -- .plan/marshal.json`) and requires an **explicit operator disposition** (Keep / Discard) before any discard; a discard is permitted only on an explicit operator "Discard" and only against that one file. Commit `6308698`.

⛔ **The word "always" does not survive in any justification** at any of the three sites — verified: `always safe` / `always a spurious` / `MUST NOT have touched` / `Recovery: git checkout --` all return zero matches across both workflow files (incl. the cross-reference bullets, one of which — planning.md — had carried "makes marshal.json restoration always safe").

### D2 — Collapse the triplet into ONE authority

Done. The full contract (premise, danger, inspection steps, disposition options) now exists **once**, in `planning.md` at the 2-refine boundary, marked "the single authority for this recovery — the outline and plan phase boundaries reference this block". The two `planning-outline.md` boundaries (3-outline, 4-plan) are now **references** to it — a one-line imperative plus a cross-reference bullet pointing at the authority — not restatements of the justification. Per the standing rule, the copies were deleted (replaced by references), not synchronised. The drift evidence the plan cited — the 2-refine copy's grammatical corruption *"a spurious write that safe to revert"* (missing "is") — is gone with the copy.

### D3 — Tests, each verified RED pre-fix

New file `test/plan-marshall/plan-marshall/test_named_recovery_marshal_config.py`, three tests, **each seen red against the unfixed docs before the fix, green after** (see § Findings for the red evidence):

- `test_named_recovery_never_instructs_unconditional_discard` — D3(a): no derived named-recovery region carries an unconditional-discard directive or an "always safe" justification.
- `test_named_recovery_inspection_first_population_nonempty_and_covers_known_members` — D3(b): the derived population of inspection-first sites is asserted **non-empty** and covers the known members, with a non-vacuous control (the plain by-heading sweep) proving the derivation examined a populated surface — so the non-empty assertion cannot pass on an empty sweep. **The derivation is asserted, not the enumeration** (the known members are checked as a subset, and the sweep globs every workflow doc).
- `test_named_recovery_contract_is_a_single_authority` — D2 collapse guard: exactly one authority (the block carrying the concrete `git diff` inspection command); every other named-recovery site references it. This is red pre-fix (three copies, zero authorities) and pins the collapse against future re-drift.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` verdict: **Python changed** (the new test file) → build gate takes its full path.

`./pw verify plan-marshall` (scoped — the entire diff is within the plan-marshall bundle and its test dir): **`16157 passed, 1 skipped in 318.99s`**; coverage line: `mypy(production) [277 files], ruff [marketplace/bundles/plan-marshall, test/plan-marshall], SPDX headers, mypy(test) [574 files], module-tests [plan-marshall]`; `=== verify: SUCCESS ===`. No `errors[]`. The single skip is the pre-existing environment-guarded test (the reference-platform `skipped == 0` gate is CI-opt-in; a local scoped run does not set it), not introduced by this change.

## Findings

Every finding with source and disposition. Recorded per instance.

### D3 pre-fix RED evidence (each test seen red first, against unfixed docs)

Run with the session's `pytest` (uv-tool 9.0.2, `-o addopts="" -o filterwarnings=ignore`) directly against the workflow docs at HEAD before the fix:

| Test | Pre-fix | Evidence |
|---|---|---|
| `test_named_recovery_never_instructs_unconditional_discard` (D3a) | RED | Offender list named all three sites — `planning.md:390`, `planning-outline.md:257`, `planning-outline.md:581` — each carrying BOTH an unconditional `git checkout --` recovery directive AND an "always safe"/"always a spurious" justification. |
| `test_named_recovery_inspection_first_population_nonempty_and_covers_known_members` (D3b) | RED | `assert []` — zero inspection-first sites. The non-vacuous control passed first (the by-heading sweep found 3 regions incl. both planning-outline.md boundaries), so the failure is specifically the empty inspection-first population, not a vacuous sweep. |
| `test_named_recovery_contract_is_a_single_authority` (D2) | RED | `assert 0 == 1` — zero authorities (no block carried the `git diff -- .plan/marshal.json` inspection command); three copies existed. |

Post-fix: all three PASS (`3 passed`), and the full scoped suite is green (§ Build gate).

### Verification sub-agents (pre-PR)

_(pending — recorded below once both sub-agents return)_

## Reviewer participation

_(pending PR creation)_

## Cost

- **Tokens:** not available to the agent in this session (a single interactive Claude Code cloud session; the harness does not surface a per-run token count here).
- **Wall-clock:** dominated by one `./pw verify plan-marshall` (~5m19s build + suite) plus the shape sweep and two verification sub-agents.
- **Population:** this single Claude Code cloud session's usage. ⛔ NOT comparable to a plan-marshall `metrics.toon` total, which counts the orchestrator-plus-agent dispatch tree under plan-marshall's per-task billing boundary — a boundary a single interactive cloud session does not share. No comparable number is presented.

## Contract check (Step 9)

_(completed at Step 8 condition 3, before arming auto-merge)_

## What have we learned (Step 9)

_(recorded at close)_

## Residue

_(recorded at close)_
