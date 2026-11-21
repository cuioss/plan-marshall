# Style — Tutorial Walkthrough

The voice for documents that take a reader from nothing to a working result by doing the thing alongside them: getting-started guides, setup runbooks, the "your first plan" page. The job of this prose is to keep one reader moving forward without losing them at any step. The style is project-agnostic; load it whenever the document succeeds only if the reader reaches the end with the thing working.

## When to use this style

Use it when the document is a guided path — the reader starts without the result and the document's success is measured by whether they get it. There is a clear start state, an ordered sequence, and a verifiable end state. Do not use it to motivate a design (that is the engineering-narrative voice) or to serve as a lookup surface (that is the reference-spec voice). A tutorial that argues instead of guiding, or that a reader must read out of order, has picked the wrong voice.

## The three-part arc

Every walkthrough in this style is one pass through the same three-step path:

1. **The start state** — what the reader has before they begin and what they will have after. Named up front so the reader knows whether this document is for them.
2. **The ordered steps** — one action per step, in the only order that works, each ending in something the reader can observe. The reader is never asked to hold two open threads at once.
3. **The checkpoint** — the observable result that proves the step (or the whole path) worked, plus the one thing to check when it did not. Confirmation, then the single most likely recovery.

A reader who follows the document top to bottom should reach the working end state, and should know at each checkpoint whether they are still on the path.

## Style rules

- **Second person, imperative.** "Run the command", "open the file" — address the reader directly and tell them the action.
- **One action per step.** A step that contains two actions is two steps. The reader does one thing, sees the result, then moves on.
- **Steps are ordered and read in order.** Unlike a spec, a walkthrough is followed front to back; later steps may assume earlier ones ran. State that assumption rather than hiding it.
- **Every step ends in something observable.** Name the output, the file that now exists, the message that prints. A step with no visible result leaves the reader unsure whether to continue.
- **Show the expected output.** Quote what the reader should see, so a divergence is caught at the step that caused it, not three steps later.
- **Header depth ceiling: three.** A walkthrough reaching for a fourth header level has branched into variants — split the variants into sibling documents and keep each path linear.

## Tone

Encouraging, concrete, and patient. The voice belongs to someone sitting beside the reader who has done this many times and wants them to succeed on the first pass. Three slots where the tone surfaces:

- **Opening** — names the start and end state plainly, so the reader commits with confidence rather than hope.
- **Checkpoint block** — confirms the observable result and names the single most common thing to check when it is missing. Reassuring, not exhaustive.
- **Closing** — confirms the end state is reached and points to where the reader goes next, so the path ends cleanly rather than trailing off.

## Calibration — what the tone is NOT

- **Not motivational fluff.** No "you've got this!"; the encouragement is in the clarity, not in the cheering.
- **Not a spec.** No exhaustive option tables; show the one path that works and defer the rest.
- **Not assuming.** Never skip a step because it is "obvious" — the reader is here precisely because it is not obvious to them yet.
- **Not branchy.** Avoid "if you want X do this, otherwise do that" mid-path; pick the default path and split true variants into their own documents.

## Related

- [`pm-documents:ref-asciidoc`](../../ref-asciidoc/SKILL.md) — AsciiDoc syntax and formatting.
- [`pm-documents:ref-documentation`](../../ref-documentation/SKILL.md) — broader content quality and review standards.
- [`styles/reference-spec.md`](reference-spec.md) — the lookup-surface sibling for the options a walkthrough defers.
