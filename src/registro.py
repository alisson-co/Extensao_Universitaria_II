"""Registro das execuções do processo de coleta."""

import json
import uuid
from datetime import datetime, timezone

PREFIXO_REGISTROS = "control/executions"


def criar_execution_id(momento):
    """Cria um identificador único que começa pela data e hora da execução."""
    return f"{momento:%Y%m%dT%H%M%SZ}-{uuid.uuid4().hex[:8]}"


def iniciar_registro(data_inicial, data_final):
    """Cria o registro de uma nova execução."""
    momento = datetime.now(timezone.utc)
    return {
        "execution_id": criar_execution_id(momento),
        "execution_datetime": momento.isoformat(timespec="seconds"),
        "execution_status": "em_andamento",
        "error_message": None,
        "period_start": data_inicial,
        "period_end": data_final,
        "rows_collected": 0,
        "files": [],
    }


def caminho_do_registro(execution_id):
    """Monta o caminho do registro dentro do bucket."""
    return f"{PREFIXO_REGISTROS}/{execution_id}.json"


def salvar_registro(bucket, registro):
    """Grava o registro da execução no bucket."""
    blob = bucket.blob(caminho_do_registro(registro["execution_id"]))
    blob.upload_from_string(
        json.dumps(registro, ensure_ascii=False, indent=2),
        content_type="application/json",
        checksum="crc32c",
    )


def ler_registro(bucket, execution_id):
    """Lê o registro de uma execução. Devolve None se ele não existir."""
    blob = bucket.blob(caminho_do_registro(execution_id))
    if not blob.exists():
        return None
    return json.loads(blob.download_as_text())
