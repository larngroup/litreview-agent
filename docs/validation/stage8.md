# Stage 8 Validation - Open-Access Full Text and PDF Processing ->revire section 4->end

**Project:** `litreview-agent` (`literature-agent`, CLI: `litagent`)  
**Stage:** 8 of the reference implementation  
**Validation date:** 2026-11-25  
**Development branch:** `stage8`  
**Recorded implementation/validation commit:** `1f30c18` (`Complete Stage 8 full-text retrieval and validation`)  
**Status:** Functional Stage 8 baseline validated on the Windows test corpus; Linux development environment prepared and automated checks reported successful. Known limitations and security work remain explicitly recorded below.

> **Purpose and evidence standard.** This document preserves the implementation, test conditions, observed outcomes, manual investigations, and decisions made during Stage 8. It is a development-validation record, **not** a measurement of scientific screening accuracy, a systematic assessment of open-access coverage, or a claim that all PDFs can be retrieved. A manual observation is labelled as such; hypotheses about publisher restrictions or document relationships are not treated as verified API diagnoses. Do not commit API credentials, institutional session material, signed download URLs, or the local research database.

## 1. Scope and acceptance boundary

Stage 8 adds a local-first path from an existing project paper to an available legal open-access full text:

1. Select project papers for retrieval.
2. Look for open-access locations through OpenAlex, with Unpaywall as a fallback when configured.
3. Download a reported PDF URL without bypassing access controls.
4. Check the download size and PDF file signature, then store the PDF locally with its computed SHA-256 digest and byte size.
5. Extract and store text **per PDF page** in SQLite for later evidence attribution.
6. Record access, download, and parsing outcomes, including failures.
7. Expose the workflow through the CLI and Streamlit.
8. Preserve existing project, screening, review, and bibliographic records.

**Current implementation boundary:** Stage 8 retrieves PDF locations reported by OpenAlex/Unpaywall and extracts existing PDF text. It does NOT perform OCR (recognising text in scanned page images), automatically log into institutional accounts, or parse publisher webpages to discover download links.

**Manual browser checks:** For paper #123, the researcher signed in manually through University of Coimbra using their own institutional access. This was an availability check in the browser, not an automated feature or an attempt to circumvent an access restriction. No access-control circumvention was implemented or performed as part of this validation; it is not a planned feature.

**Possible later improvements, not implemented here:** OCR evaluation if needed, manual import of PDFs obtained by the researcher, and fallback across additional eligible open-access locations. These are proposals, not completed functionality or a commitment to implement every option.

**Separate stages and decisions:** Extraction of structured scientific evidence and cross-paper synthesis belong to Stage 9; report generation belongs to Stage 10. Downloading and parsing a PDF do not establish scientific eligibility for the review. Human inclusion/exclusion decisions remain separate.

Larger retrieval and preprocessing changes are deferred until after the Stage 10 reference baseline unless a blocking defect requires intervention. The small fixes and validation changes already made are recorded in Section 3.5.

## 2. Test environment and baseline

### 2.1 Existing project and persisted data

The existing SQLite project `ui_test` was used instead of creating an artificial empty database. Before and after the Stage 8 database migration, the recorded project contained:

| Existing project property | Recorded value |
| --- | ---: |
| Distinct project papers | 21 |
| Papers without abstracts | 5 |
| Screened for the current criteria | 10 |
| Papers with current-criteria screening status `ok` | 9 |
| Papers with current-criteria screening status `skipped` | 1 |
| Not screened for the current criteria | 11 |
| Human-reviewed papers | 5 |
| Human include decisions | 3 |
| Human exclude decisions | 2 |
| Not human-reviewed | 16 |

These are baseline **state-preservation** checks, not new Stage 8 screening results. The earlier Stage 7 review and bibliographic-export tests are documented separately.

The three human-included paper IDs in this dataset were **#119, #121, and #129**. The wider retrieval subsets contained seven papers (`include_any`) and all 21 (`all`).

### 2.2 Development environment

- **Personal PC:** Windows/PowerShell, project virtual environment, Python **3.13.2**.
- **DEI lab machine:** `Bengio`, Ubuntu **20.04.4 LTS**, architecture `x86_64`.
- **Personal Python on Bengio:** Python **3.13.2**, installed using `uv` in `/home/francisco/.local/share/uv/python/`; `~/.local/bin/python3.13` points to that interpreter.
- **Project environment on Bengio:** `~/projects/litreview-agent/.venv`, installed without `sudo` or system-wide package modifications.
- **Git on Bengio:** 2.25.1; the `stage8` branch was cloned over SSH. The recorded initial clone showed `1f30c18` and a clean working tree.
- **Ollama on the personal PC:** Installed locally with `llama3.1:8b`; successful local screening was demonstrated during the earlier Stage 6 work. The Ollama application version on that PC was not recorded here.
- **Ollama on Bengio:** 0.40.2, with `llama3.1:8b` already listed locally. The local `.env` was configured for the Ollama provider, and the operator reported the endpoint check successful. The existence of the model and endpoint does **not** by itself establish a new end-to-end LLM inference test on Bengio; Stage 8 retrieval is not dependent on LLM generation.

