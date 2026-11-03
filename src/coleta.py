"""Coleta dos dados de campanhas na Google Ads API."""

CAMPOS_DA_CONSULTA = """
    SELECT
        customer.id,
        campaign.id,
        campaign.name,
        segments.date,
        metrics.impressions,
        metrics.clicks,
        metrics.cost_micros
    FROM campaign
    WHERE segments.date BETWEEN '{data_inicial}' AND '{data_final}'
    ORDER BY segments.date, campaign.id
"""


def montar_consulta(data_inicial, data_final):
    """Monta a consulta GAQL do período informado (datas em AAAA-MM-DD)."""
    return CAMPOS_DA_CONSULTA.format(
        data_inicial=data_inicial,
        data_final=data_final,
    )


def converter_linha(linha):
    """Converte uma linha da API para os campos do dicionário de dados."""
    return {
        "account_id": str(linha.customer.id),
        "campaign_id": str(linha.campaign.id),
        "campaign_name": linha.campaign.name,
        "date": linha.segments.date,
        "impressions": linha.metrics.impressions,
        "clicks": linha.metrics.clicks,
        # A API informa o custo em micros: 1.000.000 equivale a 1 unidade da moeda.
        "cost": linha.metrics.cost_micros / 1_000_000,
    }


def coletar_campanhas(cliente, customer_id, data_inicial, data_final):
    """Consulta a Google Ads API e devolve a lista de registros coletados."""
    servico = cliente.get_service("GoogleAdsService")
    consulta = montar_consulta(data_inicial, data_final)
    resposta = servico.search_stream(customer_id=customer_id, query=consulta)

    registros = []
    for lote in resposta:
        for linha in lote.results:
            registros.append(converter_linha(linha))
    return registros
