# Settled narrative — code-intelligence-substrate

Relocated from `epic.md` on 2026-08-22 during the landed-corpus ingest. **Nothing here was deleted
and nothing was rewritten** — every block below is the verbatim text that stood in `epic.md`, moved
so the live ledger carries only live state. `epic.md` keeps a pointer at each origin resolving here.

⛔ **This file is a record, not a brief.** It is not read to decide anything. It exists so that a
claim retired here can be shown to have been retired rather than lost, and so a reader who wants to
know *why* a decision was closed can find the reasoning that closed it.

Read `epic.md` § START HERE for live state.

---

## Why this relocation happened now

The 2026-08 cloud wave executed 36 staged specs and every one of them landed. The narrative those
36 plans generated — a per-plan annotated queue table, a full-queue reconciliation, and two
sections of defects and watches written against a queue of 49 rows — describes a state that no
longer exists. The queue is now 62 rows, 49 of them shipped. Carrying that narrative forward in the
live ledger would make the live ledger mostly history.

---


## Relocated: the stale-inline anchor tail

Residue of the 2026-07-04-era anchor, kept inside a closed HTML comment in `epic.md`'s
START-HERE section and named there as residue rather than claimed removed. It is moved here
intact. **No reader should consult it** — it is superseded in every particular by the
landing records under `landings/`.

