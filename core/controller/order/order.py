from flask import Blueprint
from http import HTTPStatus
from flask import jsonify
import logging

from core.config.aws_config import getSession

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ORDER = Blueprint('ORDER', __name__)


@ORDER.route("/getOrder/<order_id>", methods=['GET'])
def get_order(order_id):
    if not order_id:
        return jsonify({"ERROR": "MISSING 'ORDER ID'"}), HTTPStatus.BAD_REQUEST
    
    table = getSession().Table('orders')
    response = table.get_item(Key={'order_id': order_id})
    if 'Item' in response:
        return jsonify(response['Item']), HTTPStatus.OK
    else:
        return jsonify({"ERROR": "ORDER NOT FOUND"}), HTTPStatus.NOT_FOUND


@ORDER.route("/getOrders/<order_id>/customer/<customer_id>", methods=['GET'])
def get_orders(order_id, customer_id):
    if not order_id or not customer_id:
        return jsonify({"ERROR": "MISSING 'ORDER ID' OR 'CUSTOMER ID'"}), HTTPStatus.BAD_REQUEST
    
    table = getSession().Table('orders')
    response = table.get_item(
        Key={
            'order_id': order_id,
            'customer_id': customer_id
        }
    )
    if 'Item' in response:
        return jsonify(response['Item']), HTTPStatus.OK
    else:
        return jsonify({"ERROR": "ORDER NOT FOUND"}), HTTPStatus.NOT_FOUND