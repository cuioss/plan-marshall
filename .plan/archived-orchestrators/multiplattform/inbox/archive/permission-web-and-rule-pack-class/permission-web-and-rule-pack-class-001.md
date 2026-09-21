envelope_version=1
sender_type=plan
sender_id=permission-web-and-rule-pack-class
epic=multiplattform
kind=landing
created=2026-09-04T15:16:18Z

```landing-facts
schema=landing-facts/1
plan_id=permission-web-and-rule-pack-class
epic=multiplattform
pr=#1408
merge_state=merged
deliverables_total=3
deliverables_done=3
total_tokens=unknown
steps=step-4-implement:done,step-5-build-gate:done,step-6-verifier:clear,step-7-pr:done,step-8-merge:done,step-9-self-check:done
```

## Summary

Closed the last two permission-coupling surfaces PLAN-08 excluded, consuming PLAN-08's semantic vocabulary.

- **D1** — `permission_web.py` routes and states intent: removed the direct settings I/O and `WebFetch(domain)` DSL rendering (the `analyze`/`apply` subcommands and their helpers); the script is now pure domain categorization, with a no-Claude-write pin test.
- **D2** — The permission rule-pack class is declared: `permission_doctor.py`'s analysis rules and the three permission standards documents now carry Claude-rule-pack provenance (mirroring `plugin-doctor`'s documented engine/rule-pack split).
- **D3** — Inventory row retirement report: §B row 5 (permission_web.py) detection re-run finds nothing → **retire**; §B row 8 (permission-doctor + standards) detection still finds the declared Claude grammar → **stays, narrowed to the residue** (relocation/sanction decision is the orchestrator's). The inventory itself was not edited.

## Residue

- CodeRabbit finding deferred with bound: the direct-script `permission_doctor detect-*` route reports false zero-findings on an OpenCode target. The documented operator path (`platform_runtime permission analyze`) is already honest; the fail-closed enforcement on the direct-script route is a named follow-up on the permission-skills runtime-binding surface.
- D3 row 8 residue as described above.
