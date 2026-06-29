"""
Faz upload de imagens locais para o Cloudinary e retorna URLs públicas.
Necessário porque a Instagram Graph API exige URLs acessíveis publicamente.

Variáveis de ambiente (uma das duas formas):
    CLOUDINARY_URL                     — URL completa (cloudinary://key:secret@cloud)
    ou
    CLOUDINARY_CLOUD_NAME + CLOUDINARY_API_KEY + CLOUDINARY_API_SECRET

Se a entrada já for uma URL (http/https), é retornada diretamente sem upload.
"""

import logging
import os
from pathlib import Path

import cloudinary
import cloudinary.uploader

logger = logging.getLogger("subir_imagens")

_cloudinary_configurado = False


def _configurar():
    global _cloudinary_configurado
    if _cloudinary_configurado:
        return
    url = os.environ.get("CLOUDINARY_URL")
    if url:
        cloudinary.config(cloudinary_url=url)
    else:
        cloudinary.config(
            cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
            api_key=os.environ["CLOUDINARY_API_KEY"],
            api_secret=os.environ["CLOUDINARY_API_SECRET"],
        )
    _cloudinary_configurado = True


def subir_imagem(caminho_ou_url: str, pasta: str = "reset-dopamina") -> str:
    """
    Aceita caminho local ou URL.
    URLs são devolvidas sem alteração; arquivos locais são enviados ao Cloudinary.
    """
    if caminho_ou_url.startswith(("http://", "https://")):
        return caminho_ou_url

    _configurar()
    path = Path(caminho_ou_url)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {caminho_ou_url}")

    logger.info("Enviando %s para o Cloudinary...", path.name)
    result = cloudinary.uploader.upload(
        str(path),
        folder=pasta,
        resource_type="image",
    )
    url = result["secure_url"]
    logger.info("Upload concluído: %s", url)
    return url


def subir_lista(caminhos_ou_urls: list, pasta: str = "reset-dopamina") -> list:
    """Processa uma lista de caminhos/URLs e devolve lista de URLs públicas."""
    return [subir_imagem(item, pasta=pasta) for item in caminhos_ou_urls]
