envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=lessons-routing
kind=finding
created=2026-10-27T05:55:20Z

# The architecture inventory does not index YAML, JSON or workflow files, so a carrier sweep over it is incomplete

Source: API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-20-cookie-key-file-model (PR #527), candidate lesson 002. Observed with plugin and executor 0.1.2010.

## Observation

While retiring a configuration key, `architecture find '*.yaml'` returned 0 files and `architecture search --content` missed `gateway.schema.json` and a test-resource `gateway.yaml`, both of which carried the key. The outline's carrier search therefore did not cover test and main resources, workflows, benchmarks, deployment or the demo client. A tracked-file sweep outside the inventory found one more carrier, a `.github/workflows` file that set the retired environment variable.

## What to consider

- State in the outline and `manage-architecture` docs that the inventory does not walk `*.yaml`, `*.yml`, `*.json` or `.github/**`, so a removal outline adds an explicit tracked-file sweep for non-inventoried carriers.
- Or index those file types, at least for content search.
