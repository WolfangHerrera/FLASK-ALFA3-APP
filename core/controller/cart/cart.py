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

URL_IMAGES = {
    "NEQUI": "https://alfa3-assets.s3.us-east-1.amazonaws.com/qr_nequi.jpg",
    "DAVIPLATA": "https://alfa3-assets.s3.us-east-1.amazonaws.com/qr_daviplata.jpg",
    "BANCOLOMBIA": "https://alfa3-assets.s3.us-east-1.amazonaws.com/qr_bancolombia.jpg",
    "MELI": "https://alfa3-assets.s3.us-east-1.amazonaws.com/qr_meli.jpg",
}

CART = Blueprint('CART', __name__)


@CART.route("/createOrder", methods=['POST'])
def create_order():
    data = request.get_json()
    if not data or 'PRODUCTS_CART' not in data or 'CUSTOMER_DETAILS' not in data:
        return jsonify({"ERROR": "MISSING 'PRODUCTS_CART' OR 'CUSTOMER_DETAILS'"}), HTTPStatus.BAD_REQUEST

    phone_customer = data['CUSTOMER_DETAILS']['phoneNumberCustomer']
    customer_id = data['CUSTOMER_DETAILS']['documentNumberCustomer']
    colombia_tz = pytz.timezone('America/Bogota')
    now = datetime.now(colombia_tz)
    date = now.strftime('%Y%m%d-%H%M')
    order_id = 'A3-' + date + '-' + phone_customer[-4:]
    table = getSession().Table('orders')
    response = table.put_item(Item={
        'order_id': order_id,
        'customer_id': str(customer_id),
        'products_cart': data['PRODUCTS_CART'],
        'customer_details': data['CUSTOMER_DETAILS'],
        'status': 'IN_PROGRESS',
        'sub_status': 'NOT_PAID',
        'total_price': data['TOTAL_PRICE'],
        'total_price_min': data['TOTAL_PRICE_MIN'],
        'item_count': data['ITEM_COUNT'],
    })
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        numbers_to_send = os.environ.get('NUMBERS_PHONE', 'NOTHINGTOSEEHERE')
        for number in numbers_to_send.split(','):
            logger.info(f"Enviando notificación a: {number}")
            whatsapp_response = send_whatsapp_notification(number, '',order_id, 'in_progress')
            logger.info(f"Respuesta de WhatsApp: {whatsapp_response}")
        
        paymenthod = data['CUSTOMER_DETAILS']['paymentMethodCustomer']

        if validate_payment_method_mercadopago(paymenthod) :
            status = 'MP'
            url_payment = generate_url_mercadopago(data['PRODUCTS_CART'], order_id, data['CUSTOMER_DETAILS'])
        else:
            status = 'NOT_MP'
            whatsapp_response = send_whatsapp_notification(phone_customer, {'price' : data['TOTAL_PRICE'], 'paymenthod' : paymenthod}, order_id, 'payment')
            logger.info(f"Respuesta de WhatsApp: {whatsapp_response}")
            url_payment = '/order/{order_id}'.format(order_id=order_id)

        return jsonify({"ORDER_ID": order_id, "STATUS" : status, "URL_PAYMENT": url_payment}), HTTPStatus.OK
    else:
        return jsonify({"ERROR": "ERROR CREATING ORDER"}), HTTPStatus.INTERNAL_SERVER_ERROR


@CART.route("/webhook/MercadoPago", methods=['POST'])
def webhook_mercadopago():
    try:
        data = request.json

        if 'type' not in data or data['type'] != 'payment':
            return jsonify({"ERROR": "INVALID WEBHOOK EVENT"}), HTTPStatus.BAD_REQUEST

        payment_id = data['data']['id']

        sdk = mercadopago.SDK(os.environ.get(
            'MP_ACCESS_TOKEN', 'NOTHINGTOSEEHERE'))
        payment_info = sdk.payment().get(payment_id)

        if payment_info['status'] == 200:
            payment_status = payment_info['response']['status']
            external_reference = payment_info['response']['external_reference']
            logger.info(
                f"Actualizando estado de la orden: {external_reference} a {payment_status}")
            table = getSession().Table('orders')
            response = table.update_item(
                Key={'order_id': external_reference},
                UpdateExpression="set #s = :s",
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={
                    ':s': 'CONFIRMED' if payment_status == 'approved' else 'FAILED'},
                ReturnValues="UPDATED_NEW"
            )

            if payment_status == 'approved':
                order_info = table.get_item(
                    Key={'order_id': external_reference})
                if 'Item' in order_info:
                    customer_details = order_info['Item'].get(
                        'customer_details', {})
                    whatsapp_response = send_whatsapp_notification(
                        customer_details['phoneNumberCustomer'], '', external_reference,'confirmed')
                    if whatsapp_response.get('messages'):
                        return jsonify({"STATUS": "PAYMENT STATUS UPDATED"}), HTTPStatus.OK
                    else:
                        return jsonify({"ERROR": "ERROR CREATING ORDER"}), HTTPStatus.INTERNAL_SERVER_ERROR

            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                return jsonify({"STATUS": "PAYMENT STATUS UPDATED"}), HTTPStatus.OK
            else:
                return jsonify({"ERROR": "ERROR UPDATING PAYMENT STATUS"}), HTTPStatus.INTERNAL_SERVER_ERROR
        else:
            return jsonify({"ERROR": "ERROR FETCHING PAYMENT INFO"}), HTTPStatus.INTERNAL_SERVER_ERROR

    except Exception as e:
        return jsonify({"ERROR": "INTERNAL SERVER ERROR"}), HTTPStatus.INTERNAL_SERVER_ERROR


