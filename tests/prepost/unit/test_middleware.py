import pytest

from unittest.mock import MagicMock

from multidict import CIMultiDict
from types import SimpleNamespace
from sanic.log import logger
from azureml_inference_server_http.prepost_server.middleware import (
    set_log_level,
    reset_log_level,
)


@pytest.mark.asyncio
async def test_set_log_level():
    req = MagicMock()
    req.headers = CIMultiDict({"x-ms-log-level": "debug", "x-ms-request-id": "testid"})
    req.ctx = SimpleNamespace()

    logger.setLevel(20)
    await set_log_level(req)
    assert logger.level == 10
    assert req.ctx.former_log_level == 20
    await reset_log_level(req, MagicMock())
    assert logger.level == 20


@pytest.mark.asyncio
async def test_multiple_log_level():
    req = MagicMock()
    req.headers = CIMultiDict(
        [
            ("x-ms-log-level", "debug"),
            ("x-ms-log-level", "error"),
            ("x-ms-request-id", "testid"),
        ]
    )
    req.ctx = SimpleNamespace()

    logger.setLevel(20)
    await set_log_level(req)
    assert logger.level == 10
    assert req.ctx.former_log_level == 20
    await reset_log_level(req, MagicMock())
    assert logger.level == 20
