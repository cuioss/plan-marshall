# Gaps — 302-the-terminal-report-is-a-machine-readable-emission-the-inbox-drains

**Source:** verification.md (same directory)   **Open items:** 8

## G1 — Stop counting `n/a` as a present fact in the landing completeness check

- **Kind:** bug
- **Severity:** high
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py:887` — `check_landing_completeness` (`missing = [key for key in LANDING_REQUIRED_KEYS if not facts.get(key)]`)
- **What is wrong:** The producer explicitly sanctions writing `n/a` for any field it could not read (`phase-6-finalize/standards/emit-landing.md:176` and its Error Handling table row 1), and the validator only rejects empty values. Executed against a landing whose eight required values are all `n/a`, `check_landing_completeness` returned `(True, [])`.
- **Why it matters:** `plan-orchestrator/workflow/analyze.md:105` turns `complete: true` into "the landing transmitted its whole mechanisable delta … a subsequent operator paste yields nothing new from that plan". A run whose fact reads all failed therefore reports *nothing material outstanding* while having drained nothing — the exact false signal the plan exists to stop shipping, arriving through the one degraded path the producer documents.
- **Fix:** Add a sentinel set (`{'n/a'}`, case-insensitive, after strip) to `_orchestrator_inbox.py` and treat a required key whose value is a sentinel as MISSING for every key that can never legitimately be unknown — `schema`, `plan_id`, `deliverables_total`, `deliverables_done`, `total_tokens`, `steps`. Keep `pr` and `merge_state` allowed to be `n/a`, since "no PR exists" is a real state the payload spec already names (`landing-payload-spec.md:83-84`); state that asymmetry in the docstring. Extend `test_landing_completeness.py::TestSeenToFailOnPreFixLanding` with an all-`n/a` case asserting `complete is False`, and a `pr=n/a` case asserting it still passes.
- **Done when:** `check_landing_completeness` on a landing whose `total_tokens`/`steps`/`deliverables_*` are `n/a` returns `complete: False` naming those keys, while a landing with `pr=n/a`/`merge_state=n/a` and every other key real still returns `complete: True`, both pinned by tests.
- **Module/topic:** `plan-marshall:plan-orchestrator` — landing drain-completeness

## G2 — Make the required-key set cover the MECHANISABLE delta the spec itself derives

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md:43,45,88,90-91` — the delta table vs the required-key table
- **What is wrong:** One document says two different things. The delta table routes "Per-step outcome + `display_detail` for every finalize step, in composed order" as "`steps` (per-step `{step,outcome}` + typed `facts`)" (line 43) and "Repository end-state" as "folds into `steps` (`branch-cleanup` facts)" (line 45). The required-key table then defines `steps` as "Comma-joined `{step}:{outcome}` for every finalize step in composed order" (line 88) — no `display_detail`, no facts — and puts per-step typed facts and `total_wall_seconds` in the OPTIONAL list, stating "their absence is not incompleteness" (line 90). Three rows the document classifies MECHANISABLE are therefore guaranteed by no required key.
- **Why it matters:** `complete: true` is the signal `analyze.md` converts into "nothing material is outstanding", and it can be true of a landing carrying zero per-step typed facts, no wall-clock, and no repository end-state — all of which the same document says the inbox was missing. The delta the plan derived is not the delta the check enforces.
- **Fix:** Pick one and make the document say it. Either (a) promote the three rows to required — add `total_wall_seconds` to `LANDING_REQUIRED_KEYS` and require at least the `branch-cleanup` per-step facts as `step.branch-cleanup.{key}=` entries, extending `check_landing_completeness` to check for the `step.` prefix family; or (b) keep them optional and rewrite the delta table's "Routed as" cells for lines 43 and 45 to say `steps` carries outcomes only and the typed facts ride optional keys, then amend `analyze.md:105` so `complete: true` claims only what the required set actually covers.
- **Done when:** every row the delta table classifies MECHANISABLE is either named in `LANDING_REQUIRED_KEYS` or explicitly recorded in the delta table as optional, and no sentence in `landing-payload-spec.md` or `analyze.md` claims `complete: true` means the whole mechanisable delta drained unless it does.
- **Module/topic:** `plan-marshall:plan-orchestrator` — landing payload spec

