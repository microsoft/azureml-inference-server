import os
import pytest
import re
from sanic_testing import TestManager
from azureml_inference_server_http.prepost_server import create_app
from sanic.blueprints import Blueprint
from unittest import mock

from azureml_inference_server_http.prepost_server.script_loader import ScriptLoader
from azureml_inference_server_http.prepost_server.constants import (
    ENV_AML_APP_ROOT,
    ENV_AML_ENTRY_SCRIPT,
)


def test_invalid_class_score_script(root_folder, data_folder):
    with pytest.raises(SystemExit) as expected_error:
        config = {
            ENV_AML_APP_ROOT: root_folder,
            ENV_AML_ENTRY_SCRIPT: os.path.join(data_folder, "samples/prepost_invalid.py"),
        }
        ScriptLoader(config)
    assert f"Expected ModelHandler class not found" in str(expected_error)
    assert f"Error loading script from" in str(expected_error)
    assert f"Unable to load pre and postprocessing script" in str(expected_error)


def test_score_script_file_not_found(root_folder, data_folder):
    with pytest.raises(SystemExit) as expected_error:
        config = {
            ENV_AML_APP_ROOT: root_folder,
            ENV_AML_ENTRY_SCRIPT: os.path.join(data_folder, "samples/asdf.py"),
        }
        ScriptLoader(config)
    assert f"No file found at location" in str(expected_error)
    assert f"Unable to load pre and postprocessing script" in str(expected_error)


def test_loading_script_fail(root_folder, data_folder):
    with pytest.raises(SystemExit) as expected_error:
        config = {
            ENV_AML_APP_ROOT: root_folder,
            ENV_AML_ENTRY_SCRIPT: os.path.join(data_folder, "samples/requirements.txt"),
        }
        ScriptLoader(config)
    assert f"Exception: 'NoneType' object has no attribute 'loader'" in str(expected_error)
    assert f"Error loading script from" in str(expected_error)
    assert f"Unable to load pre and postprocessing script" in str(expected_error)


def test_preprocess_error(root_folder, pullover_bytes, basic_context, data_folder):
    with pytest.raises(Exception) as expected_error:
        config = {
            ENV_AML_APP_ROOT: root_folder,
            ENV_AML_ENTRY_SCRIPT: os.path.join(data_folder, "samples/prepost_with_exception.py"),
        }
        script_loader = ScriptLoader(config)
        script_loader.preprocess(pullover_bytes, basic_context)
    assert f"Encountered error in preprocess: Divided by zero" in str(expected_error)


def test_postprocess_error(root_folder, pullover_bytes, basic_context, data_folder):
    with pytest.raises(Exception) as expected_error:
        config = {
            ENV_AML_APP_ROOT: root_folder,
            ENV_AML_ENTRY_SCRIPT: os.path.join(data_folder, "samples/prepost_with_exception.py"),
        }
        script_loader = ScriptLoader(config)
        script_loader.postprocess(pullover_bytes, basic_context)
    assert f"Encountered error in postprocess: Runtime error" in str(expected_error)
