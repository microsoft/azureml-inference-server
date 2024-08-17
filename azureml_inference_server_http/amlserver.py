# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import logging
import os
import re
import sys

from . import __version__
from .args import parse_arguments
from .constants import *
from .log_config import load_logging_config

# check if flask_cors package is available
try:
    import flask_cors  # noqa: F401

    has_flask_cors = True
except ModuleNotFoundError:
    has_flask_cors = False

logger = logging.getLogger("azmlinfsrv")


def print_python_path():
    logging.debug("Current PYTHONPATH:")
    for p in sys.path:
        logging.debug(f"\t{p}")


def print_server_info():
    print()
    print(f"Azure ML Inferencing HTTP server v{__version__}")
    print()


def print_server_settings():
    server_env_vars_descriptions = {
        ENV_AZUREML_ENTRY_SCRIPT: "Entry Script Name",
        ENV_AZUREML_MODEL_DIR: "Model Directory",
        ENV_AZUREML_CONFIG_FILE: "Config File",
        ENV_WORKER_COUNT: "Worker Count",
        ENV_WORKER_TIMEOUT: "Worker Timeout (seconds)",
        ENV_PORT: "Server Port",
        ENV_HEALTH_PORT: "Health Port",
        ENV_AML_APP_INSIGHTS_ENABLED: "Application Insights Enabled",
        ENV_AML_APP_INSIGHTS_KEY: "Application Insights Key",
        ENV_AZUREML_SERVER_VERSION: "Inferencing HTTP server version",
        ENV_AML_CORS_ORIGINS: "CORS for the specified origins",
        ENV_SEPERATE_HEALTH_ENDPOINT: "Create dedicated endpoint for health",
    }

    print()
    print("Server Settings")
    print("---------------")
    for var in server_env_vars_descriptions:
        if var == ENV_AML_APP_INSIGHTS_KEY and ENV_AML_APP_INSIGHTS_KEY in os.environ:
            print(f"{server_env_vars_descriptions[var]}: AppInsights key provided")
        elif var == ENV_AML_CORS_ORIGINS and ENV_AML_CORS_ORIGINS in os.environ:
            if has_flask_cors:
                print(f"{server_env_vars_descriptions[var]}: Enabling CORS for {str(os.getenv(var))}")
            else:
                print(
                    f"{server_env_vars_descriptions[var]}: CORS cannot be enabled because "
                    "the flask-cors package is not installed."
                )
        else:
            print(f"{server_env_vars_descriptions[var]}: {str(os.getenv(var))}")
    print()


def print_routes():
    print()
    print("Server Routes")
    print("---------------")
    print(f"Liveness Probe: GET   127.0.0.1:{os.environ[ENV_HEALTH_PORT]}/")
    print(f"Score:          POST  127.0.0.1:{os.environ[ENV_PORT]}/score")
    print()


def set_environment_variables(arg_val, env_var_name, default_val=None):
    if arg_val is not None:
        os.environ[env_var_name] = str(arg_val)
    elif env_var_name in os.environ:
        pass
    # If a default value is not necessary, we do not want to add a mapping of {ENV_VAR: None} to the environment
    # If users are using os.getenv(ENV_VAR, default_value) we don't want to break that logic.
    elif default_val is not None:
        os.environ[env_var_name] = str(default_val)


def check_valid_uuid(value):
    uuid4hex = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\Z", re.I)
    return re.match(uuid4hex, value)


def validate_environment_variables():
    if ENV_AZUREML_MODEL_DIR not in os.environ:
        print(f"The environment variable '{ENV_AZUREML_MODEL_DIR}' has not been set.")
        print("Use the --model_dir command line argument to set it.")

    # If appinsights is enabled, check if valid appinsights key has been provided.
    if ENV_AML_APP_INSIGHTS_ENABLED in os.environ and ENV_AML_APP_INSIGHTS_KEY in os.environ:
        if os.environ[ENV_AML_APP_INSIGHTS_ENABLED] == "true":
            result = check_valid_uuid(os.environ[ENV_AML_APP_INSIGHTS_KEY])
            if result:
                print("Valid Application Insights instrumentation key provided.")
            else:
                os.environ[ENV_AML_APP_INSIGHTS_ENABLED] = "false"
                print("Invalid Application Insights instrumentation key provided.")
                print("Application Insights has been disabled.")
        else:
            # If ENV_AML_APP_INSIGHTS_ENABLED is set to false or an arbitrary value, explicitly disable it
            os.environ[ENV_AML_APP_INSIGHTS_ENABLED] = "false"
    else:
        # Explicitly disable ENV_AML_APP_INSIGHTS_ENABLED if env vars not set
        os.environ[ENV_AML_APP_INSIGHTS_ENABLED] = "false"


