**Cartórios do Brasil · Brazilian Notary and Registry Offices**: Brazil has **16,266 notary and registry offices** (*cartórios*) in the registry of the National Council of Justice (CNJ). This dataset is a **sample of 1,009 of them**, stratified by state, with the registry of each office (name, CNS code, status, address, phone, institutional e-mail, opening hours, staff), the **services** it provides, the **acts and revenue it reported per semester from 2005 to 2026**, and the **decisions of the CNJ Corregedoria** on it. `stats.json` adds the aggregates of all 16,266 offices.

![Brazilian Notary and Registry Offices](https://raw.githubusercontent.com/CaiqueDourado/brazilian-notary-registry-offices/main/docs/img/cover.png)

## One office in JSON

![One office as nested JSON](https://raw.githubusercontent.com/CaiqueDourado/brazilian-notary-registry-offices/main/docs/img/serventia-json.png)

Each line of `serventias.jsonl` is one office with its services, revenue and decisions nested (the image cuts the long lists).

## Files

All files join by `cns`, the national code of the office.

- `serventias.csv` / `serventias.parquet` (1,009 rows): one office per row, registry of Jul/2026. `codigo_ibge` joins [municipios-e-estados-do-brasil](https://www.kaggle.com/datasets/caiquedourado/municipios-e-estados-do-brasil).
- `atribuicoes.csv` (2,311 rows): office × service (Notas, Registro Civil, Registro de Imóveis, Protesto…).
- `arrecadacao.csv` (38,272 rows): office × period, with `atos`, `valor` (R$, nominal), `situacao` (informado, pendente, nao_informado) and `fonte` (the collection the row comes from).
- `decisoes.csv` (4,402 rows): Corregedoria decisions, with `texto` only for standard texts and `texto_omitido`.
- `serventias.jsonl`: the same sample, nested.
- `stats.json`: build counts and aggregates of all offices (per state, status, type, service, revenue per year).

## The site this comes from

The crawler behind this dataset was written in 2024 for **Portal de Cartórios no Brasil** (`****.com.br`, a client's site, address withheld), a directory with one page per office (address, phone, services, revenue history) built from these tables and published on WordPress. In 2026 it was rewritten for the new JSON pages of the CNJ, which added the Corregedoria decisions.

![Organic traffic of the portal, estimated by Semrush](https://raw.githubusercontent.com/CaiqueDourado/brazilian-notary-registry-offices/main/docs/img/portal-cartorios-semrush.png)

Organic traffic of the portal estimated by Semrush, Nov/2024 to Oct/2026: about 116 thousand visits a month at the end of the period.

## What the data shows

![Revenue per year](https://raw.githubusercontent.com/CaiqueDourado/brazilian-notary-registry-offices/main/docs/img/arrecadacao.png)

- **Revenue grew tenfold in nominal terms**: R$ 3.7 billion in 2005, R$ 18.2 billion in 2019, R$ 38.0 billion in 2025 (offices of the 2026 registry, not adjusted for inflation). 2020 dipped (R$ 18.0 billion), then 2021 jumped 37% to R$ 24.6 billion. The jump is not the change of collection: in the periods both collections have (2020–2024) their totals differ by less than 0.4%.
- **Revenue is concentrated.** In the sample, the median office reported R$ 440 thousand in 2025; the top 50 offices (5%) took 54% of the total. Offices with a real estate registry earn R$ 152 per act, the others R$ 50.
- **Minas Gerais has the most offices** (3,213), then Bahia (1,804) and São Paulo (1,680); Roraima has 19. Many small municipalities and districts have their own civil registry.
- **Notary (9,699 offices) and civil registry (8,879)** are the most common services; 4,136 offices keep real estate records. 12,203 offices are active, 3,881 inactive, 182 extinct; 79% are privatized (run by a delegated notary).
- **Almost half of the decisions say *vacant*.** VAGO is the status of 35,306 of the 73,774 decisions: since its Resolution 80 (2009) the CNJ has been reviewing offices filled without a public exam after the 1988 Constitution.

## How it was made

![How it was made](https://raw.githubusercontent.com/CaiqueDourado/brazilian-notary-registry-offices/main/docs/img/flow.png)

- **Source**: the public registry of the CNJ, *Justiça Aberta* (justicaaberta.cnj.jus.br), one page per office.
- **Two collections**: Dec/2024 (HTML; revenue since 2005) and Jul/2026 (JSON; registry, services, recent semesters, decisions). The 2026 registry is the base; the 2024 series fills the periods 2026 does not have, joined by the CNS code.
- **Build** ([scripts/build_cartorios.py](https://github.com/CaiqueDourado/brazilian-notary-registry-offices/blob/main/scripts/build_cartorios.py), DuckDB): dates and periods parsed, broken encoding fixed, 1,445,124 duplicated revenue rows removed, overlapping periods dropped, personal data masked, sample drawn by state. Checks run in CI.

## Privacy

No person fields (name and CPF of the person in charge and of the substitutes were never exported). E-mails on personal providers, and institutional mailboxes that are a person's name, are masked as `***@domain`. Decision texts are kept only when they are standard texts (the same text in 25+ offices, up to 600 characters); long *pareceres* name people and are left out. CPF numbers are masked. Only a sample is published.

## Limits

- A sample: use `stats.json` for national totals.
- Revenue is what the offices reported, nominal R$, not audited; `pendente` periods have no value yet.
- Only offices in the Jul/2026 registry are included.
- Up to 2020-S1 most values come from the Dec/2024 collection, after that from Jul/2026.

## Need the full data or a crawler like this?

This is a sample, on purpose. The same crawler collects all 16,266 offices with the revenue series and the decision history, and can refresh them on a schedule. For the complete data, an update, or a crawler and data pipeline for another public source, contact the author on [LinkedIn](https://www.linkedin.com/in/caiquedourado/) or [GitHub](https://github.com/CaiqueDourado).

## License and links

Data: CC BY 4.0, source CNJ Justiça Aberta. Code: MIT. Code, data dictionary and notebook: [github.com/CaiqueDourado/brazilian-notary-registry-offices](https://github.com/CaiqueDourado/brazilian-notary-registry-offices). Related: [municipios-e-estados-do-brasil](https://www.kaggle.com/datasets/caiquedourado/municipios-e-estados-do-brasil).
