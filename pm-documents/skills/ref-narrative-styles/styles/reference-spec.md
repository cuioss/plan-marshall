# Style — Reference Spec

The voice for documents a reader consults rather than reads: API specifications, CLI manuals, schema definitions, the `## Canonical invocations` block on a script-bearing skill. The job of this prose is to answer a precise question fast and leave no room for interpretation. The style is project-agnostic; load it whenever a reader will arrive mid-document looking for one entry, not at the top looking for an argument.

## When to use this style

Use it when the document is a lookup surface — the reader knows what they want and needs the exact shape, the exact flag, the exact return field. Each entry stands alone, so a reader who jumps straight to it understands it without the surrounding text. Do not use it to motivate a design (that is the engineering-narrative voice) or to walk someone through a procedure (that is the tutorial-walkthrough voice). A spec that argues for itself or tells a story has stopped being a spec.

## The three-part arc

Every entry in this style is one move in the same three-step contract:

1. **The signature** — the exact callable shape: the command line, the function signature, the field name and type. Verbatim, copy-pasteable, no paraphrase.
2. **The semantics** — what each part means and what the entry does. One behaviour per clause; defaults and required-ness stated, never implied.
3. **The boundary** — the failure modes, the constraints, the values outside the accepted set. What the entry refuses, stated as flatly as what it accepts.

A reader who reads one entry should be able to call the thing correctly and predict how it fails, without reading any other entry.

## Style rules

- **Entries are self-contained.** A reader who lands on one entry from a search must understand it without the preceding entries. Repeat the small shared premise rather than back-reference it.
- **The signature is verbatim.** Quote the real argparse declaration, the real type, the real field name — never a plausible-looking reconstruction. A spec that drifts from the implementation is worse than no spec.
- **Tables and lists over prose.** A field set is a table; an enum is a list. Reserve sentences for the one nuance a table cannot hold.
- **Name every default and every required value.** "Optional; defaults to `5`" — not "usually 5". Silence on required-ness is the most expensive ambiguity a spec carries.
- **No narrative connectors.** Drop "as we saw above", "now that we have", "let us". Each entry is a destination, not a step.
- **Header depth ceiling: three.** A spec reaching for a fourth header level is nesting entries that should be flattened into a table or split into sibling documents.

## Tone

Flat, exact, and complete. The voice belongs to someone who has answered the same lookup question enough times to write the answer once, precisely, so it never has to be asked again. Three slots where the tone surfaces:

- **Signature line** — the exact shape with zero hedging. No "approximately", no "something like".
- **Boundary block** — the refused inputs and failure modes, stated without apology. "Rejects any value outside the enum," not "tries to handle bad input gracefully."
- **Default callout** — every default named at the point of use, so the reader never has to infer it.

## Calibration — what the tone is NOT

- **Not narrative.** No problem-then-response arc; the reader did not come for the story.
- **Not procedural.** No "first do this, then do that"; entries are looked up, not followed in order.
- **Not approximate.** Avoid "roughly", "usually", "should" — a spec states what is, not what tends to be.
- **Not chatty.** No asides, no encouragement, no second-person address.

## Related

- [`pm-documents:ref-asciidoc`](../../ref-asciidoc/SKILL.md) — AsciiDoc syntax and formatting.
- [`pm-documents:ref-documentation`](../../ref-documentation/SKILL.md) — broader content quality and review standards.
- [`styles/engineering-narrative.md`](engineering-narrative.md) — the motivating-prose sibling for the *why* a spec leaves out.
