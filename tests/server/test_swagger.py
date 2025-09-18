# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import json
import pathlib

import flask
import pytest


from .common import data_path, TestingClient


def test_swagger_bad_version(app: flask.Flask, client: TestingClient):
    """Ensure we provide a clear error message for invalid swagger versions."""

    @app.set_user_run
    def run(num):
        pass

    response = client.get_swagger("3.0a")
    assert response.status_code == 404
    assert response.json == {"message": "Swagger version [3.0a] is not valid. Supported versions: [2, 3, 3.1]."}


def test_swagger_schema_versions(app: flask.Flask, client: TestingClient):
    """Ensure we can retrieve both swagger version 2 and swagger version 3."""

    @app.set_user_run
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
    def run(num):
        pass

    swagger_3 = client.get_swagger("3").json
    swagger_30 = client.get_swagger("3.0").json
    assert swagger_3 == swagger_30



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