def generate_url_mercadopago(productsCart, order_id, customerDetails):
    sdk = mercadopago.SDK(os.environ.get(
        'MP_ACCESS_TOKEN', 'NOTHINGTOSEEHERE'))
    items = []
    for product in productsCart:
        items.append({
            "title": product["item_name"],
            "quantity": int(product["count"]),
            "unit_price": float(product["price"])
        })

    preference_data = {
        "items": items,
        "payer": {
            "name": customerDetails['fullNameCustomer'],
            "email": customerDetails['emailCustomer'],
            "phone": {
                "area_code": "57",
                "number": customerDetails['phoneNumberCustomer']
            },
            "identification": {
                "type": customerDetails['documentTypeCustomer'],
                "number": customerDetails['documentNumberCustomer']
            },
            "address": {
                "street_name": customerDetails['streetAddressCustomer'],
            }
        },
        "back_urls": {
            "success": "https://alfa3electricos.com/order/{order_id}".format(order_id=order_id),
            "failure": "https://alfa3electricos.com/order/{order_id}".format(order_id=order_id),
            "pending": "https://alfa3electricos.com/order/{order_id}".format(order_id=order_id)
        },
        "auto_return": "approved",
        "notification_url": "https://backend.alfa3electricos.com/webhook/MercadoPago",
        "external_reference": order_id
    }
    preference_response = sdk.preference().create(preference_data)
    return preference_response['response']['init_point']


def send_whatsapp_notification(to, message, order_id, template_name):
    url = "https://graph.facebook.com/v22.0/{idPhone}/messages".format(
        idPhone=os.environ.get('ID_PHONE', 'NOTHINGTOSEEHERE'))
    headers = {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer {token}'.format(token=os.environ.get('TOKEN_PHONE', 'NOTHINGTOSEEHERE'))
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": "57{to}".format(to=to),
        "type": "template",
        "template": {
            "name": template_name,
            "language": {
                "code": "es_CO"
            },
            "components": []
        }
    }
    if template_name == 'in_progress':
         payload['template']['components'] = [
                    {
                        "type": "button",
                        "sub_type": "url",
                        "index": 0,
                        "parameters": [
                            {
                                "type": "text",
                                "text": "order/{message}".format(message=order_id),
                            }
                        ]
                    }
                ]
         
    elif template_name == 'payment':
         payload['template']['components'] = [
                    {
                        "type": "header",
                        "parameters": [
                            {
                                "type": "image",
                                "image": {
                                    "link": URL_IMAGES[message['paymenthod']]
                                }
                            }
                        ]
                    },
                    {
                        "type": "body",
                        "parameters": [
                            {
                                "type": "text",
                                "text": message['paymenthod']
                            },
                            {
                                "type": "text",
                                "text": format_number_with_commas(message['price'])
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
                                "text": "order/{order_id}".format(order_id=order_id)
                            }
                        ]
                    },
                    {
                        "type": "button",
                        "sub_type": "url",
                        "index": 1,
                        "parameters": [
                            {
                                "type": "text",
                                "text": "order/{order_id}".format(order_id=order_id)
                            }
                        ]
                    }
                ]
    else:
        payload['template']['components'] = [
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
                                "text": "order/{message}".format(message=order_id),
                            }
                        ]
                    }
                ]
        
    logger.info(f"PayLOAD WHASTAPP: {payload}")
    response = requests.post(url, json=payload, headers=headers)
    return response.json()


def format_number_with_commas(number_str):
        return "{:,}".format(int(number_str))



def validate_payment_method_mercadopago(payment_method):
    mp_payment_methods = ['CARD', 'ACCOUNT']
    if payment_method not in mp_payment_methods:
        return False
    return True