def merge_configuration(args):
    if not (args.entry_script or args.config_file):
        logger.error("Error!")
        logger.error(
            (
                "Either provide an entry_script using --entry_script or "
                "provide a path to the configuration file using --config_file"
            )
        )
        sys.exit(1)

    # If AML_APP_ROOT is set, don't overwrite it.
    os.environ.setdefault(ENV_AML_APP_ROOT, os.getcwd())

    if args.entry_script:
        os.environ[ENV_AZUREML_ENTRY_SCRIPT] = os.path.realpath(args.entry_script)

    transport_protocol = "rest" if args.rest else "grpc"
    set_environment_variables(transport_protocol, ENV_BACKEND_TRANSPORT_PROTOCOL, default_val=False)

    set_environment_variables(args.model_dir, ENV_AZUREML_MODEL_DIR)
    set_environment_variables(args.worker_count, ENV_WORKER_COUNT, default_val=DEFAULT_WORKER_COUNT)

    # Check if sending the server version as part of response is enabled
    # Enable by default if the flag is not set. If the flag is set explicitly check if it is true.
    if (
        ENV_AZUREML_SERVER_VERSION_ENABLED not in os.environ
        or os.environ[ENV_AZUREML_SERVER_VERSION_ENABLED].lower() == "true"
    ):
        set_environment_variables(f"azmlinfsrv/{__version__}", ENV_AZUREML_SERVER_VERSION)

    # If the port environment variable is set outside of cli, we overwrite it
    os.environ[ENV_PORT] = str(DEFAULT_PORT)
    set_environment_variables(args.port, ENV_PORT, default_val=DEFAULT_PORT)

    # If seperate health endpoint env is set, overwrite env of health_port w/ args.health_port or default health port
    # If not, then overwrite env of health_port with the normal default port (no seperate listener created)
    if os.getenv(ENV_SEPERATE_HEALTH_ENDPOINT) == "true":
        os.environ[ENV_HEALTH_PORT] = str(DEFAULT_HEALTH_PORT)
        set_environment_variables(args.health_port, ENV_HEALTH_PORT, default_val=DEFAULT_HEALTH_PORT)
    else:
        set_environment_variables(args.port, ENV_HEALTH_PORT, default_val=DEFAULT_PORT)

    # We assume if the instrumentation key is set via cli, then appinsights is enabled
    # Validation takes place later and will disable this if not a valid key
    if args.appinsights_instrumentation_key is not None:
        os.environ[ENV_AML_APP_INSIGHTS_ENABLED] = "true"
    set_environment_variables(args.appinsights_instrumentation_key, ENV_AML_APP_INSIGHTS_KEY)

    if args.access_control_allow_origins is not None:
        os.environ[ENV_AML_CORS_ORIGINS] = args.access_control_allow_origins

    if args.config_file:
        os.environ["AZUREML_CONFIG_FILE"] = os.path.realpath(args.config_file)


def set_path_variable():
    sys.path.append(os.environ[ENV_AML_APP_ROOT])


def run():
    args = parse_arguments()

    # Load the default logging config
    load_logging_config(PACKAGE_ROOT)

    merge_configuration(args)
    validate_environment_variables()
    set_path_variable()

    print_server_info()
    print_server_settings()
    print_routes()
    print_python_path()

    if sys.platform == "win32":
        from azureml_inference_server_http import amlserver_win as srv

        srv.run(DEFAULT_HOST, int(os.environ[ENV_PORT]), int(os.environ[ENV_WORKER_COUNT]))
    else:
        from azureml_inference_server_http import amlserver_linux as srv

        if os.getenv(ENV_SEPERATE_HEALTH_ENDPOINT) == "true":
            srv.run(
                DEFAULT_HOST,
                int(os.environ[ENV_PORT]),
                int(os.environ[ENV_WORKER_COUNT]),
                int(os.environ[ENV_HEALTH_PORT]),
            )
        else:
            srv.run(DEFAULT_HOST, int(os.environ[ENV_PORT]), int(os.environ[ENV_WORKER_COUNT]))


if __name__ == "__main__":
    run()
