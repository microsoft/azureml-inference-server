# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import json

import flask

from azureml_inference_server_http.api.aml_request import rawhttp
from azureml_inference_server_http.api.aml_response import AMLResponse
from .common import TestingClient


def test_compat_flask2_json(app: flask.Flask, client: TestingClient):
    """Ensure that `request.json` does not throw in flask 2 when compatibility flag is set."""

    @app.set_user_run
    @rawhttp
    def run(request: flask.Request):
        # This property decodes the request data as JSON. Before flask 2 this property returns `None` when the request
        # content-type is not json. Flask 2 modified the behavior to throw when content-type is not json.
        return AMLResponse(str(request.json), 200)

    data = json.dumps({"a": 1})
    response = client.post_score(data=data)
    assert response.status_code == 200
    assert response.data == b"None"


def test_compat_flask2_json_error(app: flask.Flask, client: TestingClient):
    """Ensure that `request.json` correctly calls on_json_loading_failed() when it cannot parse the input JSON."""

    @app.set_user_run
    @rawhttp
    def run(request: flask.Request):
        return AMLResponse(request.json, 200)

    response = client.post("/score", data="{", headers={"Content-Type": "application/json"})
    assert response.status_code == 500

    expected_message = {"message": "An unexpected error occurred in scoring script. Check the logs for more info."}
    assert response.json == expected_message
