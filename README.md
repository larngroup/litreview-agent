# litreview-agent

A local-first assistant for literature discovery, AI-assisted title/abstract screening, human review, and open-access PDF retrieval.

**Current baseline:** Stage 8, package version `0.8.0`, branch `stage8`. The CLI and Streamlit workflows are operational in the recorded development exercises. Structured evidence extraction and cross-paper synthesis belong to Stage 9; report generation belongs to Stage 10 and is not available in this baseline.

> **Development security warning:** HTTP logs and some error messages can expose API keys, contact emails, and signed download tokens. Credential protection is incomplete; two security regression cases remain expected failures until Stage 10. Do not share raw logs, commit `.env`, or treat this baseline as security-hardened.

## Documentation

Detailed experiments, implementation history, unresolved questions, and deferred improvements are kept outside this quick start:

| Document | Contents |
| --- | --- |
| [Stages 1-6](docs/validation/stages1-6.md) | Notebook-to-CLI development, SQLite, Crossref, screening criteria, human review, and Groq/Ollama integration; historical confirmations remain to review. |
| [Stage 7](docs/validation/stage7.md) | Streamlit and bibliographic-export validation, Zotero checks, metadata limitations, and pending confirmations. |
| [Stage 8](docs/validation/stage8.md) | PDF retrieval, `not_found` investigations, text-quality and fontTools checks, Streamlit validation, security follow-up, and the DEI environment. |

These are validation records, not claims of general screening accuracy or exhaustive literature coverage. Their confirmation registers remain open for later review.

## Installation and configuration

**Requirements:** Python **3.11 or newer** and an isolated virtual environment. Python **3.13.2** was used on the personal Windows PC and the DEI Linux machine. Ollama is needed only when selecting local LLM inference; Groq is the hosted alternative. Full-text retrieval itself does not require an LLM.

Run from the repository root. The examples below use Python 3.13 and do not replace a system Python installation.

### Windows / PowerShell

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[web,dev]"
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

### Linux / bash

```bash
python3.13 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[web,dev]"
[ -f .env ] || cp .env.example .env
chmod 600 .env
```

