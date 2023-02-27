# This file includes tests that use the default_main entry script and appinsights
# environment variables set

from test_cases import utils
import os
import sys
from shutil import copyfile
from unittest.mock import Mock

from azureml_inference_server_http.constants import SERVER_ROOT
from opencensus.trace.blank_span import BlankSpan

"""
Verifies that a GET request to the /score path with appinsights
environment variables send proper logs
"""


def test_appinsights_request_log(entry_script):
    dest_fpath = os.path.join(SERVER_ROOT, "main.py")
    os.makedirs(os.path.dirname(dest_fpath), exist_ok=True)
    copyfile(entry_script, dest_fpath)

    # Modify the path so we can search from the server root
    sys.path.insert(1, SERVER_ROOT)

    from azureml_inference_server_http.server import appinsights_client, entry

    app = entry.app

    logger = Mock()
    logger.addHandler.side_effect = Mock()
    appinsights_client.logger = logger

    mock_tracer = Mock()
    mock_span = BlankSpan()
    mock_tracer.span = Mock(return_value=mock_span)

    app.azml_blueprint.appinsights_client.tracer = mock_tracer

    client = app.test_client()

    # Set up the request
    response = client.get("/score?a=12")

    # Check 200 response and proper headers
    expected_code = 200
    expected_data = b'{"a": 12}'

    utils.assert_response(
        response,
        expected_code,
        expected_data,
        expected_headers={},
        check_default_headers=True,
        check_passed_headers=False,
    )

    expected_data = {
        "resultCode": "200",
        "success": True,
        "name": "/score",
        "url": "http://localhost/score?a=12",
        "Container Id": "Unknown",
        "Client Request Id": "",
        "Response Value": '"{\\"a\\": 12}"',
        "Workspace Name": "",
        "Service Name": "ML service",
    }

    print("Actual Log:\n", mock_span.attributes)
    # Expect 13 items
    assert len(mock_span.attributes) == 13

    for item in expected_data:
        assert expected_data[item] == mock_span.attributes[item]

    utils.verify_valid_uuid(mock_span.span_id)

    # Just check that duration header is logged, as it will be some string time value
    assert "duration" in mock_span.attributes

    os.remove(dest_fpath)


"""
Verifies that a GET request to the /score path with appinsights
environment variables for MDC logging.
"""


def test_appinsights_model_log(entry_script):
    dest_fpath = os.path.join(SERVER_ROOT, "main.py")
    os.makedirs(os.path.dirname(dest_fpath), exist_ok=True)
    copyfile(entry_script, dest_fpath)

    # Modify the path so we can search from the server root
    sys.path.insert(1, SERVER_ROOT)

    from azureml_inference_server_http.server import appinsights_client, entry

    app = entry.app

    data_capture_obj = {}

    def print_log_helper(name, extra):
        nonlocal data_capture_obj
        data_capture_obj = extra

    logs_channel = Mock()

    logs_channel.info.side_effect = print_log_helper

    appinsights_client.logger = logs_channel

    client = app.test_client()

    # Set up the request
    param1 = "hello"
    param2 = "world"
    response = client.get("/score?param1=" + param1 + "&param2=" + param2, content_type="html/text")

    # Check 200 response and proper headers
    expected_code = 200
    expected_data = '{"param1": "hello", "param2": "world"}'

    utils.assert_response(
        response,
        expected_code,
        expected_data,
        expected_headers={},
        check_default_headers=True,
        check_passed_headers=True,
        check_json_data=True,
    )

    expected_log_data = {
        "Container Id": "Unknown",
        "Workspace Name": "",
        "Service Name": "ML service",
        "Models": ["test-model:1"],
        "Input": '"{\\"param1\\": \\"hello\\", \\"param2\\": \\"world\\"}"',
        "Prediction": '{"param1": "hello", "param2": "world"}',
    }

    print("Actual Data Log:\n", data_capture_obj)

    custom_dimensions = data_capture_obj["custom_dimensions"]
    # Expect 8 items
    assert len(custom_dimensions) == 8

    for item in expected_log_data:
        assert expected_log_data[item] == custom_dimensions[item]

    utils.verify_valid_uuid(custom_dimensions["Request Id"])

    os.remove(dest_fpath)


