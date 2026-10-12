envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-12T13:53:21Z

# Lessons ingest: a deliverable in a sibling repository has no lifecycle — no worktree, no push/PR step, no footprint, and the foreign-PR gate both blocks and misses

Severity: **critical** for the Antigravity instance (operator ruling 2026-10-12), high otherwise (operator decision at this ingest, 2026-10-12). Bundle: `plan-marshall` (`phase-3-outline`, `phase-4-plan`, `phase-6-finalize` incl. `scripts/foreign_pr_gate.py`, `manage-references` footprint, `plan-retrospective`, `tools-integration-ci`, `execution-context` content-search contract).

Source: pm-mcp-core epic `pm-mcp-core-m2-m4`; every plan that changes a specification must also change `plan-marshall-documentation`, so this recurs on every plan. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/`.

**Gate defects (still present at `fc0090a24`):**

| Message | Statement |
|---|---|
| `pm-mcp-core-m2-m4-129` | PLAN-41 (#34), Antigravity: the documentation deliverable vanished — no PR in `plan-marshall-documentation`, the landing does not mention it, the foreign-PR archive gate did not object. |
| `pm-mcp-core-m2-m4-082` | PLAN-07 (#27): the foreign-PR gate assumes the foreign branch is `feature/{plan_id}`; the outline used `docs/…`; the gate failed closed (`foreign_landing_indeterminate`) on a merged foreign PR; archive needed operator authorisation. Verified: `foreign_pr_gate.py:170-171` returns `f'feature/{plan_id}'`. |

**Lifecycle gaps:**

| Messages | Gap |
|---|---|
| `-009`, `-052`, `-073`, `-112` | No finalize step pushes the sibling branch or opens its PR (ci has no repository target); docs branches were left unpushed or opened by hand / raw `gh`. |
| `-055` | No phase provisions a plan-owned sibling worktree; execute blocked on a checkout on another plan's branch. |
| `-048`, `-090`, `-100` | `../sibling` paths break inside the plan worktree; a tool that defaults its root from cwd checks the wrong tree and passes vacuously. |
| `-015`, `-045`, `-078`, `-096`, `-122` | The footprint resolver reads only the plan's repository, so shipped sibling files grade as unrealised (recall, M6, outline-vs-shipped, request alignment). |
| `-093` | Leaves have no sanctioned content search outside the inventory and fell back to `git grep`. |

Asked for: a first-class companion-repository declaration (repo, branch, worktree) recorded in plan metadata; provisioning and cleanup of that worktree; a finalize step that pushes it and opens/links its PR after `create-pr`; the foreign-PR gate takes the branch or PR from that declaration and fails closed when a declared sibling deliverable has no recorded PR; the footprint treats out-of-repo paths as their own population.

Owner today: none found.
