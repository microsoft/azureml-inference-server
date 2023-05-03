# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""AMLResponse class used by score.py that needs raw HTTP access"""

import json

from flask import Response


class AMLResponse(Response):
    """AMLResponse class used by score.py that needs raw HTTP access"""

    def __init__(self, message, status_code, response_headers={}, json_str=False, run_function_failed=False):
        """Create new instance"""
        if message is not None:
            if json_str:
                super().__init__(json.dumps(message), status=status_code, mimetype="application/json")
            else:
                super().__init__(message, status=status_code)
                content_type = "Content-Type"
                if content_type in response_headers:
                    self.headers.remove(content_type)  # remove to avoid duplication as the for loop below will add it
        else:
            # return empty json if message is None
            super().__init__(json.dumps({}), status=status_code, mimetype="application/json")

        self.headers["x-ms-run-function-failed"] = run_function_failed

        # If the user run() want to response repeated headers, comma should be used as the seperator
        # https://www.w3.org/Protocols/rfc2616/rfc2616-sec4.html#sec4.2
        for header, value in response_headers.items():
            for v in value.split(","):
                self.headers.add_header(header, v.strip())
