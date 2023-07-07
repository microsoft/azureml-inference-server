# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import itertools
import logging
import logging.config
import os
import sys
import traceback

from flask import Blueprint

from .appinsights_client import AppInsightsClient
from .config import config
from .swagger import Swagger
from .user_script import UserScript, UserScriptError
from .utils import walk_path
from ..constants import SERVER_ROOT
from ..print_log_hook import set_print_logger_redirect

# check if flask_cors is available
try:
    import flask_cors
except ModuleNotFoundError:
    flask_cors = None

FILE_TREE_LOG_LINE_LIMIT = 200

# Amount of time we wait before exiting the application when errors occur for exception log sending
WAIT_EXCEPTION_UPLOAD_IN_SECONDS = 30

sys.path.append(config.app_root)

if config.source_dir:
    source_dir = os.path.join(config.app_root, config.source_dir)
    sys.path.append(source_dir)

logger = logging.getLogger("azmlinfsrv")


class AMLInferenceBlueprint(Blueprint):
    appinsights_client: AppInsightsClient

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.user_script = UserScript(config.entry_script)

    def _init_logger(self):
        try:
            print("Initializing logger")
            set_print_logger_redirect()
        except Exception:
            print("logger initialization failed: {0}".format(traceback.format_exc()))
            sys.exit(3)

    # AML App Insights Wrapper
    def _init_appinsights(self):
        try:
            logger.info("Starting up app insights client")
            self.appinsights_client = AppInsightsClient()
        except Exception:
            logger.error(
                "Encountered exception while initializing App Insights/Logger {0}".format(traceback.format_exc())
            )
            sys.exit(3)

    def send_exception_to_app_insights(self, request_id="NoRequestId", client_request_id=""):
        if self.appinsights_client is not None:
            self.appinsights_client.send_exception_log(sys.exc_info(), request_id, client_request_id)

    def setup(self):
        # initiliaze logger and app insights
        self._init_logger()
        self._init_appinsights()

        # Enable CORS if the environemnt variable is set
        if config.cors_origins:
            if flask_cors:
                originsList = [origin.strip() for origin in config.cors_origins.split(",")]
                flask_cors.CORS(self, methods=["GET", "POST"], origins=originsList)
                logger.info(f"Enabling CORS for the following origins: {', '.join(originsList)}")
            # if flask_cors package is not available and environ variable is set then log appropriate message
            else:
                logger.info(
                    "CORS cannot be enabled because the flask-cors package is not installed. The issue can be"
                    " resolved by adding flask-cors to your pip dependencies."
                )

        try:
            self.user_script.load_script(config.app_root)
        except UserScriptError:
            # If main is not found, this indicates score script is not in expected location
            if "No module named 'main'" in traceback.format_exc():
                logger.error("No score script found. Expected score script main.py.")
                logger.error(f"Expected script to be found in PYTHONPATH: {sys.path}")
                if os.path.isdir(config.app_root):
                    logger.error(f"Current contents of AML_APP_ROOT: {os.listdir(config.app_root)}")
                else:
                    logger.error(f"The directory {config.app_root} not an accessible directory in the container.")
            elif "FileNotFoundError" in traceback.format_exc():
                logger.error("No such file or directory.")
                logger.error(traceback.format_exc())
            else:
                logger.error(traceback.format_exc())
            sys.exit(3)

        try:
            self.user_script.invoke_init()
        except UserScriptError:
            logger.error("User's init function failed")
            logger.error("Encountered Exception {0}".format(traceback.format_exc()))
            self.appinsights_client.send_exception_log(sys.exc_info())

            aml_model_dir = config.azureml_model_dir
            if aml_model_dir and os.path.exists(aml_model_dir):
                logger.info("Model Directory Contents:")

                tree = walk_path(aml_model_dir)
                for line in itertools.islice(tree, FILE_TREE_LOG_LINE_LIMIT):
                    logger.info(line)

                if next(tree, None):
                    logger.info(f"Output Truncated. First {FILE_TREE_LOG_LINE_LIMIT} lines shown.")

            self.appinsights_client.wait_for_upload()

            sys.exit(3)

        # init debug middlewares deprecated
        if "AML_DBG_MODEL_INFO" in os.environ or "AML_DBG_RESOURCE_INFO" in os.environ:
            logger.warning(
                "The debuggability features have been removed. If you have a use case for them please reach out to us."
            )

        # generate the swagger
        self.swagger = Swagger(config.app_root, SERVER_ROOT, self.user_script)

        logger.info(f"Scoring timeout is set to {config.scoring_timeout}")
        logger.info(f"Worker with pid {os.getpid()} ready for serving traffic")

    def register(self, *args, **kwargs):
        self.setup()
        super(AMLInferenceBlueprint, self).register(*args, **kwargs)
