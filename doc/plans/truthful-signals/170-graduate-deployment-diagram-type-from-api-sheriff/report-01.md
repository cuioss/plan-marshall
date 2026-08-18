# Run report — 170-graduate-deployment-diagram-type-from-api-sheriff (run 01)

**Date (UTC):** 2026-08-18    **Branch:** `claude/deployment-diagram-graduation-536j1k` (harness-assigned, kept as-is)    **PR:** _pending_    **Outcome:** _pending_

## Skills loaded

Loaded by bundle path (`marketplace/bundles/{bundle}/skills/{skill}/SKILL.md`); the `plan-marshall`
plugin was not relied on.

| Skill | Why |
|---|---|
| `cloud-plan-lane` (`.claude/skills/`) | The working contract; first action of the run |
| `plan-marshall:ref-code-quality` | Always |
| `pm-plugin-development:plugin-script-architecture` | Always |
| `pm-plugin-development:plugin-architecture` | `SKILL.md` / bundle structure is the surface |
| `pm-documents:ref-svg-diagrams` (target skill, read in full) | The skill being amended |

Not loaded, with reason: `pm-dev-python:*` and `pm-plugin-development` test standards (no Python in
the diff), `pm-documents:ref-asciidoc` (no `.adoc` changed), `plan-marshall:persona-security-expert`
(no security-relevant surface). No named skill was unobtainable.

## STOP CONDITION — resolved

The plan's stop condition was that the source standard and template live in another repository this
clone cannot reach, and that the run must halt after D1 if they are not supplied. They **were**
reachable: the operator supplied the source URL, and `cuioss/api-sheriff` is public, so the session's
git proxy served an anonymous shallow clone to `/workspace/cuioss/api-sheriff`. Its `HEAD` is
`f236406bfef47c1fde833defd5c71b4380e8aef4` — the exact commit the operator named. Nothing was
reconstructed from the plan's summary; both files were read from that clone.

## Deliverables

### D1 — GATE: graduation set and reference-implementation column

Decisions, with the artifacts that back them. Mutates nothing; recorded here.

**Graduation set: the standard AND the template.** Confirmed against the skill's own contract, by
quoted phrase rather than by line: `SKILL.md` § Enforcement states *"Per-diagram-type standards live
under `standards/diagram-type-{name}.md`."*, and the Templates table gives every row an owning
standard in its `Pairs with` column. A template landed alone would have had nothing to name there.

**Reference-implementation column: option (a) — the row carries an explicit "no reference
implementation".** The plan flagged that if even one existing type row already lacked a reference
implementation, the asymmetry concern evaporates. It does not: all five pre-existing type rows named
one, and all five files exist (`findings-pipeline.svg`, `plan-worktree-topology.svg`,
`post-execute-shipping-flow.svg`, `audit-trail-layers.svg`, `build-dispatch-sequence.svg`), as does
`phase-lifecycle.svg` for the state row this run indexed. The asymmetry is real and is stated in the
row rather than hidden.

