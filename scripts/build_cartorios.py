"""Build brazilian-notary-registry-offices (SAMPLE ONLY) from the Parquet export of exportar_cartorios.py.

    python build_cartorios.py --raw D:\\cartorios_raw --out D:\\cartorios_out [--sample 1000]

Decisions (Caique, 29/10/2026): publish only a sample, on GitHub and Kaggle; registry of Jul/2026, revenue series of
Dec/2024 (since 2005) joined to the 2026 semesters by the CNS code; Corregedoria decisions WITH the text; phone and
e-mail kept, but e-mails on personal providers (gmail, hotmail…) masked; CPF numbers and personal e-mails masked
inside the decision text; no person fields (responsible, substitutes).
Review of the first sample (29/10): institutional mailboxes that are a person's name (maria.souza@tj…) are masked too;
decision texts are published only when the same text is in >= 25 offices and has <= 600 characters (long pareceres
name people), HTML removed; revenue de-duplicated (the 2024 crawl has several ids per CNS) and a 2024 period is
dropped when it overlaps a 2026 period of the same office. Second review: e-mails inside the website field
dropped; a CPF is masked only when it is not part of a longer number (process numbers); HTML entities and Word's
style header removed from the texts.

Writes in --out/brazilian-notary-registry-offices/data:
  serventias.csv / .parquet     one office per row (sample)
  atribuicoes.csv               office × service (Notas, Registro Civil…)
  arrecadacao.csv               office × period: acts and revenue, 2005–2026 (one row per period)
  decisoes.csv                  Corregedoria decisions per office (text masked)
  serventias.jsonl              the same sample, one nested JSON per office (attributions, revenue, decisions)
  stats.json                    counts of the build and aggregates over ALL offices (no rows)
and docs/example-serventia.json (one office, for the README image). Needs duckdb.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

PERSONAL = ["gmail.com", "hotmail.com", "hotmail.com.br", "yahoo.com", "yahoo.com.br", "outlook.com", "outlook.com.br",
            "live.com", "msn.com", "uol.com.br", "bol.com.br", "terra.com.br", "ig.com.br", "icloud.com", "globo.com",
            "globomail.com", "r7.com", "zipmail.com.br", "oi.com.br", "superig.com.br", "brturbo.com.br", "pop.com.br",
            "yahoo.com.ar", "gmail.com.br", "me.com", "aol.com", "protonmail.com", "click21.com.br", "gamil.com",
            "hotmai.com", "hotmal.com", "ibest.com.br", "veloxmail.com.br", "itelefonica.com.br", "bol.com", "ymail.com",
            "rocketmail.com", "mail.com", "gmx.com", "zoho.com", "vivax.com.br", "gvt.com.br",
            "onda.com.br", "sercomtel.com.br", "netsite.com.br", "brturbo.com", "globo.com.br", "hotmail.es", "outlook.es",
            "live.com.br", "yahoo.es", "terra.com", "uol.com", "googlemail.com"]
# On institutional domains the mailbox is kept only when it names a role or the office (contato@, cartorio@,
# registrocivil@, oficio1@…); a mailbox that is a person's name (maria.souza@tj…, flavia@…) is masked as ***@domain.
ROLE = (r"(contat|cart|of[ií]c|offic|reg|rcp|rtd|rgi|^ri|tabel|nota|prot|im[oó]v|civil|serv|adm|secret|atend|financ|"
        r"jur[ií]d|escrit|sac|ouvid|cns|comarca|distr|^tj|extra|[0-9]|fale|geral|info|recep|pedido|certid|arpen|anoreg|"
        r"titul|interin|sede|nucleo|correg|cgj|mail|suporte|protocolo|expediente|cobranca|faturamento|diretoria|"
        r"gerencia|juizo|forum|f[oó]rum|vara|cejusc|contabil|rh|ti$)")
TEXT_MIN_OFFICES = 25   # a decision text is published only when the same text appears in at least this many offices
TEXT_MAX_LEN = 600      # …and is short: long, unique texts (pareceres) carry names of people
CPF = r"\d{3}\.?\d{3}\.?\d{3}\s?-?\s?\d{2}"
EMAIL = r"[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sample", type=int, default=1000, help="offices in the sample (stratified by UF)")
    a = ap.parse_args()
    import duckdb

    root = a.out / "brazilian-notary-registry-offices"
    data, docs = root / "data", root / "docs"
    for d in (data, docs):
        d.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    for f in a.raw.glob("*.parquet"):
        con.execute(f"CREATE VIEW raw_{f.stem} AS SELECT * FROM read_parquet('{f.as_posix()}')")
    q = lambda sql: con.execute(sql).fetchall()  # noqa: E731
    personal = ",".join(f"'{d}'" for d in PERSONAL)
    con.execute(f"CREATE TEMP TABLE personal AS SELECT unnest([{personal}]) d")
    role = ROLE.replace("'", "''")

    def empty(c):  # '' and placeholders → NULL
        return f"NULLIF(NULLIF(NULLIF(trim({c}), ''), '-'), '0')"

    def date(c):
        return f"try_strptime(NULLIF(trim({c}), ''), ['%d/%m/%Y %H:%M:%S', '%d/%m/%Y', '%Y-%m-%d'])::DATE"

    # ---- offices (all), cleaned
    con.execute(f"""CREATE TABLE serv AS SELECT
        id AS id_2026,
        lpad(regexp_replace(codigo_cns, '[^0-9]', '', 'g'), 6, '0') AS cns,
        trim(denominacao) AS denominacao, status, tipo,
        NULLIF(trim(situacao_juridica_responsavel), '') AS situacao,
        NULLIF(NULLIF(trim(tipo_responsavel), ''), '-') AS tipo_responsavel,
        {date('data_criacao')} AS data_criacao,
        {date('data_decisao')} AS data_ultima_decisao,
        uf, trim(municipio) AS municipio, NULLIF(cidade_codigo_ibge, '') AS codigo_ibge,
        NULLIF(trim(bairro), '') AS bairro, NULLIF(regexp_replace(cep, '[^0-9]', '', 'g'), '') AS cep,
        NULLIF(trim(endereco), '') AS endereco, NULLIF(trim(numero), '') AS numero,
        NULLIF(regexp_replace(telefone, '[^0-9]', '', 'g'), '') AS telefone,
        CASE WHEN em_ok THEN CASE WHEN em_mask THEN '***@' || em_dom ELSE em END END AS email,
        CASE WHEN em_ok THEN em_mask END AS email_mascarado,
        CASE WHEN regexp_matches(lower(trim(website)), '^(https?://)?[a-z0-9-]+(\\.[a-z0-9-]+)+') AND website NOT LIKE '%@%' THEN lower(trim(website)) END AS website,
        NULLIF(trim(horario_funcionamento), '') AS horario_funcionamento,
        CASE informatizada WHEN 'S' THEN true WHEN 'N' THEN false END AS informatizada,
        CASE acesso_internet WHEN 'S' THEN true WHEN 'N' THEN false END AS acesso_internet,
        CASE conciliacao_mediacao WHEN 'S' THEN true WHEN 'N' THEN false END AS conciliacao_mediacao,
        participa_sistema_interligado = 'True' AS sistema_interligado,
        try_cast(NULLIF(funcionarios_clt, '') AS INT) AS funcionarios_clt,
        try_cast(NULLIF(funcionarios_estatutario, '') AS INT) AS funcionarios_estatutarios,
        quantidade_colaboradores_estagiarios AS colaboradores_estagiarios,
        quantidade_colaboradores_terceirizados AS colaboradores_terceirizados,
        quantidade_total_colaboradores AS colaboradores_total
        FROM (SELECT *, em_ok AND (em_dom IN (SELECT d FROM personal) OR NOT regexp_matches(em_box, '{role}')) AS em_mask
              FROM (SELECT *, regexp_matches(em, '^[^@\\s]+@[a-z0-9-]+(\\.[a-z0-9-]+)+$') AS em_ok
                    FROM (SELECT *, split_part(em, '@', 1) em_box, split_part(em, '@', 2) em_dom
                          FROM (SELECT *, lower(regexp_replace(trim(email), '[\\s;,]+.*$', '')) em FROM raw_cartorios_2026))))""")
    stats: dict = {"serventias_2026": q("SELECT count(*) FROM serv")[0][0],
                   "cns_duplicados": q("SELECT count(*) - count(DISTINCT cns) FROM serv")[0][0],
                   "emails_mascarados": q("SELECT count(*) FROM serv WHERE email_mascarado")[0][0],
                   "emails_mascarados_provedor_pessoal": q(f"SELECT count(*) FROM serv WHERE email_mascarado AND split_part(email, '@', 2) IN (SELECT d FROM personal)")[0][0],
                   "emails_institucionais": q("SELECT count(*) FROM serv WHERE email IS NOT NULL AND NOT email_mascarado")[0][0]}

    # ---- revenue: 2026 semesters + 2024 series for the periods 2026 does not have
    def periods(src, join):
        """Revenue rows of one source, with the period as start and end dates and the state of the value."""
        return f"""SELECT x.cns,
            try_strptime(regexp_extract(p, 'De (\\d{{2}}/\\d{{2}}/\\d{{4}})', 1), '%d/%m/%Y')::DATE AS inicio,
            try_strptime(regexp_extract(p, '(?:até|atÃ©|ate) (\\d{{2}}/\\d{{2}}/\\d{{4}})', 1), '%d/%m/%Y')::DATE AS fim,
            CASE WHEN upper(trim(f.valor)) = 'PENDENTE' OR upper(trim(f.quantidade)) = 'PENDENTE' THEN 'pendente'
                 WHEN upper(trim(f.valor)) LIKE 'N%O INFORMADO' THEN 'nao_informado' ELSE 'informado' END AS situacao,
            try_cast(trim(f.quantidade) AS BIGINT) AS atos, try_cast(trim(f.valor) AS DECIMAL(18,2)) AS valor
            FROM (SELECT *, replace(replace(periodo, '&bull;', ''), 'atÃ©', 'até') p FROM {src}) f {join}"""
    # the crawls hold the same office more than once (several ids per CNS) → one row per office and period
    one = ("QUALIFY row_number() OVER (PARTITION BY cns, inicio, fim ORDER BY (situacao = 'informado') DESC, "
           "valor DESC NULLS LAST, atos DESC NULLS LAST) = 1")
    con.execute(f"CREATE TABLE arr26 AS SELECT * FROM ({periods('raw_faturamento_2026', 'JOIN serv x ON x.id_2026 = f.id_crawler_cartorio')}) {one}")
    con.execute("""CREATE TABLE c24 AS SELECT id, lpad(regexp_replace(codigo_cns, '[^0-9]', '', 'g'), 6, '0') AS cns
                   FROM raw_cartorios_2024""")
    con.execute(f"CREATE TABLE arr24 AS SELECT * FROM ({periods('raw_faturamento_2024', 'JOIN c24 x ON x.id = f.id_crawler_cartorio')}) {one}")
    con.execute("""CREATE TABLE arr AS
        SELECT cns, inicio, fim, situacao, atos, valor, '2026' AS fonte FROM arr26
        UNION ALL
        SELECT a.cns, a.inicio, a.fim, a.situacao, a.atos, a.valor, '2024' FROM arr24 a
        WHERE a.cns IN (SELECT cns FROM serv)
          AND NOT EXISTS (SELECT 1 FROM arr26 b WHERE b.cns = a.cns AND a.inicio <= b.fim AND a.fim >= b.inicio)""")
    stats.update({
        "cns_2024_em_2026": q("SELECT count(DISTINCT cns) FROM c24 WHERE cns IN (SELECT cns FROM serv)")[0][0],
        "cns_2024_total": q("SELECT count(DISTINCT cns) FROM c24")[0][0],
        "periodos_sem_data": q("SELECT count(*) FROM arr WHERE inicio IS NULL OR fim IS NULL")[0][0],
        "arrecadacao_duplicadas_removidas": q("SELECT (SELECT count(*) FROM raw_faturamento_2026) + (SELECT count(*) FROM raw_faturamento_2024 f JOIN c24 x ON x.id = f.id_crawler_cartorio) - (SELECT count(*) FROM arr26) - (SELECT count(*) FROM arr24)")[0][0],
        "arrecadacao_sobreposicao_ok": q("SELECT count(*) FROM arr a JOIN arr b ON a.cns = b.cns AND a.inicio < b.inicio AND a.fim >= b.inicio")[0][0],
        "comparacao_fontes_mesmo_periodo": {str(y): [float(v24 or 0), float(v26 or 0), n] for y, v24, v26, n in q(
            "SELECT year(inicio), sum(a.valor), sum(b.valor), count(*) FROM arr24 a JOIN arr26 b USING (cns, inicio, fim) "
            "WHERE a.situacao = 'informado' AND b.situacao = 'informado' GROUP BY 1 ORDER BY 1")},
        "valor_por_ano_n_serventias": {str(y): n for y, n in q("SELECT year(inicio), count(DISTINCT cns) FROM arr WHERE situacao = 'informado' GROUP BY 1 ORDER BY 1")},
        "arrecadacao_linhas_por_fonte": dict(q("SELECT fonte, count(*) FROM arr GROUP BY 1")),
        "arrecadacao_situacao": dict(q("SELECT situacao, count(*) FROM arr GROUP BY 1")),
        "arrecadacao_periodos": q("SELECT min(inicio)::VARCHAR, max(fim)::VARCHAR, count(DISTINCT inicio) FROM arr")[0],
        "valor_por_ano": {str(y): float(v or 0) for y, v in q("SELECT year(inicio) y, sum(valor) FROM arr WHERE inicio IS NOT NULL GROUP BY 1 ORDER BY 1")},
        "serventias_por_uf": dict(q("SELECT uf, count(*) FROM serv GROUP BY 1 ORDER BY 2 DESC")),
        "serventias_por_status": dict(q("SELECT status, count(*) FROM serv GROUP BY 1 ORDER BY 2 DESC")),
        "serventias_por_tipo": dict(q("SELECT tipo, count(*) FROM serv GROUP BY 1 ORDER BY 2 DESC")),
        "atribuicoes": dict(q("SELECT atribuicao, count(*) FROM raw_atribuicoes_2026 GROUP BY 1 ORDER BY 2 DESC")),
    })

    # ---- decisions, text masked
    def clean_text(c):
        """HTML tags and entities out, Word's style header out, spaces collapsed."""
        t = f"regexp_replace({c}, '<[^>]*>', ' ', 'g')"
        for ent, ch in (("&nbsp;", " "), ("&#160;", " "), ("&ndash;", "–"), ("&mdash;", "—"), ("&quot;", '"'), ("&amp;", "&")):
            t = f"replace({t}, '{ent}', '{ch}')"
        t = f"regexp_replace({t}, 'Normal \\d+ \\d+ (?:(?:false|true) )+PT-BR X-NONE X-NONE ', '', 'g')"
        return f"trim(regexp_replace({t}, '\\s+', ' ', 'g'))"

    def cpf_mask(t):
        """CPF numbers masked; a CPF-like run inside a longer number (process numbers) is left alone."""
        return f"regexp_replace({t}, '(^|[^0-9]){CPF}([^0-9]|$)', '\\1***.***.***-**\\2', 'g')"

    personal_re = "|".join(d.replace(".", "\\.") for d in PERSONAL)
    con.execute(f"""CREATE TABLE dec0 AS SELECT s.cns, d.status, NULLIF(trim(d.numero_do_processo), '') AS numero_processo,
        NULLIF(trim(d.evento_do_processo), '') AS evento_processo, d.codigo_decisao,
        {date('d.data_decisao')} AS data_decisao,
        regexp_replace({cpf_mask(clean_text('d.decisao'))},
                       '[A-Za-z0-9._%+-]+@((?:{personal_re}))', '***@\\1', 'g') AS texto_bruto,
        try_strptime(d.data_inclusao, '%Y-%m-%d %H:%M:%S') AS data_inclusao
        FROM raw_decisoes_2026 d JOIN serv s ON s.id_2026 = d.id_crawler_cartorio""")
    con.execute(f"""CREATE TABLE dec AS SELECT * EXCLUDE (texto_bruto, k),
        CASE WHEN k >= {TEXT_MIN_OFFICES} AND length(texto_bruto) <= {TEXT_MAX_LEN} THEN texto_bruto END AS texto,
        texto_bruto IS NOT NULL AND NOT (k >= {TEXT_MIN_OFFICES} AND length(texto_bruto) <= {TEXT_MAX_LEN}) AS texto_omitido
        FROM (SELECT *, count(DISTINCT cns) OVER (PARTITION BY texto_bruto) k FROM dec0)""")
    stats["decisoes"] = q("SELECT count(*) FROM dec")[0][0]
    stats["decisoes_com_cpf_mascarado"] = q("SELECT count(*) FROM dec0 WHERE texto_bruto LIKE '%***.***.***-**%'")[0][0]
    stats["decisoes_texto_publicado"] = q("SELECT count(*) FROM dec WHERE texto IS NOT NULL")[0][0]
    stats["decisoes_texto_omitido"] = q("SELECT count(*) FROM dec WHERE texto_omitido")[0][0]
    stats["decisoes_textos_distintos_publicados"] = q("SELECT count(DISTINCT texto) FROM dec")[0][0]
    stats["decisoes_por_status"] = dict(q("SELECT status, count(*) FROM dec GROUP BY 1 ORDER BY 2 DESC"))

    # ---- sample: stratified by UF (at least 5 per UF), deterministic
    n_all = stats["serventias_2026"]
    con.execute(f"""CREATE TABLE amostra AS SELECT cns FROM (
        SELECT cns, uf, row_number() OVER (PARTITION BY uf ORDER BY hash(cns)) rn,
               count(*) OVER (PARTITION BY uf) n FROM serv)
        WHERE rn <= greatest(5, round(n * {a.sample} / {n_all}))""")
    stats["amostra_serventias"] = q("SELECT count(*) FROM amostra")[0][0]
    S = "WHERE cns IN (SELECT cns FROM amostra)"
    con.execute(f"COPY (SELECT * EXCLUDE (id_2026) FROM serv {S} ORDER BY uf, municipio, cns) TO '{(data / 'serventias.parquet').as_posix()}' (FORMAT parquet)")
    con.execute(f"COPY (SELECT * EXCLUDE (id_2026) FROM serv {S} ORDER BY uf, municipio, cns) TO '{(data / 'serventias.csv').as_posix()}' (HEADER)")
    con.execute(f"COPY (SELECT s.cns, a.atribuicao FROM raw_atribuicoes_2026 a JOIN serv s ON s.id_2026 = a.id_crawler_cartorio "
                f"WHERE s.cns IN (SELECT cns FROM amostra) ORDER BY 1, 2) TO '{(data / 'atribuicoes.csv').as_posix()}' (HEADER)")
    con.execute(f"COPY (SELECT * FROM arr {S} ORDER BY cns, inicio) TO '{(data / 'arrecadacao.csv').as_posix()}' (HEADER)")
    con.execute(f"COPY (SELECT * FROM dec {S} ORDER BY cns, data_decisao, data_inclusao) TO '{(data / 'decisoes.csv').as_posix()}' (HEADER)")
    for t in ("atribuicoes", "arrecadacao", "decisoes"):
        stats[f"amostra_{t}"] = q(f"SELECT count(*) FROM read_csv_auto('{(data / (t + '.csv')).as_posix()}')")[0][0]

    # ---- nested JSON per office
    rows = con.execute(f"""SELECT s.* EXCLUDE (id_2026),
        (SELECT list(atribuicao ORDER BY atribuicao) FROM raw_atribuicoes_2026 a WHERE a.id_crawler_cartorio = s.id_2026) atribuicoes,
        (SELECT list(struct_pack(inicio := inicio::VARCHAR, fim := fim::VARCHAR, situacao := situacao, atos := atos,
                                 valor := valor::DOUBLE, fonte := fonte) ORDER BY inicio) FROM arr r WHERE r.cns = s.cns) arrecadacao,
        (SELECT list(struct_pack(data := data_decisao::VARCHAR, status := status, processo := numero_processo,
                                 texto := texto, texto_omitido := texto_omitido) ORDER BY data_decisao) FROM dec d WHERE d.cns = s.cns) decisoes
        FROM serv s WHERE s.cns IN (SELECT cns FROM amostra) ORDER BY uf, municipio, cns""")
    cols = [c[0] for c in rows.description]
    with open(data / "serventias.jsonl", "w", encoding="utf-8") as f:
        best, best_score = None, -1
        for r in rows.fetchall():
            rec = {c: (v.isoformat() if hasattr(v, "isoformat") else v) for c, v in zip(cols, r)}
            for k in ("arrecadacao", "decisoes", "atribuicoes"):
                rec[k] = rec[k] or []
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            score = (rec["status"] == "Ativo") * 100 + min(len(rec["arrecadacao"]), 40) + min(len(rec["decisoes"]), 5) * 2 \
                + len(rec["atribuicoes"]) * 3 + (rec["email"] is not None and not rec["email_mascarado"]) * 10
            if score > best_score:
                best, best_score = rec, score
    (docs / "example-serventia.json").write_text(json.dumps(best, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    (data / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()
