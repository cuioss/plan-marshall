envelope_version=1
sender_type=plan
sender_id=plan-v2-86-core-store-tests-b
epic=lessons-routing
kind=candidate-lesson
created=2026-11-06T11:21:31Z

# architecture-refresh flags stale-baseline modules and proposes committing unrelated generated descriptors into a test-only plan

- component: plan-marshall:phase-6-finalize
- category: improvement
- source plan: plan-v2-86-core-store-tests-b (pm-mcp-core, PR 301)

architecture-refresh Tier 0 attributed 12 modules (guard-control-* fixture projects and pm-provider-http) to the plan as module_added (attribution plan_attributable). They already exist on main; only the committed origin/main descriptor is stale. Committing them would have put 13 generated files into a test-only PR and could conflict with parallel plans' _project.json. Modules that are absent only from a stale baseline should be classified as baseline drift, not as the plan's own additions.

Evidence: architecture discover --force --apply plan: delta_classes module_added,plan,12; the operator-side decision discarded the delta (decision log of plan-v2-86-core-store-tests-b, architecture-refresh).
