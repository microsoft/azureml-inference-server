"""
Helper functions for checking response contents are equal
"""
from uuid import UUID
import json


def verify_valid_uuid(uuid_string):
    """
    Helper function that parses a uuid string to validate it

    :param uuid_string: UUID string to parse
    """
    # If the following line parses, then it is valid UUID
    UUID(uuid_string).hex
    return


def verify_headers(response, expected_headers, expected_num_headers):
    """
    Helper function that validates the expected headers.
    Note that lambda functions will need to deal with asserts on their
    own, for example, if there are multiple asserts within that function,
    etc.

    :param response: Response object to check
    :param expected_headers: The expected response
    """

    print("Actual Response Headers:\n ", response.headers)

    assert len(response.headers) == expected_num_headers

    for header in expected_headers:
        if isinstance(expected_headers[header], str):
            assert expected_headers[header] == response.headers[header]
        else:
            # Run lambda function for verify uuid
            expected_headers[header](response.headers[header])


def verify_default_headers(response, content_type="application/json"):
    """
    Helper function that validates the default values for the headers
    in the general case are correct

    :param response: Response object to check
    """

    print("Actual Response Headers:\n ", response.headers)
    verify_valid_uuid(response.headers["x-ms-request-id"])
    verify_valid_uuid(response.headers["x-request-id"])
    assert response.headers["Content-Type"] == content_type
    assert int(response.headers["Content-Length"]) > 0
    assert response.headers["x-ms-run-function-failed"] == "False"
    return


def assert_response(
    response,
    expected_status_code,
    expected_data,
    expected_headers={},
    check_default_headers=True,
    check_passed_headers=True,
    check_json_data=False,
    content_type="application/json",
):
    """
    Helper function that validates a response is valid

    :param response: Response object to check
    :param expected_status_code: Expected Status Code in response
    :param expected_data: Expected data in response
    :param expected headers (optional): The expected headers in the response
    :param check_default_headers (optional): Flag that indicates to check if default headers are present
    :param check_passed_headers (optional): Flag that indicates to check the headers passed in expected headers
    """

    print("Actual Response Status Code: ", response.status_code)
    assert response.status_code == expected_status_code

    print("Actual Response Data: ", response.data)
    if check_json_data:
        response_json = response.get_json()
        expected_json = json.loads(expected_data)
        assert expected_json == response_json
    else:
        assert response.data == expected_data

    # Verify same number of headers, note that there are 4 default headers
    # We verify headers in this function if default headers are set, otherwise verify headers directly
    # in the test case
    if check_default_headers:
        verify_default_headers(response, content_type)

        if check_passed_headers:
            for header in expected_headers:
                assert response.headers[header] == expected_headers[header]
            assert len(response.headers) == (len(expected_headers) + 6)
    return


def assert_error_message(response, expected_status_code, expected_message, check_default_headers=True):
    """
    Helper function that validates an error response

    :param response: Response object to check
    :param expected_status_code: Expected Status Code in response
    :param expected_message: Expected data in response
    :param check_default_headers (optional): Flag that indicates to check if default headers are present
    """

    if check_default_headers:
        verify_default_headers(response)

    print("Actual Response Status Code: ", response.status_code)
    assert response.status_code == expected_status_code
    print("Actual Response Data: ", response.data)
    assert response.data == expected_message
    return


def is_float_string(string):
    """Checks whether a string can be parsed as a float."""

    try:
        float(string)
    except ValueError:
        assert False
