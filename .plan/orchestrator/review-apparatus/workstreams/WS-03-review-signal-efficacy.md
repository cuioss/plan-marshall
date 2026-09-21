# WS-03: Review-signal efficacy

epic: review-apparatus

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-03-review-signal-efficacy.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Owns whether a review that DOES arrive carries the findings it should, and whether we ingest
them. Two halves, both currently unverified: the production half — does the `#13` charter in
`pr-agent-settings` actually change what the model publishes, or is depth still suppressed by a
prompt clause unreachable from configuration; and the ingestion half — does plan-marshall
extract CodeRabbit's per-finding machine payload or strip it as noise. Its outcome is that a
finding count can be read as signal rather than as an artifact of an unmeasured suppressor.

## Scope

The two central config repos plus the ingestion standards that consume their output.

- In scope: `pr-agent-settings/.pr_agent.toml` (`extra_instructions` charter,
  `num_max_findings`) and its verification-in-effect; `automatic-review/standards/coderabbit.md`
  ingestion contract and whatever script enacts it; `coderabbit/.coderabbit.yaml`
  `enable_prompt_for_ai_agents` and the open premise behind that repo's `#3`; and — added
  2026-07-30 — the review-versus-gate coverage delta, i.e. what a review bot catches that an
  in-house gate structurally cannot, **and the back-feed of that delta into the plan-local review**
  (`ext-self-review-plan-marshall`'s deterministic detector registry).
- Out of scope: the await/detect seam and the participation classifier (WS-01); the org reusable
  workflow (WS-02); the barrier, merge path and landing channel (WS-04); ⛔ **and the build-gate
  half of the former PLAN-60 — ruff `select=`, `mypy test` parity, and gate footprint scoping —
  which was returned to `truthful-signals` by operator decision and must not be re-absorbed here.**

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-PR-003-coderabbit-ai-agent-block-strip-vs-extract | staged | Settle a self-contradicting ingestion contract; then settle the coderabbit `#3` premise it blocked |
| PLAN-PR-012-feed-pr-findings-back-into-local-review | staged | ⭐ Quick-wins only. Converts PR findings into small deterministic self-review detectors. First batch of the epic's Standing Practice |
| PLAN-PR-011-review-bots-catch-what-in-house-gates-cannot | staged | The REVIEW half of `truthful-signals` PLAN-60, split on operator decision. Build-gate half returned |
| PLAN-PR-004-pr-agent-charter-unverified-in-effect | staged | Verify `#13` changed model BEHAVIOUR, not just config; pass is SHAPED, not counted |

## Sequencing and Surface Notes

- PLAN-PR-003 before PLAN-PR-004. The contradiction PLAN-PR-003 settles is a live degradation on
  every CodeRabbit review (the block is already OFF at `a97b64f`), whereas PLAN-PR-004 is a
  measurement with no ongoing bleed. Ordering also matters for a second reason: PLAN-PR-004 reads
  a published review as its oracle, and a plan that has just clarified how a published review is
  ingested is better placed to read one.
- Both plans touch config repos NOT covered by plan-marshall's `.plan/` tooling: use
  `git -C {checkout}` and the CI abstraction's `--project-dir`, never `gh` directly.
- ⚠ Always confirm a config checkout's branch before reading it as live. The `coderabbit` tree
  was on an unmerged FALSIFIED branch at epic init and was cleaned up the same day — the check is
  worth repeating rather than assuming.
- **PLAN-PR-012 and PLAN-PR-011 are complementary and must NOT merge.** PR-011's D4 makes the
  review-versus-gate delta a *measured* signal; PR-012 *acts* on it by adding detectors. Measurement
  without action changes nothing; action without measurement cannot tell whether it worked. ⛔ Neither
  absorbs the other, and neither duplicates the other's measurement. PR-012 runs first because it needs
  no metric to start — the corpus is the five owed post-merge revisits.
- **PLAN-PR-012 is disjoint from everything else in this epic** (`pm-plugin-development` self-review),
  which is why it can sit early despite carrying no live bleed.
- ⛔ **PLAN-PR-011 sequences behind WS-01's PLAN-PR-007.** Its D2 edits the same participation
  classifier PLAN-PR-007 adds a taxonomy member to, and WS-01's PLAN-PR-006 adds a third state to
  the same surface. All three must land as ONE coherent taxonomy, sequenced — never paired.
- ⚠ PLAN-PR-003 also edits `automatic-review/standards/coderabbit.md` (and possibly `sourcery.md`),
  which WS-01's PLAN-PR-006 reads as its per-bot shape source. Sequence, do not pair.
- ✅ The former adjacency note about `truthful-signals` PLAN-116 is retired: that plan was released
  to this epic on 2026-07-30 and split across WS-01, so it is no longer a foreign surface.
