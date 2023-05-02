# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from psutil import process_iter
from waitress import serve

from .constants import DEFAULT_HOST, DEFAULT_PORT, DEFAULT_WORKER_COUNT
from .server.entry import app


def validate_port_usage(port):
    for proc in process_iter():
        for conns in proc.connections(kind="inet"):
            if conns.laddr.port == port:
                raise OSError(f"Specified port '{port}' is already in use.")


def run(host, port, worker_count):
    validate_port_usage(port)
    serve(app, host=host, port=port, threads=worker_count)


if __name__ == "__main__":
    run(DEFAULT_HOST, DEFAULT_PORT, DEFAULT_WORKER_COUNT)
