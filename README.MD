# Data Lake de Google Ads — Extensão Universitária II

Coleta dados de campanhas do Google Ads e os armazena no Google Cloud Storage, com registro e validação de cada execução.

## Preparação

```powershell
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy google-ads.example.yaml google-ads.yaml
copy config.example.yaml config.yaml
gcloud auth application-default login
```

Preencha `google-ads.yaml` e `config.yaml`. Esses arquivos ficam fora do Git.

## Execução

```powershell
python tests/test_access.py                # T01: autenticação e acesso
python src/main.py                         # Coleta o dia anterior
python src/main.py --data-inicial 2026-10-01 --data-final 2026-10-31
python src/validacao.py --execution-id ID  # Valida uma execução
```

## Testes locais

Não exigem credenciais nem acesso à internet:

```powershell
python -m unittest discover -s tests -p "test_fluxo.py" -v
```

## Organização no bucket

```text
raw/google_ads/campaign_metrics/date=AAAA-MM-DD/execution_id=ID/data.jsonl
control/executions/ID.json
```

Use somente os dados de execuções com `execution_status` igual a `sucesso`.