<!-- STALE-INLINE-REMOVED-TAIL-2 *** ⭐⭐⭐ THE COMPOSITION CLAIM IS NO LONGER SECOND-HAND - STOP LABELLING IT SO. Recomputed first-party from an operator-supplied metrics.md for plan-45-demo-client-doc-consolidation, A PLAN NEITHER EPIC RAN: cache_read 73.15pct / cache_creation 25.69pct / output 1.13pct / input 0.03pct, against truthful-signals' n=47 76.1/22.8/1.1. ⭐ My recomputed billing total matched that file's own published per-phase sum TO ONE TOKEN (66,212,048 vs 66,212,049), which verifies THE FORMULA, not just the shares. ⇒ '~99pct of billing weight is context, not generation' is CONFIRMED. ⚠ Scope precisely: this corroborates the COMPOSITION - the per-phase RANKING stays retired for the three recorded reasons. ⛔ And the same file REFUTES the exploration-share claim at the low end: measured 85.4 / 74.8 / 57.2 / 80.4 / 73.1 per phase, so '76-85pct in EVERY phase from 2-refine on' is FALSE at 4-plan. Folded into CIS-036. *** ⛔ THE REPORT CARRIES FIGURES THE STORE DOES NOT - work/metrics.toon IS the machine authority (plus per-phase metrics-dispatch-boundaries-*.toon and an accumulator) and persists billing_weighted_total, dispatch_boundary_total, the four-field counts and the byte categories, SO THE COMPOSITION RECOMPUTE IS SCRIPT-DERIVABLE. BUT: (1) the aggregate Total AND its (n=5/6) population qualifier are RENDER-TIME ONLY - no aggregate in the TOON header, so the headline figure and its population exist ONLY IN PROSE and a script must re-derive both, possibly picking a different population than the renderer did; (2) inline_main_context_tokens is SPARSELY persisted (1 of 6 phase blocks in the plan checked), so a 3.45x gap visible in the report is NOT reconstructible from that plan's store; (3) the disambiguating caveats are render-only. ⇒ A RENDERER THAT COMPUTES A FIGURE IT DOES NOT PERSIST HAS PRODUCED A NUMBER NOBODY CAN CHECK. Persistence half folded into CIS-022; labelling half routed to truthful-signals as -022 with an explicit offer to cut ours if they would rather own both. *** ⛔ CORRECTED SAME DAY, do not re-derive the struck version: the plan-45 build finding is LINEAR in loop-backs, NOT superlinear (3 gate executions x 2 Maven runs, 1 initial + 2 loop-backs, +21min; the x2 is the project's MANDATED two-command Pre-Commit Process and MUST NOT be targeted). And the RESOLVER IS FINE AND NOT INVOLVED - marshal.json build.map is a glob->build_class table applied to the ACTUAL DIFF, and the 1.5s/18.4s per-module runs prove it IS WIRED AND RAN. ⭐⭐ THE REAL FINDING IS BETTER: the six expensive runs never touched that machinery - default:pre-push-quality-gate is WHOLE-TREE, does NOT consult the footprint, and would have run identically ON A PURE .adoc CHANGE. TWO BUILD PATHS AND THE EXPENSIVE ONE IS BLIND. ⇒ The ask is cheap: wire the EXISTING PROVEN classifier to the gate as a second consumer, and settle whether a doc-only loop-back diff needs a full re-run. CIS-031 D6. *** ⭐ LESSON 2026-08-03-19-001, n=4 ACROSS TWO AGENTS INCLUDING ONE OF MINE: when a claim is about a MECHANISM, READ THE MECHANISM. A timing, a comment, an ordering or a ledger entry is a PROXY - it can be ACCURATE and still support the WRONG CONCLUSION, because it is silent about which mechanism produced it. My instance: I refuted a stale-cache defect from post-merge order: values, which were the order the plan INSTALLED, not the order it RAN. The operational tell is a CAUSAL VERB with no implementation file read ('the resolver chose', 'the gate selected', 'the sync ordered'). Reading the mechanism is usually CHEAPER than the inference - one grep for the config table beat an argument from six build durations. *** ⛔ .plan/temp/ IS 2.0GB / 1587 ENTRIES from prior sessions and was DELIBERATELY NOT PURGED: there is NO sanctioned mechanism - temp_on_maintenance is a SETTING whose consuming cleanup verb is still STAGED as the sibling's PLAN-TRUTH-022 - so a hand-rolled destructive sweep over files this session did not create would be the fix-at-the-tool-layer violation we file against others. Operator informed; own artifacts verified removed. *** ⭐⭐ PLAN-CIS-030 SHIPPED #1086 (merged 9b689d65b) - LEVER L3 HAS LANDED AND THE RESULT IS MIXED IN A WAY THAT MATTERS. ✅ D2's RECONCILIATION IDENTITY HOLDS EXACTLY: attributed sum 337,032,035 == cache_read_input_tokens 337,032,035, DELTA ZERO. That is the epic's first genuinely verifiable instrumentation claim and it was checked by ARITHMETIC, not accepted. ⛔ BUT IT IS VERIFIED ON ONE PHASE OF SIX: only 6-finalize carries the attribution group; phases 1-init..5-execute carry NO cache_read_input_tokens FIELD AT ALL - absent, NOT zero - because they ran under pre-merge code (record-metrics is order 998, after the merge and the cache sync). That is the non-self-exercisability rule landing on the instrument itself; EXPECTED, not a defect. ⛔⛔ AND MY OWN FIRST CHECK REPORTED 'OK' ON ALL SIX PHASES - it read an ABSENT field as 0 and concluded 0==0 reconciles. I reproduced, inside the verification of this plan, the exact defect this epic exists to detect. Caught only by comparing against #1080's 1-init, which records 6,808,836 over 652s while #1086's ran 1,707s and records the field nowhere. ⇒ WHEN CHECKING A RECONCILIATION, DISTINGUISH ABSENT FROM ZERO BEFORE SUMMING. *** ⭐⭐⭐ D3 PRODUCED A NUMBER THAT CHALLENGES THIS EPIC'S OWN VALUE CASE, and it is staged as PLAN-CIS-036 rather than absorbed: index-answerable 7.0pct / doc-residency 62.5pct / unattributed 30.5pct of exploration bytes (the three sum EXACTLY to exploration_result_bytes 1,561,854). If that generalises, the substrate's addressable share is an ORDER OF MAGNITUDE below the roadmap premise that exploration is 76-85pct of tool-result bytes. ⚠⚠ NOT A REFUTATION, and the reason is SPECIFIC not generic caution: the one instrumented phase is 6-finalize, which is where doc-residency should be HIGHEST by construction (every finalize step reads its own standard) - so it is plausibly the WORST CASE, and 2-refine and 5-execute, where a substrate would help most, have NO DATA. ⛔ CIS-036 is HARD-GATED on several plans composed AFTER 9b689d65b existing; at staging there is at most one, and a D1 over n=1 would reproduce the defect it exists to correct. ⭐ D3 worked exactly as its spec demanded - it called the split a DELIVERABLE, NOT AN ASSUMPTION, and it has now returned an unwelcome answer, which is what makes it worth having. *** ⛔⛔ R=0 NOW - NOTHING IS RUNNING, N=2, TWO SLOTS OPEN. But positions 1-4 (CIS-031, CIS-034, CIS-035, CIS-036) are ALL WS-04 in the plan-retrospective/finalize serialization class and may not pair WITH EACH OTHER either. ⇒ EMIT AT MOST ONE WS-04 PLUS ONE WS-01. Recommended pair: CIS-035 (WS-04, but see its new D0 gate) or CIS-034, PLUS CIS-024 or CIS-032 (both WS-01). ⛔ CIS-036 is NOT emittable yet - it needs post-#1086 plans to exist first. *** ⛔ THE PLUGIN-CACHE STALENESS BIT AND WAS CAUGHT ONLY BY LUCK: five separate agents were served 0.1.1240 while the registry pinned 0.1.1288, and for lessons-capture THE TWO BODIES MATERIALLY DISAGREED - the served one would have called architecture enrich POST-MERGE, writing tracked source onto main with NO PUSH PATH (#990). Each agent read the pinned body from disk instead. Cache now at 0.1.1292. ⚠ THE OPERATOR MUST RESTART THE SESSION for the agent registry to pick it up. The armed defect filed after #1084 has now discharged once. *** ⭐ SOURCERY'S ABSENCE HAS A DETERMINISTIC CAUSE, do not re-derive: it HARD-REFUSES above 150,000 diff characters. That retires the assumption that the #1077-#1086 absences were all rate-limiting - the sightings are a MIXED population of two mechanisms with different remedies, so any per-reviewer participation rate pooling them mis-attributes both. Forwarded to review-apparatus as -009 (flagged there as second-hand and needing re-derivation). *** DRAIN 08-03 THIRD PASS, 13 enumerated / 13 archived / 0 invalid: 2 lessons PROMOTED (2026-08-03-17-001 an aggregation states its predicate precisely and leaves the SET IT RANGES OVER implicit - all three of #1086's caught defects were this one shape, and the pre-existing tests PASSED against the first; 17-002 the orchestrator-tier yield boundary lets a task's own newly-authored tests ship UNEXECUTED, and the one that did was wrong). 9 folded: 001 -> CIS-035 as a NEW D0 GATE (the four per-dispatch columns have NO producer anywhere - populate or drop, silence is not an option); 002 -> CIS-034 R2 with a MAGNITUDE (~1.16M tokens, ~34pct under-report); 003+005 -> CIS-020 D8, and 003 gives the ROOT CAUSE - session_id is a SCALAR MODELLING A LIST, so a plan spanning sessions has no slot to append to and the guard alone would break a legitimate resume; 004 -> CIS-011 D10, whole dispatch CLASSES record no boundary, which also hands D8's `17 of 9` a candidate explanation to rule in or out; 006 -> CIS-034 R3 (our own capture-don't-derive remedy arriving UNPROMPTED from a second source); 008 -> CIS-032 with TWO rejections matching signatures the rule names VERBATIM - the strongest possible evidence that documentation cannot fix a call-time failure; 009 -> CIS-025, raising it from a consistency item to a MEASURED TOKEN COST because the index cannot answer for .claude/skills so structured-queries-first SILENTLY degrades to whole-tree; 010 -> CIS-016 as a FIFTH failure mode (the detector is INSIDE its own population and sampled before it finished contributing to it, so the one failure class it can never report is its own); 013 -> CIS-016 (config_hash drift at 4 of 4 boundaries - a warning that fires at 100pct is not a detector). *** ⚠ TWO WITHHELD medium-confidence proposals were RESCUED from the plan directory before it was archived: the sonar-roundtrip mis-prune (SECOND sighting, -> CIS-012; two consecutive plans shipped production Python with no Sonar lane) and the config_hash 4-of-4. *** ⚠ PROCESS VIOLATION BY ME, logged not hidden: I archived the twelve candidate-lessons with a single Bash loop, which CLAUDE.md forbids. All succeeded and the ledger is correct, so there is nothing to repair - but the rule exists so a partial failure is visible per message rather than buried in one exit code. *** ✅ OPERATOR JUDGMENT CALLS on #1086, both recorded as SOUND: merged rather than rebased (7 commits over a file set #1083 also touched; squash collapses it anyway, and branch-cleanup had correctly escalated overlap_with_content_conflict count=7 rather than auto-reconciling); and the pre-push gate recorded HONESTLY as 'whole-tree pytest timed out locally at 462s, CI green' rather than claiming a local pass - ⭐ the epic's own thesis applied by the operator to their own report, recorded as a POSITIVE instance. *** ⭐⭐ PLAN-CIS-001 SHIPPED #1084 (merged 714130bdb, corroborated via git log) - THE EPIC'S FLAGSHIP LEVER L4a IS CLOSED AND IT WAS PROBED BY EXECUTION, not by reading the diff: `architecture search --content --pattern X` runs and returns the four-field coverage contract (files_scanned 4227, unreadable, truncated, elided). Footprint an EXACT 37/37, recall 1.00 / precision 1.00, through a scope that MOVED during execute - that store's usual failure mode did NOT fire, recorded as a success baseline. Landing report at landings/PLAN-CIS-001.md. ⚠ MY PROBE FOUND WHAT THE PLAN DID NOT REPORT: `count` is a ROW count, not a file count - three distinct files came back as six rows, once per attributed module (default and plan-marshall). Same dual-attribution shape as the CIS-027 29-vs-24 reconciliation, but THAT one was labelled and this is not. Open Defect. *** ⛔⛔ R=1 NOW: PLAN-CIS-030 is RUNNING and already at 6-finalize. N=2 so ONE SLOT IS OPEN. ⛔ THE NEXT EMIT IS **NOT** THE QUEUE HEAD: positions 1-4 are CIS-031, CIS-034, CIS-035 - ALL WS-04 and all in the plan-retrospective/finalize serialization class, so NONE may pair beside a running CIS-030. The first admissible partner is PLAN-CIS-024 (WS-01, pm-documents) or PLAN-CIS-032 (WS-01, executor generator). DO NOT RE-DERIVE THIS. *** ⛔⛔⛔ A PRECONDITION ON CIS-030 ARRIVED TOO LATE TO GATE IT - truthful-signals-038, first-party from their #1083. RE-ENTERED PHASE ROWS ARE ARITHMETICALLY IMPOSSIBLE: total_tokens ACCUMULATES across a re-close while tool_uses and agent_duration_ms are REPLACED with the closing call's zeros; one row rendered ending 2h17m BEFORE it starts; and partial:false CERTIFIES it, because the completeness contract keys `recorded` off an end_time a re-entered phase already has. close_count>1 is the NORMAL shape of a run (our own #1080 had 13 self-review loops). ⇒ ANY PER-PHASE SHARE CIS-030's D1 EMITTED IS RETIRED AS EVIDENCE - the landing analysis must LABEL it, never record it as a result. Their PLAN-TRUTH-055 is an explicit precondition; do NOT schedule L3's per-phase re-derivation ahead of it, because re-deriving from rows that cannot be true produces a result that LOOKS AUTHORITATIVE. ✅ The COMPOSITION claim survives all three known mechanisms, so '~99% of cost is context' still holds. ⛔ AND: the four per-dispatch token columns are STRUCTURALLY EMPTY - 0 across 19 rows in three ledgers, uniformly not sparsely, because every producer omits the flags and the defaults persist AS THOUGH MEASURED. cache_read:0 is impossible for a dispatch consuming 541,951 tokens. A SCHEMA SLOT IS NOT A MEASUREMENT, and those columns are the ONLY per-dispatch view of what D2 exists to attribute. *** ⭐ NEW SPEC PLAN-CIS-035 dispatch-spend-on-dispatches-that-produced-nothing (WS-04, position 4): 32pct of #1084's 6-finalize dispatch spend went to dispatches terminating in error or blocked_session_restart; the phase burned 3.6M vs 5-execute's 0.82M. ⭐ THIS IS THE RIGHT KIND OF LEVER and the clearest instance yet of the legitimate target - a failed dispatch EXAMINED NOTHING and RETURNED NOTHING, so removing its cost removes ZERO detection capability, which is the opposite shape to the rejected examine-less levers. ⛔ ANTI-DRIFT: 'retry less' and 'give up earlier' are examination reductions wearing this plan's clothes - the target is the COST OF A FAILURE, never the willingness to attempt. ⚠ CIS-011 must land first; D1's shares need a denominator that is not `17 of 9`. *** DRAIN 08-03 SECOND PASS, 10 enumerated / 10 archived / 0 invalid: the CIS-001 landing; review-apparatus-004 (accepted all three of our forwards); truthful-signals 032-039. ⛔ TWO OF OUR OWN MEMORY RECORDS WERE REFUTED and are corrected: the 7-day .orphaned_at GC is CLAUDE CODE'S, not ours (our retention is a keep-union in which the marker is ADVISORY), and `.in_use` is REPAIR RESIDUE, not a pin oracle - installed_plugins.json is the only honest read. BOTH EPICS INDEPENDENTLY HELD THE SAME WRONG MODEL of a field neither owns. ⚠ And their refutation was itself corrected: scoped to the repo when the behaviour lives outside it, so the exposure INVERTS - our 180 ISO markers may never be collected by a GC expecting epoch-ms. Discriminator test runs after 2026-08-04 00:00Z. *** ✅ OWED RE-ROUTE DISCHARGED: the 7 lessons the CIS-001 retrospective misfiled to the global store (2026-08-03-14-001..007, because it dispatched with orchestrated:false WITHOUT resolving it - `orchestrator inbox detect` existing and not being called) were TRIAGED where they sat rather than relocated. All seven are correctly shaped as lessons so they STAY in the corpus; five folded into specs (001 -> CIS-031 D5 admission gate; 003 -> CIS-020 D8 the retrospective overwrites its own subject's session_id; 004 -> CIS-016 member E; 005 -> CIS-012 the COMPOSER prunes on a footprint it declared unresolvable in the same second, NOT to be merged with CIS-016 item D because one is a mis-report and this is a mis-action; 006 -> CIS-011 D9 proving the [STEP] population is PATH-DEPENDENT). ⛔ THE DISPATCH DEFECT ITSELF IS NOT FIXED - the next orchestrated plan will do the same thing. *** ⛔⛔ NEW OPEN DEFECT, ARMED: the plugin registry pin now points at a GC-SCHEDULED directory. After #1084's sync there is exactly ONE unmarked cache version, 0.1.1291, matching the executor - while installed_plugins.json still pins 0.1.1288, now ORPHAN-MARKED. That is the #896 failure mode armed (GC deleting a pinned version produced ModuleNotFoundError on the nifi upgrade). ⭐ MECHANISM FINALLY NAMED: sync-plugin-cache updates the CACHE and the EXECUTOR and NEVER THE REGISTRY, which is why it recurs daily. Not cosmetic - a stale 0.1.1240 read produced a flag a 0.1.1288 script rejected with exit 2, and the barrier turned that into 'clean, 0 findings' in 33s. A PRE-LAUNCH PIN CHECK CANNOT COVER A MID-FINALIZE DIVERGENCE. *** ANSWERED, do not re-derive: CIS-034 D4 does NOT cover the declared footprint side (D4 is realized_files CAPTURE only), so truthful-signals keep TRUTH-057 D1; the two-producer risk does not arise because these are TWO KEYS WITH ONE WRITER EACH, not one key with two - the thing to guard is NAMING drift. *** ⭐⭐⭐ SETTLED 08-03 AND THEN PARTLY CORRECTED THE SAME DAY - READ THE WHOLE SEGMENT, THE FIRST VERSION IS SUPERSEDED. THE #1069 EFFORT RAISE PAID FOR ITSELF, AND THIS CONSTRAINS THE WHOLE PRIO-1 PROGRAMME. #1069 = 2d0229d1c merged 2026-07-30T19:51:10Z: phase-6-finalize.effort.default level-3 -> level-5 (TWO levels), phase-5-execute.default level-4 -> level-5, phase-3-outline level-4 -> level-5, plus two verification-feedback keys and post-run-review. ⛔ NOT RAISED, AND THIS IS WHY THEY WORK AS CONTROLS: phase-2-refine and phase-4-plan are BOTH STILL level-3. Corpus split at that INSTANT on each plan's OWN [1-init] start_time: 39 before / 12 after / 0 spanning. *** ⛔ SUPERSEDED FIGURES, DO NOT RE-QUOTE FROM ANYWHERE: yield 1.88x, and fixed-share 34pct -> 70pct. They came from THREE finding files named from memory out of SIXTEEN that exist, and the two omitted were qgate-2-refine.jsonl and qgate-4-plan.jsonl - THE CONTROL GROUP. That is lesson 2026-08-03-06-002 (a named list is a sample) committed by the analysis that was promoting it, and it surfaced ONLY because the operator asked whether refine was covered. No part of the method caught it. *** ✅ COST - attribution RESTS ON A CONTROL and is solid: median total 3.09M -> 4.15M = 1.34x; raised 3-outline 1.38x, 5-execute 1.77x, 6-finalize 1.39x; CONTROLS 1-init 0.89x, 2-refine 1.11x, 4-plan 0.97x. Every raised phase rose, no control did. Share-of-total agrees independently. ⚠ The finalize 1.39x is a TWO-VARIABLE cut - the same commit set lessons-capture lane minimal -> off - so it is an UNDER-estimate; 5-execute's 1.77x is the clean figure. *** ✅ YIELD - real but weaker: ALL findings per plan 26.15 -> 43.92 = 1.68x against 1.34x cost, so cost per finding STILL IMPROVES; external pr-comment yield FELL 5.28 -> 4.50 (4.18 excluding #1080), a shift-left signature. ⛔ WITHDRAWN ON THE MEAN: control 4-plan rose 1.73x with effort unchanged and cost flat. *** ⭐⭐ REINSTATED ON THE ZERO RATE, and this is the load-bearing result: raised 3-outline 18 -> 0 pct, 5-execute 77 -> 58, 6-finalize 64 -> 17; CONTROLS WENT THE OTHER WAY, 2-refine 69 -> 83 and 4-plan 54 -> 58. So the old zeros WERE under-examination - this epic's archetype living in our own quality gates - now control-backed. ⭐ It also EXPLAINS the 4-plan anomaly: its mean rose while its zero rate ALSO rose, which is only possible if the extra findings concentrate in a few plans. The mean was outlier-contaminated; the zero rate was not. ⇒ ⛔ STANDING REPORTING RULE: to test whether a detector's behaviour changed, use the outlier-robust ZERO RATE, NEVER a mean over finding counts - a mean WILL manufacture an effect in a control group. *** ⛔⛔ ANTI-GOAL, UNAFFECTED BY THE CORRECTION: LOWERING EFFORT LEVELS IS NOT A SANCTIONED TOKEN SAVING. It is the one measured intervention that improves the token number while degrading detection - it would make our own instrument report success for a QUALITY REGRESSION. Reject any lever whose mechanism reduces to 'examine less' ON THAT GROUND, not by weighing it. The legitimate target is bytes that BUY NOTHING - redundant exploration, re-read documents, unscoped re-sweeps - NEVER examination depth. *** ⚠ REMAINING LIMITS: n=12 vs 39; the resolution-mix noise test is MUCH softer over the full population (fixed 29 -> 36 pct, not 34 -> 70) AND 39pct of before-period findings carry resolution <unset> so part of it is an INSTRUMENTATION shift, not a behavioural one; and 1,176 of 1,547 findings carry NO phase field, so every per-phase figure covers under a QUARTER of the corpus. ⛔ Any corpus figure spanning 2026-07-30T19:51:10Z is a BLEND OF TWO CONFIGURATIONS - partition and state both population sizes. All of this is folded into PLAN-CIS-030 as a D1 partition obligation, the zero-rate reporting rule and an anti-goal. Sent to truthful-signals as -018, corrected by -019, closed by -020. *** ⭐ AND THE 10.4M QUESTION IS ANSWERED: NOT a measurement change - all 51 archived plans carry the same instrumentation. #1080 at 10,373,979 is 2.9x the all-corpus median and 1.52x the previous max; against the POST-raise median of 4.15M it is still 2.5x. So the effort raise explains about a third and the rest is plan-specific (13 self-review rounds, THREE 5-execute re-entries, a doc-only diff that turned into executable code mid-run). ⚠ The earlier date-bucket 'upward drift' reading is RETRACTED as the explanation - it was mostly this config change. ⭐ Loop-backs are the strongest single correlate (4 plans declaring a re-entry: median 5.07M vs 3.49M for the 47 that do not) but n=4 AND confounded - a plan loops back BECAUSE it is hard. ⛔ 5-execute is the proportionally larger blow-out (6.3x median) vs finalize (3.4x), and NOTHING STAGED OWNS THE EXECUTE HALF - CIS-031 is the finalize/self-review half only. *** ⭐⭐ OPERATOR DIRECTIVE 2026-08-02, STILL BINDING: TOKEN REDUCTION IS PRIORITY 1, the lookup/substrate work is one leg of it, and THIS EPIC IS TOP PRIORITY. Verified first-party - the second-hand caveat from truthful-signals-027 is RETIRED, rely on it. *** N=2 (operator-raised 08-02, THIS EPIC ONLY; the two siblings stay at N=1). R=1 => ONE SLOT OPEN. RUNNING: PLAN-CIS-001 content-search-seam, plan id CONFIRMED AND STAMPED 08-03 as `content-search-seam` (ordinal prefix STRIPPED - probed via manage-status list, not guessed; the CIS-027-vs-CIS-028 asymmetry is now resolved for this plan). ⚠ It is ALREADY AT 6-finalize, so expect a landing shortly. *** EMITTED 08-03, awaiting operator confirmation (auto_emit=false so `launched` is operator-confirmed and `running` is operator-owned): PLAN-CIS-030 context-byte-attribution-instrumentation. ✅ THE WS-04 BAR THAT HELD IT IS LIFTED - CIS-028 shipped, so the plan-retrospective serialization class is free. Disjoint from CIS-001 (manage-metrics + platform-runtime byte categoriser vs the content-search seam). *** ⛔ NEXT PARTNER IS **NOT** THE QUEUE HEAD: PLAN-CIS-031 (position 2) AND PLAN-CIS-034 (position 3) are BOTH WS-04 and both sit in the plan-retrospective / finalize serialization class, so neither may pair beside CIS-030. The first admissible partner is PLAN-CIS-032 (WS-01, executor generator). DO NOT RE-DERIVE THIS. *** ✅ PLAN-CIS-028 SHIPPED #1080 (merged e1ae38142, corroborated via git log). Landing report at landings/PLAN-CIS-028.md. ⛔⛔ READ ITS SECTIONS 2 AND 3 BEFORE TOUCHING ANY FINALIZE ORDERING - two of three landing obligations closed and the third did NOT, and the answer to truthful-signals' both-directions question is NO. *** ⛔ THREE ORDERING DEFECTS LIVE IN MERGED MAIN - now OWNED by PLAN-CIS-034 as R1/R2/R3, and kept in Open Defects in full because they stay live until it lands: (1) record-metrics order 998 still runs AFTER plan-retrospective 995, so the largest phase of a run is read as zero at the moment the retrospective samples it (2.17x understatement measured on #1079); the partiality machinery still labels it, so this is an honest FLOOR not a falsehood. (2) lessons-housekeeping order 4, mutates_source TRUE, still runs 991 orders BEFORE the retrospective whose quality-verification-report.md it consumes - and ⭐ THE POST-RUN BAND CANNOT ABSORB IT, because band membership REQUIRES mutates_source:false. That is a structural tension, not a missed order edit, and a remedy that only moves it later leaves the first consumer. (3) capture-don't-derive: base..HEAD is correctly GONE from the footprint fallback chain, but the shipped tier 2 is the LEGACY references.modified_files key which the docstring scopes to pre-ledger-removal plans => for every NEW plan the archived path is UNRESOLVED PERMANENTLY. Honest-but-unmeasurable is a strict improvement over confidently-wrong and is NOT the same as measured - do not read the FOOTPRINT_UNRESOLVED sentinel as the class closing. *** ⚠ A CORRECTION I MADE TO MYSELF, KEEP IT: I briefly refuted the stale-cache mechanism by reading step `order:` values on post-merge main. That is the order the plan INSTALLED, not the order it RAN (runtime was branch-cleanup 70 -> plan-retrospective -> deploy-target 81 -> sync-plugin-cache 85). WHEN DIAGNOSING A RUN, READ THE ORDER FROM THE RUN'S MANIFEST OR STEP LOG, NEVER FROM THE TREE THE RUN PRODUCED. Filed as lesson 2026-08-03-06-004. *** ⭐ WATCH, verify on the NEXT plan composed after #1080: the reorder moved plan-retrospective to 995, which now sorts it AFTER sync-plugin-cache 85, so the stale-cache false verdict may have closed AS A SIDE EFFECT. Derived expectation, NOT an observation - by the non-self-exercisability rule it cannot be confirmed from #1080's own run. Observable: check-artifact-consistency reports `inconclusive`, not `fail - Recall 0%`. *** ⛔⛔ BINDING ON PLAN-CIS-030 D1 AND ON EVERY TOKEN FIGURE THIS EPIC QUOTES: a closed phase row is NEVER re-opened on loop-back. Measured on #1078 - 5-execute closed at 162,906 then re-entered three times for 758,059 more tokens that NO phase row absorbed, an 82% under-count, while the partiality marker named only 6-finalize. The partiality contract keys `recorded` off an end_time a re-entered phase ALREADY HAS, so it passes the completeness test while being wrong. => TREAT '~99% of billing weight is context' AS DURABLE AND EVERY PER-PHASE SHARE AS SUSPECT. D1 must reconcile phase rows against work/metrics-dispatch-boundaries-*.toon, not just re-read the rows. Corroborated first-party on #1080: 13 self-review rounds across three loop-back waves, 6-finalize 5.6M outspending 5-execute. *** DRAIN RESULT 08-03, 17 enumerated / 17 archived / 0 invalid / 0 archive failures: 4 lessons PROMOTED (2026-08-03-06-001..004); msg 009 FOLDED onto existing corpus lesson 2026-07-27-08-004 rather than promoted (dedup); 010 -> CIS-016 item D with the regex mismatch now VERIFIED FIRST-PARTY at check-routing-decisions.py:105-109 vs decision-rules.md:418 (affects EVERY standard-posture plan); 012 -> CIS-013, and it ANSWERS that plan's D1 design question (invert to a positive predicate - a drop-list fails toward `operator`, a positive predicate fails toward `synthetic`); 014 -> CIS-011 as D7; 005+006+008 FORWARDED to review-apparatus as code-intelligence-substrate-007.md; truthful-signals answered as -014.md. *** ⭐ THREE NEW SPECS STAGED: CIS-031 self-review-resweeps-full-surface (position 2, WS-04) is the LARGEST single token lever measured anywhere in the fleet - 13 dispatches / 2.98M tokens / 30% of the plan, at a FLAT ~230K per round while 9 of 13 rounds followed an edit touching 1-3 files. ⛔ It is NOT a round-count reduction: rounds 10-11 caught two structurally unreachable guards on a GREEN suite and were worth the whole budget; rounds 5-7 were ~690K of prose an external reviewer then invalidated. The loop is not wasteful, it is UNSCOPED. ⚠ Its D2 keys on head_at_completion, which is NOT reliably written - settle that first or it ships a no-op. CIS-032 executor-rejects-invalid-invocations (position 5, WS-01): 20 non-zero-exit calls / 14 unique signatures in ONE run. CIS-033 empty-skill-resolution (position 9, WS-01): delegated by truthful-signals and KEPT - their offer to take it back on the archetype was DECLINED, symmetric to our earlier answer on PLAN-TRUTH-035. *** ✅ ANSWERED TO truthful-signals, do not re-derive: PLAN-TRUTH-037 retires UNCONDITIONALLY now that #1080 landed as scoped; and the NEW INBOX EMISSION POINT is POST-MERGE - lessons-capture is order 991 with post_run_review:true, so it runs after branch-cleanup 70. They asked to be told when it settled; it is told. *** ⛔ STANDING, unchanged: (1) corroborate against origin/main AND PR state BEFORE any shipped transition - it has caught a FALSE landing claim THREE times; (2) PROBE THE OBJECTIVE LIVE, never accept a plan's own success report - #1080's own report said `24 affected files` and git show --stat says 26; (3) every set-guarding detector must be POPULATION-DERIVED, and any [STEP]-marker-derived count is a FLOOR not a count (9 of 16 steps carry markers). *** ⛔ QUEUE COUNTS AND ORDER: read status.json plans[] ARRAY ORDER. Never trust a count restated in prose. *** ⭐ SECOND-PASS DRAIN 08-03: truthful-signals-030 and -031 ARRIVED MID-DRAIN and were drained in the same pass (19 total, 19 archived, 0 invalid). ⛔ THREE THINGS FROM THEM, DO NOT RE-DERIVE: (a) THEY WITHDREW their own derivable-error-direction claim - #1082 shows the OPPOSITE mechanism (a blank 6-finalize row against an accumulator holding 2,686,561 on disk = the largest phase dropped WHOLE, so that plan UNDER-states finalize). TWO mechanisms are live at once and which dominates VARIES PER PLAN => the per-phase ranking must be RE-DERIVED, never bias-adjusted. PLAN-CIS-030's fold has been struck and rewritten accordingly; if any correction factor is ever encoded there, REMOVE IT - a bias correction on an error whose sign varies launders a suspect figure into a corrected one. (b) Their ask that #1080 needs a second reader obligation is ALREADY DISCHARGED and we told them so: their citing instance #1082 = b713fe4b9 merged BEFORE #1080 = e1ae38142, so it ran the PRE-FIX reader. What survives from that section is their concrete FALLBACK, which is CIS-034 R3. (c) OWNERSHIP SPLIT ACCEPTED AS THEY PROPOSED: we take the BAND CONTRACT, they keep the corpus-resolution half in PLAN-TRUTH-044 D3. Decided, not escalated - it routes by surface ownership and matches the symmetric calls on PLAN-TRUTH-035 and CIS-033. Their D3 gate is DISCHARGED by CIS-034 existing; CIS-034 D2 MUST read their D3 first. *** ⭐ NEW SPEC PLAN-CIS-034 post-run-band-contract-and-ordering-residue (WS-04, position 3) NOW OWNS the three Open Defects above as R1/R2/R3. ⭐ It is ONE plan not three because they share a root: a step's order: decides what it can SEE and nothing declares the producer->consumer edges. ⛔ Its D3 must fix the ORDERING and LEAVE THE PARTIALITY LABELLING INTACT - the labelling is the only component currently telling the truth. ⛔ WS-04 serialization class: never pair CIS-034 with CIS-030, CIS-031 or CIS-011. *** ⭐ CONVERGENT MEASUREMENT worth more than either number: truthful-signals measured pre-submission-self-review at 709,472 tokens (their L8 / PLAN-TRUTH-048) and we measured 2,979,307 on #1080. Two independent first-party measurements, an order of magnitude apart in absolute terms, AGREEING ON THE SHAPE. ⛔ Their circularity worry (L8's SHARE is 25%/13%/11% depending on which of three totals you divide by, so sizing is blocked behind L3) does NOT block CIS-031: its success test is STRUCTURAL AND BINARY. What needs L3 is the claim about how much it saved, not permission to do it - the same discrimination they accepted from us on L4a/L4b. NEITHER LEVER WAITS. *** NEXT ACTION: when PLAN-CIS-001 lands (it is already at 6-finalize) or the operator confirms CIS-030 started, run /marshall-orchestrator analyze slug=code-intelligence-substrate. *** OPERATOR-OWED: post-merge PR revisit on #1056 #1059 #1063 #1067 #1072 #1074 #1079 AND NOW #1080 - the final 8 commits of #1080 carry NO bot review at all while the quorum read green. - /marshall-steward marshal.json stamp: provisioned 0.1.1275, now 0.1.1288. - ⛔ plugin registry pin inversion recurred 08-01 AND 08-02, roughly daily; a session restart does NOT fix it; CHECK THE PIN BEFORE EVERY PLAN LAUNCH.

