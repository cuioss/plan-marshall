envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=finding
created=2026-08-01T21:27:36Z

## Finding: `manage-change-ledger append --commit-sha` performs NO existence validation

**Observed in**: main, during execution of `mandatory-plan-id-build-results-ledger`.
**Scope**: outside every deliverable of this plan. Deliberately NOT fixed here.

### What was observed

`manage-change-ledger append --commit-sha <value>` accepted a **fabricated sha** — a value
that resolves to no object in the repository — and wrote it into the traceability ledger
without complaint. The append returned success.

### Why it matters

The change ledger's entire value proposition is *traceability*: a ledger row asserts that
a named change is anchored to a real commit. A row carrying a sha that does not exist is
not a weak anchor, it is a **false anchor** — it reads exactly like a valid one to every
downstream consumer, and no consumer re-validates. The ledger therefore reports a
confident provenance claim it never checked.

This is directly on this epic's theme, and it is a companion to the plan's own subject
matter: `PLAN-TRUTH-026` made build attribution mandatory, but attribution to a
**non-existent** commit is still unattributed in every sense that matters.

### Suggested shape of a fix (not implemented)

- Validate `--commit-sha` against the repository (`git cat-file -e {sha}^{commit}` or the
  equivalent through the project's git seam) before the append is accepted.
- Decide deliberately whether an unresolvable sha is a hard refusal or a row written with
  an explicit `sha_verified: false` discriminator — but do not keep the current state,
  where an unverified sha is indistinguishable from a verified one.
