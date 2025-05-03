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
    table = getSession().Table('orders')
    response = table.get_item(Key={'order_id': order_id})
    if 'Item' in response:
        return jsonify(response['Item']), HTTPStatus.OK
    else:
        return jsonify({"ERROR": "ORDER NOT FOUND"}), HTTPStatus.NOT_FOUND
