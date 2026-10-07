# PLAN-07: OpenCode install path is documented in README and user guide

epic: tooling-truthfulness
workstream: WS-06

> Staged plan spec — one shippable unit of work. SELF-SUFFICIENT.
>
> ⚠️ **This plan is a deliberate, operator-directed duplicate of `multiplattform` PLAN-18
> (opencode-user-documentation) and PLAN-17 (pin-opencode-install-path), both PARKED in that epic's
> WS-05.** The operator chose to stage the task in this epic rather than unpark `multiplattform`.
> See `workstreams/WS-06-opencode-install-docs.md` for the recorded rationale. Whichever of the two
> lands second MUST re-read the other first and reconcile the shared surface. The cross-epic
> duplication gate reports this overlap deliberately.

## Epic Constraints (bind every deliverable)

- **ADR-019 binds reflexively:** a statement that cannot be shown true is labelled, never asserted
  as observed. **Every claim about a working install path is OBSERVED or HYPOTHESIS.**
- **Confirm the Expected Surface against the tree as the first action.** ⛔ A surface expansion
  updates this section IN THE SAME ACT.
- **Verify-first:** an OBSERVED label requires a named artifact (a deployed
  `~/.config/opencode/` path, a live install interaction); a HYPOTHESIS label requires a named
  confirm/refute artifact.

## Objective

The repository root `README.md` describes Plan Marshall as an orchestration layer "currently Claude
Code" and its only install section is Claude-specific (`/plugin marketplace add`). The OpenCode
target has been publishing a generated tree (`dist-opencode` branch, `opencode/v*` tags) for some
time, and this very repository runs on OpenCode, yet there is no "How to install on opencode"
section in the README or the user guide. The consumption path against the published refs has never
been validated on a live install (`doc/developer/distribution.adoc` § Multi-target architecture);
the `/sync-opencode` deploy used by the project itself is the developer inner loop, not a consumer
install. This plan writes the missing documentation honestly: verified steps labelled as verified,
designed steps labelled as designed.

⛔ **What this plan must NOT do:** claim a consumer install path "works" when only the developer
inner loop has been exercised. The whole subject of this epic is a could-not-evaluate reported as a
clean result; the docs must not become another instance.

D0 pins the consumption path against a live install BEFORE D1–D3 document it. The documentation
deliverables describe whatever D0 pinned; if D0 cannot pin a path, they document the designed shape
with honest labels rather than inventing a working route.

## Deliverables

1. **D0 — Pin the OpenCode consumption path against the published refs.** The publish matrix emits
   `dist-opencode` (branch) and `opencode/v*` (tags), but which consumption path works against them
   is unverified on a live client. Three candidates, from `multiplattform`'s
   `reference/opencode-validation-protocol.md` § Post-validation work item 1: (a) a manual deploy
   into `~/.config/opencode/` (the protocol § 1.2 staging shape), (b) a git-ref/marketplace add
   analogous to Claude's `/plugin marketplace add`, (c) an OpenCode-native install
   (`opencode plugin <module>`, npm-based). Test each against a live OpenCode install and pin the
   working one as primary, recording the others as tried-and-rejected with the observed evidence.
   ⛔ **`/sync-opencode` is NOT a candidate** — it is a command that exists only in the plan-marshall
   project repo (`.opencode/commands/sync-opencode.md`), so a consumer installing into their own
   OpenCode does not have it. The deploy *shape* it performs (generated tree → config dir, singular→plural
   rename) is candidate (a); the command itself is not a consumer path. ⛔ **If none of (a)–(c)
   works, that is the finding** — report it to the orchestrator and stage remediation; do NOT invent
   a fourth path. Where the pinned path needs a consumer-facing install script, produce it here (or
   record the gap as a separately-staged change).
   *Done when:* the PR body carries one row per candidate path with a concrete observation
   (works / fails / works-with-caveats), the primary path is named and traceable to an observation,
   and — if a consumer install script is the verified vehicle — it exists and is exercised
   end-to-end against a clean config dir.
2. **D1 — README gains an "Installation (OpenCode)" section.** The root `README.md` currently has
   only "Installation (Claude Code)". Add an OpenCode counterpart that (a) names the published refs
   (`dist-opencode` snapshot, `opencode/v{x.y.z}` pinned), (b) records which consumption path is
   the primary documented one with an OBSERVED/HYPOTHESIS label per step, and (c) links the user
   guide section and the developer distribution contract.
   *Done when:* a reader can follow the section to an OpenCode install attempt; every step carries a
   label; no step claims observed when only designed.
