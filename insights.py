"""
Camada de insights (métricas de crescimento) sobre a Instagram Graph API.

Decide QUAIS métricas pedir e como reagir se a Meta rejeitar alguma —
o instagram_api.py só repassa o que for pedido. Isso porque a Meta muda
esse conjunto com frequência (a última grande mudança foi em abr/2025,
quando "impressions" e "profile_views" em série temporal foram
descontinuadas em favor de "views"). Se um dia uma métrica daqui parar
de funcionar, o log vai dizer exatamente qual e com que erro — não
precisa adivinhar.

Não persiste nada sozinho. Quem chama decide se quer guardar histórico
(o relatorio_semanal.py guarda o de seguidores no próprio repositório).
"""

import logging
from datetime import datetime, timedelta, timezone

from instagram_api import InstagramClient, InstagramAPIError

logger = logging.getLogger("insights")

# Métrica de nível de conta que pedimos por padrão. Mantida enxuta de
# propósito: "follower_count" via /insights exige >100 seguidores e tem
# mais restrições, e não precisamos dela pra calcular crescimento --
# isso é feito comparando o followers_count atual (info_conta) com o
# histórico salvo pelo relatorio_semanal.py.
METRICAS_CONTA_PADRAO = ["reach"]

# Métricas por mídia. "views" substitui "impressions"/"plays" desde a v22.
METRICAS_MIDIA_PADRAO = ["reach", "views", "likes", "comments", "saved", "shares"]
METRICAS_MIDIA_FALLBACK = ["reach", "likes", "comments"]


def _janela_unix(dias):
    agora = datetime.now(timezone.utc)
    inicio = agora - timedelta(days=dias)
    return int(inicio.timestamp()), int(agora.timestamp())


def resumo_conta(client: InstagramClient, dias=7):
    """
    Retorna:
        {
          "username": str,
          "seguidores_atual": int,
          "media_count": int,
          "reach_periodo": int | None,   # soma do reach diário na janela; None se a métrica falhar
        }
    """
    info = client.info_conta()
    resultado = {
        "username": info.get("username"),
        "seguidores_atual": info.get("followers_count"),
        "media_count": info.get("media_count"),
        "reach_periodo": None,
    }

    since, until = _janela_unix(dias)
    try:
        dados = client.insights_conta(METRICAS_CONTA_PADRAO, period="day", since=since, until=until)
        for metrica in dados.get("data", []):
            if metrica.get("name") == "reach":
                resultado["reach_periodo"] = sum(v.get("value", 0) for v in metrica.get("values", []))
    except InstagramAPIError as exc:
        logger.warning("Não consegui buscar reach da conta (%s). Seguindo só com followers_count.", exc)

    return resultado


def posts_recentes_com_insights(client: InstagramClient, dias=7, limite=20):
    """
    Lista mídias publicadas nos últimos `dias` dias (listar_midias já vem
    ordenado do mais recente pro mais antigo), cada uma com as métricas
    que a API aceitar pra aquele tipo de mídia.
    """
    midias = client.listar_midias(limite=limite)
    corte = datetime.now(timezone.utc) - timedelta(days=dias)

    recentes = []
    for m in midias:
        try:
            ts = datetime.fromisoformat(m["timestamp"].replace("Z", "+00:00"))
        except (KeyError, ValueError):
            continue
        if ts < corte:
            break
        recentes.append(m)

    for post in recentes:
        post["insights"] = _insights_midia_com_fallback(client, post["id"])

    return recentes


def _insights_midia_com_fallback(client: InstagramClient, media_id):
    try:
        dados = client.insights_midia(media_id, METRICAS_MIDIA_PADRAO)
    except InstagramAPIError as exc:
        logger.warning(
            "Conjunto completo de métricas falhou pra mídia %s (%s). Tentando conjunto reduzido: %s.",
            media_id, exc, METRICAS_MIDIA_FALLBACK,
        )
        try:
            dados = client.insights_midia(media_id, METRICAS_MIDIA_FALLBACK)
        except InstagramAPIError as exc2:
            logger.warning("Conjunto reduzido também falhou pra mídia %s (%s). Sem métricas pra esse post.", media_id, exc2)
            return {}

    return {item["name"]: item.get("values", [{}])[0].get("value", 0) for item in dados.get("data", [])}
