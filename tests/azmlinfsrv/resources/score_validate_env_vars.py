# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import os
from azureml_inference_server_http.api.aml_response import AMLResponse
from azureml_inference_server_http.api.aml_request import rawhttp


def init():
    print("Initializing")


@rawhttp
def run(input_data):

    # If the environment variable is not set, it will throw and return 500!
    print("AML_APP_ROOT:{env}".format(env=os.environ["AML_APP_ROOT"]))
    print("AZUREML_ENTRY_SCRIPT:{env}".format(env=os.environ["AZUREML_ENTRY_SCRIPT"]))
    print("AZUREML_MODEL_DIR:{env}".format(env=os.getenv("AZUREML_MODEL_DIR", "__NONE__")))
    print("AML_APP_INSIGHTS_ENABLED:{env}".format(env=os.getenv("AML_APP_INSIGHTS_ENABLED", "__NONE__")))
    print("AML_APP_INSIGHTS_KEY:{env}".format(env=os.getenv("AML_APP_INSIGHTS_KEY", "__NONE__")))
    print(
        "SERVER_VERSION_LOG_RESPONSE_ENABLED:{env}".format(
            env=os.getenv("SERVER_VERSION_LOG_RESPONSE_ENABLED", "__NONE__")
        )
    )

    return AMLResponse({}, 200, json_str=True)
