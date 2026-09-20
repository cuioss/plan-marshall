envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-09T07:59:31Z

component=plan-marshall:automatic-review
category=bug

# SKILL.md prose names review_completeness flags the live argparse surface rejects (--enabled-bots/--settled-bots vs --participated-bots/--refused-bots)

⛔ **RELOCATED FROM THE WRONG STORE — this is a MOVE, not a new report.** It was filed as lesson
`2026-09-08-18-001` in **Token-Sheriff's** lessons store, whose repo does not own the `plan-marshall` bundle.
It is written here first and removed there second (integrate-then-remove), so exactly one copy
exists at every point and none exists in two places.

Origin: Token-Sheriff epic `lessons-handling-26-09-04-01`. Original id `2026-09-08-18-001`, created 2026-09-08, lifecycle `active` at the time of the move.
⚠ Nine such lessons accumulated because a plan overrode the `wrong_store` guard rather than
routing the lesson to the repo that owns the bundle — the mechanism is reported separately as
`lessons-handling-26-09-04-01-032`. Body reproduced verbatim below.

---

## Context

Observed in TokenSheriff plan `refresh-2a-coverage-priorities`, 2026-09-08, running the
`plan-marshall:automatic-review` FIND step against PR #725.

The D3 completeness guard invoked as `automatic-review/SKILL.md`'s prose documents it — with
`--enabled-bots` / `--settled-bots` — was **rejected by the live script with exit 2**. The actual
argparse surface of `review_completeness check` is `--required-bots` / `--optional-bots` /
`--participated-bots` / `--refused-bots` / `--refused-causes` / `--refusal-size-caps` /
`--measured-diff-size`, and it has no `--triage-ran` flag either.

The dispatched agent recovered correctly: it read the live `--help`, invoked the real surface, and
got `participation_complete: true`. It did not paraphrase a plausible-looking flag into existence,
and it did not record the guard as skipped.

## Impact

This is the argparse-rejection recurrence signature that
`persona-plan-marshall-agent` § \"Never invent script subcommands\" exists to prevent — except the
invented form here is the one the SKILL's own prose prescribes, so an agent that followed the
document faithfully produces the failure. Exit 2 bypasses the script body entirely, so the
completeness guard does not run.

The failure is quiet in the direction that matters. `review_completeness` is what establishes that
every REQUIRED review bot actually participated; a silent non-run leaves the plan believing bot
participation was verified when nothing checked it. On this run that would have mattered: one
required bot (`cuioss-review-bot`) participated with zero storable findings and one optional bot
(`sourcery`) refused structurally on a diff-size cap — a shape where \"no findings\" and \"no review\"
look identical from the findings store alone, and only the guard distinguishes them.

## Directive

Update `automatic-review/SKILL.md`'s D3 prose to the live flag names, and add the invocation to that
skill's § Canonical invocations so the `manage-invocation-invalid` doctor rule — which derives its
accept-set from a live `--help` walk — can catch the next divergence at quality-gate time rather
than at dispatch time.

The general rule this run re-confirms: when a documented invocation is rejected with exit 2, read
the live `--help` and use the real surface; never adjust the call until something is accepted, and
never record the guard as run when it was not.
