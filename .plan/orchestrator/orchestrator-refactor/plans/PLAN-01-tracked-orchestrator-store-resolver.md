# PLAN-01: The orchestrator store resolves to a git-tracked, repo-local address

epic: orchestrator-refactor
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-01-tracked-orchestrator-store-resolver.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never launches
> the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Move the orchestrator ledger's *address* from the machine-local, git-ignored
`.plan/local/orchestrator/{name}/` to the shared, git-tracked `.plan/orchestrator/{name}/`,
by adding one resolver tier and one `.gitignore` negation — and by changing nothing else.
This plan does NOT restructure the files inside the tree (PLAN-02) and does NOT rename any
identifier (WS-03). Its whole deliverable is: the same bytes, at a new address, reachable
identically from every worktree and from a fresh clone. The point is cross-machine and
cross-session shareability: two operators on two checkouts work the same epic today only by
accident, because the ledger exists on exactly one machine and is excluded from every PR.

## Deliverables

1. **D0 — derive the reference population.** Enumerate every path-string reference to the
   old address across the WHOLE working tree, not just the marketplace-inventoried subset.
   Publish the method, the count, and the trees walked. State which references are code,
   which are test, which are prose, and which are inside `.plan/` itself (and therefore move
   with the tree).
2. **D1 — the resolver tier.** One new resolver for the tracked orchestrator address,
   honouring the same override precedence as its siblings. Containment
   (`_reject_unsafe_entry_id`) stays at the shared resolver per ADR-016; no entry point
   re-validates.
3. **D2 — `get_store_dir` routes there**, with `get_archived_orchestrator_dir` following, and
   the `allow_archived` read-fallback semantics preserved exactly.
4. **D3 — the `.gitignore` negation**, mirroring the existing `!.plan/project-architecture/`
   line, plus whatever exclusion the tree needs for genuinely machine-local sub-paths
   (`logs/`, `cloud-runs/` — decide per-subdirectory and record the decision, do not default).
5. **D4 — `archive` becomes git-aware.** A relocation of a tracked tree must leave the index
   in a state a commit can carry (today `orchestrator.py:1799` uses `shutil.move`).
6. **D5 — the layout contract and the resolver docstrings tell the truth.** The bounded
   main-resident corpus list in `resolve_main_anchored_path`'s docstring no longer names
   `orchestrator`; `orchestration-model.md` § Directory Layout shows the new address.
7. **D6 — an ADR**, because this amends ADR-002's bounded main-anchored exception set.

## Non-Goals

