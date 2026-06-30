#!/usr/bin/env python3
"""
Revisão quinzenal do calendário — roda 2x por mês (dias 1 e 16) via
GitHub Actions, e manda um resumo por WhatsApp avisando:

    - quantos posts já estão Aprovados (com imagem pronta) para os
      próximos 15 dias
    - quantos ainda estão como Rascunho, esperando aprovação
    - se NENHUM post está agendado no período (sinal de que é hora de
      criar um novo lote de conteúdo)

Uso:
    python revisar_calendario.py
"""

import logging

from dotenv import load_dotenv

import notion_calendario as notion
from whatsapp_notify import enviar_whatsapp, WhatsAppError

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("revisar_calendario")

DIAS_DE_JANELA = 15


def montar_mensagem(posts: list) -> str:
    if not posts:
        return (
            f"📅 Reset Dopamina 21D — Revisão do calendário\n\n"
            f"⚠️ Nenhum post agendado para os próximos {DIAS_DE_JANELA} dias!\n"
            f"Hora de criar um novo lote de conteúdo."
        )

    aprovados = [p for p in posts if p["status"] == "Aprovado" and p["urls_imagens"].strip()]
    aguardando_imagem = [p for p in posts if p["status"] == "Aprovado" and not p["urls_imagens"].strip()]
    rascunhos = [p for p in posts if p["status"] == "Rascunho"]

    linhas = [
        f"📅 Reset Dopamina 21D — Revisão do calendário ({DIAS_DE_JANELA} dias)",
        "",
        f"✅ Prontos pra publicar: {len(aprovados)}",
        f"🖼️ Aprovados sem imagem hospedada ainda: {len(aguardando_imagem)}",
        f"📝 Rascunhos aguardando aprovação: {len(rascunhos)}",
    ]

    if rascunhos:
        linhas.append("")
        linhas.append("Pendentes de aprovação:")
        for p in rascunhos:
            linhas.append(f"  • {p['data']} — {p['titulo']}")

    if aguardando_imagem:
        linhas.append("")
        linhas.append("Aprovados mas sem imagem ainda (rodar subir_imagens.py):")
        for p in aguardando_imagem:
            linhas.append(f"  • {p['data']} — {p['titulo']}")

    ultima_data = posts[-1]["data"]
    linhas.append("")
    linhas.append(f"Calendário cobre até {ultima_data}. Se isso for menos de {DIAS_DE_JANELA} dias à frente, considere planejar o próximo lote.")

    return "\n".join(linhas)


def main():
    posts = notion.listar_proximos_dias(dias=DIAS_DE_JANELA)
    mensagem = montar_mensagem(posts)

    print(mensagem)
    print()

    try:
        enviar_whatsapp(mensagem)
        logger.info("✅ Resumo enviado por WhatsApp.")
    except WhatsAppError as exc:
        logger.error("❌ Falha ao enviar WhatsApp: %s", exc)
        logger.error("O resumo acima ainda é válido — só não foi entregue por WhatsApp.")


if __name__ == "__main__":
    main()
