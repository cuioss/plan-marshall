envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-15T12:45:20Z

# Lessons ingest: staged diagnose-then-fix plans have no declared task deferral

Severity: high (8 coverage/closure findings accepted by hand for want of a deferral). Bundle: `plan-marshall` (`phase-4-plan` task planning).

Source: API-Sheriff plan `32-early-answer-it-timeouts` (PR cuioss/API-Sheriff#466), message `-005`. Full body: `lessons-routing/lessons-archive/filed-live-blockers/api-sheriff-kidicap-gateway-requirements-005.md`.

| Message | Statement |
|---|---|
| `api-sheriff-kidicap-gateway-requirements-005` | Staged (diagnose-then-fix) plans have no declared task deferral; the plan drew 8 hand-accepted coverage/closure findings. |

Asked for: a first-class declared deferral for staged plans, so diagnose-phase findings do not need hand acceptance.

Owner today: none. Not re-checked at HEAD by the ingest.
