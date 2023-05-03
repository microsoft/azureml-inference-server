# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import numpy as np
from azureml_inference_server_http.api.aml_response import AMLResponse
from inference_schema.schema_decorators import input_schema, output_schema
from inference_schema.parameter_types.numpy_parameter_type import NumpyParameterType


def init():
    print("Initializing")


@input_schema('data', NumpyParameterType(np.array([1, 2, 3])))
@output_schema(NumpyParameterType(np.array([10])))
def run(input_data):
    return AMLResponse({}, 200, json_str=True)
