# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from datetime import timedelta
import uuid
import pytest
import requests
import shutil
import pip
import sys
import json

from azureml_inference_server_http import __version__
# A test comment to be merged

from .utils import (
    cleanup,
    start_server,
    score_with_post,
    health_with_get,
    validate_server_crash,
    contains_log,
    contains_log_regex,
)
from ..constants import STDERR_FILE_PATH, STDOUT_FILE_PATH, DEFAULT_PORT

DATE_TIME_REGEX = r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}"


def test_valid_entry_script_ok(log_directory):
    server_process = start_server(log_directory, ["--entry_script", "./resources/valid_score.py"])
    req = score_with_post()
    cleanup(server_process)
    assert req.ok


def test_no_entry_script_crash(log_directory):
    server_process = start_server(log_directory, [])
    validate_server_crash(server_process)


def test_bad_path_entry_script_crash(log_directory):
    server_process = start_server(log_directory, ["--entry_script", "resources/missing_score.py"])
    validate_server_crash(server_process)


def test_invalid_indent_crash(log_directory):
    server_process = start_server(log_directory, ["--entry_script", "./resources/invalid_indent_score.py"])
    validate_server_crash(server_process)

    assert contains_log(
        log_directory, STDOUT_FILE_PATH, "IndentationError: unindent does not match any outer indentation level"
    )


def test_port_invalid_port_timeout(log_directory):
    server_port = "5001"
    request_port = "5002"
    server_process = start_server(
        log_directory, ["--entry_script", "./resources/valid_score.py", "--port", server_port]
    )
    with pytest.raises(requests.exceptions.ConnectionError) as connection_error:
        score_with_post(port=request_port)

    assert connection_error.type == requests.exceptions.ConnectionError

    cleanup(server_process)


def test_port_use_default_ok(log_directory):
    server_process = start_server(log_directory, ["--entry_script", "./resources/valid_score.py"])
    req = score_with_post(port=DEFAULT_PORT)
    cleanup(server_process)
    assert req.ok


def test_port_already_in_use_raises_oserror(log_directory):
    server_process_running = start_server(
        log_directory,
        ["--entry_script", "./resources/valid_score.py"],
    )
    server_process_failed = start_server(
        log_directory,
        ["--entry_script", "./resources/valid_score.py"],
    )

    # Timeout is longer to account for ~5 seconds worth of retries on Gunicorn when running on linux.
    validate_server_crash(server_process_failed, timeout=timedelta(seconds=15))

    req = score_with_post()
    cleanup(server_process_running)
    assert req.ok


def test_port_custom_port_ok(log_directory):
    server_port = "8347"
    request_port = "8347"
    server_process = start_server(
        log_directory, ["--entry_script", "./resources/valid_score.py", "--port", server_port]
    )
    req = score_with_post(port=request_port)
    cleanup(server_process)
    assert req.ok


def test_no_arg_from_cli_ok(log_directory):
    server_process = start_server(log_directory, ["--entry_script", "./resources/score_validate_env_vars.py"])
    req = score_with_post()

    assert contains_log(log_directory, STDOUT_FILE_PATH, "AML_APP_INSIGHTS_ENABLED:false")
    assert contains_log(log_directory, STDOUT_FILE_PATH, "AML_APP_INSIGHTS_KEY:__NONE__")
    assert contains_log(log_directory, STDOUT_FILE_PATH, "AZUREML_MODEL_DIR:__NONE__")
    cleanup(server_process)
    assert req.ok


def test_model_dir_arg_from_cli_ok(log_directory):
    model_dir = "./my/dir"
    server_process = start_server(
        log_directory, ["--entry_script", "./resources/score_validate_env_vars.py", "--model_dir", model_dir]
    )
    req = score_with_post()
    cleanup(server_process)
    assert contains_log(log_directory, STDOUT_FILE_PATH, f"AZUREML_MODEL_DIR:{model_dir}")
    assert req.ok


def test_server_version_header(log_directory):
    server_process = start_server(log_directory, ["--entry_script", "./resources/valid_score.py"])
    req = score_with_post()
    cleanup(server_process)
    assert req.ok
    assert req.headers["x-ms-server-version"] == f"azmlinfsrv/{__version__}"


def test_server_version_enabled_header(log_directory):
    env = {"SERVER_VERSION_LOG_RESPONSE_ENABLED": "true"}
    server_process = start_server(
        log_directory, args=["--entry_script", "./resources/valid_score.py"], environment=env
    )
    req = score_with_post()
    cleanup(server_process)
    assert req.ok
    assert "x-ms-server-version" in req.headers


