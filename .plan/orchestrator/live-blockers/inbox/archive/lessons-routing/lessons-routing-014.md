envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-12T13:53:19Z
lifecycle=superseded
superseded_by=lessons-routing-012.md

# Lessons ingest: `build-maven maven run` executes any plugin goal, including one fetched from Maven Central

Severity: **critical** (operator ruling 2026-10-12: Antigravity issues are the highest priority; also a supply-chain gap on every harness). Bundle: `plan-marshall` (`build-maven`), plus the Antigravity target rules.

Source: pm-mcp-core PLAN-41 (PR #34), Antigravity. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/pm-mcp-core-m2-m4-126.md` and `-131.md` (item 4).

| Message | Statement |
|---|---|
| `pm-mcp-core-m2-m4-126` | `spotless:apply` failed (`No plugin found for prefix 'spotless'`); the agent retried with the fully qualified `com.diffplug.spotless:spotless-maven-plugin:apply`, the wrapper ran it, Maven downloaded the plugin from Central, and three formatting commits followed. The project forbids adding a plugin without asking and names `verify -Ppre-commit` as the formatting authority; an ad-hoc plugin also bypasses the `.mvn/rrf` repository filter. |
| `pm-mcp-core-m2-m4-131` (item 4) | Root of the guess: `CLAUDE.md` unread under Antigravity and no target rule requiring `architecture resolve` for formatting. |

Ground truth at `fc0090a24`: no goal or plugin guard found under `marketplace/bundles/plan-marshall/skills/build-maven/scripts/` (searched for an effective-POM / allowed-goal check; none). **Still present.**

Asked for: `maven run` refuses a goal whose plugin is not declared in the effective POM (or not a registered canonical command) unless the operator allows it; formatting resolves to the project's declared quality-gate profile only.

Owner today: none. PLAN-LB-28 (`java-consumer-repos`, partly landed as #1750) touches `build-maven` but not the run guard.
