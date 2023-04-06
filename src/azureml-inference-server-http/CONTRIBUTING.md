# Overview

This python package contains the Azure Machine Learning inference server which is leveraged by the inferencing network stack of the base images.

## <a name="virtualenv">Setting your environment</a>

- Clone the [o16n-base-images](https://github.com/microsoft/azureml-inference-server) repository.
- Install [Python 3.8](https://www.python.org/downloads/).
- Install the virtualenv python package with `pip install virtualenv`.
- Create a new virtual environment with `virtualenv <env name>`, for example `virtualenv amlinf`.
- Activate the new environment.
  - In Windows, with `<env name>/scripts/activate`
  - In Linux, with `. <env name>/bin/activate`
- Navigate to the [azureml-inference-server-http](https://github.com/microsoft/azureml-inference-server/tree/main/src/azureml-inference-server-http) directory.
- Open a terminal/cmd window and install the package with `pip install -e .[dev]`
- Verify the command `azmlinfsrv` works.
- Activate pre-commit hooks with `pre-commit install`

## VSCode Integration

If you are developing with VSCode, you can consider adding the following into `.vscode/settings.json`.

### Pytest Integration

```json
{
  "python.testing.unittestEnabled": false,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
      "src/azureml-inference-server-http/new_tests"
  ]
}
```

This allows VSCode to discover our pytest unittests and list them in the testing tab on the right. You will be able to
run and debug tests directly from VSCode.

### Flake8 Integration

```json
{
  "python.linting.flake8Enabled": true,
  "python.linting.enabled": true,
  "python.linting.flake8Args": ["--config=src/azureml-inference-server-http/setup.cfg"],
}
```

This allows VSCode to show you linting problems from our Flake8 configuration in the text editor. The caveat is that
these rules are also applied to the Python files outside of `/src/azureml-inference-server-http`.

### Black Integration

```json
{
  "[python]": {
      "editor.formatOnSave": true
  },
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--config=src/azureml-inference-server-http/pyproject.toml"]
}
```

This tells VScode to run `black` for Python files on save. This does, however, apply to Python files outside of
`/src/azureml-inference-server-http`.

## How to Test

Before running the tests, make sure your environment is set up.

We have four sets of tests for the inferencing server. 

- Tests in `tests/azmlinfsrv` verify the behavior of the server launcher, which refers to the code in `azureml_inference_server_http/`. 
  - To run, run `pytest` in the
    [tests/azmlinfsrv](https://github.com/microsoft/azureml-inference-server/tree/main/src/azureml-inference-server-http/tests/azmlinfsrv)
    directory.
- Tests in `tests/prepost` verify the behavior of the prepost server, which refers to the code in `azureml_inference_server_http/prepost/`.
  - To run, run `pytest` in the
    [tests/prepost](https://github.com/microsoft/azureml-inference-server/tree/main/src/azureml-inference-server-http/tests/prepost)
    directory.
- Tests in `tests/server` verify the behavior of the main inferencing server, which refers to the code in `azureml_inference_server_http/server/`.
  - To run, run `python test_suite.py` in the
    [tests/server](https://msdata.visualstudio.com/Vienna/_git/o16n-base-images?path=/src/azureml-inference-server-http/tests/server) directory.
  - For more information about these tests refer to [this
    README](https://msdata.visualstudio.com/Vienna/_git/o16n-base-images?path=/src/azureml-inference-server-http/tests/server/README.md).
- Tests in `new_tests` aim to consolidate the three sets of tests. It will eventually replace the original tests.
  - To run, run `pytest` in this directory.
  - You can run a specific test with `pytest -k <test name>`, for example `pytest -k test_swagger_supported_versions`.

## <a name="build">How To Build</a>

To build the package, follow these steps:

- Navigate to the [azureml-inference-server-http](https://github.com/microsoft/azureml-inference-server/tree/main/src/azureml-inference-server-http) directory.
- Open a terminal/cmd window and run one of these commands to build the package:
  - On Linux, `python3 setup.py bdist_wheel`

This will create a dist/ directory which will contain the package's .whl.
