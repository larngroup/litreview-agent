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

## Others

- Final script block on jupiter notebook its compare source_ids from stage 1 (notebook) and stage 2

### Results

- Stage 1: 50 papers
- Stage 2: 50 papers
- Same source_id lists: True

CMD: litagent screen data/papers_dataset.json                       
ERROR: GROQ_API_KEY is not set. Add it to your .env file.

Added to .gitignore json data produced by notebooks