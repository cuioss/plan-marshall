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
| D3 | Index it in the skill | Both rows exist and match the contract | Yes | Yes | Yes | Yes | `SKILL.md:59` Standards row (with the F26 discriminator "Containment is what separates it from the graph type"); `SKILL.md:70` Templates row with `Pairs with` = `diagram-type-deployment.md`. 6 of 6 template rows name an owning standard. Adjacent-count sweep re-derived clean |
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
   slot. The substantive point (block conforms at 11 px) is correct; the absolute is not. The same
   absolute is asserted a second time at `report-01.md:632` (R4-A8), where it is presented as
   *"verified by element count"* — a claimed derivation that does not derive. Raised as **G5**.
3. **Round 2's link counts** (*"9 in the deployment standard, 17 in `SKILL.md`, 19 across the five
   touched siblings"*) are stated without a method. Re-derived at HEAD with an explicit method
   (all `[…](target)` matches, http/anchor/mailto excluded): `SKILL.md` 25 occurrences / **17
   unique** (matches exactly); the deployment standard 10 occurrences / **10 unique**; the five
   touched siblings **20 occurrences / 9 unique**. So the sibling figure of 20 matches on
   occurrences, not on unique targets, and no single counting rule reproduces all three round-2
   numbers. Consistent with round-2-era figures plus later edits, so not a contradiction, but not
   re-derivable as stated.

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

## Adversarial review

**Reviewed by:** an independent agent that did not write this document.

**Checked.** Every one of the four gaps, every deliverable row, and every "swept, clean" claim, at
working-tree HEAD `f816f85c` (not the `5cea6604` this document names — the pm-documents bundle is
byte-identical between them: `git diff --stat ac06e4fc HEAD -- marketplace/bundles/pm-documents/`
is empty, so every line number below is valid at both).

- **Landing facts re-derived, not repeated.** `git show --stat ac06e4fc` → 10 paths, 1424
  insertions, 20 deletions; `report-01.md` 891 lines; `diagram-type-deployment.md` 379 lines;
  `deployment-diagram-skeleton.svg` 135 lines; `git log -- .../ref-svg-diagrams/` lists exactly
  three commits, `ac06e4fc` the newest. All exact.
- **Files opened at HEAD:** `SKILL.md`, `diagram-type-deployment.md` (whole), the skeleton (whole),
  `visual-language.md`, `block-diagram-skeleton.svg`, `pm-documents/README.md`,
  `_analyze_literal_count.py`, `_analyze_historical_prose_in_skills.py`, `report-01.md` §§ D4, D5,
  Residue, and the sibling-standard diffs in `git show ac06e4fc`.
- **Every G1–G4 citation opened at its line.** `:228` / `:232–233` / `:238`, skeleton `:124`,
  `:358–360`, skeleton `:39`, `visual-language.md:43`, `:173–174`, `report-01.md:568–569`. All
  quotations are verbatim and all line numbers are right.
- **G2's six "further absent" affordances re-checked individually** against the skeleton at
  `:74`, `:161`, `:196`, `:236`, `:249`, `:253–255`. All six are genuinely absent: the skeleton
  uses the compose ladder only, carries `own-bar` on three boxes, keeps both mount pills on one
  row, ports every edge label, has no vertical-segment label (the one orthogonal run is labelled
  on its horizontal segment) and no opposite-side label.
- **Render reproduced independently.** `/opt/pw-browsers/chromium` → `Chromium 141.0.7390.37`;
  `rsvg-convert`, `inkscape`, `convert`/`magick` and `cairosvg` all absent, confirming the report's
  environment claim in this environment. I rasterised the skeleton headless at 1400 px on `#ffffff`
  and `#0d1117` and read both PNGs back: legible on both, no clipping, no collision, mount stems and
  the `8 4` trust dash both survive the raster, `own-bar` distinguishable from the plain box.
- **Sweeps re-run with broader patterns than the originals.** For D2, not just `api-sheriff` /
  `gateway` / `## Upstream graduation` but `sheriff|cuioss|cui|quarkus|keycloak|graduat|upstream|
  downstream|\.plan/|TODO|FIXME|previously|no longer|used to be|recently|for now|will be added|
  not yet|when authored|future|migrat|transition|deprecat|newly added|introduc` over the whole
  skill: every hit is benign ("state *transitions*", "*downstream* consumer" in the stack layout
  rule). For D3, not just the noun set the original used but repo-wide
  `(five|six|seven|eight|[0-9]+) (svg |per-)?diagram[- ]?types?` plus the reverse ordering, over
  `*.md`/`*.adoc`/`*.py` outside `doc/plans/` → **zero hits**. `ls skills/ | wc -l` → 11, matching
  `README.md:11`. D3's refutation holds under the wider net.
