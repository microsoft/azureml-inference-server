# AzureML Inference Server

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft 
trademarks or logos is subject to and must follow 
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.

----

## Summary

The HTTP server is the component that facilitates inferencing to deployed models. Requests made to the HTTP server run user-provided code that interfaces with the user models.
This server is used with most images in the Azure ML ecosystem, and is considered the primary component of the base image, as it contains the python assets required for inferencing.
This is the Flask server or the Sanic server code. The azureml-inference-server-http python package, wraps the server code and dependencies into a singular package.

## Quick Start

## <a name="virtualenv">Setting your environment</a>

- Clone the [azureml-inference-server](https://github.com/microsoft/azureml-inference-server) repository.
- Install [Python 3.8](https://www.python.org/downloads/).
- Install the virtualenv python package with `pip install virtualenv`.
- Create a new virtual environment with `virtualenv <env name>`, for example `virtualenv amlinf`.
- Activate the new environment.
  - In Windows, with `<env name>/scripts/activate`
  - In Linux, with `. <env name>/bin/activate`
- Navigate to the root directory.
- Open a terminal/cmd window and install the package with `pip install -e .[dev]`
- Verify the command `azmlinfsrv` works.

  [More Information](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-inference-server-http?view=azureml-api-2)

## Information

Check out the following documents for detailed information.

- Server code:
  - Information:
    - [Detailed breakdown of HTTP server](docs/AzureMLInferenceServer.md)
    - [Logging Summary](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-inference-server-http#understanding-logs)
