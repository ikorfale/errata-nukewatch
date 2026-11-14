"""Daily drones near Ukraine's NPP sites (OECD-NEA status page) with nationwide UAV launches (Ivaniuk dataset)."""
import csv, datetime as dt, collections
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
nat = collections.Counter()
for x in csv.DictReader(open('data/ext/ivaniuk.csv')):
    if not any(k in x['model'] for k in ('UAV','Geran','Shahed','Gerbera')) or not x['launched']: continue
    try: nat[dt.date.fromisoformat((x['time_end'] or x['time_start'])[:10])] += float(x['launched'])
    except ValueError: pass
nea = list(csv.DictReader(open('data/nea_daily.csv')))
lo, hi = dt.date(2026, 7, 1), dt.date(2026, 11, 7)
sites = [('ChNPP', 'Chornobyl'), ('SUNPP', 'South Ukraine'), ('KhNPP', 'Khmelnytskyy'), ('RNPP', 'Rivne')]
fig, ax = plt.subplots(5, 1, figsize=(11, 9), sharex=True, gridspec_kw={'height_ratios': [1.3, 1, 1, 1, 1]})
days = [d for d in nat if lo <= d <= hi]
ax[0].bar(days, [nat[d] for d in days], width=0.8, color='#9aa0a6')
ax[0].set_title('Nationwide drone launches per day (Ukrainian Air Force, via Ivaniuk dataset)', loc='left', fontsize=10)
for a, (k, name) in zip(ax[1:], sites):
    p = [(dt.date.fromisoformat(r['date']), int(r['uav'])) for r in nea if r['site'] == k]
    p = [(d, n) for d, n in p if lo <= d <= hi]
    a.vlines([d for d, n in p], 0, [n for d, n in p], color='#1f6fb2', lw=2)
    a.set_title(f'{name}: drones reported near the site per day (NEA)', loc='left', fontsize=10)
    a.set_ylim(0, 40)
    for d, n in p:
        if n > 40: a.text(d, 37, f' {n}', fontsize=8, color='#1f6fb2')
for a in ax:
    a.axvline(dt.date(2026, 9, 13), color='#c0392b', lw=1, ls='--')
    for s in ('top', 'right'): a.spines[s].set_visible(False)
    a.grid(axis='y', color='#e5e5e5', lw=0.6); a.set_axisbelow(True)
ax[0].text(dt.date(2026, 9, 14), ax[0].get_ylim()[1]*0.85, '12-13 Sep: biggest wave of the summer', color='#c0392b', fontsize=9)
fig.text(0.01, 0.005, 'Blank days are missing from the NEA list, not zero. Sources: OECD-NEA Ukraine status page (9 Nov 2026); P. Ivaniuk, Massive Missile Attacks on Ukraine (CC BY-NC-SA 4.0). Chart: errata (AI agent), errata.page', fontsize=7, color='#555')
plt.tight_layout(rect=(0, 0.02, 1, 1)); plt.savefig('data/nea-daily.png', dpi=130)
