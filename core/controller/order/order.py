from flask import Blueprint, request
from http import HTTPStatus
from flask import jsonify
import logging
from boto3.dynamodb.conditions import Key

from core.config.aws_config import getSession, createTable

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
    

@ORDER.route("/updateOrdersWithSubStatus/<status>", methods=['PUT'])
def update_order(status):
    list_orders = request.get_json()
    if not list_orders or not status:
        return jsonify({"ERROR": "MISSING 'ORDER ID' OR 'STATUS'"}), HTTPStatus.BAD_REQUEST
    
    print(list_orders)
    for order_id in list_orders['LIST_ORDERS']:        
        table = getSession().Table('orders')
        response = table.get_item(Key={'order_id': order_id})
        
        if 'Item' in response:
            item = response['Item']
            item['sub_status'] = status
            table.put_item(Item=item)
            print(f"Updated order {order_id} with status {status}")


    return jsonify(item), HTTPStatus.OK
    

@ORDER.route("/getOrdersBySubStatus/<sub_status>", methods=['GET'])
def get_orders_by_sub_status(sub_status):
    if not sub_status:
        return jsonify({"ERROR": "MISSING 'SUB STATUS'"}), HTTPStatus.BAD_REQUEST
    
    table = getSession().Table('orders')
    response = table.query(
        IndexName='SubStatusIndex',
        KeyConditionExpression=Key('sub_status').eq(sub_status)
    )
    
    if 'Items' in response:
        return jsonify(response['Items']), HTTPStatus.OK
    else:
        return jsonify({"ERROR": "ORDER NOT FOUND"}), HTTPStatus.NOT_FOUND


@ORDER.route("/getOrdersByCustomerId/<customer_id>", methods=['GET'])
def get_order_by_customerid(customer_id):
    if not customer_id:
        return jsonify({"ERROR": "MISSING 'CUSTOMER ID'"}), HTTPStatus.BAD_REQUEST
    
    table = getSession().Table('orders')
    response = table.query(
        IndexName='CustomerIndex',
        KeyConditionExpression=Key('customer_id').eq(customer_id)
    )
    
    if 'Items' in response:
        return jsonify(response['Items']), HTTPStatus.OK
    else:
        return jsonify({"ERROR": "ORDER NOT FOUND"}), HTTPStatus.NOT_FOUND
    