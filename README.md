# Project

> This repo has been populated by an initial template to help get you started. Please
> make sure to update the content to build a great experience for community-building.

As the maintainer of this project, please make a few updates:

- Improving this README.MD file to provide a great experience
- Updating SUPPORT.MD with content about this project's support experience
- Understanding the security reporting process in SECURITY.MD
- Remove this section from the README

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

# O16N Base Images

The O16N code base consists of 3 layers:

1. The server code. This is the Flask server or the Sanic server code.
2. The azureml-inference-server-http python package, which wraps the server code and dependencies into a singular package.
3. The inference images, which package other dependencies such as miniconda and nginx with the server code. Depending on the framework, the image will also include framework-specific packages, like pytorch.

User provided files, such as the entry script, model files, and custom dependencies are added outside of the image and server. These files and dependencies are mounted separately.

## Quick Start

Check out [this document](docs/Getting-Started.md) to start running our code.

## Layers

Check out the following documents for detailed information about every layer.

- Server code:
  - Information:
    - [High-level overview of HTTP server](docs/Base-Image-Network-Stack-Overview.md)
    - [Detailed breakdown of HTTP server](docs/BaseImageHTTPServer)
    - [Logging Summary](docs/Logging.md)
  - Testing:
    - [Manual test for appinsights logging](docs/Logging-E2E-Test-with-o16n-and-AzureMlCli.md)
- Python Package: azureml-inference-server-http
  - [How to build and run](src/azureml-inference-server-http/azureml_inference_server_http/CONTRIBUTING.md)
- Inference Images:
  - Running Information:
    - [Build inference base image](base_images/inference/base/README.md)
    - [Build framework images](base_images/frameworks/base/README.md)
  - Testing:
    - [Running validation tests locally](docs/Validation_Test)

## Build and Release

Checkout out [this document](/.devops/README.md) for information on the build and release pipes for the various components.


## Please contribute!

If you see some broken links or incorrect documentation, go ahead and make a PR! If you see some scenarios are undocumented, add a doc to the `/docs` folder or add a `README.md` to the relevant component folder.

Thanks!


