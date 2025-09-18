# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from contextlib import contextmanager
import os
from typing import Any, Dict, Optional, TypeVar

import flask
import flask.testing
import werkzeug.test
import wrapt

import azureml_inference_server_http.server
from azureml_inference_server_http.server.config import config
from azureml_inference_server_http.server.swagger import Swagger
from azureml_inference_server_http.server.user_script import TimedResult, UserScript


DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def data_path(*paths: str) -> str:
    return os.path.join(DATA_DIR, *paths)


_CallableT = TypeVar("_CallableT", bound=callable)


class TestingApp(wrapt.ObjectProxy):
    user_script: "TestingUserScript"

    @property
    def last_run(self) -> Any:
        return self.user_script.last_run

    def set_user_init(self, init_fn: _CallableT) -> _CallableT:
        return self.user_script._set_user_init(init_fn)

    def set_user_run(self, run_fn: _CallableT) -> _CallableT:
        run_fn = self.user_script._set_user_run(run_fn)
        self.regenerate_swagger()
        self.user_script.reset_run_decorators()

    @contextmanager
    def appinsights_enabled(self):
        prev_val = config.app_insights_enabled
        try:
            config.app_insights_enabled = True
            # Only re-init app insights if it wasn't already enabled
            if not prev_val:
                self.azml_blueprint._init_appinsights()

            yield self
        finally:
            config.app_insights_enabled = prev_val
            # Only re-init app insights if it wasn't already enabled
            if not prev_val:
                # Remember to close the previous appinsights client to avoid
                # lingering logger attachments
                self.azml_blueprint.appinsights_client.close()

                self.azml_blueprint._init_appinsights()

    def regenerate_swagger(self, app_root: str = "."):
        server_root = os.path.dirname(azureml_inference_server_http.server.__file__)
        self.azml_blueprint.swagger = Swagger(app_root, server_root, self.user_script)


class TestingClient(flask.testing.FlaskClient):
    def get_health(self, **kwargs) -> werkzeug.test.TestResponse:
        return self.get("/", **kwargs)

    def get_score(self, params: Dict[str, Any] = None, **kwargs) -> werkzeug.test.TestResponse:
        return self.get("/score", query_string=params or {}, **kwargs)

    def post_score(self, json: Any = None, **kwargs) -> werkzeug.test.TestResponse:
        # Only pass `json` when it is not `None` because Flask 1 forbids passing `data` and `json` to `post()` even if
        # `json` is `None`.
        if json is not None:
            kwargs["json"] = json

        return self.post("/score", **kwargs)

    def options_score(self, **kwargs) -> werkzeug.test.TestResponse:
        return self.options("/score", **kwargs)

    def score(self, method: str, input_data: Any = None, **kwargs) -> werkzeug.test.TestResponse:
        if method == "GET":
            return self.get_score(input_data, **kwargs)
        elif method == "POST":
            return self.post_score(input_data, **kwargs)
        else:
            assert input_data is None, f"input_data cannot be set for {method}"
            return self.open("/score", method=method, **kwargs)

    def get_swagger(self, version: Optional[str] = None) -> werkzeug.test.TestResponse:
        params = {"version": version} if version else {}
        return self.get("/swagger.json", query_string=params)


class TestingUserScript(UserScript):
    def __init__(self, filename: Optional[str] = None):
        script_path = data_path(f"user_scripts/{filename}") if filename else None
        super().__init__(script_path)

        self.last_run = None
        self.reset_user_module()

    def reset_run_decorators(self) -> None:
        from azureml_inference_server_http.api import aml_request

        aml_request._rawHttpRequested = False

    def reset_user_module(self) -> None:
        self._user_init = lambda: None
        self._user_run = lambda data: None
        self.reset_run_decorators()

        # Call analyze_run() to update input_parser.
        self._analyze_run()

    def _set_user_init(self, init_fn: _CallableT) -> _CallableT:
        self._user_init = init_fn
        return init_fn

    # The reset_run_decorators() funtion needs to be called manually to reset the run decorators
    def _set_user_run(self, run_fn: _CallableT) -> _CallableT:
        self._user_run = run_fn
        self._analyze_run()
        return run_fn

    def invoke_run(self, request: flask.Request, *, timeout_ms: int) -> TimedResult:
        self.last_run = super().invoke_run(request, timeout_ms=timeout_ms)
        return self.last_run
