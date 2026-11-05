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
# TODO Stage 5: 
- Fix `legacy_import.py` to preserve `skipped_no_abstract` as `skipped` / `uncertain`, instead of incorrectly marking it as `failed`.
- Add a regression test for imported screening statuses.
- Keep legacy screenings separate using `criteria_hash="legacy"`.
- Verify that `litagent status` reports screenings for the current criteria only, as planned in Stage 5.
- Ensure imported historical results remain available after re-screening.
```

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
