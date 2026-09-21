# PLAN-37: `credentials_config` Key Convention Splits Write and Read

epic: plan-optimization
workstream: WS-10

> Staged 2026-07-21 from a **consumer-repo run (API-Sheriff)**. The operator supplied a complete
> root-cause analysis against 0.1.1166/0.1.1172; **the orchestrator re-verified every cited line
> at current HEAD (0.1.1180) before staging** — all confirmed, nothing had moved.
>
> Mechanism labels per the binding practice (lesson `2026-07-21-22-001`).

## Objective

Any provider skill whose scripts self-identify **unprefixed** while the registration flow writes
**bundle-prefixed** keys **silently loses its provider config**. Observed live on Sonar; the
defect is not Sonar-specific.

**Symptom (operator-observed on a real consumer run):** with a Sonar provider registered in
`marshal.json`, every `workflow-integration-sonar` call fails — `sonar.py fetch_findings` and the
sonar-roundtrip finalize step report *"Sonar not configured"*, and once a token exists the REST
client aborts with `ValueError: HTTPS required when authentication is configured` — even though
`credentials_config` demonstrably contains the provider block.

## Root cause — ALL OBSERVED, re-verified at HEAD 0.1.1180

Two naming conventions meeting an exact-match dict lookup:

| # | Fact | Location (verified) |
|---|------|---------------------|
| 1 | The consumer self-identifies **unprefixed** | `workflow-integration-sonar/scripts/sonar.py:67` — `_SONAR_SKILL = 'workflow-integration-sonar'`; passed at `:398` `load_credential(_SONAR_SKILL, 'auto')` and `:719` `get_authenticated_client(_SONAR_SKILL)` |
| 2 | The read is an **exact match with no normalization** | `manage-providers/scripts/_providers_core.py:84` — `config.get('credentials_config', {}).get(skill_name, {})` → returns `{}` for the unprefixed name |
| 3 | The write is **also exact, no normalization** | `_providers_core.py:106` — `config['credentials_config'][skill_name] = provider_config` |
| 4 | The **filesystem path side DOES normalize** | `resolve_credential_path()` ~`:228-230` strips the bundle prefix, with an explicit comment naming this exact scenario: *"skill_name may be `plan-marshall:workflow-integration-sonar`"* |
| 5 | Empty config ⇒ no `url` ⇒ the HTTPS raise | `_providers_core.py:~553` — rejects non-https when an `authorization` header is present |

**Sharpening of the operator's framing (worth recording):** it is *not* that read and write use
opposite conventions — **neither** `read_provider_config` nor `write_provider_config` normalizes.
The asymmetry is that `_providers_core` normalizes on the **filesystem-path** side but **not** on
the **`marshal.json` key** side, and its two *caller populations* use different spellings
(registration writes prefixed; consumer scripts read unprefixed). The secrets-file side tolerates
both; the `marshal.json` side is spelling-sensitive.

**Writers identified** (for the survivor sweep): `manage-providers/scripts/_cred_edit.py`,
`_cred_configure.py`, `_providers_core.py`, and `manage-config/scripts/_config_core.py`.
`marshall-steward` does **not** write `credentials_config` directly — grepped, zero hits.

## Repro and field workaround (both operator-supplied)

- **Repro**: register a Sonar provider so `credentials_config` is keyed
  `"plan-marshall:workflow-integration-sonar"`, then run any `sonar.py` verb — the provider-config
  lookup returns empty.
- **Workaround that must become unnecessary**: putting `url`/`organization`/`project_key`
  directly into `~/.plan-marshall/credentials/workflow-integration-sonar.json` works, *because the
  file-path resolution strips the prefix* and the merged config then carries an https url. That
  the workaround exists is itself confirmation of fact #4.

## Deliverables

1. **Normalize the `credentials_config` key the way `resolve_credential_path` already does.**
   Canonicalize to **ONE** form on write; on read accept **both** (exact match, then the
   stripped/prefixed alternate). Reuse the existing prefix-stripping logic rather than writing a
   second one — a second normalizer is how this class recurs.
2. **Regression for the prefixed-write / unprefixed-read round trip.** The exact shape that
   failed: write under `plan-marshall:workflow-integration-sonar`, read as
   `workflow-integration-sonar`, assert the block resolves and the merged config carries the url.
