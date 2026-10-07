envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-10T17:28:54Z

component=plan-marshall:phase-1-init
category=bug

# File-pointer ingestion: spec headings truncate section-scoped classifiers at init

⛔ **RELOCATED FROM THE WRONG STORE — a MOVE, not a new report, and the SECOND such batch.**
Filed as lesson `2026-09-09-13-001` in **Token-Sheriff's** store, whose repo does not own the `plan-marshall`
bundle. Written here first and removed there second (integrate-then-remove).

⚠ **The pattern RECURRED.** Nine such lessons were relocated on 2026-09-09 and the mechanism was
reported as `-032`; PLAN-08 then routed its lessons correctly to the epic inbox, but PLAN-09 filed
these two into the local store again. So the `wrong_store` override is **not** reliably avoided —
it depends on which path a plan happens to take. That recurrence is itself the signal.

Origin: Token-Sheriff epic `lessons-handling-26-09-04-01`, original id `2026-09-09-13-001`, created 2026-09-09.
Body verbatim below.

---

## Observation

On the phase-1-init Step 4 **file-pointer branch** (`implement {path}`), the referenced spec is ingested
verbatim into `request.md` under the `## Original Input` heading. When the ingested spec carries its own
`##` headings — which any real spec does — every **section-scoped** reader of `request.md` stops at the
first embedded `##` and therefore sees only the two or three lines between `## Original Input` and the
spec's own first heading.

Measured on plan `mtls-alpha-reclassification` (2026-09-09), ingesting a 15 KB spec with 39 declared paths:

| Reader | Scoping | Result |
|---|---|---|
| `manage-config domain-detect` | section-scoped | 0 alias matches -> `reason=over_provisioned_always_on_only`, domains over-provisioned to all 5 including an irrelevant `javascript` |
| `manage-status change-type-heuristic` | section-scoped | every score 0.0 -> `ambiguous: true`, `persisted: false`, `change_type` left unset |
| `manage-status scope-estimate-heuristic` | **heading-blind** (documented) | correct: 39 distinct paths -> `multi_module` |

The heading-blind sensor reading correctly while the two section-scoped ones read nothing is the
controlled comparison: the spec body IS present and complete in `request.md`; only the section-scoped
readers cannot see past the embedded heading.

## Why this matters

`scope-estimate-heuristic` is already documented as heading-blind (\"the entire file minus its own
`# Request` title line, with no section selected, so an ingested spec's own `##` headings cannot truncate
the scored text\"). So the defect class is **known and was fixed for exactly one sensor**. The other two
readers on the same ingestion path were not migrated, and they fail silently — each returns a
well-formed `status: success` whose zero/ambiguous verdict is indistinguishable from a genuine
\"nothing matched\".

Downstream consequences observed on this plan:

- Domains over-provisioned (a `javascript` domain on a Java + AsciiDoc plan), so refine/outline carry
  standards that do not apply.
- `change_type` left unset, so the planning-lane router's S3 signal cannot fire at all; the run reported
  `signals_null: 2` and `low_confidence: true`. The lane still resolved `deep` correctly, but off S2 and
  S7 only — the correct answer for the wrong reason.

## Directive

Make every `request.md` classifier on the file-pointer ingestion path heading-blind, exactly as
`scope-estimate-heuristic` already is:

- `manage-config domain-detect`
- `manage-status change-type-heuristic`

Scoring the whole body minus the `# Request` title line is the established remedy in this codebase — this
is applying an existing fix to the two readers it was never propagated to, not inventing one.

Secondary (separate concern, lower value): `manage-config recipe-match` and `aspect-classify` accept only
`--request-text` with no `--request-file`, so a caller on the file-pointer branch cannot pass the ingested
spec verbatim — this spec carried 93 shell-hazardous lines, making the shell argument unsafe. The
init run had to score a condensed summary instead of the verbatim body, which the workflow explicitly
does not want (\"the LLM never retypes, paraphrases, or summarises the spec body\"). A `--request-file`
flag on both verbs would close it.
