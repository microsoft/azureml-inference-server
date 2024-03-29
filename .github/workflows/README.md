## Prepare a new version

1. Update [_version.py](https://github.com/microsoft/azureml-inference-server/tree/main/azureml_inference_server_http/_version.py) with a new version number.
2. In the root folder, run `towncrier --draft` to see what the changelog would look like.
3. If it looks good, run `towncrier` to commit the changelog to [CHANGELOG.rst](https://github.com/microsoft/azureml-inference-server/tree/main/azureml_inference_server_http/CHANGELOG.rst)
4. Create a PR with the changes.

## Build & Release

1. Merge the PR created in the above step.
2. Create a new release on the github with the tag v(version in _version.py). Ex: v0.8.0
3. **Important: For major releases (in our case ~0.X.0), azureml-defaults must be updated to use this new package** 