3. **Sweep the blast radius and migrate existing configs.**
   **HYPOTHESIS**: other provider skills are affected identically (the operator's impact claim).
   **Confirm/refute artifact**: enumerate every skill that calls `load_credential` /
   `get_authenticated_client` and compare the name it passes against what the registration flow
   writes for it. Name the affected set — or refute and say Sonar is the only one. Then ship a
   one-time migration for configs already written under the losing spelling.
4. **Plugin-doctor rule (operator-suggested — confirm it is the right home).** Flag
   `credentials_config` keys that match no skill's lookup name. **HYPOTHESIS** that plugin-doctor
   is the right enforcement point; **confirm/refute artifact**: whether plugin-doctor can see
   `marshal.json` (it lints marketplace components, and `marshal.json` is project config). If it
   cannot, propose the correct home rather than forcing the rule into the wrong analyzer.

Four deliverables, under the split guard. D1+D2 are the fix and its pin; D3 and D4 each gate on
their own artifact.

## Expected Surface

- `manage-providers/scripts/_providers_core.py` (`read_provider_config` `:84`,
  `write_provider_config` `:106`, `resolve_credential_path` `:228-230`)
- `manage-providers/scripts/_cred_edit.py`, `_cred_configure.py` (writers)
- `manage-config/scripts/_config_core.py` (writer)
- `workflow-integration-sonar/scripts/sonar.py` (`:67`, `:398`, `:719`) — likely read-only once
  the core normalizes
- possibly other provider skills (D3 determines)
- plugin-doctor rule + `rule-catalog.md` / `rule-provenance.md` (D4, if that is the right home)
- tests under the manage-providers suite

## Dependencies and Sequencing

- Depends on: none. **Emittable immediately** — disjoint from all four running plans
  (PLAN-32 `script-shared/build`, PLAN-33 `platform-runtime`, PLAN-34 `marshall-steward`,
  PLAN-36 `phase-6-finalize`).
- ⚠ **Adjacency cluster in `manage-config`**: this plan may touch
  `manage-config/scripts/_config_core.py`, while **PLAN-35** (staged) touches
  `_cmd_build_map.py`/`_cmd_aspect_classify.py` and **PLAN-38** (staged) touches the
  domain-detect path. Different files in one skill — check before running any two concurrently.
- **Consumer-facing and higher-priority than the meta-only queue items**: it silently breaks a
  registered provider in downstream repos, and the only escape is a workaround the operator had
  to discover by reading source.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-37-credentials-key-normalization.md"

PROVENANCE AND CONFIDENCE: this defect was root-caused by the operator during a real consumer-repo run (API-Sheriff) against 0.1.1166/0.1.1172, and the ORCHESTRATOR RE-VERIFIED EVERY CITED LINE AT CURRENT HEAD 0.1.1180 before staging — all confirmed, nothing had moved. Facts 1-5 in the spec are OBSERVED, not inferred: sonar.py:67 self-identifies unprefixed and passes that name at :398 and :719; _providers_core.py:84 reads with an exact-match .get() and no normalization; :106 writes with the same exact key; resolve_credential_path ~:228-230 DOES strip the bundle prefix and carries a comment naming this exact scenario; and the HTTPS raise at ~:553 is what surfaces the empty config. You do not need to re-derive the root cause — go straight to the fix. Deliverables 3 and 4 ARE hypotheses and carry named confirm/refute artifacts; honour those labels.

ONE SHARPENING the spec records and you should preserve: it is NOT that read and write use opposite conventions — NEITHER read_provider_config NOR write_provider_config normalizes. The asymmetry is that _providers_core normalizes on the FILESYSTEM-PATH side but not on the marshal.json KEY side, and its two caller populations use different spellings (registration writes bundle-prefixed, consumer scripts read unprefixed). The secrets-file side tolerates both; the marshal.json side is spelling-sensitive. Fix the key side by REUSING the existing prefix-stripping logic — do not write a second normalizer, because a second normalizer is exactly how this class recurs.

Writers already identified for your survivor sweep: manage-providers/scripts/_cred_edit.py, _cred_configure.py, _providers_core.py, and manage-config/scripts/_config_core.py. marshall-steward does NOT write credentials_config — grepped, zero hits, so do not go looking there. Note PLAN-34 is running concurrently IN marshall-steward, so if your sweep pulls you into that skill, STOP and report rather than editing it.

Four plans run concurrently (PLAN-32 script-shared/build, PLAN-33 platform-runtime, PLAN-34 marshall-steward, PLAN-36 phase-6-finalize) — all disjoint from your manage-providers + workflow-integration-sonar footprint. ⚠ If D3's sweep or D4's rule pulls you into manage-config/scripts/_config_core.py, note that PLAN-35 and PLAN-38 are staged against other files in that same skill — flag the adjacency rather than assuming it is free.
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-37.md is recorded}
