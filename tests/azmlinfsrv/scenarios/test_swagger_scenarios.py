# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import json
import pytest
from .utils import start_server, swagger_with_get, cleanup


def test_swagger_generated(log_directory):
    server_process = start_server(log_directory, ["--entry_script", "./resources/valid_score_swagger.py"])
    req = swagger_with_get()
    cleanup(server_process)

    assert req.ok

    swagger = json.loads(req.content)

    assert swagger["swagger"] == "2.0"
    assert swagger["info"]["title"] == "ML service"
