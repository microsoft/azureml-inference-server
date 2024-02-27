# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from typing import Any, Dict, Optional, Tuple, Type


import pydantic
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from ..constants import DEFAULT_APP_ROOT, PACKAGE_ROOT
from ..log_config import load_logging_config

logger = logging.getLogger("azmlinfsrv")

alias_mapping = {
    "AML_APP_ROOT": "app_root",
    "AZUREML_SOURCE_DIRECTORY": "source_dir",
    "AZUREML_ENTRY_SCRIPT": "entry_script",
    "SERVICE_NAME": "service_name",
    "WORKSPACE_NAME": "workspace_name",
    "SERVICE_PATH_PREFIX": "service_path_prefix",
    "SERVICE_VERSION": "service_version",
    "SCORING_TIMEOUT_MS": "scoring_timeout",
    "AML_FLASK_ONE_COMPATIBILITY": "flask_one_compatibility",
    "AZUREML_LOG_LEVEL": "log_level",
    "AML_APP_INSIGHTS_ENABLED": "app_insights_enabled",
    "AML_APP_INSIGHTS_KEY": "app_insights_key",
    "AML_MODEL_DC_STORAGE_ENABLED": "model_dc_storage_enabled",
    "APP_INSIGHTS_LOG_RESPONSE_ENABLED": "app_insights_log_response_enabled",
    "AML_CORS_ORIGINS": "cors_origins",
    "AZUREML_MODEL_DIR": "azureml_model_dir",
    "HOSTNAME": "hostname",
    "AZUREML_DEBUG_PORT": "debug_port",
}


def get_config_file() -> str | None:
    # Absolute path to the configuration file
    config_file = os.environ.get("AZUREML_CONFIG_FILE", None)
    if _is_valid_config_file(config_file):
        return config_file
    # Check for config.json in default locations
    roots = (
        # User code artifacts
        os.getenv("AML_APP_ROOT", DEFAULT_APP_ROOT),
        # Directory containing the entry script (might be None)
        (
            os.path.dirname(os.path.abspath(os.environ["AZUREML_ENTRY_SCRIPT"]))
            if "AZUREML_ENTRY_SCRIPT" in os.environ
            else None
        ),
    )
    for root_dir in roots:
        if not root_dir or not os.path.isdir(root_dir):
            continue
        config_file = os.path.join(root_dir, "config.json")
        if _is_valid_config_file(config_file):
            return config_file
    return None


def _is_valid_config_file(config_file) -> bool:
    return config_file and os.path.exists(config_file) and os.stat(config_file).st_size != 0


