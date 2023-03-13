import re
import os
import pytest
import logging
from azureml_inference_server_http.prepost_server import create_app
from unittest import mock

from azureml_inference_server_http.prepost_server.constants import (
    ENV_AML_APP_ROOT,
    ENV_AML_ENTRY_SCRIPT,
)


def test_image_request(request, caplog, basic_headers, pullover_bytes, root_folder, data_folder):
    with mock.patch.dict(
        os.environ,
        {
            ENV_AML_APP_ROOT: root_folder,
            ENV_AML_ENTRY_SCRIPT: os.path.join(data_folder, "samples/fashion.py"),
        },
    ):
        with caplog.at_level(logging.DEBUG):
            slugify = re.compile(r"[^a-zA-Z0-9_\-]")
            aml_app = create_app(slugify.sub("-", request.node.name))

            _, resp = aml_app.test_client.post("/score", content=pullover_bytes, headers=basic_headers)
            assert resp.status == 200
            assert resp.body == b"Pullover"
            assert resp.text == "Pullover"
            assert resp.headers.get("content-type") == "text/plain; charset=utf-8"
            assert logging.getLogger("sanic.root").getEffectiveLevel() == logging.DEBUG