Option (b) — authoring a native deployment diagram — was rejected on a fact about this repository,
not on effort: it is a Claude Code marketplace of skills and documentation and runs no deployment
topology, so a native reference implementation would have to be synthetic. The plan's own Notes
require the opposite ("a synthetic example would be a weaker artifact than the one being graduated
away from"). Option (c) was rejected up front by the plan.

**Landing mode: authored-and-indexed, not a placeholder.** The skill's placeholder pattern was a
bulleted "Future per-diagram-type standards (placeholder — not yet authored)" list under the
Standards table. That pattern is for a standard that does not exist; this one does, complete. It
therefore belongs in the table. (That list is also where a pre-existing falsehood was found — see
§ Findings, F1.)

### D2 — the standard and the template landed

`marketplace/bundles/pm-documents/skills/ref-svg-diagrams/standards/diagram-type-deployment.md`
(375 lines, from a 437-line source) and
`marketplace/bundles/pm-documents/skills/ref-svg-diagrams/templates/deployment-diagram-skeleton.svg`
(134 lines, from a 129-line source), in commit `21267da`.

Every difference from the source, and why:

| Change | Reason |
|---|---|
| `## Upstream graduation` section (24 lines) deleted | D2 requires it dropped: it explains that the document intends to move upstream, which is false once upstream is where it is |
| `## Reference implementation` section (37 lines) deleted | Project-specific: it described the api-sheriff integration-test and compose-sample topologies |
| Opening `Reference implementation:` line replaced with an explicit "none in this repository" | D1(a) |
| `pm-documents:ref-svg-diagrams/standards/*.md` → relative Markdown links | The sibling standards use relative links; the source itself named this substitution as the mechanical graduation step |
| `pm-documents:ref-svg-diagrams/SKILL.md § Step 4` → `../SKILL.md` § Step 4 | Same |
| `doc/resources/templates/deployment-diagram-skeleton.svg` → `../templates/deployment-diagram-skeleton.svg` | Matches `diagram-type-stack.md`'s form exactly |
| Container render recipe: output path `.plan/temp/` → a mounted `/out` scratch volume | Two grounds, neither of them "`.plan/temp/` is the wrong temp directory" — in *this* repository it is the mandated one (`CLAUDE.md` § Workflow Discipline). First, this is a **marketplace skill**: it ships to consumer repositories, which have no `.plan/` at all, so a recipe hard-coding that path is broken for most of its readers. Second, the path is *inside the repository*, which contradicts the section's own closing sentence ("write it under a scratch directory"); the mounted volume makes that sentence true of the recipe, which it was not before. `/tmp` alone would not do — the container is `--rm`, so an unmounted path is discarded before the read-back |
| `(integration-test-topology.svg)` file-naming example → `({subject}-topology.svg)` | Named a file that exists only downstream |
| Inset rule reworded — see F4 | A truth correction; the numbers are unchanged |
| Template header comment restructured to the sibling templates' form; nesting depth corrected; a derived y-coordinate corrected | See F5, F6 |

Marketplace documentation rules: no version history, no timestamps, no dated sections and no
"recently added" framing were introduced or survived. Verified by sweep — no residue of `api-sheriff`,
`pm-documents:` notation, `.plan/`, or the dropped sections remains in the landed standard.

### D3 — indexed in the skill

Both rows added to `SKILL.md`, matching the existing column contract.

The plan required a **cold read** of the amended tables as the test of the column contract. A
sub-agent was given the two tables and nothing else, with no repository access, and asked which
standard governs the deployment template. It answered `standards/diagram-type-deployment.md` from
Table B's `Pairs with` column and reported the answer **unambiguous, no inference needed**. The
column contract is matched.

That cold read also produced findings F26–F29.

**Adjacent prose counts: none exist.** The plan flagged a hand-written count next to a growing table
as this epic's most-repeated defect and asked for it to be re-derived or removed. A sweep of
`ref-svg-diagrams/SKILL.md`, `marketplace/bundles/pm-documents/README.md`, and every `.md`/`.adoc` in
the repository mentioning "diagram type" found **no numeric count of diagram types or templates
anywhere**. The claim is refuted; there was nothing to correct. Two non-numeric stale-prone
constructs *in `SKILL.md`* were found and removed instead — an intro enumeration of type names
(F30) and an authoring-order ordinal in § Related (F31). Three further ordinals of the same kind, in
the type standards rather than beside the tables, are F11, F12 and the state standard's.

### D4 — downstream retirement proposal (for the operator; NOT executed)

Not attempted from this run, per the plan and the lane. Recorded here as an actionable proposal.
Unlike the plan's expectation, the downstream referrers **could** be enumerated rather than sampled:
`cuioss/api-sheriff` is public and was cloned read-only at `f236406`.

**Two files to remove downstream:**

- `doc/development/diagram-type-deployment.md`
- `doc/resources/templates/deployment-diagram-skeleton.svg`

**Ordering is upstream-first, downstream-second.** The downstream README must never link to a skill
path that does not yet exist, so the downstream change waits until this PR is merged.

**Referrers found — four files, not the two the plan sampled:**

| File | What it does | Action |
|---|---|---|
| `doc/development/README.adoc` (~line 106) | Table row linking `diagram-type-deployment.md`, whose description ends *"Written in Markdown, deliberately, so it can graduate upstream unchanged."* | Repoint at the upstream skill; that closing sentence is transitional and must go with the move |
| `doc/development/integration-test-topology.adoc` (3 sites, ~lines 24, 249, 274) | Three `link:diagram-type-deployment.md[…]` references, in the drawn-to-standard note, the re-render obligation, and the read-back obligation | Repoint all three |
| `doc/resources/diagrams/integration-test-topology.svg` (line 8) | Header comment `see doc/development/diagram-type-deployment.md` | Repoint |
| `doc/resources/diagrams/compose-sample-topology.svg` (line 5) | Same header comment | Repoint |

⛔ **A whole-repository sweep is still required before removal.** The four above came from one
`grep -rIl` over one commit of one clone; a repository evolves, and a reference can be phrased in a
way that grep for these two file names does not catch (a prose mention, a docs index, a CI check, a
link with different casing). Treat the table as the current best enumeration, not as proof of
completeness.

⚠ **The graduated standard is not byte-identical to the downstream one** (see the D2 table), so this
is a retire-and-repoint, not a `git mv`. The downstream reference implementations
(`integration-test-topology.svg`, `compose-sample-topology.svg`) and their `.adoc` stay where they
are — they are consumer content, explicitly out of scope.

### D5 — gates

**plugin-doctor: clean.** `./pw quality-gate` reports `total_issues: 0` with an empty `issues[]`,
alongside `ruff … All checks passed!`, `mypy … Success: no issues found in 413 source files`, and
`SPDX-header check passed`. Its coverage line records the gate as marketplace-wide for plugin-doctor.

**Render verification: RENDERED, not carried over.** The plan flagged the downstream "no rasteriser
installed" finding as environment-specific and asked this environment to be tested rather than
assumed. It differs: no `rsvg-convert`, `inkscape`, `convert`/`magick` or `cairosvg` is present, but
**Chromium 141 is** (`/opt/pw-browsers/chromium`, the Playwright build), and Docker is available as
the standard's own documented fallback.

The graduated template was rasterised at 1200 px wide against both GitHub backgrounds — `#ffffff` and
`#0d1117` — via Chromium headless, and **both PNGs were read back** with the Read tool, per the
skill's non-skippable Step 4. The full-page render at 1200 px could not resolve the 12 px footer
caption, so that strip was re-rendered at 2.4× on both backgrounds and read back separately rather
than being passed on a glance.

Step 4 checklist, confirmed against the rendered PNGs and not the markup:

- [x] Every text run legible on both backgrounds — including the 10 px monospace mount labels and the 12 px italic caption.
- [x] Every stroke, arrow and divider visible on both. The 1.0 px `2 2` mount stems survive the raster on white, which is the defect the source standard says the heavier stem exists to prevent; the trust boundary's 2.0 px `8 4` dash is not confusable with them.
- [x] No content clipped at the `viewBox` edges.
- [x] Alignment consistent — every enclosure and leaf label shares its box's left edge.
- [x] Arrow markers terminate on the target box edges; no orphan heads.
- [x] No label collisions, including the trust-boundary label against the network enclosure label.
- [x] Font fallback as intended — sans and monospace both resolved, no serif substitution, no tofu.

**Rasteriser used was Chromium, not `rsvg-convert`.** Recorded rather than glossed: it is a different
engine from the one the standard's recipe names, so a `rsvg-convert`-specific rendering difference
would not have been caught here. Chromium is the closer analogue of GitHub's own rendering surface,
which is where these SVGs are read.

Rendered PNGs were written to the session scratch directory and are not committed, per the standard.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → **empty**. No Python footprint, so the lane's
local build gate takes its docs-only path and `./pw verify` was not run; the merge queue's
`merge_group` run verifies the change before it lands. The plan predicted this and asked for it to be
confirmed from git evidence rather than assumed — it was.

`./pw quality-gate` **was** run regardless, because D5 requires the plugin-doctor gate independently
of the build gate. It is clean (above). The working tree was re-checked after that run for the
`uv.lock` churn the lane warns about: none appeared, and every commit staged explicit paths, never
`git add -A`.

## Claim labels — re-derived

The plan labelled every claim `HYPOTHESIS` and required each to be confirmed or refuted against an
artifact. Each verdict below was derived by this run at the moment of the claim.

| Claim | Verdict | Artifact |
|---|---|---|
| The skill requires per-type standards under `standards/diagram-type-{name}.md` | **CONFIRMED** | `SKILL.md` § Enforcement, by quoted phrase: *"Per-diagram-type standards live under `standards/diagram-type-{name}.md`."* |
| Every templates-table row names its owning standard in the second column | **CONFIRMED** | The `Pairs with` column; 6 of 6 rows after the change, 5 of 5 before |
| Every type row names a reference implementation living in this repository | **CONFIRMED** — and each named file exists | All five pre-existing rows named one — `findings-pipeline.svg`, `plan-worktree-topology.svg`, `post-execute-shipping-flow.svg`, `audit-trail-layers.svg`, `build-dispatch-sequence.svg` — and all five files are present in `doc/resources/diagrams/`, as is `phase-lifecycle.svg` for the state row this run added. D1(a)'s asymmetry concern therefore stands |
| The source standard is ~429 lines and the template ~129 | **REFUTED / CORRECTED** — 437 and 129 | `wc -l` on the api-sheriff clone at `f236406` |
| The standard covers five affordances plus naming, theme strategy and a render recipe | **REFUTED** — the affordance table carries **eight** rows | The § Annotated template table: containment nesting, enclosure labels, trust boundary, trust crossings, protocol + port edge labels, first-party vs external, mounted material, collapsed group |
| The standard contains a graduation statement that must be dropped | **CONFIRMED** | `## Upstream graduation`, 24 lines, source lines 17–40 |
| A prose count of diagram types/templates exists somewhere and will go stale | **REFUTED** — no numeric count exists | Swept `ref-svg-diagrams/SKILL.md`, `marketplace/bundles/pm-documents/README.md`, and every `.md`/`.adoc` in the repository mentioning "diagram type". Two *non-numeric* stale-prone constructs were found and removed instead (F3, F4) |
| No rasteriser is installed, blocking render verification | **REFUTED for this environment** | No `rsvg-convert`/`inkscape`/`convert`/`magick`/`cairosvg`, but Chromium 141 at `/opt/pw-browsers/chromium` and Docker are both present. The downstream finding was against a different environment, as the plan suspected |
| Only two downstream files reference the graduated paths | **REFUTED** — four referrer files | `grep -rIl` over the api-sheriff clone: `doc/development/README.adoc`, `doc/development/integration-test-topology.adoc` (3 sites), `doc/resources/diagrams/integration-test-topology.svg`, `doc/resources/diagrams/compose-sample-topology.svg`. Still treated as a best enumeration, not proof — see D4 |

## Findings

Recorded per instance. Sources: **self** = this run's own reading; **cold-read** = the isolated
sub-agent given only the two amended tables; **verify** = the independent verification sub-agent.

### Stale forward references — one defect class, twelve instances

`diagram-type-state.md` is a complete 151-line standard with an existing reference implementation
(`phase-lifecycle.svg`), and `diagram-type-graph.md` and `diagram-type-sequence.md` are likewise
authored and indexed. Twelve statements across six files said otherwise. The plan's out-of-scope line
("modifying any other diagram type") was **explicitly overridden by the operator** mid-run via
`AskUserQuestion`; the question, its three options and the operator's answer ("Fix index and the state
standard") are recorded in § Operator escalation below.

| # | Site | False statement | Disposition |
|---|---|---|---|
| F1 | `SKILL.md`, under the Standards table | `standards/diagram-type-state.md` listed as *"Future per-diagram-type standards (placeholder — not yet authored)"* | **Fixed** — indexed as a Standards-table row; the placeholder list is gone |
| F2 | `SKILL.md` § When to use this skill | *"the state type is a future placeholder"* | **Fixed** |
| F3 | `standards/diagram-type-block.md` § Use a different diagram type when | *"the (future) sequence diagram type"* | **Fixed** — linked |
| F4 | `standards/diagram-type-block.md`, same list | *"the (future) state-machine diagram type"* | **Fixed** — linked |
| F5 | `standards/diagram-type-block.md`, same list | *"the (future) graph diagram type"* | **Fixed** — linked |
| F6 | `standards/diagram-type-sequence.md`, same list | *"`diagram-type-state.md`, when authored"* | **Fixed** — linked |
| F7 | `standards/diagram-type-sequence.md`, same list | *"`diagram-type-graph.md`, when authored"* | **Fixed** — linked |
| F8 | `standards/diagram-type-graph.md`, same list | *"the (future) sequence / state-machine types"* | **Fixed** — linked |
| F9 | `standards/diagram-type-flow.md`, same list | *"the (future) state-machine type"* | **Fixed** — linked |
| F10 | `standards/diagram-type-state.md`, same list | *"`diagram-type-graph.md`, when authored"* | **Fixed** — linked |
| F11 | `standards/diagram-type-block.md` line 3 | *"The first per-diagram-type standard."* — an authoring-order ordinal that git cannot confirm (every type standard was added in one commit) | **Fixed** — removed |
| F12 | `standards/diagram-type-sequence.md` line 3 | *"Second per-diagram-type standard."* | **Fixed** — removed |

`standards/diagram-type-state.md` line 3 carried the matching *"Third per-diagram-type standard."* and
was removed with them; it is counted inside the operator-authorised state fix rather than as a
thirteenth row, because it is the one instance the operator named directly.

⭐ **Why all twelve rather than the two the operator's option named:** the operator authorised the
index and the state standard. Sweeping for that same claim before fixing it — the lane's
sweep-and-count rule — found it at ten further sites in four sibling files. Correcting 2 of 12 is
precisely the n−1-of-n failure the lane names as the reason a corrected claim keeps reappearing. The
widening is disclosed here and was disclosed to the operator in the run's user-facing reply.

### The graduation itself

| # | Site | Finding | Disposition |
|---|---|---|---|
| F13 | source standard §§ 17–40 | `## Upstream graduation` — transitional by construction | **Fixed** — dropped on landing, per D2 |
| F14 | source standard § Reference implementation | Names the api-sheriff integration-test and compose-sample topologies | **Fixed** — dropped |
| F15 | source standard line 7 | `Reference implementation: doc/resources/diagrams/integration-test-topology.svg` — names a file absent from this repository | **Fixed** — replaced with an explicit "none in this repository", per D1(a). Verified independently that no diagram here is of this type: `extension-topology.svg` and `context-isolation.svg` both declare `diagram-type-block`, and `plan-worktree-topology.svg` is the graph type's reference implementation |
| F16 | source standard § Naming and file conventions | File-naming example `(integration-test-topology.svg)` names a downstream file | **Fixed** — genericised to `({subject}-topology.svg)` |
| F17 | source standard § Render verification | The container recipe wrote PNGs to `.plan/temp/` — a path that does not exist in the consumer repositories this marketplace skill ships to, and that is *inside the repository*, contradicting the section's own closing line ("write it under a scratch directory") | **Fixed** — mounts a scratch volume and writes to `/out`. `/tmp` alone would not do: the container is `--rm`, so an unmounted path is discarded before the read-back |
| F18 | source standard § Layout grid | *"Inset — child box edge to parent box inner edge: **16 px** on every side, at every level"* is not met exactly by any artifact of this type. Measured: in the skeleton, leaf boxes sit 24 px from the network's left edge and 40–64 px above its bottom; in the type's own reference implementation (`compose-sample-topology.svg`) the same 24 px left inset appears. The exact reading is unachievable, because a label band and stacked content govern the vertical clearances | **Fixed** — reworded to *"**At least 16 px** on every side, at every level — a floor, not a target. A larger clearance is not a defect."* The numbers are unchanged; only the false exactness is |
| F19 | source standard § Annotated template | The affordance table described the components as sitting *"at the standard 16 px inset"* — the same false exactness, second site | **Fixed** — *"at or above the standard 16 px inset"* |
| F20 | source template header comment | *"two-level containment nesting"*, while the standard counts the identical `host → network → container` ladder as three levels | **Fixed** — "three-level" |
| F21 | source template header comment line 49 | *"label band 28: children start at y >= 160"*. The network's top is `y=116` and its band is 28, so the floor is **144**. The neighbouring host comment derives its own figure correctly (`72 + 44 = 116`), which is what makes this one an arithmetic slip rather than a different convention | **Fixed** — `>= 144` |
| F22 | source template header comment line 8 | `see doc/development/diagram-type-deployment.md` — a downstream path | **Fixed** — restructured to the sibling templates' house form, which uses `pm-documents:ref-svg-diagrams/standards/…` notation in template headers (the *standards* use plain relative links; the two kinds differ, and each graduated file follows its own kind) |

### Defects in this run's own new prose, caught before the PR

| # | Site | Finding | Disposition |
|---|---|---|---|
| F23 | `standards/diagram-type-deployment.md` § Layout grid | This run's **first** F18 rewording asserted that label bands and content stacking *"routinely push the **top and bottom** clearances well above"* the floor. Measuring the reference implementation showed the deviation also occurs on the **left** (24 px), and that at the host→network level the inset is exactly 16 px on left, right and bottom — so "routinely" over-claimed a distribution this run had not measured, and "top and bottom" was incomplete | **Fixed** — flattened to a claim that asserts no mechanism and no distribution |
| F24 | `SKILL.md` intro | This run inserted its pointer sentence *between* the two original sentences, leaving *"Covers the visual style…"* dangling | **Fixed** — reordered |
| F30 | `SKILL.md` intro | The parenthetical *"(data-flow blocks, sequence, state, dispatch graphs)"* enumerated the covered types and was **already incomplete before this change** — it omitted the flow and stack types, both long since authored and indexed | **Fixed** — replaced with a pointer to the Standards table, which cannot go stale |
| F31 | `SKILL.md` § Related | *"starter for the first supported diagram type"* — an authoring-order ordinal git cannot confirm, of the same kind as F11/F12 | **Fixed** — *"starter for the block diagram type"* |

The two rows above are pre-existing defects in `SKILL.md`, found by the count sweep D3 required.
This run's own new prose produced three more:

| # | Site | Finding | Disposition |
|---|---|---|---|
| F25 | `SKILL.md` § When to use this skill | This run's replacement bullet enumerated all seven type names inline — a fresh stale-prone enumeration introduced by a fix whose purpose was removing one | **Fixed** — replaced with a pointer to the table |

### Cold read of the amended index tables (the plan's D3 test)

The sub-agent had the two tables and nothing else — no repository access, no context.

| # | Finding | Disposition |
|---|---|---|
| — | **The D3 test itself passes.** Asked which standard governs the deployment template, it answered `standards/diagram-type-deployment.md` from the `Pairs with` column and judged the answer *"unambiguous. No inference needed"* | Column contract matched |
| F26 | Two rows both claim "topology" — `diagram-type-graph.md` is *"Graph / topology"* and the new row is *"Deployment / topology"* — and *"nothing in either row distinguishes when a topology belongs to one versus the other"* | **Fixed** — the deployment row now names the discriminator the standard itself states: *"Containment is what separates it from the graph type."* |
| F27 | The new Templates row was the most itemized cell in its table — six enumerated features against two-to-four for its neighbours | **Fixed** — trimmed to its neighbours' level of detail |
| F28 | `diagram-type-state.md` has a standard and a reference implementation but **no template**, while every other indexed type has one. The tables present the deployment gap (annotated) and the state gap (silent) inconsistently | **Not fixed — residue.** Authoring a state skeleton is a new diagram-type deliverable, well outside this plan and outside the operator's authorisation. Recorded in § Residue |
| F29 | The deployment row states the *fact* of having no reference implementation but not its *consequence* — whether a reader should pattern-match against the skeleton instead | **Partially addressed** — the skeleton is named in the Templates row directly beneath, and the standard's § Annotated template says copy-rename-fill is the whole workflow. Judged not worth a further sentence in a table cell; recorded so the judgement is visible rather than silent |

### Operator escalation

The lane permits a run with a reachable operator to escalate a re-scope, and requires the question
and its answer to be recorded here, because a conversation event is not a committed artifact.

**Asked** (via `AskUserQuestion`, after F1/F2 were found while performing D1's instruction to follow
"whichever pattern the skill already uses for a placeholder type"): the placeholder pattern is a list
declaring `diagram-type-state.md` "not yet authored", but that file exists as a complete 151-line
standard with an existing reference implementation, and the plan's out-of-scope forbids "modifying
any other diagram type". Three options were offered: fix the index only (recommended); report only
and change nothing; or fix the index **and** the state standard.

**Answered:** *"Fix index and the state standard"* — the broadest of the three.

**What the run then did, and how it exceeded the letter of that answer.** Sweeping for the claim
before fixing it found the same falsehood at ten further sites in four sibling standards (F3–F10) and
two further ordinals (F11, F12). The run corrected all of them rather than the two the option named,
on the lane's sweep-and-count rule, and disclosed the widening to the operator in its next reply
rather than letting it pass silently. The operator has not been asked to ratify the widening; if it
is unwanted, F3–F12 are a self-contained revert that leaves the graduation and the state fix intact.

### Independent verification sub-agent — round 1

Dispatched read-only against the plan, the diff, and the two api-sheriff sources, with instructions
to account for every source→destination difference and to sweep by consumer kind. It read the diff,
all 11 standards, all 6 templates, `visual-language.md`, `pm-documents/README.md`, the `test/` tree,
`plan-marshall-plugin/extension.py`, and three plugin-doctor analysers. Its findings, renumbered into
this report's sequence:

| # | Site | Finding | Disposition |
|---|---|---|---|
| F32 | `templates/deployment-diagram-skeleton.svg` `<desc>` | *"Left of a trust boundary sits a first-party **gateway**"* — no element in the diagram is a gateway; the box is labelled `first-party component`. "Gateway" is the source repository's subject noun, inherited unchanged. The standard makes `<desc>` normative | **Fixed** — "a first-party component". This is the instance D2's *"written to graft unchanged — verify rather than assume"* was aimed at, and the run's own sweep missed it |
| F33 | `standards/diagram-type-deployment.md` § Layout grid | *"Positions and sizes snap to multiples of 8, per the shared grid rule."* The shared rule (`visual-language.md`) says *"wherever practical, except for centred text"*; the restatement dropped the qualifier and so asserts more than its source. Contradicted by this type's own 28 and 44 px label bands and its 12 px label inset, none a multiple of 8, and by 50 off-grid attribute values in the shipped skeleton | **Fixed** — qualifier restored, and the exceptions named as what sets them (the label baselines in § Enclosure labels). ⭐ This is the **same defect class** as F18, at a site the run's own audit stopped short of |
| F34 | `standards/diagram-type-deployment.md` § Annotated template | *"Dashed `8 4` at 2.0 px running the **full height** of the network"*. Measured: the trust line is `y=152…496` (344 px) inside a network of `y=116…512` (396 px) — 36 px short at the top, 16 at the bottom | **Fixed** — *"running vertically through the network's content area"* |
| F35 | `templates/deployment-diagram-skeleton.svg` header comment | *"exercises **every** affordance of the type:"* introducing a list of **six**, while the standard's affordance table names **eight**. The "every" claim is false as enumerated | **Fixed** — replaced with a pointer to that table, which cannot drift, plus the containment depth as a standalone fact |
| F36 | `report-01.md` § Deliverables, D2 table | The stated reason for moving the render output off `.plan/temp/` was that it is *"a plan-marshall-specific path"* — inverted at the destination, since `CLAUDE.md` mandates `.plan/temp/` for temp files **in this repository**. The change is right; the reason given was not | **Fixed** — restated on the two grounds that hold: the skill ships to consumer repositories with no `.plan/`, and the path was inside the repository |
| F37 | `report-01.md` § Claim labels | *"All **five** pre-existing rows named one"* followed by **six** file names — the sixth belongs to the state row this run added | **Fixed** — five named and attributed, the sixth attributed separately |
| F38 | `SKILL.md` § When to use this skill (as committed at `21267da`) | The replacement bullet enumerated all seven type names beside the table it mirrors | **Already fixed** in `b06a62f`, before the verifier reported; it read the earlier commit. Same finding as F25 |
| F39 | `standards/diagram-type-deployment.md` § Layout grid | The first F18 rewording's mechanism clause named only top and bottom | **Already fixed** in `b06a62f`. Same finding as F23 |
| F40 | Plan premise | The plan's out-of-scope says the graduation *"does not revisit the **five** that exist"*. **Six** diagram-type standards existed on `main` — `diagram-type-state.md` was on disk, merely unindexed. The plan's own count was a casualty of the same defect this run fixed | **Recorded, not fixable here** — the plan is the input, and correcting a landed plan's premise is not this run's business. Noted so the count is not repeated |

**Survivor (condition B), with its bound — F41.** `diagram-type-state.md` is now indexed as one of
seven types, but `templates/` holds six skeletons: there is no `state-diagram-skeleton.svg`. Before
this change the state type was declared a future placeholder, so no author reached § Workflow Step 3
("Copy the matching template from `templates/`") for it; after it, one indexed type of seven has no
template.

- **The bound.** The only reachable consequence is an author following Step 3 for a state diagram and
  finding no file to copy. That path is already closed by the state standard itself, whose
  § Reference implementation ends *"Use it as the template for any sequential-with-back-edge lifecycle
  diagram"* — verified by reading that line, not inferred. So the reader is redirected to
  `phase-lifecycle.svg` by the type's own standard, and the gap costs a redirect, not a dead end.
- **Why it stays open.** Authoring a state skeleton is a new diagram-type deliverable. It is outside
  the plan, outside the operator's authorisation, and would put a second unreviewed SVG in a PR whose
  reviewers are checking a graduation. It is recorded in § Residue as the natural next plan.
- Re-put to the verifier in the stopping round (see below).

**Scope finding — F42, not A- or B-governed, but it must not ship silently.** The verifier's judgement
was that the inset rewrite (F18) and the five sibling-standard edits (F3–F12) are *"good changes on the
evidence I measured"* and are nonetheless real scope beyond the plan's Deliverables and against its
explicit out-of-scope line — so they must appear in the **PR description** as declared scope, with the
operator authorisation named, *"otherwise reviewers checking a graduation meet unexplained normative
churn"*. **Actioned:** both are declared in the PR description, and the escalation is recorded above.

**On the plugin-doctor green — recorded because it bears on what D5 actually proves.** The verifier
audited the analysers rather than trusting the summary: of roughly fifty, exactly one
(`broken-relative-link`) could fire on a defect class this change can introduce, and it passes.
`literal-count-drift` is hard-coded to the `extension-api` and `persona-security-expert` surfaces and
cannot see a stale count in `ref-svg-diagrams`; `historical-prose-in-skills` matches seven narrow
regexes and would not have matched *"The first per-diagram-type standard"* or *"## Upstream
graduation"*; nothing reads SVG geometry, so F32–F34 were structurally unreachable by the gate. **The
gate's green says the links resolve and the frontmatter is well-formed. It says nothing about whether
the graduated prose is true.** For this change the verification sub-agent, not the lint, is the only
guard that covers the real defect classes — which is worth stating plainly in an epic about signals
that look more informative than they are.

**Render re-verification after the round-2 edits.** F32 and F35 changed the template. Both PNGs were
re-rendered on `#ffffff` and `#0d1117` and came back **byte-identical** to the round-1 renders that
were read back — which proves, more strongly than a second read-back could, that the edits touched
only non-rendering nodes (an XML comment and `<desc>`).

