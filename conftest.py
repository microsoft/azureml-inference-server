# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import pytest


def pytest_addoption(parser):
    parser.addoption("--online", action="store_true", default=False, help="Run Online E2E Tests")


def pytest_collection_modifyitems(config, items):
    if not config.getoption("--online"):
        skip_online = pytest.mark.skip(reason="Online tests disabled. Use --online to run.")
        for test in items:
            if "online" in test.keywords:
                test.add_marker(skip_online)
