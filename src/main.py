"""Executa o fluxo completo: coleta, armazenamento e registro.

Uso:
    python src/main.py
    python src/main.py --data-inicial 2026-10-01 --data-final 2026-10-31
"""

import argparse
import sys
from datetime import date, timedelta

import yaml
from google.ads.googleads.client import GoogleAdsClient
from google.cloud import storage

from armazenamento import armazenar_registros
from coleta import coletar_campanhas
from registro import iniciar_registro, salvar_registro


def definir_periodo(data_inicial, data_final, hoje):
    """Usa o dia anterior ou o período informado na execução."""
    if data_inicial is None and data_final is None:
        ontem = (hoje - timedelta(days=1)).isoformat()
        return ontem, ontem

    if data_inicial is None or data_final is None:
        raise ValueError("Informe a data inicial e a data final.")

    inicio = date.fromisoformat(data_inicial)
    fim = date.fromisoformat(data_final)
    if inicio > fim:
        raise ValueError("A data inicial não pode ser posterior à data final.")
    return data_inicial, data_final


def executar(carregar_cliente, bucket, customer_id, data_inicial, data_final):
    """Executa o fluxo e sempre tenta gravar o resultado no registro.

    A autenticação acontece aqui dentro para que uma falha nessa etapa
    também fique registrada.
    """
    registro = iniciar_registro(data_inicial, data_final)

    try:
        cliente_ads = carregar_cliente()
        registros = coletar_campanhas(
            cliente_ads, customer_id, data_inicial, data_final
        )
        registro["rows_collected"] = len(registros)
        registro["files"] = armazenar_registros(
            bucket, registros, registro["execution_id"]
        )
        registro["execution_status"] = "sucesso"
    except Exception as erro:
        registro["execution_status"] = "falha"
        registro["error_message"] = f"{type(erro).__name__}: {erro}"

    salvar_registro(bucket, registro)
    return registro


def main():
    parser = argparse.ArgumentParser(description="Coleta dados do Google Ads.")
    parser.add_argument("--data-inicial", help="Formato AAAA-MM-DD")
    parser.add_argument("--data-final", help="Formato AAAA-MM-DD")
    parser.add_argument("--config", default="config.yaml")
    argumentos = parser.parse_args()

    try:
        data_inicial, data_final = definir_periodo(
            argumentos.data_inicial, argumentos.data_final, date.today()
        )
    except ValueError as erro:
        parser.error(str(erro))

    with open(argumentos.config, encoding="utf-8") as arquivo:
        config = yaml.safe_load(arquivo)

    bucket = storage.Client().bucket(config["bucket_name"])

    def carregar_cliente():
        return GoogleAdsClient.load_from_storage(config["google_ads_config"])

    registro = executar(
        carregar_cliente,
        bucket,
        str(config["customer_id"]),
        data_inicial,
        data_final,
    )

    print(f"Execução: {registro['execution_id']}")
    print(f"Status: {registro['execution_status']}")
    print(f"Registros coletados: {registro['rows_collected']}")
    print(f"Arquivos gravados: {len(registro['files'])}")

    if registro["execution_status"] != "sucesso":
        print(f"Erro: {registro['error_message']}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
