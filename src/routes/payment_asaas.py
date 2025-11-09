from flask import Blueprint, request, jsonify
import requests
import os
from datetime import datetime

payment_asaas_bp = Blueprint('payment_asaas', __name__)

# Configurar Asaas
ASAAS_API_KEY = os.getenv('ASAAS_API_KEY', '$aact_prod_000MzkwODA2MWY2OGM3MWRlMDU2NWM3MzJlNzZmNGZhZGY6Ojk0NzQ0YzJlLWIxZDMtNGZmOS1hMGJjLTQyYTFiMDI4OTUyYjo6JGFhY2hfNzI3YmM0ZDQtZTliMy00OWUxLWJmYzktMzM1YTk4MzE1NTkz')

# URL base da API (produção)
ASAAS_API_URL = 'https://api.asaas.com/v3'

# Headers padrão
def get_headers():
    return {
        'access_token': ASAAS_API_KEY,
        'Content-Type': 'application/json'
    }


@payment_asaas_bp.route('/api/asaas/create_customer', methods=['POST'])
def create_customer():
    """
    Cria um cliente no Asaas
    Necessário antes de criar uma cobrança
    """
    try:
        data = request.json
        lead_data = data.get('leadData', {})
        
        # Extrair nome e sobrenome
        full_name = lead_data.get('name', '')
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0] if len(name_parts) > 0 else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        customer_data = {
            "name": full_name,
            "email": lead_data.get('email', ''),
            "phone": lead_data.get('phone', '').replace('(', '').replace(')', '').replace('-', '').replace(' ', ''),
            "mobilePhone": lead_data.get('phone', '').replace('(', '').replace(')', '').replace('-', '').replace(' ', ''),
            "notificationDisabled": False
        }
        
        response = requests.post(
            f'{ASAAS_API_URL}/customers',
            json=customer_data,
            headers=get_headers()
        )
        
        if response.status_code == 200:
            customer = response.json()
            return jsonify({
                "customerId": customer.get('id'),
                "customer": customer
            }), 200
        else:
            print(f"Erro ao criar cliente: {response.text}")
            return jsonify({"error": response.text}), response.status_code
            
    except Exception as e:
        print(f"Erro ao criar cliente: {str(e)}")
        return jsonify({"error": str(e)}), 500


@payment_asaas_bp.route('/api/asaas/create_pix_payment', methods=['POST'])
def create_pix_payment():
    """
    Cria uma cobrança PIX no Asaas e retorna o QR Code
    """
    try:
        data = request.json
        lead_data = data.get('leadData', {})
        
        # Primeiro, criar o cliente
        customer_response = create_customer()
        customer_data = customer_response[0].get_json()
        
        if customer_response[1] != 200:
            return jsonify({"error": "Erro ao criar cliente"}), 500
        
        customer_id = customer_data.get('customerId')
        
        # Criar cobrança PIX
        payment_data = {
            "customer": customer_id,
            "billingType": "PIX",
            "value": 19.90,
            "dueDate": datetime.now().strftime('%Y-%m-%d'),
            "description": "Teste de QI Profissional - Resultado Completo",
            "externalReference": f"pix_{lead_data.get('email', '')}_{datetime.now().timestamp()}",
            "postalService": False
        }
        
        response = requests.post(
            f'{ASAAS_API_URL}/payments',
            json=payment_data,
            headers=get_headers()
        )
        
        if response.status_code == 200:
            payment = response.json()
            payment_id = payment.get('id')
            
            # Obter QR Code PIX
            qr_response = requests.get(
                f'{ASAAS_API_URL}/payments/{payment_id}/pixQrCode',
                headers=get_headers()
            )
            
            if qr_response.status_code == 200:
                qr_data = qr_response.json()
                
                return jsonify({
                    "paymentId": payment_id,
                    "status": payment.get('status'),
                    "qrCode": qr_data.get('payload', ''),
                    "qrCodeBase64": qr_data.get('encodedImage', ''),
                    "invoiceUrl": payment.get('invoiceUrl', ''),
                    "value": payment.get('value')
                }), 200
            else:
                print(f"Erro ao obter QR Code: {qr_response.text}")
                return jsonify({"error": "Erro ao gerar QR Code"}), 500
        else:
            print(f"Erro ao criar cobrança: {response.text}")
            return jsonify({"error": response.text}), response.status_code
            
    except Exception as e:
        print(f"Erro ao criar pagamento PIX: {str(e)}")
        return jsonify({"error": str(e)}), 500