## G3 — Give `pr` and `merge_state` a typed producer, or stop calling them facts

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/landing-payload-spec.md:83-84` — the Source column; `phase-6-finalize/standards/emit-landing.md:158-162` — Step 1 item 4
- **What is wrong:** The spec's Source column says `pr` comes from "`create-pr` / CI" and `merge_state` from "`branch-cleanup` facts". Neither fact exists: `phase-6-finalize/workflow/create-pr.md` frontmatter declares no `records_facts` at all, and `phase-6-finalize/standards/branch-cleanup.md:11-15` declares `action`, `upstream_commit_count`, `merge_mechanism`, `work_performed` — no `merge_state`. `emit-landing.md:160-162` accordingly instructs deriving both from the step records' "`facts` / `outcome` / `display_detail`", i.e. by parsing prose.
- **Why it matters:** Two of the eight required keys — including the one the plan's own control finding #4 is about — are re-derived from free-text `display_detail`, which is exactly the substrate D4 was supposed to stop depending on. A reader of the spec believes those two keys are typed and will not notice when a `display_detail` reword silently changes them.
- **Fix:** Either wire the producers — add `records_facts: [pr_number]` to `create-pr.md` with a `--fact pr_number=` at its terminal call site, and add `merge_state` to `branch-cleanup.md`'s `records_facts` union recorded at each `--outcome done` branch — or correct the spec: change the Source cells to name `display_detail` explicitly and add a sentence saying these two keys are the documented exception to the typed-facts routing, with the reason. Prefer wiring the producers; the `records_facts` both-direction conformance test will then hold them.
- **Done when:** either `create-pr` and `branch-cleanup` declare and wire facts that supply `pr` and `merge_state`, or `landing-payload-spec.md`'s Source column names `display_detail` for both and says why they are exempt.
- **Module/topic:** `plan-marshall:phase-6-finalize` / `plan-orchestrator` — records_facts wiring

## G4 — `emit-landing` must declare `work_performed`

- **Kind:** omission
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/emit-landing.md:1-16` (frontmatter, no `records_facts`) against its Error Handling table at line 236
- **What is wrong:** `extension-api/standards/ext-point-finalize-step.md` § "`work_performed`" states: *"A step MUST declare `work_performed` when at least one of its `--outcome done` branches is reachable without the step having performed its characteristic work."* `emit-landing.md:236` has exactly such a branch — *"`orchestrator inbox write` returns an error → Non-fatal: log the failure and mark `done` with the failure noted in `display_detail`"*. The step declares no `records_facts`. The conformance suite (`test_step_records_facts_contract.py`) only enforces the converse direction — every step *declaring* `work_performed` carries it on every `done` call site — so nothing catches a step that should declare it and does not.
- **Why it matters:** A run whose landing write failed records `emit-landing:done`, and that string is what the landing's own `steps` key and the operator report both carry. "Emitted the landing" and "failed to emit and gave up" become the same record — the ambiguity `work_performed` exists to remove, in the one step whose whole job is making the run's outcome drainable.
- **Fix:** Add `records_facts: [work_performed]` to `emit-landing.md`'s frontmatter, and add `--fact work_performed=true` to the Step 4 `mark-step-done` call and `--fact work_performed=false` to the Error Handling row's `done` call (spell that call out rather than leaving it prose). Add a row for `default:emit-landing` to the Declared-obligations table in `ext-point-finalize-step.md` with its consumer question ("did this run actually emit a landing?").
- **Done when:** `emit-landing.md` declares `work_performed`, every `--outcome done` call site in its body records it, and `test_step_records_facts_contract.py` passes with the step in its derived population.
- **Module/topic:** `plan-marshall:phase-6-finalize` — records_facts contract

## G5 — Classify `default:emit-landing` in the dispatched/inline roster

- **Kind:** omission
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md` — `## Inline steps` roster (lines 40-53)
- **What is wrong:** That document declares itself "the single source of truth for which of the default + project finalize steps **dispatch** … and which run **inline**" and carries a Closure invariant — "Every step in the authoritative registry carries **exactly one** classification: it appears in either the dispatched roster or the inline roster, never both and never neither." `default:emit-landing` appears in neither roster. `phase-6-finalize/SKILL.md:178` calls it inline in a parenthetical, and `emit-landing.md` is modelled on the inline `finalize-step-preference-emitter`, but the declared authority is silent.
- **Why it matters:** The Execute Step Pipeline's dispatch branch consumes this roster to decide whether a step runs inline or spawns an envelope. `emit-landing.md` states that when it runs it must consume the dispatcher's already-resolved `orchestrated`/`epic` values and "MUST NOT re-issue either resolution call" — a contract only an inline step can satisfy. An unclassified step leaves that to inference. The omission also becomes a hard closure-invariant violation the moment G7 is fixed.
- **Fix:** Add one row under `## Inline steps` in `dispatch-inline-split.md`: `` - `default:emit-landing` — terminal machine-readable emission; reads facts already on disk and writes one inbox message, so it earns no envelope; consumes the dispatcher's resolved `orchestrated`/`epic` verdict directly ``. Keep the roster count-free, as the document requires.
- **Done when:** `default:emit-landing` appears in exactly one roster in `dispatch-inline-split.md`, and `test_dispatch_roster_closure.py` passes with the step present in its population (see G7).
- **Module/topic:** `plan-marshall:phase-6-finalize` — dispatch/inline roster

## G6 — Document `terminal_emission_dropped` in the compose output contract