On Bengio, the personal interpreter is available as `~/.local/bin/python3.13`; use that path instead of `python3.13` when it is not on `PATH`. Keep installations project-local and do not modify shared Python or Ollama installations. The environment setup is recorded in the [Stage 8 validation](docs/validation/stage8.md#22-development-environment).

### Configure `.env`

Edit `.env` in your editor, using [.env.example](.env.example) as the template. Existing environment variables take precedence over `.env` values.

| Purpose | Settings |
| --- | --- |
| OpenAlex | Fill in `OPENALEX_API_KEY` locally. |
| Scholarly API contact | Set `CONTACT_EMAIL`; it is used for Crossref polite access and the Unpaywall fallback. |
| Local Ollama | Set `LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL=http://localhost:11434/v1`, and `OLLAMA_MODEL=llama3.1:8b`. Ollama must be running with the selected model installed. |
| Hosted Groq | Set `LLM_PROVIDER=groq`, fill in `GROQ_API_KEY`, and select `GROQ_MODEL` (the recorded default is `openai/gpt-oss-20b`). |
| Storage | Defaults: `LITAGENT_DATA_DIR=data` and SQLite at `data/literature.db`. `LITAGENT_DB_PATH` can override the database location. |

Timeout, retry, and structured-output settings are also available in the template. A Groq key is not required when using Ollama. Local Ollama inference does not make discovery/download requests offline: those still contact external services.

## Web interface

With the virtual environment active:

```bash
python -m streamlit run app/streamlit_app.py --server.address localhost
```

Open `http://localhost:8501` on the computer running Streamlit. Keep the process running while using the app; stop it with `Ctrl+C`.

Create or select a project, configure its criteria, then use **Search**, **Screening**, **Review**, **Export**, **Full text**, and **Log**. Model suggestions and human decisions are stored separately. Groq sends screening inputs to an external service; an Ollama endpoint on another machine is also treated as external.

## Basic CLI workflow

The following is an illustrative small trial, not the saved criteria of the historical `ui_test` project. Replace the topic and criteria with your review protocol.

```bash
litagent project create demo --topic "human-in-the-loop machine learning"
litagent project criteria demo --include "empirical study with an evaluation" --exclude "editorial, opinion piece or book review"
litagent search "human-in-the-loop machine learning" --project demo --source openalex --source crossref --limit 10
litagent screen --project demo --max 10
litagent papers --project demo
```

Review the records in Streamlit or use `litagent review --help` for the CLI syntax. The `--paper` argument requires a numeric ID from `litagent papers`; decisions and notes must reflect the review actually performed. Once human reviews exist:

```bash
litagent evaluate --project demo
litagent export --project demo --format bibtex --subset human_include --out data/included.bib
litagent status --project demo
```

`export` also supports `csv`, `json`, and `searches`. Bibliographic subsets are `human_include` (default), `model_include_unreviewed`, and `all`; search-history exports describe project search runs rather than a filtered bibliography.

**Interpretation:** `--limit` is per search source, not a project-size target. `--max` caps the records processed by screening, not the number of LLM requests. A record without an abstract is `skipped` / `uncertain` and is not sent to the model; `ok` means processing succeeded, not necessarily `include`. Evaluation compares human reviews only with eligible successful model screenings, so `compared` can be smaller than the number reviewed.

Changing criteria creates a new screening fingerprint while preserving history. To deliberately re-screen the same criteria, for example when comparing providers, use `--redo` with the appropriate `--provider` and `--model`; changing provider alone does not force re-screening.

For older JSON datasets, use `litagent import-json --help`. Direct `litagent screen FILE.json` and `screen --topic` examples from earlier stages are not the Stage 8 workflow. Historical behavior and import-format limitations remain documented in [Stages 1-6](docs/validation/stages1-6.md).

## Full-text retrieval

After selecting papers through human review:

```bash
litagent fulltext --project demo
litagent fulltext-status --project demo
```

The default subset is `human_include`. Choose a broader set explicitly with `--subset`:

| Value | Papers considered |
| --- | --- |
| `human_include` | Papers included by a human reviewer. |
| `include_any` | Human-included papers plus unreviewed papers suggested as `include` by the model. |
| `all` | All papers in the project, without changing their review decisions. |

The pipeline uses OpenAlex and, when configured, Unpaywall to locate reported OA copies, downloads available PDFs to `data/fulltext/` by default, and stores page text and asset metadata in SQLite. Successful parsed results are reused. `fulltext-status` displays stored outcomes; it does not perform retrieval.

`not_found` means that the current locator returned no source-reported OA location for the identifier, not that the paper does not exist or that institutional access is unavailable. `open_access` does not guarantee download success. `parsed` does not guarantee error-free text on every page. See [status semantics](docs/validation/stage8.md#32-location-lookup-and-status-semantics).

**Retry commands address different operations:**

```bash
litagent failures --project demo
litagent screen --project demo --retry-failed
litagent fulltext --project demo --retry-failed
```

The first two concern model screening, not failed searches or PDF downloads. Search failures remain in search history. Full-text retry may reuse the stored PDF URL and does not guarantee discovery of an alternative copy; the exact behavior and validation limits are recorded in [Stage 8](docs/validation/stage8.md#34-retry-behavior).

In Streamlit, the **Full text** subset selector controls retrieval only. Its results table and built-in CSV export include all stored full-text records for the project. This is separate from the filtered bibliographic exports in the **Export** tab.

## Tests and validation status

```bash
python -m pip check
python -m pytest -q
```

The recorded final Stage 8 Windows run was **107 passed, 2 xfailed in 9.97s**. The two expected failures concern credential exposure in raw HTTP response content and connection exception messages; they are unresolved security cases, not successful fixes. Installation and automated checks on Bengio were reported successful, without an exact test-count transcript. See the [test evidence](docs/validation/stage8.md#101-recorded-automated-test-outcomes).

The existing `ui_test` corpus contained 21 papers, with 4 parsed PDFs, 5 `not_found` records, and 12 failed downloads. These are results from a small recorded exercise, not expected results for every query or a fresh installation. The database and PDFs are not supplied by cloning the repository.

## Data, limitations, and next steps

Research data, PDFs, and `.env` belong outside Git. Keep backups separately; cloning the code does not transfer existing projects. Review logs and exports for sensitive information before sharing them.

Screening is a preliminary title/abstract filter, not scientific full-text eligibility assessment. Source coverage and metadata vary, missing abstracts are possible, and retrieval can fail on stale URLs or restricted endpoints. Extracted text can retain headers, footers, ligatures, and spacing artifacts. BibTeX currently uses generic `@misc` entries and does not fill missing bibliographic metadata. Detailed findings are in the validation documents above.

Next: **Stage 9** evidence extraction and quote verification, then **Stage 10** reporting and release work, including the deferred security fixes. Broader PDF-location fallback, improved diagnostics, manual PDF import, and text preprocessing remain proposed later improvements, not current features. Pending historical confirmations stay in the validation records; they are not silently marked complete.

## License metadata pending review

The repository [LICENSE](LICENSE) contains **Apache License 2.0**, while [pyproject.toml](pyproject.toml) currently declares **MIT**. This inconsistency must be resolved with the project maintainers; this documentation update does not choose or change the license. The installation also reported deprecated license-table syntax. Both the consistency review and packaging update are Stage 10 follow-up items.
