# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""AMLRequest class used by score.py that needs raw HTTP access"""

from flask import Request

_rawHttpRequested = False


# `rawhttp` is an attribute to be applied on run() function in score.py to request raw http access.
#
# Example score.py:
#
# from azureml_inference_server_http.api.aml_request  import rawhttp
# from azureml_inference_server_http.api.aml_response import AMLResponse
#
# @rawhttp
# def run(request):
#   ...
#   return AMLResponse(outBytes, 200, {'Content-Type': 'image/jpeg'})
#
# The `request` in `run()` will be of type AMLRequest.
# And `run()` function could return either AMLResponse (that will be returned to the requester as-is),
# or (as before) any object or string that will be automatically converted to JSON.
def rawhttp(func):
    """Attribute applied to run() function in score.py to request raw HTTP access"""
    global _rawHttpRequested
    _rawHttpRequested = True
    return func


# Only exists to avoid score.py have dependency on Flask directly
class AMLRequest(Request):
    """AMLRequest class used by score.py that needs raw HTTP access"""

    def __init__(self):
        """Create new instance"""
        super().__init__()
