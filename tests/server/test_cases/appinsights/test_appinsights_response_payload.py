# This file includes tests that use the default_main entry script and appinsights
# environment variables set

from test_cases import utils
import os
import sys
import datetime
from shutil import copyfile
from unittest.mock import Mock

from azureml_inference_server_http.constants import SERVER_ROOT
from opencensus.trace.blank_span import BlankSpan


"""
Verifies that a score GET request with log no response payload
sends proper logs to appinsights
"""


def test_appinsights_request_no_response_payload_log(entry_script):
    print("Logger execution path: ", SERVER_ROOT)

    dest_fpath = os.path.join(SERVER_ROOT, "main.py")
    os.makedirs(os.path.dirname(dest_fpath), exist_ok=True)
    copyfile(entry_script, dest_fpath)

    # Modify the path so we can search from the server root
    sys.path.insert(1, SERVER_ROOT)

    from azureml_inference_server_http.server import entry

    app = entry.app

    logger = Mock()
    logger.addHandler.side_effect = Mock()
    app.azml_blueprint.appinsights_client.logger = logger

    mock_tracer = Mock()
    mock_span = BlankSpan()
    mock_tracer.span = Mock(return_value=mock_span)

    app.azml_blueprint.appinsights_client.tracer = mock_tracer

    client = app.test_client()

    # Set up the request
    response = client.get("/score")

    # Check 200 response and proper headers
    expected_code = 200
    expected_data = b"{}"

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
        "url": "http://localhost/score",
        "Container Id": "Unknown",
        "Client Request Id": "",
        "Response Value": None,
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
