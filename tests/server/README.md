# HTTP Flask Server Unit Tests

These tests verify the functionality of the components of the Flask HTTP server. 

## Adding and modifying tests

To add or edit tests, modify the `test_suite.py` file. Navigate to the `tests` json object to add or remove tests.

- For local debugging, a good strategy is to comment out any tests that aren't necessary while verifying your code!

Example test object:

```python
{
    "path": "debuggability/test_debug_model_info.py",
    "entry_script": "entry_scripts/default_main.py",
    "files_to_add": [
        (
            DATA_PATH / "sample_model_config_map.json",
            ROOT / "model_config_map.json",
        )
    ],
    "cleanup": [ROOT / "model_config_map.json"],
    "env_vars": {"AML_DBG_MODEL_INFO": "true"},
}
```

- The `path` key points to the path of the test file. To create a new pytest file, navigate to the `test_cases` folder and create a new file for your unit test. 
- The `entry_script` file is the path to the entry script used for this test object. To create a new entry script, navigate to `test_data/entry_scripts/` to create a new file. 
- `files_to_add` indicates the files that will be added to the server for this test. These files should live under the `test-data` directory
- `cleanup` will point to files that need to be removed once the test is done. `cleanup_folders` is used to remove entire directories, rather than singular files.
- `env_vars` includes a dictionary of environment variables that will be activated for this unit test.

To create new tests, create test objects in the format specified above and add them to the `tests` dictionary. Most likely, new entry scripts and pytest files will need to be created, so place them in the areas indicated above for your `path` and `entry_script` specifications.


## Running tests locally

Unit tests can be run locally to verify changes in the Flask HTTP server.

To test locally using the same configuration as the [Inference Server Unit Tests and Test Coverage](https://msdata.visualstudio.com/Vienna/_build?definitionId=13679&_a=summary) CI pipeline, run:
```shell
python test_suite.py
```
The following options are available to run the `test_suite.py`.
- Run with the `-q` flag to run the test suite quietly
  `python test_suite.py -q`
- Run with the `-c` flag to run with coverage.
  `python test_suite.py -c`