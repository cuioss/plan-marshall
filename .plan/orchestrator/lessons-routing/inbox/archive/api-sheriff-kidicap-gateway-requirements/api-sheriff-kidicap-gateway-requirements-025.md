envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=finding
created=2026-11-24T12:06:31Z

> Routed from API-Sheriff epic `kidicap-gateway-requirements` (repository cuioss/API-Sheriff) by its orchestrator on 2026-11-24, at the operator's direction ("move all plan-marshall related stuff" to this inbox). Facts below come from that epic's ledger unless a line says it was re-read in this run; plugin version in use there: 0.1.2184.

# finding: the three-layer leaf's read-only instruction does not keep `grep -r` out of `.plan/`

Observation (2026-11-24, `analyze` of PLAN-33, one `execution-context-level-3` leaf per `standards/three-layer-analysis.md`): the leaf's report disclosed that one `grep -r` sweep for stale `invalid_scope` wording walked into `.plan/` and printed one line of the staged spec copy, although the prompt body said never to open a `.plan/` path and the leaf opened none on purpose. The disclosure was honest and the line only repeated the spec premise already passed as data, so nothing leaked, but the S1 instruction names "paths" and a recursive search crosses them.

Suggestion: in `three-layer-analysis.md`, tell the leaf to scope every recursive search to the source directories it names (or to pass `--exclude-dir=.plan`), not only to refrain from opening `.plan/` files.

Component hint: `plan-marshall:plan-orchestrator` `standards/three-layer-analysis.md`.
