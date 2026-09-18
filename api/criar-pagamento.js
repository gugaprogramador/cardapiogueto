import { MercadoPagoConfig, Payment } from 'mercadopago';

// Catálogo de produtos com os preços oficiais
const PRODUTOS = {
  "Coca-Cola Lata": 6.00,
  "Guaracamp": 2.50,
  "Corona": 8.00,
  "Spaten": 8.00,
  "Heineken": 8.00,
  "Stella Artois": 8.00,
};

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ erro: 'Método não permitido' });
  }

  const accessToken = process.env.MP_ACCESS_TOKEN;
  if (!accessToken) {
    return res.status(500).json({ erro: 'MP_ACCESS_TOKEN não configurado nas variáveis de ambiente da Vercel.' });
  }

  const { nome } = req.body || {};

  if (!PRODUTOS[nome]) {
    return res.status(400).json({ erro: 'Produto não encontrado' });
  }

  const client = new MercadoPagoConfig({ accessToken });
  const payment = new Payment(client);

  try {
    const resposta = await payment.create({
      body: {
        transaction_amount: PRODUTOS[nome],
        description: nome,
        payment_method_id: 'pix',
        payer: {
          email: 'cliente@guetostudio.com.br',
          first_name: 'Cliente',
        },
      },
    });

    const dadosPix = resposta.point_of_interaction.transaction_data;

    return res.status(200).json({
      id: resposta.id,
      qr_code_base64: dadosPix.qr_code_base64,
      qr_code: dadosPix.qr_code,
      status: resposta.status,
    });
  } catch (error) {
    return res.status(500).json({ erro: 'Falha ao criar pagamento', detalhes: error.message });
  }
}
