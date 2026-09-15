# AsciiDoc Embedding

How SVG diagrams are embedded in AsciiDoc pages, where they live on disk, and how to verify the page renders the diagram correctly.

## File location

Every diagram lives under `doc/resources/diagrams/`. The filename is the same `kebab-case` slug as the diagram's `<title>` (per [`visual-language.md`](visual-language.md) § Naming conventions). Examples:

```text
doc/resources/diagrams/findings-pipeline.svg
doc/resources/diagrams/dispatch-resolution.svg
doc/resources/diagrams/phase-lifecycle.svg
```

Do not nest sub-directories beneath `diagrams/` (no `diagrams/concepts/...`). One flat directory keeps the catalogue easy to scan and the relative-path math in the `image::` macro simple.

## The embedding macro

Block image (its own line, captionable, the default):

```asciidoc
image::../resources/diagrams/findings-pipeline.svg[Findings pipeline — short alt-text describing what the diagram shows, align=center]
```

Inline image (rare — when a small icon belongs in the middle of a paragraph):

```asciidoc
The arrow image:../resources/diagrams/icons/arrow-right.svg[, 16] indicates …
```

## Path conventions

The macro path is **relative to the AsciiDoc page that contains it**.

| Page location | Path to `findings-pipeline.svg` |
|---------------|----------------------------------|
| `doc/concepts/automatic-reviews.adoc` | `../resources/diagrams/findings-pipeline.svg` |
| `doc/user/getting-started.adoc` | `../resources/diagrams/findings-pipeline.svg` |
| `doc/developer/marketplace-build.adoc` | `../resources/diagrams/findings-pipeline.svg` |
| `README.adoc` (root, if it existed) | `doc/resources/diagrams/findings-pipeline.svg` |

The same diagram can be referenced from multiple pages — author once, link many.

## Required macro attributes

| Attribute | Purpose | Required? |
|-----------|---------|-----------|
| Alt text (first positional) | Accessibility — describes the diagram in one sentence. Used by screen readers and surfaces in `<img alt="...">` of the rendered HTML. | Yes |
| `align=center` | Visual centering on the page. | Yes for block images. |
| `width=<px>` | Override the rendered display width. | No — omit; the SVG's `viewBox` plus the page's container determines size. |
| `link=<url>` | Make the image clickable. | No — diagrams are usually not link targets. |
| `title=<text>` | Caption rendered below the image. | No — captions add visual weight; use sparingly. |

## Accessibility

The `<title>` and `<desc>` elements inside the SVG (per [`visual-language.md`](visual-language.md) § Naming conventions) provide accessible names beyond the alt text. AsciiDoctor's HTML renderer carries the macro alt text through to the `<img alt="…">` attribute; the in-SVG `<title>` and `<desc>` are read by screen readers when the image is focused.

Three layers of accessibility text, all of which should be present:

| Layer | Lives in | Purpose |
|-------|----------|---------|
| Alt text | `image::path[alt-text, …]` macro | First-line summary for assistive tech, fallback for broken images. |
| `<title>` | inside SVG, `<title id="title">` | Accessible name announced by screen readers. |
| `<desc>` | inside SVG, `<desc id="desc">` | Long description — what the diagram means, not just what it shows. |

The SVG root references both via `aria-labelledby="title desc"`. All three should reflect the same intent; the alt text is the shortest, `<desc>` is the longest.

## Render verification

Before committing a new or modified diagram, render the page locally and confirm the `<img>` reference resolves:

```bash
asciidoctor --safe-mode=safe -o /tmp/page.html path/to/page.adoc
grep -c '<diagram-filename>.svg' /tmp/page.html
```

Should return `1` for a single embedding, `2+` for repeated embeddings. A `0` means the macro path is wrong.

Optionally open the rendered HTML in a browser to confirm visual alignment:

```bash
open /tmp/page.html
```

This catches macro typos, broken relative paths, and AsciiDoctor-specific rendering quirks that the `grep` does not.

## What doesn't work

- **Inline HTML `<img>` tags** in `.adoc` body. GitHub's AsciiDoc renderer strips them. Always use the `image::` macro.
- **`<picture>` elements** for theme switching. AsciiDoc has no `picture::` macro; GitHub does not honour inline HTML `<picture>` in `.adoc`. Use SVG-internal CSS (see [`theme-handling.md`](theme-handling.md) Strategy B).
- **`embed::` or `include::` to inline the raw SVG markup**. AsciiDoc's `include::` includes file contents as text, not as an embedded SVG. The result is XML appearing as code in the rendered page.
- **External SVG references via `href`** inside the embedded SVG (e.g. `<use href="library.svg#icon">`). The browser cannot resolve `href` cross-file when the SVG is loaded as `<img>` (only when inline). Self-contained SVGs only.

## Markdown variant

The `image::` macro is AsciiDoc-only. For Markdown pages (typically `README.md`), use:

```markdown
![Findings pipeline — short alt-text describing what the diagram shows](doc/resources/diagrams/findings-pipeline.svg)
```

Strategy C (two-file theme switch) from [`theme-handling.md`](theme-handling.md) is available in Markdown but not AsciiDoc; see that document for the full Markdown-only syntax.
