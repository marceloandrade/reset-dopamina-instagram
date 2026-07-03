#!/usr/bin/env python3
"""
Relatório semanal de crescimento — roda 1x por semana via GitHub Actions
e manda um resumo por WhatsApp:

    - seguidores atuais e variação desde o relatório da semana passada
    - alcance (reach) da conta nos últimos 7 dias
    - performance dos posts publicados nos últimos 7 dias (alcance,
      curtidas, comentários, salvamentos — o que a API devolver)

O histórico de seguidores fica salvo em dados/historico_insights.json,
dentro do próprio repositório, usando a API de Conteúdo do GitHub (o
mesmo mecanismo que o subir_imagens.py usa pra imagens). Isso é o que
permite calcular "quanto cresceu desde a semana passada" mesmo rodando
num runner novo a cada execução, sem precisar de um banco de dados.

Uso:
    python relatorio_semanal.py

Variáveis de ambiente necessárias:
    IG_USER_ID, IG_ACCESS_TOKEN   - conta do Instagram (ver instagram_api.py)
    WHATSAPP_PHONE, WHATSAPP_APIKEY - CallMeBot (ver whatsapp_notify.py)
    GITHUB_TOKEN   - token com permissão de escrita no repo (no workflow,
                     o token automático do Actions serve, com
                     permissions: contents: write)
    GITHUB_REPO    - "usuario/nome-do-repo"
    GITHUB_BRANCH  - branch de destino (padrão: main)
"""

import base64
import json
import logging
import os
from datetime import date

import requests
from dotenv import load_dotenv

from instagram_api import InstagramClient, InstagramAPIError
from whatsapp_notify import enviar_whatsapp, WhatsAppError
import insights

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("relatorio_semanal")

DIAS_JANELA = 7
GITHUB_API_BASE = "https://api.github.com"
CAMINHO_HISTORICO = "dados/historico_insights.json"
MAX_PONTOS_HISTORICO = 52  # ~1 ano de relatórios semanais


def _github_headers():
    return {
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
    }


def _carregar_historico():
    """Retorna (historico_dict, sha_do_arquivo_ou_None). sha=None => arquivo ainda não existe."""
    repo = os.environ["GITHUB_REPO"]
    branch = os.environ.get("GITHUB_BRANCH", "main")
    url = f"{GITHUB_API_BASE}/repos/{repo}/contents/{CAMINHO_HISTORICO}"

    resp = requests.get(url, headers=_github_headers(), params={"ref": branch}, timeout=30)
    if resp.status_code == 404:
        return {"seguidores": []}, None
    resp.raise_for_status()
    dados = resp.json()
    conteudo = base64.b64decode(dados["content"]).decode("utf-8")
    return json.loads(conteudo), dados["sha"]


def _salvar_historico(historico, sha):
    repo = os.environ["GITHUB_REPO"]
    branch = os.environ.get("GITHUB_BRANCH", "main")
    url = f"{GITHUB_API_BASE}/repos/{repo}/contents/{CAMINHO_HISTORICO}"

    body = {
        "message": "Atualiza histórico de insights (relatório semanal)",
        "content": base64.b64encode(
            json.dumps(historico, indent=2, ensure_ascii=False).encode("utf-8")
        ).decode("utf-8"),
        "branch": branch,
    }
    if sha:
        body["sha"] = sha

    resp = requests.put(url, headers=_github_headers(), json=body, timeout=30)
    resp.raise_for_status()


def montar_mensagem(resumo, posts, seguidores_anterior):
    hoje = date.today().isoformat()
    atual = resumo["seguidores_atual"]

    linhas = [
        f"📊 Reset Dopamina 21D — Relatório semanal ({hoje})",
        "",
        f"👥 Seguidores: {atual if atual is not None else 'indisponível'}",
    ]

    if seguidores_anterior is not None and atual is not None:
        variacao = atual - seguidores_anterior
        sinal = "📈" if variacao >= 0 else "📉"
        linhas.append(f"{sinal} Variação desde o último relatório: {variacao:+d}")
    else:
        linhas.append("ℹ️ Ainda sem comparação (primeiro relatório do histórico).")

    if resumo.get("reach_periodo") is not None:
        linhas.append(f"👁️ Alcance da conta (últimos {DIAS_JANELA} dias): {resumo['reach_periodo']}")

    linhas.append("")
    linhas.append(f"📝 Posts publicados nos últimos {DIAS_JANELA} dias: {len(posts)}")

    if posts:
        linhas.append("")
        for p in posts:
            ins = p.get("insights", {})
            titulo = (p.get("caption") or "(sem legenda)").strip().splitlines()[0][:40]
            partes = []
            if "reach" in ins:
                partes.append(f"alcance {ins['reach']}")
            if "likes" in ins:
                partes.append(f"{ins['likes']} curtidas")
            if "comments" in ins:
                partes.append(f"{ins['comments']} comentários")
            if "saved" in ins:
                partes.append(f"{ins['saved']} salvos")
            resumo_post = ", ".join(partes) if partes else "sem métricas disponíveis ainda"
            data_post = (p.get("timestamp") or "")[:10]
            linhas.append(f"  • {data_post} — {titulo}: {resumo_post}")

    return "\n".join(linhas)


def main():
    try:
        client = InstagramClient()
    except KeyError as exc:
        logger.error("❌ Variável de ambiente faltando: %s", exc)
        raise SystemExit(1)

    resumo = insights.resumo_conta(client, dias=DIAS_JANELA)
    posts = insights.posts_recentes_com_insights(client, dias=DIAS_JANELA)

    try:
        historico, sha = _carregar_historico()
    except requests.RequestException as exc:
        logger.error("⚠️ Não consegui ler o histórico no GitHub (%s). Seguindo sem comparação.", exc)
        historico, sha = {"seguidores": []}, None

    seguidores_anterior = historico["seguidores"][-1]["valor"] if historico["seguidores"] else None

    mensagem = montar_mensagem(resumo, posts, seguidores_anterior)
    print(mensagem)
    print()

    if resumo["seguidores_atual"] is not None:
        historico["seguidores"].append({"data": date.today().isoformat(), "valor": resumo["seguidores_atual"]})
        historico["seguidores"] = historico["seguidores"][-MAX_PONTOS_HISTORICO:]
        try:
            _salvar_historico(historico, sha)
            logger.info("✅ Histórico de seguidores atualizado no repositório.")
        except requests.RequestException as exc:
            logger.error("⚠️ Não consegui salvar o histórico no GitHub: %s", exc)
            logger.error("O relatório desta semana ainda é válido — só a comparação da próxima semana pode ficar sem esse ponto.")

    try:
        enviar_whatsapp(mensagem)
        logger.info("✅ Relatório enviado por WhatsApp.")
    except WhatsAppError as exc:
        logger.error("❌ Falha ao enviar WhatsApp: %s", exc)
        logger.error("O relatório acima ainda é válido — só não foi entregue por WhatsApp.")


if __name__ == "__main__":
    main()
