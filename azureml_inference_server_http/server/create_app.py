# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from distutils.version import LooseVersion
import functools
import importlib
import logging
import traceback
import warnings

import flask
from flask import Flask
import werkzeug
import werkzeug.datastructures
from werkzeug.exceptions import HTTPException

from azureml_inference_server_http.api.aml_response import AMLResponse
from . import routes
from .config import config

logger = logging.getLogger("azmlinfsrv")


def patch_flask():
    # While "packaging" is the recommended package for comparing versions, we can't introduce the dependency because
    # we need our server to work even when the user doesn't have latest dependencies installed.
    with warnings.catch_warnings():
        warnings.filterwarnings(
            action="ignore",
            category=DeprecationWarning,
            message="distutils Version classes are deprecated.",
        )
        patch_werkzeug = LooseVersion(werkzeug.__version__) >= LooseVersion("2.1")

    if patch_werkzeug:
        # Request.headers.has_key() was removed in werkzeug 2.1
        # https://github.com/pallets/werkzeug/commit/03979aaff2b8020fd6fd52e69745950d484e3fa5
        # Restore the functionality to preserve backwards compatability.
        werkzeug.datastructures.EnvironHeaders.has_key = werkzeug.datastructures.EnvironHeaders.__contains__
        werkzeug.datastructures.CombinedMultiDict.has_key = werkzeug.datastructures.CombinedMultiDict.__contains__

        # In werkzeug 2.1, get_json() is modified to throw BadRequest if the content type is not application/json.
        @functools.wraps(flask.Request.on_json_loading_failed)
        def on_json_loading_failed(self, e):
            if e is None:
                return None

            return on_json_loading_failed.__wrapped__(self, e)

        flask.Request.on_json_loading_failed = on_json_loading_failed
        logger.info("AML_FLASK_ONE_COMPATIBILITY is set. Patched Flask to ensure compatibility with Flask 1.")
    else:
        logger.info("AML_FLASK_ONE_COMPATIBILITY is set, but patching is not necessary.")


if config.flask_one_compatibility:
    try:
        patch_flask()
    except Exception:
        logger.warning(
            "AML_FLASK_ONE_COMPATIBILITY is set. However, compatibility patch for Flask 1 has failed. "
            "This is only a problem if you use @rawhttp and relies on deprecated methods such as has_key().\n"
            + traceback.format_exc()
        )


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
