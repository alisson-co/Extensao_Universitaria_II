"""T01: verifica a autenticação e o acesso à Google Ads API.

Uso: python tests/test_access.py
"""

from google.ads.googleads.client import GoogleAdsClient


def main():
    client = GoogleAdsClient.load_from_storage("google-ads.yaml")
    customer_service = client.get_service("CustomerService")
    response = customer_service.list_accessible_customers()

    print("Autenticação e acesso realizados com sucesso.")
    print(f"Quantidade de contas acessíveis: {len(response.resource_names)}")


if __name__ == "__main__":
    main()