"""
Verifies that a GET request to the /score path with request id and client request id send proper logs
"""


def test_appinsights_model_log_with_clientrequestid(entry_script):
    dest_fpath = os.path.join(SERVER_ROOT, "main.py")
    os.makedirs(os.path.dirname(dest_fpath), exist_ok=True)
    copyfile(entry_script, dest_fpath)

    # Modify the path so we can search from the server root
    sys.path.insert(1, SERVER_ROOT)

    from azureml_inference_server_http.server import appinsights_client, entry

    app = entry.app

    data_capture_obj = {}

    def print_log_helper(name, extra):
        nonlocal data_capture_obj
        data_capture_obj = extra

    logs_channel = Mock()

    logs_channel.info.side_effect = print_log_helper

    appinsights_client.logger = logs_channel

    client = app.test_client()

    # Set up the request
    param1 = "hello"
    param2 = "world"
    client.get(
        "/score?param1=" + param1 + "&param2=" + param2,
        content_type="html/text",
        headers={"x-request-id": "623c3df9-3ef0-4905-a3cc-6ef015f17c3f", "x-ms-client-request-id": "test-client-id"},
    )

    expected_log_data = {
        "Container Id": "Unknown",
        "Workspace Name": "",
        "Service Name": "ML service",
        "Models": ["test-model:1"],
        "Input": '"{\\"param1\\": \\"hello\\", \\"param2\\": \\"world\\"}"',
        "Prediction": '{"param1": "hello", "param2": "world"}',
        "Request Id": "623c3df9-3ef0-4905-a3cc-6ef015f17c3f",
        "Client Request Id": "test-client-id",
    }

    custom_dimensions = data_capture_obj["custom_dimensions"]
    # Expect 8 items
    assert len(custom_dimensions) == 8

    for item in expected_log_data:
        assert expected_log_data[item] == custom_dimensions[item]

    utils.verify_valid_uuid(custom_dimensions["Request Id"])

    os.remove(dest_fpath)


"""
Verifies that a GET request to the /score path without client request id and request id send proper logs
"""


def test_appinsights_model_log_without_clientrequestid(entry_script):
    dest_fpath = os.path.join(SERVER_ROOT, "main.py")
    os.makedirs(os.path.dirname(dest_fpath), exist_ok=True)
    copyfile(entry_script, dest_fpath)

    # Modify the path so we can search from the server root
    sys.path.insert(1, SERVER_ROOT)

    from azureml_inference_server_http.server import appinsights_client, entry

    app = entry.app

    data_capture_obj = {}

    def print_log_helper(name, extra):
        nonlocal data_capture_obj
        data_capture_obj = extra

    logs_channel = Mock()

    logs_channel.info.side_effect = print_log_helper

    appinsights_client.logger = logs_channel

    client = app.test_client()

    # Set up the request
    param1 = "hello"
    param2 = "world"
    client.get("/score?param1=" + param1 + "&param2=" + param2, content_type="html/text")

    expected_log_data = {
        "Container Id": "Unknown",
        "Workspace Name": "",
        "Service Name": "ML service",
        "Models": ["test-model:1"],
        "Input": '"{\\"param1\\": \\"hello\\", \\"param2\\": \\"world\\"}"',
        "Prediction": '{"param1": "hello", "param2": "world"}',
        "Client Request Id": "",
    }

    custom_dimensions = data_capture_obj["custom_dimensions"]
    # Expect 8 items
    assert len(custom_dimensions) == 8

    for item in expected_log_data:
        assert expected_log_data[item] == custom_dimensions[item]

    utils.verify_valid_uuid(custom_dimensions["Request Id"])

    os.remove(dest_fpath)
