from flask import Flask
from flask_cors import CORS


from core.controller.item.item import ITEM
from core.controller.order.order import ORDER
from core.controller.user.user import USER

app = Flask(__name__)
app.register_blueprint(USER)
app.register_blueprint(ITEM)
app.register_blueprint(ORDER)

CORS(app, origins=["https://www.alfa3electricos.com"])

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', 'https://www.alfa3electricos.com')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
    return response

@app.route('/')
def hello_world():
    return 'Hello World! from WOLFANGDEVS.COM'


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8081, debug=True)