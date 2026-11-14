#!/usr/bin/env python3
"""Parse IAEA 'Update N - Director General Statement on Situation in Ukraine' texts
into weekly numbers: drones reported near each NPP site, air-raid alarms, ZNPP
loss-of-off-site-power ordinal.

Rule: a number is counted for a site only when the sentence talks about drones and
the number is tied to the site (forward 'N near/at the <site>', backward '<site>
reported [detecting] N', or an explicit '..., respectively' list). Distances, dates
and spent-fuel-facility counts are skipped. Anything the parser could not tie is
left missing, never guessed.

usage: parse.py FILE... (prints JSON lines)   |   parse.py --test (fixtures)
"""
import json, re, sys, os

SITES = [  # (code, regex) longest first
    ("SUNPP", r"South Ukraine(?: Nuclear Power Plant| NPP| site)?|SUNPP"),
    ("KhNPP", r"Khmelnytsk(?:yy|yi|y)(?: Nuclear Power Plant| NPP| site)?|KhNPP"),
    ("RNPP", r"Rivne(?: Nuclear Power Plant| NPP| site)?|RNPP"),
    ("ChNPP", r"Chornobyl(?: Nuclear Power Plant| NPP| site)?|ChNPP"),
    ("ZNPP", r"Zaporizhzhya Nuclear Power Plant|ZNPP"),
]
WORDNUM = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen twenty".split())}
MONTHS = "January February March April May June July August September October November December".split()
NUM = r"\b(\d{1,4}|" + "|".join(WORDNUM) + r")\b"


def val(tok):
    tok = tok.lower()
    return int(tok) if tok.isdigit() else WORDNUM.get(tok)


def site_spans(s):
    out = []
    for code, rx in SITES:
        for m in re.finditer(rx, s):
            if any(a <= m.start() < b for a, b, _ in out):
                continue
            # 'Chornobyl Exclusion Zone' / spent fuel facility is not the ChNPP site
            if code == "ChNPP" and re.match(r"Chornobyl Exclusion", s[m.start():]):
                continue
            out.append((m.start(), m.end(), code))
    return sorted(out)


def skip_number(s, m):
    after = s[m.end():m.end() + 14]
    before = s[max(0, m.start() - 4):m.start()]
    if re.match(r"\s*(?:kilomet|km|metre|meter|m\b|kV|per ?cent|%)", after):
        return True
    if re.match(r"\s*(?:" + "|".join(MONTHS) + ")", after) or before.strip().lower() == "on":
        return True
    if re.match(r"\s*of (?:these|the|which)", after):
        return True
    return False


def drones(text):
    res, notes = {}, []
    for sent in re.split(r"(?<=[.!?])\s+", text):
        if "drone" not in sent.lower() or re.search(r"Spent Fuel", sent, re.I) and not site_spans(sent.split("Spent Fuel")[0]):
            continue
        used = set()
        # explicit 'respectively' list
        if "respectively" in sent:
            clause = re.split(r",\s*(?:while|and)?\s*", sent.split("respectively")[0])
            clause = [c for c in clause if c.strip()]
            # clause holding the numbers is the last; sites may sit in it too
            c = clause[-1] if len(clause) == 1 else ", ".join(clause[-2:]) if not site_spans(clause[-1]) else clause[-1]
            sites = [x[2] for x in site_spans(c)]
            nums = [m for m in re.finditer(NUM, c, re.I) if not skip_number(c, m)]
            if sites and len(sites) == len(nums):
                for code, m in zip(sites, nums):
                    res[code] = res.get(code, 0) + val(m.group(1))
                    used.add(m.group(0) + "@" + code)
                sent = sent.replace(c, "")
        # drop the spent-fuel clause
        sent = re.sub(r"[^,.;]*Spent Fuel[^,.;]*", "", sent, flags=re.I)
        spans = site_spans(sent)
        for m in re.finditer(NUM, sent, re.I):
            if skip_number(sent, m):
                continue
            v = val(m.group(1))
            fwd = re.match(r"\s+(?:drones?\s+)?(?:near|at)\s+(?:the\s+)?", sent[m.end():])
            code = None
            if fwd:
                nxt = [x for x in spans if x[0] == m.end() + fwd.end()]
                code = nxt[0][2] if nxt else None
            if code is None:
                tied = (re.match(r"\s+drones?", sent[m.end():]) or
                        re.search(r"(?:reported|detected|detecting|than)\s*$", sent[:m.start()]))
                prev = [x for x in spans if x[1] <= m.start()]
                if tied and prev:
                    code = prev[-1][2]
            if code and code != "ZNPP":
                if code in res:
                    notes.append(f"dup {code} {v}")
                    continue
                res[code] = v
    return res, notes


def alarms(text):
    for rx in [r"(?:total of |In total, )(\d+) air[- ]raid (?:alarms|alerts)",
               r"air[- ]raid (?:alarms|alerts)[^.]*?with (\d+) in total",
               r"(\d+) air[- ]raid (?:alarms|alerts)"]:
        m = re.search(rx, text, re.I)
        if m:
            return int(m.group(1))
    return None


def loop_n(text):
    m = re.search(r"(\d+)(?:st|nd|rd|th) (?:complete |such )?loss of (?:all )?off-site power", text, re.I)
    return int(m.group(1)) if m else None


def parse(text):
    d, notes = drones(text)
    a, l = alarms(text), loop_n(text)
    if a is not None: d["alarms"] = a
    if l is not None: d["loop_n"] = l
    return d, notes


def test():
    here = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
    exp = json.load(open(os.path.join(here, "expected.json")))
    bad = 0
    for n, e in sorted(exp.items()):
        got, notes = parse(open(os.path.join(here, f"u{n}.txt")).read())
        ok = got == e
        bad += not ok
        print(("ok  " if ok else "BAD ") + n, "" if ok else f"got={got} want={e} {notes}")
    print(f"{len(exp)-bad}/{len(exp)} fixtures match")
    return bad


if __name__ == "__main__":
    if sys.argv[1:] == ["--test"]:
        sys.exit(1 if test() else 0)
    for f in sys.argv[1:]:
        d, notes = parse(open(f).read())
        print(json.dumps({"file": f, **d, "notes": notes}))
