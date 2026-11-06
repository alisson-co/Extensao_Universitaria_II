"""Validação de uma execução: compara o registro com os arquivos do bucket.

Uso: python src/validacao.py --execution-id <id> [--config config.yaml]
"""

import argparse
import json
import sys

import yaml
from google.cloud import storage

from registro import ler_registro

CAMPOS_OBRIGATORIOS = [
    "account_id",
    "campaign_id",
    "campaign_name",
    "date",
    "impressions",
    "clicks",
    "cost",
    "execution_id",
]


def validar_execucao(bucket, execution_id):
    """Devolve a lista de problemas encontrados. Lista vazia indica sucesso."""
    registro = ler_registro(bucket, execution_id)
    if registro is None:
        return ["Registro da execução não encontrado."]

    problemas = []
    if registro["execution_status"] != "sucesso":
        problemas.append(f"Status da execução: {registro['execution_status']}.")

    total_de_linhas = 0
    for arquivo in registro["files"]:
        blob = bucket.blob(arquivo["path"])
        if not blob.exists():
            problemas.append(f"Arquivo não encontrado: {arquivo['path']}.")
            continue

        linhas = blob.download_as_text().splitlines()
        total_de_linhas += len(linhas)
        if len(linhas) != arquivo["rows"]:
            problemas.append(f"Quantidade de linhas divergente: {arquivo['path']}.")

        for numero, linha in enumerate(linhas, start=1):
            dados = json.loads(linha)
            faltando = [c for c in CAMPOS_OBRIGATORIOS if c not in dados]
            if faltando:
                problemas.append(
                    f"{arquivo['path']}, linha {numero}: faltam {faltando}."
                )
            elif dados["execution_id"] != execution_id:
                problemas.append(
                    f"{arquivo['path']}, linha {numero}: execution_id diferente."
                )

    if total_de_linhas != registro["rows_collected"]:
        problemas.append("Total de linhas diferente do registrado na execução.")

    return problemas


def main():
    parser = argparse.ArgumentParser(description="Valida uma execução da coleta.")
    parser.add_argument("--execution-id", required=True)
    parser.add_argument("--config", default="config.yaml")
    argumentos = parser.parse_args()

    with open(argumentos.config, encoding="utf-8") as arquivo:
        config = yaml.safe_load(arquivo)

    bucket = storage.Client(project=config["project_id"]).bucket(
        config["bucket_name"]
    )
    problemas = validar_execucao(bucket, argumentos.execution_id)

    if problemas:
        print("Validação com problemas:")
        for problema in problemas:
            print(f"- {problema}")
        return 1

    print("Validação concluída: coleta e armazenamento corretos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
