# Landing Analysis: PLAN-PR-041 — The model ladder leads with a superseded Flash

epic: review-apparatus
workstream: WS-03
pr: cuioss/pr-agent-settings#15 — https://github.com/cuioss/pr-agent-settings/pull/15

> Landing record for one shipped plan. Written by the `analyze` verb after verifying every
> claim against ground truth. ⛔ **This is a FOREIGN-repo landing**, the class where this epic
> has already been burned once — PLAN-PR-002's ship claim is still contradicted by an OPEN
> `cuioss-organization#235`. The method rule that landing established was applied here in full:
> corroborate against the FOREIGN PR, not against the local clone and not against the narrative.

## Corroboration — what was checked, and against what

Every material claim in the operator's report was confirmed FIRST-PARTY before any ledger write.
Nothing below is carried from the narrative.

| Claim | Verdict | Evidence |
|---|---|---|
| PR #15 merged | corroborated | `ci pr view --pr-number 15` → `state: merged`, `review_decision: approved`. The FOREIGN PR, per the PLAN-PR-002 method rule. |
| Squash-landed as `729165e` | corroborated | `git log origin/main` after `fetch --prune` → `729165e feat(model): promote gemini-3.7-flash…(#15)`, authored 2026-08-24 09:47 +0200. |
| Working branch deleted; `main` the only remote | corroborated | `fetch --prune` reported `[deleted] origin/feature/promote-gemini-3-7-flash`; `branch -r` lists only `origin/HEAD` and `origin/main`. |
| `model = vertex_ai/gemini-3.7-flash` | corroborated | `git show origin/main:.pr_agent.toml`:73. Read out of `origin/main`, not the worktree. |
| Ladder `3.6 → 3.5 → 2.5-flash → 2.5-pro` | corroborated | same file :74-79. 3.6 is demoted to FIRST fallback exactly as D2 specified — not dropped. |
| `temperature = 1.0` retained | corroborated | same file :134. |
| `custom_model_max_tokens = 1048576` | corroborated | same file :94. `max_model_tokens = 256000` unchanged at :156. |
| Sourcery APPROVED | corroborated | `ci pr reviews --pr-number 15` → one review, `sourcery-ai`, `APPROVED`, 2026-08-23T22:12Z. |
| CodeRabbit clean | corroborated | `ci pr comments` → 4 `coderabbitai` comments, 0 inline findings. |

## Deliverable Fidelity vs Spec

Five of five shipped as specified. The diff touched `.pr_agent.toml` and `README.adoc` and nothing
else — **exactly** the spec's Expected Surface, with no unplanned file.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — confirm Model Garden offers 3.7 to THIS project before promoting | shipped-as-specified | `README.adoc`:282-284 records a direct `generateContent` probe against `projects/<this project>/locations/global/publishers/google/models/gemini-3.7-flash` answering `HTTP 200` with `"modelVersion": "gemini-3.7-flash"`, and the same probe serving 3.6 and 3.5. The repository's own written precondition was honoured rather than waived on GA status. |
| D2 — promote leader, demote 3.6 to first fallback | shipped-as-specified | `.pr_agent.toml`:73-79. The ladder's newest-generation-first rule is restored. |
| D3 — settle the `temperature` question from a real run and record it | shipped-as-specified, **exceeded** | `README.adoc`:405-421. See below — this is the deliverable that came back stronger than written. |
| D4 — re-verify `custom_model_max_tokens` against the new leader | shipped-as-specified | `README.adoc`:242 now records that **neither** 3.7 nor 3.6 is registered in the pinned image, so the line stays REQUIRED; value kept at `1048576`, correct for 3.7's 1M window. The HYPOTHESIS was checked, not inferred. |
| D5 — update README where the promotion falsifies it | shipped-as-specified | 111 changed lines across the stale-registry section (:238-242), the ladder rationale and benchmark table (:277-321), and the Gemini-3 temperature section (:400-421). |

### ⭐ D3 came back stronger than specified — and with a matched negative control

The spec asked only for the observed answer. What landed is a **falsifiable** answer:
`gemini-3.7-flash` **accepts** `temperature` — `HTTP 200` at both `1.0` and `0.2`, and `200` again
with `top_p`, `top_k` and `candidate_count` all set — while still range-validating it (`3.0` and
`-1.0` each return `400`, "supported range is from 0 (inclusive) to 2.0001 (exclusive)").
"Deprecated" on Google's 3.7 page therefore means **advice, not rejection**.