class JsonConfigSettingsSource(PydanticBaseSettingsSource):
    def get_field_value(self, field: FieldInfo, field_name: str) -> Tuple[Any, str, bool]:
        config_file = get_config_file()
        with open(config_file, encoding=self.config.get("env_file_encoding")) as fp:
            file_content_json = json.load(fp)
            field_value = file_content_json.get(field.alias)
            return field_value, field_name, False

    def prepare_field_value(self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool) -> Any:
        return value

    def __call__(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {}

        for field_name, field in self.settings_cls.model_fields.items():
            field_value, field_key, value_is_complex = self.get_field_value(field, field_name)
            field_value = self.prepare_field_value(field_name, field, field_value, value_is_complex)
            if field_value is not None:
                d[field_key] = field_value

        return d


class AMLInferenceServerConfig(BaseSettings):
    # Root directory for the app
    app_root: str = pydantic.Field(default=DEFAULT_APP_ROOT)

    # Path to source directory
    source_dir: Optional[str] = pydantic.Field(default=None, alias="AZUREML_SOURCE_DIRECTORY")

    # Path to entry script file
    entry_script: Optional[str] = pydantic.Field(default=None, alias="AZUREML_ENTRY_SCRIPT")

    # Name of the service (used for Swagger schema generation)
    service_name: str = pydantic.Field(default="ML service", alias="SERVICE_NAME")

    # Name of the workspace
    workspace_name: str = pydantic.Field(default="", alias="WORKSPACE_NAME")

    # Prefix for the service path (used for Swagger schema generation)
    service_path_prefix: str = pydantic.Field(default="", alias="SERVICE_PATH_PREFIX")

    # Version of the service (used for Swagger schema generation)
    service_version: str = pydantic.Field(default="1.0", alias="SERVICE_VERSION")

    # Dictates how long scoring function with run before timeout in milliseconds.
    scoring_timeout: int = pydantic.Field(default=3600 * 1000, alias="SCORING_TIMEOUT_MS")

    # When @rawhttp is used, whether the user requires on `request` object to have the flask v1 properties/behavior.
    flask_one_compatibility: bool = pydantic.Field(default=True)

    # Sets the Logging level
    log_level: str = pydantic.Field(default="INFO", alias="AZUREML_LOG_LEVEL")

    # Whether to enable AppInsights
    app_insights_enabled: bool = pydantic.Field(default=False)

    # Key to user AppInsights
    app_insights_key: Optional[pydantic.SecretStr] = pydantic.Field(default=None)

    # Whether to enable model data collection
    model_dc_storage_enabled: bool = pydantic.Field(default=False)

    # Whether to log response to AppInsights
    app_insights_log_response_enabled: bool = pydantic.Field(default=True, alias="APP_INSIGHTS_LOG_RESPONSE_ENABLED")

    # Enable CORS for the specified origins
    cors_origins: Optional[str] = pydantic.Field(default=None)

    # Path to model directory
    azureml_model_dir: str = pydantic.Field(default="", alias="AZUREML_MODEL_DIR")

    hostname: str = pydantic.Field(default="Unknown", alias="HOSTNAME")

    # Start the inference server in DEBUGGING mode
    debug_port: Optional[int] = pydantic.Field(default=None, alias="AZUREML_DEBUG_PORT")

    # Check if extra keys are there in the config file
    @pydantic.root_validator(pre=True)
    def check_extra_keys(cls, values: Dict[str, Any]):
        supported_keys = alias_mapping.values()
        extra_keys = []
        for field_name in list(values):
            if field_name not in supported_keys:
                extra_keys.append(field_name)
        if extra_keys:
            logger.warning(
                f"Found extra keys in the config file that are not supported by the server.\nExtra keys = {extra_keys}"
            )
        return values

    # For fields that do not have a value for "env", the environment variable name is built by concatenating this
    # value with the field name. As an example, the field `app_insights_key` will read its value from the
    # environment variable `AML_APP_INSIGHTS_KEY`.
    # Allow other keys in the config.json file
    model_config = SettingsConfigDict(extra="allow", env_prefix="AML_", populate_by_name=True)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        # Check if config_file is present
        if get_config_file():
            return init_settings, env_settings, JsonConfigSettingsSource(settings_cls)
        else:
            return init_settings, env_settings


def log_config_errors(ex):
    for error in ex.errors():
        field = error["loc"][0]
        for key in alias_mapping:
            if alias_mapping[key] == field:
                field = key
        logger.critical(
            (
                "\n"
                "===============Configuration Error================="
                "\n"
                f"{field}: {error['msg']} (environment variable: {field})"
                "\n"
                "==================================================="
            )
        )


try:
    config = AMLInferenceServerConfig()
    # Try to load from app root, if unsuccessful and entry script is set, try
    # to load from entry script directory

    loaded = load_logging_config(config.app_root)

    if not loaded and config.entry_script:
        entry_script_dir = os.path.dirname(os.path.realpath(config.entry_script))
        loaded |= load_logging_config(entry_script_dir)

    if not loaded:
        # Need to reload to stop duplication of gunicorn logs since gunicorn
        # logger was reconfigured when the server was started
        load_logging_config(PACKAGE_ROOT, silent=True)
except pydantic.ValidationError as ex:
    log_config_errors(ex)
    # Gunicorn treats '3' as a boot error and terminates the master.
    sys.exit(3)
except Exception:
    logger.critical("Invalid config file!: {0}".format(traceback.format_exc()))
    sys.exit(3)
