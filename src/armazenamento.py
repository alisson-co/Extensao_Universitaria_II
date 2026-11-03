"""Gravação dos dados coletados no Google Cloud Storage (Data Lake)."""

import json

PREFIXO_DADOS = "raw/google_ads/campaign_metrics"


def caminho_do_arquivo(data_referencia, execution_id):
    """Monta o caminho do arquivo de dados dentro do bucket."""
    return (
        f"{PREFIXO_DADOS}/date={data_referencia}/"
        f"execution_id={execution_id}/data.jsonl"
    )


def agrupar_por_data(registros):
    """Separa os registros por data de referência."""
    grupos = {}
    for registro in registros:
        data = registro["date"]
        if data not in grupos:
            grupos[data] = []
        grupos[data].append(registro)
    return grupos


def converter_para_jsonl(registros):
    """Converte os registros em texto JSONL (um objeto JSON por linha)."""
    linhas = []
    for registro in registros:
        linhas.append(json.dumps(registro, ensure_ascii=False))
    return "\n".join(linhas) + "\n"


def armazenar_registros(bucket, registros, execution_id):
    """Grava um arquivo por data e devolve a lista de arquivos criados."""
    arquivos = []
    grupos = agrupar_por_data(registros)

    for data, registros_da_data in sorted(grupos.items()):
        caminho = caminho_do_arquivo(data, execution_id)
        conteudo = []
        for registro in registros_da_data:
            registro_com_origem = dict(registro)
            registro_com_origem["execution_id"] = execution_id
            conteudo.append(registro_com_origem)

        blob = bucket.blob(caminho)
        blob.upload_from_string(
            converter_para_jsonl(conteudo),
            content_type="application/x-ndjson",
            checksum="crc32c",
        )
        arquivos.append({"path": caminho, "rows": len(conteudo)})

    return arquivos
