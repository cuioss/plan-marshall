# Inbound findings hand-off — api-sheriff-roadmap round 8

**Received**: 2026-08-08 · **44 items** · **Source epic**: `api-sheriff-roadmap` (CLOSED at delivery — there is no round 9)
**Status**: RECEIVED AND PERSISTED. **Triage NOT complete.** Items are leads until each is re-derived first-party here.

> ⛔ **Why this file exists.** The reporting epic invented its own hand-off apparatus (index, carriers,
> `UNSENT` markers, per-epic round numbering) because **the bundle defines no such mechanism** — that is
> the report's own item 27-widened. A hand-off with no durable landing place is a hand-off that gets
> lost, and this round is the terminal one from a now-closed epic: **if it is dropped here, it is gone.**
> Persisted verbatim below before any triage, so triage can be wrong without being destructive.
>
> The reporter states every item was checked first-party (skill text read, scripts executed, predicates
> run). That is their evidence standard, not ours: **a claim arriving with a verification badge is still
> a lead** — the copied-claim rule (`a claim copied into a second plan does not inherit the first plan's
> verification`) applies to a claim copied across an epic boundary exactly as within one.

## Triage state

| Bucket | Items | Disposition |
|---|---|---|
| Routed to `review-apparatus` (bot participation / PR review) | 11, 15, 22, 23, 28, 29, 42 | Sent via their inbox — the PR/review test wins outright under the three-way routing rule |
| Candidate-owned by an EXISTING truthful-signals spec (dedup before staging) | 10 → `PLAN-TRUTH-058`; 35 → `PLAN-TRUTH-039`; 25 → `PLAN-TRUTH-048` (adjacent); 7/40 → the empty-assessment-sink family | **Fold as recurrence, do NOT stage new** — a recurrence is information on the existing row |
| Possibly ALREADY FIXED in main — verify before staging | 24 (`ci pr merge` false green) vs **#1087** `fix(ci): corroborate merge success, block failed-enqueue fallback` | ⛔ Verify against the merged diff first. Staging a plan for a landed fix is the C9 failure |
| Directly actionable against MY OWN machinery | 30 (`update-field` has no `--value-file`; `MAX_ARG_STRLEN` = 131072 is an undeclared ceiling on `resume_anchor`, and overflow presents as a **silent lost write**) | See § Immediate self-check below |
| New, unowned, high value | 1, 2/18/19 (guard vacuity family), 13, 14, 16, 21, 26, 27, 31, 32, 33, 34, 36, 37, 38, 39, 43, 44 | Awaiting staging decisions |

## Immediate self-check — item 30 against this very session

`resume_anchor` is written here with `manage-status update-field --value {string}`, as a shell argument.
Item 30 says that silently loses the write past ~131072 bytes while the command appears to succeed.

- **Current anchor size: ~22 KB** — roughly 17% of the ceiling. Not at risk today.
- ⭐ **Every anchor write this session was diff-verified after the fact** (re-read the field and asserted
  the new content and the preserved tail). That practice is what would have caught the silent loss, and
  it was adopted for an unrelated reason. **Keep it — it is the only defence that exists today.**
- ⛔ The ledger's own compaction history shows this anchor reached **52,754 chars** before a 66% cut. That
  is 40% of the ceiling. **The growth is real and the ceiling is undeclared** — this is a live risk for
  this epic specifically, not an abstract one.

## The three clusters, as the reporter framed them

**Cluster A — "the clean result that was never computed" (9 items: 21, 23, 25, 31, 32, 34, 38, 39, 40).**
⭐⭐ **This IS this epic's flagship archetype, arriving from an independent repository with nine
first-party instances.** One bug in nine costumes: a search, gate, or assessment returns a confident,
well-formed negative over something it never examined, and **none of them can express "I did not look."**
Item 32 nearly cost a merge; an operator disarming auto-merge caught it, no mechanism did.

**Cluster B — bot participation, nine axes across two rounds, six consecutive landings affected.**
Routed out to `review-apparatus`. Note the axis that is worst: a refusal notice matching no
`refusal_pattern` is ingested as a review comment **and credits the bot as a participant** — detection
failing in the direction that manufactures positive evidence.

**Cluster C — no vocabulary for deliberate project intent (item 44).** `build-map` has `seed`/`read`/
`drift` and no `add`, so a project-owned entry is indistinguishable from drift and `seed --force` erases
it; the classifier cannot tell *deliberately needs no build* from *unrecognised*. A consuming project had
to ship a mutation-proven contract test to defend a config file from its own configuration tool.

**Item 37 is a finding against the reporting orchestrator itself** — 8 authoring defects across two
specs, every one found by the executing plan and none by the author. Included deliberately. ⭐ The same
posture is owed here: this session has already produced two of its own (the vacuous work-at-risk defect
on TRUTH-044, and authoring cloud plan 010 with no orchestrator spec — see `PLAN-TRUTH-061` § Provenance).

---

# Report as delivered (verbatim)

# plan-marshall bundle findings — round 8

**Compiled**: 2026-08-03 → 2026-08-08 · **Delivered**: 2026-08-08 · **44 items**
**Source**: the `api-sheriff-roadmap` epic, end to end — 40 plans, closed at delivery.
Checked first-party: skill text read, scripts executed, predicates run. Nothing here is recalled.

## What this round is

Round 8 accumulated across the whole final arc of one epic rather than from a single review, and it
is the largest round so far by a factor of three. It is also the **terminal** round for this epic:
`api-sheriff-roadmap` closes with this hand-off, so there is no round 9 from this source.

| Part | Items | Source |
|------|-------|--------|
| 1 | 1–20 | Plans PLAN-08B through PLAN-49 — landings and inbox drains |
| 2 | 21–27 | PLAN-49 / PLAN-46 landings and the 0.1.0 release cut |
| 3 | 28–29 | PLAN-48 (guarded release trigger) |
| 4 | 30 | The orchestrator's own `resume_anchor` write ceiling |
| 5 | 31–35 | PLAN-52 (forward modes) — merged through a GitHub Actions major outage |
| 6 | 36 | The orchestrator closing issues after a landing |
| 7 | 37–43 | PLAN-50 (release posture reconciliation) |
| 8 | 44 | PLAN-51 (release guard control + build-gate coverage) |

**Composition**: 22 distinct components. Four are hit repeatedly — `manage-architecture` (4),
`automatic-review` (4), `phase-6-finalize` (3), `phase-3-outline` (3), `persona-module-tester` (3),
`tools-integration-ci` (3).

## The three clusters worth triaging together rather than item by item

**Cluster A — the clean result that was never computed. Nine items: 21, 23, 25, 31, 32, 34, 38, 39,
40.** This is the dominant finding of the entire epic and it is one bug wearing nine costumes: a
search, gate or assessment returns a **confident, well-formed negative** over something it never
examined. `architecture search --content` matching case-sensitively; the inventory indexing no `.svg`
at all while `which-module` returns `module: null` over a `truncated: false` response; a REQUIRED
check reporting SUCCESS over matrix children **cancelled at zero steps**; a green `ci-verify` reading
a check set containing neither required context on a head commit with zero runs; a security-audit row
marked COVERED that prescribed the control it did not have; a deep-lane plan reaching outline with
**zero** `CERTAIN_INCLUDE` assessments; `count:` misread as a file count when it is a row count.

