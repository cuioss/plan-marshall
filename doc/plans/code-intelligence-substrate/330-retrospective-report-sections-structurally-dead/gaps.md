# Gaps — 330-retrospective-report-sections-structurally-dead

All five deliverables shipped and hold against their literal *Done when*, and every re-derivable
figure in `report-01.md` matched a first-party measurement. What remains is: one unreported hole in
the same partition (a non-dict fragment on a conditional row is lost as a "benign omission"), the six
residue items the run declared and deliberately did not fix — all still open at `dd1eea1` — a false
enumeration in a shipped skill file, three instances of historical prose in shipped files, and two
minor report inaccuracies. Nothing found contradicts a shipped behaviour claim about the
written-implies-non-empty invariant itself; that was the part searched hardest and it is sound.

## G1 — Make the drop/omit split use one discriminator for non-dict fragments too

- **Kind:** bug
- **Severity:** medium
- **Topic:** detectors/auditor
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/compile-report.py:550-559`
  (`build_document`, the non-emit partition) reading `_fragment_has_payload` at `:171-196`, against
  `_fragment_renders_empty` at `:427-472`
- **Evidence:** executed at HEAD —
  `'real prose the producer wrote'` and `42` each give `_fragment_renders_empty → False` (content)
  but `_fragment_has_payload → False` (no payload). On the always-emit row `artifact-consistency`
  both land in `sections_written`; on the conditional row `script-failure-analysis` both land in
  `sections_omitted` with `dropped == []`. `_fragment_renders_empty`'s docstring claims the two
  discriminators are "genuinely consistent rather than merely described as such", which is true only
  for dicts.
- **Why it matters:** a fragment the compiler itself calls content is reported as *nothing was lost*
  — the quiet half of the partition swallowing a real loss, which is the exact failure mode this plan
  exists to eliminate, running in the opposite direction from D1.
- **Action:** in the non-emit branch, decide emptiness with the same predicate the render path uses
  (`_fragment_renders_empty`) rather than with `_fragment_has_payload` alone, so a non-empty non-dict
  trigger fragment is a DROP; keep the dict path delegating as it does today.
- **Done when:** `build_document('p','live',…, {'script-failure-analysis': 'prose'})` returns
  `dropped == ['Script Failure Analysis']`, and a parametrized test covers a string, an int and a
  list fragment on a conditional row.
- **Effort:** S
- **Risk if fixed:** any producer that legitimately writes a scalar for a conditional aspect would
  start raising the run status to `warning`; none does today, but the change interacts with G2–G4 and
  should land in the same decision.

## G2 — Stop classifying a clean `script-failure-analysis` run as a dropped section

- **Kind:** bug
- **Severity:** high
- **Topic:** detectors/auditor
- **Where:** `compile-report.py:550-559` + `_fragment_has_payload` at `:171-196`; producer shape at
  `script-failure-analysis.py:506-521`
- **Evidence:** executed at HEAD with the producer's real clean-run fragment
  (`status: success`, `plan_id`, `log_path`, `work_log_path`, `total_failures: 0`, `findings: []`,
  `lessons: []`): `should_emit: False`, `_fragment_has_payload: True`,
  `dropped: ['Script Failure Analysis']`, so `cmd_run` returns `status: warning`
  (`compile-report.py:653-655`). Declared as report residue 1 and left unfixed by design.
- **Why it matters:** every plan with no script failures — the common case — compiles a retrospective
  whose status is `warning` and whose `sections_dropped` names content that never existed. A loud
  signal that fires on every clean run stops being read, which is this epic's own thesis.
- **Action:** decide what `_fragment_has_payload` counts as content for a fragment whose own
  `status`/counters already say it produced nothing (provenance keys such as `plan_id`, `log_path`
  are the live trigger; the report's F19 correction records that stripping the provenance paths alone
  changes nothing, because `plan_id` is the first payload key). Apply the decision at the drop/omit
  boundary for every conditional row.
- **Done when:** compiling the real clean-run `script-failure-analysis` fragment yields
  `sections_dropped == []` and `status: success`, with a test built from the producer's own output
  rather than a hand-written fixture.
- **Effort:** M
- **Risk if fixed:** the same predicate governs every conditional row, so a too-broad rule could
  silence a genuine drop; the change needs the D1 invariant test suite green plus a differential over
  all eight deterministic producers.

## G3 — Stop classifying a manifest-less `manifest-decisions` skip as a dropped section

- **Kind:** bug
- **Severity:** medium
- **Topic:** detectors/auditor
- **Where:** `compile-report.py:550-559`; producer shape at
  `check-manifest-consistency.py:709-718` (`status: skipped`, `reason: '<file> not found'`,
  `checks: []`, `findings: []`, `summary: {...}`)
- **Evidence:** executed at HEAD on a manifest-less plan's real fragment pair →
  `dropped: ['Manifest Decisions', 'Routing Decisions']`. `references/report-structure.md:33` states
  the requirement it violates ("When a fragment is absent, has `status: skipped` … the compiler must
  omit the entire section"), with the divergence recorded beside it at `:37`.
- **Why it matters:** a plan that never had an `execution.toon` — every pre-manifest plan and every
  plan that legitimately skips the aspect — is reported as having lost content, and its retrospective
  status is `warning`.
- **Action:** exempt a fragment whose own `status` is in
  `retro_sections.ZERO_DECLARED_UNMEASURED_STATUSES` from the drop branch (it declared it produced
  nothing), or apply whatever rule G2 settles on; then delete the divergence paragraph at
  `report-structure.md:37-39` rather than leaving a recorded gap behind a closed one.
- **Done when:** compiling `check-manifest-consistency`'s real skipped fragment puts
  `Manifest Decisions` in `sections_omitted`, and `report-structure.md` no longer records a
  divergence for it.
- **Effort:** S
- **Risk if fixed:** a `skipped` fragment that *does* carry findings must keep rendering — the
  `chat-history-analysis` carve-out at `compile-report.py:132-135` depends on it.

## G4 — Stop classifying a manifest-less `routing-decisions` skip as a dropped section

- **Kind:** bug
- **Severity:** medium
- **Topic:** detectors/auditor
- **Where:** `compile-report.py:550-559`; producer shape at `check-routing-decisions.py:727-736`
- **Evidence:** same execution as G3 — `Routing Decisions` lands in `dropped` on a plan with no
  `execution.toon`.
- **Why it matters:** second instance of the same false loss signal, on the same common path; a
  single fix must be verified against both rows because their skipped shapes differ (`routing` has no
  `findings` key at all).
- **Action:** as G3, verified against this producer's own output rather than assumed to follow.
- **Done when:** compiling `check-routing-decisions`'s real skipped fragment puts
  `Routing Decisions` in `sections_omitted`.
- **Effort:** S
- **Risk if fixed:** `should_emit`'s routing-decisions carve-out (`compile-report.py:161-167`) must
  keep emitting the findings-less *success* shape; a change here must not narrow that.

## G5 — Resolve the dead `dispatch_boundaries` registry row

- **Kind:** omission
- **Severity:** medium
- **Topic:** detectors/auditor
- **Where:** `retro_sections.py:40` (the row) vs `analyze-logs.py:1692` (the data, nested inside the
  `log-analysis` fragment)
- **Evidence:** `SECTION_SPEC` keys − aspect-table keys = `['_executive-summary',
  'dispatch_boundaries']` (executed). No `--aspect dispatch_boundaries` command exists in `SKILL.md`
  or any document it names, so nothing can ever populate `fragments['dispatch_boundaries']`; the
  section is reported as a benign omission on every run while
  `render_dispatch_boundaries_body` (`compile-report.py:336-383`) is live and correct.
- **Why it matters:** a structurally unreachable section wearing the "nothing to say" face — the
  plan's own thesis, still live. Real per-phase dispatch-boundary data exists and never reaches the
  report's own section for it.
- **Action:** either register `dispatch_boundaries` as its own aspect (a producer step that writes
  the nested block to the top level) or delete the row and render the data from within Log Analysis;
  whichever is chosen, update `report-structure.md:17` in the same change.
- **Done when:** either a documented producer writes `fragments['dispatch_boundaries']` and the
  section renders on a plan that has boundary artifacts, or the row is gone from `SECTION_SPEC` and
  from `report-structure.md`.
- **Effort:** M
- **Risk if fixed:** deleting the row loses the per-phase table renderer's only call site; registering
  a new aspect widens the closed key set and touches the D3 aspect-table guard.

## G6 — Resolve the producerless `_executive-summary` row

- **Kind:** omission
- **Severity:** medium
- **Topic:** detectors/auditor
- **Where:** `retro_sections.py:32` (the row), `compile-report.py:527-548` (the consumer),
  `references/report-structure.md:13` (the requirement)
- **Evidence:** a tree-wide grep finds `_executive-summary` only in those three files — no producer
  writes one, and `collect-fragments.py:298-299` rejects `_`-prefixed keys outright. D1 removed the
  false *written* signal, so the headline section is now honestly omitted on every run; the compiled
  report therefore ships with no Executive Summary at all, while `report-structure.md:13` still lists
  it as section 1 of what "the compiler must emit".
- **Why it matters:** the document's headline synthesis — the part a reader reads first — is
  specified, renderable, and never produced. The specification and the shipped behaviour disagree.
- **Action:** add the documented orchestrator injection step that writes `_executive-summary` (the
  compiler already accepts a dict with `summary` or a bare string), or remove the row and the
  `report-structure.md` entry together.
- **Done when:** either a retrospective run on a normal plan lists `Executive Summary` in
  `sections_written`, or neither `SECTION_SPEC` nor `report-structure.md` names the section.
- **Effort:** M
- **Risk if fixed:** an injection step adds an LLM-authored surface to a compiler documented as a
  pure assembler; removing the row deletes the only section the compiler renders verbatim.

## G7 — Correct the "14 aspect references" lead-in in `plan-retrospective/SKILL.md`

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/SKILL.md:31`
- **Evidence:** *"dispatch the 14 aspect references in the documented order"* — the Step-3 aspect
  table at `:180-196` has **15** numbered rows (re-derived by parsing the live table).
