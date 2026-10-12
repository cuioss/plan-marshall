envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-12T13:53:23Z

# Lessons ingest: the deep-lane outline writes no assessments, so Q-Gate assessment coverage fails every deliverable

Severity: high (operator decision at this ingest, 2026-10-12: one guaranteed operator interruption per deep-lane plan). Bundle: `plan-marshall` (`phase-3-outline` deep lane, `plan-marshall/workflow/q-gate-validation.md` check 2.2, `manage-findings` assessment store).

Source: pm-mcp-core epic `pm-mcp-core-m2-m4`, eight plans. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/`.

| Message | Plan | Statement |
|---|---|---|
| `pm-mcp-core-m2-m4-001` | #18, #19 | 0 assessments (`findings_store_state: missing`); check flags 34 write + 4 read paths; outline phase closed "Q-Gate: pass" before validation ran; the stored detail also miscounts new files (26 vs 21). |
| `pm-mcp-core-m2-m4-040` | #25 | Java deep-lane path records none for 22 files; operator acceptance. |
| `pm-mcp-core-m2-m4-050` | #26 | 13 deliverables; "this outline lane produces no per-file assessments". |
| `pm-mcp-core-m2-m4-057` | #28 | 12 files; a complete content sweep over 302 files corroborated the set, yet no assessment written. |
| `pm-mcp-core-m2-m4-074` | #27 | Re-entry wrote none for 73 files; operator required a fix pass (72 recorded). |
| `pm-mcp-core-m2-m4-091` | #31 | Evidence only in `work/trace-matrix.md`; 22 recorded afterwards. |
| `pm-mcp-core-m2-m4-097` | #29 | "0 passed, 11 flagged" on this alone. |
| `pm-mcp-core-m2-m4-123` | #32 | No domain outline skill applied (`no_domain_skill`); greenfield package; also starves outline-vs-shipped. |

Asked for: the deep lane records a `CERTAIN_INCLUDE` assessment for each affected file as it settles the set, on every pass including re-entries (write-new files exempt or marked), or refuses to return with an empty store; check 2.2 reports `not run, no assessments recorded` as its own outcome rather than a pending finding.

Owner today: none found. Not re-checked at HEAD by the ingest.
