"""Write notebooks/estudo.ipynb (run it after with: jupyter nbconvert --to notebook --execute --inplace notebooks/estudo.ipynb).
The same notebook runs on Kaggle (files under /kaggle/input) and on a clone of the repo (data/)."""

from __future__ import annotations

from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
cells = [
    ("md", """# Cartórios do Brasil · Brazilian Notary and Registry Offices

A sample of about 1,000 of the 16,266 offices in the CNJ registry (Jul/2026), stratified by state, with their services,
the acts and revenue they reported per semester since 2005 and the decisions of the CNJ Corregedoria.

Data: [Kaggle](https://www.kaggle.com/datasets/caiquedourado/brazilian-notary-registry-offices) ·
code and data dictionary: [GitHub](https://github.com/CaiqueDourado/brazilian-notary-registry-offices)"""),
    ("code", """import glob, json, os
import duckdb

# Kaggle: /kaggle/input/…; GitHub clone: data/
found = glob.glob('/kaggle/input/**/serventias.parquet', recursive=True) or glob.glob('../data/serventias.parquet')
base = os.path.dirname(found[0])
SERV = f"read_parquet('{base}/serventias.parquet')"
ATR = f"read_csv_auto('{base}/atribuicoes.csv')"
ARR = f"read_csv_auto('{base}/arrecadacao.csv')"
DEC = f"read_csv_auto('{base}/decisoes.csv')"
stats = json.load(open(f'{base}/stats.json', encoding='utf-8'))
q = lambda sql: duckdb.sql(sql).df()
q(f'SELECT count(*) serventias, count(DISTINCT uf) ufs FROM {SERV}')"""),
    ("md", """## All offices, from `stats.json`

The sample has ~1,000 offices; `stats.json` keeps the counts of all 16,266."""),
    ("code", """{k: stats[k] for k in ('serventias_2026', 'serventias_por_status', 'serventias_por_tipo', 'atribuicoes')}"""),
    ("md", "## Offices per state and status (sample)"),
    ("code", """q(f'''SELECT uf, count(*) serventias, count(*) FILTER (status = 'Ativo') ativas,
      count(*) FILTER (situacao = 'VAGO') vagas FROM {SERV} GROUP BY ALL ORDER BY serventias DESC LIMIT 10''')"""),
    ("md", """## Services

One office can provide several services: in small towns one *Ofício Único* is notary, civil registry and real estate
registry at once."""),
    ("code", """q(f'''SELECT n_atribuicoes, count(*) serventias FROM
      (SELECT cns, count(*) n_atribuicoes FROM {ATR} GROUP BY 1) GROUP BY 1 ORDER BY 1''')"""),
    ("md", """## Revenue per year

Nominal R$, not adjusted for inflation. Early years may be one period per year; later ones are semesters. Only rows
with `situacao = 'informado'` have a value."""),
    ("code", """q(f'''SELECT year(inicio) ano, count(DISTINCT cns) serventias, round(sum(valor) / 1e6, 1) r_milhoes,
      round(median(valor)) mediana_periodo FROM {ARR} WHERE situacao = 'informado' GROUP BY 1 ORDER BY 1''')"""),
    ("md", "Over all offices (`stats.json`), in R$ billions:"),
    ("code", """{y: round(v / 1e9, 2) for y, v in stats['valor_por_ano'].items()}"""),
    ("md", "## Revenue per act, by service mix (last full year)"),
    ("code", """q(f'''WITH a AS (SELECT cns, sum(valor) valor, sum(atos) atos FROM {ARR}
                 WHERE situacao = 'informado' AND year(inicio) = 2025 GROUP BY 1),
         r AS (SELECT cns, bool_or(atribuicao = 'Registro de Imóveis') imoveis FROM {ATR} GROUP BY 1)
      SELECT imoveis, count(*) serventias, round(median(valor)) mediana_r, round(sum(valor) / sum(atos), 2) r_por_ato
      FROM a JOIN r USING (cns) WHERE atos > 0 GROUP BY 1''')"""),
    ("md", """## Corregedoria decisions

`texto` is kept only for standard texts; `texto_omitido` marks texts left out because they may name people."""),
    ("code", """q(f'''SELECT status, count(*) decisoes, count(texto) com_texto, count(*) FILTER (texto_omitido) omitidos
      FROM {DEC} GROUP BY 1 ORDER BY decisoes DESC''')"""),
    ("code", """q(f'SELECT texto, count(*) n FROM {DEC} WHERE texto IS NOT NULL GROUP BY 1 ORDER BY n DESC LIMIT 8')"""),
    ("md", "## One office as nested JSON"),
    ("code", """rec = json.loads(open(f'{base}/serventias.jsonl', encoding='utf-8').readline())
{k: (v[:3] if isinstance(v, list) else v) for k, v in rec.items()}"""),
    ("md", """## Join with the municipalities

`codigo_ibge` joins [municipios-e-estados-do-brasil](https://www.kaggle.com/datasets/caiquedourado/municipios-e-estados-do-brasil)
(population, region, coordinates). On Kaggle, add that dataset to the notebook."""),
    ("code", """mun = glob.glob('/kaggle/input/**/municipios.parquet', recursive=True)
if mun:
    display(q(f'''SELECT m.region, count(*) serventias, round(sum(m.population_2022) / count(DISTINCT m.ibge_code)) pop_media
                  FROM {SERV} s JOIN read_parquet('{mun[0]}') m ON m.ibge_code = s.codigo_ibge GROUP BY 1 ORDER BY 2 DESC'''))
else:
    print('add municipios-e-estados-do-brasil to join by codigo_ibge')"""),
]


def main() -> None:
    nb = nbf.v4.new_notebook()
    nb.cells = [nbf.v4.new_markdown_cell(s) if t == "md" else nbf.v4.new_code_cell(s) for t, s in cells]
    nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
    out = ROOT / "notebooks" / "estudo.ipynb"
    out.parent.mkdir(exist_ok=True)
    nbf.write(nb, out)
    print(out)


if __name__ == "__main__":
    main()