- **Why it matters:** the sentence is the workflow's own execution-mode summary; a reader following
  it dispatches a count that does not match the roster, and one aspect is silently outside the
  documented population.
- **Action:** drop the figure and name the source instead — "dispatch every aspect in the Step-3
  aspect table, in the documented order" — per the standing prefer-naming-to-counting remedy.
- **Done when:** `SKILL.md` states no aspect count that a reader must reconcile with the table, and
  no line in the file asserts a number that the table contradicts.
- **Effort:** S
- **Risk if fixed:** none.

## G8 — Correct the "9 aspects" / "8 in-context analytical aspects" dispatch-shape figures

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `plan-retrospective/SKILL.md:52` (heading) and `:54` (body)
- **Evidence:** the heading reads *"Dispatch shape: 9 aspects iterate inside one envelope"*; the body
  reads *"The 8 in-context analytical aspects (metrics, decision/work logs, references vs
  deliverables, deliverable vs lesson alignment, scope-deviation footprint, behavioural observations,
  execution-context dispatch audit, chat-history aspect when `--session-id` is present, lesson-quality
  audit)"* — the parenthetical enumerates **nine** items under the label "8", and both figures
  disagree with the 15-row table.
- **Why it matters:** a sentence that miscounts its own inline list is a false claim in a shipped
  consumer-facing document, and it is the file that defines the dispatch envelope's cost argument
  ("Per-aspect dispatch would pay 8× envelope cost").
