"""
Envio de mensagens de WhatsApp via CallMeBot (API gratuita, uso pessoal).

Configuração única (feita uma vez, fora do código):
    1. Salve o número +34 698 28 89 73 nos seus contatos do WhatsApp
    2. Mande pra esse contato a mensagem: "I allow callmebot to send me messages"
    3. Você recebe de volta uma APIKEY — guarde ela

Variáveis de ambiente necessárias:
    WHATSAPP_PHONE   - seu número com código do país, ex.: 5562999999999
    WHATSAPP_APIKEY  - a apikey recebida do bot

Limitação conhecida: CallMeBot é um serviço gratuito mantido por uma única
pessoa como hobby — pode ocasionalmente ficar com a fila cheia ("bot is
currently full") ou instável. Para um caso de uso crítico, considere migrar
para a API oficial da Twilio (paga, poucos centavos por mensagem).
"""

import os
import requests

CALLMEBOT_URL = "https://api.callmebot.com/whatsapp.php"


class WhatsAppError(Exception):
    pass


def enviar_whatsapp(mensagem: str) -> bool:
    """Envia uma mensagem de texto pro WhatsApp configurado. Retorna True se enviado."""
    phone = os.environ.get("WHATSAPP_PHONE")
    apikey = os.environ.get("WHATSAPP_APIKEY")

    if not phone or not apikey:
        raise WhatsAppError("WHATSAPP_PHONE e WHATSAPP_APIKEY precisam estar configurados.")

    params = {"phone": phone, "apikey": apikey, "text": mensagem}
    try:
        resp = requests.get(CALLMEBOT_URL, params=params, timeout=20)
    except requests.RequestException as exc:
        raise WhatsAppError(f"Falha de conexão com CallMeBot: {exc}")

    if resp.status_code != 200 or "queued" not in resp.text.lower():
        raise WhatsAppError(f"CallMeBot retornou algo inesperado: {resp.status_code} {resp.text[:200]}")

    return True
