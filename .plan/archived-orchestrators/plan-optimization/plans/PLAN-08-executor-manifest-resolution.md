# PLAN-08: executor-manifest-resolution (staleness fail-open)

epic: plan-optimization
workstream: WS-03

> Staged plan spec. Consumer-surfaced (marketplace install) + **INDEPENDENTLY VERIFIED against
> upstream source by the orchestrator, 2026-07-18** — confirmed defect, not an unverified lead.
> Re-ground file:line citations at outline.

## Objective

Fix the executor version-stamp regression whose real root cause is an unresolvable
`dist-manifest.json` on marketplace-cache installs. When plan-marshall is installed through a Claude
Code marketplace, the manifest lives at the marketplace CLONE root
(`~/.claude/plugins/marketplaces/<mp>/dist-manifest.json`), which the resolver never searches — so it
returns `None`, the executor is stamped `MARSHALL_VERSION = ''`, and `sync-defaults` then overwrites
a known-good `system.provisioned_version` with the empty sentinel. The deeper harm: version-based
staleness then **fails open** — `installed_version` is unknown, every comparison degenerates to the
empty sentinel, `marshal_status: fresh` is vacuously true, and the executor-staleness check the
Re-Run Remediation Pass depends on is silently inert.

## Deliverables

### D1 — resolver must search the marketplace clone root (root cause)

**Verified:** `find_installed_manifest_path` (`generate_executor.py:1085`) candidate list (`:1119-1121`)
= (1) meta-project target tree, (2) `base_path/dist-manifest.json`, (3) `base_path.parent/...` — plus
`$PM_DIST_MANIFEST`. The marketplace clone root is NOT a candidate. Docstring `:1089` asserts the
manifest "rides into the plugin cache on install" — false for marketplace installs. **Fix:** add the
marketplace clone root to the candidate list, derived by mapping
`.../plugins/cache/<marketplace>` → `.../plugins/marketplaces/<marketplace>`. **Acceptance:** on a
cache-install layout with the manifest only at the marketplaces clone root, the resolver returns it;
the executor stamps the real version.

### D2 — `stamp_provisioning_fields` must be non-destructive on an empty read (defense in depth)

**Verified:** `read_provisioned_version` (`_config_defaults.py:1114`) returns `''` when the executor is
absent/unstamped (`:1120-1121,1134,1138`); `stamp_provisioning_fields` (`:1141`) unconditionally
assigns `system['provisioned_version'] = read_provisioned_version()` (`:1159`), overwriting a
known-good value with `''`. **Fix:** when `read_provisioned_version()` returns `''`, LEAVE any existing
`provisioned_version` intact rather than blanking it. **Acceptance:** a sync-defaults run with an
unstamped executor preserves an existing `provisioned_version` (e.g. `0.1.1116`) instead of writing
`''`; a real version still advances it.

### D3 — unresolvable manifest must fail CLOSED (surface, don't swallow)

The current silent-`None`→empty-sentinel path makes staleness report "everything current" precisely
when it cannot tell. **Fix:** surface an unresolvable manifest as an explicit warning (and/or make
`marshal_status` refuse to report `fresh` when `installed_version` is unknown) so the subsystem fails
closed. **Acceptance:** a run with no resolvable manifest emits a legible warning and does NOT report
a vacuous `fresh`.

## Expected Surface

- `tools-script-executor/scripts/generate_executor.py` (`find_installed_manifest_path`)
- `manage-config/scripts/_config_defaults.py` (`stamp_provisioning_fields`, and the `marshal_status`/preflight staleness reporting)
- tests: cache-install fixture (manifest only at marketplaces root) + non-destructive-stamp regression + fail-closed warning

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-07 (WS-03) touches `_cmd_sync_defaults.py` (which CALLS `stamp_provisioning_fields`);
  this plan touches `_config_defaults.py:stamp_provisioning_fields` — adjacent provisioning path,
  different files. Mostly disjoint; coordinate/rebase if both touch the provisioning stamp path.
  Disjoint from PLAN-09 (merge-queue) and the in-flight PLAN-04/05/06.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-08-executor-manifest-resolution.md"
```

## Status Trail

- plan_marshall_plan_id: executor-manifest-resolution
- pr: 934 (MERGED via merge-queue, SQUASH)
- landing: landings/PLAN-08.md
- status: SHIPPED — D1/D2/D3 all delivered; ADR-009 created (fail-closed principle); lesson 2026-07-18-22-001 captured (scoped-gate blind spot)
