# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import json

import flask

from azureml_inference_server_http.api.aml_request import rawhttp
from azureml_inference_server_http.api.aml_response import AMLResponse
from .common import TestingClient


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