---

## Relocated: the pre-ingest Ordered Queue (annotated)

The hand-maintained annotated queue table as it stood before the 2026-08-22 ingest. Its
per-plan notes for the shipped plans are superseded by `landings/PLAN-CIS-*.md`, which carry
the same facts checked against the tree rather than against the plan's own account.


Five workstreams. ⛔ **Live count, live status, and live order are `status.json` `plans[]` — this
table restates none of them.** The former header asserted a plan count and claimed the `#` column
equalled both the `PLAN-CIS-{NNN}` ordinal and the array position; both claims had drifted (two rows
carried `#5`, and the asserted count trailed the array). A restated count is the epic's own
count-prose archetype, so it is removed rather than re-derived: read the array, never this heading.
The `#` column is a reading aid for queue order only and is authoritative for nothing.

| # | Plan | WS | Status | Surface (expected) | Notes |
|---|------|----|--------|--------------------|-------|
| — | PLAN-01 inventory-blind-spot | WS-01 | ✅ shipped #1056 | `manage-architecture`, `tools-marketplace-inventory` | `landings/PLAN-01.md` |
| — | PLAN-10 end-phase-replace-not-accumulate | WS-04 | ✅ shipped #1059 | `manage-metrics` | `landings/PLAN-10.md` |
| — | PLAN-11 audit-report-path-ignores-plan-dir | WS-05 | ✅ shipped #1063 | project auditor (`audit.py`) | `landings/PLAN-11.md` |
| — | PLAN-02 resolver-ext-point-seam | WS-02 | ✅ shipped #1067 | `extension-api`, `manage-architecture` | `landings/PLAN-02.md`. ⭐ **Its gate on PLAN-CIS-001/002/003/004/005 is RELEASED.** Shipped `doc/concepts/code-intelligence.adoc` + ADR-013/014. |
| — | PLAN-CIS-023 path-attribution-seam | WS-01 | ✅ **shipped #1072** | `manage-architecture` core, `extension-api` | `landings/PLAN-CIS-023.md`. ⭐ **Its gate on CIS-024 / CIS-025 / CIS-026 D2 is RELEASED.** Landed a **fourth sibling axis — `PathAttributionBase`, Axis-D** (topology nine → twelve), NOT a generalisation of shared plumbing. 7 deliverables, split guard evaluated and rationale recorded. ⛔ **H1 correction is load-bearing** — a path claim is a keyed mapping so a conflict IS expressible; the seam has its OWN rule and must not be harmonised with ADR-014's edge union. |
| — | PLAN-CIS-027 graph-merge-drops-every-resolver-edge | WS-02 | ✅ **shipped #1079** | `manage-architecture` core, `ext-point-derivation-resolver.md` | `landings/PLAN-CIS-027.md`. ⭐ **THE FOUNDING DEFECT IS CLOSED, AND IT WAS PROBED LIVE** — `edge_count` 0 → **24**, `impact pm-dev-java` empty → **9 modules**. Mechanism was none of the three hypothesised candidates: `architecture init` seeds an empty `internal_dependencies` stub and a **key-membership** test read all 12 modules as "declared with zero dependencies". ⭐ 29 resolver edges vs 24 graph edges **reconcile exactly** (5 dual-producer overlaps) — not a residue. |
| — | **PLAN-CIS-028 post-run-steps-ordered-before-their-evidence** | WS-04 | ✅ **shipped #1080** | `phase-6-finalize`, `plan-retrospective`, `.claude/skills` finalize steps | `landings/PLAN-CIS-028.md`. Merged `e1ae38142`. ⭐ **The `post_run_review` band shipped as specified** — derived per-step discriminator, post-merge band at `order > 70`, `mutates_source: false` mandatory and now **runtime-enforced** by `post_run_source_guard.py`. ⛔ **Two of three landing obligations closed; obligation 3 did NOT** — `record-metrics` (998) still runs after `plan-retrospective` (995). ⛔ **And the answer to `truthful-signals`' both-directions question is NO**: `lessons-housekeeping` (order **4**, `mutates_source: true`) still precedes the retrospective it consumes, and **band membership cannot absorb it** because the band requires `mutates_source: false`. Both are Open Defects. ⭐ **Cost**: 10.4M tokens for a 26-file diff; `pre-submission-self-review` alone was 30% of the plan → **PLAN-CIS-031**. |
| — | **PLAN-CIS-030 context-byte-attribution-instrumentation** | WS-04 | ✅ **shipped #1086** — `landings/PLAN-CIS-030.md`, merged `9b689d65b`. ⭐⭐ **D2's reconciliation identity HOLDS EXACTLY — attributed sum 337,032,035 == `cache_read_input_tokens`, delta ZERO.** The epic's first genuinely verifiable instrumentation claim. ⛔ **But verified on ONE phase of six**: only `6-finalize` carries the attribution group; phases 1–5 carry **no `cache_read_input_tokens` field at all** (absent, not zero) because they ran under pre-merge code. ⛔⛔ **My own first check reported OK on all six — it read absent as `0`. I reproduced the epic's flagship defect inside the verification of it.** ⭐⭐ **D3's split challenges the epic's own value case**: index-answerable **7.0%** vs doc-residency **62.5%** — but on `6-finalize`, the doc-residency worst case, so **neither confirmed nor refuted**. → **PLAN-CIS-036**. ⚠ *"a zero here is a MEASURED zero"* is a shipped design decision that is safe only while absent and zero stay distinguishable — Open Defect. |
| — | **PLAN-CIS-031 self-review-resweeps-full-surface-every-round** | WS-04 | ✅ **shipped #1126** | `pre-submission-self-review` round mechanics; `ext-self-review-plan-marshall` detector mix | `landings/PLAN-CIS-031.md`, merged `72982d3d4`. **All 6 deliverables fulfilled.** ⭐⭐ **Its `metrics.toon` is the epic's first six-phase instrumented record and it changed three things**: the composition claim is confirmed a THIRD time (context = **99.08%** of billing weight, recompute matching the published sum to 2 tokens); the exploration split is available on all six phases and **half-refutes PLAN-CIS-036** (`2-refine` is the worst case at 3.3% index-answerable, not `6-finalize`); and the cost decomposes into **`resident_context × turns`**, exposing a factor nothing owned → **WS-06**. ⛔ **It also REFUTES PLAN-CIS-035's headline premise** — 5 of 6 `error`-stamped dispatches found 5/5/2/3/4 defects, so `error` is not a proxy for "produced nothing". ⛔ Review coverage effectively **zero** (1 of 3 bots; the one that ran had both findings refuted). ⛔ **19 Q-Gate findings reached merge `pending`** → PLAN-CIS-044. ⚠ Superseded staging note follows: ⭐⭐ **NEW 08-03 — the largest single token lever measured anywhere in the fleet, and it is FIRST-PARTY.** On #1080: **13 dispatches / 2,979,307 tokens = 56% of 6-finalize and 30% of the whole plan**, at a flat ~230K/round, while **9 of 13 rounds followed an edit touching 1–3 files**. ⛔ **NOT a round-count reduction** — rounds 10–11 caught two structurally unreachable guards on a green suite and were worth the whole budget; rounds 5–7 were ~690K of prose an external reviewer then invalidated. **The loop is not wasteful, it is unscoped.** ⚠ D2 keys on `head_at_completion`, which is **not reliably written** — settle that first or the plan ships a no-op. ⛔ Never pair with CIS-011 (shared `mark-step-done` surface). |
| **new 1** | **PLAN-CIS-041 lsp-in-execute-lookup-and-write** | WS-03 | staged | live LSP client home (TBD at D1); possibly `manage-build-server` + `doc/concepts/build-server.adoc`; `phase-5-execute` consumer; config shared with CIS-005 | ⭐⭐ **NEW 08-09, OPERATOR-DIRECTED as the next step.** ✅ **Operator decision: STRICTLY OPT-IN, not default-on** — an unconfigured project loses nothing. A warm server used at **both ends of one task**: coordinates upfront (`definition`/`references`/`documentSymbol`), `WorkspaceEdit` + diagnostics later. ⭐ **The lifecycle objection dissolves because the amortization unit is the TASK ENVELOPE (~122 turns in `5-execute`), not the query.** ⭐ The data picks the same phase the operator did — `5-execute` has the **highest index-answerable share of any phase (33.6%)** and the longest envelopes. ⛔⛔ **This REOPENS what CIS-026 deliberately excluded (live pass-through) — do NOT fold it into CIS-026**; two incompatible lifecycles. ⛔ `marshalld` is the right host and its scope wall says "build-class work only" — D1 owns that decision plus the trust re-derivation. ⛔⛔ **A `WorkspaceEdit` is a mutation no context reviewed** — D3 must apply it through the recorded footprint-capturing path and verify by re-running diagnostics. |
| **new 2** | **PLAN-CIS-039 corpus-residency-admission-control** | WS-06 | staged | skill/standard loading contract; a corpus read verb (home TBD); `token-management.adoc` § 4 | ⭐⭐ **NEW 08-09 — THE EPIC'S LARGEST MEASURED BUCKET, AND IT IS NOT THE CODEBASE.** doc-residency is **65.2%** of exploration against index-answerable **15.9%** ⇒ **≈50% of every tool-result byte is plan-marshall reading its own skills, standards and workflow docs.** `persona-plan-marshall-agent` alone is 14,835 B of `SKILL.md` + 101,897 B of standards, loaded unconditionally by **every** dispatch. ⭐ Applies the discipline `code-intelligence.adoc` already states ("location and strength, never the lines") to the corpus for the first time. ⛔ **NOT the examine-less anti-goal** — a smaller *slice* of a document read anyway, never fewer documents. ⚠ D1 is a hard gate: the split is **n=1** and this epic has twice recorded a phase-specific figure read as a whole-corpus one. |
| **new 3** | **PLAN-CIS-042 attribution-populations-and-the-cost-decomposition** | WS-04 | staged | `manage-metrics` emission + `standards/data-format.md`; archived `metrics.toon` (read-only) | ⭐⭐ **NEW 08-09.** CIS-030 D2's identity holds **because `cache_read_unattributed` is a catch-all**: it absorbs **65.9%** of all `cache_read` and **≥83% in every phase except `6-finalize`** (40.5%). ⇒ **the instrument attributes usefully only in the phase it was built against** — this epic's signature archetype on the instrument for the SECOND time. ⭐ **Two different `unattributed` numbers exist** (bytes 18.9%, `cache_read` 65.9%) and CIS-036 D2 names one. Also emits `resident_context_tokens` + `turns`, and owns the **`4-plan` creation inversion** (65.4% of its billing weight is `cache_creation` vs 6–25% elsewhere). ⛔ **Should land before CIS-039/040** wherever a figure is load-bearing. |
| **new 4** | **PLAN-CIS-040 envelope-length-and-the-isolation-currency** | WS-06 | staged | dispatch granularity (phase TBD by D1); `doc/concepts/token-management.adoc` § 6 | ⭐⭐ **NEW 08-09 — the other cost factor.** The average byte is re-read **44.6×**, so `cost(byte) = 1.25 + 0.1 × turns_remaining`; splitting a 122-turn envelope into four 30-turn ones cuts the multiplier **13.4× → 4.15×** for ~47K of extra creation against a 28.4M phase. ⭐⭐ **And § 6 defends per-dispatch isolation in ORCHESTRATOR-CONTEXT-SIZE while the epic has established the driver is BILLING WEIGHT** — doc-contract-divergence on the system's largest architectural bet. ⛔ **The bet is right; the argument is wrong** — isolation bounds `turns_resident`, and D2 restates it without weakening it. ⚠ D4's real gate is finding a split where the second half genuinely does not need the first half's residency — otherwise it converts cheap `cache_read` into expensive `cache_creation`. |
| **new 5** | **PLAN-CIS-043 self-review-surfacing-integrity** | WS-05 | staged | `ext-self-review-plan-marshall` detectors + registry; `pre-submission-self-review.md`; orchestrator `inbox write` | ⭐⭐ **NEW 08-09, all three arms re-grounded at HEAD.** (A) `_detect_count_prose:1070` opens only `SKILL.md` while its sibling `:276-279` globs `standards/*.md` ⇒ **a stale count in a standards doc is invisible to every round, delta or full.** (B) `duplicate_claimable_keys` / `discard_without_report` carry `in_total: true` with **no consuming check** ⇒ volume-read-as-coverage **inside the contract that detects volume-read-as-coverage**. (C) ⛔⛔ **`scope_searched` + `files_scanned` NEVER SHIPPED** — `review-apparatus`'s hard requirement arrived **23 min after CIS-031's `1-init`** and was drained a day after it merged; verified absent at HEAD. ⛔ `2026-07-18-14-001` is **deliberately scoped OUT**. |
| **new 6** | **PLAN-CIS-044 blocking-boundary-arms-on-a-call-not-a-state** | WS-05 | staged | `_invariants.py`, `_cmd_lifecycle.py`, `phase-6-finalize` | ⭐⭐ **NEW 08-09, re-grounded at HEAD.** 19 Q-Gate findings reached merge `pending` on #1126. `_BLOCKING_BOUNDARIES` (`_invariants.py:1030`) is exactly `{6-finalize}` and the raise (`:1248`) fires only when a `capture` call **arrives carrying that phase** — #1126's `handshakes.toon` has no `6-finalize` row. ⇒ ⛔ **the gate arms on a call that must happen, not a state that must hold, and a missing call is indistinguishable from a passing gate.** ⭐ **No defect shipped — which is exactly what makes it worth filing**: the inertness was invisible because the outcome was fine. ⚠ D1 must derive the population; if the missing row is universal the gate has been inert fleet-wide. |
| 2 | **PLAN-CIS-034 post-run-band-contract-and-ordering-residue** | WS-04 | staged | `phase-6-finalize` band narrative + guard, `ext-point-finalize-step.md`, the `order:` frontmatter of four steps, `branch-cleanup`/`push` | ⭐ **NEW 08-03 — the three residues #1080 left, and it is the AGREED answer to a cross-epic ownership split.** ⛔ **`PLAN-TRUTH-044` D3 is GATED on this plan existing and must not implement against the band contract** — we take band membership, they keep the corpus-resolution half. R1: `mutates_source: true` and `post_run_review` are **mutually exclusive**, and `lessons-housekeeping` needs both — so it cannot simply move; leading candidate is split-the-step. R2: `record-metrics` (998) after `plan-retrospective` (995). R3: capture-don't-derive. ⭐ **One plan, not three: a step's `order:` decides what it can SEE and nothing declares the producer→consumer edges.** ⛔ D3 must fix the ordering and **leave the partiality labelling intact — it is the only component currently telling the truth.** ⛔ WS-04 serialization class: never pair with CIS-030/CIS-031/CIS-011. |
| — | **PLAN-CIS-001 content-search-seam** | WS-01 | ✅ **shipped #1084** — `landings/PLAN-CIS-001.md`, merged `714130bdb`. ⭐⭐ **FLAGSHIP LEVER L4a CLOSED, PROBED BY EXECUTION**: `architecture search --content` runs and returns the four-field coverage contract (`files_scanned` 4227). Footprint an **exact 37/37**, recall 1.00 / precision 1.00, through a scope that moved during execute — a success baseline. ⚠ **My probe found what the plan did not report**: `count` is a **ROW** count, not a file count (three files → six rows under dual module attribution) — the CIS-027 shape, unlabelled. ⛔ ReDoS **accepted, not fixed**; any future bound MUST be a reported coverage field, never a silent cap. |
| 3 | **PLAN-CIS-035 dispatch-spend-on-dispatches-that-produced-nothing** | WS-04 | staged | dispatch ledger, `record-dispatch-boundary`, finalize terminal-state handling | ⭐⭐ **NEW 08-03 from the #1084 landing — the clearest instance yet of the LEGITIMATE token target.** **32% of that run's 6-finalize dispatch spend went to dispatches terminating in `error` or `blocked_session_restart`**; the phase burned 3.6M against 5-execute's 0.82M (4.4×). ⭐ **A failed dispatch examined nothing and returned nothing, so removing its cost removes ZERO detection capability** — the opposite shape to the rejected examine-less levers, and exactly the "bytes that buy nothing" the effort analysis identified. ⛔ **Anti-drift clause**: *retry less* and *give up earlier* are examination reductions wearing this plan's clothes — the target is the **cost of a failure**, never the willingness to attempt. ⛔ Distinct from CIS-031 (re-sweeps that DO examine); neither subsumes the other. ⛔⛔ **BLOCKER CORRECTED 2026-08-08: it is `PLAN-CIS-037`, NOT CIS-011.** The `17 of 9` denominator was CIS-011's D8 and moved out in the split — **do not re-derive the old dependency.** |
| **new** | **PLAN-CIS-037 dispatch-boundary-ledger-is-not-a-commensurable-population** | WS-04 | staged | `manage-metrics` boundary writer + recorded-vs-expected renderer; the non-registering dispatch sites | ⭐⭐ **CREATED 2026-08-08 by splitting CIS-011 (11 deliverables → three plans).** Takes the boundary-ledger arithmetic arm: the `17 of 9 … complete` ratio, the dispatch classes that register **no** boundary (`2-refine`, `q-gate-validation`), and the comparator that annotates **exact agreement** as *"smaller than total_tokens"*. ⭐ **One defect from three angles — the ledger has no declared population**, and the class omission is very likely the *mechanism* behind the impossible ratio, so D2 must test D3 first. ⭐ **This is `PLAN-CIS-035`'s real blocker**, and it is a focused 5-deliverable plan rather than an 11-deliverable one ⇒ **CIS-035 unblocks EARLIER than the ledger previously said.** ✅ D3 is confirmed on an independent plan neither epic ran. ⛔ WS-04 class: never pair with CIS-011/034/035/038/020. |
| **new** | **PLAN-CIS-038 frozen-manifest-diverges-from-live-config** | WS-04 | staged | `manage-execution-manifest` frozen-vs-live; `finalize-step-sync-baseline` executor regen; simplify prompt; title-token log | ⚠ **CREATED 2026-08-08 by splitting CIS-011** — the third arm, and **the weakest-cohesion of the three, stated rather than hidden**: D2/D3 are one story (a frozen view going stale mid-run), D4 is genuine miscellany grouped by *who filed it*, not by surface. ⛔ **Carries the OLDEST claims in the queue (2026-06-21 … 2026-07-10) and MUST re-ground all four before scoping** — the same reconciliation that created it retired CIS-008 in full and halved CIS-020. **Expect at least one to be already closed.** ⚠ Lowest priority of the three arms; blocks nothing. |
| 4 | **PLAN-CIS-036 exploration-split-measured-on-one-phase-and-it-is-the-worst-case** | WS-04 | staged | `work/metrics.toon` corpus (read-only), `billing-composition` audit check | ⭐⭐ **NEW 08-03 — the epic's own instrument returned a number that CHALLENGES the epic.** PR #1086's D3 split measured **index-answerable 7.0%** vs **doc-residency 62.5%** (unattributed 30.5%) of exploration bytes — an order of magnitude below the roadmap premise. ⚠⚠ **NOT a refutation, for a specific reason**: the only instrumented phase is `6-finalize`, where doc-residency should be HIGHEST by construction, so it is plausibly the **worst case** — and `2-refine`/`5-execute`, where a substrate would help most, have **no data**. ⛔ **HARD-GATED**: needs several plans composed after `9b689d65b`; at staging there is at most one, and a D1 over n=1 reproduces the defect it exists to correct. ⭐ **D3 worked as specified** — its spec called the split *a deliverable, not an assumption*. |
| 5 | **PLAN-CIS-024 documentation-surface-provider** | WS-01 | staged | `pm-documents` | ⭐ **NEW 08-01.** Doc-corpus claim + de-dup (owns the ROW-vs-FILE-count defect) + doc search + `xref` resolution. ⛔ D3 must NOT ship a second search verb — coordinate with CIS-001. ✅ Disjoint from every WS-02/04/05 plan. |
| — | **PLAN-CIS-032 executor-rejects-invalid-invocations-before-spawn** | WS-01 | ✅ **shipped #1127** | executor **generator** (`tools-script-executor`); new `script-shared/scripts/argparse_surface.py`; `plugin-doctor` analyzers | `landings/PLAN-CIS-032.md`, merged `415dcf139`. 26 files, +7789/−1070. ⭐⭐ **PROBED LIVE by the orchestrator, and the probe checked the STREAM because that was the founding defect**: `manage-tasks nuke` returns the `invalid_invocation` TOON with a 21-verb accepted set, **and it survives `2>/dev/null`** ⇒ the corrective is on **stdout**. ⭐ The edit-time rule and the dispatch-time rejection now read ONE definition and cannot disagree. ⭐⭐⭐ **The method result: the plan REFUTED its own non-self-exercisability premise in flight** — phase-5 generates a *worktree-bound* executor, so the boundary is main-checkout-and-cache-scoped, not absolute. **Four false-rejection defects were found ONLY by probing live, none by the suite**, because *"every fixture surface happened to declare at least one flag"* → **PLAN-CIS-045**. ⛔ Q-Gate 13 findings, **0 pending** (contrast #1126's 19 → evidence for CIS-044). ⛔ `affected_files` recall **58%**, and two undeclared files were the subject of three review findings. |
| **new 7** | **PLAN-CIS-045 generator-fails-open-and-its-fixtures-cannot-see-it** | WS-05 | staged | `tools-script-executor` generator + template; `script-shared/argparse_surface.py`; the fixture corpus | ⭐⭐ **NEW 08-09 from the #1127 drain — two arms, one root.** (A) `generate_executor` **fails open**: it reported success over a **surfaces-less executor** and the guard was not live on main; the only observable is the **absence** of a stats line, which nothing consumes. ⚠ **A SECOND, independent mechanism by which the on-main executor disagrees with merged source** — ⛔ do not merge it with the pin inversion. (B) **the fixtures are structurally unable to see it**: four defects shipped past a green synthetic suite because every hand-built fixture is *populated*, making the whole class *"the derivation strips attribute X"* invisible. ⭐ **The repair half worked every time** (fail-first proof + matched negative controls on all four) — **the gap is DETECTION, not remediation.** ⛔ Anti-goal: do not add hand fixtures for the four known cases; that is the move that produced the blind spot. |
| — | *PLAN-CIS-032 — its original staging note, kept as the record of what was predicted* | WS-01 | *(superseded by the shipped row above)* | executor **generator** (`tools-script-executor`); `ARGUMENT_NAMING_*` cluster boundary | ⭐ **NEW 08-03 — first-party.** **20 non-zero-exit script calls, 14 unique signatures in ONE run**, in the repo whose own domain is these scripts; the retrospective reproduced the class *while writing the report*. ⛔ The `ARGUMENT_NAMING_*` guard is a **documentation-authoring** check and is structurally incapable of seeing a call composed at runtime from prose — and the four canonical signatures are **already** written down, so **more prose is the defending-documentation archetype**. Validate pre-spawn from the `SCRIPTS` mapping the executor already embeds. ⛔ **Fail-closed on the validator's own uncertainty** — an undescribable script must spawn as today. ⛔ **Never edit the generated executor directly.** |
| 8 | **PLAN-CIS-025 project-local-artifact-provider** | WS-01 | staged | `pm-plugin-development` | ⭐ **NEW 08-01.** `.claude/**` claimed uniformly; settles the skills-vs-commands inconsistency. ⚠ Carries an ownership DECISION (move from `plan-marshall`?) — artifacts and their tests may split across modules. |
| 7 | PLAN-CIS-002 lsp-shaped-query-api | WS-02 | staged | `manage-architecture` (+2 consumers) | LSP vocabulary + capability report + vacuous-guard fix. ⭐ **RESCOPED 08-01: additive-facade branch DECIDED, do not re-derive** — residue (`path`/`impact`/`find`/`which-module`) goes to `workspace/executeCommand`. ⚠ Co-design risk with PLAN-02. |
| — | PLAN-CIS-003 marketplace-dependency-resolver | WS-02 | ✅ **shipped #1074** | `pm-plugin-development`, `pm-dev-python` | `landings/PLAN-CIS-003.md`. 3 resolvers now execute across both hierarchies and `component_refs` materialized. ⛔ **But its headline claim — "founding defect closed" — was REFUTED at HEAD: 29 resolver edges, `graph.edge_count: 0`.** F2/F5 stay open. → PLAN-CIS-027. |
| 9 | **PLAN-CIS-029 architecture-store-concept-model** | WS-01 | staged | `manage-architecture` core (`_architecture_core.py`, `_cmd_enrich.py`), `.plan/project-architecture/**` | ⭐ **NEW 08-02 — from the operator's OKF read, redirected by the operator onto the PERSISTED STORE.** The store is bundle-shaped but has no concept model: `key_packages` uses dotted pseudo-ids resolving to no path, no `type`, `_project.json`'s `modules` map holds 12 keys → **empty objects**, and provenance/freshness is mtime only (8 of 12 docs untouched since 06-29). Adopts the **OKF data model only** — path-as-identity, closed-vocabulary `type`, description-bearing index, `generated`+`worktree_sha`; **rejects** markdown serialization and OKF's tolerate-broken-links / open-type-registry leniency. ⛔ **HARD-GATED on CIS-027** (same-file collision in `_architecture_core.py`), and sequenced BEFORE CIS-026/CIS-004 so both write into a settled model. ⛔ Verify-first: descriptions in `modules` must NOT restore it to discovery gatekeeper — the on-demand crawl semantic is load-bearing. |
| 10 | **PLAN-CIS-033 empty-skill-resolution-indistinguishable-from-minimal** | WS-01 | staged | task-allocation skill resolution; `manage-architecture` `skills_by_profile` | ⭐ **NEW 08-03 — delegated by `truthful-signals` (their `-028`) and REMOVED from their ledger; we declined their offer to take it back on the archetype.** An empty resolution and a deliberately-minimal one both degrade silently to the persona floor, so **nothing reports that a task ran without its methodology skills.** ⭐ **The masking effect is the defect**: a mis-domained task hits the SAME empty resolution as a genuinely empty inventory, so the cheaper explanation wins and **the real inventory gap survived the fix — which is what happened.** ⛔ **A fix that merely ERRORS on empty will be worked around with a placeholder skill and the signal is lost invisibly** — *deliberately minimal* must be expressible, aligned with the CIS-008/009 closed-vocabulary posture. ⚠ D1 is a gate: the finding was checked against **0.1.1276**, which predates our tree. ⛔ Never pair with CIS-029 (shared store schema). |
| 13 | **PLAN-CIS-026 lsp-derivation-resolver** | WS-02 | staged | resolver home TBD at outline; `extension-api` (read-only) | ⭐ **NEW 08-01 — the plan the direction decision converges on.** LSP server as a derivation-time producer, not a query backend. ⛔ **D1's batch-harvest feasibility is the central risk — test it FIRST, before scoping anything else.** Depends on CIS-023 for the file→module lift. |
| 14 | PLAN-CIS-004 native-coordinate-resolvers | WS-02 | staged | `build-pyproject`, `build-npm`, (verify `build-gradle`) | ✅ Disjoint from PLAN-CIS-003 and PLAN-CIS-005. |
| 15 | PLAN-CIS-005 resolver-configuration | WS-02 | staged | `marshall-steward`, `manage-run-config` | ✅ Disjoint from PLAN-CIS-003/004. ⚠ **PLAN-CIS-026 D4 shares this config surface** — coordinate, do not fork it. |
| 16 | PLAN-CIS-006 validate-precision | WS-03 | staged | `pm-plugin-development` (`_dep_detection.py`) | ⛔ **Hard gate for PLAN-CIS-007.** |
| 17 | PLAN-CIS-007 skill-lsp-server | WS-03 | staged | new skill under `pm-plugin-development` | Protocol adapter over an LSP-shaped API. ⭐ **08-01: its shape is now settled by the C decision** — a thin adapter over CIS-002's facade, and the natural host for the `marshalld`-warm live pass-through that CIS-026 excludes. |
| 18 | PLAN-CIS-008 scope-estimate-vocabulary-closure | WS-04 | staged | `plan-retrospective` (anchors), producers (read-only) | No absolute budget anchor for `multi_module`. |
| — | PLAN-CIS-009 documented-enum-diverges-from-argparse-choices | WS-04 | shipped (PR 1100) | `manage-metrics`, `plan-retrospective` (reference) | Doc claims 6 of 11 values and asserts the rest are rejected. |
| 11 | PLAN-CIS-010 finalize-dispatch-evidence-is-missing | WS-04 | staged | `phase-6-finalize` | ⛔ **Before PLAN-CIS-011.** Carries a mandatory split guard. |
| 12 | PLAN-CIS-011 finalize-dispatch-manifest-observability | WS-04 | staged | `phase-6-finalize`, `manage-execution-manifest`, `manage-status` | ⛔ **Trap + cross-epic sequence — read the spec.** ⭐ **D7 added 08-03** — fuse the `[STEP]` emission to the `mark-step-done` handshake; a step can satisfy `phase_steps_complete` while leaving no operational-log trace. ⛔ Never pair with CIS-031 (shared `mark-step-done` / `head_at_completion` surface). |
| 20 | PLAN-CIS-012 footprint-read-outside-its-window | WS-04 | staged | `plan-retrospective`, `manage-execution-manifest` | ⛔ **Partial-fix trap — read the spec.** |
| 21 | PLAN-CIS-013 chat-signal-provenance-filter-under-inclusive | WS-04 | staged | `plan-retrospective` | Filter is wrong in both directions at once. |
| 22 | PLAN-CIS-014 aggregate-cost-invisible-to-per-call-ceiling | WS-04 | staged | `platform-runtime` + hook layer | Truncated records that do not declare their truncation. |
| 23 | PLAN-CIS-015 outline-plan-scope-derivation-integrity | WS-05 | staged | `phase-3-outline`, `phase-4-plan`, `manage-tasks` | "Derived, not asserted." D1 may split. |
| 24 | PLAN-CIS-016 auditor-detector-integrity | WS-05 | staged | project auditor (`audit.py`) | At the six-deliverable guard — **do not add to it**. |
| 25 | PLAN-CIS-017 freshness-gate-cannot-distinguish-test-authored-evidence | WS-05 | staged | freshness gate + test tree/conftest | Split guard already recorded. |
| 26 | PLAN-CIS-018 main-sha-records-the-pinned-cwd | WS-04 | staged | phase-handshake capture + `summarize-invariants` | `main_sha` holds a feature-branch commit from phase 5 on. |
| 27 | PLAN-CIS-019 manifest-cross-check-discards-production-tree | WS-04 | staged | `plan-retrospective` (`check-manifest-consistency.py`) | ⛔ Absorbs the former unowned **M3 vacuous-guard** defect — do not re-add it to PLAN-CIS-016. |
| 28 | PLAN-CIS-020 retrospective-report-sections-structurally-dead | WS-04 | staged | `plan-retrospective` (`retro_sections.py`, `compile-report`) | At the six-deliverable guard. ✅ Cross-epic ownership check **RESOLVED** — we keep the render path, they keep the zeroed columns. |
| — | PLAN-CIS-021 self-review-cannot-see-a-duplicate-claimable-key | WS-05 | shipped (PR 1107) | `pm-plugin-development` (`ext-self-review-plan-marshall`) | Two mechanical candidate classes. ⛔ Spec records a deliberate scope EXCLUSION — do not re-add it. |
| 30 | PLAN-CIS-022 token-ledgers-disagree-and-the-smallest-is-named-actual | WS-04 | staged | `plan-retrospective`, `manage-metrics` | ⛔ **D1 is a hard gate** — every figure is two hops from observation and unverified. |

