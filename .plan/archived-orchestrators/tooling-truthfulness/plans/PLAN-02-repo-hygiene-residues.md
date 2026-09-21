# PLAN-02: Two verified repo-hygiene residues

epic: tooling-truthfulness
workstream: WS-04

> Staged plan spec — one shippable unit of work. SELF-SUFFICIENT: the emitted command is a
> one-line pointer and carries no brief.

## Epic Constraints (bind every deliverable)

- **ADR-019 binds reflexively:** every guard is red-first.
- **Confirm the Expected Surface against the tree as the first action.** ⛔ A surface expansion updates this section IN THE SAME ACT.

## Objective

Two small residues, both verified live at HEAD, neither needing design work. `CROSSING-INVENTORY.md`
sits tracked at the repository root — a working document that landed where it does not belong. And
the `format` alias formats three trees while `lint` checks four and `build.py`'s quality gate
rewrites four, so `marketplace/targets/` drifts into a state the gate then silently rewrites
underneath the developer.

⭐ **This plan exists to be DISJOINT.** Every other member of this epic touches an overlapping
orchestrator surface, so at `parallelization_scope: 2` this is the work that can fill the second
slot. That is a reason to keep it small and separate, not to grow it.

## Deliverables

1. **D1 — `CROSSING-INVENTORY.md` leaves the repository root.** Confirmed present and git-tracked at HEAD. ⛔ Determine whether it is superseded or merely misplaced BEFORE deleting: if its content is live, it belongs under `doc/` or in the orchestrator ledger, and deleting live content to tidy a root listing is worse than the untidy root.
   *Done when:* the root no longer carries it, and the PR body states which disposition applied and why.
2. **D2 — `format` covers the same trees `lint` and the quality gate do.** `pyproject.toml`'s `format` and `fmt` aliases run `ruff format` over `marketplace/bundles/ test/ .claude/`; `lint` adds `marketplace/targets/`, and `build.py`'s full-tree quality gate uses `[BUNDLES_DIR, TARGETS_DIR, TEST_DIR, CLAUDE_DIR]` for BOTH `ruff check --fix` and `ruff format`. So a developer running `./pw format` produces a different tree from the gate.
   *Done when:* the three tree sets agree, or a stated reason explains why one legitimately differs. ⚠️ Adding the tree may reformat files on first run — that churn is the deliverable's evidence, and per the hard rule shipped in #1461 it must be committed rather than backed out with `git restore`.

## Claim Labels

- OBSERVED: `CROSSING-INVENTORY.md` exists at the repository root and `git ls-files` resolves it — checked 2026-09-10.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: git ls-files resolves CROSSING-INVENTORY.md at repo root and the file exists on disk at HEAD 5c18ef918
- OBSERVED: `pyproject.toml`:100–101 (`fmt`, `format`) omit `marketplace/targets/`; `:75` (`lint`) includes it — read directly.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: pyproject.toml:98 lint = ruff check marketplace/bundles/ marketplace/targets/ test/ .claude/ (includes targets); :100-101 fmt/format = ruff format marketplace/bundles/ test/ .claude/ (omit targets) - line numbers shifted from the claim's :75/:100-101 but the omission holds
- OBSERVED: `build.py`'s full-tree path set is `[BUNDLES_DIR, TARGETS_DIR, TEST_DIR, CLAUDE_DIR]` and both ruff halves run over it — read at `build.py` § `cmd_quality_gate`. ⭐ This means the hard rule shipped in #1461 is ACCURATE about the gate; the `format` alias is the outlier.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: build.py:670 paths=[BUNDLES_DIR,TARGETS_DIR,TEST_DIR,CLAUDE_DIR]; :682 ruff check --fix and :688 ruff format run over it - the gate path set matches the claim
- HYPOTHESIS: `CROSSING-INVENTORY.md` is superseded rather than live — confirm/refute by reading it and searching for references before disposing of it (verify-at-outline). ⛔ An asserted absence of references is verified exactly like an asserted presence.
  - verdict: unverifiable | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: whether CROSSING-INVENTORY.md is superseded vs live requires reading its content and reference-scanning - the verifying phase owns that disposition decision; presence is corroborated but superseded-ness is not settleable from a file listing alone

## Expected Surface

- OBSERVED: `CROSSING-INVENTORY.md` — D1
- OBSERVED: `pyproject.toml` — D2
- HYPOTHESIS: `build.py` — only if D2 concludes the gate rather than the alias should change (verify-at-outline; the evidence so far says the alias is the outlier)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: **nothing in this epic.** That disjointness is the plan's operational purpose.
- Adjacent to: the quality gate's own behaviour, which D2 does not change — it aligns an alias to it.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/tooling-truthfulness/plans/PLAN-02-repo-hygiene-residues.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO file under
`.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
