# This file includes tests that use the runtime_error_main entry script and appinsights
# environment variables set

from test_cases import utils
import os
import sys
from shutil import copyfile
from unittest.mock import Mock

from azureml_inference_server_http.constants import SERVER_ROOT


"""
Verifies that a GET request to the /score path with appinsights
environment variables send proper error logs
"""


def test_appinsights_exception_log(entry_script):
    dest_fpath = os.path.join(SERVER_ROOT, "main.py")
    os.makedirs(os.path.dirname(dest_fpath), exist_ok=True)
    copyfile(entry_script, dest_fpath)

    # Modify the path so we can search from the server root
    sys.path.insert(1, SERVER_ROOT)

    from azureml_inference_server_http.server import appinsights_client, entry

    app = entry.app

    data_capture_obj = {}

    def print_log_helper(exception_info, extra):
        nonlocal data_capture_obj
        data_capture_obj = extra

    logs_channel = Mock()

    logs_channel.exception.side_effect = print_log_helper

    appinsights_client.logger = logs_channel

    client = app.test_client()

    # Set up the request
    response = client.get("/score")

    # Check that it is a 500 response
    expected_code = 500
    expected_data = b'{"message": "An unexpected error occurred in scoring script. Check the logs for more info."}'

    # Verify correct error message
    utils.assert_error_message(response, expected_code, expected_data, check_default_headers=False)

    expected_headers = {
        "Content-Type": "application/json",
        "Content-Length": str(len(expected_data)),
        "x-ms-run-function-failed": "True",
        "x-request-id": lambda x: utils.verify_valid_uuid(x),
        "x-ms-request-id": lambda x: utils.verify_valid_uuid(x),
    }

    expected_num_headers = len(expected_headers)

    utils.verify_headers(response, expected_headers, expected_num_headers)

    # Check the appinsights data is correct
    expected_log_data = {"Container Id": "Unknown"}

    print("Actual Data Log:\n", data_capture_obj)
    custom_dimensions = data_capture_obj["custom_dimensions"]
    # Expect 3 items
    assert len(custom_dimensions) == 3

    for item in expected_log_data:
        assert expected_log_data[item] == custom_dimensions[item]

    utils.verify_valid_uuid(custom_dimensions["Request Id"])

    os.remove(dest_fpath)
