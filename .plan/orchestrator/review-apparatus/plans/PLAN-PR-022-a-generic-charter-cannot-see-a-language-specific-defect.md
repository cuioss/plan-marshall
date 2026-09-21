# PLAN-PR-022: A generic charter cannot see a language-specific defect

epic: review-apparatus
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-PR-022-a-generic-charter-cannot-see-a-language-specific-defect.md` and is
> queued in the epic `status.json` `plans[]` field. The orchestrator EMITS the command below; it
> never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief,
> so every per-plan carry is authored here and nowhere else.

## Objective

The org's third reviewer (PR-Agent on `vertex_ai/gemini-3.6-flash`, posting as
`cuioss-review-bot[bot]`) reviews every repository against ONE generic security-and-correctness
charter, and it produces materially different results by language: across a 58-PR sweep it
reported findings on 4 of 13 Python/markdown pull requests and on **0 of 19 Java** ones. The
charter's concrete cues — file handles, temp files, subprocesses, `os.open`, `shutil` — are
Python-shaped, and no Java, Maven/Gradle, OCI, GitHub-Actions or Agent-Skills defect vocabulary
reaches the model at all.

This plan makes the reviewer's instructions a FUNCTION OF THE REPOSITORY'S DOMAINS instead of a
single global string, sourcing that vocabulary from the domain knowledge plan-marshall already
owns (`pm-dev-java`, `pm-dev-python`, `pm-dev-oci`, `pm-plugin-development`, `pm-documents`,
`plan-marshall:persona-security-expert`, the `ext-triage-{domain}` and `arch-gate-{lang}` family).
It also enables `/improve` behind a label so the reviewer can post inline suggestions at all, and
records two model-parameter facts that must not be re-derived.

The goal is a SECOND OPINION FROM THE SAME MODEL, better instructed — not model diversity. The
model stays `gemini-3.6-flash`; the operator settled this explicitly.

## Deliverables

Six. This exceeds the ~6-deliverable split guard at its boundary; proceeding unsplit is an
operator decision recorded in the epic decision log (see § Dependencies).

1. **Enable `/improve` behind a label gate.** The reusable workflow's `auto-improve` input
   defaults `false`, so the reviewer has never posted a single inline comment. Add a
   label-gated opt-in (mirroring the existing `skip-bot-review` idiom) so `/improve` runs when a
   PR carries the label, plus the `[pr_code_suggestions]` config block it needs. The default
   stays off — this widens the surface deliberately, not silently.
2. **A per-domain instruction-pack mechanism.** The packs must be SELECTED AND SWAPPED, never
   accumulated (see § Claim Labels — the accumulate form is refuted by the org's own evidence).
   Cover the domains the operator named: Python, Java, Maven, Gradle, Agent Skills, GitHub
   Actions, OCI containers — with the domain set derived from plan-marshall's bundle inventory
   rather than transcribed into a hand-maintained list.
3. **A generator that composes each pack from plan-marshall's existing standards.** The rules
   are already authored and good; this deliverable instruments them, it does not rewrite them.
   Prefer extending the established multi-target export idiom
   (`marketplace/targets/generate.py --target {claude,opencode}`) with a pr-agent target over
   inventing a parallel generator.
4. **Roll the generated packs out to the three swept repositories** — `plan-marshall`,
   `API-Sheriff`, `TokenSheriff` — as repo-local `.pr_agent.toml` files, and close the
   `AGENTS.md` gap (§ Claim Labels) in the two Java repositories.
5. **Record the two model-parameter facts.** `reasoning_effort` is dead config for Gemini and
   must be annotated or removed rather than left looking live; the `agents.md` / `AGENTS.md`
   case hazard must be settled. Both are documentation deliverables in `pr-agent-settings`.
6. **Preserve the high-value targets.** The existing charter's substantiation bar and
   anti-fabrication clause are load-bearing and measured; the per-domain packs must inherit them
   rather than dilute them. Ship a regression guard that fails when a generated pack drops the
   anti-fabrication clause or pushes a pack's category count past the documented ceiling.

## Claim Labels

- OBSERVED: PR-Agent posted ZERO inline comments and ZERO review submissions on all 32 pull
  requests where it participated, across three repositories; 28 of those 32 carried the bare
  "No major issues detected" table — measured via the GitHub REST API over the merged-PR
  population, non-dependabot, on 2026-08-08.
- OBSERVED: PR-Agent reported findings on 0 of 19 Java pull requests (API-Sheriff, TokenSheriff)
  and on 4 of 13 plan-marshall pull requests — same sweep.
- OBSERVED: the zero-finding Java result is NOT diff clipping — API-Sheriff#196's run logged
  `Tokens: 14603, total tokens under limit: 256000, returning full diff`, `PR main language: Java`,
  and the model returned `key_issues_to_review: []` — read in run `31256035545` step log.
- OBSERVED: `auto-improve` defaults to `false` — read at
  `cuioss-organization/.github/workflows/reusable-pr-agent-review.yml` § `workflow_call.inputs`.
- OBSERVED: `reasoning_effort` is never transmitted for Gemini. `litellm_ai_handler.py` adds the
  kwarg only for models in `SUPPORT_REASONING_EFFORT_MODELS`, whose entire contents are
  `o3-mini`, `o3-mini-2025-01-31`, `o3`, `o3-2025-04-16`, `o4-mini`, `o4-mini-2025-04-16` — read
  at `pr-agent-settings/README.adoc` § "Gemini 3 inverts the temperature advice, and
  `reasoning_effort` never reaches it". **It appears in every resolved-config dump anyway**, which
  is exactly how it was misread once already. Setting it to `high` is NOT an available lever.
- OBSERVED: accumulating categories into one growing charter is refuted by the org's own rule —
  "If the category list keeps expanding past roughly ten entries, the answer is a second focused
  pass — not an eleventh bullet" — read at `pr-agent-settings/README.adoc` § "Recall beats
  precision for this reviewer, and that is deliberate". The current charter carries NINE
  categories (read at `.pr_agent.toml` § `[pr_reviewer].extra_instructions`), so one pack of
  appended language bullets would cross that ceiling immediately.
- OBSERVED: a repo-local `.pr_agent.toml` is read and merged above the org file —
  `"use_repo_settings_file": true` in the resolved-config dump, and the run log emits
  `No local .pr_agent.toml found; using existing settings`. This is the swap seam.
- OBSERVED: `repo_context_max_lines` (default 500) is a SHARED budget walked in file order; an
  overflowing file is truncated with a marker and the loop then `break`s, dropping every later
  file with NO marker — read at `pr-agent-settings/README.adoc` § "`repo_context_max_lines` is a
  shared budget that evicts silently". Any design that adds context files must account for this.
- OBSERVED: `AGENTS.md` is configured in `repo_context_files` but is ABSENT from both
  `cuioss/API-Sheriff` and `cuioss/TokenSheriff` (HTTP 404 on the contents API) and PRESENT in
  `cuioss/plan-marshall` (5945 bytes). API-Sheriff's run log emits
  `Repo context file is empty or missing: AGENTS.md`.
- HYPOTHESIS: the absent `AGENTS.md` and the Python-shaped charter are CAUSES of the Java
  zero-finding result, rather than correlates of it. Confirm/refute by running `/review` on a
  closed Java pull request that CodeRabbit found in-charter defects on (API-Sheriff#185 or #154
  are the candidates, 26 and 47 CodeRabbit inline items respectively) with a Java-vocabulary pack
  installed, and comparing against the recorded empty result — confirm/refute at
  `cuioss/API-Sheriff` PR #185 review output (verify-at-outline). **This plan's premise does not
  depend on the causal claim** — the instruction gap is independently worth closing — but the
  deliverable-2 pack CONTENT should not be scoped as if causation were established.
- HYPOTHESIS: `pr_reviewer.inline_code_comments` exists in the pinned image and would let
  `/review` itself post inline comments without enabling `/improve` — confirm/refute at the
  pinned image `pragent/pr-agent@sha256:b253845c…` § `pr_agent/settings/configuration.toml`
  and `pr_agent/tools/pr_reviewer.py` (verify-at-outline). If it exists, it is a cheaper
  deliverable-1 than `/improve` and the plan should prefer it.
- HYPOTHESIS: `/improve` output is unaffected by `restricted_mode = true` — confirm/refute at the
  pinned image § `pr_agent/tools/pr_code_suggestions.py` (verify-at-outline). `restricted_mode`
  is set precisely so the reviewer never needs `contents: write`; a suggestion-posting tool that
  requires it would fail closed and the deliverable would need re-scoping.
- HYPOTHESIS: the existing `tools-sync-agents-file` command writes LOWERCASE `agents.md` while
  `repo_context_files` names uppercase `AGENTS.md`, so a synced file would be invisible to the
  reviewer on a case-sensitive container filesystem — confirm/refute at
  `marketplace/bundles/plan-marshall/commands/tools-sync-agents-file.md` § "Step 5 — Synthesize
  and Write" against `pr_agent/algo/repo_context.py` (verify-at-outline).
- Verify-first clause: deliverable 3 assumes plan-marshall's domain bundles carry standards at a
  granularity that can be DISTILLED into a review charter of roughly charter size. That is an
  inference from the bundle inventory, not a read of the content. Settle it against the actual
  standards documents (`pm-dev-java/skills/java-security/`, `pm-dev-python/skills/python-security/`,
  `pm-dev-oci/skills/oci-security/`, `plan-marshall/skills/persona-security-expert/standards/`)
  before scoping the generator; if the standards are too coarse or too verbose to distil
  mechanically, the generator becomes an authoring aid and deliverable 3 re-scopes accordingly.

## Expected Surface

Three repositories. `pr-agent-settings` and `cuioss-organization` are FOREIGN — see § Dependencies.

- OBSERVED: `cuioss/pr-agent-settings`:`.pr_agent.toml` — `[config]`, `[pr_reviewer]`, and a new
  `[pr_code_suggestions]` block
- OBSERVED: `cuioss/pr-agent-settings`:`README.adoc` — the `reasoning_effort` and per-domain-pack
  sections
- OBSERVED: `cuioss/cuioss-organization`:`.github/workflows/reusable-pr-agent-review.yml` —
  `workflow_call.inputs.auto-improve` and the job `if:` label gate
- HYPOTHESIS: `marketplace/targets/generate.py` and `marketplace/targets/` adapters — the
  pr-agent export target (verify-at-outline; the adapter layout is read from
  `doc/developer/marketplace-build.adoc`, not from the source)
- HYPOTHESIS: `marketplace/bundles/*/skills/*-security/`, `ext-triage-*`, `arch-gate-*` — READ-ONLY
  sources for pack composition; this plan should not modify them (verify-at-outline)
- OBSERVED: `cuioss/API-Sheriff`:`.pr_agent.toml`, `AGENTS.md` — new files
- OBSERVED: `cuioss/TokenSheriff`:`.pr_agent.toml`, `AGENTS.md` — new files
- OBSERVED: `cuioss/plan-marshall`:`.pr_agent.toml` — new file

## Dependencies and Sequencing

- Depends on: none. R = 0 at staging time.
- Overlaps with: **PLAN-PR-004** (`pr-agent-charter-unverified-in-effect`) shares
  `.pr_agent.toml` § `[pr_reviewer]` directly, and **PLAN-PR-011**
  (`review-bots-catch-what-in-house-gates-cannot`) shares the efficacy question. Both MUST be
  sequenced after this plan, and both should be re-read for absorption or retirement once it
  lands — PR-004's subject is a subset of deliverable 6.
- Adjacent to: **PLAN-PR-013** (queue head before this plan) touches
  `automatic-review/review_completeness.py` and the currency test — the CONSUMER of review
  signal, not its production. No file overlap; it stays untouched here.
- **Foreign-repo warning — read before finalize.** Two of the three write targets
  (`pr-agent-settings`, `cuioss-organization`) and two of the three rollout targets
  (`API-Sheriff`, `TokenSheriff`) are OUTSIDE this repository. PLAN-PR-002 is currently parked
  for exactly this reason: source work in a foreign repo is plan work, and finalize will offer to
  MANUFACTURE AND AUTO-MERGE AN EMPTY HOST PR when the real diff lands elsewhere. Scope the host
  PR to the plan-marshall-side generator only, and land each foreign change as its own PR in its
  own repository. `ci.py` accepts `--project-dir` as a top-level router flag (consumed by
  `extract_routing_args` before dispatch, so it does NOT appear in the argparse table) — that is
  the supported way to drive `gh` against a foreign checkout.
- **Split-guard override.** Six deliverables meets the presumptive split threshold. The operator
  chose a single plan over the recommended two-plan split (quick wins first, mechanism second) on
  2026-08-08; rationale recorded in the epic decision log. If execution shows deliverables 2–4
  outgrowing the plan, split at that boundary rather than descoping the regression guard.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-022-a-generic-charter-cannot-see-a-language-specific-defect.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests, plus the
foreign-repository files named in § Expected Surface. It creates and edits NO file under
`.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the orchestrator
owns every other ledger write — and reports its outcome through its PR and its inbox message.
