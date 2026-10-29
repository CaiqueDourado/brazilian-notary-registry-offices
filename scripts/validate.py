"""Checks run in CI on data/ and docs/. Run: python scripts/validate.py"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).parent))
from build_cartorios import PERSONAL, ROLE  # noqa: E402

D = ROOT / "data"
SERV, ATR, ARR, DEC = (f"read_csv_auto('{(D / f).as_posix()}', all_varchar=true)"
                       for f in ("serventias.csv", "atribuicoes.csv", "arrecadacao.csv", "decisoes.csv"))
CLIENTS = re.compile(r"(?i)\b(juspodivm|vendah|bavaresco|allomni|push)\b")
UFS = {"AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ",
       "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"}
errors: list[str] = []


def check(ok: bool, msg: str) -> None:
    print(("ok   " if ok else "FAIL ") + msg)
    if not ok:
        errors.append(msg)


def one(sql: str):
    return duckdb.sql(sql).fetchall()[0][0]


st = json.loads((D / "stats.json").read_text(encoding="utf-8"))
cols = [r[0] for r in duckdb.sql(f"DESCRIBE SELECT * FROM {SERV}").fetchall()]
check(cols[:3] == ["cns", "denominacao", "status"] and len(cols) == 29, "serventias: the 29 columns")
check(not ({"responsavel", "substituto", "cpf"} & set(cols)), "serventias: no person columns")
check(one(f"SELECT count(*) - count(DISTINCT cns) FROM {SERV}") == 0, "serventias: one row per CNS")
check(one(f"SELECT count(*) FROM {SERV} WHERE NOT regexp_matches(cns, '^[0-9]{{6}}$')") == 0, "serventias: CNS with 6 digits")
check({r[0] for r in duckdb.sql(f"SELECT DISTINCT uf FROM {SERV}").fetchall()} == UFS, "serventias: all 27 UFs in the sample")
check(one(f"SELECT count(*) FROM {SERV}") == st["amostra_serventias"], "serventias: rows = stats amostra_serventias")
check(one(f"SELECT count(*) FROM read_parquet('{(D / 'serventias.parquet').as_posix()}')") == st["amostra_serventias"],
      "serventias.parquet: the same rows as the CSV")

emails = duckdb.sql(f"SELECT email, email_mascarado FROM {SERV} WHERE email IS NOT NULL").fetchall()
masked_ok = all((e.startswith("***@")) == (m == "true") for e, m in emails)
check(masked_ok, "e-mail: masked exactly when email_mascarado")
plain = [e for e, m in emails if m == "false"]
check(not [e for e in plain if e.split("@")[1] in PERSONAL], "e-mail: no personal provider left unmasked")
check(not [e for e in plain if not re.search(ROLE, e.split("@")[0])], "e-mail: unmasked mailboxes are roles, not people")

check(one(f"SELECT count(*) FROM {ATR} a ANTI JOIN {SERV} s USING (cns)") == 0, "atribuicoes: every CNS is in serventias")
check(one(f"SELECT count(*) FROM {ATR}") == st["amostra_atribuicoes"], "atribuicoes: rows = stats")

check(one(f"SELECT count(*) FROM {ARR} a ANTI JOIN {SERV} s USING (cns)") == 0, "arrecadacao: every CNS is in serventias")
check(one(f"SELECT count(*) - count(DISTINCT (cns, inicio, fim)) FROM {ARR}") == 0, "arrecadacao: one row per office and period")
check(one(f"SELECT count(*) FROM {ARR} a JOIN {ARR} b ON a.cns = b.cns AND a.inicio < b.inicio AND a.fim >= b.inicio") == 0,
      "arrecadacao: no overlapping periods")
check(one(f"SELECT count(*) FROM {ARR} WHERE inicio IS NULL OR fim IS NULL OR inicio > fim") == 0, "arrecadacao: valid periods")
check(one(f"SELECT count(*) FROM {ARR} WHERE situacao NOT IN ('informado', 'pendente', 'nao_informado') OR fonte NOT IN ('2024', '2026')") == 0,
      "arrecadacao: known situacao and fonte")
check(one(f"SELECT count(*) FROM {ARR} WHERE situacao = 'informado' AND valor IS NULL") == 0, "arrecadacao: informado has a value")
check(one(f"SELECT count(*) FROM {ARR}") == st["amostra_arrecadacao"], "arrecadacao: rows = stats")

check(one(f"SELECT count(*) FROM {DEC} d ANTI JOIN {SERV} s USING (cns)") == 0, "decisoes: every CNS is in serventias")
check(one(f"SELECT count(*) FROM {DEC} WHERE texto_omitido = 'true' AND texto IS NOT NULL") == 0, "decisoes: omitted texts are empty")
check(one(f"SELECT count(*) FROM {DEC} WHERE regexp_matches(texto, '<[a-zA-Z/][^>]*>')") == 0, "decisoes: no HTML in the texts")
check(one(f"SELECT count(*) FROM {DEC} WHERE length(texto) > 600") == 0, "decisoes: texts of up to 600 characters")
check(one(f"SELECT count(*) FROM {DEC}") == st["amostra_decisoes"], "decisoes: rows = stats")

text = "\n".join((D / f).read_text(encoding="utf-8") for f in ("serventias.csv", "decisoes.csv", "serventias.jsonl"))
cpf_hits = [m.group(0) for m in re.finditer(r"\d{3}\.\d{3}\.\d{3}-\d{2}", text)]
check(not cpf_hits, "files: no CPF number (000.000.000-00)")
mail_re = re.compile(r"[A-Za-z0-9._%+-]+@(" + "|".join(re.escape(d) for d in PERSONAL) + r")\b")
check(not [m for m in mail_re.finditer(text) if not m.group(0).startswith("***")], "files: no personal e-mail")
check(not CLIENTS.search(text), "files: no client names")

lines = (D / "serventias.jsonl").read_text(encoding="utf-8").splitlines()
recs = [json.loads(x) for x in lines]
check(len(recs) == st["amostra_serventias"], "serventias.jsonl: one office per line")
check(all(isinstance(r["arrecadacao"], list) and isinstance(r["decisoes"], list) for r in recs), "serventias.jsonl: nested lists")
check(sum(len(r["arrecadacao"]) for r in recs) == st["amostra_arrecadacao"], "serventias.jsonl: the same revenue rows as the CSV")
ex = json.loads((ROOT / "docs" / "example-serventia.json").read_text(encoding="utf-8"))
check(ex["cns"] in {r["cns"] for r in recs}, "docs/example-serventia.json: an office of the sample")
check(sum(st["serventias_por_uf"].values()) == st["serventias_2026"], "stats: offices per UF add up")
check(st["arrecadacao_sobreposicao_ok"] == 0 and st["cns_duplicados"] == 0, "stats: no overlap, no duplicated CNS in the full build")

print(f"\n{len(errors)} failure(s)")
sys.exit(1 if errors else 0)
