> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# No general script renders Claude permission grammar or hardcodes the `.claude/` layout

**Epic:** multiplattform (standalone — no orchestrator ledger; scoping brief in
`doc/plans/multiplattform/README.md`, evidence in `doc/plans/multiplattform/reference/` — full
paths, because the lane moves this plan one directory deeper and relative links would dangle)
**Branch prefix:** chore — closing coupling residue in existing scripts, no new capability

## Problem

The permission tooling, credential protection, extension discovery, and two bookkeeping scripts
still carry live Claude literals outside the sanctioned homes — the residue
`doc/plans/multiplattform/reference/coupling-inventory.md` §B registers (this plan draws the five
clusters below; the inventory holds further §B entries not scoped here):

- `tools-permission-fix/scripts/permission_fix.py` — `DEFAULT_PERMISSIONS` carries the literal
  permission string `Read(~/.claude/plugins/cache/**)`; the Claude permission grammar is rendered
  in a general script instead of inside `claude_runtime`.
- `tools-permission-doctor/scripts/permission_common.py` — `get_project_settings_path` (the read
  path) inlines `.claude/settings.local.json` / `.claude/settings.json` while the write path
  delegates to the runtime, and the module docstring claims a full delegation the read path does
  not perform — a false claim in code.
- `manage-providers/scripts/_cred_ensure_denied.py` — renders Claude `permissions.deny` DSL
  strings (`Read(...)`, `Bash(...)` over `_BASH_VECTORS`) and writes them into the host settings
  file; the same grammar-in-core class.
- `extension-api/scripts/extension_discovery.py` — `_scan_project_for_implementors` builds
  `project_root / '.claude' / 'skills'` segment-wise instead of routing through
  `get_project_skill_roots()`, so project-local finalize-step implementors resolve only on the
  Claude layout.
- Display/filter residue: `tools-marketplace-inventory/scripts/scan-marketplace-inventory.py`
  builds a `./.claude/skills/…` `runtime_mount` display string, and
  `plan-retrospective/scripts/check-manifest-consistency.py` + `check-routing-decisions.py` name
  `.claude/` inside `_BOOKKEEPING_PREFIXES`.

## Goal

The Claude permission grammar and the `.claude/` layout are rendered and resolved only inside
`platform-runtime` (and the memoised layout helpers that wrap it); the scripts above state
intent, consume resolved values, and behave identically on the Claude target.

## Deliverables

1. **D1 — Default permissions render in the runtime** — the Claude-cache read permission that
   `DEFAULT_PERMISSIONS` encodes moves behind `platform-runtime`: the runtime renders the
   `Read(...)` string from the resolved bundle-cache root, and `permission_fix.py` consumes the
   rendered value instead of embedding it.
   *Done when:* no `.claude/` literal remains in `permission_fix.py`; the emitted default set on
   Claude is byte-identical to before, pinned by test.
2. **D2 — Settings-path reads delegate** — `permission_common.py`'s read-preference selector
   delegates to the same runtime path resolution the write path uses, and the module docstring
   matches what the module actually does.
   *Done when:* no `.claude/settings` literal remains in `permission_common.py`; read-preference
   behaviour (prefer `settings.local.json`, fall back to `settings.json`) is pinned by test; the
   docstring's delegation claim is true.
3. **D3 — Credential deny rules render in the runtime** — the deny-rule strings
   `_cred_ensure_denied.py` builds are rendered inside `platform-runtime` (behind the existing
   permission-op surface or a Claude-runtime rendering helper — the constraint is *where the
   grammar lives*, not the exact routing); the caller passes intent (protect the credential
   directory) and handles a `no-op` on targets without a permission backend.
   *Done when:* no `Read(`/`Bash(` permission-DSL string construction remains in
   `_cred_ensure_denied.py`; the rules written on Claude are semantically identical to before,
   pinned by test; a non-Claude runtime path degrades to `no-op` without error.
4. **D4 — Implementor scan routes through layout resolution** —
   `_scan_project_for_implementors` iterates `get_project_skill_roots()` instead of constructing
   `.claude/skills` segment-wise.
   *Done when:* no segment-wise `.claude` construction remains in the function; a test covers
   discovery through a non-default root list.
5. **D5 — Display and filter strings stop naming `.claude/`** — the `runtime_mount` display
   string derives from the resolved skill root, and `_BOOKKEEPING_PREFIXES` derives its
   project-local entry from the layout helpers (or is reworded to a layout-neutral predicate) in
   both retrospective scripts.
   *Done when:* no hardcoded `.claude/` remains in the three files; existing behaviour on Claude
   is unchanged, pinned by the scripts' existing tests.

## Out of scope

