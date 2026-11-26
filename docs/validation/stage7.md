# Stage 7 Validation - Streamlit Interface and Bibliographic Exports - TO REVIEW!!!

**Project:** `litreview-agent` (package: `literature-agent`; CLI: `litagent`)  
**Stage:** 7 of the reference implementation  
**Development branch:** `stage7` (as used in the development discussion; final remote ref not inspected in this review)  
**Recorded search date:** 2026-11-17; individual review/export timestamps were not retained  
**Documentation reconstruction date:** 2026-11-25  
**Status:** The developer exercised the browser workflow and confirmed agreement with the CLI state. Commit/tag verification, the exact Stage 7 automated-test summary, and specific manual-protocol items remain explicitly unconfirmed below.

> **Purpose and evidence standard.** Preserve what was implemented, exercised, observed, and decided during Stage 7 without relying on conversational memory. This is a small functional-validation record, not an independent usability study or a scientific estimate of screening accuracy. Distinguish recorded outputs, operator observations, reference requirements, proposed changes, and unresolved questions. Evidence labels E1-E7 are defined in Section 12.1.
>
> **Repository-review limitation.** The requested GitHub audit could not be completed in this pass. Reads for `superfr123/litreview-agent` returned HTTP 404, and the repository did not appear in the connected account's accessible repository search. This does not prove the repository is absent: its exact URL or connector permissions may need confirmation. No Stage 7 commit diff or tag is claimed to have been inspected. This document uses the uploaded README and available development conversation; later-stage reference code is not substituted for the actual Stage 7 snapshot.

## 1. Scope and acceptance boundary

Stage 7 makes the existing literature-review workflow available through a local Streamlit interface and adds bibliographic/data exports.

The agreed implementation scope was:

1. Create/select projects and edit their topic, research question, and screening criteria.
2. Search OpenAlex and Crossref, inspect search history, and retain the existing deduplication/persistence behavior.
3. Run preliminary title/abstract screening through the provider abstraction introduced earlier.
4. Inspect suggestions and errors, save human decisions and notes, and display model/human agreement.
5. Export stored records as BibTeX, CSV, JSON, or search-history CSV; expose bibliography export through the CLI as well.
6. Show workflow events in the Log view and include provider/privacy and preliminary-screening notices.
7. Add Streamlit AppTest smoke coverage alongside the existing automated suite.

These points describe the recorded Stage 7 scope, not proof that every control, format, and failure path received a manual test. Sections 7, 9, and 10 identify the exercised paths and the evidence gaps.

**Stage boundaries:** OpenAlex/Crossref discovery, criteria-based screening, human review, and Groq/Ollama support were inherited capabilities. Stage 7 exposes them in the browser rather than introducing them for the first time. Automated full-text retrieval and PDF processing belong to Stage 8; evidence extraction/synthesis and report generation belong to later stages. Manually opening an article on a publisher website during this test was an operator action, not an automated full-text feature of Stage 7.

**Privacy boundary:** Running Streamlit locally does not make an external LLM provider local. The recorded screening examples used Groq. No claim is made that a local browser session prevented titles/abstracts from being sent to that provider.

**Evidence:** E1, E2, E4, E5.

## 2. Test environment and project

### 2.1 Environment

| Item | Recorded information | Qualification |
| --- | --- | --- |
| Operator | Project developer | No independent evaluator was confirmed. |
| Host | Personal Windows PC | Validation used PowerShell and a local project virtual environment. |
| UI | Streamlit application | Launched successfully and used through the browser. |
| Storage | Project SQLite database | CLI and UI were compared against the same project. |
| Discovery sources | OpenAlex and Crossref | Both were exercised in the recorded search runs. |
| Screening provider | Groq | The exact model identifier/settings for the final `ui_test` screening run were not preserved in the inspected evidence. |
| Bibliography manager | Zotero | Three human-included records were imported and checked. |
| Exact dependency snapshot | Not recorded for Stage 7 | Do not copy the later Bengio/Stage 8 dependency versions into this historical test. |

