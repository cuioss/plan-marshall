envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:44:50Z

component=plan-marshall:script-shared
category=anti-pattern

# A fix applied to the site the reporter named, not to the derived population of sites, let the identical guard fire again

A Q-Gate finding named ONE call site. The fix was applied to that site, the gate was re-run, and the gate failed again with a byte-identical assertion — because a SECOND site of the same shape existed and was never enumerated.

## Evidence

Two findings, same plan, same rule, ~13 minutes apart:

- `9c62d4` (5-execute) — `test_no_new_shared_registration_collision` fails on a new `sys.modules` collision for `_manifest_lanes`. The finding named `test_lane_class_off_immunity.py` as the "most likely cause". The fix went to `test_finalize_steps_lane_rejection.py` (`register=False`).
- `267e2c` (5-execute) — **"Recurs after the first fix. A SECOND registering call site remains"**: `test_cmd_quality_phases.py` also loaded `_manifest_lanes` via `load_script_module(module_name='_manifest_lanes')`. The verify job ran TWICE more (`b0757b87…`, `00699b8d…`) still red, identical assertion, before the second site was found.

The second finding's own resolution shows the derivation that should have preceded the first fix: `architecture search --content --literal --pattern module_name='_manifest_lanes' --category test`, `count=2`, both hits in one file.

## Rule

When a finding names a call site, the fix's unit is the **enumerated population of sites matching the finding's shape**, never the one instance the reporter happened to cite. Run the content sweep that defines the population BEFORE the first fix, and state its size in the resolution. A reporter's call-site list is a SAMPLE.

The cost here was two full re-verify cycles on a red gate. The instrument to derive the population was available, documented, and used only after the recurrence.
