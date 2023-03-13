import logging
import aiotask_context as context

from sanic import Sanic
from sanic.exceptions import NotFound
from sanic_cors import CORS

from .aml_blueprint import aml_bp
from .middleware import (
    add_request_id_if_not_exists,
    add_x_ms_headers,
    add_response_run_function_failed,
    set_log_level,
    reset_log_level,
)
from .error_handlers import catch_404s, catch_user_code_errors, catch_triton_inference_errors
from .user.exceptions import UserCodeException, TritonInferenceException
from .log_settings import get_log_settings
from .config_manager import ConfigManager


def create_app(name="prepost-server"):
    # load_env = False prevents automatic environment variable loading into the Sanic config
    aml_app = Sanic(name, load_env=False, log_config=get_log_settings())
    aml_app.blueprint(aml_bp)
    ConfigManager.load_all_configs(aml_app)

    cors = CORS(aml_app, resources={r"/score": {"methods": ["POST", "OPTIONS"]}})
    logging.getLogger("sanic_cors").level = logging.getLogger().level

    #
    # WARNING:
    #     * Request middlewares are executed in the order declared.
    #     * Response middlewares are executed in reverse order.
    #
    # Details can be found here: https://sanicframework.org/en/guide/basics/middleware.html#order-of-execution-2
    #
    aml_app.register_middleware(add_request_id_if_not_exists, "request")
    aml_app.register_middleware(set_log_level, "request")
    aml_app.register_middleware(reset_log_level, "response")
    aml_app.register_middleware(add_x_ms_headers, "response")
    aml_app.register_middleware(add_response_run_function_failed, "response")

    aml_app.error_handler.add(UserCodeException, catch_user_code_errors)
    aml_app.error_handler.add(NotFound, catch_404s)
    aml_app.error_handler.add(TritonInferenceException, catch_triton_inference_errors)

    aml_app.config.FALLBACK_ERROR_FORMAT = "json"
    return aml_app
