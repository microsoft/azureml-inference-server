# Unit tests for exception cases on AMLBlueprint using no score script
import logging
import pytest
import sys, os
from shutil import copyfile

from azureml_inference_server_http.constants import SERVER_ROOT

"""
This test affirms that when an entry script is not found,
we recognize the error and correctly provide logs to help
user debug.
Note: In future, it should be moved to new_tests/
"""


def test_script_not_found(entry_script, logging_config, caplog):
    dest_fpath = os.path.join(SERVER_ROOT, "main.py")
    if os.path.exists(dest_fpath):
        os.remove(dest_fpath)

    # Modify the path so we can search from the server root
    sys.path.insert(1, SERVER_ROOT)

    caplog.set_level(logging.INFO, "azmlinfsrv")

    with pytest.raises(SystemExit) as expected_error:
        from azureml_inference_server_http.server.entry import app

    expected_err_msg = "No score script found. Expected score script main.py."
    error_tuple = ("azmlinfsrv", logging.ERROR, expected_err_msg)

    assert error_tuple in caplog.record_tuples
    assert expected_error.type == SystemExit
