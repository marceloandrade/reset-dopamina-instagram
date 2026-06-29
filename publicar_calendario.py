#!/usr/bin/env python3
"""
Script de publicação automática — roda 1x por dia via GitHub Actions.

Busca no Calendário de Conteúdo (Notion) os posts com Status = Aprovado,
com data de publicação até hoje, e que já têm imagem(ns) hospedada(s).
Publica cada um no Instagram e marca como Publicado.

Uso:
    python publicar_calendario.py
"""

import logging
import sys

from dotenv import load_dotenv

import notion_calendario as notion
from instagram_api import InstagramClient, InstagramAPIError

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("publicar_calendario")


def publicar_post(client: InstagramClient, post: dict) -> str:
    urls = [u.strip() for u in post["urls_imagens"].splitlines() if u.strip()]
    formato = post["formato"]

    if formato == "Foto única":
        if len(urls) != 1:
            raise ValueError(f"Foto única deveria ter 1 URL, tem {len(urls)}")
        return client.publicar_foto(urls[0], caption=post["legenda"])

    if formato == "Carrossel":
        return client.publicar_carrossel(urls, caption=post["legenda"])

    if formato == "Reels":
        if len(urls) != 1:
            raise ValueError(f"Reels deveria ter 1 URL de vídeo, tem {len(urls)}")
        return client.publicar_reels(urls[0], caption=post["legenda"])

    raise ValueError(f"Formato desconhecido: {formato}")


def main():
    posts = notion.listar_aprovados_para_publicar()

    if not posts:
        print("Nenhum post aprovado e pronto pra publicar hoje.")
        return

    client = InstagramClient()
    publicados, falhas = 0, 0

    for post in posts:
        titulo = post["titulo"]
        try:
            logger.info("Publicando: %s (%s)", titulo, post["formato"])
            media_id = publicar_post(client, post)
            notion.marcar_publicado(post["page_id"], media_id)
            logger.info("✅ Publicado: %s -> ID %s", titulo, media_id)
            publicados += 1
        except (InstagramAPIError, ValueError) as exc:
            logger.error("❌ Falhou: %s -> %s", titulo, exc)
            falhas += 1
            # Não derruba o restante do lote — o post permanece "Aprovado"
            # e será tentado novamente na próxima execução.

    print(f"\nResumo: {publicados} publicado(s), {falhas} falha(s).")
    if falhas:
        sys.exit(1)


if __name__ == "__main__":
    main()