- **Kind:** doc-drift
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/SKILL.md:130-165` (compose-result TOON example and the field-shape paragraph) and `standards/decision-rules.md:71-82` (§ Outputs bullet list)
- **What is wrong:** `cmd_compose` returns a new `terminal_emission_dropped` field (`manage-execution-manifest.py:2551`), and D2's observability claim rests on it. Neither the SKILL.md example TOON — which lists `commit_push_dropped`, `scope_gated_finalize_dropped`, `unresolved_ask_provider_dropped`, `lane_dropped` and the rest — nor the decision-rules § Outputs bullet list, which enumerates every other narrowing site's field, mentions it. `test_subtraction_visibility_population.py` derives its population from the code and asserts nothing about these documents.
- **Why it matters:** A caller reading either document to learn what a compose result can report concludes the enumeration is complete and never surfaces the terminal-emission drop, making an "observable compose-time decision" invisible to every consumer that reads the contract rather than the source.
- **Fix:** Add `terminal_emission_dropped[0]:` to the SKILL.md example TOON next to `unresolved_ask_provider_dropped`, and a bullet to `decision-rules.md` § Outputs: `terminal_emission_dropped` — the terminal-emission step dropped for a non-orchestrated plan (bare step-id list; the reason rides the paired `[STATUS]` line). Add it to the SKILL.md paragraph's list of fields "still emitted as bare step-id lists".
- **Done when:** both documents name `terminal_emission_dropped` and state its shape.
- **Module/topic:** `plan-marshall:manage-execution-manifest` — compose output contract

## G7 — Register `default:emit-landing` in the tracked `.plan/marshal.json` registry

- **Kind:** omission
- **Severity:** medium
- **Where:** `.plan/marshal.json` → `plan.phase-6-finalize.steps` (25 keys; `default:emit-landing` absent, while `manage-config list-finalize-steps` discovers 26)
- **What is wrong:** The run's Residue calls this "a local-developer re-seed concern … not a code debt" on the basis that `.plan/` is untouchable. `.plan/marshal.json` is git-tracked: `.gitignore:45-46` ignores `.plan/*` then negates `!.plan/marshal.json`, `git ls-files .plan/` lists it, and five prior `chore(steward)` commits have landed it. It is present in a fresh clone and in CI.
- **Why it matters:** Two consequences. (1) This repository's own orchestrated plans do not compose `emit-landing`, so the deliverable is inert here — the epic inbox still receives no landing from a plan-marshall run. (2) `test_dispatch_roster_closure.py::_registered_steps` (line 213-217) reads exactly this file as its population, so the closure invariant cannot see `emit-landing` — which is why G5 passed CI green.
- **Fix:** Run `/marshall-steward` (or the equivalent registry reconcile) to add `default:emit-landing` at order 1000 to `plan.phase-6-finalize.steps`, and commit the regenerated `.plan/marshal.json` and `.plan/execute-script.py`. Land it together with G5's roster row so the closure test is green in the same change.
- **Done when:** `.plan/marshal.json`'s `plan.phase-6-finalize.steps` carries 26 keys including `default:emit-landing`, and `test_dispatch_roster_closure.py` passes.
- **Module/topic:** meta-project registry — `.plan/marshal.json`

## G8 — Cover `emit-landing`'s runtime path with one end-to-end test

- **Kind:** missing-test
- **Severity:** low
- **Where:** `test/plan-marshall/phase-6-finalize/**` — no test executes the step's body; coverage is `test_finalize_orchestration_routing.py` (dispatch-table set equality, ascending order, no collision) plus `test_terminal_emission_gate.py` (compose only)
- **What is wrong:** The run declared this as residue and it is still open. Nothing exercises the sequence "orchestrated plan composed → step present at order 1000 → facts read → payload assembled → `inbox write --kind landing` → `landing-check` reports complete". Every assertion about the emission today is structural or documentary.
- **Why it matters:** The producer (`emit-landing.md`), the contract (`landing-payload-spec.md`), and the validator (`check_landing_completeness`) are three hand-maintained sites the plan itself says "share one spec". Nothing holds them together, so a change to the required-key set in one can pass CI while the other two disagree.
- **Fix:** Add a test that builds a `phase_steps["6-finalize"]` fixture with real `facts` sub-dicts (including `record-metrics`'s `total_tokens`), renders the fenced block exactly as `emit-landing.md` Step 2 specifies, writes it through `orchestrator inbox write --kind landing`, and asserts `orchestrator inbox landing-check` reports `complete: true`. Add the negative half: drop one required key from the rendered block and assert it is named in `missing_keys`. Derive the key list from `LANDING_REQUIRED_KEYS` rather than restating it, so the test fails when the producer doc and the constant drift apart.
- **Done when:** a test in `test/plan-marshall/phase-6-finalize/` or `test/plan-marshall/plan-orchestrator/` drives a spec-shaped payload end to end through `inbox write` + `landing-check` in both the complete and the missing-key direction, with the key population read from the module constant.
- **Module/topic:** `plan-marshall:phase-6-finalize` / `plan-orchestrator` — landing emission tests
