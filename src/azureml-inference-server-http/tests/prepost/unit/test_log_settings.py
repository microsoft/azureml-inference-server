import os
from typing import Container
from unittest import mock
import pytest

from azureml_inference_server_http.prepost_server.log_settings import (
    get_custom_dimensions,
)
from azureml_inference_server_http.prepost_server.constants import (
    CONTAINER_ID,
    ENV_HOSTNAME,
    ENV_SERVICE_NAME,
    ENV_WORKSPACE_NAME,
    WORKSPACE_NAME,
    SERVER_TIMESTAMP,
    REQUEST_ID,
    SERVICE_NAME,
)


def test_get_custom_dimensions(root_folder):
    with mock.patch.dict(
        os.environ,
        {
            ENV_WORKSPACE_NAME: "workspace",
            ENV_SERVICE_NAME: "service",
            ENV_HOSTNAME: "host",
        },
    ):
        custom_dimensions = get_custom_dimensions()

        assert custom_dimensions["custom_dimensions"][REQUEST_ID] == ""
        assert custom_dimensions["custom_dimensions"][SERVER_TIMESTAMP] != 0
        assert custom_dimensions["custom_dimensions"][CONTAINER_ID] == "host"
        assert custom_dimensions["custom_dimensions"][WORKSPACE_NAME] == "workspace"
        assert custom_dimensions["custom_dimensions"][SERVICE_NAME] == "service"
