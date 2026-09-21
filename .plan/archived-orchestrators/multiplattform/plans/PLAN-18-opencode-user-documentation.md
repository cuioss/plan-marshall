# PLAN-18: OpenCode is documented as a validated runtime, with its limitations stated

epic: multiplattform
workstream: WS-05

> ⛔ **PARKED — blocked on PLAN-17, which is itself blocked on an operator with a live OpenCode
> install.** This spec MUST NOT be emitted by the `next` verb. See
> `workstreams/WS-05-live-validation.md` for the unpark sequence.
>
> **Authored at ingestion** from `../reference/opencode-validation-protocol.md` § Post-validation
> work, items 2 and 3 — merged into one plan because both are documentation over the same
> observation set and splitting them would run the same trace twice.
>
> ⛔ **PARTIALLY DISCHARGED BY A SIBLING EPIC, 2026-09-15 — do not emit this spec as-is.**
> `tooling-truthfulness/PLAN-07-opencode-install-docs.md` (shipped PR #1484, squash `14fe203c869f`)
> shipped D1 (README Installation (OpenCode) + split `install-claude.adoc`/`install-opencode.adoc`,
> retargeting every reference — tree-wide search for the old `installation.adoc` returns zero hits at
> its landing HEAD) and D3/D4-equivalent consistent multi-assistant framing
> (`distribution.adoc`, `build-server.adoc`), all traced to the same live-OpenCode-1.18.30
> observation PLAN-17's note above cites. This covers this spec's **D1** and substantially overlaps
> **D4**. **NOT covered, and still genuinely open:** **D2** (the per-operation real-vs-`no-op`
> behaviour orientation layer over `platform-runtime/standards/contract.md`) and **D3** (the
> confirmed-limitations record). No artifact in `tooling-truthfulness` addresses either — verified by
> reading that epic's full landing set; neither a `contract.md`-orientation document nor a
> limitations record appears in its shipped deliverables. Per operator direction (2026-09-15), the
> epic is closing with this residual accepted as deferred, unclaimed scope rather than staged as a
> fresh plan — recorded here so a future reader does not mistake "epic closed" for "D2/D3 delivered
> somewhere." Status stays `parked`. See `multiplattform/epic.md` Decisions for the full record.

## Epic Constraints (bind every deliverable)

- **The principles bind:** no target enumeration in contracts, no wire format across the runtime boundary, no universal templating, honest no-ops. Read `../reference/principles.md`.
- **Counts and enumerations here are LEADS.** Re-derive at the moment of the claim.
- **Never edit another plan's surface**, even for an obvious adjacent fix.
- **Confirm the Expected Surface against the tree as the first action** and report any file the work needs beyond it.

## Objective

Once the protocol has run and PLAN-17 has pinned the install path, the repository still describes
OpenCode as best-effort output rather than a validated runtime. Add the verified install/update path
to the user documentation; document the per-operation OpenCode behaviour — real versus `no-op` with
`reason`/`alternative` — as an orientation layer over `platform-runtime/standards/contract.md`;
record the confirmed limitations; and upgrade the validation framing in the developer and repo-root
multi-assistant sections.

⛔ **The binding rule for this entire plan: every documented behaviour traces to something the
protocol confirmed.** A statement that is merely plausible, or inferred from the code rather than
observed on the install, does not belong here — it belongs in `contract.md` as a contract statement.
Documenting an inference as a validated fact is the precise failure this plan exists to prevent, and
it is worse than documenting nothing, because a reader cannot tell the two apart afterwards.

## Deliverables

1. **D1 — The verified install/update path in the user documentation.** `doc/user/installation.adoc` gains the path PLAN-17 pinned, cross-referencing rather than restating PLAN-17's own record.
   *Done when:* the section names the pinned path and every step traces to a PLAN-17 observation.
2. **D2 — The per-operation behaviour orientation layer.** For each runtime operation, what an OpenCode user actually gets: a real result, or a `no-op` with its `reason` and `alternative`. An **orientation layer over** `contract.md`, deriving the operation population from the ABC rather than restating it — ⛔ not a second contract, which would drift the moment an operation changes.
   *Done when:* the layer covers every operation the ABC declares (population-derived, with a non-vacuity guard) and states, per operation, whether the behaviour was observed or is contract-stated-but-unobserved.
3. **D3 — The confirmed limitations.** No platform-driven title/status hook, manual `--total-tokens`, and any `inline_only` step kinds the protocol discovered — each recorded with the observation behind it.
   *Done when:* each limitation names what was observed and where.
4. **D4 — The validation framing upgraded.** `doc/developer/marketplace-build.adoc` and the repo-root multi-assistant sections stop calling OpenCode untested-as-a-runtime, and state precisely what *was* validated and what was not.
   *Done when:* no document claims OpenCode is unvalidated, and none overclaims beyond the protocol's actual coverage. ⛔ **Both failure directions matter equally** — an overclaim is as bad as a stale disclaimer.

## Out of Scope

- **The developer inner loop and deploy options** — PLAN-04's D3. This plan adds live-validated facts **on top**, cross-referencing rather than restating.
- **The publish matrix description** — PLAN-04's D4.
- **The install path itself** — PLAN-17's.
- **Fixing anything the protocol revealed as broken.** ⛔ This is a documentation plan. A behavioural defect the protocol surfaced is **reported to the orchestrator** and staged as its own plan; documenting a defect as a limitation is only correct when the defect is a genuine, accepted constraint of the target — not when it is a bug.

## Claim Labels

- OBSERVED: the repository currently frames OpenCode as unvalidated — recorded at `archive/README.md` § "The boundary: plannable vs validation-gated" and in the developer documentation. Re-derive at unpark; PLAN-04's D3/D4 will have changed some of this framing already.
  - verdict: unverifiable | checked_at: 8fc353b6e | by: multiplattform/cleanup | rescoped: n/a | evidence: UNVERIFIABLE BY CONSTRUCTION and doubly gated. PLAN-18 depends on PLAN-17 landing AND on the live validation protocol having run; its own binding rule is that every documented behaviour must trace to something the protocol confirmed. Neither precondition exists at 8fc353b6e. ⛔ Attempting to settle these claims from the code rather than from an observed install is the EXACT failure the spec exists to prevent - it says documenting an inference as a validated fact is worse than documenting nothing, because a reader cannot tell the two apart afterwards. So cleanup deliberately declines to corroborate them from source. Before this stamp the claims carried NO verdict, indistinguishable from never-examined; they now carry checked-and-unreachable-by-design.
- OBSERVED: `contract.md` is the operation contract this plan orients over, not duplicates.
  - verdict: unverifiable | checked_at: 8fc353b6e | by: multiplattform/cleanup | rescoped: n/a | evidence: UNVERIFIABLE BY CONSTRUCTION and doubly gated. PLAN-18 depends on PLAN-17 landing AND on the live validation protocol having run; its own binding rule is that every documented behaviour must trace to something the protocol confirmed. Neither precondition exists at 8fc353b6e. ⛔ Attempting to settle these claims from the code rather than from an observed install is the EXACT failure the spec exists to prevent - it says documenting an inference as a validated fact is worse than documenting nothing, because a reader cannot tell the two apart afterwards. So cleanup deliberately declines to corroborate them from source. Before this stamp the claims carried NO verdict, indistinguishable from never-examined; they now carry checked-and-unreachable-by-design.
- HYPOTHESIS: **every substantive claim about OpenCode's actual behaviour.** ⛔ All confirm/refute at the protocol's live run and PLAN-17's landing (verify-at-outline). Like PLAN-17, this spec is intentionally un-sharpenable until then, and re-grounding it at unpark is mandatory.
  - verdict: unverifiable | checked_at: 8fc353b6e | by: multiplattform/cleanup | rescoped: n/a | evidence: UNVERIFIABLE BY CONSTRUCTION and doubly gated. PLAN-18 depends on PLAN-17 landing AND on the live validation protocol having run; its own binding rule is that every documented behaviour must trace to something the protocol confirmed. Neither precondition exists at 8fc353b6e. ⛔ Attempting to settle these claims from the code rather than from an observed install is the EXACT failure the spec exists to prevent - it says documenting an inference as a validated fact is worse than documenting nothing, because a reader cannot tell the two apart afterwards. So cleanup deliberately declines to corroborate them from source. Before this stamp the claims carried NO verdict, indistinguishable from never-examined; they now carry checked-and-unreachable-by-design.
- HYPOTHESIS: the protocol's coverage is broad enough that D2 can state an observed-versus-contract-stated verdict for **every** operation — confirm/refute against the protocol's actual observation set (verify-at-outline). ⛔ If the protocol covered only some operations, **say so per operation** rather than silently letting contract statements pass as observations. A partially-observed population reported as fully observed is the same defect one level up.
  - verdict: unverifiable | checked_at: 8fc353b6e | by: multiplattform/cleanup | rescoped: n/a | evidence: UNVERIFIABLE BY CONSTRUCTION and doubly gated. PLAN-18 depends on PLAN-17 landing AND on the live validation protocol having run; its own binding rule is that every documented behaviour must trace to something the protocol confirmed. Neither precondition exists at 8fc353b6e. ⛔ Attempting to settle these claims from the code rather than from an observed install is the EXACT failure the spec exists to prevent - it says documenting an inference as a validated fact is worse than documenting nothing, because a reader cannot tell the two apart afterwards. So cleanup deliberately declines to corroborate them from source. Before this stamp the claims carried NO verdict, indistinguishable from never-examined; they now carry checked-and-unreachable-by-design.

## Expected Surface

⛔ Re-derive at unpark; PLAN-04 and PLAN-17 will have moved some of this.

- HYPOTHESIS: `doc/user/installation.adoc` — D1 (verify-at-outline)
- HYPOTHESIS: a new or extended OpenCode-behaviour document reachable from `platform-runtime/standards/contract.md` — D2, D3 (verify-at-outline)
- HYPOTHESIS: `doc/developer/marketplace-build.adoc`, and the repo-root multi-assistant sections — D4 (verify-at-outline)

## Dependencies and Sequencing

- **Blocked on:** PLAN-17, and through it on the operator running the protocol.
- Depends on: **PLAN-04** (its D3/D4 documentation is what this plan layers onto) and **PLAN-17** (the pinned path).
- Depends on: **PLAN-09** by preference. PLAN-09's D1 gives four currently-undeclinable operations a decline vocabulary, and D2 here documents per-operation behaviour — running after PLAN-09 means documenting a complete vocabulary rather than one with four holes. ⛔ If PLAN-09 has not landed, **record the four operations as having no documented decline path**, which is itself the honest statement.
- Overlaps with: **PLAN-04** on `doc/developer/marketplace-build.adoc`; **PLAN-17** on the user documentation. ⛔ Not concurrent with either — and by the unpark sequence they land first anyway.

## Verification

- **The traceability check, which is this plan's real gate:** every statement in D1–D3 names the protocol observation behind it, and a reviewer can follow each one back. A statement with no traceable observation is removed or relabelled as contract-stated.
- D2's coverage derived from the ABC's operation population at verification time, with a non-vacuity guard — never from a restated list.
- **A cold read of D4's framing:** a reviewer reads the upgraded sections without the plan in context and answers "what has actually been validated about OpenCode, and what has not?" A vague answer in either direction — sounding unvalidated, or sounding fully validated — means the framing failed.

## Hand-Off Command

⛔ **Do not emit.** Held until PLAN-17 lands.

```text
/plan-marshall task="implement .plan/orchestrator/multiplattform/plans/PLAN-18-opencode-user-documentation.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and
edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message —
the orchestrator owns every other ledger write.
