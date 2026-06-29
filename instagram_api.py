"""
Núcleo de integração com a Instagram Graph API.

Genérico e configurável só por variáveis de ambiente — não depende de
nenhuma conta específica. É a peça que tanto a Skill do Claude Code
(uso sob demanda) quanto o workflow agendado (GitHub Actions) chamam.

Replicar para outra conta/cliente = trocar o .env, nunca este arquivo.
"""

import os
import time
import logging

import requests

logger = logging.getLogger("instagram_api")

GRAPH_API_VERSION = os.environ.get("GRAPH_API_VERSION", "v25.0")
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"


class InstagramAPIError(Exception):
    """Erro retornado pela Graph API (ou de comunicação com ela)."""

    def __init__(self, message, code=None, subcode=None, raw=None):
        super().__init__(message)
        self.code = code
        self.subcode = subcode
        self.raw = raw


class InstagramClient:
    """
    Cliente da Instagram Graph API.

    Pode receber as credenciais direto, mas o normal é deixar tudo vir
    das variáveis de ambiente (carregadas de um .env):

        IG_USER_ID        - ID da conta do Instagram Business
        IG_ACCESS_TOKEN    - token de longa duração (60 dias)
        META_APP_ID        - (opcional, só necessário para renovar token)
        META_APP_SECRET    - (opcional, só necessário para renovar token)
    """

    def __init__(self, access_token=None, ig_user_id=None, app_id=None, app_secret=None):
        self.access_token = access_token or os.environ["IG_ACCESS_TOKEN"]
        self.ig_user_id = ig_user_id or os.environ["IG_USER_ID"]
        self.app_id = app_id or os.environ.get("META_APP_ID")
        self.app_secret = app_secret or os.environ.get("META_APP_SECRET")

    # ------------------------------------------------------------------ #
    # Infraestrutura interna
    # ------------------------------------------------------------------ #

    def _request(self, method, path, params=None, retries=2):
        url = f"{GRAPH_API_BASE}/{path}"
        params = dict(params or {})
        params["access_token"] = self.access_token

        last_error = None
        for attempt in range(retries + 1):
            try:
                resp = requests.request(method, url, params=params, timeout=30)
            except requests.RequestException as exc:
                last_error = exc
                time.sleep(2 ** attempt)
                continue

            try:
                data = resp.json()
            except ValueError:
                raise InstagramAPIError(
                    f"Resposta inesperada (HTTP {resp.status_code}): {resp.text[:300]}"
                )

            if "error" in data:
                err = data["error"]
                # Rate limit (code 4 / 17 / 32) -> espera e tenta de novo
                if err.get("code") in (4, 17, 32) and attempt < retries:
                    time.sleep(2 ** attempt * 5)
                    continue
                raise InstagramAPIError(
                    err.get("message", "Erro desconhecido da Graph API"),
                    code=err.get("code"),
                    subcode=err.get("error_subcode"),
                    raw=data,
                )
            return data

        raise InstagramAPIError(f"Falha de conexão após {retries + 1} tentativas: {last_error}")

    def _esperar_processamento(self, creation_id, timeout=180, intervalo=5):
        """Espera vídeo/Reels terminar de processar antes de publicar."""
        elapsed = 0
        while elapsed < timeout:
            status = self._request("GET", creation_id, {"fields": "status_code"})
            code = status.get("status_code")
            if code == "FINISHED":
                return True
            if code == "ERROR":
                raise InstagramAPIError("Processamento do vídeo falhou no servidor da Meta.", raw=status)
            time.sleep(intervalo)
            elapsed += intervalo
        raise InstagramAPIError("Tempo esgotado esperando o processamento do vídeo/Reels.")

    # ------------------------------------------------------------------ #
    # Publicação
    # ------------------------------------------------------------------ #

    def publicar_foto(self, image_url, caption=""):
        """Publica uma única foto. Retorna o ID da mídia publicada."""
        container = self._request("POST", f"{self.ig_user_id}/media", {
            "image_url": image_url,
            "caption": caption,
        })
        creation_id = container["id"]
        result = self._request("POST", f"{self.ig_user_id}/media_publish", {
            "creation_id": creation_id,
        })
        logger.info("Foto publicada: %s", result["id"])
        return result["id"]

    def publicar_carrossel(self, image_urls, caption=""):
        """Publica um carrossel de 2 a 10 imagens. Retorna o ID da mídia publicada."""
        if not (2 <= len(image_urls) <= 10):
            raise ValueError("Um carrossel precisa de 2 a 10 imagens.")

        children_ids = []
        for url in image_urls:
            item = self._request("POST", f"{self.ig_user_id}/media", {
                "image_url": url,
                "is_carousel_item": "true",
            })
            children_ids.append(item["id"])

        container = self._request("POST", f"{self.ig_user_id}/media", {
            "media_type": "CAROUSEL",
            "children": ",".join(children_ids),
            "caption": caption,
        })
        creation_id = container["id"]
        result = self._request("POST", f"{self.ig_user_id}/media_publish", {
            "creation_id": creation_id,
        })
        logger.info("Carrossel publicado: %s", result["id"])
        return result["id"]

    def publicar_reels(self, video_url, caption="", capa_segundo=None, compartilhar_no_feed=True):
        """Publica um Reels. video_url precisa ser pública. Retorna o ID da mídia publicada."""
        params = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "share_to_feed": str(compartilhar_no_feed).lower(),
        }
        if capa_segundo is not None:
            params["thumb_offset"] = capa_segundo

        container = self._request("POST", f"{self.ig_user_id}/media", params)
        creation_id = container["id"]
        self._esperar_processamento(creation_id)
        result = self._request("POST", f"{self.ig_user_id}/media_publish", {
            "creation_id": creation_id,
        })
        logger.info("Reels publicado: %s", result["id"])
        return result["id"]

    # ------------------------------------------------------------------ #
    # Gestão
    # ------------------------------------------------------------------ #

    def apagar_midia(self, media_id):
        """
        Apaga um post, Story, Reels ou álbum de carrossel inteiro.
        Não funciona em posts impulsionados como anúncio, e em carrosséis
        só apaga o álbum completo (não dá pra remover 1 item de dentro dele).
        """
        result = self._request("DELETE", str(media_id))
        logger.info("Mídia apagada: %s", media_id)
        return result

    def info_conta(self):
        """Dados básicos da conta — bom pra checar rapidamente se o token está vivo."""
        return self._request("GET", self.ig_user_id, {
            "fields": "username,name,followers_count,media_count",
        })

    def listar_midias(self, limite=10):
        """Lista as últimas mídias publicadas (mais recentes primeiro)."""
        result = self._request("GET", f"{self.ig_user_id}/media", {
            "fields": "id,caption,media_type,permalink,timestamp",
            "limit": limite,
        })
        return result.get("data", [])

    # ------------------------------------------------------------------ #
    # Token
    # ------------------------------------------------------------------ #

    def renovar_token_longa_duracao(self):
        """
        Troca o token atual (curto ou já de 60 dias) por um novo, fresco,
        de 60 dias. Precisa de META_APP_ID e META_APP_SECRET configurados.
        """
        if not self.app_id or not self.app_secret:
            raise InstagramAPIError(
                "META_APP_ID e META_APP_SECRET precisam estar configurados para renovar o token."
            )

        url = "https://graph.facebook.com/oauth/access_token"
        params = {
            "grant_type": "fb_exchange_token",
            "client_id": self.app_id,
            "client_secret": self.app_secret,
            "fb_exchange_token": self.access_token,
        }
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()
        if "error" in data:
            raise InstagramAPIError(data["error"].get("message", "Erro ao renovar token"), raw=data)

        self.access_token = data["access_token"]
        logger.info("Token renovado. Expira em %s segundos.", data.get("expires_in"))
        return self.access_token
