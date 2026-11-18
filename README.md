# litreview-agent

A local-first assistant for academic literature discovery and AI-assisted relevance screening.

**Status:** early development. See `HELP.md` for the staged development guide.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
cp -n .env.example .env            # Only if .env does not exist; then add your API keys
pytest -q

# Database workflow (Stage 3)

litagent project create <project_name> --topic "<research_topic>"  # Create a project
# Example: litagent project create hitl --topic "human-in-the-loop machine learning"

litagent project list              # List existing projects

litagent search "<query>" --project <project_name> --limit 10  # Search OpenAlex and save papers to the project
# Example: litagent search "Active Learning" --project hitl --limit 10

litagent screen --project <project_name>  # Screen pending papers using the project's topic
# Example: litagent screen --project hitl

litagent screen --project <project_name> --retry-failed  # Retry failed screenings
litagent screen --project <project_name> --topic "Active Learning"  # Screen using a different topic

litagent status --project <project_name>  # View project status without running searches
# Example: litagent status --project hitl

# Import JSON files from the original v4 notebook
litagent import-json data/v4/papers_dataset.json --project hitl-v4 --evaluated data/v4/evaluated_dataset.json --legacy-topic "Human in the loop"
litagent status --project hitl-v4

# JSON workflow (Stage 2 — still supported, without --project)

litagent search "human-in-the-loop machine learning" --limit 50 --out data/papers_dataset.json
litagent screen data/papers_dataset.json --out data/evaluated_dataset.json

# Screen JSON produced by the Stage 1 notebook
litagent screen notebooks/papers_dataset.json

# Notes:
# --limit limits each search, not the total papers stored in a project.
# ok means successfully screened, not necessarily relevant.
# Screening results are saved incrementally; unfinished work can be continued.
# Ctrl+C marks project searches as interrupted; repeat the search to try again.
# Legacy screenings are preserved separately and may be re-screened.
# Search failures (OpenAlex/Crossref) appear in `litagent status` as failed search runs.
# `litagent failures` and `litagent screen --retry-failed` only concern LLM screening failures, not search failures.
# A failed run is kept as execution history (e.g. Crossref run 17 was an intentional Stage 4 timeout test).
# TODO Stage 5: 
- Fix `legacy_import.py` to preserve `skipped_no_abstract` as `skipped` / `uncertain`, instead of incorrectly marking it as `failed`.
- Add a regression test for imported screening statuses.
- Keep legacy screenings separate using `criteria_hash="legacy"`.
- Verify that `litagent status` reports screenings for the current criteria only, as planned in Stage 5.
- Ensure imported historical results remain available after re-screening.

