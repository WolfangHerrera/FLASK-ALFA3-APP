import os
from flask import Blueprint
import mercadopago
from http import HTTPStatus
from flask import request, jsonify

from core.config.aws_config import getSession
from datetime import datetime
import pytz
import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


ORDER = Blueprint('ORDER', __name__)


@ORDER.route("/createOrder", methods=['POST'])
def createOrder():
    data = request.get_json()
    if not data or 'PRODUCTS_CART' not in data or 'CUSTOMER_DETAILS' not in data:
        return jsonify({"ERROR": "MISSING 'PRODUCTS_CART' OR 'CUSTOMER_DETAILS'"}), HTTPStatus.BAD_REQUEST
    
    phone_customer = data['CUSTOMER_DETAILS']['phoneNumberCustomer']
    colombia_tz = pytz.timezone('America/Bogota')
    now = datetime.now(colombia_tz)
    date = now.strftime('%Y%m%d-%H%M')
    order_id = 'A3-' + date + '-' + phone_customer[-4:]
    url_payment = generateOrderMP(data['PRODUCTS_CART'], order_id)
    table = getSession().Table('orders')
    response = table.put_item(Item={
        'order_id': order_id,
        'products_cart': data['PRODUCTS_CART'],
        'customer_details': data['CUSTOMER_DETAILS'],
        'status': 'IN PROGRESS',
        'total_price': data['TOTAL_PRICE']
    })
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        return jsonify({"ORDER_ID": order_id, "URL_PAYMENT": url_payment}), HTTPStatus.OK
        whatsapp_response = sendWhatsAppNotification(phone_customer, order_id)
        if whatsapp_response.get('messages'):
            pass
        else:
            return jsonify({"ERROR": "ERROR CREATING ORDER"}), HTTPStatus.INTERNAL_SERVER_ERROR
    else:
        return jsonify({"ERROR": "ERROR CREATING ORDER"}), HTTPStatus.INTERNAL_SERVER_ERROR



@ORDER.route("/webhook/MercadoPago", methods=['POST'])
def WebhookMercadoPago():
    try:
        data = request.get_json()
        logger.info(f"DATA***: {data}")
        
        if request.is_json:
            topic = data.get('topic')
        if topic is None:
            return jsonify({"error": "Faltando el campo 'topic'"}), 400

        # Procesar según el tipo de evento
        if topic == 'payment':
            # Lógica para el evento 'payment'
            action = data.get('action')
            payment_id = data.get('data', {}).get('id')
            
            if action == 'payment.created':
                logger.info(f"Pago creado con ID: {payment_id}")
                # Aquí puedes consultar la API de MercadoPago para obtener el estado del pago
                sdk = mercadopago.SDK(os.environ.get('MP_ACCESS_TOKEN', 'NOTHINGTOSEEHERE'))
                payment_info = sdk.payment().get(payment_id)

                # Verificar el estado del pago
                payment_status = payment_info['response']['status']
                if payment_status == 'approved':
                    logger.info(f"Pago aprobado: {payment_id}")
                    # Aquí podrías actualizar el estado de la orden en tu base de datos
                else:
                    logger.info(f"Pago no aprobado: {payment_id}, estado: {payment_status}")
            
            elif action == 'payment.updated':
                logger.info(f"Pago actualizado con ID: {payment_id}")
                sdk = mercadopago.SDK(os.environ.get('MP_ACCESS_TOKEN', 'NOTHINGTOSEEHERE'))
                payment_info = sdk.payment().get(payment_id)
                payment_status = payment_info['response']['status']
                if payment_status == 'approved':
                    logger.info(f"Pago aprobado: {payment_id}")
                    # Aquí puedes actualizar el estado de la orden en tu base de datos
                else:
                    logger.info(f"Pago no aprobado: {payment_id}, estado: {payment_status}")
            
        elif topic == 'merchant_order':
            # Lógica para el evento 'merchant_order'
            resource = data.get('resource')
            if resource:
                logger.info(f"Orden de comerciante actualizada: {resource}")
                # Aquí puedes hacer una consulta a la API de MercadoPago para obtener los detalles de la orden
                sdk = mercadopago.SDK(os.environ.get('MP_ACCESS_TOKEN', 'NOTHINGTOSEEHERE'))
                order_info = sdk.merchant_order().get(resource)
                order_status = order_info['response']['status']
                if order_status == 'approved':
                    logger.info(f"Orden aprobada: {resource}")
                    # Aquí podrías actualizar la orden en tu sistema
                else:
                    logger.info(f"Orden no aprobada: {resource}, estado: {order_status}")

        else:
            logger.info(f"Evento no reconocido con 'topic': {topic}")
            return jsonify({"error": "Evento no reconocido"}), 400

        return jsonify({"status": "success"}), 200

    except Exception as e:
        logger.info(f"*** *** *** Error al procesar el webhook de MercadoPago: {str(e)}")
        return jsonify({"ERROR": "INTERNAL SERVER ERROR"}), HTTPStatus.INTERNAL_SERVER_ERROR


@ORDER.route("/getOrder/<order_id>", methods=['GET'])
def getOrder(order_id):
    logger.info(f"Buscando orden con ID: {order_id}")
    table = getSession().Table('orders')
    response = table.get_item(Key={'order_id': order_id})
    if 'Item' in response:
        return jsonify(response['Item']), HTTPStatus.OK
    else:
        return jsonify({"ERROR": "ORDER NOT FOUND"}), HTTPStatus.NOT_FOUND


def generateOrderMP(productsCart, order_id):
    sdk = mercadopago.SDK(os.environ.get('MP_ACCESS_TOKEN', 'NOTHINGTOSEEHERE'))
    items = []
    for product in productsCart:
        items.append({
            "title": product["item_name"],
            "quantity": int(product["count"]),
            "unit_price": float(product["price"])
        })

    preference_data = {
        "items": items,
        "back_urls": {
            "success": "https://alfa3electricos.com/order/{order_id}".format(order_id=order_id),
            "failure": "https://alfa3electricos.com/order/{order_id}".format(order_id=order_id),
            "pending": "https://alfa3electricos.com/order/{order_id}".format(order_id=order_id)
        },
        "auto_return": "approved",
        "notification_url": "https://alfa3-flask-fd769661555f.herokuapp.com/webhook/MercadoPago",
        "external_reference": order_id
    }
    preference_response = sdk.preference().create(preference_data)
    return preference_response['response']['init_point']


def sendWhatsAppNotification(to, message):
    url = "https://graph.facebook.com/v22.0/{idPhone}/messages".format(idPhone=os.environ.get('ID_PHONE', 'NOTHINGTOSEEHERE'))
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {token}'.format(token=os.environ.get('TOKEN_PHONE', 'NOTHINGTOSEEHERE'))
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": "57{to}".format(to=to),
        "type": "template",
        "template": {
            "name": "confirmed",
            "language": {
                "code": "en_US"
            },
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "text": message
                        }
                    ]
                },
                {
                    "type": "button",
                    "sub_type": "url",
                    "index": 0,
                    "parameters": [
                        {
                            "type": "text",
                            "text": "order/{message}".format(message=message),
                        }
                    ]
                }
            ]
        }
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()