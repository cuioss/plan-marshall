envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T18:23:15Z

# Candidate lesson: a missing provider URL surfaces as "HTTPS required when authentication is configured"

Component: plan-marshall:manage-providers (credentials, RestClient)
Category (proposed): bug
Source: plan spend-removal, finalize (script-failure cluster: `sonar fetch_findings`, `credentials verify`)

## Observation

- `sonar fetch_findings` and `credentials verify` both failed with `HTTPS required when authentication is configured` although the token file and the provider entry looked complete (`credentials check`: complete; `credentials list-providers` showed `url: https://sonarcloud.io`).
- The cause was an empty base URL. `get_authenticated_client` reads the URL from `credentials_config.<skill>.url` in `.plan/marshal.json`, then falls back to a `url` field in the credential file. The `providers.<skill>.url` entry that `list-providers` prints is not read. This repository's `marshal.json` has no `credentials_config`, and the credential file held only the token, so the URL was empty; the client's scheme check then reports it as an HTTP-versus-HTTPS problem.
- Earlier plans of the same epic ran the Sonar round trip successfully from another machine, so the data differed there, not the code. The lookup logic is identical in every installed plugin version back to 0.1.1841.

## Proposed correction

- Raise a distinct error when the resolved base URL is empty ("no URL configured for <skill>: expected credentials_config.<key>.url or a url field in the credential file") before the HTTPS check.
- Have `credentials check` report a missing URL as incomplete, and make `list-providers` and the client read the same source, so a printed URL is the URL the client uses.