**The shared defect is not the individual matcher — it is that none of these can express "I did not
look."** Every one of them renders the same as a real negative. Item 32 is the one that nearly cost
a merge: nothing caught it; an operator disarming auto-merge did.

**Cluster B — bot participation, now nine axes across two rounds.** Items 22, 23, 28, 29, 42 join
round 7's items 6, 9, 10, 11. Every axis produces the same outcome — a green signal over a review
that did not happen — by a different mechanism: OSS rate-limit that *permanently consumes* the range
it refused; a refusal notice that matches no `refusal_pattern` and is therefore ingested as a review
comment **and credits the bot as a participant**; `--participated-bots` accepting bare names and
then reporting every required bot absent; a REJECTED review clause held to a lower evidence standard
than an accepted one; and PR-Agent structurally unable to re-review on push, so any loop-back leaves
a required bot permanently unproven. **This cluster has now affected six consecutive landings.**

**Cluster C — the tooling has no vocabulary for deliberate project intent. Item 44, and it is new.**
`build-map` exposes `seed`/`read`/`drift` and no `add`, so a project-owned entry is indistinguishable
from drift and `seed --force` erases it; the file-type classifier cannot distinguish *deliberately
needs no build* from *unrecognised*, and the latter bucket blocks at phase-4-plan. The consuming
project had to ship a mutation-proven **contract test** purely to defend a config file from its own
configuration tool. Two seams, one missing concept.

## Two items that are not defect reports

- **Item 30** is against the orchestrator's own persisted state, and its failure mode is a **silent
  lost write**: `manage-status update-field` takes the value as a shell argument with no file-based
  input, so `MAX_ARG_STRLEN` (131072 bytes) is an undeclared hard ceiling on `resume_anchor`. At
  128512 bytes an append failed with *"Argument list too long"* and the ledger silently kept its
  previous value while the command appeared to succeed.
- **Item 37** is a finding against **spec authoring**, i.e. against this reporter. Included
  deliberately, on round 7's precedent that a findings round which only confirms the reporter's
  suspicions is not doing its job. The epic's last two specs contained **eight authoring defects
  between them, every one found by the executing plan and none by the orchestrator that wrote them**.

## Dedup

`bundle-handoff-index.md` is the durable dedup base and every row below was checked against rounds
1–7 before being added. Three findings this round were **folded onto existing rows as recurrences
rather than filed as new items** — row 21 (third repository-level occurrence), row 24 (`ci pr merge`
misreporting an enqueue), row 35 (four further argparse rejections in a second plan, all against
already-catalogued signatures). **Round 2's eighteen titles remain unrecoverable**, so any finding
predating 2026-07-29 still needs manual dedup.

---

- **(round 8 item 1) `plan-marshall:phase-6-finalize` — internal consistency across many surfaces
  does not detect drift from an operator ruling. UNSENT.** PLAN-37 D3 carried an explicit ruling
  (relax the `Content-Length` leg only; the `Transfer-Encoding` leg stays unconditional) and the
  implementation relaxed both. **Nine surfaces described the wider contract and all nine agreed with
  each other** — gate code, method javadoc, schema description, three doc files, a unit test, an IT
  fixture comment. Every consistency-shaped check passed; pre-submission self-review passed clean over
  179 candidates; the finalize security-audit step **verified the implementation against the
  implementation's own description** and concluded it was correct. Caught by an external review bot.
  **The ask: a check that compares the implementation to the RULING, not to its own restatements.**
  This is the sharpest instance yet of a class the corpus already circles — a consistency check cannot
  detect a uniformly-wrong premise.
- **(round 8 item 2) `plan-marshall:persona-module-tester` — a guard assertion that cannot fail is
  worse than no guard; perturb before accepting it. UNSENT.** Two vacuous guards in PLAN-37: (a) a
  count assertion over a **de-duplicated** set, where the size assertion is entailed by the preceding
  equality assertion AND the at-risk property (a duplicate token in the docs) was destroyed by the
  de-duplication before either assertion ran (fixed `0568d21`); (b) a bare-word `contains(" minimal ")`
  substring match against prose, which ordinary prose satisfies by accident (fixed `233f40b`). Both
  passed continuously — **by construction a vacuous assertion is green** — and both were caught by
  external PR review. **The ask: a perturbation step — a guard must be shown to FAIL against the
  defect it exists to catch before it is accepted.** Relates to standing clause 12 and to PLAN-43's
  whole subject.
  **RECURRENCE (2026-08-04, PLAN-43, third occurrence on this row).** PLAN-43 — the plan whose entire
  purpose was eliminating vacuous assertions — itself authored
  `assertNotNull(grpc.getHttpClient(), "a gRPC route carries the forced-h2 upstream client")`, where
  the value comes from a factory that cannot return null, so the check is unfalsifiable while its
  message names a property it does not test. Caught by CodeRabbit, not by the plan's own methodology.
  The recurrence strengthens this row's ask; the *new* ask it also raises (run the sweep's criterion
  over the sweep's own diff) is round 8 item 18 rather than a second copy of this one.
- **(round 8 item 3) `plan-marshall:build-maven` — a `-pl` module build without `-am` verifies against
  a stale installed artifact. UNSENT.** Maven resolves upstream reactor modules from `~/.m2` instead
  of the working tree, so the run verifies the target against **whatever jar was last installed**. A
  false-green generator with a nasty shape: the build succeeds, tests pass, and **nothing in the output
  signals that the code under test is not the code in the worktree**. It bites hardest in the natural
  fast-loop instinct — edit an upstream module, then run only the downstream module's tests.
- **(round 8 item 4) `workflow-integration-github` `post_responses` re-transmits every terminal
  finding — RECURRENCE, THE FOURTH. UNSENT.** Folded onto the existing round-6 item 6 row rather than
  filed as a new one. PLAN-37's roundtrip re-posted every already-terminal finding after a second
  comment batch, duplicating replies on answered threads. **New consequence observed this time:** an
  already-resolved thread can be **re-opened** by the new comment activity, so the project's
  "zero unresolved threads" post-merge assertion sees churn the plan never introduced. Duplicate volume
  scales with roundtrip count. The ask is unchanged and now four-times-evidenced: transmission is the
  state change and must be recorded per finding.
- **(round 8 item 5) THE GROUNDING RECURRENCE — carried forward from round 7, which missed it.**
  Round 6 item 1 (`plan-spec OBSERVED claims are hypotheses until re-verified`) has now recurred four
  times: PLAN-31C's `OBSERVED — verified, not assumed` claim was FALSE; the orchestrator's own Open
  Defect (26) diagnosis asserted a bundle-contract requirement that does not exist; the round-7 index
  audit found six rows reported written and never written; and PLAN-37's D3 drift above is the same
  shape one level up. **Record as a RECURRENCE on the existing row, not a new item.** The known working
  countermeasure the original never named: PLAN-31C's spec clause *"re-anchor against HEAD; delete by
  KEY, not by line number"*, which caught a five-commits-stale stamped HEAD when every line number had
  drifted and the keys survived.
