import os
import importlib
from flask import Flask, Blueprint

settings = importlib.import_module(os.environ['LAYMAN_SETTINGS_MODULE'])


def create_app(app_config):
    app = Flask(__name__)
    for key, value in app_config.items():
        app.config[key] = value
    app.register_blueprint(csw_bp)
    return app


csw_bp = Blueprint('micka_csw', __name__)


@csw_bp.route('/csw', methods=['GET'])
def get_csw():
    resp_code = os.getenv('CSW_GET_RESP_CODE', None)
    resp_code = int(resp_code) if resp_code is not None else 200
    return f"Response code is {resp_code}", resp_code
