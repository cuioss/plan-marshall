# WS-03: Production and Harness Gaps

epic: test-quality

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-03-production-and-harness-gaps.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Own the surface every reduction plan is forbidden to touch. A reduction run that finds a missing
parser seam, a loader that cannot address a file, an analyzer that mis-matches, or a rule whose
message names an inapplicable remedy **records** the defect and moves on — and until this workstream
existed, four consecutive runs each found the same blocker and none could close it. WS-03 is where
those recorded defects are discharged: `marketplace/bundles/**` production changes, `test/conftest.py`
loader mechanics, and the analyzer amendments the style rules need.

## Scope

- In scope: `marketplace/bundles/**` (the doctor analyzers, `script-shared`, `manage-providers`) —
  **the only workstream that may edit it** — plus `test/conftest.py`'s loader mechanics
  (`load_script_module`, `get_scripts_dir`, registration behaviour) and the tests for its own
  production changes.
- Out of scope: reducing any slice (WS-02's); `test/conftest.py`'s session preflight and skip guard
  (WS-05's); the module-budget campaign (WS-04's); populating the `identifier-validator-corpus`
  registry and the `broken-relative-link` rule's fragment half — both **unowned by design**, each
  needing a decision this epic does not carry.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-090-harness-and-rule-gaps | landed | Two runs. Run 01's residue is untouched by run 02 — nine named open items. Its three open classes **R1, R3 and R4 each rest on a single instance**, with no sweep establishing it was the only one |

## Sequencing and Surface Notes

- `090` was a blocking prerequisite for the **B6**/**B7** halves of `070` and `080`. Both have landed,
  so that sequencing is spent.
- **`090` owns `marketplace/bundles/**` exclusively, and that is the epic's most contested surface.**
  Two staged plans reach into it anyway and each says so: `105` § D3 widens one analyzer and § D7
  sweeps ~250 files; `120`'s checker may be placed there by the script-architecture standard. Each
  carries a halting concurrency check.
- `090` shares `test/conftest.py` with `110` — `090` owns the loader mechanics, `110` the session
  preflight and skip guard.
- **The open-class residue needs a sweep, not another instance.** R1, R3 and R4 each rest on one
  observed case with nothing establishing it was the only one, which is the shape a follow-up plan
  must close: its deliverable is the sweep, not the fix.
