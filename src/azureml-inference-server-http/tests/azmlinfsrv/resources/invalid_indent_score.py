import time
from azureml_inference_server_http.api.aml_response import AMLResponse
from azureml_inference_server_http.api.aml_request import rawhttp


def init():
    print("Initializing")


@rawhttp
def run(input_data):
     print("Bad Indent")
    print("Good Indent")
    return AMLResponse({}, 200, json_str=True)
