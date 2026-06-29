---
name: instagram-publish
description: Publica fotos, carrosséis e Reels no Instagram (@resetdopamina21d) via API oficial da Meta, lista publicações recentes e apaga mídias (sempre com confirmação). Use quando o usuário pedir para publicar, postar, divulgar, agendar manualmente ou apagar algo no Instagram.
---

# Publicar no Instagram — Reset Dopamina 21D

Este skill roda o núcleo Python (`instagram_api.py` / `cli.py`) que já está configurado e
testado nesta mesma pasta, usando o ambiente virtual e o `.env` que já existem aqui.

## Como executar

Use sempre o Python do ambiente virtual desta skill — nunca o `python` global do sistema:

- **Windows:** `${CLAUDE_SKILL_DIR}\venv\Scripts\python.exe`
- **macOS/Linux:** `${CLAUDE_SKILL_DIR}/venv/bin/python`

E sempre aponte para o `cli.py` desta pasta:
`${CLAUDE_SKILL_DIR}/cli.py`

## Comandos disponíveis

- **Checar se o token está ok:**
  `<python> ${CLAUDE_SKILL_DIR}/cli.py status`
- **Publicar foto única:**
  `<python> ${CLAUDE_SKILL_DIR}/cli.py foto --image-url "<url>" --caption "<legenda>"`
- **Publicar carrossel (2 a 10 imagens):**
  `<python> ${CLAUDE_SKILL_DIR}/cli.py carrossel --imagens "<url1>,<url2>,..." --caption "<legenda>"`
- **Publicar Reels:**
  `<python> ${CLAUDE_SKILL_DIR}/cli.py reels --video-url "<url>" --caption "<legenda>"`
- **Listar últimas publicações:**
  `<python> ${CLAUDE_SKILL_DIR}/cli.py listar --limite <N>`
- **Apagar uma publicação:**
  `<python> ${CLAUDE_SKILL_DIR}/cli.py apagar --media-id <ID> --confirmar`
- **Renovar o token de acesso (60 dias):**
  `<python> ${CLAUDE_SKILL_DIR}/cli.py renovar-token`

## Regras importantes

1. **Imagem/vídeo precisa de URL pública.** A API busca o arquivo por URL, não aceita
   upload direto. Se o usuário só tiver um arquivo local ou pedir para "criar uma imagem",
   gere/hospede a imagem primeiro (ex.: com uma ferramenta de geração de imagem disponível)
   e use a URL resultante — nunca passe um caminho de arquivo local em `--image-url`.

2. **Nunca execute `apagar` sem confirmação explícita do usuário nesta conversa**, mesmo que
   ele já tenha passado o `--media-id` direto. Pergunte "tem certeza que quer apagar o post
   X?" e espere a resposta antes de rodar o comando com `--confirmar`.

3. **Nunca exiba, imprima ou registre o conteúdo do `.env`** (token, App Secret) na
   conversa. Se precisar confirmar que as variáveis existem, apenas confirme a presença do
   arquivo — não mostre os valores.

4. Depois de publicar com sucesso, sempre informe o **ID da mídia** retornado.

5. Se um comando falhar com erro relacionado a token expirado/invalido, sugira rodar
   `renovar-token` e atualizar o `.env` manualmente com o novo valor.

## Exemplos de uso

> "publica essa foto no Instagram com a legenda 'Bom dia!'"
> → roda o comando `foto` com a URL e legenda fornecidas

> "apaga o post 178xxxx do Instagram"
> → pergunta confirmação antes de rodar `apagar --confirmar`

> "lista os últimos 5 posts do Instagram"
> → roda `listar --limite 5`

> "o token do Instagram expirou, o que eu faço?"
> → roda `renovar-token` e explica que o novo valor precisa ser colado no `.env`