- **Geometry re-derived from the SVG independently of the document.** Every enclosure label at
  `box_left+12` / `box_top+24` / `+40`; both mount stems centred on their pills (112 on 64+96,
  200 on 168+64) with a 12 px stem, 18 px pill, `x=pill_left+8`, `y=pill_top+13`, 8 px inter-pill
  gap; all three `own-bar` runs inset 8 px top and bottom; all three edge labels 8 px above their
  line at the correct midpoint, the orthogonal run labelled on its 148 px horizontal rather than
  its 88 px vertical; every inset ≥ 16 px; every leaf box ≥ 120 × 48.
- **Link resolution re-derived by script** over `SKILL.md` + all 11 standards → 66 relative links,
  4 unresolvable, all four in `theme-handling.md` (`path/to/…` worked examples) and
  `asciidoc-embedding.md`. Exact match, including the population.
- **Counts re-derived:** `find . -name "_analyze_*.py" | wc -l` → 60; `RULE_ID =
  'no-historical-prose-in-skills'` at `_analyze_historical_prose_in_skills.py:111`;
  `diagram-type-state.md` 151 lines ending on the quoted sentence; `§ CSS additions` present at
  `diagram-type-sequence.md:110` and `diagram-type-state.md:126` and nowhere else;
  `_analyze_literal_count.py` hard-scoped by path tuple to `plan-marshall/skills/extension-api`
  and `plan-marshall/skills/persona-security-expert`, so it structurally cannot see
  `pm-documents`. All six reference-implementation SVGs present in `doc/resources/diagrams/`.
- **D1's completeness claim re-checked against the pre-image**, not just the post-image: the
  Standards table before `ac06e4fc` carried exactly **five** type rows (block, graph, flow, stack,
  sequence) — state was a "not yet authored" placeholder line, not a row — so "five pre-existing
  type rows each naming a reference implementation" is correct as stated, and the six-standards
  figure in § Residue is a statement about the directory, not the table. Both are right.