- **(round 8 item 6) THE ORCHESTRATOR'S OWN SPEC TEMPLATE DRIFTED AND SUPPRESSED A CHANNEL. UNSENT.**
  PLAN-26's spec Write-Boundary read *"creates and edits NO file under `.plan/local/orchestrator/` …
  and reports its outcome through its PR alone"* — **omitting the `inbox/` exception the standard
  grants**. The plan obeyed it correctly and wrote no inbox message, then flagged the tension in its
  landing narrative. PLAN-37's spec carried the correct two-channel wording and wrote six messages.
  **Two specs authored by the same orchestrator into the same epic disagreed about whether the OUTBOX
  exists.** The bundle-side ask: the plan-spec template's Write-Boundary section is hand-copied per
  spec with no check that it matches the standard — a spec that silently revokes a standard-granted
  channel is indistinguishable from one that does not.

### Round 8 additions — compiled 2026-08-03 from PLAN-42 and PLAN-45, UNSENT

- **(round 8 item 7) `plan-marshall:phase-3-outline` / the discovery pass — the deep-lane
  component-assessment sink is EMPTY, and it is now a TWO-PLAN RECURRENCE. UNSENT.** PLAN-42 hit it
  first; PLAN-45 escalated it with the measurement: on a plan whose `status.metadata.planning_lane` is
  `deep`, `manage-findings assessment list --certainty CERTAIN_INCLUDE` returns `total_count: 0` —
  **entirely empty, not "populated with non-matching rows"**. Section 2.2 assessment-coverage is then
  unevaluable for *every* affected file, and each is formally unbacked. **No outline revision can fix
  it**: assessments originate in the discovery pass, upstream of the outline. **The ask: a deep-lane
  plan whose assessment sink is empty should FAIL LOUDLY rather than produce an unevaluable coverage
  section** — the current behaviour is indistinguishable from "the pass ran and matched nothing".
- **(round 8 item 8) argparse rejection — one root cause, three clusters, and one recurrence in a
  fresh context. UNSENT.** PLAN-45 filed three separate script-rejection clusters
  (`manage-solution-outline` at 3-outline, `manage-status` three times, `tools-integration-ci`
  `--pr-number`) that share **one** cause: a verb-scoped flag guessed at top level. **The load-bearing
  detail is the recurrence** — one instance repeated 80 minutes later in a re-entered context that had
  not seen the first failure, and the operator independently hit the same class twice on `ci pr view`.
  The knowledge lived only in the failed session, so nothing carried it forward. A rejection that
  names the correct scope (*"`--pr-number` is a verb-level flag of `checks status`"*) would close the
  whole class.
- **(round 8 item 9) `finalize-step-preference-emitter` — title-based finding-classing is SILENTLY
  BLIND for types whose titles embed per-instance IDs. UNSENT.** Filed with the operator's own
  skepticism attached: the emitter promoted a pattern on PLAN-45, but the recurrence registered only
  because the class collapsed on **type** rather than title, and the underlying findings were bot
  chatter. **The caveat is the real finding** — where titles carry per-instance IDs, title-based
  classing can never match twice, so the emitter sees nothing and reports nothing. **A detector that
  cannot fire is indistinguishable from a clean result.** The promoted pattern itself was not adopted.
- **(round 8 item 10) `phase-6-finalize` push re-entry — `no_remote` conflates "never pushed" with
  "merged and branch deleted". UNSENT.** PLAN-45 resumed finalize mid-pipeline after a prior session
  merged without recording `branch-cleanup`. The push step's re-entry probe returned `no_remote`,
  which the contract reads as *"local commits are not on origin, re-push"* — **but the remote branch
  was gone because of delete-on-merge.** Following the rule literally would have **resurrected a
  merged branch.** The plan skipped the push with a logged decision, which was correct. The two states
  are indistinguishable from the local ref alone; the probe needs to ask the PR before concluding.
- **(round 8 item 11) Sourcery weekly-quota exhaustion is now a TWO-PR pattern — recurrence on the
  bot-participation cluster.** PRs #147 and #149 consecutively. A required-adjacent bot being
  structurally absent for a whole PR, with the green quorum still proving "participation", is the
  fifth axis of the standing cluster and the one most likely to be read as coverage.
- **(round 8 item 12) THE FINALIZE PHASE COSTS 4× THE PHASE THAT DOES THE WORK, AND EXPLORES MORE THAN
  THE PHASE THAT DESIGNS IT. Measured on PLAN-45, a 10-file documentation change. UNSENT.**
  Per-phase, from the plan's own `metrics.md`:

  | phase | tokens | expl calls | expl bytes | exec calls | cache read |
  |---|---|---|---|---|---|
  | 2-refine | 296,037 | 33 | 371,632 | 99 | 26,578,192 |
  | 3-outline | 430,258 | 31 | 461,106 | 136 | 51,965,789 |
  | 4-plan | 295,283 | 18 | 225,429 | 170 | 42,453,559 |
  | 5-execute | 621,775 | 45 | 562,266 | 198 | 99,716,265 |
  | **6-finalize** | **2,468,507** | **70** | **1,217,211** | **419** | **255,879,300** |

  Finalize is **59% of the 4.16M total and 4× the execute phase**. It made **more exploration calls
  and read more exploration bytes than outline or execute** — 1.22 MB of discovery in the phase that
  should be purely mechanical — and its cache-read exceeds all other phases **combined**. **The ask:
  finalize re-discovers context that earlier phases already established.** Contributing loads, each
  individually defensible: six whole-tree build-log analyses (see item 13), 19 authored inbox
  messages, two review rounds plus a self-review re-fire, and a mid-pipeline re-entry that re-anchored
  from disk.

  **Measurement caveat, itself worth fixing:** the same section reports `Total tokens: 2,468,507`
  alongside `Inline main-context tokens: 5,899,082`. Inline cost is **2.4× the reported total**, so
  the headline 4.16M understates actual consumption and no consumer of the metrics can tell.

- **(round 8 item 13) THE PRE-PUSH QUALITY GATE IS WHOLE-TREE BY DESIGN AND RUNS TWICE PER FINALIZE
  ENTRY — the footprint-derived scoping machinery is never consulted for it. UNSENT.**
  *(Corrected 2026-08-03 after operator challenge — the first version of this row blamed module
  resolution and claimed superlinear growth. Both were wrong; the corrected findings follow.)*

  **Selection IS footprint-derived, and it works.** `.plan/marshal.json` `build.map` is a
  glob→`build_class` table (`*/src/main/*.java`→`compile`, `*/src/test/*.java`→`module-tests`,
  `pom.xml`→`verify`, …) — static *rules*, applied to the actual diff. PLAN-45's phase-5
  per-deliverable builds used it and scoped correctly: `demo-client` **1.5s**, `integration-tests`
  **18.4s**.

  **The six expensive runs did not come from that machinery.** They are three executions of
  `default:pre-push-quality-gate`, each running the project's two-command Pre-Commit Process across
  **all 5 modules**. Verified by log content: the 108 KB run invokes `maven-javadoc-plugin` and builds
  javadoc jars (the `-Ppre-commit` gate), the 76 KB run does not (plain full `verify`); both build
  `[1/5]`…`[5/5]`. **This step never consults the footprint** — it would have run identically on a
  pure `.adoc` change. The one-line javadoc edit and the `pom.xml` comment are irrelevant to it.

  **Cost is LINEAR in loop-backs, not superlinear.** Three gate executions, ~10.5 min each, mapped to
  cause from the plan's `work.log`:

  | # | trigger | evidence | builds |
  |---|---|---|---|
  | 1 | initial pre-push gate | step `11:09:37` → `11:20:22` | `110949` (5:11), `111526` (4:20) |
  | 2 | loop-back re-entry at review-fix HEAD `6d1654c` | `13:35:20` *"Loop-back re-entry (target=6-finalize, HEAD=6d1654c)"* → `13:46:29` | `133536` (5:16), `134102` (4:55) |
  | 3 | self-review re-fire fix | `13:58:41` *"Self-review re-fire at 6d1654c caught contract_drift 324f03"*, self-review done `14:04:41` | `141030` (6:23), `141705` (4:25) |

  So: **1 initial + 2 loop-backs, ×2 Maven runs each. Two loop-backs added ≈21 minutes of whole-tree
  Maven.** The constant factor of 2 is the project's mandated two-command gate; the variable is
  loop-back count.

  **The ask** is therefore not "fix the resolver" — it is: (a) let the whole-tree pre-push gate consult
  the same `build.map` classification the per-deliverable path already uses, so a footprint with no
  compilable change can skip or narrow it; and (b) consider whether the gate must re-run in full after
  a loop-back whose diff is confined to documentation.