2. **D2 — `doc/user/installation.adoc` is split into per-assistant guides, and the OpenCode
  guide is added.** (Operator direction 2026-09-13; the install docs are currently Claude-only.)
  Move the Claude content verbatim to `doc/user/install-claude.adoc`, write the OpenCode
  counterpart as `doc/user/install-opencode.adoc` (snapshot/pinned/update flow at the same
  honesty level as D1), and retarget every in-tree reference: orchestrator-measured 11 matches
  across 8 files (README.md, doc/developer/distribution.adoc ×2, doc/developer/
  build-architecture.adoc, doc/user/windows-wsl-setup.adoc ×2, doc/user/README.adoc,
  doc/concepts/build-server.adoc ×2, manage-build-server/SKILL.md, marshall-steward
  cache_freshness.py comment) — the launched plan re-derives this population at outline and
  double-checks zero residual `installation.adoc` references before shipping. Mirror the README
  section in the new guide; cross-reference rather than restate the developer distribution
  contract.
  *Done when:* `doc/user/installation.adoc` no longer exists; every reference resolves to one
  of the two new guides (verified by a tree-wide search, not by sampling); the user guide and
  README agree on the path and labels; the update flow (snapshot refresh, pinned bump) is
  documented with the same per-step labels.
3. **D3 — The multi-assistant framing in README and `doc/developer/distribution.adoc` is made
   accurate.** The README opening line "currently Claude Code" and the distribution doc's
   "unverified on a live client" wording must agree with what the new sections state — a reader of
   either should reach the same picture of what is verified about OpenCode consumption.
   *Done when:* README, user guide, and distribution doc carry a consistent, labelled statement of
   the OpenCode install surface; no overclaim and no stale disclaimer.

## Claim Labels

- OBSERVED: the root `README.md` has a single install section titled "Installation (Claude Code)"
  and no OpenCode install section — read directly at HEAD 5c18ef918.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: README.md:34 heads 'Installation (Claude Code)' and no OpenCode install section exists in the file - read at HEAD 5c18ef918
- OBSERVED: `doc/user/installation.adoc` describes only the Claude marketplace flow
  (`/plugin marketplace add ... @dist-claude` / `@claude/v{x.y.z}`); no OpenCode section exists —
  read directly at HEAD 5c18ef918.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: doc/user/installation.adoc describes only the Claude flow (/plugin marketplace add @dist-claude / @claude/v{x.y.z}); no OpenCode section exists - read at HEAD 5c18ef918
- OBSERVED: `doc/developer/distribution.adoc` states the `opencode` target publishes under
  `dist-opencode` / `opencode/v*` and that "no live OpenCode client has consumed those refs
  end-to-end" — read at that file § Multi-target architecture.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: doc/developer/distribution.adoc:10,:100 states opencode publishes under dist-opencode/opencode/v* and 'no live OpenCode client has consumed those refs end-to-end' - read at HEAD 5c18ef918
- OBSERVED: the project runs on OpenCode today via `/sync-opencode`, which deploys the generated
  `target/opencode/` tree into `~/.config/opencode/` (skills/agents/commands + `opencode.json`) —
  read at `.opencode/scripts/sync_opencode.py` and `.opencode/commands/sync-opencode.md`.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: .opencode/commands/sync-opencode.md and .opencode/scripts/sync_opencode.py exist and deploy target/opencode/ into ~/.config/opencode/ with the singular->plural rename - read at HEAD 5c18ef918
- HYPOTHESIS: the published `dist-opencode` tree is directly consumable by an OpenCode client the
  way `dist-claude` is by Claude Code — confirm/refute on a live OpenCode install, or against the
  OpenCode plugin/marketplace resolution mechanics, before labelling any consumer step OBSERVED
  (verify-at-outline). ⛔ The `multiplattform` WS-05 park exists precisely because this has never
  been validated; if outline cannot confirm it, the D1/D2 steps that depend on it ship labelled
  HYPOTHESIS (designed, not yet consumed) rather than silently upgraded.
  - verdict: unverifiable | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: whether dist-opencode is directly consumable by an OpenCode client requires a live install (the multiplattform WS-05 park); not settleable from source at HEAD
- HYPOTHESIS: **OpenCode has no native marketplace command equivalent to Claude's
  `/plugin marketplace add`.** Its documented plugin surface is npm packages or local JS/TS files
  (`.opencode/plugins/`, `~/.config/opencode/plugins/`), and skills/agents/commands are discovered
  from config directories (`~/.config/opencode/{skills,agents,commands}/`); an `opencode plugin`
  CLI installs npm-style packages, not a plan-marshall-style bundle. Confirm/refute against
  `opencode.ai/docs/plugins` and the `opencode plugin` CLI surface before D0 selects the primary
  path (verify-at-outline). ⛔ This shapes D0's candidate set: the deploy-into-config-dir shape
  (protocol § 1.2) is the one with a working precedent inside this repository, but it is the
  developer inner loop, not a consumer flow.
  - verdict: unverifiable | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: OpenCode's install surface (npm/local JS-TS plugins, config-dir skills/agents/commands) is an external product fact - corroborated against opencode.ai/docs/plugins but that is an external doc, not implementing source; D0 settles it on a live install
