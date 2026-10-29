# Changelog

## 1.0.0 — 2026-10-29

- Sample of 1,009 of the 16,266 offices in the CNJ registry (Jul/2026), stratified by state (at least 5 per state).
- Services (2,311 rows), acts and revenue per period 2005–2026 (38,272 rows; Jul/2026 collection, completed by the Dec/2024 series), Corregedoria decisions (4,402 rows).
- `serventias.jsonl` with everything nested; `stats.json` with the aggregates of all 16,266 offices.
- Privacy: no person fields; personal e-mails and mailboxes with a person's name masked; CPF masked; decision texts only when standard (25+ offices, up to 600 characters).
- Build: 1,445,124 duplicated revenue rows removed (the Dec/2024 crawl holds some offices under several ids); 2024 periods that overlap 2026 dropped.
