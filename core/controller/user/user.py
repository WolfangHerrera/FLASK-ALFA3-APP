from flask import Blueprint
import uuid
from http import HTTPStatus
from flask import request, jsonify

from core.config.aws_config import createTable, getSession
from core.utils.user.user import generateHashForPassword, setRolByName, validatePassword


USER = Blueprint('USER', __name__)

def registerUser():
    data = request.get_json()
    if not data or 'USERNAME' not in data or 'PASSWORD' not in data:
        return jsonify({"MESSAGE": "MISSING 'USER' OR 'PASSWORD'"}), HTTPStatus.BAD_REQUEST
    
    table = getSession().Table('users')
        
    response = table.put_item(
        Item={
            'username': data['USERNAME'],
            'password': generateHashForPassword(data['PASSWORD']),
            'role': setRolByName(data['USERNAME']),
        }
    )

    return response, HTTPStatus.OK


@USER.route("/loginUser", methods=['POST'])
def login():
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