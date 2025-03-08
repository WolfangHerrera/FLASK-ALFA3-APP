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

    else:
        return jsonify({"ERROR": "ERROR CREATING ORDER"}), HTTPStatus.INTERNAL_SERVER_ERROR



@ORDER.route("/webhook/MercadoPago", methods=['POST'])
def WebhookMercadoPago():
    try:
        data = request.json
        logger.info(f"Received webhook data: {data}")
        
        if 'type' not in data or data['type'] != 'payment':
            logger.info("Invalid webhook event type")
            return jsonify({"ERROR": "INVALID WEBHOOK EVENT"}), HTTPStatus.BAD_REQUEST

        payment_id = data['data']['id']
        logger.info(f"Processing payment ID: {payment_id}")
        
        sdk = mercadopago.SDK(os.environ.get('MP_ACCESS_TOKEN', 'NOTHINGTOSEEHERE'))
        payment_info = sdk.payment().get(payment_id)

        if payment_info['status'] == 200:
            payment_status = payment_info['response']['status']
            external_reference = payment_info['response']['external_reference']
            logger.info(f"Payment status: {payment_status}, External reference: {external_reference}")

            table = getSession().Table('orders')
            response = table.update_item(
                Key={'order_id': external_reference},
                UpdateExpression="set #s = :s",
                ExpressionAttributeNames={'#s': 'status'},
                ExpressionAttributeValues={':s': 'CONFIRMED' if payment_status == 'approved' else 'REJECTED'},
                ReturnValues="UPDATED_NEW"
            )

            if payment_status == 'approved':
                order_info = table.get_item(Key={'order_id': external_reference})
                if 'Item' in order_info:
                    customer_details = order_info['Item'].get('customer_details', {})
                    logger.info(f"Customer details: {customer_details}")
                    whatsapp_response = sendWhatsAppNotification(customer_details['phoneNumberCustomer'], external_reference)
                    if whatsapp_response.get('messages'):
                        return jsonify({"STATUS": "PAYMENT STATUS UPDATED"}), HTTPStatus.OK
                    else:
                        return jsonify({"ERROR": "ERROR CREATING ORDER"}), HTTPStatus.INTERNAL_SERVER_ERROR

            if response['ResponseMetadata']['HTTPStatusCode'] == 200:
                logger.info("Payment status updated successfully")
                return jsonify({"STATUS": "PAYMENT STATUS UPDATED"}), HTTPStatus.OK
            else:
                logger.info("Error updating payment status")
                return jsonify({"ERROR": "ERROR UPDATING PAYMENT STATUS"}), HTTPStatus.INTERNAL_SERVER_ERROR
        else:
            logger.info("Error fetching payment info")
            return jsonify({"ERROR": "ERROR FETCHING PAYMENT INFO"}), HTTPStatus.INTERNAL_SERVER_ERROR

    except Exception as e:
        logger.info(f"*** *** *** Error processing MercadoPago webhook: {str(e)}")
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