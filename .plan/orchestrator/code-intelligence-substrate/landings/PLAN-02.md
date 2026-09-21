# Landing Analysis: PLAN-02 — resolver-ext-point-seam

epic: code-intelligence-substrate
workstream: WS-02
pr: 1067 — https://github.com/cuioss/plan-marshall/pull/1067

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against
> ground truth — a pasted claim is a lead, never a fact.

## Ground-Truth Corroboration

| Claim | Verdict | Evidence |
|---|---|---|
| PR #1067 merged | **corroborated** | `ci pr view --head feature/resolver-ext-point-seam` → `state: merged`; `git log origin/main` → `c6b501e6a` |
| Merged as `c6b501e6a` | **corroborated** | HEAD of `origin/main` after fetch |
| 5/5 deliverables | **corroborated at the surface level** | The merge commit title matches the seam's subject; the plan's own message enumerates the shipped files and tests |
| Landing message written before merge? | ✅ **NO — and this is new** | `-001` is stamped `11:50:04Z`; the merge completed ~15:02. ⚠ **The message was still written 3h before the merge** — see below |

⚠ **The premature-emission archetype recurred, in a milder form.** `-001` again narrates in the past
tense ("What landed") from a pre-merge snapshot — and it names head `405b05f069…`, which is **not** the
merged HEAD (`76c7200b6` pre-squash, `c6b501e6a` on main). It happened to become true. Already
delegated to `truthful-signals` from the PLAN-11 landing as their `code-intelligence-substrate-009`;
this is the **fourth** instance and reinforces it rather than opening a new item.

⭐ **The plan's own retraction is the model behaviour this epic wants.** Message `-011` explicitly
supersedes `-004`, states which claim went stale and when ("true at 11:51, false by 13:40"), and
instructs the reader to drain both together. **Standing rule 2 applied as written**: the retraction
outranks the earlier finding, and both were drained as one unit.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — declare the derivation-resolver extension point (Axis-C ABC) | shipped-as-specified | `script-shared/scripts/extension/extension_base.py`; `extension-api/standards/ext-point-derivation-resolver.md` |
| D2 — discover resolvers, merge edge sets with provenance | shipped-as-specified | `extension-api/scripts/extension_discovery.py`; new `_derivation_merge.py`; `test_derivation_merge.py` |
| D3 — delegate the graph family | **shipped-modified (scope widened)** | Spec said four consumers; the real count was **six** — `_build_internal_deps_map`'s five callers plus `render_module_markdown` at `_cmd_client_render.py:230` |
| D4 — re-home the Maven coordinate join as the Maven resolver | shipped-as-specified | Characterization fixtures now cover the duplicated `com.example:auth-service` coordinate |
| D5 — document the substrate | shipped-as-specified | `doc/concepts/code-intelligence.adoc`, `extension-architecture.adoc`, `README.adoc`, ADR-013 + ADR-014 |

**5/5 shipped.** D3's widening is the epic's standing rule 4 firing for the *third* time in three
landings: the spec's cited call site was again a sample. ⭐ Here it was caught by the outline Q-Gate
*before* code existed — the first time in this epic that the sample-not-enumeration trap was caught by
a gate rather than by a later reader.

## Metrics and Anomalies

- **Tokens: ~5.6 M** · **worked: 5h35m** · 14 tasks (9 planned + 5 review fixes) · 6 phases · 25/25
  finalize steps · `partial: false`.
- **Anomalies:**
  - ⚠ **Cost watch now at FOUR points.** 5.6 M is the epic's most expensive landing yet, but it is a
    `multi_module` / `complex` / deep-lane plan, so unlike PLAN-11 it is **not** obviously
    above-anchor. ⛔ Do not add it to the "above anchor" tally without an applicable anchor — the
    absence of one is itself the PLAN-CIS-008 finding.
  - ⚠ **Three consecutive phase-5 dispatches were cut off by transient API errors** (HTTP 500, 529,
    529). Disk state was verified before each re-dispatch rather than blind-retried; no work lost, no
    work duplicated. ✅ **This is the documented harness-kill mitigation working as designed** — no
    action owed, recorded as third-party-instability cost.
  - ⚠ **~90 minutes of wall clock lost to the ADR-012 collision** (abort at 13:10, re-land at 15:02).

