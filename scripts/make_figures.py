"""Figures for the README and Kaggle, from data/stats.json (aggregates over ALL offices, not the sample).

    python scripts/make_figures.py

docs/img/arrecadacao.png  revenue per year, 2005 to the last full year
docs/img/uf.png           offices per state
(and .pt-BR.png versions)
"""

from __future__ import annotations

import json
from pathlib import Path

from common import BG, BLUE, GRID, INK, MUTED, ORANGE, num, plt, years

ROOT = Path(__file__).resolve().parents[1]
T = {
    "": dict(rev="Revenue reported by the offices, per year", revs="R$ billions, nominal (not adjusted for inflation) · offices registered in {m}",
             uf="Offices per state", ufs="{n} offices registered with the CNJ in {m}, active, inactive and extinct",
             src="Source: CNJ Justiça Aberta · brazilian-notary-registry-offices", bi="R$ {v} bi", off="{n} offices"),
    ".pt-BR": dict(rev="Arrecadação declarada pelas serventias, por ano", revs="R$ bilhões, valores nominais (sem correção) · serventias do cadastro de {m}",
                   uf="Serventias por UF", ufs="{n} serventias no cadastro do CNJ em {m}, ativas, inativas e extintas",
                   src="Fonte: CNJ Justiça Aberta · brazilian-notary-registry-offices", bi="R$ {v} bi", off="{n} serventias"),
}
MONTH = {"": "Jul/2026", ".pt-BR": "jul/2026"}


def style(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK, labelsize=9.5, length=0)
    ax.set_facecolor(BG)


def main() -> None:
    st = json.loads((ROOT / "data" / "stats.json").read_text(encoding="utf-8"))
    out = ROOT / "docs" / "img"
    out.mkdir(parents=True, exist_ok=True)
    ys = years(st)
    for suf, t in T.items():
        pt, m = bool(suf), MONTH[suf]

        fig, ax = plt.subplots(figsize=(11, 5.6), dpi=110)
        fig.patch.set_facecolor(BG)
        style(ax)
        x = [y for y, _, _ in ys]
        v = [b for _, b, _ in ys]
        ax.bar(x, v, color=[ORANGE if y == 2020 else BLUE for y in x], width=0.72)
        for y, b, _ in ys:
            if y in (x[0], 2010, 2015, 2019, 2020, 2021, x[-1]):
                ax.text(y, b + max(v) * 0.015, num(b, pt, 1), ha="center", fontsize=8.5, color=MUTED)
        ax.set_xticks(x)
        ax.set_xticklabels([str(y)[2:] if i % 1 == 0 else "" for i, y in enumerate(x)])
        ax.yaxis.set_visible(False)
        ax.set_ylim(0, max(v) * 1.12)
        fig.text(0.02, 0.94, t["rev"], fontsize=16, weight="bold", color=INK)
        fig.text(0.02, 0.895, t["revs"].format(m=m), fontsize=10, color=MUTED)
        fig.text(0.02, 0.015, t["src"], fontsize=8, color=MUTED)
        fig.subplots_adjust(left=0.03, right=0.98, top=0.85, bottom=0.08)
        fig.savefig(out / f"arrecadacao{suf}.png", facecolor=BG)
        plt.close(fig)

        items = sorted(st["serventias_por_uf"].items(), key=lambda kv: kv[1])
        fig, ax = plt.subplots(figsize=(10, 8), dpi=110)
        fig.patch.set_facecolor(BG)
        style(ax)
        vals = [n for _, n in items]
        ax.barh([u for u, _ in items], vals, color=BLUE, height=0.7)
        for i, n in enumerate(vals):
            ax.text(n + max(vals) * 0.008, i, num(n, pt), va="center", fontsize=8.5, color=MUTED)
        ax.xaxis.set_visible(False)
        ax.set_xlim(0, max(vals) * 1.1)
        fig.text(0.02, 0.965, t["uf"], fontsize=16, weight="bold", color=INK)
        fig.text(0.02, 0.937, t["ufs"].format(n=num(st["serventias_2026"], pt), m=m), fontsize=10, color=MUTED)
        fig.text(0.02, 0.012, t["src"], fontsize=8, color=MUTED)
        fig.subplots_adjust(left=0.07, right=0.97, top=0.91, bottom=0.04)
        fig.savefig(out / f"uf{suf}.png", facecolor=BG)
        plt.close(fig)
    print(f"-> {out}")


if __name__ == "__main__":
    main()
