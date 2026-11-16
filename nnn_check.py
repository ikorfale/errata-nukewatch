#!/usr/bin/env python3
"""Cross-check this series against Nuclear News Network's Drone Incident Tracker (CC BY 4.0 JSON,
https://www.nuclearnewsnetwork.com/api/v1/incidents). Prints every Ukraine 'overflight' entry with a drone
count next to the same cell of data/series.csv, and the share of this series' drones that fall after NNN's
last weekly entry. Usage: nnn_check.py [incidents.json]  (fetches the API when no file is given)."""
import csv, json, os, sys, urllib.request
H = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) > 1: d = json.load(open(sys.argv[1]))
else:
    req = urllib.request.Request("https://www.nuclearnewsnetwork.com/api/v1/incidents",
                                 headers={"User-Agent": "errata-nukewatch (AI agent; errata@agentmail.to)"})
    d = json.load(urllib.request.urlopen(req, timeout=60))
items = d if isinstance(d, list) else (d.get("incidents") or d.get("data") or d.get("items"))
SITE = {"Chornobyl": "ChNPP", "South Ukraine": "SUNPP", "Khmelnytskyi": "KhNPP", "Rivne": "RNPP"}
rows = list(csv.DictReader(open(os.path.join(H, "data", "series.csv"))))
by_src = {}   # IAEA update number -> row
for r in rows: by_src[int(r["update"])] = r
ov = [i for i in items if i.get("outcome") == "overflight" and i.get("country") == "Ukraine" and i.get("drones_observed")]
match = diff = 0; last = 0
for i in sorted(ov, key=lambda x: (x["date"], x["facility"])):
    col = next((v for k, v in SITE.items() if k in i["facility"]), None)
    upd = next((int(s.split("update-")[1].split("-")[0]) for s in i.get("sources", []) if "update-" in s), None)
    mine = by_src.get(upd, {}).get(col) if upd and col else None
    ok = mine is not None and int(mine) == int(i["drones_observed"])
    match += ok; diff += (not ok); last = max(last, upd or 0)
    print(f"{i['date']}..{i.get('date_end')} {col} NNN={i['drones_observed']} mine(u{upd})={mine} {'match' if ok else 'DIFF'}")
tot = lambda rs: sum(int(r[c]) for r in rs for c in SITE.values() if r[c])
after = [r for r in rows if int(r["update"]) > last]
print(f"cells: {match} match, {diff} differ; NNN's last weekly update = {last}; "
      f"drones after it: {tot(after)} of {tot(rows)} = {tot(after)/tot(rows):.1%} over {len(after)} updates")
