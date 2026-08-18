# Gaps — 080-key-order-canonicalization-unreachable-and-false-green

**Source:** verification.md (same directory)   **Open items:** 7

## G1 — Handle `ConcurrentConfigModificationError` at the `manage-config` dispatch boundary

- **Kind:** bug
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-config/scripts/manage-config.py:913-985` — `main()`; the exception is raised at `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_core.py:212-218` — `save_config`
- **What is wrong:** D4 introduced a new exception type that no caller handles — `grep 'except ConcurrentConfigModificationError'` across `marketplace/` returns zero hits, against 35 `save_config` call sites in 12 modules. Only the `normalize-keys` arm of `main()` is wrapped in a `try/except`. An execution probe that races a concurrent write between `load_config` and `save_config` inside the real handler `_cmd_orchestrator.cmd_orchestrator_set` produced `UNCAUGHT: ConcurrentConfigModificationError`; `main()` has no wrapper around `result = cmd_*(args)`, so the process dies with a traceback and prints no TOON.
- **Why it matters:** `ref-workflow-architecture/standards/manage-contract.md:34` requires every `cmd_*` handler to return a dict with a `status` field and `main()` to print TOON and return 0; expected errors are reported as `status: error`. A traceback on stderr with an empty stdout is unparseable by the LLM callers these verbs exist for — the guard converts a silent lost update into an unstructured crash for every verb except the one the plan happened to touch. The same escape exists in `marshall-steward`'s `upgrade.py:331-355` `migrate-bot-lists` sub-step.
- **Fix:** wrap the dispatch in `manage-config.py:main()` so `ConcurrentConfigModificationError` becomes `error_exit(str(e), error_type='concurrent_modification')` printed as TOON with exit 0, and do the same at the `upgrade.py` sub-step that calls `save_config`. Remove the now-redundant per-arm `try/except` on `normalize-keys` or leave it — but the general path must not be the only unhandled one.
- **Done when:** a test drives a `manage-config` verb other than `normalize-keys` through a load→concurrent-write→save race and asserts the CLI emits `status: error` with a `concurrent_modification` marker and exit code 0, with no traceback on stderr.
- **Module/topic:** `plan-marshall:manage-config` — config write path

## G2 — Name the Claude runtime seed in the `order_config_keys` bypass enumeration

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_core.py:168-177` — `order_config_keys` docstring; the missing site is `marketplace/bundles/plan-marshall/skills/platform-runtime/scripts/_claude_runtime_impl.py:44-79` — `ClaudeRuntime.project_initial_setup`
- **What is wrong:** the docstring states the routed paths and then enumerates what it is "NOT reached by": the two extension-defaults writers and "the OpenCode runtime seed". A full re-derivation finds six `.plan/marshal.json` write sites, not five: `save_config` (routed), `_providers_core._save_marshal` (routed), `ext_defaults_set`, `ext_defaults_set_default`, `opencode_runtime` `project_initial_setup`, and `_claude_runtime_impl` `project_initial_setup` — the last writing through `claude_runtime._write_json` (`claude_runtime.py:1205`) with top-level `runtime` and `project_dir` and no ordering. That site predates the plan (commit `55cf61f1`, an ancestor of the landing commit), so the report's re-derived "5 sites, 2 routed / 3 bypass" is wrong at the moment it was stated.
- **Why it matters:** the docstring is the authority a future reader consults to know which writers must be routed; an exhaustive-looking list that omits a live writer recreates exactly the over-claim this plan corrected. The Claude seed is the *default* target's seed, so the omitted writer is the more commonly executed of the two.
- **Fix:** extend the `order_config_keys` docstring enumeration to name both runtime seeds (Claude and OpenCode) as bypass writers, and state the count as four bypass / two routed.
- **Done when:** the docstring names `_claude_runtime_impl.project_initial_setup` alongside the OpenCode seed and the two extension-defaults writers, and any count it states is four.
- **Module/topic:** `plan-marshall:manage-config` — `_config_core` ordering authority

## G3 — Reconcile the Re-Run Remediation Pass ordering with Stage 2's load-bearing position

