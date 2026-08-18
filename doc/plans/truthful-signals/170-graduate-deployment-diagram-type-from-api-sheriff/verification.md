# Verification — 170-graduate-deployment-diagram-type-from-api-sheriff

**Verified against:** commit `5cea6604a2a934fd6b7567bf44e4118ead017a5a`   **Landed as:** PR #1296, commit `ac06e4fc94782328f87d1395472a72b7e7a8559d`   **Verdict:** implemented-with-gaps

## Method

Read `plan.md` and all 891 lines of `report-01.md` in full. Located the landed commit
(`ac06e4fc`, the squash of PR #1296) and read its full diff and file stat: 10 paths, 1424
insertions — `plan.md` (rename only), `report-01.md` (new), `SKILL.md`, five sibling type
standards, `standards/diagram-type-deployment.md` (new, 379 lines),
`templates/deployment-diagram-skeleton.svg` (new, 135 lines). `git log --oneline --
marketplace/bundles/pm-documents/skills/ref-svg-diagrams/` confirms **no later commit** touches
the skill, so HEAD is the landed state and nothing here is superseded.

Files opened at HEAD: `SKILL.md`, all seven `diagram-type-*.md` standards,
`visual-language.md`, `theme-handling.md`, `asciidoc-embedding.md`, all six
`templates/*.svg`, `marketplace/bundles/pm-documents/README.md`,
`plugin-doctor/scripts/_analyze_literal_count.py`, `test/marketplace/test_extension_profiles.py`.

Commands run and what they returned:

- `./pw quality-gate` at HEAD → `status: pass`, `total_issues: 0`, empty `issues[]`, ruff/mypy
  (414 files)/SPDX all green, plugin-doctor marketplace-wide. **D5's plugin-doctor claim
  independently reproduced** (the report's "413 source files" was its own commit; 414 today
  reflects later unrelated plans).
- `find . -name "_analyze_*.py" | wc -l` → **60**, reproducing the report's corrected analyser
  population exactly.
- `grep` for `RULE_ID`/`rule_id` → `broken-relative-link`, `literal-count-drift`,
  `no-historical-prose-in-skills`, `tmp-redirect-in-skills` all exist; `_analyze_literal_count.py`
  read in full and confirmed hard-scoped to `extension-api` and `persona-security-expert`, so it
  cannot see a stale count in `ref-svg-diagrams` — the report's claim, checked at the source.
- Python script resolving every relative Markdown link in `SKILL.md` + all 11 standards → 66
  links, 4 unresolvable, **all four pre-existing** in `theme-handling.md` (`path/to/file.svg`
  worked examples) and `asciidoc-embedding.md`; none in a file this plan touched.
- `xml.etree.ElementTree` parse of the skeleton → well-formed; `viewBox 0 0 1000 620`,
  `role="img"`, `aria-labelledby="title desc"`. Script-derived max rect extent `(976, 528)`,
  inside the `viewBox`.
- **Rendered the skeleton myself** with the same engine the report names: `/opt/pw-browsers/chromium`
  reports `Chromium 141.0.7390.37` (the report's claim, confirmed). Rasterised on `#ffffff` and
  `#0d1117` at 1200 px and again at 2400 px, and **read all three PNGs back** with the Read tool.
  Everything legible on both grounds; the 12 px footer caption is *not* resolvable in the 1200 px
  render and is at 2400 px — independently reproducing the exact limitation the report records
  and the reason it re-rendered that strip.
- Re-derived by hand from the SVG coordinates: every one of the eight § Annotated-template
  affordance rows, the inset/label-band/radius ladder, `own-bar` 8 px corner insets, mount pill
  widths and the 8 px inter-pill gap, all three edge-label placements (including the longest
  segment of the orthogonal run), and both `trust-cross` intersections. All check out.
- Re-derived the depth-5 arithmetic in § Containment nesting: `1000 − 48 − 8×16 = 824 ≈ 820`;
  `620 − 48 − 4×44 − 4×16 = 332 ≈ 330`. It re-derives.
- Re-derived the D3 "no adjacent count" sweep: `grep -rniE "(one|…|ten|[0-9]+) (diagram )?(types|
  templates|skeletons|standards)"` over `marketplace/bundles/pm-documents/` → **zero hits**. The
  only numeric count in `pm-documents/README.md` is `### Skills (11 registered)`, and
  `ls skills/ | wc -l` → **11**, so it is accurate and untouched by this plan.
- `git status --porcelain` at the end shows only sibling agents' output files and my own two;
  nothing was mutated. No mutation test was applicable — the change adds no guard, no code and no
  test; there is nothing to break and re-run.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D1 | GATE: graduation set + reference-implementation column | Both decisions recorded with reasons | Yes | Yes | Yes | Yes | `report-01.md` § D1. Option (a) verified: 5 pre-existing type rows each name a reference implementation and all 5 files exist in `doc/resources/diagrams/`, as does `phase-lifecycle.svg` — `ls doc/resources/diagrams/`. Option (c) was rejected by the plan itself |
| D2 | Land the standard and the template | Both exist upstream, comply with marketplace doc rules | Yes | Yes | **Mostly** | **No** | `standards/diagram-type-deployment.md` (379 L), `templates/deployment-diagram-skeleton.svg` (135 L). Sweep for `api-sheriff`, `gateway`, `integration-test-topology`, `compose-sample-topology`, `## Upstream graduation`, `.plan/temp` → **CLEAN**. But see G1 (`protocol in upper case` self-contradicted at line 228 vs 232) and G2 (line 358's absent-affordance enumeration reads as complete and is not) |
| D3 | Index it in the skill | Both rows exist and match the contract | Yes | Yes | Yes | Yes | `SKILL.md:64` Standards row (with the F26 discriminator "Containment is what separates it from the graph type"); `SKILL.md:75` Templates row with `Pairs with` = `diagram-type-deployment.md`. 6 of 6 template rows name an owning standard. Adjacent-count sweep re-derived clean |
| D4 | Record downstream retirement as an operator proposal | Report records files, ordering, repointing, sweep-required | Yes | Yes | Yes | Yes | `report-01.md` § D4 names both files to delete, four referrer files with line numbers, upstream-first ordering, and states the enumeration is a best enumeration not proof. Cross-repo content **not verifiable from this clone** — see below |
| D5 | Gates: plugin-doctor clean + render question resolved | Gate clean; explicit render verdict | Yes | Yes | Yes | Yes | `./pw quality-gate` re-run at HEAD → `status: pass`, `total_issues: 0`. Render verdict is explicit ("RENDERED, not carried over") with a per-commit ledger; I reproduced the render on both backgrounds with the same Chromium 141 |

**D2 — the two defects.** `standards/diagram-type-deployment.md:228` fixes the edge-label format as
*"protocol in upper case"*, and the example block four lines below at `:232–233` contains `gRPC :9000`
and `mTLS :8444`, neither of which is upper case; `:238` then makes `mTLS` normative in its own right,
and `templates/deployment-diagram-skeleton.svg:124` ships `gRPC :9000` as the worked placeholder. The
rule is falsified by its own examples and by the paired artifact — the same class as R2-12 and R2-13,
which the run did fix, at a site four rounds read past. Separately, `:358–360` states *"The
affordances specified above but **absent** from the skeleton — the numbered-leg convention and its
legend block, the closed-`rect` boundary form, and nesting past depth 3 — are authored from this
document"*, an apposition that reads as the complete absent set. The report's own § Residue names
**six further** absent affordances (vertical edge-label placement, crowding remedy 1, the mount
wrap-to-second-row, the orchestrated `cluster → namespace → pod → container` ladder, the omit-`:port`
form, and omitting `own-bar` entirely) — I confirmed all six absent from the skeleton by reading it.

## Report accuracy

Every re-derivable figure in `report-01.md` was recomputed at HEAD. **No contradiction was found in
any claim about the shipped skill.** Specifically confirmed:

- 60 `_analyze_*.py` analyser modules (round 2's corrected count) — exact.
- `literal-count-drift` hard-scoped to `extension-api` and `persona-security-expert` — read the
  module docstring and detection section; the claim holds.
- `no-historical-prose-in-skills` is the real `RULE_ID` (R3-A11) — confirmed at
  `_analyze_historical_prose_in_skills.py:111`.
- All six named reference-implementation SVGs exist.
- `diagram-type-state.md` is 151 lines and its last line reads *"Use it as the template for any
  sequential-with-back-edge lifecycle diagram"*; its `viewBox` table offers **four** topologies —
  so R4-A12's scoping of the three `SKILL.md` disclosure sites is accurate.
- All twelve stale forward references (F1–F12) plus the state ordinal are gone; `grep` for
  `future|when authored|not yet authored` over the skill returns nothing.
- The shared 8-grid rule is restated in substance verbatim, exception included (R3-A9).
- No numeric diagram-type/template count exists anywhere (D3's refutation).
- `.caption` is 12 px in deployment, flow, graph, sequence and stack; `block-diagram-skeleton.svg`
  defines no `.caption` and its `.col-sub` is 11 px — R4-A7's re-derived populations are exact.
- Chromium 141 present at `/opt/pw-browsers/chromium`; no `rsvg-convert`, `inkscape`,
  `convert`/`magick`, or `cairosvg`. Proposal 2's evidence holds in this environment too.
- `./pw quality-gate` reproduces `total_issues: 0`.

Three imprecisions, none of them about the shipped skill:

1. **§ Residue, mount-stem row — false at HEAD.** It reads *"The skeleton centres both stems on
   their pills; **the standard's worked example does not**, and neither states a rule."* At HEAD the
   worked example does centre: `diagram-type-deployment.md:173` puts the stem at `x=144` and `:174`
   puts the pill at `x=96 width=96`, centre 144. R4-A11 — recorded in the same report — is what moved
   it from 140 to 144. This is exactly the self-falsifying-disposition mechanism the report itself
   diagnosed, surviving in the section that discloses it. Raised as G4.
2. **§ Residue, footer-caption row** says `block-diagram-skeleton.svg` *"has no footer-caption
   element at all"*. Block carries three `<text class="col-sub">optional footer caption</text>`
   elements (`:49`, `:64`, `:78`), inside the column boxes rather than in a diagram-level footer
   slot. The substantive point (block conforms at 11 px) is correct; the absolute is not.
3. **Round 2's link counts** (*"9 in the deployment standard, 17 in `SKILL.md`, 19 across the five
   touched siblings"*) are stated without a method. Counting unique relative targets at HEAD gives
   17 for `SKILL.md` (exact), 10 for the deployment standard, and 20 for the siblings — consistent
   with round-2-era figures plus later edits, so not a contradiction, but not re-derivable as
   stated either.

## Out-of-scope compliance

The landed diff touches nothing outside `marketplace/bundles/pm-documents/skills/ref-svg-diagrams/`
and this plan's own directory — verified by `git show --stat`. No stray file, no `.plan/` write, no
other plan's directory.

The plan's out-of-scope line *"Modifying any other diagram type"* **was crossed**: five sibling
standards were edited (F3–F12). This is declared rather than hidden — the report records the
`AskUserQuestion` escalation verbatim with the operator's answer ("Fix index and the state
standard"), states plainly that the run went wider than the option named, and the PR description
carries a "Declared scope beyond the plan's deliverables" section naming both the sibling edits and
the geometry rewording. The edits themselves are corrections of false statements, and I confirmed
each landed as described. Compliance: **crossed, disclosed, and authorised in substance.**

D4's cross-repository boundary was respected — nothing outside this repository was changed.

## Residue carried forward

| Report residue item | Still open at HEAD? | Evidence |
|---|---|---|
| Downstream retirement (D4) | **Not verifiable here** — different repository | — |
| No `state-diagram-skeleton.svg` | **Open** | `ls templates/` → 6 skeletons, 7 indexed types |
| Skeleton `<title>` / `<desc>` do not satisfy their own rules | **Open** | `<title>` names no environment; `<desc>` instructs on enumerating a collapsed group but neither enumerates one nor names the boundary, against `:316` |
| Footer caption is an author instruction | **Open** | `skeleton:134` reads "Skeleton only. Replace every label…" |
| No rule for the mount stem's horizontal position | **Open** — but its stated justification is now false | See Report accuracy #1 / G4 |
| `.caption` 12 px vs `visual-language.md`'s 11 px | **Open**, and the new file is one of the five | G3 |
| Ordinals removed deliberately | Closed | Confirmed absent from block/sequence/state line 3 |
| No trust-label placement rule for the open-path form | **Open** | `:297` still places the label "8 px above its top-left corner"; a `<line>` has none |
| No sibling standard routes a reader to the deployment type | **Open** | `grep -i deployment` over the six sibling standards → **no match** |
| Container-rasteriser recipe homed in one type standard | **Open** | Recipe only at `diagram-type-deployment.md:326–349` |
| Six affordances with no skeleton placeholder | **Open** — and mis-stated in the shipped doc | G2 |
| No § CSS additions section for deployment | **Open** | Sequence (`:110`) and state (`:126`) have one; deployment has none |
| Skeleton's trust geometry puts the external component on the authenticated side | **Open** | External box `x=744` is right of the boundary at `x=470` |
| `SKILL.md` § Related names one of six templates | **Open** | `SKILL.md:129` |
| `diagram-type-sequence.md` has a template but no § Annotated template | **Open** | Its `## ` headings carry no such section |
| § D2 difference table complete for `21267da`, not HEAD | Stated, no action | — |
| The plan's "five diagram types" premise | Noted; the plan is the input | Six standards existed on `main` |

## What could NOT be verified

- **Anything about `cuioss/api-sheriff`.** The source standard's 437/129 line counts, the
  `## Upstream graduation` section at source lines 17–40, the four downstream referrer files and
  their line numbers, and D4's whole enumeration are claims about a repository this clone does not
  contain. I made no attempt to fetch it. D4's *content* is therefore unverified; only its
  *presence and actionability in the report* are verified.
- **The run's own render history.** The per-commit render ledger records what the run rasterised
  and read back at four intermediate commits. That is a claim about past actions, not about the
  tree. I verified the current skeleton renders and reads back cleanly on both backgrounds with
  the engine named, which corroborates the practice but cannot confirm the per-commit record.
- **The cold read and the four verification sub-agents' transcripts.** Not artifacts in the tree.
  Their *outputs* are verifiable and were verified where they touch files.
- **The operator escalation.** A conversation event, recorded in the report; no committed artifact
  backs it. The PR description's declared-scope section is consistent with it.
- **Reviewer participation and the merge-gate record.** GitHub state, not tree state; not checked.
