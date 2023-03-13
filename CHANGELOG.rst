0.8.0 (2022-12-15)
~~~~~~~~~~~~~~~~~~

Breaking Changes
----------------

- Drop support for Python 3.6

Enhancements
------------

- All error responses will be in json. (Format: {'message': <error_message>})
- Loggers can be configured by users through a logging.json file in
  `AML_APP_ROOT` or alongside the entry script.

  Log message default format has been updated. (Format: "<UTC DATE> <UTC TIME>
  <LOG LEVEL CHAR> [<PID>] <LOGGER NAME> - <MESSAGE>")


0.7.7 (2022-11-01)
~~~~~~~~~~~~~~~~~~

Fixes
-----

- Upgrade ``inference-schema`` dependency to support Python 3.9


0.7.6 (2022-09-13)
~~~~~~~~~~~~~~~~~~

Fixes
-----

- ``AML_APP_ROOT`` variable is now defaulted to the current working directory
- ``AZUREML_ENTRY_SCRIPT`` is now set to an absolute path to the entry script


0.7.5 (2022-08-16)
~~~~~~~~~~~~~~~~~~

Breaking Changes
----------------

- The header for Client Request ID is renamed from ``x-client-request-id`` to ``x-ms-client-request-id``.
- Server will no longer throw an error when both ``x-ms-request-id`` and ``x-request-id`` are provided. Going forward,
  ``x-ms-request-id`` will be treated as the Client Request ID. However, it is still considered deprecated and users
  are recommended to use ``x-ms-client-request-id`` for Client Request ID.

  - When neither ``x-ms-request-id`` or ``x-ms-client-request-id`` is set, the server copies the value of
    ``x-request-id`` to ``x-ms-request-id``. This is done to preserve backwards compatability, ensuring that
    ``x-ms-request-id`` is not empty. No value is logged to AppInsights as "Client Request Id".
  - When only ``x-ms-request-id`` is set, the server returns ``x-ms-request-id`` and ``x-ms-client-request-id`` set to the
    value. This value is logged to AppInsights as "Client Request Id".
  - When only ``x-ms-client-request-id`` is set, the server returns ``x-ms-request-id`` and ``x-ms-client-request-id``
    set to the value. This value is logged to AppInsights as "Client Request Id".
  - When both ``x-ms-request-id`` and ``x-ms-client-request-id`` are set, the values are returned in the respective
    headers. However, only the value from ``x-ms-client-request-id`` is logged to AppInsights as "Client Request Id".


0.7.4 (2022-07-29)
~~~~~~~~~~~~~~~~~~

Fixes
-----

- Fix an issue where the server would require arguments that have default values in run().


0.7.3 (2022-07-18)
~~~~~~~~~~~~~~~~~~

Features
--------

- CORS can be enabled with the environment variable ``AML_CORS_ORIGINS``. Refer to README for detailed usage.
- Server can now be started with ``python -m azureml_inference_server_http`` in additional to ``azmlinfsrv``.
- OPTIONS calls are modified to return ``200 OK`` instead of the previous ``405 Method not allowed``.
- Users can bring their own swaggers by placing ``swagger2.json`` and ``swagger3.json`` in ``AML_APP_ROOT``.

Enhancements
------------

- Swaggers are always generated now, regardless whether the user's run() function is decorated with inference-schema. 
- The x-request-id and x-client-request-id headers are now limited to 100 characters.

Fixes
-----

- Fixed an issue that prevents the server from cleanly exiting when the scoring script cannot be initialized. If
  AppInsights is not enabled, users may see ``AttributeError: 'AppInsightsClient' object has no attribute 'logger'``.


0.7.2 (2022-06-06)
~~~~~~~~~~~~~~~~~~

Enhancements
------------

- Added support for Flask 2.1.

- The server now responds with a 400 Bad Request when it finds invalid inputs.


0.7.1 (2022-05-10)
~~~~~~~~~~~~~~~~~~

Deprecation
-----------

- The "x-ms-request-id" header is deprecated and is being replaced by "x-request-id". Until "x-ms-request-id" is
  removed, the server will accept either header and respond with both headers set to the same request id. Providing two
  request ids through the headers is not allowed and will be responded with a Bad Request.


Enhancements
------------

- Added support for Flask 2.0. A compatibility layer is introduced to ensure this upgrade doesn't break users who use
  ``@rawhttp`` as the methods on the Flask request object have slightly changed. Specifically,

  * ``request.headers.has_keys()`` was removed
  * ``request.json`` throws an exception if the content-type is not "application/json". Previously it returns ``None``.

  The compatibility layer restores these functionalities to their previous behaviors. However, this compatibility layer
  will be removed in a future date and users are encouraged to audit their score scripts today. To see if your score
  script is ready for Flask 2, run the server with the environment variable ``AML_FLASK_ONE_COMPATIBILITY`` set to
  ``false``.
 
  Flask's full changelog can be found here: https://flask.palletsprojects.com/en/2.1.x/changes/

- Added support for the "x-request-id" and "x-client-request-id" headers. A new GUID is generated for "x-request-id" if
  one is not provided. These values are echoed back to the client in the response headers. 
