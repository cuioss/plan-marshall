envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-08-26-01
epic=truthful-signals
kind=finding
created=2026-08-26T21:12:12Z

# A routed build loses tests_run and asserts "this run tested nothing" — four independent observations

**From:** `lessons-handling-26-08-26-01` (lessons-drain router). Routed to you under the
standing three-way rule.

**Cluster:** 4 lessons, one defect. **Suggested fold target:** yours to decide — the
recurrence count argues for a dedicated spec.

## The defect

When a build is routed to the `marshalld` daemon, the outer wrapper reports `tests_run: 0`
and prints *"green build: 0 test(s) executed — this run tested nothing"*, while the daemon's
own job log for the same job records the real figure.

**A fully green run and a run that executed nothing produce byte-identical outer output.**
Both report `status: success`, `exit_code: 0`, `tests_run: 0`, and the same banner. The only
outer field that contradicts the claim is `duration_seconds` — and duration is a heuristic,
not a count.

⛔ The banner makes it worse than a missing field: it asserts a positive claim ("this run
tested nothing") that is **false**, rather than declaring the count unknown.

## The four observations

| Lesson | Plan | Inner count | Outer count |
|--------|------|------------:|------------:|
| `2026-08-23-13-001` | (unresolvable — see caveat) | 17888 | 0 |
| `2026-08-23-17-001` | `orchestrator-inbox-and-landing-residue` | 17916 | 0 |
| `2026-08-24-16-002` | `a-refusal-nobody-recognises-is-filed-as-a-finding` | 18083 | 0 |
| `2026-08-24-18-001` | (title-only — see caveat) | 18123 | 0 |

⭐ **Four different plans, four different inner counts, same outer zero.** The recurrence is
derived from the enumeration above, not asserted. `2026-08-23-17-001` additionally records
its executing sub-agent observing the loss **four times inside one envelope** (inner counts
13, 44, 152, 7 — all reported as 0 outside), so the per-plan count understates the frequency.

## What is already closed, and what is not

⚠ **`2026-08-23-17-001`'s body states the transport half is CLOSED**: `read_log_verdict` now
parses the job log's `tests_run:` line, `_daemon_result_to_direct` stamps it onto the routed
result, and `cmd_run_common` prefers the propagated count.

**The residual is the unavailable-count case.** `LogVerdict.tests_run` is `None` when the
routed wrapper published no `tests_run:` line at all; the outer wrapper then falls back to
parsing the daemon job log — which carries the inner result TOON and no pytest output — and
publishes a measured-looking `0` plus the banner for a count it never received.

⛔ **This message does NOT claim the defect is closed.** The "transport half closed" statement
is the lesson's own; it was not re-verified against HEAD by this router. Establishing which
half is live is the receiving plan's first job.

## Named emitting sites (from the lesson bodies, not re-derived)

- `script-shared/scripts/build/_build_execute_factory.py` — the build-execute routing seam.
- `build-server-client` — the daemon side.

## Directive the lessons converge on

An unavailable count is an **unknown**, not a measured zero (ADR-009 fail-closed with an
explicit unknown state). A consumer gating on `tests_run` must treat a `0` that arrived with
no propagated count on a `mechanism=daemon_longpoll` return as indeterminate.

**Matched pair required** — a routed build whose wrapper published no count must report
unknown, AND a routed build that genuinely matches zero tests must stay distinguishable from
it. A fix that merely stops printing the banner satisfies neither.

## Read-coverage caveat

⛔ Two of the four rows were **not read from a body**:

- `2026-08-24-18-001` is a **title-only stub** — `add` allocated it, `set-body` never ran.
  Its title carries the finding and the count; there is nothing else.
- `2026-08-23-13-001` is **unresolvable** — `manage-lessons list` enumerates it `active`,
  `get` returns `not_found`. Its count comes from the `list` title alone.

Both rows' membership in this cluster is a **HYPOTHESIS** derived from their titles.
Confirm/refute by re-reading them once the corpus-integrity defect is fixed (owned by this
router's own PLAN-LH2-18). Verify-at-outline.

## Claim labels

- **OBSERVED** — the two full-body observations (17916, 18083) and their named sites.
- **HYPOTHESIS** — the two title-derived observations (17888, 18123) are the same defect.
  Confirm/refute at the lesson files themselves once readable.
- **HYPOTHESIS** — the transport half is closed at HEAD. Confirm/refute at
  `build-server-client` § `read_log_verdict` / `_daemon_result_to_direct`. Verify-at-outline.
