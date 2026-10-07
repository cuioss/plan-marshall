# PLAN-17: Pin the OpenCode install path against the published refs

epic: multiplattform
workstream: WS-05

> ⛔ **PARKED — blocked on an operator with a live OpenCode install.** This spec MUST NOT be emitted
> by the `next` verb. The gate is not a predecessor plan: it is a human at an interactive terminal
> running `../reference/opencode-validation-protocol.md`. The cloud plan lane cannot provide one.
>
> Unparking sequence: the operator confirms an install exists → the operator runs the protocol →
> the orchestrator `analyze`s its observations → this row moves `parked` → `staged` **and is
> re-grounded against what the protocol actually found** → only then is it emitted.
>
> **Authored at ingestion** from `../reference/opencode-validation-protocol.md` § Post-validation
> work, item 1.
>
> ⛔ **DISCHARGED BY A SIBLING EPIC, 2026-09-15 — do not emit this spec.** D0 of
> `tooling-truthfulness/PLAN-07-opencode-install-docs.md` (shipped PR #1484, squash `14fe203c869f`,
> `tooling-truthfulness/landings/PLAN-07.md`) ran exactly this plan's D1/D2 objective — testing the
> candidate consumption paths from `../reference/opencode-validation-protocol.md` against a live
> install — and pinned OBSERVED on **live OpenCode 1.18.30**: marketplace-add and the npm-plugin
> path tried-and-rejected, no fourth path invented, the manual config-dir deploy via the generator +
> `/sync-opencode` pipeline pinned as primary with no consumer script needed. Corroborated
> independently: (1) `tooling-truthfulness/landings/PLAN-07.md` states the observation directly;
> (2) `corpus cross-check --slug multiplattform` reports this spec colliding with
> `tooling-truthfulness/PLAN-07-opencode-install-docs.md` on `marketplace/targets/opencode/**` and
> `doc/developer/distribution.adoc`; (3) that epic's own Decisions log (2026-09-11) records the
> operator accepting this as a deliberate cross-epic duplication of THIS spec, choosing to stage the
> work there rather than unpark WS-05. D3 (generated tree root manifest) was not separately
> re-confirmed, but PLAN-07's D0 finding — the manual deploy path, not a marketplace-install
> mechanism — makes it moot for the pinned path. Status stays `parked` (no queue-status vocabulary
> member fits "superseded"); the epic is closing with WS-05's precondition resolved via this sibling
> rather than executed here. See `multiplattform/epic.md` Decisions for the full record.

## Epic Constraints (bind every deliverable)

- **The principles bind:** no target enumeration in contracts, no wire format across the runtime boundary, no universal templating, honest no-ops. Read `../reference/principles.md`.
- **Counts and enumerations here are LEADS.** Re-derive at the moment of the claim.
- **Never edit another plan's surface**, even for an obvious adjacent fix.
- **Confirm the Expected Surface against the tree as the first action** and report any file the work needs beyond it.

## Objective

`claude-distribute.yml` publishes `dist-opencode` (branch) and `opencode/v*` (tags) on every `main`
push and source tag. **Which consumption path actually works against those refs is unverified on a
live client** — a git-ref add, an OpenCode marketplace install, and a deploy into
`~/.config/opencode/` are three candidates and no one has tried any of them. Test them against a real
install, pin the working one as primary, document it, and confirm the generated tree's root holds
whatever manifest that path expects.

⛔ **This plan's premises are deliberately thin, and that is correct.** They cannot be sharpened
without the install. The protocol's observations are the input that makes this spec scopeable; a run
that begins before those observations exist is guessing.

## Deliverables

1. **D1 — The three candidate paths are tested against a live install** and the result recorded per path: works / fails / works with caveats, each with the observed evidence.
   *Done when:* the PR body carries one row per candidate path with a concrete observation, not a judgement.
2. **D2 — The working path is pinned and documented** as the primary consumption path, with the others recorded as tried-and-rejected and why. ⛔ **If none works, that is the finding** — record it, and the epic stages remediation rather than this plan inventing a fourth path.
   *Done when:* the documentation names one primary path traceable to a D1 observation.
3. **D3 — The generated tree's root carries the manifest the chosen path expects**, or the gap is recorded as a generator change the orchestrator stages separately.
   *Done when:* either the root is correct, or the PR body names exactly what the generator must emit and the orchestrator has the finding.

## Out of Scope

- **The developer inner loop and deploy options** — PLAN-04's D3 owns those, and this plan cross-references rather than restating them.
- **User documentation and the confirmed-limitations layer** — PLAN-18's.
- **Changing the publish matrix** — the workflow already publishes both targets correctly; this plan pins *consumption*, not publication.
- **Generator changes.** ⛔ If D3 finds the root manifest wrong, that is a `marketplace/targets` change in WS-02, reported and staged — not absorbed here.

## Claim Labels

