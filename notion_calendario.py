"""
Lê o banco de dados do Notion que serve como calendário editorial
e retorna os posts agendados para publicação (Data <= hoje, Status == Pendente).

Variáveis de ambiente necessárias:
    NOTION_TOKEN          — Integration token do Notion (secret_...)
    NOTION_DATABASE_ID    — ID do banco de dados do calendário

Estrutura esperada do banco de dados Notion:
    Data       — Date
    Tipo       — Select: Foto | Carrossel | Reels
    URLs       — Rich text (URLs separadas por vírgula ou quebra de linha)
    Legenda    — Rich text
    Status     — Select: Pendente | Publicado | Erro
    Media ID   — Rich text (preenchido após publicação)
    Erro       — Rich text (preenchido em caso de falha)
"""

import logging
import os
from datetime import date

from notion_client import Client

logger = logging.getLogger("notion_calendario")

STATUS_PENDENTE = "Pendente"
STATUS_PUBLICADO = "Publicado"
STATUS_ERRO = "Erro"


class NotionCalendario:

    def __init__(self, token=None, database_id=None):
        self.client = Client(auth=token or os.environ["NOTION_TOKEN"])
        self.database_id = database_id or os.environ["NOTION_DATABASE_ID"]

    def posts_para_publicar(self):
        """Retorna todos os posts com Data <= hoje e Status == Pendente."""
        hoje = date.today().isoformat()
        response = self.client.databases.query(
            database_id=self.database_id,
            filter={
                "and": [
                    {"property": "Data", "date": {"on_or_before": hoje}},
                    {"property": "Status", "select": {"equals": STATUS_PENDENTE}},
                ]
            },
            sorts=[{"property": "Data", "direction": "ascending"}],
        )
        return [self._parse_page(p) for p in response["results"]]

    def marcar_publicado(self, page_id, media_id):
        self.client.pages.update(
            page_id=page_id,
            properties={
                "Status": {"select": {"name": STATUS_PUBLICADO}},
                "Media ID": {"rich_text": [{"text": {"content": str(media_id)}}]},
            },
        )
        logger.info("Notion atualizado: página %s marcada como Publicado.", page_id)

    def marcar_erro(self, page_id, mensagem):
        self.client.pages.update(
            page_id=page_id,
            properties={
                "Status": {"select": {"name": STATUS_ERRO}},
                "Erro": {"rich_text": [{"text": {"content": mensagem[:2000]}}]},
            },
        )
        logger.warning("Notion atualizado: página %s marcada como Erro.", page_id)

    # ------------------------------------------------------------------ #
    # Helpers de parsing
    # ------------------------------------------------------------------ #

    def _parse_page(self, page):
        props = page["properties"]
        return {
            "page_id": page["id"],
            "data": self._get_date(props.get("Data")),
            "tipo": self._get_select(props.get("Tipo")),
            "urls": self._get_url_list(props.get("URLs")),
            "legenda": self._get_rich_text(props.get("Legenda")),
            "status": self._get_select(props.get("Status")),
        }

    def _get_date(self, prop):
        if not prop or not prop.get("date"):
            return None
        return prop["date"].get("start")

    def _get_select(self, prop):
        if not prop or not prop.get("select"):
            return None
        return prop["select"].get("name")

    def _get_rich_text(self, prop):
        if not prop or not prop.get("rich_text"):
            return ""
        return "".join(rt["plain_text"] for rt in prop["rich_text"])

    def _get_url_list(self, prop):
        texto = self._get_rich_text(prop)
        urls = []
        for item in texto.replace(",", "\n").splitlines():
            item = item.strip()
            if item:
                urls.append(item)
        return urls
