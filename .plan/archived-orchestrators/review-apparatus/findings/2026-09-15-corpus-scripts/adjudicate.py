#!/usr/bin/env python3
"""Adjudication proxy (plan-marshall only): read OUR posted answers per review-practice section 2."""
import json, os, re, glob, collections, sys
BASE = os.path.dirname(os.path.abspath(__file__))
LOWER = "2026-08-30T20:16:39Z"
HUMANS = {"cuioss-oliver", "OliverWolffGIP"}
CR, PRA, SRC = "coderabbitai[bot]", "cuioss-review-bot[bot]", "sourcery-ai[bot]"
BATCH_HDR = "## Triage dispositions"

ACCEPT = re.compile(r"\b(confirmed|agreed|accepted|accept|addressed|fixed|fix(?:ing)? (?:this|it)|will be addressed|being addressed|applied|adopted|valid (?:finding|point)|good catch|correct(?:ed)?\b|done\b|implemented|resolved by|repaired)", re.I)
REJECT = re.compile(r"(declin|not fixed|won't|will not|not (?:applicable|a defect|an issue|actionable)|false positive|suppress|out of scope|no (?:code )?change|rejected|reject|disagree|intentional|by design|deliberate|not adopting|leaving (?:as|it)|keeping (?:as|the)|not a finding|no action required|recorded as read|informational|not review feedback)", re.I)


ENVELOPE = re.compile(r"(review[- ]?(status|summary|body|run|envelope)|run-status envelope|run summary|umbrella summary|round summary|no reviewable claim|no (independent )?actionable content|carries no (finding|claim|reviewable)|bookkeeping summary|not a finding about the code|not code feedback|no code action for the summary|review received and fully triaged|all \d+ actionable comments (are )?accepted)", re.I)
MIXED = re.compile(r"(split verdict|partly|half taken|half right|two parts|both halves|dispositions differ|land differently|one item fixed, one declined|two accepted.*two declined|judged separately|take-into-account rather than fix|accepted without a code change|accepted as a known)", re.I)
DEFER = re.compile(r"(^held|held for (its own|a follow-up)|held, not dismissed|follow-up plan|deferred|survives as follow-up|records as a proposal|valid and already recorded)", re.I)
REJ2 = re.compile(r"(declin|not changing|not[- ]actionable|no change (made|needed)?|nothing to change|not adopting|not acted on|refuted|already (in place|points|handled|covered|derived)|premise is wrong|predates this pr|pre-existing|outside (this plan|the plan|the commit)|by plan contract|suppressed|out of scope|false positive|not a defect|by design|intentional|deliberate|design decision|not a separate finding)", re.I)
ACC2 = re.compile(r"(^(already fixed|already corrected|confirmed|agreed|accepted|accurate|taking|taken|credited|applying|applied|fixed|addressed|corrected|upheld|correct,|correct and|diagnosis confirmed|guard predicate quoted correctly|the defect is real|the gap is real|good catch|valid)|\b(landed|fixed in|fixed on|closed in|corrected in|folded into|addressed by|will be addressed|being addressed|being fixed|applied in|routed to|TASK-\d+))", re.I)


def classify_text(t):
    head = t.strip()[:300]
    if ENVELOPE.search(head[:200]) and not re.search(r"outside-diff (finding|item|minor)|taking the nitpick|items in this (summary|review body)|nitpick", head, re.I):
        return "envelope"
    if re.match(r"\s*(Accurate finding, suppressed|Acknowledged, not fixed)", head, re.I):
        return "rejected"
    if MIXED.search(head):
        return "mixed"
    if DEFER.search(head):
        return "deferred"
    a = ACC2.search(head); r = REJ2.search(head)
    if a and r:
        return "accepted" if a.start() < r.start() else "rejected"
    if a:
        return "accepted"
    if r:
        return "rejected"
    return "unclear"


