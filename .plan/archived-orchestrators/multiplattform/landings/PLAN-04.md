# Landing Analysis: PLAN-04 — A developer can deploy the generated OpenCode tree in one command

epic: multiplattform
workstream: WS-04
pr: [#1372](https://github.com/cuioss/plan-marshall/pull/1372) — merged as `5dc7efd5a94813242fb99b3be68c286e29f8b3a1`

> Landing record for one shipped plan. Written by the `analyze` verb after verifying
> every claim in the operator's landing narrative against ground truth. The narrative
> was treated as a set of leads; each verdict below names the artifact that settled it.

## Deliverable Fidelity vs Spec

Every deliverable shipped as specified. No deliverable was dropped or silently re-scoped.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| **D1** — `sync-opencode` project-local skill, prune bounded to managed entries | shipped-as-specified | `.claude/skills/sync-opencode/SKILL.md` (+152), `scripts/sync_opencode.py` (+407). `_derive_synced_bundles` resolves the managed namespace against exact `marketplace/bundles/` directory names; flags `--source`/`--target-dir`/`--bundles`/`--dry-run` present |
| **D2** — unit tests under `test/sync-opencode/`, no live install | shipped-as-specified | `test/sync-opencode/test_sync_opencode.py` (+296), **14 test functions**. Every named behaviour has ≥1 case: path mapping, dry-run (×2), `--bundles` subsetting, stale-managed deletion (×2), unmanaged preservation (×3) |
| **D3** — OpenCode inner-loop documentation | shipped-as-specified | `doc/developer/marketplace-build.adoc` §"OpenCode inner loop" (+61). All three deploy options present; the `.opencode/` shadowing caveat and the "env var cannot point at singular `target/opencode/`" caveat both stated |
| **D4** — `distribution.adoc` states the live matrix | shipped-as-specified | `doc/developer/distribution.adoc` (+49/-13) now reads "two active entries — `claude` and `opencode`"; the two-row table matches `.github/workflows/claude-distribute.yml:39-46` read at analysis time. No "Claude-only" or "hypothetical" claim survives; the unverified-on-live-client statement is present |

**Verification not re-run.** D2's tests were corroborated by static read (14 `def test_` functions), not by execution — a verify run against repository source is plan work, outside the orchestrator's small-ops carve-out. CI's own `verify / verify` job passed (835s), which is the executing evidence.

### Realized vs declared surface

The spec declared four named paths plus the glob `test/sync-opencode/**`. The landing touched **seven** files:

| Realized file | Declared? |
|---|---|
| `.claude/skills/sync-opencode/SKILL.md` | yes |
| `.claude/skills/sync-opencode/scripts/sync_opencode.py` | yes |
| `doc/developer/distribution.adoc` | yes |
| `doc/developer/marketplace-build.adoc` | yes |
| `test/sync-opencode/__init__.py`, `test/sync-opencode/test_sync_opencode.py` | yes, via the `test/sync-opencode/**` glob |
| `pyproject.toml` | **no — undeclared** |

One undeclared entry (`pyproject.toml`, a one-line test-path registration). This is the standard's **under-declaration** residual class, at its mildest: a build-config line the spec's four deliverables implied but never named. The spec's declaration is **not** being retro-corrected — PLAN-04 is terminal and will never be paired again, so the correction would serve no gate. It is recorded here as corpus evidence for the disjointness gate's known error profile.

## Metrics and Anomalies

- **Tokens: unavailable.** The work ran in OpenCode outside the plan-marshall lifecycle, so no `manage-metrics` record exists. Not estimated.
- **Duration (PR window, from git/CI ground truth):** first branch commit `90e189d38` at 09:00:23Z → review-fix `caff5c0fc` at 09:24:26Z → merged 09:41:13Z. **~41 minutes**, two commits on the branch.
- **CI:** 10 checks, `overall_status: success`. `verify / verify` SUCCESS (835s); `verify / conclusion` SUCCESS on both runs. One `verify / verify` SKIPPED on the earlier run `33377522517` — the documented docs-only footprint gate, not a failure.
- **Anomalies:** none material. The operator's local plugin-doctor drift did not reproduce in CI, as reported.

## Routing and Merge Behavior

- **Review:** three bots. **Sourcery** approved with no findings. **cuioss-review-bot** and **CodeRabbit** raised **8 distinct actionable findings** across 5 threads; **7 fixed** in `caff5c0fc`, **1 declined**.
  - *Bundle-derivation prune bug* — flagged by both cuioss-review-bot and CodeRabbit. `_derive_synced_bundles` truncated entry names at the first hyphen, so `plan-marshall-*` collapsed to `plan` and an unrelated user entry like `plan-my-tool` was classified as managed and deleted on prune. **Fixed**, with `test_sync_opencode_preserves_user_entry_that_shares_bundle_prefix` as the regression test. This was the one genuinely operator-consequential finding — a data-loss path against user-managed OpenCode skills.
  - *Unreachable `partial` status* removed (zero hits remain in script or SKILL.md), *`opencode.json`-only source accepted* (`sync_opencode.py:356`), *MD040 fence language*, and two doc-accuracy corrections — all **fixed** and verified in the merged tree.
  - *Declined:* CodeRabbit's suggestion to generate or CI-check the `distribution.adoc` target table against the workflow matrix. The operator declined it on the record as a deliberate documentation trade-off — the table is an accurate snapshot and the prose already names the workflow as source of truth. The bot kept the finding open and offered a follow-up issue; the operator declined that too and resolved the thread. **Recorded as a watch below**, not as a defect.
- **CI/merge:** merged via the GitHub merge queue, squashed to a single commit on `main`. **No rebase conflicts, no re-verify signals, no surface collision** — PLAN-04 ran alone, so no pairing evidence was generated.

## Reconciliation Actions

- [x] row `status` → `landed` — `orchestrator queue --transition PLAN-04 --status landed`
- [x] row `pr` stamped `#1372` — `orchestrator queue --set-row PLAN-04 --field pr`
- [x] row `landing` stamped `landings/PLAN-04.md` — `orchestrator queue --set-row PLAN-04 --field landing`
- [x] row `plan_marshall_plan_id` stamped `n/a` — `orchestrator queue --set-row PLAN-04 --field plan_marshall_plan_id`
- [x] epic.md reconciled from status.json; both generated blocks regenerated via `orchestrator resume-summary`
- [x] watch opened: the declined `distribution.adoc` table-drift finding
- [x] open defect opened: the stale generated executor (out of epic scope)
- [x] `resume_anchor` updated

**Terminal-status token.** `landed` is used rather than the workflow doc's `shipped`. Both are members of `TERMINAL_PLAN_STATUSES`, and PLAN-01/02/03 in this same queue all carry `landed` — a second terminal spelling in one queue would read as two different end-states. Consistency within the ledger decided it.

## Follow-Ups

- **Watch — `distribution.adoc` target table can drift from the workflow matrix.** The declined review finding is real but deliberately unowned: the table is a human-maintained snapshot that names `.github/workflows/claude-distribute.yml` as its authority. *Re-check trigger: any change to that workflow's `strategy.matrix.include`, or PLAN-17/PLAN-18 touching `distribution.adoc`.* Recorded as a watch in `epic.md`.
- **PLAN-04's OpenCode plural-layout HYPOTHESIS remains `unverifiable` and is unchanged by this landing.** D2's tests are temp-directory only by design, so nothing here reaches a live OpenCode install. The claim stays owned by WS-05's validation protocol § 1.2. ⛔ Do not read "PLAN-04 landed" as evidence the plural-directory assumption holds.
- **WS-05's dependency is now satisfied on the tooling side.** The validation protocol named `/sync-opencode` as its deploy step; that skill now exists. WS-05 remains parked on operator access to a live OpenCode install — the unpark gate is unchanged.
- **No spec surface was folded or widened by this landing**, so no `## Expected Surface` edit was owed anywhere in the corpus.
