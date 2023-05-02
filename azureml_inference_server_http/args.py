# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import argparse
import logging
import sys

from . import __version__
from .constants import ENV_AZUREML_MODEL_DIR


def print_arguments(args):
    for arg in vars(args):
        logging.debug(arg + ":" + str(args.__dict__[arg]))


def validate_port(port):
    port = int(port)
    if port < 1 or port > 65535:
        raise ValueError(
            f"Specified port '{port}' is invalid. Please specify a port within range the [1, 65535] range."
        )
    return port


def validate_worker_count(worker_count):
    worker_count = int(worker_count)
    if worker_count <= 0:
        raise ValueError(
            f"Specified worker count '{worker_count}' is invalid. Please specify a worker count greater than zero."
        )
    return worker_count


def parse_arguments():
    parser = argparse.ArgumentParser(description=f"Azure ML Inferencing HTTP server v{__version__}", add_help=True)
    parser.add_argument("--entry_script", required=False, help="The relative or absolute path to the scoring script.")
    parser.add_argument(
        "--model_dir",
        required=False,
        help=(
            "The relative or absolute path to the model directory. The model directory will be accessible"
            f"through the '{ENV_AZUREML_MODEL_DIR}' environment variable."
        ),
    )
    parser.add_argument(
        "--appinsights_instrumentation_key",
        required=False,
        help="The instrumentation key to the application insights where the logs will be published.",
    )
    parser.add_argument(
        "--port", required=False, type=validate_port, help="The serving port of the server. Default is 5001."
    )
    parser.add_argument(
        "--health_port", required=False, type=validate_port, help="The health port of the server. Default is 5000."
    )
    parser.add_argument(
        "--worker_count",
        required=False,
        type=validate_worker_count,
        help="The number of worker threads which will process concurrent requests. Default is 1.",
    )
    parser.add_argument(
        "--access_control_allow_origins",
        required=False,
        help=(
            'Enable CORS for the specified origins. Separate multiple origins with ",".'
            'Example: "microsoft.com, bing.com"'
        ),
    )
    parser.add_argument(
        "--config_file",
        required=False,
        help="The relative or absolute path to the configuration file",
    )
    parser.add_argument("--rest", default=False, required=False, action="store_true", help=argparse.SUPPRESS)

    try:
        args = parser.parse_args()
    except SystemExit as err:
        if err.code == 2:
            print()
            # Don't print usage when parsing the command line.
            parser.usage = argparse.SUPPRESS
            parser.print_help()
            parser.usage = None
        sys.exit(1)

    try:
        print_arguments(args)
    except Exception:
        logging.debug(f"Failed to print arguments '{args}'")

    return args
