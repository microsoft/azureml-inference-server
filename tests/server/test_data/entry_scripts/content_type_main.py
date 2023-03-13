from azureml_inference_server_http.api.aml_response import AMLResponse


def init():
    print("User init function invoked.")


def run(data):
    """Returns the original data with and sets an arbitrary content type."""

    print("User run function invoked.")
    headers = {"Content-Type": "some arbitrary content type"}
    return AMLResponse(data, 200, response_headers=headers)
