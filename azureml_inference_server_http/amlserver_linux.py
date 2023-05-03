# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import os
import sys

import gunicorn.app.wsgiapp

from .constants import (
    DEFAULT_HEALTH_PORT,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DEFAULT_WORKER_COUNT,
    DEFAULT_WORKER_PRELOAD,
    DEFAULT_WORKER_TIMEOUT_SECONDS,
    ENV_WORKER_PRELOAD,
    ENV_WORKER_TIMEOUT,
)


def run(host, port, worker_count, health_port=None):
    #
    # Manipulate the sys.argv to apply settings to gunicorn.app.wsgiapp.
    #
    # Not all gunicorn settings can be applied using environment variables and
    # command arguments have higher authoritative than other settings.
    #
    # Configuration authoritative:
    #   https://docs.gunicorn.org/en/stable/configure.html#configuration-overview
    #
    sys.argv = [
        sys.argv[0],
        "-b",
        f"{host}:{port}",
        "-w",
        str(worker_count),
        "--timeout",
        os.environ.get(ENV_WORKER_TIMEOUT, DEFAULT_WORKER_TIMEOUT_SECONDS),
        # Access log file setting required to capture log messages from
        # gunicorn and user script
        "--access-logfile",
        "-",
        # Not sending error logs to /dev/null results in them being output
        # twice. Once by our log handler, once to the gunicorn log handler
        "--error-logfile",
        "/dev/null",
    ]

    if health_port:
        sys.argv.insert(1, "-b")
        sys.argv.insert(2, f"{host}:{health_port}")

    if os.environ.get(ENV_WORKER_PRELOAD, DEFAULT_WORKER_PRELOAD).lower() == "true":
        sys.argv.append("--preload")

    sys.argv.append("azureml_inference_server_http.server.entry:app")

    gunicorn.app.wsgiapp.WSGIApplication("%(prog)s [OPTIONS] [APP_MODULE]").run()


if __name__ == "__main__":
    run(DEFAULT_HOST, DEFAULT_PORT, DEFAULT_WORKER_COUNT, DEFAULT_HEALTH_PORT)