@payment_asaas_bp.route('/api/asaas/create_card_payment', methods=['POST'])
def create_card_payment():
    """
    Cria uma cobrança com cartão de crédito no Asaas
    Retorna URL para checkout
    """
    try:
        data = request.json
        lead_data = data.get('leadData', {})
        
        # Criar cliente
        customer_response = create_customer()
        customer_data = customer_response[0].get_json()
        
        if customer_response[1] != 200:
            return jsonify({"error": "Erro ao criar cliente"}), 500
        
        customer_id = customer_data.get('customerId')
        
        # Criar cobrança com cartão
        payment_data = {
            "customer": customer_id,
            "billingType": "CREDIT_CARD",
            "value": 19.90,
            "dueDate": datetime.now().strftime('%Y-%m-%d'),
            "description": "Teste de QI Profissional - Resultado Completo",
            "externalReference": f"card_{lead_data.get('email', '')}_{datetime.now().timestamp()}"
        }
        
        response = requests.post(
            f'{ASAAS_API_URL}/payments',
            json=payment_data,
            headers=get_headers()
        )
        
        if response.status_code == 200:
            payment = response.json()
            
            return jsonify({
                "paymentId": payment.get('id'),
                "status": payment.get('status'),
                "invoiceUrl": payment.get('invoiceUrl', ''),
                "bankSlipUrl": payment.get('bankSlipUrl', ''),
                "value": payment.get('value')
            }), 200
        else:
            print(f"Erro ao criar cobrança: {response.text}")
            return jsonify({"error": response.text}), response.status_code
            
    except Exception as e:
        print(f"Erro ao criar pagamento com cartão: {str(e)}")
        return jsonify({"error": str(e)}), 500


@payment_asaas_bp.route('/api/asaas/check_payment_status/<payment_id>', methods=['GET'])
def check_payment_status(payment_id):
    """
    Verifica o status de um pagamento
    """
    try:
        response = requests.get(
            f'{ASAAS_API_URL}/payments/{payment_id}',
            headers=get_headers()
        )
        
        if response.status_code == 200:
            payment = response.json()
            status = payment.get('status')
            
            return jsonify({
                "status": status,
                "statusDetail": payment.get('description', ''),
                "approved": status in ['RECEIVED', 'CONFIRMED'],
                "value": payment.get('value'),
                "paymentDate": payment.get('paymentDate')
            }), 200
        else:
            print(f"Erro ao verificar status: {response.text}")
            return jsonify({"error": response.text}), response.status_code
            
    except Exception as e:
        print(f"Erro ao verificar status: {str(e)}")
        return jsonify({"error": str(e)}), 500


@payment_asaas_bp.route('/api/asaas/webhook', methods=['POST'])
def webhook():
    """
    Recebe notificações do Asaas sobre mudanças no status do pagamento
    """
    try:
        data = request.json
        
        # Log da notificação
        print(f"Webhook Asaas recebido: {data}")
        
        event = data.get('event')
        payment_data = data.get('payment', {})
        
        if event == 'PAYMENT_RECEIVED' or event == 'PAYMENT_CONFIRMED':
            payment_id = payment_data.get('id')
            customer_email = payment_data.get('customer', {}).get('email')
            
            print(f"Pagamento {payment_id} recebido! Email: {customer_email}")
            
            # Aqui você pode:
            # 1. Salvar no banco de dados
            # 2. Enviar email para o cliente
            # 3. Liberar acesso ao resultado
            # 4. Atualizar status do lead
        
        return jsonify({"status": "received"}), 200
        
    except Exception as e:
        print(f"Erro no webhook: {str(e)}")
        return jsonify({"error": str(e)}), 500


@payment_asaas_bp.route('/payment/success', methods=['GET'])
def payment_success():
    """
    Página de sucesso após pagamento
    """
    payment_id = request.args.get('payment_id')
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pagamento Aprovado</title>
        <script>
            window.location.href = '/?payment=success&payment_id={payment_id}';
        </script>
    </head>
    <body>
        <p>Redirecionando...</p>
    </body>
    </html>
    """


@payment_asaas_bp.route('/payment/failure', methods=['GET'])
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


