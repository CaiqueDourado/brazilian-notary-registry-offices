"""Shared style for the cover and the figures."""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

INK, MUTED, LINE, GRID, BG, CARD = "#111111", "#5c5c5c", "#d9dde3", "#e6e8eb", "#fdfdfc", "#ffffff"
BLUE, ORANGE, AQUA, VIOLET = "#2a78d6", "#eb6834", "#1baf7a", "#7c5cd6"
MONO = "DejaVu Sans Mono"
for fam in ("Inter", "DejaVu Sans"):
    try:
        matplotlib.font_manager.findfont(fam, fallback_to_default=False)
        plt.rcParams["font.family"] = fam
        break
    except ValueError:
        pass

ATTR_EN = {
    "Notas": "Notary (deeds)", "Registro Civil das Pessoas Naturais": "Civil registry (births, marriages, deaths)",
    "Protesto de Títulos": "Protest of bills", "Registro de Títulos e Documentos": "Registry of deeds and documents",
    "Registro Civil das Pessoas Jurídicas": "Registry of legal entities", "Registro de Imóveis": "Real estate registry",
    "Registro de Contratos Marítimos": "Maritime contracts", "Registro de Distribuição": "Distribution registry",
    "Registro de Interdições e Tutelas": "Interdictions and guardianships",
}
ATTR_SHORT = {
    "Notas": ("Notas", "Notary"), "Registro Civil das Pessoas Naturais": ("Registro Civil (PN)", "Civil registry"),
    "Protesto de Títulos": ("Protesto", "Protest of bills"), "Registro de Títulos e Documentos": ("Títulos e Documentos", "Deeds and documents"),
    "Registro Civil das Pessoas Jurídicas": ("Pessoas Jurídicas", "Legal entities"), "Registro de Imóveis": ("Imóveis", "Real estate"),
    "Registro de Contratos Marítimos": ("Contratos Marítimos", "Maritime contracts"), "Registro de Distribuição": ("Distribuição", "Distribution"),
    "Registro de Interdições e Tutelas": ("Interdições e Tutelas", "Interdictions"),
}


def num(n: float, pt: bool, d: int = 0) -> str:
    s = f"{n:,.{d}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".") if pt else s


def years(st: dict) -> list[tuple[int, float, int]]:
    """(year, revenue in R$ billions, offices with an informed value) for the full years of the series."""
    n = st.get("valor_por_ano_n_serventias", {})
    last = max(int(y) for y in st["valor_por_ano"])
    return [(int(y), v / 1e9, n.get(y, 0)) for y, v in sorted(st["valor_por_ano"].items()) if int(y) < last]