def test_server_version_not_enabled_header(log_directory):
    env = {"SERVER_VERSION_LOG_RESPONSE_ENABLED": "false"}
    server_process = start_server(
        log_directory, args=["--entry_script", "./resources/valid_score.py"], environment=env
    )
    req = score_with_post()
    cleanup(server_process)
    assert req.ok
    assert "x-ms-server-version" not in req.headers


def test_server_version_enabled_bad_value(log_directory):
    env = {"SERVER_VERSION_LOG_RESPONSE_ENABLED": "notgood"}
    server_process = start_server(
        log_directory, args=["--entry_script", "./resources/valid_score.py"], environment=env
    )
    req = score_with_post()
    cleanup(server_process)
    assert req.ok
    assert "x-ms-server-version" not in req.headers


def test_print_init_ok(log_directory):
    server_process = start_server(log_directory, ["--entry_script", "./resources/valid_score.py"])
    req = score_with_post()

    cleanup(server_process)
    log_regex = rf"{DATE_TIME_REGEX} I \[\d+\] azmlinfsrv.print - Initializing"
    assert contains_log_regex(log_directory, STDOUT_FILE_PATH, log_regex)
    assert req.ok


def test_server_import_aml_contrib_services_redirect(log_directory):
    server_process = start_server(
        log_directory, args=["--entry_script", "./resources/score_aml_contrib_services_import.py"]
    )
    req = score_with_post()
    cleanup(server_process)
    assert req.ok


def test_print_run_ok_and_single_print(log_directory):
    server_process = start_server(log_directory, ["--entry_script", "./resources/valid_score.py"])
    req = score_with_post()

    cleanup(server_process)
    assert contains_log_regex(
        log_directory,
        STDOUT_FILE_PATH,
        rf"{DATE_TIME_REGEX} I \[\d+\] azmlinfsrv.print - A new request received~~~",
        expected_output_count=1,
    )
    assert req.ok


def test_log_configurability(log_directory, tmp_path):
    # The server should load the config from the app dir
    env = {"AML_APP_ROOT": str(tmp_path.absolute())}
    # Need to copy the entry script to the app root
    shutil.copy("./resources/valid_score.py", tmp_path / "valid_score.py")
    # Set the logging configuration with the appropriate file name
    shutil.copy("./resources/alternate_log_config.json", tmp_path / "logging.json")

    server_process = start_server(log_directory, ["--entry_script", "./valid_score.py"], environment=env)
    cleanup(server_process)

    assert contains_log_regex(
        log_directory,
        STDOUT_FILE_PATH,
        rf"[INFO] \[\d+\] azmlinfsrv {DATE_TIME_REGEX} | Starting up app insights client",
    )


def test_model_dir_env_var_cli_overrides_env(log_directory):
    model_dir = "./my/dir"
    env = {"AZUREML_MODEL_DIR": "./not/good"}
    server_process = start_server(
        log_directory=log_directory,
        args=["--entry_script", "./resources/score_validate_env_vars.py", "--model_dir", model_dir],
        environment=env,
    )
    req = score_with_post()
    cleanup(server_process)
    assert contains_log(log_directory, STDOUT_FILE_PATH, f"AZUREML_MODEL_DIR:{model_dir}")
    assert req.ok


def test_model_dir_env_var_no_cli_ok(log_directory):
    env = {"AZUREML_MODEL_DIR": "./not/good"}
    server_process = start_server(
        log_directory=log_directory, args=["--entry_script", "./resources/score_validate_env_vars.py"], environment=env
    )
    req = score_with_post()
    cleanup(server_process)

    assert not contains_log(log_directory, STDOUT_FILE_PATH, "Use the --model_dir command line argument to set it.")
    assert req.ok


def test_app_insights_cli_ok(log_directory):
    app_insights_key = str(uuid.uuid4())
    server_process = start_server(
        log_directory,
        args=[
            "--entry_script",
            "./resources/score_validate_env_vars.py",
            "--appinsights_instrumentation_key",
            app_insights_key,
        ],
    )
    req = score_with_post()
    assert contains_log(log_directory, STDOUT_FILE_PATH, "Application Insights Key: AppInsights key provided")
    assert contains_log(log_directory, STDOUT_FILE_PATH, "Application Insights Enabled: true")
    assert contains_log(log_directory, STDOUT_FILE_PATH, "Valid Application Insights instrumentation key provided.")
    assert contains_log(log_directory, STDOUT_FILE_PATH, f"AML_APP_INSIGHTS_KEY:{app_insights_key}")
    assert contains_log(log_directory, STDOUT_FILE_PATH, "AML_APP_INSIGHTS_ENABLED:true")
    cleanup(server_process)
    assert req.ok


