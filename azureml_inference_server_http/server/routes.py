# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import datetime
import faulthandler
import logging
import os
import time
import traceback
import uuid

from flask import g, request, Response
from werkzeug.exceptions import HTTPException

from azureml_inference_server_http.api.aml_response import AMLResponse
from .aml_blueprint import AMLInferenceBlueprint
from .config import config
from .input_parsers import (
    BadInput,
    JsonStringInput,
    RawRequestInput,
    UnsupportedHTTPMethod,
    UnsupportedInput,
)
from .swagger import SwaggerException
from .user_script import TimedResult, UserScriptException, UserScriptTimeout

# Get (hopefully useful, but at least obvious) output from segfaults, etc.
faulthandler.enable()

HEADER_LIMIT = 100

logger = logging.getLogger("azmlinfsrv")
main_blueprint = AMLInferenceBlueprint("main", __name__)


def wrap_response(response):
    response_headers = {}
    response_body = response
    response_status_code = 200

    return AMLResponse(response_body, response_status_code, response_headers, json_str=True)


@main_blueprint.route("/swagger.json", methods=["GET"])
def get_swagger_specification():
    g.api_name = "/swagger.json"
    version = request.args.get("version")

    # Setting default version where no query parameters passed
    if version is None:
        version = "2"

    try:
        swagger_json = main_blueprint.swagger.get_swagger(version)
        return AMLResponse(swagger_json, 200, json_str=True)
    except SwaggerException as e:
        return ErrorResponse(404, e.message)


# Health probe endpoint
@main_blueprint.route("/", methods=["GET"])
def health_probe():
    return "Healthy"


# Errors from Server Side
@main_blueprint.errorhandler(HTTPException)
def handle_http_exception(ex: HTTPException):
    if 400 <= ex.code < 500:
        logger.debug("Client request exception caught")
    elif 500 <= ex.code < 600:
        logger.debug("Server side exception caught")
    else:
        logger.debug("Caught an HTTP exception")

    return ErrorResponse(ex.code, ex.description)


# Unhandled Error
# catch all unhandled exceptions here and return the stack encountered in the response body
@main_blueprint.errorhandler(Exception)
def all_unhandled_exception(error):
    logger.debug("Unhandled exception generated")
    error_message = "Encountered Exception: {0}".format(traceback.format_exc())
    logger.error(error_message)
    internal_error = "An unexpected internal error occurred. Check the logs for more info."
    return ErrorResponse(500, internal_error)


@main_blueprint.before_request
def _before_request() -> None:
    g.api_name = None
    g.start_datetime = datetime.datetime.utcnow()
    g.starting_perf_counter = time.perf_counter()


@main_blueprint.before_request
def _init_headers() -> None:
    g.request_id = ""
    g.client_request_id = ""
    g.legacy_client_request_id = ""

    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    if len(request_id) <= HEADER_LIMIT:
        g.request_id = request_id
    else:
        return ErrorResponse(431, f"x-request-id must not exceed {HEADER_LIMIT} characters")

    # x-ms-request-id was used as both the Request ID and Client Request ID. Going forward we want to move users to
    # using `x-ms-request-id` for Request ID and `x-ms-client-request-id` for Client Request ID. To retain backwards
    # compatability, we need to make sure the value of `x-ms-request-id` is not empty.
    legacy_client_request_id = request.headers.get("x-ms-request-id", "")
    client_request_id = request.headers.get("x-ms-client-request-id", "")
    if legacy_client_request_id:
        # Warning message
        logger.warning(
            (
                "x-ms-request-id header has been deprecated and will be removed from future versions of the server."
                " Please use x-ms-client-request-id."
            )
        )
        # When `x-ms-request-id` is set and `x-ms-client-request-id` isn't. Use `x-ms-request-id` as the Client Request
        # ID.
        if not client_request_id:
            client_request_id = legacy_client_request_id
    else:
        # When `x-ms-request-id` not set, populate this value from `x-ms-client-request-id` or `x-request-id`. The
        # latter is guaranteed to have a value.
        legacy_client_request_id = client_request_id or request_id

    if len(legacy_client_request_id) <= HEADER_LIMIT and len(client_request_id) <= HEADER_LIMIT:
        g.legacy_client_request_id = legacy_client_request_id
        g.client_request_id = client_request_id
    else:
        return ErrorResponse(
            431, f"x-ms-request-id and x-ms-client-request-id must not exceed {HEADER_LIMIT} characters"
        )


