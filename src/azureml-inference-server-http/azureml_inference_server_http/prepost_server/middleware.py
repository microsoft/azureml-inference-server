import os
import uuid
from sanic.log import logger
from .constants import LOG_LEVEL_MAP
import aiotask_context as context

from .log_settings import get_custom_dimensions

#
# Request Middlewares
#


async def add_request_id_if_not_exists(request):
    if "x-ms-request-id" not in request.headers:
        request_id = str(uuid.uuid4())
        request.headers["x-ms-request-id"] = request_id
        context.set("x-ms-request-id", request_id)
    else:
        request_id = request.headers.get("x-ms-request-id")
    context.set("x-ms-request-id", request_id)


async def set_log_level(request):
    """Set maximum log-level from request headers"""
    if "x-ms-log-level" in request.headers:
        levels = request.headers.getall("x-ms-log-level")
        level_codes = [LOG_LEVEL_MAP.get(level) for level in levels]
        filtered = list(filter(lambda x: x is not None, level_codes))
        if len(filtered) == 0:
            logger.info(
                f"Unknown logging level(s) {levels}. Options are notset, debug, info, warning, error, "
                f"and critical. Please refer to Python's logging module documentation here: "
                f"https://docs.python.org/3/library/logging.html#levels",
                extra=get_custom_dimensions(),
            )
            return
        log_level = min(level_codes)
        request.ctx.former_log_level = logger.level
        logger.info(
            f"Setting logging level to {log_level} for request id {request.headers['x-ms-request-id']}.",
            extra=get_custom_dimensions(),
        )
        logger.setLevel(log_level)


#
# Response Middlewares
#


async def add_x_ms_headers(request, response):
    # In case there are multiple "x-ms-request-id" in the request header,
    # we need to make them available in the response header.
    if "x-ms-request-id" in request.headers:
        for value in request.headers.getall("x-ms-request-id"):
            response.headers.add("x-ms-request-id", value)

    server_ver = os.environ.get("HTTP_X_MS_SERVER_VERSION", "")
    if server_ver:
        response.headers.add("x-ms-server-version", server_ver)


async def reset_log_level(request, response):
    ctx = vars(request.ctx)
    if ctx.get("former_log_level"):
        logger.setLevel(ctx.get("former_log_level"))
        logger.log(msg=f"Reset logging level to {logger.level}.", level=logger.level, extra=get_custom_dimensions())


async def add_response_run_function_failed(request, response):
    if request.headers.get("x-ms-run-function-failed"):
        response.headers.add("x-ms-run-function-failed", "True")
