# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

import sys

from .config import config  # noqa: I100

debug_port = config.debug_port
if debug_port:
    print("!! Starting the inference server in DEBUGGING mode because AZUREML_DEBUG_PORT is set.")
    print("!! This environment variable should not be set in a production environment.")

    try:
        import debugpy
    except ModuleNotFoundError:
        print("** Cannot connect to a debugger because debugpy is not installed.")
        sys.exit(-1)

    print(f"** Connecting to debugger at port {debug_port}...")
    debugpy.connect(debug_port)
    debugpy.wait_for_client()


from .create_app import create  # noqa: E402, I100, I202

app = create()
