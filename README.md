# litreview-agent

A local-first assistant for academic literature discovery and AI-assisted relevance screening.

**Status:** early development. See `HELP.md` for the staged development guide.

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env               # then edit .env and add your keys
pytest
litagent search "human-in-the-loop machine learning" --limit 50
litagent screen data/papers_dataset.json
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
