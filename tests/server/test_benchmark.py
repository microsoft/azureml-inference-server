# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from azureml.contrib.services.aml_request import rawhttp
import flask


from .common import TestingClient


def test_benchmark_run_not_decorated(benchmark, app: flask.Flask, client: TestingClient):
    @benchmark
    def test_scoring():
        @app.set_user_run
        def run(data):
            return {"a": 1}

        response = client.post_score()
        assert response.status_code == 200


def test_benchmark_run_decorated_with_rawhttp(benchmark, app: flask.Flask, client: TestingClient):
    @benchmark
    def test_scoring():
        @app.set_user_run
        @rawhttp
        def run(request):
            pass

        response = client.post_score()
        assert response.status_code == 200



# Removed test_benchmark_run_decorated_with_inference_schema since InferenceSchema is no longer supported
