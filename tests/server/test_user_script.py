# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import json
import logging
import os
import pathlib
import shutil
import sys
import time
import unittest.mock

import flask
import pytest

from azureml_inference_server_http.api.aml_request import rawhttp
from azureml_inference_server_http.server.user_script import (
    UserScriptError,
    UserScriptException,
    UserScriptImportException,
)
from .common import data_path, TestingClient, TestingUserScript

# Load script


def test_script_not_found(caplog, config):
    """Ensure we throw error when main.py file is not found"""

    with caplog.at_level(logging.ERROR, logger="azmlinfsrv"):
        with pytest.raises(SystemExit) as expected_error:
            from azureml_inference_server_http.server.create_app import create

            config.entry_script = None
            create()

    expected_err_msg = "No score script found. Expected score script main.py."
    error_tuple = ("azmlinfsrv", logging.ERROR, expected_err_msg)

    assert error_tuple in caplog.record_tuples
    assert expected_error.type == SystemExit


def test_import_error_in_main(tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, app: flask.Flask, caplog):
    """Ensure we throw a proper error when the main can't be loaded because it's invalid."""

    monkeypatch.syspath_prepend(tmp_path)
    shutil.copyfile(data_path("user_scripts/import_error_main.py"), tmp_path / "main.py")
    with caplog.at_level(logging.ERROR, logger="azmlinfsrv"):
        with pytest.raises(SystemExit) as expected_error:
            app.azml_blueprint.setup()

    assert "Failed to import user script because it raised an unhandled exception" in caplog.record_tuples[0][2]
    assert expected_error.type == SystemExit


def test_user_script_load_main(
    tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch, app: flask.Flask, client: TestingClient
):
    """Ensure we can load user scripts with ``import main``"""

    monkeypatch.syspath_prepend(tmp_path)
    shutil.copyfile(data_path("user_scripts/simple.py"), tmp_path / "main.py")

    app.azml_blueprint.setup()

    response = client.get_score({"num": 10})
    assert response.status_code == 200
    assert response.json == {"num": 10}


@pytest.mark.xfail(reason="It throws SystemExit today. We should propagate the actual exception.")
def test_user_script_load_bad_indent(app: flask.Flask):
    """Ensure we throw a proper error from setup() when the user script can't loaded because it's invalid."""

    app.azml_blueprint.user_script = TestingUserScript("bad_indent.py")
    with pytest.raises(UserScriptImportException) as excinfo:
        app.azml_blueprint.setup()

    ex = excinfo.value
    assert str(ex) == "Failed to import user script because it raised an unhandled exception"
    assert isinstance(ex.__cause__, IndentationError)
    assert ex.__cause__ is ex.user_ex


def test_user_script_load_bad_run_signature(app: flask.Flask):
    """Ensure run() doesn't take unsupported arguments"""

    with pytest.raises(UserScriptError) as excinfo:

        @app.set_user_run
        def run(*args):
            pass

    assert str(excinfo.value) == "run() cannot accept positional-only arguments, *args, or **kwargs."


def test_user_script_user_import(app: flask.Flask, client: TestingClient, config):
    """Ensure we can load files from source directory"""

    source_dir = os.path.join(config.app_root, "mock_source_dir")
    os.makedirs(source_dir, exist_ok=True)
    shutil.copyfile(data_path("mock_source_dir", "import_test.py"), os.path.join(source_dir, "import_test.py"))
    app.azml_blueprint.user_script = app.user_script = TestingUserScript("source_dir_main.py")
    app.azml_blueprint.setup()

    response = client.get_score()
    shutil.rmtree(source_dir)
    assert response.status_code == 200
    assert response.json == {"key": "value"}


# init()


@pytest.mark.xfail(reason="It throws SystemExit today. We should propagate the actual exception.")
def test_user_script_init_exception(app: flask.Flask):
    @app.set_user_init
    def init():
        1 / 0

    # Mock out load_script() so we don't overwrite our custom init()
    with unittest.mock.patch.object(app.user_script, "load_script"):
        with pytest.raises(UserScriptException) as excinfo:
            app.azml_blueprint.setup()

    ex = excinfo.value
    assert str(ex) == "Caught an unhandled exception from the user script"
    assert isinstance(ex.__cause__, ZeroDivisionError)
    assert ex.__cause__ is ex.user_ex


