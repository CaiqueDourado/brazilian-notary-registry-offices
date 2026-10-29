"""Cover image (EN and PT) from data/stats.json and docs/example-serventia.json. Run: python scripts/make_cover.py"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from matplotlib.patches import FancyBboxPatch

from common import AQUA, ATTR_SHORT, BG, BLUE, CARD, INK, LINE, MONO, MUTED, ORANGE, num, plt, years

ROOT = Path(__file__).resolve().parents[1]
T = {
    "": dict(title="Brazilian Notary and Registry Offices · Cartórios do Brasil",
             sub="{n} offices registered with the CNJ · a sample of {s} with services, revenue since 2005 and Corregedoria decisions",
             p1="One office", p1s="docs/example-serventia.json", p2="Revenue per year", p2s="R$ billions, all offices, nominal",
             p3="Services", p3s="offices offering each one", city="city", status="status", serv="services", last="last semester",
             acts="acts", foot="brazilian-notary-registry-offices · source: CNJ Justiça Aberta"),
    ".pt-BR": dict(title="Cartórios do Brasil · serventias extrajudiciais",
                   sub="{n} serventias no cadastro do CNJ · amostra de {s} com atribuições, arrecadação desde 2005 e decisões da Corregedoria",
                   p1="Uma serventia", p1s="docs/example-serventia.json", p2="Arrecadação por ano", p2s="R$ bilhões, todas as serventias, nominal",
                   p3="Atribuições", p3s="serventias com cada uma", city="município", status="situação", serv="atribuições", last="último semestre",
                   acts="atos", foot="brazilian-notary-registry-offices · fonte: CNJ Justiça Aberta"),
}


def panel(ax, x, w, color, title, sub):
    ax.add_patch(FancyBboxPatch((x, 6), w, 52, boxstyle="round,pad=0,rounding_size=1.4", fc=CARD, ec=LINE, lw=1.1))
    ax.add_patch(FancyBboxPatch((x, 57.2), w, 0.8, boxstyle="square,pad=0", fc=color, ec="none"))
    ax.text(x + 2, 53, title, fontsize=13, weight="bold", color=INK, va="center")
    ax.text(x + 2, 49.2, sub, fontsize=8.6, color=MUTED, va="center")


def main() -> None:
    st = json.loads((ROOT / "data" / "stats.json").read_text(encoding="utf-8"))
    ex = json.loads((ROOT / "docs" / "example-serventia.json").read_text(encoding="utf-8"))
    out = ROOT / "docs" / "img"
    out.mkdir(parents=True, exist_ok=True)
    ys = years(st)
    last = [p for p in ex["arrecadacao"] if p["situacao"] == "informado"][-1]
    for suf, t in T.items():
        pt = bool(suf)
        fig = plt.figure(figsize=(12, 6.2), dpi=100)
        fig.patch.set_facecolor(BG)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, 120)
        ax.set_ylim(0, 74)
        ax.axis("off")
        ax.text(3, 69, t["title"], fontsize=21, weight="bold", color=INK, va="center")
        ax.text(3, 63.6, t["sub"].format(n=num(st["serventias_2026"], pt), s=num(st["amostra_serventias"], pt)),
                fontsize=10.5, color=MUTED, va="center")

        x1, w1 = 3, 38
        panel(ax, x1, w1, AQUA, t["p1"], t["p1s"])
        name = textwrap.wrap(ex["denominacao"], 42)
        name = name[:2] + (["…"] if len(name) > 2 else [])
        y = 44
        for ln in name:
            ax.text(x1 + 2, y, ln, fontsize=10, weight="bold", color=INK, va="center")
            y -= 3.6
        rows = [("CNS", ex["cns"]), (t["city"], f"{ex['municipio']} · {ex['uf']}"),
                (t["status"], f"{ex['status']} · {ex['situacao']}"), (t["serv"], str(len(ex["atribuicoes"]))),
                (t["last"], f"R$ {num(last['valor'], pt, 2)}"), (t["acts"], num(last["atos"], pt))]
        y -= 1.5
        for k, v in rows:
            ax.text(x1 + 2, y, k, fontsize=9, color=MUTED, va="center", family=MONO)
            ax.text(x1 + 15, y, v, fontsize=9.4, color=BLUE, va="center", family=MONO)
            y -= 4.3

        x2, w2 = x1 + w1 + 2.5, 36
        panel(ax, x2, w2, BLUE, t["p2"], t["p2s"])
        mx = max(b for _, b, _ in ys)
        bw = (w2 - 6) / len(ys)
        for i, (yr, b, _) in enumerate(ys):
            h = 30 * b / mx
            ax.add_patch(FancyBboxPatch((x2 + 3 + i * bw, 12), bw * 0.72, h, boxstyle="square,pad=0",
                                        fc=ORANGE if yr == 2020 else BLUE, ec="none"))
            if i in (0, len(ys) - 1):
                ax.text(x2 + 3 + i * bw + bw * 0.36, 12 + h + 1.4, num(b, pt, 1), fontsize=8.4, color=MUTED, ha="center")
                ax.text(x2 + 3 + i * bw + bw * 0.36, 9.4, str(yr), fontsize=8.4, color=MUTED, ha="center")

        x3 = x2 + w2 + 2.5
        panel(ax, x3, 117 - x3, ORANGE, t["p3"], t["p3s"])
        items = list(st["atribuicoes"].items())[:7]
        top = items[0][1]
        for i, (k, v) in enumerate(items):
            y = 43 - i * 5.4
            ax.text(x3 + 2, y + 1.3, ATTR_SHORT.get(k, (k, k))[0 if pt else 1], fontsize=8.8, color=INK, va="center")
            w = max(0.6, 19 * v / top)
            ax.add_patch(FancyBboxPatch((x3 + 2, y - 1.9), w, 1.7, boxstyle="square,pad=0", fc=ORANGE, ec="none"))
            ax.text(x3 + 2.8 + w, y - 1.05, num(v, pt), fontsize=8, color=MUTED, va="center")

        ax.text(3, 2.6, t["foot"], fontsize=8.4, color=MUTED)
        ax.text(117, 2.6, "github.com/CaiqueDourado", fontsize=8.4, color=MUTED, ha="right")
        fig.savefig(out / f"cover{suf}.png", facecolor=BG)
        plt.close(fig)
    print(f"-> {out}")


if __name__ == "__main__":
    main()