Files on Bengio are edited through VS Code; terminal-editor commands such as `nano` are not required for this workflow.

The project was installed on Bengio with:

```bash
python -m pip install -e ".[web,dev]"
```

The installation log confirmed an editable `literature-agent==0.8.0` installation and these relevant packages: `httpx 0.28.1`, `pypdf 6.21.4`, `openai 3.59.0`, `pydantic 2.14.4`, `python-dotenv 1.2.4`, `fonttools 4.69.1`, `streamlit 1.67.0`, and `pytest 9.2.0`. Installation and the subsequent environment checks were reported successful by the operator.

**Compatibility note:** The project was adjusted to target Python 3.11 or newer, consistent with the newly declared `fonttools>=4.69.1,<5` dependency. The Bengio environment uses Python 3.13.2 and does not change the machine's Python 3.8.10 installation.

## 3. Implementation inventory

| Area | Relevant path | Stage 8 responsibility |
| --- | --- | --- |
| Selection and execution | `src/literature_agent/pipeline.py` | Select papers, run locate/download/parse sequence, retain prior results, count statuses, log events |
| OA lookup | `src/literature_agent/fulltext/locate.py` | Interpret OpenAlex and Unpaywall OA metadata; return direct PDF and landing-page information when supplied |
| PDF download | `src/literature_agent/fulltext/download.py` | Stream PDF data, enforce byte limit and PDF signature, record digest and file size |
| Text extraction | `src/literature_agent/fulltext/pdf_text.py` | Extract one text string per page with `pypdf`; reject encrypted/unreadable or wholly non-text PDFs |
| Persistence | `src/literature_agent/fulltext/store.py` | Store full-text asset metadata and page-numbered text in SQLite |
| Database | `src/literature_agent/storage/database.py` | Keep project and paper records while adding full-text storage |
| CLI | `src/literature_agent/cli.py` | `fulltext` and `fulltext-status` commands |
| Web UI | `app/streamlit_app.py` | `Full text` tab: subset, retry, retrieval, results table |
| HTTP helper | `src/literature_agent/discovery/http.py` | Shared API timeouts/retries, and partial sensitive-parameter filtering |
| Full-text test support | `tests/test_fulltext.py`, `tests/pdf_helpers.py` | Full-text automated test cases and PDF fixture helpers; the helper module is not a separate set of tests |
| Security regression tests | `tests/test_http_security.py` | Check selected application error paths with mock requests; two known exposure cases remain marked expected failures |
| Project configuration | `pyproject.toml`, `.env.example` | Runtime dependencies, optional web/dev dependencies, OpenAlex/Unpaywall and LLM settings |

### 3.1 Paper subsets

`run_fulltext` supports three subsets:

| CLI value | Meaning | Number in `ui_test` |
| --- | --- | ---: |
| `human_include` | Papers with a final human `include` decision | 3 |
| `include_any` | Human-included papers plus unreviewed papers suggested as `include` by the model | 7 |
| `all` | Every paper in the project | 21 |

The default is `human_include`. Screening and human review are not overwritten by retrieval. A paper that has already been successfully parsed is returned as `parsed` from its cached state, including with `--retry-failed`; counting `parsed` does not necessarily mean another network download happened.

### 3.2 Location lookup and status semantics

The locator prefers a direct PDF URL from OpenAlex's `best_oa_location`. If that is unavailable, it may consult Unpaywall when both a DOI and `CONTACT_EMAIL` exist. OpenAlex is also usable with an OpenAlex identifier when no DOI is present. The current implementation does **not** exhaustively enumerate alternative open-access copies.

Relevant states:

| Layer | Examples | Interpretation |
| --- | --- | --- |
| Access | `open_access` | An OA location was returned by the configured source(s), not proof that the PDF can be downloaded |
| Access | `not_found` | The current locator returned no source-reported OA location (direct PDF URL or landing page) for the queried DOI/OpenAlex ID |
| Access | `no_identifier` | Neither DOI nor OpenAlex ID was available for lookup |
| Access | `lookup_failed` | The remote lookup failed; not evidence of a nonexistent paper |
| Download | `downloaded`, `failed`, `pending`, `not_applicable` | Download outcome or whether download applies |
| Parse | `parsed`, `failed`, `pending`, `not_applicable` | Text extraction outcome or whether extraction applies |

The pipeline also exposes processing summaries such as `download_failed` and `parse_failed`. These are workflow results and should not be confused with individual SQLite column values.

**What `not_found` means in this implementation:** the paper already exists in the project. During the full-text lookup, `locate_open_access()` returned `None` for its DOI or OpenAlex ID. `process_fulltext()` consequently stored `access_status="not_found"`, `download_status="not_applicable"`, and `parse_status="not_applicable"`. No publisher PDF download was attempted for that result. This is an outcome of the current metadata lookup, not a conclusion about every possible way to obtain the document.