def test_user_script_run_no_argument(app: flask.Flask):
    """Validate the error we throw when user's run() doesn't accept any parameter."""

    # Without request_headers
    with pytest.raises(UserScriptError) as excinfo:

        @app.set_user_run
        def run():
            pass

    ex = excinfo.value
    assert str(ex) == "run() needs to accept an argument for input data."

    # With request_headers
    with pytest.raises(UserScriptError) as excinfo:

        @app.set_user_run
        def run_with_request_headers(request_headers):
            pass

    ex = excinfo.value
    assert str(ex) == 'run() needs to accept an argument other than "request_headers".'


# Undecorated run()


def test_user_script_input_json_get(app: flask.Flask, client: TestingClient):
    """Ensure we pass the user input from a GET request as a JSON string when run() is not decorated."""

    @app.set_user_run
    def run(data):
        pass

    input_data = {"a": 1, "b": "x", "c": 1.2, "d": [1, 2, 3], "e": "null", "f": json.dumps({"X": "Y"})}
    response = client.get_score(input_data)
    assert response.status_code == 200
    assert app.last_run.input == {"data": json.dumps({**input_data, "e": None, "f": {"X": "Y"}})}


def test_user_script_input_json_post(app: flask.Flask, client: TestingClient):
    """Ensure we pass the user input from a POST request as a JSON string when run() is not decorated."""

    @app.set_user_run
    def run(data):
        pass

    input_data = {"a": 1, "b": "x", "c": 1.2, "d": [1, 2, 3], "e": None, "f": {"X": "Y"}}
    response = client.post_score(input_data)
    assert response.status_code == 200
    assert app.last_run.input == {"data": json.dumps(input_data)}


def test_user_script_input_json_not_utf8(app: flask.Flask, client: TestingClient):
    """When run() is not decorated, ensure a clear error message is provided when the input is not in UTF-8."""

    @app.set_user_run
    def run(data):
        pass

    response = client.post_score(data=b"\xff")
    assert response.status_code == 400
    assert response.json == {
        "message": (
            "Input cannot be decoded as UTF-8: "
            "'utf-8' codec can't decode byte 0xff in position 0: invalid start byte"
        )
    }


def test_user_script_input_json_options(app: flask.Flask, client: TestingClient):
    """An OPTIONS request to a non-decorated run() should return 200."""

    @app.set_user_run
    def run(data):
        pass

    response = client.options_score()
    assert response.status_code == 200
    assert response.data == b""


def test_user_script_input_json_default_parameter(app: flask.Flask, client: TestingClient):
    """Allow extra arguments when a default value is provided. XXX: Do we need to support this scenario?"""

    @app.set_user_run
    def run(data, color="red"):
        return color

    response = client.get_score()
    assert response.status_code == 200
    assert response.json == "red"


def test_user_script_run_request_headers(app: flask.Flask, client: TestingClient):
    """Verifies that a POST request to the /score path with custom request headers
    is handled correctly by the run function"""

    @app.set_user_run
    def run(input_data, request_headers):
        response_dict = json.loads(input_data)
        response_dict.update(request_headers)
        return response_dict

    response = client.post_score({"param1": "hello", "param2": "world"}, headers={"test-header": "test-header-value"})
    data = response.json

    assert response.status_code == 200
    assert data["param1"] == "hello"
    assert data["param2"] == "world"
    assert data["Test-Header"] == "test-header-value"


# run() decorated with @rawhttp


def test_user_script_input_rawhttp_get(app: flask.Flask, client: TestingClient):
    """Ensure we pass the raw flask request to user's run() for GET requests when it is decorated with @rawhttp."""

    @app.set_user_run
    @rawhttp
    def run(request):
        pass

    response = client.get_score({"a": 1, "b": "x", "c": 1.2})
    assert response.status_code == 200
    assert len(app.last_run.input) == 1

    request = app.last_run.input["request"]
    assert isinstance(request, flask.Request)
    assert request.method == "GET"
    assert request.query_string == b"a=1&b=x&c=1.2"


def test_user_script_input_rawhttp_post(app: flask.Flask, client: TestingClient):
    """Ensure we pass the raw flask request to user's run() for GET requests when it is decorated with @rawhttp."""

    @app.set_user_run
    @rawhttp
    def run(request):
        pass

    response = client.post_score([1, 2, 3])
    assert response.status_code == 200
    assert len(app.last_run.input) == 1

    request = app.last_run.input["request"]
    assert isinstance(request, flask.Request)
    assert request.method == "POST"
    assert request.data == b"[1, 2, 3]"


