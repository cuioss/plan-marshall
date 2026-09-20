#!/usr/bin/env python3
"""Read-only collector: enumerate PRs updated in window and dump raw per-PR JSON (GET only)."""
import json, subprocess, sys, os
from concurrent.futures import ThreadPoolExecutor

LOWER = "2026-08-30T20:16:39Z"
BASE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(BASE, "raw")
REPOS = ["plan-marshall", "cui-http", "TokenSheriff", "API-Sheriff",
         "cui-test-mockwebserver-junit5", "cui-test-juli-logger"]


def gh(args):
    r = subprocess.run(["gh"] + args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)}: {r.stderr}")
    return r.stdout


def api_paginated(path):
    out = gh(["api", "-H", "Accept: application/vnd.github+json", path + "?per_page=100", "--paginate", "--slurp"])
    pages = json.loads(out)
    items = []
    for p in pages:
        items.extend(p)
    return items


def enumerate_repo(repo):
    out = gh(["pr", "list", "--repo", f"cuioss/{repo}", "--search", f"updated:>={LOWER}", "--state", "all",
              "--json", "number,title,createdAt,updatedAt,labels,author,state,mergedAt,additions,deletions,changedFiles,headRefName,baseRefName",
              "--limit", "1000"])
    return json.loads(out)


def dump_pr(repo, pr):
    n = pr["number"]
    fn = os.path.join(RAW, f"{repo}__{n}.json")
    if os.path.exists(fn) and "--refresh" not in sys.argv:
        return fn
    d = {"repo": repo, "pr": pr}
    d["issue_comments"] = api_paginated(f"repos/cuioss/{repo}/issues/{n}/comments")
    d["review_comments"] = api_paginated(f"repos/cuioss/{repo}/pulls/{n}/comments")
    d["reviews"] = api_paginated(f"repos/cuioss/{repo}/pulls/{n}/reviews")
    d["commits"] = api_paginated(f"repos/cuioss/{repo}/pulls/{n}/commits")
    with open(fn, "w") as f:
        json.dump(d, f)
    return fn


def main():
    os.makedirs(RAW, exist_ok=True)
    enum = {}
    for repo in REPOS:
        enum[repo] = enumerate_repo(repo)
        print(repo, len(enum[repo]))
    with open(os.path.join(BASE, "enumeration.json"), "w") as f:
        json.dump(enum, f)
    jobs = []
    for repo, prs in enum.items():
        for pr in prs:
            # skip-bot-review PRs are dumped too (excluded at classification), so the
            # bypass population can be inspected for bot activity before the label.
            jobs.append((repo, pr))
    with ThreadPoolExecutor(max_workers=6) as ex:
        for fn in ex.map(lambda j: dump_pr(*j), jobs):
            pass
    print("dumped", len(jobs))


if __name__ == "__main__":
    main()
