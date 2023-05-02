# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import sys


def _patch_azureml_contrib_services():
    # override the azureml.contrib.services package with local one, meanwhile keep the other stuff under azureml.*
    # untouched note this must be done prior to importing the package in app logic
    import azureml.contrib.services.aml_request
    import azureml_inference_server_http.api.aml_request

    # works for 'import azureml.contrib.services.aml_request'
    sys.modules["azureml.contrib.services"].aml_request = sys.modules["azureml_inference_server_http.api"].aml_request
    # works for 'from azureml.contrib.services.aml_request import *'
    sys.modules["azureml.contrib.services.aml_request"] = sys.modules["azureml_inference_server_http.api.aml_request"]

    import azureml.contrib.services.aml_response
    import azureml_inference_server_http.api.aml_response

    # works for 'import azureml.contrib.services.aml_response'
    sys.modules["azureml.contrib.services"].aml_response = sys.modules[
        "azureml_inference_server_http.api"
    ].aml_response
    # works for 'from azureml.contrib.services.aml_response import *'
    sys.modules["azureml.contrib.services.aml_response"] = sys.modules[
        "azureml_inference_server_http.api.aml_response"
    ]


_patch_azureml_contrib_services()
