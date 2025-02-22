import os
from flask import Blueprint
import uuid
from http import HTTPStatus
from flask import request, jsonify

from core.config.aws_config import getSession
from datetime import datetime
import pytz
import requests


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

    table = getSession().Table('orders')
    response = table.put_item(Item={
        'order_id': order_id,
        'products_cart': data['PRODUCTS_CART'],
        'customer_details': data['CUSTOMER_DETAILS'],
        'status': 'CONFIRMED',
        'total_price': data['TOTAL_PRICE']
    })
    if response['ResponseMetadata']['HTTPStatusCode'] == 200:
        whatsapp_response = sendWhatsAppNotification(phone_customer, order_id)
        if whatsapp_response.get('messages'):
            return jsonify({"ORDER_ID": order_id}), HTTPStatus.OK
    else:
        return jsonify({"ERROR": "ERROR CREATING ORDER"}), HTTPStatus.INTERNAL_SERVER_ERROR


@ORDER.route("/getOrder/<order_id>", methods=['GET'])
def getOrder(order_id):
    table = getSession().Table('orders')
    response = table.get_item(Key={'order_id': order_id})
    if 'Item' in response:
        return jsonify(response['Item']), HTTPStatus.OK
    else:
        return jsonify({"ERROR": "ORDER NOT FOUND"}), HTTPStatus.NOT_FOUND


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
                "code": "es_CO"
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