@main_blueprint.after_request
def populate_response_headers(response: Response) -> Response:
    server_ver = os.environ.get("HTTP_X_MS_SERVER_VERSION", "")
    if server_ver:
        response.headers.add("x-ms-server-version", server_ver)

    # We may not have a request id we receive an invalid request id.
    if g.request_id:
        response.headers["x-request-id"] = g.request_id
    if g.legacy_client_request_id:
        response.headers["x-ms-request-id"] = g.legacy_client_request_id
    if g.client_request_id:
        response.headers["x-ms-client-request-id"] = g.client_request_id

    # Office services have their own tracing field 'TraceId', we need to support it.
    if "TraceId" in request.headers:
        response.headers.add("TraceId", request.headers["TraceId"])

    return response


# log all response status code after request is done
@main_blueprint.after_request
def _after_request(response: Response) -> Response:
    duration_ms = (time.perf_counter() - g.starting_perf_counter) * 1e3  # second to millisecond
    if g.api_name:
        path = request.path
        # No query, don't bother
        if request.query_string:
            path += f"?{request.query_string.decode()}"

        if response.is_streamed:
            response_length = "N/A"
        else:
            response_length = response.calculate_content_length()

        response_props = (
            request.method,
            path,
            response.status_code,
            # Always show 3 decimal places of precision
            "{:0.3f}ms".format(round(duration_ms, 3)),
            response_length,
        )

        logger.info(" ".join(map(str, response_props)))

    # Log to app insights
    if request.path != "/":
        main_blueprint.appinsights_client.log_request(
            request=request,
            response=response,
            start_datetime=g.start_datetime,
            duration_ms=duration_ms,
            request_id=g.request_id,
            client_request_id=g.client_request_id,
        )

    return response


def log_successful_request(timed_result: TimedResult):
    # This is ugly but we have to do this to maintain backwards compatibility. In the future we should simply log
    # `time_result.input` as-is.
    if isinstance(main_blueprint.user_script.input_parser, (JsonStringInput, RawRequestInput)):
        # This logs the raw request (probably in its repr() form) if @rawhttp is used. We should consider not logging
        # this at all in the future.
        model_input = next(iter(timed_result.input.values()))
    else:
        model_input = timed_result.input

    main_blueprint.appinsights_client.send_model_data_log(
        g.request_id, g.client_request_id, model_input, timed_result.output
    )


@main_blueprint.route("/score", methods=["GET", "POST", "OPTIONS"], provide_automatic_options=False)
def handle_score():
    g.api_name = "/score"

    try:
        timed_result = main_blueprint.user_script.invoke_run(request, timeout_ms=config.scoring_timeout)
        log_successful_request(timed_result)
    except BadInput as ex:
        return ErrorResponse(400, ex.args[0])
    except UnsupportedInput as ex:
        return ErrorResponse(415, ex.args[0])
    except UnsupportedHTTPMethod:
        # return 200 response for OPTIONS call, if CORS is enabled the required headers are implicitly
        # added by flask-cors package
        if request.method == "OPTIONS":
            return AMLResponse("", 200)
        return ErrorResponse(405, "Method not allowed")
    except UserScriptTimeout as ex:
        main_blueprint.send_exception_to_app_insights(g.request_id, g.client_request_id)
        logger.debug("Run function timeout caught")
        logger.error("Encountered Exception: {0}".format(traceback.format_exc()))
        return ErrorResponse(500, f"Scoring timeout after {ex.timeout_ms} ms", run_function_failed=True)
    except UserScriptException:
        main_blueprint.send_exception_to_app_insights(g.request_id, g.client_request_id)
        logger.debug("Run function exception caught")
        logger.error("Encountered Exception: {0}".format(traceback.format_exc()))
        return ErrorResponse(
            500,
            "An unexpected error occurred in scoring script. Check the logs for more info.",
            run_function_failed=True,
        )

    response = timed_result.output
    if isinstance(response, Response):  # this covers both AMLResponse and flask.Response
        logger.info("run() output is HTTP Response")
        if response.status_code >= 500:
            if "x-ms-run-function-failed" in response.headers:
                response.headers["x-ms-run-function-failed"] = True
            else:
                response.headers.add("x-ms-run-function-failed", True)
    else:
        response = wrap_response(response)

    # we're formatting time_taken_ms explicitly to get '0.012' and not '1.2e-2'
    response.headers.add("x-ms-run-fn-exec-ms", f"{timed_result.elapsed_ms:.3f}")
    return response


class ErrorResponse(AMLResponse):
    def __init__(self, status_code: int, message: str, run_function_failed: bool = False):
        message_json = {"message": message}
        super().__init__(message_json, status_code, json_str=True, run_function_failed=run_function_failed)
