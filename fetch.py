#!/usr/bin/env python3
"""Fetch archived IAEA 'Update N' statements from the Wayback Machine (iaea.org itself sits
behind a Cloudflare challenge) and write plain text: data/txt/uNNN.txt, first line the date,
then one paragraph per line (same layout as fixtures/).

Polite: one request every 4 s, raw HTML cached in data/html/, reruns skip what is cached.
Usage: fetch.py [--cdx]   (--cdx refreshes the index first)
"""
import gzip, html, json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")
UA = "errata-nukewatch/0.1 (research; errata@agentmail.to)"
SLUG = re.compile(r"/update-(\d+)-iaea-director-general-statement-on-(?:the-)?(?:situation-in-)?ukraine")
BOILER = ("vienna international centre", "sign up for our weekly", "cookies", "subscribe", "newsletter", "javascript")


def get(url, tries=3):
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip"})
            with urllib.request.urlopen(req, timeout=60) as r:
                b = r.read()
            if b[:2] == b"\x1f\x8b":
                b = gzip.decompress(b)
            return b
        except Exception as e:
            print("retry", k, url, e, file=sys.stderr)
            time.sleep(10 * (k + 1))
    return None


def build_index():
    url = ("https://web.archive.org/cdx/search/cdx?url=iaea.org/newscenter/pressreleases/update-"
           "&matchType=prefix&fl=original,timestamp&filter=statuscode:200&collapse=urlkey")
    best = {}
    raw = get(url).decode() if "--offline" not in sys.argv else open(os.path.join(D, "cdx.txt")).read()
    for line in raw.splitlines():
        p = line.split()
        if len(p) < 2:
            continue
        m = SLUG.search(p[0])
        if not m:
            continue
        # keep the archived URL exactly as captured: the timestamp belongs to that variant
        # (pairing a stripped URL with a ?utm_ variant's timestamp gave HTTP 405, u300)
        n, u, clean = int(m.group(1)), p[0], "?" not in p[0]
        key = (clean, p[1])
        if n not in best or key > best[n][2]:
            best[n] = (u, p[1], key)
    json.dump({str(n): best[n][:2] for n in sorted(best)}, open(os.path.join(D, "wayback_index.json"), "w"))
    return best


def text_of(s):
    date = None
    m = re.search(r'datetime="(\d{4}-\d{2}-\d{2})', s)
    if m:
        date = m.group(1)
    else:
        m = re.search(r"\b(\d{1,2} [A-Z][a-z]{2,8} 20\d\d)\b", s)
        date = m.group(1) if m else "?"
    i = s.find("field--name-body")
    body = s[i:] if i >= 0 else s
    paras = []
    for p in re.findall(r"<p[^>]*>(.*?)</p>", body, flags=re.S):
        t = html.unescape(re.sub(r"<[^>]+>", "", p)).strip()
        t = re.sub(r"\s+", " ", t)
        if len(t) < 60 or any(b in t.lower() for b in BOILER):
            continue
        paras.append(t)
    return date, paras


def main():
    os.makedirs(os.path.join(D, "html"), exist_ok=True)
    os.makedirs(os.path.join(D, "txt"), exist_ok=True)
    if "--cdx" in sys.argv or not os.path.exists(os.path.join(D, "wayback_index.json")):
        build_index()
    idx = json.load(open(os.path.join(D, "wayback_index.json")))
    log = open(os.path.join(D, "fetch.log"), "a")
    for n in sorted(idx, key=int):
        u, t = idx[n]
        hp = os.path.join(D, "html", f"u{int(n):03d}.html.gz")
        if not os.path.exists(hp):
            b = get(f"https://web.archive.org/web/{t}id_/{u}")
            time.sleep(4)
            if not b:
                print(n, "FAIL", file=log, flush=True)
                continue
            with gzip.open(hp, "wb") as f:
                f.write(b)
        s = gzip.open(hp).read().decode("utf-8", "replace")
        date, paras = text_of(s)
        with open(os.path.join(D, "txt", f"u{int(n):03d}.txt"), "w") as f:
            f.write(date + "\n" + "\n".join(paras) + "\n")
        print(n, date, len(paras), file=log, flush=True)
    print("=== end", file=log, flush=True)


if __name__ == "__main__":
    main()
