import os

from inference_schema.parameter_types.standard_py_parameter_type import StandardPythonParameterType
from inference_schema.schema_decorators import input_schema, output_schema


def init():
    os.environ["simple_schema_init_called"] = "1"


@input_schema("num", StandardPythonParameterType(1))
@output_schema(StandardPythonParameterType(11))
def run(num):
    return num + 10