- **(round 8 item 14) `manage-config` — `q_gate_validation: "once"` + `plan_without_asking: true`
  silently UN-GATES blocking Q-Gate findings. HIGH. UNSENT.** Q-Gate findings route to a review gate
  that the `*_without_asking` autonomy flag disables, so a **blocking** finding reaches task planning
  ungated and nothing reports it. **Corroborated first-party in this project's `marshal.json`**, and
  the pairing occurs twice: `phase-3-outline` = `q_gate_validation: "once"` + `plan_without_asking:
  true`; `phase-4-plan` = `q_gate_validation: "once"` + `execute_without_asking: true`. On PLAN-27 it
  let through a hardening block that would not have started and a bucket misassignment that would have
  stripped the verify lane from the reactor changes — both caught only by manual operator
  intervention. **The two settings are individually reasonable and jointly unsound; nothing in either
  one's documentation says so, and no validation refuses the combination.** The ask: either the
  autonomy flag must not suppress a *blocking* gate, or the combination must be refused at config
  validation time.
- **(round 8 item 15) Bot participation — THREE CONSECUTIVE PRs with a required-or-adjacent reviewer
  structurally absent. Recurrence on the standing cluster.** #147 Sourcery weekly quota, #149 Sourcery
  weekly quota, #150 CodeRabbit rate limit twice (final two commits never reviewed; merged with
  PR-Agent clean at `5b5a68e`, CI and Sonar green, operator-decided and recorded). The cluster is no
  longer an occasional failure mode — **at three-in-a-row it is the normal case**, and "the quorum was
  green" now routinely means "one reviewer was structurally unavailable".
