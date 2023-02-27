import argparse
import coverage
import os
import sys
from junitparser import JUnitXml
import subprocess
from shutil import copyfile, rmtree
from pathlib import Path
import time
import uuid


# Note, if running this script locally from this folder, set these environment variables (replacing the path to the base image folder):
# export TEST_DIRECTORY=$(pwd)
# export ROOT_DIRECTORY=REPLACE_ME_WITH_PATH_TO/o16n-base-images/
# export OUTPUT_PATH=.


class TestSuite:
    def __init__(self, quiet, calculate_coverage):
        self.quiet = quiet
        self.calculate_coverage = calculate_coverage
        self.logger = self.create_logger()

    def create_logger(self):
        """Create a logger to log info while running tests."""
        import logging

        logger = logging.getLogger()
        level = logging.INFO if self.quiet else logging.DEBUG
        logger.setLevel(level)
        stdout_handler = logging.StreamHandler()
        logger.addHandler(stdout_handler)

        return logger

    def get_files_of_type(self, directory, extension):
        """
        Helper function that is equivalent to *.filetype for some directory

        :param directory: Target directory
        :param extension: File type
        """
        files_in_directory = os.listdir(directory)
        filtered_files = [file for file in files_in_directory if file.endswith(extension)]
        return filtered_files

    def remove_files_of_type(self, directory, extension):
        """
        Helper function that is equivalent to rm *.filetype for some directory

        :param directory: Target directory
        :param extension: File type
        """
        filtered_files = self.get_files_of_type(directory, extension)
        for file in filtered_files:
            path_to_file = directory / file
            self.logger.debug("Removing file: %s" % (path_to_file))
            os.remove(path_to_file)

    def merge_junit(self, file_list):
        merged_xml = JUnitXml()
        for file_path in file_list:
            self.logger.debug(f"MERGEING FILE {file_path}")
            merged_xml += JUnitXml.fromfile(file_path)

        return merged_xml

    def verify_env_variables(self):
        """
        Helper function that verifies required environment variables are set before running script
        """

        # we currently don't need to verify any env variables
        vars = []
        for v in vars:
            if v not in os.environ:
                raise AssertionError("The variable %s is not set. Please set it before running the test suite." % (v))

            self.logger.debug("Environment variable %s: %s" % (v, os.environ.get(v)))

    def add_files(self, files):
        """
        Helper function that adds files to specified locations

        :param files: List of pairs of form (original_path, dest_path)
        """

        for file_obj in files:
            self.logger.debug("Adding File %s to %s" % (file_obj[0], file_obj[1]))
            os.makedirs(os.path.dirname(file_obj[1]), exist_ok=True)
            if file_obj[0] != None:
                copyfile(file_obj[0], file_obj[1])

    def set_env_vars(self, env_vars):
        """
        Helper function that sets the environment variables

        :param env_vars: Dictionary of form {env_var_name, value}
        """

        for var_name in env_vars:
            self.logger.debug("Adding Environment Variable %s with value %s" % (var_name, env_vars[var_name]))
            os.environ[var_name] = env_vars[var_name]

    def clear_env_vars(self, env_vars):
        """
        Helper function that removes environment variables

        :param env_vars: Dictionary of form {env_var_name, value}
        """
        for var_name in env_vars:
            del os.environ[var_name]

    def test_setup(self, test):
        """
        Setup the environment variables and files needed to run a test.

        :param test: Dictionary of test configuration
        """
        if "env_vars" in test:
            self.logger.debug("Adding Environment Variables for Test %d" % (test["id"]))
            self.set_env_vars(test["env_vars"])

        if "files_to_add" in test:
            self.logger.debug("Adding Files for Test %d" % (test["id"]))
            self.add_files(test["files_to_add"])

    def run_test(self, test, TEST_PATH, DATA_PATH):
        """
        Run a single test with pytest and record covergae.

        :param test: Dictionary of test configuration
        :param TEST_PATH: base directory which contains test cases
        :param DATA_PATH: base directory which contains test resources like entry scripts
        """
        self.logger.info(f"\nTest {test['id']}: {test['path']}")
        self.logger.info(f"Entry script: {test['entry_script']}")
        # The following is equivalent to: coverage run -m pytest -s PATH -o junit_family=xunit2 --junitxml=002.xml --entry_script=ENTRY_SCRIPT_PATH
        # We use subprocess here instead of calling pytest.main directly because we are trying to avoid the python importing of files (in this case the main.py that is modified in each test)
        # We must run coverage through the subprocess so that it logs the values for the pytest
        # We want to use the executable path through sys.executable so that virtual environments are respected in the subprocess

        # prevent the black formatter from structuring this list as one item per line
        # fmt: off
        arguments = [
            sys.executable, "-m",
            "coverage", "run", "-m",
            "pytest",
                "-o",
                "junit_family=xunit2",
                "--junitxml=" + str(test["id"]) + ".xml",
                "--entry-script=" + str(DATA_PATH / test["entry_script"]),
                str(TEST_PATH / test["path"]),
        ]
        # fmt: on

        if self.quiet:
            arguments += ["--quiet", "-W ignore::DeprecationWarning"]
        else:
            arguments.append("-s")

        subprocess.call(arguments, env=os.environ.copy())

    def test_teardown(self, test):
        """
        Clean up environment variables and files after test ends.

        :param test: Dictionary of test configuration
        """
        # #Post test cleanup if needed
        if "cleanup" in test:
            self.logger.debug("Cleaning up Test %d" % (test["id"]))
            for to_remove in test["cleanup"]:
                os.remove(to_remove)

        # #Post test cleanup if needed
        if "cleanup_folders" in test:
            self.logger.debug("Removing Folders for Test %d" % (test["id"]))
            for to_remove in test["cleanup_folders"]:
                self.logger.debug("Removing folder %s" % (to_remove))
                rmtree(to_remove)

        if "env_vars" in test:
            self.logger.debug("Removing Environment Variables for Test %d" % (test["id"]))
            self.clear_env_vars(test["env_vars"])

    def generate_coverage_reports(self, OUTPUT_PATH):
        """
        Generate coverage reports and clean up coverage files

        :param OUTPUT_PATH: directory where we save coverage reports
        """
        ### GENERATE DOCUMENTATION FROM TESTS ###

        # Get the list of generated test xml files and merge them
        self.logger.debug("Merging generated text xml")
        generated_xmls = self.get_files_of_type(Path(".").resolve(), ".xml")

        junit_xml = self.merge_junit(generated_xmls)

        # Clean up generated xml files from every test
        self.remove_files_of_type(Path(".").resolve(), ".xml")

        junit_xml.write(OUTPUT_PATH / "discovery.xml")

    def run_all_tests(self):
        """
        Script that does the following:
        - Declares the tests to be run
        - Runs tests
        - Generates a merged xml of the tests that have been run
        - Generates a code coverage xml of the tests

        The following environment variables are required:
        Required:
            - TEST_DIRECTORY: The directory with the test cases and data
            - ROOT_DIRECTORY: The root of the repo
        Optional:
            - OUTPUT_PATH: The directory where generated files are output, relative to test directory, default is TEST_DIRECTORY
        """

        TEST_DIRECTORY = Path(__file__).resolve().parent
        ROOT = TEST_DIRECTORY.parents[3]
        DATA_PATH = TEST_DIRECTORY / "test_data"
        TEST_PATH = TEST_DIRECTORY / "test_cases"
        OUTPUT_PATH = TEST_DIRECTORY

        self.logger.debug("Set up environment variables to be used for tests")
        os.environ["TEST_DATA_PATH"] = str(DATA_PATH)  # For use in tests

        # Set the app root to current root
        os.environ["AML_APP_ROOT"] = str(ROOT)

        # Set the path to the coverage config file so we can run this script from any directory
        os.environ["COVERAGE_RCFILE"] = str(TEST_DIRECTORY / ".coveragerc")

        cov = coverage.Coverage()

        ##TEST SETUP##
        self.logger.debug("Declare tests")
        # List the test path and entry script pairing
        # If some generated files need to be deleted in cleanup, specify here
        # path: path to the test files
        # entry_scripts: path to the entry script files
        # cleanup: list of files to be deleted after the tests
        tests = [
            {
                "path": "appinsights/test_appinsights.py",
                "entry_script": "entry_scripts/default_main.py",
                "env_vars": {
                    "AML_APP_INSIGHTS_ENABLED": "true",
                    "AML_APP_INSIGHTS_KEY": str(uuid.uuid4()),
                    "AML_MODEL_DC_STORAGE_ENABLED": "true",
                    "AZUREML_MODEL_DIR": str(ROOT / "azureml-models"),
                },
                "files_to_add": [(None, ROOT / "azureml-models/test-model/1/something.txt")],
                "cleanup_folders": [ROOT / "azureml-models"],
            },
            {
                "path": "appinsights/test_appinsights_response_payload.py",
                "entry_script": "entry_scripts/default_main.py",
                "env_vars": {
                    "AML_APP_INSIGHTS_ENABLED": "true",
                    "AML_APP_INSIGHTS_KEY": str(uuid.uuid4()),
                    "APP_INSIGHTS_LOG_RESPONSE_ENABLED": "false",
                },
                "files_to_add": [(None, ROOT / "azureml-models/test-model/1/something.txt")],
                "cleanup_folders": [ROOT / "azureml-models"],
            },
            {
                "path": "appinsights/test_appinsights_response_binary.py",
                "entry_script": "entry_scripts/binary_main.py",
                "env_vars": {
                    "AML_APP_INSIGHTS_ENABLED": "true",
                    "AML_APP_INSIGHTS_KEY": str(uuid.uuid4()),
                    "APP_INSIGHTS_LOG_RESPONSE_ENABLED": "true",
                },
            },
            {
                "path": "appinsights/test_appinsights_exception.py",
                "entry_script": "entry_scripts/runtime_error_main.py",
                "env_vars": {
                    "AML_APP_INSIGHTS_ENABLED": "true",
                    "AML_APP_INSIGHTS_KEY": str(uuid.uuid4()),
                    "AML_MODEL_DC_STORAGE_ENABLED": "true",
                },
            },
            {
                "path": "appinsights/test_appinsights_recorder.py",
                "entry_script": "entry_scripts/default_main.py",
                "env_vars": {
                    "AML_APP_INSIGHTS_KEY": str(uuid.uuid4()),
                },
            },
            {
                "path": "appinsights/test_appinsights_recorder_exception.py",
                "entry_script": "entry_scripts/default_main.py",
            },
            {
                "path": "test_entry_debugpy.py",
                "entry_script": "entry_scripts/default_main.py",
            },
            {
                "path": "aml_blueprint/test_blueprint_score_not_found.py",
                "entry_script": "entry_scripts/default_main.py",
            },
        ]

        self.logger.debug(f"TESTS JSON: {tests}")

        ##TEST RUN##
        self.logger.debug("Run tests")
        for i, test in enumerate(tests):
            test["id"] = i
            self.test_setup(test)
            self.run_test(test, TEST_PATH, DATA_PATH)
            self.test_teardown(test)

        if self.calculate_coverage:
            self.generate_coverage_reports(OUTPUT_PATH)


def create_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-q", "--quiet", action="store_true")
    parser.add_argument("-c", "--enable-coverage", action="store_true")
    return parser


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()

    suite = TestSuite(quiet=args.quiet, calculate_coverage=args.enable_coverage)
    suite.run_all_tests()
