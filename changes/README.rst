============================================================================
Azure Machine Learning Inference HTTP Server (azureml-inference-server-http)
============================================================================

Check our official documentation `here <https://docs.microsoft.com/en-us/azure/machine-learning/how-to-inference-server-http>`__.

We are currently working on an updated version of this package, if you would like to suggest features or share feedback please fill out this form `here
<https://forms.office.com/Pages/ResponsePage.aspx?id=v4j5cvGGr0GRqy180BHbRzjWjI2uwMBOsl7fXFLuCRJUNEc4MFVTVThKRUgxTjNGTTExMVc3M1E1QS4u>`__.

Python 3.7 Deprecation
======================

- Python 3.7 support on all platforms will be dropped in **June, 2023** in line with stated end-of-life as noted in the `python developer guide <https://statics.teams.cdn.office.net/evergreen-assets/safelinks/1/atp-safelinks.html>`__.

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

* AML_APP_ROOT
* AZUREML_SOURCE_DIRECTORY
* AZUREML_ENTRY_SCRIPT
* SERVICE_NAME
* WORKSPACE_NAME
* SERVICE_PATH_PREFIX
* SERVICE_VERSION
* SCORING_TIMEOUT_MS
* AML_FLASK_ONE_COMPATIBILITY
* AZUREML_LOG_LEVEL
* AML_APP_INSIGHTS_ENABLED
* AML_APP_INSIGHTS_KEY
* AML_MODEL_DC_STORAGE_ENABLED
* APP_INSIGHTS_LOG_RESPONSE_ENABLED
* AML_CORS_ORIGINS
* AZUREML_MODEL_DIR
* HOSTNAME
* AZUREML_DEBUG_PORT

Sample config.json:

| {
| "AZUREML_ENTRY_SCRIPT": "/mnt/d/tests/manual/default_score.py"
| "AML_CORS_ORIGINS": "www.microsoft.com ",
| "SCORING_TIMEOUT_MS": 6000,
| "AML_APP_INSIGHTS_ENABLED": true
| }


Changelog
=========

