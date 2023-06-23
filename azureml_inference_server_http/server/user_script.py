# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import inspect
import logging
import os
from types import ModuleType
from typing import Any, Callable, Dict, NamedTuple, Optional

import flask
from inference_schema.schema_util import is_schema_decorated

from .exceptions import AzmlinfsrvError
from .input_parsers import InputParserBase, JsonStringInput, ObjectInput, RawRequestInput
from .utils import timeout, Timer
from ..api import aml_request


# XXX: Since we didn't configure the root logger, getLogger(__name__) would not write to the right handlers. Here we'll
# reuse the logger that is configured in aml_blueprint.py, which is the logger named "azmlinfsrv".
# Note that this is not the actual root logger (prior to Python 3.9)
logger = logging.getLogger("azmlinfsrv.user_script")


class UserScriptError(AzmlinfsrvError):
    pass


class UserScriptException(UserScriptError):
    """User script threw an exception."""

    def __init__(self, ex: BaseException, message: Optional[str] = None):
        self.user_ex = ex

        message = message or "Caught an unhandled exception from the user script"
        super().__init__(message)


class UserScriptImportException(UserScriptException):
    def __init__(self, ex: BaseException):
        super().__init__(ex, "Failed to import user script because it raised an unhandled exception")


class UserScriptTimeout(UserScriptError):
    def __init__(self, timeout_ms: float, elapsed_ms: float):
        super().__init__(f"Script failed to finish execution within the allocated time: {timeout_ms}ms")
        self.timeout_ms = timeout_ms
        self.elapsed_ms = elapsed_ms


class TimedResult(NamedTuple):
    elapsed_ms: float
    input: Dict[str, Any]
    output: Any


class UserScript:
    input_parser: InputParserBase
    _wrapped_user_run: Callable
    _user_init: Callable
    _user_run: Callable

    def __init__(self, entry_script: Optional[str] = None):
        self.entry_script = entry_script

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.entry_script})"

    def load_script(self, app_root: str) -> None:
        if self.entry_script:
            import importlib.util as imp

            script_location = os.path.join(app_root, self.entry_script.replace("/", os.sep))
            try:
                main_module_spec = imp.spec_from_file_location("entry_module", script_location)
                user_module = imp.module_from_spec(main_module_spec)
                main_module_spec.loader.exec_module(user_module)
            except BaseException as ex:
                raise UserScriptImportException(ex) from ex
        else:
            try:
                import main as user_module
            except BaseException as ex:
                raise UserScriptImportException(ex) from ex

        # Ensure the user script has a init() and a run().
        if not hasattr(user_module, "init"):
            raise UserScriptError(f"User script at {user_module.__file__} does not have a init() function defined.")
        if not hasattr(user_module, "run"):
            raise UserScriptError(f"User script at {user_module.__file__} does not have a run() function defined.")

        # Some Azure SDK generates a proxy script (known as the driver module) to call the actual score script. We
        # can't skip over the driver module because they perform some additional tasks. For example, the Designer
        # team's driver script generates swagger.json for their users.
        maybe_user_module = getattr(user_module, "driver_module", None)
        if isinstance(maybe_user_module, ModuleType) and hasattr(maybe_user_module, "run"):
            # The user module is beind a driver module. To the best of my knowledge none of the run() in the driver
            # module has any special logic -- they simply forward the call to the run() of the actual score script. The
            # only problem is that they don't pass the arguments correctly when it is decorated with inference-schema.
            # Until the driver modules are fixed (or, better, removed), we call the run() of the actual score script
            # directly to lessen the impact.
            self._user_run = maybe_user_module.run
            logger.info(
                f"Found driver script at {user_module.__file__} and the score script at {maybe_user_module.__file__}"
            )
        else:
            # No driver module
            self._user_run = user_module.run
            logger.info(f"Found user script at {user_module.__file__}")

        # Driver modules usually add special logic into init(), so we don't want to skip over it like we do with run().
        self._user_init = user_module.init

        self._analyze_run()

    def invoke_init(self) -> None:
        logger.info("Invoking user's init function")
        try:
            self._user_init()
        except BaseException as ex:
            raise UserScriptException(ex) from ex

        logger.info("Users's init has completed successfully")

    def invoke_run(self, request: flask.Request, *, timeout_ms: int) -> TimedResult:
        run_parameters = self.input_parser(request)

        # Invoke the user's code with a timeout and a timer.
        timer = None
        try:
            with timeout(timeout_ms), Timer() as timer:
                run_output = self._wrapped_user_run(**run_parameters, request_headers=dict(request.headers))
        except TimeoutError:
            # timer may be unset if timeout() threw TimeoutError before Timer() is called. Should probably not happen
            # but not impossible.
            elapsed_ms = timer.elapsed_ms if timer else 0
            raise UserScriptTimeout(timeout_ms, elapsed_ms) from None
        except Exception as ex:
            raise UserScriptException(ex) from ex

        return TimedResult(elapsed_ms=timer.elapsed_ms, input=run_parameters, output=run_output)

    def _analyze_run(self) -> None:
        # Inspect the the run() function. Make sure it is declared in the right way.
        run_params = inspect.signature(self._user_run).parameters.values()
        if any(param.kind not in [param.KEYWORD_ONLY, param.POSITIONAL_OR_KEYWORD] for param in run_params):
            raise UserScriptError("run() cannot accept positional-only arguments, *args, or **kwargs.")

        # Determine whether we need to pass "request_headers" to run().
        if any(param.name == "request_headers" for param in run_params):
            has_request_headers = True
            run_params = [param for param in run_params if param.name != "request_headers"]
            self._wrapped_user_run = self._user_run
        else:
            has_request_headers = False
            self._wrapped_user_run = lambda request_headers, **kwargs: self._user_run(**kwargs)

        first_param = next(iter(run_params), None)
        if not first_param:
            if has_request_headers:
                raise UserScriptError('run() needs to accept an argument other than "request_headers".')
            else:
                raise UserScriptError("run() needs to accept an argument for input data.")

        # Decide the input parser we need for user's run() function.
        if aml_request._rawHttpRequested and is_schema_decorated(self._user_run):
            raise UserScriptError("run() cannot be decorated with both @rawhttp and @input_schema")
        elif aml_request._rawHttpRequested:
            self.input_parser = RawRequestInput(first_param.name)
            logger.info("run() is decorated with @rawhttp. Server will invoke it with the flask request object.")
        elif is_schema_decorated(self._user_run):
            self.input_parser = ObjectInput(run_params)
            logger.info(
                "run() is decorated with @input_schema. Server will invoke it with the following arguments: "
                f"{', '.join(param.name for param in run_params)}."
            )
        else:
            self.input_parser = JsonStringInput(first_param.name)
            logger.info("run() is not decorated. Server will invoke it with the input in JSON string.")

    def get_run_function(self) -> Callable:
        return self._user_run
