import os
import pytest
import json
import re
from azureml_inference_server_http.prepost_server import create_app
from sanic.blueprints import Blueprint
from unittest import mock

from azureml_inference_server_http.prepost_server.constants import (
    ENV_AML_APP_ROOT,
    ENV_AML_ENTRY_SCRIPT,
    ENV_AZUREML_BACKEND_PORT,
    ENV_BACKEND_TRANSPORT_PROTOCOL,
)


@pytest.fixture(scope="function", params=[("rest", "8000"), ("grpc", "8001")])
def error_app(request, root_folder, data_folder):
    slugify = re.compile(r"[^a-zA-Z0-9_\-]")
    with mock.patch.dict(
        os.environ,
        {
            ENV_AML_APP_ROOT: root_folder,
            ENV_AML_ENTRY_SCRIPT: os.path.join(data_folder, "samples/prepost_with_exception.py"),
            ENV_BACKEND_TRANSPORT_PROTOCOL: request.param[0],
            ENV_AZUREML_BACKEND_PORT: request.param[1],
        },
    ):
        aml_app = create_app(slugify.sub("-", request.node.name))
        yield aml_app


@pytest.fixture(scope="function", params=[("rest", "8000")])  # Add gRPC once working
def triton_exception_app(request, root_folder, data_folder):
    slugify = re.compile(r"[^a-zA-Z0-9_\-]")
    with mock.patch.dict(
        os.environ,
        {
            ENV_AML_APP_ROOT: root_folder,
            ENV_AML_ENTRY_SCRIPT: os.path.join(data_folder, "samples/fashion_bad_inputs.py"),
            ENV_BACKEND_TRANSPORT_PROTOCOL: request.param[0],
            ENV_AZUREML_BACKEND_PORT: request.param[1],
        },
    ):
        aml_app = create_app(slugify.sub("-", request.node.name))
        yield aml_app


def test_preprocess_exception(error_app, basic_headers, pullover_bytes):
    basic_headers["accept"] = "application/json"
    _, resp = error_app.test_client.post("/score", content=pullover_bytes, headers=basic_headers)
    assert resp.status == 500
    assert resp.headers["x-ms-run-function-failed"] == "True"
    assert (
        '{"description": "Internal Server Error", "message": "Encountered error in preprocess: Divided by zero", "status": 500}'
        == json.dumps(resp.json, sort_keys=True)
    )


def test_triton_inference_exception(triton_exception_app, basic_headers, pullover_bytes):
    basic_headers["accept"] = "application/json"
    _, resp = triton_exception_app.test_client.post("/score", content=pullover_bytes, headers=basic_headers)
    assert resp.status == 400
    assert '{"description": "Bad Request", "message": "Incorrect inputs", "status": 400}' == json.dumps(
        resp.json, sort_keys=True
    )