**NOT re-checked.** (1) `./pw quality-gate` was **not** re-run: the working tree is dirty with other
agents' in-flight work, including an untracked `test/pm-plugin-development/plugin-doctor/
test_zz_pop.py`, so a marketplace-wide gate result now would be a statement about their changes, not
this plan's. Instead I re-derived the one analyser finding that could plausibly fire on this diff
(`broken-relative-link`, above) and confirmed `literal-count-drift` cannot reach this bundle.
(2) The `mypy` file counts (413 / 414). (3) Anything in `cuioss/api-sheriff` — I also made no
attempt to fetch it. (4) The per-commit render ledger, the cold read, the sub-agent transcripts, the
operator escalation, and GitHub state. (5) No mutation test was applied: the change ships no code,
no test and no guard, and the tree was dirty in any case.

| Item | Original claim | Verdict | Evidence |
|---|---|---|---|
| G1 | `:228` "protocol in upper case" is falsified by `:232–233`, `:238` and skeleton `:124` | **upheld**, severity `medium` correct | All four sites read verbatim. `gRPC :9000` and `mTLS :8444` sit four lines below the rule; `:238` makes `mTLS` normative; the skeleton ships `gRPC :9000` at `:124`. A shipped normative rule an author acts on and is wrong — above a dead sentence, below wrong behaviour |
| G2 | `:358–360`'s absent-affordance apposition reads complete and is not | **upheld**, severity `medium` correct | Sentence read verbatim; all six further absences confirmed one by one against the skeleton (line refs above). The three named absences are not a different *kind* of item from the six, so the split is unprincipled, not a definitional defence |
| G3 | Skeleton `.caption` is 12 px against `visual-language.md:43`'s 11 px, with no type-standard override | **upheld**, severity `low` correct | `.caption` grep across `templates/` → 12 px in deployment, flow, graph, sequence, stack; block has no `.caption` and its `.col-sub` is 11 px. `diagram-type-deployment.md` fixes no caption size (grep for `caption`/`px` returns geometry only), and `:10–13` explicitly delegates typography to `visual-language.md` — so the rationale holds at its source, not only by reading |
| G4 | `report-01.md:569`'s mount-stem row is falsified by its own R4-A11 fix | **upheld**, severity `low` correct | Row read verbatim at `:569`. `:173` `x1="144"`, `:174` `x="96" width="96"` → centre 144: the worked example *does* centre. The underlying residue (no rule) is real, so the row is corrected rather than deleted, exactly as the Fix says |
| G5 | — | **added** | Second instance of the same defect class as G4, in the same section of the same file, previously recorded only as prose imprecision #2. Findings are recorded per instance |
| D1 row | Clean pass; five pre-existing rows all name a reference implementation | **upheld** | Checked against the *pre-image* of `SKILL.md`, which is the only place the claim is falsifiable. Five type rows, five named implementations, all files present |
| D2 row | Clean sweep for consumer-specific and transitional text | **upheld under a much broader pattern** | 25-alternative sweep over the whole skill; no consumer reference, no graduation statement, no transitional prose survives |
| D3 row | Both index rows match the contract; adjacent-count sweep clean | **re-evidenced** | Rows confirmed, but the cited lines were **wrong**: the Standards row is `SKILL.md:59` and the Templates row `SKILL.md:70`, not `:64` / `:75`. Corrected in the table. 6 of 6 template rows name an owning standard. The count sweep was re-run repo-wide and stays clean; `SKILL.md:58`'s "the one type with no skeleton" and `:72`'s "the state type has no starter here" are themselves accurate completeness claims (6 skeletons, 7 types) |
| D4 row | Clean pass on report content | **upheld** | `report-01.md:117–143` read in full: two files named, four referrers with line numbers and a per-file action, upstream-first ordering stated with its reason, and `:134–138` states the whole-repository sweep is still owed and the table is "the current best enumeration, not proof". Every done-when clause is present. Content beyond this repository still unverified |
| D5 row | Gate clean + render verdict explicit | **upheld on the render half, narrowed on the gate half** | Render reproduced independently on both backgrounds; `report-01.md:151–178` gives an explicit "RENDERED, not carried over" verdict with the engine, the scale, the read-back and the 12 px-caption limitation. The gate was not re-run (dirty tree) — see NOT re-checked |
| Verdict | `implemented-with-gaps` | **upheld** | All five deliverables are implemented and their done-when conditions met; the open items are false or incomplete statements inside shipped documentation, none of which leaves a deliverable undone. `partially-implemented` would be wrong |
| Report accuracy #3 | "20 for the siblings" presented as a unique-target count | **rewritten** | Re-derived: 20 is the occurrence count; the unique count is 9. The stated method and the stated figure did not agree |
| Method, render bullet | "read all three PNGs back" after describing two backgrounds at two scales | **noted, not corrected** | The arithmetic does not close (2 × 2 = 4), but it is a claim about the author's own past actions and cannot be re-derived from the tree. Left as written rather than replaced with a guess |

**Documents corrected.** In `verification.md`: the D3 evidence cell's two wrong `SKILL.md` line
numbers (`:64` → `:59`, `:75` → `:70`); Report accuracy #3 rewritten with an explicit counting
method and the occurrence/unique split; Report accuracy #2 extended with the second site of the same
false absolute and a pointer to G5. In `gaps.md`: G5 added; the open-item count raised 4 → 5; the
lead paragraph's "All four" updated; a `## Refuted during adversarial review` section added
recording that nothing was refuted and why that is a result rather than an omission. No severity was
changed — all four original severities survive the rubric, and no gap was found to duplicate,
split or refute.

**Residual doubt, in the order a third reviewer should take it.** (1) The **quality gate has not been
independently re-run** since the tree went dirty; it is the one clean-pass half of this verification
that rests on the report's own word plus a targeted substitute. Re-run it on a clean checkout of
`ac06e4fc`. (2) **`cuioss/api-sheriff` remains entirely unfetched** by both reviewers — D4's two
file paths, four referrers and their line numbers are the largest block of unchecked factual claims
in the report, and the repository is public at `f236406`. (3) **The report's `§ Findings` tables
were sampled, not swept.** Both reviewers concentrated on `§ Residue`, where two of the five
falsified rows were found; the round-1-to-round-4 finding tables carry ~50 disposition cells of the
same mutable-quote construction that produced G4 and G5, and nobody has read them against HEAD.
(4) The `§ Annotated template` affordance table (`:362–371`) certifies eight placeholders as present
and correctly shaped; I re-derived the geometry of all eight, but a fifth reviewer should check the
*wording* of each row against the rule it summarises — that pairing is what produced G1.
