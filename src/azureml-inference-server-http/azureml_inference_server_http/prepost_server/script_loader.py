import importlib.util
import os
import sys
import inspect

from sanic.log import logger
from .constants import ENV_AML_APP_ROOT, ENV_AML_ENTRY_SCRIPT, SCRIPT_CLASS_NAME
from .user.exceptions import UserCodeException, UserCodeConfigurationException
from .log_settings import get_custom_dimensions


class ScriptLoader(object):
    def __init__(self, config):
        try:
            self.user_module = self.import_source(config)
            self.user_class = self.user_module.ModelHandler()
        except UserCodeConfigurationException as e:
            logger.critical(f"Error. Exiting with exception: {str(e)}", extra=get_custom_dimensions())
            sys.exit(f"Unable to load pre and postprocessing script. Error: {str(e)}")

    def import_source(self, config):
        app_root = config[ENV_AML_APP_ROOT]
        entry_script = config[ENV_AML_ENTRY_SCRIPT]

        script_location = os.path.join(app_root, entry_script.replace("/", os.sep))
        if not os.path.isfile(script_location):
            raise UserCodeConfigurationException(f"No file found at location: {script_location}")

        try:
            logger.debug(f"Loading user's module from: {script_location}", extra=get_custom_dimensions())
            module_name = "score_script_module"
            module_spec = importlib.util.spec_from_file_location(module_name, script_location)
            module = importlib.util.module_from_spec(module_spec)
            module_spec.loader.exec_module(module)
        except Exception as e:
            raise UserCodeConfigurationException(f"Error loading script from {script_location}. Exception: {e}")

        if self.validate_score_script(module):
            return module
        else:
            logger.critical(
                f"Invalid processing script from location: {script_location}", extra=get_custom_dimensions()
            )
            raise UserCodeConfigurationException(
                f"Error loading script from {script_location}. Expected {SCRIPT_CLASS_NAME} class not found."
            )

    def preprocess(self, raw_data, ctx):
        try:
            return self.user_class.preprocess(raw_data, ctx)
        except Exception as e:
            logger.error(f"Error in preprocess: {str(e)}", extra=get_custom_dimensions())
            raise UserCodeException(f"Encountered error in preprocess: {str(e)}")

    def postprocess(self, raw_data, ctx):
        try:
            return self.user_class.postprocess(raw_data, ctx)
        except Exception as e:
            logger.error(f"Error in postprocess: {str(e)}", extra=get_custom_dimensions())
            raise UserCodeException(f"Encountered error in postprocess: {str(e)}")

    @staticmethod
    def validate_score_script(module):
        handler_class = next(
            filter(
                lambda member_obj: inspect.isclass(member_obj[1]) and member_obj[0] == SCRIPT_CLASS_NAME,
                inspect.getmembers(module),
            ),
            None,
        )
        return handler_class is not None
