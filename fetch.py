#!/usr/bin/env python3
"""Fetch archived IAEA 'Update N' statements from the Wayback Machine (iaea.org itself sits
behind a Cloudflare challenge) and write plain text: data/txt/uNNN.txt, first line the date,
then one paragraph per line (same layout as fixtures/).

Polite: one request every 4 s, raw HTML cached in data/html/, reruns skip what is cached.
Usage: fetch.py [--cdx] [--new-only]   (--cdx refreshes the index first; --new-only skips updates
at or below the last row of data/series.csv)
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
    raw = get(url) if "--offline" not in sys.argv else open(os.path.join(D, "cdx.txt")).read().encode()
    if raw is None:  # CDX down (503 on 21 Nov): keep the saved index, say so, do not crash the daily run
        print("cdx: unreachable, using saved wayback_index.json")
        ip = os.path.join(D, "wayback_index.json")
        return {int(k): (v[0], v[1], None) for k, v in json.load(open(ip)).items()} if os.path.exists(ip) else {}
    raw = raw.decode()
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
    out = {str(n): list(best[n][:2]) for n in sorted(best)}
    ip = os.path.join(D, "wayback_index.json")
    if os.path.exists(ip):  # keep updates found earlier that this CDX answer left out (u375, 14 Nov)
        for n, v in json.load(open(ip)).items():
            out.setdefault(n, v)
    json.dump(dict(sorted(out.items(), key=lambda kv: int(kv[0]))), open(ip, "w"))
    return best


RSS = "https://www.iaea.org/feeds/topnews"  # not behind the Cloudflare challenge; titles, dates and links only
TITLE = re.compile(r"Update (\d+) \u2013 IAEA Director General Statement on (?:the )?Situation in Ukraine")


def published_latest():
    """Newest Ukraine update the IAEA itself lists in its RSS: (n, date, url) or None.
    Written to data/published.json so a run can say 'published, not archived yet' instead of a silent new: 0."""
    b = get(RSS, tries=2)
    if not b:
        return None
    best = None
    for item in re.findall(r"<item>(.*?)</item>", b.decode("utf-8", "replace"), re.S):
        t = re.search(r"<title>(.*?)</title>", item, re.S)
        m = TITLE.search(html.unescape(t.group(1))) if t else None
        if not m:
            continue
        link = re.search(r"<link>(.*?)</link>", item, re.S)
        pd = re.search(r"<pubDate>\s*(\d{2})-(\d{2})-(\d{2})", item, re.S)  # feed prints yy-mm-dd
        date = f"20{pd.group(1)}-{pd.group(2)}-{pd.group(3)}" if pd else ""
        n = int(m.group(1))
        if best is None or n > best[0]:
            best = (n, date, link.group(1).strip().replace("http://", "https://") if link else "")
    if best:
        json.dump({"update": best[0], "date": best[1], "url": best[2]}, open(os.path.join(D, "published.json"), "w"))
    return best


def request_archive(url):
    """Ask the Wayback Machine's Save Page Now to capture url (one polite request; it may refuse or be down)."""
    try:
        req = urllib.request.Request("https://web.archive.org/save/" + url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status
    except Exception as e:
        return getattr(e, "code", None) or str(e)[:60]


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
        best = build_index()
        pub = published_latest()
        if pub and best and pub[0] > max(best):  # IAEA lists an update nobody has archived yet (u376, 19-21 Nov)
            n, date, url = pub
            lag = ""
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}", date):
                lag = f", lag {(time.time() - time.mktime(time.strptime(date, '%Y-%m-%d'))) / 86400:.0f} d"
            st = request_archive(url)
            print(f"published: u{n} {date}, not archived{lag}; save-page-now -> {st}")
            if st == 200:
                time.sleep(5)
                build_index()
    idx = json.load(open(os.path.join(D, "wayback_index.json")))
    log = open(os.path.join(D, "fetch.log"), "a")
    floor = 0
    if "--new-only" in sys.argv:  # daily run: old Wayback gaps (u315/u316 give HTTP 402) are permanent, skip them
        sp = os.path.join(D, "series.csv")
        if os.path.exists(sp):
            floor = max(int(l.split(",")[0]) for l in open(sp).read().splitlines()[1:] if l)
    for n in sorted(idx, key=int):
        if int(n) <= floor:
            continue
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
