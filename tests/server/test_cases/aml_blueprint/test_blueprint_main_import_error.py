# This file includes tests that use the import_error_main entry script
import pytest
import sys, os
from shutil import copyfile

from azureml_inference_server_http.constants import SERVER_ROOT

"""
This test affirms that when an exception is raised
with main.py, the exception is correctly caught and
reported.
Note: In future, it should be moved to new_tests/
"""


def test_import_error_failure(entry_script, capfd):
    dest_fpath = os.path.join(SERVER_ROOT, "main.py")
    os.makedirs(os.path.dirname(dest_fpath), exist_ok=True)
    copyfile(entry_script, dest_fpath)

    # Modify the path so we can search from the server root
    sys.path.insert(1, SERVER_ROOT)

    with pytest.raises(SystemExit) as expected_error:
        from azureml_inference_server_http.server.entry import app

    out, _ = capfd.readouterr()

    assert "ModuleNotFoundError: No module named 'asdf'" in out
    assert expected_error.type == SystemExit

    os.remove(dest_fpath)
