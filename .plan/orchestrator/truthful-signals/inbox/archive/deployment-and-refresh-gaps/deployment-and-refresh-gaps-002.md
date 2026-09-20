envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=candidate-lesson
created=2026-09-02T20:14:33Z

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, plan `coverage-gate-visibility` (PR #681), original message `coverage-gate-visibility-002.md`.
> Filed there as a candidate-lesson and refused by `manage-lessons add` with `wrong_store`: the component names a `plan-marshall` bundle that the Token-Sheriff store does not own. Content is unmodified below.

component=plan-marshall:phase-6-finalize
category=anti-pattern
source_plan=coverage-gate-visibility
source_epic=deployment-and-refresh-gaps

# A review finding's diagnosis and its proposed resolution are separately falsifiable — settle both against the primary source, walked to its root

## The rule

A finding arrives as two claims welded together: *this is wrong* (diagnosis) and
*here is what it should say instead* (resolution). They fail independently. A
correct diagnosis routinely ships with an inferred resolution that is itself
false, and a confident diagnosis routinely rests on a source read only partway.

So the disposition of a finding is never "the finding is right, apply it" or "the
finding is wrong, dismiss it". It is two verdicts, each settled against the
PRIMARY SOURCE — and for anything inherited, the primary source is the full
ancestor chain, not the nearest ancestor that happens to mention the subject.

This run produced one clean instance of each failure mode.

## Instance 1 — correct diagnosis, wrong inferred fix (internal self-review)

`pre-submission-self-review` flagged genuinely ambiguous `AGENTS.md` wording about
the inherited coverage rule. The diagnosis was sound: the prose really was
ambiguous. Its inferred resolution was that "the bundle gate is BRANCH-only".

Checked against the primary source — `cui-java-parent-1.5.10.pom` lines 409-421 —
the `element=BUNDLE` rule gates BOTH limits:

- `INSTRUCTION` ratio >= 0.80
- `BRANCH` ratio >= 0.80

Applying the finding as written would have replaced ambiguous prose with a NEW
false claim, and would have read as a fix because the diagnosis it rode in on was
correct.

Note what could NOT have settled it: the project's own existing prose said the
same wrong thing at three separate sites. Corroboration across sites in the same
repo is not corroboration — it is one claim counted three times. Only the POM
settles what the POM enforces.

## Instance 2 — confident diagnosis from an incomplete inheritance walk (external bot)

CodeRabbit filed a MAJOR finding: jacoco `prepare-agent` runs only inside
`cui-java-parent`'s inactive coverage profile, therefore the default build lane is
uninstrumented and the whole coverage gate is decorative.

It had read the PARENT and stopped there. The binding is one level further up, in
the GRANDPARENT `cui-parent-pom-1.5.10.pom`: `prepare-agent` and `report` are
bound in the DEFAULT `pluginManagement` block (block opens line 157, the
executions sit at lines 486-505), with no enclosing profile. The finding was a
false positive produced entirely by where the walk stopped.

It was also refutable without reading any POM at all: this plan's own negative
control turned a plain `verify` RED and reported real per-class coverage ratios.
Instrumentation that does not run cannot produce ratios. When a static reading and
a behavioural observation disagree about whether something executes, the
behavioural observation wins.

## Practice

1. Split every finding into diagnosis and resolution and rule on them separately.
   Record both verdicts. "Valid finding" is not a disposition.
2. Settle each verdict against the primary source — the POM, the schema, the
   argparse declaration, the plugin's own docs. Never against the finding's own
   reasoning, and never against the project's existing prose, which is exactly the
   artifact under suspicion.
3. For any inherited or layered configuration, walk to the ROOT before concluding
   a binding is absent. "Not in the parent" is not "not bound".
4. Prefer an empirical disposition where one exists. A negative control that
   already ran outranks a re-reading of the config.
5. A correct diagnosis is not a licence to apply the attached fix. This run's fix
   went in the OPPOSITE direction from the one the finding proposed, and the
   finding was still worth filing.
