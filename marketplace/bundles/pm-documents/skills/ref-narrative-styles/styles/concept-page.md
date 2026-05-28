# Style — Concept page

The voice and structure that the `doc/concepts/*.adoc` pages share. A reader who lands on any concept page should be able to recover three things from it alone: the pain point that motivates the design, the structural response Plan Marshall makes, and the honest limit beyond which the response stops working. Twelve pages on `main` already speak in this voice. This document codifies the rules so the thirteenth, fourteenth, and fiftieth all sound like the same author wrote them.

## When to use this style

Use it when authoring or rewriting a page under `doc/concepts/`. The surface is a navigational summary that defers contract detail to canonical specifications under `marketplace/bundles/.../standards/` — never a spec itself. Length is bounded (most pages 30-100 lines of AsciiDoc); a page that is reaching for `====` headers or a fourth screen of body prose has become a spec and belongs somewhere else.

Do not use it for `doc/user/`, `doc/developer/`, or skill standards. Those surfaces have different audiences and different voices.

## The three-step arc

Every concept page is one move in the same three-step argument:

1. **The pain point** — stock Claude Code, used naïvely for non-trivial work, fails in a known way. The token spend blows up, the agent edits the wrong file, the run silently picks a different code path each time, the model reports success against state it never produced. Name the pain in concrete, observable terms.
2. **The structural response** — Plan Marshall narrows what the LLM can do at that failure surface (isolation via worktrees, deterministic skill loading, scripted external integrations, scripted builds with zero-token waits, automated reviews through one pipeline, phase handshakes that mechanically refuse drift). The response is structural — usually a primitive plus a contract — not an exhortation.
3. **The honest limit** — none of this prevents the LLM from trying. The mechanism shifts the failure mode from "the agent did something weird and you didn't know" to "the gate caught it" or "the prompt fired before damage." The CAUTION blocks in `process-enforcement.adoc` and `security.adoc` are the canonical worked examples of this register.

A reader who reads several concept pages should feel them stack into one coherent argument.

### Per-page mapping

The concept pages each sit at a different position in the arc. The pain point each one names:

| Page | Pain it names |
|------|---------------|
| `branches-and-worktrees.adoc` | The developer and the agent fighting over one HEAD; plans contaminating each other; "my main checkout has uncommitted changes from a plan I forgot was running." |
| `planning-workflow.adoc` | "What is the agent supposed to be doing right now?" unanswered through most of a long session. |
| `execution-context.adoc` | Each subagent dispatch a fresh ad-hoc invention — different prompt shape, different tools, different skill loads. |
| `skill-handling.adoc` | "It loaded what?" — the agent silently pulling in skills the prompt happened to surface. |
| `recipes.adoc` | Re-discovering a known-shape transformation as if it were novel. |
| `automatic-reviews.adoc` | Stock review processes ask the LLM to remember to address every comment. |
| `build-management.adoc` | A 10-minute Maven build streamed into the LLM session burns tokens, fragments attention, and fills the context window. |
| `token-management.adoc` | A long plan running into the context window or degrading recall. |
| `tools-and-scripts.adoc` | MCP-style runtime tool discovery producing three different code paths for one operation. |
| `process-enforcement.adoc` | LLMs are not reliable process followers. |
| `security.adoc` | The accept-edits-vs-YOLO trade — too many prompts versus unbounded blast radius. |
| `audit-trail.adoc` | "What did this run actually do?" unanswered. |
| `extension-architecture.adoc` | "How do I add a domain without forking the orchestrator?" |
| `README.adoc` | (Index — no pain point of its own.) |

When a new concept page is added to the tree, decide which pain it names before writing the body. If you cannot name the pain in one observable sentence, the page is not yet a concept page.

## Style rules

A single voice across every page. Concrete rules, in priority order:

- **Third-person, present tense.** "The LLM does X." "Plan Marshall responds with Y." Avoid first-person plural ("we", "our system"). Avoid future tense ("will do X") when present works.
- **Subjects matter.** Sentences usually start with the actor — the LLM, the orchestrator, the dispatcher, the developer, the plan — rather than with abstract nouns ("It is the case that…", "There exists a mechanism…").
- **Name the primitive, then explain it.** Bold or italicise the load-bearing term on first introduction (`*worktree*`, `*feature branch*`, `*hash_id*`, `*phase handshake*`). After that the term is in normal weight.
- **Concrete over abstract.** "A 10-minute Maven build" beats "long-running build processes." "A reviewer comparing two runs sees the same five-step decision loop" beats "consistency across review iterations is improved."
- **Defer detail with confidence, not apology.** "See `worktree-handling.md` for the full contract" — not "this is just a summary; the real story is elsewhere," not "for more information consult." The deferred link reads as a courtesy to the reader, not as the page admitting incompleteness.
- **References are clickable.** A backtick-wrapped filename in body prose is a defect when there's a `link:` or `xref:` macro available — every file reference resolves to its canonical home or to the managing skill, except for genuinely generic file-shape references (e.g. "every skill has a `SKILL.md`") which stay as plain prose.
- **One idea per paragraph.** A paragraph carrying two `==` worth of content is two paragraphs.
- **Sentences mostly 15-25 words.** Long sentences are fine for nuance but they are not the default.
- **No bullet-list-as-paragraph.** Bullets are for genuinely parallel items (a list of profiles, a list of resolution outcomes). Continuous reasoning stays in prose.
- **Header depth ceiling.** Three levels of structure (`=` page title, `==` section, `===` subsection) is the maximum. A page reaching for `====` has become a spec.