⛔ **Five staged specs carry scope-changing constraints in their own text — read the spec, not this
table**: PLAN-CIS-010 (split guard), PLAN-CIS-011 (roster-is-wrong trap + PLAN-TRUTH-001 sequence), PLAN-CIS-012
(partial-fix trap), PLAN-CIS-021 (recorded scope exclusion), PLAN-CIS-022 (hard verification gate before
any other deliverable may be scoped).


---

## Relocated: Queue Reconciliation 2026-08-09 — full-queue review

The reconciliation pass that preceded the cloud wave. **Two of its five findings were
themselves corrected by the wave** — see `epic.md` § 2026-08-22 Landed-Corpus Ingest,
corrections C1 and C2. Retained because its standing rules (R1's historical-id rule, R2's
surface-derived serialization classes) are still binding and are cited from the live ledger.


> Second full-queue pass (the first was 2026-08-08). Scope: correctness against HEAD, ambiguity,
> duplication, and distribution across the 34 staged plans. ⛔ **Coverage is stated honestly below —
> this pass verified a subset first-party and says which.**

### R1 — ⛔⛔ THE OLDER HALF OF THE QUEUE CITES A RETIRED EPIC AS ITS BLOCKERS

**At least six specs gate, block, or sequence themselves against `PLAN-NN` ids belonging to the
retired `plan-optimization` epic** — PLAN-10, 42, 46, 51, 52, 54, 57, 59, 60, 62, 73, 74, 75, 80, 81,
89, 92, 94, 99, 100, 102, 103, 109. **Every one of them shipped.** Instances struck this pass:

