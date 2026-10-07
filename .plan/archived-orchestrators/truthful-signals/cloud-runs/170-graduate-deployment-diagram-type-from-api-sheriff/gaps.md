# Gaps — 170-graduate-deployment-diagram-type-from-api-sheriff

**Source:** verification.md (same directory)   **Open items:** 5

All five are small. The graduation itself landed: the standard, the skeleton and both index rows
exist, comply with their own contract, render legibly on both GitHub backgrounds, and pass
`./pw quality-gate` (`total_issues: 0`, re-run at HEAD). Nothing below blocks or misleads about
what runs where; each is a false or incomplete statement inside documentation whose subject is
truthful statements.

## G1 — Reconcile "protocol in upper case" with `gRPC` and `mTLS`

- **Kind:** stale-statement (internal contradiction)
- **Severity:** medium
- **Where:** `marketplace/bundles/pm-documents/skills/ref-svg-diagrams/standards/diagram-type-deployment.md:228` — § Protocol and port edge labels, the **Format:** line
- **What is wrong:** The rule reads *"`PROTOCOL :port` — protocol in upper case, single space, colon
  immediately followed by the port number with no intervening space."* The example block four lines
  below (`:232–233`) contains `gRPC :9000`, `mTLS :8444` and a bare `mTLS`, none of them upper case;
  `:238` then makes `mTLS` normative in its own right (*"`mTLS` is written as a protocol in its own
  right when mutual authentication is the fact the reader needs"*); and the paired skeleton ships
  `gRPC :9000` as a worked placeholder at
  `templates/deployment-diagram-skeleton.svg:124`. Three artifacts refute the rule, one of them in
  the same document four lines away.
- **Why it matters:** An author who follows the rule literally writes `GRPC :9000` and `MTLS :8444`,
  producing labels the standard's own example list and its own skeleton contradict. This is the same
  defect class as R2-12 and R2-13, both of which this run found and fixed elsewhere in the same file;
  it survived four verification rounds because no round read the format rule against the example
  block beneath it.
- **Fix:** Reword `:228` so the casing rule matches practice — e.g. *"protocol written in its
  conventional casing, which is upper case for the common wire protocols (`HTTPS`, `HTTP`, `TCP`,
  `WS`) and the vendor casing where one is established (`gRPC`, `mTLS`); single space; colon
  immediately followed by the port number with no intervening space."* Do not change the examples or
  the skeleton — they are the ground truth here.
- **Done when:** No example in `:232–233`, and no edge label in the skeleton, contradicts the casing
  sentence at `:228`.
- **Module/topic:** `pm-documents:ref-svg-diagrams` — `standards/diagram-type-deployment.md`

## G2 — Stop presenting the absent-affordance list as complete

- **Kind:** incomplete-sweep (false completeness)
- **Severity:** medium
- **Where:** `marketplace/bundles/pm-documents/skills/ref-svg-diagrams/standards/diagram-type-deployment.md:358–360` — § Annotated template
- **What is wrong:** The sentence reads *"The affordances specified above but **absent** from the
  skeleton — the numbered-leg convention and its legend block, the closed-`rect` boundary form, and
  nesting past depth 3 — are authored from this document"*. The em-dash apposition identifies the set,
  so a reader takes it as the complete list of absences. It is not: `report-01.md` § Residue names six
  further affordances the skeleton has no placeholder for, and I confirmed each absent by reading the
  skeleton — vertical edge-label placement (`:249`), crowding remedy 1 (`:253–255`), the mount
  wrap-to-second-row (`:196`), the orchestrated `cluster → namespace → pod → container` ladder
  (`:74`), the omit-`:port` form (`:236`), and omitting `own-bar` entirely (`:161`).
- **Why it matters:** R3-A2 was raised precisely because this section over-claimed what the skeleton
  covers; the fix narrowed the *positive* promise to the affordance table but replaced it with a
  *negative* enumeration that is itself incomplete. An author who reads it stops looking after three
  items and reproduces the gap the fix was meant to close.
- **Fix:** Make the sentence non-enumerative — state that the table below is the set the skeleton
  covers and that **any** affordance specified in this document but not appearing in that table is
  authored from the document, then keep the three named items as examples introduced by "for
  example" or drop them. Either wording removes the completeness claim without needing the list to
  be maintained.
- **Done when:** § Annotated template contains no closed enumeration of what the skeleton lacks, and
  the six affordances named in § Residue are no longer contradicted by the shipped text.
- **Module/topic:** `pm-documents:ref-svg-diagrams` — `standards/diagram-type-deployment.md`

## G3 — Bring the new skeleton's `.caption` to the shared 11 px

- **Kind:** doc-drift (new artifact diverging from the shared standard)
- **Severity:** low
- **Where:** `marketplace/bundles/pm-documents/skills/ref-svg-diagrams/templates/deployment-diagram-skeleton.svg:39` — the `.caption` rule in the `<style>` block
- **What is wrong:** `.caption { font-size: 12px; … }`. `standards/visual-language.md:43` fixes
  *"Caption / footer / annotation | sans-serif stack | **11 px** | 400 | italic"*, and
  `diagram-type-deployment.md` fixes no caption size of its own, so nothing in this type's standard
  authorises the override. The report declares the divergence as residue, but its bound — *"Four of
  the five are templates this run did not touch"* — leaves out that the fifth is the file this run
  authored, where the value was free to choose.
- **Why it matters:** The graduation added a sixth artifact to a five-instance drift instead of
  landing the one instance it controlled in conformance, and the type standard's own preamble tells
  the reader that typography comes from `visual-language.md` unless this document fixes it.
- **Fix:** Change `font-size: 12px` to `font-size: 11px` in the deployment skeleton's `.caption`
  rule, re-render on `#ffffff` and `#0d1117` and read both PNGs back (the caption is the element the
  1200 px render already cannot resolve, so re-render that strip at 2.4× as well). Fixing the other
  four templates is a separate change — see the § Residue item covering all five.
- **Done when:** `grep '\.caption' templates/deployment-diagram-skeleton.svg` shows `11px`, and the
  re-rendered caption is confirmed legible on both backgrounds.
- **Module/topic:** `pm-documents:ref-svg-diagrams` — `templates/`

## G4 — Correct the mount-stem residue row, which its own fix falsified

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/170-graduate-deployment-diagram-type-from-api-sheriff/report-01.md:569` — § Residue, the row *"No rule for the mount stem's horizontal position"*
- **What is wrong:** The row reads *"The skeleton centres both stems on their pills; **the
  standard's worked example does not**, and neither states a rule."* At HEAD the worked example does
  centre: `diagram-type-deployment.md:173` puts the stem at `x=144` and `:174` puts the pill at
  `x=96 width=96`, whose centre is 144. R4-A11 — recorded in the same report, in the same round —
  is what moved that attribute from 140 to 144. The underlying residue (no *rule* fixes the stem's
  `x`) is still real; only the justification is false.
- **Why it matters:** The report diagnoses at length that its own disposition and residue cells
  quote mutable text and are silently falsified by later fixes, and proposes a contract change to
  stop it. This row is that mechanism still operating inside the section that discloses it — and it
  understates how cheap the remedy now is, since both the skeleton and the worked example already
  agree on the convention a rule would state.
- **Fix:** Edit the row to say that the skeleton and the standard's worked example both centre the
  stem on its pill and that no rule states the convention, so a follow-up can simply write the
  existing behaviour down. Do not delete the row — the residue is open.
- **Done when:** The row's factual clause matches `diagram-type-deployment.md:173–174` at HEAD, and
  the follow-up it points to is described as writing down an already-consistent convention.
- **Module/topic:** `doc/plans/truthful-signals/` run reports — cloud-plan-lane report hygiene

## G5 — Correct the footer-caption residue row's false absolute about `block-diagram-skeleton.svg`

- **Kind:** stale-statement (false absolute, asserted as verified)
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/170-graduate-deployment-diagram-type-from-api-sheriff/report-01.md:568` — § Residue, the row *"The skeleton's footer caption is an author instruction, not diagram content"*; the same absolute is restated at `report-01.md:632` (finding R4-A8)
- **What is wrong:** The row reads *"four of the five sibling skeletons use that slot for a
  type-descriptive caption, and `block-diagram-skeleton.svg` **has no footer-caption element at
  all**"*. `block-diagram-skeleton.svg` carries three of them —
  `<text class="col-sub">optional footer caption</text>` at `:49`, `:64` and `:78`, one per column
  box. What is true is narrower: block has no `.caption` **class** and no diagram-level footer slot,
  putting its footer captions inside the column boxes at 11 px via `.col-sub`. R4-A8 at `:632`
  introduced this absolute while correcting the row's population, and recorded it as *"verified by
  element count"* — an element count that, run today, returns three.
- **Why it matters:** This is the same defect as G4, at a second site in the same section of the same
  file, and it is the more serious of the two because the false clause is presented as the *product*
  of a derivation. It is also load-bearing for G3: block's `.col-sub` at 11 px is the evidence that
  the shared 11 px caption rule is satisfiable in a skeleton, and a reader who believes block has no
  footer caption at all loses that evidence. A finding is recorded per instance, so this is filed
  separately from G4 rather than folded into it.
- **Fix:** Edit `report-01.md:568` to say that `block-diagram-skeleton.svg` defines no `.caption`
  class and no diagram-level footer slot, and instead carries three per-column
  `<text class="col-sub">optional footer caption</text>` elements at 11 px. Edit the R4-A8 row at
  `:632` to match, and drop or qualify its *"verified by element count"* claim, which is what made
  the false absolute look checked.
- **Done when:** Neither `report-01.md:568` nor `:632` asserts that `block-diagram-skeleton.svg` has
  no footer-caption element, and `grep -c 'optional footer caption'
  marketplace/bundles/pm-documents/skills/ref-svg-diagrams/templates/block-diagram-skeleton.svg`
  → `3` no longer contradicts either row.
- **Module/topic:** `doc/plans/truthful-signals/` run reports — cloud-plan-lane report hygiene

## Refuted during adversarial review

**None.** An independent agent that did not write this document re-verified all four original gaps
at HEAD and upheld every one, at its original severity. This section is empty as a *result*, not as
an omission — what was checked to reach it is recorded in `verification.md` § Adversarial review, and
in summary: every cited line was opened and every quotation compared verbatim; G2's six further
absent affordances were each confirmed absent from the skeleton individually rather than taken from
the report; G3's rationale was confirmed at its source (`visual-language.md:43` fixes 11 px, the
deployment standard fixes no caption size, and its preamble at `:10–13` delegates typography), and
the `.caption` populations were re-derived across all six templates; G4's arithmetic was recomputed
from `diagram-type-deployment.md:173–174`. Two candidate refutations were tested and failed: G1 is
not rescued by reading `gRPC`/`mTLS` as vendor casing the rule tacitly permits — the rule says
"upper case" without qualification — and G2 is not rescued by treating its three named absences as a
different *kind* of item from the six omitted, since all nine are alike "specified in the document,
not present in the skeleton".

Two candidate *additions* were also tested and deliberately not filed. The skeleton's external
component sitting on the authenticated side of the trust boundary (carried as § Residue) is a
legitimate topology — an external datastore reached over an authenticated leg — and the `<desc>`
describes it accurately, so it is not a defect. And no sibling standard routing a reader to the
deployment type, though real, is the plan's own declared out-of-scope boundary (*"Modifying any
other diagram type"*) rather than a gap in what was delivered.
