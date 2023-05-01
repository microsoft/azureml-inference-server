# Overview

This python package contains the Azure Machine Learning inference server which is leveraged by the inferencing network stack of the base images.

## <a name="virtualenv">Setting your environment</a>

- Clone the [o16n-base-images](https://msdata.visualstudio.com/Vienna/_git/o16n-base-images) repository.
- Install [Python 3.8](https://www.python.org/downloads/).
- Install the virtualenv python package with `pip install virtualenv`.
- Create a new virtual environment with `virtualenv <env name>`, for example `virtualenv amlinf`.
- Activate the new environment.
  - In Windows, with `<env name>/scripts/activate`
  - In Linux, with `. <env name>/bin/activate`
- Navigate to the [azureml-inference-server-http](https://msdata.visualstudio.com/Vienna/_git/o16n-base-images?path=/src/azureml-inference-server-http) directory.
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
      "src/azureml-inference-server-http/tests/server"
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
    [tests/azmlinfsrv](https://msdata.visualstudio.com/Vienna/_git/o16n-base-images?path=/src/azureml-inference-server-http/tests/azmlinfsrv)
    directory.
- Tests in `tests/server` verify the behavior of the main inferencing server, which refers to the code in `azureml_inference_server_http/server/`.
  - To run, run `pytest` in this directory.
  - You can run a specific test with `pytest -k <test name>`, for example `pytest -k test_swagger_supported_versions`.

## <a name="build">How To Build</a>

To build the package, follow these steps:

- Navigate to the [azureml-inference-server-http](https://msdata.visualstudio.com/Vienna/_git/o16n-base-images?path=/src/azureml-inference-server-http) directory.
- Open a terminal/cmd window and run one of these commands to build the package:
  - On Linux, `python3 setup.py bdist_wheel`

This will create a dist/ directory which will contain the package's .whl.

## Prepare a new version

1. Update [_version.py](https://msdata.visualstudio.com/Vienna/_git/o16n-base-images?path=/src/azureml-inference-server-http/azureml_inference_server_http/_version.py) with a new version number.
2. Under `/src/azureml-inference-server-http`, run `towncrier --draft` to see what the changelog would look like.
3. If it looks good, run `towncrier` to commit the changelog to [CHANGELOG.rst](https://msdata.visualstudio.com/Vienna/_git/o16n-base-images?path=/src/azureml-inference-server-http/azureml_inference_server_http/CHANGELOG.rst)
4. Create a PR with the changes.

## Build & Release

1. Create a production build using the [build pipeline](https://msdata.visualstudio.com/Vienna/_build?definitionId=15391)
2. Once the build is completed release the build using the [release pipeline](https://msdata.visualstudio.com/Vienna/_release?_a=releases&view=mine&definitionId=1053)
3. **Important: For major releases (in our case ~0.X.0), azureml-defaults must be updated to use this new package** 
    1. Here is an example PR: [example](https://msdata.visualstudio.com/Vienna/_git/AzureMlCli/pullrequest/823041)
    2. Systems images must also be updated