| Spec | Stale constraint | Effect |
|---|---|---|
| `CIS-010` | *"blocked while PLAN-92 is in flight"*; overlaps PLAN-100/52/60 | **would have blocked an emit** |
| `CIS-012` | *"⛔ BLOCKED BY PLAN-10"* on D5 | **would have blocked D5** (PLAN-10 = #1059, shipped) |
| `CIS-013` | *"Gated on PLAN-54 landing"* | **would have blocked the whole plan** |
| `CIS-017` | D3 depends on *"until PLAN-59 lands"* | **changes D3's shape** — see R4 |
| `CIS-014`, `CIS-015`, `CIS-016` | PLAN-42/46/73/74/75/80/94 as sequencing context | narrative only |

⇒ ⛔ **STANDING RULE, binding on every emit: a `PLAN-NN` id with NO `CIS` segment is HISTORICAL.**
Do not re-derive a blocker from one. The live queue's ids are `PLAN-CIS-NNN` plus the four legacy
`PLAN-01/02/10/11` rows, all `shipped`.
⭐ **This is F0 (a staged spec decays against a moving tree) at a new granularity: not the spec's
*claim* decaying, but its *dependency graph* pointing at a graveyard.** F0's remedy (re-ground before
emitting) catches the first; nothing was catching the second.

### R2 — ⛔ THE `WS-04` SERIALIZATION CLASS IS OVER-BROAD, AND THAT IS THE THROUGHPUT BOTTLENECK

**15 of the 34 staged plans (44%) are WS-04, and the epic declares WS-04 a single serialization class
in which no two may pair.** With `N=2` that caps the epic at *one WS-04 plan at a time* — a
15-deep serial critical path.

⭐⭐ **But WS-04 is not one surface. It is four, wrongly pooled** — the class was written from the
*workstream*, not from the *surfaces*:

| Real surface | Plans | Mutually exclusive? |
|---|---|---|
| `plan-retrospective` | CIS-012, CIS-013, CIS-016(part), CIS-019, CIS-020, CIS-022 | yes |
| `phase-6-finalize` | CIS-010, CIS-011, CIS-034 | yes |
| `manage-metrics` | CIS-042, CIS-037, CIS-035 (+CIS-022 render side) | yes |
| `manage-execution-manifest` | CIS-038 (+CIS-012 secondary) | yes |
| **`platform-runtime` + hook** | **CIS-014** | ⭐ **collides with NOTHING in WS-04** |
| **phase-handshake / `_invariants.py`** | **CIS-018** | ⭐ **collides with NOTHING in WS-04** |
| **read-only corpus** | **CIS-036** | ⭐ **mutates nothing — collides with NOTHING** |

⇒ ✅ **CIS-014, CIS-018 and CIS-036 are freed to pair with the retrospective/finalize cluster.**
⛔ **They stay in WS-04** — the workstream is a *charter*, and measurement integrity is genuinely
their theme. **The defect was conflating the charter with the disjointness class.** § Operating Rules
now lists surface classes, not workstream classes.

### R3 — ⛔ DUPLICATION: TWO WRITERS FOR ONE FIX, TWICE

- **`[DISPATCH]` emission** — `CIS-011` D11 *and* `CIS-010` (whose own boundary note assigns it to
  CIS-011 while its Third Evidence Fold claims it). **Self-contradictory inside one spec.**
  ✅ **Settled: CIS-011 owns emission; CIS-010 keeps the detector, `[ARTIFACT]`, and the
  channel-completeness ratio.** CIS-010's D2 re-scoped from emission to consumer-side discrimination.
- **recall-0% / footprint** — `CIS-013` items (b) and (e) duplicate `CIS-012`'s entire founding
  subject. ✅ **Struck from CIS-013; CIS-012 is sole consumer-side owner, CIS-034 D4 sole producer.**
  CIS-013's item (c) also cross-noted to `CIS-022` rather than folded, to avoid a third writer.

### R4 — ⭐ CORRECTNESS: ONE MECHANISM REFUTED, TWO CONFIRMED AND SHARPENED

| Spec | Verdict | Evidence |
|---|---|---|
| **`CIS-018`** | ⛔⛔ **mechanism REFUTED, symptom CONFIRMED live 08-09** | `_capture_main_sha` already passes an explicit tree (`_invariants.py:437`), so D2 as written is a **no-op**. The defect is one layer down in `_repo_root()` (`:253`). Symptom reproduced on #1126's `5-execute` row (`main_sha == worktree_sha == a6657d8b`). **Plan is now smaller and more precise.** |
| **`CIS-016` A** | ✅ stands; line stale | site moved `:873` → `:1070`; `metadata.get("recipe_key")` has **zero hits** — the auditor populates `recipe_key` *from* `plan_source` and never reads it |
| **`CIS-016` B** | ✅ stands, **bigger than filed** | `[LOCK] (merge:` appears in **3 files, all TESTS, zero production emitters** ⇒ the detector *and its passing test suite* are both vacuous |
| **`CIS-013`** | ✅ exact at HEAD | `:101` / `:149` / `:264` all still correct — no re-derivation owed |

