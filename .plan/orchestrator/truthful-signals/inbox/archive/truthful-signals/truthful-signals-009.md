envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=truthful-signals
kind=finding
created=2026-09-14T07:53:03Z
revision=4
amended=2026-09-14T08:11:35Z
lifecycle=superseded
superseded_by=next-level-001.md

# The instruction corpus is calibrated for one model it does not name, and ships byte-identical to a fleet it cannot vary for

Filed 2026-09-14 from an operator-directed analysis. Revision 1 added the three primary sources.
⭐⭐ **Revision 2 changes what the finding is about.** Revisions 0–1 framed it as *stale guardrails
should be pruned*. An operator constraint — plan-marshall is run on models other than Claude, with
OpenCode currently under test on Muse Spark 1.3, DeepSeek v4.1 Flash and Gemini 3.8 Flash, and Codex
planned — inverts that. ⛔ **The de-escalation sweep proposed in revision 1 is unsafe as written, and
this revision retracts it as a standalone deliverable.** What remains is a sharper and more valuable
finding: the corpus has **one calibration knob and a fleet of models behind it**, and no mechanism to
tell them apart.

⚠ Revision 3 corrected a factual error in revision 2, which counted `pr_agent` as a third runtime
consumer. It is a review-artifact export, not a runtime. That correction moved the variance axis from
*target* to *model*, ruling out the mechanism revision 2 had suggested.

⭐⭐ **Revision 4 adds the `antigravity` target — in development now, for the Gemini models — and with
it the timing argument that makes this urgent rather than merely true.** The fleet is being widened
*while the mechanism stays fixed*: the in-flight target imports the same vocabulary-only transform
engine and introduces no calibration axis. **A third runtime is the cheapest moment to settle this
question and the last cheap one** — the cost of retrofitting a calibration axis rises with every
target that ships without one, and every consumer repository that pins to their output.

## Sources

| # | Page | Status |
|---|---|---|
| 1 | `platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices` | Primary, fetched, quoted below |
| 2 | `platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-hallucinations` | Primary, fetched |
| 3 | `docs.claude.com/…/prompt-engineering/overview` | 302 → `platform.claude.com/…/overview`; a stub that delegates to #1 |

⛔ **All three are Anthropic documents about Anthropic models.** In revision 1 that was unremarkable.
Under the multi-model constraint it is the central caveat: **every prescription quoted below is
model-scoped guidance, and this corpus does not ship to one model.** Sources for the non-Anthropic
models in the fleet were not consulted and none of their behaviour is characterised here.

The originating article is untrusted external content and is not evidence; it supplied framing only.
Its two quotes were checked and are verbatim from #1. ⛔ Its two unverifiable claims (an "adaptive
thinking beats manual reasoning budgets" evaluation result, and a "July 2026 memory update") appear in
**none** of the three sources and are **not carried**.

## The mechanism finding (new in revision 2, and the reason this is worth a plan)

Measured in this checkout at `main` `77cb2e251`:

- `TARGET_REGISTRY` (`marketplace/targets/__init__.py`) registers three names on `main`, but only
  **two** are runtimes that consume the workflow corpus: **`claude` and `opencode`**. ⛔ **`pr_agent`
  is NOT a runtime and must not be counted as one** — `PrAgentTarget` sets `emits_bundle_tree = False`
  and emits "a REVIEWER ARTIFACT SET rather than an assistant bundle tree" (one instruction-pack
  artifact per derived domain, plus a spine, under `{output_dir}/packs/`). It is a review-instruction
  export; it executes no plan and runs no workflow. An earlier revision of this message listed it as
  a third consumer — that was wrong, and the correction relocates the variance axis; see below.
- ⭐ **A third runtime is in development: `antigravity`, the target for the Gemini models.**
  Operator-stated, and corroborated in the `antigravity` worktree: `marketplace/targets/antigravity/`
  is present and **untracked**, with `marketplace/targets/__init__.py` and `pyproject.toml` modified;
  `AntigravityTarget` is documented as the "concrete Google Antigravity build target" with
  `supports_agents` and `supports_commands` both true. ⚠ Nothing has landed — branch
  `feature/antigravity` sits at `53ab7dd2e`, an ancestor of `main`, so the work is entirely
  uncommitted. Treat every detail here as a snapshot of in-flight work, not as contract.
