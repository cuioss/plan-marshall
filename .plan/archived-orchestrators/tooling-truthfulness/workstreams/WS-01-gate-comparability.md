# WS-01: The disjointness gate reads something it can actually compare

epic: tooling-truthfulness

## Charter

Own every way the disjointness gate returns a clean verdict it did not earn. The gate's job is to
decide whether two plans can run concurrently; it does that by comparing declared surfaces. Four
distinct mechanisms let that comparison succeed vacuously — an exact-path matcher that cannot see
containment, a live plan that declares nothing yet and therefore matches nothing, a staged spec
whose work list decayed as siblings landed, and a plan that expanded its surface and told the report
instead of the declaration. In each case the gate says *disjoint* when the honest answer is *I could
not tell*.

⛔ **This workstream is design-heavy and partly not code.** Two members ask what the gate SHOULD
read, not merely how to fix a comparison. Expect a recorded decision, not only a patch.

The workstream closes when a candidate whose surface the gate cannot compare is SEQUENCED rather
than passed, and the reason is named in the shortfall.
