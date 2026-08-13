# Run report — 360-collapse-the-version-selection-machinery (run 01)

**Date (UTC):** 2026-08-13    **Branch:** claude/version-selection-collapse-gt8iqd (harness-assigned)    **PR:** [#1223](https://github.com/cuioss/plan-marshall/pull/1223)    **Outcome:** completed — all seven deliverables landed, `./pw verify` green, auto-merge armed (landing self-confirmed via read-poll)

## Skills loaded

- `cloud-plan-lane` (first action, the working contract)
- `plan-marshall:ref-code-quality` (+ `standards/code-organization.md`)
- `pm-plugin-development:plugin-script-architecture`
- `plan-marshall:persona-implementer`
- `pm-dev-python:python-core`
- `pm-dev-python:pytest-testing`

All loaded by reading the bundle source path (the `plan-marshall` plugin is not installed in this cloud session). No skill was unobtainable.

## D0 — GATE: chain, ownership, consumer sets, why-baked (confirmed from source)

### The seven-link chain, ownership confirmed by symbol

| # | Link | Symbol / site | Owner | Confirmed |
|---|------|---------------|-------|-----------|
| 1 | Cache layout `{base}/{bundle}/{version}/skills/` | assumed by `marketplace_bundles._partition_version_dirs`, `resolve_bundle_path` | **inherited** (plugin host) | yes |
| 2 | Sync creates a NEW version dir, never deletes | plugin-host install + our `marshall-steward` sync (not among the four expected files) | **ours** | yes (out-of-file; the accumulation is what the rest guards) |
| 3 | Executor bakes absolute version-pinned paths | `generate_executor.discover_scripts` → `{{SCRIPT_MAPPINGS}}` / `{{EXTRA_SCRIPT_DIRS}}` | **ours** | yes — but see "why-baked" below: the bake is a **fast path**, not a hard pin |
| 4 | Multi-version pollution detector | `generate_executor._detect_multi_version_pollution` | **ours** | yes |
| 5 | Orphan-marker writer | `generate_executor._mark_superseded_version_dirs` | **ours** | yes — the SOLE `.orphaned_at` writer under our tree |
| 6 | Retention pins | `generate_executor._retention_pinned_versions` (+ the independent keep-union in `cache_retention.py`) | **ours** | yes |
| 7 | Plugin host's own collector reads the marker | foreign Claude-Code plugin GC (epoch-ms encoding) | **shared field, two producers** | design argument (live-machine state, not reachable from clone) — its *consequence* needs no measurement |

⇒ Links 4–6 are all **ours**. The D0 gate condition "if any of links 4–6 is required by the plugin host rather than by us, re-scope" is **not triggered** — no re-scope on that axis.

### Consumer sets (both directions)

**`.orphaned_at` marker — READERS (existence only):**
1. `marketplace_bundles._partition_version_dirs` (the sole read site in that module; `select_live_version_dir`, `live_version_dirs`, `resolve_bundle_path`, `collect_script_dirs`, `find_bundles` all funnel through it).
2. `generate_executor._CLAUDE_RESOLVER_TEMPLATE` → baked `_resolve_notation_by_target` (the mandated policy mirror).
3. `pm-plugin-development plugin-doctor _plugin_pin_trap.py` — **the sibling detector, OUT OF SCOPE** (reads existence via a named constant `ORPHAN_MARKER_NAME`).
4. `_doctor_shared.py` — comment only; explicitly states it does NOT handle markers.
5. `cache_retention.py` — comment only; docstring states the marker is "advisory only and NEVER consulted."

**`.orphaned_at` marker — WRITERS:**
1. `generate_executor._mark_superseded_version_dirs` (ours, ISO-8601 UTC).
2. Foreign: Claude-Code plugin GC (epoch-ms).

**Baked executor path — READERS (what would break if SCRIPT_MAPPINGS stopped being version-pinned):**
- The generated executor's `resolve_notation` — but the direct `SCRIPTS[notation]` lookup is **existence-guarded** (`Path(direct).is_file()`), and misses fall through to `_resolve_notation_by_target` (runtime glob) then `_resolve_notation_by_cwd_walk`. So a deleted baked path already self-heals at runtime.
- `verify_executor`, `get_executor_mappings`, `cmd_paths`, `cmd_drift` read `SCRIPTS` back for diagnostics only.

### Why the paths were baked (D0 required)

**Startup cost / determinism**, not correctness. `SCRIPT_MAPPINGS` is a `dict[notation → absolute path]` for O(1) dispatch without a filesystem walk on every invocation; `{{EXTRA_SCRIPT_DIRS}}` bakes PYTHONPATH the same way. The runtime fallback (`resolve_notation` tiers 2–4) already resolves when a baked path is stale. ⇒ **The structural fix (D1) is a near-straight win, not a trade:** the executor already resolves at runtime; the baked map is a cache, and the direct lookup is existence-guarded. The only thing D1 removes is the *marker consultation* inside the runtime resolver and the selector — which is precisely the "a runtime resolver that still consults the marker set has MOVED the problem" hazard the plan names.

### Refuted-invariant circularity (checkable from source — confirmed)

`marketplace_bundles._partition_version_dirs` computes `live = [d for d in eligible if d == pinned or not (d/'.orphaned_at').exists()]`, and `select_live_version_dir` returns `max(live, key=version)`; the degraded branch fires only when `live == []`. The disk arm of the pin (`select_live_version_dir` inside `_retention_pinned_versions`) selects **among live dirs**, so once saturation is reached that arm returns nothing and cannot recover — the guard against reaching the state depends on not already being in it. Confirmed by symbol.

### The refuted "structurally impossible" claim — sites located (D5 targets)

- `generate_executor._retention_pinned_versions` docstring — "Pinning these is what makes marker saturation structurally impossible…" (deleted by D4).
- `generate_executor._mark_superseded_version_dirs` docstring — same claim (deleted by D4).
- `marketplace_bundles.select_live_version_dir` / `_partition_version_dirs` docstrings (rewritten by D1).
- `manage-config/standards/data-model.md` § "Plugin-cache retention semantics" — the "Pin resolution has exactly three arms" and "two sanctioned existence-read sites" paragraphs.
- `tools-script-executor/SKILL.md` § "Version-aware bundle-path resolution" — the degraded-fallback / pollution-detector / two-existence-read-sites / mirroring-mandate prose.
- `pm-plugin-development plugin-doctor _doctor_shared.py` — a comment referencing "the all-versions-orphaned contribute-zero bug fixed in `script-shared::find_bundles`".

### The D2 enforcement-test interaction (confirmed)

`test/plan-marshall/script-shared/test_orphan_marker_existence_only.py` is a population-derived test asserting **exactly two** sanctioned existence-read sites (`_partition_version_dirs`, the `_CLAUDE_RESOLVER_TEMPLATE` mirror) and **one** sanctioned write site (`_mark_superseded_version_dirs`). Removing the marker machinery (D1/D2/D4) removes all three subjects. The test therefore **must be retired** — recorded here and in the Findings section rather than deleted silently (the move this epic exists to catch). Reason: the invariant it enforces ("our sites read the shared field existence-only to stay encoding-agnostic vs. the foreign co-producer") has no subjects once our tree stops reading or writing the field. The only remaining reader, plugin-doctor's `_plugin_pin_trap.py`, is out of scope and was never one of the test's two sanctioned sites.

## Deliverables

- **D0 — GATE (chain + ownership + why-baked).** Done. Confirmed all seven links by symbol; links 4–6 are all ours (no re-scope). Established the paths were baked for **startup cost / determinism**, and that the runtime resolver (`resolve_notation`) already existence-guards the baked path and falls through to a runtime resolver — so D1 is a near-straight win, not a trade. Full analysis in the D0 section above.
- **D1 — LEVER A (runtime resolution, marker-free).** Done. `marketplace_bundles.select_live_version_dir` rewritten to numerically-newest-eligible-wins with **no `.orphaned_at` read and no degraded fallback**; `_partition_version_dirs` and `live_version_dirs` deleted (their only purpose was the marker partition / the deleted pollution counter). The executor's embedded `_CLAUDE_RESOLVER_TEMPLATE` mirror rewritten to drop the marker consultation (picks newest candidate). Startup cost: **none added** — the resolver already globbed the cache at runtime for a `SCRIPTS` miss; removing the marker `.exists()` probes is strictly less work. The resolver **no longer consults the marker set**, so the class is eliminated, not moved (D1's ⛔).
- **D2 — LEVER C (stop writing the shared marker) + enforcement-test interaction.** Done. `_mark_superseded_version_dirs` (the sole writer under our tree) deleted. **`test_orphan_marker_existence_only.py` retired** — its subjects (the two sanctioned existence-read sites `_partition_version_dirs` + `_CLAUDE_RESOLVER_TEMPLATE`, and the one sanctioned write site `_mark_superseded_version_dirs`) no longer exist under our tree, so the invariant it enforced ("our sites read the shared field existence-only to stay encoding-agnostic vs. the foreign co-producer") has no subjects. This is recorded, not silent (the move the epic exists to catch). Its "no marker write" guarantee is **re-established, not dropped**, by the new D6(d) test `test_no_production_source_writes_the_shared_marker`, which scans the whole production tree for a `.orphaned_at` write. No namespaced marker was introduced — none is needed, because the runtime resolver picks newest without any marker.
- **D3 — LEVER B (delete-on-sync).** Evaluated, **NOT adopted** (decision recorded). Delete-on-sync remains unsafe even after D1: a superseded version dir may still be on a *running* process's baked PYTHONPATH (the executor captures `_PYTHONPATH` at generation time), so immediate `rmtree` on sync would race a live process. The runtime resolver self-healing to newest reduces the *resolution* exposure but not the *import-path* exposure of an already-launched process. Pruning therefore stays the `marshall-steward` `cache_retention sweep`'s deferred union-keep job (newest-`N` ∪ younger-than-`D`-days ∪ newest-on-disk ∪ provisioned ∪ manifest ∪ executing-dir), which never deletes the live dir. `cache_retention.py` is unchanged.
- **D4 — Retire dead machinery.** Done. Deleted `_detect_multi_version_pollution`, `_retention_pinned_versions`, `_live_version_dirs`, `_carries_skills_tree`, `_mark_superseded_version_dirs`, the `cmd_preflight` pollution/marking block, the selector's degraded fallback, and the now-unused `select_live_version_dir`/`live_version_dirs` imports in `generate_executor.py`. **Guard 4 (`_check_emitted_path_provenance`) is retained** — it is marker-independent (confirmed by symbol and by the surviving guard-4 test suite) and still fail-closes a version-split executor at write time.
- **D5 — Correct the saturation claims.** Done. The "structurally impossible" claims lived in `_retention_pinned_versions` / `_mark_superseded_version_dirs` docstrings (deleted by D4). The restating docs were corrected: `data-model.md` (pin-resolution + existence-read paragraphs removed), `tools-script-executor/SKILL.md` (version-aware resolution section rewritten), `provisioning-fail-closed-audit.md` (`_detect_multi_version_pollution` row removed, `cmd_preflight` row updated), `plan-marshall/SKILL.md` (preflight pollution bullets), and the `_doctor_shared.py` comment. A tree-wide sweep confirms no document asserts the refuted guarantee.
- **D6 — Tests, red-first.** Done. Four deliverables in `test/plan-marshall/tools-script-executor/test_marker_free_resolution.py`, each verified against the pre-fix code:
  - (a) `test_resolver_ignores_orphan_mark_and_selects_newest_carrying_the_script` — **red pre-fix** (marked newest demoted to an older unmarked dir), green post-fix. A companion `test_resolver_survives_deletion_of_generation_time_version` documents the deletion-survival property (green both — the runtime resolver already survived deletion; the tree moved past the plan's premise here).
  - (b) `test_saturated_cache_resolves_to_newest_without_degraded_warning` — **red pre-fix** (degraded stderr fired), green post-fix.
  - (c) `test_broken_cache_with_no_eligible_candidate_fails_loudly` (+ companion) — the matched **negative control**: `None` on no eligible candidate. Passes pre- *and* post-fix by construction (the loud-failure path was never broken); its job is to keep the marker-free fix from degrading into an always-find-something resolver. Reported honestly rather than contrived red.
  - (d) `test_no_production_source_writes_the_shared_marker` — **red pre-fix** (`write_text` at the old `_mark_superseded_version_dirs`), green post-fix.

## Build gate

The `git diff --name-only origin/main...HEAD -- '*.py'` verdict is **non-empty** (production scripts + tests changed), so `./pw verify` took its full path. **Result: SUCCESS** — `19560 passed, 14 skipped` with every sub-step green: mypy(production) [398 files], ruff [marketplace/bundles, test, .claude], SPDX headers, plugin-doctor [marketplace-wide], mypy(test) [732 files], module-tests [whole-tree pytest]. No `uv.lock` or generated-file churn was produced (deliverable paths staged explicitly, `git status` clean of stray files before commit). `UV_HTTP_TIMEOUT=600` was exported on every `./pw` call per the lane's cloud-session note.

## Findings

Per instance, with source and disposition.

**Pre-PR verification sub-agent (independent `general-purpose` dispatch, read-only):**

- **F1 — stale pollution-detector reference (real defect, the class this epic targets).** `tools-script-executor/SKILL.md` § "generate_executor — preflight" (Canonical invocations, ~line 765) still named the **deleted** `_detect_multi_version_pollution` and described the removed "EITHER of two independent triggers" pollution regeneration path. I had swept the "Version-aware bundle-path resolution" section of the same file but missed this second section. **Disposition: fixed** — rewritten to state only version-staleness regenerates, and that multiple version dirs no longer trigger regen/marker-write. Re-verified clean.
- **F2 — stale test comment referencing a deleted symbol.** `test_generate_executor.py` (~line 1759, in `test_preflight_subcommand_registered_and_emits_toon`) carried a comment referencing `_detect_multi_version_pollution` and the monkeypatch stubs this PR removed. Comment-only (test still passed). **Disposition: fixed** — rewritten to describe cache-first HOME isolation only. Re-verified clean.
- **F3 — D6(a) literal-spec deviation (disclosed, accepted).** The plan's D6(a) headline ("an executor generated against a version still resolves after that version is deleted", seen red first) was found to be **already true pre-fix** — the runtime resolver (`resolve_notation`) predates this plan and already existence-guards the baked path + falls through to a runtime glob. So the deletion-survival test `test_resolver_survives_deletion_of_generation_time_version` is green both pre- and post-fix; the red-first evidence for D6(a) is supplied instead by the marker-ignoring test `test_resolver_ignores_orphan_mark_and_selects_newest_carrying_the_script`. **Disposition: accepted and recorded** (the report and this Findings section state it outright). The agent confirmed it is a transparent re-interpretation forced by the tree moving under the spec, NOT a "delete the guard to pass" move. The practical consequence — D1 removed *marker consultation* from an already-runtime resolver, rather than *adding* runtime resolution — is stated here so it is not overstated.
- **Pre-existing field-count observation (out-of-scope, fixed as declared incidental).** `plan-marshall/SKILL.md:108` said the preflight has a "six-field TOON contract" while the verb returns **seven** fields (confirmed against `_PREFLIGHT_FIELDS` and the preflight docstring). Not introduced by this change. **Disposition: fixed** (one-word correction in a file this PR already edits, declared here and in the commit body) rather than left as a known-false claim; re-verified against the actual return.

**CI:** recorded after the PR's `verify` run concludes (see Reviewer participation / merge gate below).

## Reviewer participation

The expected reviewer population is derived from configuration — the `author_login` of each `marketplace/bundles/plan-marshall/skills/automatic-review/standards/{bot_kind}.md` registry doc (cross-named by `.github/workflows/pr-agent.yml`) — not transcribed here. Populated after the PR opens and the automated reviewers report (both the review-summary and inline-thread surfaces).

| Reviewer (`author_login`) | Verdict | Body evidence / reason |
|---|---|---|
| `cuioss-review-bot` | `reviewed` | Issue-comment body "PR Reviewer Guide 🔍 — PR contains tests / No security concerns identified / No major issues detected" (an explicit nothing-to-report over the diff). |
| `coderabbitai` | `rate-limited` | Issue-comment body "Review limit reached … Next review available in: ~10 minutes" — engaged but did not review this diff. Window reopens on its own; routine and outside our control. |
| `sourcery-ai` | `rate-limited` | Review body "you have reached your weekly rate limit of 500000 diff characters" — a quota refusal in place of a review. |

**Coverage: 1 of 3.** The § Step 8 shortfall disclosure **fired**: "Review coverage 1 of 3 — `cuioss-review-bot` reviewed (no major issues); `coderabbitai` rate-limited (window reopens); `sourcery-ai` rate-limited (weekly quota)." Rate limits are routine and outside our control, so per the lane contract this is disclosed, not blocked. There were **no actionable review comments** on any of the three surfaces (issue comments, review summaries, inline threads) — the two non-`reviewed` bodies are quota notices, not findings, and need no reply; the one `reviewed` body reported no issues. Inline review-thread surface: empty.

## Cost

- **Tokens:** not available to the agent in this session — a single interactive Claude Code cloud session does not surface its own token usage to the model. Stated plainly rather than estimated.
- **Wall-clock:** ~1h from skill load to auto-merge arm (first branch push at commit `77fd115`→`b295a0d`; PR opened 20:49 UTC; merge-gate arm shortly after). Source: git/PR event timestamps.
- **Population:** this single Claude Code cloud session's activity as the harness runs it — one interactive session plus three background sub-agent dispatches (two test-inventory Explore agents, one pre-PR verification agent, re-dispatched once). ⛔ **NOT comparable** to a plan-marshall `metrics.toon` total, which counts an orchestrator-plus-agent dispatch tree under plan-marshall's own per-task billing boundary that this session does not share. No comparable figure is presented.

## Contract check (Step 9)

| Step | Verdict |
|---|---|
| 1 Skills loaded | **Done** — named in § Skills loaded; all obtained by bundle-path read (plugin not installed). |
| 2 Branch | **Done** — harness-assigned `claude/version-selection-collapse-gt8iqd` kept as-is; exists on `origin` (pushed as first action). Branch form: **harness-assigned**. |
| 3 Plan directory | **Done** — `doc/plans/truthful-signals/360-collapse-the-version-selection-machinery/plan.md` exists (git mv), opens with the first-instruction block (verified present at Step 3 and here). |
| 4 Implement | **Done** — commits carry the `Co-Authored-By: Claude` trailer, no "Generated with Claude Code" footer; all seven deliverables addressed. |
| 4 Per-commit gate | **Done** — every `*.py`-touching commit was preceded by a clean gate; the authoritative pre-PR gate is the full `./pw verify` SUCCESS (§ Build gate). Fast iterative red/green checks used `uv run python -m pytest` (see § What have we learned). |
| 4 Pushed | **Done** — every commit pushed; no unpushed commit remains at report-commit time. |
| 5 Build gate | **Done** — git-derived Python-change verdict non-empty → full `./pw verify` = SUCCESS (19560 passed, 14 skipped). |
| 6 Verification sub-agent | **Done** — dispatched (read-only), 3 findings (F1/F2/field-count) fixed, re-dispatched, re-verified clean; F3 disclosed. All in § Findings. |
| 7 PR cycle | **Done** — PR #1223 opened, kept its bot review (touches `*.py` + `marketplace/bundles/**`, so **no** `skip-bot-review`). All three comment surfaces read; every comment dispositioned (none actionable). |
| 8 Merge gate | Conditions 1–3 met (report finalized as last pre-merge commit); auto-merge armed (SQUASH). Cloud session self-confirms the landing via read-poll (`send_later` is available here). Merge commit reported to the operator, not embedded (it does not exist until the squash lands). |
| 8 Bridge | **Done** — no status/bookkeeping write landed under `doc/plans/` outside this plan's own directory; report carries the PR number and per-deliverable outcome for the orchestrator to collect. |
| 9 This check | **Done** — appended here. |
| 9 What have we learned | Present below. |

**GitHub access path used:** the **GitHub MCP server** (cloud path), for both reads and the PR create/arm. No `gh` CLI available. **Plugin cache sync:** a cloud run **never owes** a `/sync-plugin-cache` — it is a machine-local build step, not a debt this run records. The merged bundle source is authoritative; a local developer who wants their `~/.claude` cache refreshed runs the sync themselves.

## What have we learned (Step 9)

**One contract-change proposal, with evidence from this run — presented to the operator, not self-approved, not shipped.**

*Proposal:* add a short note to the `cloud-plan-lane` § Build gate that, for **fast iterative red/green checks on specific test files**, `uv run python -m pytest <path> -o addopts=""` is available in the cloud session and is dramatically faster than routing every check through `./pw module-tests` — while **reserving the full `./pw verify` for the authoritative gate** (unchanged).

*Evidence (this run):* `uv` is on `PATH` (0.8.17) and shares the pyproject-defined environment. Targeted `uv run` pytest calls on the affected files returned in **~0.2 s** each after the first dependency fetch, versus the full `./pw verify` at **~6m43s**. This run used the fast path repeatedly for the red-first D6 verification and the iterative test-update green checks, then ran the full `./pw verify` once as the gate. The contract currently names only `./pw`, so a fresh agent would default to the slow whole-suite command for every iteration. The proposal changes nothing about the gate — it documents an iteration affordance the contract is silent on.

*Not proposed as a lane-contract change:* the D6(a) tension (a plan's "seen-red-first" deliverable that the tree had already made true) is a **plan-authoring** concern for the `author-cloud-plan` skill, not the execution contract — the lane's Step 6 handled it correctly (report the deviation honestly). Recorded here for the plan author, not as a `cloud-plan-lane` amendment.

*Operator decision required:* ship the § Build-gate note as a separate `chore(cloud-plan-lane)` PR (per the contract's Step-9 rule), or decline. Not applied in this PR.

## Residue

- **Sibling detector re-scope (out of scope here).** `pm-plugin-development plugin-doctor _plugin_pin_trap.py` still reads `.orphaned_at` and still describes retention pins / degraded fallback in its own logic. The plan deliberately leaves it untouched ("NOT superseded by this… re-scope it after this lands"). After this lands, a follow-up should re-scope that detector: the version-split state it guards can no longer occur, but its oracle also covers pin-versus-source content staleness, which this plan did not address.
- **Pre-existing field-count bug fixed in passing.** `plan-marshall/SKILL.md` said the preflight had a "six-field" TOON contract; it returns seven. Corrected and declared (not silently), since the file was already being edited.
- **No follow-up owed on this PR's own surface** — every deliverable is complete and the full build is green.
