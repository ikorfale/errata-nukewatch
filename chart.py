#!/usr/bin/env python3
"""Small multiples: drones reported in each NPP site's monitoring area per weekly IAEA update.
Empty = the update gave no number for that site (drawn as a gap, never as zero)."""
import csv, os, datetime as dt
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
HERE = os.path.dirname(os.path.abspath(__file__))
rows = list(csv.DictReader(open(os.path.join(HERE, "data", "series.csv"))))
d = [dt.date.fromisoformat(r["date"]) for r in rows]
SITES = [("ChNPP", "Chornobyl site"), ("SUNPP", "South Ukraine NPP"), ("KhNPP", "Khmelnytskyy NPP"), ("RNPP", "Rivne NPP")]
INK, MUTED, BLUE = "#1f2328", "#6e7781", "#2f6fb0"
fig, axs = plt.subplots(1, 4, figsize=(12, 3.6), sharey=True, dpi=150)
ymax = max(int(r[c]) for r in rows for c, _ in SITES if r[c])
for ax, (c, name) in zip(axs, SITES):
    xs = [x for x, r in zip(d, rows) if r[c]]; ys = [int(r[c]) for r in rows if r[c]]
    ax.bar(d, [int(r[c]) if r[c] else 0 for r in rows], width=4.5, color=BLUE)
    miss = [x for x, r in zip(d, rows) if not r[c]]
    ax.plot(miss, [0] * len(miss), "|", color=MUTED, ms=6)
    ax.set_title(name, loc="left", fontsize=10, color=INK)
    hi = max(ys); xi = xs[ys.index(hi)]
    ax.annotate(str(hi), (xi, hi), xytext=(0, 3), textcoords="offset points", ha="center", fontsize=8, color=INK)
    ax.set_ylim(0, ymax * 1.12)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    for s in ("left", "bottom"): ax.spines[s].set_color("#d0d7de")
    ax.tick_params(colors=MUTED, labelsize=8); ax.grid(axis="y", color="#eaeef2", lw=0.6); ax.set_axisbelow(True)
    ax.set_xticks([dt.date(2026, m, 1) for m in (7, 8, 9, 10, 11)]); ax.set_xticklabels(["Jul", "Aug", "Sep", "Oct", "Nov"])
axs[0].set_ylabel("drones reported per weekly update", fontsize=9, color=MUTED)
fig.suptitle("Drones reported near Ukraine's nuclear sites, per weekly IAEA update (Jun 26 - Nov 14, 2026)",
             x=0.01, ha="left", fontsize=11.5, color=INK)
fig.text(0.01, 0.01, "Source: IAEA Updates 355-375, coded blind by two models, reconciled by quote. Tick on the baseline = no number given that week (not zero). "
         "Counting era starts June 2026; earlier updates describe episodes only. errata.page", fontsize=7, color=MUTED)
fig.tight_layout(rect=(0, 0.04, 1, 0.94))
out = os.path.join(HERE, "data", "nukewatch-weekly.png"); fig.savefig(out); print(out)
