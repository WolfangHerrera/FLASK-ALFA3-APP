from flask import Blueprint
import uuid
from http import HTTPStatus
from flask import request, jsonify

from core.config.aws_config import createTable, getSession
from core.utils.user.user import generateHashForPassword, setRolByName, validatePassword


ITEM = Blueprint('ITEM', __name__)

@ITEM.route("/createItem", methods=['POST'])
def createItem():
    data = request.get_json()
    if not data or 'ITEM_NAME' not in data or 'PRICE' not in data:
        return jsonify({"ERROR": "MISSING 'NAME' OR 'PRICE'"}), HTTPStatus.BAD_REQUEST
    
    table = getSession().Table('items')
        
    response = table.put_item(
        Item={
            'item_id': data['ITEM_ID'],
            'item_name': data['ITEM_NAME'],
            'item_description': data['ITEM_DESCRIPTION'],
            'price': data['PRICE'],
            'img_url': data['IMG_URL'],
        }
    )

    return response, HTTPStatus.OK


@ITEM.route("/getItems", methods=['GET'])
def getItems():
    table = getSession().Table('items')
    response = table.scan()
    
    return jsonify(response['Items']), HTTPStatus.OK


@ITEM.route("/getItemById", methods=['GET'])
def getItemById():
    data = request.get_json()
    if not data or 'ITEM_ID' not in data:
        return jsonify({"ERROR": "MISSING 'ITEM_ID'"}), HTTPStatus.BAD_REQUEST
    
    table = getSession().Table('items')
    response = table.get_item(
        Key={
            'item_id': data['ITEM_ID']
        }
    )
    
    return jsonify(response['Item']), HTTPStatus.OK


@ITEM.route("/updateItem", methods=['PUT'])
def updateItem():
    data = request.get_json()
    if not data or 'ITEM_ID' not in data:
        return jsonify({"ERROR": "MISSING 'ITEM_ID'"}), HTTPStatus.BAD_REQUEST
    
    table = getSession().Table('items')
    response = table.update_item(
        Key={
            'item_id': data['ITEM_ID']
        },
        UpdateExpression='SET item_name = :item_name, price = :price, img_url = :img_url, item_description = :item_description',
        ExpressionAttributeValues={
            ':item_name': data['ITEM_NAME'],
            ':item_description': data['ITEM_DESCRIPTION'],
            ':price': data['PRICE'],
            ':img_url': data['IMG_URL'],
        }
    )
    
    return response, HTTPStatus.OK


@ITEM.route("/deleteItem", methods=['DELETE'])
def deleteItem():
    data = request.get_json()
    if not data or 'ITEM_ID' not in data:
        return jsonify({"ERROR": "MISSING 'ITEM_ID'"}), HTTPStatus.BAD_REQUEST
    
    table = getSession().Table('items')
    response = table.delete_item(
        Key={
            'item_id': data['ITEM_ID']
        }
    )
    
    return response, HTTPStatus.OK