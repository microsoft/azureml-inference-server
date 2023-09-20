============================================================================
Azure Machine Learning Inference HTTP Server (azureml-inference-server-http)
============================================================================

Check our official documentation `AzureML Inference Server - Docs <https://docs.microsoft.com/en-us/azure/machine-learning/how-to-inference-server-http>`__.

Please note, the AzureML Inference Server is now open source! The repo is available here: `AzureML Inference Server - Github <https://github.com/microsoft/azureml-inference-server>`__.

CORS support
=============

Cross-origin resource sharing is a way to allow resources on a webpage to be requested from another domain. CORS works
via HTTP headers sent with the client request and returned with the service response. For more information on CORS and
valid headers, see `Cross-origin resource sharing <https://en.wikipedia.org/wiki/Cross-origin_resource_sharing>`__ in
Wikipedia.

Users can specify the domains allowed for access through the ``AML_CORS_ORIGINS`` environment variable, as a comma
separated list of domains, such as ``www.microsoft.com, www.bing.com``. While discouraged, users can also set it to
``*`` to allow access from all domains. CORS is disabled if this environment variable is not set.

Existing usage to employ ``@rawhttp`` as a way to specify CORS header is not affected, and can be used if you need more
granular control of CORS (such as the need to specify other CORS headers). See `here
<https://docs.microsoft.com/en-us/azure/machine-learning/how-to-deploy-advanced-entry-script#cross-origin-resource-sharing-cors>`__
for an example.

Loading server config from a json file
======================================

Server supports the loading of the config using a json file.
Config file can be specified using:

1. The env variable ``AZUREML_CONFIG_FILE`` (the absolute path to the json configuration file).
2. CLI parameter --config_file. 

Note:

1. All the paths mentioned in the config.json (configuration file) should be absolute path.
2. Priority: CLI > ENV Variable > config file

config.json will be searched in below locations by default if config file is not provided explicitly using env variable/CLI paramter:

1. AML_APP_ROOT directory
2. Directory containing the scoring script

Config file will support only below keys:

+-----------------------------------+-----------+-----------------------+
| Key                               | Required? | Default Value         |
+-----------------------------------+-----------+-----------------------+
| AML_APP_ROOT                      | Yes       | "/var/azureml-app"    |
+-----------------------------------+-----------+-----------------------+
| AZUREML_SOURCE_DIRECTORY          | No        |                       |
+-----------------------------------+-----------+-----------------------+
| AZUREML_ENTRY_SCRIPT              | No        |                       |
+-----------------------------------+-----------+-----------------------+
| SERVICE_NAME                      | Yes       | "ML service"          |
+-----------------------------------+-----------+-----------------------+
| WORKSPACE_NAME                    | Yes       |  ""                   |
+-----------------------------------+-----------+-----------------------+
| SERVICE_PATH_PREFIX               | Yes       |  ""                   |
+-----------------------------------+-----------+-----------------------+
| SERVICE_VERSION                   | Yes       | "1.0"                 |
+-----------------------------------+-----------+-----------------------+
| SCORING_TIMEOUT_MS                | Yes       |  3600 * 1000          |
+-----------------------------------+-----------+-----------------------+
| AML_FLASK_ONE_COMPATIBILITY       | Yes       | "True"                |
+-----------------------------------+-----------+-----------------------+
| AZUREML_LOG_LEVEL                 | Yes       |  "INFO"               |
+-----------------------------------+-----------+-----------------------+
| AML_APP_INSIGHTS_ENABLED          | Yes       |  False                |
+-----------------------------------+-----------+-----------------------+
| AML_APP_INSIGHTS_KEY              | No        | None                  |
+-----------------------------------+-----------+-----------------------+
| AML_MODEL_DC_STORAGE_ENABLED      | Yes       | False                 |
+-----------------------------------+-----------+-----------------------+
| APP_INSIGHTS_LOG_RESPONSE_ENABLED | Yes       | "True"                |
+-----------------------------------+-----------+-----------------------+
| AML_CORS_ORIGINS                  | No        | None                  |
+-----------------------------------+-----------+-----------------------+
| AZUREML_MODEL_DIR                 | Yes       |  False                |
+-----------------------------------+-----------+-----------------------+
| HOSTNAME                          | No        | "Unknown"             |
+-----------------------------------+-----------+-----------------------+
| AZUREML_DEBUG_PORT                | No        | None                  |
+-----------------------------------+-----------+-----------------------+

The code for the config can be found here: `config.py <https://github.com/microsoft/azureml-inference-server/blob/main/azureml_inference_server_http/server/config.py>`__.

Sample config.json:

| {
| "AZUREML_ENTRY_SCRIPT": "/mnt/d/tests/manual/default_score.py"
| "AML_CORS_ORIGINS": "www.microsoft.com ",
| "SCORING_TIMEOUT_MS": 6000,
| "AML_APP_INSIGHTS_ENABLED": true
| }


Changelog
=========

