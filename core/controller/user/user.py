import logging
from flask import Blueprint
from http import HTTPStatus
from flask import request, jsonify

from core.config.aws_config import getSession
from core.utils.user.user import generateHashForPassword, setRolByName, validatePassword

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

USER = Blueprint('USER', __name__)

@USER.route("/registerUser", methods=['POST'])
def registerUser():
    data = request.get_json()
    if not data or 'USERNAME' not in data or 'PASSWORD' not in data:
        return jsonify({"MESSAGE": "MISSING 'USER' OR 'PASSWORD'"}), HTTPStatus.BAD_REQUEST
    
    logger.info(f"DATA -- REGISTER: {data}")
    table = getSession().Table('users')

    existing_user = table.get_item(
        Key={
            'username': data['USERNAME']
        }
    )

    logger.info(f"EXISTING USER: {existing_user}")
    
    if 'Item' in existing_user:
        return jsonify({"MESSAGE": "USER ALREADY EXIST"}), HTTPStatus.NOT_FOUND
        
    try:
        response = table.put_item(
            Item={
                'username': data['USERNAME'],
                'password': generateHashForPassword(data['PASSWORD']),
            }
        )
        logger.info(f"RESPONSE: {response}")
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return jsonify({"MESSAGE": "USER REGISTER SUCCESSFUL"}), HTTPStatus.CREATED
        else:
            return jsonify({"MESSAGE": "FAILED TO REGISTER USER"}), HTTPStatus.INTERNAL_SERVER_ERROR
        
    except Exception as e:
        return jsonify({"MESSAGE": f"ERROR: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR


@USER.route("/loginUser", methods=['POST'])
def loginUser():
    data = request.get_json()
    if not data or 'USERNAME' not in data or 'PASSWORD' not in data:
        return jsonify({"MESSAGE": "MISSING 'USER' OR 'PASSWORD'"}), HTTPStatus.BAD_REQUEST
    
    table = getSession().Table('users')
    
    response = table.get_item(
        Key={
            'username': data['USERNAME']
        }
    )
    
    if 'Item' not in response:
        return jsonify({"MESSAGE": "USER NOT EXIST"}), HTTPStatus.NOT_FOUND
    
    if not validatePassword(data['PASSWORD'], response['Item']['password']):
        return jsonify({"MESSAGE": "INVALID PASSWORD"}), HTTPStatus.UNAUTHORIZED
    
    return jsonify(response['Item']), HTTPStatus.OK


@USER.route("/updateUser", methods=['PUT'])
def updateUser():
    data = request.get_json()
    if not data or 'USERNAME' not in data:
        return jsonify({"MESSAGE": "MISSING 'USER' OR 'PASSWORD'"}), HTTPStatus.BAD_REQUEST
    
    table = getSession().Table('users')
    
    response = table.get_item(
        Key={
            'username': data['USERNAME']
        }
    )
    
    if 'Item' not in response:
        return jsonify({"MESSAGE": "USER NOT EXIST"}), HTTPStatus.NOT_FOUND
    
    try:
        response = table.update_item(
            Key={
                'username': data['USERNAME']
            },
            UpdateExpression="SET customer_details = :customer_details",
            ExpressionAttributeValues={
                ':customer_details': data['CUSTOMER_DETAILS']
            }
        )
        logger.info(f"RESPONSE: {response}")
        if response['ResponseMetadata']['HTTPStatusCode'] == 200:
            return jsonify({"MESSAGE": "USER UPDATED SUCCESSFUL"}), HTTPStatus.OK
        else:
            return jsonify({"MESSAGE": "FAILED TO UPDATE USER"}), HTTPStatus.INTERNAL_SERVER_ERROR
        
    except Exception as e:
        return jsonify({"MESSAGE": f"ERROR: {str(e)}"}), HTTPStatus.INTERNAL_SERVER_ERROR
