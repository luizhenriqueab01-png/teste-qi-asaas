from flask import Blueprint, request, jsonify
import mercadopago
import os
from datetime import datetime

payment_bp = Blueprint('payment', __name__)

# Configurar Mercado Pago
# IMPORTANTE: Substitua pela sua chave real ou use variável de ambiente
MERCADO_PAGO_ACCESS_TOKEN = os.getenv('MERCADO_PAGO_ACCESS_TOKEN', 'TEST-YOUR-ACCESS-TOKEN-HERE')

sdk = mercadopago.SDK(MERCADO_PAGO_ACCESS_TOKEN)

@payment_bp.route('/api/create_preference', methods=['POST'])
def create_preference():
    """
    Cria uma preferência de pagamento no Mercado Pago
    Usado para Checkout Pro (redireciona para página do MP)
    """
    try:
        data = request.json
        lead_data = data.get('leadData', {})
        
        preference_data = {
            "items": [
                {
                    "title": "Teste de QI Profissional - Resultado Completo",
                    "quantity": 1,
                    "unit_price": 19.90,
                    "currency_id": "BRL"
                }
            ],
            "payer": {
                "name": lead_data.get('name', ''),
                "email": lead_data.get('email', ''),
                "phone": {
                    "number": lead_data.get('phone', '')
                }
            },
            "back_urls": {
                "success": f"{request.host_url}payment/success",
                "failure": f"{request.host_url}payment/failure",
                "pending": f"{request.host_url}payment/pending"
            },
            "auto_return": "approved",
            "statement_descriptor": "TESTE QI",
            "external_reference": f"lead_{lead_data.get('email', '')}_{datetime.now().timestamp()}",
            "notification_url": f"{request.host_url}api/webhook"
        }
        
        preference_response = sdk.preference().create(preference_data)
        preference = preference_response["response"]
        
        return jsonify({
            "preferenceId": preference["id"],
            "initPoint": preference["init_point"],
            "sandboxInitPoint": preference.get("sandbox_init_point", "")
        }), 200
        
    except Exception as e:
        print(f"Erro ao criar preferência: {str(e)}")
        return jsonify({"error": str(e)}), 500


@payment_bp.route('/api/create_pix_payment', methods=['POST'])
def create_pix_payment():
    """
    Cria um pagamento PIX e retorna o QR Code
    """
    try:
        data = request.json
        lead_data = data.get('leadData', {})
        
        payment_data = {
            "transaction_amount": 19.90,
            "description": "Teste de QI Profissional - Resultado Completo",
            "payment_method_id": "pix",
            "payer": {
                "email": lead_data.get('email', ''),
                "first_name": lead_data.get('name', '').split()[0] if lead_data.get('name') else '',
                "last_name": ' '.join(lead_data.get('name', '').split()[1:]) if len(lead_data.get('name', '').split()) > 1 else '',
            },
            "notification_url": f"{request.host_url}api/webhook",
            "external_reference": f"pix_{lead_data.get('email', '')}_{datetime.now().timestamp()}"
        }
        
        payment_response = sdk.payment().create(payment_data)
        payment = payment_response["response"]
        
        # Extrair dados do PIX
        point_of_interaction = payment.get("point_of_interaction", {})
        transaction_data = point_of_interaction.get("transaction_data", {})
        
        return jsonify({
            "paymentId": payment["id"],
            "status": payment["status"],
            "qrCode": transaction_data.get("qr_code", ""),
            "qrCodeBase64": transaction_data.get("qr_code_base64", ""),
            "ticketUrl": transaction_data.get("ticket_url", "")
        }), 200
        
    except Exception as e:
        print(f"Erro ao criar pagamento PIX: {str(e)}")
        return jsonify({"error": str(e)}), 500


@payment_bp.route('/api/check_payment_status/<payment_id>', methods=['GET'])
def check_payment_status(payment_id):
    """
    Verifica o status de um pagamento
    """
    try:
        payment_response = sdk.payment().get(payment_id)
        payment = payment_response["response"]
        
        return jsonify({
            "status": payment["status"],
            "statusDetail": payment.get("status_detail", ""),
            "approved": payment["status"] == "approved"
        }), 200
        
    except Exception as e:
        print(f"Erro ao verificar status: {str(e)}")
        return jsonify({"error": str(e)}), 500


@payment_bp.route('/api/webhook', methods=['POST'])
def webhook():
    """
    Recebe notificações do Mercado Pago sobre mudanças no status do pagamento
    """
    try:
        data = request.json
        
        # Log da notificação
        print(f"Webhook recebido: {data}")
        
        # Verificar tipo de notificação
        if data.get("type") == "payment":
            payment_id = data.get("data", {}).get("id")
            
            if payment_id:
                # Buscar informações do pagamento
                payment_response = sdk.payment().get(payment_id)
                payment = payment_response["response"]
                
                print(f"Pagamento {payment_id} - Status: {payment['status']}")
                
                # Aqui você pode:
                # 1. Salvar no banco de dados
                # 2. Enviar email para o cliente
                # 3. Liberar acesso ao resultado
                # 4. Atualizar status do lead
                
                if payment["status"] == "approved":
                    print(f"Pagamento aprovado! Email: {payment.get('payer', {}).get('email')}")
                    # TODO: Enviar email com resultado
                    # TODO: Marcar lead como pago no banco
        
        return jsonify({"status": "received"}), 200
        
    except Exception as e:
        print(f"Erro no webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500


@payment_bp.route('/payment/success', methods=['GET'])
def payment_success():
    """
    Página de sucesso após pagamento (Checkout Pro)
    """
    payment_id = request.args.get('payment_id')
    status = request.args.get('status')
    
    # Redirecionar para o frontend com os parâmetros
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pagamento Aprovado</title>
        <script>
            window.location.href = '/?payment=success&payment_id={payment_id}&status={status}';
        </script>
    </head>
    <body>
        <p>Redirecionando...</p>
    </body>
    </html>
    """


@payment_bp.route('/payment/failure', methods=['GET'])
def payment_failure():
    """
    Página de falha no pagamento
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pagamento Recusado</title>
        <script>
            window.location.href = '/?payment=failure';
        </script>
    </head>
    <body>
        <p>Redirecionando...</p>
    </body>
    </html>
    """


@payment_bp.route('/payment/pending', methods=['GET'])
def payment_pending():
    """
    Página de pagamento pendente
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pagamento Pendente</title>
        <script>
            window.location.href = '/?payment=pending';
        </script>
    </head>
    <body>
        <p>Redirecionando...</p>
    </body>
    </html>
    """

