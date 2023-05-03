# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import json
import logging
import logging.config
import os
import time


class RootAccessFilter(logging.Filter):
    def filter(self, record: logging.LogRecord):
        return "GET / HTTP/1.1" not in record.getMessage()


class AMLLogFormatter(logging.Formatter):
    def __init__(
        self,
        fmt: str = "%(asctime)s %(levelname).1s [%(process)d] %(name)s - %(message)s",
        datefmt: str = None,
        style: str = "%",
    ):
        super().__init__(fmt=fmt, datefmt=datefmt, style=style)
        self.converter = time.gmtime


def load_logging_config(root_dir: str, silent: bool = False) -> bool:
    # Handle `None`, empty strings, and non-existent directories
    if root_dir and os.path.isdir(root_dir):
        # Check for a file named 'logging.json'
        config_path = os.path.join(root_dir, "logging.json")
        if os.path.isfile(config_path):
            with open(config_path) as f:
                logging_config = json.load(f)

            logging.config.dictConfig(logging_config)
            if not silent:
                logging.getLogger("azmlinfsrv").info(f"Loaded logging config from {config_path}")
            return True
    return False
