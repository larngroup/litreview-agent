# Stages 1-6 - Initial Development and Validation (TO REVIEW)

**Project:** `litreview-agent` (package: `literature-agent`; CLI: `litagent`)  
**Repository:** `larngroup/litreview-agent`  
**Scope:** Development before the Streamlit interface: notebook, Python package, SQLite, multi-source discovery, criteria-based screening, and LLM providers.  
**Branches inspected:** `stage1`, `stage2`, `stage3`, `stage4`, `stage5`, `stage6`. The `main` branch was not used.  
**Historical development window:** The inspected implementation/follow-up commits span 2026-11-04 to 2026-11-17. Commit timestamps are not necessarily the dates of every manual test.  
**Repository audit/document reconstruction:** 2026-11-26.  
**Status:** Implementation history reconstructed from pinned repository sources and the available development conversation. Functional exercises are recorded below; missing historical artifacts and scientific-validation requirements remain explicitly unconfirmed.

> **Purpose.** Preserve the work completed before Stage 7 without relying on conversational memory. This is one consolidated historical document, not six new installation guides. It distinguishes the implemented capability, project-specific fixes, observed results, and remaining questions for each stage. See [stage7.md](stage7.md) and [stage8.md](stage8.md) for later validation.
>
> **Evidence standard.** A commit message is a record of what the author reported; a source file establishes what that snapshot implements; a supplied terminal output establishes the result of that particular run. These are not interchangeable. No historical test suite, live search, model request, or private SQLite database was rerun during this documentation audit. The complete original implementation manuals and every earlier project conversation were not independently reopened; quoted reference requirements are identified as such. References R1-R6 and C1-C4 are defined in Section 12.

## 1. Scope, terminology, and stage boundaries

The development sequence was:

```text
Stage 1: stabilised OpenAlex/Groq notebook and JSON records
    -> Stage 2: reusable Python package, CLI and pytest suite
    -> Stage 3: SQLite projects, provenance and append-only decision history
    -> Stage 4: shared scholarly HTTP client and Crossref integration
    -> Stage 5: explicit criteria, three-way screening and human evaluation
    -> Stage 6: shared OpenAI-compatible provider with Groq/Ollama presets
    -> Stage 7: Streamlit and bibliographic exports (separate document)
```

This is the functional progression, not a claim that each current branch tip is the direct Git parent of the next branch tip.

**Within Stages 1-6:** bibliographic discovery, normalisation, title/abstract screening, storage, human decisions, basic agreement metrics, error handling and provider integration.

**Not implemented by these stages:** the Streamlit interface, the Stage 7 bibliographic export workflow, the Stage 8 open-access PDF pipeline, full-text evidence extraction, cross-paper synthesis, or final report generation. The notebook filename containing `synthesizer` does not establish that a synthesis pipeline was implemented in Stage 1.

Important distinctions throughout the record:

- A successful request or `ok` screening does not mean that a paper is relevant.
- A retrieved record is not necessarily a primary research study or a distinct publication version.
- Missing abstracts are a metadata limitation; they are not a negative scientific relevance decision.
- A model suggestion is separate from a human decision.
- A local package/notebook can still send text to a hosted provider such as Groq.
- The IDs and run numbers below belong to the developer's historical SQLite database; a fresh installation will not reproduce those IDs automatically.

## 2. Repository provenance and attribution

### 2.1 Branch snapshots inspected

