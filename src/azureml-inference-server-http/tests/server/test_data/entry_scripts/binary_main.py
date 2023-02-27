from azureml_inference_server_http.api.aml_response import AMLResponse


def init():
    pass


def run(input_data):
    return AMLResponse(b"xd8\xe1\xb7\xeb\xa8\xe5", 200)
