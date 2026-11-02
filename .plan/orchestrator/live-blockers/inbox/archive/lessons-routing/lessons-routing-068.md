envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-02T10:27:12Z

# Pre-push freshness gate passed on a 5-test build row labelled whole-tree

Severity: **high (operator ruling, 2026-11-02 sweep)** against a medium default: if true, the gate fails open. Bundle: `plan-marshall` (`phase-6-finalize` pre-push freshness check). Residual check against PLAN-LB-58 (#1866, shipped).

## Source

- `api-sheriff-api-sheriff-0-2-0-078` item 2: API-Sheriff plan-v02-48-adr-corpus-cleanup-part-2 (2026-10-30), i.e. after #1866 shipped.

## Observation

The pre-push freshness check passed on a test row covering 5 tests whose label said whole-tree. A targeted run can therefore satisfy a check whose wording claims the whole tree.

## Ground truth

Message text only — one sentence of evidence; the build row and the plugin version were **not re-checked**. This asks for a residual check, not new work.

## Ask

Check at HEAD whether the freshness gate derives "whole-tree" from the row's actual scope (test count / module set) or from its label, and whether a narrow row can be recorded under a whole-tree label.
