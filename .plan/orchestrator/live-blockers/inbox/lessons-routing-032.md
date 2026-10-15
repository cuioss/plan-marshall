envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-15T12:33:53Z

# Lessons ingest: deep-lane outline written without the assessment pass (recurrence of -022)

Severity: high (prior ruling: deep-lane no assessments = high; recurrence of `lessons-routing-022`, amended by `-028` and message 191). Bundle: `plan-marshall` (`phase-3-outline` deep lane, Q-Gate assessment coverage 2.2).

Source: pm-mcp-core epic `pm-mcp-core-m2-m4` inbox messages `-203`..`-286`. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/`.

| Message | Statement |
|---|---|
| `pm-mcp-core-m2-m4-212` | 26-path outline shipped zero `CERTAIN_INCLUDE` assessments. |
| `pm-mcp-core-m2-m4-226` | Deep outline lane recorded no assessments; flags all files, always accepted. |
| `pm-mcp-core-m2-m4-238` | Duplicate of 226: zero assessments, all deliverables flagged. |
| `pm-mcp-core-m2-m4-248` | Deep-lane outline skipped component assessments. |
| `pm-mcp-core-m2-m4-266` | Deep outline lacked assessments before Q-Gate. |
| `pm-mcp-core-m2-m4-274` | Outline authored without the assessment pass; revision repeated the gap. |

Asked for: same as `-022` (record assessments as the set settles, or refuse with an empty store; check 2.2 reports its own outcome). Six further recurrences since `-028` was amended with message 191.

Owner today: none (nearest: `-022`). Not re-checked at HEAD by the ingest.
