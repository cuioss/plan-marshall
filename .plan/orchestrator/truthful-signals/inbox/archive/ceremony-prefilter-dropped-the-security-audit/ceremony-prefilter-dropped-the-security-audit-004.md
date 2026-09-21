envelope_version=1
sender_type=plan
sender_id=ceremony-prefilter-dropped-the-security-audit
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T15:46:53Z

component=plan-marshall:manage-execution-manifest
category=bug
created=2026-07-29

# A warning message outlived its gate: one fixed string reporting the wrong gate's reason

`_ceremony_prefilter_warnings` emitted a single fixed string naming a `change_type` /
`affected_files` gate as the reason for **every** ceremony drop. When a second drop path was added
whose gate has **no `change_type` leg at all**, that path inherited the message unchanged — so the
system reported one gate's reason for another gate's decision.

The output was confident, well-formed, specific, and about a mechanism that had not participated in
the decision. An operator debugging a drop would have gone looking at `change_type`, found it
irrelevant, and had no path to the actual gate.

## Why the test did not catch it

The warning's test asserted by **substring-matching the shared prefix** of the message — the part
both paths have in common. The differing tail, which is the entire informational payload, was never
asserted. The test passed on the wrong message because it only ever looked at the right part of it.

## Solution

- **A decision message belongs to its decision path, not to the emitter.** When a gate gains a
  second path, the message must be parameterized per path in the same edit. A message that survives
  a gate's bifurcation unchanged is by construction wrong on one of the branches.
- **Never assert a message by its shared prefix.** Assert on the part that distinguishes this case
  from the neighbouring one — the discriminating tail. A prefix assertion is a test that is
  structurally incapable of detecting the defect class it appears to guard.
- **Derive the reason from the gate that fired.** PLAN-112's fix carries the reason as data —
  `security_class_omitted: [{step, reason}]` — instead of as a literal in the emitter, so the reason
  cannot drift away from the decision that produced it.

## Impact

Applies to every emitter with one message and more than one code path reaching it, and to every
test that matches user-facing strings by prefix or by `in`. Both halves recur: the emitter that
did not fork when its gate did, and the assertion that made the omission invisible.
