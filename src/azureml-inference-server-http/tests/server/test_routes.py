import logging

import flask
from inference_schema.parameter_types.standard_py_parameter_type import StandardPythonParameterType
from inference_schema.schema_decorators import input_schema
import pytest

from azureml_inference_server_http.api.aml_response import AMLResponse
from azureml_inference_server_http.server.routes import HEADER_LIMIT
from .common import TestingClient
from .utils import assert_valid_guid


# Health


def test_routes_health(app: flask.Flask, client: TestingClient):
    response = client.get_health()
    assert response.status_code == 200
    assert response.data == b"Healthy"


# Headers


@pytest.mark.parametrize(("to_error"), [True, False])
def test_routes_request_id(app: flask.Flask, client: TestingClient, to_error: bool):
    """Ensure the request id is generated and propagated back to the user.."""

    @app.set_user_run
    @input_schema("error", StandardPythonParameterType(False))
    def run(error):
        if error:
            raise RuntimeError

    # A x-request-id is not provided. Server should generate one.
    response = client.post_score({"error": to_error})
    assert_valid_guid(response.headers["x-request-id"])
    assert response.headers["x-request-id"] == response.headers["x-ms-request-id"]

    # A x-request-id provided. Server should return the same.
    request_id = test_routes_request_id.__name__
    response = client.post_score({"error": to_error}, headers={"x-request-id": request_id})
    assert response.headers["x-request-id"] == request_id
    assert response.headers["x-ms-request-id"] == request_id


def test_routes_request_id_limit(app: flask.Flask, client: TestingClient):
    """Ensure we error when the request id is too long."""

    # Just within the limit
    response = client.get_score(headers={"x-request-id": "A" * (HEADER_LIMIT)})
    assert response.status_code == 200

    # Slightly over the limit
    response = client.get_score(headers={"x-request-id": "A" * (HEADER_LIMIT + 1)})
    assert response.status_code == 431
    assert "x-request-id" not in response.headers
    assert "x-ms-request-id" not in response.headers
    assert "x-ms-client-request-id" not in response.headers

    assert response.json == {"message": f"x-request-id must not exceed {HEADER_LIMIT} characters"}


def test_routes_x_ms_request_id(client: TestingClient, caplog):
    """Ensure we log warning when the request has x-ms-request-id header"""

    with caplog.at_level(logging.WARNING, logger="azmlinfsrv"):
        response = client.get_score(headers={"x-ms-request-id": "1234"})
        assert response.status_code == 200
    info_tuple = (
        "azmlinfsrv",
        logging.WARNING,
        (
            "x-ms-request-id header has been deprecated and will be removed from future versions of the server. "
            "Please use x-ms-client-request-id."
        ),
    )
    assert info_tuple in caplog.record_tuples


@pytest.mark.parametrize(("to_error"), [True, False])
def test_routes_client_request_id(app: flask.Flask, client: TestingClient, to_error: bool):
    """We support Client Request ID from x-ms-request-id (legacy, deprecated) and x-ms-client-request-id. Validate the
    correctness when none, or one, or both of these values are provided."""

    @app.set_user_run
    @input_schema("error", StandardPythonParameterType(False))
    def run(error):
        if error:
            raise RuntimeError

    # When the client doesn't provide x-ms-client-request-id, server shouldn't generate it.
    response = client.post_score({"error": to_error})
    assert "x-ms-client-request-id" not in response.headers

    # When the client only provides a value for x-ms-request-id, it is copied to x-ms-client-request-id and treated as
    # the Client Request ID.
    response = client.post_score({"error": to_error}, headers={"x-ms-request-id": "A"})
    assert response.headers["x-ms-request-id"] == "A"
    assert response.headers["x-ms-client-request-id"] == "A"

    # When the client only provides a value for x-ms-client-request-id, it is copied to x-ms-request-id and treated as
    # the Client Request ID.
    response = client.post_score({"error": to_error}, headers={"x-ms-client-request-id": "A"})
    assert response.headers["x-ms-request-id"] == "A"
    assert response.headers["x-ms-client-request-id"] == "A"

    # When the client provides both x-ms-request-id and x-ms-client-request-id, ensure we return both of them as-is.
    response = client.post_score({"error": to_error}, headers={"x-ms-request-id": "A", "x-ms-client-request-id": "B"})
    assert response.headers["x-ms-request-id"] == "A"
    assert response.headers["x-ms-client-request-id"] == "B"


@pytest.mark.parametrize("client_request_id_name", ["x-ms-request-id", "x-ms-client-request-id"])
def test_routes_client_request_id_limit(app: flask.Flask, client: TestingClient, client_request_id_name: str):
    """Ensure we error when the client request id is too long."""

    # Just within the limit
    response = client.get_score(headers={client_request_id_name: "A" * (HEADER_LIMIT)})
    assert response.status_code == 200

    # Slightly over the limit
    response = client.get_score(headers={client_request_id_name: "A" * (HEADER_LIMIT + 1)})
    assert response.status_code == 431
    assert_valid_guid(response.headers["x-request-id"])
    assert "x-ms-request-id" not in response.headers
    assert "x-ms-client-request-id" not in response.headers

    assert response.json == {
        "message": f"x-ms-request-id and x-ms-client-request-id must not exceed {HEADER_LIMIT} characters"
    }

    # Make sure we retain the value of the request id when it is specified.
    response = client.get_score(headers={"x-request-id": "A", client_request_id_name: "B" * (HEADER_LIMIT + 1)})
    assert response.status_code == 431
    assert response.headers["x-request-id"] == "A"
    assert "x-ms-request-id" not in response.headers
    assert "x-ms-client-request-id" not in response.headers


