envelope_version=1
sender_type=plan
sender_id=build-tests-do-not-neutralize-daemon-routing
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T17:44:20Z

component=plan-marshall:plan-retrospective
category=bug

# The recall denominator counts intent=read files as expected modifications

`check-artifact-consistency` computes `affected_files_recall` as `|declared ∩ realized| / |declared|`. It builds `declared` from every path in every deliverable's `affected_files` list — **ignoring the `intent` field each path carries.**

This plan declared 12 paths. Eight of them belong to Deliverable 1, and every one is `intent: read`:

```
D1 "Derive the affected test population and the routing carve-out set"
  affected_files: 8 paths, all {"intent": "read"}
  verification criteria: "...No repository file was modified by this deliverable."
```

D1 is a derivation deliverable. It is *supposed* to modify nothing, it says so in its own success criteria, and it did exactly that. Yet all 8 of its read-intent paths sit in the recall denominator as though the plan had promised to edit them.

Consequence: the ceiling on achievable recall for this plan was **4/12 = 33%** (the distinct write-intent paths), against a threshold of 70%. **No possible execution of this plan could have passed the check.** Any plan with an analysis/derivation deliverable inherits the same unpassable gate.

The check is not merely noisy — it is vacuous in the strict sense: its pass condition is unreachable for a whole legitimate class of plans, so a pass carries no information and a fail carries no information either.

Note the interaction with cl-008 (filed alongside this one): that finding explains why the *numerator* was 0 (worktree already removed). This finding explains why the *denominator* is wrong even when the numerator is right. Fixing either alone still leaves a wrong number.

## Solution

- **Filter `declared` by intent before computing recall.** Only paths with a write-class intent (`write-new`, `write-replace`, and any future write variants) belong in the denominator. Read-intent paths are an input declaration, not a delivery promise.
- **Report the two populations separately** so the distinction survives into the report: `write_intent_recall` (the gated number) alongside `read_intent_touched` (informational — a read-intent path that *was* modified is worth surfacing as minor scope drift, which is exactly what happened here with `test_pyproject_routing.py`).
- **Guard the fix with a fixture** carrying a read-intent-only deliverable, so the unreachable-pass-condition regression cannot return.

Recomputed for this plan under the proposed rule: write-intent recall = **6/6 = 100%**, with 2 undeclared files touched (1 line and 11 lines) — a clean result that the current check reports as a hard failure.

## Evidence

- aspect: `artifact-consistency` — `affected_files_recall,fail,Recall 0% below 70% threshold`, `declared: 12`
- aspect: `request-result-alignment` — `declared_write_intent: 6`, `declared_read_intent: 8`, `write_intent_recall_pct: 100.0`
- `manage-solution-outline list-deliverables` — D1's 8 `affected_files` entries each carry `"intent": "read"`; D1's verification criteria state "No repository file was modified by this deliverable"
