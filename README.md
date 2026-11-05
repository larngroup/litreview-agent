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
litagent project create <project_name> --topic "<Topic to search>"   # create a project
#for example: litagent project create hitl --topic "human-in-the-loop machine learning"

litagent search "<Topic to found relevance>" --project <project_name> --limit <select searching limit>    #search into the database
#for example: litagent search "Active Learning" --project hitl --limit 10

litagent screen --project <project_name>            #
#for example: litagent screen --project hitl         

litagent status --project <project_name>            #status: permite consultar o estado atual sem executar uma nova pesquisa.
#for example: litagent status --project hitl        

# import JSON files from the original v4 notebook into a separate project -> see your path to v4
litagent import-json path/to/v4/papers_dataset.json --project hitl-v4 --evaluated path/to/v4/evaluated_dataset.json --legacy-topic "Human in the loop"
litagent status --project hitl-v4   # to check


#NOTAS cli
#Database workflow (new in Stage 3):
    litagent project create NAME --topic "..."
    litagent search "query" --project NAME --limit 100
    litagent screen --project NAME [--retry-failed]     #se um artigo já ficou registado como failed, não é repetido automaticamente numa execução normal. Para o repetir, tens de usar a flag --retry-failed
    litagent status --project NAME
    litagent import-json --project NAME papers.json [--evaluated evaluated.json]

#JSON workflow from Stage 2 (still works, no --project):
    litagent search "query" --out data/papers_dataset.json
    litagent screen data/papers_dataset.json --out data/evaluated_dataset.json

#README FILE TO FINISH - USED NOW TO NOTES
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
