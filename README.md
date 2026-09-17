# Gueto Studio — backend do Pix

Guia pra você entender o que está rodando, não só copiar e colar.

## O fluxo, em palavras simples

```
Cliente clica "Comprar"
        │
        ▼
Frontend (JS) manda o NOME do produto pro backend
        │
        ▼
Backend (Flask) olha o preço no SEU catálogo e pede um Pix pro Mercado Pago
        │
        ▼
Mercado Pago devolve QR Code + "copia e cola"
        │
        ▼
Frontend mostra o QR Code e fica perguntando "já pagou?" a cada 3s
        │
        ▼
Cliente paga pelo app do banco dele
        │
        ▼
Mercado Pago marca o pagamento como "approved"
        │
        ▼
Frontend detecta isso e troca a tela por "Pagamento confirmado!"
```

Repare que seu servidor nunca "recebe" o dinheiro nem processa cartão/Pix
de verdade — isso é 100% responsabilidade do Mercado Pago. Seu backend só
**pede** a criação do pagamento e depois **consulta** o status dele. Essa
separação (quem cobra vs. quem só pergunta "já foi?") é o coração de
qualquer integração de gateway de pagamento, não só Mercado Pago.

## Passo 1 — Criar credenciais de TESTE no Mercado Pago

1. Crie/acesse sua conta em [mercadopago.com.br](https://www.mercadopago.com.br)
2. Vá em **Seu negócio → Configurações → Credenciais** (ou busque por
   "credenciais de teste" no painel de desenvolvedor)
3. Copie o **Access Token de teste** (começa com `TEST-`)
4. No projeto, copie `.env.example` para um arquivo novo chamado `.env` e
   cole o token ali

Nunca suba o `.env` de verdade pro GitHub — é sua chave privada. Um
`.gitignore` com a linha `.env` resolve isso.

## Passo 2 — Instalar e rodar localmente

```bash
python -m venv venv
source venv/bin/activate        # no Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abra `http://localhost:5000` — o próprio Flask está servindo o `index.html`
agora (por isso ele fica na mesma pasta do `app.py`).

## Passo 3 — Testar um pagamento sem gastar dinheiro de verdade

O Mercado Pago tem **usuários de teste** e **cartões/Pix de teste** — com
credenciais `TEST-`, nenhum pagamento é real. Pra aprovar um Pix de teste
manualmente, você pode simular a aprovação direto no painel de
desenvolvedor do Mercado Pago (seção de simulador de pagamentos), sem
precisar realmente escanear nada.

## Passo 4 — Colocar no ar (GitHub Pages não serve mais)

Isso é importante: o GitHub Pages só serve arquivos estáticos (HTML/CSS/JS
puros) — ele **não roda Python**. Agora que existe um `app.py`, você
precisa de um host que rode servidores Python, por exemplo:

- **Render** ou **Railway** (têm plano gratuito, bom pra aprender e pra um
  projeto de portfólio)
- **PythonAnywhere** (também tem plano gratuito, é bem direto pra Flask)

O processo em qualquer um deles é parecido: conectar o repositório do
GitHub, apontar `python app.py` (ou um comando equivalente com gunicorn)
como comando de start, e cadastrar `MP_ACCESS_TOKEN` como variável de
ambiente no painel do serviço (em vez do arquivo `.env`, que é só local).

## Passo 5 — Trocar teste por produção

Quando o site estiver no ar e testado, é só trocar o Access Token de teste
pelo **Access Token de produção** (mesmo lugar no painel do Mercado Pago) —
o código não muda em nada.

## Próximo passo pra quem quiser aprofundar: webhook

O jeito que o `app.py` está hoje, o frontend fica **perguntando** o status
a cada 3 segundos (isso se chama *polling*). Funciona bem e é o jeito mais
simples de entender. Já existe uma rota `/webhook` pronta no `app.py` como
próximo passo: é o Mercado Pago quem **avisa** seu servidor sozinho quando
o status muda, sem precisar ficar perguntando. Pra testar isso localmente
você precisaria expor seu `localhost` pra internet com uma ferramenta como
o [ngrok](https://ngrok.com) e cadastrar a URL gerada como "URL de
notificação" nas configurações do seu app no Mercado Pago. Vale explorar
depois que o fluxo com polling estiver funcionando de ponta a ponta.
