import json
import os
from unittest import mock

import pytest
from aiohttp import web
import re
from azureml_inference_server_http.prepost_server import create_app
from azureml_inference_server_http.prepost_server.constants import (
    ENV_AML_APP_ROOT,
    ENV_AML_ENTRY_SCRIPT,
    ENV_BACKEND_TRANSPORT_PROTOCOL,
    ENV_AZUREML_BACKEND_PORT,
)
from azureml_inference_server_http.prepost_server.script_loader import ScriptLoader
from sanic.blueprints import Blueprint
from sanic_testing import TestManager
from multiprocessing import Process
from .mocked_triton import create_fake_triton
from .mocked_triton_grpc import create_fake_grpc_triton


def pytest_addoption(parser):
    parser.addoption("--use-triton", required=False, action="store_true", help="Use real Triton")


@pytest.fixture(scope="session", autouse=True)
def mocked_triton(request):
    if request.config.getoption("--use-triton") == True:
        yield
    else:
        p1 = Process(target=create_fake_triton, args=(), daemon=True)
        p2 = Process(target=create_fake_grpc_triton, args=(), daemon=True)
        p1.start()
        p2.start()
        yield
        p1.terminate()
        p2.terminate()


@pytest.fixture(scope="session")
def root_folder() -> str:
    # points to azureml_inference_server_http/prepost_server/
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "azureml_inference_server_http",
        "prepost_server",
    )


@pytest.fixture(scope="session")
def data_folder() -> str:
    return os.path.join(os.path.dirname(__file__), "data")


@pytest.fixture
def pullover_triton_json(data_folder):
    with open(os.path.join(data_folder, "pullover_triton_response.json")) as f:
        return json.load(f)


@pytest.fixture(scope="session")
def pullover_bytes(data_folder):
    with open(os.path.join(data_folder, "pullover.jpg"), "rb") as image:
        return image.read()


@pytest.fixture(scope="function", params=[("rest", "8000"), ("grpc", "8001")])
def app(request, root_folder, data_folder):
    slugify = re.compile(r"[^a-zA-Z0-9_\-]")
    with mock.patch.dict(
        os.environ,
        {
            ENV_AML_APP_ROOT: root_folder,
            ENV_AML_ENTRY_SCRIPT: os.path.join(data_folder, "samples/fashion.py"),
            ENV_BACKEND_TRANSPORT_PROTOCOL: request.param[0],
            ENV_AZUREML_BACKEND_PORT: request.param[1],
        },
    ):
        aml_app = create_app(slugify.sub("-", request.node.name))
        yield aml_app


@pytest.fixture()
def script_loader(root_folder, data_folder):
    config = {
        ENV_AML_APP_ROOT: root_folder,
        ENV_AML_ENTRY_SCRIPT: os.path.join(data_folder, "samples/fashion.py"),
    }
    return ScriptLoader(config)


@pytest.fixture
def basic_headers():
    return {
        "content-type": "image/jpeg",
        "accept": "text/plain",
        "x-ms-custom": "empty",
    }


@pytest.fixture
def basic_context(basic_headers):
    return {"method": "POST", "skip-inference": False, "headers": basic_headers}
