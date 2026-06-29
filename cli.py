#!/usr/bin/env python3
"""
Interface de linha de comando do kit de automação do Instagram.

Tanto a Skill do Claude Code (uso sob demanda) quanto o workflow do
GitHub Actions (uso agendado) chamam este arquivo — é a porta de
entrada única para o núcleo (instagram_api.py).

Exemplos:
    python cli.py status
    python cli.py foto --image-url "https://.../foto.jpg" --caption "Legenda aqui"
    python cli.py carrossel --imagens "url1,url2,url3" --caption "Legenda"
    python cli.py reels --video-url "https://.../video.mp4" --caption "Legenda"
    python cli.py apagar --media-id 18108923192475148
    python cli.py listar --limite 5
    python cli.py renovar-token
"""

import argparse
import json
import logging
import os
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

from instagram_api import InstagramClient, InstagramAPIError

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("cli")


def construir_cliente():
    try:
        return InstagramClient()
    except KeyError as exc:
        print(f"❌ Variável de ambiente faltando: {exc}. Confira o seu .env (veja .env.example).")
        sys.exit(1)


def cmd_status(args, client):
    info = client.info_conta()
    print(json.dumps(info, indent=2, ensure_ascii=False))


def cmd_foto(args, client):
    media_id = client.publicar_foto(args.image_url, caption=args.caption or "")
    print(f"✅ Foto publicada! ID: {media_id}")


def cmd_carrossel(args, client):
    urls = [u.strip() for u in args.imagens.split(",") if u.strip()]
    media_id = client.publicar_carrossel(urls, caption=args.caption or "")
    print(f"✅ Carrossel publicado! ID: {media_id}")


def cmd_reels(args, client):
    media_id = client.publicar_reels(args.video_url, caption=args.caption or "")
    print(f"✅ Reels publicado! ID: {media_id}")


def cmd_apagar(args, client):
    confirmar = args.confirmar or os.environ.get("IG_CONFIRMAR_DELETE") == "1"
    if not confirmar:
        print(
            "⚠️  Apagar é irreversível. Rode de novo com --confirmar para executar de fato.\n"
            f"   (media-id: {args.media_id})"
        )
        sys.exit(1)
    client.apagar_midia(args.media_id)
    print(f"🗑️  Mídia {args.media_id} apagada.")


def cmd_listar(args, client):
    midias = client.listar_midias(limite=args.limite)
    print(json.dumps(midias, indent=2, ensure_ascii=False))


def cmd_renovar_token(args, client):
    novo_token = client.renovar_token_longa_duracao()
    print("✅ Token renovado com sucesso.")
    print("Atualize o IG_ACCESS_TOKEN no seu .env (local) e/ou no Secret do GitHub Actions com:")
    print(novo_token)


def main():
    parser = argparse.ArgumentParser(description="Kit de automação do Instagram — núcleo Python")
    sub = parser.add_subparsers(dest="comando", required=True)

    sub.add_parser("status", help="Mostra dados básicos da conta (testa se o token está ok)")

    p_foto = sub.add_parser("foto", help="Publica uma foto única")
    p_foto.add_argument("--image-url", required=True)
    p_foto.add_argument("--caption", default="")

    p_carrossel = sub.add_parser("carrossel", help="Publica um carrossel (2 a 10 imagens)")
    p_carrossel.add_argument("--imagens", required=True, help="URLs separadas por vírgula")
    p_carrossel.add_argument("--caption", default="")

    p_reels = sub.add_parser("reels", help="Publica um Reels")
    p_reels.add_argument("--video-url", required=True)
    p_reels.add_argument("--caption", default="")

    p_apagar = sub.add_parser("apagar", help="Apaga uma mídia (irreversível)")
    p_apagar.add_argument("--media-id", required=True)
    p_apagar.add_argument("--confirmar", action="store_true", help="Confirma a exclusão de fato")

    p_listar = sub.add_parser("listar", help="Lista as últimas mídias publicadas")
    p_listar.add_argument("--limite", type=int, default=10)

    sub.add_parser("renovar-token", help="Troca o token atual por um novo de 60 dias")

    args = parser.parse_args()
    client = construir_cliente()

    comandos = {
        "status": cmd_status,
        "foto": cmd_foto,
        "carrossel": cmd_carrossel,
        "reels": cmd_reels,
        "apagar": cmd_apagar,
        "listar": cmd_listar,
        "renovar-token": cmd_renovar_token,
    }

    try:
        comandos[args.comando](args, client)
    except InstagramAPIError as exc:
        print(f"❌ Erro da API do Instagram: {exc}")
        if exc.code:
            print(f"   código: {exc.code} / subcódigo: {exc.subcode}")
        sys.exit(1)
    except ValueError as exc:
        print(f"❌ Entrada inválida: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
