"""Autoriza o acesso ao Google Ads e cria o arquivo google-ads.yaml.

Uso:
    python src/gerar_refresh_token.py --client-secret CAMINHO_DO_JSON

O navegador será aberto: entre com a conta que tem acesso ao Google Ads.
"""

import argparse
import sys
from pathlib import Path

import yaml
from google_auth_oauthlib.flow import InstalledAppFlow

ESCOPO_GOOGLE_ADS = "https://www.googleapis.com/auth/adwords"


def montar_configuracao(credenciais, login_customer_id):
    """Monta o conteúdo do google-ads.yaml."""
    configuracao = {
        "client_id": credenciais.client_id,
        "client_secret": credenciais.client_secret,
        "refresh_token": credenciais.refresh_token,
        "use_proto_plus": True,
    }
    if login_customer_id:
        configuracao["login_customer_id"] = login_customer_id
    return configuracao


def main():
    parser = argparse.ArgumentParser(description="Gera o google-ads.yaml.")
    parser.add_argument("--client-secret", required=True)
    parser.add_argument("--login-customer-id", help="Somente se usar MCC")
    parser.add_argument("--saida", default="google-ads.yaml")
    argumentos = parser.parse_args()

    if Path(argumentos.saida).exists():
        print(f"{argumentos.saida} já existe. Apague ou renomeie o arquivo.")
        return 1

    fluxo = InstalledAppFlow.from_client_secrets_file(
        argumentos.client_secret, scopes=[ESCOPO_GOOGLE_ADS]
    )
    credenciais = fluxo.run_local_server(
        port=0, access_type="offline", prompt="select_account consent"
    )

    configuracao = montar_configuracao(credenciais, argumentos.login_customer_id)
    with open(argumentos.saida, "w", encoding="utf-8") as arquivo:
        yaml.safe_dump(configuracao, arquivo)

    print(f"Arquivo {argumentos.saida} criado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
