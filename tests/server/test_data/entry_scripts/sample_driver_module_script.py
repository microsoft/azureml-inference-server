# This file is used to test that the driver module successfully calls this entry script.
import json
import numpy as np

from inference_schema.schema_decorators import input_schema, output_schema
from inference_schema.parameter_types.numpy_parameter_type import NumpyParameterType


def init():
    print("User init function invoked.")
    pass


input_sample = np.array([10, 9, 8, 7, 6, 5, 4, 3, 2, 1])
output_sample = np.array([3726.995])
"""
Simple run function that sums the input data.
"""


@input_schema("data", NumpyParameterType(input_sample))
@output_schema(NumpyParameterType(output_sample))
def run(data):
    print("User run function invoked.")
    return sum(data).tolist()