- The shared body-transform engine (`marketplace/targets/body_transform_engine.py`) applies exactly
  **three** line-level transforms: structural load directives (`Skill:`, `Read:`), the slash-command
  rewrite, and registered tool-idiom rewrites (`AskUserQuestion`, `Task:`). All are data-driven from
  each target's `mapping.json`.
- Component-level target scoping exists via `targets:` frontmatter, but is **all-or-nothing** and is
  used by **6 components** corpus-wide, every one of them `targets: [claude]`.

⭐⭐ **The generator translates vocabulary, not calibration.** It rewrites *what a tool is called* and
*how a skill is loaded*. Nothing in it can vary *how emphatically an instruction is stated* or *how
much verification scaffolding a workflow carries*. Those travel in prose, and prose is emitted
byte-identical to every target.

⛔ **So there is no expressive mechanism for per-model instruction calibration, and an all-or-nothing
component switch is not one** — the unit of divergence is a whole skill, not a paragraph, and no
existing component uses it for calibration.

⭐⭐ **And the variance axis is MODEL, not TARGET — which is why a per-target mechanism cannot solve
this.** The operator-stated fleet, as of this revision:

| Runtime target | Models | State |
|---|---|---|
| `claude` | Claude | On `main` |
| `opencode` | Muse Spark 1.3, DeepSeek v4.1 Flash | On `main`, under test |
| `antigravity` | the Gemini models | **In development**, nothing landed |
| Codex | — | Planned |

⚠ The model→target mapping is operator-stated and has moved during this analysis; re-confirm it
rather than quoting this table as settled.

Two consequences, and the second is the one that matters:

- **`opencode` is ONE target hosting MANY models**, so the fleet's diversity lives **below** target
  granularity. ⛔ **Extending `targets:` scoping to paragraph level would still not express it**:
  `targets: [opencode]` cannot distinguish Muse Spark 1.3 from DeepSeek v4.1 Flash, and those two may
  well need different calibration from each other.
- ⛔⛔ **`antigravity` inherits the same vocabulary-only translation and adds no calibration axis.**
  `AntigravityTarget` imports `build_user_invocable_lookup`, `load_transform_rules` and
  `make_body_transformer` from the shared `body_transform_engine` — the identical three transforms,
  supplied as data from its own `mapping.json`. **The fleet is widening while the mechanism stays
  fixed.** A third runtime is being added under an architecture that can translate what a tool is
  called but cannot vary how an instruction is calibrated.

Any mechanism therefore has to key on **model or capability tier**, and no such axis exists anywhere
in the generator today or in the in-flight target.

## Why that makes revision 1's settlement unsafe

Revision 1 quoted #1's Opus 5 prescription:

> "Claude Opus 5 is the exception: it verifies its own work well without explicit instruction, and
> verification instructions carried over from prompts tuned for earlier models can cause
> over-verification, adding tokens and latency. **When migrating to Claude Opus 5, remove these
> instructions rather than rewriting them.**"

and #1's overtriggering prescription:

> "If your prompts were designed to reduce undertriggering on tools or skills, these models may now
> overtrigger. The fix is to dial back any aggressive language. Where you might have said 'CRITICAL:
> You MUST use this tool when...', you can use more normal prompting like 'Use this tool when...'."

Both say *remove scaffolding because this model no longer needs it*. Applied to a shared corpus, that
removes it for **every** consumer — including models whose need for it is entirely unmeasured.

⚠ **The obvious intuition here must not be stated as fact, and this message declines to state it.**
It is tempting to assert that flash-tier and smaller models under-trigger and therefore need the
scaffolding Opus 5 does not. ⛔ **No evidence for that was gathered about Muse Spark 1.3, DeepSeek
v4.1 Flash, or Gemini 3.8 Flash, and asserting it would be exactly the confident-signal-without-
provenance defect this epic exists to catch.** It is the *hypothesis that makes the sweep risky* —
which is sufficient to gate the sweep, and insufficient to design against. Establishing it, or
refuting it, is the work.