The locator checks the preferred OA metadata exposed by OpenAlex and, when a DOI and contact email are configured and the fallback is needed, Unpaywall. It does not search every repository, inspect all publisher pages, or use the researcher's authenticated browser session. Missing metadata, an unrecognised identifier, an unreported OA copy, or querying a related record instead of the article can therefore lead to `not_found`. A lookup HTTP 404 is treated as no result from that source; other handled lookup failures, such as exhausted network retries, use `lookup_failed` instead.

**A missing direct PDF URL is a different case:** if an OA landing page is returned, the asset is recorded as `open_access`. Without a direct `pdf_url`, the current pipeline then returns `download_failed` with a "No direct PDF link" message. Likewise, a reported PDF URL that returns HTTP 403 is a download failure, not `not_found`. The word "usable" is avoided in the `not_found` definition because a returned OA location has not yet been proven downloadable.

The three manual investigations illustrate the distinction:

- **#120:** a PDF opened in the researcher's browser, although the locator had found no OA location. Anonymous OA access was not confirmed; the `not_found` result does not establish that Cloudflare blocked an automated download.
- **#123:** the researcher obtained the PDF after manually authenticating through UC. This does not contradict `not_found`: the agent searches reported OA locations and does not check the user's institutional subscription or browser session.
- **#134:** an associated research article was accessible, but the stored identifier points to a peer-review decision record. Finding the main article does not establish that the same document was available for the exact identifier queried.

Read `not_found` as **"No OA location found by the configured lookup for this identifier"**, not **"Paper does not exist"**, **"Full text is unavailable everywhere"**, or **"The user has no institutional access"**. It does not change the paper's screening or human-review decision.

### 3.3 Download checks, SHA-256 recording, and local persistence

The downloader:

- follows HTTP redirects using its configured `httpx` client;
- streams to a temporary `.part` file;
- limits a file to **50 MiB** by default;
- checks for the `%PDF-` signature rather than accepting an HTML login page as a PDF;
- computes SHA-256 and records byte size;
- cleans up incomplete temporary files after errors.

Successful local PDFs are saved under `data/fulltext/<paper_id>.pdf`. Asset fields include source (`locator`), `pdf_url`, `landing_url`, licence, OA version, access/download/parse states, path, digest, size, page count, and error text. `fulltext_pages` stores each page with a **1-based** `page_number` and extracted text. Replacing the pages for an asset is transactional.

**Where the PDF digest and size are recorded (implemented behavior):**

1. `fulltext/download.py::download_pdf()` initializes `hashlib.sha256()`, increments `size` and calls `digest.update(chunk)` while writing each downloaded chunk, and returns `DownloadedFile(destination, digest.hexdigest(), size)`.
2. `pipeline.py::process_fulltext()` passes `downloaded.sha256` and `downloaded.size_bytes` to `store.save_asset()` after a successful download.
3. `fulltext/store.py` persists these values as `fulltext_assets.sha256` and `fulltext_assets.size_bytes`.

This happens automatically during a successful download; it was not a separate manual step. **No independent comparison of the stored PDF digests/sizes against the four local PDF files was recorded in this validation.** The code does not compare against an authoritative publisher checksum or recheck the digest before returning an already cached `parsed` result. Computing a digest records the bytes received; it does not establish document identity, publication version, licensing, or full PDF structural correctness. The `%PDF-` check is a file-signature check, not a complete PDF validator.

The SHA-256 printed by the later `compare_fonts.py` experiment instead hashes the **extracted UTF-8 text**, not the PDF binary. These are two different uses of SHA-256 and should not be conflated. The experiment hashes the in-memory UTF-8 string; Windows text-file newline translation can make that digest differ from a hash of the saved `.txt` bytes even when the represented text is unchanged.

**Storage scope:** The current store maintains one asset per `paper_id`, rather than one per project or publication version. `project_assets()` selects those assets through project membership. A shared paper can therefore expose the same stored full-text asset in multiple projects; multiple full-text versions are not tracked by this design.

The extractor collapses whitespace already present in the `pypdf` output with `" ".join(text.split())`. It does not reconstruct word boundaries, so internal splits such as `th at` can remain. It does not remove headers, footers, page numbers, or figure captions, and it does not perform OCR.

### 3.4 Retry behavior

- Without retry, already parsed papers are reused and failed records can retain their prior status.
- With `--retry-failed` / the Streamlit retry checkbox, `not_found` can trigger a fresh lookup, failed downloads may be tried again, and failed parsing can be retried for a previously downloaded PDF.
- The current code also retries an `access_status="lookup_failed"` lookup on a normal retrieval call, even without `--retry-failed`; the flag is not the sole trigger for every retry path.
- A failed download may be retried using the **same previously saved URL**, rather than requesting fresh OA locations. This is a known limitation, particularly for stale links.
- A missing direct PDF URL remains a download failure with an informative landing-page message; the user can investigate manually.

### 3.5 Small changes made during validation