```

## Web interface (Stage 7 — Streamlit)

Install the web dependencies from the project root:

```bash
pip install -e ".[web,dev]"
```

Start the application:

```bash
python -m streamlit run app/streamlit_app.py --server.address localhost
```

Open http://localhost:8501 in your browser. Keep the terminal open while using the app; press `Ctrl+C` to stop it.

## Stage 7 — Manual verification notes (2026-11-17)

**Scope:** Functional validation of the Streamlit interface using project `ui_test`. These are observations from a small test, not a scientific evaluation of screening accuracy.

### Confirmed results

- The Streamlit interface started successfully; project creation, search, screening, review, BibTeX export, and Zotero import were exercised.
- The Streamlit dashboard and `litagent status --project ui_test` agree: **21 papers**, **5 without abstracts**, **10 screened** with the current criteria (**9 `ok`, 1 `skipped`**), and **5 human-reviewed** (**3 `include`, 2 `exclude`**). Eleven papers remained unscreened.
- Search history includes two initial searches (10 new records from OpenAlex and 10 from Crossref) and two repeated searches (0 new from OpenAlex, 1 new from Crossref). Duplicate records were recognised. The manual test used a limit of **10 per source**, rather than the **20** specified in the reference verification procedure.
- The screening comparison reported `compared: 3`, `agreement: 1.0`, `include_recall: 1.0`, and `includes_wrongly_excluded: 0`. Only three reviewed records had a comparable model decision; the other two human reviews were not included in the agreement calculation (e.g. an unscreened or missing-abstract record). These figures are not a scientific accuracy estimate.
- BibTeX export with the filter **"Included by a human reviewer"** yielded **3 entries** because only three of the five human-reviewed papers had an `include` decision. All three imported successfully into Zotero; their DOI links were manually opened and led to the expected documents.
- The **Log** tab displays search and screening start/completion events. Criteria-update events should be checked in the full history if not visible in the latest rows.

### Observed limitations and follow-up items

1. **Export audit events:** No BibTeX/export event appeared in the displayed Log. Export works, but the action does not appear to be logged in the inspected history. Consider adding an `export_completed` event with format, filter and number of records if export traceability is needed. This is **not** a requirement of the Stage 7 verification procedure.
2. **Generic BibTeX entry type:** Exported references use `@misc`, which Zotero imports as **Document**. This is valid BibTeX, but loses useful publication-type distinctions such as journal article (`@article`) and doctoral thesis (`@phdthesis`). Only choose a more specific type when supported by source metadata; do not infer it from the title.
3. **Missing metadata — paper #129:** The doctoral thesis *Protein-ligand binding affinity prediction using combined molecular dynamics simulations and deep learning algorithms* was stored with an unknown year, so the BibTeX and Zotero records have no date. The source page states **"Soutenance le 11/12/2023"**, indicating a 2023 defence date; this was not captured in the database. Missing fields are preferable to fabricated values. A later metadata-enrichment step could record the defence year with provenance.
4. **Metadata consistency — paper #119:** The point-cloud paper was exported with year **2021**; a 2022 journal issue/publication date has also been noted. Distinguish online-first from issue publication dates before changing the stored year. The author names were inspected in Zotero and **no confirmed author error** was found; an earlier potential name discrepancy is **unverified**, not an established defect.
5. **Source coverage / missing abstracts:** Five of the 21 records lack abstracts in SQLite, even though an abstract for at least one paper (#123) was located manually on the publisher's website. Such records are marked `skipped`/`uncertain` during automated screening, not sent to the LLM, and can be reviewed manually. This is a source-metadata coverage limitation, not evidence of a model error.
6. **Incomplete Stage 7 manual protocol:** The reference verification procedure asked for **limit 20** per discovery source and a deliberate change to at least one actual model suggestion. The recorded trial used limit 10; any intentional override of an LLM-generated `include`/`exclude` decision should be documented separately if performed. Manual resolution of a `skipped`/`uncertain` paper is not a direct disagreement with an LLM prediction.
7. **README maintenance:** Parts of the older quick-start examples and the Stage 5 TODO remain historical and may not match the current Stage 7 CLI. They should be reviewed separately rather than copied as current usage instructions.

**Conclusion:** The tested Stage 7 workflow is operational and the CLI/UI counters agree. The BibTeX entries imported successfully, and no invented fields were demonstrated in the inspected sample; missing and generic metadata remain follow-up items. Preserve these observations while proceeding to Stage 8.

## Stage 8 - 
### TODO importante
- No output aparece a tua API key do OpenAlex dentro do URL, em texto legível (É o XXX):
```bash
litagent fulltext --project ui_test
INFO HTTP Request: GET https://api.openalex.org/works/doi:10.1093/bib/bbab474?select=id%2Copen_access%2Cbest_oa_location&api_key=XXXXXX "HTTP/1.1 200 OK"
INFO HTTP Request: GET https://arxiv.org/pdf/2107.04340 "HTTP/1.1 200 OK"
[1/3] parsed
INFO HTTP Request: GET https://api.openalex.org/works/doi:10.1021/acs.jcim.7b00650?select=id%2Copen_access%2Cbest_oa_location&api_key=XXXXX "HTTP/1.1 200 OK"
INFO HTTP Request: GET https://api.unpaywall.org/v2/10.1021/acs.jcim.7b00650?email=petro.anonimo123%40gmail.com "HTTP/1.1 200 OK"
[2/3] download_failed
INFO HTTP Request: GET https://api.openalex.org/works/doi:10.70675/afb433b4z5353z43edzae3fzb8133e571989?select=id%2Copen_access%2Cbest_oa_location&api_key=XXXXX "HTTP/1.1 200 OK"
INFO HTTP Request: GET https://api.unpaywall.org/v2/10.70675/afb433b4z5353z43edzae3fzb8133e571989?email=petro.anonimo123%40gmail.com "HTTP/1.1 200 OK"
[3/3] download_failed
Summary: {'parsed': 1, 'download_failed': 2}
```
## testes
- #121 — K DEEP: registo Zenodo removido; acesso ao PDF pela ACS sujeito a pagamento ou autenticação institucional.
- #122 — Bioinformatics: PDF acessível manualmente, mas download automático bloqueado com HTTP 403.
- #125 — CSBJ: URL antigo desatualizado; encontraste uma alternativa funcional para descarregar o PDF.
- #127, #128 e #129: URLs completos identificados, ainda por verificar manualmente.

Truncamento do terminal: confirmado que [:60] cortava apenas a apresentação. Registada a tua alteração para [:200].
### TODOs futuros: 
- melhorar a descoberta de PDFs
- identificar ligações desatualizadas
- distinguir causas de falha
- ocultar a API key nos logs (acima).

## Important limitations

- Screening uses titles and abstracts only. It is a preliminary filter, not a full-text eligibility decision.
- Search results depend on the coverage of the sources used; they are never an exhaustive survey of the literature.
- When a hosted provider such as Groq is used, titles and abstracts are sent to that external service.
- We are using Groq's free plan limits so it isn´t recommended to do many requests or the status will be 'failed'. If that happens search on data folder file evaluated_dataset.json on the last screening_error you can find the time to reset the RPM limit.
- We using the model openai/gpt-oss-20b its have:

| Metric | Meaning | Rate Limit |
| --- | --- | --- |
| **RPM** | *Requests Per Minute*  | 30 |
| **RPD** | *Requests Per Day*  | 1.000 |
| **TPM** | *Tokens Per Minute*  | 8.000 |
| **TPD** | *Tokens Per Day* | 200.000 |