Python 3.13.2 was subsequently reported for the personal PC during Stage 8. That later report is not a separately captured Stage 7 environment snapshot. Similarly, the Linux/Bengio setup was validated later and is documented in [stage8.md](stage8.md), not claimed as a Stage 7 test.

The README recorded these installation/startup instructions:

```bash
python -m pip install -e ".[web,dev]"
python -m streamlit run app/streamlit_app.py --server.address localhost
```

The browser entry point was `http://localhost:8501`.

### 2.2 Review topic and criteria

The actual SQLite project name is **`ui_test`**, with an underscore. The reference exercise suggested `ui-test`; commands in this validation record use the name actually created.

**Topic:** Machine Learning and Deep Learning for Protein-Ligand Binding Affinity Prediction in Drug Discovery.

**Research question agreed in the conversation:**

> How accurately can machine learning and deep learning models predict protein-ligand binding affinity?

The screening discussion described criteria addressing ML/DL prediction of protein-ligand affinity, evaluation of predictive performance, and exclusion of review/editorial/opinion material or studies without the required evaluation.

> **TO CONFIRM - Q3:** Preserve the exact saved research-question field and complete inclusion/exclusion lists from `ui_test`. The paragraph above is a summary of the discussion, not a verbatim database export. Do not reconstruct missing criteria wording, Boolean logic, or document-type rules from it. In particular, confirm whether doctoral theses are eligible; one thesis was included in the functional exercise.

### 2.3 Final Stage 7 project state

The operator posted the following CLI state, which agreed with the Streamlit counters:

| Property | Recorded value |
| --- | ---: |
| Project records | 21 |
| Records without an abstract in SQLite | 5 |
| Records processed by screening for the current criteria | 10 |
| Screening status `ok` | 9 |
| Screening status `skipped` | 1 |
| Not screened for the current criteria | 11 |
| Model suggestions `include` | 6 |
| Model suggestions `exclude` | 3 |
| Automatic `uncertain` placeholder | 1 |
| No current model suggestion | 11 |
| Human-reviewed records | 5 |
| Human `include` | 3 |
| Human `exclude` | 2 |
| Not human-reviewed | 16 |

Here, "21 records" is the project count, not a verified count of 21 distinct primary research studies. The sample includes different publication types. Paper IDs are local SQLite identifiers and should not be expected to match a fresh database.

**Evidence:** E1-E3.

## 3. Implementation inventory and attribution

### 3.1 Components relevant to this validation

| Component/path | Recorded responsibility | Verification boundary |
| --- | --- | --- |
| `app/streamlit_app.py` | Project controls and Criteria, Search, Screening, Review, Export, and Log views | Browser functionality was exercised; final Stage 7 source revision awaits GitHub access. |
| `src/literature_agent/pipeline.py` | Shared discovery/screening workflows called by interfaces | Architectural scope recorded in the development plan; exact Stage 7 diff not inspected. |
| `src/literature_agent/storage/database.py` | Persist projects, search runs, screening, human review, and events | Same-project CLI/UI counters matched; no claim of a new Stage 7 schema migration. |
| `src/literature_agent/exports.py` | Build bibliography/data exports from stored records | BibTeX behavior was manually exercised; implementation-level edge cases need the actual source/tests. |
| `src/literature_agent/cli.py` | Expose `litagent export` and retain existing commands | CLI status was exercised; a Stage 7 CLI export run was not retained. |
| `tests/test_streamlit_app.py` / AppTest coverage | UI smoke tests listed in the Stage 7 scope | Exact cases and assertions require the Stage 7 test snapshot. |
| Export test coverage | Test export behavior | Exact test file inventory and results require the Stage 7 snapshot. |
| `pyproject.toml` | Web/dev installation support | Web installation/startup worked; do not substitute the later Stage 8 dependency list. |
| `README.md` | Startup instructions and validation notes | Supplied and inspected. |

The agreed commit-description shorthand was "project/criteria/search/screening/review/export/log tabs". Project creation/selection was part of the UI; this record does not require it to have been a literal separate tab rather than a sidebar control.

