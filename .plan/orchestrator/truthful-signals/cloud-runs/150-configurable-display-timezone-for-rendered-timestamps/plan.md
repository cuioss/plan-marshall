> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# A configurable DISPLAY timezone for rendered timestamps — storage stays UTC

**Epic:** truthful-signals
**Branch prefix:** feature

## Problem

Every timestamp this system stores and compares is UTC, and must stay UTC. Every timestamp it
*renders to the operator* is **also** UTC — and that is the actual pain. The operator reads them in
local time and converts by hand, or falls back to a standing rule of *"run `date` or say nothing"*.

The fix is a **display-only** timezone in run configuration, consumed at rendering surfaces
exclusively.

## ⛔ The scoping decision, and why the obvious version is refused

The request as raised was *"configure the timezone at run-configuration and every time-resolving
should use this."* **The second half is refused, on evidence.** Storage and comparison stay UTC
unconditionally, and this plan builds a guard to keep it that way.

Four reasons a configured zone must never reach the write path:

1. **A whole prior plan was spent converging the last straggler onto UTC.** A configured write-zone
   re-opens exactly the class of defect that plan closed — and **that defect was invisible until it
   produced an identifier whose prefix disagreed with the `created` field beside it.**
2. **Cross-record comparison breaks silently.** Retention cutoffs, quiet-window comparisons, and
   ordering all compare records written at different times. Two records written under different
   configured zones are **incomparable, with no error** — which is the exact failure mode this epic is
   named after.
3. **Records cross machines and repositories.** Lessons and findings move between this repository and
   several consumer repositories. A per-project write-zone makes a shared corpus internally
   inconsistent.
4. **DST makes civil-zone arithmetic wrong twice a year.** A configured civil zone has ambiguous and
   non-existent local times; retention arithmetic across a DST boundary is off by an hour, silently.
   UTC has no such discontinuity.

⭐ **The operator's underlying complaint is real and is fully addressed by the display half.** The
inconvenience is *reading* UTC, not *storing* it.

## Goal

An operator can read rendered timestamps in a zone of their choosing, every rendered timestamp says
which zone it is in, and nothing that is stored, compared, or sorted can ever consult the setting.

## Deliverables

1. **D1 — GATE: derive the rendering surfaces.** Mutates nothing. Enumerate every place a stored
   timestamp is rendered for a human — landing and retrospective reports, metrics output, phase
   breakdowns, decision and work log rendering, terminal title, operator-facing summaries, inbox
   listings.
   *Done when:* every site is enumerated **and classified as RENDER or STORE/COMPARE**, with the
   population the enumeration was derived from stated.
   ⛔ **The classification IS the deliverable that makes the boundary enforceable.** The knob reaches
   RENDER sites only; D4 is built on this classification, so a sloppy D1 produces a guard that guards
   nothing.
   ⚠ **A value that is both stored and rendered from the same site is STORE, and is out of scope.**
   The known candidate is a lesson identifier prefix, which doubles as a **sort key** — converting it
   would silently reorder a corpus.
2. **D2 — The knob.** A `display_timezone` run-config value (IANA zone name, default `UTC`), settable
   through the ordinary configuration flow and resolved through the ordinary run-config path.
   *Done when:* the knob exists, validates an IANA name, and defaults to `UTC`.
   ⚠ **Default `UTC` means the unset behaviour is byte-identical to today.** No existing artifact
   changes unless the operator opts in — that is what makes this safe to land.
3. **D3 — Every rendered timestamp carries its zone label.**
   *Done when:* no rendering path can emit a converted timestamp without its label, and the test suite
   fails if one does.
   ⛔ **This is load-bearing, not cosmetic.** Converting a rendered timestamp *without* labelling it is
   **worse than leaving it in UTC**: the reader can no longer tell which zone they are looking at, and
   two artifacts rendered under different configurations become indistinguishable. **An unlabelled
   converted timestamp is a regression.**
4. **D4 — A guard that the knob cannot reach the write path.** A test or doctor rule asserting that no
   STORE/COMPARE site consults `display_timezone`.
   *Done when:* the guard exists, is **derived over D1's classification** rather than a hand-written
   list, and **publishes the population it examined**.
   ⚠ **This is the deliverable that keeps the refusal above true a year from now**, when the reasoning
   has been forgotten and a configured write-zone looks like an obvious convenience.
