import parser
import pytest
import os
import sys
from datetime import datetime
from psutil import process_iter
from signal import SIGTERM
from multiprocessing import Process

from .constants import DEFAULT_PORT


def pytest_addoption(parser):
    now = datetime.now()
    parser.addoption("--test_run_name", action="store", default=now.strftime("%Y-%m-%d_%H-%M-%S"))


@pytest.fixture(scope="session")
def test_run_name(pytestconfig):
    return pytestconfig.getoption("test_run_name")


@pytest.fixture(scope="session", autouse=True)
def create_log_directory(test_run_name):
    path = os.path.join("out", test_run_name)
    if not os.path.exists(path):
        os.makedirs(path)

    def my_func(name):
        return os.path.join(path, name)

    return my_func


@pytest.fixture()
def log_directory(create_log_directory, test_run_name):
    test_case_name = os.environ.get("PYTEST_CURRENT_TEST").split(":")[-1].split(" ")[0]
    path = os.path.join("out", test_run_name, test_case_name)
    if not os.path.exists(path):
        os.makedirs(path)

    return path


@pytest.fixture(scope="session")
def root_folder():
    return os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    )


# Frees the default port used by the azureml server before the test is ran.
@pytest.fixture(autouse=True)
def free_port():
    try:
        for proc in process_iter():
            for conns in proc.connections(kind="inet"):
                if conns.laddr.port == DEFAULT_PORT:
                    proc.send_signal(SIGTERM)
    except Exception as ex:
        print(ex)