### 3.2 Inherited fixes versus Stage 7 work

Keep these distinctions when the commit comparison becomes available:

| Development period | Work already discussed/implemented | Do not misattribute it to Stage 7 |
| --- | --- | --- |
| Stages 3-4 | Persistent search history, per-source failure handling, Crossref relevance ordering with cursor pagination, deduplication, HTTP timeout/retry/pacing, interruption handling | Stage 7 uses these workflows. |
| Stage 5 | Criteria fingerprints, screening states, human review, evaluation, legacy import status corrections, expanded CLI paper details | These are not newly introduced merely because the UI displays them. |
| Stage 6 | Groq/Ollama provider abstraction and provider checks; deterministic connection-error test | Existing provider functionality exposed in the Stage 7 UI. |
| Stage 7 | Streamlit UI, bibliography/data exports, associated smoke coverage, browser validation, startup instructions and metadata/UI limitation notes | This document's scope. |
| Stage 8 | Full-text module, PDF parsing, fontTools investigation, full-text CSV table export, HTTP `email` exclusion and security xfails, Linux setup | Documented separately; not evidence of Stage 7 feature coverage. |

Preservation of every inherited fix at the final Stage 7 commit remains a source/diff question, not something established by the small browser exercise alone.

### 3.3 Commit and tag provenance

| Reference | Evidence available | Status |
| --- | --- | --- |
| Stage 6 final commit `5087281` | Operator-pasted `git log` with provider-abstraction message | Historical reference; commit object not reopened in this review. |
| Final Stage 7 commit | Agreed message beginning `Add Streamlit interface and exports (BibTeX, CSV, JSON, search history)` | Final SHA and exact committed changes not retrieved. An agreed message is not proof of the stored commit. |
| `v0.7.0-mvp` | Tag name in the reference checklist and suggested commands | Creation, target commit, and remote push not confirmed here. |
| First Stage 8 commit | Operator later reported making an initial Stage 8 commit | SHA and its relationship to the Stage 7 tip not retrieved. |
| Later Stage 8 commit `1f30c18` | Operator-pasted clone/log output | Subsequent context only; not the first Stage 8 commit and not the Stage 7 release. |

> **TO CONFIRM - Q1:** Obtain the exact repository URL/connector access, final Stage 7 SHA, relevant Stage 6-to-Stage 8 history, and tag target. No commit list, diff, or tag was fabricated to fill this gap.

## 4. Discovery and search-history verification

The topic was used as the search query in the UI. Two searches were run initially and then repeated, with **limit 10 per source**.

| Run | Source | Start time (UTC, 2026-11-17) | Retrieved | New to project |
| --- | --- | --- | ---: | ---: |
| 26 | OpenAlex | 15:33:28 | 10 | 10 |
| 27 | Crossref | 15:33:29 | 10 | 10 |
| 28 | OpenAlex | 15:53:40 | 10 | 0 |
| 29 | Crossref | 15:53:44 | 10 | 1 |

All four recorded search runs completed. Together they returned **40 result occurrences** and added **21 project records**. Repeating the searches did not add all results again: the first repeat added none and the second added one.

This supports correct reuse/deduplication in this exercise. It does not prove that every pair of related publications was deduplicated correctly, that all result sets were stable, or why the Crossref repeat contained one new record.

The reference procedure requested **20 results per source**. The recorded runs all used **10**. Repeating a top-10 query is not equivalent to retrieving the top 20 or a second page. The developer did not need to erase the project, but this remains a documented deviation from the literal protocol.

The UI search history and the CLI run list were checked. Search history is cumulative; it is not a count of the papers remaining eligible after screening or review.

**Evidence:** E1, E2, E4.

## 5. Screening and human-review verification

### 5.1 Screening maximum and states

Screening was run with a maximum of **10** records. The final state was **9 `ok`, 1 `skipped`, and 11 not screened**.

