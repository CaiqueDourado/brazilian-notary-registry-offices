"""Get the Kaggle folder ready to upload: dataset-metadata.json with the description and every file's columns.

    python scripts/prepare_kaggle.py --kaggle data
    kaggle datasets create -p data                 # first time
    kaggle datasets version -p data -m "…"         # later versions
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
S, I, N, B, DT = "string", "integer", "number", "boolean", "datetime"
SERV = [
    ("cns", S, "Código Nacional de Serventia (CNS), 6 digits: the national id of the office given by the CNJ"),
    ("denominacao", S, "Official name of the office"),
    ("status", S, "Ativo, Inativo or Extinto"),
    ("tipo", S, "PRIVATIZADO (run by a delegated notary), OFICIALIZADO (run by the state) or PUBLICO"),
    ("situacao", S, "Legal situation of the office in the CNJ: PROVIDO (filled by public exam), VAGO (vacant), INATIVA…"),
    ("tipo_responsavel", S, "Kind of person in charge: Titular, Interino, Interventor… (the person is not in the dataset)"),
    ("data_criacao", DT, "Date the office was created"),
    ("data_ultima_decisao", DT, "Date of the latest CNJ decision on the office"),
    ("uf", S, "State, 2 letters"), ("municipio", S, "Municipality as written by the CNJ"),
    ("codigo_ibge", I, "IBGE code of the municipality, joins municipios-e-estados-do-brasil"),
    ("bairro", S, "Neighbourhood"), ("cep", S, "Postal code, digits only"), ("endereco", S, "Street address"),
    ("numero", S, "Street number as written (s/n = no number)"),
    ("telefone", S, "Phone of the office, digits only, with area code"),
    ("email", S, "E-mail of the office. ***@domain when masked (personal provider or a person's name)"),
    ("email_mascarado", B, "True when the mailbox was masked"),
    ("website", S, "Website as informed, invalid values removed"),
    ("horario_funcionamento", S, "Opening hours per weekday"),
    ("informatizada", B, "The office is computerised"), ("acesso_internet", B, "The office has internet access"),
    ("conciliacao_mediacao", B, "The office offers conciliation and mediation"),
    ("sistema_interligado", B, "Takes part in the interconnected civil registry system"),
    ("funcionarios_clt", I, "Employees under the CLT"), ("funcionarios_estatutarios", I, "Statutory employees"),
    ("colaboradores_estagiarios", I, "Interns"), ("colaboradores_terceirizados", I, "Outsourced staff"),
    ("colaboradores_total", I, "Total staff"),
]
FILES = {
    "serventias.csv": ("Sample of offices (stratified by state), one per row, registry of Jul/2026.", SERV),
    "serventias.parquet": ("The same table as Parquet.", SERV),
    "atribuicoes.csv": ("The services each office provides.", [
        ("cns", S, "Office"), ("atribuicao", S, "Service: Notas, Registro Civil das Pessoas Naturais, Registro de Imóveis…")]),
    "arrecadacao.csv": ("Acts and revenue reported by each office, per semester (some early years per year), 2005 to 2026.", [
        ("cns", S, "Office"), ("inicio", DT, "First day of the period"), ("fim", DT, "Last day of the period"),
        ("situacao", S, "informado (value reported), pendente (not yet reported) or nao_informado"),
        ("atos", I, "Number of acts in the period"), ("valor", N, "Revenue in the period, R$, nominal"),
        ("fonte", S, "Collection the row comes from: 2026 (Jul/2026) or 2024 (Dec/2024, for periods 2026 does not have)")]),
    "decisoes.csv": ("Decisions of the CNJ Corregedoria on each office (status history).", [
        ("cns", S, "Office"), ("status", S, "Status set by the decision: PROVIDO, VAGO, CONVERSÃO EM DILIGÊNCIA…"),
        ("numero_processo", S, "Number of the administrative process, when there is one"),
        ("evento_processo", S, "Event of the process"), ("codigo_decisao", I, "Code of the decision type"),
        ("data_decisao", DT, "Date of the decision"), ("data_inclusao", DT, "When the decision was added to the CNJ system"),
        ("texto", S, "Text of the decision, only for standard texts (same text in 25+ offices, up to 600 characters)"),
        ("texto_omitido", B, "True when the text exists but was left out because it may name people")]),
    "serventias.jsonl": ("The same sample, one nested JSON per line: the office with its services, revenue and decisions.", None),
    "stats.json": ("Counts of the build and aggregates over ALL 16 thousand offices: per state, status, type, service, "
                   "revenue per year.", None),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kaggle", type=Path, required=True)
    k = ap.parse_args().kaggle
    resources = []
    for name, (desc, fields) in FILES.items():
        if not (k / name).exists():
            raise SystemExit(f"missing {k / name}: run build_cartorios.py first")
        r = {"path": name, "description": desc}
        if fields:
            r["schema"] = {"fields": [{"name": n, "type": t, "description": d} for n, t, d in fields]}
        resources.append(r)
    meta = {
        "title": "Cartórios do Brasil: serventias e arrecadação",
        "subtitle": "Sample of Brazil's notary offices with revenue since 2005 and CNJ decisions",
        "id": "caiquedourado/brazilian-notary-registry-offices",
        "licenses": [{"name": "Attribution 4.0 International (CC BY 4.0)"}],
        "keywords": ["brazil", "law", "government", "finance"],
        "description": (ROOT / "docs" / "kaggle-description.md").read_text(encoding="utf-8"),
        "isPrivate": False,
        "resources": resources,
    }
    text = json.dumps(meta, ensure_ascii=False, indent=1)
    (k / "dataset-metadata.json").write_text(text, encoding="utf-8")
    copy = ROOT / "kaggle" / "dataset-metadata.json"
    copy.parent.mkdir(exist_ok=True)
    copy.write_text(text, encoding="utf-8")  # the repo keeps a copy
    print(f"{len(resources)} files described -> {k / 'dataset-metadata.json'}")
    print(f"title {len(meta['title'])} chars · subtitle {len(meta['subtitle'])} chars")


if __name__ == "__main__":
    main()
