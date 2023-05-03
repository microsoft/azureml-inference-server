# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import json
import pathlib

import flask
from inference_schema._constants import ALL_SUPPORTED_VERSIONS
from inference_schema.parameter_types.numpy_parameter_type import NumpyParameterType
from inference_schema.parameter_types.standard_py_parameter_type import StandardPythonParameterType
from inference_schema.schema_decorators import input_schema, output_schema
import numpy as np
import pytest


from azureml_inference_server_http.server.swagger import Swagger
from .common import data_path, TestingClient


def test_swagger_supported_versions():
    """Ensures that each swagger builder class declares a version that is compatible with inference-schema."""

    declared_versions = set()
    inference_schema_version = ALL_SUPPORTED_VERSIONS[:]
    for builder_cls in Swagger._builder_classes:
        for version in builder_cls.__version_aliases__:
            assert (
                version not in declared_versions
            ), f"More than one builder classes declared support for swagger {version}"
            declared_versions.add(version)

            try:
                inference_schema_version.remove(version)
            except ValueError:
                continue
            else:
                break
        else:
            pytest.fail(
                f"None of the versions {builder_cls} supports [{', '.join(builder_cls.__version_aliases__)}] "
                f"is supported by inference-schema [{', '.join(ALL_SUPPORTED_VERSIONS)}]"
            )

    if inference_schema_version:
        pytest.fail(
            "These swagger versions from inference-schema are not supported by any swagger builder: "
            f"[{', '.join(inference_schema_version)}]"
        )


def test_swagger_bad_version(app: flask.Flask, client: TestingClient):
    """Ensure we provide a clear error message for invalid swagger versions."""

    @app.set_user_run
    @input_schema("num", StandardPythonParameterType(1))
    def run(num):
        pass

    response = client.get_swagger("3.0a")
    assert response.status_code == 404
    assert response.json == {"message": "Swagger version [3.0a] is not valid. Supported versions: [2, 3, 3.1]."}


def test_swagger_schema_versions(app: flask.Flask, client: TestingClient):
    """Ensure we can retrieve both swagger version 2 and swagger version 3."""

    @app.set_user_run
    @input_schema("num", StandardPythonParameterType(1))
    def run(num):
        pass

    response = client.get_swagger()
    assert response.status_code == 200
    assert_swagger_version(response.json, 2)

    response = client.get_swagger("2")
    assert response.status_code == 200
    assert_swagger_version(response.json, 2)

    response = client.get_swagger("3")
    assert response.status_code == 200
    assert_swagger_version(response.json, 3)

    response = client.get_swagger("3.1")
    assert response.status_code == 200
    assert_swagger_version(response.json, 3.1)


def test_swagger_schema_versions_alias(app: flask.Flask, client: TestingClient):
    """Ensure we can retrieve swaggers with their vesion aliases."""

    @app.set_user_run
    @input_schema("num", StandardPythonParameterType(1))
    def run(num):
        pass

    swagger_3 = client.get_swagger("3").json
    swagger_30 = client.get_swagger("3.0").json
    assert swagger_3 == swagger_30


def test_swagger_schema_versions_no_2(app: flask.Flask, client: TestingClient):
    """When version 2 is not available, ensure that we provide a clear error message and that version 3 can still be
    retrieved."""

    @app.set_user_run
    @input_schema("data", StandardPythonParameterType([1, "a"]))
    def run(data):
        pass

    response = client.get_swagger("2")
    assert response.status_code == 404
    assert response.json == {
        "message": "Swagger version [2] is not supported for the scoring script. Supported swagger versions: [3, 3.1]."
    }

    response = client.get_swagger("3")
    assert response.status_code == 200
    assert_swagger_version(response.json, 3)


