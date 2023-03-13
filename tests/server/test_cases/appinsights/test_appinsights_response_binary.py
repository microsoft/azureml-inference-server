# This file includes tests that use the default_main entry script and appinsights
# environment variables set
import os
import sys
from shutil import copyfile
from unittest.mock import Mock

from azureml_inference_server_http.constants import SERVER_ROOT
from opencensus.trace.blank_span import BlankSpan


def test_appinsights_response_not_string(entry_script):
    """
    Verifies the appinsights logging with scoring request response
    not a valid string
    """
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
    assert response.status_code == 200

    expected_data = {
        "resultCode": "200",
        "success": True,
        "name": "/score",
        "url": "http://localhost/score",
        "Container Id": "Unknown",
        "Response Value": '"Scoring request response payload is a non serializable object or raw binary"',
        "Workspace Name": "",
        "Service Name": "ML service",
    }

    print("Actual Log:\n", mock_span.attributes)

    for item in expected_data:
        assert expected_data[item] == mock_span.attributes[item]

    os.remove(dest_fpath)