- **The OpenCode permission backend** — the honest `no-op` the OpenCode runtime returns for
  permission ops is correct per the no-op policy; implementing a real backend is validation-gated
  work (`doc/plans/multiplattform/reference/opencode-validation-protocol.md`), and building it
  here would be speculation about an unvalidated runtime.
- **The permission-grammar knowledge in `permission_doctor.py`'s analysis rules and the
  permission standards documents** — the doctor *analyzes* Claude settings as its subject matter;
  relocating analysis rules is rule-pack work of a different kind than closing live render/resolve
  residue, and folding it in would triple the surface.
- **`HARNESS_BASH_CEILING_SECONDS` and the `manage-files` IDE launch** — inventory §C entries with
  different shapes (a runtime-sourced value; a per-host capability); each needs its own design
  and neither is a `.claude/` literal.
- **Runtime ABC/registration changes** — plan `010` owns `runtime_base.py` and
  `platform_runtime.py`; this plan adds no operation and changes no contract shape.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/tools-permission-fix/scripts/permission_fix.py` — D1
- `marketplace/bundles/plan-marshall/skills/tools-permission-doctor/scripts/permission_common.py` — D2
- `marketplace/bundles/plan-marshall/skills/manage-providers/scripts/_cred_ensure_denied.py` — D3
- `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/claude_runtime.py`,
  `_claude_runtime_impl.py` — D1/D3 rendering moves in
- `marketplace/bundles/plan-marshall/skills/platform-runtime/standards/contract.md` — only if
  D1/D3 need a minimal schema addition (the claim table's hypothesis); otherwise untouched
- `marketplace/bundles/plan-marshall/skills/extension-api/scripts/extension_discovery.py` — D4
- `marketplace/bundles/pm-plugin-development/skills/tools-marketplace-inventory/scripts/scan-marketplace-inventory.py` — D5
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-manifest-consistency.py`,
  `check-routing-decisions.py` — D5
- The corresponding `test/` subtrees for each script above

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `DEFAULT_PERMISSIONS` carries `Read(~/.claude/plugins/cache/**)` | OBSERVED | `permission_fix.py` — `DEFAULT_PERMISSIONS`; locate by symbol |
| `get_project_settings_path` inlines `.claude/settings*.json` on the read path while the write path delegates | OBSERVED | `permission_common.py` — `get_project_settings_path` vs `get_project_settings_path_for_write` |
| `_cred_ensure_denied.py` renders `Read(...)`/`Bash(...)` deny strings over `_BASH_VECTORS` | OBSERVED | the file — `_BASH_VECTORS` and the rule-building block |
| The segment-wise `.claude` construction sits in `_scan_project_for_implementors` | OBSERVED | `extension_discovery.py` — `_scan_project_for_implementors` |
| `runtime_mount` and `_BOOKKEEPING_PREFIXES` are the remaining display/filter literals | OBSERVED, set is a lead | re-derive the full residual set before starting: sweep `marketplace/bundles/**` scripts for `.claude` literals (both quote styles, segment-wise included), discard `platform-runtime` internals and the sanctioned multi-root resolvers; anything beyond the five clusters above (seven files — the fifth cluster spans three) is reported, not silently adopted or skipped |
| `get_project_skill_roots()` / `get_bundle_cache_roots()` exist memoised in `script-shared/scripts/marketplace_paths.py` and are the mandated route | OBSERVED | `marketplace_paths.py` — the two helpers and their cache constants |
| The existing permission-op TOON contract can carry D1/D3 without a schema change | HYPOTHESIS | `platform-runtime/standards/contract.md` — the permission-op schemas; a needed schema addition is recorded in the report and made minimally, not silently |

## Verification

- `./pw verify` over the branch diff (Python changes — the build gate applies).
- Per-deliverable behaviour pins demonstrated red-first where they encode current output
  (D1's default set, D3's rule set).
- The residual sweep from the claim table, re-run at verification time over the changed tree: the
  seven files across the five clusters are clean and no new literal was introduced by the fixes
  themselves.
- The pre-PR verification sub-agent checks each deliverable against this plan and sweeps the
  changed values' consumers by kind — prose restating the settings paths, tests stubbing the old
  literal strings, and the permission standards' worked examples are the known consumer kinds.

## Notes

- D1 and D3 move rendering *into* `platform-runtime`; plan `010` reshapes contracts in the same
  files, so the two plans must not run concurrently — see the epic README's concurrency table.
- D2's false module docstring is itself a defect to fix, not just collateral: a stated delegation
  that does not exist is the stale-claim class this repository's standards exist to prevent.
- The doctor/standards knowledge excluded above is registered in
  `doc/plans/multiplattform/reference/coupling-inventory.md` §B (permission-grammar analysis
  rules and standards) so it is not lost by the exclusion.
