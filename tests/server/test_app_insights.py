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
from azure.monitor.opentelemetry.exporter import AzureMonitorLogExporter
from azure.monitor.query import LogsQueryClient, LogsQueryStatus
import flask
from opentelemetry._logs import get_logger_provider
from opentelemetry.sdk._logs.export import LogRecordExportResult
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

    provider.force_flush.assert_called_once()


@pytest.mark.online
def test_appinsights_e2e(config, app, caplog, monkeypatch):
    caplog.set_level(logging.INFO, logger=__name__)
    caplog.set_level(logging.INFO, logger="azure.monitor.opentelemetry.exporter")
    for name in (
        "azure.monitor.opentelemetry.exporter.export._base",
        "azure.monitor.opentelemetry.exporter.export.logs._exporter",
    ):
        monkeypatch.setattr(logging.getLogger(name), "disabled", False)
    logger.info(
        "App Insights E2E configuration: workspace_id=%s, instrumentation_key_configured=%s, initially_enabled=%s",
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

    log_message = f"Testing App Insights {uuid.uuid4()}"
    export_attempts = []
    original_export = AzureMonitorLogExporter.export

    def observed_export(exporter, batch, **kwargs):
        target_records = [item.log_record for item in batch if item.log_record.body == log_message]
        attempt = None
        if target_records:
            attempt = {"record_count": len(target_records), "result": None}
            export_attempts.append(attempt)
            logger.info(
                "Exporter received target message: record_count=%d, attributes=%r",
                len(target_records),
                [record.attributes for record in target_records],
            )

        result = original_export(exporter, batch, **kwargs)
        if attempt is not None:
            attempt["result"] = result
            logger.info("Target message export completed: result=%s", result)
        return result

    monkeypatch.setattr(AzureMonitorLogExporter, "export", observed_export)

    with app.appinsights_enabled():
        insights_client = app.azml_blueprint.appinsights_client
        print_logger = logging.getLogger("azmlinfsrv.print")

        assert insights_client.enabled, "App Insights client initialization failed"
        assert builtins.print is print_to_logger, "The print logging hook is not installed"
        assert print_logger.isEnabledFor(logging.INFO), "The print logger is filtering INFO records"
        assert insights_client.azureLogHandler in print_logger.handlers, "The Azure logging handler is not attached"

        emitted_at = datetime.now(timezone.utc)
        logger.info("Emitting test message at %s: %s", emitted_at.isoformat(), log_message)
        print(log_message)
        assert get_logger_provider().force_flush(timeout_millis=30_000), "Telemetry flush did not complete"
        assert export_attempts, (
            "The target message never reached AzureMonitorLogExporter.export; "
            "check logging handler, provider, and processor dispatch"
        )
        assert all(attempt["result"] == LogRecordExportResult.SUCCESS for attempt in export_attempts), (
            f"Target message export failed or raised an exception: {export_attempts!r}. "
            "Check captured exporter logs for ingestion authentication, endpoint, or connectivity errors"
        )

    # Query by message first so missing code attributes cannot hide an ingested record.
    query = f"""
        AppTraces
        | where Message == '{log_message}'
        | project TimeGenerated, Message, Properties
    """
    query_timespan = timedelta(minutes=15)
    query_start = emitted_at - query_timespan
    logger.info(
        "Export succeeded; polling workspace for up to 300 seconds with a fixed start %s before emission.",
        query_timespan,
    )
    logger.info("Kusto query:%s", query)

    start_time = time.monotonic()
    deadline = start_time + 300
    attempts = 0
    last_status = None
    last_row_count = None
    with DefaultAzureCredential() as creds, LogsQueryClient(creds) as log_client:
        while time.monotonic() < deadline:
            attempts += 1
            query_started = time.monotonic()
            query_end = datetime.now(timezone.utc)
            logger.info(
                "Query attempt %d: elapsed_seconds=%.1f, utc_window=[%s, %s]",
                attempts,
                query_started - start_time,
                query_start.isoformat(),
                query_end.isoformat(),
            )
            try:
                query_resp = log_client.query_workspace(
                    AML_LOG_ANALYTICS_WORKSPACE_ID,
                    query,
                    timespan=(query_start, query_end),
                    server_timeout=30,
                )
            except AzureError as exc:
                logger.error(
                    "Workspace query attempt %d failed: error_type=%s, status_code=%s. "
                    "Check Azure credentials, workspace query permissions, and connectivity.",
                    attempts,
                    type(exc).__name__,
                    getattr(exc, "status_code", None),
                )
                raise

            last_status = query_resp.status
            last_row_count = None
            if last_status != LogsQueryStatus.SUCCESS:
                error = query_resp.partial_error
                logger.warning(
                    "Query returned partial results: error_code=%s, error_message=%s",
                    error.code if error is not None else None,
                    error.message if error is not None else None,
                )
            else:
                assert query_resp.tables, "Successful workspace query returned no tables"
                table = query_resp.tables[0]
                last_row_count = len(table.rows)
                logger.info(
                    "Query attempt %d completed: matching_rows=%d, duration_seconds=%.1f",
                    attempts,
                    last_row_count,
                    time.monotonic() - query_started,
                )
                if table.rows:
                    df = pd.DataFrame(data=table.rows, columns=table.columns)
                    assert (df["Message"] == log_message).all()
                    properties = [json.loads(value) if isinstance(value, str) else value for value in df["Properties"]]
                    assert any(
                        value.get("code.function.name") == "print_to_logger" for value in properties
                    ), f"Message was ingested, but the print hook code attribute is missing or incorrect: {properties!r}"
                    logger.info(
                        "Verified App Insights message after %d attempts: matching_rows=%d, TimeGenerated=%s",
                        attempts,
                        last_row_count,
                        df["TimeGenerated"].tolist(),
                    )
                    return

            remaining = deadline - time.monotonic()
            if remaining > 0:
                time.sleep(min(10, remaining))

    failure_message = (
        f"Target message reached the exporter and export returned SUCCESS, but workspace ingestion "
        f"was not verified within 300 seconds: workspace_id={AML_LOG_ANALYTICS_WORKSPACE_ID}, "
        f"attempts={attempts}, last_status={last_status}, last_matching_rows={last_row_count}, "
        f"emitted_at={emitted_at.isoformat()}, message={log_message!r}. "
        "Check the Application Insights resource's workspace association and ingestion delay."
    )
    logger.error(failure_message)
    pytest.fail(failure_message)


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
