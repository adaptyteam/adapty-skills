#!/usr/bin/env python3
"""One placement, plus 3 flows over 2 pages at page size 2 -- so a run that
reads page 1 alone misses the flow that matches."""
import json, sys
a = sys.argv[1:]
CALLS = sys.argv[0].replace('fake-adapty.py', 'calls.log')
open(CALLS, 'a').write(' '.join(a) + '\n')
PL = [{"id": "pl-a", "developer_id": "main", "title": "Main"}]
FLOWS = [
    {"id": "f-1", "name": "Winback", "status": "published"},
    {"id": "f-2", "name": "Trial upsell", "status": "published"},
    {"id": "f-3", "name": "Main Paywall flow", "status": "draft"},
]
PW = [{"id": "pw-1", "title": "Main Paywall", "product_ids": []}]


def page(rows):
    size = int(a[a.index("--page-size") + 1]) if "--page-size" in a else 20
    num = int(a[a.index("--page") + 1]) if "--page" in a else 1
    start = (num - 1) * size
    print(json.dumps({"data": rows[start:start + size],
                      "meta": {"pagination": {"count": len(rows), "page": num,
                                              "pages": max(1, -(-len(rows) // size))}}}))
    sys.exit(0)


if a[:2] == ["placements", "list"]:
    page(PL)
if a[:2] == ["flows", "list"]:
    page(FLOWS)
if a[:2] == ["paywalls", "list"]:
    page(PW)
if a[:2] == ["placements", "get"]:
    print(json.dumps(dict(PL[0], audiences=[
        {"paywall_id": "pw-1", "priority": 0, "segment_ids": []}])))
    sys.exit(0)
print("unexpected: " + " ".join(a), file=sys.stderr)
sys.exit(9)
