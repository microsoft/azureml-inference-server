import logging
import os
import time
import aiotask_context as context
from opencensus.ext.azure.log_exporter import AzureLogHandler

from .constants import (
    CUSTOM_DIMENSIONS,
    ENV_AML_APP_INSIGHTS_ENABLED,
    ENV_AML_APP_INSIGHTS_KEY,
    CONTAINER_ID,
    WORKSPACE_NAME,
    SERVER_TIMESTAMP,
    REQUEST_ID,
    SERVICE_NAME,
    ENV_WORKSPACE_NAME,
    ENV_SERVICE_NAME,
    ENV_HOSTNAME,
)


def get_request_id():
    try:
        return context.get("x-ms-request-id") or ""
    except (ValueError, AttributeError):
        return ""


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        record.request_id = get_request_id()
        return True


LOG_SETTINGS = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default",
            "filters": ["requestid"],
        },
        "appinsights": {
            "class": "opencensus.ext.azure.log_exporter.AzureLogHandler",
            "level": "INFO",
            "formatter": "default",
            "connection_string": f"InstrumentationKey={os.environ.get(ENV_AML_APP_INSIGHTS_KEY, '')}",
            "filters": ["requestid"],
        },
    },
    "filters": {
        "requestid": {
            "()": RequestIdFilter,
        },
    },
    "formatters": {
        "default": {
            "format": "%(asctime)s - [%(levelname)s] %(module)s::%(funcName)s():l%(lineno)d %(request_id)s | %(message)s",
        },
        "appinsights": {
            "format": "%(asctime)s - [%(levelname)s] %(module)s::%(funcName)s():l%(lineno)d %(request_id)s | %(message)s",
        },
    },
    "loggers": {
        "": {"level": "INFO", "handlers": ["console", "appinsights"], "propagate": True},
    },
}


def get_custom_dimensions():
    """
    Create custom dimensions for logging with appinsights/opencensus.
    NOTE: we load environment variables here instead of config_manager because this executes before config_manager
    """
    workspace_name = os.environ.get(ENV_WORKSPACE_NAME, "")
    service_name = os.environ.get(ENV_SERVICE_NAME, "")
    host = os.environ.get(ENV_HOSTNAME, "Unknown")
    srv_timestamp = time.time()
    request_id = get_request_id()
    return {
        CUSTOM_DIMENSIONS: {
            CONTAINER_ID: host,
            # "Syslog Timestamp": syslog_timestamp, # TODO: do we need to add syslog?
            SERVER_TIMESTAMP: srv_timestamp,
            REQUEST_ID: request_id,
            WORKSPACE_NAME: workspace_name,
            SERVICE_NAME: service_name,
        }
    }


def get_log_settings():
    if os.environ.get(ENV_AML_APP_INSIGHTS_ENABLED, "false").lower() != "true":
        # Remove the appinsights handler if not enabled
        # TODO: should we do this if ENV_AML_APP_INSIGHTS_KEY is wrong?
        if "appinsights" in LOG_SETTINGS["handlers"]:
            del LOG_SETTINGS["handlers"]["appinsights"]
        if "appinsights" in LOG_SETTINGS["loggers"][""]["handlers"]:
            LOG_SETTINGS["loggers"][""]["handlers"].remove("appinsights")
    return LOG_SETTINGS
