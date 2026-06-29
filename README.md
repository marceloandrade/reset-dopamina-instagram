# Kit de Automação do Instagram

Núcleo Python para publicar (e apagar) conteúdo no Instagram via Graph API oficial da Meta.
Feito pra ser **replicável**: para usar com outra conta, basta um novo `.env` — nenhum código muda.

## O que isso faz

- Publica foto única, carrossel (2 a 10 imagens) e Reels
- Apaga mídias (com confirmação obrigatória)
- Lista as últimas publicações
- Renova o token de acesso (60 dias) quando precisar

Pré-requisito: a conta do Instagram já precisa estar configurada como Business/Creator,
vinculada a uma Página do Facebook, com um App criado na Meta e um token de longa duração
gerado — esse é o trabalho da "Etapa 0" do projeto, documentado no caderno do Notion.

## Instalação

```bash
cd instagram-kit
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configuração

```bash
cp .env.example .env
```

Abra o `.env` e preencha:
- `IG_USER_ID` — ID da conta do Instagram Business
- `IG_ACCESS_TOKEN` — o token de longa duração (60 dias)
- `META_APP_ID` e `META_APP_SECRET` — só necessários se for usar o comando `renovar-token`

⚠️ O `.env` nunca deve ir para o Git nem para nenhuma documentação pública — ele já está
no `.gitignore`.

## Uso (linha de comando)

```bash
# Testar se o token está funcionando
python cli.py status

# Publicar uma foto
python cli.py foto --image-url "https://exemplo.com/foto.jpg" --caption "Minha legenda"

# Publicar um carrossel
python cli.py carrossel --imagens "https://.../1.jpg,https://.../2.jpg,https://.../3.jpg" --caption "Legenda"

# Publicar um Reels
python cli.py reels --video-url "https://exemplo.com/video.mp4" --caption "Legenda"

# Listar as últimas publicações
python cli.py listar --limite 5

# Apagar uma mídia (precisa confirmar explicitamente)
python cli.py apagar --media-id 18108923192475148 --confirmar

# Renovar o token antes dele expirar
python cli.py renovar-token
```

## Uso programático (dentro de outro script Python)

```python
from instagram_api import InstagramClient

client = InstagramClient()  # lê tudo do .env automaticamente
media_id = client.publicar_foto("https://exemplo.com/foto.jpg", caption="Legenda")
```

## Importante: imagens e vídeos precisam de URL pública

A Graph API busca o arquivo a partir de uma URL — ela não aceita upload direto de um
arquivo do seu computador. A imagem/vídeo precisa estar hospedado em algum lugar acessível
pela internet no momento da publicação (no projeto completo, isso vai ser resolvido pelo
próprio repositório no GitHub — Etapa 4).

## Limitações conhecidas da API

- Carrossel: só dá para apagar o álbum inteiro, não uma imagem específica de dentro dele
- Não dá para apagar posts que já foram impulsionados como anúncio
- O token de longa duração expira em 60 dias — use `renovar-token` antes disso
- Limite de publicação: 100 posts via API por período de 24h (carrossel conta como 1 post)

## Replicar para outra conta/cliente

1. Repita a "Etapa 0" com a conta nova (App próprio na Meta, token próprio)
2. Copie esta pasta inteira
3. Crie um novo `.env` com as credenciais da conta nova
4. Pronto — nenhuma linha de código precisa mudar
