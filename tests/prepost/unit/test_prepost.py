import pytest
import os
from unittest import mock

from azureml_inference_server_http.prepost_server.constants import (
    ENV_AML_APP_ROOT,
    ENV_AML_ENTRY_SCRIPT,
)


class TestPrepost:
    def test_preprocess(self, pullover_bytes, basic_context, script_loader):
        pullover_request = script_loader.preprocess(pullover_bytes, basic_context)
        assert pullover_request["model_name"] == "fashion"
        assert pullover_request["model_version"] == "1"
        assert len(pullover_request["inputs"]) == 1
        assert pullover_request["inputs"][0]["name"] == "Conv1_input"
        assert pullover_request["inputs"][0]["shape"] == [1, 28, 28, 1]

    def test_postprocess(self, basic_context, script_loader):
        data = {
            "model_name": "fashion",
            "model_version": "1",
            "outputs": [
                {
                    "name": "Dense",
                    "datatype": "FP32",
                    "shape": [1, 10],
                    "data": [
                        -7.816166400909424,
                        -11.580815315246582,
                        -7.181772232055664,
                        -7.041390419006348,
                        -6.257577419281006,
                        1.146122932434082,
                        -5.0611724853515625,
                        2.53564453125,
                        -1.2158299684524536,
                        4.956004619598389,
                    ],
                }
            ],
        }
        out, content_type = script_loader.postprocess(data, basic_context)
        assert out == "Ankle boot"
        assert content_type == "text/plain"
