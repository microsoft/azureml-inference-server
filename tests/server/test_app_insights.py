# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import builtins
from datetime import datetime, timedelta, timezone
import json
import logging
import os
import time
from unittest.mock import Mock
import uuid

from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential
from azure.monitor.query import LogsQueryClient, LogsQueryStatus
import flask
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags
import pandas as pd
import pytest

from azureml_inference_server_http.api.aml_response import AMLResponse
from azureml_inference_server_http.print_log_hook import print_to_logger

AML_LOG_ANALYTICS_WORKSPACE_ID = os.environ.get("AML_LOG_ANALYTICS_WORKSPACE_ID", None)
logger = logging.getLogger(__name__)


def test_appinsights_log_handler(config, monkeypatch):
    from azureml_inference_server_http.server import appinsights_client
    from opentelemetry.instrumentation.logging.handler import LoggingHandler

    config.app_insights_enabled = False
    client = appinsights_client.AppInsightsClient()
    provider = Mock()
    monkeypatch.setattr(appinsights_client, "LoggerProvider", Mock(return_value=provider))
    monkeypatch.setattr(appinsights_client, "set_logger_provider", Mock())
    monkeypatch.setattr(appinsights_client, "get_logger_provider", Mock(return_value=provider))
    monkeypatch.setattr(appinsights_client, "AzureMonitorLogExporter", Mock())
    monkeypatch.setattr(appinsights_client, "BatchLogRecordProcessor", Mock())
    root_handlers = list(logging.getLogger().handlers)

    try:
        client.init_otel_log("unused", None)
        assert isinstance(client.azureLogHandler, LoggingHandler)
        assert client.azureLogHandler in appinsights_client.logger.handlers
        assert client.azureLogHandler in logging.getLogger("azmlinfsrv.print").handlers
        assert logging.getLogger().handlers == root_handlers

        record = logging.LogRecord(
            "azmlinfsrv.print", logging.INFO, __file__, 1, "test message", (), None, "print_to_logger"
        )
        record.custom_dimensions = {"Request Id": "test-request"}
        client.azureLogHandler.emit(record)

        emitted_record = provider.get_logger.return_value.emit.call_args.args[0]
        assert emitted_record.body == "test message"
        assert emitted_record.attributes["code.function.name"] == "print_to_logger"
        assert emitted_record.attributes["custom_dimensions"] == {"Request Id": "test-request"}
    finally:
        client.close()


