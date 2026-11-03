"""Testes locais do fluxo, sem acessar o Google Ads nem o Cloud Storage.

Uso: python -m unittest discover -s tests -p "test_fluxo.py" -v
"""

import json
import sys
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from coleta import coletar_campanhas, montar_consulta  # noqa: E402
from main import definir_periodo, executar  # noqa: E402
from validacao import validar_execucao  # noqa: E402


def criar_linha(campanha, data, custo_micros):
    return SimpleNamespace(
        customer=SimpleNamespace(id=1234567890),
        campaign=SimpleNamespace(id=campanha, name=f"Campanha {campanha}"),
        segments=SimpleNamespace(date=data),
        metrics=SimpleNamespace(
            impressions=100, clicks=7, cost_micros=custo_micros
        ),
    )


class ServicoFalso:
    def __init__(self, linhas=None, erro=None):
        self.linhas = linhas or []
        self.erro = erro
        self.chamada = None

    def search_stream(self, customer_id, query):
        self.chamada = {"customer_id": customer_id, "query": query}
        if self.erro:
            raise self.erro
        return [SimpleNamespace(results=self.linhas)]


class ClienteFalso:
    def __init__(self, servico):
        self.servico = servico

    def get_service(self, nome):
        return self.servico


class BlobFalso:
    def __init__(self, bucket, nome):
        self.bucket = bucket
        self.nome = nome

    def upload_from_string(self, conteudo, content_type, checksum):
        if self.bucket.falhar_dados and self.nome.startswith("raw/"):
            raise OSError("Bucket indisponível")
        self.bucket.arquivos[self.nome] = conteudo

    def exists(self):
        return self.nome in self.bucket.arquivos

    def download_as_text(self):
        return self.bucket.arquivos[self.nome]


class BucketFalso:
    def __init__(self, falhar_dados=False):
        self.arquivos = {}
        self.falhar_dados = falhar_dados

    def blob(self, nome):
        return BlobFalso(self, nome)


class TestFluxo(unittest.TestCase):
    def setUp(self):
        self.linhas = [
            criar_linha(1, "2026-10-01", 1_500_000),
            criar_linha(2, "2026-10-01", 250_000),
            criar_linha(1, "2026-10-02", 0),
        ]

    def executar_fluxo(self, servico, bucket):
        return executar(
            lambda: ClienteFalso(servico),
            bucket,
            "1234567890",
            "2026-10-01",
            "2026-10-02",
        )

    def test_t02_coleta_converte_os_campos(self):
        servico = ServicoFalso(self.linhas)
        registros = coletar_campanhas(
            ClienteFalso(servico), "1234567890", "2026-10-01", "2026-10-02"
        )

        self.assertEqual(len(registros), 3)
        self.assertEqual(registros[0]["account_id"], "1234567890")
        self.assertEqual(registros[0]["campaign_id"], "1")
        self.assertEqual(registros[0]["cost"], 1.5)
        self.assertIn(
            "BETWEEN '2026-10-01' AND '2026-10-02'", servico.chamada["query"]
        )

    def test_consulta_contem_os_campos_definidos(self):
        consulta = montar_consulta("2026-10-01", "2026-10-02")
        for campo in [
            "customer.id",
            "campaign.id",
            "campaign.name",
            "segments.date",
            "metrics.impressions",
            "metrics.clicks",
            "metrics.cost_micros",
        ]:
            self.assertIn(campo, consulta)

    def test_t03_armazena_um_arquivo_por_data(self):
        bucket = BucketFalso()
        registro = self.executar_fluxo(ServicoFalso(self.linhas), bucket)

        caminho = registro["files"][0]["path"]
        self.assertEqual(len(registro["files"]), 2)
        self.assertTrue(
            caminho.startswith(
                "raw/google_ads/campaign_metrics/date=2026-10-01/execution_id="
            )
        )
        primeira_linha = json.loads(bucket.arquivos[caminho].splitlines()[0])
        self.assertEqual(primeira_linha["execution_id"], registro["execution_id"])

    def test_t04_registra_execucao_com_sucesso(self):
        bucket = BucketFalso()
        registro = self.executar_fluxo(ServicoFalso(self.linhas), bucket)

        salvo = json.loads(
            bucket.arquivos[f"control/executions/{registro['execution_id']}.json"]
        )
        self.assertEqual(salvo["execution_status"], "sucesso")
        self.assertEqual(salvo["rows_collected"], 3)
        self.assertIsNone(salvo["error_message"])
        self.assertTrue(salvo["execution_datetime"])

    def test_t05_registra_falha_na_coleta(self):
        bucket = BucketFalso()
        servico = ServicoFalso(erro=RuntimeError("Falha na API"))
        registro = self.executar_fluxo(servico, bucket)

        self.assertEqual(registro["execution_status"], "falha")
        self.assertIn("Falha na API", registro["error_message"])
        self.assertEqual(len(bucket.arquivos), 1)

    def test_t05_registra_falha_na_autenticacao(self):
        def carregar_cliente():
            raise PermissionError("Credencial inválida")

        bucket = BucketFalso()
        registro = executar(
            carregar_cliente, bucket, "1234567890", "2026-10-01", "2026-10-02"
        )

        self.assertEqual(registro["execution_status"], "falha")
        self.assertIn("Credencial inválida", registro["error_message"])

    def test_t05_registra_falha_no_armazenamento(self):
        bucket = BucketFalso(falhar_dados=True)
        registro = self.executar_fluxo(ServicoFalso(self.linhas), bucket)

        self.assertEqual(registro["execution_status"], "falha")
        self.assertIn("Bucket indisponível", registro["error_message"])

    def test_periodo_sem_dados_termina_com_sucesso(self):
        bucket = BucketFalso()
        registro = self.executar_fluxo(ServicoFalso([]), bucket)

        self.assertEqual(registro["execution_status"], "sucesso")
        self.assertEqual(registro["files"], [])

    def test_t06_fluxo_completo_e_validado(self):
        bucket = BucketFalso()
        registro = self.executar_fluxo(ServicoFalso(self.linhas), bucket)

        self.assertEqual(validar_execucao(bucket, registro["execution_id"]), [])

    def test_validacao_detecta_arquivo_ausente(self):
        bucket = BucketFalso()
        registro = self.executar_fluxo(ServicoFalso(self.linhas), bucket)
        del bucket.arquivos[registro["files"][0]["path"]]

        self.assertTrue(validar_execucao(bucket, registro["execution_id"]))

    def test_periodo_padrao_e_o_dia_anterior(self):
        self.assertEqual(
            definir_periodo(None, None, date(2026, 11, 3)),
            ("2026-11-02", "2026-11-02"),
        )

    def test_periodo_rejeita_data_invertida(self):
        with self.assertRaises(ValueError):
            definir_periodo("2026-10-02", "2026-10-01", date(2026, 11, 3))

    def test_periodo_exige_as_duas_datas(self):
        with self.assertRaises(ValueError):
            definir_periodo("2026-10-02", None, date(2026, 11, 3))


if __name__ == "__main__":
    unittest.main()
