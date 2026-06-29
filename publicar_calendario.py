"""
Orquestra a publicação agendada: lê o Notion, sobe imagens se necessário
e publica no Instagram — atualizando o status no Notion em seguida.

Uso:
    python publicar_calendario.py              # publica tudo pendente até hoje
    python publicar_calendario.py --dry-run    # lista sem publicar
    python publicar_calendario.py --sem-upload # usa URLs do Notion diretamente
"""

import argparse
import logging
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("publicar_calendario")


def publicar_post(client, post, fazer_upload=True):
    from subir_imagens import subir_lista
    from instagram_api import InstagramAPIError

    tipo = (post["tipo"] or "").lower()
    urls = post["urls"]

    if not urls:
        raise ValueError("Post sem URLs definidas na coluna 'URLs' do Notion.")

    if fazer_upload:
        urls = subir_lista(urls)

    if tipo == "foto":
        return client.publicar_foto(urls[0], caption=post["legenda"])
    elif tipo == "carrossel":
        return client.publicar_carrossel(urls, caption=post["legenda"])
    elif tipo == "reels":
        return client.publicar_reels(urls[0], caption=post["legenda"])
    else:
        raise ValueError(
            f"Tipo '{post['tipo']}' desconhecido. Use Foto, Carrossel ou Reels no Notion."
        )


def main():
    parser = argparse.ArgumentParser(description="Publica posts agendados do Notion no Instagram")
    parser.add_argument("--dry-run", action="store_true", help="Lista os posts sem publicar")
    parser.add_argument(
        "--sem-upload",
        action="store_true",
        help="Usa as URLs do Notion diretamente, sem subir ao Cloudinary",
    )
    args = parser.parse_args()

    from notion_calendario import NotionCalendario
    from instagram_api import InstagramClient, InstagramAPIError

    calendario = NotionCalendario()
    posts = calendario.posts_para_publicar()

    if not posts:
        logger.info("Nenhum post pendente para publicar hoje.")
        return

    logger.info("%d post(s) encontrado(s) para publicar.", len(posts))

    if args.dry_run:
        for p in posts:
            legenda_resumida = (p["legenda"] or "")[:60]
            print(f"[DRY-RUN] {p['data']} | {p['tipo']} | {len(p['urls'])} URL(s) | {legenda_resumida}...")
        return

    client = InstagramClient()
    publicados = 0
    erros = 0

    for post in posts:
        page_id = post["page_id"]
        logger.info(
            "Publicando: %s | %s | %s",
            post["data"],
            post["tipo"],
            (post["legenda"] or "")[:50],
        )
        try:
            media_id = publicar_post(client, post, fazer_upload=not args.sem_upload)
            calendario.marcar_publicado(page_id, media_id)
            logger.info("Publicado com sucesso. Media ID: %s", media_id)
            publicados += 1
        except (InstagramAPIError, ValueError, FileNotFoundError) as exc:
            logger.error("Falha ao publicar página %s: %s", page_id, exc)
            calendario.marcar_erro(page_id, str(exc))
            erros += 1

    logger.info("Resultado final: %d publicado(s), %d erro(s).", publicados, erros)
    if erros:
        sys.exit(1)


if __name__ == "__main__":
    main()
