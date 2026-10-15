envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-15T12:45:37Z

# Lessons ingest: ci-verify triage recurrence (no new item, evidence for -019)

Severity: high (inherited recurrence; no new defect). Bundle: `plan-marshall` (verification-feedback producers, ci-verify triage).

Source: API-Sheriff plan `32-early-answer-it-timeouts` (PR cuioss/API-Sheriff#466), message `-011` (`kind=finding`). Full body: `lessons-routing/lessons-archive/filed-live-blockers/api-sheriff-kidicap-gateway-requirements-011.md`.

| Message | Statement |
|---|---|
| `api-sheriff-kidicap-gateway-requirements-011` | Recurrence of the tracked red-CI-triage item (`lessons-routing-019`, owner PLAN-LB-24): `verification-feedback` still has no producer for the ci-verify caller. |

Asked for: nothing new — recurrence evidence for `-019` / PLAN-LB-24; check whether that row already covers this caller.

Owner today: PLAN-LB-24 (via `-019`). Not re-checked at HEAD by the ingest.
