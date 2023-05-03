# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

from azureml.contrib.services.aml_response import AMLResponse
from azureml.contrib.services.aml_request import rawhttp


def init():
    print("Initializing")


@rawhttp
def run(input_data):
    return AMLResponse({}, 200, json_str=True)
