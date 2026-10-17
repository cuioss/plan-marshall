# Theme Handling

How an SVG diagram adapts to GitHub's light and dark themes when rendered through the AsciiDoc / Markdown viewer. Three strategies; pick one per diagram and record the choice in a comment at the top of the SVG.

## Background

GitHub renders both `.adoc` and `.md` pages with one of two themes (light or dark), chosen by the user in their account settings or set by their OS preference. An SVG referenced via `image::path/to/file.svg[]` (AsciiDoc) or `![](path/to/file.svg)` (Markdown) is loaded as an `<img>` — it does **not** inherit page CSS. Inside the SVG, the only way to know which theme is active is the CSS `prefers-color-scheme` media query, which evaluates against the OS preference (not GitHub's per-account preference).

GitHub-native dark-mode tricks (e.g. the `#gh-dark-mode-only` URL fragment, the `<picture>` element with `media="(prefers-color-scheme: dark)"`) are **Markdown-only** — AsciiDoc pages on GitHub do not honor them. So for the AsciiDoc-heavy `doc/` tree, the only portable theme-handling lever is **CSS inside the SVG itself**.

## Strategy A — theme-neutral (default; safest)

**One palette, picked to be legible on both themes. No media query.**

Use case: any diagram where slightly-lower contrast on each theme is acceptable in exchange for absolute predictability. This is the default.

```svg
<?xml version="1.0" encoding="UTF-8"?>
<!-- theme-handling: A (theme-neutral) -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 500"
     role="img" aria-labelledby="title desc">
  <title id="title">…</title>
  <desc  id="desc">…</desc>

  <defs>
    <style>
      .stroke   { stroke: #6e7681; stroke-width: 1.2; fill: none; }
      .text     { fill: #6e7681; }
      .muted    { fill: #6e7681; font-style: italic; }
      .arrow    { stroke: #6e7681; stroke-width: 1.5; fill: none; }
      .arrow-fill { fill: #6e7681; }
    </style>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="9" markerHeight="9" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" class="arrow-fill"/>
    </marker>
  </defs>

  <!-- … content uses class="stroke", class="text", … -->
</svg>
```

**Properties:**

- Works on any browser, any renderer, any theme.
- Lowest authoring effort.
- Lower contrast than ideal on each individual theme (a single mid-tone never reaches the contrast of theme-specific blacks-on-white or whites-on-near-black).
- **Use for diagrams with simple, easily-readable structure.** The findings-pipeline reference implementation uses this strategy.

## Strategy B — theme-aware via `prefers-color-scheme`

**Two palettes inside one SVG, swapped by CSS media query.**

Use case: dense diagrams where maximum contrast on each theme is worth the slight risk of media-query non-support in edge-case renderers.

```svg
<?xml version="1.0" encoding="UTF-8"?>
<!-- theme-handling: B (theme-aware via CSS) -->
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 900 500"
     role="img" aria-labelledby="title desc">
  <title id="title">…</title>
  <desc  id="desc">…</desc>

  <defs>
    <style>
      /* Light-mode defaults */
      .stroke     { stroke: #1f2328; stroke-width: 1.2; fill: none; }
      .text       { fill: #1f2328; }
      .muted      { fill: #59636e; font-style: italic; }
      .arrow      { stroke: #1f2328; stroke-width: 1.5; fill: none; }
      .arrow-fill { fill: #1f2328; }

      @media (prefers-color-scheme: dark) {
        .stroke     { stroke: #f0f6fc; }
        .text       { fill: #f0f6fc; }
        .muted      { fill: #9198a1; }
        .arrow      { stroke: #f0f6fc; }
        .arrow-fill { fill: #f0f6fc; }
      }
    </style>
    <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5"
            markerWidth="9" markerHeight="9" orient="auto">
      <path d="M0,0 L10,5 L0,10 z" class="arrow-fill"/>
    </marker>
  </defs>

  <!-- … content -->
</svg>
```

**Properties:**

- Renders with full GitHub Primer contrast on each theme.
- Browser support: Chrome / Edge / Firefox / Safari 13+. Some older or non-browser SVG renderers ignore the media query and fall through to the light-mode rule — which is the same as Strategy A would have given them, so degradation is graceful.
- The media query evaluates against the **OS preference**, not GitHub's per-account preference. A user with light OS + dark GitHub will see the light-mode SVG palette on dark page background. Usually fine; rarely jarring.
- **Use for high-density diagrams** where the extra contrast is the deciding factor.

## Strategy C — theme-aware via two files (markdown-only)

**Two separate SVG files, switched by GitHub's MD-native dark-mode hash trick.**

Use case: **README.md only.** This strategy does NOT work in AsciiDoc and should not be used for diagrams under `doc/`.

```markdown
![diagram](path/to/diagram-light.svg#gh-light-mode-only)
![diagram](path/to/diagram-dark.svg#gh-dark-mode-only)
```

Or with the modern `<picture>` element (HTML inline in Markdown):

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="diagram-dark.svg">
  <img src="diagram-light.svg" alt="…">
</picture>
```

**Properties:**

- Maximum control: each theme gets its own hand-crafted SVG.
- Two files to maintain in lockstep.
- AsciiDoc pages on GitHub do not honor either form. `image::diagram.svg#gh-light-mode-only[]` propagates the `#gh-light-mode-only` fragment through to the `<img>` tag, but GitHub's AsciiDoc renderer strips it.
- **Use for README.md only.** Don't use for the AsciiDoc `doc/` tree.

## Decision matrix

| Question | If yes → | If no → |
|----------|----------|---------|
| Is the diagram going into the AsciiDoc `doc/` tree? | Strategy A or B | Strategy C is available |
| Does the diagram have ≥3 columns and many fine-grained labels? | Lean Strategy B | Strategy A suffices |
| Will the diagram render in non-browser tooling (CI thumbnail, archived export)? | Strategy A | Either A or B |
| Is the diagram a hero image / logo where contrast must be maximised on both themes? | Strategy C (if in README.md), else Strategy B | Strategy A |

## Recording the choice

Every SVG file starts with an XML comment that declares its strategy:

```svg
<?xml version="1.0" encoding="UTF-8"?>
<!-- theme-handling: A (theme-neutral) -->
```

This makes the choice visible to anyone editing the file. Reviewers can spot a mid-edit strategy switch (Strategy A diagrams accidentally accumulating `@media` rules, or Strategy B diagrams missing the media query) at a glance.

## What does NOT work

- **`currentColor`** to inherit from page CSS. SVG-as-image has no parent context; `currentColor` falls back to its initial value (`black`). Diagrams written with `stroke="currentColor"` are black-on-anything — invisible on dark.
- **CSS variables (`var(--token)`) defined outside the SVG.** Custom properties in the host page do not cross the `<img>` boundary. Define everything inline in `<style>`.
- **GitHub-Flavored Markdown alerts** (`> [!CAUTION]`) inside the SVG — those are MD syntax, not SVG.
- **Inline `<style>` inside the SVG `<body>`** without a `<defs>` wrapper — works in most browsers, but `<style>` inside `<defs>` is the canonical placement. Use `<defs>`.

## Worked example

The reference `findings-pipeline.svg` uses **Strategy A** (theme-neutral) — single `#6e7681` palette, no media query. The trade-off was deliberate: the diagram has six visual rows in the middle column, so any media-query failure mode would have been highly visible. Strategy A guarantees the same readable rendering everywhere at the cost of some per-theme contrast.

For a Strategy B example, see (TBD — first theme-aware diagram authored against this skill will be linked here).