## The eval gap that compounds it

`CLAUDE.md` states plainly: *"only Claude Code is tested as a runtime."* The test tree corroborates —
`test/marketplace/targets`, `test/sync-opencode`, `test/plan-marshall/platform-runtime/
test_opencode_runtime.py` and the adapter tests are **structural**: they assert emission, frontmatter
mapping, registration lockstep and executor resolution. ⛔ **No behavioural or eval harness for any
non-Claude runtime was found.**

Reference #3 requires success criteria and empirical tests *before* prompt engineering, and warns
*"not every success criteria or failing eval is best solved by prompt engineering."* Combine the two:
a calibration sweep tuned on Claude would land on the fleet with **zero regression signal on precisely
the models most likely to be harmed by it**. The regression would surface as quietly worse results on
a runtime nobody measures — which is the least detectable failure mode available.

## What the corpus measurements now mean

Corpus: `marketplace/bundles/**/*.md` at `77cb2e251` — 689 files, 174,800 lines. Occurrences, not
lines. These size a **surface**; under revision 2 they are explicitly **not** a remediation backlog.

| Exposure (all per #1, Anthropic models only) | Measured corpus exposure |
|---|---|
| A — emphatic tool/skill instruction → overtriggering | 1,446 caps-emphasis tokens (`CRITICAL` 146, `MUST` 1,036, `NEVER` 119, `ALWAYS` 25, + `MANDATORY`/`REQUIRED`/`IMPORTANT`); `must` any case 2,499; `if in doubt` 15 |
| B — carried-over verification instruction → over-verification | 2,193 verification-instruction occurrences across **341 of 689 files**; 175 thoroughness intensifiers |
| C — subagent overspawn | ⚠ **Not measured.** Structural relevance only, via the `execution-context*` dispatch surface |

⚠ PLAN-TRUTH-089's finalize gate (81% of a 13.9M-token run; self-review ×19; all 17 loop-back
iterations consumed) remains a *second candidate mechanism* under Exposure B, **not** a re-diagnosis:
⛔ the self-seeded-findings diagnosis was not re-examined and is not disputed. Both could be live.

## What this does NOT establish

- **Exposure counts are exposure, not defect.** A `MUST` is a problem only if it overtriggers *here*.
  Nothing was instrumented in this repository.
- **No non-Anthropic model behaviour is characterised.** Not asserted, not inferred, not assumed.
- **Model-version scoping is real.** Exposure A is stated for Opus 4.5/4.6; Exposure B's carve-out for
  Opus 5 specifically. Sweeping every rule against one model's behaviour reproduces the original error
  at a new date — and under revision 2, against one *vendor's* behaviour as well.
- **The 468-of-3,321 remedy ratio from revision 0 is still not a defect rate.** A sample showed the
  remainder is dominated by legitimate *descriptive* negation stating contract semantics (`never 0`,
  `never touches marshal.json`). The regex cannot separate normative from descriptive negation; the
  true bare-fence population is **unknown and not derived here**, and any plan must derive it.
- Reflexive XML scaffolding (**3**) and manual chain-of-thought (**4**) remain non-issues. Uncertainty
  permission is already dense (**793** phrases, **775** `indeterminate`/`unknown` tokens) — #2's lead
  technique, *"Allow Claude to say 'I don't know'"*, is **already satisfied**.

## The one settled correction, which survives the multi-model constraint intact

The originating article presented "phrase instructions positively, not negatively" as **general**
advice. It is not. In #1 that rule sits under the heading **"Control the format of responses"** and is
scoped to output formatting. #1's own recommended anti-hallucination prompt runs the other way:

> "`<investigate_before_answering>` **Never** speculate about code you have not opened. If the user
> references a specific file, you **MUST** read the file before answering…"