- **(round 8 item 16) `plan-marshall:manage-architecture` — a reachability census on the call form
  `name(` silently misses the method-reference form `::name`, and the zero result reads as absence.
  UNSENT.** PLAN-43 D3 had to decide whether `SealedSessionCookieCodec.Unsealed` was reachable from
  production. The census searched `unseal(` and returned **no production consumer**. The real call site
  is `codec::unseal`. Acting on that verdict would have deleted a live public symbol from a
  security-sensitive codec. This is a **method defect in how the census is constructed**, not a
  transcription slip: the pattern encoded one of the two syntactic forms a Java call site can take, and
  the absence of the other was read as absence of the callee. **The ask: before any
  unused/unreached/safe-to-delete verdict, both forms are mandatory in the census — invocation `name(`
  and method-reference `::name` — with both patterns and both result sets recorded in the evidence
  trail.** Generalises to every language with a callable-reference syntax distinct from invocation
  (Python bare `name`, JS `obj.method` as a value, Kotlin/C# method groups). Related to the
  OBSERVED-claim discipline in standing clause 14: a census is exactly the kind of proxy that gets
  marked OBSERVED without the read behind it.
- **(round 8 item 17) `plan-marshall:workflow-integration-sonar` — a behaviour-preserving
  complexity refactor that only MOVES guards can RAISE a new symbolic-execution finding. UNSENT.**
  Fixing `java:S3776` in `ClientHelloSniParser` by extracting the loop body into helpers relocated
  bounds guards out of the loop. No guard was removed, weakened or reordered; runtime behaviour was
  identical. Sonar's next pass raised a **new** `javabugs:S6466` on a provably unreachable path,
  because the engine reasons per-method and the moved guard crossed the boundary it reasons within.
  **The ask: treat a cognitive-complexity extraction as a change that can move the gate count rather
  than only reduce it — budget a follow-up gate pass instead of assuming the extraction is
  finding-neutral — and when a symbolic-execution finding lands on a path a relocated guard already
  protects, establish reachability first rather than adding a redundant check to satisfy the engine.**
  Chain-fixing accretes defensive checks the original inline form did not need.
- **(round 8 item 18) `plan-marshall:persona-module-tester` — a criterion-driven sweep must run its
  own criterion over its own diff, as an explicit closing deliverable. UNSENT.** See the RECURRENCE
  note on round 8 item 2 for the concrete instance. The **new** ask here is structural, not another
  vacuity report: **a sweep does not automatically apply its criterion to the code it writes** — the
  reviewer's attention points outward at the corpus, and the diff it produces is a blind spot
  *precisely because* it is "the fix" rather than "the corpus". Make "apply the sweep's criterion to
  the sweep's own footprint" a mandatory closing step before the PR opens, not an assumed consequence
  of the author having internalised the criterion. Applies to every criterion-driven sweep — assertion
  quality, logging standards, null-safety, naming, security-pattern remediation. The failure is
  self-concealing: the author who just spent the plan calibrating on the defect is the one least
  likely to see it in their own output.
- **(round 8 item 19) `plan-marshall:persona-module-tester` — a syntactic-marker density score is a
  SCREEN, not a verdict; report the screen-to-verdict conversion rate. UNSENT.** PLAN-43 D1 ranked 135
  test files by weak-assertion marker density. **Three files cleared the density gate and yielded zero
  strengthenings** — every flagged method already had a matched negative control, which the marker
  cannot see. Editing the top-ranked files mechanically would have churned **17 sound tests**. The gap
  between "flagged" and "warranted" was ~40% of the screened population, and it is also the honest
  explanation for the plan's under-cap delivery (18+1 against a stated cap of 20). **The ask: a density
  score selects candidates for READING and never authorises an edit; record the screen-to-verdict
  conversion rate as a first-class sweep output (a low rate is information about the *marker*, not a
  failure of the sweep); and under-delivering against a stated cap because the pool ran dry is a
  correct outcome to be reported with the pool numbers, never padded to the cap.** Applies to every
  metric-screened remediation — complexity scores, duplication blocks, coverage-gap rankings,
  lint-density heatmaps. Cheap to fall into precisely because a quantitative ranking *feels* like
  evidence of a defect rather than evidence of where to look.
- **(round 8 item 20) cross-cutting finding triage — a derived CI-job failure is superseded by its
  root-cause fix, not triaged a second time. UNSENT.** Four CI job failures were filed on PLAN-43 while
  the true signal was a single upstream quality-gate verdict; once that verdict was settled and
  re-verified at the new HEAD, all four resolved together against the same evidence. **The ask: a
  finding whose detail merely restates "job X failed" carries no independent diagnostic content, so it
  is dispositioned against the root-cause fix — naming the superseding evidence (the new HEAD and the
  re-verified gate result) so the disposition stays checkable — rather than carried as its own work
  item.** Triaging them independently duplicates work and invites a second fix for a cause already
  closed. Note the tension to resolve in the ask: this must not become a licence for bulk dismissal,
  which is why the superseding evidence is named per finding.
- **(round 8 item 21) `plan-marshall:manage-architecture` — `architecture search --content` matches
  CASE-SENSITIVELY, and its clean zero is indistinguishable from a real negative. UNSENT.** Filed
  2026-08-05 from PLAN-08B. A lowercase sweep returns `count: 0` *with every coverage field clean* —
  the exact shape the complete-coverage rule teaches a caller to trust — while the term is present in
  other casing. Two concrete misses on one plan: 85 `Plan NN` citations in
  `doc/security-threat-model.adoc` invisible to every `plan ` sweep, and a `Production-Shaped`
  document title invisible to every `production-shaped` sweep. **The ask: expose a case-insensitivity
  flag, or state the matching semantics in the response payload, so the caller is not left inferring
  them from a zero that carries positive coverage evidence.** Distinct from item 16 (which is about
  the *call form* `name(` missing `::name`) though the failure shape is the same family: a
  mechanically-narrow match producing an authoritative-looking zero. Compounds with the already-known
  scope gap — the verb does not walk `.github/**`, `.claude/**` or `CLAUDE.md`, so a clean zero over
  those trees is meaningless regardless of casing.
  **RECURRENCE 2026-08-06 from PLAN-48 (`-001` finding 2), and it sharpens the scope half of this row
  into its own ask.** `.github/**` blindness reproduced independently by three agents on PLAN-48, at a
  cost of one detour each. Two corrections to what was believed: `doc/**` is **covered** (a sweep
  scanned 936 files with empty `unreadable[]`/`elided[]` and returned real hits from
  `doc/user/container-image.adoc`, refuting an earlier agent's claim), and `.claude/**` was never
  probed on that plan, so it is **unverified** rather than confirmed-broken. **The added ask: the
  coverage fields are the contract surface that is lying — a path set the inventory does not walk
  should be reported as out of coverage (an explicit `uncovered[]` alongside `unreadable[]` /
  `elided[]`) rather than folded into a clean zero.** That is a smaller change than indexing the
  trees and it makes the gap legible without changing what the verb indexes. Third repository-level
  occurrence of this family (compose/infra YAML and `src/main/resources` are already in the
  API-Sheriff lesson corpus as `architecture-search-false-negative-yaml`).
- **(round 8 item 22) `plan-marshall:automatic-review` — a CodeRabbit OSS rate-limit refusal
  PERMANENTLY CONSUMES the commit range it refused. UNSENT.** Filed 2026-08-05 from PLAN-08B, where
  the limit fired on `39cda67..5c5b2a7`. CodeRabbit's incremental bookkeeping marks a range
  *reviewed* when it DECLINES that range, including a rate-limit decline that reviewed nothing. The
  documented recovery — wait out the ~30-minute window, re-trigger — was **refused** with "does not
  re-review already reviewed commits". There is no caller-reachable un-mark. **The ask: treat a
  rate-limit refusal as coverage LOST, not coverage DEFERRED — do not budget a re-trigger as its
  recovery, decide the merge-anyway call immediately on the coverage actually obtained, and record
  which bots did and did not review the range.** This is materially worse than the already-known
  "rate limit blocks merge" behaviour (which costs time and is recovered by waiting): this one costs
  coverage, and waiting makes it permanent rather than resolving it. Highest-risk shape, which fired
  here: the refused range contained the fixes for that same bot's own findings.
- **(round 8 item 23) `plan-marshall:automatic-review` — CodeRabbit's rate-limit refusal notice does
  not match the registry `refusal_patterns`, so a refusal is CREDITED AS A REVIEW. UNSENT.** Filed
  2026-08-05 from PLAN-08B; same incident as item 22, different layer, and the pair is why that run
  both lost the coverage *and* recorded it as obtained. The refusal notice matched no configured
  pattern, so it was (1) ingested as an ordinary review comment and entered triage as if it were a
  finding, and (2) counted CodeRabbit as a review participant. **The ask: extend `refusal_patterns`
  for CodeRabbit against the ACTUAL observed comment body (not a paraphrase), and stop treating bot
  participation as coverage evidence without checking the bot emitted at least one substantive
  verdict — a participation count a refusal can increment is not a coverage metric.** Suggested
  durable guard: a fixture asserting each registered bot's known refusal wordings classify as
  refusals, since the pattern list is unverifiable prose otherwise and drifts silently whenever a
  vendor rewords. Blast radius is the merge gate: a mis-classified refusal can satisfy a
  required-reviewer check. Detection failing in the direction that HIDES a gap is strictly worse
  than failing to detect at all, because it manufactures positive evidence of a review that never
  happened.
- **(round 8 item 24) `plan-marshall:tools-integration-ci` — `ci pr merge --delete-branch` CLOSES A PR
  UNMERGED ON A MERGE-QUEUE REPO WHILE RETURNING `merged: true`. UNSENT.** Filed 2026-08-05 from
  PLAN-49 (lesson `2026-08-05-11-003`), and it nearly lost a full plan's work. On a queue-gated repo
  `pr merge` only ENQUEUES; `--delete-branch` then removes the head ref out from under the queued
  entry, so the queue drops it and GitHub records the PR closed-and-unmerged with `main` untouched.
  `branch-cleanup` had already deleted the branch and removed the worktree, leaving the only copy as
  **unreferenced commits in the local object store**. **The ask is two-part: (a) never pass
  `--delete-branch` on a queue-gated repo — the queue owns head-ref lifetime — and (b) the returned
  `merged: true` is an OPTIMISTIC INFERENCE FROM A SUCCESSFUL ENQUEUE, NOT AN OBSERVATION; it must
  either be renamed to say so (`enqueued`) or be made to verify against the GitHub API +
  `mergeQueue.entries` before claiming a merge.** The epic already carries the never-pass-`--delete-branch`
  rule as a standing clause learned once before; this occurrence shows the rule is not enough while
  the return value still says `merged`.
  **RECURRENCE 2026-08-07 from PLAN-52 / PR #185 — third occurrence, and it widens the row to a SECOND
  VERB.** `ci pr merge` returned `status: success` TWICE while only ARMING auto-merge: at the second
  return `autoMergeRequest.enabledAt` was set while the PR was `state=OPEN`, `mergeable_state=blocked`,
  `mergeCommit=null` and `mergeQueue.entries` EMPTY — and branch-cleanup acted on that success and had
  to be walked back. **NEW: `ci pr merge-queue` returned `enqueued: true` while `isInMergeQueue=false`
  and `mergeQueue.entries` was empty**, so the defect is not confined to the merge verb. **The added
  ask: on a merge-queue repository "merge" is a TWO-STEP action (accept, then land), and any wrapper
  collapsing them into one boolean is wrong for the entire window between them — return the accepted
  state and the landed state as separate fields rather than one optimistic verb-named boolean.**
- **(round 8 item 25) `pm-plugin-development:ext-self-review-plan-marshall` — `pre-submission-self-review`
  renders a green `[OK]` having reviewed NOTHING outside Python/Markdown. UNSENT.** Filed 2026-08-05
  from PLAN-49 (lesson `2026-08-05-11-002`). 19 of the surfacer's 20 detectors gate on `.py`/`.md`,
  so a 25-file Java/AsciiDoc diff surfaced zero candidates — and the step reported success anyway.
  **The ask: a step that could not evaluate its subject must report that distinctly from a step that
  evaluated and found nothing; a domain with no surfacer should render `skipped — no surfacer for
  this domain`, never `OK`.** Same family as items 21 and 23: a mechanism reporting a clean result
  it never actually computed.
- **(round 8 item 27) `plan-marshall:marshall-orchestrator` — the `close` verb has NO pre-close
  close-out, so everything an epic accumulated is frozen rather than dispositioned. UNSENT.** Filed
  2026-08-05. **Verified first-party before filing:** `workflow/close.md` Step 2 "Pre-close
  reconciliation" is *queue-settlement only* — confirm no unreconciled `launched` plan, regenerate the
  START-HERE block, freeze `history.md`. Unresolved defects and watches are "carried forward as
  leads", which preserves the text and disposes of nothing. **What an epic actually accumulates and
  what `close` does not touch:** an undelivered findings hand-off to the bundle; a lessons corpus that
  is **global to the repo, not per-epic**, so it silently becomes the next epic's inheritance; open
  defects that need re-homing to a successor epic rather than freezing; and — the one with teeth —
  **defect entries that *assert* a re-homing which was never written into the target tree.** That last
  is not hypothetical: it happened here, and it is structurally likely because the orchestrator's
  write boundary forbids writing into another epic's tree, so an orchestrator can only *record the
  intent* to re-home and must rely on a later session to enact it. **The ask: give `close` a
  pre-flight — deliver the outstanding bundle round, disposition every lesson (with the corpus's
  repo-global scope made explicit), distribute open defects to successor epics, and VERIFY each
  asserted re-homing exists in the target rather than trusting the assertion. Consider a sanctioned
  cross-epic write path for re-homing, since the boundary is what makes the gap structural.**
  API Sheriff is shipping this as a project-level skill because two live epics need it within weeks;
  the mechanism is generic to any plan-marshall orchestrator epic in any repo and belongs upstream.

  **WIDENED 2026-08-05 — THE FINDINGS HAND-OFF ITSELF HAS NO MECHANISM AT ALL, AND THAT GAP IS
  LARGER THAN THE CLOSE-OUT GAP ABOVE.** The bundle hand-off is how a consuming repo returns findings
  *about plan-marshall* to the bundle — the channel this very row travels on — and **nothing in the
  bundle defines it.** This epic invented the whole apparatus locally: a `bundle-handoff-index.md` as
  a durable dedup base kept forever, per-round carriers archived on delivery, `UNSENT` markers flipped
  in the same action as the send, and per-epic round numbering. **It was invented because the need was
  real and recurring — seven rounds delivered over roughly three weeks, entirely driven by prose in a
  resume anchor.** Every consuming repo either reinvents this or, far more likely, **loses its
  findings**: without an index there is no dedup base, so a finding observed twice is filed twice or
  not at all, and without a flip marker a compiled round is silently re-sent or silently never sent.
  **The ask: define the findings hand-off as a first-class bundle mechanism — the index and its
  dedup semantics, the carrier format, the sent/unsent lifecycle, and per-epic numbering — so a
  consuming repo has a channel rather than a convention it must invent.** Note the shape of the
  evidence: this row exists *because* the apparatus existed to carry it, which is precisely the
  survivorship bias to correct for — the findings that were lost in repos without one left no trace.
- **(round 8 item 26) `plan-marshall:manage-solution-outline` — phase-3's `get-module-context` is
  STRUCTURALLY UNRUNNABLE for any worktree plan, silently dropping the Architecture Hints section on
  every such run. UNSENT.** Filed 2026-08-05 from PLAN-49 (lesson `2026-08-05-11-001`). **The ask:
  make the failure visible, and resolve the module context against the worktree's main-anchored root
  so worktree plans get the same outline inputs as in-tree plans.** Note the compounding: `use_worktree`
  is common in this project, so the silent drop is closer to the norm than the exception.
  **RECURRENCE 2026-08-06 from PLAN-48 (`-001` finding 1) — second plan, and now with the mechanism
  named.** Observed TWICE on PLAN-48 (initial outline dispatch and re-dispatch); the Architecture
  Hints section was omitted from `solution_outline.md` both times. The contradiction is between two
  individually-correct facts: `get-module-context` hard-resolves the plan's worktree path, while
  `phase-3-outline/SKILL.md` § "Phase-Entry Worktree Assertion" states the worktree is not created
  until phase-5-execute Step 2.5. **Why it stays invisible: Step 10b-bis is explicitly additive and
  omittable, so the agent correctly continues rather than hard-stopping — a step that is always
  skipped and is *allowed* to be skipped produces no signal at all.** Suggested fix sharpened: mirror
  the fallback `manage-status get-worktree-path` already implements (it returns the current checkout
  while `worktree_path` is unset). The asymmetry between the two resolvers is the defect.
- **(round 8 item 28) `plan-marshall:tools-integration-ci` — `--participated-bots` takes
  evidence-typed `bot:evidence` pairs, and feeding it bare bot names makes a fail-closed gate report
  EVERY required bot absent. UNSENT.** Filed 2026-08-06 from PLAN-48 / PR #171. The gate is correctly
  fail-closed, so the malformed input does not error — it produces a confident, fully-populated
  "no required bot participated" verdict that would have blocked the merge on a fiction. Caught only
  because the operator checked the verdict against the PR. **The ask: reject an un-typed
  `--participated-bots` value with a distinct error rather than parsing it into a maximally negative
  result. A fail-closed default is correct; silently *manufacturing* the fail-closed condition from
  malformed input is not — it makes the gate indistinguishable from a real absence.** Same family as
  items 22/23 and the standing PR-wide-not-HEAD-scoped participation finding: the recurring theme is
  that this gate's evidence surface cannot distinguish *looked and found nothing* from *could not
  look*, and here it cannot distinguish either from *was asked the question wrongly*.
- **(round 8 item 29) `plan-marshall:automatic-review` — a REJECTED review clause owes the same
  evidence standard as an accepted one, and nothing in the disposition flow asks for it. UNSENT.**
  Filed 2026-08-06 from PLAN-48 / PR #171, where it cost two wrong rejections of the same reviewer on
  the same false premise. CodeRabbit made two separate correct claims about `pull_request` event
  refs; both were rejected by re-asserting the plan's own reasoning rather than by reading the source
  the reviewer cited, and one rejection is still the public record on the PR. **The ask: the
  comment-disposition flow requires a rationale for a rejection but not a *source* — so "disagree,
  here is my reasoning" is a complete disposition, while the reviewer's citation is discarded
  unread. Require a rejection that contradicts a cited source to either cite a counter-source or be
  escalated.** The compounding factor is worth stating: multi-clause suggestions are triaged clause
  by clause (correctly), and a suggestion's correct half lends unearned credibility to the
  disposition of its incorrect half — in this instance *both* halves were correct and both were
  reasoned about from the same wrong premise, so clause-by-clause triage did not help at all.
- **(round 8 item 30) `plan-marshall:manage-status` — `update-field` takes its value as a SHELL
  ARGUMENT with no file-based input, so a field silently becomes UNWRITABLE past a size the tool
  never declares, and the failure presents as a LOST WRITE rather than an error. UNSENT.** Filed
  2026-08-06 from the api-sheriff-roadmap orchestrator. `resume_anchor` is documented as a "verbatim
  string" with no stated bound; at 128512 bytes the next append hit the kernel's `MAX_ARG_STRLEN`
  (131072, 32 pages) and the shell refused to exec with `Argument list too long`. **The ledger
  silently kept its previous value while the surrounding command sequence appeared to run** — the
  orchestrator caught it only because it re-read the field afterwards. **The ask: add a
  `--value-file` alongside `--value` (the same path-allocate pattern `manage-lessons set-body` and
  `inbox write --payload-file` already use for exactly this reason), and until then have the verb
  detect an over-length value and fail with a distinct, named error.** Two things make this sharper
  than an ergonomics complaint: the affected field is the one the orchestration model designates as
  the *durable* record across sessions, so it is the field most likely to grow; and its only
  sanctioned writer is this verb, so there is no fallback — direct file access to `status.json` is
  prohibited outright. Same family as items 22/23/28: a mechanism whose failure is indistinguishable
  from success at the point of decision.
- **(round 8 item 31) `plan-marshall:phase-6-finalize` — a green CI verdict can hide that the REQUIRED
  checks never ran; the rollup aggregates only what exists. UNSENT.** Filed 2026-08-07 from PLAN-52 /
  PR #185, where it fired TWICE in one plan. (1) `ci-verify` recorded `CI green` with
  `ci_final_status=success` over a check set containing only Sourcery, CodeRabbit and the CLA check —
  **neither** required context (`build / conclusion`, `integration-tests / conclusion`) was present,
  and the head commit had ZERO workflow runs. Discovered hours later, when the merge refused. (2) A
  REQUIRED context reported `success` while its matrix children were `cancelled` with **zero steps
  executed** — nothing compiled, nothing tested — and the parent run's own conclusion was `failure`.
  **A merge on that vacuous gate was prevented only by an operator DISARMING auto-merge; no mechanism
  caught it, and arming auto-merge is a standing instruction to merge on the next green.** The ask:
  assert two things separately — every required context is PRESENT on the exact head SHA, and each
  one's underlying JOBS reached `conclusion=success` with a non-zero executed-step count. Enumerate
  the required set from the ruleset; never infer it from what came back. Same family as items 22/23/28
  and now its sharpest instance: absence of a required check is indistinguishable from success in any
  naive rollup read.
- **(round 8 item 32) `plan-marshall:phase-6-finalize` — a required status check is satisfied only by
  a `pull_request`-attributed run; a `workflow_dispatch` green does not count. UNSENT.** Filed
  2026-08-07 from PLAN-52. The merge was blocked for roughly eleven hours not by the code but because
  the green checks came from `workflow_dispatch`, which the ruleset counts as *expected* rather than
  *satisfied*. **The recovery that worked is worth shipping as the documented one: close-and-reopen
  fires `reopened`, producing properly attributed `pull_request` runs — and as a bonus re-triggers
  PR-Agent, whose triggers are `opened`/`reopened`/`ready_for_review`.** The ask: teach the re-trigger
  step that event attribution is part of check satisfaction, and prefer close-and-reopen over a
  dispatch when a required context is unsatisfied.
- **(round 8 item 33) `plan-marshall:phase-3-outline` — an identifier- or key-scoped sweep cannot
  close a SEMANTIC set, and its clean result reads as completeness. UNSENT.** Filed 2026-08-07 from
  PLAN-52, which recorded **three misses in one plan**. Same family as items 16/21 and the
  architecture-search scope gap, but a distinct mechanism: those are about a matcher being narrower
  than the caller believes; this is about the SEARCH KEY being categorically unable to enumerate the
  target — a set defined by meaning cannot be closed by a sweep over identifiers or config keys. **The
  ask: where a deliverable's completeness criterion is a semantic set, say so and require a
  first-party enumeration with its rationale, rather than accepting a sweep as the closure proof.**
- **(round 8 item 34) `plan-marshall:recipe-security-audit` — a threat-model row marked COVERED
  prescribed the exact control it did not have. UNSENT.** Filed 2026-08-07 from PLAN-52. The row named
  its own mitigation and was recorded as covered; the control was absent. **This is the
  clean-result-never-computed class (items 21/23/25/31) reaching the SECURITY audit surface, which is
  the worst place for it** — a COVERED row is precisely what a later reader will not re-derive. NOTE
  THE CORRECTION THE PLAN'S OWN LESSONS AGENT MADE: the GW-04 self-refutation was **pre-existing at
  the merge base `bcfe3c9`**, not introduced by PLAN-52, and the plan's first framing implied
  otherwise. The finding stands; its attribution was fixed.
- **(round 8 item 35) `plan-marshall:tools-script-executor` — the documented argparse-rejection guard
  did not prevent 16 rejections in one plan. UNSENT.** Filed 2026-08-07 from PLAN-52. A guard that
  exists, is documented, and is bypassed sixteen times in a single plan is not being read at the
  moment it is needed. **The ask: make the rejection self-correcting at the point of failure — the
  error should name the accepted surface rather than referring the caller to documentation they have
  already demonstrably not consulted.**
  **RECURRENCE, folded 2026-08-07 from PLAN-50 rather than duplicated: four MORE argparse rejections
  at exit 2 in a second plan, and all four map onto signatures ALREADY CATALOGUED in
  `persona-plan-marshall-agent` § "Never invent script subcommands — recurrence signatures".** Two
  plans, twenty rejections, every one of them a documented signature. **That the catalogue exists and
  the class keeps recurring is now the evidence, not the anecdote** — a prose-level guard placed
  where the caller is not reading does not prevent the class. Named instance: `manage-files
  --subdir`, twice in one hour, against a verb set where no verb takes it.
- **(round 8 item 36) `plan-marshall:tools-integration-ci` — `issue prepare-comment` is plan-scoped,
  so the ORCHESTRATOR has no route to a prepared comment body at all. UNSENT.** Filed 2026-08-07 from
  the roadmap orchestrator, closing issues #182/#183 after PLAN-52 landed. `ci issue prepare-comment
  --plan-id plan-52-protocol-headers-block` returned `plan_not_found` because the plan's
  `.plan/local/plans/` directory is removed once the plan finalizes — which is exactly when the
  orchestrator does its post-landing issue hygiene. **The path-allocate pattern therefore has a hole
  precisely at the lifecycle stage that needs it most**, and the only fallback is `gh issue comment
  --body-file`, i.e. the direct `gh` call the orchestrator skill prohibits. Note the asymmetry that
  makes this a design gap rather than a missing flag: **`ci issue close --issue N` has no plan
  scoping and worked unchanged**, so the same verb group is half-reachable from the orchestrator.
  **The ask: give `prepare-comment` / `prepare-body` an orchestrator store (`--store orchestrator
  --slug {epic}`) the way `manage-logging` and `manage-status` already have, so the body-file
  discipline survives the plan directory's removal.**
- **(round 8 item 37) `plan-marshall:phase-2-refine` — a plan spec's carrier enumerations are read as
  a work list when they are only advisory hints. UNSENT.** Filed 2026-08-07 from PLAN-50, which
  checked 7 spec premises and found **4 stale or invalid — including the declared blocking
  deliverable** (D5's "the runbook fails closed on every future release cut" had already been fixed
  by PR #169's renumbering, voiding the spec's own shed-order ruling). D4 named two section headings
  that do not exist. **This is PLAN-48's landed lesson — "enumerate carriers mechanically rather than
  from recall" — recurring one level up, against a PLAN SPEC rather than against source.** A spec's
  Claim Labels already carry HEADs and dates and that was not sufficient. **The ask: have refine
  treat every enumeration in a spec as a hypothesis to re-derive, and report the refutation rate as a
  first-class output — 4-of-7 is a signal about the authoring process, not a per-premise footnote.**
- **(round 8 item 38) `plan-marshall:manage-architecture` — the inventory indexes NO `.svg` at all,
  so an SVG carrier is invisible to the content-search gate and resolves to `module: null`. UNSENT.**
  Filed 2026-08-07 from PLAN-50, confirmed live twice (at `e6ed358` and again at execute).
  `architecture find --pattern "*.svg"` returns `count: 0`; `which-module` on a real, published SVG
  returns `module: null` with `attributor_count: 0` **over a CLEAN response** (`truncated: false`,
  `elided[0]`), so the negative looks trustworthy. **It cost a real miss**:
  `doc/resources/diagrams/release-publish-flow.svg` asserted *"Manual dispatch is the only trigger"*
  in a published diagram and no enumeration found it. Same clean-result-never-computed family as
  items 21/23/25/31, on a new file type. **THIS IS THE ONE THAT COULD NOT BE FILED AS A LESSON AT
  ALL** — the store refuses a `plan-marshall:`-component lesson without `--allow-foreign-store`,
  correctly not overridden — so the epic inbox is its only durable carrier.
- **(round 8 item 39) `plan-marshall:manage-architecture` — `search --content` returns ONE ROW PER
  ATTRIBUTED MODULE, so a criterion phrased on `count:` scores a false failure. UNSENT.** Filed
  2026-08-07 from PLAN-50. A success criterion reading *"returns exactly one file"* saw `count: 6`
  over **three** distinct paths, each appearing twice because `doc/**` is dual-attributed to both
  `api-sheriff-parent` and `documentation`. **`count` is a row count, not a file count, and nothing
  in the response says so.** Distinct from items 21/16 (matcher narrower than the caller believes) —
  here the matcher is right and the CARDINALITY is misread. **The ask: name the field for what it
  counts, or emit a distinct `file_count`.**
- **(round 8 item 40) `plan-marshall:phase-3-outline` — a DEEP-lane plan reached outline with ZERO
  `CERTAIN_INCLUDE` assessments. UNSENT.** Filed 2026-08-07 from PLAN-50. `status.metadata` reported
  `planning_lane: deep` and the outline enumerated **9 affected files across 7 deliverables**, while
  `assessment list --certainty CERTAIN_INCLUDE` returned `total_count: 0`. Outline § 2.2 (Assessment
  Coverage) therefore fails for every affected file. **The deep lane's discovery pass recorded no
  assessments at all** — the third recurrence of the empty-sink shape already on standing defect (30).
  **The plan reported it once rather than as 9 duplicate per-file findings, and refused to backfill
  synthetic records to make the section pass — record the grounding method instead.**
- **(round 8 item 41) `pm-documents:ref-documentation` — a renamed heading and a deleted
  disambiguating antecedent do not merely go stale, they INVERT the meaning. UNSENT.** Filed
  2026-08-07 from PLAN-50; three Q-Gate findings sharing one shape, all caught by
  `pre-submission-self-review`, all fixed. Renaming a section to *"The guard has fired once and has
  never been observed refusing"* left a cross-reference still asserting the opposite; deleting a
  disambiguating antecedent silently re-pointed a pronoun. **Each surviving text asserts the CONVERSE
  of what it points at, so a reader who trusts it lands on the exact wrong belief the change was made
  to correct** — strictly worse than a broken link, which at least fails visibly. **The ask: on a
  heading rename or antecedent deletion, require the inbound references to be re-read for SENSE, not
  just re-pointed.**
- **(round 8 item 42) `plan-marshall:automatic-review` — PR-Agent never re-reviews on push, so a
  loop-back HEAD leaves a required bot permanently unproven. UNSENT.** Filed 2026-08-07 from PLAN-50.
  After loop-back fixes advanced HEAD, the participation guard reported
  `unproven_bots=pr-agent,sourcery` with `pr-agent:absent` — CodeRabbit re-reviewed the range
  automatically, PR-Agent structurally cannot (its triggers are `opened`/`reopened`/
  `ready_for_review` plus on-demand `/review`). The guard correctly returned `loop_back` rather than
  force-done. **The ask: `re_review_on_loopback` must POST an explicit `/review` for bots that do not
  self-trigger, or a required bot is unprovable by construction after any loop-back.** Adjacent to
  items 22/23/28/29 — the epic's bot-participation family, now five entries.
- **(round 8 item 43) `plan-marshall:manage-adr` — an ADR that is BOTH a supersession subject and a
  carrier of the swept posture receives contradictory instructions. UNSENT.** Filed 2026-08-07 from
  PLAN-50. D6 directed a sweep of every dispatch-only statement and ADR-0034 was the single largest
  carrier (4 of 8 mechanical hits); D3 made that same ADR the supersession subject. **Executing D6
  literally would have rewritten the BODY of a decision record.** The plan refused, correctly: an ADR
  body is an immutable record of what was decided when, and supersession changes its STATUS, never
  its text. **Two asks: (a) make "an ADR body is never rewritten by a sweep" an enforced rule rather
  than a convention the executor has to know; (b) this is also an ORCHESTRATOR authoring defect —
  check for file overlap BETWEEN deliverables of one plan, not only across plans.**
- **(round 8 item 44) `plan-marshall:manage-config` + the file-type classifier — the tooling has NO
  VOCABULARY FOR "THE PROJECT MEANT THIS". UNSENT.** Filed 2026-08-08 from PLAN-51, reported as ONE
  finding with two faces because it is the same missing concept surfacing at two seams; filing them
  separately would read as two feature requests instead of one design gap.
  **Face 1 — `build-map` cannot preserve a project-owned entry.** The verb set is `seed`, `read`,
  `drift` and there is **no `add`**. An entry a project adds by hand derives from no extension's
  `classify_globs()`, so `drift` reports it as removed and `seed --force` **erases it**. There is no
  way to mark an entry as *mine, deliberately, keep it*.
  **Face 2 — the classifier cannot distinguish *deliberately needs no build* from *unrecognised*.**
  Both land in `unknown`, and that bucket **blocks at phase-4-plan**. `.plan/marshal.json` is
  genuinely the first case — it configures plan-marshall, not Maven, so no Maven output depends on it
  — yet it stalled the plan whose own subject was build classification.
  **Why this is sharp rather than academic**: PLAN-51's fix to `build.map` had a built-in expiry from
  the moment it landed, and the repository had to ship a **contract test**
  (`BuildGateCoverageContractTest`, mutation-proven) purely to convert a silent tool-driven erasure
  into a red build. **A project should not need a unit test to defend a config file from its own
  configuration tool.** The ask: a way to express project intent that seeding preserves and drift
  does not flag, and a classifier bucket for *deliberately inert* distinct from *unknown*.
