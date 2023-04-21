import importlib.util as imp
import os


script_location = os.path.join(os.path.dirname(__file__), "simple_schema.py")
driver_module_spec = imp.spec_from_file_location("service_driver", script_location)
driver_module = imp.module_from_spec(driver_module_spec)
driver_module_spec.loader.exec_module(driver_module)


def init():
    os.environ["simple_schema_driver_init_called"] = "1"
    driver_module.init()


def run(input, request_headers):
    return driver_module.run(input) + 7