def test_app_insights_bad_key_cli_ok(log_directory):
    app_insights_key = "my-super-duper-key"
    server_process = start_server(
        log_directory=log_directory,
        args=[
            "--entry_script",
            "./resources/score_validate_env_vars.py",
            "--appinsights_instrumentation_key",
            app_insights_key,
        ],
    )

    assert contains_log(log_directory, STDOUT_FILE_PATH, f"Invalid Application Insights instrumentation key provided.")
    assert contains_log(log_directory, STDOUT_FILE_PATH, "Application Insights Key: AppInsights key provided")
    assert contains_log(log_directory, STDOUT_FILE_PATH, "Application Insights Enabled: false")
    assert contains_log(log_directory, STDOUT_FILE_PATH, "Application Insights has been disabled.")
    req = score_with_post()
    assert contains_log(log_directory, STDOUT_FILE_PATH, "AML_APP_INSIGHTS_ENABLED:false")
    cleanup(server_process)
    assert req.ok


def test_worker_count_env_var(log_directory):
    env = {"WORKER_COUNT": "2"}
    server_process = start_server(
        log_directory, args=["--entry_script", "./resources/score_validate_env_vars.py"], environment=env
    )
    req = score_with_post()
    assert contains_log(log_directory, STDOUT_FILE_PATH, f"Worker Count: 2")
    cleanup(server_process)
    assert req.ok


def test_worker_timeout_env_var(log_directory):
    env = {"WORKER_TIMEOUT": "20"}
    server_process = start_server(
        log_directory, args=["--entry_script", "./resources/score_validate_env_vars.py"], environment=env
    )
    req = score_with_post()
    assert contains_log(log_directory, STDOUT_FILE_PATH, f"Worker Timeout (seconds): 20")
    cleanup(server_process)
    assert req.ok


def test_app_insights_cli_env_var(log_directory):
    app_insights_key = str(uuid.uuid4())
    env = {"AML_APP_INSIGHTS_KEY": app_insights_key, "AML_APP_INSIGHTS_ENABLED": "true"}
    server_process = start_server(
        log_directory, args=["--entry_script", "./resources/score_validate_env_vars.py"], environment=env
    )

    req = score_with_post()
    assert contains_log(log_directory, STDOUT_FILE_PATH, "Application Insights Key: AppInsights key provided")
    assert contains_log(log_directory, STDOUT_FILE_PATH, "Application Insights Enabled: true")
    assert contains_log(log_directory, STDOUT_FILE_PATH, "Valid Application Insights instrumentation key provided.")
    assert contains_log(log_directory, STDOUT_FILE_PATH, f"AML_APP_INSIGHTS_KEY:{app_insights_key}")
    assert contains_log(log_directory, STDOUT_FILE_PATH, "AML_APP_INSIGHTS_ENABLED:true")
    cleanup(server_process)
    assert req.ok


def test_app_insights_false_if_invalid(log_directory):
    app_insights_key = str(uuid.uuid4())
    env = {"AML_APP_INSIGHTS_KEY": app_insights_key, "AML_APP_INSIGHTS_ENABLED": "asdf"}
    server_process = start_server(
        log_directory, args=["--entry_script", "./resources/score_validate_env_vars.py"], environment=env
    )

    req = score_with_post()
    assert contains_log(log_directory, STDOUT_FILE_PATH, "Application Insights Key: AppInsights key provided")
    assert contains_log(log_directory, STDOUT_FILE_PATH, "Application Insights Enabled: false")
    assert contains_log(log_directory, STDOUT_FILE_PATH, "AML_APP_INSIGHTS_ENABLED:false")
    cleanup(server_process)
    assert req.ok


def test_app_insights_cli_over_env(log_directory):
    app_insights_key_cli = "my-super-duper-key"
    app_insights_key_env = str(uuid.uuid4())
    env = {"AML_APP_INSIGHTS_KEY": app_insights_key_env}
    server_process = start_server(
        log_directory=log_directory,
        args=[
            "--entry_script",
            "./resources/score_validate_env_vars.py",
            "--appinsights_instrumentation_key",
            app_insights_key_cli,
        ],
        environment=env,
    )

    assert contains_log(log_directory, STDOUT_FILE_PATH, f"Invalid Application Insights instrumentation key provided.")
    assert contains_log(log_directory, STDOUT_FILE_PATH, "Application Insights Key: AppInsights key provided")
    assert contains_log(log_directory, STDOUT_FILE_PATH, "Application Insights Enabled: false")
    assert contains_log(log_directory, STDOUT_FILE_PATH, "Application Insights has been disabled.")
    req = score_with_post()
    assert contains_log(log_directory, STDOUT_FILE_PATH, "AML_APP_INSIGHTS_ENABLED:false")
    cleanup(server_process)
    assert req.ok