1. **CLI diagnostics:** The displayed error/PDF-URL excerpt in `fulltext-status` was enlarged from `[:60]` to `[:200]` characters. This affects terminal presentation, not SQLite data or downloads.
2. **Font handling:** `fonttools>=4.69.1,<5` was included as a runtime dependency after testing optional `pypdf` font parsing behavior. See Section 7.
3. **HTTP parameter filtering:** The Unpaywall `email` parameter was added to the set excluded from the safe parameter representation used in some `SourceError` messages. It complements filtering of `api_key` and `mailto`; it is **not** comprehensive credential redaction. See Section 8.
4. **Regression tests:** `tests/test_http_security.py` was added. Two known leak paths are represented by strict expected failures (`xfail`) instead of being silently treated as fixed.

No downloader redesign, manual PDF importer, automatic institutional login, or destructive data cleanup was introduced during Stage 8 validation.

## 4. Database migration and data safety

The Stage 8 schema migration was run against the existing 21-paper `ui_test` dataset. The recorded verification found that the 21 papers and previous screening/human review data were preserved. The new full-text tables were populated without replacing the original research records. The evidence is a comparison of aggregate `status` counts and the inspected records, not an exhaustive row-by-row audit of all historical searches, screenings and reviews.

The local database and PDF files are **not** part of the source-controlled dataset. The recorded check:

```bash
git ls-files data
```

returned only:

```text
data/.gitkeep
```

`git ls-files .env` returned no tracked `.env`. The environment file is created locally from `.env.example` and is not tracked in the inspected checkout. These checks do not establish that no secret exists elsewhere in the repository or its history; no repository-wide secret audit was recorded. Reproducing the corpus-level counts requires a local database with the same 21 paper records and prior review decisions. A fresh clone does **not** automatically contain this corpus or its four downloaded PDFs.

## 5. Full-text retrieval results on `ui_test`

### 5.1 Corpus-wide outcome

The CLI and Streamlit were compared against the saved project records. An exported Full text CSV was also inspected independently: **21 rows, 21 distinct paper IDs, and 11 exported columns**.

| Outcome | Count | Paper IDs |
| --- | ---: | --- |
| `parsed` | **4** | 119, 126, 130, 131 |
| `not_found` | **5** | 120, 123, 134, 135, 136 |
| `download_failed` | **12** | 121, 122, 124, 125, 127, 128, 129, 132, 133, 137, 138, 139 |
| **Total** | **21** | All project papers |

Within the 12 download failures:

- **5** had an OA landing page but **no direct PDF URL**: #121, #127, #128, #129, #137.
- **7** returned **HTTP 403** at the reported PDF URL: #122, #124, #125, #132, #133, #138, #139.

An HTTP 403 alone does not distinguish paywall enforcement, human-verification controls, expired or invalid links, or other authorization policies. No universal diagnosis is claimed for those seven responses.

### 5.2 Parsed PDFs and stored page counts

| Paper | Pages in SQLite | Reported PDF location |
| --- | ---: | --- |
| #119 | 38 | `https://arxiv.org/pdf/2107.04340` |
| #126 | 10 | `https://public-pages-files-2025.frontiersin.org/journals/bioinformatics/articles/10.3389/fbinf.2025.1712577/pdf` |
| #130 | 30 | `https://www.biorxiv.org/content/biorxiv/early/2026/09/23/2026.09.17.752433.full.pdf` |
| #131 | 9 | `https://www.frontiersin.org/articles/10.3389/fmolb.2020.00093/pdf` |

The program reports successful storage and extraction of page text. This is **not** a guarantee that every character, equation, column, image, or scientific symbol in the original PDFs was reproduced accurately.

