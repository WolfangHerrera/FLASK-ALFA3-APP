from flask import Flask
from flask_cors import CORS

from core.controller.item.item import ITEM
from core.controller.user.user import USER

APP = Flask(__name__)
APP.register_blueprint(USER)
APP.register_blueprint(ITEM)

CORS(APP)

@APP.route('/')
def hello_world():
    return 'Hello, World!'


if __name__ == "__main__":
    APP.run(host='0.0.0.0', port=8081, debug=True)