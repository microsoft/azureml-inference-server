from os.path import join

import re
import sys
import pytest
import requests

from azureml_inference_server_http import __version__

from .utils import (
    get_logs,
    start_server,
    score_with_post,
    contains_log,
    validate_server_crash,
    get_score_script,
    get_model_dir,
)
from ..constants import STDERR_FILE_PATH, STDOUT_FILE_PATH


@pytest.fixture
def image_data(root_folder):
    path = join(
        root_folder,
        "src",
        "azureml-inference-server-http",
        "tests",
        "prepost",
        "data",
        "pullover.jpg",
    )
    with open(path, "rb") as image:
        return image.read()


# Test happy path for prepost server
@pytest.mark.skipif(sys.platform == "win32", reason="Skip on Windows")
def test_valid_entry_script_ok(log_directory, root_folder, image_data):
    score_script = join(
        root_folder,
        "src",
        "azureml-inference-server-http",
        "tests",
        "azmlinfsrv",
        "resources",
        "prepost_score.py",
    )
    model_dir = join(
        root_folder,
        "src",
        "azureml-inference-server-http",
        "tests",
        "prepost",
        "data",
        "models",
    )
    server_process = start_server(
        log_directory=log_directory, args=["--prepost", "--entry_script", score_script, "--model_dir", model_dir]
    )

    headers = {"content-type": "image/jpeg", "accept": "text/plain"}
    req = score_with_post(data=image_data, headers=headers)
    server_process.kill()
    assert req.ok
    assert req.text == "Pullover"


# Test happy path for prepost server using grpc
@pytest.mark.skipif(sys.platform == "win32", reason="Skip on Windows")
def test_valid_entry_script_ok_rest(log_directory, root_folder, image_data):
    score_script = join(
        root_folder,
        "src",
        "azureml-inference-server-http",
        "tests",
        "azmlinfsrv",
        "resources",
        "prepost_score.py",
    )
    model_dir = join(
        root_folder,
        "src",
        "azureml-inference-server-http",
        "tests",
        "prepost",
        "data",
        "models",
    )
    server_process = start_server(
        log_directory=log_directory,
        args=["--prepost", "--entry_script", score_script, "--model_dir", model_dir, "--rest"],
    )

    headers = {"content-type": "image/jpeg", "accept": "text/plain"}
    req = score_with_post(data=image_data, headers=headers)
    server_process.kill()
    assert req.ok
    assert req.text == "Pullover"


# Test entry script not found crashes prepost server
@pytest.mark.skipif(sys.platform == "win32", reason="Skip on Windows")
def test_invalid_prepost_crash(log_directory, root_folder):
    score_script = join(
        root_folder,
        "src",
        "azureml-inference-server-http",
        "tests",
        "azmlinfsrv",
        "resources",
        "prepost_invalid.py",
    )
    model_dir = join(
        root_folder,
        "src",
        "azureml-inference-server-http",
        "tests",
        "prepost",
        "data",
        "models",
    )
    server_process = start_server(
        log_directory=log_directory, args=["--prepost", "--entry_script", score_script, "--model_dir", model_dir]
    )
    validate_server_crash(server_process)
    assert contains_log(log_directory, STDERR_FILE_PATH, "Invalid processing script from location")


# Test invalid port crashes with prepost server
@pytest.mark.skipif(sys.platform == "win32", reason="Skip on Windows")
def test_port_invalid_port_timeout(log_directory, root_folder, image_data):
    score_script = join(
        root_folder,
        "src",
        "azureml-inference-server-http",
        "tests",
        "azmlinfsrv",
        "resources",
        "prepost_score.py",
    )
    model_dir = join(
        root_folder,
        "src",
        "azureml-inference-server-http",
        "tests",
        "prepost",
        "data",
        "models",
    )

    server_port = "5001"
    request_port = "5002"
    server_process = start_server(
        log_directory, ["--prepost", "--entry_script", score_script, "--model_dir", model_dir, "--port", server_port]
    )

    with pytest.raises(requests.exceptions.ConnectionError) as connection_error:
        req = score_with_post(data=image_data, port=request_port)

    assert connection_error.type == requests.exceptions.ConnectionError

    server_process.kill()


# Test custom port runs properly with prepost server
@pytest.mark.skipif(sys.platform == "win32", reason="Skip on Windows")
def test_port_custom_port_ok(log_directory, root_folder, image_data):
    score_script = join(
        root_folder,
        "src",
        "azureml-inference-server-http",
        "tests",
        "azmlinfsrv",
        "resources",
        "prepost_score.py",
    )
    model_dir = join(
        root_folder,
        "src",
        "azureml-inference-server-http",
        "tests",
        "prepost",
        "data",
        "models",
    )

    server_port = "8347"
    request_port = "8347"
    server_process = start_server(
        log_directory, ["--prepost", "--entry_script", score_script, "--model_dir", model_dir, "--port", server_port]
    )
    req = score_with_post(data=image_data, port=request_port)
    server_process.kill()
    assert req.ok
    assert req.text == "Pullover"