def test_routes_trace_id(client: TestingClient):
    """Verifies that a GET request to the /score path with the
    trace ID header properly passes back the trace ID when specified."""

    response = client.get_score(headers={"TraceId": "test-id"})
    assert response.headers["TraceId"] == "test-id"


def test_routes_request_id_not_overwritten(app: flask.Flask, client: TestingClient):
    """Verifies that x-request-id cannot be overwritten in the scoring script"""

    @app.set_user_run
    def run(data):
        resp = AMLResponse("", 200)
        resp.headers["x-request-id"] = "cannot-be-overwritten"
        return resp

    response = client.post_score(headers={"x-request-id": "623c3df9-3ef0-4905-a3cc-6ef015f17c3f"})
    assert response.status_code == 200
    assert response.headers["x-request-id"] == "623c3df9-3ef0-4905-a3cc-6ef015f17c3f"


# Scoring response


def test_routes_scoring_response_json(app: flask.Flask, client: TestingClient):
    """Responses are encoded in JSON by default."""

    @app.set_user_run
    def run(data):
        return {"a": 1}

    response = client.get_score()
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json == {"a": 1}


def test_routes_scoring_amlresponse_empty(app: flask.Flask, client: TestingClient):
    """When ``None`` is provided as the response output, AMLResponse converts it to an empty JSON object."""

    @app.set_user_run
    def run(data):
        return AMLResponse(None, 333)

    response = client.get_score()
    assert response.status_code == 333
    assert response.headers["content-type"] == "application/json"
    assert response.headers["x-ms-run-function-failed"] == "False"
    assert response.json == {}


def test_routes_scoring_amlresponse_string(app: flask.Flask, client: TestingClient):
    """The data passed to AMLResponse is not converted to JSON and is returned as-is."""

    @app.set_user_run
    def run(data):
        return AMLResponse("test", 444)

    response = client.get_score()
    assert response.status_code == 444
    assert response.headers["content-type"] != "application/json"
    assert response.headers["x-ms-run-function-failed"] == "False"
    assert response.data == b"test"


def test_routes_scoring_amlresponse_json(app: flask.Flask, client: TestingClient):
    """Ensure the response body is encoded in JSON when ``json_str`` is set."""

    @app.set_user_run
    def run(data):
        return AMLResponse("test", 555, json_str=True)

    response = client.get_score()
    assert response.status_code == 555
    assert response.headers["content-type"] == "application/json"
    assert response.headers["x-ms-run-function-failed"] == "True"
    assert response.data == b'"test"'


def test_routes_scoring_amlresponse_headers(app: flask.Flask, client: TestingClient):
    """Validates how headers are being added to the response. Whether this is right or wrong
    is a different question."""

    @app.set_user_run
    def run(data):
        headers = {"a": "A", "b": "A, B, C", "content-type": "A", "x-ms-run-function-failed": "Z"}
        return AMLResponse(None, 555, headers, run_function_failed=True)

    response = client.get_score()

    # User header
    assert response.headers["a"] == "A"

    # AMLResponse will split the header by comma.
    header_b = [value for header, value in response.headers.items() if header == "b"]
    assert header_b == ["A", "B", "C"]

    # While the user did specify a value for these headers, they are overwritten.
    assert response.headers["content-type"] == "application/json"
    assert response.headers["x-ms-run-function-failed"] == "True"


def test_routes_scoring_amlresponse_failed(app: flask.Flask, client: TestingClient):
    """Ensure the header "x-ms-run-function-failed" is set to true"""

    @app.set_user_run
    def run(data):
        return AMLResponse(None, 555)

    response = client.get_score()
    assert response.headers["x-ms-run-function-failed"] == "True"


def test_routes_scoring_cors_enabled(app_cors: flask.Flask):
    """Verifies that an OPTIONS request to /score returns an expected value in Access-Control-Allow-Origin
    header if AML_CORS_ORIGINS is set"""

    response = app_cors.test_client().options_score(headers={"Origin": "www.microsoft.com"})
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == "www.microsoft.com"


def test_routes_scoring_cors_enabled_2(app_cors: flask.Flask):
    """Verifies that an OPTIONS request to /score does not return Access-Control-Allow-Origin header
    when the origin is not allowed"""

    response = app_cors.test_client().options_score(headers={"Origin": "www.azure.com"})
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers


# Errors


def test_routes_404(client: TestingClient):
    response = client.get("/does_not_exist")
    assert response.status_code == 404
    assert response.json == {
        "message": (
            "The requested URL was not found on the server."
            " If you entered the URL manually please check your spelling and try again."
        )
    }


def test_routes_405(client: TestingClient):
    response = client.delete("/")
    assert response.status_code == 405
    assert response.json == {"message": "The method is not allowed for the requested URL."}
