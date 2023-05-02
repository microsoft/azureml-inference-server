# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.


class AzmlinfsrvError(Exception):
    pass


class AzmlAssertionError(AzmlinfsrvError):  # pragma: no cover
    def __init__(self, reason: str):
        message = (
            "It looks like you have encountered a bug in the azureml-inference-server-http package. "
            "Please reach out to us with the stack trace and a description on how you encountered this error.\n"
            f"Error: {reason}"
        )
        super().__init__(message)