## Tone — what "matter-of-fact, slightly self-ironic" sounds like

The register every concept page shares: matter-of-fact, slightly weary about LLM behaviour, never preachy, never marketing. It is the voice of someone who has been burned by a Claude Code session and built scaffolding around the experience.

Three slots per page where this tone naturally surfaces:

### 1. The opening motivation paragraph

One sentence — early, sometimes the very first — that names the pain point with a small wink.

Existing high-bar examples:

- `process-enforcement.adoc`: "Telling them not to does not stop them."
- `security.adoc`: "way fewer prompts than accept-edits, way more secure than YOLO"
- `branches-and-worktrees.adoc`: "Two actors want to edit the same checkout — the developer and the agent — and stock Claude Code lets them."
- `skill-handling.adoc`: "In an unconstrained Claude Code session, 'which skill applies here' is a runtime guess the model makes from whatever the prompt happened to surface."

If the page opens with "Plan Marshall does X" — describing the solution before naming the pain — rewrite it. The reader needs the pain first so the solution has something to push against.

### 2. A CAUTION block where there is a real limit

Honest, not defensive. Examples:

- `security.adoc`: "**Does this solve the problem completely? No.** `dev-agent-behavior-rules` is skill-loaded *guidance*, not kernel-level enforcement…"
- `process-enforcement.adoc`: "**Does this guarantee compliance? No.** Layer 1 is skill-loaded text, not kernel enforcement…"

CAUTION blocks are added sparingly — only where the limit is genuinely interesting. If a concept has no real limit worth naming (e.g. `recipes.adoc`, `branches-and-worktrees.adoc`), do not invent one. A NOTE block that names a structural observation (the way `branches-and-worktrees.adoc` names the `phase_handshake` invariant pair) is an acceptable substitute when the page has nuance worth surfacing without rising to "honest limit."

### 3. The closing — what it doesn't solve

A short paragraph or one-liner near the `== Related` block naming what the concept page stops at. Example for `recipes.adoc`: "Recipes do not make the recurring shape any less recurring — the underlying drudgery is still there, just dispatched efficiently." Example for `audit-trail.adoc`'s CAUTION: "The audit trail is post-hoc, not real-time enforcement."

## Calibration — what the tone is NOT

- **Not jokey.** No memes, no exclamation points, no "you know how it is."
- **Not sneering at the LLM.** The voice is "I work with this thing and these are its sharp edges," not "the LLM is dumb."
- **Not marketing.** Avoid "powerful", "elegant", "seamless", "best-in-class." The existing prose of `branches-and-worktrees.adoc` ("Plan Marshall realises this by allocating two paired resources for each plan") is the right register — direct, no adjectival flourish.
- **Not apologetic.** The CAUTION blocks are honest but they are not "sorry it's not better." They are "here's where the line is."

## Operational checklist

After authoring or rewriting a page, walk it against this four-step pass:

1. **Opening.** Read the first paragraph. Does it name the pain in one sentence, in the right register? If it leads with "Plan Marshall does X", rewrite to lead with the pain instead. Use one of the high-bar examples above as the model.
2. **CAUTION block.** Does the page have a real limit worth naming? If yes, polish the CAUTION block to the `security.adoc` / `process-enforcement.adoc` voice. If no real limit exists, do not invent one.
3. **Closing.** Read the prose just before `== Related`. Does it name what the page does not solve, in one or two sentences? If missing and the concept has a closing limit, add it. If the page already closes well, leave it.
4. **Sweep for voice violations.** Find-and-replace pass on the surviving prose: first-person plural ("we", "our"), adjectival marketing ("powerful", "elegant", "seamless", "best-in-class"), future tense where present works, header depth beyond `===`. Rewrite each occurrence.

## Worked examples

The 12 concept pages already on `main` are the canonical worked-example collection. When the rules above feel abstract, read one of these end-to-end and notice how it applies them:

- **Pain-point openings** at their cleanest: `process-enforcement.adoc`, `security.adoc`, `branches-and-worktrees.adoc`.
- **Multi-paragraph response section** that names the primitive and the contract: `automatic-reviews.adoc`, `build-management.adoc`.
- **CAUTION block done well**: `security.adoc` ("Does this solve the problem completely? No."), `process-enforcement.adoc` ("Does this guarantee compliance? No.").
- **Honest closing line near `== Related`**: `audit-trail.adoc` (post-hoc, not real-time), `recipes.adoc` (the drudgery is still there).
- **Tight `== Related` block** that defers content to canonical specs without apology: every concept page (look at any two side by side; the shape is uniform).

## Related

| Resource | Purpose |
|----------|---------|
| [`../SKILL.md`](../SKILL.md) | The narrative-styles library index — when to load this style versus a future one. |
| [`pm-documents:ref-asciidoc`](../../ref-asciidoc/SKILL.md) | AsciiDoc syntax + formatting — the *how* this style is written in. |
| [`pm-documents:ref-documentation`](../../ref-documentation/SKILL.md) | Broader content-quality and review-orchestration standards. |
| [`pm-documents:ref-svg-diagrams`](../../ref-svg-diagrams/SKILL.md) | The visual sibling — when a concept page reaches for a diagram, that skill carries the per-type standards. |
