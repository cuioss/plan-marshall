# Run report — 080-key-order-canonicalization-unreachable-and-false-green (run 01)

**Date (UTC):** 2026-08-11    **Branch:** `claude/key-order-canonicalization-unreachable-hygrin` (harness-assigned; kept as-is per lane contract)    **PR:** _pending_    **Outcome:** _in progress_

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

_(filled in as implemented — see commits)_

## Build gate

_(pending)_

## Findings

_(pending — verification sub-agent, CI, PR review)_

## Reviewer participation

_(pending)_

## Cost

_(recorded at finalize)_

## Contract check (Step 9)

_(recorded at finalize)_

## What have we learned (Step 9)

_(recorded at finalize)_

## Residue

_(recorded at finalize)_
