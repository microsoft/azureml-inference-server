# This file defines any fixtures and configurations used for the tests
import pytest
import sys, os
from shutil import copyfile
import flask

from azureml_inference_server_http.constants import SERVER_ROOT, DEFAULT_APP_ROOT


"""
Define any command line arguments. We specify the entry script here
so that it can be passed in.
"""


def pytest_addoption(parser):
    parser.addoption("--entry-script", action="store", default="default_main.py")


"""
Pytest fixture that defines the entry script from the command line argument.
"""


@pytest.fixture(scope="session")
def entry_script(pytestconfig):
    return pytestconfig.getoption("entry_script")


"""
Pytest fixture that defines the app object before
every test. We can use the one that is initialized
in common/server/entry, since the create_app() function
does not take any unique parameters.
"""


@pytest.fixture(scope="session")
def app(entry_script):
    dest_fpath = os.path.join(SERVER_ROOT, "main.py")
    os.makedirs(os.path.dirname(dest_fpath), exist_ok=True)
    copyfile(entry_script, dest_fpath)

    # Modify the path so we can search from the server root
    # Inserting into sys path as recommended in the stackoverflow thread
    # https://stackoverflow.com/questions/10095037
    sys.path.insert(1, SERVER_ROOT)

    from azureml_inference_server_http.server import entry

    app = entry.app

    yield app

    os.remove(dest_fpath)


"""
Pytest fixture to the test client on the Flask app.
"""


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def logging_config():
    """
    Loading the default log config when importing config causes log
    propagation to be disabled, which means caplog cannot capture it. We can
    get around this by loading a different log config through the entry script
    directory or the app root.
    """
    test_config = os.path.join(os.path.dirname(__file__), "test_logging_config.json")
    target_config = os.path.join(os.getenv("AML_APP_ROOT", DEFAULT_APP_ROOT), "logging.json")

    yield copyfile(test_config, target_config)

    os.remove(target_config)
