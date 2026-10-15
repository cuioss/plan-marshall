envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-15T12:45:11Z

# Lessons ingest: outline assessments miss files, lack backing, and outlive refuted designs

Severity: high (under-coverage class fired repeatedly inside one outline). Bundle: `plan-marshall` (`phase-3-outline` assessments, Q-Gate coverage).

Source: API-Sheriff plan `32-early-answer-it-timeouts` (PR cuioss/API-Sheriff#466), messages `-001`..`-003`. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/`.

| Message | Statement |
|---|---|
| `api-sheriff-kidicap-gateway-requirements-001` | Success criteria cited files missing from the affected lists (under-coverage fired twice, D1 then D3). |
| `api-sheriff-kidicap-gateway-requirements-002` | Affected files added without assessment, or backed only by `CERTAIN_EXCLUDE` (recurred 3x in one outline). |
| `api-sheriff-kidicap-gateway-requirements-003` | Assessments outlived a refuted design and contradicted re-outlined deliverables (fired twice across two re-outline rounds). |

Asked for: affected lists cover the criteria's files, every listed file carries a backing assessment, and re-outline drops assessments of the refuted design.

Owner today: none. Not re-checked at HEAD by the ingest.
