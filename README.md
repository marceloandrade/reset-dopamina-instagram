# Kit de Automação do Instagram

Núcleo Python para publicar (e apagar) conteúdo no Instagram via Graph API oficial da Meta.
Feito pra ser **replicável**: para usar com outra conta, basta um novo `.env` — nenhum código muda.

## O que isso faz

- Publica foto única, carrossel (2 a 10 imagens) e Reels
- Apaga mídias (com confirmação obrigatória)
- Lista as últimas publicações
- Consulta métricas de crescimento — seguidores, alcance e engajamento por post (insights)
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

# Ver métricas de crescimento (últimos 7 dias, com performance dos posts)
python cli.py insights --dias 7 --posts

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

## Métricas de crescimento (insights)

Além de publicar, o kit também lê métricas direto da Graph API — sem precisar
abrir o app do Instagram:

- **Nível de conta:** seguidores atuais e alcance (`reach`) somado nos últimos N dias
- **Nível de post:** alcance, visualizações, curtidas, comentários, salvamentos e
  compartilhamentos de cada mídia publicada no período

```bash
python cli.py insights --dias 7 --posts
```

Isso é o que alimenta o `relatorio_semanal.py`: todo domingo/segunda o
GitHub Actions (`.github/workflows/relatorio_semanal.yml`) roda esse script sozinho,
manda um resumo por WhatsApp (via `whatsapp_notify.py`) e guarda o histórico de
seguidores em `dados/historico_insights.json`, **dentro do próprio repositório** —
é assim que ele sabe comparar "quanto cresceu desde a semana passada" mesmo rodando
num runner novo a cada execução, sem precisar de banco de dados.

### ⚠️ Permissão extra necessária

Insights exige a permissão **`instagram_manage_insights`** no token — as permissões
de publicação (`instagram_basic`, `instagram_content_publish`) não são suficientes.
Essa permissão não aparece em "Adicionar casos de uso" nem no caso de uso de Páginas:
ela mora dentro do caso de uso **"Gerenciar mensagens e conteúdo no Instagram"**, aba
**Permissões e recursos**, em ordem alfabética. Se `cli.py insights` retornar erro
`(#10) Application does not have permission for this action`, é isso — veja o item 6
do catálogo de erros no Notion pro passo a passo completo.

Depois de adicionar a permissão lá, gere um token novo no Graph API Explorer e rode
`python cli.py renovar-token` normalmente (mesmo fluxo de sempre).

### Métricas usadas (e por que não `impressions`)

A Meta descontinuou `impressions` e `profile_views` (série temporal) em abril/2025,
substituindo por `views`. O módulo `insights.py` já usa o conjunto atual (`reach`,
`views`, `likes`, `comments`, `saved`, `shares`) e cai automaticamente para um
conjunto reduzido se a API rejeitar alguma métrica — a Graph API muda esse conjunto
de tempos em tempos, então isso é tratado como algo esperado, não uma exceção.

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
