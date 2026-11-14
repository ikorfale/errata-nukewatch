"""Test for #750: is the Sept 2026 step in IAEA site drone counts more drones or a counting change?
Inputs (download into data/ext/, not committed):
  ivaniuk.csv        https://ua-air-defense-tracker.org/data/missile_attacks_daily.csv (P. Ivaniuk, CC BY-NC-SA 4.0)
  tryvoga-daily.csv  https://tryvoga.live/data/daily.csv (region x day drones, from 2026-10-05)
Output: data/oblast_check.csv (weekly windows ending at each IAEA update date)."""
import csv, datetime as dt
from scipy.stats import spearmanr
E = 'data/ext/'
r = list(csv.DictReader(open(E + 'ivaniuk.csv')))
t = list(csv.DictReader(open(E + 'tryvoga-daily.csv', encoding='utf-8-sig')))
ser = list(csv.DictReader(open('data/series.csv', encoding='utf-8-sig')))
OBL = {'ChNPP': 'kyiv-oblast', 'SUNPP': 'mykolaiv', 'KhNPP': 'khmelnytskyi', 'RNPP': 'rivne'}
def day(x):
    try: return dt.date.fromisoformat(x[:10])
    except ValueError: return None
last_iv = max(day(x['time_start']) for x in r if day(x['time_start']))
out = []
for s in ser:
    d = dt.date.fromisoformat(s['date']); a = d - dt.timedelta(days=7)
    row = {'update': s['update'], 'date': s['date']}
    row['national_uav'] = '' if d > last_iv else int(sum(float(x['launched'] or 0) for x in r
        if day(x['time_start']) and a <= day(x['time_start']) < d
        and any(k in x['model'] for k in ('UAV', 'Geran', 'Shahed', 'Gerbera'))))
    for site, reg in OBL.items():
        row[site] = s[site]
        row[reg + '_drones'] = '' if a < dt.date(2026, 10, 5) else sum(int(x['drones'] or 0) for x in t
            if x['region_id'] == reg and a <= dt.date.fromisoformat(x['date']) < d)
    out.append(row)
with open('data/oblast_check.csv', 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
for site in ('ChNPP', 'SUNPP'):
    for lo, hi, lab in ((355, 366, 'before u367'), (367, 374, 'from u367')):
        p = [(x['national_uav'], float(x[site])) for x in out
             if lo <= int(x['update']) <= hi and x[site] and x['national_uav']]
        rho = spearmanr([a for a, b in p], [b for a, b in p]).statistic
        share = sum(b for a, b in p) / sum(a for a, b in p) * 1000
        print(f'{site} {lab}: n={len(p)} drones near site per 1000 launched nationwide={share:.1f} rho(week)={rho:.2f}')
