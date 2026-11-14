"""Parse OECD-NEA 'Ukraine: current status of nuclear power installations' site entries into daily UAV counts.
Input: data/ext/nea-status.txt (page text). A range 'N on 13-14 October' is assigned to its last day.
Output: data/nea_daily.csv (site,date,uav,entry_date). Duplicates across entries keep the later entry."""
import re, csv, datetime as dt
M = {m: i for i, m in enumerate(['January','February','March','April','May','June','July','August',
     'September','October','November','December'], 1)}
SITES = [('KhNPP', r'Khmelnytskyi|KhNPP'), ('RNPP', r'Rivne|RNPP'), ('SUNPP', r'South Ukraine|SUNPP'),
         ('ChNPP', r'ChNPP|Chornobyl exclusion|exclusion zone')]
txt = open('data/ext/nea-status.txt').read().splitlines()
rows = {}
for line in txt:
    m = re.match(r'\* (\d+) (\w+)(?: (2026))?:(.*)', line)
    if not m or m.group(2) not in M: continue
    body = m.group(4)
    if not re.search(r'drone|UAV', body, re.I) or 'IAEA reported that in a 24' in body: continue
    site = next((s for s, p in SITES if re.search(p, body)), None)
    if not site: continue
    edate = dt.date(2026, M[m.group(2)], int(m.group(1)))
    body = body.split('reported', 1)[-1] if 'reported:' in body or 'including' not in body else body.split('including', 1)[1]
    for n, d1, mon in re.findall(r'(\d+)(?: UAV flights?| UAVs?| flights| drones?)? (?:on|between) (?:\d+\s*[-–]\s*)?(?:\d+ \w+\s*[-–]\s*)?(\d+) (\w+)', body):
        if mon not in M: continue
        y = 2026 if M[mon] <= edate.month else 2025
        day = dt.date(y, M[mon], int(d1))
        if day > edate: continue
        rows[(site, day)] = (int(n), edate)
with open('data/nea_daily.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['site', 'date', 'uav', 'entry_date'])
    for (s, d), (n, e) in sorted(rows.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        w.writerow([s, d, n, e])
print(len(rows), 'site-days')