def test_swagger_v2_read_user_swagger(tmp_path: pathlib.Path, app: flask.Flask, client: TestingClient):
    """If the user brings their own copy of Swagger (v2), use that instead of generating one for them."""

    # When only swagger2.json is present.
    with open(tmp_path / "swagger2.json", "w", encoding="utf-8") as fp:
        json.dump("swagger2", fp)

    app.regenerate_swagger(tmp_path)
    assert client.get_swagger(2).json == "swagger2"

    # When both swagger.json and swagger2.json are present, prioritize swagger.json.
    with open(tmp_path / "swagger.json", "w", encoding="utf-8") as fp:
        json.dump("swagger", fp)

    app.regenerate_swagger(tmp_path)
    assert client.get_swagger(2).json == "swagger"


def test_swagger_v3_read_user_swagger(tmp_path: pathlib.Path, app: flask.Flask, client: TestingClient):
    """If the user brings their own copy of Swagger (v3), use that instead of generating one for them."""

    # When swagger3.json is present.
    with open(tmp_path / "swagger3.json", "w", encoding="utf-8") as fp:
        json.dump("swagger3", fp)

    app.regenerate_swagger(tmp_path)
    assert client.get_swagger(3).json == "swagger3"


def assert_swagger_version(swagger: dict, version: int):
    if version == 3.1:
        version = swagger["openapi"]
        assert version == "3.1.0"
    elif version == 3:
        version = swagger["openapi"]
        assert version == "3.0.3"
    elif version == 2:
        version = swagger["swagger"]
        assert version == "2.0"
    else:
        pytest.fail(f"Unsupported version: {version}")


@pytest.mark.parametrize("swagger_version", [2, 3, 3.1])
def test_swagger_generation(app: flask.Flask, client: TestingClient, swagger_version):
    """Verifies that a GET request to the /swagger.json path for different versions returns the expected swagger
    schema for the entry script. For this, we use an entry script with schema generation decorators."""

    input_sample = np.array([10, 9, 8, 7, 6, 5, 4, 3, 2, 1], dtype=np.int64)
    output_sample = np.array([3726.995])

    @app.set_user_run
    @input_schema("data", NumpyParameterType(input_sample))
    @output_schema(NumpyParameterType(output_sample))
    def run(data):
        print("User run function invoked.")
        return sum(data).tolist()

    with open(data_path(f"swagger/expected_swagger{swagger_version}.json")) as f:
        expected_json = json.load(f)

    response = client.get_swagger(swagger_version)
    assert response.status_code == 200
    assert response.json == expected_json


def test_swagger_generation_with_path_prefix(app: flask.Flask, client: TestingClient, config):
    """Verifies that a GET request to the /swagger.json path returns the expected swagger schema for the entry script.
    For this, we use an entry script with schema generation decorators
    and set a custom environment variable for the path prefix."""

    config.service_path_prefix = "test"
    input_sample = np.array([10, 9, 8, 7, 6, 5, 4, 3, 2, 1], dtype=np.int64)
    output_sample = np.array([3726.995])

    @app.set_user_run
    @input_schema("data", NumpyParameterType(input_sample))
    @output_schema(NumpyParameterType(output_sample))
    def run(data):
        print("User run function invoked.")
        return sum(data).tolist()

    with open(data_path("swagger/expected_swagger_prefix_case.json")) as f:
        expected_json = json.load(f)

    response = client.get_swagger()
    assert response.status_code == 200
    assert response.json == expected_json


@pytest.mark.parametrize("swagger_version", [2, 3, 3.1])
def test_swagger_generation_without_decorator(app: flask.Flask, client: TestingClient, swagger_version):
    """Verifies that a GET request to the /swagger.json path returns the expected swagger schema for the entry script.
    For this, we use a default entry script with no schema decorators"""

    @app.set_user_run
    def run(data):
        return data

    with open(data_path(f"swagger/expected_swagger{swagger_version}_without_decorator.json")) as f:
        expected_json = json.load(f)

    response = client.get_swagger(swagger_version)
    assert response.status_code == 200
    assert response.json == expected_json
