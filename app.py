from flask import Flask
from flask_cors import CORS

from core.controller.item.item import ITEM
from core.controller.user.user import USER

app = Flask(__name__)
app.register_blueprint(USER)
app.register_blueprint(ITEM)

CORS(app)

@app.route('/')
def hello_world():
    return 'Hello, World!'


if __name__ == "__main__":
    # APP.run(host='0.0.0.0', port=8081, debug=True)
    pass