- OBSERVED: **`/sync-opencode` is not a consumer install path.** It exists only as a command in
  this project repo (`.opencode/commands/sync-opencode.md`), so a consumer of the published refs
  has no access to it. The deploy shape it performs (generated `target/opencode/` → config dir via
  the singular→plural rename) remains a D0 candidate; the command itself does not. — operator
  direction 2026-09-11.
  - verdict: unverifiable | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: reconciliation with multiplattform PLAN-17/18 (whichever launches second re-reads the other) is a sequencing settlement, not a source-verifiable fact
- Verify-first clause: D0/D1/D2 must reconcile with `multiplattform` PLAN-17/PLAN-18, which own the
  same surface and are parked on the live-validation protocol. If the protocol runs before this
  plan ships, re-read those specs first; if it has not run, every consumer-path step stays labelled.
  - verdict: corroborated | checked_at: 5c18ef918 | by: tooling-truthfulness/cleanup | rescoped: n/a | evidence: /sync-opencode exists only as a command in this project repo (.opencode/commands/sync-opencode.md), unavailable to a consumer of the published refs - operator direction 2026-09-11 and confirmed by file location

## Expected Surface

- OBSERVED: `README.md` — D1, D3
- OBSERVED: `doc/user/install-claude.adoc` — D2 (moved Claude content; replaces
  `doc/user/installation.adoc`, which is DELETED in the same act — operator direction 2026-09-13)
- OBSERVED: `doc/user/install-opencode.adoc` — D2 (new OpenCode guide)
- OBSERVED: `doc/user/README.adoc` — D2 (index entry for the split; promoted from HYPOTHESIS —
  the rename forces an index edit, no longer conditional)
- OBSERVED: `doc/user/windows-wsl-setup.adoc` — D2 (2 reference retargets, orchestrator-measured)
- OBSERVED: `doc/developer/distribution.adoc` — D2 reference retargets + D3 (framing only; the
  matrix description is `multiplattform` PLAN-04's)
- OBSERVED: `doc/developer/build-architecture.adoc` — D2 (1 reference retarget, orchestrator-measured)
- OBSERVED: `doc/concepts/build-server.adoc` — D2 (2 reference retargets, orchestrator-measured)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-build-server/SKILL.md` — D2
  (1 reference retarget, orchestrator-measured)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/cache_freshness.py` —
  D2 (comment-only reference, orchestrator-measured)
- HYPOTHESIS: **a consumer-facing OpenCode install script** — D0, ONLY if the pinned path needs one
  (verify-at-outline). Candidate homes: a project-level `.opencode/scripts/` peer of
  `sync_opencode.py`, or the root `scripts/` tree. ⛔ `sync_opencode.py` deploys the *generated local
  tree* into the config dir and is only runnable from the plan-marshall repo; it is the developer
  inner loop and is NOT itself a consumer install from the published refs. D0 may reuse its deploy
  engine (the singular→plural rename) inside a consumer-facing script, but must not present the
  command as the consumer path. ⛔ If the pinned path needs NO script, D0 records that decision and
  the surface stays unclaimed.
- HYPOTHESIS: `marketplace/targets/opencode/**` — D0, ONLY if the pinned path reveals the generated
  root lacks the manifest the path expects (verify-at-outline). ⛔ Per `multiplattform` PLAN-17's
  out-of-scope rule, that is a REPORTED finding for the generator, staged separately — not absorbed
  into this documentation plan.

## Dependencies and Sequencing

- Depends on: none in this epic.
- **D0 gates D1–D3 by sequence, not by external dependency:** D0 runs first (it pins the path the
  documentation describes). D1–D3 are authored against D0's finding; if D0's live-install test
  cannot run in this plan's environment, D1–D3 fall back to honest HYPOTHESIS labelling of the
  designed shape.
- ⛔ **Sibling-epic duplication (accepted by operator direction):** overlaps `multiplattform`
  PLAN-18 at the user install guide (now `doc/user/install-claude.adoc` /
  `doc/user/install-opencode.adoc`, formerly `doc/user/installation.adoc`) and the README, and
  PLAN-17 at the install-path question (D0 is this plan's counterpart to PLAN-17's pin). Neither
  may run concurrently with this plan;
  whichever launches second must re-read the other's spec first. Recorded in
  `workstreams/WS-06-opencode-install-docs.md`.
- Adjacent to: `multiplattform` PLAN-04 (`/sync-opencode` inner loop), whose D3/D4 documentation
  this plan cross-references rather than restates.
- Does NOT depend on the `multiplattform` validation protocol: this plan ships honest labels
  instead of waiting. If the protocol runs before this plan ships, re-ground the claims first.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/tooling-truthfulness/plans/PLAN-07-opencode-install-docs.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO file under
`.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.