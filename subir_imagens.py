#!/usr/bin/env python3
"""
Rotina de upload de imagens — a peça que liga "imagem pronta no computador"
a "URL pública que a API do Instagram consegue buscar".

Fluxo:
    1. Olha os arquivos dentro de PASTA_NOVAS (ex.: ~/publicacoes/novas)
    2. Pra cada arquivo, descobre a qual post do Calendário ele pertence
       (casando o nome do arquivo, sem extensão, com o campo "Arquivos
       locais" de cada linha do Notion)
    3. Só finaliza um post quando TODOS os arquivos esperados dele já
       estão presentes na pasta /novas nesta execução (evita estado
       parcial/inconsistente)
    4. Sobe os arquivos do post pro repositório GitHub (API de Conteúdo,
       sem precisar de git instalado)
    5. Atualiza o campo "URLs das imagens" do post no Notion
    6. Move os arquivos processados de /novas pra /enviadas

Uso:
    python subir_imagens.py

Variáveis de ambiente necessárias:
    GITHUB_TOKEN        - Personal Access Token com permissão de escrita no repo
    GITHUB_REPO         - "usuario/nome-do-repo"
    GITHUB_BRANCH       - branch de destino (padrão: main)
    NOTION_TOKEN        - token da integração do Notion
    NOTION_DATA_SOURCE_ID - ID do data source do Calendário de Conteúdo
    PASTA_NOVAS         - caminho da pasta de imagens novas (padrão: ./publicacoes/novas)
    PASTA_ENVIADAS      - caminho da pasta de imagens já enviadas (padrão: ./publicacoes/enviadas)
"""

import base64
import logging
import os
import shutil
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

import notion_calendario as notion

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("subir_imagens")

GITHUB_API_BASE = "https://api.github.com"
EXTENSOES_IMAGEM = {".png", ".jpg", ".jpeg", ".webp", ".mp4", ".mov"}


def _github_headers():
    token = os.environ["GITHUB_TOKEN"]
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }


def _subir_arquivo_github(caminho_local: Path, nome_no_repo: str) -> str:
    """Sobe 1 arquivo pro GitHub via API de Conteúdo. Retorna a URL pública raw."""
    repo = os.environ["GITHUB_REPO"]
    branch = os.environ.get("GITHUB_BRANCH", "main")

    conteudo_b64 = base64.b64encode(caminho_local.read_bytes()).decode("utf-8")
    url = f"{GITHUB_API_BASE}/repos/{repo}/contents/imagens/{nome_no_repo}"

    # Se o arquivo já existir no repo, precisa do "sha" atual pra poder sobrescrever
    sha_existente = None
    resp_get = requests.get(url, headers=_github_headers(), params={"ref": branch}, timeout=30)
    if resp_get.status_code == 200:
        sha_existente = resp_get.json().get("sha")

    body = {
        "message": f"Adiciona imagem {nome_no_repo}",
        "content": conteudo_b64,
        "branch": branch,
    }
    if sha_existente:
        body["sha"] = sha_existente

    resp = requests.put(url, headers=_github_headers(), json=body, timeout=60)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Falha ao subir {nome_no_repo} pro GitHub: {resp.status_code} {resp.text[:300]}")

    dados = resp.json()
    download_url = dados.get("content", {}).get("download_url")
    if download_url:
        return download_url
    # fallback, monta a URL raw manualmente
    return f"https://raw.githubusercontent.com/{repo}/{branch}/imagens/{nome_no_repo}"


def _agrupar_por_post(arquivos: list[Path]) -> dict:
    """
    Casa cada arquivo local com a página correspondente do Notion.
    Retorna {page_id: {"post": dict, "arquivos": [Path, ...]}}.
    """
    grupos: dict = {}
    nao_identificados = []

    for arquivo in arquivos:
        nome_sem_ext = arquivo.stem
        post = notion.buscar_por_arquivo(nome_sem_ext)
        if post is None:
            nao_identificados.append(arquivo.name)
            continue

        page_id = post["page_id"]
        grupos.setdefault(page_id, {"post": post, "arquivos": []})
        grupos[page_id]["arquivos"].append(arquivo)

    if nao_identificados:
        logger.warning(
            "Não encontrei no Calendário a quem pertencem: %s (deixados em /novas)",
            ", ".join(nao_identificados),
        )

    return grupos


def _completo(grupo: dict) -> bool:
    """Verifica se todos os arquivos esperados desse post já estão na pasta /novas."""
    esperados = {n.strip() for n in grupo["post"]["arquivos_locais"].split(",") if n.strip()}
    presentes = {a.stem for a in grupo["arquivos"]}
    return esperados.issubset(presentes) and bool(esperados)


def _ordenar_conforme_esperado(grupo: dict) -> list[Path]:
    """Ordena os arquivos do grupo na mesma ordem do campo 'Arquivos locais'."""
    ordem = [n.strip() for n in grupo["post"]["arquivos_locais"].split(",") if n.strip()]
    por_nome = {a.stem: a for a in grupo["arquivos"]}
    return [por_nome[nome] for nome in ordem if nome in por_nome]


def main():
    pasta_novas = Path(os.environ.get("PASTA_NOVAS", "./publicacoes/novas")).expanduser()
    pasta_enviadas = Path(os.environ.get("PASTA_ENVIADAS", "./publicacoes/enviadas")).expanduser()
    pasta_enviadas.mkdir(parents=True, exist_ok=True)

    if not pasta_novas.exists():
        print(f"❌ Pasta não encontrada: {pasta_novas}")
        sys.exit(1)

    arquivos = [
        f for f in pasta_novas.iterdir()
        if f.is_file() and f.suffix.lower() in EXTENSOES_IMAGEM
    ]
    if not arquivos:
        print("Nenhuma imagem nova encontrada em", pasta_novas)
        return

    grupos = _agrupar_por_post(arquivos)
    posts_finalizados = 0

    for page_id, grupo in grupos.items():
        titulo = grupo["post"]["titulo"]

        if not _completo(grupo):
            esperados = grupo["post"]["arquivos_locais"]
            logger.info("Post '%s' ainda incompleto (esperado: %s) — aguardando.", titulo, esperados)
            continue

        arquivos_ordenados = _ordenar_conforme_esperado(grupo)
        logger.info("Subindo %d arquivo(s) do post '%s'...", len(arquivos_ordenados), titulo)

        urls = []
        for arquivo in arquivos_ordenados:
            url = _subir_arquivo_github(arquivo, arquivo.name)
            urls.append(url)
            logger.info("  ✓ %s -> %s", arquivo.name, url)

        notion.atualizar_urls_imagens(page_id, "\n".join(urls))
        logger.info("  ✓ Notion atualizado com %d URL(s) para '%s'", len(urls), titulo)

        for arquivo in arquivos_ordenados:
            shutil.move(str(arquivo), str(pasta_enviadas / arquivo.name))
        logger.info("  ✓ Arquivos movidos para %s", pasta_enviadas)

        posts_finalizados += 1

    print(f"\n✅ {posts_finalizados} post(s) finalizado(s) e prontos pra publicação.")


if __name__ == "__main__":
    main()
