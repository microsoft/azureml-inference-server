# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import datetime
import json
import logging
import os
import sys
import time
import requests  # Import the requests library

import flask
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor  # Import RequestsInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import get_tracer_provider, set_tracer_provider, SpanKind
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk._logs import LoggingHandler, LoggerProvider, set_logger_provider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from azure.monitor.opentelemetry.exporter import AzureMonitorLogExporter, AzureMonitorTraceExporter
from opentelemetry.sdk.trace.sampling import ALWAYS_ON

from .config import config

# Amount of time we wait before exiting the application when errors occur for exception log sending
WAIT_EXCEPTION_UPLOAD_IN_SECONDS = 30

logger = logging.getLogger("azmlinfsrv.trace")


class AppInsightsClient(object):
    """Batching parameters, whichever of the below conditions gets hit first will trigger a send.
    send_interval: interval in seconds
    send_buffer_size: max number of items to batch before sending
    """

    send_interval = 5.0
    send_buffer_size = 100

    def __init__(self):
        self.enabled = False
        self._model_ids = self._get_model_ids()
        self.azureLogHandler = None

        if config.app_insights_enabled and config.app_insights_key:
            try:
                connection_string = f"InstrumentationKey={config.app_insights_key.get_secret_value()}"

                # Configure the resource
                resource = Resource.create({"service.name": config.service_name})

                # Configure logging
                logger_provider = LoggerProvider(resource=resource)
                set_logger_provider(logger_provider)
                azure_log_exporter = AzureMonitorLogExporter(connection_string=connection_string)
                logger_provider.add_log_record_processor(BatchLogRecordProcessor(azure_log_exporter))

                # Attach the LoggingHandler to the logger
                self.azureLogHandler = LoggingHandler(level=logging.INFO)
                logger.addHandler(self.azureLogHandler)
                logging.getLogger("azmlinfsrv.print").addHandler(self.azureLogHandler)

                # Configure tracing
                tracer_provider = TracerProvider(resource=resource, sampler=ALWAYS_ON)
                azure_span_exporter = AzureMonitorTraceExporter(connection_string=connection_string)
                tracer_provider.add_span_processor(BatchSpanProcessor(azure_span_exporter))
                set_tracer_provider(tracer_provider)
                self.tracer = get_tracer_provider().get_tracer(__name__)

                # Instrument requests library
                RequestsInstrumentor().instrument(tracer_provider=get_tracer_provider())
                logger.info("Requests library instrumentation enabled.")

                # Test HTTP request to verify instrumentation
                response = requests.get("https://azure.microsoft.com/")
                logger.info(f"Test HTTP request status code: {response.status_code}")

                self._container_id = config.hostname
                self.enabled = True
                logger.info("AppInsightsClient initialized successfully.")
            except Exception as ex:
                self.log_app_insights_exception(ex)

    def close(self):
        if self.azureLogHandler:
            logger.removeHandler(self.azureLogHandler)
            logging.getLogger("azmlinfsrv.print").removeHandler(self.azureLogHandler)

    def log_app_insights_exception(self, ex):
        print("Error logging to Application Insights:")
        print(ex)

    def send_model_data_log(self, request_id, client_request_id, model_input, prediction):
        try:
            if not self.enabled or not config.mdc_storage_enabled:
                return
            properties = {
                "custom_dimensions": {
                    "Container Id": self._container_id,
                    "Request Id": request_id,
                    "Client Request Id": client_request_id,
                    "Workspace Name": config.workspace_name,
                    "Service Name": config.service_name,
                    "Models": self._model_ids,
                    "Input": json.dumps(model_input),
                    "Prediction": json.dumps(prediction),
                }
            }
            logger.info("model_data_collection", extra=properties)
        except Exception as ex:
            self.log_app_insights_exception(ex)

    def log_request(
        self,
        request: flask.Request,
        response: flask.Response,
        *,
        start_datetime: datetime.datetime,
        duration_ms: float,
        request_id: str,
        client_request_id: str,
    ) -> None:
        if not self.enabled:
            return

        if config.app_insights_log_response_enabled:
            # Check if response payload can be converted to a valid string
            try:
                response_value = response.get_data(as_text=True)
            except (UnicodeDecodeError, AttributeError) as ex:
                self.log_app_insights_exception(ex)
                response_value = "Scoring request response payload is a non serializable object or raw binary"

            # Encode the response value as JSON
            response_value = json.dumps(response_value)
        else:
            response_value = None

        successful = response.status_code < 400
        formatted_start_time = start_datetime.isoformat() + "Z"
        try:
            attributes = {
                "http.method": request.method,
                "http.url": request.url,
                "http.target": request.path,
                "http.status_code": response.status_code,
                "http.response_content_length": len(response.data) if response.data else 0,
                "http.client_ip": request.remote_addr,
                "ai.operation.id": request_id,
                "ai.operation.parentId": client_request_id,
                "ai.operation.name": request.path,
                "start_time": formatted_start_time,
                "duration": self._calc_duration(duration_ms),
                "success": successful,
                "Workspace Name": config.workspace_name,
                "Service Name": config.service_name,
            }

            # Send the log to the requests table using OpenTelemetry
            with self.tracer.start_as_current_span(request.path, kind=SpanKind.SERVER) as span:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
        except Exception as ex:
            logger.error("Error while logging request", exc_info=True)
            self.log_app_insights_exception(ex)

    def send_exception_log(self, exc_info, request_id="Unknown", client_request_id=""):
        try:
            if not self.enabled:
                return
            properties = {
                "custom_dimensions": {
                    "Container Id": self._container_id,
                    "Request Id": request_id,
                    "Client Request Id": client_request_id,
                }
            }

            logger.exception(exc_info, extra=properties)
        except Exception as ex:
            self.log_app_insights_exception(ex)

    def _calc_duration(self, duration):
        local_duration = duration or 0
        duration_parts = []
        for multiplier in [1000, 60, 60, 24]:
            duration_parts.append(local_duration % multiplier)
            local_duration //= multiplier
        duration_parts.reverse()
        formatted_duration = "%02d:%02d:%02d.%03d" % tuple(duration_parts)
        if local_duration:
            formatted_duration = "%d.%s" % (local_duration, formatted_duration)
        return formatted_duration

    def _get_model_ids(self):
        # Model information is stored in /var/azureml-app/model_config_map.json in AKS deployments. But, in ACI
        # deployments, that file does not exist due to a bug in container build-out code. Until the bug is fixed
        # /var/azureml-app/azureml-models will be used to enumerate all the models.
        model_ids = []
        try:
            models = [str(model) for model in os.listdir(config.azureml_model_dir)]

            for model in models:
                versions = [int(version) for version in os.listdir(os.path.join(config.azureml_model_dir, model))]
                ids = ["{}:{}".format(model, version) for version in versions]
                model_ids.extend(ids)
        except Exception:
            self.send_exception_log(sys.exc_info())

        return model_ids

    def wait_for_upload(self):
        if not self.enabled:
            return

        logger.info("Waiting for logs to be sent to Application Insights before exit.")
        logger.info(f"Waiting {WAIT_EXCEPTION_UPLOAD_IN_SECONDS} seconds for upload.")
        time.sleep(WAIT_EXCEPTION_UPLOAD_IN_SECONDS)