5. **D5 — Tests, each verified to FAIL pre-fix.**
   - (a) With the knob unset, every rendered timestamp is **byte-identical to today**.
   - (b) With it set to a positive-offset zone, a rendered timestamp converts **and carries its label**.
   - (c) A stored timestamp is **unchanged under any knob value**.
   - (d) The render-site population is derived and **asserted non-empty**.
   *Done when:* all four hold and the report states each was seen red first.

Five deliverables, under the split presumption.

## Out of scope

- **Any change to stored or compared timestamps.** See the four reasons above. This is not a
  simplification of the request — it is the request's load-bearing constraint, and D4 exists
  specifically to enforce it against a future author who has forgotten why.
- **Converting historical artifacts.** Records already written stay as written. Retroactively
  re-rendering an archive would make old and new artifacts disagree with each other for no gain.
- **A per-surface timezone.** One setting, applied at every RENDER site. Per-surface overrides
  multiply the "which zone is this?" problem that D3 exists to solve.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/manage-run-config/**` — or wherever the resolved run-config
  path lives, for the knob itself.
- `marketplace/bundles/plan-marshall/skills/marshall-steward/**` — the configuration flow.
- **The render sites D1 derives — deliberately NOT guessed here.** Naming them in advance would invite
  the run to treat the guess as the population, which is the mistake D1 exists to prevent.
- Tests for whichever modules D1 identifies.

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| Every time-resolution call in the bundles uses `datetime.now(UTC)`; the tree is fully converged | HYPOTHESIS | search the bundles for time-resolution calls. ⛔ The reported figure of **32 sites with zero naive calls is a LEAD** — re-derive it, since this plan's entire safety argument rests on the tree already being converged |
| The one bare `datetime.now()` match is prose in a testing standard *warning against* wall-clock deadlines | HYPOTHESIS | that document — a cheap check that prevents a false positive from derailing D1 |
| A prior plan converged the last straggler onto UTC, after a mixed-clock defect produced an id prefix disagreeing with its own `created` field | HYPOTHESIS | git history for that change. ⚠ Its landing record lives under `.plan/` and is **not reachable from this clone** — reconstruct the rationale from the diff, or rely on the four arguments restated above, which are self-contained |
| The render/store split is cleanly separable | HYPOTHESIS | **D1's per-site classification.** ⛔ If a single value is both stored and rendered from one site, that site is STORE and out of scope |
| A lesson identifier prefix doubles as a sort key | HYPOTHESIS | the lesson id generation and any ordering that consumes it. ⛔ **The known STORE trap** — converting it would silently reorder the corpus |
| An existing configuration surface exists that this knob slots into | HYPOTHESIS | the steward configuration flow — ⛔ an asserted **presence**; if it does **not** exist, D2 grows and should be re-sized rather than improvised |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D5(a) is the safety test.** Unset must be byte-identical to today. If a single rendered artifact
  differs with the knob unset, the change is not opt-in and must not land.
- ⛔ **D5(c) is the invariant test.** A stored timestamp unchanged under *any* knob value is the entire
  refusal in the Problem section, expressed as an assertion.
- **D3's labelling should get a cold read**: give the Step 6 verification sub-agent a converted,
  labelled timestamp with no other context and ask what instant it denotes and in which zone. If it
  cannot answer both, the label is insufficient — and an ambiguous label is the failure mode that makes
  conversion worse than no conversion.
- **D4 must publish the population it guarded.** A guard derived over an empty classification passes
  trivially, which is this epic's namesake defect.
- Python and test changes are expected, so the build gate takes its full path.

## Notes

- ⚠ **Sequencing:** a sibling plan in this epic catalogues and surfaces every configuration knob.
  **Adding a knob and cataloguing knobs collide** — sequence against it, or fold D2's surfacing into
  that plan and say so. This plan also touches the steward, which another sibling's shim sweep names;
  verify before pairing.
- ⛔ **Do not go looking for the orchestrator spec or any landing record.** They live under `.plan/`,
  which is git-ignored and absent from this clone. The four arguments for keeping storage in UTC are
  restated in full above precisely so this plan does not depend on reading that record.
