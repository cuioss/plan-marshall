envelope_version=1
sender_type=orchestrator
sender_id=grounded-evidence-pinning
epic=code-intelligence-substrate
kind=finding
created=2026-09-14T08:36:50Z

# Grounded evidence pinning — external prior art, plus a deferred validation obligation

## Source

`langchain-ai/openwiki` (MIT, TypeScript, LangChain). Read from the implementation, not from secondary
coverage: `src/claims/core/types.ts`, `src/claims/evidence/repository/resolver.ts`, `src/claims/guidance.ts`,
`README.md`. Surfaced by a Medium road-test article (David R Oliver, 2026-08-26); the article's description
of the mechanic checks out against the source.

## The mechanic

```
Claim    { id, statement, evidence: Evidence[] }
Evidence { resource: "repo://src/server.ts#L40-L82", version: <opaque resolver-owned token> }
```

- `version` for a line range is `linerange-v1:<sha256 of the range content>:<exterior anchor metadata>`;
  for a whole file, `repo-file-v1:<sha256>`.
- The agent submits `ProposedEvidence` — **resource only**. The version is resolved deterministically by the
  resolver. A model can never supply the hash that proves its own claim.
- The resolver **relocates** a citation when edits shift it: `locateUnchangedLineRange` first, then
  `locateChangedLineRange` via the hashed lines surrounding the range. Ambiguous anchor pairs deliberately
  resolve to `null`.
- Three states: `current` / `stale` / `unresolved`. Plus a `retract` operation. Never a silent re-pin.
- Sidecars mirror pages (`openwiki/.claims/concepts/feature.json`) and carry `pageVersion`, a sha256 of the
  prose the claims back.
- Reconciliation is **sparse**: issue-free claims are retained deterministically when omitted from the
  submission, so the model is shown only the stale subset and never re-states an unchanged claim.
- Run shape `begin → submit_plan → next_page → submit_page → finish`, checkpointed, with a **durability
  boundary per page**; finalization re-proves the whole run before discarding the checkpoint.
- A claim id is unique corpus-wide and owned by exactly one page — enforced structurally, not detected.

## Why this belongs to this epic

Cost is `resident_context × turns`, and the measured average byte re-read is 44.6×. Sparse reconciliation
attacks exactly that: the substrate holds the pins, and the model's working set is the *delta*, not the
corpus. It is the same lever WS-06 aims at, arrived at independently by a shipping tool.

Second, we already own the hashing half. ADR-006 (`Generated-tree drift is gated at the consume boundary`)
plus `source_fingerprint.compute_source_tree_fingerprint`, the `.emit-marker.json` `file_hashes` manifest,
and `sync._staleness_guard` are content-hash drift gating over a shared `hash_objects` primitive. What we
hash today is *generated tree ↔ source tree*. We have never hashed *prose ↔ source*. A claim sidecar is an
extension of an existing primitive, not new infrastructure.

Third, it is the machine-checkable form of the only move that terminates restatement drift — replace the
restatement with a pointer at its source (PLAN-TRUTH-089: 27% of finalize findings were self-seeded across
5 chains). Today that is a reviewer's judgment call backed by `ext-self-review-plan-marshall` heuristics
(`source-of-truth duplicates`, `stale count-prose`). A hash-pinned citation makes it a comparison.

## The five design elements worth taking

1. **Resolver-owned versions.** The claimant proposes the resource; the substrate computes the proof.
2. **Anchor relocation with a third state.** A naive line hash false-stales on every unrelated edit above
   the citation, and a false-stale rate is what kills adoption of a pinning layer. Ambiguity must fail loud
   to `unresolved`, never silently re-pin — the `truthful-signals` theme, implemented correctly.
3. **Sparse reconciliation.** Unchanged pins are retained by omission. This is the token lever.
4. **Per-unit durability boundary.** A crash costs at most one unit. Finer grain than our step records.
5. **Single-owner invariant, enforced structurally.** Better than our detector-based duplicate hunting.

## What does NOT transfer

`CLAIMS_SUBSTANCE_GUIDANCE` reads: *"Completeness takes priority over minimizing Claim count… Ensure every
material, source-dependent proposition the wiki relies on is represented."* That is an **exhortation to a
model with no derivation behind it**. Every individual claim is falsifiable; the SET is not. Nothing in the
design detects a material fact that was never claimed.

This is `derive-completeness-never-assert-it` verbatim, and it feeds `volume-read-as-coverage`: receipts on
18 claims present as "page verified" while the uncited prose is unchecked. **A pinning layer buys
no-false-positives, not no-false-negatives** — and a `verified:` stamp on the page actively hides the
difference. Any adoption here must derive pin coverage from an independent population (e.g. the
`same-document normative directives` detector population) and publish that population size, per the
set-guarding detector rule.

Do not adopt the tool itself: it rewrites `CLAUDE.md` / `AGENTS.md` managed blocks (collides with
`tools-sync-agents-file`), `--init` destructively replaces an existing wiki, it is 0.x with no cost cap, and
it would stand up a second documentation substrate beside `manage-architecture`. The mechanic is the asset.

Worth noting separately: openwiki's coding-agent integration mode runs the whole pipeline *inside* Claude
Code / Codex / Cursor / OpenCode over MCP (`openwiki_begin` … `openwiki_finish`), on the host's authenticated
session and native repo tools, with openwiki keeping only the durable job lifecycle and deterministic
finalization. That is our script-owns-state / model-does-semantics split, independently arrived at, and
multi-runtime by construction — the same constraint the fleet rule states.

## Operator instruction — the deferred validation obligation

**Do not validate this early, and do not open a workstream for it now.** The operator's standing instruction:
run a **full validation after every step of the substrate is implemented AND after several plans have
actually executed against it.**

The reason is not caution, it is observability. An evidence-pinning layer's real failure modes are
**population statistics**, not unit behaviours, and none of them is visible from a test suite or from a
single plan:

- **false-stale rate** — pins that flipped `stale` without the cited fact changing;
- **unresolved rate** — pins the relocator refused to place, which is the cost side of failing loud;
- **coverage** — material facts carrying no pin at all, derived from an independent population, never asserted;
- **realized token delta** — the sparse-reconciliation saving actually banked, measured against the
  `resident_context × turns` model rather than against a headline figure.

Every one of those needs a real corpus of pins **aged across real edits by real plans**. A validation run
before that point would measure a substrate nothing has yet drifted underneath, and would report a clean
signal that means nothing — the precise failure this epic's sibling epic is named after.
