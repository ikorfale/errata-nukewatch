#!/usr/bin/env python3
"""Weekly extension of data/series.csv with updates the IAEA published since the last row.

Steps: refresh the Wayback index and fetch new texts (fetch.py --cdx), run the parser on every
update newer than the last row, append one row each, redraw the chart. Rows added this way were
read by the parser only (no blind second coder); their numbers are listed in data/parser_only.json
so readers and the README can tell them apart. An update the parser reads as all-empty is still
appended (empty means "no number given", never zero) and logged.

Usage: update.py [--no-fetch] [--dry]
Exit 0 with "new: N" on stdout; N=0 means nothing new.
"""
import csv, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")
sys.path.insert(0, HERE)
import parse  # noqa: E402

COLS = ["update", "date", "ChNPP", "SUNPP", "KhNPP", "RNPP", "znpp_loop", "alarms"]


def main():
    dry = "--dry" in sys.argv
    if "--no-fetch" not in sys.argv:
        subprocess.run([sys.executable, "-I", os.path.join(HERE, "fetch.py"), "--cdx", "--new-only"], check=True)
    path = os.path.join(D, "series.csv")
    rows = list(csv.DictReader(open(path)))
    last = max(int(r["update"]) for r in rows)
    po_path = os.path.join(D, "parser_only.json")
    parser_only = json.load(open(po_path)) if os.path.exists(po_path) else []
    new = []
    for f in sorted(os.listdir(os.path.join(D, "txt"))):
        m = re.fullmatch(r"u(\d+)\.txt", f)
        if not m or int(m.group(1)) <= last:
            continue
        n = int(m.group(1))
        lines = open(os.path.join(D, "txt", f)).read().split("\n", 1)
        date, text = lines[0].strip(), (lines[1] if len(lines) > 1 else "")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", date) or len(text) < 500:
            print(f"skip u{n}: date={date!r} text={len(text)} chars (capture incomplete?)", file=sys.stderr)
            continue
        d, notes = parse.parse(text)
        row = {"update": n, "date": date, "ChNPP": d.get("ChNPP", ""), "SUNPP": d.get("SUNPP", ""),
               "KhNPP": d.get("KhNPP", ""), "RNPP": d.get("RNPP", ""), "znpp_loop": d.get("loop_n", ""),
               "alarms": d.get("alarms", "")}
        print("row", json.dumps(row), "notes", notes)
        new.append(row)
    if new and not dry:
        with open(path, "a", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=COLS)
            for r in new:
                w.writerow(r)
        parser_only = sorted(set(parser_only) | {r["update"] for r in new})
        json.dump(parser_only, open(po_path, "w"))
        subprocess.run([sys.executable, "-I", os.path.join(HERE, "chart.py")], check=True, cwd=HERE)
    print("new:", len(new))


if __name__ == "__main__":
    main()
