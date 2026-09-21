"""Step 5 — the CodeRabbit reviewer signal, for both lanes.

Fetches per PR through the CI abstraction and aggregates. Comment BODIES are never printed: only
counts, so the measurement can be taken without pulling the corpus into a context window.

Three states are kept distinct, never two:
  '-'  CodeRabbit produced NO review (quota / limit / label / absence)  -> could not look
  '0'  CodeRabbit reviewed and raised nothing                          -> looked, found nothing
  N    N originating findings
"""
import json
import pathlib
import re
import subprocess
import sys

REPO = "/Users/oliver/git/plan-marshall"
SCRATCH = pathlib.Path("/private/tmp/claude-501/-Users-oliver-git-plan-marshall/518a46ed-6f9f-4d30-953d-44090e7a1635/scratchpad")

HDR = re.compile(r'^comments\[(\d+)\]\{([^}]*)\}:')
DECLINE = re.compile(
    r'review limit reached|reached your PR review limit|rate limit|weekly rate limit|'
    r'you have reached your|quota|skip-bot-review', re.I)
FINGERPRINT = "cr-comment:v1"


def fetch(pr):
    p = subprocess.run(
        ["python3", ".plan/execute-script.py", "plan-marshall:tools-integration-ci:ci",
         "pr", "comments", "--pr-number", str(pr)],
        cwd=REPO, capture_output=True, text=True)
    return p.stdout


def parse(out):
    lines = out.split("\n")
    cols, rows = None, []
    for i, ln in enumerate(lines):
        m = HDR.match(ln.strip())
        if m:
            cols = m.group(2).split(",")
            for r in lines[i + 1:]:
                if not r.startswith("  "):
                    break
                parts = r.strip("\n").lstrip().split("\t")
                if len(parts) >= len(cols):
                    rows.append(dict(zip(cols, parts)))
            break
    return cols, rows


def measure(pr):
    out = fetch(pr)
    if "status: success" not in out:
        return dict(pr=pr, state="error", findings=None, resolved=None, note="fetch failed")
    cols, rows = parse(out)
    cr = [r for r in rows if "coderabbit" in (r.get("author") or "").lower()]
    # An originating finding: an INLINE comment carrying the fingerprint. The marker is what
    # separates a finding from CodeRabbit's own auto-generated replies.
    findings = [r for r in cr if FINGERPRINT in (r.get("body") or "")
                and (r.get("kind") or "") not in ("issue_comment", "review_body")]
    declined = any(DECLINE.search(r.get("body") or "") for r in cr)
    resolved = sum(1 for r in findings if (r.get("resolved") or "").strip().lower() == "true")
    if not cr:
        return dict(pr=pr, state="absent", findings=None, resolved=None,
                    note="no coderabbit comment at all")
    if not findings and declined:
        return dict(pr=pr, state="declined", findings=None, resolved=None,
                    note="review declined (limit/quota)")
    return dict(pr=pr, state="reviewed", findings=len(findings), resolved=resolved,
                note=f"{len(cr)} cr comments total")


def main():
    which = sys.argv[1]
    prs = json.loads(sys.argv[2])
    res = []
    for pr in prs:
        r = measure(pr)
        res.append(r)
        print(f"  #{pr:<6} {r['state']:<9} findings={str(r['findings']):>4} "
              f"resolved={str(r['resolved']):>4}  {r['note']}")
    (SCRATCH / f"reviewer_{which}.json").write_text(json.dumps(res), encoding="utf-8")
    rev = [r for r in res if r["state"] == "reviewed"]
    tot_f = sum(r["findings"] for r in rev)
    tot_r = sum(r["resolved"] for r in rev)
    print(f"\n{which}: PRs={len(res)}  reviewed={len(rev)}  "
          f"declined={sum(1 for r in res if r['state']=='declined')}  "
          f"absent={sum(1 for r in res if r['state']=='absent')}  "
          f"error={sum(1 for r in res if r['state']=='error')}")
    print(f"{which}: findings={tot_f}  resolved={tot_r}  "
          f"resolution={(100*tot_r/tot_f):.1f}%" if tot_f else f"{which}: findings=0")


main()