⛔ **A blanket de-negation sweep would be a defect, not a fix** — it would strip the very form the
source recommends for grounding and safety rules. This holds regardless of which model consumes the
corpus, so it is the one conclusion revision 2 does not have to qualify. Raw negation density
(`never` 4,015; `do not`-family 3,107; `⛔` 308) is therefore **not by itself a defect signal**.

## Why it belongs in this epic

The shape, restated for revision 2: **the corpus presents as universal instruction while being
calibrated against one model's observed behaviour — which it does not name, cannot vary, and never
re-tests.** Every `⛔` is a patch for a failure some model, on some runtime, once exhibited. Its
continued necessity is a claim about current behaviour across the whole fleet, and that claim is
undated, unattributed and unverified.

The cost case is unchanged and still argues for doing the work: resident context is ~99% of billing
weight at 44.6× average byte re-read, so obsolete instruction is a permanent per-plan tax, and #1 says
Exposure B's instruction is not merely dead weight but *actively generating extra tokens and latency*.
⚠ **But the saving is now conditional on not regressing the fleet**, which is the whole difficulty.

## Suggested settlement (leads, not instructions — nothing prototyped or sized)

Ordered so that nothing destructive precedes the evidence that would justify it.

0. ⭐ **Decide the calibration-axis question while `antigravity` is still in flight.** Not an
   implementation — a decision, and the only time-sensitive item here. Either the generator grows a
   model/tier axis or it is deliberately declared out of scope; both are acceptable, and drifting
   into the second by default while shipping a third target is not. ⚠ This does **not** gate the
   antigravity work, and nothing in this message should be read as asking to hold it.
1. **Cross-model eval coverage first.** The gating deliverable for any *edit*, and the one with
   standalone value whatever the outcome. Without a behavioural signal on the OpenCode and
   Antigravity runtimes there is no way to tell a calibration improvement from a silent fleet
   regression. #3's precondition makes this mandatory rather than preferable.
2. **Characterise divergence before designing for it.** Measure whether the fleet actually diverges on
   scaffolding sensitivity. ⛔ If it does not, the whole calibration-variance question dissolves and
   only the far cheaper provenance work remains — so this step can *retire* deliverables 3 and 4, and
   should be allowed to.
3. **Provenance, extended.** Stamp normative rules with the motivating incident **and the model and
   target observed** — the target axis is new in revision 2 and is what makes a future sweep able to
   reason about the fleet at all. Cheap, non-destructive, independently useful, and safe to do before
   the evals land.
4. **A calibration-variance mechanism — only if 2 shows divergence.** Today there is none below
   whole-component granularity. ⛔ **Do not scope this per-target**: the fleet's diversity lives below
   target granularity (one `opencode` target, many models), so paragraph-level `targets:` scoping and
   a per-target `mapping.json` calibration layer are both **insufficient by construction**. The axis
   must be model or capability tier. Whether that becomes a new generator axis, or a deliberate
   decision to hold the corpus at the weakest supported model's calibration, is a design question this
   message does not answer. ⭐ The cheapest option is the latter, and it costs Claude runs some tokens
   rather than costing the fleet correctness.
5. **⛔ Do NOT run a Claude-tuned de-escalation sweep on the shared corpus.** Revision 1 proposed this
   as deliverables 3 and 4; revision 2 retracts it. It may only return scoped behind 1 and 2, and even
   then only through whatever mechanism 4 settles on.
6. **Check duplication before staging.** The remedy-pairing idea overlaps the **vacuous-guard**
   archetype in the WS-10 defect list (n≥6). Reconcile rather than opening a parallel track.

## Routing note

Not PR/review subject matter, so the PR test does not claim it for `review-apparatus`. It is a
corpus-wide truthfulness property of the instruction substrate, now with a multi-target delivery
dimension. ⚠ **If the epic judges the mechanism half (deliverables 2–4) to be primarily a
build/generator concern rather than a signal-truthfulness concern, it may belong with the
multi-target generator work instead — the split is a routing decision this message does not make.**
