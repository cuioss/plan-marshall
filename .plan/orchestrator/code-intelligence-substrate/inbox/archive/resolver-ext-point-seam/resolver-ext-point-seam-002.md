envelope_version=1
sender_type=plan
sender_id=resolver-ext-point-seam
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-30T11:50:35Z

component=plan-marshall:phase-3-outline
category=anti-pattern
title=A cited call site is a SAMPLE, not an enumeration - prose awareness does not prevent the recurrence, only a mechanical enumeration step does

# A cited call site is a SAMPLE, not an enumeration

Three separate instances of the same archetype fired inside a single plan
(`resolver-ext-point-seam`, PR #1067). All three were caught, none reached main. The
reusable content is not the archetype itself — it is already known — but the fact that it
recurred **inside a plan whose own Overview explicitly flagged the trap**, which falsifies
the implicit remedy "warn about it in the plan text".

## The three instances

1. **The spec's cited join site was 1 of 2.** The plan spec named one coordinate-join
   site. The live tree had two: an inline join in `_cmd_client_query.py` serving the
   `graph` verb, plus `_build_internal_deps_map` serving `path` / `neighbors` / `impact`.
   Caught by outline discovery, because outline discovery reads the tree rather than the
   spec.

2. **The outline's caller enumeration was 3 of 5, and the real count was 6.** The outline
   enumerated `_build_internal_deps_map`'s callers as three; the live count was five; and a
   sixth derivation consumer — `render_module_markdown` at `_cmd_client_render.py:230` —
   was unenumerated entirely. Had it stayed unenumerated, it would have kept rendering
   empty dependencies after the seam landed: a silent, green-passing regression in rendered
   output. Caught by Q-Gate.

3. **A characterization fixture corpus was 2 of 5, and the omission was the exact case the
   deliverable existed to prevent.** Deliverable 4's characterization fixtures enumerated 2
   of the 5 poms in the corpus, omitting `legacy/auth-service/pom.xml` — whose
   deliberately-duplicated `com.example:auth-service` coordinate is precisely what meets
   the last-write-wins join. Because a characterization test's job is to pin *current*
   behaviour, the under-enumerated corpus would have faithfully pinned today's silent
   module-drop **as expected behaviour**, preserving the latent defect the deliverable was
   written to eliminate. Caught by Q-Gate.

## Why instance 3 is the sharpest one

Instances 1 and 2 fail loudly-ish: a missed call site eventually shows up as a broken
consumer. Instance 3 fails *silently and permanently*: an under-enumerated characterization
corpus converts a latent defect into a green test that certifies the defect. A
characterization suite is the one place where under-enumeration is not merely incomplete
coverage — it is an active, self-perpetuating endorsement of the bug.

## Solution

The corrective is not "be careful" and not "note the risk in the Overview" — this plan did
both and recurred three times anyway. The corrective is a mechanical enumeration step,
owned by whichever phase produces the set:

1. **Never carry a count forward from a spec, an outline, or a reviewer's list.** Every one
   of those is a sample. Re-derive the count from the live tree at the moment you consume
   it.
2. **Derive call-site sets from the population, not by reading.** For a
   symbol-with-N-callers claim, run the enumeration query (`architecture find --pattern`,
   or a grep over the symbol) and use its output as the set. Never hand-transcribe a subset.
3. **A characterization fixture corpus must be population-derived from the live corpus
   directory** — enumerate every fixture in the directory, then justify each *exclusion*
   explicitly. Opt-out with a stated reason, never opt-in by selection. An unstated
   exclusion in a characterization corpus is indistinguishable from an endorsement of the
   behaviour on the excluded case.
4. **Prose warnings are not a control.** If a plan's Overview identifies an
   enumeration risk, that risk must be discharged by a concrete enumeration step in a
   deliverable, not by the warning itself.

## Impact

Applies to any phase that produces a set claim: phase-3-outline (call-site enumeration),
phase-4-plan (deliverable fixture corpora), and any reviewer-supplied list of call sites.
Recurrence signature to look for: a natural-language count ("three callers", "two join
sites", "the 2 relevant poms") that was never produced by a query.
