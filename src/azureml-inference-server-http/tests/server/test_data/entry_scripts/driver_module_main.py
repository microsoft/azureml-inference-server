import os
import importlib.util as imp

script_location = os.path.join(os.environ.get("AML_APP_ROOT"), "sample_driver_module_script.py")

driver_module_spec = imp.spec_from_file_location("service_driver", script_location)
driver_module = imp.module_from_spec(driver_module_spec)
driver_module_spec.loader.exec_module(driver_module)


def init():
    print("Driver Module init function invoked.")
    driver_module.init()


def run(input):
    print("Driver Module run function invoked.")
    return_obj = driver_module.run(input)
    return return_obj