⭐ **CIS-018 is the pass's most valuable result**: its own verify-first clause predicted exactly this
outcome (*"if capture already takes an explicit path and resolves it wrongly, D2's remedy changes
shape"*) — **the clause paid for itself**, and a plan that would have shipped a green no-op now has
the right target.

### R5 — ⚠ SPEC BLOAT IS NOW A FIRST-ORDER COST, AND THE EPIC IS GENERATING IT

`CIS-012` is **428 lines**, `CIS-013` **358**, `CIS-010` **347** — accreted evidence folds, several
restating the same archetype four and five times. ⛔ **A spec IS the brief** (self-sufficient, the
emitted command carries no context), so every line is loaded by the executing plan.

⇒ ⭐⭐ **This is `WS-06`'s doc-residency finding turned on the epic's own artifacts.** The epic that
measured *"≈half of every tool-result byte is plan-marshall reading its own corpus"* is itself
authoring 400-line briefs. ⛔ **No trimming was done in this pass** — the folds carry real evidence
and cutting them is a judgement call per fold, not a sweep. **Recorded as an obligation on each
spec's own outline: a spec past ~200 lines states its split verdict before scoping.**

### ⛔ Coverage of this pass — stated so it is not over-read

**Verified first-party against HEAD:** CIS-013, CIS-016 (A+B), CIS-018, plus the CIS-010/011 and
CIS-012/013 duplication pairs. **Read in full but not re-verified against source:** CIS-010, CIS-012,
CIS-014, CIS-015, CIS-017, CIS-024, CIS-029, CIS-037, CIS-038. **Not re-read this pass:** CIS-002,
CIS-004, CIS-005, CIS-006, CIS-007, CIS-019, CIS-020, CIS-022, CIS-025, CIS-026, CIS-033, CIS-034,
CIS-035, CIS-036, CIS-039–045.
⛔ **A spec absent from the first list has NOT been re-grounded** — F0's per-emit obligation stands
for it in full. **This pass narrows the risk; it does not discharge it.**


---

## Relocated: Open Defects as they stood before the ingest

Superseded by `epic.md` § Open Defects, which is re-authored against the ingest's evidence.
**Four of these were resolved by the wave and two were refuted as to cause** — the live
section states which.


- ⛔⛔⛔ **NEW 2026-08-09 (#1127) — A SECOND, INDEPENDENT WAY THE ON-MAIN EXECUTOR SILENTLY
  DISAGREES WITH MERGED SOURCE.** `generate_executor` treats *derived nothing* and *derived
  everything* as the same outcome: at the end of #1127's finalize the documented on-main
  regeneration reported `status: success` while producing a **surfaces-less executor**, and the
  plan's own headline guard **was not live on main** despite a green sync and a green regen.
  Probed live, `manage-tasks nuke` fell through to argparse *after* spawn. Recovered only by
  running the merged-source generator directly (106 surfaces / 148 scripts).
  ⛔ **The ONLY observable distinguishing the two outcomes is the ABSENCE of a surface-stats
  line, and nothing consumes absence.** ⚠ **A pre-launch pin check does not cover this** — it
  manufactures a green *finalize* over an inert guard. ⛔ **Do NOT merge it with the plugin-registry
  pin inversion**: same failure class, different mechanism, and a fix for one does not cover the
  other. → **owned by `PLAN-CIS-045`** (staged 2026-08-09).

- ⛔⛔ **NEW 2026-08-09 (#1127) — THE MERGE GATE'S REQUIRED-REVIEWER PREDICATE IS SATISFIED BY
  PARTICIPATION, AND `participated_but_empty` IS PARTICIPATION.** `pr-agent`, the **sole REQUIRED**
  bot, resolved `participated_but_empty` on **all three** passes and filed zero findings; **every
  one of the 14 actionable findings came from OPTIONAL CodeRabbit** (including three real Majors);
  `sourcery` resolved `hard_quota` on all three. The barrier passed `participation_complete: true`.
  ⇒ **A green required-bot signal carried no information about whether the diff was substantively
  reviewed.** ⚠ Also: **14 of 60 provider comment threads unresolved while our store showed 0
  pending** — a barrier reading only our own store cannot see the difference.
  ⇒ **ROUTED to `review-apparatus` as `code-intelligence-substrate-011`; NOT ours to fix.**
  ⛔ **Do not stage a CIS-side plan for it** — the required-vs-optional composition question needs
  a corpus and belongs in their quality-chain view.

- ⛔ **NEW 2026-08-09 — `4-plan` SPENDS 65.4% OF ITS BILLING WEIGHT ON CACHE *CREATION*,
  INVERTED AGAINST EVERY OTHER PHASE (6–25%).** Read/creation ratio **6.5** versus 36–180
  elsewhere: something in `4-plan` repeatedly creates large prefixes read back only ~6 times.
  ⛔ **Mechanism UNKNOWN and must be READ, not inferred from the ratio** (lesson
  `2026-08-03-19-001` — a ledger figure is a proxy and is silent about which mechanism produced
  it). **Owned by `PLAN-CIS-042` D3** (writer) with `PLAN-CIS-040` D3 as the consuming side —
  ⛔ **one writer, and it is CIS-042.** ⚠ n=1; confirm the inversion across the post-`9b689d65b`
  population before scoping a remedy.

- ⛔⛔ **NEW 2026-08-09 — `termination_cause=error` CONFLATES A CRASH WITH A PRODUCTIVE RETURN,
  AND `PLAN-CIS-035`'s HEADLINE RESTS ON THE CONFLATION.** On #1126, **five of six `error`-stamped
  self-review dispatches found 5/5/2/3/4 defects and returned for a loop-back** — the plan's most
  productive dispatches, stamped with the token reserved for a fatal error.
  `DISPATCH_TERMINATION_CAUSES` has **no member for "returned with findings"**, so the loop-back
  path has nowhere honest to land. ⇒ **CIS-035's *"32% of dispatch spend produced nothing"* is
  measured over a MIXED population and must be re-derived before any share is quoted.** Folded
  onto CIS-035 as a premise correction; the taxonomy member itself is a `manage-metrics` change —
  ⚠ **coordinate with `PLAN-CIS-037`, do not ship two writers for one vocabulary.**
  ⛔ **And widening the taxonomy fixes only half**: the `DISPATCH_TERMINATION_CAUSE` logging-gap
  rule is scoped to `metrics-dispatch-boundaries-5-execute.toon` **only**, so the 6-finalize file
  — 12 rows, 2,507,354 tokens, 51% of that plan — **is read by no rule at all.**

- ⛔ **NEW 2026-08-09 — A MESSAGE AIMED AT A RUNNING PLAN IS UNDELIVERABLE AND SILENT.** See
  § Structural Findings **F8**. It cost `PLAN-CIS-031` a deliverable that its author had been
  handed, in writing, 23 minutes into the run. → `PLAN-CIS-043` D4.

- ✅ **ANSWERED 2026-08-09 by `truthful-signals-041` — the exchange below is CLOSED; nothing owed
  back.** They **adopted `pin_content == source_content`** as a `PLAN-TRUTH-059` deliverable,
  reported as *"N of M files match; K diverge"* and **never as a boolean**, taking all three of our
  shape notes verbatim (report the population, keep both existing failure states, and ⛔ **do not
  swap the ordinal and mtime heuristics for each other** — their contradicting *each other* is
  exactly why neither can be the tie-break). **Their oracle's failure set is now four, and the
  fourth is ours**: `unmarked == [pin]` **and the pin is stale against source**.
  - ⭐ **The framing they kept, and it is the transferable part**: `unmarked == [pin]` establishes
    that the registry and the keep-set agree **with each other**, and says nothing about whether
    either agrees with the repository. **An internally-consistent pair of records, mutually
    confirming and jointly wrong** — the shape both epics keep filing against other people's
    detectors, found this time in our own oracle.
  - ⚠⚠ **AND A CORRECTION TO HOW OUR OWN MEASUREMENT MUST BE READ — THE UNMARKED SET IS NOT
    STATIONARY.** We measured `unmarked == ['0.1.1304']`; **they measured
    `unmarked == ['0.1.1240','0.1.1304']` THE SAME DAY** at the #1115 landing. **Neither reading is
    wrong — the markers are being rewritten between readings**, which `PLAN-TRUTH-049`'s
    re-grounded D-1 found independently (`0.1.1240` carried two different `.orphaned_at` values
    inside one session, then was unmarked again). ⇒ ⛔ **Our conjunct-1 pass is a SNAPSHOT, not a
    STATUS: it is evidence that the conjunct held at our sampling instant and NOT that it holds on
    this machine.** ⭐ This strengthens the content-diff conclusion rather than qualifying it — if
    the cheap orderings contradict each other **and** the set being ordered is itself moving, the
    content diff is **the only check whose answer does not depend on when you looked.**
  - ⚠ **Our 8-file delta is first-party to us and NOT re-derived by them.** It rides their spec as
    the *shape* of the defect with an explicit instruction to re-derive at D0 rather than pin a
    test to those eight filenames. ✅ Ownership unchanged: `PLAN-TRUTH-059` keeps the detector and
    our do-not-duplicate stands — ⛔ **do NOT stage a CIS-side pin detector.**

- ⛔⛔⛔ **NEW 2026-08-08, MEASURED FIRST-PARTY — THE AGREED PIN ORACLE PASSES OVER A STALE LOADER.
  This REFUTES the sufficiency of `PLAN-TRUTH-059`'s oracle and must reach that plan before it ships.**
  - **The state, measured, not inferred**: `installed_plugins.json` pins **`0.1.1304`**, and `0.1.1304`
    is **the only unmarked cache dir** ⇒ **`unmarked_dirs == [pinned_version]` HOLDS. The oracle
    reports CLEAN.**
  - ⛔ **And the pinned version is STALE against source anyway**: of **360** `.md` files under
    `marketplace/bundles/plan-marshall/skills/`, the pinned dir matches source on **352** and
    **DIVERGES ON 8**. All 8 match the **orphan-marked** `0.1.1325` instead — including
    `manage-status/SKILL.md`, `plan-retrospective/SKILL.md`, `marshall-steward/SKILL.md`,
    `manage-lessons/SKILL.md`, `plan-marshall/workflow/planning.md`, and a standards file that
    **exists in `manage-lessons/standards/` only in 1325**.
  - ⇒ ⛔ **The dir that matches source is scheduled for deletion; the dir that is pinned and loaded is
    not the newest source state.** A restart re-seats on 1304 and reproduces this exactly.
  - ⭐⭐ **WHY THE ORACLE MISSES IT, and this is the transferable part**: **neither the version ordinal
    nor the mtime orders these dirs correctly.** By ordinal `1325 > 1304`; by mtime `1304` (20:55) is
    **newer** than `1325` (20:53). ⇒ **A later-written cache dir was built from an OLDER source state**,
    so both of the cheap orderings disagree with the truth, and the only honest evidence is a
    **content diff against source**. ⛔ **`unmarked == [pin]` is a WELL-FORMEDNESS check, not a
    FRESHNESS check** — it establishes that the registry and the keep-set agree with each other, and
    says nothing about whether either agrees with the repository.
  - ⇒ **The oracle needs a second conjunct: `pin_content == source_content`.** Forwarded to
    `truthful-signals`; ⛔ **this epic still does NOT stage a detector** — the do-not-duplicate on
    `PLAN-TRUTH-059` stands, and this sharpens their plan rather than reclaiming it.
  - ✅ **REPAIRED 2026-08-08 — pin == executor == sole-unmarked == `0.1.1327`**, verified independently
    (14/14 registry entries, 0 `installPath` resolve failures, markers stable across two samples).
    The staleness described above is closed: `0.1.1327` matches source on **360/360** skill `.md` and
    its `dist-manifest.source_sha` equals repo HEAD.
  - ⛔⛔ **BUT IT RECURRED FIRST, AS INCIDENT 13, DURING THE `PLAN-CIS-031` LAUNCH — and that is the
    finding, not the repair.** State on detection: pin `1326`, executor `1327`, **`unmarked == []`**
    (the documented zero-unmarked failure shape — pin *and* executor target both GC-scheduled). The
    routine `generate_executor preflight` on a `/plan-marshall` invocation re-anchored the executor at
    a version the registry had never heard of. ⇒ **The repair holds only until the next executor
    regeneration; it is not a resolution.** 13/13 the gap contained the launching plan's own target
    surface.
  - ⭐⭐ **THE ORACLE FAILED IN BOTH DIRECTIONS WITHIN ONE HOUR, and this is what `PLAN-TRUTH-059` needs:**
    - **False PASS** — earlier the same evening `unmarked == [pin]` held while the pinned dir was
      **8 files stale** against source. A well-formedness check, not a freshness check.
    - **False FAIL** — a marker survey taken *during* an in-progress sweep read
      `unmarked == [1240, 1326, 1327]` and produced a **144-divergent-file alarm that did not exist**
      (the `1240`/`1327` markers landed seconds after the sample). ⛔ **A marker survey is a
      READ-DURING-WRITE hazard: double-sample it, seconds apart, before believing either verdict.**
    - ⇒ **The oracle needs BOTH a second conjunct (`pin_content == source_content`) AND a stability
      requirement (two agreeing samples).** Neither is in the current design. Forwarded as `-025`.
  - ⭐ **The repair recipe that worked, twice-earned — see memory `project_plugin_registry_pin_orphan_inversion`
    § REPAIR-SCRIPT DEFECT.** SPLIT the script: markers (plain cache I/O, agent-runnable) and registry
    (classifier-blocked, operator-only). **Markers FIRST** — a failed registry step then leaves
    `pin=old / unmarked=new`, and since the loader follows the *unmarked* dir it serves the correct
    content; the reverse order reproduces the incident-11 inversion. ⛔ **Never touch `.in_use`**
    (unlink raises `PermissionError` on macOS and aborted a repair mid-pass on 08-08, leaving a state
    worse than the fault). Wrap every marker mutation in `try/except OSError` and keep going.
  - ⚠ **Restart is still owed** — `/reload-plugins` does NOT re-seat skill bodies. After restarting,
    assert the **per-load** oracle: a freshly-loaded skill must announce `Base directory: …/0.1.1327/…`.
    A clean registry says nothing about what the session actually loaded (incident 8).

- ⛔⛔ **UNOWNED, ARMED, AND IT HAS A KNOWN BLAST RADIUS — the plugin registry pin now points at a
  GC-SCHEDULED directory.** After #1084's cache sync there is exactly **one** unmarked cache version,
  `0.1.1291`, matching the executor — while **`installed_plugins.json` still pins `0.1.1288`, which is
  now orphan-marked and scheduled for collection.** ⇒ **This is the `#896` failure mode armed**: the
  7-day GC deleting a version a stale executor is pinned to is precisely what produced
  `ModuleNotFoundError: plan_logging` on the nifi upgrade. ⭐ **The mechanism is finally named** —
  `sync-plugin-cache` updates the **cache and the executor** and **never the registry**, which is why
  this recurs ~daily rather than being bad luck. The registry is the plugin manager's file so the fix
  is not ours, **but the detection is, and nobody has filed it.** ⛔ **Severity is not cosmetic**:
  `truthful-signals` measured a stale `0.1.1240` read producing an `--enabled-bots` flag a `0.1.1288`
  script rejected with exit 2, which the pre-merge barrier turned into *"clean, 0 findings"* in 33
  seconds — **a pin gap manufactures false green at the merge boundary.** They logged incidents 7–9 in
  one run, including a dispatch that loaded a persona from a version **49 behind** its own envelope
  with no loader indication ⇒ **a pre-launch pin check is necessary and demonstrably NOT sufficient.**
  - ✅ **NO LONGER UNOWNED as of 2026-08-08 — `truthful-signals` staged the detector as
    `PLAN-TRUTH-059`, and we are NOT writing a second one.** They asked us to check before staging our
    own precisely so the detector is not built twice; checked, and nothing in our queue owns it.
    ⛔ **Do not stage a CIS-side pin detector.** Their shape, recorded so we can consume it: scope is
    *noticing and refusing to proceed*, never writing the registry (it is the plugin manager's file);
    the oracle is **`unmarked_dirs == [pinned_version]`** read from `installed_plugins.json`, with
    **both** failure states in scope — pin-orphan-marked-while-newer-unmarked, **and `unmarked == []`,
    which is a failure state and not a pass**; ⛔ **counting executor path-versions does NOT detect it**
    (every incident had a clean executor and a stale loader); and it is a **mid-run** assertion,
    because our § 6 mechanism and their incidents 7–9 together prove a pre-launch check is necessary
    and not sufficient. ⚠ Their D0 verifies the `sync-plugin-cache` mechanism **by symbol** rather than
    inheriting our framing — correct, since ours is a stated conclusion from two observers, not a code
    read. **The epic keeps this entry open as the standing operational risk; the detector work is
    theirs.**

- ⚠ **UNOWNED — `search --content`'s `count` does not say which question it answers.** Probed live on
  merged `main`: three distinct files returned as **six rows**, each once per attributed module
  (`default` and `plan-marshall`). A caller reading `count` as *"files matching"* is wrong by the
  module-attribution factor. ⭐ **Not necessarily a behaviour defect** — per-module rows may be exactly
  what a module-scoped caller wants — but the field name does not distinguish rows from files, and
  this epic's whole thesis is that an unlabelled count is a confident number with a hidden caveat.
  **Same dual-attribution shape as the CIS-027 29-vs-24 reconciliation, which was labelled; this is
  not.** Fix is a labelled field or a documented contract.
  - ⭐ **SECOND SIGHTING 2026-08-08, independent observer, and it now has a companion defect —
    NOW OWNED by PLAN-CIS-002.** `review-apparatus` hit the same shape from their own tree
    (`count: 2` for **one** file, attributed under `default` and `plan-marshall`; per-row
    `match_count` was correct). ⇒ Two independent observers, two different call sites, same
    row-vs-file conflation — this is a contract defect, not a probe artifact.
  - ⛔ **The companion defect is worse and is CORROBORATED FIRST-PARTY**: `search --content` has **no
    `--ignore-case`**, compiles with `re.MULTILINE` only
    (`manage-architecture/scripts/_cmd_client_handlers.py:1000`), and `--literal` applies `re.escape`
    — so **verbatim matching and case-insensitivity are mutually exclusive by construction**, and the
    inline-`(?i)` escape hatch is undocumented in `--help` (`architecture.py:268`). ⛔ **It has already
    shipped a false residual-zero into merged main** (`review-apparatus`, PLAN-PR-009:
    `test_ci_base.py:548,561,569` — sweeps returned 0 for phrasings live in the tree).
    **This matters beyond convenience: `architecture search --content` is the ONLY content-sweep
    primitive a dispatched leaf has** (Grep/Glob revoked at runtime, Bash `grep`/`find` hook-blocked),
    so its measurement defects are unavoidable rather than avoidable. Both halves folded into
    **PLAN-CIS-002** 2026-08-08; this entry stays until that plan lands.

- ⚠ **RESOLVED-BY-TRIAGE, kept visible — the 7 misrouted lessons.** The CIS-001 retrospective was
  dispatched with `orchestrated: false` **without resolving it**, so lessons `2026-08-03-14-001…007`
  went to the **global store** instead of arriving here as `candidate-lesson` messages. ⭐ **This is
  `orchestrator inbox detect` existing and not being called** — the single detection seam was
  bypassed, not wrong. **Discharged 2026-08-03 by triaging them where they sat** rather than
  relocating them: all seven are substantive and correctly shaped as lessons, so they stay in the
  corpus; five were folded into specs (CIS-031 D5, CIS-020 D8, CIS-016 member E, CIS-012, CIS-011 D9),
  one was already forwarded to `review-apparatus`, one needs no epic work. ⛔ **The dispatch defect
  itself is NOT fixed** — the next orchestrated plan will do the same thing.

> ✅ **The next three defects were UNOWNED for about an hour and are now OWNED by `PLAN-CIS-034`**
> (staged 2026-08-03 in the same drain, after `truthful-signals-031` proposed the ownership split
> that gave them a home). They are kept here in full because CIS-034's spec cites them and because
> **all three are live in merged `main` until it lands.**

- ⛔⛔ **→ CIS-034 R1 — `lessons-housekeeping` is sandwiched from the OTHER side, and
  the post-run band CANNOT absorb it.** OBSERVED first-party 2026-08-03 on merged `main`:
  `project:finalize-step-lessons-housekeeping` declares `order: 4` and `mutates_source: true`, so it
  runs in the SETTLE band **991 orders before** `plan-marshall:plan-retrospective` (995), whose
  `quality-verification-report.md` it consumes. Its own log says so: *"quality-verification-report.md
  unavailable (retrospective runs at order 995, after this settle-band step) … proceeded on
  request.md plus the branch diff"*. ⛔ **#1080 relocated the post-run band DOWNWARD only** —
  `truthful-signals` predicted exactly this and asked us to confirm; **the answer sent back was NO.**
  ⭐ **The part neither epic had: band membership REQUIRES `mutates_source: false`, and this step
  declares `true`.** Relocating it into the post-merge band would put a declared mutator after the
  merge gate with no push path — the very defect `post_run_source_guard` was added to detect. ⇒ **A
  structural tension, not a missed `order:` edit.** ⛔ **A remedy that only moves it later leaves the
  first consumer; one that only moves it earlier breaks the second.** Unstaged; `truthful-signals`
  is expecting a report when it is staged.
- ⛔ **→ CIS-034 R2 — `record-metrics` (998) still runs AFTER `plan-retrospective`
  (995).** Landing obligation 3 on #1080 did **not** close: the branch's change to `record-metrics.md`
  is the single added line `post_run_review: true`, which does not close the accumulator first. ⇒ The
  #1079 shape survives — the largest phase of a run is read as zero at exactly the moment the
  retrospective samples it (measured there as a **2.17× understatement** of the Total). ⭐ **The
  partiality machinery still labels it correctly**, so this produces an honest FLOOR rather than a
  false total — which is why it is a defect and not a falsehood. ⚠ **PLAN-CIS-030's surface sits
  directly on top of this**; settle it at outline rather than measuring around it.
- ⛔ **→ CIS-034 R3 — "capture, don't derive": the footprint is still never captured while true.** #1080
  correctly removed `base..HEAD` from the fallback chain (three-dot live diff → legacy
  `references.modified_files` → `FOOTPRINT_UNRESOLVED`, never a silent empty set). ⛔ **But the
  recommended tier 2 — the plan's own merge commit recorded at `branch-cleanup` — was NOT
  implemented**, and the shipped legacy key is scoped by its own docstring to *"archived plans created
  before the ledger was removed"*. ⇒ **For every NEW plan the archived path resolves to UNRESOLVED
  permanently.** The verdict is now **honest but permanently unmeasurable** — a strict improvement
  over a confident wrong answer, and **not the same as a working measurement.** The filer's remedy
  (have `branch-cleanup` or `push` persist `realized_files` / `work/footprint.toon` as a
  deterministic side-effect) is agreed and unstaged.
- ⛔ **UNOWNED, OPERATOR DECISION — a `bug_fix` touching production code shipped with NO Sonar
  roundtrip.** OBSERVED first-party on #1079: `execution_profile=standard` prunes every `lane: full`
  step by design, so `sonar-roundtrip` was dropped by the **posture cutoff**, not by any footprint
  predicate. ⭐ **This is the configuration working as specified, not a defect in the machinery** —
  it is recorded here because the *consequence* is an operator call: whether `standard` should keep
  Sonar for `bug_fix` changes that touch production code. ⚠ **Do not fold this into PLAN-CIS-016** —
  CIS-016's folded item D is the *checker* misattributing this drop, which is a different defect
  with a different fix. Two sibling steps (`finalize-step-security-audit`, `adr-propose`) were
  dropped by the same pass and correctly went unflagged.
- ⚠ **RECORDED, NOT OWNED — the store still contains ZERO `derived.json` files**, while
  `_architecture_core.py` treats a per-module `derived.json` as the on-disk existence marker under
  the on-demand crawl model. ⭐ **DOWNGRADED 2026-08-02 from suspect to curiosity**: the founding
  zero-edge defect is now closed **without** CIS-027 needing to touch this, so the absence is **not**
  its cause. That elimination is the whole of what is settled — whether it is benign or a second
  latent problem is still open, and it belongs to **PLAN-CIS-029**'s concept-model work.

- ✅ **`architecture find` returns a ROW count, not a FILE count — NOW OWNED, mechanism identified
  2026-08-01.** Reproduced at HEAD: `--pattern "*code-intelligence*"` returns `count: 2` for **one**
  physical file, indexed as `default`/`doc` and `documentation`/`doc`. ⭐ **The mechanism is
  root-crawl-plus-domain-claim overlap, not a catch-all bug**: `default` is an *alias for the real
  root module* (`_cmd_client_query.py`:620–627), so its inventory legitimately holds repo-root
  files, and `pm-documents`' `documentation` module claims the same `doc/**`. ⛔ **The old
  "verify whether dual-module indexing predates #1056" note is RETIRED — it does not depend on
  #1056 at all.** → **PLAN-CIS-024 D2** owns the de-duplication.
- ⛔ **UNOWNED — ADR-007's survivor sweep is Accepted but UNBUILT, and it is the operator's
  reference-refactoring ask.** ADR-007 enumerates four survivor classes — deleted symbol, deleted
  path, deleted heading/`xref` anchor, renamed identifier — and states the deleted-symbol class has
  *"no dedicated whole-surface detector"*. ⭐ **All four map one-to-one onto LSP `references` /
  `documentLink` / `rename`+`WorkspaceEdit`**, so ADR-007's unbuilt detector and the LSP surface are
  the same capability approached from two directions. ⚠ **Deliberately NOT staged as of 2026-08-01**
  — the operator confirmed staging for PLAN-CIS-023/024/025/026 only. This entry exists so the ask
  is not lost. Its natural home is a new workstream sequenced AFTER a symbol source exists
  (PLAN-CIS-026 or the `marshalld`-hosted live pass-through), so it consumes `references`/`rename`
  rather than reimplementing them. Its doc-surface half is partially served by **PLAN-CIS-024 D4**
  (xref resolution → the deleted-heading class).
- ⛔ **UNOWNED — the `*_reasoning` field family conflates a source citation with an inference.**
  OBSERVED 2026-08-02 in `.plan/project-architecture/plan-marshall/enriched.json`:
  `responsibility_reasoning` **cites** (`"source: marketplace/bundles/plan-marshall/README.md
  (Purpose + Components sections)"`) while `purpose_reasoning` **argues** (`"Plugin bundle exposing
  skills/agents/commands; no runtime entrypoint but is consumed by…"`). One naming convention,
  two epistemic classes, no way for a consumer to tell them apart — the store-layer instance of the
  epic's own OBSERVED-vs-HYPOTHESIS discipline. ⭐ OKF v0.2 separates exactly these into `sources`
  (provenance, with `author`/`last_modified` signals) and `generated` (how the content was
  produced). ⚠ **Deliberately OUT of PLAN-CIS-029's scope** — CIS-029 adds the provenance
  *container*; splitting the existing prose is a separate migration with its own re-derivation
  cost. Its natural home is a follow-on to CIS-029, once `generated` exists to migrate into.
- ⚠ **`plan-retrospective`'s invariant aspect has three names** — "Invariant outcomes" in the SKILL
  table, `invariant-check-summary.md` as the reference file, `invariant-summary` as the only key the
  registry accepts. Registering by the documented label fails live. ⭐ **Now adjacent to PLAN-CIS-020**,
  which owns the neighbouring registry/render contract in the same bundle — pick it up there if that
  plan's outline lands in the same file.

**Retired 2026-07-30 by the PLAN-11 landing (#1063):**

- ✅ **`check-manifest-consistency` rule M3 vacuous guard** — no longer unowned; **moved into
  PLAN-CIS-019 as D3**, the same file it lives in. ⛔ Do not re-add it to PLAN-CIS-016.
- ✅ **`audit.py`'s `write_persisted_report` derives its path from `Path.cwd()`** — **the premise was
  REFUTED, not merely fixed.** `write_persisted_report` takes `repo_root` as a parameter and never
  called `Path.cwd()`; the sole defect site was `main()`, and that one value fed **six** consumers.
  Fixed in #1063 by `_resolve_repo_root()` (`audit.py:667`, consumed at `:7259`). ⭐ Kept visible as a
  retirement rather than deleted, because the *shape* of the error — the reported location being a
  sample of the defect rather than the defect — is standing rule 4 and is folded into PLAN-CIS-015.


---

## Relocated: Watches as they stood before the ingest

Superseded by `epic.md` § Watches.


- ⭐ **OWED ARCHITECTURE HINT, DELIBERATELY NOT EXECUTED HERE (2026-08-09, from #1127 inbox `-009`).**
  A review bot re-litigated two decisions #1127 had already settled with evidence, because **the
  rationale lived only in the Q-Gate finding store, where the bot cannot read it** — `c80c7d`
  proposed deriving the executor's universal-flag accept-set (reversing `c32ae7`, which settled the
  mirror because the generated executor dispatches before any shared dir is on `sys.path`), and
  `b89631` proposed a wall-clock budget for the edit-time derivation (reversing `27509a`, because a
  budget makes a build-gating verdict host-speed-dependent by silently shrinking the accept-set).
  Both observations were correct; both remedies were wrong for reasons already written down.
  - **Hint text, verbatim, for whichever plan lands it**: *"When a plan settles a design question
    deliberately and records the rationale only in its Q-Gate finding store or decision log, an
    automated reviewer cannot see it and will propose reversing it. Surface a settled decision where
    the reviewer reads — the code comment or the doc the decision governs — so the review round
    spends itself on new ground instead of re-arguing closed ground."*
  - Target: `architecture enrich insight --module default` (cross-cutting; not attributable to one
    module). Recurrence 4, above the `preference_min_recurrence: 2` threshold.
  - ⛔ **NOT run by the orchestrator**: `architecture enrich` post-merge writes tracked source onto
    `main` with **no push path** (the #990 shape). **A plan must land it, not a ledger pass.**

- ⚠ **WATCH, do NOT read as a regression (2026-08-09).** #1127's `pre-submission-self-review` ran
  **six rounds for 1,008,012 tokens ≈ 60% of its 6-finalize spend** — the same proportion
  `PLAN-CIS-031` measured *before* its delta-scoping landed, on a plan that ran **after** it.
  ⛔ **This is NOT evidence CIS-031 failed**: #1127's rounds were loop-back-driven with a
  **self-seeding doc-claim half**, which is a different mechanism from the unscoped re-sweep CIS-031
  fixed. ⭐ **It IS the second sighting of self-seeding** (first: #1126's four failed corrections),
  which is what makes it a pattern → folded to `PLAN-CIS-043` D5. **Observable to settle it:
  `PLAN-CIS-040` D1 should compare per-round scope size, not per-round token count** — the delta
  scoping shows up in the former and is invisible in the latter.

- ⛔⛔ **BINDING ON MY OWN EMIT DISCIPLINE — a spec's assertion about its write surface is NOT evidence
  for a disjointness call. SECOND FIRING, 2026-08-03.** `PLAN-45`'s spec asserted **no production or
  test source change**; its realized footprint carried a one-line javadoc edit in
  `integration-tests/src/test/java/**`, which is `PLAN-34`'s **declared write surface**. The pairing
  was made against the assertion and the assertion did not hold. ⭐ **Consequences were mild only by
  luck** — the edit is auto-mergeable and both worktrees already carried the file. **The same
  mechanism with a non-trivial edit is a cross-plan rebase conflict discovered at finalize.**
  ⇒ ⛔ **A spec is authored BEFORE the work, so its write-surface statement is a PREDICTION consumed
  as a measurement** — and a *negative* assertion (*"touches no source"*) is the weakest form of all,
  unfalsifiable at emit and defeated by one incidental edit. **Rank declared surfaces below anything
  derived; record the BASIS of each pairing (declared vs derived) so a later collision identifies
  which kind of evidence failed.** ⭐ **And when a plan genuinely must not touch source, that has to be
  enforced by the deliverable excluding source edits — not requested in prose.** Filed as lesson
  `2026-08-03-18-001`. **This governs every emit I make at `parallelization_scope > 1`.**

- ⭐⭐ **UNOWNED — TWO BUILD PATHS, AND THE EXPENSIVE ONE IS FOOTPRINT-BLIND.** Six whole-tree Maven
  runs on `plan-45` (≈30 min). ⛔ **CORRECTED the same day** — the first version of this Watch blamed
  module selection and said the cost was superlinear. **Both were wrong.**
  ⇒ ✅ **The resolver is fine and is not involved**: `marshal.json`'s `build.map` is a glob→build_class
  table applied to the actual diff, and the 1.5s / 18.4s per-module runs prove it **is wired and ran**
  on the phase-5 per-deliverable path.
  ⇒ ⭐⭐ **The six expensive runs never touched it.** They are `default:pre-push-quality-gate`, a
  whole-tree step building `[1/5]…[5/5]` every time that **does not consult the footprint** and would
  have run identically **on a pure `.adoc` change**. The javadoc line was irrelevant to it.
  ⇒ **Cost is LINEAR in loop-backs** (3 executions ≈10.5 min each: 1 initial + 2 loop-backs ≈ +21
  min), and the ×2 per execution is the project's **mandated** two-command Pre-Commit Process
  (`-Ppre-commit` javadoc jars + plain `verify`) — **not waste, do not target it.**
  ⭐ **The ask is now cheap and concrete**: wire the *existing, proven* `build.map` classifier to the
  pre-push gate as a second consumer, and settle whether a doc-only loop-back diff needs a full
  re-run. Folded into `PLAN-CIS-031` D6; the gate's owning surface may still be the build layer rather
  than this epic.

- ⭐⭐ **SETTLED 2026-08-03, FIRST-PARTY — THE #1069 EFFORT RAISE PAID FOR ITSELF, AND THIS IS THE
  BINDING ANTI-GOAL FOR THE WHOLE TOKEN PROGRAMME.** PR #1069 (`2d0229d1c`, merged
  `2026-07-30T19:51:10Z`) raised `phase-6-finalize.effort.default` **level-3 → level-5**,
  `phase-5-execute.effort.default` **level-4 → level-5**, `phase-3-outline` **level-4 → level-5**
  (plus two `verification-feedback` keys and `post-run-review`). Splitting the archived corpus at that
  instant on each plan's own `[1-init] start_time` — **39 before / 12 after / 0 spanning**.

  ⚠ **FIGURES CORRECTED 2026-08-03. The first version of this Watch was computed over three finding
  files named from memory out of SIXTEEN that exist, and the two it omitted were
  `qgate-2-refine.jsonl` and `qgate-4-plan.jsonl` — the CONTROL GROUP.** Corrected below; the
  superseded numbers (yield 1.88×, `fixed` 34%→70%) must not be re-quoted from anywhere.

  **COST — attribution rests on a CONTROL and is solid.** Median total **3.09M → 4.15M (1.34×)**.
  Raised phases: 3-outline 1.38×, 5-execute **1.77×**, 6-finalize 1.39×. **Controls: 1-init 0.89×,
  2-refine 1.11×, 4-plan 0.97×.** ⭐ Every raised phase rose; no control did. Share-of-total agrees
  independently (raised phases grew their share, controls shrank theirs).

  **YIELD — real, but weaker and only clean on the right statistic.** All findings per plan
  **26.15 → 43.92 (1.68×)** against 1.34× cost, so **cost per finding still improves**; external
  `pr-comment` yield **FELL 5.28 → 4.50** (4.18 excluding #1080), a shift-left signature.
  ⛔ **On MEAN findings the control `4-plan` rose 1.73× with effort unchanged and cost flat — so the
  per-phase attribution is WITHDRAWN on the mean.**

  ⭐⭐ **On the ZERO RATE it separates cleanly, and that is the load-bearing result**: raised phases
  3-outline **18%→0%**, 5-execute **77%→58%**, 6-finalize **64%→17%**; controls 2-refine
  **69%→83%** and 4-plan **54%→58%** both went the OTHER way. ⇒ The old zeros were
  under-examination — this epic's own archetype living in our quality gates — and it is now
  control-backed. ⭐ **It also explains the anomaly**: `4-plan`'s mean rose while its zero rate ALSO
  rose, which is only possible if the extra findings concentrate in a few plans. **The mean was
  outlier-contaminated; the zero rate was not.**
  ⇒ ⛔ **STANDING REPORTING RULE: to test whether a detector's behaviour changed, use the
  outlier-robust ZERO RATE, never a mean over finding counts — a mean will manufacture an effect in a
  control group.**

  ⛔⛔ **Lowering effort levels is NOT a sanctioned token saving** — it is the one measured
  intervention that improves the token number while degrading detection, i.e. it would make our own
  instrument report success for a quality regression. **The legitimate target is bytes that buy
  nothing — redundant exploration, re-read documents, unscoped re-sweeps — never examination depth.**

  ⚠ **Limits, not to be laundered away**: n=12 vs 39; `lessons-capture` lane went `minimal` → `off`
  in the SAME commit, making the finalize **cost** ratio a two-variable cut whose 1.39× is an
  under-estimate (5-execute's 1.77× is the clean figure); the resolution-mix "noise test" is much
  softer over the full population (`fixed` **29%→36%**, not 34%→70%) **and 39% of before-period
  findings carry `resolution: <unset>`**, so part of it is an instrumentation shift; and **1,176 of
  1,547 findings carry NO `phase` field**, so every per-phase figure here covers under a quarter of
  the corpus. → Folded into **PLAN-CIS-030** as a D1 partition obligation, the zero-rate reporting
  rule, and an anti-goal. Sent to `truthful-signals` as `-018`, corrected by `-019`, closed by `-020`.

- ⭐ **VERIFY ON THE NEXT PLAN COMPOSED AFTER #1080 — the stale-cache false verdict may have closed
  as a SIDE EFFECT.** #1080 moved `plan-retrospective` to `order: 995`, which now sorts it **after**
  `project:finalize-step-sync-plugin-cache` (85). ⇒ The retrospective should now execute the
  **merged** aspect scripts rather than the pre-merge cached copies. ⛔ **This is a derived
  expectation, NOT an observation**, and by the epic's own non-self-exercisability rule
  (lesson `2026-08-03-06-004`) it **cannot** be confirmed from #1080's own run. **The observable**:
  `check-artifact-consistency` reports `inconclusive`, not `fail — Recall 0%`. ⚠ **A correction worth
  keeping**: this orchestrator briefly refuted the stale-cache mechanism by reading the `order:`
  values on post-merge `main` — that is the order the plan **installed**, not the order it **ran**
  (runtime was `branch-cleanup 70 → plan-retrospective → deploy-target 81 → sync-plugin-cache 85`).
  **When diagnosing a run, read the order from the run's manifest or step log, never from the tree
  the run produced.**

- ⛔ **BINDING ON PLAN-CIS-030 AND ON EVERY TOKEN FIGURE THIS EPIC QUOTES — a closed phase row is
  never re-opened on loop-back.** From `truthful-signals-029` § 4, first-party on #1078:
  `[5-execute]` closed at **162,906** tokens, then the plan re-entered it **three more times** for a
  further **758,059 tokens that no phase row absorbed** — an **82% under-count** — while the
  partiality marker named only `6-finalize`. ⭐ **The partiality contract keys "recorded" off the
  presence of an `end_time`, and a re-entered phase HAS one, so it passes the completeness test while
  being wrong.** ⇒ ⛔ **Treat "~99% of billing weight is context" as durable and EVERY per-phase share
  as suspect** — composition is a ratio over components a missing row drops together; a per-phase
  ranking is not, and a loop-back re-enters an EARLIER phase, so `6-finalize 49.4%` is likely an
  over-estimate. ⭐ **Corroborated first-party on #1080**: 13 self-review rounds across three
  loop-back waves, `6-finalize` (5.6M) outspending `5-execute`. **A thrice-re-entered execute phase
  is the normal shape of a plan-marshall run, not an edge case.**

- ⚠ **SUPPORTING DATUM, route rather than absorb — `scope_estimate` was TWO BANDS LOW on #1080** and
  it is a live input to the `scope_gated_finalize` pre-filter, which **attempted to drop
  `plan-marshall:plan-retrospective` from that plan's own manifest** — on the run that produced 19
  self-review findings and two near-miss vacuous guards. It survived **only on declared-lane
  immunity**. → Related to `PLAN-CIS-008`; recorded in `PLAN-CIS-031`'s Claim Labels, deliberately
  **not absorbed** by either.

- ⛔ **OPERATIONAL, ORCHESTRATOR-FACING — `ci pr view --pr-number` DOES NOT EXIST (exit 2), while the
  surviving `--head` help text still names it as "an alternative to `--pr-number`".** Reproduced
  independently by this orchestrator (2026-08-02) **and** by `review-apparatus`. ⭐ **Use
  `ci pr view --head {branch}`.** ⛔⛔ **The consequence is the dangerous part and it is this epic's
  exact subject: a merge-queue waiter on #1077 polled the invalid-flag command for 30 minutes and
  read the errors as "not merged yet" — the PR had ALREADY MERGED.** An **erroring poll is
  indistinguishable from a negative poll**, which is the vacuous-guard archetype relocated from
  detectors to waiters. → Owned by `review-apparatus` **PLAN-PR-017**, which derives the population
  of doc-prescribed-but-undeclared invocations rather than patching the three known sites.
  ⭐ **Three sites found by accident implies more found on purpose.**

- ➜ **DELEGATED to `review-apparatus` 2026-07-30** (`code-intelligence-substrate-001.md`): the
  review-coverage watch — five distinct participation-failure modes observed across five PRs in one
  day. Removed from this ledger rather than copied, per the three-way routing rule. It overlaps their
  `PLAN-PR-005`/`006`/`007`; the mode we could not map onto those (partial participation across two
  HEADs, where the *merged* diff went unreviewed) was called out for them to check.
- ⛔ **FINALIZE ABOVE 40% FOR A FOURTH CONSECUTIVE LANDING, WITH A RISING SLOPE — this is no longer
  a watch awaiting data.** 42% → 48% (PLAN-11) → **52% (PLAN-CIS-003: 4.9 M total, 2.5 M in
  finalize, 12h50m wall / 5h19m worked)**. Four points trending upward is a trend line. → **PLAN-CIS-008
  and PLAN-CIS-014 are the owners and should be prioritised accordingly.** ⚠ Part of the #1074 cost was
  self-inflicted and is recorded as such by the plan itself: it babysat a merge-lock block instead of
  arming an available Monitor, and three monitor predicates then fired on non-events by gating on
  *absence-of-known-in-progress-markers* rather than the producer's **terminal marker**. ⭐ Gating on
  absence-of-a-negative instead of presence-of-the-terminal-signal is a reusable defect shape.
- ⭐ **NEW ARCHETYPE, two independent sightings in two consecutive landings — a step scheduled where
  its input does not exist.** (1) PLAN-CIS-023: `branch-cleanup` deletes the worktree
  `affected_files_recall` derives its footprint from, scoring **0% against a 21/21 exact footprint** —
  vacuous on *every* standard-posture plan. (2) PLAN-CIS-003: `review-retrospective.md` shipped a
  **falsehood**, written at `order: 50` *before* the review it claimed to measure. **Same shape as
  PLAN-10's finalize-ordering defect.** Three sightings across the epic makes this a class, not
  incidents. → ✅ **PARTLY DISCHARGED by PLAN-CIS-028 / #1080 (shipped 08-03).** **FIFTH sighting**
  came from #1079, where `affected_files_recall` again reported **0% against an exact 8/8 footprint**.
  ⛔ **The class is NOT closed and the watch stays open.** What #1080 fixed is the **reporting**: an
  unresolvable footprint now yields `inconclusive` via a stated `FOOTPRINT_UNRESOLVED` sentinel, never
  a confident `0%`. What it did **not** fix is the **ordering**, in three places now recorded as Open
  Defects: `record-metrics` (998) after `plan-retrospective` (995); `lessons-housekeeping` (4) before
  the retrospective it consumes; and the footprint still derived at read time rather than captured
  while true. ⭐ **Honest-but-unmeasurable is a strict improvement over confidently-wrong and is not
  the same as measured** — do not let the sentinel be read as the class closing.
- ⭐ **NEW 2026-08-02 — the token measurement itself, and it is now a plan.** `truthful-signals`
  reports (n=47 archived plans, ⚠ **second-hand, one pass by one reader**) that **~99% of billing
  weight is context, not generation** — `cache_read` 76.1%, `cache_creation` 22.8%, **`output` 1.1%**
  — and that **exploration is 76–85% of tool-result bytes in every phase from 2-refine onward**,
  with **6-finalize the LARGEST exploration consumer** (≈133 calls/plan). ⭐ **They predicted the
  opposite and were refuted by measuring**, which is the strongest reason to take the rest
  seriously and to re-derive it anyway. The compounding mechanism is the load-bearing part: a byte
  enters once at **1.25×** and is re-read every subsequent turn at **0.1×**, so **the cost of a byte
  is a function of WHEN it enters context, not just its size.** → **PLAN-CIS-030** owns the
  attribution instrumentation. ⛔ **Watch, not conclusion**: that exploration bytes *cause* the
  `cache_read` weight is a HYPOTHESIS its own author flags as unestablished.
- ⚠ **WATCH — a two-reviewer comparison is being reported as a review retrospective.** Sourcery was
  **absent from #1079** (CodeRabbit + pr-agent only), consistent with the standing `review-apparatus`
  concern. Forwarded to them with the `--enabled-bots` finding rather than tracked here; recorded so
  the next landing's reviewer count is read as a **sample of participation, not a roster**.
- ⚠ **A refutation is itself capable of being wrong — recorded as the counterweight to the
  celebrated one.** PLAN-CIS-023's triage correctly refuted a CodeRabbit claim by probing the live
  verb. One landing later, PLAN-CIS-003's triage refuted finding `cd99e7` **on a false premise**,
  citing a q-gate resolution that argues *against* the refutation; honest score restated as
  4 confirmed / 1 refuted / 1 refuted-but-mostly-right, and the residual doc drift **shipped**.
  ⛔ **Do not read "we refute bot findings now" as a maturity marker** — refuting is correct practice
  and needs the same evidence discipline as accepting.
- ⚠ **Token cost per plan is running well above anchor — now THREE data points, and finalize is the
  consistent driver.** One landing cost 3.4 M tokens for a `single_module bug_fix` (2.4× anchor,
  finalize alone 42 %); another had **no applicable anchor at all**; PLAN-11 (#1063) cost **3.98 M for
  three deliverables, with `6-finalize` alone at 1.90 M = 48 %**. ⭐ Two consecutive landings with
  finalize above 40 % is a trend line, not two anecdotes — but **three points is still not a
  population**; do not quote it as a rate. → PLAN-CIS-008 and PLAN-CIS-014 are the owners; this watch
  tracks whether the trend moves after they land.
- ⚠ **Wall-clock vastly exceeds worked time and nothing explains the gap.** PLAN-11: 16h6m wall against
  4h27m worked (3.6×), with `5-execute` alone at 10h30m wall for 1h20m worked (**8×**). Idle, not
  compute. No owner — recorded because a cost conversation that only counts tokens will misread it.
- ✅ **RETIRED 2026-08-01 — "LSP is per-language, price the markdown/AsciiDoc blind spot".** The
  objection was **wrongly worded and would have argued against LSP for the wrong reason.** It holds
  only for *reusing off-the-shelf* language servers; we would **write** the server, so it indexes
  whatever we teach it, and `documentLink` is the best available fit for `xref:`/markdown-link
  integrity. ⚠ **The residual true half**: per-language cost is real at **Tier 2** (one parser per
  language) — keep that as an argument against chasing broad Tier 2 coverage, **not** against the
  LSP shape at Tier 0/1. See the Direction table's tier split.
- ✅ **Surface-disjointness call CONFIRMED CORRECT on the first concurrent pair — BOTH have now landed.**
  PLAN-11 (project auditor `audit.py`) and PLAN-02 (`extension-api` / `manage-architecture`) ran
  together under `parallelization_scope = 2` with **zero observed collision** — no rebase conflicts, no
  re-verify signals between them. ⚠ One good pairing is not a validated method; keep recording both
  outcomes.
- ⛔ **NEW — the disjointness model does not model shared NAMESPACES, and this cost 90 minutes.**
  PLAN-02's merge aborted one minute before completing because upstream #1066 had claimed
  `doc/adr/012` while PLAN-02 held its own. `baseline-reconcile` reported `no_overlap` and the rebase
  applied cleanly — **both correct, and both measuring bytes rather than meaning.** The collision was
  cross-PR *and* cross-epic, so no per-epic surface table could have caught it. Delegated to
  `truthful-signals`, but recorded here because **the same exposure exists for lesson ids
  (`YYYY-MM-DD-HH-NNN`) whenever two plans finalize in the same hour** — which this epic does routinely.
- ⭐ **Sourcery has TWO refusal modes, and this epic has been recording the wrong one.** Prior landings
  attributed its refusals to the weekly quota. On #1067 the cause was the **150 000-diff-character size
  cap**, stated twice in PLAN-02's `decision.log` and explicitly contrasted with a quota there.
  ⛔ **Both modes are real — the point is that they are not interchangeable.** A weekly-quota refusal
  self-clears by waiting; a size-cap refusal **never** does, so it will refuse every PR of that size
  forever and the only remedies are splitting the PR or accepting the gap knowingly. ⚠ **Do not read
  this as "Sourcery has no quota mode"** — read it as *the recorded cause must name which mode fired*,
  because the remediation inverts. Two of this epic's four landings were large enough to trip the cap.

- ⭐ **NEW 2026-08-09 — TWO SELF-REVIEW CANDIDATE CLASSES FORWARDED BY `review-apparatus` (`-007`),
  HELD AS A WATCH RATHER THAN STAGED, AND THE SIZING GATE IS THE REASON.** Provenance is
  **third-hand**: first-party to `PLAN-PR-022` (#1130), forwarded by `review-apparatus` who state
  they did **not** re-derive it. ⛔ **Re-derived here, and the forwarded instance is REFUTED as
  live**: `commands/tools-sync-agents-file.md` **:28–42** is now *"Step 2 — Inspect Existing State
  (case-EXACT)"* — it forbids an existence check by name, lists with `Glob '*.md'`, compares
  basenames byte-for-byte, tabulates the three outcomes, performs the two-hop `git mv`, and **:76–77**
  asserts both post-conditions. **The remedy the message describes as "for reference" is the
  shipped state.** ⇒ nothing is owed on the instance; only the *class* is live.
  - **Class 1 — a case-exact filename question asked with an existence check.** Deterministically
    detectable, single remedy shape. ⚠ **Population unknown: n=1 known instance, and it is already
    fixed.**
  - **Class 2 — cross-representation sweep** (a change whose docstring states a portability hazard
    should have its markdown surface swept for the same hazard). ⚠ **The sibling itself flags it as
    a broad trigger that could be noisy and asks that its rate be derived before a detector is
    pinned to it.** We agree.
  - ⛔ **NOT folded into `PLAN-CIS-043`.** That spec is already at **five** deliverables with a
    split evaluation explicitly owed at outline; a sixth breaches the scope-bloat guard on a spec
    already sitting at its edge. When either class is sized, its home is the
    `ext-self-review-plan-marshall` registry + detectors — the CIS-043 / CIS-045 serialization
    class — and it should ride whichever of those is being scoped, not a new plan.
  - ⭐ **The standing rule is what decides this: SIZE IT BEFORE STAGING IT.** The cache-prefix
    rejection established that a real structural defect can be quantitatively negligible. A
    candidate class whose only known instance is already remediated has not been sized, and
    staging it would be the same error in the other direction.
  - ✅ **Recorded so it is not re-litigated**: the sibling **accepts F8** (a message aimed at a
    running plan has no reader) and **independently endorses `PLAN-CIS-043` D4's deliberate
    scope-out of a mid-run delivery channel**. That is concurrence from the epic that raised the
    requirement, not a new constraint.


---

## Relocated: settled Open Decisions

The two decisions closed on 2026-08-09 — the `in_total` direction and the cache-prefix
rejection — with the reasoning that closed them. **Both are recorded so they are not
re-derived as open options.** The live § Open Decisions keeps only what is still open.


- ⭐ **Should the phase-5 chain tail be re-ordered to verify ONCE, after the Step 10a commit?** Today
  the tail is verify → commit → verify-again, and the second verify is **structurally unavoidable**:
  the Step 10a commit changes the `worktree_sha`, so `pre-commit-verify-freshness` correctly reports
  stale every time. Re-ordering to commit-then-verify would remove **one full verify per chain tail**.
  ⚠ Raised by `audit-report-path-ignores-plan-dir-004`; recorded here so the epic decides once rather
  than each plan re-discovering the cost. ⛔ It is a design question about step ordering, **not** a
  defect — the freshness gate is behaving correctly and must not be weakened (see the fold in
  `PLAN-CIS-017`). Cost impact belongs with `PLAN-CIS-014` / `PLAN-CIS-008`.

- ✅ **DECIDED 2026-08-09 BY THE OPERATOR — ADD THE TWO CONSUMING CHECKS.** `PLAN-CIS-043` D2 no
  longer escalates: it **adds a consuming check for `duplicate_claimable_keys` (N21) and
  `discard_without_report` (N22)**, so `counts.total`, the Step 1b dispatch gate, and the
  *"{N} candidates examined"* verdict stay at their current magnitude **and become honest**.
  ⛔ **The direction that was NOT taken — dropping `in_total` — is recorded so it is not
  re-derived as an option**: it would have lowered the count, changed the dispatch-gate threshold
  behaviour, and shrunk the verdict headline. ⭐ **The decision is consistent with the epic's
  standing anti-goal**: dropping `in_total` makes the *number* smaller without examining anything
  more, which is the "improve the metric by examining less" shape the #1069 analysis rejected on
  principle. Adding the checks is the arm that increases what is actually examined.
  ⛔ **The invariant is still owed either way** — a registry entry with `in_total: true` MUST have
  a consuming check, enforced by a **population-derived** contract test over the registry, never a
  hand-copied list.

- ~~⭐ **NEW 2026-08-09 — `in_total` vs check coverage: which way do we resolve it?**~~ *(superseded by the decision above; the framing is kept because it records why the choice was not mechanical)*
  `duplicate_claimable_keys` (N21) and `discard_without_report` (N22) are registry entries with
  `in_total: true` and **no consuming check**, so they inflate `counts.total`, the candidate-count
  dispatch gate, and the *"{N} candidates examined"* verdict. **The two remedies move the
  published count in OPPOSITE directions**, which is why the originating plan deliberately left it
  open: **add the two checks** → the count stays high and becomes honest; **drop `in_total`** →
  the count falls, the dispatch-gate threshold behaviour changes, and the verdict headline
  shrinks. ⇒ **This is an epic-level policy call, not a plan-level one.** `PLAN-CIS-043` D2 ships
  the missing invariant either way; **the direction is owed to the operator.**

- ⛔ **CLOSED 2026-08-09, RECORDED SO IT IS NOT RE-PROPOSED — the cache-prefix reordering is
  REJECTED on measurement, not on principle.** The structural defect is real and was read from the
  mechanism: `execution-context.md` orders a dispatch as variant system prompt → **volatile prompt
  body** (`plan_id`, `WORKTREE`, `name`, task inputs) → persona load → `skills[]` → workflow
  `Read`, so **the largest stable payload sits behind the volatile fields and cross-dispatch
  prefix sharing is impossible past the system prompt.** ⇒ **Worth ~0.39% of the bill**: ~27
  dispatches × ~12.5K skill stack ≈ 337K creation ≈ 421K billing-weighted against 108.9M. In
  `6-finalize`, creation runs ~493K **per dispatch**, of which the skill stack is 2.5% — **97.5%
  of creation is in-conversation growth, not prefix re-creation.** ⛔ **Do not stage a plan for
  it.** ⭐ The general lesson is worth more than the lever: **a real structural defect can be
  quantitatively negligible, and the only way to know is to size it before staging it.**

