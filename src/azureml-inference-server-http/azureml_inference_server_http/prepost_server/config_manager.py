from .constants import (
    DEFAULT_BACKEND_GRPC_PORT,
    ENV_AML_APP_ROOT,
    ENV_AML_ENTRY_SCRIPT,
    DEFAULT_APP_ROOT,
    ENV_AZUREML_BACKEND_HOST,
    ENV_AZUREML_BACKEND_PORT,
    DEFAULT_AZUREML_BACKEND_HOST,
    DEFAULT_BACKEND_REST_PORT,
    ENV_BACKEND_TRANSPORT_PROTOCOL,
    ENV_AML_APP_INSIGHTS_ENABLED,
    ENV_AML_APP_INSIGHTS_KEY,
    DEFAULT_BACKEND_TRANSPORT_PROTOCOL,
)
from .user.exceptions import DeploymentConfigurationException
from sanic.log import logger
import os

from .log_settings import get_custom_dimensions


class ConfigManager(object):
    """
    ConfigManager is responsible for managing the configuration of the backend
    """

    @staticmethod
    def load_config(
        var_name,
        default_val=None,
        error_predicate=lambda _: False,
        error_msg="",
        process_config_fn=lambda x: x,
    ):
        config_val = os.environ.get(var_name, default_val)

        if error_predicate(config_val):
            raise DeploymentConfigurationException(error_msg)

        logger.debug(f"{var_name}: {config_val}", extra=get_custom_dimensions())
        return process_config_fn(config_val)

    @staticmethod
    def load_all_configs(app):
        app.config[ENV_AML_APP_ROOT] = ConfigManager.load_config(ENV_AML_APP_ROOT, DEFAULT_APP_ROOT)

        app.config[ENV_AML_ENTRY_SCRIPT] = ConfigManager.load_config(
            ENV_AML_ENTRY_SCRIPT,
            default_val=None,
            error_predicate=lambda x: x is None,
            error_msg=f"No value found for environment variable {ENV_AML_ENTRY_SCRIPT}",
        )

        app.config[ENV_AZUREML_BACKEND_HOST] = ConfigManager.load_config(
            ENV_AZUREML_BACKEND_HOST, DEFAULT_AZUREML_BACKEND_HOST
        )
        app.config[ENV_BACKEND_TRANSPORT_PROTOCOL] = ConfigManager.load_config(
            ENV_BACKEND_TRANSPORT_PROTOCOL, DEFAULT_BACKEND_TRANSPORT_PROTOCOL
        )

        default_port = (
            DEFAULT_BACKEND_REST_PORT
            if app.config[ENV_BACKEND_TRANSPORT_PROTOCOL] == "rest"
            else DEFAULT_BACKEND_GRPC_PORT
        )
        app.config[ENV_AZUREML_BACKEND_PORT] = ConfigManager.load_config(
            ENV_AZUREML_BACKEND_PORT,
            default_val=default_port,
            error_predicate=lambda x: (not x.isdigit()) or (int(x) < 1 or int(x) > 65535),
            error_msg=f"Out of bounds value found for environment variable {ENV_AZUREML_BACKEND_PORT}",
            process_config_fn=lambda x: int(x),
        )
        app.config[ENV_AML_APP_INSIGHTS_ENABLED] = ConfigManager.load_config(
            ENV_AML_APP_INSIGHTS_ENABLED,
            default_val="false",
            error_predicate=lambda x: x.lower() not in ["true", "false"],
            error_msg=f"Invalid value found for environment variable {ENV_AML_APP_INSIGHTS_ENABLED}",
        )

        if app.config[ENV_AML_APP_INSIGHTS_ENABLED].lower() == "true":
            app.config[ENV_AML_APP_INSIGHTS_KEY] = ConfigManager.load_config(
                ENV_AML_APP_INSIGHTS_KEY,
                default_val=None,
                error_predicate=lambda x: x is None,
                error_msg=f"No value found for environment variable {ENV_AML_APP_INSIGHTS_KEY}",
            )
