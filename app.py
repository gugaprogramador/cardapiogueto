"""
Backend do Gueto Studio
------------------------
O que esse arquivo faz, em ordem:

1. Sobe um servidor Flask que também serve o index.html (o site continua
   sendo "um site só", só que agora com um cérebro em Python por trás).
2. Quando o cliente clica em "Comprar", o frontend chama /api/criar-pagamento.
   Esse endpoint fala com a API do Mercado Pago e pede um pagamento Pix.
   O Mercado Pago devolve um QR Code (imagem) e um "copia e cola" (texto).
3. O frontend fica perguntando (polling) pro endpoint /api/status-pagamento
   se aquele pagamento já foi pago.
4. Quando o Mercado Pago confirma que caiu o Pix, a gente avisa o cliente.

Conceito-chave pra entender o fluxo todo:
    O QR Code Pix e o "copia e cola" já contêm a informação de pagamento.
    Quem processa o pagamento de verdade é o banco do cliente + o Mercado
    Pago — nosso servidor só PEDE a criação do pagamento e depois FICA DE
    OLHO no status dele. A gente nunca lida com dinheiro diretamente.
"""

import os
import mercadopago
from flask import Flask, jsonify, request, send_from_directory
from dotenv import load_dotenv

load_dotenv()  # lê o arquivo .env e joga as variáveis em os.environ

app = Flask(__name__, static_folder=".", static_url_path="")

ACCESS_TOKEN = os.getenv("MP_ACCESS_TOKEN")
if not ACCESS_TOKEN:
    raise RuntimeError(
        "MP_ACCESS_TOKEN não encontrado. Copie .env.example para .env "
        "e cole seu Access Token de teste do Mercado Pago."
    )

sdk = mercadopago.SDK(ACCESS_TOKEN)

# ---------------------------------------------------------------------------
# MODO_TESTE_LOCAL
#
# Pix não tem "número de cartão de teste" como cartão de crédito tem — não
# existe um jeito simples de simular um Pix pago sem envolver dinheiro real
# de algum lado. Então, só pra você conseguir ver a tela de "pagamento
# confirmado" funcionando enquanto aprende o fluxo, esse modo FINGE que o
# pagamento foi aprovado depois de algumas consultas, sem chamar o Mercado
# Pago pra checar o status de verdade.
#
# Ligue só localmente, no seu .env: MODO_TESTE_LOCAL=true
# NUNCA deixe isso ligado em produção — a variável já vem desligada por
# padrão, então em produção não precisa fazer nada.
# ---------------------------------------------------------------------------
MODO_TESTE_LOCAL = os.getenv("MODO_TESTE_LOCAL", "false").lower() == "true"
_contador_consultas_teste = {}

# ---------------------------------------------------------------------------
# Catálogo de produtos DEFINIDO NO SERVIDOR.
#
# Ponto importante de segurança: o botão "Comprar" no HTML manda o preço
# junto (data-preco), mas qualquer pessoa pode abrir o DevTools do navegador
# e mudar esse valor pra "0.01" antes de clicar. Por isso o backend NUNCA
# confia no preço que vem do frontend — ele recebe só o NOME do produto e
# busca o preço de verdade aqui embaixo.
# ---------------------------------------------------------------------------
PRODUTOS = {
    "Coca-Cola Lata": 6.00,
    "Guaracamp": 2.50,
    "Corona": 8.00,
    "Spaten": 8.00,
    "Heineken": 8.00,
    "Stella Artois": 8.00,
}


@app.route("/")
def home():
    """Serve o index.html, igual um site estático faria."""
    return send_from_directory(".", "index.html")


@app.route("/api/criar-pagamento", methods=["POST"])
def criar_pagamento():
    """
    Recebe {"nome": "Corona"} do frontend e devolve os dados do Pix:
    QR Code em base64 (pra mostrar como imagem) e o "copia e cola".
    """
    dados = request.get_json(silent=True) or {}
    nome_produto = dados.get("nome")

    if nome_produto not in PRODUTOS:
        return jsonify({"erro": "Produto não encontrado"}), 400

    preco = PRODUTOS[nome_produto]

    # Isso aqui é o "pedido de pagamento" que mandamos pro Mercado Pago.
    # payment_method_id="pix" é o que diz pra API: "quero um Pix, não cartão".
    corpo_pagamento = {
        "transaction_amount": preco,
        "description": nome_produto,
        "payment_method_id": "pix",
        "payer": {
            # Em produção você pode pedir o e-mail real do cliente; pra um
            # frigobar com compra rápida, um e-mail fixo funciona bem.
            "email": "cliente@guetostudio.com.br",
            "first_name": "Cliente",
        },
    }

    resultado = sdk.payment().create(corpo_pagamento)
    pagamento = resultado["response"]

    if resultado["status"] not in (200, 201):
        # Isso normalmente indica Access Token errado, conta não habilitada
        # pra Pix, ou algum campo obrigatório faltando.
        return jsonify({"erro": "Falha ao criar pagamento", "detalhes": pagamento}), 500

    dados_pix = pagamento["point_of_interaction"]["transaction_data"]

    return jsonify(
        {
            "id": pagamento["id"],
            "qr_code_base64": dados_pix["qr_code_base64"],  # imagem do QR
            "qr_code": dados_pix["qr_code"],  # texto "copia e cola"
            "status": pagamento["status"],  # normalmente "pending" aqui
        }
    )


@app.route("/api/status-pagamento/<payment_id>")
def status_pagamento(payment_id):
    """
    O frontend chama isso a cada poucos segundos perguntando:
    "esse pagamento já foi aprovado?"

    Os status possíveis mais comuns: pending, approved, rejected, cancelled.
    """
    if MODO_TESTE_LOCAL:
        # As duas primeiras consultas voltam "pending" (pra você ver o
        # "Aguardando pagamento..." piscando de verdade); da terceira em
        # diante, finge que aprovou.
        vezes = _contador_consultas_teste.get(payment_id, 0) + 1
        _contador_consultas_teste[payment_id] = vezes
        status_simulado = "approved" if vezes >= 3 else "pending"
        return jsonify({"status": status_simulado})

    resultado = sdk.payment().get(payment_id)
    pagamento = resultado["response"]
    return jsonify({"status": pagamento.get("status", "pending")})


# ---------------------------------------------------------------------------
# BÔNUS (opcional, pra quando quiser ir além do polling): webhook.
#
# Em vez do frontend "ficar perguntando" pro backend, o Mercado Pago pode
# AVISAR o seu backend sozinho, assim que o status de um pagamento muda,
# fazendo um POST nessa URL. É o jeito mais usado em produção, mas exige
# que sua URL seja pública (ver README, seção "próximos passos").
# ---------------------------------------------------------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    dados = request.get_json(silent=True) or {}

    if dados.get("type") == "payment":
        payment_id = dados.get("data", {}).get("id")
        if payment_id:
            resultado = sdk.payment().get(payment_id)
            status = resultado["response"].get("status")
            print(f"[webhook] pagamento {payment_id} está: {status}")
            # Aqui, num projeto maior, você salvaria isso num banco de
            # dados em vez de só imprimir no terminal.

    # O Mercado Pago só precisa de um 200 OK pra saber que você recebeu.
    return "", 200


if __name__ == "__main__":
    app.run(debug=True, port=5000)