- **Kind:** doc-drift
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/marshall-steward/SKILL.md:478-505` — Re-Run Remediation Pass steps (a)/(e)/(f); contradicted by `marketplace/bundles/plan-marshall/skills/marshall-steward/references/upgrade-flow.md:302-332` — Stage 2
- **What is wrong:** Stage 2 now runs `normalize-keys` **last** and states that "its position is load-bearing" because `sync-defaults` and `steps-sort` are conditional writes. The Re-Run Remediation Pass still runs `normalize-keys` as step **(a)** — first — with `sync-defaults` at (e) and `steps-sort` at (f). The run edited step (a)'s prose to surface `unrecognized_keys` but left the position untouched, although the plan's Expected surface names this file as one that "must stay consistent with the new Stage 2 wiring".
- **Why it matters:** the two documents give a reader opposite accounts of whether the canonicalizer's position matters, and the D10(c) test pins the order only inside Stage 2, so the menu path is unpinned. Either the ordering rationale is wrong (in which case Stage 2's justification misleads) or the menu pass is mis-ordered.
- **Fix:** move the `normalize-keys` call in the Re-Run Remediation Pass to run after `sync-defaults` and `steps-sort` (re-lettering the steps, or stating the execution order explicitly if the letters are load-bearing elsewhere); alternatively, if the position is genuinely immaterial because every `save_config` write canonicalizes, soften Stage 2's "load-bearing" claim to say what is actually true — that `normalize-keys` is the unconditional writer and its position among conditional writers does not change the result.
- **Done when:** the two documents state one consistent ordering rule, and a test pins the Re-Run Pass order the same way `test_upgrade_flow_stage2.py` pins Stage 2's.
- **Module/topic:** `plan-marshall:marshall-steward` — upgrade + remediation flows

## G4 — `runtime` and `project_dir` are first-party keys the new warning calls unrecognized

- **Kind:** bug
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_core.py:130-152` — `CANONICAL_TOP_LEVEL_KEY_ORDER`; producers at `_claude_runtime_impl.py:70-74` and `opencode_runtime.py:73-79`; reader at `platform_runtime.py:234-240` — `_resolve_target`
- **What is wrong:** `project initial-setup` writes top-level `runtime` (Claude and OpenCode targets) and `project_dir` (Claude target) into `marshal.json`, and `platform_runtime._resolve_target` reads `runtime.target` back. Neither key is in `CANONICAL_TOP_LEVEL_KEY_ORDER`, so after D2 `normalize-keys` returns `status: warning` naming them, and both Stage 2 and the Re-Run Pass instruct the operator to surface that list as "a stray or consumer-added block".
- **Why it matters:** the honest signal fires on the product's own keys, describing first-party configuration as stray. A warning that is always present on a legitimately-configured project is the noise that trains operators to ignore the signal — the failure mode this epic exists to prevent.
- **Fix:** either add `runtime` (and `project_dir`, if it is meant to persist) to `CANONICAL_TOP_LEVEL_KEY_ORDER` at their intended slots and document them in `manage-config/standards/data-model.md`, or stop persisting them as top-level keys. If the plan's out-of-scope boundary on redesigning the canonical list is honoured, raise it as a schema decision rather than leaving the false warning in place.
- **Done when:** `unrecognized_top_level_keys()` returns `[]` for a `marshal.json` produced by `project initial-setup` followed by `manage-config init`, demonstrated by a test.
- **Module/topic:** `plan-marshall:manage-config` / `plan-marshall:platform-runtime` — marshal.json top-level schema

