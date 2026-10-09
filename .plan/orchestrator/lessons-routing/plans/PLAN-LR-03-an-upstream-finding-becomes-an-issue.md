# PLAN-LR-03: An upstream finding becomes an issue

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `/Users/oliver/git/plan-marshall-mcp/doc/known-defects/lessons-routing-carry-over.md` as PM-MCP input.
> Do NOT emit; un-park only by explicit operator decision.

epic: lessons-routing
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Objective

Give the upstream class a destination: a finding about plan-marshall, raised in a consumer repo,
becomes an **issue on the plan-marshall repository**.

⭐ **The transport already exists** — `plan-marshall:tools-integration-ci:ci` exposes an `issue`
subcommand alongside `pr` / `checks` / `branch` / `repo`. ⛔ **This plan builds a route, not an
integration**, and must not introduce a second CI path: the hard rule that all CI/Git provider
operations go through the abstraction binds here exactly as elsewhere.

## Deliverables

Five deliverables. D0 is a gate and it is the one most likely to change this plan's shape.

**D0 — GATE: establish that a consumer repo CAN open an issue on this repository.** ⚠ **Unverified at
staging and recorded as a Watch.** The `ci issue` surface exists; whether a client developer's
credentials can write to a foreign repo across orgs is a **different question** and it is not answered
by the surface existing. Establish it before any transport is built.

⛔ **A negative answer does not kill this plan — it re-shapes it**, and the alternatives must be priced
here rather than discovered at implementation: a queued outbox the client flushes deliberately; a
generated issue body the developer pastes; a token the operator provisions per repo. ⭐ **State which
alternative applies under which permission finding**, so the run does not stall on a fork nobody
decided.

**D1 — the issue body is actionable WITHOUT the originating machine.** The finding is leaving the
machine that holds all its context, so the body must carry: the lesson body, the component, the
producing plan, **and the plan-marshall version/commit the client was running.** ⛔ **The version is
not optional** — a finding about behaviour that has since changed is worse than no finding, because it
costs a maintainer a reproduction attempt against a moving target. ⚠ Consumer repos on this machine
have run **markedly different plan-marshall versions**, so a stale-version report is the expected case,
not the edge case.

**D2 — deduplicate across repos and across developers.** The same defect found by three consumer repos
must not open three issues; the same defect found twice by one repo must not open two. ⛔ **Derive the
dedup key rather than assuming one** — the component alone is too coarse (several distinct findings
share `plan-marshall:build-maven`) and the full body is too fine (two reports of one defect never match
verbatim). ⚠ Publish the population any dedup check was computed over; a "no duplicate found" over an
unscanned corpus is a vacuous pass, an archetype the parent project has recorded repeatedly.

⭐ **Real collision confirmed at cleanup 2026-09-23** (re-derive at outline, do not just cite this):
`plan-marshall:build-maven` is stranded TWICE across two different repos — `cui-jsf-test-basic`
(`2026-06-16-09-001`) and `nifi-extensions` (`2026-07-16-21-002`) — a live instance of the "component
alone is too coarse" premise, not a hypothetical.

**D3 — the failure path is loud and lossless.** Offline, no permission, rate-limited, or the API
refuses: ⛔ **the finding must NOT silently fall back to the local store** — that is precisely the
stranding this epic ends, and a silent fallback would rebuild it behind a route that reports success.
The content survives, the failure is named, and the caller is told what to do.

**D4 — tests including a matched negative control.** Assert a local finding does **not** route upstream.
⭐ **That control is load-bearing**: a route that fires on everything looks identical to a working route
until a client's private code appears in a public issue tracker. ⚠ Treat that as the failure mode to
design against, not a remote one.

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/**`
- `marketplace/bundles/plan-marshall/skills/tools-integration-ci/**` *(expected READ-ONLY — the `issue`
  surface is consumed, not extended; record the reason if that proves false)*
- `test/plan-marshall/manage-lessons/**`

## Dependencies and Sequencing

⛔ **Re-derive with `corpus cross-check` at emit time.**

- ⛔ **Depends on PLAN-LR-02 (hard)** — the route is a function of the audience axis.
- ⛔⛔ **Depends on PLAN-LR-05 (hard) — D1 IS WRONG WITHOUT IT.** D1 requires the issue body to carry the
  version the client was running. LR-05 stamps that at **filing** time. Without it, D1 could only sample
  a **live** version at routing time — the version at the moment of routing, not of observation — which
  is wrong for every finding filed before an upgrade, and the stranded corpus is two months old.
  ⇒ **When LR-05 lands, D1 READS a recorded field; it must never sample one.**
- ⚠ **PLAN-LR-04 depends on this.** Migrating stranded findings before the route exists moves them from
  one dead end to another.

## Claim Labels

- OBSERVED: `ci.py` exposes an `issue` subcommand alongside `pr` / `checks` / `branch` / `repo` — read at `tools-integration-ci/scripts/ci.py` § argparse subparsers.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: ci --help lists {pr,checks,issue,branch,repo}; 'issue  Issue operations'
- HYPOTHESIS: a consumer repo's credentials can open an issue on `cuioss/plan-marshall` across orgs — confirm/refute at the provider layer with a dry-run issue call from a consumer checkout (verify-at-outline). ⛔ **UNVERIFIED and gating: D0 exists solely to settle it, and a negative answer re-shapes this plan rather than killing it.**
  - verdict: unverifiable | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: requires a live authenticated cross-org write probe from a consumer checkout; a dry-run issue create is a mutation and out of scope for a read-only cleanup pass. Remains correctly gated at D0
- HYPOTHESIS: consumer repos on this machine run differing plan-marshall versions, so a stale-version report is the expected case — confirm/refute at each consumer `.plan/execute-script.py` § `MARSHALL_VERSION` (verify-at-outline).
  - verdict: corroborated | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: MARSHALL_VERSION read at each consumer .plan/execute-script.py:80 - API-Sheriff 0.1.1753, TokenSheriff 0.1.1670, nifi-extensions 0.1.1137, cui-jsf-test-basic absent (predates the constant); this repo 0.1.1753 - 616-release spread confirms stale-version is the expected case
- HYPOTHESIS: a dedup key exists that is coarser than the full body and finer than the component alone — confirm/refute at outline against the real stranded corpus (verify-at-outline). **Neither bound is assumed correct; D2 derives the key.**
  - verdict: unverifiable | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: design derivation deliberately deferred to outline; confirmed a real collision (plan-marshall:build-maven stranded twice, cui-jsf-test-basic + nifi-extensions) strengthening the component-alone-too-coarse premise, but the key itself is still D2's to derive
- Verify-first clause: the failure path must be demonstrated to preserve content and name its failure, since a silent fallback to the local store rebuilds the stranding this plan removes.
  - verdict: corroborated | checked_at: 14d8f3ccd | by: lessons-routing/cleanup | rescoped: n/a | evidence: still an open design obligation - no issue-route or MARSHALL_VERSION reference exists anywhere under manage-lessons/scripts/** at HEAD, confirmed via architecture search --content