- No file inside the tree changes shape. No `status.json` field moves. No `epic.md` section
  moves. (PLAN-02's job.)
- No identifier is renamed. (WS-03's job.)
- No compatibility shim is built here — the old address stops resolving, or it does not, and
  that decision is WS-02's sibling migration-mechanism plan's, taken against the
  four-condition checklist at `phase-3-outline/standards/outline-workflow-detail.md:815-829`.

## Claim Labels

- OBSERVED — `marketplace_paths.py:660` composes `main_root / PLAN_DIR_NAME / 'local' / subpath`;
  `.plan/local` is hard-coded at exactly one line, inside `resolve_main_anchored_path`.
- OBSERVED — `file_ops.py:581-642` (`get_store_dir`) is the single choke point for the
  orchestrator store, with `_reject_unsafe_entry_id` containment already applied there, and
  `file_ops.py:645-672` (`get_archived_orchestrator_dir`) is its archived sibling.
- OBSERVED — `.gitignore:45-47` reads `.plan/*` / `!.plan/marshal.json` /
  `!.plan/project-architecture/`; `git ls-files .plan` returns 14 tracked files, proving a
  git-tracked directory under `.plan/` already works.
- OBSERVED — `file_ops.py:1376-1411` (`get_tracked_config_dir` / `get_marshal_path`) is an
  already-existing repo-local resolver for the tracked half of `.plan/`, with its own
  `PLAN_TRACKED_CONFIG_DIR` override and cwd-upward-walk fallback.
- OBSERVED — `.plan/project-architecture/` is an existing git-tracked, one-file-per-module
  directory (13 files, 62,748 B) — a working precedent for both the resolver shape and the
  per-concern split PLAN-02 will use.
- OBSERVED — the complete consumer set of `get_store_dir(` / `get_archived_orchestrator_dir(`
  is 11 source files / 26 call sites in the marketplace inventory (`architecture search
  --content`, `--category source`, `files_scanned: 476`), one of which is cross-bundle:
  `pm-plugin-development/.../epic-surface-partition.py:132`.
- OBSERVED — `orchestrator.py:1799` performs the archive relocation with `shutil.move`, not a
  git-aware move; the largest archived tree measured on this machine is 599 files
  (`lessons-handling-26-08-08-01`).
- OBSERVED — 87 literal references to `.plan/local/orchestrator` / `archived-orchestrators`
  exist across 48 files in the marketplace inventory (7 source, 13 test, 28 doc) — a FLOOR,
  scoped to the inventoried tree only (excludes `.claude/**`, `.github/**`, anything
  `.gitignore`d).
- HYPOTHESIS — a repo-local tracked resolver is correct and a main-anchored one is not,
  because every linked worktree is the same repository and therefore carries the same
  tracked tree; confirm/refute at `marketplace_paths.py` § `resolve_main_anchored_path`
  against `file_ops.py` § `get_tracked_config_dir`, and against
  `git -C <worktree> ls-files .plan` (verify-at-outline).
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: file_ops.py:597-602,637 get_store_dir routes orchestrator via get_tracked_config_dir, never main-anchored; marketplace_paths.py:640-641 documents this; ADR-024 (Proposed) records the decision; git ls-files .plan/orchestrator/truthful-signals/plans/ = 44 tracked specs. Residual: _status_core.py:496-498 still comments ADR-002/main-anchored, now stale.
- HYPOTHESIS — the `PLAN_BASE_DIR` / `set_base_dir()` test-override precedence
  (`marketplace_paths.py:648-655`) must be mirrored in the new tier or every existing
  override-based test breaks; confirm/refute at
  `test/plan-marshall/script-shared/test_marketplace_paths.py` and
  `test/plan-marshall/tools-file-ops/test_store_root.py` (verify-at-outline).
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: get_tracked_config_dir():1397-1404 honours set_base_dir() override then PLAN_TRACKED_CONFIG_DIR then PLAN_BASE_DIR then cwd walk-up; get_store_dir routes every orchestrator resolution through it at :637. Both cited tests survive plus a new test_tracked_orchestrator_gitignore.py.
- HYPOTHESIS — `shutil.move` over a tracked tree leaves an unstaged delete+add of every file;
  confirm/refute at `orchestrator.py` § `cmd_archive` with a fixture epic under git
  (verify-at-outline).
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: orchestrator.py _relocate_epic_tree (now at :1908-1955) docstring states a plain move leaves a whole-tree delete+add unreadable as one rename; D4 shipped: git mv subprocess at :1932-1938, shutil.move retained only as documented fallback at :1955. cmd_archive now begins at :1958 and calls _relocate_epic_tree at :2010 (the claim's original :1799 citation is stale, lines shifted).
- Verify-first clause: re-derive the D0 reference population against the FULL working tree
  (not the inventory-scoped 87/48 figures above, which explicitly exclude `.claude/**`,
  `.github/**`, and `.gitignore`d paths) before scoping the edit set.
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: orchestrator-refactor/cleanup | rescoped: n/a | evidence: architecture search --content .plan/local/orchestrator returns count:16/file_count:11 but MISSES .plan/orchestrator/truthful-signals/plans/PLAN-TRUTH-146*.md:31,33 (tracked-but-uninventoried), proving the inventory sweep is narrower than the working tree, exactly as the clause warns. Residual old-address hits at HEAD: SKILL.md(2), _orchestrator_inbox.py(2), 3 test files(5), doc/analyzis-cloud-plan/*(14).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-file-ops/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-orchestrator/standards/orchestration-model.md`
- OBSERVED: `.gitignore`
- OBSERVED: `doc/adr/`
- OBSERVED: `test/plan-marshall/script-shared/test_marketplace_paths.py`
- OBSERVED: `test/plan-marshall/tools-file-ops/test_store_root.py`
- OBSERVED: `test/plan-marshall/tools-file-ops/test_file_ops.py`

## Dependencies and Sequencing

- Depends on: none — this is the epic's foundational plan, staged first in its workstream
  and, of the whole epic's corpus, the one every other candidate either depends on or
  collides with.
- Overlaps with: PLAN-02 (`orchestrator.py`, `orchestration-model.md` — PLAN-02 assumes this
  plan has landed, land this one first); PLAN-03 (`marketplace_paths.py` — PLAN-03's redirect
  primitive extends the resolver tier this plan creates, land this one first); PLAN-07
  (`orchestrator.py` — sequence PLAN-07 last, after this plan).
- Adjacent to: `lessons-routing` PLAN-LR-04 (staged, sibling epic) states the same
  git-ignored-store durability problem in its Vision; its Expected Surface is `prose` (0
  resolved paths), so the disjointness gate cannot see this overlap. If PLAN-LR-04 reaches
  for a durability substrate before this plan lands, check its spec body by hand.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/orchestrator-refactor/plans/PLAN-01-tracked-orchestrator-store-resolver.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