⭐⭐ **The `200` was proven non-vacuous by a matched negative control**: the same endpoint on the
same model *rejects* `thinkingLevel: MINIMAL` with `HTTP 400 Thinking level is unsupported`. So the
accept is a real accept and not blanket tolerance of anything sent. This is the exact remedy for the
vacuous-guard archetype this epic tracks (n≥6, repeatedly re-introduced BY fixes for it) — a passing
check that could not have failed proves nothing, and here it was made able to fail.

The conclusion recorded is the one the spec predicted for the right reason: the key STAYS at `1.0`,
because deleting it hands the model PR-Agent's own `0.2` rather than removing the parameter. The
only config-reachable suppression, `custom_reasoning_model = true`, also disables system messages,
so it is not a temperature-only lever. Revisit if a future model answers `400`.

## Metrics and Anomalies

- Tokens / duration: **not measured — no plan-marshall lifecycle ran.** The work was executed
  ad-hoc by orchestrator recommendation, so there is no metrics store, no execution manifest, and
  no phase ledger. ⛔ This is a KNOWN, ACCEPTED consequence of the ad-hoc route, not a gap to
  investigate: an ad-hoc run has no instrumented producer.
- Diff: 2 files, +165 / −43.
- Anomalies: none in the change itself.

## Routing and Merge Behavior

- **Review**: Sourcery `APPROVED`; CodeRabbit 4 comments, 0 inline findings. Both clean before the
  merge, both corroborated against PR state rather than against the report.
- **⛔ pr-agent (`cuioss-review-bot`) did not participate — and structurally cannot.**
  `git ls-tree -r origin/main` returns exactly two paths: `.pr_agent.toml` and `README.adoc`. The
  repository has no `.github/` tree at all, so no workflow invokes pr-agent there. CodeRabbit and
  Sourcery review it because they are org-level GitHub Apps; pr-agent runs from a workflow and
  therefore does not. Its absence here is **expected, not a defect** — recorded because an
  unexplained absent bot is precisely the signal this epic exists to keep legible.
- **CI/merge**: squash merge to `main`, head branch deleted. No conflicts, no rebase, no re-verify.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-PR-041 --status shipped`
- [x] row `pr` stamped — `cuioss/pr-agent-settings#15`
- [x] row `landing` stamped — `landings/PLAN-PR-041.md`
- [x] row `plan_marshall_plan_id` stamped — `NO_PLAN` (the ad-hoc sentinel; no lifecycle plan exists)
- [x] Watch opened — the reviewer-configuration repo is unreviewable by the reviewer it configures
- [x] Watch opened — first-real-review confirmation of the runner identity (below)
- [x] resume_anchor updated
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator resume-summary`

## Follow-Ups

1. **⚠ The entitlement proof is a PROXY, not the runner's identity — carried as a Watch, not closed.**
   The `HTTP 200` came from a direct call using OPERATOR USER credentials; the workflow authenticates
   as a **WIF service account**. Publisher-model entitlement is project-scoped, which is what makes
   this the right proxy — but it is a proxy, and the distinction is the honest one to keep.
   ⭐ **The failure mode is bounded and self-healing**: if 3.7 were not served to that identity, the
   ladder falls through to 3.6-flash and the review still publishes. A wasted call, never a lost
   review. **Closing evidence** is `"model": "gemini-3.7-flash"` in the next real review run log.
   ⛔ Do not record this as closed until that line is read first-party.
2. **⛔ The repo that configures the third reviewer is the one repo that reviewer cannot review.**
   Recorded as a Watch. Adjacent to PLAN-PR-030 (the instrument that measures our gates can report
   them perfect) and PLAN-PR-026 (nobody-reviewed and reviewed-clean are one signal) — the same
   shape one level up: the reviewer's own configuration changes are reviewed by everyone except the
   reviewer they configure. Not staged as a plan; no deliverable is obvious and the two named specs
   already own the surrounding surface.
3. **The change is live org-wide immediately.** `.pr_agent.toml` is read from the default branch, so
   the next PR opened in ANY `cuioss` repo is reviewed by 3.7-flash. No fan-out step is owed, and
   nothing else in the org needs a corresponding change.
4. **No sequencing consequence for PLAN-PR-038.** PR-038 publishes generated packs INTO this
   repository as new artifacts; this landing changed the `[config]` block and the README. The spec's
   recorded adjacency note holds unchanged — different files, no collision, either order works.
