from typing import Dict

import aiohttp
import aiotask_context as context
from sanic import Request, response, Blueprint
from sanic.log import logger
from sanic.response import json

from .clients.client_factory import ClientFactory
from .constants import ENV_AZUREML_BACKEND_HOST, ENV_AZUREML_BACKEND_PORT, ENV_BACKEND_TRANSPORT_PROTOCOL
from .script_loader import ScriptLoader
from .log_settings import get_custom_dimensions

from .utils import capture_time_taken_async, capture_time_taken

aml_bp = Blueprint("aml_blueprint")


@aml_bp.before_server_start
async def init(app, loop):
    logger.debug("@aml_bp.before_server_start")
    logger.debug("Setting aml_bp.ctx.aiohttp_session")
    aml_bp.ctx.script_loader = ScriptLoader(app.config)
    aml_bp.ctx.aiohttp_session = aiohttp.ClientSession(loop=loop)
    loop.set_task_factory(context.task_factory)

    aml_bp.ctx.client = ClientFactory.create_client(
        addr=app.config[ENV_AZUREML_BACKEND_HOST],
        port=app.config[ENV_AZUREML_BACKEND_PORT],
        protocol=app.config[ENV_BACKEND_TRANSPORT_PROTOCOL],
    )
    logger.debug(f"Created client type {type(aml_bp.ctx.client)}", extra=get_custom_dimensions())


@aml_bp.after_server_stop
async def finish(app, loop):
    logger.debug("@aml_bp.after_server_stop", extra=get_custom_dimensions())
    logger.debug("Closing aml_bp.ctx.aiohttp_session", extra=get_custom_dimensions())
    try:
        loop.run_until_complete(aml_bp.ctx.aiohttp_session.close())
        loop.close()
    except RuntimeError:
        pass  # NOTE: only happens in tests


@aml_bp.route("/", methods=["GET"])
async def health(request):
    # TODO: used for testing, remove
    logger.debug("GET from route /", extra=get_custom_dimensions())
    return json({"Status": "OK. Ready to serve requests."})


@aml_bp.route("/score", methods=["POST", "OPTIONS"])
async def score(request):
    logger.info(f"Received {request.method} request at route {request.url}.", extra=get_custom_dimensions())
    raw_data = request.body
    ctx = create_context(request)

    logger.debug("Invoking user's preprocessing", extra=get_custom_dimensions())
    data, pre_time_ms = capture_time_taken(aml_bp.ctx.script_loader.preprocess)(raw_data, ctx)

    kfservingv2_result = {}
    inf_time_ms = 0

    if not ("skip-inference" in ctx and ctx["skip-inference"] == True):
        kfservingv2_result, inf_time_ms = await capture_time_taken_async(aml_bp.ctx.client.infer_async)(
            data, aml_bp.ctx.aiohttp_session
        )

    logger.debug("Invoking user's postprocessing", extra=get_custom_dimensions())
    (response_data, content_type), post_time_ms = capture_time_taken(aml_bp.ctx.script_loader.postprocess)(
        kfservingv2_result, ctx
    )

    response_headers = add_response_headers(pre_time_ms, inf_time_ms, post_time_ms)
    return handle_response_type(response_data, content_type, response_headers)


def add_response_headers(pre_time, inf_time, post_time):
    headers = {}
    # we're formatting time_taken_ms explicitly to get '0.012' and not '1.2e-2'
    headers["x-ms-preproc-exec-ms"] = f"{pre_time:.3f}"
    headers["x-ms-infr-exec-ms"] = f"{inf_time:.3f}"
    headers["x-ms-postproc-exec-ms"] = f"{post_time:.3f}"
    return headers


def handle_response_type(response_data, content_type, response_headers) -> response:
    logger.debug(f"Returning response with content-type: {content_type}", extra=get_custom_dimensions())
    if content_type == "application/json":
        return response.json(response_data, headers=response_headers)
    elif content_type == "application/octet-stream":
        return response.raw(response_data, headers=response_headers)
    elif content_type == "text/plain":
        return response.text(response_data, headers=response_headers)
    else:
        logger.warn(f"Unfamiliar content-type: {content_type}", extra=get_custom_dimensions())
        return response.HTTPResponse(response_data, status=200, content_type=content_type, headers=response_headers)


def create_context(request: Request) -> Dict:
    ctx = {
        "method": request.method,
        "url": request.url,
        "query-string": request.query_string,
        "path": request.path,
        "headers": {
            "content-type": request.headers.get("content-type"),
            "content-length": request.headers.get("content-length"),
            "accept": request.headers.get("accept", ""),
            "x-ms-request-id": request.headers.get("x-ms-request-id", ""),
            "x-ms-custom": request.headers.get("x-ms-custom", ""),  # TODO: make any custom header
        },
        "skip-inference": False,
    }
    logger.debug(f"Request Context={ctx}", extra=get_custom_dimensions())
    return ctx
