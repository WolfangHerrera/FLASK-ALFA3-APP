import logging
from flask import Flask, request
from flask_cors import CORS

from core.controller.item.item import ITEM
from core.controller.order.order import ORDER
from core.controller.user.user import USER

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.register_blueprint(USER)
app.register_blueprint(ITEM)
app.register_blueprint(ORDER)

CORS(app, origins=["https://www.alfa3electricos.com", "https://alfa3electricos.com", "https://mercadopago.com.ar"])

@app.after_request
def after_request(response):
    logger.info(f"RESPONSE AFTER REQUEST *****: {response}")
    origin = request.headers.get('Origin')
    if origin in ["https://www.alfa3electricos.com", "https://alfa3electricos.com", "https://mercadopago.com.ar"]:
        response.headers.add('Access-Control-Allow-Origin', origin)
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    return response

@app.route('/')
def hello_world():
    return 'Hello World! from WOLFANGDEVS.COM'

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8081, debug=True)
