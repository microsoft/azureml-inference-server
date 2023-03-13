import pytest
import os
from unittest import mock
from unittest.mock import Mock
from azureml_inference_server_http.prepost_server.user.exceptions import (
    DeploymentConfigurationException,
)
from azureml_inference_server_http.prepost_server.constants import (
    ENV_AML_APP_ROOT,
    ENV_AML_ENTRY_SCRIPT,
    ENV_AZUREML_BACKEND_HOST,
    ENV_AZUREML_BACKEND_PORT,
    DEFAULT_APP_ROOT,
    DEFAULT_AZUREML_BACKEND_HOST,
)

from azureml_inference_server_http.prepost_server.config_manager import ConfigManager


# Test entry script and app root set properly


def test_config_manager_entry_script_ok(root_folder):
    entry_script = "prepost/data/samples/prepost_invalid.py"
    with mock.patch.dict(os.environ, {ENV_AML_APP_ROOT: root_folder, ENV_AML_ENTRY_SCRIPT: entry_script}):
        app = Mock()
        app.config = {}
        ConfigManager.load_all_configs(app)

        assert app.config[ENV_AML_APP_ROOT] == root_folder
        assert app.config[ENV_AML_ENTRY_SCRIPT] == entry_script
        assert app.config[ENV_AZUREML_BACKEND_PORT] == 8001
        assert app.config[ENV_AZUREML_BACKEND_HOST] == DEFAULT_AZUREML_BACKEND_HOST


# Test default app root
def test_config_manager_app_root():
    entry_script = "prepost/data/samples/prepost_invalid.py"
    with mock.patch.dict(os.environ, {ENV_AML_ENTRY_SCRIPT: entry_script}):
        app = Mock()
        app.config = {}
        ConfigManager.load_all_configs(app)

        assert app.config[ENV_AML_APP_ROOT] == DEFAULT_APP_ROOT
        assert app.config[ENV_AML_ENTRY_SCRIPT] == entry_script


# Test error with no entry script
def test_config_manager_entry_script_not_found(root_folder):
    with pytest.raises(DeploymentConfigurationException) as expected_error:
        with mock.patch.dict(os.environ, {ENV_AML_APP_ROOT: root_folder}):
            app = Mock()
            app.config = {}
            ConfigManager.load_all_configs(app)
    assert f"No value found for environment variable {ENV_AML_ENTRY_SCRIPT}" in str(expected_error)


# Test custom host and port
def test_config_manager_custom_host_port():
    entry_script = "prepost/data/samples/prepost_invalid.py"
    with mock.patch.dict(
        os.environ,
        {
            ENV_AML_ENTRY_SCRIPT: entry_script,
            ENV_AZUREML_BACKEND_HOST: "custom",
            ENV_AZUREML_BACKEND_PORT: "2000",
        },
    ):
        app = Mock()
        app.config = {}
        ConfigManager.load_all_configs(app)

        assert app.config[ENV_AZUREML_BACKEND_HOST] == "custom"
        assert app.config[ENV_AZUREML_BACKEND_PORT] == 2000


# Test out of bounds port
def test_config_manager_invalid_port():
    entry_script = "prepost/data/samples/prepost_invalid.py"
    with pytest.raises(DeploymentConfigurationException) as expected_error:
        with mock.patch.dict(
            os.environ,
            {ENV_AML_ENTRY_SCRIPT: entry_script, ENV_AZUREML_BACKEND_PORT: "1000000"},
        ):
            app = Mock()
            app.config = {}
            ConfigManager.load_all_configs(app)

    assert f"Out of bounds value found for environment variable {ENV_AZUREML_BACKEND_PORT}" in str(expected_error)