- **Action:** replace both figures with the named set, or re-derive them once and state which
  population each denominator is over (in-context analytical vs total rostered).
- **Done when:** the heading and body carry no count that the enumeration beside them contradicts.
- **Effort:** S
- **Risk if fixed:** the `8×` cost sentence must be re-derived alongside, not left orphaned.

## G9 — Add the `registry → table` direction to the aspect-table correspondence guard

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `test/plan-marshall/plan-retrospective/test_registered_aspects_render.py:321-404`
  (`TestAspectTableKeysMatchTheRegistry`)
- **Evidence:** the class docstring states the limitation itself: *"The correspondence is checked in
  ONE direction only — `table → registry`. A `SECTION_SPEC` row shipped with no table row is caught
  by nothing here"*. Re-derived: `SECTION_SPEC` keys − table keys = `['_executive-summary',
  'dispatch_boundaries']`, which is exactly why the reverse assertion is not shipped.
- **Why it matters:** a new registry row added without a table row ships undocumented and its
  registration key is unobtainable from the document that instructs registrations — the defect D3
  exists to prevent, uncovered in the other direction.
- **Action:** once G5 and G6 land, add the reverse assertion (`_spec_fragment_keys()` minus
  `_`-prefixed keys ⊆ scanned table keys) with no exemption list.
- **Done when:** the reverse assertion exists, has no exemptions, and passes.
- **Effort:** S
- **Risk if fixed:** adding it before G5/G6 would require encoding the two dead rows as exemptions,
  which pins them in place — do not.

## G10 — Remove the historical clause from `plan-retrospective/SKILL.md` § Step 4

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `plan-retrospective/SKILL.md:311`
- **Evidence:** *"…deliberately **not enumerated here**: an earlier version of this sentence listed
  the fields and then told the reader not to restate them, and it was left naming three when the
  registry had grown to five."* `CLAUDE.md` § Documentation Standards forbids version history and
  transitional narrative in documentation; the file is exempt from plugin-doctor's
  `no-historical-prose-in-skills` only because `plan-retrospective/**` is allowlisted in
  `rule-provenance.md:205`, so the gate cannot catch it.
- **Why it matters:** a shipped consumer-facing skill carries a paragraph about its own editing
  history, which is precisely the class the standard removes; the rule that would have caught it is
  suppressed by an allowlist, so nothing else will.
- **Action:** keep the present-tense instruction ("the vocabularies are declared in
  `scripts/retro_sections.py`; read them there") and delete the clause about the earlier version.
- **Done when:** `SKILL.md` contains no sentence describing what an earlier version of itself said.
- **Effort:** S
- **Risk if fixed:** none.

## G11 — Remove the attempt narrative from `_fragment_renders_empty`'s docstring

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `compile-report.py:441-447`
- **Evidence:** *"⛔ **A non-empty CONTAINER is not the same as a usable BODY**, and testing the
  container was one of several attempts that each closed a narrower case than the invariant needs —
  no count is given here, because a count of attempts goes stale on the next one."*
- **Why it matters:** the docstring of a shipped script records this plan's development history
  rather than the predicate's present contract; a reader has to filter run narrative out of an API
  description, and the same standard that governs skill prose governs the bundle's code docs.
- **Action:** state the rule ("a non-empty container is not a usable body, so for a dict the question
  delegates to `_fragment_has_payload`") and drop the reference to previous attempts.
- **Done when:** the docstring describes only the current predicate and its rationale.
- **Effort:** S
- **Risk if fixed:** the delegation rationale must survive the trim — it is the load-bearing half.

## G12 — Remove the sweep narrative from the `ZERO_ATTRIBUTION_FIELDS` comment block

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `retro_sections.py:132-147`
- **Evidence:** *"Those last two were added after a sweep over the eight in-tree deterministic
  producers, which flagged `check-artifact-consistency` and `summarize-invariants` on every clean
  run."*
- **Why it matters:** same class as G11 — the registry's comment describes when and why two entries
  were appended rather than what the vocabulary means now, and it is the block a future editor reads
  before adding a sixth field.
- **Action:** keep the per-field citations (which are current-state and load-bearing) and the live
  population note; delete the "were added after a sweep" framing.
- **Done when:** the comment block states only what each name means and where each producer publishes
  it.
- **Effort:** S
- **Risk if fixed:** the citations must not be dropped with the narrative — they are what makes the
  vocabulary derived rather than invented.

## G13 — Fold a pre-list plan's legacy `session_id` into `session_ids` on first append

- **Kind:** incomplete
- **Severity:** low
- **Topic:** dispatch/finalize
- **Where:** `claude_runtime.py:1568-1594` (`_manage_status_read_session`) and
  `_status_query.py:190-238` (`_cmd_metadata_append`)
- **Evidence:** `test_a_resume_on_a_pre_list_plan_does_not_fail`
  (`test/plan-marshall/manage-status/test_manage_status_metadata.py:328-357`) asserts that after a
  resume the list is `['sess-resumed']` while the retired scalar still holds `sess-original`; the
  read path prefers the list whenever it is present
  (`test_the_list_wins_over_a_stale_legacy_scalar`), so the pre-list session's identity becomes
  unreachable through the resolver the moment the list exists.
- **Why it matters:** D4's stated goal is that "a multi-session run is representable" and that "the
  measured plan's identities survive". For a plan that spans the change, one identity survives in
  `status.json` but not in the list any consumer reads — the loss D4 removed going forward is still
  present across the boundary.
- **Action:** on the first append to `session_ids` for a plan whose `session_id` scalar is present
  and whose list is absent, seed the list with the scalar before appending (leaving the scalar in
  place for the shim), or state explicitly in the shim comment that the pre-list identity is
  deliberately not carried over.
- **Done when:** appending to a plan carrying only the legacy scalar yields
  `session_ids == ['<legacy>', '<new>']`, or the shim block records the deliberate non-migration with
  its reason.
- **Effort:** S
- **Risk if fixed:** the seeding must stay idempotent and must not fire for a plan whose list already
  exists, or a repeated capture would reinsert a retired identity.

## G14 — Document the intended consumer action for `sections_unattributed_zero`

- **Kind:** incomplete
- **Severity:** low
- **Topic:** bundle-docs
- **Where:** `plan-retrospective/SKILL.md:311` and `references/report-structure.md:65`; producer at
  `compile-report.py:663`
- **Evidence:** both documents describe the signal correctly and both stop at "it is reported"; no
  step in the workflow instructs the agent to read it, act on it, or surface it, and the compiled
  markdown document does not carry it. `grep -rn sections_unattributed_zero marketplace/ test/`
  returns exactly three hits — the producer and the two descriptions — and no consumer.
- **Why it matters:** D1's second half exists to make an ambiguous zero visible; a signal emitted only
  into the script's TOON result, with no documented reader, can be ignored without anyone noticing —
  which is the same silent-death mode as the dead registry rows this plan measured.
- **Action:** name the consumer action in the Step-4 instruction (for example: when the list is
  non-empty, the retrospective names those sections in its own summary), or record explicitly that
  the signal is diagnostic-only and consumed by nothing.
- **Done when:** a reader of `SKILL.md` Step 4 can say what to do when `sections_unattributed_zero`
  is non-empty.
- **Effort:** S
- **Risk if fixed:** wiring it into any gate would blur an ambiguity signal with the content-loss
  signal, which the design deliberately keeps separate — the action must stay non-gating.

## G15 — Correct the merge-gate head recorded in the run report

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `report-01.md` § Contract check (Step 9), row "8 Merge gate"
- **Evidence:** the row reads *"conditions 1–3 met on head `2dd1b31` … then auto-merge armed"*. The
  PR's merged head is `1e0354390e6aed68afaa40e19d5dc53c8137adb3` (one commit later); the
  `verify / conclusion` check that gated the merge ran against that head (success 01:37:22Z, merge
  01:53:25Z). The run *did* disclose the moved head in a PR comment, but the report's contract-check
  row does not.
- **Why it matters:** the contract-check table is the run's own record of which tree the gate was
  established on; a head that is not the merged head makes the record unusable for a later reader
  reconstructing what CI actually verified.
- **Action:** restate the row against the merged head and note that the final commit was the report's
  own participation update, with CI re-established there.
- **Done when:** the row names `1e03543` (or names both heads and what moved between them).
- **Effort:** S
- **Risk if fixed:** none.

## G16 — Record a disposition for the plan's sequencing warning

- **Kind:** report-defect
- **Severity:** low
- **Topic:** plan-lane-contract
- **Where:** `report-01.md` (absent throughout); the instruction is `plan.md` § Notes,
  "⛔⛔ **Sequencing warning** … Coordinate before starting; do not treat it as a finalize-time
  discovery."
- **Evidence:** a case-insensitive search of `report-01.md` for *sequenc*, *ordering*, *coordinat*,
  *destroyed input* and *footprint* returns one unrelated hit ("reordering the columns"). The warning
  has no disposition anywhere in the report — not addressed, not deferred, not declared moot.
- **Why it matters:** the warning states that this plan "can be fully correct and still render a
  destroyed input", which is a correctness condition on everything the plan shipped. A reader cannot
  tell whether it was considered. (Substantively it appears covered: the sibling plan
  `250-footprint-read-outside-its-window` has landed and the footprint resolver now falls back to a
  persisted realized-footprint capture — see `plan-retrospective/SKILL.md:200`.)
- **Action:** add a line to the report recording the warning's disposition and the evidence for it
  (the sibling plan and the resolver fallback), so the obligation is closed on the record rather than
  silently.
- **Done when:** `report-01.md` names the sequencing warning and states its disposition.
- **Effort:** S
- **Risk if fixed:** none.
