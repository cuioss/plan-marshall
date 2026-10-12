envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-12T13:53:24Z

# Lessons ingest: Java skill profiles attach Quarkus, CDI and Weld skills to modules that cannot use them, and miss cui-testing

Severity: medium. Bundle: **domain content** — `pm-dev-java` (`skills/plan-marshall-plugin/extension.py` profile metadata) and `pm-dev-java-cui` (`plan-marshall-plugin`), with the `plan-marshall` `phase-4-plan` persona union as the consumer. Filed under RULING 2026-10-09 (b): domain-bundle content at any severity.

Source: pm-mcp-core epic `pm-mcp-core-m2-m4`, five plans; pm-mcp-core's enforcer bans Quarkus/CDI in every module. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/`.

| Message | Plan | Statement |
|---|---|---|
| `pm-mcp-core-m2-m4-010` | #18 | `java-quarkus`, `java-cdi` attached to `pm-core` tasks; task text had to say "ignore any loaded framework skill". |
| `pm-mcp-core-m2-m4-076` | #27 | Same. |
| `pm-mcp-core-m2-m4-088` | #31 | Also `junit-weld-testing`; and `pm-dev-java-cui:cui-testing` NOT attached although the project's test rules require it. |
| `pm-mcp-core-m2-m4-114` | #29 | Every Java task; token cost and pull toward forbidden patterns. |
| `pm-mcp-core-m2-m4-118` | #32 | Orchestrator pruned by hand, incl. `junit-integration` for a module with no ITs. |

Ground truth at `fc0090a24`: `pm-dev-java/skills/plan-marshall-plugin/extension.py` declares `java-quarkus` (architecture, implementation, module_testing), `java-cdi` and `junit-weld-testing` as optionals; only `java-cdi` and `java-lombok` are dependency-gated (`:173-184`, on `jakarta.enterprise` / `lombok`). `java-quarkus`, `junit-weld-testing` and `junit-integration` have no dependency gate, and a dep-absent CDI is demoted to optional rather than dropped. **Still present.**

Asked for: gate `java-quarkus` on `io.quarkus`, `junit-weld-testing` on Weld/CDI, `junit-integration` on an IT profile or IT sources, and drop (not merely demote) a skill whose dependency is absent; have `pm-dev-java-cui` attach `cui-testing` when the module's test scope uses `cui-test-generator` / `cui-test-juli-logger`; check whether the phase-4 persona union promotes optionals unconditionally.

Owner today: none found.
