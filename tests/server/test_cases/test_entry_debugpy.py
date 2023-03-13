import os
from shutil import copyfile
import sys
import unittest.mock

from azureml_inference_server_http.constants import SERVER_ROOT


def test_entry_debugpy(entry_script):
    dest_fpath = os.path.join(SERVER_ROOT, "main.py")
    os.makedirs(os.path.dirname(dest_fpath), exist_ok=True)
    copyfile(entry_script, dest_fpath)

    # Modify the path so we can search from the server root
    sys.path.insert(1, SERVER_ROOT)

    PORT = 33889  # An arbitrary number.
    with unittest.mock.patch("debugpy.connect") as connect_mock:
        with unittest.mock.patch("debugpy.wait_for_client") as wait_mock:
            os.environ["AZUREML_DEBUG_PORT"] = str(PORT)

            from azureml_inference_server_http.server.entry import app

            connect_mock.assert_called_with(PORT)
            assert wait_mock.called