def test_server_port_set_to_default(log_directory):
    server_port = 3535
    env = {"SERVER_PORT": str(server_port)}
    server_process = start_server(
        log_directory=log_directory, args=["--entry_script", "./resources/score_validate_env_vars.py"], environment=env
    )

    assert contains_log(log_directory, STDOUT_FILE_PATH, "Server Port: 5001")
    req = score_with_post()
    cleanup(server_process)
    assert req.ok


def test_cors_enabled(log_directory):
    server_process = start_server(
        log_directory,
        args=[
            "--entry_script",
            "./resources/score_validate_env_vars.py",
            "--access_control_allow_origins",
            "*",
        ],
    )
    req = score_with_post()
    assert contains_log(log_directory, STDOUT_FILE_PATH, "CORS for the specified origins: Enabling CORS for *")
    cleanup(server_process)
    assert req.ok


def test_cors_enabled_for_multiple_origins(log_directory):
    server_process = start_server(
        log_directory,
        args=[
            "--entry_script",
            "./resources/score_validate_env_vars.py",
            "--access_control_allow_origins",
            "www.microsoft.com, www.azure.com, www.bing.com",
        ],
    )
    req = score_with_post()
    assert contains_log(
        log_directory,
        STDOUT_FILE_PATH,
        "CORS for the specified origins: Enabling CORS for www.microsoft.com, www.azure.com, www.bing.com",
    )
    cleanup(server_process)
    assert req.ok


def test_cors_enabled_without_package(log_directory):
    pip.main(["uninstall", "flask-cors", "-y"])
    server_process = start_server(
        log_directory,
        args=[
            "--entry_script",
            "./resources/score_validate_env_vars.py",
            "--access_control_allow_origins",
            "www.microsoft.com, www.azure.com, www.bing.com",
        ],
    )
    req = score_with_post()
    assert contains_log(
        log_directory,
        STDOUT_FILE_PATH,
        "CORS for the specified origins: CORS cannot be enabled because the flask-cors package is not installed.",
    )
    cleanup(server_process)
    assert req.ok


@pytest.mark.skipif(sys.platform == "win32", reason="Skip on Windows")
def test_seperate_health_port(log_directory):
    env = {"SEPERATE_HEALTH_ENDPOINT": "true"}
    server_process = start_server(
        log_directory=log_directory,
        args=["--entry_script", "./resources/valid_score.py"],
        environment=env,
    )

    assert contains_log(log_directory, STDOUT_FILE_PATH, "Health Port: 5000")
    req = health_with_get()
    cleanup(server_process)
    assert req.ok


@pytest.mark.skipif(sys.platform == "win32", reason="Skip on Windows")
def test_set_custom_health_port_cli(log_directory):
    env = {"SEPERATE_HEALTH_ENDPOINT": "true"}
    health_port = "8346"
    server_process = start_server(
        log_directory,
        ["--entry_script", "./resources/valid_score.py", "--health_port", health_port],
        environment=env,
    )

    assert contains_log(log_directory, STDOUT_FILE_PATH, "Health Port: 8346")
    req = health_with_get(port=health_port)
    cleanup(server_process)
    assert req.ok


@pytest.mark.skipif(sys.platform == "win32", reason="Skip on Windows")
def test_no_custom_health_port(log_directory):
    server_process = start_server(
        log_directory,
        ["--entry_script", "./resources/valid_score.py"],
    )

    assert contains_log(log_directory, STDOUT_FILE_PATH, "Health Port: 5001")
    req = health_with_get(port=5001)
    cleanup(server_process)
    assert req.ok


def test_streaming_score(log_directory):
    server_process = start_server(
        log_directory,
        args=[
            "--entry_script",
            "./resources/streaming-score.py",
        ],
    )
    data = {"items": ["sentence 1", "sentence 2", "sentence 3", "sentence 4", "sentence 5"]}
    json_data = json.dumps(data)
    req = score_with_post(json=json.loads(json_data), stream=True)

    chunkedOutput = []
    assert callable(req.iter_content) and hasattr(req.iter_content(), "__iter__")
    for chunk in req.iter_content(chunk_size=None):
        if chunk:
            chunkedOutput.append(chunk.decode("utf-8"))

    for idx, item in enumerate(data["items"]):
        assert chunkedOutput[idx] == f"item: {item}\n\n"

    assert contains_log_regex(
        log_directory,
        STDOUT_FILE_PATH,
        r"POST\s\/\w+\s\d{3}\s\d+\.\d{3}ms\sN\/A",
    )
    cleanup(server_process)
    assert req.ok
