# Run report — 080-key-order-canonicalization-unreachable-and-false-green (run 01)

**Date (UTC):** 2026-08-11    **Branch:** `claude/key-order-canonicalization-unreachable-hygrin` (harness-assigned; kept as-is per lane contract)    **PR:** [#1156](https://github.com/cuioss/plan-marshall/pull/1156)    **Outcome:** completed (auto-merge armed; landing delegated to the merge queue)

## Skills loaded

Loaded by path (bundle source, cloud-clone-safe route):

- `plan-marshall:ref-code-quality` — plus its `standards/error-handling.md` (fail-closed
  classification rules (b)/(d) map directly onto this plan's honest-signal defects).
- `pm-plugin-development:plugin-script-architecture`
- `pm-dev-python:python-core` (Python production code)
- `pm-dev-python:pytest-testing` (Python tests)

`plan-marshall:persona-implementer` and `pm-plugin-development:plugin-architecture` were not
separately loaded; the code-quality + script-architecture + python-core standards already govern the
production and bundle-doc surface this plan touches.

## Claim verification (every claim re-derived at the moment of the claim)

The plan labels every claim `HYPOTHESIS`. Re-derivation against the **current tree** (which has
evolved past the plan's snapshot — several truthful-signals plans have landed since it was authored):

| Claim | Verdict | Evidence |
|---|---|---|
| `normalize_keys` ends in an unconditional `return {'action': 'normalized'}` | **CONFIRMED** | `_config_core.py:717-731` — constant return, no report of appended keys |
| `order_config_keys` appends unrecognized keys last; `save_config` routes through it | **CONFIRMED** | `_config_core.py:96-114` (append loop), `:117-121` (`save_config` → `order_config_keys`) |
| `upgrade` Stage 2 runs `sync-defaults`+`steps-sort` but NOT `normalize-keys` | **CONFIRMED** | `upgrade-flow.md:299-304` — two invocations, no `normalize-keys` |
| `upgrade` bypasses the interactive menu entirely | **CONFIRMED** | `marshall-steward/SKILL.md:148-150` — "bypass both the mode routing and the Main Menu entirely" |
| Stage 2 sub-step list emitted from `upgrade.py` (not read from doc) | **CONFIRMED (with nuance)** | `upgrade.py:105-144` `_STAGE_SPECS` emits **coarse** sub_steps (`reconcile-marshal-json`). The **fine** steps (`sync-defaults`/`steps-sort`/+`normalize-keys`) live only in the doc's expansion — so adding `normalize-keys` at the fine grain is a doc edit with no code/doc divergence. |
| `sync-defaults` returned `success, added_count: 1` while adding nothing | **REFUTED (already fixed)** | `_cmd_sync_defaults.py:452-494` computes `added_count = len(added)` where `added` accrues only genuine additions (`_deep_merge_missing` `if key not in live`). `test_sync_defaults.py:296` already pins `added_count == 0` on a no-op and `:307` pins `added_count == len(added)`. D3 is already satisfied + tested. |
| Every config write is an unguarded whole-document read-modify-write | **CONFIRMED** | `load_config` → caller mutation → `save_config` with no lock/CAS. |
| `order_config_keys` docstring asserts two routed paths while five sites exist and ≥3 bypass it | **CONFIRMED (contested row, re-derived)** | 5 marshal.json write sites: `save_config` (`_config_core.py:117`, routed), `write_provider_config`→`_save_marshal`→`order_config_keys` (`_providers_core.py:91-111`, routed), `ext_defaults_set` (`_config_core.py:338`, **bypass**), `ext_defaults_set_default` (`:361`, **bypass**), `opencode_runtime._save` (`opencode_runtime.py:78`, **bypass**). Two routed, **three bypass**. The docstring's clause "so no write appends a block out of canonical order" over-claims. |
| `check_freshness` compares only against the local clone manifest, no upstream leg | **CONFIRMED** | `cache_freshness.py:134-185` compares newest cache-version dir vs clone-root `dist-manifest.json` version; no git-remote/upstream fetch. |
| upgrade-flow doc claims a sub-step owns cache-vs-upstream skew and nothing implements it | **CONFIRMED** | `upgrade-flow.md:157-161` "This sub-step owns [cache-versus-upstream skew]" — but the code compares cache-vs-**clone** (the table at `:146` honestly says "marketplace-clone manifest version"). |
| The uninstall/install remediation text is asserted by an existing test | **CONFIRMED** | `cache_freshness.py:76-79` `REMEDIATION`; `test_cache_freshness.py:232-237` asserts the literal `/plugin uninstall` + `/plugin install` strings. This is **test-pins-the-defect**. |
| `/plugin update plan-marshall` is sufficient and non-destructive | Operator-supplied; applied per plan guidance | Shipped as the corrected remediation; validated by the Step-6 cold-read sub-agent. |

## Gate verdicts

### D1 — honest-signal shape (mutates nothing)

- **(a) Return shape.** `normalize_keys()` returns
  `{'status': 'warning'|'success', 'action': 'normalized', 'unrecognized_keys': [...]}`.
  When `order_config_keys` had to append top-level keys absent from `CANONICAL_TOP_LEVEL_KEY_ORDER`,
  `unrecognized_keys` names them and `status` is `warning`; otherwise `unrecognized_keys` is `[]` and
  `status` is `success`. This matches the epic's established shape (a non-clean status naming the
  offenders), and lets a caller distinguish a truly canonical result from one that merely preserved
  stray blocks.
- **(b) Is an unrecognized top-level key ever legitimate → warning, not error.** All plan-marshall
  blocks are in the canonical order, so an unrecognized top-level key is not expected in normal
  operation — but a consumer project or a legacy/hand-edit can carry one, and `order_config_keys`
  deliberately **preserves** it rather than dropping it. A hard error would (1) break a consumer who
  legitimately extended `marshal.json`, and (2) make an idempotent hygiene verb fail. So the signal is
  a **warning** that names the offenders — visible and actionable without being destructive or fatal.
- **(c) Position in Stage 2 → LAST**, after `sync-defaults` (which may add keys) and `steps-sort`.
  `normalize-keys` is the **unconditional** canonicalizer; every `save_config` write already
  canonicalizes *recognized* keys, so `normalize-keys`' distinct value is guaranteeing that a
  canonicalizing write happens even when `sync-defaults`/`steps-sort` are both no-ops. Running it last
  gives it the final word after any key-adding operation.

### D6 — what `fresh` is allowed to mean (mutates nothing)

An upstream-blind comparison (cache vs local marketplace-**clone** manifest) **may** return `fresh`,
but only as a verdict explicitly scoped to the local clone; it must never read as a claim of currency
with the actual upstream. A real upstream leg requires a network fetch of the git remote — which turns
a deterministic read-only emitter into a network-dependent one **and** reaches into the separately-owned
executor-preflight / version-resolution surface the plan places OUT OF SCOPE. Per the plan Goal's
explicit alternative ("compares against upstream **or declares that it cannot**"), `check_freshness`
takes the **declare-it-cannot** path: every verdict carries a `compared_against` scope field so a
`fresh` verdict self-discloses that it does not verify clone-vs-upstream currency, and the doc's
over-claim (D8) is corrected to name cache-vs-**clone** skew.

## Deliverables

| # | Deliverable | Commit | State |
|---|---|---|---|
| D1 | GATE — honest-signal shape (mutates nothing) | — | Verdicts recorded above (return shape, warning-not-error, position LAST). Contested bypass-count claimed above. |
| D2 | `normalize_keys` names what it could not order | `da77a8c` | `normalize_keys()` returns `status`/`action`/`unrecognized_keys`; `unrecognized_top_level_keys()` helper added; dispatch surfaces the verb's own status; manage-config SKILL.md (verb table + canonical-invocations) and marshall-steward Re-Run Pass step (a) updated in lock-step. |
| D3 | `sync-defaults` reports effect, not intent | — (already satisfied) | REFUTED as a live defect: current `_cmd_sync_defaults.py` computes `added_count = len(added)` from actual `_deep_merge_missing` additions, and `test_sync_defaults.py:296` already pins `added_count == 0` on a no-op (`:307` pins `== len(added)`). No change needed; recorded as a re-derived refutation. |
| D4 | Guard the whole-document read-modify-write | `da77a8c` | `save_config` optimistic-concurrency guard (`ConcurrentConfigModificationError` when the file changed on disk since `load_config` read it) + atomic write; `load_config` records the fingerprint. |
| D5 | `upgrade` Stage 2 runs the canonicalizer | `b185b49` | `normalize-keys` added to upgrade-flow.md Stage 2 as the LAST reconcile step. Verified the coarse sub-step (`reconcile-marshal-json`) is emitted from `upgrade.py` but the FINE steps (`sync-defaults`/`steps-sort`/`normalize-keys`) live only in the doc — so this is a doc-grain edit with no code/doc divergence; `upgrade.py` correctly needs no change. |
| D6 | GATE — what `fresh` may mean (mutates nothing) | — | Verdict recorded above (declare-it-cannot; `fresh` is clone-scoped). |
| D7 | Implement D6 | `b185b49` | Every `check_freshness` verdict stamps `compared_against: local_clone_manifest`, so `fresh` self-discloses it does not check clone-vs-upstream currency. |
| D8 | Retire the vacuous ownership claim | `b185b49` | upgrade-flow.md's "owns cache-versus-upstream skew" corrected to cache-versus-clone; both sub-steps' lack of an upstream leg stated plainly. |
| D9 | Correct remediation text + the test that pins it wrong | `b185b49` | `REMEDIATION` → non-destructive `/plugin update plan-marshall` + version verify (constant + upgrade-flow prose + docstring example). Test corrected; **seen RED first** — see Findings. |
| D10 | Tests | `da77a8c` + `b185b49` | (a) `test_config_write_guard.py::test_normalize_keys_names_unrecognized_top_level_key` + CLI `test_main_normalize_keys_warns_and_names_unrecognized_key`; (b) `::test_normalize_keys_is_byte_stable_on_already_canonical_file`; (c) `test_upgrade_flow_stage2.py`; (d) `test_cache_freshness.py::test_every_verdict_declares_its_local_clone_comparison_scope`; (e) `::test_save_config_refuses_a_concurrent_overwrite`. |

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` is non-empty (Python changed: `_config_core.py`,
`manage-config.py`, `cache_freshness.py`, and three test modules), so the full path applies.

`./pw verify plan-marshall` → **`verify: SUCCESS`**, **15887 passed, 1 skipped**. The whole
plan-marshall bundle's tests pass, including every cross-module `save_config`/`load_config` consumer —
the D4 change to the hot config write path regressed nothing. Per-commit `./pw quality-gate` was clean
(`total_issues: 0`, empty `issues[]`) before each Python-touching commit.

## Findings

- **D9 red-first (demonstrated).** The corrected `test_remediation_names_the_commands_literally`
  was run against the OLD `REMEDIATION` and failed RED before the text was changed — captured:
  `assert '/plugin update plan-marshall' in cache_freshness.REMEDIATION` failed, the assertion error
  showing the old string "Run '/plugin marketplace update' … '/plugin uninstall plan-marshall'
  followed by '/plugin install plan-marshall'". The final test additionally asserts the destructive
  `/plugin uninstall` and `/plugin install` commands are absent and a version-verify step is present —
  all of which also fail against the old text. After the fix it is GREEN. Disposition: **fixed**.
- **D9 cold-read (Step 6, isolated sub-agent).** An independent sub-agent was given ONLY the new
  remediation text and asked what it would run to recover. It answered exactly `/plugin update
  plan-marshall` then `/plugin` (to verify the version) — the non-destructive update plus a version
  verify, with no reach for uninstall/install. The wording succeeded. Disposition: **accepted**.
- **Test-body substring pitfall (self-caught).** The first form of the corrected test asserted the
  bare word `'uninstall' not in REMEDIATION`, which failed because the new text says "no uninstall or
  reinstall" (operator reassurance). Tightened to assert the destructive *commands* `/plugin uninstall`
  / `/plugin install` are absent — the actual defect. Disposition: **fixed**.
- **Verification sub-agent (Step 6, independent).** Dispatched against plan.md + the branch diff.
  Verdict: 9/10 deliverables fully satisfied in the committed range; D3 correctly recorded as
  already-fixed; all five D10 tests pin what they claim; D4 confirmed a genuine optimistic-concurrency
  guard (re-reads disk at save time), not merely an atomic write; and it **independently re-derived
  the contested write-site count** (5 sites, 2 routed / 3 bypass) matching this report, and
  **independently re-ran the D9 cold-read** with the correct non-destructive answer. It flagged
  residuals already inside the plan's out-of-scope (the check→`os.replace` TOCTOU window; the three
  bypass writers remaining unguarded) — acceptable, and now honestly documented rather than hidden.
  Its ONE actionable finding: the D9 report record (red-first + cold-read) and the Deliverables /
  Build-gate sections were still placeholders in the commit it reviewed (`b185b49`).
  **Disposition: already fixed** — those sections were committed in `e501316`, after the agent's
  review snapshot; the finding is a timing artifact of reviewing an earlier HEAD, not an open gap.

## Reviewer participation

Expected population derived from configuration — the `author_login` of each
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc
(`coderabbit.md` → `coderabbitai`; `sourcery.md` → `sourcery-ai`; `pr-agent.md` → `cuioss-review-bot`),
cross-named by `.github/workflows/pr-agent.yml`.

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Posted a "PR Reviewer Guide" against the diff: tests present, no security concerns, one focus-finding — a concurrency concern on the D4 guard's `_CONFIG_FINGERPRINTS`. Addressed in commit `5bb92fc` (unique per-write temp name; the guard's cross-process guarantee and its deliberate in-process limit documented at the definition site) and answered on the thread explaining the threat model + plan scope. |
| `coderabbitai` | `rate-limited` | Published only a refusal: "Review limit reached … Next review available in: 49 minutes." It engaged but did not review this diff. |
| `sourcery-ai` | `rate-limited` | Review body is only "you have reached your weekly rate limit of 500000 diff characters." A quota notice in place of a review. |

**Coverage: 1 of 3 reviewed** — `cuioss-review-bot` reviewed (and its finding was addressed);
`coderabbitai` rate-limited (window reopens ~49 min); `sourcery-ai` rate-limited (weekly quota). The
§ Step 8 shortfall disclosure fired: the run proceeds on 1-of-3 coverage and **says so** — the two
shortfalls are routine rate limits outside our control, which disclose-not-block per the contract.

## Cost

- **Tokens:** not surfaced to the agent as a precise per-run figure in this session — stated plainly
  rather than estimated.
- **Wall-clock:** a single interactive Claude Code cloud session on 2026-08-11, from the first branch
  push through arming auto-merge (roughly one hour, dominated by two full `./pw verify` passes at ~4.5
  min each and the CI re-runs each push triggered).
- **Population:** this single cloud session's usage as the harness counts it. ⛔ NOT comparable to a
  plan-marshall `metrics.toon` total — that counts an orchestrator-plus-agent dispatch tree under
  plan-marshall's own per-task billing boundary, which this interactive session does not share. The
  figures are not made comparable and are not presented as if they were.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | Done — named above. |
| 2 Branch | Done — harness-assigned `claude/key-order-canonicalization-unreachable-hygrin`, pushed to `origin` before any work; branch form recorded (harness-assigned). |
| 3 Plan directory | Done — `doc/plans/truthful-signals/080-…/plan.md` exists and opens with the first-instruction block (verified present before the move). |
| 4 Implement | Done — commits carry the `Co-Authored-By: Claude` trailer; all deliverables addressed. |
| 4 Per-commit gate | Done — `./pw quality-gate` (`total_issues: 0`, empty `issues[]`) run before each Python-touching commit. |
| 4 Pushed | Done — every commit pushed; no unpushed commit remains at finalize. |
| 5 Build gate | Done — Python changed → full path; `./pw verify plan-marshall` → SUCCESS, 15887 passed / 1 skipped. |
| 6 Verification sub-agent | Done — independent verifier + isolated D9 cold-read; findings and dispositions in § Findings. |
| 7 PR cycle | Done — PR #1156; both comment surfaces read (conversation + inline threads, the latter empty); every comment dispositioned. |
| 8 Merge gate | Conditions 1–3 met; reviewer shortfall disclosed (condition 4); auto-merge armed and the landing delegated to the merge queue (this cloud session cannot self-wake to watch the queue — a completed outcome per § Step 8, not partial). |
| 8 Bridge | No status/bookkeeping write landed under `doc/plans/` outside this plan's own directory; the report carries the PR number and per-deliverable outcome. |
| 9 This check | This table. |

GitHub access path used: the **GitHub MCP server** (cloud path). Branch form: **harness-assigned**. A
cloud run owes no `/sync-plugin-cache` (machine-local build step, not a debt this lane records).

## What have we learned (Step 9)

**No contract change proposed.** The run exercised the cloud-plan-lane end to end without hitting an
ambiguous, unworkable, or unnecessary step. The one notable situation — the plan's snapshot had drifted
from the current tree (D3 already fixed and test-pinned; the freshness three-valued verdict already
shipped) — is exactly what the contract's "re-derive every claim at the moment of the claim" and the
plan's own HYPOTHESIS labelling are built to absorb, and they did: claims were re-verified, the refuted
one (D3) was recorded as such rather than a no-op change manufactured to match the plan. No step
produced an artifact it could not, and no command failed in the environment. Nothing here is run-specific
evidence of a contract gap, so proposing an edit would be speculative — which the contract forbids.

## Residue

- **Three `order_config_keys` bypass writers remain unguarded whole-document writes** —
  `ext_defaults_set`, `ext_defaults_set_default` (`_config_core.py`), and `opencode_runtime._save`.
  D4 was scoped by the plan to the `save_config` path, and its out-of-scope excludes a general
  concurrency/ordering framework, so these are left as-is but now **honestly documented** (the
  `order_config_keys` docstring names them as bypasses). A follow-up that wants every marshal.json
  write to enforce ordering and lost-update safety would route these three through `save_config` /
  `order_config_keys` — a separate, reviewable change.
- **In-process concurrent-writer serialization is not provided** by the `save_config` guard (documented
  at the definition site). Closing it needs a per-load token or a held file lock — the locking primitive
  the plan leaves out of scope. Not a defect for these one-shot CLI verbs, which never write the config
  from two in-process writers concurrently.
- **The upstream-currency question stays structurally out of scope.** D7 makes `check_freshness` honest
  about NOT checking clone-vs-upstream currency (`compared_against: local_clone_manifest`), but a real
  upstream leg belongs to the separately-owned executor-preflight / version-resolution surface. Per the
  plan's sequencing note: the version-freshness story now has a truthful *scope-disclosure* signal, but
  no end-to-end upstream check — a follow-up owned elsewhere.
