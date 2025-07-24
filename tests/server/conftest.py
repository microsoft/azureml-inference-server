# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import functools
import logging
import os
import uuid

import flask
import flask.testing
import pydantic
import pytest

# Set a user script for the initial load. We need to set the environment variable before creating
# global config object (in swagger.py) as it does not override later.
os.environ["AZUREML_ENTRY_SCRIPT"] = os.path.join(os.path.dirname(__file__), "data/user_scripts/empty.py")
# Remove and refactor the below env variables after the merge of PR related to creating new app for each test case
os.environ["AML_APP_ROOT"] = os.path.dirname(os.path.dirname(__file__))
os.environ["AZUREML_SOURCE_DIRECTORY"] = "mock_source_dir"

from azureml_inference_server_http.constants import PACKAGE_ROOT  # noqa: E402
from azureml_inference_server_http.log_config import load_logging_config  # noqa: E402
from azureml_inference_server_http.server.config import config as server_config  # noqa: E402
from azureml_inference_server_http.server.create_app import create  # noqa: E402
from .common import TestingApp, TestingClient, TestingUserScript  # noqa: E402, I202


def create_app() -> TestingApp:
    app = create()
    app.test_client_class = TestingClient
    app.azml_blueprint.user_script = app.user_script = TestingUserScript()
    app = TestingApp(app)

    return app


def pytest_configure(config):
    config.addinivalue_line("markers", "online: mark test as having online dependencies")


@pytest.fixture()
def app() -> TestingApp:
    return create_app()


@pytest.fixture()
def client(app: TestingApp) -> TestingClient:
    return app.test_client()


@pytest.fixture()
def app_cors(config):
    config.cors_origins = "www.microsoft.com,  www.bing.com"
    return create_app()


@pytest.fixture()
def app_appinsights(config):
    config.app_insights_enabled = True
    config.mdc_storage_enabled = True
    config.app_insights_key = pydantic.SecretStr(str(uuid.uuid4()))
    return create_app()


@pytest.fixture()
def config():
    backup_config = server_config.model_copy()
    try:
        yield server_config
    finally:
        for field in server_config.model_fields:
            setattr(server_config, field, getattr(backup_config, field))


# Monkey-patch RawRequestInput to always retrieve the actual request object so it can be referenced later in the test
# body. Proxy objects cannot be used outside of a flask context.
def patch_raw_request_input():
    from azureml_inference_server_http.server.input_parsers import RawRequestInput

    @functools.wraps(RawRequestInput.__call__)
    def raw_request_input_call(self, request: flask.Request) -> flask.Request:
        return raw_request_input_call.__wrapped__(self, request._get_current_object())

    RawRequestInput.__call__ = raw_request_input_call


patch_raw_request_input()

# Need to load a default logging config so the loggers are appropriately
# configured
load_logging_config(PACKAGE_ROOT)

# Need to enable propagation of the azmlinfsrv logger so that pytest's caplog
# fixture is able to intercept the logs when testing log data.
logging.getLogger("azmlinfsrv").propagate = True
