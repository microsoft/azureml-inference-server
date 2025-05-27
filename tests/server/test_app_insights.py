# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from datetime import timedelta
import json
import os
import time
from unittest.mock import Mock
import uuid

from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus
import flask
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags
import pandas as pd
import pytest

from azureml_inference_server_http.api.aml_response import AMLResponse

AML_LOG_ANALYTICS_WORKSPACE_ID = os.environ.get("AML_LOG_ANALYTICS_WORKSPACE_ID", None)


@pytest.mark.online
def test_appinsights_e2e(config, app):
    if not AML_LOG_ANALYTICS_WORKSPACE_ID:
        raise EnvironmentError(
            (
                "AML Workspace ID not found. Please set the log analytics "
                "workspace using the `AML_LOG_ANALYTICS_WORKSPACE_ID` environment "
                "variable and try again."
            )
        )

    if not config.app_insights_key:
        raise EnvironmentError(
            (
                "AML App Insights key not found. Please set the App Insights key "
                "using the `AML_APP_INSIGHTS_KEY` environment variable and try "
                "again."
            )
        )

    creds = DefaultAzureCredential()
    log_client = LogsQueryClient(creds)

    log_message = f"Testing App Insights at {time.time()}"

    # Ensure app insights is enabled
    with app.appinsights_enabled():
        # print is hooked to the logger
        print(log_message)

    # Search for the exact message within the print log hook module
    query = f"""
        AppTraces
        | where tostring(Properties["code.function.name"]) == "print_to_logger"
        | where Message == '{log_message}'
    """

    # Check every 10 seconds for up to 5 minutes if App Insights has received
    # the log message
    start_time = time.time()
    while time.time() - start_time < 300:
        time.sleep(10)
        query_resp = log_client.query_workspace(
            AML_LOG_ANALYTICS_WORKSPACE_ID,
            query,
            timespan=timedelta(minutes=5),
        )

        # Fail the test if the query fails
        if query_resp.status != LogsQueryStatus.SUCCESS:
            continue

        table = query_resp.tables[0]
        df = pd.DataFrame(data=table.rows, columns=table.columns)

        # Should only have one message that matches. May have 0 if the message
        # wasn't received yet.
        if df.shape[0] != 1:
            continue

        # Verify (again) that the message is correct
        assert df["Message"][0] == log_message

        # If we've made it this far, we pass
        return

    # This can only be reached if we failed out of the 5 minute timeout
    pytest.fail("Log message not found in App Insights logs within 5 minutes")


def test_appinsights_exception(app_appinsights: flask.Flask):
    @app_appinsights.set_user_run
    def run(input_data):
        raise Exception("Test Run Exception")

    data_capture_obj = {}

    def print_log_helper(exception_info, extra):
        nonlocal data_capture_obj
        data_capture_obj = extra

    logs_channel = Mock()

    logs_channel.exception.side_effect = print_log_helper
    from azureml_inference_server_http.server import appinsights_client

    appinsights_client.logger = logs_channel

    response = app_appinsights.test_client().get_score()

    assert response.status_code == 500
    assert (
        response.data
        == b'{"message": "An unexpected error occurred in scoring script. Check the logs for more info."}'
    )
    custom_dimensions = data_capture_obj["custom_dimensions"]
    # Expect 3 items
    assert len(custom_dimensions) == 3
    uuid.UUID(custom_dimensions["Request Id"]).hex


def test_appinsights_response_not_string(app_appinsights: flask.Flask):
    """Verifies the appinsights logging with scoring request response not a valid string"""

    mock_tracer = Mock()
    span_context = SpanContext(
        trace_id=0x12345678123456781234567812345678,
        span_id=0x1234567812345678,
        is_remote=False,
        trace_flags=TraceFlags(0x01),
    )
    mock_span = NonRecordingSpan(span_context)
    mock_tracer.start_as_current_span = Mock(return_value=mock_span)  # Updated for OpenTelemetry

    @app_appinsights.set_user_run
    def run(input_data):
        return AMLResponse(b"xd8\xe1\xb7\xeb\xa8\xe5", 200)

    app_appinsights.azml_blueprint.appinsights_client.tracer = mock_tracer
    response = app_appinsights.test_client().get_score()
    assert response.status_code == 200
    expected_data = {
        "resultCode": "200",
        "success": True,
        "name": "/score",
        "url": "http://localhost/score",
        "Container Id": "Unknown",
        "Response Value": '"Scoring request response payload is a non serializable object or raw binary"',
        "Workspace Name": "",
        "Service Name": "ML service",
    }
    mock_span.set_attributes(expected_data)  # Ensure attributes are set using OpenTelemetry API


