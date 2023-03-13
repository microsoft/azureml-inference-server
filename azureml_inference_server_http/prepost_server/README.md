# Overview

This folder contains the code for the prepost-server.

## Setting up environment

## Run Prepost-Server

`python run.py`
## Running tests

`pytest tests/`

### Test with real Triton instance

`pytest tests/ --use-triton`

## Publishing to azureml-inference-http-server

## Build and Run Pre-/Post-Processing Server and Triton within the Same Image
### Building Image

To build the image with Triton and Prepost server, run the following command on the Dockerfile at the root of this directory

```shell
cd src/azureml-inference-server-http/azureml_inference_server_http/prepost_server
./setup_context.sh
docker build -t triton_prepost_img -f Dockerfile .
```

### Running Image

To run the image, the environment variables `AZUREML_MODEL_DIR` for the model directory and `AZUREML_ENTRY_SCRIPT` for the user code must be set.
To also install other python packages. a requirements.txt file must be created in the same directory as the user code script.
This variable can be set with `AZUREML_EXTRA_REQUIREMENTS_TXT`.

Navigate to the folder containing the model directory, user code and requirements.txt and set appropriate values. Example run below:

```shell
cd src/azureml-inference-server-http/azureml_inference_server_http/prepost_server/tests/data
docker run -it -v $(pwd):/var/azureml-app -e AZUREML_MODEL_DIR="models" -e AZUREML_EXTRA_REQUIREMENTS_TXT="requirements.txt" -e AZUREML_ENTRY_SCRIPT="samples/fashion.py" triton_prepost_img
```

## Build and Run Pre-/Post-Processing Server and Triton with Separate Images

### Build Image

Follow below steps to setup environment and build image:

```BASH
cd src/azureml-inference-server-http/azureml_inference_server_http/prepost_server
./setup_context.sh
docker build -f Dockerfile.srv -t prepost-only:v2
```

### Run Pre-/Post-Processing Image and Triton Image

To make both images can talk to each other, we need to create a separate docker network and put both containers in the one. The pre-/post-processing container will use the triton container's name to access Triton server.

```BASH
docker network create prepost_test

# Start Triton container with "--net prepost_test" and "--name triton"
docker run --rm -p8000:8000 -p8001:8001 -p8002:8002 -v$(pwd)/models:/model --net prepost_test --name triton tritonserver:latest tritonserver --model-repository=/model --log-verbose=1 --strict-model-config=false

# Start pre-/post-processing container
docker run -it -p 5001:5001 --net prepost_test -e AZUREML_EXTRA_REQUIREMENTS_TXT="requirements.txt" -e WORKER_COUNT=2 -e AZUREML_BACKEND_HOST="triton" -e AZUREML_BACKEND_PORT=8000 -v $(pwd):/var/azureml-app prepost-only:v2
```
