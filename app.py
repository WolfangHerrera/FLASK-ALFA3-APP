import logging
from flask import Flask, request
from flask_cors import CORS

from core.controller.item.item import ITEM
from core.controller.order.order import ORDER
from core.controller.user.user import USER


app = Flask(__name__)
app.register_blueprint(USER)
app.register_blueprint(ITEM)
app.register_blueprint(ORDER)

CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
# CORS(app, origins=["https://alfa3.wolfangdevs.com", "https://alfa3electricos.com", "https://mercadopago.com"])

@app.route('/')
def hello_world():
    return 'Hello World! from WOLFANGDEVS.COM'

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8081, debug=True)
