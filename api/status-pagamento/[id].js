import { MercadoPagoConfig, Payment } from 'mercadopago';

export default async function handler(req, res) {
  const { id } = req.query;

  if (!id) {
    return res.status(400).json({ erro: 'ID do pagamento não fornecido' });
  }

  const accessToken = process.env.MP_ACCESS_TOKEN;
  if (!accessToken) {
    return res.status(500).json({ erro: 'MP_ACCESS_TOKEN não configurado' });
  }

  const client = new MercadoPagoConfig({ accessToken });
  const payment = new Payment(client);

  try {
    const resposta = await payment.get({ id });
    return res.status(200).json({
      status: resposta.status || 'pending',
    });
  } catch (error) {
    return res.status(500).json({ status: 'pending', erro: error.message });
  }
}