| Display/status | Interpretation in the tested workflow |
| --- | --- |
| `ok` | The screening request produced a valid result; it can be `include`, `exclude`, or `uncertain`. It does not mean the paper is relevant. |
| `skipped` with `uncertain` | The record lacked an abstract in SQLite and was left for manual handling instead of being sent to the model. This is a pipeline placeholder, not a substantive LLM judgment. |
| Not screened | No current-criteria result was available for the record; the maximum of 10 left further records unprocessed. |
| Human decision | A separately saved reviewer judgment, not a replacement of the recorded model output. |

Five project records lacked abstracts, but only one of the ten processed records was skipped. These counts are compatible: the other missing-abstract records need not have been selected in that limited run.

The thesis example (#129) was reviewed manually while still not screened. This demonstrated that manual review did not require an existing LLM result.

No failed LLM request was reported for this `ui_test` screening run. An earlier intentional invalid-key/retry experiment belongs to Stage 5 and must not be presented as a Stage 7 UI failure/retry test.

### 5.2 Five reviewed examples

The following mapping is reconstructed from the reviewed examples, final totals, and the three exported human-included IDs. It is not a fresh SQL query of the historical review table.

| Local ID | Record | Automatic state discussed | Human outcome recorded/reconstructed |
| --- | --- | --- | --- |
| 119 | A point cloud-based deep learning strategy for protein-ligand binding affinity prediction | Model `include`; consistent with the two include/include pairs | `include`; present in the human-included BibTeX export |
| 120 | From machine learning to deep learning: Advances in scoring functions for protein-ligand docking | Model `exclude` | `exclude`; review article under the stated criteria |
| 121 | K DEEP: Protein-Ligand Absolute Binding Affinity Prediction via 3D-Convolutional Neural Networks | Model `include` | `include`; present in the human-included BibTeX export |
| 123 | Recent advances in machine learning predictions of protein-ligand binding affinities | Missing abstract; automatic `skipped`/`uncertain` | `exclude` after manually finding and reading the publisher abstract |
| 129 | Protein-ligand binding affinity prediction using combined molecular dynamics simulations and deep learning algorithms | Not screened | `include`; present in the human-included BibTeX export; thesis type noted |

For #123, finding the abstract in a browser does not establish that it was inserted into SQLite or that the record was rescreened. For #129, the preliminary inclusion did not establish that all predictive-performance criteria had been verified from the full thesis.

Suggested review-note wording was supplied during the discussion, but the exact saved note text and reviewer-initial fields were not exported for this document. They must not be reproduced as verbatim persisted records.

### 5.3 Human override versus disagreement with the LLM

The `uncertain` to human `exclude` change on the missing-abstract example demonstrated resolution of an automatic placeholder. It was not a correction of an actual LLM judgment, because that record was skipped.

The reference procedure said to change at least one model suggestion and add a note. The operator exercised human review and saved five outcomes. Whether resolving the automatic placeholder satisfies the intended override step should be clarified; it does not establish disagreement with an LLM-generated classification. However, the final comparable matrix contains no human/model disagreement, and no separate saved override of an actual LLM-generated `include`/`exclude` result was retained in the reviewed record.

> **TO CONFIRM - Q4:** Was a genuine model-suggestion override saved, with a note, during another step of the UI trial? If not, record the placeholder override as the narrower test actually performed. Do not create an intentionally incorrect scientific decision just to force disagreement.

**Evidence:** E1-E4.

## 6. Agreement report: why `compared` was three

The recorded report was:

```json
{
  "compared": 3,
  "agreement": 1.0,
  "include_recall": 1.0,
  "includes_wrongly_excluded": 0,
  "matrix": {
    "human=include/model=include": 2,
    "human=exclude/model=exclude": 1
  }
}
```

Only three of the five reviewed records had an eligible completed model screening for comparison. The skipped/no-abstract example and the not-screened thesis explain the other two reviews.

| Field | Meaning in this sample |
| --- | --- |
| `compared: 3` | Three reviewed records entered the model/human comparison, not five. |
| `agreement: 1.0` | All three comparable pairs agreed: 3/3. |
| `include_recall: 1.0` | Both human-included records within that comparable subset were model includes: 2/2. |
| `includes_wrongly_excluded: 0` | No comparable human include was a model exclude. |
| Matrix | Two include/include pairs and one exclude/exclude pair. |

The third human include (#129) does not enter the recall denominator because it had not been screened. Thus 100% recall here is **not** evidence that the model found all human-included records in the project.

A skipped `uncertain` and a model-generated `uncertain` are different cases; the exclusion here concerns screening status, not a blanket rule that the label `uncertain` can never be compared.

This was a **functional calculation check** on three comparable records. The reviewer saw model suggestions and discussed decisions with the assistant. It was not a blind gold-standard exercise, and the figures must not be used as a model-accuracy or systematic-review-quality claim.

**Evidence:** E1-E3.

## 7. Bibliographic export and metadata validation

### 7.1 Human-included BibTeX and Zotero

The filter **"Included by a human reviewer"** was selected for BibTeX export. Although five records had human reviews, only **three** had a human `include` decision. The exported file contained those three entries, and Zotero imported three entries.

| Local ID | Exported record | DOI retained in the investigation |
| --- | --- | --- |
| 119 | A point cloud-based deep learning strategy for protein-ligand binding affinity prediction | `10.1093/bib/bbab474` |
| 121 | K DEEP: Protein-Ligand Absolute Binding Affinity Prediction via 3D-Convolutional Neural Networks | `10.1021/acs.jcim.7b00650` |
| 129 | Protein-ligand binding affinity prediction using combined molecular dynamics simulations and deep learning algorithms | `10.70675/afb433b4z5353z43edzae3fzb8133e571989` |

The operator opened all three DOI links and confirmed that they led to the corresponding documents. The initially suspected "only three of five imported" problem was therefore explained by the selected inclusion filter, not a demonstrated Zotero or export failure.

These are historical operator observations. DOI links were not re-resolved during this documentation pass, and the original BibTeX bytes were not available for a new parser-level audit here.

### 7.2 Field-level observations

| Observation | Recorded conclusion | What must not be inferred |
| --- | --- | --- |
| Generic `@misc` entries | The earlier file inspection recorded generic BibTeX types, and Zotero showed Document rather than a specific journal/thesis type. | Generic type is a metadata/export limitation, not proof of fabricated content. |
| #129 year missing | Streamlit showed `year unknown`; the exported record omitted the year. The operator found `Soutenance le 11/12/2023` on the source page. | The French date format was suggested as a possible explanation, but no parser trace proved it caused the missing year. A defence date is also a distinct metadata fact to preserve with provenance. |
| #119 year 2021 versus a reported 2022 issue date | A possible online-first/issue-date distinction was discussed. | No source-data update or definitive date correction was established in this validation. |
| #119 author-name concern | The operator inspected the names and did not confirm an error. | Do not retain an earlier assistant suspicion as a confirmed author defect. |
| #129 document type | The record was identified as a doctoral thesis during manual inspection. | Do not silently relabel it as a journal article or assume a final thesis-eligibility policy. |
| Bibliographic completeness | The missing year and generic type show that an importable record need not be a complete citation; no exhaustive field-level audit was retained. | Do not claim that every journal, volume, page, or author field was independently validated. |

**Bounded conclusion:** The three exported entries were importable and matched the documents the operator opened. No invented field was demonstrated in that inspected sample. This is not an exhaustive audit of all upstream metadata or every export path.

### 7.3 Export coverage boundaries

| Export capability in Stage 7 scope | Manual evidence retained |
| --- | --- |
| BibTeX, human-included subset | Exercised; three records imported into Zotero and DOI targets checked. |
| CSV bibliography/decisions export | Capability listed; no separate Stage 7 file comparison retained. |
| JSON full-record export | Capability listed; no separate Stage 7 round-trip/field check retained. |
| Search-history CSV | Capability listed; no separate Stage 7 exported-file check retained. |
| `litagent export` | Command included in agreed implementation scope; no standalone CLI export transcript retained. |
| Other bibliography subsets | Not independently verified in this Stage 7 record. |

The two identical CSVs downloaded from the **Full text table** were tested later in Stage 8. That table's export and subset semantics are not proof that the Stage 7 bibliography export ignores its filter. They are different controls and code paths.

**Evidence:** E1, E3, E5; later boundary cross-check in E6.

## 8. Event log and CLI/UI consistency

### 8.1 Events inspected

The displayed Log view showed search and screening start/completion events:

```text
search_started
search_completed
screening_started
screening_completed
```

No export event was seen in the inspected log. Export itself worked. This supports an observation about missing export traceability in that view; it is not proof that the file was not generated, nor a requirement failure under the quoted reference step, which asked for search, screening, and criteria events.

A `criteria_updated` event was suggested as the item to look for, but the available record does not contain the operator's final confirmation that it was found. Project creation and a subsequent criteria update must not be assumed to produce identical audit events.

> **TO CONFIRM - Q5:** Was a criteria-update event located in the Log, and was an explicit criteria edit/save performed after project creation? Until confirmed, this part of the manual protocol remains unverified.

### 8.2 CLI/UI state check

The operator ran:

```powershell
litagent status --project ui_test
```

The relevant output was:

```text
Papers: 21  (without abstract: 5)
Screening status (current criteria): {'ok': 9, 'skipped': 1, 'not screened': 11}
Model suggestions:                   {'include': 6, 'exclude': 3, 'uncertain': 1, '-': 11}
Human decisions:                     {'include': 3, 'exclude': 2, 'not reviewed': 16}
```

These values matched the UI counters discussed during validation. The four completed search runs are listed in Section 4.

This confirms consistency of the observed project state, not complete equivalence of every CLI/UI feature or error path. The reference workflow was performed through the browser, with this CLI command used for the explicit final cross-check.

**Evidence:** E1-E3.

## 9. Automated tests and reference checklist

The operator reported that the Stage 7 changes passed the tests and the website worked. The reference checklist quoted **`100 passed`**, but an exact Stage 7 `pytest -q` summary and duration were not retained in the inspected record.

| Item | Evidence status |
| --- | --- |
| Automated suite after Stage 7 implementation | Operator reported all tests passed. Exact count/duration unconfirmed. |
| Reference `100 passed` | A guide expectation, not a captured measured result. |
| AppTest smoke tests | Listed in the Stage 7 implementation/commit scope; exact tests require source verification. |
| Manual browser workflow | Detailed observations retained in this document. |
| Later Stage 8 `106 passed` | Different stage; do not use it to infer a Stage 7 count. |
| Later Stage 8 `107 passed, 2 xfailed` | Confirmed later full-suite result; the security xfails were not part of Stage 7. |

No tests were executed against an exact Stage 7 checkout during this documentation reconstruction. A later checkout/test run, if performed, must be labelled with its actual commit and dependency environment rather than presented as the original November 17 test run.

> **TO CONFIRM - Q2:** Recover the exact Stage 7 pytest summary if available. If it was not retained, keep "operator reported all tests passed; numerical summary not retained" rather than back-calculating it.

## 10. Manual-protocol acceptance matrix

The procedure below comes from the Stage 7 verification instructions quoted by the operator, not from a newly retrieved complete manual.

| Reference step | Recorded execution | Assessment |
| --- | --- | --- |
| 1. Create `ui-test`, topic, and two inclusion criteria | Created `ui_test`, selected the affinity-prediction topic and a single research question, and used criteria in review discussions. | Project creation exercised. Exact final saved criteria need Q3 confirmation. |
| 2. Search both sources with limit 20 and check history | OpenAlex/Crossref searched with limit 10, then repeated; four runs retained. | Function exercised with an explicit limit deviation. |
| 3. Screen max 10, watch progress, inspect failures if present | Ten processed: nine `ok`, one `skipped`; eleven left unprocessed. | Screening/progress exercised. No failed LLM case reported in this sample. |
| 4. Review five, change at least one suggestion, add a note | Five reviewed; an automatic missing-abstract placeholder was resolved and an unscreened thesis included. | Human review exercised. Actual LLM override and saved-note specifics need Q4 confirmation. |
| 5. Export human-included BibTeX and verify in a reference manager | Three human includes exported/imported in Zotero; all three DOI targets checked. | Functional path passed; metadata limitations recorded. |
| 6. Find search, screening, and criteria events | Search/screening events seen; no export event seen. | Search/screening logging exercised; criteria event needs Q5 confirmation. |
| 7. Compare CLI and UI totals | `litagent status --project ui_test` matched the recorded UI state. | Passed for the observed snapshot. |

The quoted MVP checklist additionally required a second person, ideally the supervisor, to carry out the browser verification, README startup instructions, and a committed/tagged `v0.7.0-mvp` release.

| Additional checklist item | Recorded status |
| --- | --- |
| README app-start command | Added and present in the supplied README. |
| Independent browser verification | Not confirmed; the retained exercise was performed by the developer with assistant support. |
| Commit | Final Stage 7 hash/message awaits Q1 repository verification. |
| Tag `v0.7.0-mvp` | Suggested/required name known; existence and pushed target not confirmed. |

> **TO CONFIRM - Q6:** Did another person complete the browser protocol? If yes, record their role, date, scope, and findings without claiming that developer/assistant discussion was independent validation.

**Decision boundary:** The developer's functional baseline was used to proceed to Stage 8. Do not describe every literal reference-checklist item as completed while the noted deviations and evidence gaps remain.

## 11. Findings, decisions, and later follow-up

### 11.1 Findings supported by the recorded exercise

- The browser workflow created and populated a project, ran limited screening, and stored human review decisions.
- Repeated searches reused existing records rather than blindly adding all results again.
- Missing-abstract, not-screened, completed-model, and human-review states were distinguishable, although the interface terminology initially caused confusion.
- `compared: 3` was compatible with five human reviews; the two excluded comparisons were not failed evaluations.
- Three Zotero imports were correct for three human includes, not an export loss from five reviewed records.
- Bibliographic completeness remained limited: generic entry types, a missing thesis year, and a date-convention question were identified. No confirmed author-name error was established.
- Search/screening history and CLI/UI counters were consistent in the observed project.

### 11.2 Changes and decisions recorded during Stage 7 validation

The browser/export functionality and smoke-test coverage were part of the implementation scope. The clearly recorded follow-up documentation work was adding the Streamlit startup command and the manual-verification/metadata notes to the README.

No export-format rewrite, automatic metadata enrichment, or new PDF retrieval mechanism was confirmed as a fix during this Stage 7 validation. These findings were documented rather than silently corrected in the dataset.

The expanded CLI paper display, legacy import fixes, and provider changes discussed earlier were inherited work; an exact commit comparison is still needed to establish whether any additional adjustments occurred within the Stage 7 commit range.

### 11.3 Deferred improvements

| Follow-up | Basis and constraint |
| --- | --- |
| Export audit events | Consider recording format, subset, and record count; no event was observed in the inspected Log. |
| Specific BibTeX types | Emit article/thesis/conference types only when supported by stored metadata. |
| Metadata enrichment with provenance | Address missing year/type/publication details and distinguish date meanings. Do not invent values. |
| Clearer UI state explanations | Distinguish skipped placeholders, actual model uncertainty, not-screened records, and human decisions. |
| Preserve/clarify eligibility policy | Decide how theses and review material are treated for the scientific review, separate from the functional demonstration. |
| Documentation cleanup | Separate current commands from legacy examples and completed TODOs; retain this validation history. |
| Wider export/edge-case testing | Verify untested formats/subsets and failures without treating the one successful BibTeX import as exhaustive coverage. |

The subsequent Stage 8 work investigated document relationships, related publication versions, OA access, PDF extraction, and additional security concerns. Those later observations are documented in [stage8.md](stage8.md); they are not retroactively labelled as Stage 7 tests or fixes.

## 12. Evidence register, open confirmations, and closure

### 12.1 Evidence register

| Label | Material used | Evidential limits |
| --- | --- | --- |
| E1 | Uploaded `README.md`, section `Stage 7 - Manual verification notes (2026-11-17)`, plus the Streamlit startup section | Directly inspected in this review. Contains historical notes later carried into a Stage 8-era README, not a commit-pinned Stage 7 README. |
| E2 | Operator-pasted `litagent status --project ui_test` output and search runs 26-29 | Direct numerical evidence retained in the available conversation. No live historical database was queried here. |
| E3 | Available Stage 7 review/export discussion and operator reports: five reviews, three Zotero imports, DOI checks, metadata observations, agreement JSON | Some examples were originally discussed with screenshots. Not all original image/BibTeX bytes remain accessible; exact notes/criteria are not reconstructed from missing images. |
| E4 | Stage 7 verification procedure and MVP checklist quoted by the operator | Provides the requested protocol; not proof of execution and not a fresh inspection of the complete original manual. |
| E5 | Agreed Stage 7 commit description and operator-reported implementation/test success | Supports declared scope, not exact commit contents, per-file diffs, numerical pytest results, or remote tag state. |
| E6 | Reviewed [Stage 8 validation record](stage8.md) and subsequent operator outputs | Used only to separate later work and preserve the inherited `ui_test` baseline; later tests are not counted as Stage 7 tests. |
| E7 | GitHub connector access attempts during this reconstruction | Repository reads returned 404 and the target was not listed in accessible searches; final commit/tag/diff audit remains pending. |

Only the conversation material available to this review and the retrieved files were used. No claim is made that every other chat in the Project was searchable or exhaustively inspected. Project-file searches did not recover an additional authoritative Stage 7 snapshot.

### 12.2 Confirmation register

| ID | Question to the operator | Update when evidence is available |
| --- | --- | --- |
| Q1 | What is the exact repository URL, can the connector access it, and which commit/tag closes Stage 7? | Verify the Stage 6-to-Stage 8 history, identify the actual Stage 7 tip, inspect diffs/tests, and confirm `v0.7.0-mvp`. |
| Q2 | Was the Stage 7 pytest summary retained? | Record the real count, failures/skips if any, duration, environment, and commit; otherwise preserve the gap. |
| Q3 | What exact criteria/research question were saved for this `ui_test` round, including the thesis policy? | Add a verbatim criteria snapshot with provenance; do not infer missing wording. |
| Q4 | Was any actual LLM suggestion overridden with a saved note, beyond the skipped-placeholder example? | Record paper ID, before/after decision, and the factual note or explicitly state this narrower protocol step was not demonstrated. |
| Q5 | Was a criteria-update event found in the UI Log? | Record the action/event evidence, or leave criteria-event inspection unconfirmed. |
| Q6 | Was the browser protocol also completed by an independent person? | Add role/date/scope/results, or retain developer-only validation. |

### 12.3 Closure assessment

**Supported conclusion:** The Stage 7 browser workflow was operational in the developer's `ui_test` exercise. The recorded project contained 21 papers, ten processed screening records, and five human reviews. Three human-included bibliographic entries imported into Zotero and resolved to the documents inspected by the operator. The CLI and UI state agreed.

**Limits:** The exercise used 10 rather than 20 results per source; agreement was calculated on only three non-blind comparisons; metadata completeness was not guaranteed; exact saved criteria/notes and selected audit events are not fully preserved; no independent user trial, exact final pytest count, or final commit/tag has been verified in this reconstruction.

**Decision:** Preserve the successful functional observations and the explicit qualifications. Proceeding to Stage 8 did not erase these limitations. Complete Q1-Q6 where evidence is available; do not rerun history on a newer branch and present it as the original Stage 7 result.

---

### Record maintenance

Update this document when the operator confirms an open item or the exact commit snapshot becomes accessible. Keep completed tests, code behavior, manual observations, hypotheses, and proposed improvements distinct. Do not include API keys, raw `.env` contents, institutional credentials, or signed download tokens. This file documents Stage 7 only; it does not replace the user guide or modify the README, source code, or Stage 8 validation record.
