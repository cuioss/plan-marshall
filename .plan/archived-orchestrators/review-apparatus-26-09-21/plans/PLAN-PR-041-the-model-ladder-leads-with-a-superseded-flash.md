# PLAN-PR-041: The model ladder leads with a superseded Flash

epic: review-apparatus
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Operator-requested 2026-08-23. Every model fact below was verified against Google's own
> documentation and against the two foreign repositories BEFORE staging, not assumed.

## Objective

The org reviewer leads its fallback ladder with `vertex_ai/gemini-3.6-flash`. Google released
**`gemini-3.7-flash`** on 2026-08-13 — a newer generation of the same Flash line, at the same
introductory price, with the same 1M context window. The ladder's own stated ordering rule is
**newest-generation-first**, so it now violates its own rule. Promote 3.7 to the leader, demote 3.6
to the first fallback, and settle the one parameter question the promotion raises.

This is a *configuration currency* change, not a defect fix. It is staged rather than absorbed
because the promotion is entangled with a **documented contradiction in Google's own guidance** that
the repository's README asserts as settled fact in three places.

## Deliverables

1. **Confirm the Model Garden card offers `gemini-3.7-flash` to this project** before changing the
   leader. This is the repository's own written precondition — its README records a `404` ladder on
   the 3.x *pro* tier that cost ~8 wasted calls and a minute per review, and the `404` text ("not
   found or your project does not have access to it") is ambiguous enough to read as a transient
   fault. ⛔ Do not skip this on the strength of the model being GA in general.
2. **Promote the leader and re-order the ladder.** `model = "vertex_ai/gemini-3.7-flash"`, with
   `vertex_ai/gemini-3.6-flash` inserted as the FIRST fallback ahead of 3.5-flash. The ladder is
   ordered newest-generation-first by its own documented rule; leaving 3.6 out of it entirely would
   make the first fallback a two-generation drop.
3. **Settle the `temperature` question and record the answer.** Google's "What's new in Gemini 3.7
   Flash" page lists `temperature`, `top_p`, `top_k` and `candidate_count` as **deprecated
   parameters to remove**, while the general Gemini 3 developer guide — which does not mention 3.7
   at all — still says to keep `temperature` at `1.0`. The two pages disagree and the newer one is
   not reachable from the older one. ⛔ **The toml cannot resolve this by deleting the key**: the
   pinned image sets `kwargs["temperature"]` for every model absent from
   `NO_SUPPORT_TEMPERATURE_MODELS`, which contains no Gemini id, so removing `temperature = 1.0`
   yields pr-agent's own `0.2` default reaching the model — the exact Gemini-2.5-era value the
   current comment block exists to prevent. Determine from a real run whether 3.7 **accepts-and-
   ignores** the parameter or returns **HTTP 400**, and write the observed answer into the file.
4. **Re-verify `custom_model_max_tokens` against the new leader.** 3.7-flash is 1M in / 64k out, so
   `1048576` remains correct — but the line is REQUIRED rather than optional tuning, because an
   unregistered model makes `get_max_tokens()` raise, and the pinned image's `MAX_TOKENS` table stops
   at the 3.5 pair. Confirm 3.7 is likewise absent there and keep the line with its reason updated.
5. **Update `README.adoc` where the promotion falsifies it.** Three sections assert the current
   leader as fact: the stale-upstream-registry section (which names `gemini-3.6-flash` as the
   canonical example of an absent id), the ladder rationale and its benchmark table, and the
   Gemini-3 temperature section. ⭐ The README already carries a correction notice recording that an
   earlier revision wrongly claimed 3.6-flash was registered — do not repeat that shape by asserting
   3.7's registry status without checking it.

Five deliverables, inside the split guard.

## Claim Labels

- OBSERVED: the configured leader is `vertex_ai/gemini-3.6-flash` — read at
  `pr-agent-settings/.pr_agent.toml`:51, with `fallback_models` at :52 listing
  `3.5-flash`, `2.5-flash`, `2.5-pro` and **no 3.6 entry below the leader**.
  - verdict: corroborated | checked_at: f6d058b4b | by: review-apparatus/status | rescoped: n/a | evidence: Read cuioss/pr-agent-settings/.pr_agent.toml first-party: model = vertex_ai/gemini-3.6-flash at :51, fallback_models at :52-56 listing 3.5-flash, 2.5-flash, 2.5-pro with no 3.6 entry below the leader.
- OBSERVED: `gemini-3.7-flash` is the current Flash release — GA 2026-08-13 per Google's
  "What's new in Gemini 3.7 Flash", 1M context / 64k output, listed as a stable model on the
  Gemini API models page alongside 3.6, 3.5 and the 3.5-lite / 3.1-lite variants.
  - verdict: corroborated | checked_at: f6d058b4b | by: review-apparatus/status | rescoped: n/a | evidence: Google 'What's new in Gemini 3.7 Flash' (ai.google.dev/gemini-api/docs/latest-model) gives model id gemini-3.7-flash, GA 2026-08-13, 1M context / 64k max output. The models page (ai.google.dev/gemini-api/docs/models) lists it as stable alongside 3.6-flash, 3.5-flash, 3.5-flash-lite and 3.1-flash-lite. No 'gemini-3-flash' stable id exists; gemini-3-flash-preview is a separate preview entry.
- OBSERVED: `gemini-3.6-flash` is **not deprecated and carries no retirement date**, and the
  introductory pricing ($0.75 / 1M input, $3.75 / 1M output) applies to BOTH 3.6 and 3.7 through
  2026-12-31. ⭐ The promotion is therefore **cost-neutral** and **not forced** — it is an upgrade
  taken on merit, which is why it is a small plan and not an incident.
  - verdict: corroborated | checked_at: f6d058b4b | by: review-apparatus/status | rescoped: n/a | evidence: The 3.7 what's-new page applies introductory pricing of 0.75 USD/1M input and 3.75 USD/1M output to BOTH 3.7 Flash and 3.6 Flash through 2026-12-31, and states no deprecation or retirement date for 3.6. The models page still lists 3.6-flash as stable; the shut-down list names only 2.0-flash, 2.0-flash-lite and 3.1-flash-lite-preview. The promotion is therefore elective and cost-neutral, not forced by a retirement.
- OBSERVED: the two Google pages contradict each other on `temperature`. The 3.7 page lists it among
  deprecated parameters to remove; the Gemini 3 developer guide still states "we strongly recommend
  keeping the temperature parameter at its default value of 1.0" and does not mention 3.7 anywhere.
  - verdict: corroborated | checked_at: f6d058b4b | by: review-apparatus/status | rescoped: n/a | evidence: Both pages fetched in this session. ai.google.dev/gemini-api/docs/latest-model (3.7) lists under migration: remove deprecated parameters temperature, top_p, top_k, candidate_count; replace thinking_budget with thinking_level. ai.google.dev/gemini-api/docs/gemini-3 returns NO mention of 3.7 Flash at all (it covers 3.1 Pro, 3 Flash, 3.1 Flash-Lite, 3.1 Flash Image, 3 Pro Image) and still states 'we strongly recommend keeping the temperature parameter at its default value of 1.0'. The older page is not merely silent on 3.7 - it gives the opposite instruction, and nothing on it signals it is superseded.
- OBSERVED: the toml cannot suppress the parameter. `.pr_agent.toml`:83 sets `temperature = 1.0`
  behind a comment block recording a first-party end-to-end verification in the pinned image —
  `pr_reviewer.py:233` passes `config.temperature` into `chat_completion()`, and the litellm handler
  sets `kwargs["temperature"]` for every model NOT in `NO_SUPPORT_TEMPERATURE_MODELS`, a list of
  o1/o3/o4/gpt-5-codex and Claude Opus ids **containing no Gemini entry**.
  - verdict: corroborated | checked_at: f6d058b4b | by: review-apparatus/status | rescoped: n/a | evidence: Read .pr_agent.toml:83 and its comment block first-party at HEAD. CAVEAT ON THE BASIS: the pr_reviewer.py:233 / NO_SUPPORT_TEMPERATURE_MODELS chain is the REPOSITORY'S OWN recorded end-to-end verification against the pinned image, re-read here - it was NOT re-executed against the sha-pinned image in this session, which is not reachable from here. The consequence stands on plain reading either way: pr-agent supplies config.temperature itself, so deleting the key yields pr-agent's 0.2 default rather than parameter absence. Deliverable 3 must confirm against the run log, not against this comment.
- OBSERVED: the fallback ladder makes an optimistic leader safe. The README states the floor of the
  ladder is what served before the ladder existed, "so the worst case is the previous behaviour plus
  a few seconds", and the org workflow's empty-review gate fails loudly only when EVERY model call
  fails. ⭐ **Both risks in this change — no entitlement, and a 400 on a deprecated parameter — fall
  through to 3.6-flash, which serves today.** This is the fact that makes the change small.
  - verdict: corroborated | checked_at: f6d058b4b | by: review-apparatus/status | rescoped: n/a | evidence: Read pr-agent-settings/README.adoc around the ladder section: 'The floor of the ladder is what served before it existed, so the worst case is the previous behaviour plus a few seconds' and 'Before the gate below existed an unavailable model cost one silent, review-less run per pull request - it now fails loudly instead, which is what makes leading with the optimistic choice safe.' Corroborated on the org side by reusable-pr-agent-review.yml:279-290 and :375, whose gate fires only when the runner produced NO review at all. A leader that 404s or 400s therefore costs a wasted rung and falls through to the next entry.
- OBSERVED: `custom_model_max_tokens = 1048576` is REQUIRED, not tuning — `.pr_agent.toml`:65, whose
  comment records that `get_max_tokens()` raises for an id absent from the pinned image's
  `MAX_TOKENS`, and that the table stops at the 3.5 pair.
  - verdict: corroborated | checked_at: f6d058b4b | by: review-apparatus/status | rescoped: n/a | evidence: Read .pr_agent.toml:65 first-party: custom_model_max_tokens = 1048576, under the comment 'REQUIRED by the model above, not optional tuning' recording that gemini-3.6-flash is absent from pr_agent/algo/__init__.py MAX_TOKENS in the pinned image (table stops at the 3.5 pair) and that utils.py get_max_tokens() RAISES unless the value is positive, with the instruction 'Delete this line the day the pinned image registers the model, and not before.' 3.7-flash is 1M context, so the VALUE stays correct; only its stated reason needs the new id.
- OBSERVED: the surface is FOREIGN-ONLY and collides with nothing. `.pr_agent.toml` and `README.adoc`
  in `cuioss/pr-agent-settings` appear in no other staged spec's Expected Surface, and
  `architecture search --content --pattern gemini` over this repository returns 7 matches in 4 files,
  **all incidental test fixtures and one archived report** — no model id is pinned in plan-marshall.
  - verdict: corroborated | checked_at: 77c9dc70a | by: review-apparatus/status | rescoped: n/a | evidence: RE-RUN at the new HEAD after #1336 and #1337 landed mid-session. architecture search --content --pattern gemini: count 7, file_count 4, files_scanned 5283, truncated false - identical to the f6d058b4b run, all hits test fixtures plus one archived doc/plans report, no model id pinned in plan-marshall. No staged spec's Expected Surface names .pr_agent.toml or pr-agent-settings/README.adoc. Inventory caveat: search --content is inventory-scoped, but pr-agent-settings is a SEPARATE repository read directly by path, so the sweep's scope does not bear on it.
- HYPOTHESIS: 3.7-flash is absent from the pinned image's `MAX_TOKENS` table exactly as 3.6 is
  (verify-at-outline). Near-certain — the table stops two generations earlier and the image is
  sha-pinned — but deliverable 4's whole point is that this repository already published one wrong
  registry claim, so it is checked rather than inferred.
- HYPOTHESIS: `thinking_level` (values `low` / `medium` / `high`; `medium` is 3.7's default, and
  `minimal` is rejected on 3.7) has no passthrough in the pinned pr-agent image, making it
  unreachable from this config. If a passthrough exists, whether to set it is a SEPARATE decision and
  must not be absorbed here — record it as a finding, do not scope-creep this plan.
- Verify-first clause: whether this project is entitled to `gemini-3.7-flash` on Vertex AI. Confirmed
  only that the model is GA and present in Model Garden generally — **this project's entitlement is
  not established**, and the repository's own history is that the pro tier was GA and still 404'd
  here. Deliverable 1 settles it before deliverable 2 changes anything.

## Expected Surface

- OBSERVED: `cuioss/pr-agent-settings/.pr_agent.toml`:51-55 — the leader and the fallback ladder
- OBSERVED: `cuioss/pr-agent-settings/.pr_agent.toml`:65 — `custom_model_max_tokens` and its reason
- OBSERVED: `cuioss/pr-agent-settings/.pr_agent.toml`:83 — `temperature` and its comment block
- OBSERVED: `cuioss/pr-agent-settings/README.adoc` — the stale-registry section, the ladder rationale
  and benchmark table, and the Gemini-3 temperature section

⛔ **No plan-marshall file is in scope.** This spec touches one foreign repository and nothing else.

## Dependencies and Sequencing

- Depends on: none.
- ✅ **Collision-free — no staged spec and no live plan claims either file.** Alongside PLAN-PR-039
  this is one of only two specs in the corpus whose whole surface is foreign, which is precisely the
  disjointness property WS-02 and WS-03 rely on.
- ⚠ Adjacent to **PLAN-PR-038**, which publishes generated review packs INTO `cuioss/pr-agent-settings`
  as new artifacts. Different files and a different section of the repository, so not a collision —
  but if PR-038 lands first, re-read the repository layout before editing, and if this lands first,
  PR-038 inherits a changed `[config]` block it does not touch.
- ⚠ **The foreign-repo lane carries two of this epic's own open defects** — PLAN-PR-028 D4 (the
  foreign-PR gate clears on a payload with no `foreign` classification, clears `unpushed`, and passes
  no `--branch`) and PLAN-PR-033 (the foreign gate population and branch-F recovery). A plan-lifecycle
  run of this spec therefore executes through machinery this epic has already recorded as broken.
  ⭐ **This is the argument for handling it ad-hoc rather than through the lifecycle** — see below.
- ⛔ **Deliverable 3 cannot be settled from documentation.** Both Google pages are in scope and they
  disagree; only a real review run distinguishes accepted-and-ignored from HTTP 400. Whatever the
  outcome, it is written down — the answer is the deliverable, not the absence of an error.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-041-the-model-ladder-leads-with-a-superseded-flash.md"
```

## Write-Boundary

The work implementing this spec touches only `cuioss/pr-agent-settings`. It edits NO plan-marshall
source, and NO file under `.plan/local/orchestrator/` other than its own inbox message.
