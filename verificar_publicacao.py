#!/usr/bin/env python3
"""
Monitor de publicação — roda 2h depois do horário agendado de publicar.yml
(14h Brasília, já que publicar.yml roda às 12h) pra checar se sobrou algum
post "Aprovado" com data de hoje (ou atrasado) que deveria ter sido
publicado e não foi.

Propositalmente NÃO tenta publicar de novo sozinho: se o post ficou
"Aprovado" é porque ou a publicação falhou (e é seguro tentar de novo),
ou falhou DEPOIS de publicar mas ANTES de marcar como "Publicado" no
Notion (raro, mas nesse caso publicar de novo criaria um post duplicado
no Instagram). Como não dá pra distinguir os dois casos com segurança
automaticamente, o script só avisa por WhatsApp e deixa a decisão de
rodar de novo com o Marcelo.

Uso:
    python verificar_publicacao.py
"""

import logging

from dotenv import load_dotenv

import notion_calendario as notion
from whatsapp_notify import enviar_whatsapp, WhatsAppError

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verificar_publicacao")


def montar_alerta(posts_pendentes):
    linhas = [
        "⚠️ Reset Dopamina 21D — publicação pendente",
        "",
        f"{len(posts_pendentes)} post(s) deveriam ter sido publicados e ainda estão 'Aprovado':",
        "",
    ]
    for p in posts_pendentes:
        linhas.append(f"  • {p['titulo']} — data: {p['data']} ({p['formato']})")

    linhas += [
        "",
        "O que fazer:",
        "1. Abre o GitHub Actions → 'Publicar calendário no Instagram'",
        "2. Olha os logs da última execução falha pra ver o motivo do erro",
        "3. Se o motivo já tiver solução conhecida, corrige e clica em",
        "   'Executar novamente' nessa mesma execução",
        "",
        "A próxima execução diária (amanhã, 12h) tentaria de novo sozinha,",
        "mas como o post tem data específica, mais vale corrigir hoje.",
    ]
    return "\n".join(linhas)


def main():
    posts_pendentes = notion.listar_aprovados_para_publicar()

    if not posts_pendentes:
        print("Nada pendente — todos os posts com data até hoje já foram publicados (ou ainda não têm imagem, o que é esperado).")
        return

    mensagem = montar_alerta(posts_pendentes)
    print(mensagem)
    print()

    try:
        enviar_whatsapp(mensagem)
        logger.info("✅ Alerta enviado por WhatsApp.")
    except WhatsAppError as exc:
        logger.error("❌ Falha ao enviar o alerta por WhatsApp: %s", exc)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
