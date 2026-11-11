# Stage 4 — scripts de validação e diagnóstico

Estes são os scripts Python que usamos no terminal para verificar a integração de **OpenAlex + Crossref** com SQLite. Foram organizados por ordem lógica de execução. Cada ficheiro começa com uma descrição em `""" ... """` e pode ser executado individualmente.

## Preparação

A partir da **raiz do repositório** `litreview-agent`, com `.venv` ativo, coloca estes ficheiros diretamente na pasta `debug/`. Executa os comandos abaixo a partir da raiz do projeto `litreview-agent`, com o ambiente virtual ativo.

Os scripts usam `literature_agent.config.load_settings()`, pelo que respeitam o `.env` e o caminho da base de dados (`LITAGENT_DB_PATH`, por defeito `data/literature.db`). **Não copiam nem imprimem as API keys.** Os scripts 02–04 contactam o Crossref; os restantes consultam apenas a SQLite local.

## Ordem de execução

| Ordem | Ficheiro | Objetivo | Pedidos à API? |
|---|---|---|---|
| 1 | `01_check_sqlite_schema.py` | Confirmar que `search_runs.status` aceita `interrupted`, correção do Ctrl+C (Stage 3). | Não |
| 2 | `02_check_crossref_rate_limits.py` | Ler os headers de limites e confirmar o pool Polite com `CONTACT_EMAIL`. | Sim, 1 |
| 3 | `03_compare_crossref_cursor_sort.py` | Reproduzir a diferença entre pesquisa sem cursor, com cursor, e com cursor + `sort=score`. | Sim, 3 |
| 4 | `04_check_crossref_abstracts.py` | Verificar presença e extração de abstracts JATS na resposta original do Crossref. | Sim, 1 |
| 5 | `05_inspect_stored_crossref_run.py` | Ler DOIs, títulos e abstracts efetivamente guardados em `paper_sources` por uma run. | Não |
| 6 | `06_check_cross_source_dedup.py` | Identificar artigos associados às **duas fontes** com um único ID global. | Não |
| 7 | `07_check_metadata_conflicts.py` | Procurar diferenças de título/ano/DOI entre registos de proveniência. | Não |
| 8 | `08_coverage_by_source.py` | Resumir a contribuição incremental de cada fonte para um projeto. | Não |

### Comandos (PowerShell)

```powershell
python debug/01_check_sqlite_schema.py
python debug/02_check_crossref_rate_limits.py
python debug/03_compare_crossref_cursor_sort.py
python debug/04_check_crossref_abstracts.py

# Examinar a última run Crossref do projeto de validação:
python debug/05_inspect_stored_crossref_run.py --project stage4-validation

# Comparar com as runs históricas antes/depois da correção da ordenação:
python debug/05_inspect_stored_crossref_run.py --project stage4-validation --run-id 21
python debug/05_inspect_stored_crossref_run.py --project stage4-validation --run-id 22

# Encontrar publicações associadas a ambas as fontes:
python debug/06_check_cross_source_dedup.py
python debug/06_check_cross_source_dedup.py --project stage4-validation

python debug/07_check_metadata_conflicts.py --project stage4-validation
python debug/08_coverage_by_source.py --project stage4-validation
```

**Nota:** os números das runs (`21`, `22`) são os que obtiveste nos teus testes e só se aplicam à base de dados que ainda os contém. O script 05, sem `--run-id`, seleciona automaticamente a última run Crossref concluída.

## Testes complementares (CLI)

### Pesquisa real nas duas fontes

```powershell
litagent search "human-in-the-loop machine learning" --project stage4-validation --source openalex --source crossref --limit 10
```

### Timeout real: teste negativo (opcional)

Faz o teste com um timeout artificialmente baixo para validar os retries e o erro `SourceError`. O bloco `finally` restaura a variável de ambiente mesmo se o comando terminar com erro.

```powershell
$previous = [Environment]::GetEnvironmentVariable('HTTP_TIMEOUT_SECONDS', 'Process')
try {
    $env:HTTP_TIMEOUT_SECONDS = '0.001'
    litagent search "human-in-the-loop machine learning" --project stage4-validation --source crossref --limit 1
}
finally {
    if ($null -eq $previous) {
        Remove-Item Env:HTTP_TIMEOUT_SECONDS -ErrorAction SilentlyContinue
    } else {
        $env:HTTP_TIMEOUT_SECONDS = $previous
    }
}
```

**Atenção:** o valor esperado é uma falha controlada após tentativas HTTP; se o pedido tiver sucesso inesperadamente, o teste não valida o timeout. Não executar repetidamente sem necessidade.

### Testes de regressão

```powershell
pytest -q tests/test_search_interrupt.py
pytest -q tests/test_crossref_relevance_sort.py
pytest -q
```

## Resultados observados nesta validação

- O Crossref com `CONTACT_EMAIL` devolveu `HTTP 200`, `x-api-pool: polite-array`, `x-rate-limit-limit: 3`, `x-rate-limit-interval: 1s` e `x-concurrency-limit: 3`.
- O teste de timeout produziu `SourceError` após 5 tentativas, sem ficar bloqueado.
- A **run 21**, antes da correção de ordenação, trouxe 10 registos sem abstract, maioritariamente artigos antigos pouco relevantes para o tópico.
- A **run 22**, após acrescentar `sort=score` e `order=desc`, trouxe 10 artigos, dos quais 8 sem abstract. Dois apresentaram abstracts limpos com **916** e **716** caracteres.
- A consulta final de proveniência encontrou **5 artigos** associados tanto ao OpenAlex como ao Crossref (IDs 6, 32, 64, 67, 71).
- Os testes de regressão para o Ctrl+C e para a ordenação do Crossref passaram.

### Como interpretar os contadores

- `new` numa run significa **novo no projeto**, não necessariamente novo na SQLite global.
- `matched_by` indica como um registo foi identificado no conjunto global; pode ser superior a zero mesmo quando `new > 0`.
- `without_abstract` numa pesquisa conta **abstracts vazios na resposta dessa fonte**, antes de os dados serem fundidos com outros registos.
- `paper_sources` conserva a proveniência de cada pesquisa; `papers` contém a representação consolidada do artigo.
- `find_conflicts()` pode devolver zero sem que isso represente uma falha na deduplicação.

Este material é uma **verificação exploratória de desenvolvimento**, não uma avaliação científica definitiva da cobertura de cada API.
