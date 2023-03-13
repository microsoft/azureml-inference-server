import os
from unittest import mock
import pytest
import re
from azureml_inference_server_http.prepost_server import create_app
from azureml_inference_server_http.prepost_server.constants import (
    ENV_AML_APP_ROOT,
    ENV_AML_ENTRY_SCRIPT,
    ENV_AML_APP_INSIGHTS_ENABLED,
    ENV_AML_APP_INSIGHTS_KEY,
)


def test_appinsights_enabled_app(request, root_folder, data_folder):
    slugify = re.compile(r"[^a-zA-Z0-9_\-]")
    with pytest.raises(ValueError) as excinfo:
        with mock.patch.dict(
            os.environ,
            {
                ENV_AML_APP_ROOT: root_folder,
                ENV_AML_ENTRY_SCRIPT: os.path.join(data_folder, "samples/fashion.py"),
                ENV_AML_APP_INSIGHTS_ENABLED: "true",
                ENV_AML_APP_INSIGHTS_KEY: "fake-key",
            },
        ):
            aml_app = create_app(slugify.sub("-", request.node.name))
    assert excinfo.value.args[0] == "Unable to configure handler 'appinsights'"