@pytest.mark.online
def test_appinsights_e2e(config, app, caplog):
    caplog.set_level(logging.INFO, logger=__name__)
    logger.info(
        "App Insights E2E configuration: workspace_id=%s, instrumentation_key_configured=%s, " "initially_enabled=%s",
        AML_LOG_ANALYTICS_WORKSPACE_ID,
        bool(config.app_insights_key),
        config.app_insights_enabled,
    )
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
    logger.info(
        "Created LogsQueryClient with %s; authentication occurs when querying the workspace.",
        type(creds).__name__,
    )

    log_message = f"Testing App Insights at {time.time()}"

    # Ensure app insights is enabled
    with app.appinsights_enabled():
        insights_client = app.azml_blueprint.appinsights_client
        print_logger = logging.getLogger("azmlinfsrv.print")
        logger.info(
            "Telemetry setup: client_enabled=%s, handler_type=%s, handler_attached=%s, "
            "print_logger_disabled=%s, print_logger_effective_level=%s, print_hook_installed=%s, "
            "batch_interval_seconds=%s",
            insights_client.enabled,
            type(insights_client.azureLogHandler).__name__,
            insights_client.azureLogHandler in print_logger.handlers,
            print_logger.disabled,
            logging.getLevelName(print_logger.getEffectiveLevel()),
            builtins.print is print_to_logger,
            insights_client.send_interval,
        )
        emitted_at = datetime.now(timezone.utc)
        logger.info("Emitting test message at %s: %s", emitted_at.isoformat(), log_message)
        # print is hooked to the logger
        print(log_message)
    logger.info("Exited telemetry context; waiting for asynchronous export and workspace ingestion.")

    # Search for the exact message within the print log hook module
    query = f"""
        AppTraces
        | where tostring(Properties["code.function.name"]) == "print_to_logger"
        | where Message == '{log_message}'
    """
    query_timespan = timedelta(minutes=15)
    logger.info(
        "Polling workspace every 10 seconds for up to 300 seconds with a rolling %s query window.",
        query_timespan,
    )
    logger.info("Kusto query:%s", query)

    # Check every 10 seconds for up to 5 minutes if App Insights has received
    # the log message
    start_time = time.monotonic()
    attempts = 0
    last_status = None
    last_row_count = None
    while time.monotonic() - start_time < 300:
        time.sleep(10)
        attempts += 1
        query_started = time.monotonic()
        query_end = datetime.now(timezone.utc)
        query_start = query_end - query_timespan
        logger.info(
            "Query attempt %d: elapsed_seconds=%.1f, approximate_utc_window=[%s, %s], "
            "message_age_seconds=%.1f, emission_within_window=%s",
            attempts,
            query_started - start_time,
            query_start.isoformat(),
            query_end.isoformat(),
            (query_end - emitted_at).total_seconds(),
            query_start <= emitted_at <= query_end,
        )
        try:
            query_resp = log_client.query_workspace(
                AML_LOG_ANALYTICS_WORKSPACE_ID,
                query,
                timespan=query_timespan,
            )
        except AzureError as exc:
            logger.error(
                "Workspace query attempt %d failed after %.1f seconds: error_type=%s, "
                "status_code=%s. Check Azure credentials, workspace query permissions, and connectivity.",
                attempts,
                time.monotonic() - query_started,
                type(exc).__name__,
                getattr(exc, "status_code", None),
            )
            raise

        last_status = query_resp.status
        last_row_count = None
        logger.info(
            "Query attempt %d completed: status=%s, duration_seconds=%.1f",
            attempts,
            last_status,
            time.monotonic() - query_started,
        )

        if query_resp.status != LogsQueryStatus.SUCCESS:
            error = query_resp.partial_error
            logger.warning(
                "Query returned partial results: error_code=%s, error_message=%s, partial_row_counts=%s",
                error.code if error is not None else None,
                error.message if error is not None else None,
                [len(table.rows) for table in (query_resp.partial_data or [])],
            )
            continue

        table = query_resp.tables[0]
        last_row_count = len(table.rows)
        logger.info(
            "Query result: table_count=%d, matching_rows=%d, columns=%s",
            len(query_resp.tables),
            last_row_count,
            table.columns,
        )
        df = pd.DataFrame(data=table.rows, columns=table.columns)

        # Should only have one message that matches. May have 0 if the message
        # wasn't received yet.
        if df.shape[0] != 1:
            logger.warning("Expected exactly one matching trace, found %d; retrying.", df.shape[0])
            continue

        # Verify (again) that the message is correct
        assert df["Message"][0] == log_message

        # If we've made it this far, we pass
        logger.info(
            "Verified App Insights message after %d attempts and %.1f seconds; TimeGenerated=%s",
            attempts,
            time.monotonic() - start_time,
            df["TimeGenerated"][0] if "TimeGenerated" in df.columns else "<column not returned>",
        )
        return

    # This can only be reached if we failed out of the 5 minute timeout
    logger.error(
        "App Insights verification timed out: elapsed_seconds=%.1f, attempts=%d, last_status=%s, "
        "last_matching_rows=%s, workspace_id=%s, emitted_at=%s, message=%s. "
        "The query window may now exclude the message; check ingestion delay, "
        "the Application Insights workspace association, and the code.function.name filter.",
        time.monotonic() - start_time,
        attempts,
        last_status,
        last_row_count,
        AML_LOG_ANALYTICS_WORKSPACE_ID,
        emitted_at.isoformat(),
        log_message,
    )
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
