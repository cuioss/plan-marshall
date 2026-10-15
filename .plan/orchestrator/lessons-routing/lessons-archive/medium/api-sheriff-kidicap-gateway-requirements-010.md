envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T12:24:56Z

# Candidate lesson: ci router argparse rejections when free text reaches `ci checks logs` (tools-integration-ci)

Forwarded from API-Sheriff epic `kidicap-gateway-requirements`, plan `plan-32-early-answer-it-timeouts` (PR cuioss/API-Sheriff#466).

Source message: 022 (script-failure cluster, 3 argparse_rejection lines in 11 s during 5-execute TASK-10).

## Observation

- `unrecognized arguments: run:`: a `run:` label copied from earlier output was passed as an argument.
- `checks logs: --match: expected one argument`: an empty, unquoted or dash-leading value.
- `unrecognized arguments: out`: free text split into separate arguments.

The executor recovered.

## Candidate rule

Pass `--match` as one single-quoted, non-empty value (`--match='<text>'` if it may start with `-`), and `--run-id` as the bare numeric id. A doc example or a friendlier error that names the offending token would prevent the retry loop.
