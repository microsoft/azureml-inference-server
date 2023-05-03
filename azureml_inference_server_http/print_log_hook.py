# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
`print_log_hook.py` allows for interception of all calls to `print(...)` and
forwards the message according to a simple rule set:
1. If the message was intended to be printed to the stdout filestream, the
   message is instead logged to the `amlinfsrv.print` logger.
2. If the message was intended to be printed to any other file, the message
   is forwarded as provided to the builtin Python print function.
"""
import builtins
import functools
import logging
import sys

_default_print = builtins.print
_logger = logging.getLogger("azmlinfsrv.print")


@functools.wraps(print)
def print_to_logger(*objects, sep=" ", end="\n", file=None, flush=False):
    file = file or sys.stdout
    content = sep.join(map(str, objects))

    if file is sys.stdout:
        _logger.info(content)
    else:
        _default_print(*objects, sep=sep, end=end, file=file, flush=flush)


def set_print_logger_redirect():
    builtins.print = print_to_logger