**Subset boundary for the next stage:** These four PDFs are counted across `all`, not across the human-included subset. Of the three human-included records (#119, #121, #129), only **#119** had a parsed PDF at this snapshot. The PDFs for #126, #130 and #131 do not become human-included merely because they were retrieved with `--subset all`. Human eligibility decisions remain separate; a default human-included Stage 9 run must not be described as having four full-text sources.

### 5.3 CLI commands used for validation

```bash
litagent fulltext --project ui_test
litagent fulltext --project ui_test --subset include_any
litagent fulltext --project ui_test --subset all
litagent fulltext-status --project ui_test
```

The CLI status command was used to inspect access, download, parse, licence, and diagnostic information. The main retrieval path stores its outcome in SQLite and logs project events. Commands may use cached records and should not be interpreted as forcing downloads on every execution.

## 6. Manual investigation of failures

These checks were performed through normal browser access. **Browser access is not equivalent to anonymous OA availability.** A browser session with institutional entitlements is outside the current automated OA-only retrieval workflow.

### 6.1 Three `not_found` cases

| ID | Identifier | Manual observation | Interpretation |
| --- | --- | --- | --- |
| **#120** | `10.1002/wcms.1429` | The Wiley article page and its `/doi/pdf/` URL were accessible in a browser after Cloudflare verification. | No OA location was returned to the agent. Browser access does not establish whether anonymous OA access would work. Cloudflare was observed in the browser, **not proven to be the reason for the lookup's `not_found` state**. |
| **#123** | `10.1016/j.sbi.2025.103193` | ScienceDirect initially offered organizational access or purchase. After University of Coimbra authentication and consent to share institutional attributes, a View PDF action became available. | Full text was available **through institutional entitlements**, not through the existing OA-only workflow. The final asset URL was signed and temporary; it should not be stored or shared as a stable PDF URL. |
| **#134** | `10.1039/d5dd00436e/v1/decision1` | The DOI led to an open-peer-review or editorial-decision context. The associated published research article is `10.1039/d5dd00436e`, and a related bioRxiv preprint is `10.64898/2025.12.17.694851`. The published article offered a PDF. | The stored record appears to be a **decision letter, not the research article**. This raises document-type and duplicate-version issues; it does not justify silently rewriting the stored DOI. |

The stored CSV titles for **#134, #135 and #136** explicitly begin `Decision letter for "Explainable Active Learning Framework for Ligand Binding Affinity Prediction"`. This directly supports treating them as decision-letter records rather than three research articles. Their exact round/version relationships are suggested by the DOI suffixes and the reviewed website, but the complete source relation metadata were not independently audited.

### 6.2 Additional failed-download observations

| ID(s) | Observation | Validation boundary |
| --- | --- | --- |
| **#121** | The recorded Zenodo landing record was observed to have been removed by its owner (dated 2019-12-06). A publisher copy was seen behind payment or institutional access. | Stale OA metadata can persist. This does not prove that no alternative lawful OA copy exists. |
| **#122** | The automated OUP `Bioinformatics` PDF request returned HTTP 403. A browser path after human verification allowed the PDF to be viewed. | No bypass of the human-verification mechanism was attempted or proposed. |
| **#125** | The stored CSBJ PDF URL was stale or redirected incorrectly. A different publisher URL worked manually in the browser. | The agent did not automatically rediscover and substitute that URL. |
| **#127, #128, #129, #137** | OA metadata provided landing URLs but no direct PDF link. | These cases were not all manually validated to completion. No assertion is made that they lack a PDF. |
| **#138, #139** | Both records were saved with the same reported PDF URL, apparently associated with a later version. | The precise preprint-version relationship and actual downloaded content require additional verification. |

**Handling of signed URLs:** The user's institutional ScienceDirect URL and the publisher CDN links contained expiring signatures/tokens. Their query strings are deliberately omitted from this record. They are unsuitable as permanent bibliographic metadata.

## 7. PDF extraction quality and `fontTools` experiment

### 7.1 Manual comparison of PDF page 2

Page 2 of **three original PDFs** was compared manually against text extracted and stored in SQLite:

| Paper | Result of the inspected page |
| --- | --- |
| **#119** | Text appeared consistent; minor spacing discrepancies were noticed. Some differences could have been introduced by copying original PDF text into a diff tool. |
| **#126** | Scientific text was present, along with figure captions, page numbers, headers, and footers, consistent with whole-page text selection. |
| **#131** | Scientific text was present, but spacing issues, running page elements, and typographic ligatures such as `fi` represented by the Unicode ligature `U+FB01` were observed. |

**Conclusion limited to the inspected pages:** No significant scientific-text omission was identified in those three manual page comparisons. The full PDFs were not manually proofread page by page, and figures, equations, and reading order in complex layouts have not been comprehensively benchmarked.

Figure captions should not be removed blindly: they may carry evidence relevant to the thesis. Headers, footers, and page labels may be candidates for future preprocessing, but the source extraction should remain available for traceability.

### 7.2 Controlled comparison with and without `fontTools`

A local Windows test used the **same four downloaded PDFs** and the same `extract_pages()` function with `fontTools` present and absent. The experiment archive (`litagent-fonttools-test.zip`), supplied during validation rather than assumed to be in the Git repository, contains two sets of page-text outputs and warning logs. Their bytes were checked again while preparing this document.

| Paper | Pages | Text bytes in archived `.txt` | Byte-identical with/without `fontTools`? |
| --- | ---: | ---: | --- |
| #119 | 38 | 52,530 | Yes |
| #126 | 10 | 42,704 | Yes |
| #130 | 30 | 85,126 | Yes |
| #131 | 9 | 44,584 | Yes |

- `warnings.log` **without** `fontTools`: **43 warning lines**, related to optional CFF Type1 font encoding support.
- `warnings.log` **with** `fontTools`: **0 warning lines**.
- The archived extracted `.txt` files for all four PDFs were **byte-for-byte identical** across the two environments.
- No Unicode replacement characters (`U+FFFD`) were found in the archived text; **#131 still contained 136 typographic ligature characters** across the full extracted text.
- The initial controlled experiment used `fontTools` **4.69.0**. That release was subsequently identified as yanked; the pip warning stated `Incomplete provenance: use 4.69.1, same code`. The project dependency was set to **`fonttools>=4.69.1,<5`**, and a follow-up test with 4.69.1 on #131 again showed **no warnings**, nine pages, and the same inspected excerpt.

**Reproducibility boundary:** The archive contains the comparison script, extracted text and warning logs, but not the original PDFs, the SQLite database, or saved console output recording the Windows `pypdf` version. The script prints version metadata, but that output is not included in the ZIP. The Bengio package versions in Section 2 are not evidence of the earlier Windows experiment's versions. The archived text equality covers the 4.69.0 comparison; the 4.69.1 follow-up establishes the reported warning/page/excerpt behavior for #131, not a new byte comparison of all four full texts.

**Interpretation:** The dependency removes the observed optional font-parsing warnings in this test but **does not prove better extracted text** for these PDFs or fix the recorded ligatures. It remains useful for PDF font-decoding support. Do not describe the disappearance of warnings as proof that scientific text is complete.

### 7.3 Relevance to Stage 9

The inspected reference Stage 9 implementation checks a quotation by normalizing whitespace and case and then searching for it as a substring of the supplied page text. It does not normalize Unicode ligatures. Ligatures such as `U+FB01` and inconsistent internal spacing can therefore make a visually correct quotation fail this match. A later normalization strategy should be tested on real cases, preferably applied to the comparison representation **without modifying or discarding the original extracted text**. A failed quote match must remain distinguishable from a false or unsupported scientific claim. Conversely, a matching quotation establishes textual presence, not that the model's paraphrase or scientific interpretation is correct.

## 8. Security findings and regression coverage

### 8.1 Confirmed exposure paths

During Stage 8, HTTP INFO logs were observed displaying request URLs with the OpenAlex `api_key` and Unpaywall `email` query parameters. Depending on the failure path, raw HTTP response bodies or transport exception strings may also contain user-supplied secrets. Download errors and logged URLs can similarly contain sensitive signed query strings.

**Critical distinction:** Adding `email` to the safe parameter filter reduces exposure in **one formatted error path**, but it does **not** sanitize httpx/httpcore request logs, arbitrary response content, exception messages, existing SQLite diagnostics, or all download errors. It is not a complete security remediation.

Changes recorded during validation:

- `src/literature_agent/discovery/http.py`: exclude the `email` parameter from the `safe_params` representation, alongside `api_key` and `mailto`; the actual request parameters are left unchanged.
- `tests/test_http_security.py`: use `httpx.MockTransport` to check that the constructed request still carries the required parameters and that selected error/application-log paths do not expose them. No real API, credential or network call is used. Checks of `caplog` are restricted to the application logger, not the third-party `httpx`/`httpcore` request logs.
- Local targeted test result: **6 passed, 2 xfailed**. The expected failures are the **HTTP 400 response-body** case and the **`ConnectError` exception-message** case in `tests/test_http_security.py`. These cases execute and fail the credential-exposure assertion as expected; they are not skipped tests or completed fixes. They remain marked `xfail(strict=True)` until Stage 10 redaction work resolves the underlying issues.

The operator chose to retain detailed HTTP diagnostics temporarily for development and defer comprehensive logging redaction until Stage 10. This was an **explicitly accepted temporary risk**, not a finding that credentials are now fully protected.

### 8.2 Outstanding security actions

- [ ] Rotate any OpenAlex API key that was previously exposed in terminal output or shared logs; completion was **not confirmed** in this validation record.
- [ ] Restore safe log levels for `httpx`/`httpcore` or implement robust credential-aware redaction without hiding useful operational diagnostics.
- [ ] Redact/sanitize sensitive query parameters and signed URLs in all error and persistence paths, including exceptions and response snippets.
- [ ] Resolve both expected-failure security tests and remove `xfail` markers only after the fixes pass.
- [ ] Review any historical log and SQLite records before exporting or sharing them.

Do not commit `.env`, access tokens, full signed PDF links, or raw diagnostic logs containing identifiers/secrets. Consent-based institutional authentication is not a Stage 8 automation goal.

## 9. Streamlit Full text validation

The `Full text` tab was tested against the same `ui_test` data. It provides subset selection, a retry checkbox, a `Retrieve full texts` button, a progress indicator, and a table displaying stored asset results.

### 9.1 Subset execution results

The following results were reported directly from Streamlit:

| Selection | Progress completed | Final summary |
| --- | --- | --- |
| Included by a human (`human_include`) | 3/3 | `{'parsed': 1, 'download_failed': 2}` |
| Included by a human or suggested by the model (`include_any`) | 7/7 | `{'parsed': 1, 'download_failed': 6}` |
| All papers (`all`) | 21/21 | `{'parsed': 4, 'not_found': 5, 'download_failed': 12}` |
| `human_include` **with retry enabled** | 3/3 | `{'parsed': 1, 'download_failed': 2}` |

The progress label describes the **most recently processed paper**. For example, `21/21: download_failed` is not a summary saying all 21 downloads failed; the `Finished` dictionary gives the aggregate counts.

The retry test completed without changing the two failures in the selected subset. In this dataset, **#119 was already `parsed`, while #121 and #129 had no direct `pdf_url`**. The code reused #119 and returned `download_failed` for the other two before calling `download_pdf()`; their stored `open_access` status also did not trigger a fresh lookup. This validates the checkbox/button execution and handling of these existing records, **not** a new HTTP retry, recovery after a network failure, a refreshed OA lookup, or parsing-failure recovery.

### 9.2 Table and built-in CSV export

Two CSV exports were performed: one while `human_include` was selected and one while `all` was selected. Both contained the **same 21 project asset records, 11 columns, and ordering**. Their content was compared directly and matched.

This is **intended by the current code path**:

- The subset selector filters the papers **to process** when the retrieval button is pressed.
- The results table uses `project_assets(conn, project_id)` and displays **all full-text asset records already stored for the selected project**.
- The table's built-in Streamlit CSV export exports that displayed table; it is not the separate bibliography export feature from Stage 7.

Therefore, changing the retrieval subset does **not** change the table/export contents. A future UI refinement could rename the selector to `Papers to retrieve` and introduce an independent table filter. This is a usability improvement, not an observed data-loss or export bug.

## 10. Test evidence and reproducibility

### 10.1 Recorded automated test outcomes

| Check | Recorded result | Caveat |
| --- | --- | --- |
| Initial Stage 8 automated suite on Windows | **106 passing tests** | This was before the later CLI/security/dependency follow-up changes. |
| Targeted HTTP/security regression tests | **6 passed, 2 xfailed** | The two expected failures remain known unresolved credential-exposure paths. |
| Final full-suite rerun on Windows | **107 passed, 2 xfailed in 9.97s** | `pytest -q` output supplied by the operator after reviewing this document; the two expected failures remain deferred to Stage 10. |
| Installation on Bengio | Succeeded | Editable `literature-agent 0.8.0`; dependency log inspected. |
| `pip check` / `pytest -q` on Bengio | Operator reported success | The exact final summary/count and test duration were not copied into this record. Do **not** invent a precise passing-test total. |

The final Windows rerun is now directly supported by the terminal output supplied by the operator:

```text
pytest -q
107 passed, 2 xfailed in 9.97s
```

This is a confirmed result, not an estimated total: 109 test cases were reported, with 107 passing and two known security cases failing as expected. The earlier 106-passing result is retained only as the historical initial Stage 8 run; three security cases were subsequently added, of which one passes and two remain expected failures. This Windows output does not establish the numerical result on Bengio, where successful checks were reported without an exact summary.

The reference guide's previously quoted `110 passed` was not used as an acceptance target: the number of collected tests depends on the project's actual test files and parametrization. The presence of `tests/pdf_helpers.py` alone does not add test cases; no extra tests were added merely to reach that number.

### 10.2 Diagnostic and verification commands

From an activated project environment:

```bash
python --version
python -m pip check
python -m pytest -q
litagent project list
litagent status --project ui_test
litagent fulltext-status --project ui_test
```

The last two commands require the original local `ui_test` database. They cannot be expected to return the 21-paper counts on a clean clone. These are diagnostic/verification commands, not a strict read-only procedure: tests can create caches and temporary fixtures, and database opening can initialize or migrate a schema. Use the intended environment and database.

For a repeat of the **existing-data** Streamlit check:

```bash
python -m streamlit run app/streamlit_app.py --server.address localhost
```

Then select `ui_test`, open `Full text`, inspect the table, and choose a subset before running retrieval. Avoid `all` with retry when a small controlled test is sufficient; it can issue repeated network requests against failing publisher endpoints.

### 10.3 Development and repository safety

The GitHub branch `stage8` was cloned on Bengio via SSH into `~/projects/litreview-agent`. The SSH authentication succeeded. The personal Python was installed with `uv`; the virtual environment is project-local; the system's Python 3.8.10 and shared Ollama installation were left untouched. The `.env` was created locally with restricted file permissions and remains outside Git.

A subsequent follow-up commit documenting the Bengio validation was reported by the operator, but its hash was not supplied in the conversation; this document deliberately does not fabricate it. The recorded reference hash for the initial Stage 8 validation commit is `1f30c18`.

## 11. Limitations, decisions, and pending work

### 11.1 Confirmed limitations of the Stage 8 baseline

1. **OA metadata coverage:** `not_found` records the absence of a source-reported OA location returned by the current locator, not a universal lack of full text. OA copies may be missed; institutional subscription access is outside this lookup and is not evaluated.
2. **Single preferred PDF location:** The pipeline does not automatically cycle through all plausible OA URLs after an unsuccessful preferred download.
3. **Stale links and retries:** Failed downloads may keep retrying the same URL instead of refreshing lookup metadata.
4. **Publisher restrictions:** HTTP 403 responses are not sufficiently classified to explain their cause, and human-verification requirements are not bypassed.
5. **Document types and versions:** Review decisions, errata, preprints, and the main article may be represented as distinct records if upstream discovery metadata are not handled adequately.
6. **Text extraction quality:** `parsed` means that extraction completed and at least one page yielded a nonempty normalized string; it is not a scientific-usability check. Spacing, reading order, mathematical expressions, tables, figure labels, ligatures, or individual pages may still be inaccurate.
7. **Security:** Sensitive HTTP data can remain visible in logs and some errors; the two xfailed tests explicitly preserve awareness of this risk.
8. **UI ambiguity:** The retrieval subset filters processing, not the saved-results table or its export.
9. **Evidence limits:** Four parsed PDFs in a small, preselected project are not a representative estimate of literature-wide PDF retrieval performance.

### 11.2 Required follow-up for Stage 10 security/release readiness

- [ ] Comprehensive redaction or safe logging for API credentials, contact emails, signed URLs, response snippets, and transport exceptions.
- [ ] Fix and enable the two currently xfailed security assertions.
- [ ] Audit stored diagnostics for secrets and rotate any exposed credentials as appropriate.
- [ ] Update the deprecated `pyproject.toml` licence syntax from `license = { text = "MIT" }` to a current SPDX-compatible declaration after checking the repository's actual license file. Setuptools emitted a build warning with a stated future deadline of **2027-02-18**.
- [ ] Record the Stage 10 release-test summary for each validated environment, including any remaining expected failures. The Stage 8 Windows rerun is already recorded in Section 10.1.

### 11.3 Optional improvements **after** the Stage 10 reference baseline

- Structured diagnostic reasons for `no_direct_pdf`, `no_oa_location`, `http_forbidden`, `http_not_found`, `resource_gone`, `authentication_required`, `payment_required`, `rate_limited`, `server_error`, `not_a_pdf`, `file_too_large`, `timeout`, and `connection_error`. Avoid assuming a paywall or anti-bot cause from status 403 alone.
- Candidate fallback across legitimate OpenAlex/Unpaywall OA locations, with URL deduplication and bounded retries/backoff where appropriate.
- Safer refresh behavior for failed or outdated PDF URLs.
- Manual import of legally obtained PDFs, with provenance, version checks, hashing, and licensing/access conditions; **not** automatic institutional sign-in.
- Publication-type filtering and linkages between research articles, preprints, corrections, and peer-review decision records.
- Text quality diagnostics, header/footer detection, controlled Unicode/ligature normalization for quote matching, and separate OCR evaluation if needed. Preserve the stored page text and original PDFs.
- Regression fixtures for error categories and PDF quality; measure coverage on the **same** corpus before and after changes.
- Independent filtering of the Streamlit Full text results table and clearer subset labelling.
- Bibliographic metadata quality and export-event audit improvements identified in Stage 7.

**Prioritization decision:** Do not expand Stage 8 into a general-purpose PDF acquisition system before completing Stages 9 and 10. The reference Stage 9 can prefer stored full-text pages and fall back to abstracts; any abstract-only evidence must be labelled appropriately and must not be misrepresented as a full-text assessment. Preserve the relationship between quoted evidence and its actual source.

## 12. Closure assessment

**Completed and observed:**

- The Stage 8 migration preserved the original 21-paper test project and prior screening/review state.
- The workflow located, downloaded, and parsed **four** open-access PDFs, preserving page counts and text in SQLite.
- The remaining records were retained with non-destructive, inspectable statuses: **five `not_found`** and **twelve `download_failed`**.
- Manual page-2 comparisons of three PDFs did not show significant scientific-text loss in those limited samples.
- The controlled `fontTools` test removed **43 optional font warnings** without altering the archived extracted text of the four PDFs.
- Three `not_found` records and selected download failures were investigated, clarifying the difference between OA discovery, browser access, and institutional entitlement.
- The Streamlit Full text tab, its three subsets, retry path, saved-results table, and built-in CSV export behaved consistently with the CLI and the implementation.
- The final Windows automated suite reported **107 passed, 2 xfailed in 9.97s**. The expected failures are the two security cases deferred to Stage 10, not unexpected failures of the retrieval workflow.
- The `stage8` branch was committed and cloned to an isolated Python 3.13.2 environment on the DEI lab machine; installation and local checks were reported successful.

**Remaining limitations or checks not demonstrated in this Stage 8 record:** exhaustive full-text retrieval, all-pages PDF fidelity, an independent stored-checksum audit, complete credential redaction, scientific validity of later LLM evidence, successful HTTP download recovery in the selected UI retry test, or a new Ollama inference run on Bengio. Earlier local Ollama screening on the personal PC was demonstrated during Stage 6; that is separate evidence, not a missing Stage 8 requirement. These limits are not grounds to claim the observed functional baseline failed.

**Decision:** Close the Stage 8 functional baseline and proceed to **Stage 9 (evidence extraction and quote verification)**, retaining the security obligations for Stage 10 and optional retrieval/extraction improvements for a later, separately tested phase.

---

### Record maintenance

When updating this file, distinguish (a) source code behavior, (b) automated results with logs, (c) manual browser observations, and (d) proposed improvements. Add commit hashes, exact test counts, timestamps, and additional verification only when supported by a recorded run. Do not paste raw `.env` contents, API request URLs with secrets, expiring signed PDF links, or private institutional authentication information.