## Routing and Merge Behavior

⛔ **The final merged HEAD was reviewed by ZERO of three configured bots**, and the finalize read
green throughout. Corrected picture per `-011`:

| Bot | What it actually reviewed | Saw the merged HEAD? |
|---|---|:---:|
| pr-agent (**required**) | `405b05f06` only, an informational "PR Reviewer Guide" with no actionable content | no |
| coderabbit | `371854d14` — the HEAD *before* the 5 fixes it requested | no |
| sourcery | nothing, any revision | no |

- **Sourcery's refusal is a 150 000-diff-character SIZE CAP, not a quota** — misclassified as
  `hard_quota` in both persisted artifacts. ⛔ **It will refuse every PR this size, forever.** Waiting
  is guaranteed futile; the only remedies are splitting the PR or accepting the gap knowingly.
- **CI/merge:** all gates green; squash-merged via the queue to `c6b501e6a`. One aborted merge attempt
  at 13:10 (ADR namespace collision), then rebase + renumber + re-verify + re-push.
- **Surface collisions: none with PLAN-11**, which ran concurrently and landed first. ✅ **Second
  consecutive correct disjointness call.** The one collision that did occur was **cross-PR and
  cross-epic** — upstream #1066 claiming `doc/adr/012` — a namespace the disjointness model does not
  model at all.

⛔ **The five CodeRabbit defects were caught by luck, not by a gate.** The pre-merge review barrier was
overridden at 12:37 and the merge was seconds from completing at 13:08. The 13:10 abort — for an
unrelated ADR numbering collision — forced the rebase that re-triggered CodeRabbit, which then found 5
defects, 3 Major. **Without the collision, all five would have merged**, including a
`merge_resolver_edges()` that returned `status: ok, edge_count: 0, notes: []` while dropping every
edge — a vacuous confident zero inside the plan whose stated purpose is anti-vacuity.

## Reconciliation Actions

- [x] row `status` → `shipped` · `pr` `1067` · `landing` `landings/PLAN-02.md` ·
      `plan_marshall_plan_id` `resolver-ext-point-seam`
- [x] epic.md queue reconciled from status.json
- [x] **F2 and F4 retired** — the empty-graph finding and the disarmed feasibility gate are the defects
      this plan was staged to fix
- [x] Watches updated; new defects/watches added from the drain
- [x] `plan-id-rename-map.md` updated — PLAN-02's row moves from "running" to "shipped"
- [x] resume_anchor updated; START-HERE regenerated

## Follow-Ups

Twelve messages drained (11 from the plan, **plus one inbound from `truthful-signals` the plan did not
count**):

| Message | Signal | Disposition |
|---|---|---|
| `-001` | the landing | reconciled (this record) |
| `-002` | a cited call site is a SAMPLE — 3 instances in one plan, inside a plan that flagged the trap | **folded** into PLAN-CIS-015 |
| `-003` | a centralizing refactor silently widened a lazy contract into an eager one | **promoted** to the global lessons corpus |
| `-004` | review coverage 1-of-3 (superseded) | **delegated** to `review-apparatus`, with `-011` |
| `-005` | `review-retrospective.md` not regenerated after loop-back; shipped a confident RED its own history refutes | **delegated** to `review-apparatus` |
| `-006` | size-cap refusal misclassified as `hard_quota` — opposite remediations | **delegated** to `review-apparatus` |
| `-007` | an overridden pre-merge barrier survived a rebase to a different HEAD | **delegated** to `review-apparatus` |
| `-008` | ADR namespace collision invisible to `no_overlap` / textual conflict detection | **delegated** to `truthful-signals` |
| `-009` | monitors armed with tokens that cannot match; timeout indistinguishable from waiting | **delegated** to `truthful-signals` |
| `-010` | self-review has no detector for duplicate-claimable keys or discard-without-report | **staged** as PLAN-CIS-021 |
| `-011` | correction to `-004` | **delegated** with `-004` |
| `truthful-signals-019` | three token ledgers disagree; the smallest is surfaced as `actual_tokens` | **accepted**, staged as PLAN-CIS-022 |

⭐ **`truthful-signals-019` also resolved PLAN-CIS-020's mandatory cross-epic check** — see that spec.
