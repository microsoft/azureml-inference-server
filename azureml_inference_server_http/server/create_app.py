# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import importlib
import logging

from flask import Flask
from werkzeug.exceptions import HTTPException

from azureml_inference_server_http.api.aml_response import AMLResponse
from . import routes

logger = logging.getLogger("azmlinfsrv")


def create():
    app = Flask(__name__)
    # To create a new instance of main_blueprint each time the create() is called
    importlib.reload(routes)
    app.register_blueprint(routes.main_blueprint)
    app.azml_blueprint = app.blueprints["main"]

    # Handle 404,405 errors to return json response
    @app.errorhandler(HTTPException)
    def handle_404_error(ex: HTTPException):
        message_json = {"message": ex.description}
        return AMLResponse(message_json, ex.code, json_str=True)

    return app


if __name__ == "__main__":
    app = create()
    app.run(host="0.0.0.0", port=31311)