| Branch | Audited tip | Commit timestamp (UTC) | Role of that tip |
| --- | --- | --- | --- |
| `stage1` | [`8a487ed`](https://github.com/larngroup/litreview-agent/commit/8a487ed904ee8bc217570680efb0f9fcf70e5a53) | 2026-11-05 12:44:42 | Minor notebook/install-cell and ignore-rule follow-up after stabilisation. |
| `stage2` | [`d1a2143`](https://github.com/larngroup/litreview-agent/commit/d1a2143ca344f99ff524cf08f7e42f588a4c52f4) | 2026-11-04 21:03:38 | README limitations update after package/CLI extraction. |
| `stage3` | [`3957efc`](https://github.com/larngroup/litreview-agent/commit/3957efc6ead67c9e2de52da33737ae308d41c38e) | 2026-11-05 17:59:45 | Closing documentation commit summarising storage and interruption work. |
| `stage4` | [`0a40e00`](https://github.com/larngroup/litreview-agent/commit/0a40e00a98b4d3cdfd69241ae02d88ade32ad700) | 2026-11-11 20:56:13 | Crossref relevance correction and reusable diagnostics, after initial integration and pacing/log changes. |
| `stage5` | [`a088750`](https://github.com/larngroup/litreview-agent/commit/a08875021ddc5ede02f053402ec83d3685104469) | 2026-11-12 10:28:23 | Detailed paper listing, corresponding CLI assertions, and documentation; also comments out HTTP logger restrictions. |
| `stage6` | [`5087281`](https://github.com/larngroup/litreview-agent/commit/50872810b78b3d821792b67e81a5607fe6ea54f6) | 2026-11-17 02:06:01 | Adds the provider regression-test file; provider implementation was already in the preceding Stage 6 snapshot. |

These pinned SHAs, rather than future branch contents, define this audit. No release tags for Stages 1-6 were independently verified here.

### 2.2 Implementation commits versus closing messages

A closing commit can describe an entire stage while changing only a small part of it. The relevant milestones are:

| Stage | Implementation/follow-up sequence | Attribution note |
| --- | --- | --- |
| 1 | `3b90e66` -> `8a487ed` | `3b90e66` records notebook stabilisation and environment support; the later diff comments out the install cell and ignores the future database path. |
| 2 | `1e889d0` -> `34ff548` -> `d1a2143` | Package/CLI extraction is in `1e889d0`; subsequent commits clean/update the README. |
| 3 | `df6eb60` -> `2c5b136` -> `b5f6486` -> `3957efc` | Initial storage, a regression reproducer, the interruption fix, and closing documentation. The closing message explicitly says its own change was the README. |
| 4 | `ecfdacf` -> `529edb2` -> `0a40e00` | Initial multi-source integration; pacing/logging follow-up; relevance correction and diagnostics. |
| 5 | `5d1fb66` -> `aab3631` -> `9ca9046` -> `a088750` | Criteria workflow; a comment-only follow-up; legacy-status fix; listing/tests/documentation follow-up. Despite its message `initial commit`, the audited `aab3631` diff changes only a logging comment. |
| 6 | `0942ae8` -> `5087281` | Initial provider implementation, followed by `tests/test_providers.py`. The final message summarises the whole stage, but its diff only adds that test file. |

The Stage 1 tip includes a follow-up dated after the Stage 2 tip. Also, the first Stage 3 commit has `34ff548`, not the later Stage 2 README tip `d1a2143`, as its parent. Do not infer a perfectly linear chain of current branch tips from the stage numbers.

**Evidence:** R1-R6; selected commit diffs and parent metadata inspected through the GitHub connector.

## 3. Stage 1 - Stabilise the notebook

### 3.1 Objective and implemented baseline

The stabilised notebook is `groq_openai_papers_finder_synthesizer_v5.ipynb`, located at the Stage 1 repository root. Its heading identifies it as the Stage 1 stabilised finder/screener.

The implementation consolidates the older retrieval alternatives (`featcher_v1`, `fetch_papers`, `fetch_papers2`) into `fetch_openalex(query, limit)`, with:

- OpenAlex retrieval through `pyalex`, cursor pagination, an explicit requested limit, and a project safety cap of 10,000 records.
- Per-run duplicate checking, retrieval counters, missing-abstract counts, query and timestamps.
- `reconstruct_abstract()` handling absent/malformed inverted indexes and invalid positions without inserting placeholder prose.
- DOI normalisation and a consistent record shape: source/source ID, DOI, title, year, authors, keywords, abstract, abstract availability, query, retrieval timestamp and schema version.
- JSON persistence for retrieved records, the search run and evaluated records.

The code prevents exceeding the requested limit. It cannot guarantee that the source contains enough unique records to fill every request; "exact limit" in the original description should not be read as an unconditional guarantee of that many usable results.

Screening uses Groq through `langchain_openai.ChatOpenAI` and an OpenAI-compatible endpoint. The notebook supplies the user's chosen topic, title, abstract and keywords, requests JSON-object output and validates a strict Boolean `is_relevant` plus a reason with Pydantic.

Missing abstracts are returned as `screening_status="skipped_no_abstract"` without a model call. Other outcomes are `ok` or `failed`; records carry the model, prompt version, timestamp, raw response and error fields as applicable. The recorded configuration names `openai/gpt-oss-20b`, temperature `0.0` and prompt `relevance-v1`; this is historical configuration, not a current provider/model recommendation.

### 3.2 Project-specific environment and robustness work

The stabilisation commit explicitly records support for both Colab and local VS Code/Jupyter use:

- Detect Colab and use its Secrets interface there; accept the legacy secret names `OpenAlex` and `GROQ` as aliases in that path.
- Prefer configured environment variables when resolving Colab secrets.
- Outside Colab, load `.env` with `python-dotenv` and read the canonical environment names.
- Keep contact email optional; report only whether credentials are configured, not their values.
- Configure request retries and avoid hard-coded personal credentials.
- Include offline self-tests for abstract reconstruction, DOI/record conversion and response parsing/validation.

The later `8a487ed` diff comments out the notebook package-install cell and adds `data/literature.db` to the ignore rules. Do not describe that snapshot as automatically installing its notebook dependencies.

### 3.3 Validation recorded and its limits

The `3b90e66` commit message reports manual review of **10 relevant and 10 non-relevant records**, with **20/20 matching classifications**, including closer examination of two initially ambiguous papers and discussion with ChatGPT.

This is a **commit-reported small manual check**, not a newly verified result in this audit. The record identities, saved predictions, exact review protocol and independent annotations were not supplied with this reconstruction. ChatGPT assistance is not an independent human gold standard, and no evidence establishes a blinded/random sample or generalisable 100% accuracy.

The inspected notebook contains offline self-test code; its cleared cell outputs do not provide a retained execution transcript for those tests.

> **TO CONFIRM - Q1:** Are the 20 reviewed records and their original predictions/decisions still available? Record the topic, selection method and whether decisions were made before viewing the model suggestions. Keep the claim attributed to the commit until that evidence is supplied.

**Evidence:** R1. This section does not claim to have rerun the notebook or reconstructed the pre-Stage 1 v4 implementation.

## 4. Stage 2 - Extract a package and JSON-based CLI

### 4.1 Objective and principal changes

Stage 2 moves reusable logic into `src/literature_agent/`, with `pyproject.toml`, `.env.example`, an editable-install workflow, the `litagent` entry point and a pytest suite.

The implementation commit identifies these components:

| Component | Responsibility introduced or extracted |
| --- | --- |
| `models.py` | Validated `Paper` data model and normalisation helpers. |
| `config.py` | Environment/`.env` settings. |
| `discovery/openalex.py` | Abstract reconstruction, work conversion and OpenAlex search extracted from the notebook. |
| `screening/` | JSON response parsing and topic-based relevance screening. |
| `providers/groq.py` | OpenAI client configured for Groq, replacing LangChain in the package workflow. |
| `cli.py` | `search` and JSON-file `screen` commands, progress, summaries and useful configuration errors. |
| `tests/` | Automated regression/unit tests around the extracted package. |
| `notebooks/` | Retained notebook workflow rather than the production package depending on LangChain. |

The inspected Stage 2 CLI still uses `configure_pyalex()`/`search_openalex()`. The move to direct shared HTTP for production OpenAlex retrieval belongs to Stage 4, not Stage 2.

Historical Stage 2 commands were:

```bash
litagent search "human-in-the-loop machine learning" --limit 50 --out data/papers_dataset.json
litagent screen data/papers_dataset.json --out data/evaluated_dataset.json
```

The CLI accepts `--topic` for JSON screening; otherwise it requires one unambiguous stored query. It writes search output and a companion run log, then writes evaluated JSON after the screening list returns. This is not yet the incremental SQLite screening persistence introduced in Stage 3.

### 4.2 Follow-up changes and recorded checks

The package-extraction commit and its README diff report:

- **50 notebook records and 50 CLI records, with identical source-ID lists** in the comparison performed.
- Compatibility of Stage 1 JSON with Stage 2 screening.
- A missing `GROQ_API_KEY` producing a clear CLI error rather than an uncontrolled traceback.
- Clarification that `ok` means successful screening, including a successful negative relevance decision.
- Generated notebook JSON and local secrets excluded from Git.

The pinned Stage 2 CLI confirms the missing-key handling and topic-selection paths. The exact 50-record datasets were not retrieved here; the 50/50 comparison remains a recorded historical result, not a fresh API equivalence experiment.

The later README commits clean the initial instructions and add Groq free-plan/model-limit notes. Those figures are historical documentation, not verified present-day quotas. No current API quota is required to interpret this validation record.

> **TO CONFIRM - Q2:** Retain the query and source-ID comparison output/datasets for the reported 50/50 check if available. A passing comparison for that query is not a guarantee of identical results across different dates, queries or API responses.

### 4.3 Boundary with subsequent stages

Stage 2 provides JSON interchange and preliminary screening, not project-level SQLite persistence or the later review/evaluation CLI. Search-to-JSON remains available later, but direct JSON-file screening is removed in Stage 5 in favour of import into a project. Old Stage 2 commands must therefore remain labelled historical.

**Evidence:** R2 and the pinned Stage 2 `cli.py`.

## 5. Stage 3 - SQLite, provenance and resumable screening

### 5.1 Objective and storage model

Stage 3 introduces schema version 1, project workflows and the separation of merged bibliographic metadata, source observations, model screening and human review.

| Table | Role |
| --- | --- |
| `schema_info` | Application database schema version. |
| `projects` | Named review projects, topic, question and criteria fields. |
| `search_runs` | Query/source, status, counts, timestamps and errors for a search execution. |
| `papers` | Merged bibliographic record with a global local ID. |
| `paper_sources` | Source/run provenance and a serialized per-source `Paper` record. |
| `project_papers` | Membership of a paper in a project and first associated search run. |
| `screenings` | Appended model results with status, decision, criteria/topic hash, provider/model, raw response and settings. |
| `reviews` | Appended human decisions and notes, separate from model suggestions. |
| `events` | Execution events and diagnostic details. |

**Provenance qualification:** `add_paper()` serializes `paper.model_dump(mode="json")` into `record_json`. This preserves the application's per-source record before merging; it is not necessarily a verbatim archive of the complete original API JSON, XML or HTTP response. Some source-file comments describe provenance more broadly than this implementation supports.

Deduplication tries DOI, source/source ID, then normalised title with compatible year. Title matching avoids ambiguous candidates and does not merge records carrying different non-null DOIs merely because their titles match. This is conservative record matching, not a complete publication-version reconciliation system.

Existing merged fields are not replaced by newer non-empty values; missing fields can be filled. `find_conflicts()` reports differences in DOI, title and year. It does not establish universal consistency across every metadata field.

A paper may already exist globally but be new to a particular project. Consequently, `new_in_project`, `new_paper` and `matched_by` describe different things. Repeated retrievals can add provenance rows without adding a second project-paper membership.

### 5.2 Pipeline, history and import

New CLI/database workflows include project creation/listing, project searches/screens, status and legacy JSON import. The database already contains human-review support, but the later convenient `review`, `papers`, `failures` and `evaluate` CLI workflow belongs to Stage 5.

Screening resumability initially uses a fingerprint of the topic and prompt version. Results are inserted into `screenings` one paper at a time; selecting the latest result does not delete earlier rows. Human decisions are stored independently and supply `final_decision`, rather than silently adopting the model output.

Legacy import converts old records and supports matching them to project papers. It does not modify the input JSON file. Where retrieval dates are absent, the importer records its use of file-modification time rather than treating that time as a verified original API retrieval date. The later skipped-status correction is documented in Section 7.3.

### 5.3 Extra correction: Ctrl+C left searches marked `running`

The historical defect was a search interrupted by Ctrl+C remaining `running`, with no completed timestamp. An `except Exception` block alone did not catch `KeyboardInterrupt`.

The Git history separates reproduction and repair:

- `2c5b136`: regression reproducer using an isolated SQLite database and fake search interruption; the message also records a real Ctrl+C reproduction.
- `b5f6486`: recognise `interrupted`, finish/log the run, re-raise the interruption and handle it cleanly in the CLI.
- `3957efc`: closing documentation of the stage and the interruption fix.

The final Stage 3 pipeline explicitly catches `KeyboardInterrupt`; the schema accepts `interrupted`; the CLI follow-up avoids an uncontrolled traceback. The regression file is `tests/test_search_interrupt.py`.

**Limits of this correction:**

- It concerns normal Ctrl+C handling, not forced process termination, power failure or operating-system shutdown.
- Search retrieval returns a list before the pipeline persists it. A correct interrupted status does not imply that partially fetched in-memory results were saved.
- A changed `CREATE TABLE IF NOT EXISTS` definition is not itself proof of migration of every pre-existing SQLite constraint. The later diagnostic script checks whether the database actually accepts `interrupted`.

### 5.4 Validation status

The commits record regression reproduction/fix and pytest verification. Exact final Stage 3 passing-test totals and a complete archived real-search interruption transcript are not available in this record. The later Stage 4 diagnostic and preserved Stage 6 pipeline confirm that interruption handling remained an explicit integration concern.

**Evidence:** R3; pinned `pipeline.py` and `storage/database.py`; C1 for later confirmation of the inherited behaviour.

## 6. Stage 4 - Crossref and a shared scholarly HTTP client

### 6.1 Baseline integration

Stage 4 adds a registry for `openalex`/`crossref`, a common `SearchSource` interface, per-source failure handling in multi-source searches and additional diagnostics.

`PoliteClient` centralises timeouts, request spacing and bounded retries. The inspected retry set is **429, 500, 502, 503 and 504**, not every possible HTTP 5xx status. Numeric `Retry-After` values are honoured with a cap; otherwise exponential delays are used. Transport/timeouts are handled, and exhausted attempts raise `SourceError`.

Production OpenAlex retrieval switches from `pyalex` to this HTTP path, including the API key parameter. The notebook retains its separate `pyalex` workflow. Crossref adds cursor pagination, source-record conversion, JATS abstract cleaning and optional `mailto` identification.

An ordinary error in one source is recorded without necessarily stopping another source. Ctrl+C is deliberately different: it interrupts the workflow instead of being swallowed as an ordinary per-source failure.

### 6.2 Investigation: missing abstracts were partly a ranking problem

The query used for the recorded investigation was:

```text
human-in-the-loop machine learning
```

Initially, a 10-record Crossref search reported **10 without abstracts**. Direct inspection found abstracts for two relevant DOI records, prompting a comparison of the actual result sets rather than an assumption that JATS cleaning or relevance screening had discarded the text.

| Crossref request variant | Observed result for the investigation query |
| --- | --- |
| No cursor | Topic-related results, including two records with abstracts. |
| `cursor="*"` without explicit relevance sort | An unrelated-looking set, including older clinical papers, all ten without abstracts. |
| Cursor plus `sort="score"`, `order="desc"` | The relevant first-page set was restored in this comparison. |

The correction explicitly passes relevance sorting on every page. `tests/test_crossref_relevance_sort.py` uses a fake two-page HTTP client to assert both cursor advancement and the `sort`/`order` parameters. The developer supplied a failing assertion before the fix and **1 passed in 0.11s** afterwards.

A subsequent real Crossref run (**run 22**, project `stage4-validation`) reported:

```json
{
  "retrieved": 10,
  "new": 9,
  "duplicates": 1,
  "matched_by": {"doi": 5},
  "without_abstract": 8
}
```

Stored per-source inspection showed ten records and the two expected cleaned abstracts:

| DOI | Raw abstract characters reported | Cleaned/stored abstract characters reported |
| --- | ---: | ---: |
| `10.52783/pmj.v35.i1s.2295` | 933 | 916 |
| `10.54941/ahfe1007707` | 733 | 716 |

This demonstrated correction of the observed retrieval/ranking problem and preservation of these available abstracts. It did not make the other eight records acquire abstracts, prove universal Crossref ranking behaviour, or change the scientific screening criteria.

The `matched_by` count is not required to equal `duplicates`: a globally known DOI can still be new to the selected project. The output above must not be interpreted as five duplicate project additions.

### 6.3 Request spacing and rate-limit observations

The developer checked actual response headers, rather than assuming that a generic documentation table described every pool/endpoint.

| Historical request context | Headers reported in the conversation |
| --- | --- |
| Anonymous Crossref request | `x-rate-limit-limit: 1`, interval `1s`. |
| Identified Crossref query request | HTTP 200; limit `3`, interval `1s`; concurrency `3`; pool `polite-array`. |

The committed registry uses:

| Source/configuration | Minimum interval between request starts |
| --- | ---: |
| OpenAlex | 0.1 seconds |
| Crossref with contact email | 0.5 seconds |
| Crossref without contact email | 1.1 seconds |

The additional change in `529edb2` was **1.0 to 1.1 seconds for the anonymous Crossref path**. The discussion considered other values, but the audited final registry retains 0.5 seconds for the identified path.

These are historical configuration choices, not current service guarantees. In particular, **1.1 seconds per request is not 1.1 requests per second**. The sources need not be artificially slowed to identical runtimes, and this scholarly-source pacing does not regulate Groq model requests or token quotas.

### 6.4 Timeout, overlap and conflict checks

A real timeout exercise set `HTTP_TIMEOUT_SECONDS` to `0.001` and requested one Crossref record. The output showed four retries with **1, 2, 4 and 8 second** delays, then a clear `ConnectTimeout`-based `SourceError` after **five attempts**. The intentionally failed run later appeared as **run 17** in `hitl` search history.

That historical `search_runs` failure is distinct from LLM screening failures. It correctly remained in search history; `litagent failures` and `screen --retry-failed` do not repair or erase it.

The first database overlap check returned zero papers with multiple sources, and an early conflict check also returned zero. Those results alone did not prove a deduplication defect. A later posted query listed **five shared-source merged records**, IDs **6, 32, 64, 67 and 71**, each with both `crossref` and `openalex` provenance.

The original posted overlap query had no project filter. Treat this as a database-wide result from that snapshot, not a measured overlap total for every project or a provider-coverage estimate. Multiple retrievals can leave more than one provenance observation per source.

The final per-source incremental-coverage figures and post-correction conflict examples are not retained in the available conversation. Do not substitute `n_new` totals for the number of papers exclusively indexed by a provider.

### 6.5 Reusable diagnostics added to `debug/`

| Script | Purpose |
| --- | --- |
| `01_check_sqlite_schema.py` | Check that the stored `search_runs` table accepts `interrupted`. |
| `02_check_crossref_rate_limits.py` | Query and display rate/concurrency/pool headers with configured contact identification. |
| `03_compare_crossref_cursor_sort.py` | Compare the three search variants used to diagnose ranking. |
| `04_check_crossref_abstracts.py` | Inspect API abstract presence and JATS cleaning. |
| `05_inspect_stored_crossref_run.py` | Inspect serialized per-source records for a selected search run. |
| `06_check_cross_source_dedup.py` | List shared-source paper IDs, optionally restricted by project. |
| `07_check_metadata_conflicts.py` | Report differing stored source metadata. |
| `08_coverage_by_source.py` | Summarise chronological new-in-project contributions across completed runs. |

Each script has a module description; `debug/README.md` gives the order and commands. These scripts were placed outside `tests/`: several contact real APIs or inspect the working database and are not equivalent to isolated pytest fixtures.

### 6.6 Security change and later reversal

The final Stage 4 CLI sets `httpx` and `httpcore` loggers to `WARNING`, including when application verbosity is enabled. This addresses the observed request-URL disclosure at INFO/DEBUG level. The HTTP helper separately omits `api_key` and `mailto` from one error parameter representation.

That was **not comprehensive credential redaction**: raw response snippets and exception text could still contain sensitive information. The exact Stage 5 closing diff (`a088750`) subsequently comments out the two logger-level calls. The protection did not merely disappear mysteriously in Stage 8; the historical change is visible in Git. Later Stage 8 decisions about retaining debug output and the two security `xfail` cases belong to [stage8.md](stage8.md).

**Evidence:** R4 and C1. No new source queries were made during this retrospective audit.

## 7. Stage 5 - Explicit criteria, human review and evaluation

### 7.1 Principal changes

Stage 5 replaces the package's Boolean topic-only model output with **`include` / `exclude` / `uncertain`** and an explicit `Criteria` model containing topic, research question, inclusion criteria and exclusion criteria.

`Criteria.fingerprint()` hashes the criteria plus `PROMPT_VERSION` (`screening-v2` in the inspected snapshot). Criteria changes therefore select a new screening round while prior database rows remain available. This identifies inputs; it does not guarantee identical future model outputs.

The model response is schema-validated and contains a decision, reason, matched inclusion criteria and matched exclusion criteria. The implementation permits one response-format repair attempt by default, and records unrecognised criterion strings as diagnostic information.

New or expanded CLI operations are `project criteria`, `review`, `papers`, `failures`, `evaluate`, and screening options such as `--max` and `--redo`. The status view uses the current criteria fingerprint. Direct JSON-file screening is removed; historical JSON should be imported into a project first.

**Attempt-storage qualification:** successful screening stores the accepted raw response and an attempt count. In the inspected successful-repair path, the prior rejected raw reply is not copied into the successful result's details. Failure paths retain their attempt details. Therefore, the commit phrase "raw responses and attempts stored" should not be expanded into a claim that every intermediate reply is retained for every successful repair.

### 7.2 Status is separate from decision

| Situation | Screening status | Decision | Model request? |
| --- | --- | --- | --- |
| Valid include/exclude/uncertain JSON | `ok` | Returned label | Yes. |
| No abstract | `skipped` | Automatic `uncertain` | No. |
| Provider/authentication/parse failure | `failed` | No valid decision | May have been attempted. |
| Not processed for the current criteria | No current screening row | No suggestion | Not established by this state alone. |

`not screened` is a presentation state, not a fourth stored screening status in the schema. `ok/uncertain` from a model is different from `skipped/uncertain` assigned by the pipeline.

In the `hitl` exercise, `--max 20` processed **15 available candidate records**, resulting in **8 `ok` and 7 `skipped`**. A maximum is a cap, not a request to manufacture additional papers. Missing-abstract records still count among processed candidates even though they are not sent to the model.

### 7.3 Extra correction: skipped legacy records imported as failed

The Stage 3 import path originally treated a non-Boolean `is_relevant` as a failure. This incorrectly classified an explicitly skipped legacy record.

`9ca9046` implements and tests the following distinction:

| Input represented in the added fixture | Imported status | Imported decision |
| --- | --- | --- |
| `status="skipped_no_abstract"`, `is_relevant=None` | `skipped` | `uncertain` |
| `status="failed"`, `is_relevant=None` | `failed` | None |
| `is_relevant=True` | `ok` | `include` |

The new `tests/test_legacy_import_skipped.py` complements, rather than replaces, `tests/test_legacy_import.py`. Imported screenings continue to use `criteria_hash="legacy"`, separating them from current criteria-based results.

**Audit finding - legacy field alias remains to review:** the committed Stage 1 notebook writes `screening_status`, whereas this Stage 5 correction reads `record.get("status")`. The Stage 6 importer has the same blob SHA and logic. The added regression fixture covers `status`, not `screening_status`. A record with only `screening_status="skipped_no_abstract"` and a null relevance value is therefore not covered by the claimed compatibility and appears to follow the failure branch. This is a source-review finding, not a newly executed end-to-end regression in this audit. Check the actual archived JSON variants before describing all Stage 1/2 legacy statuses as fixed.

Also, imported evaluation rows do not receive a `raw_response` argument in the inspected importer. Preservation of old source files and history must not be confused with complete migration of every original evaluation field.

### 7.4 Extra improvement: detailed CLI paper listing

The listing was expanded to show paper ID, title, DOI, a DOI/source link where available, abstract availability, model suggestion and human decision. This made the missing-abstract and unscreened cases easier to interpret.

An existing CLI test still expected the old compact `model=include   human=exclude` line and failed after the intentional output change. A subsequent attempt left that old assertion in place after captured output had already been consumed. The final committed test checks the new fields instead.

**Audit qualification:** that same diff removes the previous explicit `status` output-content assertion. The test still executes `status`, but does not assert those former status counters at that point. Restoring that coverage is a separate improvement; do not claim the rewrite preserved every old assertion.

### 7.5 Criteria experiment and functional agreement report

The exercise first ran without explicit inclusion/exclusion criteria, producing several model `uncertain` outcomes and a warning. Criteria were then set and later refined to an empirical-study question.

The last explicitly posted configuration used:

**Research question:** How does human feedback during training affect the accuracy of machine-learning models?

**Inclusion criteria:**

1. `empirical study with an evaluation`
2. `humans provide feedback, labels or corrections during model training or operation`

**Exclusion criteria:**

1. `editorial, opinion piece or book review`
2. `fully automated method with no human involvement`

The model then produced three includes and five excludes among the eight screened records with abstracts; seven records remained `skipped/uncertain`. Five older, unrelated clinical records from the earlier Crossref ranking problem were still visible in the project. Fixing future retrieval did not automatically remove those existing records.

The initial evaluation reported `compared=0`. A review of paper #105 did not change this because that paper's screening status was `skipped`, and `agreement_report()` only compares rows with a human review and screening status `ok`. Reviewing paper #7, whose model screening was valid, produced `compared=1`.

The subsequent review exercise deliberately used test decisions, including disagreements for #8 and #10. It was requested to exercise the program, not to construct independent scientific labels. The first command for #1 was malformed, so only seven eligible reviews were initially compared. After correcting that command:

```json
{
  "compared": 8,
  "agreement": 0.75,
  "include_recall": 0.667,
  "includes_wrongly_excluded": 1,
  "matrix": {
    "human=include/model=include": 2,
    "human=include/model=exclude": 1,
    "human=exclude/model=include": 1,
    "human=exclude/model=exclude": 4
  }
}
```

The arithmetic is consistent: six of eight labels agree, and two of three human includes were also model includes. `includes_wrongly_excluded` counts human-include/model-exclude pairs specifically. Model `uncertain` on a human include can reduce include recall without incrementing that separate exclusion count.

The accompanying `status` output showed **15 project papers**, **7 without abstracts**, **8 `ok`**, **7 `skipped`**, and **9 human-reviewed records** (6 exclude, 3 include). Nine reviewed records and eight comparable records are compatible because comparison requires a valid model screening.

**Interpretation:** these numbers validate joins, counters, filtering and the confusion-matrix calculation. They are not an unbiased accuracy estimate. Do not reuse deliberately chosen testing labels as a gold standard without independent re-review.

### 7.6 Real failed-screening retry and history checks

A separate `stage5-retry-test` project exercised an actual Groq authentication failure and retry:

1. A request with invalid temporary credential configuration returned **HTTP 401**; paper **#116** became `failed` with a clear invalid-key error.
2. `litagent failures` reported **1 failed screening**.
3. After restoring the valid credential configuration, `screen --retry-failed` returned **HTTP 200**, `ok/include`.
4. `litagent failures` then reported **0 failed screenings**.

This is real failed-screening recovery evidence, unlike an invocation that only reports `nothing to screen`. No credentials are reproduced here.

A SQL grouping posted during validation showed **four criteria-hash groups: 15, 15, 15 and 10 rows**. This supports retention of different historical rounds in that database. It does not, by itself, prove that one of those groups was the separately labelled `legacy` import; the code and regression fixture supply the evidence for that path.

### 7.7 What the functional exercise did not establish

The reference verification text quoted in the conversation called for a randomly chosen human-reviewed sample of at least 50, review before seeing model suggestions, discussion with the supervisor, and a repeatability exercise. Completion of those activities is not confirmed here.

The program's warning below 30 comparable records and the manual's larger review target are different things. Passing the functional eight-record exercise satisfies neither an independent gold-standard evaluation nor a broad scientific validation of recall.

**Evidence:** R5, C2. The old Stage 5 TODO in later README versions is historical documentation; it must not override the actual fix/test evidence or hide the remaining field-alias issue.

## 8. Stage 6 - Provider abstraction, Groq and local Ollama

### 8.1 Objective and principal implementation

Stage 6 introduces a shared `OpenAICompatibleProvider`, `LLMResponse`/`LLMError`, provider presets/factory and `--provider`/`--model` options. The inspected implementation supports the named Groq and Ollama presets; the generic client's extensibility is not evidence that every compatible server was tested.

Structured output can fall back through:

```text
json_schema -> json_object -> none
```

This changes the requested response-format mode, not the model or hosting provider. Pydantic validation remains necessary after fallback. The implementation tries weaker modes on `BadRequestError`; other failures have clear authentication, not-found, timeout, connection or API-error messages.

Provider/model metadata is recorded by the screening workflow; successful results also store `output_mode`. A failed call need not have a single successful output mode to record. The provider response includes latency metadata, but no benchmark of end-to-end runtime was retained in the supplied validation outputs.

The Ollama preset:

- Uses its OpenAI-compatible `/v1` endpoint and checks installed model names through `/api/tags`.
- Supports the `:latest` alias handling shown in the source.
- Gives an actionable error when the requested model is absent.
- Classifies `localhost`, `127.0.0.1` and `::1` URLs as local; other configured hosts count as external.
- Uses the placeholder API-key string expected by the client integration, not a separately obtained hosted-service credential for the local Ollama setup.

The local/external classification is based on the configured hostname. It is not an independent network/privacy audit, and a remote Ollama instance must not be described as running on the user's own PC.

### 8.2 Real Groq and Ollama exercises

The personal Windows PC had `llama3.1:8b` installed; `ollama list` showed model ID **`46e0c10c039e`** and approximately **4.9 GB**. The reported real local request returned HTTP 200 and `ok/include` for the single-paper retry-test project.

A later `hitl` run with Groq, `--max 10 --redo`, produced **8 `ok`, 2 `skipped`**. The output showed HTTP 429 responses followed by automatic retries and successful responses; recorded waits included 3 seconds and a 7-second/3-second retry sequence. The stage did not add a new proactive Groq token-rate limiter.

This did not contradict the Stage 4 pacing fix: scholarly-source request spacing and hosted LLM quotas/retries concern separate clients and limits.

The corresponding local command used explicitly:

```bash
litagent screen --project hitl --provider ollama --model llama3.1:8b --max 10 --redo
```

Its summary was **8 `ok`, 2 `skipped`**, with all eight valid model decisions equal to `include`. The developer reported that local execution was slow; no timings or hardware-normalised comparison were retained.

The subsequent evaluation output was:

```json
{
  "compared": 8,
  "agreement": 0.375,
  "include_recall": 1.0,
  "includes_wrongly_excluded": 0,
  "matrix": {
    "human=include/model=include": 3,
    "human=exclude/model=include": 5
  }
}
```

An all-include result naturally catches all three human includes in this small set while disagreeing on five human excludes. A recall of 1.0 here is not evidence of a strong or selective screener.

**Comparison limits:** this was the existing small, partly artificial review exercise from Stage 5, not a new gold standard. The earlier Groq agreement report in Section 7.5 must not be silently labelled a newly captured, matched Stage 6 benchmark. A separate final Groq `evaluate` summary for the exact provider comparison was not supplied in the visible record. Do not claim model superiority from these numbers.

### 8.3 Resumption and provider comparisons

The inspected screening candidate selection keys off criteria/prompt fingerprint, not provider/model. Switching providers alone does not necessarily rescreen already processed records. The comparison commands correctly used `--redo`.

Provider/model information can be retained in appended screening rows, but the normal project view selects the latest screening for the current criteria. Consequently, capture/export each run explicitly for a controlled comparison rather than assuming the default `evaluate` command compares two providers side by side.

### 8.4 Extra correction: a platform-sensitive connection test

The first provider test attempted a connection to `127.0.0.1:9`, expecting a `cannot connect` error. On the developer's Windows machine, the observed result was `request timed out`, and the assertion failed even though the application had reported a meaningful failure.

The final test mocks `openai.APIConnectionError` on the provider client's completion call, making this specific error-mapping assertion deterministic instead of relying on local port behaviour. The final Stage 6 commit adds `tests/test_providers.py`, including this corrected test.

The same file covers schema transmission, format fallback, authentication/not-found messages, provider creation, model-list checks, remote/local classification and screening through a local fake HTTP server. A test named `...through_real_http` uses that local server; it is not evidence of a live Groq API call.

**Coverage qualification:** not every provider test is fully detached from the local network environment: `test_ollama_not_running` still uses a localhost endpoint. The deterministic change applies to the identified connection-error test, not automatically to all tests in the suite.

A supplied pre-fix suite result was **1 failed, 94 passed in 11.15s**. The developer subsequently reported success, but an exact final post-fix summary is not retained here. Do not turn the former 95-case total into a measured final passing count without the output.

### 8.5 Operational incident and later environment boundary

During the Stage 6 commit workflow, the developer reported a forced PC shutdown followed by `fatal: index file corrupt`. Later output showed the previous `0942ae8` commit, followed by successful final publication of `5087281` on `stage6`.

This is a repository/workstation incident, not evidence of an application logic defect or proof that Ollama caused the shutdown. The exact recovery procedure is not reconstructed from missing messages. It also does not extend the normal Ctrl+C guarantee from Stage 3 to arbitrary system failures.

Linux compatibility was discussed during Stage 6, but the actual isolated Bengio/DEI environment setup was validated later in Stage 8. Ollama exists on both the personal PC and Bengio by that later point; do not retroactively call the Stage 6 output a Bengio inference run.

**Evidence:** R6 and C3.

## 9. Test evidence register: measured, reported and unconfirmed

| Area | Evidence actually available | Interpretation |
| --- | --- | --- |
| Stage 1 manual sample | Commit reports 20 reviewed records, zero disagreements. | Reported manual check; original labels/protocol not retained here. |
| Stage 1 offline tests | Self-test code in the notebook; cleared outputs. | Implementation confirmed, historical execution transcript unconfirmed. |
| Stage 2 notebook/CLI comparison | Commit/README diff records 50 vs 50 and identical source-ID lists. | Historical comparison reported; datasets/query details need retention. |
| Stage 3 interruption | Separate reproducer/fix commits; final handler/schema inspected. | Regression work evidenced; no exact final suite total asserted. |
| Stage 4 Crossref sort | Failing assertion supplied, then `1 passed in 0.11s`; corrected real API/SQLite outputs. | Targeted correction demonstrated in that example. |
| Stage 4 full suite | Developer reported all tests passing. | Exact final summary not retained in the available record. |
| Stage 5 legacy import | Failing skipped-status example, committed correction and later reported pass. | Explicit `status` fixture covered; field-alias caveat remains. |
| Stage 5 CLI suite | `1 failed, 83 passed in 4.09s` before output-assertion correction; later success reported. | This is a pre-fix snapshot, not the final passing total. |
| Stage 5 real retry | Groq 401 -> restored configuration -> 200; failed count 1 -> 0. | Authentication-failure recovery demonstrated. |
| Stage 5 metrics | Exact eight-pair matrix and 0.75 agreement/0.667 recall supplied. | Functional arithmetic/selection test, not scientific accuracy. |
| Stage 6 provider suite | `1 failed, 94 passed in 11.15s` before deterministic test fix; later success reported. | Exact final post-fix total still requires the retained output. |
| Stage 6 real providers | Groq and local Ollama successful HTTP/screening outputs, plus the Ollama matrix. | Integration exercised; no independent large-sample model evaluation. |

The reference checklist figures quoted in the conversation (such as Stage 5's 81 or Stage 6's 92 passing tests) were reference expectations, not measured totals for this modified repository. Test parametrization and added regressions change counts.

The later **107 passed, 2 xfailed** output belongs to Stage 8. Its two security expected failures must not be attributed to the historical Stage 1-6 suites.

No assertion is made that CI ran these snapshots; no workflow-run evidence was collected in this audit.

## 10. Findings to preserve when integrating later stages

### 10.1 Established project-specific changes

| Change | Introduced/identified in | Why it matters |
| --- | --- | --- |
| Notebook local/Colab credential handling and robust records | Stage 1 | Reusable workflow without hard-coded secrets or fabricated missing-value text. |
| Package extraction and missing-key CLI handling | Stage 2 | Separates reusable logic from notebook execution and improves operational errors. |
| Search interruption persistence | Stage 3 | Prevents normal Ctrl+C from silently leaving the run in a misleading state. |
| Shared HTTP and source registry | Stage 4 | Consistent timeout/retry/pacing and per-source failures. |
| Explicit Crossref cursor relevance sorting | Stage 4 | Corrects the observed unrelated first-page results. |
| Crossref public interval 1.1 seconds | Stage 4 | Small pacing margin for the measured anonymous path. |
| Diagnostic scripts | Stage 4 | Repeatable API, provenance and database investigations outside unit tests. |
| Explicit skipped-vs-failed legacy import | Stage 5 | Preserves the tested missing-abstract outcome rather than inventing a processing failure. |
| DOI/link/abstract visibility in the CLI | Stage 5 | Makes manual diagnosis/review easier. |
| Current-criteria status and functional evaluation | Stage 5 | Separates prior rounds, human decisions and comparable model outcomes. |
| Shared Groq/Ollama provider and response-format fallback | Stage 6 | Supports hosted/local inference without duplicating the screening workflow. |
| Deterministic connection-error regression | Stage 6 | Tests the intended exception mapping rather than OS-specific port behaviour. |

### 10.2 Audit qualifications and open improvements

These findings are documentation/audit observations, not new code changes made while producing this file:

1. **Secrets:** Stage 4 reduced HTTP log exposure, but `a088750` explicitly re-enabled those logs by commenting the restrictions. Error/body/exception redaction was incomplete. Later remediation belongs in the Stage 8/Stage 10 security record.
2. **Legacy format variants:** verify both `status` and `screening_status` with archived fixtures; the existing regression does not prove both variants are handled.
3. **Test coverage preservation:** the Stage 5 paper-listing rewrite removed an older status-output assertion. Review whether equivalent counter assertions exist elsewhere before calling coverage unchanged.
4. **Provenance granularity:** `paper_sources.record_json` is a serialized application `Paper`, not a guaranteed raw response archive. Legacy evaluation imports and successful JSON repair do not preserve every possible original/intermediate field.
5. **Evaluation quality:** small assisted or deliberately labelled exercises are functional checks. Fifty independently reviewed papers, supervisor discussion and repeatability were requested but are not confirmed complete here.
6. **Criteria/provider history:** append-only results and a fingerprint aid traceability but do not by themselves produce a fair cross-provider benchmark or identical repeated outputs.
7. **Coverage:** source overlap, newly added project records and metadata conflicts are different quantities. No universal discovery coverage or deduplication accuracy was measured.
8. **Historical data:** a corrected discovery function does not automatically clean unrelated records already stored during earlier faulty searches.
9. **Documentation drift:** old JSON commands, stale TODOs and historical provider-limit values should remain labelled by stage rather than copied into a current quick start.

Do not overwrite later files wholesale merely to recreate an old reference stage. Preserve relevant corrections and regression tests when integrating subsequent functionality.

## 11. Reproduction boundaries and useful historical commands

This document is not an instruction to rerun old code against the current working database. Different stages have different schemas, commands and dependencies. Use isolated checkouts/environments and disposable data if a historical reproduction is needed.

The following Git commands only inspect the already fetched stage references and changes; they do not switch branches or modify files:

```bash
git log --oneline stage1
git log --oneline stage2
git log --oneline stage3
git log --oneline stage4
git log --oneline stage5
git log --oneline stage6
git show b5f6486 -- src/literature_agent/pipeline.py
git show 0a40e00 -- tests/test_crossref_relevance_sort.py
git show 9ca9046 -- src/literature_agent/storage/legacy_import.py
git show a088750 -- src/literature_agent/cli.py tests/test_cli_db.py
git show 5087281 -- tests/test_providers.py
```

Representative commands actually used in the Stage 4-6 exercises were:

```bash
litagent search "human-in-the-loop machine learning" --project stage4-validation --source openalex --source crossref --limit 10
litagent screen --project hitl --max 20
litagent papers --project hitl
litagent evaluate --project hitl
litagent failures --project stage5-retry-test
litagent screen --project stage5-retry-test --retry-failed
litagent screen --project hitl --provider groq --max 10 --redo
litagent screen --project hitl --provider ollama --model llama3.1:8b --max 10 --redo
```

Those commands are historical workflow examples, not a claim that current APIs will return the same records, IDs, limits or model decisions. Do not paste old API keys, full signed URLs, private `.env` values or intentionally wrong benchmark labels into a new scientific run.

## 12. Sources, confirmation register and closure

### 12.1 Repository evidence

All links below refer to the user-specified repository and stage histories or pinned files. No `main` content was used.

**R1 - Stage 1**

- [Stage 1 history](https://github.com/larngroup/litreview-agent/commits/stage1).
- [Stabilisation and reported manual review: `3b90e66`](https://github.com/larngroup/litreview-agent/commit/3b90e66f25cefe43afa8af22ea920ac3477d0d70).
- [Minor follow-up: `8a487ed`](https://github.com/larngroup/litreview-agent/commit/8a487ed904ee8bc217570680efb0f9fcf70e5a53).
- [Pinned stabilised notebook](https://github.com/larngroup/litreview-agent/blob/8a487ed904ee8bc217570680efb0f9fcf70e5a53/groq_openai_papers_finder_synthesizer_v5.ipynb).

**R2 - Stage 2**

- [Stage 2 history](https://github.com/larngroup/litreview-agent/commits/stage2).
- [Package extraction and reported equivalence checks: `1e889d0`](https://github.com/larngroup/litreview-agent/commit/1e889d07e6906535f61146a4728fd044c3b98bb7).
- [README cleanup: `34ff548`](https://github.com/larngroup/litreview-agent/commit/34ff548abcf0f6c2f8ac2db4f3ccf7b28c4567f3).
- [README limits update: `d1a2143`](https://github.com/larngroup/litreview-agent/commit/d1a2143ca344f99ff524cf08f7e42f588a4c52f4).
- [Pinned JSON-based CLI](https://github.com/larngroup/litreview-agent/blob/d1a2143ca344f99ff524cf08f7e42f588a4c52f4/src/literature_agent/cli.py).

**R3 - Stage 3**

- [Stage 3 history](https://github.com/larngroup/litreview-agent/commits/stage3).
- [Initial storage snapshot: `df6eb60`](https://github.com/larngroup/litreview-agent/commit/df6eb6006ac1162fd2c045408934b1041e4f9ca3).
- [Interruption reproducer: `2c5b136`](https://github.com/larngroup/litreview-agent/commit/2c5b136bb7f312a5edc614e3bcc616806d32953b).
- [Interruption correction: `b5f6486`](https://github.com/larngroup/litreview-agent/commit/b5f648668c2571e41e83083592134558161329a0).
- [Closing commit: `3957efc`](https://github.com/larngroup/litreview-agent/commit/3957efc6ead67c9e2de52da33737ae308d41c38e).
- [Pinned pipeline](https://github.com/larngroup/litreview-agent/blob/3957efc6ead67c9e2de52da33737ae308d41c38e/src/literature_agent/pipeline.py) and [database implementation](https://github.com/larngroup/litreview-agent/blob/3957efc6ead67c9e2de52da33737ae308d41c38e/src/literature_agent/storage/database.py).

**R4 - Stage 4**

- [Stage 4 history](https://github.com/larngroup/litreview-agent/commits/stage4).
- [Initial integration: `ecfdacf`](https://github.com/larngroup/litreview-agent/commit/ecfdacfada06b0e8ee8054fb9b53de5a257d8208).
- [Pacing/logging change: `529edb2`](https://github.com/larngroup/litreview-agent/commit/529edb218b2b950028a3232912701aabf9fed087).
- [Relevance/diagnostics follow-up: `0a40e00`](https://github.com/larngroup/litreview-agent/commit/0a40e00a98b4d3cdfd69241ae02d88ade32ad700).
- [Pinned registry](https://github.com/larngroup/litreview-agent/blob/0a40e00a98b4d3cdfd69241ae02d88ade32ad700/src/literature_agent/discovery/__init__.py), [HTTP client](https://github.com/larngroup/litreview-agent/blob/0a40e00a98b4d3cdfd69241ae02d88ade32ad700/src/literature_agent/discovery/http.py), and [CLI logging configuration](https://github.com/larngroup/litreview-agent/blob/0a40e00a98b4d3cdfd69241ae02d88ade32ad700/src/literature_agent/cli.py).
- [Pinned Crossref conversion and search](https://github.com/larngroup/litreview-agent/blob/0a40e00a98b4d3cdfd69241ae02d88ade32ad700/src/literature_agent/discovery/crossref.py).
- [Pinned cursor-sort regression](https://github.com/larngroup/litreview-agent/blob/0a40e00a98b4d3cdfd69241ae02d88ade32ad700/tests/test_crossref_relevance_sort.py) and [diagnostic scripts](https://github.com/larngroup/litreview-agent/tree/0a40e00a98b4d3cdfd69241ae02d88ade32ad700/debug).

**R5 - Stage 5**

- [Stage 5 history](https://github.com/larngroup/litreview-agent/commits/stage5).
- [Criteria implementation: `5d1fb66`](https://github.com/larngroup/litreview-agent/commit/5d1fb66e4bb432e2b09892a8cccb39ba02b23dd9).
- [Comment-only follow-up: `aab3631`](https://github.com/larngroup/litreview-agent/commit/aab3631df361fb6180adc5dcb7480862e8dfc6f7).
- [Legacy-status correction: `9ca9046`](https://github.com/larngroup/litreview-agent/commit/9ca9046f75ad76be8dbaa3c2507cf17b60b3360e).
- [Listing/test/documentation and logging change: `a088750`](https://github.com/larngroup/litreview-agent/commit/a08875021ddc5ede02f053402ec83d3685104469).
- [Pinned criteria/screening implementation](https://github.com/larngroup/litreview-agent/blob/a08875021ddc5ede02f053402ec83d3685104469/src/literature_agent/screening/relevance.py), [evaluation](https://github.com/larngroup/litreview-agent/blob/a08875021ddc5ede02f053402ec83d3685104469/src/literature_agent/screening/evaluation.py), and [legacy importer](https://github.com/larngroup/litreview-agent/blob/a08875021ddc5ede02f053402ec83d3685104469/src/literature_agent/storage/legacy_import.py).

**R6 - Stage 6**

- [Stage 6 history](https://github.com/larngroup/litreview-agent/commits/stage6).
- [Initial provider implementation: `0942ae8`](https://github.com/larngroup/litreview-agent/commit/0942ae842429a79838c4d33de62cee64e3d22ec0).
- [Provider regression tests and closing message: `5087281`](https://github.com/larngroup/litreview-agent/commit/50872810b78b3d821792b67e81a5607fe6ea54f6).
- [Pinned compatible client](https://github.com/larngroup/litreview-agent/blob/50872810b78b3d821792b67e81a5607fe6ea54f6/src/literature_agent/providers/openai_compatible.py), [Ollama preset](https://github.com/larngroup/litreview-agent/blob/50872810b78b3d821792b67e81a5607fe6ea54f6/src/literature_agent/providers/ollama.py), and [provider tests](https://github.com/larngroup/litreview-agent/blob/50872810b78b3d821792b67e81a5607fe6ea54f6/tests/test_providers.py).
- [Pinned screening output-mode and fingerprint handling](https://github.com/larngroup/litreview-agent/blob/50872810b78b3d821792b67e81a5607fe6ea54f6/src/literature_agent/screening/relevance.py).
- [Pinned pipeline preserving earlier work](https://github.com/larngroup/litreview-agent/blob/50872810b78b3d821792b67e81a5607fe6ea54f6/src/literature_agent/pipeline.py) and [legacy-import alias path](https://github.com/larngroup/litreview-agent/blob/50872810b78b3d821792b67e81a5607fe6ea54f6/src/literature_agent/storage/legacy_import.py).

### 12.2 Conversation evidence

| Label | Retained basis in the available development conversation |
| --- | --- |
| C1 | Stage 4 terminal outputs: rate headers, intentional timeout, three Crossref ranking variants, before/after cursor test, run 22 abstracts and five shared-source IDs. |
| C2 | Stage 5 terminal outputs: legacy regression failure, criteria changes, 15-record screening, 0/1/7/8 comparison progression, eight-pair matrix, status, CLI assertion failures, Groq 401/200 retry and criteria-hash groups. |
| C3 | Stage 6 terminal outputs: Ollama model listing and successful inference, Groq 429/retries, ten-candidate local run and eight-pair matrix, connection-test failure, successful-fix acknowledgement and Git incident/commit outputs. |
| C4 | Later discussions and validation records used only to identify stage boundaries and later decisions: [stage7.md](stage7.md) and [stage8.md](stage8.md). Later outcomes are not retroactively counted as tests of earlier snapshots. |

Where an exact original message is not available, this document uses a commit or source reference instead of inventing a chat result. The narrative is not a claim to have searched every conversation in the project.

### 12.3 Confirmation register

| ID | Confirmation requested | Current treatment |
| --- | --- | --- |
| Q1 | Can the Stage 1 20-record sample, topic, predictions and review procedure be recovered? Was review done before seeing model suggestions? | 20/20 agreement is attributed to the commit, not an independently verified accuracy result. |
| Q2 | Are the Stage 2 50-record notebook/CLI datasets, query and source-ID comparison output retained? | The recorded 50/50 match is preserved with its evidence limitation. |
| Q3 | Are the original automated-test outputs available (notebook self-tests for Stage 1 and pytest for later stages), especially the post-fix Stage 5 and Stage 6 summaries? | Partial failing runs and later success reports are distinguished; no inferred final totals. |
| Q4 | Were the Stage 4 final conflict examples and per-source incremental-coverage outputs saved? | Early zero-conflict output and five global shared-source records are retained; no missing coverage totals invented. |
| Q5 | Was the requested independent 50-paper review, supervisor discussion or repeated-screening agreement measurement subsequently completed for Stages 5/6? | Not confirmed; eight-record functional exercises are not substitutes. |
| Q6 | Is there a saved final Groq evaluation from the same Stage 6 comparison, with model/prompt/criteria settings and timing? | No matched performance benchmark or runtime comparison is claimed. |
| Q7 | Do the legacy JSON files actually imported use `status`, `screening_status`, or both? Is there a local fixture for the latter not present in the audited commits? | The confirmed fix is limited to its tested field; the alias discrepancy is a pending compatibility review. |

These questions do not block preserving the historical record. Resolve them by appending evidence and updating the relevant section; absence of a transcript is not proof that an activity never occurred.

### 12.4 Closure and maintenance

By the final Stage 6 snapshot, the project had moved from a stabilised notebook to a project-based, multi-source CLI with SQLite provenance, explicit screening criteria, human review and Groq/Ollama support. The recorded exercises exposed and addressed concrete retrieval, interruption, import and test-portability issues.

The evidence supports operational progress and selected functional validations. It does not support exhaustive literature coverage, general model accuracy, complete credential protection, or completion of every scientific/independent-review requirement.

Keep this document historical. Place current installation/usage instructions and active priorities in the planned setup, usage and roadmap documents. Preserve the original test conditions, distinguish later audit findings from historically performed work, and do not silently replace uncertain results with more convincing numbers.