def batched_sections(ic):
    out = {}
    for x in ic:
        if x["user"]["login"] in HUMANS and x["body"].startswith(BATCH_HDR):
            parts = re.split(r"^### In reply to comment_id: `([A-Za-z0-9_\-]+)`\s*$", x["body"], flags=re.M)
            for i in range(1, len(parts) - 1, 2):
                out.setdefault(parts[i], []).append((x["id"], parts[i + 1].strip()))
    return out


def main():
    units = []
    for f in sorted(glob.glob(os.path.join(BASE, "raw", "plan-marshall__*.json"))):
        d = json.load(open(f))
        pr = d["pr"]
        if any(l["name"] == "skip-bot-review" for l in pr["labels"]) or pr["createdAt"] < LOWER:
            continue
        n = pr["number"]
        rc, ic, rv = d["review_comments"], d["issue_comments"], d["reviews"]
        batch = batched_sections(ic)
        replies = collections.defaultdict(list)
        for x in rc:
            if x.get("in_reply_to_id") and x["user"]["login"] in HUMANS:
                replies[x["in_reply_to_id"]].append(x)

        def answer(node_id, root_id=None):
            if root_id is not None and replies.get(root_id):
                t = replies[root_id][0]["body"]
                return "thread", classify_text(t), t[:200]
            if node_id in batch:
                t = batch[node_id][0][1]
                return "batched", classify_text(t), t[:200]
            return "none", "unanswered", ""

        for x in rc:
            if x.get("in_reply_to_id"):
                continue
            u = x["user"]["login"]
            if u not in (CR, PRA, SRC):
                continue
            via, disp, txt = answer(x["node_id"], x["id"])
            units.append(dict(pr=n, state=pr["state"], bot=u, kind="inline", id=x["id"], node=x["node_id"],
                              created=x["created_at"], via=via, disp=disp, txt=txt, body=x["body"][:160]))
        for x in rv:
            u = x["user"]["login"]
            b = x["body"] or ""
            if u == CR and re.search(r"Actionable comments posted|Nitpick comments|outside the diff", b):
                kind = "cr_review_body" + ("+outside_diff" if "outside the diff" in b else "") + ("+nitpick" if "Nitpick comments" in b else "")
            elif u == SRC and re.search(r"I've found \d+", b):
                kind = "src_review_body"
            else:
                continue
            via, disp, txt = answer(x["node_id"])
            units.append(dict(pr=n, state=pr["state"], bot=u, kind=kind, id=x["id"], node=x["node_id"],
                              created=x["submitted_at"], via=via, disp=disp, txt=txt, body=b[:160]))
        for x in ic:
            u = x["user"]["login"]
            b = x["body"]
            if u == PRA and b.startswith("## PR Reviewer Guide") and "Recommended focus areas" in b:
                via, disp, txt = answer(x["node_id"])
                units.append(dict(pr=n, state=pr["state"], bot=u, kind="pra_guide_substantive", id=x["id"], node=x["node_id"],
                                  created=x["created_at"], via=via, disp=disp, txt=txt, body=b[:160]))
            elif u == PRA:
                # canned guide / empty improve: not a finding; record whether it was answered anyway
                via, disp, txt = answer(x["node_id"])
                units.append(dict(pr=n, state=pr["state"], bot=u, kind="pra_canned_NOT_FINDING", id=x["id"], node=x["node_id"],
                                  created=x["created_at"], via=via, disp=disp, txt=txt, body=b[:80]))
    json.dump(units, open(os.path.join(BASE, "adjudication.json"), "w"), indent=1)
    tab = collections.Counter((u["bot"], u["kind"], u["disp"]) for u in units)
    for k, v in sorted(tab.items()):
        print(k, v)
    print("\nby bot (finding units only, excl canned):")
    for bot in (CR, PRA, SRC):
        us = [u for u in units if u["bot"] == bot and u["kind"] != "pra_canned_NOT_FINDING"]
        print(bot, len(us), collections.Counter(u["disp"] for u in us), "via", collections.Counter(u["via"] for u in us))
        us_m = [u for u in us if u["state"] == "MERGED"]
        print("   merged-only", len(us_m), collections.Counter(u["disp"] for u in us_m))


if __name__ == "__main__":
    main()