# Test custom worker count runs properly with prepost server
@pytest.mark.skipif(sys.platform == "win32", reason="Skip on Windows")
def test_worker_count_env_var(log_directory, root_folder, image_data):
    score_script = join(
        root_folder,
        "src",
        "azureml-inference-server-http",
        "tests",
        "azmlinfsrv",
        "resources",
        "prepost_score.py",
    )
    model_dir = join(
        root_folder,
        "src",
        "azureml-inference-server-http",
        "tests",
        "prepost",
        "data",
        "models",
    )

    env = {"WORKER_COUNT": "2"}
    server_process = start_server(
        log_directory, args=["--prepost", "--entry_script", score_script, "--model_dir", model_dir], environment=env
    )
    headers = {"content-type": "image/jpeg", "accept": "text/plain"}
    req = score_with_post(data=image_data, headers=headers)
    assert contains_log(log_directory, STDOUT_FILE_PATH, f"Worker Count: 2")
    server_process.kill()
    assert req.ok
    assert req.text == "Pullover"


# Test server version in response for prepost server
@pytest.mark.skipif(sys.platform == "win32", reason="Skip on Windows")
def test_server_version_in_response_header(log_directory, root_folder, image_data):
    score_script = get_score_script(root_folder)
    model_dir = get_model_dir(root_folder)
    server_process = start_server(
        log_directory=log_directory, args=["--prepost", "--entry_script", score_script, "--model_dir", model_dir]
    )

    headers = {"content-type": "image/jpeg", "accept": "text/plain"}
    req = score_with_post(data=image_data, headers=headers)
    server_process.kill()
    assert req.ok
    assert req.text == "Pullover"
    assert req.headers["x-ms-server-version"] == f"azmlinfsrv/{__version__}"


# Test server version not enabled for prepost server
@pytest.mark.skipif(sys.platform == "win32", reason="Skip on Windows")
def test_server_version_not_enabled(log_directory, root_folder, image_data):
    score_script = get_score_script(root_folder)
    model_dir = get_model_dir(root_folder)
    env = {"SERVER_VERSION_LOG_RESPONSE_ENABLED": "false"}
    server_process = start_server(
        log_directory=log_directory,
        args=["--prepost", "--entry_script", score_script, "--model_dir", model_dir],
        environment=env,
    )

    headers = {"content-type": "image/jpeg", "accept": "text/plain"}
    req = score_with_post(data=image_data, headers=headers)
    server_process.kill()
    assert req.ok
    assert req.text == "Pullover"
    assert "x-ms-server-version" not in req.headers


# Test server version enabled for prepost server
@pytest.mark.skipif(sys.platform == "win32", reason="Skip on Windows")
def test_server_version_enabled(log_directory, root_folder, image_data):
    score_script = get_score_script(root_folder)
    model_dir = get_model_dir(root_folder)
    env = {"SERVER_VERSION_LOG_RESPONSE_ENABLED": "true"}
    server_process = start_server(
        log_directory=log_directory,
        args=["--prepost", "--entry_script", score_script, "--model_dir", model_dir],
        environment=env,
    )

    headers = {"content-type": "image/jpeg", "accept": "text/plain"}
    req = score_with_post(data=image_data, headers=headers)
    server_process.kill()
    assert req.ok
    assert req.text == "Pullover"
    assert "x-ms-server-version" in req.headers


# Test correct log format with prepost server
@pytest.mark.skipif(sys.platform == "win32", reason="Skip on Windows")
def test_request_id_in_logs(log_directory, root_folder, image_data):
    score_script = join(
        root_folder,
        "src",
        "azureml-inference-server-http",
        "tests",
        "azmlinfsrv",
        "resources",
        "prepost_score.py",
    )
    model_dir = join(
        root_folder,
        "src",
        "azureml-inference-server-http",
        "tests",
        "prepost",
        "data",
        "models",
    )
    server_process = start_server(
        log_directory=log_directory, args=["--prepost", "--entry_script", score_script, "--model_dir", model_dir]
    )

    # Headers are case insensitive
    headers = {"content-type": "image/jpeg", "accept": "text/plain", "X-Ms-ReQuEsT-Id": "fake_request_id"}
    req = score_with_post(data=image_data, headers=headers)
    assert req.ok
    assert req.text == "Pullover"
    assert contains_log(log_directory, STDERR_FILE_PATH, "fake_request_id")

    headers = {"content-type": "image/jpeg", "accept": "text/plain"}
    req = score_with_post(data=image_data, headers=headers)
    server_process.kill()
    assert req.ok
    assert req.text == "Pullover"
    logs = get_logs(log_directory, STDERR_FILE_PATH)
    # Test uuid4 in logs
    m = re.search(r"[a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}", logs[-1])
    assert m is not None