def test_user_script_input_rawhttp_options(app: flask.Flask, client: TestingClient):
    """Ensure we pass the raw flask request to user's run() for OPTIONS requests when it is decorated with @rawhttp."""

    @app.set_user_run
    @rawhttp
    def run(request):
        pass

    response = client.options_score()
    assert response.status_code == 200
    assert len(app.last_run.input) == 1

    request = app.last_run.input["request"]
    assert isinstance(request, flask.Request)
    assert request.method == "OPTIONS"


def test_user_script_input_rawhttp_default_parameter(app: flask.Flask, client: TestingClient):
    """Allow extra arguments when a default value is provided. XXX: Do we need to support this scenario?"""

    @app.set_user_run
    @rawhttp
    def run(request, color="red"):
        return color

    response = client.get_score()
    assert response.status_code == 200
    assert response.json == "red"


@pytest.mark.parametrize("method", ["GET", "POST"])
@pytest.mark.parametrize("content_type", [None, "", "application/json", "text/plain", "application/octet-stream"])
def test_user_script_input_json_content_type(app: flask.Flask, client: TestingClient, method: str, content_type: str):
    """Scoring with different content-type should return 200"""

    @app.set_user_run
    def run(data):
        return data

    payload = {"data": "some plain text"}

    response = client.score(method, input_data=payload, content_type=content_type)
    assert response.status_code == 200
    assert response.json == '{"data": "some plain text"}'


# run() Exceptions


def test_user_script_run_exception(app: flask.Flask, client: TestingClient):
    """Uncaught exceptions from the user script are returned in the response."""

    @app.set_user_run
    def run(data):
        1 / 0

    response = client.get_score()
    assert response.status_code == 500
    assert response.json == {
        "message": "An unexpected error occurred in scoring script. Check the logs for more info."
    }


@pytest.mark.xfail(reason="Feature not implemented")
def test_user_script_run_http_exception(app: flask.Flask, client: TestingClient):
    """Ensure HTTP exceptions are not caught by the user script wrapper and propagated to Flask."""

    @app.set_user_run
    def run(data):
        flask.abort(499)

    response = client.get_score()
    assert response.status_code == 499


@pytest.mark.parametrize("latency_ms", [200, 400])
def test_user_script_run_timer(app: flask.Flask, client: TestingClient, latency_ms: int):
    """Ensure the reported time on the user function is accurate. The upper limit is slightly high because this test is
    not meant to catch regression on the server's performance. This test is designed to verify the correctness of the
    timer."""

    # NOTE: We can't reference ``latency_ms`` in run() due to a bug in inference-schema
    @app.set_user_run
    def run(sleep_s):
        time.sleep(float(sleep_s))

    # Increase the tolerence for Windows because the latency fluctuates quite a bit. We need subtract `TOLERANCE` from
    # the lower bound because the duration passed to time.sleep() is not a lower bound in Windows.
    TOLERANCE = 20 if os.name == "nt" else 0

    # This is the time spent on the entire request (server + user script).
    start_time = time.perf_counter()
    response = client.post_score(data=str(latency_ms / 1_000))
    elapsed_ms = (time.perf_counter() - start_time) * 1_000
    assert response.status_code == 200
    assert latency_ms - TOLERANCE <= elapsed_ms < latency_ms + 30 + TOLERANCE

    # This is the time spent in user's run() function, reported by the server.
    reported_latency = float(response.headers["x-ms-run-fn-exec-ms"])
    assert reported_latency <= elapsed_ms
    assert latency_ms - TOLERANCE <= reported_latency < latency_ms + 10 + TOLERANCE


@pytest.mark.skipif(sys.platform == "win32", reason="Scoring timeout does not work on Windows")
@pytest.mark.parametrize("timeout_ms", [200, 400])
def test_user_script_run_timeout(app: flask.Flask, client: TestingClient, timeout_ms: int, config):
    """Ensure the scoring request is aborted if run() is taking too long."""

    @app.set_user_run
    def run(data):
        time.sleep(1)

    config.scoring_timeout = timeout_ms

    # This is the time spent on the entire request (server + user script).
    start_time = time.perf_counter()
    response = client.get_score()
    elapsed_ms = (time.perf_counter() - start_time) * 1_000
    assert response.status_code == 500
    assert response.json == {"message": f"Scoring timeout after {timeout_ms} ms"}
    assert timeout_ms <= elapsed_ms < timeout_ms + 10

    assert response.headers["x-ms-run-function-failed"] == "True"
