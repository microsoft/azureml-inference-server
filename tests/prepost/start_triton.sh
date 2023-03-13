#!/bin/bash

docker run --rm -p8000:8000 -p8001:8001 -p8002:8002 -v$(pwd)/data/models:/models nvcr.io/nvidia/tritonserver:21.08-py3 tritonserver --model-repository=/models --log-verbose=1 --strict-model-config=false
