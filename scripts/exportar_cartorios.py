"""Export the registry-office tables from SQL Server to Parquet (one read per table), then profile them with DuckDB.

    python exportar_cartorios.py --server localhost --out D:\\cartorios_raw

Exports (raw copy for your machine only, never for GitHub):
  cartorios_2026.parquet       trabalhos_crawler_cartorios_2026_07_18.crawler_cartorios (48.8 k), WITHOUT the person
                               fields (responsavel, substituto) and without the raw HTML/JSON (conteudo*)
  atribuicoes_2026.parquet     …_2026_07_18.crawler_cartorios_atribuicoes
  faturamento_2026.parquet     …_2026_07_18.crawler_cartorios_faturamento
  decisoes_2026.parquet        …_2026_07_18.crawler_cartorios_decisoes (221 k, with the text)
  cartorios_2024.parquet       trabalhos_crawler_cartorios_2024_12_20.crawler_cartorios: only id and codigo_cns (to link
                               the long revenue series to 2026)
  faturamento_2024.parquet     …_2024_12_20.crawler_cartorios_faturamento (2.0 M, semesters since 2005)
  cidades_2026.parquet, cidade.parquet, estado.parquet   the city tables of the 2026 database
Not exported: responsaveis_historico, substitutos (names and CPF), bkp_denominacao, the 2024-04 database and
projeto_bavaresco (another client).

Then writes perfil_cartorios.txt next to the files (send it to Claude). Needs pyodbc, pyarrow and duckdb.
Re-running skips files that already exist.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

D26 = "trabalhos_crawler_cartorios_2026_07_18.dbo"
D24 = "trabalhos_crawler_cartorios_2024_12_20.dbo"
CART_COLS = ("id, id_cidade, id_crawler, codigo_cns, status, denominacao, data_criacao, tipo, situacao_juridica_responsavel, "
             "tipo_responsavel, assuncao, nomeacao, ingresso, uf, municipio, bairro, cep, endereco, telefone, email, "
             "recomendacao_corregedoria, funcionarios_clt, funcionarios_estatutario, horario_funcionamento, informatizada, "
             "acesso_internet, slug, website, numero, data_decisao, cidade_codigo_ibge, cidade_pais, cidade_sigla_pais, "
             "quantidade_colaboradores_estagiarios, quantidade_colaboradores_terceirizados, quantidade_total_colaboradores, "
             "conciliacao_mediacao, participa_sistema_interligado")
TABLES = {
    "cartorios_2026": f"SELECT {CART_COLS} FROM {D26}.crawler_cartorios WITH (NOLOCK)",
    "atribuicoes_2026": f"SELECT id, id_crawler_cartorio, atribuicao FROM {D26}.crawler_cartorios_atribuicoes WITH (NOLOCK)",
    "faturamento_2026": f"SELECT id, id_crawler_cartorio, periodo, quantidade, valor FROM {D26}.crawler_cartorios_faturamento WITH (NOLOCK)",
    "decisoes_2026": (f"SELECT id, id_crawler_cartorio, status, numero_do_processo, evento_do_processo, codigo_decisao, "
                      f"data_decisao, CAST(decisao AS nvarchar(max)) decisao, data_inclusao FROM {D26}.crawler_cartorios_decisoes WITH (NOLOCK)"),
    "cartorios_2024": f"SELECT id, codigo_cns FROM {D24}.crawler_cartorios WITH (NOLOCK)",
    "faturamento_2024": f"SELECT id, id_crawler_cartorio, periodo, quantidade, valor FROM {D24}.crawler_cartorios_faturamento WITH (NOLOCK)",
    "cidades_2026": f"SELECT id, id_crawler, nome, estado, municipio, slug FROM {D26}.crawler_cidades WITH (NOLOCK)",
    "cidade": f"SELECT * FROM {D26}.Cidade WITH (NOLOCK)",
    "estado": f"SELECT * FROM {D26}.Estado WITH (NOLOCK)",
}
BATCH = 100_000


def connect(server: str):
    import pyodbc
    return pyodbc.connect(f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};Trusted_Connection=yes", autocommit=True)


def export(cur, name: str, sql: str, out: Path) -> None:
    target = out / f"{name}.parquet"
    if target.exists():
        print(f"{name}: already there, skipped")
        return
    t0 = time.time()
    cur.execute(sql)
    cols = [c[0] for c in cur.description]
    writer, n = None, 0
    tmp = target.with_suffix(".tmp")
    while True:
        rows = cur.fetchmany(BATCH)
        if not rows:
            break
        data = {c: [r[i] for r in rows] for i, c in enumerate(cols)}
        table = pa.table({c: pa.array([None if v is None else (v if isinstance(v, (int, float, bool)) else str(v)) for v in vals])
                          for c, vals in data.items()})
        if writer is None:
            writer = pq.ParquetWriter(tmp, table.schema, compression="zstd")
        elif table.schema != writer.schema:
            table = table.cast(writer.schema)
        writer.write_table(table)
        n += len(rows)
    if writer:
        writer.close()
        tmp.replace(target)
    print(f"{name}: {n:,} rows in {time.time() - t0:.0f}s")


def profile(out: Path) -> None:
    import duckdb
    con = duckdb.connect()
    lines = []
    p = lambda *x: lines.append(" ".join(str(i) for i in x))  # noqa: E731
    for f in sorted(out.glob("*.parquet")):
        name = f.stem
        con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_parquet('{f.as_posix()}')")
        n = con.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
        p(f"\n## {name}: {n:,} rows")
        for (col, typ, *_) in con.execute(f"DESCRIBE {name}").fetchall():
            nn, nd = con.execute(f"SELECT count({col}), count(DISTINCT {col}) FROM {name}").fetchone()
            ex = con.execute(f"SELECT {col}::varchar v, count(*) c FROM {name} WHERE {col} IS NOT NULL "
                             f"GROUP BY 1 ORDER BY c DESC LIMIT 4").fetchall()
            exs = " | ".join(f"{(v or '')[:50]!r}×{c}" for v, c in ex)
            p(f"  {col:<38} {typ:<9} filled {nn:>9,}  distinct {nd:>9,}  top: {exs}")
    p("\n## links")
    p("2026 faturamento → cartorio:", con.execute("SELECT count(*) FROM faturamento_2026 f ANTI JOIN cartorios_2026 c ON f.id_crawler_cartorio = c.id").fetchone()[0], "orphans")
    p("2024 cns also in 2026:", con.execute("SELECT count(DISTINCT a.codigo_cns) FROM cartorios_2024 a JOIN cartorios_2026 b ON a.codigo_cns = b.codigo_cns").fetchone()[0])
    p("2024 periods:", con.execute("SELECT min(periodo), max(periodo), count(DISTINCT periodo) FROM faturamento_2024").fetchone())
    p("2026 periods:", con.execute("SELECT min(periodo), max(periodo), count(DISTINCT periodo) FROM faturamento_2026").fetchone())
    p("periods only in 2026:", [r[0] for r in con.execute("SELECT DISTINCT periodo FROM faturamento_2026 EXCEPT SELECT DISTINCT periodo FROM faturamento_2024 ORDER BY 1").fetchall()][:40])
    p("valor examples 2024:", [r[0] for r in con.execute("SELECT valor FROM faturamento_2024 USING SAMPLE 8 ROWS (reservoir, 7)").fetchall()])
    p("valor examples 2026:", [r[0] for r in con.execute("SELECT valor FROM faturamento_2026 USING SAMPLE 8 ROWS (reservoir, 7)").fetchall()])
    p("decisions with CPF-like text:", con.execute(r"SELECT count(*) FROM decisoes_2026 WHERE regexp_matches(decisao, '\d{3}\.?\d{3}\.?\d{3}-?\d{2}')").fetchone()[0])
    p("decision text length p50/p90/max:", con.execute("SELECT median(length(decisao)), quantile_cont(length(decisao), 0.9), max(length(decisao)) FROM decisoes_2026").fetchone())
    p("emails by domain (top 15):", con.execute("SELECT split_part(lower(email), '@', 2) d, count(*) c FROM cartorios_2026 WHERE email LIKE '%@%' GROUP BY 1 ORDER BY c DESC LIMIT 15").fetchall())
    p("types × status:", con.execute("SELECT tipo, status, count(*) FROM cartorios_2026 GROUP BY ALL ORDER BY 3 DESC LIMIT 20").fetchall())
    p("by uf:", con.execute("SELECT uf, count(*) FROM cartorios_2026 GROUP BY 1 ORDER BY 2 DESC").fetchall())
    (out / "perfil_cartorios.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"-> {out / 'perfil_cartorios.txt'}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server", default="localhost")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--only-profile", action="store_true")
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    if not a.only_profile:
        con = connect(a.server)
        cur = con.cursor()
        for name, sql in TABLES.items():
            export(cur, name, sql, a.out)
    profile(a.out)


if __name__ == "__main__":
    main()