## G5 — Confirm or replace the `/plugin update plan-marshall` remediation

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/marshall-steward/scripts/cache_freshness.py:86-90` — `REMEDIATION`; restated at `cache_freshness.py:62` (docstring example) and `references/upgrade-flow.md:153-156, 291`; contradicted by `doc/user/installation.adoc:57-64` and `README.md:46`
- **What is wrong:** the plan labelled "`/plugin update plan-marshall` is sufficient and non-destructive" as an unverified operator-supplied claim and required confirmation before shipping it as guidance. The report's evidence is the Step-6 cold read, which tests whether a reader follows the wording, not whether the command exists or is the correct recovery here. The repository's own user documentation prescribes a different sequence for refreshing an installed plugin: `/plugin marketplace update plan-marshall`, reinstall the plugins, then restart Claude Code or run `/reload-plugins`. The new remediation mentions neither reinstall nor `/reload-plugins`.
- **Why it matters:** this string is emitted verbatim to an operator on a refusing (`stale` / `unknown`) freshness verdict — the one moment the upgrade is blocked and the operator has nothing else to go on. If the command does not exist, or does not refresh the cache without a reload, the gate refuses and the remediation does not clear it.
- **Fix:** confirm against the Claude Code plugin CLI whether `/plugin update <name>` exists and refreshes the installed cache without a reload. If it does, add the reload/restart step if one is required and reconcile `doc/user/installation.adoc` § "Updating the snapshot" to the same sequence. If it does not, replace `REMEDIATION` (and its two doc restatements plus the docstring example) with the documented sequence, and update `test_remediation_names_the_commands_literally` in lock-step.
- **Done when:** one update sequence appears in `cache_freshness.REMEDIATION`, `upgrade-flow.md`, `doc/user/installation.adoc`, and `README.md`, and each command in it is one the plugin CLI accepts.
- **Module/topic:** `plan-marshall:marshall-steward` — cache-freshness remediation + user installation docs

## G6 — Record the provider write path as an unguarded whole-document read-modify-write

- **Kind:** omission
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-providers/scripts/_providers_core.py:212-239` — `write_provider_config`, and `:91-111` — `_save_marshal`
- **What is wrong:** `write_provider_config` reads the whole `marshal.json`, mutates `credentials_config`, and writes the whole document back through `_save_marshal`, which uses a plain `write_text` — no load fingerprint, no `os.replace`. It is a **routed** writer for ordering purposes, so it escaped the report's residue list, which enumerates only the three *bypass* writers as "remaining unguarded whole-document writes". The lost-update window D4 closes on `save_config` is wide open here, and the write is not even atomic.
- **Why it matters:** a reader of the residue would conclude that every remaining unguarded writer is one of the three named bypass sites and that routing through `order_config_keys` implies being covered by D4 — neither is true. A concurrent `credentials edit` and any `manage-config` write still lose one side silently.
- **Fix:** route `_save_marshal` through `_config_core.save_config` (which already applies the ordering, the fingerprint guard, and the atomic replace), pairing it with a `_config_core.load_config` at the read end so the fingerprint is recorded; or, if the provider path must stay independent, replicate the fingerprint + `os.replace` there. At minimum, name this site in the residue and in the `order_config_keys`/`save_config` docstrings as an unguarded routed writer.
- **Done when:** a test races a concurrent write against `write_provider_config` and shows the other writer's change survives, or the path delegates to `save_config` and the existing D4 test covers it.
- **Module/topic:** `plan-marshall:manage-providers` — marshal.json write path

## G7 — Add `compared_against` to the upgrade-flow's documented parse set

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/marshall-steward/references/upgrade-flow.md:138-141` — the freshness sub-step's parse instruction
- **What is wrong:** the sub-step tells the LLM router to "Parse `freshness`, `refuses_upgrade`, and `remediation`". D7's whole contribution is the fourth field, `compared_against`, which every verdict now stamps; it is explained in the prose below the verdict table but is absent from the field list the router is told to read.
- **Why it matters:** the truthful scope disclosure is emitted but not in the set the one documented consumer is instructed to consult, so a `fresh` verdict can still be reported upward as unqualified currency — a smaller instance of the archetype the plan targets.
- **Fix:** extend the parse sentence to `freshness`, `refuses_upgrade`, `compared_against`, and `remediation`, and state that a `fresh` verdict must be reported with its comparison scope attached.
- **Done when:** `upgrade-flow.md`'s parse instruction names `compared_against`, and the `## Canonical invocations` entry for `cache_freshness — check` in `marshall-steward/SKILL.md` lists it among the emitted fields.
- **Module/topic:** `plan-marshall:marshall-steward` — upgrade-flow freshness gate
