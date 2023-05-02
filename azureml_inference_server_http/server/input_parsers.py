# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import inspect
import json
from typing import Any, Dict, List

import flask

from .exceptions import AzmlAssertionError, AzmlinfsrvError


class InputError(AzmlinfsrvError):
    pass


class BadInput(InputError):
    pass


class UnsupportedInput(InputError):
    pass


class UnsupportedHTTPMethod(InputError):
    def __init__(self, method: str):
        self.method = method
        super().__init__(f"Unsupported HTTP method: {self.method}")


def _parse_input(input_string: str) -> Any:
    try:
        return json.loads(input_string)
    except ValueError:
        return input_string


class InputParserBase:
    __slots__ = []

    def __call__(self, request: flask.Request) -> Dict[str, Any]:
        if request.method == "GET":
            return self._parse_get_input(request)
        elif request.method == "POST":
            return self._parse_post_input(request)
        else:
            raise UnsupportedHTTPMethod(request.method)

    def _parse_get_input(self, request: flask.Request) -> Dict[str, Any]:  # pragma: no cover
        raise AzmlAssertionError(
            f"{self.__class__} does not provide an implementation for {self._parse_get_input.__name__}."
        )

    def _parse_post_input(self, request: flask.Request) -> Dict[str, Any]:  # pragma: no cover
        raise AzmlAssertionError(
            f"{self.__class__} does not provide an implementation for {self._parse_post_input.__name__}."
        )

    def _parse_get_parameters(self, request: flask.Request) -> Dict[str, Any]:
        """Parse url parameters as if they are inputs from the request body. This function will attempt to parse all
        input values as JSON values. If a parameter shows up multiple times in the parameters, it will be parsed as a
        list.

        Examples
        --------
        - /score?a=1&b=[1,2]&c=a&d=null is parsed as
            {
                "a": 1, "b": [1, 2], "c": "a", "d": null
            }
        - /score?foo=bar1&foo=bar2&x=y is parsed as
            {
                "x": "y", "foo": [
                    "bar1", "bar2"
                ]
            }
        """
        parsed_input = {}

        # Request arg keys are case-sensitive
        for k in request.args.keys():
            values = request.args.getlist(k)
            if len(values) == 1:
                parsed_input[k] = _parse_input(values[0])
            else:
                parsed_input[k] = [_parse_input(v) for v in values]

        return parsed_input


class RawRequestInput(InputParserBase):
    """Pass the flask request object as-is to the user's run() function. This is used when @rawhttp is specified."""

    __slots__ = ["parameter_name"]

    def __init__(self, parameter_name: str):
        self.parameter_name = parameter_name

    def __call__(self, request: flask.Request) -> Dict[str, Any]:
        return {self.parameter_name: request}


class JsonStringInput(InputParserBase):
    """Decode the input as a string before passing to the user's run() function. This is used when the user's run()
    function is undecorated.
    """

    __slots__ = ["parameter_name"]

    def __init__(self, parameter_name: str):
        self.parameter_name = parameter_name

    def _parse_get_input(self, request: flask.Request) -> str:
        return {self.parameter_name: json.dumps(self._parse_get_parameters(request))}

    def _parse_post_input(self, request: flask.Request) -> str:
        try:
            return {self.parameter_name: str(request.data, "utf-8")}
        except UnicodeDecodeError as ex:
            raise BadInput(f"Input cannot be decoded as UTF-8: {ex}") from None


class ObjectInput(InputParserBase):
    """Parse the body of the request as a JSON and pass the value in the value found in ``parameter_name`` to user's
    run() function. An error is raised if ``parameter_name`` is not found in the body JSON. This is used when the
    user's run function is decorated with @input_schema.
    """

    __slots__ = ["parameters"]

    def __init__(self, parameters: List[inspect.Parameter]):
        self.parameters = parameters

    def _parse_get_input(self, request: flask.Request) -> Any:
        parsed_body = self._parse_get_parameters(request)
        return self._extract_parameters(parsed_body)

    def _parse_post_input(self, request: flask.Request) -> Any:
        if not request.is_json:
            raise UnsupportedInput("Expects Content-Type to be application/json")

        body = request.get_data()
        try:
            json_body = json.loads(body)
        except json.JSONDecodeError as ex:
            if body:
                raise BadInput(f"POST body could not be decoded as JSON: {ex}") from None
            else:
                raise BadInput("POST body is empty. Expecting a JSON dictionary.") from None

        if not isinstance(json_body, dict):
            raise BadInput("POST body should be a JSON dictionary.")

        return self._extract_parameters(json_body)

    def _extract_parameters(self, body: Dict) -> Dict[str, Any]:
        parameters: Dict[str, Any] = {}
        for parameter in self.parameters:
            input_value = body.get(parameter.name, parameter.default)
            if input_value is inspect.Parameter.empty:
                raise BadInput(f"A value is not provided for the {parameter.name!r} parameter.")

            parameters[parameter.name] = input_value

        return parameters
