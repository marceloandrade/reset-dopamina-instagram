"""
Integração com o Notion — ler e escrever no Calendário de Conteúdo.

Usa a API pública do Notion diretamente (sem SDK), versão 2026-03-11, que
já trabalha com "data sources" (o conceito novo que substituiu o antigo
"database" direto nas versões anteriores a 2025-09-03).

Variáveis de ambiente necessárias:
    NOTION_TOKEN            - token da integração interna do Notion
    NOTION_DATA_SOURCE_ID   - ID do data source do Calendário de Conteúdo
"""

import os
import datetime
import requests

NOTION_VERSION = "2026-03-11"
NOTION_API_BASE = "https://api.notion.com/v1"


class NotionError(Exception):
    pass


def _headers():
    token = os.environ["NOTION_TOKEN"]
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


def _data_source_id():
    return os.environ["NOTION_DATA_SOURCE_ID"]


def _request(method, path, json_body=None):
    url = f"{NOTION_API_BASE}/{path}"
    resp = requests.request(method, url, headers=_headers(), json=json_body, timeout=30)
    if resp.status_code >= 400:
        raise NotionError(f"Notion API {resp.status_code}: {resp.text[:500]}")
    return resp.json()


# ---------------------------------------------------------------------- #
# Leitura
# ---------------------------------------------------------------------- #

def _texto_rich_text(prop):
    """Extrai o texto puro de uma propriedade rich_text do Notion."""
    if not prop or not prop.get("rich_text"):
        return ""
    return "".join(t.get("plain_text", "") for t in prop["rich_text"])


def _pagina_para_post(pagina):
    """Converte uma página do Notion num dicionário simples e previsível."""
    props = pagina["properties"]
    titulo = "".join(t.get("plain_text", "") for t in props["Título"]["title"])
    data = (props.get("Data de publicação") or {}).get("date") or {}
    status = (props.get("Status") or {}).get("select") or {}
    formato = (props.get("Formato") or {}).get("select") or {}
    paleta = (props.get("Paleta") or {}).get("select") or {}

    return {
        "page_id": pagina["id"],
        "titulo": titulo,
        "data": data.get("start"),
        "status": status.get("name"),
        "formato": formato.get("name"),
        "paleta": paleta.get("name"),
        "legenda": _texto_rich_text(props.get("Legenda")),
        "urls_imagens": _texto_rich_text(props.get("URLs das imagens")),
        "arquivos_locais": _texto_rich_text(props.get("Arquivos locais")),
        "id_midia_publicada": _texto_rich_text(props.get("ID da mídia publicada")),
    }


def listar_aprovados_para_publicar(data=None):
    """
    Lista os posts com Status = Aprovado, com URL de imagem já preenchida,
    e Data de publicação <= data informada (padrão: hoje). É isso que o
    workflow agendado roda todo dia.
    """
    if data is None:
        data = datetime.date.today().isoformat()

    body = {
        "filter": {
            "and": [
                {"property": "Status", "select": {"equals": "Aprovado"}},
                {"property": "Data de publicação", "date": {"on_or_before": data}},
            ]
        }
    }
    resultado = _request("POST", f"data_sources/{_data_source_id()}/query", body)
    posts = [_pagina_para_post(p) for p in resultado.get("results", [])]
    # só publica o que já tem imagem hospedada
    return [p for p in posts if p["urls_imagens"].strip()]


def listar_proximos_dias(dias: int = 15) -> list:
    """
    Lista TODOS os posts (qualquer status) com data de publicação entre hoje
    e hoje + `dias`. Usado pela rotina de revisão quinzenal — diferente de
    listar_aprovados_para_publicar(), aqui queremos ver rascunhos também,
    pra saber o que ainda falta aprovar.
    """
    hoje = datetime.date.today()
    limite = (hoje + datetime.timedelta(days=dias)).isoformat()

    body = {
        "filter": {
            "and": [
                {"property": "Data de publicação", "date": {"on_or_after": hoje.isoformat()}},
                {"property": "Data de publicação", "date": {"on_or_before": limite}},
            ]
        },
        "sorts": [{"property": "Data de publicação", "direction": "ascending"}],
    }
    resultado = _request("POST", f"data_sources/{_data_source_id()}/query", body)
    return [_pagina_para_post(p) for p in resultado.get("results", [])]


def buscar_por_arquivo(nome_arquivo):
    """
    Encontra a página do calendário cujo campo 'Arquivos locais' contém o
    nome de arquivo informado (ex.: 'pub_01_2'). Usado pela rotina de
    upload pra saber a qual post cada imagem pertence.
    """
    body = {
        "filter": {
            "property": "Arquivos locais",
            "rich_text": {"contains": nome_arquivo},
        }
    }
    resultado = _request("POST", f"data_sources/{_data_source_id()}/query", body)
    paginas = resultado.get("results", [])
    if not paginas:
        return None
    return _pagina_para_post(paginas[0])


# ---------------------------------------------------------------------- #
# Escrita
# ---------------------------------------------------------------------- #

def _rich_text_prop(texto):
    return {"rich_text": [{"type": "text", "text": {"content": texto[:2000]}}]}


def atualizar_urls_imagens(page_id, urls_imagens):
    """Grava a lista de URLs públicas (já prontas) no post."""
    body = {"properties": {"URLs das imagens": _rich_text_prop(urls_imagens)}}
    _request("PATCH", f"pages/{page_id}", body)


def marcar_publicado(page_id, id_midia_publicada):
    """Marca o post como Publicado e grava o ID retornado pela Graph API."""
    body = {
        "properties": {
            "Status": {"select": {"name": "Publicado"}},
            "ID da mídia publicada": _rich_text_prop(str(id_midia_publicada)),
        }
    }
    _request("PATCH", f"pages/{page_id}", body)
