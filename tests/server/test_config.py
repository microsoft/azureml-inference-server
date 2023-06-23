# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import logging

import pydantic
import pytest

from azureml_inference_server_http.server.config import AMLInferenceServerConfig, log_config_errors


def test_config_errors(caplog):
    with pytest.raises(pydantic.ValidationError) as exc:
        AMLInferenceServerConfig(scoring_timeout="string")
    with caplog.at_level(logging.CRITICAL, logger="azmlinfsrv"):
        log_config_errors(exc.value)
    info_tuple = (
        "azmlinfsrv",
        logging.CRITICAL,
        "\n===============Configuration Error=================\nSCORING_TIMEOUT_MS: value is not a valid integer "
        "(environment variable: SCORING_TIMEOUT_MS)\n============================"
        "=======================",
    )
    assert info_tuple in caplog.record_tuples
