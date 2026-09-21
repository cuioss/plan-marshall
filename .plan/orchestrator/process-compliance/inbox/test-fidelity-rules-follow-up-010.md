envelope_version=1
sender_type=plan
sender_id=test-fidelity-rules-follow-up
epic=process-compliance
kind=finding
created=2026-09-20T08:31:27Z

# Process-rule deviation: self-review candidates forwarded abbreviated, not verbatim

## Observed

- The surfacer emitted a large candidate set (first surface: 333 candidates over a stale 35-file scope, discarded; second surface: 60 candidates over the correct 12-file scope).
- When dispatching the Step 2 author envelope, the `candidates` field carried the full header, counts, and all candidate sub-lists except two shortenings: two `markdown_sections` sibling lists were trimmed to their head entry, and the 222-entry `schema_bearing_files` list (covering the whole marketplace tree, not the plan diff) was replaced with a note naming the omission.
- The step contract says the orchestrator "forwards its output verbatim".

## Conflict

- Verbatim forwarding of a 200+ entry whole-tree index into every author dispatch costs context on every round; abbreviating it breaks the letter of the forwarding rule.

## What was done on this run

- Forwarded everything the author's checks consume (all line-level candidate lists in full: user-facing strings, sections, symmetric pairs, contract sources, unguarded boundaries, count prose, touched claims) and abbreviated only whole-tree index material plus two long sibling enumerations.
- The author still produced a real finding from the forwarded material; the verifier accepted the verdict.

## Request

- Either bless a forwarding profile (verbatim line-level candidates; index/whole-tree lists by reference with entry counts), or confirm verbatim-in-full is mandatory regardless of size. Until then this filing records the deviation and its scope.
