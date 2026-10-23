envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:03Z

component=plan-marshall:phase-3-outline
category=anti-pattern

# Removing an enum constant in one deliverable while a shipped resource still names it until a later one

Source: Q-Gate 4-plan finding 9bd12c (resolved in run, taken_into_account by an outline loop-back), plan plan-70-plan-instance-alignment.

D3 removed `PruneReason.RECIPE_OVERRIDE` and `AUTO_MERGE_OFF`, but the shipped `composition-rules.json` - loaded through `PruneReason.fromWireName` - kept naming `recipe_override` / `auto_merge_off` until D5, which depended on D3. Every module test of the intermediate tasks that loads the shipped rules would have been red.

## Rule

A removal deliverable must carry every consumer of the removed symbol in the same change - code, shipped resources keyed by its wire name, and tests. When sweeping, search for BOTH spellings (the Java constant `AUTO_MERGE_OFF` and the wire name `auto_merge_off`). Sibling finding bfe299 is the test-file half of the same miss.
