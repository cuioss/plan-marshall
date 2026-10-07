envelope_version=1
sender_type=plan
sender_id=self-review-cannot-see-an-unreachable-guard
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T22:04:31Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=bug
created=2026-07-29

# Shipped test guard is conditionally vacuous on terminal width

A test added by this plan asserts against argparse-rendered help/usage text. Argparse hyphen-wraps long option strings once the rendered line exceeds the terminal width, so the assertion only matches a wrapped fragment of the real string. At a wider terminal (verified: 120 columns) the wrapping does not occur and the same assertion would pass even against wrong or missing content — the guard's failure mode is silently environment-dependent rather than deterministic.

## Solution

Identified during self-review of this plan's own diff before submission; not yet corrected inline in this plan (filed as residue for the epic).

## Impact

Any test asserting on argparse `--help`/usage rendered text must either pin `COLUMNS` (or the equivalent env var) to a fixed value, or assert against the parsed argument/action structure instead of the rendered string, to avoid a guard that is vacuous at some terminal widths and effective at others. Consider adding this as a standing self-review candidate: "assertion against CLI help/usage text without a pinned render width."