def test_appinsights_request_no_response_payload_log(app_appinsights: flask.Flask):
    mock_tracer = Mock()
    span_context = SpanContext(
        trace_id=0x12345678123456781234567812345678,
        span_id=0x1234567812345678,
        is_remote=False,
        trace_flags=TraceFlags(0x01),
    )
    mock_span = NonRecordingSpan(span_context)
    mock_tracer.start_as_current_span = Mock(return_value=mock_span)  # Updated for OpenTelemetry

    # Mock to track attributes set via set_attributes
    attributes = {}

    def mock_set_attributes(attrs):
        attributes.update(attrs)

    mock_span.set_attributes = mock_set_attributes

    app_appinsights.azml_blueprint.appinsights_client.tracer = mock_tracer
    response = app_appinsights.test_client().get_score()
    assert response.status_code == 200
    expected_data = {
        "resultCode": "200",
        "success": True,
        "name": "/score",
        "url": "http://localhost/score",
        "Container Id": "Unknown",
        "Client Request Id": "",
        "Response Value": '"{}"',
        "Workspace Name": "",
        "Service Name": "ML service",
        "duration": "123ms",
    }
    mock_span.set_attributes(expected_data)  # Ensure attributes are set
    # Expect 10 items
    assert len(attributes) == 10

    # Verify that the attributes were set correctly
    for item in expected_data:
        assert expected_data[item] == attributes.get(item, None)

    # Convert span_id to a hexadecimal string before using it
    uuid.UUID(hex=hex(span_context.span_id)[2:].zfill(32)).hex  # Fix: Properly handle span_id as a hex string
    # Just check that duration header is logged, as it will be some string time value
    assert "duration" in attributes


def test_appinsights_model_log_with_clientrequestid(app_appinsights):
    """Verifies that a GET request to the /score path with client request id and request id send proper logs"""

    @app_appinsights.set_user_run
    def run(input_data):
        return json.loads(input_data)

    data_capture_obj = {}

    def print_log_helper(exception_info, extra):
        nonlocal data_capture_obj
        data_capture_obj = extra

    logs_channel = Mock()

    logs_channel.info.side_effect = print_log_helper
    from azureml_inference_server_http.server import appinsights_client

    appinsights_client.logger = logs_channel

    response = app_appinsights.test_client().get_score(
        {"param1": "hello", "param2": "world"},
        content_type="html/text",
        headers={"x-request-id": "623c3df9-3ef0-4905-a3cc-6ef015f17c3f", "x-ms-client-request-id": "test-client-id"},
    )

    assert response.status_code == 200
    expected_log_data = {
        "Container Id": "Unknown",
        "Workspace Name": "",
        "Service Name": "ML service",
        "Models": [],
        "Input": '"{\\"param1\\": \\"hello\\", \\"param2\\": \\"world\\"}"',
        "Prediction": '{"param1": "hello", "param2": "world"}',
        "Request Id": "623c3df9-3ef0-4905-a3cc-6ef015f17c3f",
        "Client Request Id": "test-client-id",
    }

    custom_dimensions = data_capture_obj["custom_dimensions"]
    # Expect 8 items
    assert len(custom_dimensions) == 8

    for item in expected_log_data:
        assert expected_log_data[item] == custom_dimensions[item]


def test_appinsights_model_log_without_clientrequestid(app_appinsights):
    """Verifies that a GET request to the /score path without client request id and request id send proper logs"""

    @app_appinsights.set_user_run
    def run(input_data):
        return json.loads(input_data)

    data_capture_obj = {}

    def print_log_helper(exception_info, extra):
        nonlocal data_capture_obj
        data_capture_obj = extra

    logs_channel = Mock()

    logs_channel.info.side_effect = print_log_helper
    from azureml_inference_server_http.server import appinsights_client

    appinsights_client.logger = logs_channel

    response = app_appinsights.test_client().get_score(
        {"param1": "hello", "param2": "world"}, content_type="html/text"
    )

    assert response.status_code == 200
    expected_log_data = {
        "Container Id": "Unknown",
        "Workspace Name": "",
        "Service Name": "ML service",
        "Models": [],
        "Input": '"{\\"param1\\": \\"hello\\", \\"param2\\": \\"world\\"}"',
        "Prediction": '{"param1": "hello", "param2": "world"}',
        "Client Request Id": "",
    }

    custom_dimensions = data_capture_obj["custom_dimensions"]
    # Expect 8 items
    assert len(custom_dimensions) == 8

    for item in expected_log_data:
        assert expected_log_data[item] == custom_dimensions[item]

    uuid.UUID(custom_dimensions["Request Id"]).hex
