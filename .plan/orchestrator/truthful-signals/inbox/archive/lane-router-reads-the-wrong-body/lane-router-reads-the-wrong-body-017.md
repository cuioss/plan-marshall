envelope_version=1
sender_type=plan
sender_id=lane-router-reads-the-wrong-body
epic=truthful-signals
kind=landing
created=2026-07-29T11:14:00Z

# Follow-up landing: PR #1052 remediates both post-merge findings from #1049

## Status

**RESOLVED — remediation PR open.** This message closes the "owed follow-up" named in
message 011 § "Owed follow-up". The two CodeRabbit findings that landed live on main via
`83a0466d2` now have a fix PR.

- **Remediation PR**: https://github.com/cuioss/plan-marshall/pull/1052
- **Branch**: `fix/lane-router-title-strip-and-s3-prose`
- **Base**: `main`
- **Fixes**: both findings described in messages 011 and 012

## What was fixed

### 1. `_read_request_body` title strip anchored to line 1 (minor)

The generator filtered EVERY line matching `^#\s+Request\b` while the docstring stated the
host title is "the ONLY line removed". An ingested spec's own `# Request …` heading was
silently dropped from the scored text. Now anchored to `lines[0]` only.

The old behaviour was **conservative** — dropping text can only widen the band, never narrow
it — so no mis-route is attributable to it. The defect was code-vs-contract divergence, which
is the class #1049 existed to eliminate.

### 2. `phase-1-init/SKILL.md` unset-`change_type` prose corrected (major)

The prose claimed an unset `change_type` deep-biases "per the DQ1 signal set". Verified false
at HEAD:

```python
s2_deep = scope_estimate in _DEEP_SCOPE_ESTIMATES or scope_estimate is None   # explicit unknown clause
s3_deep = change_type in _DEEP_CHANGE_TYPES and not narrow_and_concrete       # None is not a member
```

S3 cannot fire for `None`. Both describing sites (Step 8a.5 and Step 8b) now state the
S2-vs-S3 asymmetry plainly instead of presenting the two unknowns as symmetric.

## Mirror-surface sweep performed

Swept `marketplace/bundles/` for the same S3 claim. **No other surface repeats it** —
`manage-status/SKILL.md:678` states S3 correctly as `∈ {feature, feature_breaking}`. This
sweep is the check that message 012 says the original self-review should have had fed to it.

## Verification

- Regression test added pinning that a non-first-line `# Request …` heading survives the strip.
- `module-tests plan-marshall` green.
- Whole-tree `quality-gate` green.

## What this does NOT close

Messages 011 and 012 remain **open as lessons** — the fix repairs the two symptoms, not the
two mechanisms:

- **011** (barrier check-then-act window) is a `phase-6-finalize` defect and is untouched by
  this PR. The next plan through that path is exposed identically.
- **012** (prior-gate findings not fed into the self-review candidate set) is a
  `pre-submission-self-review` defect and is untouched.

Fixing the symptom does not retire either lesson. Sibling plan
`post-merge-review-findings-untriaged-in-main` appears to be working the adjacent seam and
should be cross-read before either is scheduled.
