# Style — Engineering Narrative

The voice for documents that argue for a piece of engineering: design RFCs, concept pages, the narrative section of an ADR — any prose whose job is to explain *why* something exists rather than *what* it does. The style is project-agnostic; load it whenever a design document needs to actually land with its reader.

## When to use this style

Use it when the document's purpose is to motivate a design choice — name the problem, describe the structural response, mark the honest limit. Do not use it for reference material (an API spec, a CLI manual) or for procedural runbooks (numbered steps). Those have other voices.

## The three-part arc

Every document in this style is one move in the same three-step argument:

1. **The problem** — a concrete failure or friction the reader recognises. Observable. Named early, in one or two sentences.
2. **The structural response** — what the design changes about the situation. Usually a primitive plus a contract, not an exhortation.
3. **The honest limit** — what the response does not solve. Not apologetic; not defensive; named so the reader knows where the line is.

A reader who finishes the document should be able to recover all three from it.

## Style rules

- **Third-person, present tense.** Avoid first-person plural ("we"); avoid future tense where present works.
- **Subjects are actors.** Sentences start with the thing doing something, not with abstract scaffolding ("It is the case that…").
- **Name the primitive on first use** in bold or italic; from then on it appears in normal weight.
- **Concrete over abstract.** Replace category nouns with the smallest specific example that still carries the point.
- **Defer with confidence.** "See [spec] for the full contract" — not "this is only a summary; the real story is elsewhere."
- **One idea per paragraph.** Sentences mostly 15-25 words.
- **Header depth ceiling: three.** A document reaching for a fourth header level has become a spec — move the detail into a spec instead.

## Tone

Matter-of-fact, slightly self-ironic about the problem the design solves. The voice belongs to someone who has been burned by the problem and built the response around the experience. Three slots where the tone naturally surfaces:

- **Opening sentence** — names the problem with a small wink, not a marketing claim.
- **Honest-limit block** (often a `CAUTION` admonition in AsciiDoc) — names what the response does not solve. "Here's where the line is," not "sorry it's not better."
- **Closing** — one or two sentences near `== Related` naming what the document stops at.

## Calibration — what the tone is NOT

- **Not jokey.** No exclamation points, no memes.
- **Not sneering.** "I work with this thing and these are its sharp edges," not "the system is dumb."
- **Not marketing.** Avoid "powerful", "elegant", "seamless".
- **Not apologetic.** Limits are stated, not lamented.

## Related

- [`pm-documents:ref-asciidoc`](../../ref-asciidoc/SKILL.md) — AsciiDoc syntax and formatting.
- [`pm-documents:ref-documentation`](../../ref-documentation/SKILL.md) — broader content quality and review standards.
- [`pm-documents:ref-svg-diagrams`](../../ref-svg-diagrams/SKILL.md) — visual sibling for the diagrams a narrative document reaches for.
