# Project

## Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.

## Trademarks

This project may contain trademarks or logos for projects, products, or services. Authorized use of Microsoft 
trademarks or logos is subject to and must follow 
[Microsoft's Trademark & Brand Guidelines](https://www.microsoft.com/en-us/legal/intellectualproperty/trademarks/usage/general).
Use of Microsoft trademarks or logos in modified versions of this project must not cause confusion or imply Microsoft sponsorship.
Any use of third-party trademarks or logos are subject to those third-party's policies.

----

# AzureML Inference Server

The HTTP server is the component that facilitates inferencing to deployed models. Requests made to the HTTP server run user-provided code that interfaces with the user models.
This server is used with most images in the Azure ML ecosystem, and is considered the primary component of the base image, as it contains the python assets required for inferencing.
This is the Flask server or the Sanic server code. The azureml-inference-server-http python package, wraps the server code and dependencies into a singular package.

## Quick Start

Check out [this document](src\azureml-inference-server-http\CONTRIBUTING.md) to start running our code.

## Layers

Check out the following documents for detailed information about every layer.

- Server code:
  - Information:
    - [Detailed breakdown of HTTP server](docs/AzureMLInferenceServer)
    - [Logging Summary](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-inference-server-http#understanding-logs)
- Python Package: azureml-inference-server-http
  - [How to build and run](src/azureml-inference-server-http/azureml_inference_server_http/CONTRIBUTING.md)


## Please contribute!

If you see some broken links or incorrect documentation, go ahead and make a PR! If you see some scenarios are undocumented, add a doc to the `/docs` folder or add a `README.md` to the relevant component folder.

Thanks!


