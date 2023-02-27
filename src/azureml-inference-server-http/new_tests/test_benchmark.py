from azureml.contrib.services.aml_request import rawhttp
import flask
from inference_schema.parameter_types.standard_py_parameter_type import StandardPythonParameterType
from inference_schema.schema_decorators import input_schema

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


def test_benchmark_run_decorated_with_inference_schema(benchmark, app: flask.Flask, client: TestingClient):
    @benchmark
    def test_scoring():
        @app.set_user_run
        @input_schema("num", StandardPythonParameterType(1))
        def run(num):
            pass

        input_data = {"num": 10}
        response = client.post_score(input_data)
        assert response.status_code == 200