- OBSERVED: `claude-distribute.yml` carries a live two-entry matrix publishing `dist-opencode` and `opencode`-prefixed tags — read directly at `.github/workflows/claude-distribute.yml` lines 38–48 at HEAD `2cd1a19c`. ⚠️ This file is **outside the content-search inventory**; verify by direct read, never by a zero-hit search.
  - verdict: unverifiable | checked_at: 8fc353b6e | by: multiplattform/cleanup | rescoped: n/a | evidence: UNVERIFIABLE BY CONSTRUCTION, and recording that is the point of this stamp. PLAN-17 is parked in WS-05, whose charter states OpenCode has never executed a plan-marshall workflow live. Every substantive premise of this plan - which consumption path works against dist-opencode and the opencode/v* tags, what manifest the generated root needs, whether the plural-layout assumption held - is answerable ONLY by a real install, which no one has performed. ⛔ This is not a gap in the re-grounding; it is the workstream's defining condition, and the spec itself says its premises are deliberately thin and that this is correct. Before this stamp the claims carried NO verdict at all, which is indistinguishable from never-looked-at; they now carry checked-and-unreachable. An unverifiable verdict does not block emission - but the PARK does, and the park lifts only when the validation protocol runs.
- OBSERVED: which consumption path works is unverified — an asserted absence of knowledge, recorded as such in `../reference/opencode-validation-protocol.md` § Post-validation work.
  - verdict: unverifiable | checked_at: 8fc353b6e | by: multiplattform/cleanup | rescoped: n/a | evidence: UNVERIFIABLE BY CONSTRUCTION, and recording that is the point of this stamp. PLAN-17 is parked in WS-05, whose charter states OpenCode has never executed a plan-marshall workflow live. Every substantive premise of this plan - which consumption path works against dist-opencode and the opencode/v* tags, what manifest the generated root needs, whether the plural-layout assumption held - is answerable ONLY by a real install, which no one has performed. ⛔ This is not a gap in the re-grounding; it is the workstream's defining condition, and the spec itself says its premises are deliberately thin and that this is correct. Before this stamp the claims carried NO verdict at all, which is indistinguishable from never-looked-at; they now carry checked-and-unreachable. An unverifiable verdict does not block emission - but the PARK does, and the park lifts only when the validation protocol runs.
- HYPOTHESIS: **every substantive premise of this plan** — which path works, what manifest the root needs, whether the plural layout assumption held. ⛔ All confirm/refute at the protocol's live run (verify-at-outline). **This spec is intentionally un-sharpenable until then**, and re-grounding it at unpark is mandatory, not optional.
  - verdict: unverifiable | checked_at: 8fc353b6e | by: multiplattform/cleanup | rescoped: n/a | evidence: UNVERIFIABLE BY CONSTRUCTION, and recording that is the point of this stamp. PLAN-17 is parked in WS-05, whose charter states OpenCode has never executed a plan-marshall workflow live. Every substantive premise of this plan - which consumption path works against dist-opencode and the opencode/v* tags, what manifest the generated root needs, whether the plural-layout assumption held - is answerable ONLY by a real install, which no one has performed. ⛔ This is not a gap in the re-grounding; it is the workstream's defining condition, and the spec itself says its premises are deliberately thin and that this is correct. Before this stamp the claims carried NO verdict at all, which is indistinguishable from never-looked-at; they now carry checked-and-unreachable. An unverifiable verdict does not block emission - but the PARK does, and the park lifts only when the validation protocol runs.

## Expected Surface

⛔ Genuinely unknown until the protocol runs. The list below is the **expected** shape and must be
re-derived at unpark.

- HYPOTHESIS: `doc/user/installation.adoc` — D2 (verify-at-outline)
- HYPOTHESIS: `doc/developer/distribution.adoc` — D2, the consumption half only; PLAN-04's D4 owns the matrix description (verify-at-outline)
- HYPOTHESIS: `marketplace/targets/opencode/**` — D3, **only if** the root manifest is wrong, and then only as a reported finding (verify-at-outline)

## Dependencies and Sequencing

- **Blocked on:** the operator running `../reference/opencode-validation-protocol.md`. Not a plan dependency — an operator-availability gate.
- Depends on: **PLAN-04** by preference. PLAN-04's `/sync-opencode` is the protocol's § 1.2 deploy step; running the protocol after PLAN-04 lands means testing the real deploy path rather than a manual fallback.
- Blocks: **PLAN-18**.
- Overlaps with: **PLAN-04** on `doc/developer/distribution.adoc`. ⛔ Not concurrent — and by the unpark sequence they cannot be, since PLAN-04 lands first.
- May **refute** PLAN-04's plural-directory HYPOTHESIS (protocol § 1.2). ⛔ A refutation there is a **re-scope of PLAN-04's D1**, reported to the orchestrator — not a defect in PLAN-04 and not something this plan fixes.

## Verification

- Every claim in D2's documentation traces to a **D1 observation**, not to a plausible inference. A documented path with no observation behind it is the failure this plan exists to prevent.
- The PR body and the inbox message distinguish *observed on the live install* from *inferred* for every statement.
- A cold read of the pinned path: a reader follows the documented install path on a clean machine and reaches a working install, or the wording failed.

## Hand-Off Command

⛔ **Do not emit.** Held until the operator confirms a live OpenCode install and the protocol has run.
The command below is recorded for the unpark, not for use now:

```text
/plan-marshall task="implement .plan/orchestrator/multiplattform/plans/PLAN-17-pin-opencode-install-path.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write.
